# Snowflake Delta-landing implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entities in a Snowflake source with `FileType = 'delta'` land as a Delta table per run in `LH_DATA_LANDINGZONE`; `parquet` entities keep the COPY INTO route.

**Architecture:** An If activity per entity in `PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01` picks the Script (COPY INTO) or a new Copy activity. The queue row (`execution.PipelineLandingzoneEntity`) carries the location: a `FilePath` starting with `Tables` is relative to the lakehouse root, otherwise to `Files/`. One shared helper, `landing_path()` in `NB_FMD_UTILITY_FUNCTIONS`, resolves it for Bronze and for the maintenance notebook. No dacpac.

**Tech Stack:** Fabric Data Pipeline JSON, PySpark notebooks (`notebook-content.py`), Python 3 stdlib test scripts (`scripts/test_*.py`, run by hand, no network), Fabric REST for the trial test.

**Spec:** `Projects/Fabric/ontwerp-delta-variant.md` (spike: run `f4516da7`, log `generale-repetitie.md` 2026-10-13).

## Global Constraints

- Identifiers and comments in framework code in English; commit messages, PR text and docs in Dutch, no attribution lines.
- Write LF line endings (the blobs are LF; a Windows checkout is CRLF).
- No literal workspace or item GUIDs in `src/` (guid-guard, ADR-009/010): use `@item()` and library variables.
- No dacpac change: nothing under `src/Config_Database/` may change (dacpac-guard).
- Do not merge without explicit approval from Mitchell. Test in the trial before the PR is marked ready.
- Existing `parquet` behaviour must stay the same (default `FileType`).

## Review Focus

- A `FileName` with characters that are invalid in a table name (space, dot, hyphen) on a `delta` entity: the copy fails. Expected: documented constraint (letters, digits, `_`), the entity run fails with the copy error; no sanitizing (YAGNI). Pinned by a doc line in Task 5.
- Two runs of the same entity within one minute (same `yyyyMMddHHmm`): same table name, `tableActionOption: Overwrite` replaces the first. Expected: not a supported case (the Files route overwrites too). Documented.
- `FilePath` equal to `Tables` or `Tables/ldz` versus a file path that merely contains `Tables` (`fmd/Tables_x/...`, `TablesX/y`): only a leading `Tables` segment counts. Pinned by `test_landing_path`.
- `lakehouse_schema_enabled = false`: not tested in this change; the pipeline then writes to `Tables` without a schema. Documented as untested.
- An entity switched from `parquet` to `delta` (or back) while old deliveries are still in the queue: old rows keep their own `FilePath`, so both are cleaned up correctly. Pinned by `test_landing_path` (both prefixes) and checked in the trial (Task 4, step 6).

## File Structure

| File | Change |
|---|---|
| `src/NB_FMD_UTILITY_FUNCTIONS.Notebook/notebook-content.py` | add `landing_path()` |
| `src/NB_FMD_LOAD_LANDING_BRONZE.Notebook/notebook-content.py` | use `landing_path()`, add Delta read branch |
| `src/NB_FMD_MAINTENANCE.Notebook/notebook-content.py` | use `landing_path()` |
| `src/PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.DataPipeline/pipeline-content.json` | If + Copy, rewire dependencies and audit expressions, queue-row expressions |
| `scripts/test_snowflake_delta.py` | new: structure test of the pipeline + `landing_path` tests |
| `templates/registratie/registreer_entiteiten.sql` | comment on `FileType` |
| `docs/adr/014-snowflake-schrijft-landing-zone.md`, `docs/adr/015-opslagbeheer.md` | amend |
| `Projects/Fabric/output/…` (outside the repo) | draaiboek, intake-checklist, troubleshooting, testplan log |

---

### Task 1: Worktree and `landing_path()`

**Files:**
- Create: `scripts/test_snowflake_delta.py`
- Modify: `src/NB_FMD_UTILITY_FUNCTIONS.Notebook/notebook-content.py` (append a cell at the end)

