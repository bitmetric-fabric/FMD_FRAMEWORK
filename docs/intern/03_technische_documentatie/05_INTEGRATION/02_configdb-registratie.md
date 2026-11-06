# Configdb-registratie — bronnen en entiteiten registreren

**Bron:** `FMD/src/Config_Database/integration/StoredProcedures/*.sql`, `FMD/src/PL_TOOLING_POST_ASQL_TO_FMD.DataPipeline/pipeline-content.json` · `output/01_kennisbasis/registratie.md`
**Status:** vastgesteld, tenzij anders aangegeven

*Correctie 2026-10-13: er is een derde route bijgekomen, en die is nu de aanbevolen route: `NB_REGISTRATIE`
met `PL_FMD_DISCOVER_SOURCE` (ADR-018), zie Route 3. Routes 1 en 2 blijven bestaan voor uitzonderingen.*

Er zijn twee routes om een bron te registreren: **handmatig** (via de kern-stored-procedures, geschikt voor één-of-enkele-tabellen) en **bulk** (via `PL_TOOLING_POST_ASQL_TO_FMD`, geschikt voor het in één keer registreren van een hele Azure SQL-bron met meerdere tabellen).

---

## Route 3 (aanbevolen sinds 2026-10-13): `NB_REGISTRATIE`, met ontdekken via de connectie

*Toegevoegd 2026-10-13: ADR-018, FMD_FRAMEWORK #60, #63 en #64.* Deze route vervangt in de praktijk:
- het lijstsjabloon `templates/registratie/registreer_entiteiten.sql`;
- voor een nieuwe bron met veel tabellen ook `PL_TOOLING_POST_ASQL_TO_FMD`.

~~Beide bestaan nog als terugvaloptie. Ze worden pas verwijderd na akkoord.~~ *(Bijgewerkt 2026-10-15, `FMD_FRAMEWORK#71`, na akkoord van Mitchell. Het sjabloon is verwijderd. `PL_TOOLING_POST_ASQL_TO_FMD` staat niet meer in `config/item_deployment.json`, dus de setup rolt hem niet meer uit; een bestaande installatie houdt hem, en de bestanden blijven in de repo omdat de pipeline ook in `edkreuk/FMD_FRAMEWORK` bestaat.)*

### Werkwijze met de editor (aanbevolen sinds 2026-10-16)

*Correctie 2026-10-16: hieronder stond de werkwijze met lijsten (`sources`/`entities`) als hoofdroute. `NB_REGISTRATIE`
bevat sindsdien geen lijsten meer maar de editor; de lijstmanier blijft mogelijk (zie "Werkwijze zonder editor"). Reden:
ADR-018, aanvulling "Interactieve editor". Bron: `FMD/src/NB_FMD_REGISTRATION_FUNCTIONS.Notebook/notebook-content.py`,
`FMD/src/NB_REGISTRATIE.Notebook/notebook-content.py`, ADR-018.*

1. **Connectie** (eenmalig per connectie, *vastgesteld*): `register_connection("CON_FMD_<SOURCE>", "SQL")` in
   `NB_REGISTRATIE`. De Fabric-connectie moet al bestaan; het FMD-type is `SQL`, `AZURESQLMI`, `ORACLE`, `ADLS`, `ONELAKE`,
   `SFTP`, `FTP`, `ADF`, `NOTEBOOK` of `SNOWFLAKE`. *Correctie 2026-10-29 (reden: `FMD_FRAMEWORK#84`, `fbaf0c0`): ook `ODATA`; *vastgesteld* in `CONNECTION_TYPES` van `NB_FMD_REGISTRATION_FUNCTIONS`.*
2. **Editor openen** (cel "Stap 2"): kies omgeving (`D`, `T`, `A`, `P` of `DEV_<NAAM>`) en klik op **Laden uit de configdb**.
   De editor laadt niet vanzelf. *Getest in eigen omgeving* (2026-10-16): laden tijdens het uitvoeren van de cel liet de
   velden van tab 1 leeg en de volgende klik op Laden faalde met `TraitError: Invalid selection: index out of bounds`
   (`11_troubleshooting.md`). *Aanname:* het Fabric-frontend stuurt na het openen van de widgets eigen toestand terug
   (`index=None`) en overschrijft de net gezette waarden.
3. **Tab 1 Bronnen:** bron kiezen of toevoegen (alias, connectie, database, namespace, brontype, `LoadGroup`, `HistoryDays`).
   Bewaren gaat naar het geheugen, niet naar de configdb.
