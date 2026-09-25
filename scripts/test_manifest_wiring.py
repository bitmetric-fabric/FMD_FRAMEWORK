"""Check op de manifest-bedrading (PR 3). Geen dependencies, geen netwerk.

    python3 scripts/test_manifest_wiring.py

Twee dingen:
  1. manifest.example.yaml reproduceert de configuratie van voor PR 3, door de
     manifest- en configuratiecellen van beide setup-notebooks echt uit te voeren.
  2. apply_spark_settings en apply_value_sets doen wat ze beloven op kopieen van
     de echte bestanden - inclusief het behouden van sleutels, commentaar en
     regeleindes die het manifest niet noemt.
"""

import json
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
EXAMPLE = (REPO / "manifest.example.yaml").read_text(encoding="utf-8")

# --- stub voor requests --------------------------------------------------
class _Response:
    status_code = 200
    text = EXAMPLE

    def raise_for_status(self):
        pass


fake_requests = types.ModuleType("requests")
fake_requests.get = lambda url, *a, **k: _Response()
sys.modules["requests"] = fake_requests


def cells_of(path):
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return {c.get("id"): "".join(c["source"]) for c in notebook["cells"]}, notebook["cells"]


def compile_all(cells, name):
    bad = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        if source.lstrip().startswith(("%", "!")) or "\n%" in source:
            continue  # magics: geen geldige Python
        try:
            compile(source, f"{name}:{cell.get('id')}", "exec")
        except SyntaxError as exc:
            print(f"  SYNTAXFOUT {name} cel {cell.get('id')}: {exc}")
            bad += 1
    return bad


def run(path, cell_ids):
    sources, cells = cells_of(path)
    errors = compile_all(cells, path.name)
    scope = {}
    for cell_id in cell_ids:
        exec(compile(sources[cell_id], f"{path.name}:{cell_id}", "exec"), scope)
    return scope, errors


print("=== compileren + uitvoeren ===")

fmd, e1 = run(
    REPO / "setup" / "NB_SETUP_FMD.ipynb",
    [
        "fmd-manifest-bootstrap",
        "afbf0bf0-89ce-4eb9-bdc3-8efd8444ea4c",
        "c6095d96-c13d-49fd-b388-7347598d2032",
        "c5e6f777-a65a-491b-ba14-0ce8b19c04ff",
        "99ab87f1-553e-426f-9c42-1f2232cd5e8f",
        "3ada47fa-6823-4cdc-bebe-3f573f4f2bd1",
        "40ebe458-bd01-495a-81a1-6b7b5aef9ec8",
    ],
)

bd, e2 = run(
    REPO / "setup" / "NB_SETUP_BUSINESS_DOMAINS.ipynb",
    [
        "bd-manifest-bootstrap",
        "afbf0bf0-89ce-4eb9-bdc3-8efd8444ea4c",
        "2086f732-b219-4101-9eab-92c95044c075",
        "c6095d96-c13d-49fd-b388-7347598d2032",
        "c5e6f777-a65a-491b-ba14-0ce8b19c04ff",
        "99ab87f1-553e-426f-9c42-1f2232cd5e8f",
        "60ded5a6-4998-4f43-a7aa-5a9c26dad6a1",
    ],
)

print(f"  syntaxfouten: {e1 + e2}")

# --- verwachte waarden van VOOR PR 3 -------------------------------------
CAP = "<your capacity name>"
expected = []


def check(label, got, want):
    expected.append((label, got == want, got, want))


check("FMD domain_name", fmd["domain_name"], "INTEGRATION")
check("FMD framework_post_fix", fmd["framework_post_fix"], "")
check("FMD lakehouse_schema_enabled", fmd["lakehouse_schema_enabled"], True)
check("FMD spark_version", fmd["spark_version"], "2.0")
check("FMD capacity_name_config", fmd["capacity_name_config"], CAP)
check("FMD key_vault", fmd["key_vault"], "<your key vault name>")
check("FMD sp_tenant_id", fmd["fabric_sql_sp_tenant_id"], "tenantid")
check("FMD sp_client_id", fmd["fabric_sql_sp_client_id"], "sp-fmd-fabric-pipelines-app-id")
check("FMD sp_secret", fmd["fabric_sql_sp_secret"], "sp-fmd-fabric-pipelines-secret")

