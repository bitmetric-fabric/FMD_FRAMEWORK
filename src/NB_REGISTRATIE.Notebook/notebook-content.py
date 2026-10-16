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
# Startpunt voor het toevoegen en aanpassen van bronnen en tabellen. Customer-owned: run `NB_SETUP_FMD` places this
# notebook once and never overwrites it. Lives in the configuration workspace. De registratie staat in de configdb;
# deze notebook onderhoudt geen lijsten.
#
# **Werkwijze** (draaiboek §A.4a):
# 1. Staat de bronconnectie nog niet in de configdb? Registreer hem eenmalig met `register_connection(...)` (stap 1).
#    De Fabric-connectie moet al bestaan; die wijzig je hier niet.
# 2. Open de editor (stap 2), kies de omgeving en klik op **Laden uit de configdb**.
# 3. Tab 1: bron kiezen of toevoegen. Tab 2: bij een nieuwe bron eerst **Ontdekking starten (pipeline)**; dat start
#    `PL_FMD_DISCOVER_SOURCE` in de CODE-workspace, wacht tot hij klaar is en laadt de ontdekte tabellen. Daarna tabellen
#    zoeken, selecteren, primary key, laadwijze en cleansing rules instellen.
#    Tab 3: het overzicht van wat er wordt geregistreerd, **Controleren**, **Proefdraaien** en pas daarna **Registreren**.
# 4. Dezelfde editor gebruik je in elke stap van een feature:
#    - tijdens de feature in je eigen developer-workspace: omgeving `DEV_<NAAM>` (bijvoorbeeld `DEV_MITCHELL`; de
#      workspace `DEV_<NAAM>_<prefix>_INTEGRATION_DATA` moet al in de configdb staan, en de bronbinding is die van D);
#    - na de merge: `D`;
#    - vlak voor een promotie: `T`, en later `P`.
#
# Alle wijzigingen blijven in het geheugen tot **Registreren**. Registreren kan pas na een proefdraai op precies deze
# wijzigingen. De registratie zelf is `register()`, ongewijzigd: de editor bouwt alleen de lijsten die `register()` verwacht.
# Na het registreren toont de editor het resultaat als `table("""...""")`: bewaar dat in het log of in git.
#
# **Cleansing rules**: per laag kies je *ongewijzigd laten* (de bestaande regels blijven), *vervangen* (de lijst is de
# waarheid) of *alles verwijderen*. Een gewijzigde Silver-regel werkt alleen op rijen die daarna veranderen; voor de hele
# tabel registreer je met `register(..., dry_run=False, requeue_silver=True)` (zie onderaan).
# `exclude_rows` laat rijen met een bronvlag weg, bijvoorbeeld voor CDC-deletes: als Silver-regel
# `{"function": "exclude_rows", "columns": "EVENT_CRUD", "parameters": {"values": ["delete"]}}`. Silver ziet de sleutel dan
# als verdwenen en zet hem op `IsDeleted = 1, IsCurrent = 0`. Niet als Bronze-regel gebruiken. De lijst met functies in de
# editor kent `exclude_rows` nog niet; kies daar "(eigen functie)" en vul de naam en de parameters als JSON in.

# CELL ********************

%run NB_FMD_REGISTRATION_FUNCTIONS

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Stap 1: connectie registreren (eenmalig per connectie)
# Het type is het FMD-type: `SQL` (Azure SQL), `AZURESQLMI`, `ORACLE`, `ADLS`, `ONELAKE`, `SFTP`, `FTP`, `ADF`,
# `NOTEBOOK` of `SNOWFLAKE`. Opnieuw draaien is veilig. Haal het commentaarteken weg en vul de naam in.

# CELL ********************

# register_connection("CON_FMD_<SOURCE>", "SQL")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Stap 2: de editor
# Klik op **Laden uit de configdb**. Daarna werk je van links naar rechts door de drie tabs.

# CELL ********************

registration_ui(domain="INTEGRATION", environment="D")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Zonder editor (geavanceerd)
# De editor roept `register(sources, entities, domain, environments, dry_run, requeue_silver)` aan; je kunt dat ook
# rechtstreeks doen. `table("""...""")` maakt de lijsten van een geplakte tabel (kolommen gescheiden door een tab of
# `|`), en `print_entity_list(...)` print de ontdekte tabellen als tabel. De velden staan in de docstring van `register`.
# Een Silver-regel voor de hele tabel opnieuw toepassen: `register(..., dry_run=False, requeue_silver=True)`; dat zet de
# entiteiten met een gewijzigde Silver-regel terug in de wachtrij (`execution.sp_RequeueSilverLayerEntities`). Verwijder
# de Silver-tabel eerst als de regel een type of de kolommen verandert (de editor kent `requeue_silver` niet).
#
# De ontdekking starten zonder de editor: `start_discovery(...)` (hieronder) start `PL_FMD_DISCOVER_SOURCE` in de
# CODE-workspace van deze omgeving en wacht tot hij klaar is. Je hebt een rol nodig die items in die workspace mag uitvoeren.

# CELL ********************

# start_discovery("CON_FMD_<SOURCE>", "<SourceDatabase>", schema_filter="", domain="INTEGRATION", environment="D")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
