-- Fabric notebook source

-- METADATA ********************

-- META {
-- META   "kernel_info": {
-- META     "name": "synapse_pyspark"
-- META   },
-- META   "dependencies": {
-- META     "lakehouse": {
-- META       "default_lakehouse_name": "",
-- META       "default_lakehouse_workspace_id": ""
-- META     }
-- META   }
-- META }

-- MARKDOWN ********************

-- # Create materialized lake views 
-- 1. Use this notebook to create materialized lake views. 
-- 2. Select **Run all** to run the notebook. 
-- 3. When the notebook run is completed, return to your lakehouse and refresh your materialized lake views graph. 


-- MARKDOWN ********************

-- ## Gold van deze omgeving
-- `%%configure` zet de default lakehouse op de Gold uit `VAR_GOLD_SHORTCUTS_FMD`, zodat de notebook in elke
-- omgeving (en in een developer-workspace) in de eigen Gold schrijft. Het vangnet stopt de notebook als hij in een
-- developer-workspace (`DEV_*`) draait terwijl die Gold niet in een `DEV_*`-workspace staat (ADR-011).
-- Deze twee cellen moeten de eerste codecellen blijven: `%%configure` werkt alleen aan het begin van een sessie.

-- CELL ********************

-- MAGIC %%configure
-- MAGIC {
-- MAGIC     "defaultLakehouse": {
-- MAGIC         "name": "LH_GOLD_LAYER",
-- MAGIC         "id": {"variableName": "$(/**/VAR_GOLD_SHORTCUTS_FMD/SourceLakehouseId)"},
-- MAGIC         "workspaceId": {"variableName": "$(/**/VAR_GOLD_SHORTCUTS_FMD/SourceWorkspaceId)"}
-- MAGIC     }
-- MAGIC }

-- METADATA ********************

-- META {
-- META   "language": "python",
-- META   "language_group": "synapse_pyspark"
-- META }

-- CELL ********************

-- MAGIC %%pyspark
-- MAGIC # Vangnet: een developer-workspace (DEV_*) schrijft nooit in een gedeelde Gold (ADR-011).
-- MAGIC ctx = notebookutils.runtime.context
-- MAGIC ws, gold_ws = ctx.get("currentWorkspaceName"), ctx.get("defaultLakehouseWorkspaceName")
-- MAGIC print(f"Workspace {ws}, Gold in {gold_ws}")
-- MAGIC if str(ws).startswith("DEV_") and not str(gold_ws).startswith("DEV_"):
-- MAGIC     raise RuntimeError(f"{ws} zou schrijven in de Gold van {gold_ws}: draai eerst bind (NB_SETUP_DEVELOPER_WORKSPACES)")

-- METADATA ********************

-- META {
-- META   "language": "python",
-- META   "language_group": "synapse_pyspark"
-- META }

-- CELL ********************

-- Welcome to your new notebook
-- Type here in the cell editor to add code!
-- CREATE MATERIALIZED LAKE VIEW <mlv_name> AS select_statement

-- METADATA ********************

-- META {
-- META   "language": "sparksql",
-- META   "language_group": "synapse_pyspark"
-- META }

-- MARKDOWN ********************

-- ## Refresh the materialized lake views
-- Creating/replacing an MLV above does not refresh it. Run this cell after the CREATE statements
-- (or schedule it after them in a pipeline) so the views actually recompute. The Gold lakehouse
-- of this environment comes from VAR_GOLD_SHORTCUTS_FMD, so nothing needs to be filled in here.
-- The cell fails when the refresh does not start or does not complete.

-- CELL ********************

%%pyspark
import requests, time

# The Gold lakehouse of this environment. It lives in the DATA workspace, not in the CODE
# workspace this notebook runs in; the setup fills these per value set.
gold = notebookutils.variableLibrary.getLibrary("VAR_GOLD_SHORTCUTS_FMD")
workspace_id = gold.SourceWorkspaceId
lakehouse_id = gold.SourceLakehouseId

token = notebookutils.credentials.getToken("https://api.fabric.microsoft.com")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/jobs/RefreshMaterializedLakeViews/instances"
response = requests.post(url, headers=headers)
if response.status_code != 202:
    raise Exception(f"MLV refresh did not start: {response.status_code} {response.text}")

location = response.headers["Location"]
while True:
    time.sleep(15)
    job = requests.get(location, headers=headers).json()
    if job.get("status") in ("Completed", "Failed", "Cancelled", "Deduped"):
        break
print(f"MLV refresh: {job['status']}")
if job["status"] in ("Failed", "Cancelled"):
    raise Exception(f"MLV refresh ended with status {job['status']}: {job.get('failureReason')}")

-- METADATA ********************

-- META {
-- META   "language": "python",
-- META   "language_group": "synapse_pyspark"
-- META }
