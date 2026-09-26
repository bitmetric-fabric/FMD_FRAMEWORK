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