4. **Tab 2 Tabellen:**
   - **Ontdekking starten (pipeline)** start `PL_FMD_DISCOVER_SOURCE` in de CODE-workspace van de gekozen omgeving, wacht
     tot hij klaar is en laadt daarna de ontdekte tabellen; het veld *Schemafilter* beperkt dat tot één schema (leeg is alles).
     *Getest in eigen omgeving* (FMD_EIND, 2026-10-16, bron AW, schemafilter leeg): run
     `805163b3-17db-4813-9a60-d04fb13c63ae`, `Completed` na 1 min 44 s, 96 tabellen ontdekt.
     - *Getest in eigen omgeving* (2026-10-16): ook omgeving T (run `00d57544-9b4b-47e3-9ae6-fccb5d6da7ac`) en P (run
       `cb1c01c9-7104-4bf3-9e01-30cb2aaf90d8`), en de Snowflake-tak van de pipeline (FMD_TRIAL, `CON_TRIAL_SNOWFLAKE` /
       `FMD_BRON`, schema `TPCH`, run `47d555a8-ceb4-4fd4-97f1-4dcd6d50aa9e`, 7 tabellen met kolommen; geen primary keys,
       want de tabellen hebben geen PK-constraint). De Snowflake-run is rechtstreeks op de pipeline gestart, niet via de editor.
     - Een `DEV_<NAAM>`-omgeving draait de ontdekking in de CODE-workspace van D (de developer-CODE-workspace heeft de
       pipeline niet). *Alleen lokaal getest*, niet in Fabric.
     - Je hebt een rol nodig die een run mag starten (Contributor of hoger; bij sommige itemtypen Member, volgens de
       documentatie van Microsoft). Bij een 403 geeft de editor een melding. *Aanname:* een Viewer krijgt die 403; niet
       getest, want daarvoor is een tweede identiteit nodig.
   - **Ontdekte tabellen laden** leest alleen wat de laatste ontdekking al in `integration.DiscoveredEntity` heeft gezet.
   - Links de lijst met filter en bulkacties; rechts de eigenschappen van de gekozen tabel: doelschema en -tabel, bestand,
     incrementeel met watermarkkolom, actief, historie in Silver, primary key en cleansing rules per laag.
   - Een nieuwe tabel doet pas mee na **Selecteren voor registratie**. Een geregistreerde tabel doet mee zodra je hem wijzigt.
5. **Tab 3 Controleren en registreren:**
   - het overzicht toont per tabel wat er wordt geregistreerd; een veld dat afwijkt van de huidige registratie is oranje
     met de oude waarde eronder (*getest in eigen omgeving*, 2026-10-16);
   - **Controleren** en **Proefdraaien** (de bestaande `register(..., dry_run=True)`, teruggedraaid) tonen hun uitkomst
     direct onder de knoppen;
   - na elke wijziging na de proefdraai is de proefdraai ongeldig en blijft Registreren geblokkeerd;
   - **Registreren** kan alleen na een proefdraai op precies deze wijzigingen en een bevestiging.
6. Dezelfde editor gebruik je in elke stap van een feature: `DEV_<NAAM>`, `D`, `T`, `P`.

