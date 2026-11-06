# Registratie van bronnen en entiteiten (handmatig en bulk)

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

*Bijgewerkt 2026-10-13 (ADR-018, FMD_FRAMEWORK #60, #63 en #64):* er is een notebookroute bijgekomen.
- Je registreert met `NB_REGISTRATIE` in de CONFIG-workspace, en kunt een bron eerst ontdekken met
  `PL_FMD_DISCOVER_SOURCE`.
- Die route is nu aanbevolen. Hij vervangt het lijstsjabloon en, voor nieuwe bronnen met veel tabellen,
  `PL_TOOLING_POST_ASQL_TO_FMD`.
- Werkwijze en controles: `03_technische_documentatie/05_INTEGRATION/02_configdb-registratie.md`, Route 3.
- **Status:** *getest in eigen omgeving*, 2026-10-13.
- *Bijgewerkt 2026-10-15 (`FMD_FRAMEWORK#71`, ADR-018 nu *Accepted*):*
  - het lijstsjabloon is verwijderd;
  - `PL_TOOLING_POST_ASQL_TO_FMD` wordt niet meer uitgerold (een bestaande installatie houdt hem; de bestanden blijven in de repo vanwege upstream);
  - `NB_REGISTRATIE` accepteert `environments=["DEV_<NAAM>"]` voor een developer-workspace, met de bronbindingen van D. *Getest in eigen omgeving*, trial-Dev, zie `testplan-trial.md` T-C11 (de notebookroute zelf niet gedraaid).

De routes hieronder blijven bestaan voor uitzonderingen.

## Handmatige registratie — de drie kern-stored-procedures

Alle drie bestaan exact zoals verwacht in de fork-code.

**`integration.sp_UpsertConnection`**
**Bron:** `FMD/src/Config_Database/integration/StoredProcedures/sp_UpsertConnection.sql`. **Status:** vastgesteld.
```sql
,@ConnectionGuid UNIQUEIDENTIFIER
,@Name nvarchar(200)
,@Type nvarchar(50)
,@IsActive bit
```
Eenvoudige IF EXISTS/ELSE-upsert op `ConnectionGuid`. Geen output-select, geen `GatewayType`/`DatasourceReference`-parameter — die kolommen zijn dus alleen via een directe INSERT/UPDATE te vullen, niet via deze sp.

**`integration.sp_UpsertDataSource`**
**Bron:** `FMD/src/Config_Database/integration/StoredProcedures/sp_UpsertDataSource.sql`. **Status:** vastgesteld.
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
Upsert-logica op `@DataSourceId` (0 = insert); retourneert `DataSourceId` via `SELECT`. `@LoadGroup` is een fork-eigen toevoeging.

**`integration.sp_UpsertLandingzoneBronzeSilver`**
**Bron:** `FMD/src/Config_Database/integration/StoredProcedures/sp_UpsertLandingzoneBronzeSilver.sql`. **Status:** vastgesteld.
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
Dit is de "3-in-1"-proc: gebruikt `@WorkspaceGuid` om via `sp_GetLakehouse` de GUID's van `LH_DATA_LANDINGZONE`, `LH_BRONZE_LAYER`, `LH_SILVER_LAYER` binnen die workspace op te zoeken (deze lakehouse-namen moeten dus letterlijk zo heten en al geregistreerd staan in `integration.Lakehouse`), doet vervolgens 3× een `MERGE` (Landingzone → Bronze → Silver) binnen één transactie (`BEGIN TRY`/`BEGIN TRANSACTION`, rollback bij fout), en retourneert alle drie de gegenereerde ID's. Bronze en Silver krijgen `IsActive=1` en `FileType='Delta'` hardcoded (niet als parameter).

Exacte parameter**volgorde** komt 1-op-1 overeen met het upstream wiki-voorbeeld — geen divergentie fork vs. upstream op dit punt.
**Bron:** `bronnen/fmd-upstream-wiki/wiki-clone/Adding-a-new-entity.md`. **Status:** vastgesteld.

**Aanvullend gevonden (niet expliciet door gebruiker genoemd, wel relevant):** losse `sp_Upsert*`-procs per laag bestaan ook: `sp_UpsertLandingzoneEntity`, `sp_UpsertBronzeLayerEntity`, `sp_UpsertSilverLayerEntity`, plus `sp_UpsertBronzeCleansingRule`/`sp_UpsertSilverCleansingRule` (deze twee THROWEN `50000` als de entiteit nog niet bestaat — puur update, geen insert) en `sp_UpsertLakehouse`/`sp_UpsertWorkspace`/`sp_UpsertPipeline` (voor het registreren van de Fabric-items zelf). **Status:** vastgesteld.

**Read-only lookup-procs** die de upsert-flow ondersteunen: `sp_GetConnection` (by Guid), `sp_GetDataSource` (by Name — let op: zoekt alleen op `Name`, niet op combinatie met Type/Connection, dus bij dubbele namen tussen bronnen kan dit de verkeerde teruggeven), `sp_GetLakehouse` (by Workspace+Name, OUTPUT-param), `sp_GetLandingzoneEntity`, `sp_GetBronzeLayerEntity`, `sp_GetSilverLayerEntity`. **Status:** vastgesteld (bestaan+gedrag); het risico bij dubbele DataSource-namen is een eigen constatering, niet expliciet zo in de bron benoemd — **open vraag** of dit in de praktijk al eens is voorgekomen.

## Bulkregistratie — `PL_TOOLING_POST_ASQL_TO_FMD`

*Bijgewerkt 2026-10-15 (`FMD_FRAMEWORK#71`): de setup rolt deze pipeline niet meer uit; zie hierboven. De beschrijving hieronder blijft kloppen voor een installatie die hem al heeft.*

**Bron:** `FMD/src/PL_TOOLING_POST_ASQL_TO_FMD.DataPipeline/pipeline-content.json`. **Status:** vastgesteld dat de pipeline bestaat en dit doet.

**Wat de pipeline doet, activity voor activity:**
1. **`Copy metadata`** (Copy-activity, bron = `AzureSqlSource` met dynamische `sqlReaderQuery`): draait een T-SQL-query tegen de **bron**-Azure SQL-database die voor elke tabel/view in parameter `@Tables` (comma-separated schema.tabel-lijst) automatisch kolommappings + primary keys afleidt (via `sys.objects`/`sys.columns`/`sys.sql_expression_dependencies`, ook voor 1-op-1 views) en als JSON wegschrijft naar `Files/metadata/{DatasourceName}.json` in `LH_DATA_LANDINGZONE`.
2. **`LKP DATASOURCE`** → `sp_GetDataSource` (by Name) en **`LKP CONNECTION`** → `sp_GetConnection` (by Guid).
3. **`LKP_INSERT_DATASOURCE`** → `sp_UpsertDataSource` met `Namespace`/`Name`/`Type` uit de pipeline-parameters, `IsActive=True`.
4. **`LKP_ENTITIES`**: leest het net weggeschreven metadata-JSON terug.
5. **`ForEach LZE`**: loopt over elke entiteit uit dat JSON-bestand en roept per entiteit `sp_UpsertLandingzoneBronzeSilver` aan.

**Pipeline-parameters:**
```
ConnectionGuid       (string, GUID van de bron-Azure SQL-connectie)
DatasourceName       (string, bv. 'WideWorldImporters')
DatasourceNamespace  (string, bv. 'wwi')
DatasourceType       (string, 'ASQL_01' of 'ASQL_02'; een andere waarde wordt stil overgeslagen, zie 07_extension-points.md §1)
Tables               (string, comma-separated SQL-literal-lijst zoals ''schema.tabel'',''schema.tabel2'')
```
**Correctie (repo-audit 2026-09-22):** deze lijst noemde in een eerdere versie ook een los parameter `Data_WorkspaceGuid`. Dat is niet meer juist — de daadwerkelijke `parameters`-sectie van `pipeline-content.json` bevat alleen de vijf hierboven genoemde parameters. De workspace-GUID komt niet (meer) uit een pipeline-parameter, maar uit de libraryVariable `fmd_data_workspace_guid` in `VAR_CONFIG_FMD` — zie de sectie "Historische bugs/fixes" hieronder, die dit al correct beschreef, waardoor de parameterlijst hierboven er tot nu toe niet meer mee overeenkwam.

### Casing "mismatch" in `PL_TOOLING_POST_ASQL_TO_FMD` — statische analyse door live test weerlegd

De `Copy metadata`-query genereert JSON met **camelCase**-veldnamen (`sourceName`, `sourceSchema`, `primaryKeys`, `columnMappings`, `isView`). In `ForEach LZE` gebruikt de `storedProcedureParameters` van `sp_UpsertLandingzoneBronzeSilver` echter PascalCase dot-notation (`item().SourceName` etc.) en missen `TargetName`/`TargetSchema` de normale `{"value": "...", "type": "Expression"}`-omhulling. Op basis hiervan werd op 2026-09-22 (code-inspectie, commit `703017b`) verondersteld dat dit tot foutieve registratie of een harde runtime-fout zou leiden.

**Weerlegd door empirische test (2026-09-22, Mitchell, job `50b62157`, `FMDTRIAL CODE (D)`, tegen de ongewijzigde pipeline-versie):** *Noot (2026-09-25, review 2): job `50b62157` en de verklaring zijn niet terug te vinden in `bronnen/` (het nieuwste transcript is van 15-09). Mitchell handhaaft het label op basis van de test zelf.* de pipeline liep volledig door zonder fouten, en de configdatabase bevat na afloop de correcte, echte tabelnamen (niet de letterlijke tekst `@item().SourceName`). Gecorrigeerd begrip: Fabric's expressietaal evalueert `@`-voorvoegsel-strings kennelijk ook zonder expliciete Expression-wrapper, en dot-notation-toegang is case-insensitief tegen camelCase JSON-properties. **Er is dus geen bug** — de pipeline werkt zoals hij is. Volledige toelichting en methodologische les (statische codeanalyse is geen vervanging voor empirisch testen) in `output/03_technische_documentatie/05_INTEGRATION/03_operationele-aandachtspunten.md` punt 1.
**Bron:** `FMD/src/PL_TOOLING_POST_ASQL_TO_FMD.DataPipeline/pipeline-content.json`, activity `ForEach LZE` vs. `Copy metadata`. **Status:** getest in eigen omgeving — géén bug bevestigd.

### Historische bugs/fixes rond deze pipeline (wél expliciet in de transcripten gedocumenteerd)

- Hardcoded, niet-eigen workspace-/artifact-GUID's in de `linkedService`-secties blokkeerden Deployment-Pipeline-promotie (`WorkspaceNotFound`/`EntityNotFound`). Opgelost: alle referenties lopen nu via de Variable Library.
  **Bron:** `bronnen/claude-code-transcripten/markdown/2026-09-15_requestvalidationfailed-deployment-pipeline-error.md`; bevestigd in `bronnen/notities/fmd-open-actions.md` punt 5. **Status:** getest in eigen omgeving.
- Parameter `ConnectionGuid` had als `defaultValue` een echte, niet-Bitmetric connectie-GUID uit de upstream-tenant. Opgelost door de default te vervangen door de sentinel `00000000-0000-0000-0000-000000000001`.
  **Bron:** `bronnen/claude-code-transcripten/markdown/2026-09-15_fmd-framework-afwijkingen-triage.md`, commit `aba7f72`. **Status:** vastgesteld in code (een codewijziging, geen test in de tenant; correctie 2026-09-25, review 2 steekproef 12).
- Huidige stand: workspace/lakehouse-referenties lopen via `VAR_CONFIG_FMD`-libraryvariabelen `fmd_data_workspace_guid`/`fmd_landingzone_lakehouse_guid` (Dev als default, Test/Prod als valueSet-override) — zelf ook weer een toepassing van het Variable-Library-patroon. Dit is ook de reden dat `Data_WorkspaceGuid` niet meer als los parameter van **deze pipeline** (`PL_TOOLING_POST_ASQL_TO_FMD`) voorkomt (zie de correctie in de parameterlijst hierboven). De load-pipelines (`PL_FMD_LOAD_ALL`, `_LANDINGZONE`, `_BRONZE`, `_SILVER`) hebben de parameters `Data_WorkspaceGuid` en `LoadGroup` nog wel.
  **Bron:** `bronnen/notities/fmd-open-actions.md`, punt 5; herbevestigd tegen `pipeline-content.json` in de repo-audit van 2026-09-22. **Status:** vastgesteld.
- Zijdelingse bug bij het toevoegen van `LoadGroup`: in de 9 `PL_FMD_LDZ_COMMAND_*`-pipelines (niet in `PL_TOOLING_POST_ASQL_TO_FMD`) werd het `LoadGroup`-filter aanvankelijk ná de `GROUP BY` geplakt i.p.v. in de `WHERE`, wat ongeldige SQL opleverde. Het was een fout in Claude's eigen transformatie, gevonden bij het diffen, en gefixt vóór de merge.
  **Bron:** `bronnen/claude-code-transcripten/markdown/2026-09-11_fmd-agents-configuratie-vastleggen.md`. **Status:** vastgesteld (tijdens eigen ontwikkelwerk; correctie 2026-09-25, review 2 steekproef 13).
- Verwant (ander bulk-registratiescript, niet deze pipeline zelf, gevonden buiten de opgegeven leeslijst): een handmatig bulk-registratiescript riep `sp_UpsertDataSource` aan met **positionele** parameters, waardoor een bedoelde `1` in `@LoadGroup` terechtkwam in plaats van `@IsActive`. Functioneel bleef het werken (IsActive viel terug op zijn default), maar `LoadGroup` kreeg onbedoeld de waarde `'1'`. Dit is het dichtstbijzijnde gevonden bewijs voor de claim "exacte parameterformaat van de bulk-pipeline" — het gaat niet over `PL_TOOLING_POST_ASQL_TO_FMD` zelf, maar over een los script met dezelfde soort kwetsbaarheid (positionele i.p.v. benoemde parameters).
  **Bron:** `bronnen/claude-code-transcripten/markdown/2026-09-15_fmd-trial-capacity-testing-stappen.md` (buiten de aanvankelijk opgegeven leeslijst voor dit onderzoek). **Status:** getest in eigen omgeving (incident vastgesteld), maar **open vraag** of dit exact is wat `Promp.txt` bedoelde met "casing-inconsistenties tussen bulk- en handmatige registratie" — zie `geleerde-lessen.md`.

## Drie "live defects" rond cross-workspace-referenties (Gold-laag, niet registratie zelf — apart genoteerd)

1. `InvokePipeline`-target wees naar Dev i.p.v. de juiste omgeving.
2. `PBISemanticModelRefresh`-target wees naar Dev.
3. Direct Lake-pad (semantisch model) wees naar Dev — resultaat: **Productie-rapport toonde Dev-data.**

Root cause: Fabric slaat cross-workspace-referenties op als letterlijke object-ID's die nooit rebinden, noch bij branch-out, noch bij Deployment Pipeline-promotie (alleen same-workspace-referenties rebinden via logische ID's).
**Bron:** `bronnen/notities/fmd-cross-workspace-references.md`; `bronnen/claude-code-transcripten/markdown/2026-09-11_fmd-agents-configuratie-vastleggen.md`. **Status:** vastgesteld.

