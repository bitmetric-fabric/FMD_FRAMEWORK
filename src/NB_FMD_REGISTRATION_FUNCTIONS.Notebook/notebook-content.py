# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # Registration functions and editor
# The library behind NB_REGISTRATIE, in two parts: the functions (read the registration, check it, register,
# start the discovery) and, further down, the editor (`registration_ui`, ipywidgets), which is only a screen on
# top of them. One notebook because NB_REGISTRATIE does a single %run. Lives in the configuration workspace,
# next to SQL_FMD_FRAMEWORK, so it never needs a GUID for the config database: it looks up the one SQLDatabase
# item in its own workspace through the Fabric REST API. Framework-owned: the setup overwrites it on every run,
# unlike NB_REGISTRATIE itself.

# CELL ********************

import struct, pyodbc, time, json, requests, re

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def resolve_config_database():
    """
    Finds the SQLDatabase item in the current (configuration) workspace and returns
    (driver, connstring, database) for execute_with_outputs. No GUID in the code: the workspace
    is whichever one this notebook runs in.
    """
    token = notebookutils.credentials.getToken('https://analysis.windows.net/powerbi/api')
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {token}'})

    workspace_id = notebookutils.runtime.context['currentWorkspaceId']
    items = session.get(f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items")
    items.raise_for_status()
    databases = [i for i in items.json().get('value', []) if i['type'] == 'SQLDatabase']
    if len(databases) != 1:
        raise RuntimeError(f"Expected one SQLDatabase item in this workspace, found {len(databases)}.")

    detail = session.get(f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/sqldatabases/{databases[0]['id']}")
    detail.raise_for_status()
    props = detail.json()['properties']
    return '{ODBC Driver 18 for SQL Server}', props['serverFqdn'], props['databaseName']

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def build_exec_statement(proc_name, **params):
    """Build a parameterized EXEC statement for safe stored procedure execution.

    Returns:
        tuple: (sql_template with ? placeholders, list of parameter values)
    """
    param_placeholders = []
    param_values = []
    for key, value in params.items():
        if value is not None:
            param_placeholders.append(f"@{key}=?")
            param_values.append(value)

    if param_placeholders:
        sql = f"EXEC {proc_name} " + ", ".join(param_placeholders)
    else:
        sql = f"EXEC {proc_name}"
    return sql, param_values

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def execute_with_outputs(exec_statement, driver, connstring, database, **params):
    """
    Runs the given T-SQL (optionally wrapping to capture return code).
    Returns a dict with:
      - result_sets: list[list[dict]]
      - return_code: int or None
      - out_params: dict (if you selected them)
      - messages: list[str]

    Identical to the copy in NB_FMD_UTILITY_FUNCTIONS (CODE workspace): a notebook's %run only
    reaches other notebooks in the same workspace, so this configuration-workspace notebook
    carries its own copy rather than depending on one it cannot %run.
    """
    token = notebookutils.credentials.getToken('https://analysis.windows.net/powerbi/api').encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token)}s', len(token), token)

    for attempt in range(1, 4):
        try:
            conn = pyodbc.connect(
                f"DRIVER={driver};SERVER={connstring};PORT=1433;DATABASE={database};",
                attrs_before={1256: token_struct},
                timeout=12
            )
            break
        except pyodbc.Error as e:
            if attempt == 3 or e.args[0] != "HYT00":
                raise
            print(f"Login timeout, retry {attempt}/2: {e}")
            time.sleep(5 * attempt)
    if not exec_statement:
        raise ValueError("proc_name (exec_statement) must not be empty.")

    sql_to_run, sql_params = build_exec_statement(exec_statement, **params)

    result_sets = []
    messages = []
    return_code = None
    out_params = {}

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.timeout = 10

            cursor.execute(sql_to_run, sql_params)

            while True:
                if cursor.description:
                    cols = [d[0] for d in cursor.description]
                    rows = cursor.fetchall()
                    result_sets.append([dict(zip(cols, r)) for r in rows])
                if not cursor.nextset():
                    break

            if result_sets:
                last = result_sets[-1]
                if len(last) == 1 and "__return_code__" in last[0]:
                    return_code = last[0]["__return_code__"]
                    result_sets = result_sets[:-1]

            if result_sets:
                maybe = result_sets[-1]
                if len(maybe) == 1 and any(k.startswith("__out_") for k in maybe[0].keys()):
                    out_params = {k.replace("__out_", ""): v for k, v in maybe[0].items()}
                    result_sets = result_sets[:-1]

            try:
                cursor.commit()
            except Exception as e:
                print(f"Commit failed (expected for read-only operations): {e}")
    finally:
        try:
            conn.close()
        except Exception as e:
            print(f"Connection cleanup failed: {e}")

    return {
        "result_sets": result_sets,
        "return_code": return_code,
        "out_params": out_params,
        "messages": messages
    }

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

INT_COLUMNS = ('IsIncremental', 'IsActive', 'IsHistorized', 'HistoryDays')
JSON_COLUMNS = ('BronzeCleansingRules', 'SilverCleansingRules')


def table(text):
    """
    Turns a pasted table into the list of dicts that `register` takes, so `sources` and `entities`
    can be filled by pasting from Excel instead of typing dict literals. First row = column names
    (the same names the dicts use); the columns are separated by tabs (what Excel puts on the
    clipboard) or by `|` (a markdown table works too). Blank lines, lines starting with `#` and a
    markdown separator row (`---|---`) are skipped, so `#` switches a row off.
    An empty cell leaves the field out, so the procedure's default applies. IsIncremental, IsActive,
    IsHistorized and HistoryDays become numbers (0 or 1, not True/False); the cleansing columns
    hold the rule list as JSON. A column name the procedure does not know is reported by `register`.
    """
    lines = [l for l in text.strip().splitlines()
             if l.strip() and not l.lstrip().startswith('#') and not set(l.strip()) <= set('|-: ')]
    if len(lines) < 2:
        raise ValueError("A table needs a header row and at least one data row.")
    sep = '\t' if '\t' in lines[0] else '|'
    cells = [[c.strip() for c in (l.strip().strip('|') if sep == '|' else l).split(sep)] for l in lines]
    header = cells[0]
    out = []
    for number, row in enumerate(cells[1:], start=2):
        if len(row) > len(header):
            raise ValueError(f"Row {number} has {len(row)} cells but there are {len(header)} columns: {row}")
        item = {}
        for column, value in zip(header, row + [''] * (len(header) - len(row))):
            if value == '':
                continue
            if column in INT_COLUMNS:
                item[column] = int(value)
            elif column in JSON_COLUMNS:
                item[column] = json.loads(value)
            else:
                item[column] = value
        out.append(item)
    return out


def print_entity_list(connection_name, data_source_name, schema=None, source_alias="SRC", as_dict=False):
    """
    Prints one tab-separated row per table/view PL_FMD_DISCOVER_SOURCE found for this connection +
    database (optionally narrowed to one schema): paste it into Excel to edit it, or straight into
    `table(\"\"\"...\"\"\")` for the `entities` list in NB_REGISTRATIE. PrimaryKeys comes from the
    source when it has one; an empty cell makes register(..., dry_run=True) stop on it rather than
    silently registering an empty key. `as_dict=True` prints Python dict literals instead.
    """
    driver, connstring, database = resolve_config_database()
    result = execute_with_outputs("[integration].[sp_GetDiscoveredEntities]", driver, connstring, database,
                                  ConnectionName=connection_name, DataSourceName=data_source_name, SchemaFilter=schema)
    rows = result["result_sets"][0]
    if not rows:
        print(f"Nothing discovered for {connection_name}/{data_source_name}"
              + (f", schema {schema}" if schema else "") + ". Run PL_FMD_DISCOVER_SOURCE first.")
        return

    if not as_dict:
        print("Source\tSourceSchema\tSourceName\tPrimaryKeys")
    for r in rows:
        pk = r["PrimaryKeys"] or ""
        if not as_dict:
            print(f"{source_alias}\t{r['SourceSchema']}\t{r['SourceName']}\t{pk}")
            continue
        # The TODO goes after the closing "}," so a pasted line stays valid Python.
        todo = "" if pk else "  # TODO: no primary key found, fill in or confirm there is none"
        print(
            "    {" + f'"Source": "{source_alias}", "SourceSchema": "{r["SourceSchema"]}", '
            f'"SourceName": "{r["SourceName"]}", "PrimaryKeys": "{pk}"' + "}," + todo
        )
    if not as_dict and any(not r["PrimaryKeys"] for r in rows):
        print("\nNo primary key found for some tables: fill in the PrimaryKeys cell, or leave it empty "
              "and register(..., dry_run=True) will stop on it.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Same list sp_RegisterEntities uses to check that a DataSourceType fits the connection's Type.
CONNECTION_TYPES = ('SQL', 'AZURESQLMI', 'ORACLE', 'ADLS', 'ONELAKE', 'SFTP', 'FTP', 'ADF', 'NOTEBOOK', 'SNOWFLAKE')


def register_connection(name, type, is_active=True):
    """
    Registers a Fabric connection in integration.Connection, so `register` can bind sources to it.
    Looks the connection up by display name through the Fabric REST API, so nobody has to copy its
    GUID from the portal. `type` is the FMD type (CONNECTION_TYPES), not the Fabric one: Azure SQL
    and SQL Managed Instance both show up as 'SQL' in Fabric, so it cannot be derived. A wrong
    type is caught by `register` ("does not fit the type of connection"). Safe to run again.
    The connection itself is never touched, only the row in the configuration database.
    """
    if type not in CONNECTION_TYPES:
        raise ValueError(f"Unknown type '{type}'. Use one of: {', '.join(CONNECTION_TYPES)}.")

    token = notebookutils.credentials.getToken('https://analysis.windows.net/powerbi/api')
    headers = {'Authorization': f'Bearer {token}'}
    connections, url = [], "https://api.fabric.microsoft.com/v1/connections"
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        body = response.json()
        connections += body.get('value', [])
        url = body.get('continuationUri')

    # The API only lists connections this identity may see; a missing one is as likely a permission as a typo.
    matches = [c for c in connections if c['displayName'] == name]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one Fabric connection named '{name}' that you can access, found {len(matches)}.")

    driver, connstring, database = resolve_config_database()
    execute_with_outputs("[integration].[sp_UpsertConnection]", driver, connstring, database,
                         ConnectionGuid=matches[0]['id'], Name=name, Type=type, IsActive=1 if is_active else 0)
    print(f"Registered {name} as {type} (Fabric type: {matches[0]['connectionDetails']['type']}, "
          f"active: {is_active}).")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def register(sources, entities, domain, environments, dry_run=True, requeue_silver=False):
    """
    Registers `sources` and `entities` into one domain's DATA workspace, once per environment in
    `environments`: "D", "T", "A", "P", or "DEV_<NAME>" for a developer's own DATA workspace
    (DEV_<NAME>_<prefix>_<DOMAIN>_DATA; it uses the bindings of D). Use the same lists throughout:
    ["DEV_<NAME>"] during a feature, ["D"] after the merge, ["T"] and ["P"] before each promotion.
    Everything, including the "nothing registered yet" case, happens inside sp_RegisterEntities' own
    transaction: dry_run=True runs the full check and the registration, then rolls back and prints
    what would have changed.

    requeue_silver (only with dry_run=False): a changed Silver cleansing rule only reaches rows that
    change afterwards. With True, the entities whose Silver rule this run changes are put back in the
    queue (execution.sp_RequeueSilverLayerEntities), so the next PL_FMD_LOAD_SILVER rebuilds them from
    Bronze. A change of a type or of the columns also needs the Silver table dropped first.

    sources: a row binds a logical Source to a connection and database for one environment.
      Environment '*' applies to every environment without a row of its own (D, T, A, P; a DEV_
      run uses the D row). Namespace must be the same for a Source in every environment.
      LoadGroup here is the default of the data source, so environments that share a binding share it;
      a table can set its own (entities, below).
      HistoryDays (optional): for an incremental entity without a watermark yet, the first load
      only fetches the last N days; an existing watermark is never changed.
    entities: Source, SourceSchema, SourceName and PrimaryKeys are required.
      FileName defaults to <TargetSchema>_<TargetName>, FileType to 'parquet' ('delta' for
      Snowflake without a storage integration, ADR-014; FileName then only letters, digits, '_').
      IsActive: the list is the truth, switch an entity off with 0 here, not by hand.
      IsHistorized (default 0): 1 keeps the history of changes in Silver (SCD2), ADR-016; empty
      means 0, also for an entity registered with 1 before. CustomNotebookName only for NOTEBOOK.
      LoadGroup (optional): the group of this table; empty = the group of its source. Load one group with
      PL_FMD_LOAD_ALL(LoadGroup=...). SourceColumns (optional): the source columns to load, comma separated,
      empty = all; PrimaryKeys and the watermark column must be in it. SourceFilter (optional): a predicate
      without WHERE, e.g. OrderDate >= '2024-01-01', added to the copy query and to the watermark query.
      SourceColumns and SourceFilter only for ASQL_01, ASQL_02 and SNOWFLAKE_01. Like IsActive, the list is the
      truth: an entity without these fields gets them emptied.
      An entity is found by data source + SourceSchema + SourceName; another SourceName is a new one.
    """
    driver, connstring, database = resolve_config_database()

    def call(environment, dry):
        result = execute_with_outputs("[integration].[sp_RegisterEntities]", driver, connstring, database,
                                      Domain=domain, Environment=environment,
                                      Sources=json.dumps(sources), Entities=json.dumps(entities),
                                      DryRun=1 if dry else 0)
        return result["result_sets"]

    def silver_changed(preview):
        # ponytail: the requeue filter is a comma-separated Schema.Name list, so a name with a comma
        # cannot be requeued this way; none exist in the framework's sources so far.
        return [f"{r['SourceSchema']}.{r['SourceName']}" for r in preview
                if "SilverCleansingRules changed" in (r.get('Changes') or "")]

    for environment in environments:
        print(f"\n=== {domain} / {environment} ({'dry run' if dry_run else 'registering'}) ===")
        # The old rule is gone after the real run, so find the changed entities with a dry run first.
        to_requeue = silver_changed(call(environment, True)[-2]) if requeue_silver and not dry_run else []
        # First result set: the resolved workspace. The procedure's own result is always at the
        # end (dry run: preview, then orphans); the nested upsert procedures add sets in between.
        sets = call(environment, dry_run)
        print(f"Workspace: {sets[0][0]['ResolvedWorkspace']}")

        if dry_run:
            print("Entities:")
            for row in sets[-2]:
                changes = f"   {row['Changes']}" if row.get('Changes') else ""
                print(f"  {row['Action']:<9} {row['SourceSchema']}.{row['SourceName']}{changes}")
                if row.get('Warning'):
                    print(f"            WARNING: {row['Warning']}")
            if silver_changed(sets[-2]):
                print("A changed Silver rule only reaches rows that change afterwards. To rebuild those "
                      "entities from Bronze, register with dry_run=False, requeue_silver=True (drop the "
                      "Silver table first if the rule changes a type or the columns).")
            orphans = sets[-1]
            if orphans:
                print("Active in this workspace but not in this list (left as is):")
                for row in orphans:
                    print(f"  {row['DataSourceName']}: {row['SourceSchema']}.{row['SourceName']}")
        else:
            print("Registered:")
            for row in sets[-1]:
                print(f"  {row['SourceSchema']}.{row['SourceName']}: IsActive={row['IsActive']}, "
                      f"InLoadView={row['InLoadView']}, Watermark={row['Watermark']}")
            if to_requeue:
                queued = execute_with_outputs("[execution].[sp_RequeueSilverLayerEntities]", driver, connstring,
                                              database, WorkspaceId=sets[0][0]['WorkspaceGuid'],
                                              Entities=",".join(to_requeue), DryRun=0)["result_sets"][-1]
                print("Silver queue (next PL_FMD_LOAD_SILVER rebuilds these from Bronze):")
                for row in queued:
                    print(f"  {row['SourceSchema']}.{row['SourceName']}: {row['Result']}")
            elif requeue_silver:
                print("No Silver rule changed: nothing put back in the queue.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Read-only access to the configuration database, for the registration UI. There is no procedure that
# returns what is registered, so this reads the tables sp_RegisterEntities itself writes (LandingzoneEntity,
# BronzeLayerEntity, SilverLayerEntity, DataSource). The DATA workspace is still resolved by the procedure
# (a dry run with empty lists), so the matching rules for domain and environment live in one place only.
# Every write goes through register().

def read_config(sql, *params):
    """Runs a SELECT against the configuration database and returns a list of dicts."""
    if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
        raise ValueError("read_config only runs SELECT queries.")
    driver, connstring, database = resolve_config_database()
    token = notebookutils.credentials.getToken('https://analysis.windows.net/powerbi/api').encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token)}s', len(token), token)
    for attempt in range(1, 4):
        try:
            conn = pyodbc.connect(f"DRIVER={driver};SERVER={connstring};PORT=1433;DATABASE={database};",
                                  attrs_before={1256: token_struct}, timeout=12)
            break
        except pyodbc.Error as e:
            if attempt == 3 or e.args[0] != "HYT00":
                raise
            time.sleep(5 * attempt)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


