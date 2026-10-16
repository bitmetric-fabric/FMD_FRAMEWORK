# ADR-018: Bronnen registreren via een notebook, niet via `sqlcmd`

Status: Accepted (2026-10-15, akkoord Mitchell; was Proposed sinds 2026-10-13)
Datum: 2026-10-13

## Context

`templates/registratie/registreer_entiteiten.sql` registreert bronnen en entiteiten via
`sqlcmd -v DataWorkspace=… Environment=…`. Dat geeft drie problemen:

- **De omgeving kan verkeerd gekozen worden.** `DataWorkspace` is een vrije tekst met het
  klantprefix (`"<PREFIX> INTEGRATION DATA (T)"`); een tikfout of het verkeerde prefix registreert
  in de verkeerde omgeving, zonder dat iets dat tegenhoudt (E-R5, eindcontrole 2026-10-08).
- **Buiten `sqlcmd` werkt het sjabloon niet.** De query-editor van de portal heeft geen
  SQLCMD-modus (aanname), en rookproef 3 laat W1 juist in de portal doen.
- **Een nieuwe bron met veel tabellen is handwerk.** Voor Azure SQL bestaat
  `PL_TOOLING_POST_ASQL_TO_FMD`, die de tabellenlijst wel uit de bron haalt, maar alleen als
  full load registreert, alleen toevoegt, en niet voor Snowflake werkt.

## Beslissing

Registreren gaat via een notebook, `NB_REGISTRATIE`, in de **CONFIG-workspace** (naast
`SQL_FMD_FRAMEWORK`), niet via een deployment pipeline.

- **Waarom CONFIG, niet CODE:** de lijsten horen bij de installatie, niet bij een omgeving. Een
  notebook in CODE gaat mee in de deployment pipeline en moet dus per omgeving opnieuw; een
  notebook in CONFIG registreert direct in elke omgeving vanuit één plek.
- **De logica staat in de configdb**, niet in het notebook: `integration.sp_RegisterEntities`
  neemt dezelfde `@Sources`/`@Entities`-lijsten als het sjabloon (nu als JSON), met dezelfde
  controles en dezelfde "alles of niets"-transactie. Het notebook (`NB_FMD_REGISTRATION_FUNCTIONS`,
  frameworkeigendom) is een dunne aanroep; `NB_REGISTRATIE` (klanteigendom, de setup overschrijft
  het niet) bevat alleen de lijsten. *Bijgewerkt 2026-10-16:* `NB_REGISTRATIE` bevat nu de aanroep van de editor
  (zie de aanvulling hieronder) en geen lijsten meer.
- **De omgeving kiest een workspace, niet andersom.** De procedure krijgt `@Domain` (bijvoorbeeld
  `INTEGRATION` of `FINANCE`) en `@Environment` (D/T/A/P), en zoekt de ene DATA-workspace waarvan de
  naam `<Domain> DATA` bevat, met het bijpassende achtervoegsel en een actieve `LH_DATA_LANDINGZONE`.
  Bij 0 of meer dan 1 treffer volgt een fout. Je typt het domein, niet de volledige workspacenaam met
  het klantprefix: dat voorkomt zowel de prefix-typefout als de omgevingsmismatch van E-R5.
  *Correctie, getest in FMD_TRIAL 2026-10-13:* de eerste versie zocht op een exacte prefix-match
  (`LIKE '<Domain> DATA%'`) en vond daardoor niets, want elke workspace heeft het klantprefix vóór
  het domein (`"FMD_TRIAL INTEGRATION DATA (D)"`). Gefixt naar een deelstring-match.
- **Ook een developer-workspace, `DEV_<NAAM>`** (aanvulling 2026-10-15, op verzoek van Mitchell).
  `environments=["DEV_MITCHELL"]` zoekt de DATA-workspace `DEV_MITCHELL_<prefix>_<DOMEIN>_DATA` (ADR-011
  noemt `DEV_<NAAM>_<PREFIX>_INTEGRATION_DATA`) en registreert daarin met de bindingen van D: een
  developer-workspace leest uit dezelfde bron als Dev.
  - *Reden:* zonder dit moest een developer tijdens een feature een los SQL-script gebruiken, zonder
    controles of dry run, en dezelfde entiteit daarna nog eens in de lijst zetten voor D. Nu gebruik je
    dezelfde lijst in elke stap: `DEV_<NAAM>` tijdens de feature, `D` na de merge, `T` en `P` voor de
    promotie.
  - *Beperking:* alleen voor `domain="INTEGRATION"`. De DATA-workspace van een business domain heet
    `DEV_<NAAM>_<PREFIX>_DATA`, zonder domeinnaam, en bevat geen landing zone.
  - De DataSource-rijen worden gedeeld met D (één rij per connectie, database en type): een gewijzigde
    `LoadGroup` of `Namespace` vanuit een `DEV_`-run geldt ook voor D.
  - De naam mag alleen letters, cijfers, `_` en `-` bevatten, omdat hij in een `LIKE`-patroon terechtkomt.
  - De workspace moet al in de configdb staan (`sp_UpsertWorkspace` en `sp_UpsertLakehouse`).
