# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "",
# META       "default_lakehouse_workspace_id": ""
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Notebook to create shortcuts in Gold
# 
# Don't forget to change the parameters in the **VAR_GOLD_SHORTCUTS_FMD** library
#
# With an empty **ShortcutNames** the notebook creates one schema shortcut per Silver schema (except `dbo`),
# with the same name in Gold. Tables added to Silver later show up in Gold without a new run;
# only a new Silver schema needs one. A Gold schema with the same name as a Silver schema must not exist yet.
#
# Fill **ShortcutNames** only for lakehouses without schemas, or to shortcut a selection of tables.
#
# More details: https://github.com/edkreuk/FMD_FRAMEWORK


# CELL ********************

import json, requests
import notebookutils 

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

#Shortcut location parameters

# Empty: one schema shortcut per Silver schema (see above).
# Otherwise each entry is a table name (uses SourceSchema / Shortcut_TargetSchema) or a (schema, table) pair.
# A pair uses that schema in both Gold and Silver, for sources that land in several Silver schemas.
ShortcutNames=[]         #Tablenames of the to be created shortcuts, same name will be used for destination

ShortcutSettings=notebookutils.variableLibrary.getLibrary("VAR_GOLD_SHORTCUTS_FMD")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def create_shortcut(path:str, name:str, target:dict, workspace_id:str ,lakehouse_id:str ,conflict_policy:str="Abort"):

    # Get Token
    token = notebookutils.credentials.getToken("pbi")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "path": path,    # e.g., "Files/raw" OR "Tables"
        "name": name,    # e.g., "sales_external"
        "target": target # see examples below
    }

    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{lakehouse_id}/shortcuts"
    params = {"shortcutConflictPolicy": conflict_policy}

    resp = requests.post(url, headers=headers, params=params, data=json.dumps(body))
    if resp.status_code in (200, 201):
        print(f"Shortcut '{name}' created at '{path}'.")
        print("Location:", resp.headers.get("Location", "<none>"))
    else:
        print("Failed:", resp.status_code, resp.text)
    return resp.status_code in (200, 201)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

failed = []
if not ShortcutNames:
    silver_tables = f"abfss://{ShortcutSettings.Shortcut_TargetWorkspaceId}@onelake.dfs.fabric.microsoft.com/{ShortcutSettings.Shortcut_TargetLakehouseId}/Tables"
    schemas = [f.name.rstrip("/") for f in notebookutils.fs.ls(silver_tables) if f.isDir and f.name.rstrip("/") != "dbo"]
    if not schemas:
        raise RuntimeError(f"No Silver schemas found under {silver_tables}; for a lakehouse without schemas, fill ShortcutNames")
    for schema in schemas:
        oneLake_target = {"oneLake": {"workspaceId": ShortcutSettings.Shortcut_TargetWorkspaceId, "itemId": ShortcutSettings.Shortcut_TargetLakehouseId, "path": "Tables/"+schema}}
        if not create_shortcut(path="Tables", name=schema, target=oneLake_target, workspace_id=ShortcutSettings.SourceWorkspaceId, lakehouse_id=ShortcutSettings.SourceLakehouseId, conflict_policy="CreateOrOverwrite"):
            failed.append(schema)
    if failed:
        raise RuntimeError(f"{len(failed)} of {len(schemas)} schema shortcuts failed: {failed}")

for entry in ShortcutNames:
    schema, ShortcutName = entry if isinstance(entry, (tuple, list)) else (None, entry)
    gold_schema = schema or ShortcutSettings.SourceSchema
    silver_schema = schema or ShortcutSettings.Shortcut_TargetSchema
    oneLake_target = {    "oneLake": {        "workspaceId": ShortcutSettings.Shortcut_TargetWorkspaceId,        "itemId":      ShortcutSettings.Shortcut_TargetLakehouseId,"path": "Tables/"+silver_schema+"/"+ShortcutName   }}
    if not create_shortcut(path="Tables/"+gold_schema, name=ShortcutName, target=oneLake_target,workspace_id=ShortcutSettings.SourceWorkspaceId,lakehouse_id=ShortcutSettings.SourceLakehouseId, conflict_policy="CreateOrOverwrite"):
        failed.append(ShortcutName)

# A failed shortcut (for example a table name in ShortcutNames that does not exist in Silver) must fail the run.
if failed:
    raise RuntimeError(f"{len(failed)} of {len(ShortcutNames)} shortcuts failed: {failed}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