check(
    "FMD environments (namen/capaciteit)",
    [
        (e["environment_name"], e["workspaces"]["data"]["name"], e["workspaces"]["code"]["name"],
         e["workspaces"]["data"]["capacity_name"])
        for e in fmd["environments"]
    ],
    [
        ("development", "INTEGRATION DATA (D)", "INTEGRATION CODE (D)", CAP),
        ("test", "INTEGRATION DATA (T)", "INTEGRATION CODE (T)", CAP),
        ("production", "INTEGRATION DATA", "INTEGRATION CODE", CAP),
    ],
)

check(
    "FMD configuration",
    (fmd["configuration"]["workspace"]["name"], fmd["configuration"]["DatabaseName"],
     fmd["configuration"]["workspace"]["capacity_name"]),
    ("INTEGRATION CONFIG", "SQL_INTEGRATION_FRAMEWORK", CAP),
)

# Nul-ID's in het voorbeeldmanifest -> lege rollijsten (voorheen: lijsten met
# nul-GUID's waar fab acl set stil op faalde).
check("FMD workspace_roles_code", fmd["workspace_roles_code"], [])
check("FMD workspace_roles_data", fmd["workspace_roles_data"], [])
check("FMD domain_contributor_role principals", fmd["domain_contributor_role"]["principals"], [])
check("FMD connection_role principals", fmd["connection_role"]["principals"], [])

check("BD business_domain_names", bd["business_domain_names"], ["FINANCE", "SALES"])
check("BD SourceSchema uit manifest", bd["SourceSchema"], "")
check("BD Shortcut_TargetSchema uit manifest", bd["Shortcut_TargetSchema"], "")
check("BD configuration_database_workspace", bd["configuration_database_workspace"], "INTEGRATION CONFIG")
check("BD configuration_database_name", bd["configuration_database_name"], "SQL_INTEGRATION_FRAMEWORK")
check(
    "BD business_domain_deployment",
    [(e["environment_name"], e["environment_short"], sorted(e["workspaces"]),
      e["workspaces"]["data"]["capacity_name"]) for e in bd["business_domain_deployment"]],
    [
        ("development", "D", ["code", "data", "reporting", "semantic"], CAP),
        ("test", "T", ["code", "data", "reporting", "semantic"], CAP),
        ("production", "P", ["code", "data", "reporting", "semantic"], CAP),
    ],
)

# D3: zodra capacity_business_domain wel is ingevuld, moet hij die pakken.
# In place muteren, want require() sluit over de globals van zijn eigen cel.
bd_sources, _ = cells_of(REPO / "setup" / "NB_SETUP_BUSINESS_DOMAINS.ipynb")
bd_environments_cell = bd_sources["60ded5a6-4998-4f43-a7aa-5a9c26dad6a1"]
for env in bd["manifest"]["environments"]:
    env["capacity_business_domain"] = f"GOLD-{env['short']}"
exec(compile(bd_environments_cell, "bd-env", "exec"), bd)
check(
    "BD capaciteit volgt capacity_business_domain",
    [e["workspaces"]["data"]["capacity_name"] for e in bd["business_domain_deployment"]],
    ["GOLD-D", "GOLD-T", "GOLD-P"],
)

# Workspacenamen: Production krijgt geen omgevingsmarker, Dev/Test wel
# (ws_suffix in de manifest-bootstrap-cel). Cel 330d211a-... roept
# deploy_workspaces aan; we vervangen die door iets dat alleen de naam
# vastlegt, zodat we de echte celtekst testen zonder Fabric te benaderen.
captured_names = []
ws_names_scope = dict(bd)
ws_names_scope["deploy_workspaces"] = (
    lambda business_domain_name, workspace, workspace_name, **kw: captured_names.append(workspace_name)
)
ws_names_scope["create_fabric_domain"] = lambda name: None
ws_names_scope["config"] = {"workspaces": {
    "workspace_business_domain_code": None,
    "workspace_business_domain_data": None,
    "workspace_business_domain_reporting": None,
}}
ws_names_scope["mapping_table"] = []
ws_names_scope["tasks"] = []
exec(compile(bd_sources["330d211a-1b1e-44b2-b989-93e751d5612c"], "bd-ws-names", "exec"), ws_names_scope)
check(
    "BD workspacenamen (CODE/DATA/REPORTING/SEMANTIC per D/T/production)",
    captured_names,
    [
        "FINANCE CODE (D)", "FINANCE DATA (D)", "FINANCE REPORTING (D)", "FINANCE SEMANTIC (D)",
        "FINANCE CODE (T)", "FINANCE DATA (T)", "FINANCE REPORTING (T)", "FINANCE SEMANTIC (T)",
        "FINANCE CODE", "FINANCE DATA", "FINANCE REPORTING", "FINANCE SEMANTIC",
        "SALES CODE (D)", "SALES DATA (D)", "SALES REPORTING (D)", "SALES SEMANTIC (D)",
        "SALES CODE (T)", "SALES DATA (T)", "SALES REPORTING (T)", "SALES SEMANTIC (T)",
        "SALES CODE", "SALES DATA", "SALES REPORTING", "SALES SEMANTIC",
    ],
)