**Interfaces:**
- Produces: `landing_path(workspace: str, lakehouse: str, file_path: str, file_name: str) -> str`, returns `abfss://{workspace}@onelake.dfs.fabric.microsoft.com/{lakehouse}/{root}{file_path}/{file_name}` where `root` is `""` if `file_path` is `Tables` or starts with `Tables/`, else `"Files/"`.

- [ ] **Step 1: Create the worktree on a new branch from main**

```bash
cd "/c/Users/MitchellKrops/OneDrive - Bitmetric B.V/Projects/Fabric/FMD"
git fetch origin
git worktree add "$TEMP/fmd-delta" -b feature/snowflake-delta-landing origin/main
```
Expected: a clean worktree at `%TEMP%\fmd-delta`; all following paths are relative to it.

- [ ] **Step 2: Write the failing test** `scripts/test_snowflake_delta.py`

```python
"""Check of the Delta landing for Snowflake (ADR-014). No dependencies, no network.

    python3 scripts/test_snowflake_delta.py

Checks the landing_path() helper and the structure of PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.
"""

import ast
import json
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
PIPELINE = REPO / "src/PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.DataPipeline/pipeline-content.json"
UTILITY = REPO / "src/NB_FMD_UTILITY_FUNCTIONS.Notebook/notebook-content.py"


def load_function(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


def test_landing_path():
    landing_path = load_function(UTILITY, "landing_path")
    base = "abfss://ws@onelake.dfs.fabric.microsoft.com/lh/"
    assert landing_path("ws", "lh", "fmd/sf/Sales_Customer/2026/10/13", "Sales_Customer_202610130900.parquet") == \
        base + "Files/fmd/sf/Sales_Customer/2026/10/13/Sales_Customer_202610130900.parquet"
    assert landing_path("ws", "lh", "Tables/ldz", "sf_Sales_Customer_202610130900") == base + "Tables/ldz/sf_Sales_Customer_202610130900"
    assert landing_path("ws", "lh", "Tables", "sf_Sales_Customer_202610130900") == base + "Tables/sf_Sales_Customer_202610130900"
    # only a leading Tables segment counts
    assert landing_path("ws", "lh", "fmd/Tables_x", "f.parquet") == base + "Files/fmd/Tables_x/f.parquet"
    assert landing_path("ws", "lh", "TablesX/y", "f.parquet") == base + "Files/TablesX/y/f.parquet"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print("ok", name)
    print(f"{len(tests)} tests passed")
```

- [ ] **Step 3: Run it, expect FAIL**

Run: `python3 scripts/test_snowflake_delta.py`
Expected: `StopIteration` (no `landing_path` in the utility notebook yet).

- [ ] **Step 4: Append the helper cell** at the end of `src/NB_FMD_UTILITY_FUNCTIONS.Notebook/notebook-content.py`, in the same cell/metadata format as the existing cells:

```python
# CELL ********************

def landing_path(workspace, lakehouse, file_path, file_name):
    """OneLake path of a landing zone delivery.

    A file_path that starts with 'Tables' is relative to the lakehouse root (Delta landing, ADR-014); anything else is relative to Files/.
    """
    root = "" if file_path == "Tables" or file_path.startswith("Tables/") else "Files/"
    return f"abfss://{workspace}@onelake.dfs.fabric.microsoft.com/{lakehouse}/{root}{file_path}/{file_name}"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
```

- [ ] **Step 5: Run the test, expect PASS**

Run: `python3 scripts/test_snowflake_delta.py`
Expected: `ok test_landing_path` / `1 tests passed`.

- [ ] **Step 6: Commit**

```bash
git add scripts/test_snowflake_delta.py src/NB_FMD_UTILITY_FUNCTIONS.Notebook/notebook-content.py
git commit -m "landing_path(): pad van een levering in de landing zone, ook voor Delta-tabellen"
```

---

### Task 2: Bronze and maintenance use `landing_path()`