- **`dry_run=True` is de voorgeschreven eerste stap.** De procedure voert alle controles en de
  registratie echt uit en draait dan terug, en toont per entiteit of hij nieuw, gewijzigd of
  ongewijzigd is, plus de entiteiten die in die workspace actief zijn maar niet in de lijst staan.
- **Geen apart logspoor.** CONFIG is niet aan Git gekoppeld (*vastgesteld*,
  `output/03_technische_documentatie/10_operations.md`, getest 2026-10-11), dus de lijst heeft geen
  PR-review zoals bij het sjabloon. Die review was een afspraak, geen controle: niets dwong af dat
  het uitgevoerde script het gereviewde was. De bescherming zit in de controles, de dry run en de
  transactie; de configdb zelf is de huidige stand, en het notebook heeft de versiegeschiedenis van
  Fabric. Een logtabel pas als een klant om een audittrail vraagt.
- **Interactieve editor** (aanvulling 2026-10-16, op verzoek van Mitchell). `NB_REGISTRATIE` onderhoudt geen
  lijsten meer: de configdb is de enige plek waar de registratie staat. De editor (`registration_ui()`, in
  `NB_FMD_REGISTRATION_FUNCTIONS`, frameworkeigendom, in CONFIG) toont bronnen, ontdekte tabellen, primary keys en
  cleansing rules in widgets, leest de huidige stand uit de configdb en roept `register()` ongewijzigd aan. Alle
  wijzigingen blijven in het geheugen; registreren kan pas na een proefdraai op precies dezelfde wijzigingen en een
  bevestiging. Tab 3 toont per tabel wat er wordt geregistreerd (doel, bestand, laadwijze, primary key, actief,
  historie, cleansing-regels), met wat afwijkt van de huidige registratie gemarkeerd.
  - *Eén notebook voor bibliotheek en scherm* (*bijgewerkt 2026-10-16*). De editor stond kort in een eigen notebook,
    `NB_FMD_REGISTRATION_UI`; dat is nooit gemerged of uitgerold buiten onze testinstallaties en is samengevoegd met
    `NB_FMD_REGISTRATION_FUNCTIONS`. *Reden:* `NB_REGISTRATIE` doet één `%run`, en drie items in CONFIG voor één taak is
    te veel. De naam `NB_FMD_REGISTRATION_FUNCTIONS` blijft, omdat bestaande kopieën van `NB_REGISTRATIE` (klanteigendom,
    de setup overschrijft ze niet) al `%run NB_FMD_REGISTRATION_FUNCTIONS` doen. Nadeel: de naam dekt het scherm niet
    helemaal; de kop van de notebook zegt het.
  - *Lezen:* er is geen procedure die teruggeeft wat geregistreerd is. De editor leest met `SELECT`
    (`read_config`, weigert alles behalve `SELECT`/`WITH`) de tabellen die `sp_RegisterEntities` zelf schrijft:
    `LandingzoneEntity`, `BronzeLayerEntity`, `SilverLayerEntity`, `DataSource`. De DATA-workspace zelf bepaalt de
    procedure: een dry run met lege lijsten, zodat de zoekregels voor domein en omgeving op één plek blijven.
    Schrijven gaat uitsluitend via `register()`. Een leesprocedure in de dacpac is de nettere vorm; dat is niet gedaan
    omdat het een nieuwe dacpac vraagt.
  - *Alle velden mee:* een weggelaten `IsActive` wordt 1 en een weggelaten `IsHistorized` 0 (ADR-016). De editor
    stuurt daarom bij elke tabel die hij registreert alle velden mee, ook die hij niet wijzigde. Een bron en een tabel die
    niet wijzigen worden niet meegestuurd.
  - *Cleansing rules per laag:* ongewijzigd laten (het veld ontbreekt), vervangen (de lijst is de waarheid) of alles
    verwijderen (`[]`). Een leeg of nog niet geladen paneel verwijdert dus nooit iets. De functies en parameters zijn een
    spiegel van de docstrings in `NB_FMD_DQ_CLEANSING` (`CLEANSING_FUNCTIONS`): een functie die niet is ingebouwd wordt
    als JSON bewerkt.
  - *De bron-alias* (`ERP`, `AW`) bestaat alleen in de lijsten, niet in de database. De editor leidt hem af uit de
    namespace.
  - *Vastlegging:* na het registreren toont de editor het resultaat als `table("""...""")`-tekst om te bewaren. Er is
    geen logtabel; zie "Geen apart logspoor".
  - *Getest in eigen omgeving* (FMD_EIND, 2026-10-16): laden, bron, ontdekte tabellen, markeren, overzicht, Controleren en
    Proefdraaien (teruggedraaid), en het starten van `PL_FMD_DISCOVER_SOURCE` vanuit de editor, zie hieronder.
    Geregistreerd is er niets. Bron: `testplan-trial.md`. Eerdere versie van deze regel (2026-10-16, eerder die dag):
    "niet getest in Fabric; starten van de pipeline vanuit de editor niet gebouwd".
  - *Ontdekking starten vanuit de editor* (*gebouwd 2026-10-16*): de knop "Ontdekking starten (pipeline)" op tab 2, en
    `start_discovery(connectie, database, schema_filter, domain, environment)` los aan te roepen. Beide zoeken de
    CODE-workspace bij de DATA-workspace van de gekozen omgeving (zelfde naam met `DATA` vervangen door `CODE`, de guid uit
    `integration.Workspace`; de `WorkspaceGuid` in `integration.Pipeline` is die van de DATA-workspace en is daarvoor niet
    bruikbaar), zoeken `PL_FMD_DISCOVER_SOURCE` op naam, starten hem met `POST …/jobs/instances?jobType=Pipeline` en
    polliten op `Location` (10 s, time-out 20 min). Daarna laadt de editor de ontdekte tabellen. Het token is dat van de
    gebruiker die het notebook draait (`getToken` met de Power BI-audience); die heeft dus een rol nodig die items in de
    CODE-workspace mag uitvoeren. *Getest in eigen omgeving* (FMD_EIND, 2026-10-16, bron AW, schemafilter leeg): run
    `805163b3-17db-4813-9a60-d04fb13c63ae` in `FMD_EIND INTEGRATION CODE (D)`, `Completed` na 1 min 44 s; 96 tabellen
    ontdekt.
    - *Getest in eigen omgeving, omgeving T en P* (FMD_EIND, 2026-10-16, via de knop): runs
      `00d57544-9b4b-47e3-9ae6-fccb5d6da7ac` (`FMD_EIND INTEGRATION CODE (T)`) en
      `cb1c01c9-7104-4bf3-9e01-30cb2aaf90d8` (`FMD_EIND INTEGRATION CODE`, productie, zonder achtervoegsel), beide
      `Completed`. De bron zat in T en P nog niet in de configdb; ik heb hem alleen in het geheugen toegevoegd (tab 1),
      want de ontdekking heeft alleen connectie en database nodig.
    - *Getest in eigen omgeving, Snowflake-tak* (FMD_TRIAL, 2026-10-16, `CON_TRIAL_SNOWFLAKE` / `FMD_BRON`,
      `SchemaFilter = TPCH`): de pipeline is rechtstreeks via de API gestart, niet via de editor (de notebooks in de trial
      hebben de nieuwe editor niet). Run `47d555a8-ceb4-4fd4-97f1-4dcd6d50aa9e` in `FMD_TRIAL INTEGRATION CODE (D)`,
      `Completed` na 1 min 30 s. In `integration.DiscoveredEntity` staan 7 tabellen van `TPCH` met kolommen en types
      (bijvoorbeeld `C_CUSTKEY NUMBER`, `C_NAME TEXT`); `PrimaryKeys` is bij alle leeg, wat klopt voor deze
      voorbeeldtabellen zonder PK-constraint. Hiermee is de eerder ongeteste Snowflake-tak voor deze bron bevestigd.
    - *`DEV_<NAAM>`, aangepast na een test* (2026-10-16): in FMD_TRIAL staat alleen `DEV_MITCHELL_TRIAL_INTEGRATION_DATA` in
      `integration.Workspace`, niet `…_CODE`, en `DEV_MITCHELL_TRIAL_INTEGRATION_CODE` heeft geen
      `PL_FMD_DISCOVER_SOURCE`. De eerste opzet (DATA→CODE-naamregel op de DEV-workspace) kan daar dus niet werken. Nu
      draait `DEV_<NAAM>` de ontdekking in de CODE-workspace van D: de bronbinding is die van D en
      `integration.DiscoveredEntity` heeft geen omgevingskolom. *Alleen lokaal getest* (omgeving doorgegeven aan de
      workspace-resolutie: `DEV_` wordt `D`, `T`, `D` en `P` blijven zichzelf); niet in Fabric, want in FMD_EIND staat geen
      developer-workspace.
    - *Gebruiker met alleen een leesrol, niet te testen met één identiteit.* Volgens de documentatie van Microsoft starten
      Admin, Member en Contributor een run en kan Viewer alleen volgen; voor sommige itemtypen (CopyJob, DataBuildToolJob)
      staat Member als minimum, en de pagina van de algemene API noemt geen rol (*Run On Demand Item Job*, Microsoft
      Learn, 2026-10-16). `start_discovery` geeft bij HTTP 401 of 403 nu een duidelijke melding (rol Contributor of
      hoger nodig) in plaats van een kale HTTP-fout; die melding is lokaal getest met een nep-403. *Aanname:* een
      Viewer krijgt die 403.
