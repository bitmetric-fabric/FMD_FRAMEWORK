# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # Registratie
# Customer-owned: run `NB_SETUP_FMD` places this notebook once and never overwrites it, so your
# lists survive a re-run of the setup. Lives in the configuration workspace.
# 
# **Werkwijze** (draaiboek §A.4a):
# 1. Nieuwe bron met veel tabellen? Draai eerst `PL_FMD_DISCOVER_SOURCE` (in de CODE-workspace) met de
#    connectie en de database. Gebruik daarna `print_entity_list(...)` hieronder om de regels voor
#    `entities` te genereren, en plak ze in de cel.
# 2. Vul `sources` en `entities` in, of pas een bestaande lijst aan.
# 3. Draai eerst `register(..., dry_run=True)`: dat voert alle controles en de registratie uit en
#    draait dan terug, en toont per entiteit of hij nieuw, gewijzigd of ongewijzigd is.
# 4. Zonder verrassingen: `register(..., dry_run=False)`.
# 5. Na een promotie: dezelfde lijst, nu met `environments=["T"]` (of `["P"]`).
# 
# IsIncremental, IsActive en IsHistorized: 0 of 1 (geen True/False).
#
# **Cleansing rules** (optioneel): `BronzeCleansingRules` en `SilverCleansingRules` per entiteit, een lijst
# van `{"function": ..., "columns": "A;B", "parameters": {...}}`. Een entiteit zonder het veld houdt zijn
# regels. Met het veld is de lijst de waarheid, en `[]` wist ze. Een ongeldige regel stopt de registratie; een
# functie die niet ingebouwd is (`normalize_text`, `fill_nulls`, `parse_datetime`) geeft een waarschuwing.
# Een gewijzigde Silver-regel werkt alleen op rijen die daarna veranderen. Voor de hele tabel: zie
# `execution.sp_RequeueSilverLayerEntities` (en de tabel verwijderen als de regel een type verandert).

# CELL ********************

%run NB_FMD_REGISTRATION_FUNCTIONS

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Ontdekken (optioneel, voor een bron met veel tabellen)

# CELL ********************

# print_entity_list("CON_FMD_<SOURCE>", "<SourceDatabase>", schema="Sales", source_alias="ERP")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Lijsten

# CELL ********************

# Environment: '*' (alle omgevingen) of de short van één omgeving (D, T, A, P). Een eigen regel
# wint van '*'. DataSourceName is de database voor ASQL en Snowflake.
sources = [
    {"Environment": "*", "Source": "ERP", "ConnectionName": "CON_FMD_<SOURCE>", "DataSourceName": "<SourceDatabase>",
     "Namespace": "erp", "DataSourceType": "ASQL_01", "LoadGroup": "", "HistoryDays": None},
]

# Alleen Source, SourceSchema, SourceName en PrimaryKeys zijn verplicht. De rest krijgt een
# standaardwaarde (TargetSchema/TargetName gelijk aan de bron, FileType parquet, IsActive 1).
entities = [
    {"Source": "ERP", "SourceSchema": "Sales", "SourceName": "Customer", "PrimaryKeys": "CustomerID"},
    # Met cleansing rules:
    # {"Source": "ERP", "SourceSchema": "Sales", "SourceName": "Store", "PrimaryKeys": "StoreID",
    #  "SilverCleansingRules": [{"function": "normalize_text", "columns": "Name", "parameters": {"case": "upper"}}]},
]

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Proefdraaien en registreren

# CELL ********************

register(sources, entities, domain="INTEGRATION", environments=["D"], dry_run=True)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# register(sources, entities, domain="INTEGRATION", environments=["D"], dry_run=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