# Cel e117937f bouwt de deployment-pipeline-stage-namen op met een andere
# expressievorm (" " + group.upper() + ws_suffix(...)) - apart getest zodat
# er geen dubbele of ontbrekende spatie sluipt in de production-naam.
pipeline_names_scope = dict(bd)
captured_pipelines = []
pipeline_names_scope["deploy_deployment_pipeline"] = (
    lambda pipeline_name, stage_workspace_names: captured_pipelines.append(
        (pipeline_name, stage_workspace_names))
)
exec(compile(bd_sources["e117937f"], "bd-pipeline-names", "exec"), pipeline_names_scope)
check(
    "BD deployment-pipeline-stagenamen (CODE-groep, FINANCE)",
    next(names for pname, names in captured_pipelines if pname == "FINANCE CODE"),
    [
        ("Development", "FINANCE CODE (D)"),
        ("Test", "FINANCE CODE (T)"),
        ("Production", "FINANCE CODE"),
    ],
)

print("\n=== vergelijking met de defaults van voor PR 3 ===")
failed = 0
for label, ok, got, want in expected:
    if ok:
        print(f"  OK   {label}")
    else:
        failed += 1
        print(f"  FOUT {label}\n         nu:  {got!r}\n         was: {want!r}")

# --- rollen met echte ID's -----------------------------------------------
print("\n=== rollen met ingevulde ID's (simulatie) ===")
role_scope = dict(fmd)
role_scope["manifest"]["security"] = {
    "admin_group_id": "11111111-1111-1111-1111-111111111111",
    "contributor_group_id": "22222222-2222-2222-2222-222222222222",
    "service_principal_id": "33333333-3333-3333-3333-333333333333",
}
sources, _ = cells_of(REPO / "setup" / "NB_SETUP_FMD.ipynb")
exec(compile(sources["99ab87f1-553e-426f-9c42-1f2232cd5e8f"], "roles", "exec"), role_scope)
for name in ("workspace_roles_code", "workspace_roles_data"):
    print(f"  {name}:")
    for role in role_scope[name]:
        print(f"    {role['principal']['type']:<16} {role['role']:<12} {role['principal']['id']}")

print(f"\nresultaat: {failed} afwijking(en), {e1 + e2} syntaxfout(en)")
NOTEBOOK_FAILURES = failed + e1 + e2


# --- de twee functies uit het notebook halen -----------------------------
utilities_source = (REPO / "src/NB_UTILITIES_SETUP_FMD.Notebook/notebook-content.py").read_text(encoding="utf-8")
start = utilities_source.index("def apply_spark_settings(")
end = utilities_source.index("# -------------------------------\n# Item deployment")
scope = {"os": os, "json": json}

MANIFEST = {
    "spark": {
        "runtime_version": "2.0",
        "default": {"driver_cores": 4, "driver_memory": "28g",
                    "executor_cores": 4, "executor_memory": "28g"},
    },
    "environments": [{"name": "Development"}, {"name": "Test"}, {"name": "Production"}],
}


def _lookup(path):
    node = MANIFEST
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


scope["require"] = lambda p: _lookup(p)[0]
scope["optional"] = lambda p, d=None: _lookup(p)[0] if _lookup(p)[1] else d
exec(compile(utilities_source[start:end], "hooks", "exec"), scope)

failures = []


def check(label, condition, detail=""):
    print(("  OK   " if condition else "  FOUT ") + label + ("" if condition else f"  {detail}"))
    if not condition:
        failures.append(label)


# --- Sparkcompute ---------------------------------------------------------
print("=== apply_spark_settings ===")
original = (REPO / "src/ENV_FMD.Environment/Setting/Sparkcompute.yml").read_bytes()