- **Ontdekken voor een bron met veel tabellen:** `PL_FMD_DISCOVER_SOURCE`, in de **CODE**-workspace
  (niet CONFIG, zie Alternatieven), leest de metadata van de bron (tabellen, kolommen, primary
  keys) en zet die in `integration.DiscoveredEntity`. `print_entity_list()` in het notebook maakt
  daar kant-en-klare regels van om te plakken. `sp_RegisterEntities` controleert een regel tegen
  die metadata wanneer die er is: de naam moet bestaan (bij Snowflake met exacte hoofdletters,
  ADR-014), de PK-kolommen moeten bestaan, en de watermarkkolom moet bij Snowflake `DATE` of
  `TIMESTAMP` zijn. Discovery is optioneel: zonder gegevens voor die bron slaat de controle over.

## Alternatieven

- **De pipeline in CONFIG, naast het notebook.** Eerst gekozen, toen verworpen tijdens het bouwen:
  elke bestaande pipeline die de configdb aanspreekt doet dat via `VAR_CONFIG_FMD`
  (`fmd_config_workspace_guid`/`fmd_config_database_guid`, ADR-009/010), en die Variable Library
  bestaat alleen in elke CODE-workspace. CONFIG heeft geen self-reference library, en die erbij
  bouwen is nieuw, ongetest terrein. `PL_FMD_DISCOVER_SOURCE` staat daarom in CODE, net als
  `PL_TOOLING_POST_ASQL_TO_FMD`; `NB_REGISTRATIE` (in CONFIG) start hem via de Fabric API in de
  gekozen CODE-workspace en pollt op `Location` (akkoord Mitchell, 2026-10-13; gebouwd en getest 2026-10-16,
  zie "Interactieve editor").
