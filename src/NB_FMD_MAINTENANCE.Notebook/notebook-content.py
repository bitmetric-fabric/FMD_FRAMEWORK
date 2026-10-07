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
# META     },
# META     "environment": {}
# META   }
# META }

# MARKDOWN ********************

# # FMD Maintenance
# Ruimt opslag op in de DATA-workspace van deze omgeving:
# 1. Leveringen in de landing zone die Bronze heeft verwerkt en die ouder zijn dan de bewaartermijn
#    (`VAR_FMD.landingzone_retention_days`). Een onverwerkte levering blijft altijd staan.
# 2. Oude Delta-bestanden in Bronze en Silver (`VACUUM`, standaard 168 uur). De historie in Silver zit in de rijen (SCD2) en blijft.
#
# Draait via `PL_FMD_MAINTENANCE`, met een eigen schema los van de loads. Een fout laat dus geen load falen.

# CELL ********************

config_settings = notebookutils.variableLibrary.getLibrary("VAR_CONFIG_FMD")
default_settings = notebookutils.variableLibrary.getLibrary("VAR_FMD")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# PARAMETERS CELL ********************

RetentionDays = ""  # leeg: VAR_FMD.landingzone_retention_days
WorkspaceGuid = ""  # leeg: VAR_CONFIG_FMD.fmd_data_workspace_guid (de DATA-workspace van deze omgeving)
VacuumHours = 168   # Delta weigert minder dan 168 uur
driver = '{ODBC Driver 18 for SQL Server}'
connstring = config_settings.fmd_fabric_db_connection
database = config_settings.fmd_fabric_db_name
schema_enabled = default_settings.lakehouse_schema_enabled

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run NB_FMD_UTILITY_FUNCTIONS

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import json
from delta.tables import DeltaTable

retention_days = int(RetentionDays or default_settings.landingzone_retention_days)
workspace = WorkspaceGuid or config_settings.fmd_data_workspace_guid
onelake = "onelake.dfs.fabric.microsoft.com"

result_sets = execute_with_outputs("[execution].[sp_GetMaintenanceTargets]", driver, connstring, database,
                                   WorkspaceId=workspace, RetentionDays=retention_days)["result_sets"]
deliveries, tables = (result_sets + [[], []])[:2]
print(f"DATA-workspace {workspace}: {len(deliveries)} verwerkte leveringen ouder dan {retention_days} dagen, {len(tables)} tabellen")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1. Landing zone

# CELL ********************

failed = []
deleted, already_gone = 0, 0

# Beperking: elke run controleert alle oude, verwerkte leveringen opnieuw (fs.exists per levering).
# Wordt dat traag, markeer verwijderde leveringen dan in de wachtrij en sla ze over in sp_GetMaintenanceTargets.
for d in deliveries:
    path = f"abfss://{d['WorkspaceGuid']}@{onelake}/{d['LakehouseGuid']}/Files/{d['FilePath']}/{d['FileName']}"
    try:
        if notebookutils.fs.exists(path):
            notebookutils.fs.rm(path, True)  # een bestand, of een map (Snowflake schrijft meerdere bestanden)
            deleted += 1
        else:
            already_gone += 1
    except Exception as e:
        failed.append(f"{path}: {e}")

print(f"Landing zone: {deleted} verwijderd, {already_gone} al weg")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. VACUUM op Bronze en Silver

# CELL ********************

vacuumed = 0
for t in tables:
    if str(schema_enabled).lower() == "true":
        name = f"{t['Namespace']}/{t['Schema']}_{t['Name']}"
    else:
        name = f"{t['Namespace']}_{t['Schema']}_{t['Name']}"
    path = f"abfss://{t['WorkspaceGuid']}@{onelake}/{t['LakehouseGuid']}/Tables/{name}"
    try:
        if DeltaTable.isDeltaTable(spark, path):
            DeltaTable.forPath(spark, path).vacuum(float(VacuumHours))
            vacuumed += 1
    except Exception as e:
        failed.append(f"{t['Layer']} {path}: {e}")

print(f"VACUUM: {vacuumed} tabellen")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

result = {"WorkspaceGuid": workspace, "RetentionDays": retention_days, "LandingDeleted": deleted,
          "LandingAlreadyGone": already_gone, "TablesVacuumed": vacuumed, "Errors": len(failed)}
print(json.dumps(result, indent=2))

if failed:
    raise Exception(f"Maintenance: {len(failed)} fout(en):\n" + "\n".join(failed[:20]))

notebookutils.notebook.exit(json.dumps(result))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
