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


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print("ok", name)
    print(f"{len(tests)} tests passed")