# The data source types that fit a connection type: the list sp_RegisterEntities checks.
SOURCE_TYPES_BY_CONNECTION = {
    'SQL': ['ASQL_01', 'ASQL_02'], 'AZURESQLMI': ['SQLMI_01'], 'ORACLE': ['ORACLE_01'], 'ADLS': ['ADLS_01'],
    'ONELAKE': ['ONELAKE_TABLES_01', 'ONELAKE_FILES_01'], 'SFTP': ['SFTP_01'], 'FTP': ['FTP_01'], 'ADF': ['ADF'],
    'NOTEBOOK': ['NOTEBOOK'], 'SNOWFLAKE': ['SNOWFLAKE_01'],
}

_SQL_SOURCES = """
SELECT DISTINCT c.[Name] AS ConnectionName, ds.[Name] AS DataSourceName, ds.[Namespace], ds.[Type] AS DataSourceType, ds.[LoadGroup]
FROM [integration].[LandingzoneEntity] le
JOIN [integration].[Lakehouse] lh ON lh.[LakehouseId] = le.[LakehouseId]
JOIN [integration].[DataSource] ds ON ds.[DataSourceId] = le.[DataSourceId]
JOIN [integration].[Connection] c ON c.[ConnectionId] = ds.[ConnectionId]
WHERE lh.[WorkspaceGuid] = ?
ORDER BY ds.[Namespace], ds.[Name]
"""

_SQL_ENTITIES = """
SELECT ds.[Namespace], ds.[Name] AS DataSourceName, ds.[Type] AS DataSourceType, c.[Name] AS ConnectionName,
       le.[SourceSchema], le.[SourceName], le.[FileName], le.[FileType], le.[IsIncremental], le.[IsIncrementalColumn],
       le.[IsActive], le.[CustomNotebookName], ble.[Schema] AS TargetSchema, ble.[Name] AS TargetName, ble.[PrimaryKeys],
       ble.[CleansingRules] AS BronzeRules, sle.[CleansingRules] AS SilverRules, ISNULL(sle.[IsHistorized], 0) AS IsHistorized,
       le.[LoadGroup] AS EntityLoadGroup, le.[SourceColumns], le.[SourceFilter], lv.[LoadValue] AS Watermark
FROM [integration].[LandingzoneEntity] le
JOIN [integration].[Lakehouse] lh ON lh.[LakehouseId] = le.[LakehouseId]
JOIN [integration].[DataSource] ds ON ds.[DataSourceId] = le.[DataSourceId]
JOIN [integration].[Connection] c ON c.[ConnectionId] = ds.[ConnectionId]
LEFT JOIN [integration].[BronzeLayerEntity] ble ON ble.[LandingzoneEntityId] = le.[LandingzoneEntityId]
LEFT JOIN [integration].[SilverLayerEntity] sle ON sle.[BronzeLayerEntityId] = ble.[BronzeLayerEntityId]
LEFT JOIN [execution].[LandingzoneEntityLastLoadValue] lv ON lv.[LandingzoneEntityId] = le.[LandingzoneEntityId]
WHERE lh.[WorkspaceGuid] = ?
ORDER BY ds.[Namespace], le.[SourceSchema], le.[SourceName]
"""

_SQL_DISCOVERED = """
SELECT de.[SourceSchema], de.[SourceName], de.[ObjectType], de.[Columns], de.[PrimaryKeys], de.[DiscoveredAt]
FROM [integration].[DiscoveredEntity] de
JOIN [integration].[Connection] c ON c.[ConnectionId] = de.[ConnectionId]
WHERE c.[Name] = ? AND de.[DataSourceName] = ?
ORDER BY de.[SourceSchema], de.[SourceName]
"""


def list_connections():
    """[{'Name', 'Type'}] of the active connections in integration.Connection."""
    return read_config("SELECT [Name], [Type] FROM [integration].[Connection] WHERE [IsActive] = 1 ORDER BY [Name]")


def load_discovered(connection_name, data_source_name):
    """What PL_FMD_DISCOVER_SOURCE found: {(schema, name): {'ObjectType', 'Columns': [{'Name', 'Type'}], 'PrimaryKeys', 'DiscoveredAt'}}."""
    found = {}
    for row in read_config(_SQL_DISCOVERED, connection_name, data_source_name):
        found[(row['SourceSchema'], row['SourceName'])] = {
            'ObjectType': row['ObjectType'], 'Columns': json.loads(row['Columns'] or '[]'),
            'PrimaryKeys': row['PrimaryKeys'] or '', 'DiscoveredAt': row['DiscoveredAt']}
    return found


def _rules(text):
    return json.loads(text) if text else []


def build_state(domain, environment, workspace, source_rows, entity_rows):
    """
    The registration of one DATA workspace as plain dicts (no database access: testable). Entities carry every
    field that register() would otherwise default, so a re-registration cannot change what was not edited
    (an omitted IsActive means 1, an omitted IsHistorized 0). BronzeMode/SilverMode say what happens with the
    cleansing rules: 'keep' (the field is left out), 'replace' (the list is the truth) or 'clear' ([]).
    The "Source" alias only exists in the lists, not in the database: it is the namespace, upper case.
    """
    sources, alias_of = [], {}
    for row in source_rows:
        alias = str(row['Namespace']).upper()
        while any(s['Source'] == alias for s in sources):
            alias += '_2'
        alias_of[(row['ConnectionName'], row['DataSourceName'], row['DataSourceType'])] = alias
        sources.append({'Source': alias, 'ConnectionName': row['ConnectionName'], 'DataSourceName': row['DataSourceName'],
                        'Namespace': row['Namespace'], 'DataSourceType': row['DataSourceType'],
                        'LoadGroup': row['LoadGroup'] or '', 'HistoryDays': None})
    entities = []
    for row in entity_rows:
        entities.append({
            'Source': alias_of[(row['ConnectionName'], row['DataSourceName'], row['DataSourceType'])],
            'SourceSchema': row['SourceSchema'] or '', 'SourceName': row['SourceName'],
            'TargetSchema': row['TargetSchema'] or '', 'TargetName': row['TargetName'] or '',
            'FileName': row['FileName'], 'FileType': row['FileType'],
            'IsIncremental': int(bool(row['IsIncremental'])), 'IsIncrementalColumn': row['IsIncrementalColumn'] or '',
            'CustomNotebookName': row['CustomNotebookName'] or '', 'PrimaryKeys': row['PrimaryKeys'] or '',
            'IsActive': int(bool(row['IsActive'])), 'IsHistorized': int(bool(row['IsHistorized'])),
            'LoadGroup': row.get('EntityLoadGroup') or '', 'SourceColumns': row.get('SourceColumns') or '',
            'SourceFilter': row.get('SourceFilter') or '', 'Watermark': row.get('Watermark'),
            'BronzeRules': _rules(row['BronzeRules']), 'SilverRules': _rules(row['SilverRules']),
            'BronzeMode': 'keep', 'SilverMode': 'keep', 'Registered': True, 'Selected': False})
    return {'domain': domain, 'environment': environment, 'workspace': workspace, 'sources': sources, 'entities': entities}


def resolve_data_workspace(domain, environment):
    """(name, guid) of the DATA workspace for this domain and environment."""
    driver, connstring, database = resolve_config_database()
    # The supported way to resolve the workspace: the procedure's own dry run, with nothing to register.
    resolved = execute_with_outputs("[integration].[sp_RegisterEntities]", driver, connstring, database,
                                    Domain=domain, Environment=environment, Sources="[]", Entities="[]", DryRun=1)
    workspace = resolved["result_sets"][0][0]
    return workspace['ResolvedWorkspace'], str(workspace['WorkspaceGuid'])


