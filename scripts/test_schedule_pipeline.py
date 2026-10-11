"""Check op create_schedule_pipeline (NB_UTILITIES_SETUP_FMD). Geen dependencies, geen netwerk.

    python3 scripts/test_schedule_pipeline.py

De twee functies worden echt uit het notebook gehaald en uitgevoerd met stubs voor Fabric. Gecontroleerd:
  1. de definitie: een Switch op Target, LOAD -> orchestratie met LoadGroup, MAINTENANCE -> maintenance,
     alles anders -> Fail, met de IDs en de connectie die erin gaan;
  2. een bestaande pipeline wordt niet overschreven (geen POST);
  3. een nieuwe pipeline gaat in de CONFIG-workspace en in de map SchedulePipelines;
  4. een mislukte aanmaak of een niet te vinden ID geeft een status die met "failed" begint.
"""

import base64
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # de functies printen een vinkje; de Windows-console is cp1252
REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
source = (REPO / "src/NB_UTILITIES_SETUP_FMD.Notebook/notebook-content.py").read_text(encoding="utf-8")
start = source.index("SCHEDULE_PIPELINE_FOLDER = ")
end = source.index("def set_variable_library_stage_values(")

CONFIG_WS, CODE_WS = "CONFIG WS", "CODE WS (D)"
IDS = {CONFIG_WS: "cfg-ws-id", CODE_WS: "code-ws-id"}
ITEMS = {"PL_FMD_ORCHESTRATION_TEMPLATE.DataPipeline": "orch-id", "PL_FMD_MAINTENANCE.DataPipeline": "maint-id"}
CONNECTION = "conn-id"

calls = {"post": [], "folder": []}
state = {"exists": False, "post_status": 201, "orchestration_id": "orch-id"}


class Response:
    def __init__(self, status_code=200, body=None):
        self.status_code, self._body, self.text = status_code, body or {}, "x"

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def run_fab_command(command, capture_output=False, silently_continue=False, raw_output=False):
    return "* true" if state["exists"] else "* false"


def get_item_id(workspace, item, prop):
    if workspace == CODE_WS and item == "PL_FMD_ORCHESTRATION_TEMPLATE.DataPipeline":
        return state["orchestration_id"]
    return ITEMS.get(item) or "created-id"


def invoke_fabric_api_request(method, path, payload=None):
    content = {"properties": {"activities": [{"externalReferences": {"connection": CONNECTION}}]}}
    part = {"path": "pipeline-content.json", "payload": base64.b64encode(json.dumps(content).encode()).decode()}
    return Response(200, {"definition": {"parts": [part]}})


def invoke_fabric_request(method, url, payload=None):
    calls["post"].append((url, payload))
    return Response(state["post_status"])


scope = {
    "json": json, "base64": base64, "FABRIC_API_BASE_URL": "https://fabric/v1/",
    "run_fab_command": run_fab_command, "get_item_id": get_item_id,
    "get_workspace_id_by_name": IDS.get,
    "invoke_fabric_api_request": invoke_fabric_api_request, "invoke_fabric_request": invoke_fabric_request,
    "assign_item_to_folder": lambda ws, item_id, folder: calls["folder"].append((ws, item_id, folder)),
}
exec(compile(source[start:end], "NB_UTILITIES_SETUP_FMD:schedule", "exec"), scope)

failures = 0


def check(ok, text):
    global failures
    print(("  ok     " if ok else "  FOUT   ") + text)
    failures += 0 if ok else 1


print("=== definitie ===")
definition = scope["schedule_pipeline_definition"]("code-ws-id", "orch-id", "maint-id", CONNECTION)["properties"]
switch = definition["activities"][0]
cases = {c["value"]: c["activities"][0] for c in switch["typeProperties"]["cases"]}
load, maintenance = cases["LOAD"], cases["MAINTENANCE"]
default = switch["typeProperties"]["defaultActivities"][0]
check(switch["type"] == "Switch" and switch["typeProperties"]["on"]["value"] == "@pipeline().parameters.Target", "Switch op Target")
check(set(cases) == {"LOAD", "MAINTENANCE"}, "precies twee cases: LOAD en MAINTENANCE")
check((load["typeProperties"]["workspaceId"], load["typeProperties"]["pipelineId"]) == ("code-ws-id", "orch-id"), "LOAD: orchestratie in CODE")
check(load["typeProperties"]["parameters"]["LoadGroup"]["value"] == "@pipeline().parameters.LoadGroup", "LOAD: LoadGroup gaat mee")
check((maintenance["typeProperties"]["workspaceId"], maintenance["typeProperties"]["pipelineId"]) == ("code-ws-id", "maint-id"), "MAINTENANCE: maintenance in CODE")
check(all(a["typeProperties"]["waitOnCompletion"] and a["externalReferences"]["connection"] == CONNECTION for a in (load, maintenance)),
      "beide wachten op het resultaat, met de connectie van de orchestratie")
check(default["type"] == "Fail" and default["typeProperties"]["errorCode"] == "UnknownTarget", "onbekende Target faalt")
check(definition["parameters"]["Target"]["defaultValue"] == "LOAD" and definition["parameters"]["LoadGroup"]["defaultValue"] == "", "defaults: LOAD en leeg")
check(definition["concurrency"] == 1, "concurrency 1: twee runs van dezelfde omgeving lopen niet door elkaar")

print("=== bestaande pipeline blijft staan ===")
state["exists"] = True
status = scope["create_schedule_pipeline"](CONFIG_WS, CODE_WS, "D")
check(status.startswith("already exists") and not calls["post"], "geen POST, status zegt dat hij bestaat")

print("=== nieuwe pipeline ===")
state["exists"] = False
status = scope["create_schedule_pipeline"](CONFIG_WS, CODE_WS, "T")
url, payload = calls["post"][0]
created = json.loads(base64.b64decode(payload["definition"]["parts"][0]["payload"]))["properties"]
check(status == "success", "status success")
check(url == "https://fabric/v1/workspaces/cfg-ws-id/items", "POST naar de CONFIG-workspace")
check(payload["displayName"] == "PL_FMD_SCHEDULE_T" and payload["type"] == "DataPipeline", "naam PL_FMD_SCHEDULE_<short>")
check(created == definition, "inhoud is de definitie van hierboven")
check(calls["folder"] == [(CONFIG_WS, "created-id", "SchedulePipelines")], "in de map SchedulePipelines")

print("=== fouten ===")
state["post_status"] = 400
check(scope["create_schedule_pipeline"](CONFIG_WS, CODE_WS, "P").startswith("failed"), "mislukte aanmaak geeft failed")
state["post_status"], state["orchestration_id"] = 201, ""
check(scope["create_schedule_pipeline"](CONFIG_WS, CODE_WS, "P").startswith("failed"), "ontbrekende orchestratie geeft failed")

print("\nALLES OK" if not failures else f"\n{failures} FOUT(EN)")
sys.exit(1 if failures else 0)
