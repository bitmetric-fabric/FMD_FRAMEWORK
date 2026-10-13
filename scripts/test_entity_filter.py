"""Check of the entity filter (DataSourceName / Entities) in the load chain. No dependencies, no network.

    python3 scripts/test_entity_filter.py

Static check of the pipelines and SQL sources. The filter has to be in every place where LoadGroup is:
  1. every load pipeline that declares LoadGroup (except PL_FMD_ORCHESTRATION) also declares DataSourceName and
     Entities, default "";
  2. everywhere LoadGroup is passed on (invoke parameter or stored procedure parameter) both are passed on too;
  3. every inline query with the LoadGroup clause also calls fn_EntityInFilter, with the single quotes of both
     values doubled (a quote in a table name must not break or inject into the query);
  4. the two getters and their views have the filter parameters and columns, and the function exists.
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
NEW = ["DataSourceName", "Entities"]
LOADGROUP_CLAUSE = "(''='@{pipeline().parameters.LoadGroup}' or LoadGroup='@{pipeline().parameters.LoadGroup}')"
ESCAPED = {n: "'@{replace(pipeline().parameters.%s,'''','''''')}'" % n for n in NEW}

failures = 0


def check(ok, text):
    global failures
    print(("  ok     " if ok else "  FOUT   ") + text)
    failures += 0 if ok else 1


def walk(node):
    """Yield every dict and every str in a JSON tree."""
    yield node
    if isinstance(node, dict):
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


print("=== pipelines ===")
checked = 0
for path in sorted((REPO / "src").glob("PL_FMD_*.DataPipeline/pipeline-content.json")):
    name = path.parent.name.removesuffix(".DataPipeline")
    definition = json.loads(path.read_text(encoding="utf-8"))
    if "LoadGroup" not in definition["properties"].get("parameters", {}) or name == "PL_FMD_ORCHESTRATION":
        continue
    checked += 1
    parameters = definition["properties"]["parameters"]
    check(all(parameters.get(n) == {"type": "string", "defaultValue": ""} for n in NEW), f"{name}: parameters declared, default empty")
    passed = [d for d in walk(definition) if isinstance(d, dict) and "LoadGroup" in d and d is not parameters]
    check(all(n in d for d in passed for n in NEW), f"{name}: all {len(passed)} places that pass LoadGroup on also pass the filter")
    queries = [s for s in walk(definition) if isinstance(s, str) and LOADGROUP_CLAUSE in s]
    check(all("fn_EntityInFilter" in q and all(ESCAPED[n] in q for n in NEW) for q in queries),
          f"{name}: all {len(queries)} queries call fn_EntityInFilter with escaped values")
check(checked == 25, f"25 pipelines in the load chain checked (got {checked})")

orchestration = (REPO / "src/PL_FMD_ORCHESTRATION.DataPipeline/pipeline-content.json").read_text(encoding="utf-8")
check("DataSourceName" not in orchestration, "PL_FMD_ORCHESTRATION (schedule wrapper) is unchanged: LoadGroup only")

print("=== SQL ===")
EXEC = REPO / "src/Config_Database/execution"
function = (EXEC / "Functions/fn_EntityInFilter.sql").read_text(encoding="utf-8")
check("ISNULL(@DataSourceNameFilter, '') = ''" in function and "ISNULL(@EntitiesFilter, '') = ''" in function, "function: empty or NULL means no filter")
check("STRING_SPLIT" in function and "CONCAT(@SourceSchema, '.', @SourceName)" in function, "function: matches SourceName or SourceSchema.SourceName")
for layer in ("Bronze", "Silver"):
    proc = (EXEC / f"StoredProcedures/sp_Get{layer}layerEntity.sql").read_text(encoding="utf-8")
    view = (EXEC / f"Views/vw_LoadTo{layer}Layer.sql").read_text(encoding="utf-8")
    check("@DataSourceName NVARCHAR(100) = ''" in proc and "@Entities NVARCHAR(MAX) = ''" in proc, f"sp_Get{layer}layerEntity: parameters with default empty")
    check("[execution].[fn_EntityInFilter](@DataSourceName, @Entities, DataSourceName, LandingzoneSourceSchema, LandingzoneSourceName) = 1" in proc,
          f"sp_Get{layer}layerEntity: calls fn_EntityInFilter")
    check(all(c in view for c in ("AS [DataSourceName]", "AS [LandingzoneSourceSchema]", "AS [LandingzoneSourceName]")), f"vw_LoadTo{layer}Layer: filter columns")
landing = (EXEC / "Views/vw_LoadSourceToLandingzone.sql").read_text(encoding="utf-8")
check(all(re.search(r"\[%s\]" % c, landing) for c in ("DataSourceName", "SourceSchema", "SourceName")), "vw_LoadSourceToLandingzone: has the columns the queries filter on")

print("\nALLES OK" if not failures else f"\n{failures} FOUT(EN)")
sys.exit(1 if failures else 0)