for environment, expected_driver in (("config", "4"),):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "Setting").mkdir()
    (tmp / "Setting/Sparkcompute.yml").write_bytes(original)

    scope["apply_spark_settings"](str(tmp))
    result = (tmp / "Setting/Sparkcompute.yml").read_bytes().decode("utf-8")

    check(f"[{environment}] driver_cores = {expected_driver}",
          f"driver_cores: {expected_driver}\r\n" in result or f"driver_cores: {expected_driver}\n" in result,
          result)
    check(f"[{environment}] onbekende sleutels behouden",
          "enable_native_execution_engine: true" in result
          and "dynamic_executor_allocation:" in result
          and "max_executors: 2" in result)
    check(f"[{environment}] commentaar behouden", result.count("#") >= 4)
    check(f"[{environment}] CRLF behouden", "\r\n" in result)
    check(f"[{environment}] geen dubbele sleutels",
          all(sum(1 for line in result.splitlines() if line.startswith(key + ":")) == 1
              for key in ("driver_cores", "driver_memory", "executor_cores",
                          "executor_memory", "runtime_version")))
    shutil.rmtree(tmp, ignore_errors=True)

# alles wat het manifest niet noemt blijft staan, byte voor byte
tmp = Path(tempfile.mkdtemp())
(tmp / "Setting").mkdir()
(tmp / "Setting/Sparkcompute.yml").write_bytes(original)
scope["apply_spark_settings"](str(tmp))
after_bytes = (tmp / "Setting/Sparkcompute.yml").read_bytes()
untouched = [line for line in original.decode("utf-8").splitlines()
             if not line.split(":", 1)[0].strip() in
             ("driver_cores", "driver_memory", "executor_cores", "executor_memory", "runtime_version")]
check("regels buiten het manifest ongewijzigd",
      all(line in after_bytes.decode("utf-8") for line in untouched))
shutil.rmtree(tmp, ignore_errors=True)

# ontbrekend bestand mag niet crashen
tmp = Path(tempfile.mkdtemp())
scope["apply_spark_settings"](str(tmp))
check("ontbrekende Sparkcompute.yml wordt overgeslagen", True)
shutil.rmtree(tmp, ignore_errors=True)

# --- valueSets ------------------------------------------------------------
print("\n=== apply_value_sets ===")
library = REPO / "src/VAR_FMD.VariableLibrary"
tmp = Path(tempfile.mkdtemp()) / "lib"
shutil.copytree(library, tmp)

before = sorted(p.stem for p in (tmp / "valueSets").glob("*.json"))
scope["apply_value_sets"](str(tmp))
after = sorted(p.stem for p in (tmp / "valueSets").glob("*.json"))
order = json.loads((tmp / "settings.json").read_text(encoding="utf-8"))["valueSetsOrder"]

check("vier value sets in src/", before == ["Acceptance", "Development", "Production", "Test"], before)
check("Acceptance verwijderd (niet in manifest)", after == ["Development", "Production", "Test"], after)
check("valueSetsOrder volgt manifest", order == ["Development", "Test", "Production"], order)
shutil.rmtree(tmp.parent, ignore_errors=True)

# met Acceptance erbij moet hij blijven staan
MANIFEST["environments"].insert(2, {"name": "Acceptance"})
tmp = Path(tempfile.mkdtemp()) / "lib"
shutil.copytree(library, tmp)
scope["apply_value_sets"](str(tmp))
after = sorted(p.stem for p in (tmp / "valueSets").glob("*.json"))
check("DTAP behoudt Acceptance", after == ["Acceptance", "Development", "Production", "Test"], after)
shutil.rmtree(tmp.parent, ignore_errors=True)


# --- D6: VAR_GOLD_SHORTCUTS_FMD kan weer gedeployed worden ----------------
print("\n=== update_variable_library / VAR_GOLD_SHORTCUTS_FMD ===")

declared = next(
    item for item in json.loads(
        (REPO / "config/item_deployment_code_business_domain.json").read_text(encoding="utf-8"))
    if item["name"].startswith("VAR_GOLD_SHORTCUTS")
)["variables"]

uvl_start = utilities_source.index("def update_variable_library(")
uvl_end = utilities_source.index("def copy_to_tmp(")
uvl_source = utilities_source[uvl_start:uvl_end]


