# ADR-018: Bronnen registreren via een notebook, niet via `sqlcmd`

Status: Proposed
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
  het niet) bevat alleen de lijsten.
- **De omgeving kiest een workspace, niet andersom.** De procedure krijgt `@Domain` (bijvoorbeeld
  `INTEGRATION` of `FINANCE`) en `@Environment` (D/T/A/P), en zoekt de ene DATA-workspace waarvan de
  naam `<Domain> DATA` bevat, met het bijpassende achtervoegsel en een actieve `LH_DATA_LANDINGZONE`.
  Bij 0 of meer dan 1 treffer volgt een fout. Je typt het domein, niet de volledige workspacenaam met
  het klantprefix: dat voorkomt zowel de prefix-typefout als de omgevingsmismatch van E-R5.
  *Correctie, getest in FMD_TRIAL 2026-10-13:* de eerste versie zocht op een exacte prefix-match
  (`LIKE '<Domain> DATA%'`) en vond daardoor niets, want elke workspace heeft het klantprefix vóór
  het domein (`"FMD_TRIAL INTEGRATION DATA (D)"`). Gefixt naar een deelstring-match.
- **`dry_run=True` is de voorgeschreven eerste stap.** De procedure voert alle controles en de
  registratie echt uit en draait dan terug, en toont per entiteit of hij nieuw, gewijzigd of
  ongewijzigd is, plus de entiteiten die in die workspace actief zijn maar niet in de lijst staan.
- **Geen apart logspoor.** CONFIG is niet aan Git gekoppeld (*vastgesteld*,
  `output/03_technische_documentatie/10_operations.md`, getest 2026-10-11), dus de lijst heeft geen
  PR-review zoals bij het sjabloon. Die review was een afspraak, geen controle: niets dwong af dat
  het uitgevoerde script het gereviewde was. De bescherming zit in de controles, de dry run en de
  transactie; de configdb zelf is de huidige stand, en het notebook heeft de versiegeschiedenis van
  Fabric. Een logtabel pas als een klant om een audittrail vraagt.
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
  gekozen CODE-workspace en pollt op `Location` (akkoord Mitchell, 2026-10-13).
- **Alles in het notebook, niets in de configdb.** Verworpen: dan bestaan er twee versies van de
  controles (notebook en sjabloon), die uit elkaar lopen. De logica hoort op één plek.
- **Een logtabel per run.** Verworpen (akkoord Mitchell, 2026-10-13): de configdb is zelf al de
  huidige stand, en de dry run laat vooraf zien wat er verandert. Een logtabel voegt niets toe
  zolang niemand om een audittrail vraagt.
- **Het `sqlcmd`-sjabloon laten staan.** Verworpen: lost geen van de drie problemen op.

## Gevolgen

- `templates/registratie/registreer_entiteiten.sql` en `PL_TOOLING_POST_ASQL_TO_FMD` vervallen.
  Verwijderen pas na akkoord Mitchell.
- De setup plaatst `NB_FMD_REGISTRATION_FUNCTIONS` en `NB_REGISTRATIE` in CONFIG
  (`config/data_deployment.json`), en `PL_FMD_DISCOVER_SOURCE` in elke CODE-workspace
  (`config/item_deployment.json`). `NB_REGISTRATIE` staat in `CUSTOMER_OWNED_ITEMS`.
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