- **Alles in het notebook, niets in de configdb.** Verworpen: dan bestaan er twee versies van de
  controles (notebook en sjabloon), die uit elkaar lopen. De logica hoort op één plek.
- **Een logtabel per run.** Verworpen (akkoord Mitchell, 2026-10-13): de configdb is zelf al de
  huidige stand, en de dry run laat vooraf zien wat er verandert. Een logtabel voegt niets toe
  zolang niemand om een audittrail vraagt.
- **Het `sqlcmd`-sjabloon laten staan.** Verworpen: lost geen van de drie problemen op.

## Gevolgen

- `templates/registratie/registreer_entiteiten.sql` en `PL_TOOLING_POST_ASQL_TO_FMD` vervallen.
  ~~Verwijderen pas na akkoord Mitchell.~~ *Bijgewerkt 2026-10-15, na akkoord van Mitchell:*
  - het sjabloon is verwijderd; de uitleg van de velden staat nu in de docstring van `register()` en in
    `NB_REGISTRATIE`;
  - `PL_TOOLING_POST_ASQL_TO_FMD` staat niet meer in `config/item_deployment.json`, dus de setup rolt
    hem niet meer uit. De bestanden in `src/` blijven staan, want de pipeline bestaat ook in
    `edkreuk/FMD_FRAMEWORK`: verwijderen geeft bij elke upstream-sync een mergeconflict. Een bestaande
    installatie houdt het item, want de setup verwijdert niets.
- De setup plaatst `NB_FMD_REGISTRATION_FUNCTIONS` en `NB_REGISTRATIE` in CONFIG (`config/data_deployment.json`), en
  `PL_FMD_DISCOVER_SOURCE` in elke CODE-workspace (`config/item_deployment.json`). `NB_REGISTRATIE` staat in
  `CUSTOMER_OWNED_ITEMS`. *Gevolg van place-once (2026-10-16):* een opgeschoonde `NB_REGISTRATIE` bereikt alleen nieuwe
  installaties. Een bestaande installatie houdt zijn kopie; die blijft werken zolang `NB_FMD_REGISTRATION_FUNCTIONS`
  bestaat, maar toont de oude opzet en kent de knop alleen als hij zelf de nieuwe cellen overneemt (of het item wordt
  verwijderd en opnieuw geplaatst). Bijgewerkt is `FMD_EIND INTEGRATION CONFIG`; trial, GR en andere installaties niet.