def run_update(parameters):
    """Draait update_variable_library op een kopie van de echte library."""
    library = Path(tempfile.mkdtemp()) / "lib"
    shutil.copytree(REPO / "src/business_domain/VAR_GOLD_SHORTCUTS_FMD.VariableLibrary", library)
    uvl_scope = {"json": json, "variable_parameters": parameters}
    exec(compile(uvl_source, "uvl", "exec"), uvl_scope)
    uvl_scope["update_variable_library"](str(library), declared)
    written = json.loads((library / "variables.json").read_text(encoding="utf-8"))
    shutil.rmtree(library.parent, ignore_errors=True)
    return written


# zoals NB_UTILITIES variable_parameters aanmaakt, voordat de herstelcel draait
base_parameters = {
    "key_vault_uri_name": "val_key_vault_uri_name",
    "lakehouse_schema_enabled": True,
    "purview_account_name": "val_purview_account_name",
}

try:
    run_update(dict(base_parameters))
    check("zonder de herstelcel faalt het deployen", False, "er ging niets mis")
except KeyError as exc:
    check("zonder de herstelcel faalt het deployen, met bruikbare melding",
          "SourceWorkspaceId" in str(exc) and "variable_parameters" in str(exc), str(exc))

restored = dict(base_parameters)
restore_scope = dict(bd)
restore_scope["variable_parameters"] = restored
exec(compile(bd_sources["bd-variable-parameters"], "vp", "exec"), restore_scope)

check("herstelcel vult precies de zes gedeclareerde bronnen",
      sorted(k for k in restored if k not in base_parameters),
      sorted(v["source"] for v in declared))

written = run_update(restored)
check("library houdt zes variabelen",
      [v["name"] for v in written["variables"]],
      [v["name"] for v in declared])
check("schema komt uit het manifest",
      [v["value"] for v in written["variables"] if v["name"] == "SourceSchema"],
      [bd["manifest"]["shortcuts"]["source_schema"]])
check("ID's blijven leeg tot de auto-fill ze invult",
      [v["value"] for v in written["variables"]
       if v["name"] in ("SourceWorkspaceId", "SourceLakehouseId",
                        "Shortcut_TargetWorkspaceId", "Shortcut_TargetLakehouseId")],
      ["", "", "", ""])

# --- waarden per omgeving als value set (promotie-bestendig) -----------------
# Een default die per omgeving verschilt, overleeft een deployment-pipeline-promotie
# niet: de deploy overschrijft hem met de waarde van de bronstage (getest 2026-09-25).
print("\n=== stage_value_overrides ===")


def library_parts(folder):
    return {p.relative_to(folder).as_posix(): json.loads(p.read_text(encoding="utf-8"))
            for p in folder.rglob("*.json")}


def overrides(parts, stage):
    return parts[f"valueSets/{stage}.json"]["variableOverrides"]


source_parts = library_parts(REPO / "src/VAR_CONFIG_FMD.VariableLibrary")
parts = library_parts(REPO / "src/VAR_CONFIG_FMD.VariableLibrary")
parts["valueSets/Test.json"]["variableOverrides"] = [{"name": "fmd_fabric_db_name", "value": "ANDERS"}]
stage_values = {
    "Development": {"fmd_data_workspace_guid": "dev-ws", "fmd_landingzone_lakehouse_guid": "dev-lh"},
    "Test": {"fmd_data_workspace_guid": "tst-ws", "fmd_landingzone_lakehouse_guid": "tst-lh"},
    "Production": {"fmd_data_workspace_guid": "prd-ws", "fmd_landingzone_lakehouse_guid": "dev-lh"},
}
scope["stage_value_overrides"](parts, stage_values)
defaults = {v["name"]: v["value"] for v in parts["variables.json"]["variables"]}
source_defaults = {v["name"]: v["value"] for v in source_parts["variables.json"]["variables"]}

check("eerste omgeving wordt de default",
      (defaults["fmd_data_workspace_guid"], defaults["fmd_landingzone_lakehouse_guid"]) == ("dev-ws", "dev-lh"),
      defaults)
check("andere variabelen houden hun default",
      all(defaults[k] == v for k, v in source_defaults.items()
          if k not in ("fmd_data_workspace_guid", "fmd_landingzone_lakehouse_guid")))
check("Development krijgt geen overrides", overrides(parts, "Development") == [], overrides(parts, "Development"))
check("Test krijgt zijn eigen waarden als override",
      [o for o in overrides(parts, "Test") if o["name"] != "fmd_fabric_db_name"]
      == [{"name": "fmd_data_workspace_guid", "value": "tst-ws"},
          {"name": "fmd_landingzone_lakehouse_guid", "value": "tst-lh"}],
      overrides(parts, "Test"))