def load_registration(domain, environment):
    """The current registration of the DATA workspace for this domain and environment, as a state dict."""
    name, guid = resolve_data_workspace(domain, environment)
    return build_state(domain, environment, name, read_config(_SQL_SOURCES, guid), read_config(_SQL_ENTITIES, guid))


ENTITY_FIELDS = ('TargetSchema', 'TargetName', 'FileName', 'FileType', 'IsIncremental', 'IsIncrementalColumn',
                 'CustomNotebookName', 'PrimaryKeys', 'IsActive', 'IsHistorized', 'LoadGroup', 'SourceColumns', 'SourceFilter')

# The types whose copy query takes SourceColumns and SourceFilter. Keep in step with sp_RegisterEntities.
SOURCE_FILTER_TYPES = ('ASQL_01', 'ASQL_02', 'SNOWFLAKE_01')


def entity_key(entity):
    return (entity['Source'], entity['SourceSchema'], entity['SourceName'])


def new_entity(source, schema, name, discovered=None):
    """A table that is not registered yet, with the defaults sp_RegisterEntities would apply."""
    default_type = 'delta' if source['DataSourceType'] == 'SNOWFLAKE_01' else 'parquet'  # ADR-014
    return {'Source': source['Source'], 'SourceSchema': schema, 'SourceName': name, 'TargetSchema': schema,
            'TargetName': name, 'FileName': f'{schema}_{name}', 'FileType': default_type, 'IsIncremental': 0,
            'IsIncrementalColumn': '', 'CustomNotebookName': '',
            'PrimaryKeys': ((discovered or {}).get('PrimaryKeys') or '').replace(' ', ''),
            'IsActive': 1, 'IsHistorized': 0, 'LoadGroup': '', 'SourceColumns': '', 'SourceFilter': '', 'Watermark': None,
            'BronzeRules': [], 'SilverRules': [], 'BronzeMode': 'keep',
            'SilverMode': 'keep', 'Registered': False, 'Selected': False}


# Cleansing functions as NB_FMD_DQ_CLEANSING reads them. This mirrors the docstrings there, because the
# functions carry no machine-readable parameter list; a function that is not built in (registered in
# NB_FMD_CUSTOM_DQ_CLEANSING) is edited as JSON. Keep in step with NB_FMD_DQ_CLEANSING.
CLEANSING_FUNCTIONS = {
    'normalize_text': [
        {'name': 'case', 'kind': 'choice', 'options': ['lower', 'upper', 'title'], 'default': None},
        {'name': 'collapse_spaces', 'kind': 'bool', 'default': True},
        {'name': 'empty_as_null', 'kind': 'bool', 'default': True}],
    'fill_nulls': [
        {'name': 'default_string', 'kind': 'str', 'default': None},
        {'name': 'default_numeric', 'kind': 'number', 'default': None},
        {'name': 'default_date', 'kind': 'date', 'default': None},
        {'name': 'defaults', 'kind': 'json', 'default': None}],
    'parse_datetime': [
        {'name': 'target_type', 'kind': 'choice', 'options': ['date', 'timestamp'], 'default': 'date'},
        {'name': 'formats', 'kind': 'list', 'default': ['yyyy-MM-dd']},
        {'name': 'into', 'kind': 'str', 'default': None},
        {'name': 'keep_original', 'kind': 'bool', 'default': True}],
}


def validate_rule(rule, columns=None):
    """[(level, message)] for one rule {'function', 'columns', 'parameters'}; level is 'error' or 'warning'."""
    problems = []
    function = rule.get('function') or ''
    if not function:
        return [('error', 'function is missing')]
    cols = [c for c in (rule.get('columns') or '').split(';') if c]
    if not cols:
        problems.append(('error', f'{function}: no columns'))
    elif columns is not None:
        problems += [('warning', f'{function}: column {c} not found by discovery') for c in cols if c not in columns]
    params = rule.get('parameters') or {}
    if not isinstance(params, dict):
        return problems + [('error', f'{function}: parameters must be an object')]
    if '__invalid_json__' in params:
        return problems + [('error', f'{function}: parameters are not valid JSON')]
    spec = CLEANSING_FUNCTIONS.get(function)
    if spec is None:
        return problems + [('warning', f'{function} is not built in; fine if NB_FMD_CUSTOM_DQ_CLEANSING registers it')]
    known = {p['name']: p for p in spec}
    for name, value in params.items():
        p = known.get(name)
        if p is None:
            problems.append(('warning', f'{function}: parameter {name} is ignored by the function'))
        elif p['kind'] == 'choice' and value not in p['options']:
            problems.append(('error', f'{function}.{name} must be one of {p["options"]}'))
        elif p['kind'] == 'bool' and not isinstance(value, bool):
            problems.append(('error', f'{function}.{name} must be true or false'))
        elif p['kind'] == 'number' and (isinstance(value, bool) or not isinstance(value, (int, float))):
            problems.append(('error', f'{function}.{name} must be a number'))
        elif p['kind'] == 'date' and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value)):
            problems.append(('error', f'{function}.{name} must be a date as yyyy-MM-dd'))
        elif p['kind'] == 'list' and not (isinstance(value, list) and value and all(isinstance(v, str) for v in value)):
            problems.append(('error', f'{function}.{name} must be a non-empty list of text'))
        elif p['kind'] == 'json' and not isinstance(value, dict):
            problems.append(('error', f'{function}.{name} must be an object'))
    if function == 'parse_datetime' and params.get('into') and len(cols) != 1:
        problems.append(('warning', 'parse_datetime: "into" only applies when exactly one column is given'))
    return problems


def _modified_source_aliases(state, original):
    before = {s['Source']: s for s in original['sources']}
    return {s['Source'] for s in state['sources'] if before.get(s['Source']) != s}


def changed_fields(entity, original=None):
    """What differs from the loaded state: a list of field names (empty when untouched or not registered)."""
    if original is None:
        return []
    changed = [f for f in ENTITY_FIELDS if entity[f] != original[f]]
    for layer in ('Bronze', 'Silver'):
        mode, rules, before = entity[f'{layer}Mode'], entity[f'{layer}Rules'], original[f'{layer}Rules']
        if (mode == 'clear' and before) or (mode == 'replace' and rules != before):
            changed.append(f'{layer}CleansingRules')
    return changed


def entities_to_register(state, original):
    """The entities register() gets: tables selected as new, registered ones that changed, and the registered
    tables of a source that changed (the data source row is written with each of its entities)."""
    originals = {entity_key(e): e for e in original['entities']}
    touched = _modified_source_aliases(state, original)
    chosen = []
    for e in state['entities']:
        if not e['Registered']:
            if e['Selected']:
                chosen.append(e)
        elif changed_fields(e, originals.get(entity_key(e))) or e['Source'] in touched:
            chosen.append(e)
    return chosen


def build_payload(state, original):
    """(sources, entities) in the form register() takes. A rule field is only present for 'replace' and 'clear'."""
    chosen = entities_to_register(state, original)
    used = {e['Source'] for e in chosen}
    sources = []
    for s in state['sources']:
        if s['Source'] in used:
            item = {'Environment': '*', **{k: s[k] for k in ('Source', 'ConnectionName', 'DataSourceName', 'Namespace', 'DataSourceType', 'LoadGroup')}}
            if s.get('HistoryDays'):
                item['HistoryDays'] = int(s['HistoryDays'])
            sources.append(item)
    entities = []
    for e in chosen:
        item = {k: e[k] for k in ('Source', 'SourceSchema', 'SourceName', *ENTITY_FIELDS)}
        for field in ('IsIncrementalColumn', 'CustomNotebookName', 'LoadGroup', 'SourceColumns', 'SourceFilter'):
            if not item[field]:
                del item[field]
        for layer in ('Bronze', 'Silver'):
            if e[f'{layer}Mode'] == 'replace':
                item[f'{layer}CleansingRules'] = e[f'{layer}Rules']
            elif e[f'{layer}Mode'] == 'clear':
                item[f'{layer}CleansingRules'] = []
        entities.append(item)
    return sources, entities


def validate_state(state, original, discovered=None):
    """
    [{'table', 'field', 'level', 'message'}] for what would be registered. register(dry_run=True) stays the
    authority; this catches the obvious before the round trip and names the table and field.
    `discovered` is {alias: load_discovered(...)}.
    """
    discovered = discovered or {}
    problems = []

    def add(table_name, field, level, message):
        problems.append({'table': table_name, 'field': field, 'level': level, 'message': message})

    sources, _ = build_payload(state, original)
    by_alias = {s['Source']: s for s in state['sources']}
    connection_types = {c['Name']: c['Type'] for c in state.get('connections', [])}
    for s in sources:
        for field in ('Source', 'ConnectionName', 'DataSourceName', 'Namespace', 'DataSourceType'):
            if not s.get(field):
                add(s['Source'] or '(source)', field, 'error', 'required')
        ctype = connection_types.get(s['ConnectionName'])
        if ctype and s['DataSourceType'] not in SOURCE_TYPES_BY_CONNECTION.get(ctype, []):
            add(s['Source'], 'DataSourceType', 'error', f"{s['DataSourceType']} does not fit connection type {ctype}")
        if s.get('HistoryDays') is not None and s['HistoryDays'] < 1:
            add(s['Source'], 'HistoryDays', 'error', 'must be 1 or more')
    seen = set()
    for e in entities_to_register(state, original):
        name = f"{e['SourceSchema']}.{e['SourceName']}"
        if entity_key(e) in seen:
            add(name, 'SourceName', 'error', 'listed twice')
        seen.add(entity_key(e))
        for field in ('SourceName', 'TargetSchema', 'TargetName', 'FileName', 'FileType', 'PrimaryKeys'):
            if not e[field]:
                add(name, field, 'error', 'required')
        for field in ('IsIncremental', 'IsActive', 'IsHistorized'):
            if e[field] not in (0, 1):
                add(name, field, 'error', 'must be 0 or 1')
        source = by_alias.get(e['Source'])
        if source is None:
            add(name, 'Source', 'error', f"source {e['Source']} is not defined")
            continue
        if source['DataSourceType'] == 'NOTEBOOK' and not e['CustomNotebookName']:
            add(name, 'CustomNotebookName', 'error', 'required for type NOTEBOOK')
        found = discovered.get(e['Source'], {}).get((e['SourceSchema'], e['SourceName']))
        snowflake = source['DataSourceType'] == 'SNOWFLAKE_01'
        columns = None
        if found:
            columns = {c['Name']: c['Type'] for c in found['Columns']}
            norm = (lambda x: x) if snowflake else (lambda x: x.lower())
            lookup = {norm(c): c for c in columns}
            for pk in [p.strip() for p in e['PrimaryKeys'].split(',') if p.strip()]:
                if norm(pk) not in lookup:
                    add(name, 'PrimaryKeys', 'error', f'column {pk} not found by discovery')
            if e['IsIncremental'] == 1 and e['IsIncrementalColumn'] and norm(e['IsIncrementalColumn']) not in lookup:
                add(name, 'IsIncrementalColumn', 'error', f"column {e['IsIncrementalColumn']} not found by discovery")
            elif snowflake and e['IsIncremental'] == 1 and e['IsIncrementalColumn'] in columns:
                ctype = columns[e['IsIncrementalColumn']].upper()
                if not (ctype.startswith('DATE') or ctype.startswith('TIMESTAMP')):
                    add(name, 'IsIncrementalColumn', 'error', f'type {ctype}; Snowflake needs DATE or TIMESTAMP')
        elif source['DataSourceType'] != 'NOTEBOOK':
            add(name, 'SourceName', 'warning', 'not found in the discovered tables (run PL_FMD_DISCOVER_SOURCE)')
        if e['IsIncremental'] == 1 and not e['IsIncrementalColumn']:
            add(name, 'IsIncrementalColumn', 'error', 'required when IsIncremental = 1')
        if len(e['LoadGroup']) > 50:
            add(name, 'LoadGroup', 'error', 'longer than 50 characters')
        wanted = [c.strip() for c in e['SourceColumns'].split(',') if c.strip()]
        if (wanted or e['SourceFilter']) and source['DataSourceType'] not in SOURCE_FILTER_TYPES:
            add(name, 'SourceColumns' if wanted else 'SourceFilter', 'error', f"only supported for {', '.join(SOURCE_FILTER_TYPES)}")
        before = next((o for o in original['entities'] if entity_key(o) == entity_key(e)), None)
        if before is not None and before['SourceColumns'] != e['SourceColumns']:
            add(name, 'SourceColumns', 'warning', 'taking columns away from a table that is already in Bronze makes the Bronze merge fail '
                '(DELTA_MERGE_UNRESOLVED_EXPRESSION, tested 2026-10-20): drop the Bronze and Silver table first. Adding columns is not tested')
        if ';' in e['SourceFilter']:
            add(name, 'SourceFilter', 'error', 'must be one predicate: no semicolon')
        elif e['SourceFilter']:
            add(name, 'SourceFilter', 'warning', 'runs against the source at load time; the dry run does not test the predicate')
        if wanted:
            norm_c = (lambda x: x) if snowflake else (lambda x: x.lower())
            have = {norm_c(c) for c in wanted}
            for pk in [p.strip() for p in e['PrimaryKeys'].split(',') if p.strip()]:
                if norm_c(pk) not in have:
                    add(name, 'PrimaryKeys', 'error', f'column {pk} is not in SourceColumns')
            if e['IsIncremental'] == 1 and e['IsIncrementalColumn'] and norm_c(e['IsIncrementalColumn']) not in have:
                add(name, 'IsIncrementalColumn', 'error', f"column {e['IsIncrementalColumn']} is not in SourceColumns")
            if columns:
                known = {norm_c(c) for c in columns}
                for c in [c for c in wanted if norm_c(c) not in known]:
                    add(name, 'SourceColumns', 'error', f'column {c} not found by discovery')
        originals = {entity_key(o): o for o in original['entities']}
        for layer in ('Bronze', 'Silver'):
            mode, rules = e[f'{layer}Mode'], e[f'{layer}Rules']
            if mode == 'replace' and not rules:
                add(name, f'{layer}CleansingRules', 'error', 'replace with an empty list: choose "Remove all" instead')
            if mode == 'replace':
                for number, rule in enumerate(rules, start=1):
                    for level, message in validate_rule(rule, list(columns) if columns else None):
                        add(name, f'{layer}CleansingRules[{number}]', level, message)
            if mode == 'clear' and originals.get(entity_key(e), {}).get(f'{layer}Rules'):
                count = len(originals[entity_key(e)][f'{layer}Rules'])
                add(name, f'{layer}CleansingRules', 'warning', f'removes all {count} existing rule(s)')
    return problems