**Files:**
- Modify: `src/NB_FMD_LOAD_LANDING_BRONZE.Notebook/notebook-content.py` (cell "Set SourceFile and target Location", ~line 261; read cell ~line 318)
- Modify: `src/NB_FMD_MAINTENANCE.Notebook/notebook-content.py` (~line 101)
- Test: `scripts/test_snowflake_delta.py`

**Interfaces:**
- Consumes: `landing_path(workspace, lakehouse, file_path, file_name)` from Task 1 (both notebooks already `%run NB_FMD_UTILITY_FUNCTIONS`).

- [ ] **Step 1: Add failing tests** (append to `scripts/test_snowflake_delta.py`, before `if __name__`):

```python
BRONZE = REPO / "src/NB_FMD_LOAD_LANDING_BRONZE.Notebook/notebook-content.py"
MAINTENANCE = REPO / "src/NB_FMD_MAINTENANCE.Notebook/notebook-content.py"


def test_notebooks_use_landing_path():
    bronze = BRONZE.read_text(encoding="utf-8")
    maintenance = MAINTENANCE.read_text(encoding="utf-8")
    assert "source_changes_data_path = landing_path(SourceWorkspace, SourceLakehouse, SourceFilePath, SourceFileName)" in bronze
    assert "/Files/{SourceFilePath}/{SourceFileName}" not in bronze
    assert "path = landing_path(d['WorkspaceGuid'], d['LakehouseGuid'], d['FilePath'], d['FileName'])" in maintenance
    assert "/Files/{d['FilePath']}" not in maintenance


def test_bronze_reads_delta():
    bronze = BRONZE.read_text(encoding="utf-8")
    assert "if SourceFileType == 'delta':" in bronze
    assert "spark.read.format('delta').load(source_changes_data_path)" in bronze
```

- [ ] **Step 2: Run, expect FAIL** (`AssertionError` in `test_notebooks_use_landing_path`).

- [ ] **Step 3: Bronze, path.** Replace the line

```python
source_changes_data_path = f"abfss://{SourceWorkspace}@onelake.dfs.fabric.microsoft.com/{SourceLakehouse}/Files/{SourceFilePath}/{SourceFileName}"
```
with
```python
source_changes_data_path = landing_path(SourceWorkspace, SourceLakehouse, SourceFilePath, SourceFileName)
```

- [ ] **Step 4: Bronze, read.** In the cell that starts with `if SourceFileType=='csv':`, make that `if` an `elif` and put a new first branch in front of it:

```python
if SourceFileType == 'delta':
    # Delta landing (ADR-014): one table per run, written by the Snowflake copy activity
    dfDataChanged = spark.read.format('delta').load(source_changes_data_path)
elif SourceFileType=='csv':
```
The rest of the cell (xlsx, xls, the parquet `else`) stays as is, so the parquet path and `convert_small_numeric_columns_to_int` are untouched.

- [ ] **Step 5: Maintenance.** In the landing zone loop replace

```python
    path = f"abfss://{d['WorkspaceGuid']}@{onelake}/{d['LakehouseGuid']}/Files/{d['FilePath']}/{d['FileName']}"
```
with
```python
    path = landing_path(d['WorkspaceGuid'], d['LakehouseGuid'], d['FilePath'], d['FileName'])
```
and change the comment on the `rm` line to: `# a file, or a folder (Snowflake writes several files, or a Delta table folder)`. `onelake` is still used for the VACUUM paths, so keep it.

- [ ] **Step 6: Run the tests, expect PASS** (`3 tests passed`).

- [ ] **Step 7: Commit**

```bash
git add scripts/test_snowflake_delta.py src/NB_FMD_LOAD_LANDING_BRONZE.Notebook src/NB_FMD_MAINTENANCE.Notebook
git commit -m "Bronze leest en onderhoud ruimt op via landing_path(); Bronze kan een Delta-levering lezen"
```

---

### Task 3: Pipeline: If, Copy activity, rewired dependencies

**Files:**
- Modify: `src/PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.DataPipeline/pipeline-content.json` (via a one-off patch script, then check the diff)
- Create: `patch_delta_pipeline.py` in the session scratchpad (not committed)
- Test: `scripts/test_snowflake_delta.py`