- Een opgeslagen notebook kan `metadata.widgets` meenemen: de widgetstatus van eerdere runs (in `NB_REGISTRATIE` van
  FMD_EIND 465 KB). Zet dat niet mee in een nieuw geplaatste kopie; de bron in `src/` heeft het niet.
- Draaiboek §A.4a, runbook stap 4 en `10_operations` moeten naar het notebook verwijzen in plaats
  van naar het sjabloon.
- De Snowflake-tak van `PL_FMD_DISCOVER_SOURCE` (meerdere statements in één Script-activiteit, de
  vorm van `resultSets` daarvan, en de `OBJECT_CONSTRUCT`/`ARRAY_AGG`-query) is **niet getest**.

## Test

**Getest in FMD_TRIAL, 2026-10-13** (`sp_RegisterEntities`, `sp_UpsertDiscoveredEntities`,
`sp_GetDiscoveredEntities`, `integration.DiscoveredEntity` tijdelijk met de hand aangemaakt op
`SQL_INTEGRATION_FRAMEWORK`, daarna weer verwijderd; zie `testplan-trial.md` voor de test-ID's):

- Workspace-resolutie op `FMD_BRON`/`CON_TRIAL_SNOWFLAKE` (DataSourceId 9): `@Domain='INTEGRATION'`,
  `@Environment='D'` vindt precies `FMD_TRIAL INTEGRATION DATA (D)`.
- `dry_run=1` op de al geregistreerde `TPCH.CUSTOMER`/`TPCH.ORDERS`: beide `Unchanged`, niets
  weggeschreven; de orphan-lijst toont de overige actieve bronnen correct.
- Een nieuwe entiteit (`TPCH.NATION`) echt geregistreerd, en een tweede identieke run hergebruikte
  dezelfde `LandingzoneEntityId` (idempotent, geen dubbele registratie).
- Foutgevallen, elk met een duidelijke melding en niets weggeschreven: onbekende sleutel in een
  regel, lege `PrimaryKeys`, onbekend domein, ongeldige `@Environment`.
- Metadatacontrole tegen `DiscoveredEntity` (een volledige TPCH-schemadiscovery gesimuleerd):
  correcte naam/PK/watermark slaagt; verkeerd hoofdlettergebruik, een niet-bestaande PK-kolom en een
  numerieke watermarkkolom worden elk apart en met de juiste melding geweigerd.

**Twee fouten gevonden en gefixt, met een nieuwe dacpac:**
1. De workspace-zoekopdracht gebruikte `LIKE '<Domain> DATA%'` (exacte prefix) in plaats van een
   deelstring-match, en vond daardoor nooit iets — elke workspace heeft het klantprefix vóór het
   domein. Zie de correctie hierboven bij "De omgeving kiest een workspace".
2. **Een `THROW`-bericht met een letterlijk `%`-teken komt bij `sqlcmd`/ODBC Driver 18 leeg binnen**
   (`PRINT` toont dezelfde tekst wel correct). Dit is geen bug in deze procedure specifiek, maar een
   valkuil voor elke toekomstige `THROW` in dit framework; zie `11_troubleshooting.md`.
3. De metadatacontrole blokkeerde aanvankelijk élke entiteit in een schema zodra er **iets** ontdekt
   was voor die connectie+database, ook een entiteit die nooit in die discovery-run zat (bijvoorbeeld
   `TPCH.CUSTOMER`, terwijl alleen `TPCH.REGION` was ontdekt). Gefixt door de guard te scopen op
   `SourceSchema`: `sp_UpsertDiscoveredEntities` vervangt per run het hele schema, dus discovery van
   een schema is alles-of-niets, en registratie van een nooit-ontdekt schema blijft ongemoeid.

**De Snowflake-discoverytak van `PL_FMD_DISCOVER_SOURCE` is wél echt getest**, los van de rest van de
pipeline (een los testpipeline-item `PL_TEST_SNOWFLAKE_DISCOVER` in `FMD_TRIAL INTEGRATION CODE (D)`,
met de `SC_METADATA_SNOWFLAKE`-query rechtstreeks tegen `FMD_BRON.TPCH`; na de test verwijderd):

- **Bevestigd, met een fix in de pipeline-JSON:** twee losse `scripts[]`-items in één Script-activiteit
  delen geen sessie. `SHOW PRIMARY KEYS IN DATABASE …` in het eerste item en
  `… FROM TABLE(RESULT_SCAN(LAST_QUERY_ID(-1)))` in het tweede gaf `invalid identifier '"schema_name"'`:
  de tweede statement vond het resultaat van de eerste niet. Eén puntkomma-gescheiden string in **één**
  `scripts[]`-item werkt wel (`SHOW PRIMARY KEYS …; WITH pk AS (… RESULT_SCAN(LAST_QUERY_ID(-1)) …) SELECT …`),
  en de volledige discoveryquery (met de `ARRAY_AGG`/`OBJECT_CONSTRUCT`-JSON-opbouw) draaide daarmee
  zonder fouten tegen `FMD_BRON.TPCH`. `PL_FMD_DISCOVER_SOURCE.DataPipeline/pipeline-content.json` is
  hierop aangepast.
- **Bevestigd:** Snowflake's `INFORMATION_SCHEMA.KEY_COLUMN_USAGE` bestaat niet (`does not exist or not
  authorized`, FMD_READER-rol); alleen `TABLE_CONSTRAINTS` bestaat daar. `SHOW PRIMARY KEYS` is dus de
  juiste route voor PK-kolommen, niet een ANSI-stijl `INFORMATION_SCHEMA`-join.
**Het connectieprobleem is opgelost, en de hele pipeline is daarna end-to-end getest** (akkoord
Mitchell, 2026-10-13: "laten we dit eerst helemaal getest hebben"). `User does not have access to
the connection` bleek te kloppen: de GUID in `config/item_config.yaml` (`372237f9-…`) bestaat niet
(meer) onder mijn account (`EntityNotFound` op `GET /v1/connections/{id}`, ook voor Mitchell zelf
— mogelijk een verweesde of opnieuw aangemaakte connectie in deze tenant, verder niet uitgezocht).
Fabric's `FabricSqlDatabase`-connector is generiek (het echte doel komt uit `workspaceId`/
`artifactId`, niet uit de connectie zelf), dus een testpipeline met Mitchells **eigen**
`CON_FMD_FABRIC_SQL` (`8f751fe0-…`) in plaats van die GUID werkte voor hetzelfde doel — puur om te
testen; de framework-bestanden verwijzen nog naar de oorspronkelijke GUID.

- **Een tweede, los van discovery staand ontwerpprobleem gevonden en opgelost:** de volledige
  pipeline (met de `Switch`-activiteit uit het eerste ontwerp) faalde direct met een lege
  `BadRequest`, nul activiteiten gestart, ook los van connecties en parameters.
  - ~~Oorzaak: een activiteit met een dynamische connectie-expressie werkt niet genest in een
    `Switch`, wel in een `IfCondition`.~~
  - *Correctie 2026-10-13, na een hertest op vraag van Mitchell.* Reden: die conclusie was getrokken
    uit twee tests die in twee dingen verschilden. In de `Switch`-test had de geneste activiteit nog
    `dependsOn: LKP_CONNECTION`, een activiteit buiten de container; in de `IfCondition`-test was die
    `dependsOn` leeggemaakt.
  - Hertest met alleen dat verschil, verder identiek (`Switch` met `SC_METADATA_SNOWFLAKE` in de case):
    - met `dependsOn: []` → **Completed**, de Script-activiteit echt gedraaid (Succeeded, 24,6 s);
    - met `dependsOn: LKP_CONNECTION` → **Failed**, `BadRequest`, 0 activiteiten.
  - **Werkelijke oorzaak** (*getest in eigen omgeving*): een `dependsOn` vanuit een geneste activiteit
    naar een activiteit buiten de container. De container-soort en de dynamische connectie spelen geen
    rol; `@activity('LKP_CONNECTION').output…` als expressie binnen de container werkt.
  - **Fix:** de eerste activiteit in elke tak heeft geen `dependsOn`; de container hangt af van
    `LKP_CONNECTION`.
  - ~~De pipeline gebruikt nu drie `IfCondition`-activiteiten.~~ *Bijgewerkt 2026-10-13, op verzoek van
    Mitchell:* terug naar één `Switch` (`SW_CONNECTION_TYPE`, cases `SQL` en `SNOWFLAKE`, standaardtak
    `FA_UNSUPPORTED_TYPE`). Reden: één activiteit in plaats van drie, en de standaardtak vangt elk
    ander type af. Daarna opnieuw end-to-end getest, zie hieronder.
  - Of `IfCondition` dezelfde fout geeft bij een `dependsOn` naar buiten, is niet apart getest
    (*aanname*: ja, het is dezelfde regel).
- **End-to-end test van de `Switch`-versie, alle drie de takken** (*getest in eigen omgeving*,
  2026-10-13; testpipeline in `FMD_TRIAL INTEGRATION CODE (D)`, daarna verwijderd):

  | Tak | Parameters | Run | Resultaat |
  |---|---|---|---|
  | `SNOWFLAKE` | `CON_TRIAL_SNOWFLAKE`, `FMD_BRON`, `TPCH` | `c862182f` | Completed; 7 tabellen, 0 met PK |
  | `SQL` | `CON_FMD_ASQL_AW`, `AdventureWorks`, `Sales` | `14a8ab49` | Completed; 28 objecten (19 tabellen met PK, 9 views) |
  | standaard | `CON_FMD_NOTEBOOK`, `ECB_FX` | `a6c8ca31` | Failed, zoals bedoeld: "…its type (NOTEBOOK) has no discovery support yet" |

  - `logging.PipelineExecution`: Start→End voor de twee geslaagde runs, Start→Failed voor de
    standaardtak.
  - `dry_run=1` met de zeven bestaande AdventureWorks-`Sales`-entiteiten in D, tegen de écht
    ontdekte metadata: zeven keer `Unchanged`. Met `Custmer` in plaats van `Customer` geweigerd
    ("not found by PL_FMD_DISCOVER_SOURCE for this schema").
  - **Fix in de SQL-query:** `TYPE_NAME(c.user_type_id)` gaf `NULL` voor een alias-type
    (`Sales.Currency.Name`, type `dbo.Name`), en `FOR JSON` liet `Type` dan weg. Nu
    `TYPE_NAME(c.system_type_id)`: het basistype (`nvarchar`). Hertest (run `5bf664d0`): alle
    kolommen van alle 28 objecten hebben een type.
  - **Verschil met `PL_TOOLING_POST_ASQL_TO_FMD`** (*vastgesteld*): die leidde voor een view op één
    basistabel de PK af van die tabel. `PL_FMD_DISCOVER_SOURCE` doet dat niet: een view krijgt
    `PrimaryKeys = NULL`, en dus een TODO in `print_entity_list()`. In de trial gaat het om 9 views in
    `Sales`, waaronder `SalesOrderDetail`. Bewust eenvoudig gehouden; toevoegen als het handwerk
    oplevert bij een klant met veel views.
- **Volledige end-to-end run, geslaagd:** de herbouwde pipeline (met de `IfCondition`-fix) tegen
  `FMD_BRON`/`CON_TRIAL_SNOWFLAKE`, `SchemaFilter='TPCH'`. `integration.DiscoveredEntity` kreeg alle
  zeven TPCH-tabellen (`CUSTOMER`, `LINEITEM`, `NATION`, `ORDERS`, `PART`, `PARTSUPP`, `SUPPLIER`) met
  volledige kolomlijsten en types. **`PrimaryKeys` is voor alle zeven `NULL`**: deze
  Snowflake-sample-data heeft geen PK-constraints gedeclareerd (`SHOW PRIMARY KEYS` leverde niets op).
  Geen bug: `print_entity_list()` markeert dat al met een TODO, en de registratie van zo'n tabel
  vraagt een handmatig ingevulde `PrimaryKeys`.
- **De `resultSets[0]`-aanname klopte**: daarna `dry_run=1` op `TPCH.CUSTOMER`/`ORDERS` (beide
  bestaand, nu tegen de écht ontdekte metadata) gaf `Unchanged`; een verzonnen `TPCH.NIET_ECHT` werd
  terecht geweigerd ("not found by PL_FMD_DISCOVER_SOURCE for this schema").
- Na de test alles opgeruimd: het testpipeline-item verwijderd uit `FMD_TRIAL INTEGRATION CODE (D)`,
  de vier SQL-testobjecten gedropt, `integration.LandingzoneEntity` weer op 40 rijen (ongewijzigd).

- **De notebooks in Fabric** (*getest in eigen omgeving*, 2026-10-13). Beide notebooks tijdelijk in
  `FMD_TRIAL INTEGRATION CONFIG`, `NB_REGISTRATIE` gevuld met de 7 AW-`Sales`- en de 2 Snowflake-
  entiteiten die al in D staan, en als job gedraaid. Eerst opnieuw ontdekt (`SQL` run `905a875d`,
  `SNOWFLAKE` run `23e45c9f`). Drie fouten gevonden en gefixt:
  1. **Fout 266 bij de dry run.** pyodbc draait met `autocommit=False` en heeft dus al een transactie
     open (`@@TRANCOUNT = 1`). De `ROLLBACK` van de dry run beëindigde die ook: "Transaction count
     after EXECUTE indicates a mismatching number of BEGIN and COMMIT statements". `sqlcmd`
     autocommit, daarom kwam het in de eerdere tests niet naar boven. Gereproduceerd met `sqlcmd`
     en een buitenste `BEGIN TRANSACTION`. Fix in `sp_RegisterEntities`: `BEGIN TRANSACTION` +
     `SAVE TRANSACTION RegisterEntities`, bij een dry run `ROLLBACK TRANSACTION RegisterEntities`,
     daarna altijd `COMMIT`. Hertest: de teller van de aanroeper blijft 1, en de checksum van de
     registratietabellen is onveranderd.
  2. **Volgorde van de resultsets.** `sp_UpsertDataSource` en `sp_UpsertLandingzoneBronzeSilver`
     geven per entiteit eigen resultsets terug. Die stonden tussen de lijst met wezen en de preview,
     en `register()` las vaste posities. Fix: de procedure geeft de wezen nu pas aan het eind terug,
     na de preview, en `register()` leest van achteren (`sets[-2]`/`sets[-1]`).
  3. **`print_entity_list()` gaf ongeldige Python.** Bij een regel zonder PK stond `# TODO` vóór de
     afsluitende `},`, waardoor een geplakte lijst niet compileerde. De TODO staat nu na `},`. In de
     hertest wordt de uitvoer met `eval` als lijst ingelezen: AW `Sales` 28 regels (9 TODO), Snowflake
     `TPCH` 7 regels (7 TODO).

  Hertest (job `cefff852`, Completed):
  - `%run NB_FMD_REGISTRATION_FUNCTIONS` en `resolve_config_database()` werken vanuit de
    config-workspace. Er staat geen GUID in de code.
  - Dry run in D en in T: de juiste DATA-workspace (`… DATA (D)` en `… DATA (T)`), en 9× `Unchanged`.
    De wezen per workspace worden goed getoond.
  - Foutgevallen, allemaal geweigerd met een eigen melding:
    - tikfout `Custmer`;
    - Snowflake `customer` in kleine letters;
    - PK-kolom `CustomerKey` bestaat niet;
    - lege `PrimaryKeys`;
    - sleutel `PrimaryKey`;
    - Snowflake-watermark `O_TOTALPRICE` ("type NUMBER, must be DATE or TIMESTAMP");
    - omgeving `X`;
    - omgeving `A` (geen workspace);
    - domein `HR`.
  - Echte run (`dry_run=False`) voor de twee Snowflake-entiteiten met dezelfde waarden:
    `InLoadView=yes`, de watermarks blijven staan, en de entiteittabellen zijn onveranderd
    (checksum). Alleen `DataSource.Description` werd "Registered with sp_RegisterEntities", zie
    hieronder.
  - Tijdens de test registreerde een andere sessie `TPCH.NATION` met het oude sjabloon. Die
    verscheen correct als wees in D. Niet aangeraakt.
  - Opgeruimd: beide notebooks, de testpipeline en de vier SQL-testobjecten zijn verwijderd.

**Nog open:**
- ~~De SQL-tak van `PL_FMD_DISCOVER_SOURCE` is niet apart end-to-end getest.~~ *Gedaan 2026-10-13*,
  zie de tabel hierboven.
- ~~De twee notebooks zelf zijn niet in Fabric getest.~~ *Gedaan 2026-10-13*, zie "De notebooks in
  Fabric" hierboven.
- ~~Een echte registratie in T ná een promotie is nog niet gedaan.~~ *Gedaan 2026-10-13* in de rookproef
  na de merge, met de echte setup (`testplan-trial.md`, "vervolg 7"):
  - `TPCH.NATION` geregistreerd in T vanuit het uitgerolde `NB_REGISTRATIE` (`29cf50c8`);
  - `PL_FMD_LOAD_ALL` in T geladen tot Silver (`df23d149`);
  - een tweede setup-run overschreef `NB_REGISTRATIE` niet.

  De rookproef vond twee fouten in deze ADR-wijziging, gefixt in PR #63:
  - de setup stopte na de dacpac;
  - een lege markdownregel werd samengevoegd met de volgende regel.
- ~~Waarom de GUID uit `config/item_config.yaml` niet bestaat.~~ *Verklaard 2026-10-13:* het is een
  placeholder die de setup vervangt door de echte `CON_FMD_FABRIC_SQL` (mapping in `NB_SETUP_FMD`).
  Vastgesteld in de uitgerolde `PL_FMD_DISCOVER_SOURCE`.
- ~~`sp_RegisterEntities` overschrijft bij elke run `DataSource.Description`.~~ *Gefixt 2026-10-13,
  op verzoek van Mitchell:* een bestaande bron houdt zijn beschrijving, en alleen een nieuwe krijgt
  "Registered with sp_RegisterEntities". Geen `Description`-veld in de lijst, want daar is niet om
  gevraagd. *Getest in eigen omgeving:*
  - een echte run voor `AdventureWorks` (`Sales.Currency`): "Demoklant" bleef staan, en de checksum
    was onveranderd;
  - een nieuwe bron, binnen een teruggedraaide transactie, kreeg de standaardtekst.
