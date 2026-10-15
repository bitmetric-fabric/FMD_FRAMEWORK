# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # Registration functions
# Function declarations for NB_REGISTRATIE. Lives in the configuration workspace, next to
# SQL_FMD_FRAMEWORK, so it never needs a GUID for the config database: it looks up the one
# SQLDatabase item in its own workspace through the Fabric REST API. Framework-owned: the setup
# overwrites it on every run, unlike NB_REGISTRATIE itself.

# CELL ********************

import struct, pyodbc, time, json, requests

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

def print_entity_list(connection_name, data_source_name, schema=None, source_alias="SRC"):
    """
    Prints Python dict literals, one per table/view PL_FMD_DISCOVER_SOURCE found for this
    connection + database (optionally narrowed to one schema), ready to paste into the
    `entities` list in NB_REGISTRATIE. PrimaryKeys comes from the source when it has one;
    a table without a primary key gets a TODO instead, so register(..., dry_run=True) stops
    on it rather than silently registering an empty key.
    """
    driver, connstring, database = resolve_config_database()
    result = execute_with_outputs("[integration].[sp_GetDiscoveredEntities]", driver, connstring, database,
                                  ConnectionName=connection_name, DataSourceName=data_source_name, SchemaFilter=schema)
    rows = result["result_sets"][0]
    if not rows:
        print(f"Nothing discovered for {connection_name}/{data_source_name}"
              + (f", schema {schema}" if schema else "") + ". Run PL_FMD_DISCOVER_SOURCE first.")
        return

    for r in rows:
        pk = r["PrimaryKeys"] or ""
        # The TODO goes after the closing "}," so a pasted line stays valid Python.
        todo = "" if pk else "  # TODO: no primary key found, fill in or confirm there is none"
        print(
            "    {" + f'"Source": "{source_alias}", "SourceSchema": "{r["SourceSchema"]}", '
            f'"SourceName": "{r["SourceName"]}", "PrimaryKeys": "{pk}"' + "}," + todo
        )

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
      LoadGroup lives on the data source, so environments that share a binding share it.
      HistoryDays (optional): for an incremental entity without a watermark yet, the first load
      only fetches the last N days; an existing watermark is never changed.
    entities: Source, SourceSchema, SourceName and PrimaryKeys are required.
      FileName defaults to <TargetSchema>_<TargetName>, FileType to 'parquet' ('delta' for
      Snowflake without a storage integration, ADR-014; FileName then only letters, digits, '_').
      IsActive: the list is the truth, switch an entity off with 0 here, not by hand.
      IsHistorized (default 0): 1 keeps the history of changes in Silver (SCD2), ADR-016; empty
      means 0, also for an entity registered with 1 before. CustomNotebookName only for NOTEBOOK.
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