**Interfaces:**
- Produces (pipeline): inside `FE_ENTITY`, activity `IF_FILETYPE` (If) with `ifTrueActivities = [CP_COPY_TO_LANDINGZONE]` and `ifFalseActivities = [SC_COPY_INTO_LANDINGZONE]`. `SC_COPY_INTO_LANDINGZONE` keeps its content but moves into the false branch with `dependsOn: []`; `IF_FILETYPE` takes its old `dependsOn` (`LK_GET_LASTLOADDATE`). `SP_FAIL_AUDIT_PIPELINE_CP` and `SP_UPDATE_PROCESS` depend on `IF_FILETYPE`.
- Queue row for `delta`: `FilePath = Tables/ldz` (or `Tables` when `VAR_FMD_lakehouse_schema_enabled` is not `true`), `FileName = <namespace>_<FileName>_<yyyyMMddHHmm>`; for `parquet` unchanged (`TargetFilePath`, `TargetFileName`).

- [ ] **Step 1: Add the failing structure test** (append to `scripts/test_snowflake_delta.py`):

```python
def foreach_activities():
    pipeline = json.loads(PIPELINE.read_text(encoding="utf-8"))["properties"]
    foreach = next(a for a in pipeline["activities"] if a["name"] == "FE_ENTITY")
    return {a["name"]: a for a in foreach["typeProperties"]["activities"]}


def test_pipeline_branches_on_filetype():
    acts = foreach_activities()
    branch = acts["IF_FILETYPE"]
    assert branch["type"] == "IfCondition"
    assert branch["typeProperties"]["expression"]["value"] == "@equals(item().TargetFileType,'delta')"
    assert [a["name"] for a in branch["typeProperties"]["ifTrueActivities"]] == ["CP_COPY_TO_LANDINGZONE"]
    assert [a["name"] for a in branch["typeProperties"]["ifFalseActivities"]] == ["SC_COPY_INTO_LANDINGZONE"]
    assert [d["activity"] for d in branch["dependsOn"]] == ["LK_GET_LASTLOADDATE"]
    # nothing outside the If may depend on an activity inside it
    for name in ("SP_FAIL_AUDIT_PIPELINE_CP", "SP_UPDATE_PROCESS"):
        assert [d["activity"] for d in acts[name]["dependsOn"]] == ["IF_FILETYPE"], name
    for name, a in acts.items():
        for d in a.get("dependsOn", []):
            assert d["activity"] in acts, f"{name} depends on {d['activity']} which is not at the ForEach level"


def test_copy_activity_writes_a_delta_table_per_run():
    copy = foreach_activities()["IF_FILETYPE"]["typeProperties"]["ifTrueActivities"][0]
    tp = copy["typeProperties"]
    assert tp["source"]["type"] == "SnowflakeV2Source"
    assert tp["source"]["query"]["value"] == "@item().SourceDataRetrieval"
    assert tp["sink"]["type"] == "LakehouseTableSink"
    assert tp["sink"]["tableActionOption"] == "Overwrite"
    assert tp["enableStaging"] is True
    sink_ds = tp["sink"]["datasetSettings"]
    assert sink_ds["linkedService"]["properties"]["typeProperties"]["workspaceId"] == "@item().WorkspaceGuid"
    assert sink_ds["linkedService"]["properties"]["typeProperties"]["artifactId"] == "@item().TargetLakehouseGuid"
    assert "item().DataSourceNamespace" in sink_ds["typeProperties"]["table"]["value"]


def test_queue_row_carries_the_location():
    acts = foreach_activities()
    update = acts["SP_UPDATE_PROCESS"]["typeProperties"]["storedProcedureParameters"]
    name = update["Filename"]["value"]["value"]
    path = update["FilePath"]["value"]["value"]
    assert "item().TargetFileName" in name and "item().DataSourceNamespace" in name and "'delta'" in name
    assert "item().TargetFilePath" in path and "'Tables/ldz'" in path
    # the audit expressions name the activity of the branch that ran
    text = json.dumps(acts["SP_END_AUDIT_PIPELINE_CP"]) + json.dumps(acts["SP_FAIL_AUDIT_PIPELINE_CP"])
    assert "activity('SC_COPY_INTO_LANDINGZONE')" in text and "activity('CP_COPY_TO_LANDINGZONE')" in text
```