BULK_FIELDS = ('IsActive', 'IsHistorized', 'LoadGroup')


def bulk_set(state, keys, field, value, apply=False):
    """The keys a bulk change touches, and the ones whose value actually changes. Nothing is written unless apply."""
    if field not in BULK_FIELDS:
        raise ValueError(f"Bulk change is only offered for {', '.join(BULK_FIELDS)}.")
    wanted = set(keys)
    new = str(value).strip() if field == 'LoadGroup' else int(value)  # LoadGroup is text, the others 0 or 1
    affected = [e for e in state['entities'] if entity_key(e) in wanted and e[field] != new]
    if apply:
        for e in affected:
            e[field] = new
    return [entity_key(e) for e in affected]


def table_status(entity, original):
    """'new', 'selected' (a new table marked for registration), 'changed' or 'registered'."""
    if not entity['Registered']:
        return 'selected' if entity['Selected'] else 'new'
    originals = {entity_key(o): o for o in original['entities']}
    return 'changed' if changed_fields(entity, originals.get(entity_key(entity))) else 'registered'


def export_tables(sources, entities):
    """The payload as table(\"\"\"...\"\"\") text, as a record of what was registered. Rules as JSON."""
    def block(name, rows, order):
        columns = [c for c in order if any(c in r for r in rows)]
        lines = [' | '.join(columns)]
        for r in rows:
            cells = [json.dumps(r[c]) if isinstance(r.get(c), (list, dict)) else ('' if r.get(c) is None else str(r[c])) for c in columns]
            lines.append(' | '.join(cells))
        return f'{name} = table("""\n' + '\n'.join(lines) + '\n""")'
    src_order = ['Environment', 'Source', 'ConnectionName', 'DataSourceName', 'Namespace', 'DataSourceType', 'LoadGroup', 'HistoryDays']
    ent_order = ['Source', 'SourceSchema', 'SourceName', 'TargetSchema', 'TargetName', 'FileName', 'FileType', 'PrimaryKeys',
                 'IsIncremental', 'IsIncrementalColumn', 'CustomNotebookName', 'IsActive', 'IsHistorized',
                 'LoadGroup', 'SourceColumns', 'SourceFilter', 'BronzeCleansingRules', 'SilverCleansingRules']
    return block('sources', sources, src_order) + '\n\n' + block('entities', entities, ent_order)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

DISCOVERY_PIPELINE = 'PL_FMD_DISCOVER_SOURCE'
_JOB_FINISHED = ('Completed', 'Failed', 'Cancelled', 'Deduped')


def code_workspace_of(data_workspace_name):
    """
    (name, guid) of the CODE workspace that belongs to a DATA workspace: the same name with the last DATA replaced
    by CODE (X INTEGRATION DATA (D) -> X INTEGRATION CODE (D); DEV_X_INTEGRATION_DATA -> DEV_X_INTEGRATION_CODE).
    The guid is read from integration.Workspace by that name; the pipeline's own WorkspaceGuid in
    integration.Pipeline is the DATA workspace, so it cannot be used.
    """
    name = re.sub(r'DATA(?!.*DATA)', 'CODE', data_workspace_name)
    rows = read_config("SELECT [WorkspaceGuid] FROM [integration].[Workspace] WHERE [Name] = ?", name) if name != data_workspace_name else []
    if len(rows) != 1:
        raise RuntimeError(f"Geen CODE-workspace gevonden bij '{data_workspace_name}' (gezocht: '{name}' in integration.Workspace). "
                           f"Start {DISCOVERY_PIPELINE} dan handmatig in de CODE-workspace.")
    return name, str(rows[0]['WorkspaceGuid'])


def start_discovery(connection_name, data_source_name, schema_filter='', domain='INTEGRATION', environment='D',
                    progress=print, timeout_minutes=20, poll_seconds=10):
    """
    Starts PL_FMD_DISCOVER_SOURCE in the CODE workspace of this domain and environment and waits until it is done.
    The pipeline lists the tables, columns and primary keys of the source into integration.DiscoveredEntity;
    load_discovered / the editor read that afterwards. schema_filter is the pipeline's optional SchemaFilter
    (empty: all schemas). Returns {'status': 'Completed'|'Failed'|'Cancelled'|'Deduped', 'failureReason': ...}.
    Needs a role on the CODE workspace that may run items. A DEV_<NAME> environment runs it in the CODE workspace
    of D: it shares its source binding with D, integration.DiscoveredEntity has no environment column, and the
    developer CODE workspace had no PL_FMD_DISCOVER_SOURCE (DEV_MITCHELL_TRIAL_INTEGRATION_CODE, FMD_TRIAL, 2026-10-16).
    """
    data_name, _ = resolve_data_workspace(domain, 'D' if environment.startswith('DEV_') else environment)
    code_name, code_guid = code_workspace_of(data_name)
    token = notebookutils.credentials.getToken('https://analysis.windows.net/powerbi/api')
    headers = {'Authorization': f'Bearer {token}'}
    base = f'https://api.fabric.microsoft.com/v1/workspaces/{code_guid}'

    pipelines, url = [], f'{base}/items?type=DataPipeline'
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        body = response.json()
        pipelines += body.get('value', [])
        url = body.get('continuationUri')
    matches = [p for p in pipelines if p['displayName'] == DISCOVERY_PIPELINE]
    if len(matches) != 1:
        raise RuntimeError(f"Verwacht één pipeline {DISCOVERY_PIPELINE} in {code_name}, gevonden: {len(matches)}.")

    parameters = {'ConnectionName': connection_name, 'DataSourceName': data_source_name, 'SchemaFilter': schema_filter or ''}
    run = requests.post(f"{base}/items/{matches[0]['id']}/jobs/instances?jobType=Pipeline", headers=headers,
                        json={'executionData': {'parameters': parameters}})
    if run.status_code in (401, 403):
        # Listing items needs only a read role; starting a job does not (Microsoft: Admin, Member or Contributor start runs).
        raise RuntimeError(f"Geen recht om {DISCOVERY_PIPELINE} te starten in {code_name} (HTTP {run.status_code}). Daarvoor is minimaal de rol "
                           "Contributor nodig, bij sommige itemtypen Member. Vraag die aan of start de pipeline handmatig in de CODE-workspace.")
    run.raise_for_status()  # 202 Accepted; the job is polled through the Location header
    location = run.headers['Location']
    progress(f'Ontdekking gestart in {code_name} ({connection_name} / {data_source_name}) ...')

    deadline = time.time() + timeout_minutes * 60
    while True:
        response = requests.get(location, headers=headers)
        response.raise_for_status()
        job = response.json()
        if job.get('status') in _JOB_FINISHED:
            return {'status': job['status'], 'failureReason': job.get('failureReason')}
        if time.time() > deadline:
            raise RuntimeError(f"Ontdekking niet klaar na {timeout_minutes} minuten (status {job.get('status')}); "
                               f"de pipeline loopt mogelijk nog in {code_name}.")
        time.sleep(poll_seconds)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Editor
# Interactive editor on top of `register()`, in widgets: sources, tables found by discovery, primary keys and
# cleansing rules. The logic (reading what is registered, building the payload, validating) is above; this part
# is only the screen. Open it through NB_REGISTRATIE.

# CELL ********************

import contextlib, copy, hashlib, html, io, json, traceback
import ipywidgets as w
from IPython.display import display

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def vbox(children=(), **layout):
    """A VBox that does not stretch its children: a stretched button is as wide as the page, with its text at the edge."""
    return w.VBox(list(children), layout=w.Layout(align_items='flex-start', **layout))


class Pane:
    """
    Messages and tables under the editor. A plain HTML widget on purpose: in a Fabric notebook the Output widget
    does not capture, so print() lands in the cell and clear_output() wipes the whole cell output, editor included.
    """

    def __init__(self, height='56px', tall='260px', hide_empty=False):
        # A fixed height with a scroll bar: a pane that grows with its content pushes the editor around.
        # It only switches between two heights: small for a one-line message, tall for a table or a long report.
        # hide_empty: no empty box until there is a message; only for a pane that has nothing below it to push.
        self.small, self.tall, self.hide_empty = height, tall, hide_empty
        self.parts = []
        self.widget = w.HTML(layout=w.Layout(height=height, overflow='auto', border='1px solid #ddd', padding='4px', width='100%',
                                             display='none' if hide_empty else ''))

    def clear(self):
        self.parts = []
        self._render()

    def print(self, text=''):
        self.parts.append('<pre style="margin:0;white-space:pre-wrap">' + html.escape(str(text)) + '</pre>')
        self._render()

    def raw(self, markup):
        self.parts.append(markup)
        self._render()

    def capture(self, fn, *args, **kwargs):
        """Runs fn and shows what it prints (register() reports with print)."""
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                return fn(*args, **kwargs)
        finally:
            if buffer.getvalue():
                self.print(buffer.getvalue().rstrip())

    def _render(self):
        self.widget.value = ''.join(self.parts)
        long = sum(p.count('\n') for p in self.parts) > 2 or any('<table' in p for p in self.parts)
        self.widget.layout.height = self.tall if long else self.small
        if self.hide_empty:
            self.widget.layout.display = '' if self.parts else 'none'


def _where(e):
    """The frames of our own code in an exception, one per line: 'index out of bounds' alone does not name the field."""
    frames = [f for f in traceback.extract_tb(e.__traceback__) if 'site-packages' not in f.filename]
    return '\n'.join(f'  {f.name}, regel {f.lineno}: {f.line or ""}' for f in frames)


def set_options(widget, options):
    """Sets the options and keeps the current value if it is still there, otherwise the first one."""
    old = widget.value
    widget.options = options
    values = [o[1] if isinstance(o, tuple) else o for o in widget.options]
    widget.value = old if old in values else (values[0] if values else None)