**Beperkingen** (*vastgesteld*, uit de code): de editor kent `requeue_silver` niet (alleen via `register(...)` rechtstreeks) ~~en de lijst met
cleansing-functies in de editor kent `exclude_rows` nog niet (kies "(eigen functie)")~~.
*Correctie 2026-10-29 (reden: `FMD_FRAMEWORK#78`, `09f3eb1`): de editor kent `exclude_rows` en `clamp_min_date` wel (*vastgesteld*, `CLEANSING_FUNCTIONS` in `NB_FMD_REGISTRATION_FUNCTIONS` op `origin/main`). Ook nieuw sinds deze tekst (*vastgesteld* in de code): LoadGroup, kolomkeuze (`SourceColumns`, Snowflake met cast `naam::TYPE`) en bronfilter per tabel in tab 2 (#77, #83), voor `ASQL_01`, `ASQL_02`, `SNOWFLAKE_01` en `ODATA_01` (#84); `NB_REGISTRATIE` en de functies op een Python-kernel (#81, `4bd204c`). De klantversie van deze werkwijze: `klantdocumentatie/v3/bron/ontwikkeling/bronregistratie.md`.*

### Werkwijze zonder editor (`register()` rechtstreeks)

**Werkwijze:**
1. **Ontdekken.** Optioneel, voor een bron met veel tabellen.
   - Run `PL_FMD_DISCOVER_SOURCE` in de CODE-workspace met `ConnectionName`, `DataSourceName` (de
     database) en eventueel `SchemaFilter`.
   - De pipeline ondersteunt SQL (ASQL) en Snowflake. Bij een ander connectietype faalt hij met een
     eigen melding.
   - Het resultaat komt in `integration.DiscoveredEntity`: tabellen en views, kolommen met type, en PK's.
2. **Lijst maken.** In `NB_REGISTRATIE` (CONFIG-workspace) geeft `print_entity_list(...)` regels om te
   plakken, met de PK al ingevuld.
   - Een tabel zonder PK-constraint en een view krijgen `# TODO`.
   - Het notebook is klanteigendom: de setup zet het één keer neer en overschrijft het daarna niet.
3. **`sources` en `entities` invullen.**
   - Verplicht per entiteit: `Source`, `SourceSchema`, `SourceName` en `PrimaryKeys`. De rest krijgt een
     standaardwaarde.
   - Let op: de lijst is de bron van waarheid. Een leeg veld betekent de standaardwaarde, ook voor een
     bestaande entiteit. Een leeg `IsHistorized` is 0 (ADR-016) en een leeg `IsIncremental` is 0.
   - **Cleansing rules** (optioneel, *toegevoegd 2026-10-15, `FMD_FRAMEWORK#69`, gemerged*): `BronzeCleansingRules` en `SilverCleansingRules`,
     een lijst van `{"function": ..., "columns": "A;B", "parameters": {...}}`. Hier geldt de uitzondering op de
     regel hierboven: een entiteit **zonder** het veld houdt zijn regels, zodat een bestaande installatie met
     handmatig gezette regels niets verliest. Met het veld is de lijst de waarheid, en `[]` of `null` wist ze.
     - **Delete-vlag uit de bron** (*toegevoegd 2026-10-16, branch `feature/cleansing-exclude-rows`, nog niet gemerged; getest in trial-Dev, `testplan-trial.md` T-D15*) *(bijgewerkt 2026-10-29: gemerged als `FMD_FRAMEWORK#73`, `9e0e24c`; *vastgesteld* in `git log origin/main`)*:
       de ingebouwde functie `exclude_rows` laat rijen weg waarvan een kolom een van de opgegeven waarden heeft
       (hoofdletterongevoelig; NULL houdt de rij; lege `values` is een fout). Voorbeeld voor een CDC-bron:
       `"SilverCleansingRules": [{"function": "exclude_rows", "columns": "EVENT_CRUD", "parameters": {"values": ["delete"]}}]`.
       Gebruik hem alleen als **Silver**-regel: bij een incrementele Bronze moet de delete-rij juist binnenkomen,
       anders blijft de bestaande Bronze-rij staan. Silver ziet de sleutel dan als verdwenen en zet de bestaande rij op
       `IsDeleted = 1`, `IsCurrent = 0` (met en zonder historie, ADR-016). De delete-rij zelf komt nooit in Silver;
       een sleutel die in Silver nog niet bestond, komt er niet in (*getest in eigen omgeving*, 2026-10-16). Silver
       blijft daarmee de afgesloten rijen bewaren: Silver-consumenten filteren op `IsCurrent = 1`. De
       registratie keurt een regel zonder `columns` of met een lege `values` af, ook in de dry run
       (*correctie 2026-10-16: eerder stond hier dat dat pas in de run faalt; dat is op verzoek van Mitchell voor de
       merge toegevoegd en getest, `testplan-trial.md` T-D15*). Een niet-bestaande kolom wordt pas in de run
       gezien (`UNRESOLVED_COLUMN`): de procedure kent de kolommen alleen na `PL_FMD_DISCOVER_SOURCE`.
4. **Proefdraaien:** `register(sources, entities, domain="INTEGRATION", environments=["D"], dry_run=True)`.
   Dat toont:
   - de DATA-workspace;
   - per entiteit `New`, `Changed` of `Unchanged`, en bij `Changed` wat er verandert (oud -> nieuw);
   - de actieve entiteiten die niet in de lijst staan;
   - een kolom `Warning` bij een functie die niet ingebouwd is (`normalize_text`, `fill_nulls`,
     `parse_datetime`, en vanaf de branch `exclude_rows`; een eigen functie uit `NB_FMD_CUSTOM_DQ_CLEANSING` mag, de procedure kan hem niet zien),
     en bij een gewijzigde Silver-regel op een bestaande entiteit. Zo'n regel werkt alleen op rijen die daarna
     veranderen; voor de hele tabel zie `10_operations.md`, *Silver opnieuw opbouwen*.
     *Bijgewerkt 2026-10-15 (`FMD_FRAMEWORK#72`, PR open; getest in trial-Dev, `testplan-trial.md` T-C12; gemerged als `daf07ac`, bijgewerkt 2026-10-29):* de dry
     run toont daarvoor een hint, en `register(..., dry_run=False, requeue_silver=True)` zet de entiteiten met een
     gewijzigde Silver-regel in de wachtrij. De Silver-tabel verwijderen bij een type- of kolomwijziging blijft
     handwerk.
5. **Registreren:** hetzelfde met `dry_run=False`. Na een promotie dezelfde lijst met
   `environments=["T"]` of `["P"]`.
   - **Tijdens een feature, in je developer-workspace** (*toegevoegd 2026-10-15, `FMD_FRAMEWORK#71`*):
     `environments=["DEV_<NAAM>"]`. De procedure zoekt de DATA-workspace `DEV_<NAAM>_<PREFIX>_INTEGRATION_DATA`
     en gebruikt de bronbindingen van D. Je gebruikt dezelfde lijst in elke stap: `DEV_<NAAM>` tijdens de
     feature, `D` na de merge, `T` en `P` vóór de promotie.
   - De naam mag alleen letters, cijfers, `_` en `-` bevatten.
   - De workspace moet al in de configdb staan (`sp_UpsertWorkspace` en `sp_UpsertLakehouse`).
   - Alleen voor `domain="INTEGRATION"`: de DATA-workspace van een business domain heet
     `DEV_<NAAM>_<PREFIX>_DATA`, zonder domeinnaam, en heeft geen landing zone.
   - De `DataSource`-rijen zijn gedeeld met D: een andere `LoadGroup` of `Namespace` vanuit een `DEV_`-run
     geldt ook voor D.

**Van D naar T en P kopiëren** (*toegevoegd 2026-10-26, branch `feature/copy-registration`, nog niet gemerged, nog niet in Fabric getest*) *(bijgewerkt 2026-10-29: gemerged als `FMD_FRAMEWORK#82`, `f930560`; *vastgesteld* in `git log origin/main`)*:
- `copy_registration("INTEGRATION", ["T", "P"])` in `NB_REGISTRATIE` leest de registratie van D (`load_registration`) en registreert die via
  `register()` in T en P. De proefdraai toont per tabel `New`, `Changed` of `Unchanged`; bij een fout in een omgeving wordt nergens iets geschreven.
  Geen nieuwe procedure en geen dacpac (*vastgesteld*: `NB_FMD_REGISTRATION_FUNCTIONS`, cel met `plan_copy`).
- Standaard alleen tabellen die in het doel nog niet staan. `update=True` brengt ook bestaande tabellen in lijn met D, behalve hun dataselectie.
  Alleen actieve tabellen uit D (`only_active=False` neemt ook uitgezette mee). Een watermark wordt nooit gekopieerd; `history_days` zet een
  start-watermark voor een incrementele tabel zonder watermark.
- **Dataselectie per omgeving** (`overrides`): `SourceFilter`, `SourceColumns`, `IsActive` en `LoadGroup` staan op `LandingzoneEntity` en dus per
  DATA-workspace. `{"T": {"*": {"IsActive": 0}, "Sales.SalesOrderHeader": {"IsActive": 1, "SourceFilter": "OrderDate >= '2025-01-01'"}}}` laadt in T
  alleen die ene tabel en met dat filter. Een tabelregel gaat voor `"*"`; een veld buiten die vier of een tabel die niet in D staat is een fout, en
  `validate_state` controleert de uitkomst (brontype, PK en watermark in `SourceColumns`, geen `;` in het filter).
- Beperkingen (*vastgesteld*, ADR-020): een filter of kolomkeuze wijzigen verwijdert niets uit Bronze en Silver; kolommen weghalen bij een tabel die al in
  Bronze staat laat de Bronze-merge falen; de proefdraai voert het filter niet uit. `HistoryDays` geldt voor alle incrementele tabellen van die bron zonder watermark.
- *Getest in eigen omgeving* (2026-10-26, `testplan-trial.md` T-C13, FMD_TRIAL): dry run D→T en D→P met en zonder overrides, een echte registratie (T: 1 tabel, P: 2 tabellen) en een tweede aanroep zonder wijzigingen. Draaide in een Livy-sessie (Spark), dus niet het notebook op de Python-kernel. Niet getest: een load van de nieuwe tabellen en overrides in een echte run. Logica lokaal: `scripts/test_registration_editor.py` (77 controles).

**Controles** (in `integration.sp_RegisterEntities`):
- een onbekend veld in een regel is een fout;
- cleansing rules moeten een JSON-array van objecten zijn, elk met een `function`, `columns` als tekst
  (kolommen gescheiden door `;`) en `parameters` als object. Een tekst, een object in plaats van een array of
  een regel zonder `function` is een fout. Bij het vergelijken telt de tekst: eenmaal vanuit de lijst
  geregistreerd is hij stabiel, maar regels die eerder met de hand zijn gezet, tonen de eerste keer `Changed`,
  ook als alleen de opmaak verschilt;
- de DATA-workspace volgt uit domein en omgeving, en dat moet precies één workspace zijn;
- de controles van het lijstsjabloon (verwijderd 2026-10-15) zitten nu in de procedure: connectie, type,
  dubbele regels, `Namespace`, `LoadGroup` en `HistoryDays`;
- als de bron ontdekt is, ook tegen die metadata:
  - de tabel moet bestaan, bij Snowflake met exacte hoofdletters;
  - de PK- en watermarkkolommen moeten bestaan;
  - het watermark moet bij Snowflake DATE of TIMESTAMP zijn.

De registratie is alles of niets per omgeving. Een bestaande DataSource houdt zijn beschrijving.

**Status:** *getest in eigen omgeving*, 2026-10-13, in FMD_TRIAL (`testplan-trial.md`, "vervolg" 1 t/m 7):
- discovery `2a255475`;
- registratie in T `29cf50c8`;
- load in T `df23d149`.

De kolom met wijzigingen (#64) is getest met een tijdelijke kopie van de procedure, nog niet vanuit het
notebook.

**Cleansing rules in de lijst:** *getest in eigen omgeving* 2026-10-15 (trial-Dev, `sqlcmd`, `testplan-trial.md` T-C10); de `Warning`-regel in `register()` zelf is niet vanuit het notebook gedraaid.

**`DEV_<NAAM>` als omgeving:** *getest in eigen omgeving* 2026-10-15 (trial-Dev, `sqlcmd`, `testplan-trial.md` T-C11):
- de workspace wordt gevonden, een nieuwe tabel is `New` (en wordt teruggedraaid), en een echte run zonder wijziging laat landing zone, Bronze, Silver en de DataSource-rij ongewijzigd;
- de bindingen zijn die van D, en de foutgevallen geven elk een eigen melding;
- D, T en P werken als voorheen.

Niet getest: de notebookroute (`register()` via pyodbc) met `DEV_<NAAM>`, een echte registratie van een nieuwe entiteit in de dev-workspace, en een load in de dev-CODE-workspace.

---

## Route 1: handmatige registratie — de drie kern-stored-procedures

### `integration.sp_UpsertConnection`
```sql
,@ConnectionGuid UNIQUEIDENTIFIER
,@Name nvarchar(200)
,@Type nvarchar(50)
,@IsActive bit
```
Eenvoudige IF EXISTS/ELSE-upsert op `ConnectionGuid`. **Geen output-select.** Vult **niet** `GatewayType`/`DatasourceReference` — die kolommen zijn alleen via een directe INSERT/UPDATE te zetten.

### `integration.sp_UpsertDataSource`
```sql
,@ConnectionId INT
,@DataSourceId INT = 0
,@Name NVARCHAR(100)
,@Namespace VARCHAR(100)
,@Type VARCHAR(30)
,@Description NVARCHAR(200)
,@LoadGroup VARCHAR(50) = ''
,@IsActive BIT = 1
```
Upsert-logica op `@DataSourceId` (`0` = insert). **Retourneert `DataSourceId` via SELECT** — vang deze waarde op voor de volgende stap. `@LoadGroup` is de fork-eigen toevoeging.

### `integration.sp_UpsertLandingzoneBronzeSilver`
```sql
,@DataSourceId INT
,@WorkspaceGuid UNIQUEIDENTIFIER
,@SourceSchema NVARCHAR(100)
,@SourceName NVARCHAR(200)
,@TargetSchema NVARCHAR(100)
,@TargetName NVARCHAR(200)
,@SourceCustomSelect NVARCHAR(4000)
,@FileName NVARCHAR(200)
,@FilePath NVARCHAR(100)
,@FileType NVARCHAR(20)
,@IsIncremental BIT
,@IsIncrementalColumn NVARCHAR(50) = NULL
,@CustomNotebookName VARCHAR(200)
,@PrimaryKeys NVARCHAR(200)
```

Dit is de "3-in-1"-procedure:
1. Gebruikt `@WorkspaceGuid` om via `sp_GetLakehouse` de GUID's van `LH_DATA_LANDINGZONE`, `LH_BRONZE_LAYER` en `LH_SILVER_LAYER` binnen die workspace op te zoeken. **Deze lakehouses moeten al geregistreerd staan** in `integration.Lakehouse` met exact deze namen — zie `01_ddl-spec.md`.
2. Doet vervolgens **3× een `MERGE`** (Landingzone → Bronze → Silver) binnen **één transactie** (`BEGIN TRY`/`BEGIN TRANSACTION`, rollback bij fout).
3. Retourneert alle drie de gegenereerde ID's.
4. Bronze en Silver krijgen `IsActive=1` en `FileType='Delta'` **hardcoded** — geen parameter, dus niet per entiteit te overschrijven via deze procedure.

De parametervolgorde komt 1-op-1 overeen met het upstream wiki-voorbeeld (`Adding-a-new-entity.md`) — geen divergentie fork vs. upstream op dit punt.

### Aanvullende procedures (niet in de originele briefing genoemd, wel relevant)

Losse `sp_Upsert*` per laag bestaan ook, voor wie liever per laag i.p.v. in één transactie werkt:
- `sp_UpsertLandingzoneEntity`, `sp_UpsertBronzeLayerEntity`, `sp_UpsertSilverLayerEntity`
- `sp_UpsertBronzeCleansingRule` / `sp_UpsertSilverCleansingRule` — **let op:** deze THROWEN foutcode `50000` als de entiteit nog niet bestaat. Puur update, geen insert-fallback.
- `sp_UpsertLakehouse` / `sp_UpsertWorkspace` / `sp_UpsertPipeline` — voor het registreren van de Fabric-items zelf (vereist vóór je entiteiten kunt registreren, zie stap 0 hieronder)

**Read-only lookup-procedures:**
- `sp_GetConnection` (by Guid)
- `sp_GetDataSource` (by Name) — **⚠️ zoekt alleen op `Name`**, niet op de combinatie met `Type`/`Connection`. Bij dubbele `DataSource`-namen tussen verschillende bronnen kan dit de verkeerde `DataSource` teruggeven. (Open vraag: of dit in de praktijk al is voorgekomen is niet bevestigd — wel een reëel risico gezien de UC op (`ConnectionId`,`Name`,`Type`) toestaat dat dezelfde `Name` bij meerdere connecties voorkomt.)
- `sp_GetLakehouse` (by Workspace+Name, OUTPUT-param)
- `sp_GetLandingzoneEntity`, `sp_GetBronzeLayerEntity`, `sp_GetSilverLayerEntity`

### Handmatige registratie — stappenplan

```
0. Vooraf (eenmalig per workspace): registreer Workspace + de drie lakehouses
   sp_UpsertWorkspace     → WorkspaceGuid
   sp_UpsertLakehouse ×3  → LH_DATA_LANDINGZONE, LH_BRONZE_LAYER, LH_SILVER_LAYER
                             (exact deze namen — geen vrije keuze)

1. sp_UpsertConnection     → registreer de bronconnectie (database, file, etc.)
2. sp_UpsertDataSource     → registreer de logische bron, vang DataSourceId op
3. sp_UpsertLandingzoneBronzeSilver
   → per entiteit (tabel/view), met DataSourceId uit stap 2 en WorkspaceGuid uit stap 0
   → registreert Landingzone + Bronze + Silver in één transactie
```

---

## Route 2: bulkregistratie — `PL_TOOLING_POST_ASQL_TO_FMD`

*Bijgewerkt 2026-10-15 (`FMD_FRAMEWORK#71`): de setup rolt deze pipeline niet meer uit (hij staat niet meer in `config/item_deployment.json`). Een bestaande installatie houdt hem. Gebruik voor een nieuwe bron met veel tabellen `PL_FMD_DISCOVER_SOURCE` met `NB_REGISTRATIE` (Route 3): die werkt ook voor Snowflake, controleert tegen de ontdekte metadata en legt niet alles als full load vast.*

Voor het in één keer registreren van meerdere tabellen/views uit één Azure SQL-bron.

**Pipeline-parameters (definitief, gecorrigeerd t.o.v. eerdere documentatie — zie `03_operationele-aandachtspunten.md` punt 3):**
```
ConnectionGuid       (string, GUID van de bron-Azure SQL-connectie)
DatasourceName       (string, bv. 'WideWorldImporters'; exact de naam van de brondatabase, want
                      PL_FMD_LDZ_COPY_FROM_ASQL_01 gebruikt DataSource.Name als database)
DatasourceNamespace  (string, bv. 'wwi')
DatasourceType       (string, 'ASQL_01' of 'ASQL_02'; een andere waarde wordt stil overgeslagen, zie 07_extension-points.md §1)
Tables               (string, comma-separated SQL-literal-lijst zoals ''schema.tabel'',''schema.tabel2'';
                      quotes en haakjes worden gestript, dus Sales.Customer,Person.Person werkt ook)
```
Er is **geen** los `Data_WorkspaceGuid`-parameter (meer) — de workspace-GUID komt uit de Variable Library (`VAR_CONFIG_FMD`, libraryvariabele `fmd_data_workspace_guid`).

**Wat de pipeline doet, activity voor activity:**

1. **`Copy metadata`** — draait een T-SQL-query tegen de bron-Azure SQL-database die voor elke tabel/view in `@Tables` automatisch kolommappings + primary keys afleidt (via `sys.objects`/`sys.columns`/`sys.sql_expression_dependencies`, ook voor 1-op-1 views) en als JSON wegschrijft naar `Files/metadata/{DatasourceName}.json` in `LH_DATA_LANDINGZONE`. Vanaf PR #14 stopt de query vóórdat er iets geregistreerd wordt als een object niet bestaat of geen afleidbare PK heeft (een tabel zonder PK, of een view met meer dan één basistabel). Die objecten registreer je handmatig (Route 1) met expliciete `PrimaryKeys`; zie `11_troubleshooting.md`.
2. **`LKP DATASOURCE`** → `sp_GetDataSource` (by Name) en **`LKP CONNECTION`** → `sp_GetConnection` (by Guid).
3. **`LKP_INSERT_DATASOURCE`** → `sp_UpsertDataSource` met `Namespace`/`Name`/`Type` uit de pipeline-parameters, `IsActive=True`.
4. **`LKP_ENTITIES`** — leest het net weggeschreven metadata-JSON terug.
5. **`ForEach LZE`** — loopt over elke entiteit uit dat JSON-bestand en roept per entiteit `sp_UpsertLandingzoneBronzeSilver` aan.

**Update (2026-09-22):** een eerdere versie van dit document waarschuwde hier voor een "bevestigde bug" in stap 5 (casing-mismatch), gebaseerd op statische codeanalyse. Een empirische testrun door Mitchell (job `50b62157`, `FMDTRIAL CODE (D)`) heeft aangetoond dat de pipeline in de praktijk correct registreert — zie `03_operationele-aandachtspunten.md`, punt 1, voor de volledige toelichting en de correctie van het onderliggende mechanisme (Fabric's expressietaal evalueert `@`-strings ook zonder expliciete Expression-wrapper, en dot-notation is case-insensitief). De pipeline is dus zonder voorbehoud bruikbaar. Opnieuw bevestigd in de hertest (2026-09-26, run `7935bd0b`, `testplan-trial.md` T-C06).

**Let op bij opnieuw draaien (2026-09-26, T-C06):** de pipeline overschrijft een bestaande bron en bestaande entiteiten met vaste waarden: `IsIncremental = 0`, `IsIncrementalColumn`/`SourceCustomSelect`/`CustomNotebookName` leeg, `PrimaryKeys` opnieuw afgeleid, `DataSource.LoadGroup = ''`, `IsActive = 1` en `Description` = de naam. Vanaf PR #15 voegt de pipeline alleen toe (`@OnlyInsert = 1`): een bestaande bron of entiteit blijft ongemoeid, en wijzigen gaat via Route 1. Zet in een fork van vóór PR #15 in `Tables` alleen nieuwe objecten.

### Bulkregistratie — stappenplan

```
1. Zorg dat de bronconnectie al geregistreerd staat (sp_UpsertConnection) — de pipeline doet dit niet zelf
2. Zorg dat Workspace + 3 lakehouses geregistreerd staan (zie Route 1, stap 0)
3. Run PL_TOOLING_POST_ASQL_TO_FMD met: ConnectionGuid, DatasourceName, DatasourceNamespace,
   DatasourceType, Tables
4. Verifieer na afloop (algemene goede praktijk, niet vanwege een bekende bug): controleer of
   SourceName/SourceSchema/PrimaryKeys en de Bronze/Silver-tabelnamen daadwerkelijk correct zijn
   doorgekomen, niet alleen dat de pipeline "geslaagd" rapporteert
```

---

## Deactivering (B-INFRA-02)

Dit is de enige volledige beschrijving; andere documenten verwijzen hiernaar. Het principe: nooit DELETE, alleen `IsActive = 0`.

**Waar het filter echt zit.** De drie `execution`-views filteren **alleen** op de entiteitstabellen:

| View | Filter |
|---|---|
| `vw_LoadSourceToLandingzone` | `LZE.[IsActive] = 1` |
| `vw_LoadToBronzeLayer` | `LZE.[IsActive] = 1 AND BLE.[IsActive] = 1` |
| `vw_LoadToSilverLayer` | `LZE` + `BLE` + `SLE` `IsActive = 1` |

`Connection.IsActive`, `DataSource.IsActive` en `Lakehouse.IsActive` komen in geen enkele view, pipeline-lookup of `sp_Get*`-procedure voor. Ze zijn **administratief** en stoppen de load niet.

**Procedure.** Kies het niveau:

```sql
-- 1. Eén entiteit volledig stoppen (Landingzone, Bronze en Silver)
UPDATE [integration].[LandingzoneEntity]
SET    [IsActive] = 0
WHERE  [LandingzoneEntityId] = <LandingzoneEntityId>

-- 2. Een hele bron stoppen: alle entiteiten van die DataSource
UPDATE [integration].[LandingzoneEntity]
SET    [IsActive] = 0
WHERE  [DataSourceId] = <DataSourceId>

-- 3. Alleen Silver stoppen (Landingzone en Bronze blijven laden)
UPDATE [integration].[SilverLayerEntity]
SET    [IsActive] = 0
WHERE  [SilverLayerEntityId] = <SilverLayerEntityId>

-- Optioneel, alleen voor de administratie (heeft géén effect op de load):
UPDATE [integration].[DataSource]
SET    [IsActive] = 0
WHERE  [DataSourceId] = <DataSourceId>
```

**Controleren.** Na deactivering mag de entiteit niet meer in de laadview staan:

```sql
SELECT [EntityId]
      ,[DataSourceName]
      ,[SourceSchema]
      ,[SourceName]
FROM   [execution].[vw_LoadSourceToLandingzone]
WHERE  [DataSourceId] = <DataSourceId>
-- verwacht: geen rijen (procedure 2) of zonder de gedeactiveerde entiteit (procedure 1)
```

**Herregistratie en `IsActive`: opgelost vanaf fork-commit `4dd41cf` (PR #8).**
- Vanaf `4dd41cf` zet `sp_UpsertLandingzoneBronzeSilver` `IsActive = 1` alleen bij een **nieuwe** entiteit. Bij een bestaande Landingzone-, Bronze- of Silver-entiteit blijft `IsActive` staan. Een gedeactiveerde entiteit blijft dus uit, ook na een nieuwe registratieronde via het sjabloon in `draaiboek_detail.md` Bijlage A of via de bulkpipeline.
- **Oudere dacpac:** daar zet de `WHEN MATCHED`-tak hard `IsActive = 1`, en activeert elke registratieronde gedeactiveerde entiteiten stil opnieuw. Draai daar na elke registratieronde de controlequery hierboven, of neem de betreffende tabellen niet op in `@Tables`. Welke versie een configdb heeft, zie je aan de procedure zelf: vanaf `4dd41cf` staat er het commentaar "IsActive only applies to new entities".
- `sp_UpsertDataSource` zet `DataSource.IsActive` nog wel op 1 (`@IsActive BIT = 1`, en `PL_TOOLING_POST_ASQL_TO_FMD` geeft `IsActive=True` mee). Dat heeft geen effect op de load, want geen view filtert erop (zie de tabel hierboven).

**Heractiveren.** Zet `IsActive = 1` terug. Landingzone-bestanden die vóór de deactivering al geland waren (`IsProcessed = 0`), worden dan eerst verwerkt, op volgorde van bestandsnaam.

**Status:** vastgesteld (view-definities, `sp_UpsertLandingzoneBronzeSilver`, `sp_UpsertDataSource`, `PL_TOOLING_POST_ASQL_TO_FMD`; grep op `IsActive` over alle pipeline-JSON, notebooks en procedures). Niet als procedure getest in de eigen omgeving; dat gebeurt in `testplan-trial.md` (T-C03 t/m T-C05). *Correctie 2026-09-25 (review 1 F3, review 2 M-F3): de vorige versie zette `Connection`/`DataSource` op 0 en stelde dat "de views op elk niveau filteren". Beide statements hebben geen effect op de load.*

## Historische bugs/fixes (ter context, al opgelost)

- Hardcoded workspace-/artifact-GUID's in `linkedService`-secties blokkeerden eerder Deployment-Pipeline-promotie (`WorkspaceNotFound`/`EntityNotFound`). **Opgelost:** alle referenties lopen nu via de Variable Library.
- `ConnectionGuid`-parameter had een echte, niet-Bitmetric GUID als `defaultValue`. **Opgelost:** vervangen door sentinel `00000000-0000-0000-0000-000000000001`.
- `GROUP BY`-querybug bij het invoeren van `LoadGroup`: het filter werd ná `group by DatasourceType` geplakt in plaats van in de WHERE. Dit speelde in de 9 `PL_FMD_LDZ_COMMAND_*`-pipelines, niet in `Copy metadata`. Het was een fout in een eigen transformatie, gevonden bij het nakijken van de diffs (`bronnen/claude-code-transcripten/markdown/2026-09-11_fmd-agents-configuratie-vastleggen.md` r.7717). **Opgelost.**