- [ ] **Step 2: Run, expect FAIL** (`KeyError: 'IF_FILETYPE'`).

- [ ] **Step 3: Write the patch script** `patch_delta_pipeline.py` (scratchpad). It loads the pipeline JSON, rewrites it and writes it back (2-space indent, `ensure_ascii=False`, LF):

```python
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
pipeline = json.loads(path.read_text(encoding="utf-8"))
foreach = next(a for a in pipeline["properties"]["activities"] if a["name"] == "FE_ENTITY")
acts = foreach["typeProperties"]["activities"]
by_name = {a["name"]: a for a in acts}
script = by_name["SC_COPY_INTO_LANDINGZONE"]

SCHEMA_ON = "equals(toLower(string(pipeline().libraryVariables.VAR_FMD_lakehouse_schema_enabled)),'true')"
TABLE = "concat(item().DataSourceNamespace,'_',replace(item().TargetFileName,concat('.',item().TargetFileType),''))"
DELTA = "equals(item().TargetFileType,'delta')"

copy = {
    "name": "CP_COPY_TO_LANDINGZONE", "type": "Copy", "dependsOn": [],
    "policy": {"timeout": "0.01:00:00", "retry": 0, "retryIntervalInSeconds": 30, "secureOutput": False, "secureInput": False},
    "description": "Snowflake naar een Delta-tabel per run in de landing zone, zonder storage integration (ADR-014, Delta-variant).",
    "typeProperties": {
        "source": {
            "type": "SnowflakeV2Source",
            "query": {"value": "@item().SourceDataRetrieval", "type": "Expression"},
            "exportSettings": {"type": "SnowflakeExportCopyCommand"},
            "datasetSettings": {"annotations": [], "type": "SnowflakeV2Table", "schema": [],
                                "typeProperties": {"database": {"value": "@item().DataSourceName", "type": "Expression"}},
                                "externalReferences": {"connection": "@item().ConnectionGuid"}}},
        "sink": {
            "type": "LakehouseTableSink", "tableActionOption": "Overwrite", "partitionOption": "None",
            "datasetSettings": {
                "annotations": [],
                "linkedService": {"name": "LDZ", "properties": {"annotations": [], "type": "Lakehouse", "typeProperties": {
                    "workspaceId": "@item().WorkspaceGuid", "artifactId": "@item().TargetLakehouseGuid", "rootFolder": "Tables"}}},
                "type": "LakehouseTable", "schema": [],
                "typeProperties": {"schema": {"value": f"@if({SCHEMA_ON},'ldz','')", "type": "Expression"},
                                   "table": {"value": f"@{TABLE}", "type": "Expression"}}}},
        "enableStaging": True,
        "translator": {"type": "TabularTranslator", "typeConversion": True,
                       "typeConversionSettings": {"allowDataTruncation": True, "treatBooleanAsNumber": False}}}}

branch = {
    "name": "IF_FILETYPE", "type": "IfCondition", "dependsOn": script["dependsOn"],
    "typeProperties": {"expression": {"value": f"@{DELTA}", "type": "Expression"},
                       "ifTrueActivities": [copy], "ifFalseActivities": [script]}}
script["dependsOn"] = []
acts[acts.index(script)] = branch

for name in ("SP_FAIL_AUDIT_PIPELINE_CP", "SP_UPDATE_PROCESS"):
    for d in by_name[name].get("dependsOn", []):
        if d["activity"] == "SC_COPY_INTO_LANDINGZONE":
            d["activity"] = "IF_FILETYPE"

def audit(name, old, new_part):
    value = by_name[name]["typeProperties"]["storedProcedureParameters"]["LogData"]["value"]
    assert value["value"].count(old) == 1, (name, old)
    value["value"] = value["value"].replace(old, new_part)

# audit: the output/error of the branch that ran
audit("SP_END_AUDIT_PIPELINE_CP", "@{activity('SC_COPY_INTO_LANDINGZONE').output}",
      "@{if(" + DELTA + ",activity('CP_COPY_TO_LANDINGZONE').output,activity('SC_COPY_INTO_LANDINGZONE').output)}")
audit("SP_FAIL_AUDIT_PIPELINE_CP", "@{activity('SC_COPY_INTO_LANDINGZONE').error}",
      "@{if(" + DELTA + ",activity('CP_COPY_TO_LANDINGZONE').error,activity('SC_COPY_INTO_LANDINGZONE').error)}")

# queue row: where the delivery landed
p = by_name["SP_UPDATE_PROCESS"]["typeProperties"]["storedProcedureParameters"]
p["Filename"]["value"]["value"] = f"@if({DELTA},{TABLE},item().TargetFileName)"
p["FilePath"]["value"]["value"] = f"@if({DELTA},if({SCHEMA_ON},'Tables/ldz','Tables'),item().TargetFilePath)"

path.write_text(json.dumps(pipeline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
```

