"""Check op replace_ids_and_mark_inactive (NB_UTILITIES_SETUP_FMD). Geen dependencies, geen netwerk.

    python3 scripts/test_id_mapping.py

Bij twee business domains mappen beide domeinen dezelfde template-ID's (de notebooks en de workspace-
placeholder 0000...). Gecontroleerd: de Gold-pipeline van elk domein krijgt de ID's van zijn eigen
CODE-workspace, ook als een ander domein eerder in de mapping-tabel staat.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
source = (REPO / "src/NB_UTILITIES_SETUP_FMD.Notebook/notebook-content.py").read_text(encoding="utf-8")
start = source.index("def replace_ids_and_mark_inactive(")
end = source.index("# Description and Identity Assignment")
exec(source[start:end])

PLACEHOLDER = "00000000-0000-0000-0000-000000000000"
NB_LOAD_GOLD, NB_MLV = "8b6fabb1-f9a2-af87-4260-23061c74f547", "7f3419e4-1e18-9166-43d1-de9529d88dc3"
pipeline = {"properties": {"activities": [
    {"name": "NB_LOAD_GOLD", "type": "TridentNotebook", "typeProperties": {"notebookId": NB_LOAD_GOLD, "workspaceId": PLACEHOLDER}},
    {"name": "NB_MLV_EXAMPLE", "type": "TridentNotebook", "typeProperties": {"notebookId": NB_MLV, "workspaceId": PLACEHOLDER}},
]}}

mapping_table = [{"Description": "SQL", "environment": "config", "ItemType": "SQLDatabase", "old_id": "db-old", "new_id": "db-new"}]
for domain in ("FINANCE", "SALES"):  # same order as deploy_workspaces, then deploy_item, in NB_SETUP_BUSINESS_DOMAINS
    for kind in ("CODE", "DATA"):
        ws = f"{domain} {kind} (D)"
        mapping_table.append({"Description": ws, "environment": "development", "ItemType": "Workspace",
                              "old_id": PLACEHOLDER, "new_id": f"{ws}-id", "workspace": ws})
for domain in ("FINANCE", "SALES"):
    ws = f"{domain} CODE (D)"
    for name, old in (("NB_LOAD_GOLD", NB_LOAD_GOLD), ("NB_MLV_EXAMPLE", NB_MLV)):
        mapping_table.append({"Description": name, "environment": "development", "ItemType": "Notebook",
                              "old_id": old, "new_id": f"{domain}-{name}", "workspace": ws})


def deploy(workspace_name):
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "pipeline-content.json")
        Path(path).write_text(json.dumps(pipeline), encoding="utf-8")
        replace_ids_and_mark_inactive(folder, mapping_table, "development", [], workspace_name)
        return [a["typeProperties"] for a in json.loads(Path(path).read_text(encoding="utf-8"))["properties"]["activities"]]


for domain in ("FINANCE", "SALES"):
    ws = f"{domain} CODE (D)"
    got = deploy(ws)
    assert got == [{"notebookId": f"{domain}-NB_LOAD_GOLD", "workspaceId": f"{ws}-id"},
                   {"notebookId": f"{domain}-NB_MLV_EXAMPLE", "workspaceId": f"{ws}-id"}], (domain, got)

print("OK: elke Gold-pipeline wijst naar de notebooks en de workspace van zijn eigen domein")