Fix (end-to-end getest, 2026-09-12): notebooks lezen hun lakehouse-ID via `%%configure`/`notebookutils.variableLibrary.getLibrary(...)` uit een Variable Library i.p.v. hardcoded; pipelines gebruiken `libraryVariables`+`@pipeline().libraryVariables.X`; semantische modellen kunnen zelf geen Variable Library lezen — personal workspaces vereisen handmatige Direct Lake-pointer-swap vóór commit, Test/Prod vereisen een Deployment Pipeline **deployment rule** (portal-only, geen REST API — apart openstaand actiepunt, zie `operations.md`).
**Status:** getest in eigen omgeving ("proven end-to-end").

## Aanvullende open actiepunten uit `fmd-open-actions.md`

- **Actiepunt #4:** `PL_MASTER_ORCHESTRATION` hardcodet nog steeds zijn cross-workspace-target — niet omgezet naar library-variabelen zoals `PL_FINANCE_LOAD_GOLD` dat wel is. Elke nieuwe redeploy vanuit Dev introduceert de stale referentie opnieuw. **Status:** vastgesteld/open. *(Let op: deze naam is afkomstig uit Bitmetrics eigen notitiebestand `fmd-open-actions.md`, niet uit de FMD_FRAMEWORK-repo zelf — zie de gecorrigeerde sectie "Orchestratiepatroon" in `operations.md`, waar de daadwerkelijke fork-pipeline `PL_FMD_LOAD_ALL`/`PL_FMD_ORCHESTRATION` heet. Mogelijk gaat het hier om een interne/andere pipeline; nader te verifiëren of dit hetzelfde item betreft.)*
- **Actiepunt #6:** vermoeden dat `PL_FMD_LDZ_COMMAND_FTP` per ongeluk `PL_FMD_LDZ_COPY_FROM_ADF` aanroept i.p.v. `PL_FMD_LDZ_COPY_FROM_FTP_01`. **Status: opgelost/vals alarm** (geverifieerd 2026-09-22, commit `703017b`, zie `output/03_technische_documentatie/05_INTEGRATION/03_operationele-aandachtspunten.md` punt 4). De InvokePipeline-activity binnen `PL_FMD_LDZ_COMMAND_FTP` heeft het misleidende label `PL_FMD_LDZ_COPY_FROM_ADF`, maar het daadwerkelijk aangeroepen `pipelineId` (`4972831f-6320-ab73-46e2-336d0bc59199`) komt exact overeen met de `logicalId` van `PL_FMD_LDZ_COPY_FROM_FTP_01`. Functioneel correct, puur een verwarrend activity-label.

## Verschillen fork vs. upstream-wiki (registratie-specifiek)

Zie ook `configdb.md`. Upstream `Data-Integration.md` beschrijft directe INSERT-statements als hoofdpad voor Connection/DataSource; de fork heeft ook volwaardige upsert-sp's beschikbaar die niet als aanbevolen pad in die wiki-pagina staan. **Status:** vastgesteld.