- [ ] **Step 4: Run it and review the diff**

```bash
python3 "<scratchpad>/patch_delta_pipeline.py" src/PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.DataPipeline/pipeline-content.json
git diff --stat
git diff src/PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.DataPipeline/pipeline-content.json | head -250
```
Expected: only the Script activity moved (re-indented) into `IF_FILETYPE`, plus the new Copy block and the edited expressions. If `json.dumps` reformats other parts (indentation, escaping), adjust `indent`/`separators` until the diff is limited to this change. Check that the file ends with the same trailing newline as before.

- [ ] **Step 5: Run the tests, expect PASS** (`6 tests passed`).

- [ ] **Step 6: Run the guards locally**

```bash
python3 scripts/guid_guard.py
python3 scripts/test_schedule_pipeline.py; python3 scripts/test_manifest_wiring.py; python3 scripts/test_id_mapping.py
```
Expected: all pass (no literal GUIDs added; no dacpac change).

- [ ] **Step 7: Commit**

```bash
git add src/PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.DataPipeline scripts/test_snowflake_delta.py
git commit -m "Snowflake-landing: FileType 'delta' schrijft een Delta-tabel per run (Copy-activiteit), 'parquet' blijft COPY INTO"
```

---

### Task 4: Test in the trial (GR Dev), then the mix in FMD_TRIAL Dev

**Files:**
- Create (scratchpad): `gr_deploy_delta.py` (patches the *deployed* items with the same transformations, via `getDefinition`/`updateDefinition`), `gr_delta_check.py` (counts, types, queue rows, OneLake listing)
- Modify: `generale-repetitie.md`, `testplan-trial.md` (log)

**Interfaces:**
- Consumes: the three patched notebooks and `patch_delta_pipeline.py` from Tasks 1–3.

- [ ] **Step 1: Deploy to `FMD_GR INTEGRATION CODE (D)`.** The deployed pipeline and notebooks carry workspace-specific values (library variables, default lakehouse), so do not upload the repo files. For each of `PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01`, `NB_FMD_UTILITY_FUNCTIONS`, `NB_FMD_LOAD_LANDING_BRONZE`, `NB_FMD_MAINTENANCE`: `getDefinition`, apply the same string/JSON replacement as Tasks 1–3 (assert each target occurs exactly once, otherwise stop), `updateDefinition`. Keep the original definitions in the scratchpad as backup.