check("bestaande override op een andere variabele blijft staan",
      {"name": "fmd_fabric_db_name", "value": "ANDERS"} in overrides(parts, "Test"), overrides(parts, "Test"))
check("geen override die gelijk is aan de default (die zou hem vastpinnen)",
      overrides(parts, "Production") == [{"name": "fmd_data_workspace_guid", "value": "prd-ws"}],
      overrides(parts, "Production"))

snapshot = json.dumps(parts, sort_keys=True)
scope["stage_value_overrides"](parts, stage_values)
check("opnieuw draaien verandert niets", json.dumps(parts, sort_keys=True) == snapshot)

del parts["valueSets/Test.json"]
scope["stage_value_overrides"](parts, stage_values)
check("ontbrekende value set wordt aangemaakt",
      parts["valueSets/Test.json"]["name"] == "Test" and len(overrides(parts, "Test")) == 2,
      parts.get("valueSets/Test.json"))

# --- de twee setupcellen roepen het aan met de juiste omgevingen en waarden ---
print("\n=== setupcellen: waarden per omgeving ===")
stage_calls = []


def record(library, stages, values):
    stage_calls.append((library, stages, values))


gold_scope = dict(bd)
gold_scope.update({
    "get_workspace_id_by_name": lambda name: None if name == "SALES DATA" else f"ws:{name}",
    "get_item_id": lambda workspace, name, prop: f"id:{workspace}/{name}",
    "set_variable_library_stage_values": record,
})
exec(compile(bd_sources["123a5aa6"], "bd-gold-autofill", "exec"), gold_scope)
finance = next(c for c in stage_calls if c[1][0][1] == "FINANCE CODE (D)")
sales = next(c for c in stage_calls if c[1][0][1] == "SALES CODE (D)")
check("VAR_GOLD_SHORTCUTS_FMD: één aanroep per domein", len(stage_calls) == 2, stage_calls)
check("FINANCE: stages in manifestvolgorde met hun CODE-workspace",
      finance[1] == [("Development", "FINANCE CODE (D)"), ("Test", "FINANCE CODE (T)"),
                     ("Production", "FINANCE CODE")],
      finance[1])
check("FINANCE Test wijst naar de Test-Gold en de Test-Silver",
      finance[2]["Test"] == {
          "SourceWorkspaceId": "ws:FINANCE DATA (T)",
          "SourceLakehouseId": "id:FINANCE DATA (T)/LH_GOLD_LAYER.Lakehouse",
          "Shortcut_TargetWorkspaceId": "ws:INTEGRATION DATA (T)",
          "Shortcut_TargetLakehouseId": "id:INTEGRATION DATA (T)/LH_SILVER_LAYER.Lakehouse"},
      finance[2]["Test"])
check("niet op te zoeken omgeving krijgt lege ID's, geen Dev-waarden",
      sales[2]["Production"]["SourceWorkspaceId"] == "", sales[2]["Production"])

stage_calls.clear()
fmd_sources, _ = cells_of(REPO / "setup" / "NB_SETUP_FMD.ipynb")
config_scope = dict(fmd)
config_scope.update({
    "item_deployment": [], "variable_parameters": {}, "mapping_table": [], "tasks": [],
    "deploy_item": lambda *a, **k: None,
    "get_workspace_id_by_name": lambda name: f"ws:{name}",
    "get_item_id": lambda workspace, name, prop: f"id:{workspace}/{name}",
    "set_variable_library_stage_values": record,
})
exec(compile(fmd_sources["9dbaf8ad-721a-46c3-8c2c-1ea9a48dc1a3"], "fmd-var-config", "exec"), config_scope)
check("VAR_CONFIG_FMD: één aanroep", len(stage_calls) == 1 and stage_calls[0][0] == "VAR_CONFIG_FMD", stage_calls)
check("VAR_CONFIG_FMD: Production wijst naar de Production-DATA-workspace",
      stage_calls[0][2]["Production"] == {
          "fmd_data_workspace_guid": "ws:INTEGRATION DATA",
          "fmd_landingzone_lakehouse_guid": "id:INTEGRATION DATA/LH_DATA_LANDINGZONE.Lakehouse"},
      stage_calls[0][2]["Production"])

print(f"\nresultaat: {len(failures)} fout(en)")
sys.exit(1 if (failures or NOTEBOOK_FAILURES) else 0)