def _rule_text(rule):
    columns = rule.get('columns') or ''
    columns = ';'.join(columns) if isinstance(columns, list) else columns
    params = ', '.join(f'{k}={v}' for k, v in (rule.get('parameters') or {}).items())
    return f"{rule.get('function') or '?'}({columns}{'; ' + params if params else ''})"


def overview_html(state, original):
    """
    What register() is about to write, one row per table, from what was filled in on the tabs before. A plain
    HTML table, not a DataFrame: a DataFrame would go to the cell output instead of this widget, and this one
    needs several lines per cell (rules) and marks what differs from the registered state.
    """
    chosen = entities_to_register(state, original)
    if not chosen:
        return '<i>Niets te registreren. Selecteer op tab 2 nieuwe tabellen, of wijzig een geregistreerde tabel.</i>'
    originals = {entity_key(e): e for e in original['entities']}
    esc = html.escape

    def load_mode(e):
        if not e['IsIncremental']:
            return 'volledig'
        return 'incrementeel op ' + (esc(e['IsIncrementalColumn']) if e['IsIncrementalColumn'] else '<b style="color:#b00020">kolom ontbreekt</b>')

    def rules(e, layer, as_registered=False):
        mode, found = e[f'{layer}Mode'], e[f'{layer}Rules']
        if mode == 'clear' and not as_registered:
            return 'alle regels verwijderd'
        if not found:
            return 'geen'
        text = '<br>'.join(esc(_rule_text(r)) for r in found)
        return text if mode == 'replace' or as_registered else f'ongewijzigd:<br>{text}'

    groups = {s['Source']: s['LoadGroup'] for s in state['sources']}

    def load_group(e, old=False):
        return esc(e['LoadGroup']) if e['LoadGroup'] else f"<i>van bron: {esc(groups.get(e['Source']) or '(leeg)')}</i>"

    def source_columns(e, old=False):
        cols = [c.strip() for c in e['SourceColumns'].split(',') if c.strip()]
        return f"{len(cols)}: " + esc(', '.join(cols)) if cols else 'alle'

    def source_filter(e, old=False):
        return esc(e['SourceFilter']) or '-'

    # (header, text of an entity, the fields that mark it as changed)
    columns = [
        ('Doel', lambda e, old=False: esc(f"{e['TargetSchema']}.{e['TargetName']}"), ('TargetSchema', 'TargetName')),
        ('Bestand', lambda e, old=False: esc(f"{e['FileName']} ({e['FileType']})") + (f"<br>notebook {esc(e['CustomNotebookName'])}" if e['CustomNotebookName'] else ''),
         ('FileName', 'FileType', 'CustomNotebookName')),
        ('Laden', lambda e, old=False: load_mode(e), ('IsIncremental', 'IsIncrementalColumn')),
        ('LoadGroup', load_group, ('LoadGroup',)),
        ('Kolommen', source_columns, ('SourceColumns',)),
        ('Filter', source_filter, ('SourceFilter',)),
        ('Primary key', lambda e, old=False: esc(e['PrimaryKeys'].replace(',', ', ')) or '<b style="color:#b00020">ontbreekt</b>', ('PrimaryKeys',)),
        ('Actief', lambda e, old=False: 'ja' if e['IsActive'] else 'nee', ('IsActive',)),
        ('Historie Silver', lambda e, old=False: 'ja' if e['IsHistorized'] else 'nee', ('IsHistorized',)),
        ('Bronze-regels', lambda e, old=False: rules(e, 'Bronze', old), ('BronzeCleansingRules',)),
        ('Silver-regels', lambda e, old=False: rules(e, 'Silver', old), ('SilverCleansingRules',)),
    ]
    rows = []
    for e in chosen:
        before = originals.get(entity_key(e))
        changed = set(changed_fields(e, before))
        status = 'nieuw' if not e['Registered'] else ('gewijzigd' if changed else 'bron gewijzigd')
        cells = [f"<td><b>{esc(e['SourceSchema'])}.{esc(e['SourceName'])}</b><br><small>{esc(e['Source'])} · {status}</small></td>"]
        for _, text, fields in columns:
            if before is not None and changed & set(fields):
                cells.append(f'<td style="background:#fff3e0"><b>{text(e)}</b><br><small>was: {text(before, True)}</small></td>')
            else:
                cells.append(f'<td>{text(e)}</td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    head = ''.join(f'<th align=left>{h}</th>' for h in ['Tabel'] + [c[0] for c in columns])
    return (f'<table style="border-collapse:collapse;font-size:12px" cellpadding=4 border=1 bordercolor="#ddd"><tr>{head}</tr>{"".join(rows)}</table>'
            f'<small>Oranje: wijkt af van wat nu geregistreerd is.</small>')


class ColumnPicker:
    """
    A multi-select of columns with a search box above it. The choice survives the search: a chosen column stays in
    the list even when it does not match. `value` is the chosen columns in table order. on_change() runs after a
    change by the user, not after load().
    """

    def __init__(self, label, rows=6, width='100%', on_change=None):
        self.on_change, self.columns, self.chosen, self._loading = on_change, [], [], False
        self.title = w.HTML(f'<b>{html.escape(label)}</b>')
        self.search = w.Text(placeholder='zoek kolom', continuous_update=True, layout=w.Layout(width=width))
        self.select = w.SelectMultiple(rows=rows, layout=w.Layout(width=width))
        self.all_btn = w.Button(description='Alle zichtbare', layout=w.Layout(width='auto'), tooltip='Kiest alle kolommen die bij de zoekterm passen')
        self.none_btn = w.Button(description='Wissen', layout=w.Layout(width='auto'))
        self.widget = vbox([self.title, self.search, self.select, w.HBox([self.all_btn, self.none_btn])], width=width)
        self.search.observe(lambda _: self._render(), names='value')
        self.select.observe(self._picked, names='value')
        self.all_btn.on_click(lambda _: self._set(set(self.chosen) | set(self._visible())))
        self.none_btn.on_click(lambda _: self._set(set()))

    @property
    def value(self):
        return tuple(self.chosen)

    def load(self, columns, chosen, label=None):
        """Sets the columns to choose from and what is chosen, without calling on_change. A chosen name that is not a column stays."""
        self.columns = list(columns)
        self.columns += [c for c in chosen if c not in self.columns]
        self.chosen = [c for c in self.columns if c in chosen]
        if label is not None:
            self.title.value = f'<b>{html.escape(label)}</b>'
        self.search.value = ''
        self._render()

    def _visible(self):
        text = self.search.value.strip().lower()
        return [c for c in self.columns if text in c.lower()]

    def _render(self):
        visible = self._visible()
        options = [c for c in self.columns if c in self.chosen or c in visible]
        self._loading = True
        self.select.options = options
        self.select.value = tuple(c for c in options if c in self.chosen)
        self._loading = False

    def _picked(self, change):
        if self._loading:
            return
        self.chosen = [c for c in self.columns if c in change['new']]
        if self.on_change:
            self.on_change()

    def _set(self, wanted):
        self.chosen = [c for c in self.columns if c in wanted]
        self._render()
        if self.on_change:
            self.on_change()


class RuleEditor:
    """The cleansing rules of one layer (Bronze or Silver) of the table being edited."""

    MODES = [('Ongewijzigd laten', 'keep'), ('Vervangen door onderstaande regels', 'replace'), ('Alle regels verwijderen', 'clear')]
    CUSTOM = '(eigen functie)'

    def __init__(self, layer, on_change):
        self.layer, self.on_change, self.columns, self.rules, self._loading = layer, on_change, [], [], False
        # A dropdown, not radio buttons: with "Ongewijzigd laten" (the usual case) the editor is one line, not four.
        self.mode = w.Dropdown(options=self.MODES, value='keep', description=f'{layer}-cleansing', style={'description_width': '110px'},
                               layout=w.Layout(width='100%', max_width='520px'))
        self.add = w.Button(layout=w.Layout(width='auto'), description='Regel toevoegen', icon='plus')
        self.rows = vbox()
        self.box = vbox([self.rows, self.add])
        self.widget = vbox([self.mode, self.box])
        self.mode.observe(self._mode_changed, names='value')
        self.add.on_click(lambda _: self._add())
        self._show()

    def load(self, entity, columns):
        self._loading = True
        self.columns = list(columns)
        self.rules = [self._normal(r) for r in copy.deepcopy(entity[f'{self.layer}Rules'])]
        self.mode.value = entity[f'{self.layer}Mode']
        self._rebuild()
        self._show()
        self._loading = False

    @staticmethod
    def _normal(rule):
        rule = rule if isinstance(rule, dict) else {}
        columns = rule.get('columns')
        columns = ';'.join(columns) if isinstance(columns, list) else (columns or '')
        params = rule.get('parameters')
        return {'function': rule.get('function') or '', 'columns': columns, 'parameters': params if isinstance(params, dict) else {}}

    def _show(self):
        self.box.layout.display = '' if self.mode.value == 'replace' else 'none'

    def _mode_changed(self, _):
        self._show()
        self._changed()

    def _changed(self):
        if not self._loading:
            self.on_change(self.layer, self.mode.value, copy.deepcopy(self.rules))

    def _add(self):
        function = next(iter(CLEANSING_FUNCTIONS))
        self.rules.append({'function': function, 'columns': '', 'parameters': {}})
        self._rebuild()
        self._changed()

    def _move(self, i, step):
        j = i + step
        if 0 <= j < len(self.rules):
            self.rules[i], self.rules[j] = self.rules[j], self.rules[i]
            self._rebuild()
            self._changed()

    def _delete(self, i):
        del self.rules[i]
        self._rebuild()
        self._changed()

    def _rebuild(self):
        self.rows.children = [self._row(i, r) for i, r in enumerate(self.rules)]

    def _row(self, i, rule):
        known = rule['function'] in CLEANSING_FUNCTIONS
        function = w.Dropdown(options=list(CLEANSING_FUNCTIONS) + [self.CUSTOM], value=rule['function'] if known else self.CUSTOM,
                              description='Functie', layout=w.Layout(width='320px'))
        chosen = [c for c in rule['columns'].split(';') if c]
        columns = ColumnPicker('Kolommen', rows=min(6, max(3, len(self.columns))), width='320px')
        columns.load(self.columns, chosen)
        custom_name = w.Text(continuous_update=False, value=rule['function'] if not known else '', description='Naam', layout=w.Layout(width='320px'))
        custom_params = w.Textarea(continuous_update=False, value=json.dumps(rule['parameters']) if not known else '{}', description='Parameters (JSON)',
                                   layout=w.Layout(width='100%', max_width='520px', height='60px'))
        param_widgets = {}
        for p in (CLEANSING_FUNCTIONS.get(rule['function']) or []):
            param_widgets[p['name']] = self._param_widget(p, rule['parameters'].get(p['name']))
        up = w.Button(description='↑', tooltip='Regel omhoog', layout=w.Layout(width='40px'))
        down = w.Button(description='↓', tooltip='Regel omlaag', layout=w.Layout(width='40px'))
        delete = w.Button(description='✕', tooltip='Regel verwijderen', layout=w.Layout(width='40px'))

        def collect(_=None):
            if self._loading:
                return
            if function.value == self.CUSTOM:
                try:
                    params = json.loads(custom_params.value or '{}')
                except ValueError:
                    params = {'__invalid_json__': custom_params.value}
                new = {'function': custom_name.value.strip(), 'columns': ';'.join(columns.value), 'parameters': params}
            else:
                names = {p['name'] for p in CLEANSING_FUNCTIONS[function.value]}
                params = {k: v for k, v in rule['parameters'].items() if k not in names}  # not ours to drop
                for p in CLEANSING_FUNCTIONS[function.value]:
                    value = self._param_value(p, param_widgets[p['name']]) if p['name'] in param_widgets else None
                    if value is not None:
                        params[p['name']] = value
                new = {'function': function.value, 'columns': ';'.join(columns.value), 'parameters': params}
            self.rules[i] = new
            self._changed()

        def function_changed(_):
            if self._loading:
                return
            self.rules[i] = {'function': function.value if function.value != self.CUSTOM else '', 'columns': ';'.join(columns.value), 'parameters': {}}
            self._rebuild()
            self._changed()

        function.observe(function_changed, names='value')
        columns.on_change = collect
        for widget in [custom_name, custom_params, *param_widgets.values()]:
            widget.observe(collect, names='value')
        up.on_click(lambda _: self._move(i, -1)); down.on_click(lambda _: self._move(i, 1)); delete.on_click(lambda _: self._delete(i))
        head = w.HBox([w.HTML(f'<b>{i + 1}.</b>', layout=w.Layout(width='24px')), function, up, down, delete])
        body = [head, columns.widget]
        if function.value == self.CUSTOM:
            body += [custom_name, custom_params]
        else:
            body += list(param_widgets.values())
        return vbox(body, border='1px solid #ccc', padding='4px', margin='2px 0')

    @staticmethod
    def _param_widget(p, value):
        label = p['name']
        if p['kind'] == 'choice':
            options = [('(standaard)', None)] + [(o, o) for o in p['options']]
            if value is not None and value not in p['options']:
                options.append((f'{value} (ongeldig)', value))
            return w.Dropdown(options=options, value=value, description=label)
        if p['kind'] == 'bool':
            return w.Dropdown(options=[('(standaard)', None), ('ja', True), ('nee', False)], value=value if isinstance(value, bool) else None, description=label)
        if p['kind'] == 'list':
            return w.Text(continuous_update=False, value=', '.join(value) if isinstance(value, list) else ('' if value is None else str(value)), description=label, placeholder='yyyy-MM-dd, dd/MM/yyyy')
        if p['kind'] == 'json':
            return w.Text(continuous_update=False, value=json.dumps(value) if isinstance(value, dict) else ('' if value is None else str(value)), description=label, placeholder='{"Kolom": 0}')
        return w.Text(continuous_update=False, value='' if value is None else str(value), description=label)

    @staticmethod
    def _param_value(p, widget):
        value = widget.value
        if p['kind'] in ('choice', 'bool'):
            return value
        value = (value or '').strip()
        if value == '':
            return None
        if p['kind'] == 'number':
            try:
                return float(value) if '.' in value else int(value)
            except ValueError:
                return value  # left as text: validate_rule reports it
        if p['kind'] == 'list':
            return [v.strip() for v in value.split(',') if v.strip()]
        if p['kind'] == 'json':
            try:
                return json.loads(value)
            except ValueError:
                return value
        return value

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

STATUS_NL = {'new': 'nieuw', 'selected': 'geselecteerd', 'changed': 'gewijzigd', 'registered': 'geregistreerd'}


class RegistrationUI:
    """
    Interactive editor for the registration. Everything is edited in memory; nothing is written until
    "Registreren". The registration itself is register(), unchanged; the logic (reading what is registered,
    building the payload, validating) lives in NB_FMD_REGISTRATION_FUNCTIONS.
    """

    def __init__(self, domain='INTEGRATION', environment='D'):
        self.state = self.original = None
        self.discovered = {}
        self.dry_run_of = self.done_of = None
        self.current = None
        self._loading = False
        self.out = Pane()
        self.res = Pane(tall='200px')  # the result of Controleren / Proefdraaien, on tab 3 next to its buttons
        self._build_header(domain, environment)
        self._build_sources_tab()
        self._build_tables_tab()
        self._build_register_tab()
        # Own tabs instead of w.Tab: in a Fabric notebook the Tab widget does not hide the other pages, so all
        # three stacked under each other. A page is hidden with its own display style, which does work.
        self.pages = [self.sources_tab, self.tables_tab, self.register_tab]
        self.tab_pick = w.ToggleButtons(options=[('1. Bronnen', 0), ('2. Tabellen', 1), ('3. Controleren en registreren', 2)], value=0,
                                     style={'button_width': 'auto'})
        self.tab_pick.observe(lambda c: self._show_page(c['new']), names='value')
        self._show_page(0)
        # The messages sit above the tabs, so a result is in view without scrolling down to it.
        self.top_btn = w.Button(layout=w.Layout(width='auto'), description='Terug naar begin', icon='arrow-up', tooltip='Naar tab 1 en de meldingen wissen; wijzigingen blijven staan')
        self.top_btn.on_click(lambda _: self.back_to_start())
        self.root = w.VBox([self.header, self.status, self.out.widget, self.tab_pick, *self.pages, w.HBox([self.top_btn])],
                           layout=w.Layout(width='100%'))
        # No load here: widget values set while this cell is still running are overwritten by the state the Fabric
        # frontend sends back when it opens the widgets (index=None), which left tab 1 empty and broke the next load.
        display(self.root)

    def back_to_start(self):
        """Tab 1 and empty messages. The edits in memory stay."""
        self.tab_pick.value = 0
        self.out.clear()
        self.res.clear()

    def _show_page(self, index):
        for i, page in enumerate(self.pages):
            page.layout.display = '' if i == index else 'none'
        self.out.widget.layout.display = 'none' if index == 2 else ''  # tab 3 has its own result pane

    def _pane(self):
        """Where a message goes: the pane of tab 3 while that tab is open, otherwise the one above the tabs."""
        return self.res if self.tab_pick.value == 2 else self.out

    def __repr__(self):
        return ''  # registration_ui(...) as the last line of a cell would otherwise print the object

    # ---- plumbing ----------------------------------------------------------------------------------
    def _guard(self, button, fn):
        """Runs fn from a button: one at a time, errors shown instead of a stack trace in the cell."""
        def handler(_):
            if button.disabled:
                return
            button.disabled = True
            try:
                fn()
            except Exception as e:
                self._pane().print(f'FOUT: {type(e).__name__}: {e}\n' + _where(e))
            finally:
                button.disabled = False
                self._update_register_state()
        button.on_click(handler)

    def _payload(self):
        return build_payload(self.state, self.original)

    def _fingerprint(self):
        sources, entities = self._payload()
        return hashlib.sha1(json.dumps([self.state['environment'], sources, entities], sort_keys=True, default=str).encode()).hexdigest()

    def _say(self, text, clear=True):
        pane = self._pane()
        if clear:
            pane.clear()
        pane.print(text)

    # ---- header ------------------------------------------------------------------------------------
    def _build_header(self, domain, environment):
        self.domain = w.Text(continuous_update=False, value=domain, description='Domein', layout=w.Layout(width='260px'))
        self.env = w.Combobox(continuous_update=False, options=['D', 'T', 'A', 'P'], value=environment, ensure_option=False, description='Omgeving',
                              placeholder='D, T, A, P of DEV_<NAAM>', layout=w.Layout(width='300px'))
        self.load_btn = w.Button(layout=w.Layout(width='auto'), description='Laden uit de configdb', button_style='primary', icon='refresh')
        self.header = w.HBox([self.domain, self.env, self.load_btn])
        self.status = w.HTML('Nog niets geladen: klik op <b>Laden uit de configdb</b> om te beginnen.', layout=w.Layout(height='28px'))
        self._guard(self.load_btn, self.load)

    def load(self):
        if self.state is not None and entities_to_register(self.state, self.original):
            self._say('LET OP: er waren niet-opgeslagen wijzigingen; die zijn nu weggegooid door opnieuw te laden.')
        else:
            self._pane().clear()
        self._say(f'Laden:{self.domain.value} / {self.env.value} ...', clear=False)
        self.state = load_registration(self.domain.value.strip(), self.env.value.strip())
        self.state['connections'] = list_connections()
        self.original = copy.deepcopy(self.state)
        self.discovered, self.dry_run_of, self.done_of, self.current = {}, None, None, None
        self.confirm.value = False
        self._fill_sources_tab()
        self._fill_tables_tab()
        self._focus(None)
        self._say(f"Geladen: werkruimte {self.state['workspace']}, {len(self.state['sources'])} bron(nen), "
                  f"{len(self.state['entities'])} geregistreerde tabel(len).")
        self.refresh()

    def refresh(self, list_too=True):
        """After every change: the status line, the list and the register button."""
        if self.state is None:
            return
        chosen = entities_to_register(self.state, self.original)
        n_new = sum(1 for e in chosen if not e['Registered'])
        dirty = f'<b style="color:#b45f06">● {len(chosen)} te registreren</b> ({n_new} nieuw, {len(chosen) - n_new} gewijzigd)' if chosen else 'Geen wijzigingen.'
        self.status.value = (f"Werkruimte: <b>{html.escape(str(self.state['workspace']))}</b> · omgeving {html.escape(self.state['environment'])} · {dirty}")
        if list_too:
            self._refresh_list()
        self.overview.value = overview_html(self.state, self.original)
        self._update_register_state()

    # ---- tab 1: sources ----------------------------------------------------------------------------
    def _build_sources_tab(self):
        wide = lambda: w.Layout(width='520px')  # a new Layout each time: widgets must not share one
        self.s_pick = w.Dropdown(description='Bron', layout=wide())
        self.s_alias = w.Text(continuous_update=False, description='Alias', placeholder='bijv. AW', layout=wide())
        self.s_conn = w.Dropdown(description='Connectie', layout=wide())
        self.s_ds = w.Text(continuous_update=False, description='Database', placeholder='DataSourceName', layout=wide())
        self.s_ns = w.Text(continuous_update=False, description='Namespace', placeholder='bijv. aw', layout=wide())
        self.s_type = w.Dropdown(description='Brontype', layout=wide())
        self.s_lg = w.Text(continuous_update=False, description='LoadGroup', placeholder='leeg = standaard', layout=wide())
        self.s_hd = w.Text(continuous_update=False, description='HistoryDays', placeholder='leeg; alleen voor nieuwe incrementele tabellen', layout=wide())
        self.s_save = w.Button(layout=w.Layout(width='auto'), description='Bron bewaren (in geheugen)', icon='check')
        self.s_note = w.HTML()
        self.sources_tab = vbox([self.s_pick, self.s_alias, self.s_conn, self.s_ds, self.s_ns, self.s_type, self.s_lg, self.s_hd,
                                   self.s_save, self.s_note])
        self.s_pick.observe(lambda c: self._show_source(c['new']), names='value')
        self.s_conn.observe(lambda _: self._source_types(), names='value')
        self._guard(self.s_save, self._save_source)

    NEW_SOURCE = '(nieuwe bron)'

    def _fill_sources_tab(self):
        self._loading = True
        set_options(self.s_conn, [c['Name'] for c in self.state['connections']])
        set_options(self.s_pick, [s['Source'] for s in self.state['sources']] + [self.NEW_SOURCE])
        self._loading = False
        self._show_source(self.s_pick.value)
        self.s_note.value = ('<i>Een bron hoort bij de database van deze omgeving. Voor DEV_&lt;NAAM&gt; geldt: de gegevens van de bron '
                             'worden gedeeld met D.</i>' if self.state['environment'].startswith('DEV_') else
                             '<i>Wijzigen van een bron schrijft de bron opnieuw met al haar tabellen mee.</i>')

    def _source_types(self):
        ctype = next((c['Type'] for c in self.state['connections'] if c['Name'] == self.s_conn.value), None) if self.state else None
        set_options(self.s_type, SOURCE_TYPES_BY_CONNECTION.get(ctype, []))

    def _show_source(self, alias):
        if self.state is None:
            return
        source = next((s for s in self.state['sources'] if s['Source'] == alias), None)
        self._loading = True
        self.s_alias.disabled = source is not None
        self.s_alias.value = source['Source'] if source else ''
        self.s_conn.value = source['ConnectionName'] if source and source['ConnectionName'] in self.s_conn.options else (self.s_conn.options[0] if self.s_conn.options else None)
        self._source_types()
        self.s_ds.value = source['DataSourceName'] if source else ''
        self.s_ns.value = source['Namespace'] if source else ''
        self.s_type.value = source['DataSourceType'] if source and source['DataSourceType'] in self.s_type.options else None
        self.s_lg.value = source['LoadGroup'] if source else ''
        self.s_hd.value = str(source['HistoryDays']) if source and source.get('HistoryDays') else ''
        self._loading = False

    def _save_source(self):
        alias = self.s_alias.value.strip()
        problems = [f'{label} is verplicht' for label, v in (('Alias', alias), ('Connectie', self.s_conn.value), ('Database', self.s_ds.value.strip()),
                                                              ('Namespace', self.s_ns.value.strip()), ('Brontype', self.s_type.value)) if not v]
        try:
            hd = int(self.s_hd.value) if self.s_hd.value.strip() else None
        except ValueError:
            hd, problems = None, problems + ['HistoryDays moet een geheel getal zijn']
        existing = next((s for s in self.state['sources'] if s['Source'] == alias), None)
        if existing is None and any(s['Source'] == alias for s in self.state['sources']):
            problems.append('Alias bestaat al')
        if problems:
            return self._say('Bron niet bewaard: ' + '; '.join(problems))
        item = {'Source': alias, 'ConnectionName': self.s_conn.value, 'DataSourceName': self.s_ds.value.strip(), 'Namespace': self.s_ns.value.strip(),
                'DataSourceType': self.s_type.value, 'LoadGroup': self.s_lg.value.strip(), 'HistoryDays': hd}
        if existing:
            existing.update(item)
        else:
            self.state['sources'].append(item)
        self._fill_sources_tab()
        self.s_pick.value = alias
        self._fill_tables_tab()
        self.refresh()
        self._say(f'Bron {alias} bewaard in het geheugen (nog niet geregistreerd).')

    # ---- tab 2: tables -----------------------------------------------------------------------------
    def _build_tables_tab(self):
        label = lambda: {'description_width': '130px'}  # a new dict each time; wide enough for "Watermarkkolom" and "Custom notebook"
        self.t_src = w.Dropdown(description='Bron', layout=w.Layout(width='320px'))
        self.t_discover = w.Button(layout=w.Layout(width='auto'), description='Ontdekte tabellen laden', icon='search',
                                   tooltip='Leest wat de laatste ontdekking in de configdb heeft gezet')
        self.t_schema = w.Text(description='Schemafilter', placeholder="leeg = alle schema's", layout=w.Layout(width='320px'), continuous_update=False)
        self.t_run = w.Button(layout=w.Layout(width='auto'), description='Ontdekking starten (pipeline)', icon='play',
                              tooltip='Start PL_FMD_DISCOVER_SOURCE in de CODE-workspace, wacht tot hij klaar is en laadt daarna de ontdekte tabellen')
        self.t_filter = w.Text(description='Zoeken', placeholder='schema, tabel of LoadGroup', layout=w.Layout(width='320px'), continuous_update=False)
        self.t_incols = w.Checkbox(description='ook in kolomnamen', indent=False, layout=w.Layout(width='auto'),
                                   tooltip="Zoekt ook in de kolommen van de ontdekte tabellen (eerst 'Ontdekte tabellen laden')")
        self.t_status = w.Dropdown(description='Status', options=['alle', 'nieuw', 'geselecteerd', 'geregistreerd', 'gewijzigd'], layout=w.Layout(width='220px'))
        self.t_list = w.SelectMultiple(rows=12, layout=w.Layout(width='100%'))
        self.t_all = w.Button(layout=w.Layout(width='auto'), description='Alles in lijst selecteren', icon='list',
                              tooltip='Selecteert alle tabellen die na het filter in de lijst staan')
        self.t_mark = w.Button(layout=w.Layout(width='auto'), description='Selecteren voor registratie', icon='check-square')
        self.t_unmark = w.Button(layout=w.Layout(width='auto'), description='Selectie weghalen', icon='square')
        self.b_field = w.Dropdown(description='Bulk', options=list(BULK_FIELDS), layout=w.Layout(width='220px'))
        self.b_value = w.Dropdown(options=[('aan (1)', 1), ('uit (0)', 0)], layout=w.Layout(width='100px'))
        self.b_text = w.Text(placeholder='leeg = van de bron', layout=w.Layout(width='160px', display='none'), continuous_update=False)
        self.b_preview = w.Button(layout=w.Layout(width='auto'), description='Voorbeeld')
        self.b_apply = w.Button(layout=w.Layout(width='auto'), description='Toepassen op selectie', button_style='warning')
        self.b_out = Pane(height='40px', tall='140px', hide_empty=True)
        wide = lambda: w.Layout(width='100%')  # a new Layout each time: widgets must not share one; the right column sets the width
        self.d_head = w.HTML(self.NO_TABLE)
        self.d_tschema = w.Text(description='Doelschema', layout=wide(), style=label(), continuous_update=False)
        self.d_tname = w.Text(description='Doeltabel', layout=wide(), style=label(), continuous_update=False)
        self.d_fname = w.Text(description='FileName', layout=wide(), style=label(), continuous_update=False)
        self.d_ftype = w.Combobox(continuous_update=False, description='FileType', options=['parquet', 'delta'], ensure_option=False, layout=wide(), style=label())
        self.d_lg = w.Text(description='LoadGroup', layout=wide(), style=label(), continuous_update=False)
        self.d_active = w.Checkbox(description='Actief', indent=False)
        self.d_hist = w.Checkbox(description='Historie in Silver', indent=False)
        self.d_inc = w.Checkbox(description='Incrementeel', indent=False)
        # A Combobox: type to search the columns; a name that discovery does not know is still accepted (and reported by Controleren).
        self.d_inccol = w.Combobox(continuous_update=False, description='Watermarkkolom', ensure_option=False, placeholder='kolom', layout=wide(), style=label())
        self.d_wm = w.HTML()
        self.d_cols = ColumnPicker('Kolommen om te laden (niets gekozen = alle)', rows=8, on_change=lambda: self._detail_changed(None))
        self.d_filter = w.Textarea(description='Bronfilter', placeholder="bijv. OrderDate >= '2024-01-01'", layout=w.Layout(width='100%', height='56px'),
                                   style=label(), continuous_update=False)
        self.d_pk = ColumnPicker('Primary key', rows=6, on_change=lambda: self._detail_changed(None))
        self.d_nb = w.Text(description='Custom notebook', layout=wide(), style=label(), continuous_update=False)
        self.d_reset = w.Button(layout=w.Layout(width='auto'), description='Deze tabel terugzetten', icon='undo')
        self.d_widgets = [self.d_tschema, self.d_tname, self.d_fname, self.d_ftype, self.d_lg, self.d_inc, self.d_inccol, self.d_active, self.d_hist,
                          self.d_filter, self.d_nb]
        self.bronze, self.silver = RuleEditor('Bronze', self._rules_changed), RuleEditor('Silver', self._rules_changed)
        # Hidden until a table is clicked in the list: there is nothing to edit before that.
        self.detail = vbox([self.d_tschema, self.d_tname, self.d_fname, self.d_ftype, self.d_lg, self.d_active, self.d_hist, self.d_inc, self.d_inccol,
                              self.d_wm, self.d_cols.widget, self.d_filter, self.d_pk.widget, self.d_nb, self.d_reset, self.bronze.widget, self.silver.widget],
                             width='100%')
        self.detail.layout.display = 'none'
        wrap = lambda *children: w.HBox(list(children), layout=w.Layout(flex_flow='row wrap'))
        top = vbox([wrap(self.t_src, self.t_discover), wrap(self.t_schema, self.t_run)])
        filters = wrap(self.t_filter, self.t_incols, self.t_status)
        marks = wrap(self.t_all, self.t_mark, self.t_unmark)
        bulk = wrap(self.b_field, self.b_value, self.b_text, self.b_preview, self.b_apply)
        # Two columns: pick on the left, edit on the right, so list and properties are in view together. The
        # columns wrap under each other when the cell is narrow.
        left = vbox([top, filters, self.t_list, marks, bulk, self.b_out.widget], flex='1 1 440px', min_width='0', margin='0 16px 0 0')
        right = vbox([w.HTML('<b>Eigenschappen van één tabel</b>'), self.d_head, self.detail], flex='1 1 440px', min_width='0')
        self.tables_tab = w.HBox([left, right], layout=w.Layout(flex_flow='row wrap', width='100%', align_items='flex-start'))
        self.t_src.observe(lambda _: self._refresh_list(), names='value')
        self.t_filter.observe(lambda _: self._refresh_list(), names='value')
        self.t_incols.observe(lambda _: self._refresh_list(), names='value')
        self.t_status.observe(lambda _: self._refresh_list(), names='value')
        self.t_list.observe(self._list_selected, names='value')
        self.b_field.observe(lambda _: self._bulk_field(), names='value')
        for widget in self.d_widgets:
            widget.observe(self._detail_changed, names='value')
        self._guard(self.t_discover, self.discover)
        self._guard(self.t_run, self.run_discovery)
        self._guard(self.t_all, self._select_all)
        self._guard(self.t_mark, lambda: self._mark(True))
        self._guard(self.t_unmark, lambda: self._mark(False))
        self._guard(self.b_preview, lambda: self._bulk(False))
        self._guard(self.b_apply, lambda: self._bulk(True))
        self._guard(self.d_reset, self._reset_entity)

    NO_TABLE = '<i>Klik een tabel in de lijst om hem te bewerken.</i>'

    def _fill_tables_tab(self):
        self._loading = True
        set_options(self.t_src, [s['Source'] for s in self.state['sources']])
        self._loading = False
        self._refresh_list()

    def _entity(self, key):
        return next((e for e in self.state['entities'] if entity_key(e) == key), None)

    def _original(self, key):
        return next((e for e in self.original['entities'] if entity_key(e) == key), None)

    def _source_of(self, e):
        return next((s for s in self.state['sources'] if s['Source'] == e['Source']), None)

    def _group_of(self, e):
        """The LoadGroup the table loads in: its own, otherwise the one of its source."""
        source = self._source_of(e)
        return e['LoadGroup'] or (source['LoadGroup'] if source else '')

    def _label(self, e):
        status = table_status(e, self.original)
        group = self._group_of(e)
        return (f"{'☑' if status == 'selected' else '·'} [{STATUS_NL[status]:<13}] {e['SourceSchema']}.{e['SourceName']}   "
                f"(B:{len(e['BronzeRules'])} S:{len(e['SilverRules'])})" + (f"   groep: {group}" if group else ''))

    def _listed(self):
        if self.state is None:
            return []
        text, status = self.t_filter.value.strip().lower(), self.t_status.value
        listed = []
        for e in sorted(self.state['entities'], key=lambda x: (x['SourceSchema'], x['SourceName'])):
            if e['Source'] != self.t_src.value:
                continue
            if text:
                haystack = f"{e['SourceSchema']}.{e['SourceName']} {self._group_of(e)}".lower()
                found = self.discovered.get(e['Source'], {}).get((e['SourceSchema'], e['SourceName']))
                if self.t_incols.value and found:
                    haystack += ' ' + ' '.join(c['Name'] for c in found['Columns']).lower()
                if text not in haystack:
                    continue
            if status != 'alle' and STATUS_NL[table_status(e, self.original)] != status:
                continue
            listed.append(e)
        return listed

    def _refresh_list(self):
        if self.state is None or self._loading:
            return
        self._loading = True
        keep = set(self.t_list.value)
        listed = self._listed()
        entries = [(self._label(e), entity_key(e)) for e in listed]
        if [tuple(o) for o in self.t_list.options] != entries:
            self.t_list.options = entries
            self.t_list.value = tuple(k for k in (entity_key(e) for e in listed) if k in keep)
        self._loading = False

    def _select_all(self):
        self.t_list.value = tuple(o[1] for o in self.t_list.options)
        self.b_out.clear()
        self.b_out.print(f'{len(self.t_list.value)} tabel(len) in de lijst geselecteerd.')

    def run_discovery(self):
        """Starts the discovery pipeline for the chosen source, waits for it and then loads what it found."""
        source = next((s for s in self.state['sources'] if s['Source'] == self.t_src.value), None) if self.state else None
        if source is None:
            return self._say('Laad eerst de configdb en kies een bron (tab 1).')
        result = start_discovery(source['ConnectionName'], source['DataSourceName'], self.t_schema.value.strip(),
                                 domain=self.state['domain'], environment=self.state['environment'],
                                 progress=lambda text: self._say(text, clear=False))
        if result['status'] != 'Completed':
            return self._say(f"Ontdekking niet gelukt: {result['status']}. {result['failureReason'] or ''}".strip(), clear=False)
        self.discover()

    def discover(self):
        source = next((s for s in self.state['sources'] if s['Source'] == self.t_src.value), None)
        if source is None:
            return self._say('Kies eerst een bron (tab 1).')
        found = load_discovered(source['ConnectionName'], source['DataSourceName'])
        self.discovered[source['Source']] = found
        if not found:
            return self._say(f"Geen ontdekte tabellen voor {source['ConnectionName']} / {source['DataSourceName']}. "
                             'Draai eerst PL_FMD_DISCOVER_SOURCE in de CODE-workspace.')
        known = {entity_key(e) for e in self.state['entities']}
        added = 0
        for (schema, name), info in found.items():
            if (source['Source'], schema, name) not in known:
                self.state['entities'].append(new_entity(source, schema, name, info))
                added += 1
        newest = max(info['DiscoveredAt'] for info in found.values())
        self._say(f'{len(found)} tabel(len) ontdekt (laatste ontdekking {newest}); {added} nieuw in de lijst.')
        self.refresh()
        if self.current:
            self._show_entity(self.current)  # the columns of the table on screen are known now

    def _mark(self, selected):
        touched = 0
        for key in self.t_list.value:
            e = self._entity(key)
            if e and not e['Registered'] and e['Selected'] != selected:
                e['Selected'] = selected
                touched += 1
        self.b_out.clear()
        self.b_out.print(f"{touched} tabel(len) {'geselecteerd voor registratie' if selected else 'niet meer geselecteerd'} (alleen nieuwe tabellen).")
        self.refresh()

    def _bulk_field(self):
        """LoadGroup is text; the other bulk fields are 0 or 1."""
        text = self.b_field.value == 'LoadGroup'
        self.b_text.layout.display = '' if text else 'none'
        self.b_value.layout.display = 'none' if text else ''

    def _bulk(self, apply):
        keys = list(self.t_list.value)
        self.b_out.clear()
        if not keys:
            return self.b_out.print('Selecteer eerst tabellen in de lijst.')
        field = self.b_field.value
        value = self.b_text.value if field == 'LoadGroup' else self.b_value.value
        affected = bulk_set(self.state, keys, field, value, apply=apply)
        same = len(keys) - len(affected)
        shown = (str(value).strip() or '(van de bron)') if field == 'LoadGroup' else value
        lines = [f"{'Toegepast op' if apply else 'Zou veranderen voor'} {len(affected)} tabel(len); {same} hadden deze waarde al."]
        lines += [f'  {schema}.{name}: {field} -> {shown}' for _, schema, name in affected[:40]]
        if len(affected) > 40:
            lines.append(f'  ... en {len(affected) - 40} meer')
        self.b_out.print('\n'.join(lines))
        if apply:
            self.refresh()
            if self.current:
                self._show_entity(self.current)

    def _list_selected(self, change):
        """The properties column follows the table you click last; with several selected, the bulk action covers them all."""
        if self._loading:
            return
        new, old = tuple(change['new']), tuple(change['old'])
        added = [k for k in new if k not in old]
        key = added[0] if len(added) == 1 else (self.current if self.current in new else (new[0] if new else None))
        self._focus(key)
        self._refresh_list()  # the labels of the tables edited so far

    def _focus(self, key):
        """Shows one table in the properties column; None hides the column."""
        e = self._entity(key) if key else None
        self.current = key if e else None
        self.detail.layout.display = '' if e else 'none'
        if e is None:
            self.d_head.value = self.NO_TABLE
            return
        picked = len(self.t_list.value)
        more = f' · {picked} tabellen geselecteerd: hier bewerk je alleen deze' if picked > 1 else ''
        self.d_head.value = f"<b>{html.escape(e['SourceSchema'])}.{html.escape(e['SourceName'])}</b> · {html.escape(e['Source'])}{more}"
        self._show_entity(key)

    def _columns(self, e):
        found = self.discovered.get(e['Source'], {}).get((e['SourceSchema'], e['SourceName']))
        return [c['Name'] for c in found['Columns']] if found else []

    def _show_entity(self, key):
        e = self._entity(key) if key else None
        self.current = key if e else None
        if e is None:
            return
        before, self._loading = self._loading, True
        columns = self._columns(e)
        pks = [p.strip() for p in e['PrimaryKeys'].split(',') if p.strip()]
        chosen = [c.strip() for c in e['SourceColumns'].split(',') if c.strip()]
        self.d_tschema.value, self.d_tname.value, self.d_fname.value, self.d_ftype.value = e['TargetSchema'], e['TargetName'], e['FileName'], e['FileType']
        self.d_inc.value, self.d_active.value, self.d_hist.value = bool(e['IsIncremental']), bool(e['IsActive']), bool(e['IsHistorized'])
        source = self._source_of(e)
        self.d_lg.value = e['LoadGroup']
        self.d_lg.placeholder = f"leeg = van de bron: {source['LoadGroup']}" if source and source['LoadGroup'] else 'leeg = van de bron'
        self.d_inccol.options = columns
        self.d_inccol.value = e['IsIncrementalColumn']
        if not e['Registered']:
            self.d_wm.value = ''
        elif e.get('Watermark'):
            self.d_wm.value = f"<small>Huidige watermark: <code>{html.escape(str(e['Watermark']))}</code></small>"
        else:
            self.d_wm.value = '<small>Nog geen watermark.</small>'
        note = '' if columns else ' (geen kolommen ontdekt: draai de ontdekking)'
        self.d_pk.load(columns, pks, 'Primary key' + note)
        self.d_cols.load(columns, chosen, 'Kolommen om te laden (niets gekozen = alle)' + note)
        self.d_filter.value = e['SourceFilter']
        self.d_nb.value = e['CustomNotebookName']
        self._toggle_fields(source)
        self.bronze.load(e, columns)
        self.silver.load(e, columns)
        self._loading = before

    def _toggle_fields(self, source):
        """Only the fields that apply: the watermark with Incrementeel, columns and filter for the types that take them, the notebook for NOTEBOOK."""
        for widget in (self.d_inccol, self.d_wm):
            widget.layout.display = '' if self.d_inc.value else 'none'
        for widget in (self.d_cols.widget, self.d_filter):
            widget.layout.display = '' if source and source['DataSourceType'] in SOURCE_FILTER_TYPES else 'none'
        self.d_nb.layout.display = '' if source and source['DataSourceType'] == 'NOTEBOOK' else 'none'

    def _detail_changed(self, _):
        e = self._entity(self.current) if self.current and not self._loading else None
        if e is None:
            return
        e.update(TargetSchema=self.d_tschema.value.strip(), TargetName=self.d_tname.value.strip(), FileName=self.d_fname.value.strip(),
                 FileType=self.d_ftype.value.strip(), IsIncremental=int(self.d_inc.value), IsIncrementalColumn=(self.d_inccol.value or '').strip(),
                 IsActive=int(self.d_active.value), IsHistorized=int(self.d_hist.value), PrimaryKeys=','.join(self.d_pk.value),
                 CustomNotebookName=self.d_nb.value.strip(), LoadGroup=self.d_lg.value.strip(), SourceColumns=','.join(self.d_cols.value),
                 SourceFilter=self.d_filter.value.strip())
        self._toggle_fields(self._source_of(e))
        self.refresh(list_too=False)

    def _rules_changed(self, layer, mode, rules):
        e = self._entity(self.current) if self.current else None
        if e is None:
            return
        e[f'{layer}Mode'], e[f'{layer}Rules'] = mode, rules
        self.refresh(list_too=False)

    def _reset_entity(self):
        e = self._entity(self.current) if self.current else None
        if e is None:
            return
        orig = self._original(self.current)
        e.clear()
        if orig:
            e.update(copy.deepcopy(orig))
        else:
            source = next(s for s in self.state['sources'] if s['Source'] == self.current[0])
            e.update(new_entity(source, self.current[1], self.current[2], self.discovered.get(source['Source'], {}).get((self.current[1], self.current[2]))))
        self._show_entity(self.current)
        self.refresh()

    # ---- tab 3: validate, dry run, register --------------------------------------------------------
    def _build_register_tab(self):
        self.v_btn = w.Button(layout=w.Layout(width='auto'), description='Controleren', icon='search')
        self.dry_btn = w.Button(layout=w.Layout(width='auto'), description='Proefdraaien (dry_run=True)', button_style='info', icon='flask')
        self.confirm = w.Checkbox(value=False, indent=False, description='Ik heb de wijzigingen en de proefdraai gecontroleerd en wil registreren', layout=w.Layout(width='auto'))
        self.reg_btn = w.Button(layout=w.Layout(width='auto'), description='Registreren (dry_run=False)', button_style='danger', icon='upload', disabled=True)
        # What will be registered, per table, as filled in on tab 2. Always current, so it can be read before and
        # after the dry run. A fixed height with a scroll bar, like the panes: a long list must not push the buttons away.
        self.overview = w.HTML(layout=w.Layout(max_height='220px', overflow='auto', width='100%', border='1px solid #ddd', padding='4px'))
        self.register_tab = vbox([w.HTML('<b>Dit wordt geregistreerd</b> (uit wat je op tab 1 en 2 hebt ingevuld). Controleer dit, proefdraai, bevestig en registreer.'),
                                  self.overview, w.HBox([self.v_btn, self.dry_btn]), self.res.widget, self.confirm, self.reg_btn], width='100%')
        self.confirm.observe(lambda _: self._update_register_state(), names='value')
        self._guard(self.v_btn, self.check)
        self._guard(self.dry_btn, self.dry_run)
        self._guard(self.reg_btn, self.register_now)

    def _update_register_state(self):
        if self.state is None:
            return
        fingerprint = self._fingerprint()
        sources, entities = self._payload()
        self.reg_btn.disabled = not (self.confirm.value and entities and self.dry_run_of == fingerprint and self.done_of != fingerprint)
        self.reg_btn.description = f"Registreren in {self.state['environment']} ({len(entities)} tabel(len))"
        if self.dry_run_of and self.dry_run_of != fingerprint:
            self.confirm.value = False
            self.dry_run_of = None  # the old result no longer describes what is on screen
            self.res.clear()
            self.res.print('Er is iets gewijzigd sinds de proefdraai. Draai opnieuw proef voordat je registreert.')

    def _problems_html(self, problems):
        rows = ''.join(f"<tr style='color:{'#b00020' if p['level'] == 'error' else '#b45f06'}'><td>{p['level']}</td><td>{html.escape(p['table'])}</td>"
                       f"<td>{html.escape(p['field'])}</td><td>{html.escape(p['message'])}</td></tr>" for p in problems)
        return f"<table><tr><th align=left>niveau</th><th align=left>tabel</th><th align=left>veld</th><th align=left>melding</th></tr>{rows}</table>"

    def _summary(self):
        chosen = entities_to_register(self.state, self.original)
        print(f"Te registreren in {self.state['environment']} ({self.state['workspace']}): {len(chosen)} tabel(len); de details staan in het overzicht hierboven.")

    def check(self):
        self.res.clear()
        problems = validate_state(self.state, self.original, self.discovered)
        self.res.capture(self._summary)
        if problems:
            self.res.raw(self._problems_html(problems))
        else:
            self.res.print('Geen problemen gevonden.')
        return not any(p['level'] == 'error' for p in problems)

    def dry_run(self):
        if not self.check():
            return self._say('Er zijn fouten. Los die eerst op.', clear=False)
        sources, entities = self._payload()
        if not entities:
            return self._say('Niets te registreren.', clear=False)
        # The existing function, unchanged: a dry run runs every check and the registration, then rolls back.
        self.res.capture(register, sources, entities, domain=self.state['domain'], environments=[self.state['environment']], dry_run=True)
        self.dry_run_of = self._fingerprint()
        self._say('Proefdraai gedaan en teruggedraaid. Controleer de uitkomst en het overzicht hierboven, vink de bevestiging aan en registreer.', clear=False)

    def register_now(self):
        fingerprint = self._fingerprint()
        if not (self.confirm.value and self.dry_run_of == fingerprint and self.done_of != fingerprint):
            return self._say('Niet uitgevoerd: eerst proefdraaien op deze wijzigingen en bevestigen.')
        sources, entities = self._payload()
        self.reg_btn.disabled = True
        self.res.clear()
        self.res.capture(register, sources, entities, domain=self.state['domain'], environments=[self.state['environment']], dry_run=False)
        self.res.print('Geregistreerd. Bewaar dit als vastlegging (plakbaar met table()):\n\n' + export_tables(sources, entities))
        self.done_of = fingerprint
        self.confirm.value = False
        self.res.print('Klik "Laden uit de configdb" voor de actuele stand.')


def registration_ui(domain='INTEGRATION', environment='D'):
    """Opens the registration editor. Click "Laden uit de configdb" to read what is registered."""
    return RegistrationUI(domain, environment)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