- [ ] **Step 2: Register the delta entities** in the FMD_GR configdb (sqlcmd `ActiveDirectoryAzCli`, server and database in `generale-repetitie.md`): Source `SF` (`'*'`, `CON_GR_SNOWFLAKE`, `FMD_BRON`, namespace `sf`, `SNOWFLAKE_01`, LoadGroup `INTRADAY`) and entities `TPCH.CUSTOMER` (full, PK `C_CUSTKEY`, `FileType 'delta'`) and `TPCH.ORDERS` (incremental on `GEWIJZIGD_OP`, PK `O_ORDERKEY`, `FileType 'delta'`), via the list template `templates/registratie/registreer_entiteiten.sql` with `-v DataWorkspace=<GR DATA (D) workspace id> Environment=D`. This is GR-E5 for two of the eight tables; the rest follows in the rehearsal.

- [ ] **Step 3: Run `PL_FMD_LOAD_ALL`** in `FMD_GR INTEGRATION CODE (D)` (`gr_run_pipeline.py`). Expected: Completed. Then check with `gr_delta_check.py`:
  - landing tables `sf_TPCH_CUSTOMER_<ts>` and `sf_TPCH_ORDERS_<ts>` (naming follows `FileName`) under `Tables/ldz` in `LH_DATA_LANDINGZONE` (OneLake DFS);
  - queue rows in `execution.PipelineLandingzoneEntity`: `FilePath = Tables/ldz`, `IsProcessed = 1`;
  - Silver counts equal the source (CUSTOMER 150,000; ORDERS 1,500,001) and decimal/timestamp types intact in Bronze and Silver (`INFORMATION_SCHEMA.COLUMNS` after `refreshMetadata`);
  - the end-audit in `logging.PipelineExecution` holds the Copy metrics (`rowsCopied`). If the run fails on the `if(...)` audit expressions ("activity not run"), `if()` is not lazy: replace both expressions with `activity('IF_FILETYPE').output` / `.error`, accept the loss of copy metrics, and say so in the PR. Record which case it was.

- [ ] **Step 4: Second run, incremental.** Run again without changing Snowflake: ORDERS copies 0 rows (watermark), Silver unchanged. Then ask Mitchell to change 10 rows in Snowflake as ACCOUNTADMIN (`UPDATE FMD_BRON.TPCH.ORDERS SET GEWIJZIGD_OP = CURRENT_TIMESTAMP() WHERE O_ORDERKEY IN (<10 keys>)`; the read user cannot), run again, and record Bronze/Silver counts.

- [ ] **Step 5: Cleanup.** Run `PL_FMD_MAINTENANCE` (Target MAINTENANCE) with `RetentionDays = 1`, after backdating `LoadEndDateTime` of the processed queue rows by 2 days in the FMD_GR configdb (test-only change to a log column; state it in the log). Expected: the processed landing tables are removed from `Tables/ldz` (`LandingDeleted` >= 2 in the notebook exit), and a delivery with `IsProcessed = 0` stays. Confirm via OneLake DFS.

- [ ] **Step 6: Regression and mix in `FMD_TRIAL` Dev** (where the storage integration exists): deploy the same patches to the trial Dev items (same method as Step 1), keep `SF` entities `CUSTOMER` and `ORDERS` on `parquet`, add `NATION` (full) as `delta`. Run `LOAD_ALL`. Expected: the parquet entities load as before (landing under `Files/`), `NATION` lands under `Tables/ldz`, all reach Silver. Then switch `CUSTOMER` to `delta` and back, running each time: the old parquet delivery and the new delta delivery are both processed and cleaned up correctly.

- [ ] **Step 7: Make the GR change survive.** The GR Dev items were patched outside git. Note in `generale-repetitie.md` that these four items are committed to the GR CODE (D) `dev` branch as part of GR-E8, or the setup is re-run after the merge, whichever the rehearsal needs at that point.

- [ ] **Step 8: Log.** Write results (run IDs, counts, durations, the `if()` outcome, DataMovement per run from `queryactivityruns`) into `generale-repetitie.md` and `testplan-trial.md`.

---

### Task 5: Documentation and PR

**Files:**
- Modify: `docs/adr/014-snowflake-schrijft-landing-zone.md`, `docs/adr/015-opslagbeheer.md`, `templates/registratie/registreer_entiteiten.sql`
- Modify (outside the repo): `Projects/Fabric/output/04_implementatieplan/draaiboek_detail.md`, `output/02_beslisdocument/04_intake-checklist.md`, `output/03_technische_documentatie/11_troubleshooting.md`

