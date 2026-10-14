"""Check of the Data_WorkspaceGuid fallback in the load pipelines a person starts directly. No dependencies, no network.

    python3 scripts/test_workspace_fallback.py

PL_FMD_LOAD_ALL, _LANDINGZONE, _BRONZE and _SILVER can each be started on their own (a rerun, a subset). Without
Data_WorkspaceGuid they must take VAR_CONFIG_FMD.fmd_data_workspace_guid of their own environment, not run green
with an empty workspace and load nothing:
  1. the parameter is declared with default "";
  2. every use of the parameter is inside the fallback expression;
  3. the library variable the fallback reads is declared.
"""

import json
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
PARAMETER = "pipeline().parameters.Data_WorkspaceGuid"
# As a whole value ("@if(...)") or inside an inline query ("@{if(...)}").
FALLBACK = ("if(empty(pipeline().parameters.Data_WorkspaceGuid), "
            "pipeline().libraryVariables.VAR_CONFIG_FMD_fmd_data_workspace_guid, pipeline().parameters.Data_WorkspaceGuid)")

failures = 0


def check(ok, text):
    global failures
    print(("  ok     " if ok else "  FOUT   ") + text)
    failures += 0 if ok else 1


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)


for name in ("PL_FMD_LOAD_ALL", "PL_FMD_LOAD_LANDINGZONE", "PL_FMD_LOAD_BRONZE", "PL_FMD_LOAD_SILVER"):
    properties = json.loads((REPO / f"src/{name}.DataPipeline/pipeline-content.json").read_text(encoding="utf-8"))["properties"]
    uses = [s for s in strings(properties["activities"]) if PARAMETER in s]
    check(properties["parameters"].get("Data_WorkspaceGuid") == {"type": "string", "defaultValue": ""}, f"{name}: parameter default empty")
    check(uses and all(PARAMETER not in s.replace(FALLBACK, "") for s in uses), f"{name}: all {len(uses)} uses fall back to the library variable")
    check(properties.get("libraryVariables", {}).get("VAR_CONFIG_FMD_fmd_data_workspace_guid", {}).get("variableName") == "fmd_data_workspace_guid",
          f"{name}: library variable declared")

print("\nALLES OK" if not failures else f"\n{failures} FOUT(EN)")
sys.exit(1 if failures else 0)