- [ ] **Step 1: ADR-014.** Move "Copy-activiteit naar een Delta-tabel per run" from *Alternatieven* to a new section *Delta-variant* (ondersteund, per entiteit via `FileType = 'delta'`): when to use it (klant kan of wil geen storage integration), how it works (If in de pipeline, tabel per run in schema `ldz`, `FilePath` met `Tables` als gedeelde regel voor Bronze en onderhoud), cost (gemeten: 1,5 miljoen rijen 85 s, 0,27 DIU-uur, DataMovement; 17x langzamer dan COPY INTO), constraints (`FileName` alleen letters, cijfers en `_`; één run per minuut per entiteit; lakehouse zonder schema's niet getest; accountparameters `PREVENT_UNLOAD_TO_INLINE_URL` niet getest). Zet een gedateerde correctie bij de regel "Een klant die dat niet toestaat, valt terug op de Delta-variant". Nederlands, met statuslabels (vastgesteld / getest met datum en run-ID / aanname).

- [ ] **Step 2: ADR-015.** One paragraph: the landing cleanup removes a Delta landing table the same way as a file delivery, keyed on `FilePath`/`FileName` of the queue row, via `landing_path()`.

- [ ] **Step 3: Template comment.** In `templates/registratie/registreer_entiteiten.sql`, next to the `[FileType]` column: `-- FileType: 'parquet' (default; Snowflake schrijft met een storage integration) of 'delta' (Copy-activiteit naar een Delta-tabel per run, ADR-014)`.

- [ ] **Step 4: Output docs** (outside the repo): draaiboek fase 4 (bron registreren) and the intake checklist get the question "Kan de klant een storage integration laten maken? Zo nee: `FileType = 'delta'`, met de kosten en beperkingen uit ADR-014"; troubleshooting gets an entry for a failing Delta copy (staging, tabelnaam). Each claim with a status label and the run ID from Task 4.

- [ ] **Step 5: Final checks and PR.** Re-run `python3 scripts/test_snowflake_delta.py` and the guards; `git diff origin/main --stat` shows only the files in the File Structure table (nothing under `Config_Database`). Push and open the PR (Dutch title and description, no attribution lines):

```bash
git add -A docs templates
git commit -m "ADR-014 en ADR-015: Delta-variant voor Snowflake naast storage integration"
git push -u origin feature/snowflake-delta-landing
gh pr create --repo bitmetric-fabric/FMD_FRAMEWORK --base main --title "Snowflake: Delta-tabel per run als landing naast COPY INTO (per entiteit via FileType)" --body-file "<scratchpad>/pr_body.md"
```
The body states what and why, the trial runs (IDs, counts, cost), what is untested (lakehouse zonder schema's, strenge accounts) and that there is no dacpac change. Do not merge: ask Mitchell. After a merge: merge `origin/main` into `trial-deploy` and push to `trial main`; merge `origin/main` into `repetitie`.

---

## Self-review

- **Spec coverage:** keuze per entiteit (Task 3), pipeline If (3), tabelnaam `<ns>_<FileName>_<ts>` in `ldz` (3), wachtrij legt pad vast (3), Bronze (2), opruimen (2, test in 4), registratie (5), documentatie (5), testplan 1–5 uit de spec (Task 4 steps 2–6), kosten en risico's (5).
- **Placeholders:** none; the angle-bracket items (`<ts>`, `<scratchpad>`, `<GR DATA (D) workspace id>`) are run-time values with their source named.
- **Names:** `landing_path(workspace, lakehouse, file_path, file_name)` is identical in Tasks 1–2; activity names `IF_FILETYPE`, `CP_COPY_TO_LANDINGZONE`, `SC_COPY_INTO_LANDINGZONE` are identical in the patch script and the tests.
- **Deviation from the spec:** the spec said Bronze and maintenance "share one rule"; the plan implements that as one shared function in the utility notebook.
