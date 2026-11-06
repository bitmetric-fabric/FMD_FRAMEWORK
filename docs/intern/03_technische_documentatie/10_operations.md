# Operations

**Fase:** 3 (Technische documentatie)
**Datum:** 2026-09-25
**Status:** Versie 2: gecorrigeerd na review 2 (zie versiegeschiedenis onderaan)
**Bron:** `output/01_kennisbasis/operations.md`, `bronnen-en-extensies.md`, `05_INTEGRATION/03_operationele-aandachtspunten.md`. Code in `FMD/src/` (per sectie genoemd).

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

Dit document beschrijft de operationele kant van een draaiende FMD-implementatie:
- monitoring;
- orchestratie en foutpropagatie;
- het watermarkmechanisme;
- herstarten na een fout;
- een watermark resetten;
- de harde timeouts.

Deactiveren staat in `05_INTEGRATION/01_ddl-spec.md` en B-INFRA-02. Foutpatronen en hun oplossing staan in `11_troubleshooting.md`.

## Melding bij een gefaalde geplande run

Het framework zelf stuurt geen meldingen. Fabric kan dat wel voor een **geplande** pipeline. Kies op de ~~schedule-pipeline (`PL_FMD_SCHEDULE_NIGHTLY`/`_INTRADAY`)~~ geplande pipeline *(correctie 2026-10-06: `PL_FMD_ORCHESTRATION_TEMPLATE`, zie "Orchestratie en foutpropagatie")* **Home → Schedule → Failure notifications** en voeg gebruikers of groepen toe. Een gefaalde `PL_FMD_LOAD_ALL` laat de geplande pipeline falen (`waitOnCompletion: true`), en dan gaat er een mail. Dit kan alleen in de portal, en een handmatige run geeft geen mail. Uitbreiding: Activator op de job-events, of workspace monitoring met een KQL-query. Zie draaiboek fase 5 stap 4.

*Correctie 2026-10-11 (ontwerp `FMD_FRAMEWORK#52`, ADR-017; gemerged 2026-10-11, `4971d88`):* zet de Failure notifications op `PL_FMD_SCHEDULE_<short>` in INTEGRATION CONFIG, één keer per omgeving, niet meer op de pipelines in CODE. Reden: een schedule hoort bij de item-definitie en gaat mee met een promotie, de ontvangers niet; CONFIG zit in geen deployment pipeline. Een mislukte run in CODE laat de schedule-pipeline falen (`waitOnCompletion`), dus de mail komt van die pipeline (zie "Plannen" bij "Orchestratie en foutpropagatie"). *Getest in eigen omgeving* (2026-10-11, FMD_SMOKE3): mail ontvangen bij een gefaalde geplande run van `PL_FMD_SCHEDULE_P` (gemeld door Mitchell, geen run-ID vastgelegd). Op de orchestratie zelf was dit eerder getest: rookproef 2, stap 11, run `884c289b`.

Na een melding: de query hieronder op `PipelineExecution` geeft de reden. Sinds PR #30 staat de fout van het mislukte child daarin.
- *Correctie 2026-10-06 (rookproef 2, stap 11):* faalt de landingzone, dan staat in `PipelineExecution` alleen de keten, zonder entiteit. Een voorbeeld: "LDZ failed", inner activity `SW_CHECK_DATASOURCENAME`, met `EntityId` `NULL`. De entiteit en de echte fout staan in `CopyActivityExecution`, met `LogType = 'FailedCopyActivity'`; gebruik daarvoor de query hieronder. Ook de foutmelding van de run zelf verwijst naar `PipelineExecution`.
- **Een promotie van INTEGRATION CODE neemt het schema mee, maar niet de ontvangers** (*getest in eigen omgeving*, 2026-10-06). Voeg na elke promotie de ontvangers in de doelomgeving opnieuw toe, en controleer het tijdstip (draaiboek fase 5 stap 4).

**Status:** *vastgesteld* (Microsoft Learn, *Create alerts for pipeline runs*, 2026-09-29; pipeline-JSON). *Toegevoegd 2026-10-05.*
- *Getest in eigen omgeving 2026-10-06* (rookproef 2): de geplande run `884c289b` faalde, en de mail kwam aan.

## Back-up en herstel van de configuratiedatabase

De configdb (`SQL_FMD_FRAMEWORK`) is één database voor alle omgevingen (B-ENV-02). Er zijn twee vangnetten.

**1. Automatische back-ups (Fabric).**
- Wekelijks een volledige back-up, elke 12 uur een differentiële, en ongeveer elke 10 minuten een logback-up.
- Bewaartermijn standaard 7 dagen, in te stellen tot 35 dagen: database → Settings → *Backup retention policy*. Voor een klant met Prod: 35 dagen.
- Herstel kan alleen in de portal (database → *Restore database*): een restore tot op een tijdstip, altijd naar een **nieuwe** database in dezelfde workspace. Een bestaande database overschrijven kan niet, en er is geen REST API of CLI voor.
- **Wordt de workspace verwijderd, dan zijn de back-ups ook weg.**
- Bron: Microsoft Learn, *Automatic backups* en *Restore from a backup* (bijgewerkt 2026-02-17). *Vastgesteld*; een restore in de portal is niet zelf getest.

**2. Export naar een bacpac (buiten Fabric).** Dit vangt het verlies van de workspace op. Maak er een vóór elke dacpac-wijziging die bestaande tabellen of kolommen raakt (ADR-013), en vóór een herregistratie op grote schaal:

```
dotnet tool install microsoft.sqlpackage --tool-path <map>        # eenmalig
sqlpackage /a:Export /ssn:"tcp:<server>,1433" /sdn:"<database>" /at:<token> /tf:configdb_<datum>.bacpac
```

- `<token>`: `az account get-access-token --resource https://database.windows.net/ --query accessToken -o tsv`. Zet het token niet in een script of log.
- `<server>` en `<database>`: `VAR_CONFIG_FMD` (`fmd_fabric_db_connection`, `fmd_fabric_db_name`).
- Bewaar de bacpac buiten de Fabric-tenant, op een plek met toegangsbeheer. Hij bevat de registraties en de volledige logging.

Terugzetten gebeurt altijd in een **lege, nieuwe** database: `sqlpackage /a:Import /tsn:… /tdn:<nieuwe database> /at:<token> /sf:<bacpac>`.

**Een herstelde database in gebruik nemen.** Pipelines vinden de configdb via `VAR_CONFIG_FMD` (`fmd_config_database_guid`, `fmd_config_workspace_guid`). Notebooks vinden haar via `fmd_fabric_db_connection` en `fmd_fabric_db_name`. Zet die variabelen in elke CODE-workspace van elke omgeving om naar de nieuwe database. De connectie `CON_FMD_FABRIC_SQL` hoeft niet te veranderen: die heeft geen databaseparameter (`create_fabric_sql_connection`). *Vastgesteld in code, niet getest.*
- Wil je alleen een paar rijen terug (bijvoorbeeld een per ongeluk gewijzigde registratie), laat de oude database dan staan en registreer die rijen opnieuw met `NB_REGISTRATIE` (ADR-018; *correctie 2026-10-13*, voorheen het lijstsjabloon uit draaiboek §A.4a). De herstelde database gebruik je dan alleen om de oude waarden in op te zoeken. *Aanname, niet getest.*

**Status:** getest in eigen omgeving (2026-10-05, trial-configdb, akkoord Mitchell):
- **Export:** 26 seconden, 155 KB, alleen lezend.
- **Import:** in een nieuwe database `SQL_A7_RESTORE_TEST` in `FMD_TRIAL INTEGRATION CONFIG`, 41 seconden.
- **Vergelijking:** alle 14 tabellen hebben hetzelfde aantal rijen, bijvoorbeeld `LandingzoneEntity` 33, `PipelineExecution` 705 en `NotebookExecution` 935. Ook het schema is gelijk: 27 procedures, 3 views en alle constraints.
- **Opruimen:** de testdatabase en de bacpac zijn daarna verwijderd.
- **Niet getest:** de restore in de portal en het omzetten van `VAR_CONFIG_FMD`.

## Monitoring: FMD_Logging Power BI-rapport

Het Power BI-rapport "FMD_Logging" staat bovenop de drie tabellen in het `logging`-schema: `CopyActivityExecution`, `NotebookExecution` en `PipelineExecution` (zie `05_INTEGRATION/01_ddl-spec.md`). Het is het eerste aanlooppunt voor operationeel inzicht.

**Status:** getest in eigen omgeving.

Bekende datakwaliteitsissues in de logging-data. Die zijn relevant voor iedereen die zelf rapportages op deze tabellen bouwt.
- `LogType` wordt op twee manieren gespeld: `FailPipeline` en `FailedPipeline`. Beide staan in de pipeline-JSON.
- `EntityLayer` heeft 4 waarden: `Bronze`, `Control`, `Landingzone` en `Silver`.
- `TriggerType` bevat naast `"Manual"` ook de kale waarde `"1"` (bij `PL_FMD_LOAD_ALL`).
- Een fout in de merge-stap van `NB_FMD_LOAD_LANDING_BRONZE` wordt in `NotebookExecution` gelogd met `LogType = 'EndNotebookActivity'` en `"Action": "Error"` in `LogData`, niet met een Fail-type. Filter je alleen op `Fail*`, dan mis je notebookfouten per entiteit.
- **In forks van vóór PR #18 worden fouten uit de controlestappen van dat notebook niet per entiteit gelogd.** Het gaat om: geen PK, PK-kolom ontbreekt, en dubbele PK's. In `NotebookExecution` staan dan alleen `StartNotebookActivity`-regels (3 per bestand, door de retries), zonder `End`. De fout verschijnt alleen in `PipelineExecution` (`PL_FMD_LOAD_BRONZE`, `FailPipeline`), met de activitynaam (`<Tabel>_0_0`) maar zonder EntityId. De foutmelding zelf staat alleen in de notebook-run in Monitor (hertest T-D06). Vanaf PR #18 logt het notebook deze fouten als `"Action": "Error"` met de melding, en wordt een bestand per run één keer geprobeerd.

**Status:** getest in eigen omgeving; het vierde punt is vastgesteld in de code (`except`-blok van `NB_FMD_LOAD_LANDING_BRONZE`).

Deze query toont de falende entiteiten van de laatste dag:

```sql
SELECT [LogDateTime]
      ,[EntityLayer]
      ,[EntityId]
      ,[NotebookName] AS [Onderdeel]
      ,[LogData]
FROM   [logging].[NotebookExecution]
WHERE  [LogDateTime] >= DATEADD(DAY, -1, SYSUTCDATETIME())
  AND  [LogData] LIKE '%"Error"%'
UNION ALL
SELECT [LogDateTime]
      ,[EntityLayer]
      ,[EntityId]
      ,[CopyActivityName]
      ,[LogData]
FROM   [logging].[CopyActivityExecution]
WHERE  [LogDateTime] >= DATEADD(DAY, -1, SYSUTCDATETIME())
  AND  [LogType] = 'FailedCopyActivity'
ORDER BY [LogDateTime] DESC
```

In forks van vóór PR #18 mist deze query Bronze-fouten uit de controlestappen (zie hierboven). Een child dat faalt vóór zijn eigen logging (bijvoorbeeld een login-timeout naar de configdb) staat nooit in `NotebookExecution`; de pipelinequery hieronder is dan de enige plek. Vanaf PR #30 (gemerged 2026-10-05) staat de reden van dat child in `LogData` achter `Failed notebooks: [...]` (*getest in eigen omgeving*, 2026-10-05, `11_troubleshooting.md`); daarvoor alleen de activitynaam. Aanvullend, en ook daarna nuttig: gefaalde laag-pipelines, en bestanden die blijven hangen.

```sql
SELECT [LogDateTime], [PipelineName], LEFT([LogData], 1000) AS [LogData]
FROM   [logging].[PipelineExecution]
WHERE  [LogDateTime] >= DATEADD(DAY, -1, SYSUTCDATETIME())
  AND  [LogType] IN ('FailPipeline', 'FailedPipeline')
ORDER BY [LogDateTime] DESC;

SELECT PLE.[LandingzoneEntityId], PLE.[FileName], PLE.[InsertDateTime]
FROM   [execution].[PipelineLandingzoneEntity] PLE
WHERE  PLE.[IsProcessed] = 0
  AND  PLE.[InsertDateTime] < DATEADD(HOUR, -2, SYSUTCDATETIME());   -- bestand blijft hangen
```

## Orchestratie en foutpropagatie

`PL_FMD_LOAD_ALL` heeft vier parameters (*correctie 2026-10-13: twee, tot de subset-filters; zie* Een subset van tabellen laden*)*:
- `Data_WorkspaceGuid`: vanaf PR #20 is de default leeg, en dan neemt de pipeline `VAR_CONFIG_FMD.fmd_data_workspace_guid`, die per omgeving een eigen value set heeft. In forks van daarvoor stond hier de template-GUID uit `config/item_config.yaml` (`workspace_data`). De setup verving die alleen in Dev, en een promotie kopieerde de Dev-waarde naar Test en Prod. Een load in Test of Prod laadde daardoor Dev (hertest T-E01). Controleer dit in een bestaande omgeving: de default van deze parameter in `PL_FMD_LOAD_ALL`, `PL_FMD_LOAD_LANDINGZONE` en de schedule-pipelines in Test/Prod mag niet de Dev-DATA-workspace zijn.
- `LoadGroup`: default `''`, wat "alle groepen" betekent. *Aanvulling 2026-10-20 (branch `feature/loadgroup-kolommen-filter`, ADR-020, nog niet gemerged; bijgewerkt 2026-10-29: gemerged als `FMD_FRAMEWORK#77`, `5a700f9`):* een tabel kan een eigen groep hebben (`integration.LandingzoneEntity.LoadGroup`); de groep waarin een tabel laadt is die van de tabel, anders die van de bron. *Getest in eigen omgeving* (2026-10-20, DEV_MITCHELL, runs `5100ce6c` met `tst_b` en `fe32abfd` met `tst_a`, `testplan-trial.md` T-D16): een run met een groep laadt alleen de tabellen van die groep. Een tabel in een andere groep dan haar bron laadt niet bij een run voor de groep van de bron.
- `DataSourceName` en `Entities`: default `''`, wat "geen filter" betekent.

De pipeline roept de drie lagen aan, maar **ketent op `Completed`, niet op `Succeeded`**:

| Activity | Type | Afhankelijk van |
|---|---|---|
| `SP_START_AUDIT_PIPELINE` | StoredProcedure | (geen) |
| `PL_FMD_LOAD_LANDINGZONE` | InvokePipeline | `SP_START_AUDIT_PIPELINE` (Succeeded) |
| `PL_FMD_LOAD_BRONZE` | InvokePipeline | `PL_FMD_LOAD_LANDINGZONE` (**Completed**) |
| `PL_FMD_LOAD_SILVER` | InvokePipeline | `PL_FMD_LOAD_BRONZE` (**Completed**) |
| `SP_FAIL_{LDZ,BRZ,SLV}_AUDIT_PIPELINE` | StoredProcedure | de bijbehorende laag (Failed) |
| `SP_END_AUDIT_PIPELINE` | StoredProcedure | `PL_FMD_LOAD_SILVER` (Succeeded) |
| `FA_THROW_ERROR_BRZ`, `FA_THROW_ERROR_SLV` | Fail | de bijbehorende `SP_FAIL_*` (Completed) |
| `FA_THROW_ERROR_LDZ` | Fail | `SP_FAIL_LDZ_AUDIT_PIPELINE` (Completed) **en** `PL_FMD_LOAD_SILVER` (Completed) |

**Wat dit betekent:**
- Bronze draait ook als Landingzone is gefaald, en Silver ook als Bronze is gefaald. Dat is foutisolatie per entiteit. Bronze verwerkt alleen landingzone-bestanden die met succes zijn geland (`execution.PipelineLandingzoneEntity.IsProcessed = 0`). De entiteiten die wél geland zijn, lopen dus gewoon door. Een entiteit die in Landingzone faalde, heeft geen nieuw bestand en wordt in Bronze overgeslagen.
- Een groene run bewijst dus **niet** dat elke entiteit geladen is. Een rode run betekent niet dat er niets geladen is.

`PL_FMD_ORCHESTRATION` is een wrapper rond `PL_FMD_LOAD_ALL`. De setup (`NB_SETUP_BUSINESS_DOMAINS`) hangt er automatisch de `PL_FMD_LOAD_GOLD` van elk business-domein aan, met als conditie `PL_FMD_LOAD_ALL` **Succeeded**. Na een fout in één entiteit draait Gold dus voor geen enkel domein. Start Gold na herstel zo nodig handmatig. ~~Plannen gebeurt via `PL_FMD_SCHEDULE_NIGHTLY`/`PL_FMD_SCHEDULE_INTRADAY`, volgens de afspraak met de klant.~~ De naam `PL_MASTER_ORCHESTRATION` komt niet voor in de repo.

**Plannen** (*correctie 2026-10-06*, review 3 P3-B1/B2, `FMD_FRAMEWORK#35`):
- Plan `PL_FMD_ORCHESTRATION`, met één schema per cadans. Elk schema geeft een eigen `LoadGroup` mee: leeg voor de nachtelijke run (alle bronnen), `INTRADAY` (of een andere groep) voor de runs overdag.
- Het filter in elke laadpipeline is `'' = <LoadGroup van de run> OR LoadGroup = <LoadGroup van de run>`. Een run met een groep laadt dus geen bronnen zonder groep.
- `concurrency: 1` laat een run wachten zolang een andere loopt. Gold draait na elke run.
- Een promotie neemt de schema's met hun parameters mee, en zet ze aan. De ontvangers van *Failure notifications* gaan niet mee.
- `PL_FMD_SCHEDULE_*` laden zonder Gold, en `PL_FMD_SCHEDULE_NIGHTLY` slaat bronnen zonder groep over. Gebruik ze niet als standaard.
- **Status:** getest in eigen omgeving (2026-10-06, `rookproef-main-2.md` stap 14: job-runs `88d43b5f` en `a5fb91e2`, promotie `8705689e`).

**Correctie 2026-10-11** (ontwerp `FMD_FRAMEWORK#52`, ADR-017; gemerged 2026-10-11, `4971d88`): de schema's staan niet meer op `PL_FMD_ORCHESTRATION_TEMPLATE` en `PL_FMD_MAINTENANCE` in CODE, maar op `PL_FMD_SCHEDULE_<short>` in INTEGRATION CONFIG (map `SchedulePipelines`), één per omgeving (D, T, P). Reden: een schedule hoort bij de item-definitie en gaat dus mee met een promotie (zie hierboven); CONFIG zit in geen deployment pipeline. Dit vervangt de bullets over promotie hierboven, voor een installatie met #52.
- De pipeline heeft de parameters `Target` (`LOAD` of `MAINTENANCE`) en `LoadGroup`. Een Switch op `Target` roept de orchestratie (met `LoadGroup`) of `PL_FMD_MAINTENANCE` aan in de CODE-workspace van die omgeving, en wacht op het resultaat. Een andere `Target` laat de pipeline falen (`UnknownTarget`). `concurrency: 1`.
- Nachtelijk, intraday en maintenance zijn elk een schedule op hetzelfde item, met `Target` en `LoadGroup` als schedule-parameters. De ontvangers van *Failure notifications* stel je één keer per omgeving in.
- De setup maakt de pipelines eenmalig aan en overschrijft ze nooit. Een bestaande installatie houdt haar schema's op de pipelines in CODE tot ze die zelf overzet.
- Een promotie neemt deze schema's niet mee, en een setup-update raakt ze niet. Dat lost E-R2 (eindcontrole 2026-10-08) op voor de schema's. E-R3 is *vastgesteld* in de code (de setup verwijdert in CONFIG niets en `create_schedule_pipeline` slaat een bestaand item over) en getest met die functie, maar niet met een volledige setup-run.
- Welke bron er geladen wordt, verandert niet: de orchestratie in elke CODE-workspace laadt de DATA-workspace van haar eigen omgeving, via `VAR_CONFIG_FMD`.
- De pipeline verwijst met letterlijke workspace- en pipeline-ID's naar CODE. Krijgt een van die items een nieuw ID, dan moet je de schedule-pipeline bijwerken, of verwijderen (met zijn schedules) en door de setup opnieuw laten aanmaken. *Aanname:* een setup-update op een bestaande installatie laat de ID's van de orchestratie en de maintenance gelijk (niet getest).
- De schema's staan niet in git, want CONFIG is niet aan git gekoppeld (~~*aanname*, niet nagegaan~~ *getest in eigen omgeving*: `GET …/git/connection` op FMD_SMOKE3 INTEGRATION CONFIG gaf `NotConnected`, 2026-10-11). Leg tijden, `Target`, `LoadGroup` en ontvangers vast in het implementatieplan van de klant.
- **Status:** *getest in eigen omgeving* (2026-10-11, FMD_SMOKE3, `testplan-trial.md` T-D10):
  - routering naar de juiste CODE-workspace voor D, P en T (runs `3ea62335`, `f07c2dee`, `0908355d`, `2f39a73d`);
  - foutpropagatie: een ongeldige `Target` (`152b56ed`, `cdc23dc7`) en een fout in Gold, drie niveaus dieper;
  - promotie D → T van INTEGRATION CODE zonder schedule in T (operatie `5351536f`);
  - `create_schedule_pipeline` tegen de echte `fab`-CLI (run `91f84e4a`): bestaande overgeslagen, ontbrekende aangemaakt in de juiste map.
  - *Niet getest:* de hele `NB_SETUP_FMD` in één run, en een volledig groene `LOAD`-run.

**Status:** vastgesteld (`FMD/src/PL_FMD_LOAD_ALL.DataPipeline/pipeline-content.json`, `PL_FMD_ORCHESTRATION`, `NB_UTILITIES_SETUP_FMD` → `wire_domain_into_orchestration`).

## Een subset van tabellen laden (`DataSourceName`, `Entities`)

*Toegevoegd 2026-10-13, `FMD_FRAMEWORK#65` (gemerged 2026-10-13, `494c885`).* Naast `LoadGroup` kun je een run beperken tot één bron en een paar tabellen. `PL_FMD_LOAD_ALL`, `PL_FMD_LOAD_LANDINGZONE`, `PL_FMD_LOAD_BRONZE` en `PL_FMD_LOAD_SILVER` hebben twee extra parameters, default `''` (geen filter):

| Parameter | Betekenis |
|---|---|
| `DataSourceName` | Exacte naam van één bron (`integration.DataSource.Name`). |
| `Entities` | Kommalijst. Een item matcht de `SourceName` van de landing-zone-entiteit, of `SourceSchema.SourceName`. Spaties rond een item tellen niet mee. |

- Beide gevuld is een AND. Samen met `LoadGroup` moeten alle drie kloppen. Voorbeeld: `DataSourceName = FMD_BRON`, `Entities = TPCH.NATION`.
- De naam is de naam in de bron, in alle lagen. Het is niet de naam van de Bronze- of Silver-tabel. Een naam die voor meerdere entiteiten geldt, matcht ze allemaal binnen de werkruimte van de run (*vastgesteld* in de functie, niet apart getest).
- `PL_FMD_LOAD_ALL` geeft beide door aan de landing zone, Bronze en Silver. `PL_FMD_ORCHESTRATION` heeft ze niet: een schedule hoort geen tabellijst te dragen.
- De regel zit op één plek, `execution.fn_EntityInFilter`. De getter-procedures en de inline queries in de landing-zone-pipelines roepen hem aan. In die queries worden enkele quotes in de waarden verdubbeld.

**Bronze en Silver los verwerken alleen wat al in de queue staat** (`execution.PipelineLandingzoneEntity`, `PipelineBronzeLayerEntity`). `PL_FMD_LOAD_BRONZE` met `Entities = dbo.Klant` verwerkt de onverwerkte bestanden van die tabel; het laadt hem niet opnieuw. Een verse herlaad doe je met `PL_FMD_LOAD_ALL` en het filter. Los draaien van Bronze of Silver vraagt nog steeds `Data_WorkspaceGuid`, want die twee pipelines vallen niet terug op de library-variabele.

**Een gefilterde run laat de queue van andere tabellen liggen.** Die rijen blijven onverwerkt tot een run zonder dat filter, of met een filter dat ze raakt. Een groene run betekent dus niet dat de queue leeg is. Controleer dat met `execution.PipelineLandingzoneEntity` en `PipelineBronzeLayerEntity` met `IsProcessed = 0`.

**Status:**
- *Vastgesteld* (`FMD/src/Config_Database/execution/Functions/fn_EntityInFilter.sql`, `sp_GetBronzelayerEntity.sql`, `sp_GetSilverlayerEntity.sql`, `scripts/test_entity_filter.py`).
- *Getest in eigen omgeving* (2026-10-13, trial-Dev, `testplan-trial.md` vervolg 9): de functie op 11 gevallen, beide procedures tegen de echte queue, en in pipeline-runs de landing zone los (`2778fea2`), Bronze los (`9f49c40f`), Silver los (`7c5af120`), `PL_FMD_LOAD_ALL` met filter (`872ca0a5`), met een filter zonder match (`5f91c9c4`), een regressierun met alleen `LoadGroup` (`da9bdc83`) en waarden met quotes (`6668b5cf`).
- *Getest in eigen omgeving* (2026-10-13, vervolg 10): hoofdletterongevoelig (collation `SQL_Latin1_General_CP1_CI_AS`); een quote in een echte naam matcht op functieniveau; 100.000 rijen door de functie in 1,7 s; promotie D naar T (selectief, operatie `5dba7270`) en een gefilterde `PL_FMD_LOAD_ALL` in T (`9ab3367c`).
- *Niet getest:* P en de promotie T naar P (de deploy werd door de permissiecontrole geweigerd), en een tabelnaam met een quote die via een pipeline echt matcht.

---

## `FA_THROW_ERROR_*`: een echte fout, geen "valse fout"

`FA_THROW_ERROR_LDZ`, `FA_THROW_ERROR_BRZ` en `FA_THROW_ERROR_SLV` in `PL_FMD_LOAD_ALL` zijn gewone Fail-activities. Ze maken de run rood **nadat** de fout in `logging.PipelineExecution` is weggeschreven. Hun foutcodes zijn `LandingzoneFailed`, `BronzeFailed` en `SilverFailed`.

De meldingstekst zegt het zelf: *"The Bronze layer failed. The failure is already recorded in logging.PipelineExecution; query it for the failing entity."*

Hetzelfde patroon (loggen en daarna opnieuw gooien) zit in elke `PL_FMD_LDZ_COMMAND_*`- en `PL_FMD_LDZ_COPY_FROM_*`-pipeline, en in `PL_FMD_LOAD_BRONZE`/`_SILVER`. Daar bevat de Fail-melding de `evalue` van het mislukte notebook.

**De oorzaak kan datakwaliteit zijn.** `NB_FMD_LOAD_LANDING_BRONZE` gooit bewust een fout:
- als een PK-kolom ontbreekt: `raise ValueError(f"PK: {pk_column} doesn't exist in the source.")`;
- als het bronbestand dubbele PK's bevat (cel "Check for Duplicates"): `raise ValueError(f'Source file contains duplicated rows for PK: …')`.

Ook dan is het een **echte** fout. De entiteit is niet geladen, en het bestand wordt bij elke volgende run opnieuw geprobeerd (zie *Herstarten*).

**Handelwijze:**
- Behandel `FA_THROW_ERROR_*` altijd als een incident.
- Zoek met de query hierboven de falende entiteit op.
- Is de oorzaak technisch (connectie, capaciteit, timeout)? Dan lost het beheerteam het op.
- Is de oorzaak datakwaliteit (PK ontbreekt of is dubbel)? Dan escaleer je naar de eigenaar van de brondata.

**Status:** vastgesteld (`PL_FMD_LOAD_ALL`, `PL_FMD_LOAD_BRONZE`, `NB_FMD_LOAD_LANDING_BRONZE`). Dit vervangt de eerdere beschrijving als "bewust valse fout, niet escaleren". Die was onjuist.

## Watermarkmechanisme (incrementeel laden)

Er zijn twee paden, en die werken verschillend.

**Standaardpad (`ConnectionType = 'SQL'`, `PL_FMD_LDZ_COPY_FROM_ASQL_01`):**
1. `vw_LoadSourceToLandingzone` bouwt voor elke entiteit twee queries:
   - `LastLoadValue`: een query die **aan de bronkant** `MAX(<IsIncrementalColumn>)` ophaalt;
   - `SourceDataRetrieval`: `SELECT * … WHERE <IsIncrementalColumn> > '<opgeslagen LoadValue>'`.
2. `LK_GET_LASTLOADDATE` voert eerst de `MAX()`-query uit, vóór de copy.
3. `CP_source_datalandingzone` kopieert met `SourceDataRetrieval`. Er is geen bovengrens: rijen die tussen stap 2 en 3 binnenkomen, worden nu én bij de volgende run meegenomen. De merge op PK in Bronze vangt die dubbelen op.
4. `SP_UPDATE_LASTLOADVALIE` slaat het maximum uit stap 2 op in `execution.LandingzoneEntityLastLoadValue`.
   - Sinds PR #24 (`7852a77`) gebeurt dat tot op de milliseconde: `CONVERT(VARCHAR(23), …, 121)`.
   - Daarvoor was het style 120, dus tot op de seconde. Rijen uit de laatste seconde werden dan elke run opnieuw geladen, zie `11_troubleshooting.md`.

Voor niet-incrementele entiteiten wordt `GETDATE()` als waarde opgeslagen. Is de opgeslagen `LoadValue` `NULL`, dan laat `SourceDataRetrieval` de `WHERE` weg en volgt er een full load.

**Custom-notebookpad (`ConnectionType = 'NOTEBOOK'`, zie `07_extension-points.md`):**
1. Het notebook ontvangt de opgeslagen waarde als parameter `LastLoadValue`.
2. Het notebook berekent zelf de nieuwe stand.
3. Het geeft die terug via `notebookutils.notebook.exit` met een `LoadValue`-sleutel.
4. `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB` → `SP_UPDATE_LASTLOADVALIE` schrijft `@json(…exitValue).LoadValue` weg.

⚠️ `NB_FMD_CUSTOM_NOTEBOOK_TEMPLATE` zet `LoadValue = datetime.now()`. Dat is het tijdstip van de run, niet het maximum van de data. Neem je dat over, dan worden records die later binnenkomen met een oudere tijdstempel nooit meer opgehaald. Gebruik in een custom notebook het maximum van de daadwerkelijk opgehaalde data.

**Status:** vastgesteld (view-definitie, `PL_FMD_LDZ_COPY_FROM_ASQL_01`, `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB`, template). De paden voor Oracle en SQLMI zijn niet in detail nagelopen.

**Snowflake-pad (`ConnectionType = 'SNOWFLAKE'`, `FMD_FRAMEWORK#40`):** hetzelfde verloop als het standaardpad, maar in Snowflake-syntax en uitgevoerd in Snowflake.
1. `LastLoadValue` is `SELECT TO_VARCHAR(MAX("<kolom>")::TIMESTAMP_NTZ, 'YYYY-MM-DD HH24:MI:SS.FF3') …`; bij een volledige load `CURRENT_TIMESTAMP()`, zonder de tabel te lezen.
2. `SC_COPY_INTO_LANDINGZONE` laat Snowflake met `COPY INTO` zelf het parquet-bestand schrijven (een map met meerdere bestanden), met `WHERE "<kolom>" > '<LoadValue>'`.
3. De watermark staat in de **tijdzone van het Snowflake-account** (standaard `America/Los_Angeles`, dus 9 uur achter op Nederland in de zomer). Berekening en vergelijking gebeuren allebei in Snowflake, dus het klopt. Reken hem niet om als je hem met de hand zet (*Een watermark resetten*).
4. De kolom moet `DATE` of `TIMESTAMP` zijn; een numerieke watermark faalt.
   - *Aanvulling 2026-10-26:* een kolom van het type `TIME` laadt niet naar Delta. Schrijf hem in `SourceColumns` als `naam::VARCHAR` (alleen `SNOWFLAKE_01`); zie `11_troubleshooting.md` ("Snowflake-landing faalt op een `TIME`-kolom"). *Getest in eigen omgeving* 2026-10-26 in FMD_TRIAL D (`TIME` in de key, runs `bbd8091b` zonder cast faalt, `7d51748b` met cast slaagt tot Silver).
5. **Een run zonder wijzigingen schrijft geen bestand.** Snowflake maakt bij 0 rijen geen map aan. Bronze logt dan `SourceFileName: FILE NOT FOUND` in `logging.NotebookExecution`, zet de levering op verwerkt en eindigt groen. Dat is normaal en geen fout; bij ASQL landt in dat geval een leeg bestand. *Getest in eigen omgeving* 2026-10-07 (landing `f2302259`, Bronze `acb96646`).

**Status:** *getest in eigen omgeving* 2026-10-07 (`testplan-trial.md` T-F04: run `5a5fbb21` haalde 4 gewijzigde rijen op, watermark `2026-10-06 10:46:35.174` → `2026-10-07 00:03:15.948`).

## Een watermark resetten

Een volledige herlading van één entiteit forceer je door de opgeslagen waarde leeg te maken:

```sql
UPDATE [execution].[LandingzoneEntityLastLoadValue]
SET    [LoadValue]        = NULL
      ,[LastLoadDatetime] = GETDATE()
WHERE  [LandingzoneEntityId] = <LandingzoneEntityId>
```

- **Verwijder de rij niet.** `vw_LoadToBronzeLayer` doet een `INNER JOIN` op `execution.LandingzoneEntityLastLoadValue`. Zonder die rij komt de entiteit na de volgende landing niet meer in Bronze, tot de rij opnieuw is aangemaakt.
- Een reset tot een bepaald punt kan ook: vul dan de gewenste ondergrens in, in hetzelfde formaat als de kolom. Sinds PR #24 (`7852a77`) is dat `CONVERT(VARCHAR(23), …, 121)` (milliseconde-precisie); in een fork van vóór PR #24 was dat nog `CONVERT(VARCHAR, …, 120)` (seconde-precisie) — zie *Watermarkmechanisme* hierboven.
- Voor een incrementele entiteit voert Bronze een merge uit zonder deletes. Een full reload werkt bestaande rijen bij en voegt nieuwe toe. In de bron verwijderde rijen blijven staan.

**Status:** vastgesteld (view-definities en `sp_UpsertLandingZoneEntityLastLoadValue`); niet als procedure getest in de eigen omgeving.

## Herstarten na een fout

- **Gewoon opnieuw starten mag.** Door de `Completed`-ketening kun je `PL_FMD_LOAD_ALL` (of één laag-pipeline) opnieuw starten, met dezelfde parameters. Landingzone-bestanden die nog niet verwerkt zijn (`IsProcessed = 0`), worden in de volgende Bronze-run opgepakt. `sp_UpsertPipelineLandingzoneEntity` voegt geen dubbele registratie toe voor hetzelfde bestand.
- **Een bestand dat in Bronze faalt, blijft hangen.** Een bestand dat bijvoorbeeld door dubbele PK's faalt, blijft `IsProcessed = 0` en wordt elke run opnieuw geprobeerd; vóór PR #18 3 keer per run (`"retry": 2` in `NB_FMD_PROCESSING_PARALLEL_MAIN`), daarna 1 keer. Die verwerkt de bestanden van één entiteit op volgorde, met een dependency op het vorige bestand. Een gefaald bestand houdt daardoor de latere bestanden van die entiteit tegen: die worden niet gestart, maar tellen wel als gefaald (*"Failed notebooks: ['<Tabel>_0_0', '<Tabel>_0_1']"*). Getest in de hertest (`testplan-trial.md` T-D04).
- **Herstel via de configuratie werkt.** Is de oorzaak een registratiefout (bijvoorbeeld verkeerde `PrimaryKeys`), corrigeer die dan en start opnieuw. De wachtende bestanden worden dan op volgorde verwerkt (T-D04: drie bestanden in één run).
- **Herstel** zo'n bestand door de bron te corrigeren en opnieuw te landen, of door het bestand bewust over te slaan:
  ```sql
  UPDATE [execution].[PipelineLandingzoneEntity]
  SET    [IsProcessed]     = 1
        ,[LoadEndDateTime] = GETDATE()
  WHERE  [LandingzoneEntityId] = <LandingzoneEntityId>
    AND  [FileName]            = '<bestandsnaam>'
  ```
  Leg het overslaan vast. De data uit dat bestand komt dan niet in Bronze.
- **Een kopie die op throttling faalt** (`UserErrorWithLargeConcurrentRuns`): vanaf branch `fix/landing-copy-retry` probeert de Copy-activiteit het zelf nog 3 keer, met 120 s ertussen. Zo'n herhaling zie je niet in `logging.CopyActivityExecution` (één `StartCopyActivity` per entiteit), wel in de runhistorie van de copy-pipeline in Fabric. Zie `11_troubleshooting.md` (*vastgesteld* in de pipelinedefinitie; de werking bij echte throttling is een *aanname*).
- **Custom notebook:** een fout die niet als `NotebookExecutionException` binnenkomt, wordt in `NB_FMD_PROCESSING_LANDINGZONE_MAIN` geslikt. Het notebook sluit af met `exit(None)`, en de fout duikt pas op in `SP_UPDATE_LASTLOADVALIE` (ongeldige `exitValue`). Kijk bij zo'n melding dus in de run van het custom notebook zelf.

**Status:** blokkeren en herstel via configuratie getest in eigen omgeving (2026-09-26, `testplan-trial.md` T-D03/T-D04); het gedrag van custom notebooks is vastgesteld in de code, niet getest.

*Correctie 2026-09-28 (demoklant, `plan-demoklant-trial.md`):* het overslaan van een bestand is nu ook **getest in eigen omgeving**. Run `7d56043f` (Dev) faalde op een dubbele PK in `fin_SalesTarget_202609281745.csv` (entiteit 33). Na een goed bestand en de `UPDATE` hierboven (1 rij) was de herstel-run `1ef8d3c3` `Completed`: het nieuwe bestand ging door Bronze en Silver, zonder blokkade.

## Silver opnieuw opbouwen na een gewijzigde cleansing rule

Silver verwerkt alleen entiteiten die een open rij hebben in `execution.PipelineBronzeLayerEntity` (`vw_LoadToSilverLayer`, `IsProcessed = 0`). Pas je een Silver-regel aan, dan gebeurt er dus niets tot de volgende Bronze-levering. Die levering verwerkt bovendien alleen de rijen die met de nieuwe regel een andere hash krijgen. Wil je de nieuwe regel op de hele tabel, dan zet je de entiteit zelf opnieuw in de wachtrij. Ook het al dan niet verwijderen van de tabel kies je zelf.

| | Alleen opnieuw in de wachtrij | Tabel verwijderen en opnieuw opbouwen |
|---|---|---|
| `IsHistorized = 0` (standaard) | Geraakte rijen worden bijgewerkt. Voldoende als de regel alleen waarden verandert. | Nodig als de regel een kolomtype verandert of een kolom toevoegt. |
| `IsHistorized = 1` | Elke geraakte rij krijgt een nieuwe versie. De fout opgeschoonde versie blijft als historie staan. | De tabel komt in één run opnieuw uit Bronze, met één versie per rij. De opgebouwde historie is weg. |

Waarom een vormwijziging altijd een nieuwe tabel vraagt: de merge schrijft alleen de kolommen van de **bestaande** tabel (`NB_FMD_LOAD_BRONZE_SILVER`, `columns_to_insert`). Een nieuwe kolom wordt overgeslagen, een hernoemde breekt de merge.

**Stappen** (per omgeving; de configdb is gedeeld, de tabel en de pipeline horen bij de omgeving):
1. Pas de regel aan: `EXEC integration.sp_UpsertSilverCleansingRule @SilverLayerEntityId = <id>, @CleansingRules = N'<json>'` (`NULL` haalt hem weg).
2. Alleen bij opnieuw opbouwen: verwijder de tabel in `LH_SILVER_LAYER` van die omgeving (`Tables/<namespace>/<Schema>_<Name>`).
3. Zet de entiteit opnieuw in de wachtrij. *Via `NB_REGISTRATIE` (toegevoegd 2026-10-15, `FMD_FRAMEWORK#72`, PR open, gemerged als `daf07ac` (bijgewerkt 2026-10-29); getest in trial-Dev, `testplan-trial.md` T-C12):* registreer met `register(..., dry_run=False, requeue_silver=True)`. Dat past de regel toe (stap 1) en zet precies de entiteiten met een gewijzigde Silver-regel in de wachtrij; de dry run toont een hint zodra een Silver-regel verandert. Stap 2 (de tabel verwijderen) blijft handwerk, en moet vóór de eerstvolgende Silver-run. Niet getest: een load na de requeue en meerdere entiteiten tegelijk. *Of rechtstreeks, vanaf `execution.sp_RequeueSilverLayerEntities` (`FMD_FRAMEWORK#67`, gemerged 2026-10-15; getest in trial-Dev, T-D14)*: `EXEC execution.sp_RequeueSilverLayerEntities @WorkspaceId = '<DATA-workspace>', @Entities = N'<SourceSchema.SourceName>'` toont als dry run (standaard) welke entiteiten het raakt; met `@DryRun = 0` zet hij ze in de wachtrij. Filter en quotes werken als bij *Een subset van tabellen laden*. Zonder die procedure, met `Schema` en `Name` uit `integration.BronzeLayerEntity`:
   ```sql
   EXEC [execution].[sp_UpsertPipelineBronzeLayerEntity]
        @BronzeLayerEntityId = <id>, @SchemaName = N'<Schema>', @TableName = N'<Name>', @IsProcessed = 0;
   ```
   Staat er al een open rij, dan voegt de procedure niets toe.
4. Draai `PL_FMD_LOAD_SILVER`, met `Data_WorkspaceGuid` van de DATA-workspace van die omgeving en met `DataSourceName`/`Entities`, zodat alleen deze tabellen lopen (*Een subset van tabellen laden*). Zonder `Data_WorkspaceGuid` is de run groen en laadt hij niets, in een fork van vóór `FMD_FRAMEWORK#66` (gemerged 2026-10-15). Vanaf #66 valt de pipeline terug op `VAR_CONFIG_FMD.fmd_data_workspace_guid` van de eigen omgeving (T-D13).
5. Controleer het aantal rijen, `IsCurrent` en een paar waarden.

**Let op:**
- De bron van de herbouw is de Bronze-tabel: bij een volledige load de laatste levering, bij een incrementele alle rijen die ooit binnenkwamen. Rijen die eerder uit de bron verdwenen, staan niet meer in Bronze en komen dus helemaal niet terug in Silver, ook niet als soft delete.
- Na go-live kost een herbouw van een tabel met `IsHistorized = 1` zijn historie. Leg de regels vast vóór de eerste productieload.
- Klopt een **Bronze**-regel niet, dan is dit niet genoeg: Bronze bewaart geen historie en moet opnieuw uit de landing zone of uit de bron komen (`15_opslagbeheer.md`, het punt *Bronze opnieuw opbouwen*, en *Een watermark resetten* hierboven).

**Status:** *getest in eigen omgeving* 2026-10-14 (trial-Dev, `TPCH.NATION`, `testplan-trial.md` T-D11):
- alleen opnieuw in de wachtrij, met historie: run `77c986df`, 25 nieuwe versies naast de 25 oude;
- zonder historie: run `bf1dc6b0`, de rijen bijgewerkt en geen nieuwe versies;
- tabel verwijderd: runs `79bd78f2` en `17c7a7f7`, elk 25 rijen met één versie.

Het verwijderen is getest via de OneLake-API, niet via de lakehouse-UI. Dat een vormwijziging zonder verwijderen misgaat, is *vastgesteld* in de code en niet getest.

## Harde timeouts

De framework-pipelines hebben vaste timeouts. Een eerste full load bij een klant, of één grote merge in Bronze of Silver, kan daar tegenaan lopen. De melding is dan een timeout, geen inhoudelijke fout, en door de `Completed`-ketening draait de volgende laag gewoon door.

| Waar | Timeout |
|---|---|
| `PL_FMD_LOAD_ALL` → Invoke LZ, Bronze en Silver | 1 uur per laag (`0.01:00:00`) |
| `PL_FMD_LOAD_LANDINGZONE` → `PL_FMD_LDZ_COMMAND_*` | 1 uur (NOTEBOOK en ORACLE: 12 uur) |
| `PL_FMD_LDZ_COMMAND_NOTEBOOK` → `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB` | 1 uur, dus de 12 uur erboven is niet het echte plafond |
| `PL_FMD_LOAD_BRONZE`/`_SILVER` → `NB_FMD_PROCESSING_PARALLEL_MAIN` | 1 uur (de DAG zelf: `timeoutInSeconds: 7200`) |
| `runMultiple` in `PARALLEL_MAIN`, per notebookcel | 10 minuten (`timeoutPerCellInSeconds: 600`) |
| Custom notebook via `NB_FMD_PROCESSING_LANDINGZONE_MAIN` | 15 minuten (`notebookutils.notebook.run(…, 900, …)`) |

**Handelwijze:**
- Schat bij de intake het volume van de eerste load.
- Draai grote bronnen bij de eerste keer apart, met een eigen `LoadGroup`.
- Verhogen van een timeout is een wijziging aan de generieke laag. Dat loopt via de fork (B-ARCH-02), niet via een klantaanpassing.

**Status:** vastgesteld (`policy.timeout` in de genoemde pipeline-JSON, `NB_FMD_PROCESSING_PARALLEL_MAIN`, `NB_FMD_PROCESSING_LANDINGZONE_MAIN`).

## Livy-sessies

Livy-sessies (gebruikt door notebooks) sterven na inactiviteit of lang wachten, met `LIVY_JOB_TIMED_OUT` als gevolg. **Controleer de sessiestatus vóór gebruik en maak zo nodig een nieuwe sessie aan.**

**Status:** getest in eigen omgeving (optreden gelogd in `bronnen/claude-code-transcripten/origineel/7e1e81a3….jsonl`).

## Capaciteitscontentie

Notebook-jobs en Livy-sessies kunnen bij drukte op de gedeelde capaciteit 15 tot 30+ minuten in de wachtrij staan (`NotStarted`/`queued`). Dat is geen fout: poll geduldig, elke 60 tot 180 seconden. Duurt het meer dan 20 à 25 minuten, leg dan aan de gebruiker of klant voor of doorwachten gewenst is.

**Status:** vastgesteld.

## Na elke promotie

*Correctie 2026-10-06 (review 3, P3-R7):* de volgorde van promoveren, registreren en laden staat in één runbook: draaiboek fase 7 stap 2. Deze sectie is de controlelijst na de promotie. Twee verschillen met de versie hieronder:
- de registratie in het doel hoort vóór de load. *Correctie 2026-10-13:* die gaat nu via `NB_REGISTRATIE`
  met dezelfde lijst en `environments=["T"]` of `["P"]` (ADR-018, getest in T op 2026-10-13); voorheen
  was het het lijstsjabloon uit draaiboek §A.4a;
- de shortcuts gaan mee met de promotie van de DATA-workspace van het domein, en die promotie kan pas na de load (anders `CopyOverwriteResult.GenericError`). Het shortcut-notebook is alleen een terugvaloptie.

Een promotie kopieert definities, geen data. Doe per doelomgeving, in deze volgorde:
1. **Load:** `PL_FMD_LOAD_ALL` in INTEGRATION CODE van de doelomgeving. Shortcuts kunnen pas bestaan als Silver daar gevuld is.
2. **Shortcuts:** ~~het shortcut-notebook van het domein.~~ *(2026-10-06: controleer de shortcuts, `GET …/items/{LH_GOLD_LAYER}/shortcuts`; draai het notebook alleen als ze ontbreken.)* Het shortcut-notebook van het domein: In de demoklant is dat `NB_GOLD_SHORTCUTS`, dat faalt als een shortcut niet lukt. Het framework-notebook `NB_CREATE_SHORTCUTS` faalt sinds PR #31 ook bij een mislukte shortcut; in oudere forks eindigt het groen (`11_troubleshooting.md`).
   > **Aanvulling 2026-10-07:** een nieuwe tabel in Silver krijgt pas een shortcut als je hem in de lijst van dat notebook zet (`ShortcutNames`, of `SHORTCUTS` in `NB_GOLD_SHORTCUTS`) en het notebook draait. Een bestaande shortcut verandert niet. Met PR `FMD_FRAMEWORK#45` (*getest in eigen omgeving*, 2026-10-07, runs in `testplan-trial.md`; gemerged 2026-10-07, `a5acd94`) accepteert `NB_CREATE_SHORTCUTS` een `(schema, tabel)`-paar, zodat `NB_GOLD_SHORTCUTS` niet meer nodig is. Het notebook is klant-eigen: pas een bestaande installatie met de hand aan in Dev en promoveer.
3. **MLV's:** het MLV-notebook van het domein. De refresh-cel ververst de Gold van de eigen omgeving en faalt bij een mislukte refresh (PR #21). Daarna het SQL-endpoint van Gold bijwerken (`POST …/sqlEndpoints/{id}/refreshMetadata`). De MLV-refresh doet dat niet, en een Direct Lake-model op het SQL-endpoint geeft anders *Invalid object name* (Prod, 2026-09-28). In de demoklant doet de laatste cel van het MLV-notebook dit.
4. **Direct Lake:** controleer met `GET …/datasets/{id}/datasources` dat elk model naar Gold van de doelomgeving wijst. Met een data source rule gebeurt dat vanzelf; zonder rule niet (draaiboek fase 7, stap 4b). *Aanvulling 2026-10-26 (T-E08):* bij een model op OneLake (`AzureStorage.DataLake`) is de data source rule niet beschikbaar; gebruik daar een parameter rule (`06_BUSINESS_DOMEINEN/04_semantisch-model-direct-lake.md`, *Variant: Direct Lake op OneLake*).
5. **Rapporten:** controleer dat `datasetId` van elk rapport het model in de doelomgeving is. De deployment pipeline koppelt dat om.
6. **Schema's** (*toegevoegd 2026-10-06*, rookproef 2):
   - Een promotie van INTEGRATION CODE zet de schema's van `PL_FMD_ORCHESTRATION` mee, ingeschakeld en met hun parameters, maar zonder de ontvangers van *Failure notifications*.
   - Controleer de tijden en voeg de ontvangers opnieuw toe. Zet uit wat in deze omgeving niet gepland hoort te draaien.
   - *Aanvulling 2026-10-08 (eindcontrole E-R4):* hetzelfde voor het schema van `PL_FMD_MAINTENANCE`, ook in INTEGRATION CODE: het tijdstip buiten het laadvenster, de ontvangers, en een laatste run die `Completed` is (`15_opslagbeheer.md`).
   - *Correctie 2026-10-11 (`FMD_FRAMEWORK#52`, gemerged 2026-10-11, `4971d88`):* met de schedule-pipelines in INTEGRATION CONFIG vervalt deze stap voor schema's en ontvangers: een promotie raakt ze niet (*getest in eigen omgeving*, operatie `5351536f`). Controleer wel nog dat de laatste maintenance-run `Completed` is. Een installatie die nog schema's op de pipelines in CODE heeft, houdt deze stap totdat ze is overgezet.

Draai loads in verschillende omgevingen niet tegelijk. Veel parallelle notebooks tegen dezelfde configdb gaven een `Login timeout expired` (zie `11_troubleshooting.md`).

**Status:** getest in eigen omgeving (2026-09-28, demoklant D → T → P; `plan-demoklant-trial.md`).

## De setup opnieuw draaien als update

Een bestaande installatie breng je op de actuele fork door de setup opnieuw te draaien: bootstrap → `NB_SETUP_FMD` → `NB_SETUP_BUSINESS_DOMAINS`.
- **Wat de setup doet:** alle framework-items worden overschreven (`fab import -f`), de dacpac wordt opnieuw uitgerold, en de registraties in de configdb blijven staan. Bestaande deployment pipelines en stages slaat de setup over.
- **Klantitems** met een eigen naam kent de setup niet, en die blijven dus staan.
- *Aanvulling 2026-10-08 (review 3, P3-R1; `FMD_FRAMEWORK#47`):*
  - **Overschrijven gebeurt in D, T én P tegelijk, buiten de promotie om.** Een framework-item in Prod verandert dus bij de setup-run, niet pas bij de volgende promotie.
  - **Uitzondering, de klantnotebooks:** `NB_FMD_CUSTOM_DQ_CLEANSING` (vanaf #28) en de Gold-notebooks `NB_LOAD_GOLD`, `NB_MLV_EXAMPLE` en `NB_CREATE_SHORTCUTS` (vanaf #47) worden één keer aangemaakt en daarna nooit overschreven. Een fix in een van deze templates bereikt een bestaande installatie daardoor niet vanzelf: neem hem met de hand over in Dev, en promoveer.
  - ~~`PL_FMD_LOAD_GOLD_TEMPLATE` wordt wel overschreven. Zet daar geen klantcode in.~~ *Correctie 2026-10-12 (`FMD_FRAMEWORK#58`, vastgesteld in `NB_UTILITIES_SETUP_FMD`, `CUSTOMER_OWNED_ITEMS`):* ook `PL_FMD_LOAD_GOLD` is klanteigendom. De setup maakt hem één keer per stage (D/T/P) aan en overschrijft hem daarna niet.
    - De klant voegt zijn eigen Gold-notebooks in Dev als activity aan `PL_FMD_LOAD_GOLD` toe, en promoveert. Promoveer de notebooks samen met of vóór de pipeline, anders faalt de promotie met *Missing Dependencies* (`testplan-trial.md` T-A07b).
    - Een latere framework-wijziging aan de Gold-pipeline bereikt een bestaande installatie daardoor niet: neem hem met de hand over in Dev, en promoveer.
  - *Toegevoegd 2026-10-16 (ADR-018; vastgesteld in `NB_UTILITIES_SETUP_FMD`, `CUSTOMER_OWNED_ITEMS`):* ook **`NB_REGISTRATIE`** is klanteigendom en wordt één keer geplaatst. `NB_FMD_REGISTRATION_FUNCTIONS` (bibliotheek en editor in één notebook) wordt wel bij elke setup-run overschreven. Een bestaande installatie krijgt dus de nieuwe editor en de knop *Ontdekking starten (pipeline)* vanzelf, maar behoudt zijn oude `NB_REGISTRATIE`: heeft die nog de lijstcellen, neem dan de nieuwe cellen over (`registration_ui(...)`) of verwijder het item en laat de setup het opnieuw plaatsen. Een kopie die `%run NB_FMD_REGISTRATION_UI` doet, bestaat alleen in onze eigen testinstallaties en moet daar worden aangepast. Bijgewerkt is alleen `FMD_EIND INTEGRATION CONFIG` (2026-10-16); trial, GR en andere installaties niet.
  - *Toegevoegd 2026-10-21 (branch `registratie-python-kernel`, PR volgt, gemerged als `FMD_FRAMEWORK#81`, `4bd204c` (bijgewerkt 2026-10-29); `testplan-trial.md`, vervolg 2026-10-21):* `NB_REGISTRATIE` en `NB_FMD_REGISTRATION_FUNCTIONS` draaien op een Python-kernel (`jupyter`, `python3.12`) in plaats van `synapse_pyspark`: er is geen sessiestart van Spark meer nodig. *Vastgesteld* (code gelezen): de functies gebruiken alleen `pyodbc`, `requests`, `notebookutils` en `ipywidgets`, geen Spark. *Getest in eigen omgeving* (trial CONFIG, 2026-10-21): `%run`, ODBC Driver 18, het token, `load_registration` en `register(..., dry_run=True)` werken; de editor-cel start en rendert (de knoppen zijn niet bediend). Omdat `NB_REGISTRATIE` klanteigendom is, behoudt een bestaande installatie na een setup-run zijn Spark-kernel, terwijl `NB_FMD_REGISTRATION_FUNCTIONS` wel naar Python gaat. Die combinatie is getest en werkt (Spark-`NB_REGISTRATIE` met Python-bibliotheek, `Completed`, 32 s). Wil je de Python-sessie, zet dan in het eigen `NB_REGISTRATIE` de kernel op Python (via `updateDefinition` met `kernel_info` `jupyter`/`python3.12` en `language_group` `jupyter_python`, zoals in de trial gedaan; de route via de Fabric-UI is niet getest). *Aanname:* de kosten per sessie zijn lager (2 vCores in plaats van een Spark-node met 8 vCores); niet gemeten op de capaciteit. Niet getest: de editor-knoppen in de Python-runtime.
  - Vóór #47 zette een setup-run de Gold-notebooks in D, T en P terug naar de lege template.
  - *Getest in eigen omgeving* (2026-10-07, FMD_TRIAL, run `67a8e09d` van `NB_SETUP_BUSINESS_DOMAINS`; notebooknaam toegevoegd 2026-10-11, E-V4): test-klantcode in `NB_LOAD_GOLD` van FINANCE D/T/P bleef staan, en alle 18 Gold-notebooks bleven gelijk.
- *Toegevoegd 2026-10-12 (`FMD_FRAMEWORK#58`, vastgesteld):* **hernoem eerst bij een installatie van vóór #58.** Hernoem in elke stage (D, T, P), in de workspace zelf, `PL_FMD_ORCHESTRATION_TEMPLATE` naar `PL_FMD_ORCHESTRATION` (INTEGRATION CODE) en `PL_FMD_LOAD_GOLD_TEMPLATE` naar `PL_FMD_LOAD_GOLD` (CODE van elk domein). Doe dat vóór de setup-run.
  - De setup zoekt items op naam. Zonder hernoemen maakt hij nieuwe items naast de oude.
  - `PL_FMD_SCHEDULE_<short>` verwijst op ID, en blijft dan de oude orchestratie aanroepen (zie *Plannen*).
  - Is het al gebeurd: zie `11_troubleshooting.md`, *Na een setup-update staan er twee orchestratie- of Gold-pipelines*.
- **Let op:** in een fork van vóór `FMD_FRAMEWORK#70` staat `load_demo_data = True` vast in cel 5 van `NB_SETUP_FMD`. De demo-entiteit `in.customer` en `Tables/in/customer` in de landingzone komen daardoor bij elke setup-run terug; verwijder ze na de run als je ze niet wilt. Vanaf #70 (gemerged 2026-10-15) staat dit in het manifest als `framework.load_demo_data`, standaard `false`; wie de demo wil, zet het op `true`.
- **Controleer daarna** of de items gelijk zijn aan `src/` (`getDefinition`). Verschillen in serialisatie, zoals een `-- MAGIC`-prefix of weggelaten metadata, zijn normaal.

**Status:** getest in eigen omgeving (2026-09-28, runs `dc5413b0`, `9bc2b5ef`, `ba6664cd`; eerst een export van de configdb-registratie als vangnet).

## Samenvatting operationele routine

| Frequentie | Actie |
|---|---|
| Na elke geplande run | Falende entiteiten opzoeken met de query onder *Monitoring*. Een groene pipeline alleen is niet genoeg. |
| Bij `FA_THROW_ERROR_*` / `LandingzoneFailed` / `BronzeFailed` / `SilverFailed` | Behandelen als incident: falende entiteit opzoeken, technisch oplossen of escaleren naar de broneigenaar |
| Per load-run | Bij een wachttijd van meer dan 20 à 25 minuten: denk aan capaciteitscontentie, niet aan een storing |
| Bij een timeout-melding | Volume tegenover de timeouts hierboven; zo nodig de bron in een eigen `LoadGroup` |
| Bij gebruik van notebooks na een langere pauze | Livy-sessiestatus controleren vóór gebruik |
| Na elke deployment | Shortcuts/Direct-Lake-checklist uitvoeren, zie `09_cicd-en-deployment.md` |
| Wekelijks (schema op `PL_FMD_MAINTENANCE`) | Verwerkte leveringen ouder dan de bewaartermijn opruimen en `VACUUM` op Bronze en Silver. Controleer de run: een fout laat de pipeline falen met de lijst van fouten. Zie `15_opslagbeheer.md` (`FMD_FRAMEWORK#42`). |

---

## Historie in Silver per tabel (`IsHistorized`)

Silver houdt standaard alleen de huidige rij per sleutel. *(Correctie 2026-10-13: tot en met v3.5 stond hier dat Silver standaard de historie bijhoudt (SCD2) en dat je `IsHistorized` op 0 zet; sinds ADR-016 *Herzien 2026-10-13* is dat omgekeerd, omdat historie die niemand vraagt opslag en merge-tijd kost.)* Voor een tabel waar de klant de historie van wijzigingen wil, zet je `IsHistorized` op 1 in het lijstsjabloon (`registreer_entiteiten.sql`, kolom `IsHistorized`; leeg betekent 0) en draai je het sjabloon opnieuw. Betekenis (ADR-016, *vastgesteld* in `NB_FMD_LOAD_BRONZE_SILVER`):

| | `IsHistorized = 1` (SCD2) | `IsHistorized = 0` (standaard) |
|---|---|---|
| Gewijzigde rij | nieuwe versie; de oude krijgt `IsCurrent = 0` en een `RecordEndDate` | de huidige rij wordt bijgewerkt (`RecordModifiedDate` verschuift) |
| Verwijderde bronrij | `IsDeleted = 1`, `IsCurrent = 0` | idem |
| Terugkerende sleutel | nieuwe huidige rij naast de gesloten rij | idem |

- Omschakelen 1 naar 0: de bestaande historie blijft staan; ruim ze zelf op (`IsCurrent = 0 AND IsDeleted = 0`) als je de opslag wilt terug hebben. Omschakelen 0 naar 1: de historie begint vanaf dat moment.
- Een Gold-query op `IsCurrent = 1` werkt voor beide standen.
- Dit verkleint de opslag, maar niet de rekentijd per run: Silver leest elke run de hele Bronze- en Silver-tabel (*vastgesteld*). Alleen de wijzigingen lezen is een apart voorstel.
- De kolom komt met een nieuwe dacpac (ADR-013); bestaande entiteiten krijgen 1. *(Correctie 2026-10-13: de dacpac met default 0 laat bestaande rijen ongemoeid; die behouden hun waarde.)*
- **Bestaande installatie na de default-wijziging (2026-10-13):** de volgende registratierun zet elke entiteit met een lege `IsHistorized` in de lijst op 0, ook als ze eerder 1 had. De lijst is de waarheid. Wie voor een tabel historie nodig heeft, zet vóór die run `IsHistorized = 1` in de lijst. De historie die al in Silver staat blijft staan, maar groeit niet meer.
- Een entiteit die buiten de lijst om wordt geregistreerd (`sp_UpsertLandingzoneBronzeSilver`, `PL_TOOLING_POST_ASQL_TO_FMD`) krijgt bij aanmaak 0. *(Aanname uit de code: die procedures zetten de kolom niet zelf, dus de default geldt; niet apart getest.)*
- *Getest in eigen omgeving* 2026-10-09 (trial-Dev, `testplan-trial.md`).
- *Getest in eigen omgeving* 2026-10-13 (trial-Dev, `testplan-trial.md`, default 0): de default na publicatie van de dacpac, een dry-run en een echte run van `sp_RegisterEntities` met lege en met expliciete waarde. Een pipelinerun met een gewijzigde bronrij bij de nieuwe default is niet opnieuw getest; het merge-pad is ongewijzigd.

---

## Duur en aantal rijen per laag (`logging.vw_ExecutionSummary`)

*Toegevoegd 2026-10-20, `FMD_FRAMEWORK#80` (nog niet gemerged; bijgewerkt 2026-10-29: gemerged, `4c1c4c5`).* De view geeft per run, laag en entity de duur, de status en het aantal rijen. Alleen lezen, geen schemawijziging in de logtabellen.

| Kolom | Betekenis |
|---|---|
| `PipelineRunGuid`, `PipelineParentRunGuid` | De run en de pipeline die hem startte (keten `LOAD_ALL` > `LOAD_LANDINGZONE` > `COPY_FROM_*`). |
| `EntityLayer`, `EntityId`, `EntitySchema`, `EntityName` | Laag (`Landingzone`, `Bronze`, `Silver`) en de entity in die laag. Het `EntityId` is per laag een andere sleutel; de naam komt uit de bijbehorende `integration`-tabel. |
| `StartTime`, `EndTime`, `DurationSeconds` | Uit het eerste Start- en laatste End/Failed-record van die run (`LogDateTime`). |
| `Status` | `Succeeded`, `Failed` (`FailedCopyActivity`, of een notebook-End met `Action = Error`) of `Running` (nog geen End). |
| `RowsRead`, `RowsWritten` | Landingzone: `rowsRead` en `rowsCopied` uit de Copy-output. Bronze en Silver: `RowsWritten` (ingevoegd plus bijgewerkt). |
| `RowsInserted`, `RowsUpdated`, `RowsDeleted` | Alleen Bronze en Silver, uit `operationMetrics` van de Delta-commit (`MERGE`; bij de eerste lading `WRITE`, dan alles ingevoegd). |

- **Voorbeeld:** `SELECT EntityLayer, EntityName, DurationSeconds, Status, RowsWritten FROM logging.vw_ExecutionSummary WHERE EntityLayer = 'Bronze' ORDER BY StartTime DESC`.
- **Runs van vóór deze wijziging** hebben in Bronze en Silver wel duur en status, maar geen rijen (`NULL`). Een afgekapte `LogData` (de kolom is `VARCHAR(8000)`) geeft ook `NULL` voor de rijen.
- **Landingzone-rijen kwamen niet uit `LogData`:** het End-record van de Copy-activiteit was ongeldige JSON (komma voor de afsluitende accolade, zie `11_troubleshooting.md`). De view verwijdert die komma bij het lezen, en de pipelines zijn hersteld.
- De rijen komen uit `DESCRIBE HISTORY` van de eigen commit in de notebooks (`delta_version` en `delta_row_metrics` in `NB_FMD_UTILITY_FUNCTIONS`); er is geen extra scan.

**Status:**
- *Vastgesteld* (`FMD/src/Config_Database/logging/Views/vw_ExecutionSummary.sql`, `NB_FMD_UTILITY_FUNCTIONS`, `NB_FMD_LOAD_LANDING_BRONZE`, `NB_FMD_LOAD_BRONZE_SILVER`).
- *Getest in eigen omgeving* (2026-10-20): de view op SQL Server 2022 met testdata (LDZ ok met oude komma, LDZ fail, Bronze-merge, Silver-error, afgekapte JSON). In trial-Dev op de bestaande logs: alle 288 `EndCopyActivity`-records leesbaar (221 met rijen). Notebooks los bijgewerkt (geen setup); `PL_FMD_LOAD_BRONZE` (`31c4f465`) en `PL_FMD_LOAD_SILVER` (`94d5e840`) Completed. Bronze-aantallen kloppen met `DESCRIBE HISTORY`: `fx.fx_CurrencyRate` 4 ingevoegd, `aw.Sales_SalesOrderDetail` 307 bijgewerkt. Dit is een Fabric SQL database, de container-test is geen bewijs voor Fabric.
- *Getest in eigen omgeving* (2026-10-20, tweede ronde, Livy op LH_SILVER_LAYER): Silver-aantallen komen overeen met `DESCRIBE HISTORY` (`aw.Sales_SalesOrderDetail` 307 ingevoegd en 307 bijgewerkt, 614 uitvoerrijen; `aw.Sales_SalesOrderHeader` 126 en 126; `fx.fx_CurrencyRate` 4 en 0). Een historiserende wijziging telt dus als één update (oude rij sluiten) plus één insert. De helpers zijn los getest op een wegwerp-Delta-tabel: eerste lading (`WRITE`, versie -1) 5 ingevoegd; een merge met 1 insert, 1 update en 1 delete geeft 1/1/1 (written 2); een merge zonder wijzigingen commit geen nieuwe versie en geeft overal 0, dus zonder de versiecheck zouden oude aantallen terugkomen.
- *Niet getest:* het notebookpad voor de eerste lading en een delete in een echte Bronze- of Silver-run (alleen de helpers zijn getest); een bewust falende Silver-entity (alleen Bronze is getest, zie hieronder); de overige tien aangepaste LDZ-pipelines in een echte run.
- *Getest in eigen omgeving* (2026-10-20, vierde ronde, falende Landing-entity): `SourceFilter` van `LandingzoneEntityId` 38 tijdelijk op `NOSUCHCOLUMN_FMD_TEST = 1` (was `NULL`), `PL_FMD_LOAD_LANDINGZONE` met `Entities = Currency` (run `f65bb077`, Failed, melding `Operation on target FE_ENTITY failed ... SW_CHECK_DATASOURCENAME`). `logging.CopyActivityExecution` heeft `StartCopyActivity` en `FailedCopyActivity` (`errorCode 2100`, bronzijde); de view toont `Status = Failed`, `DurationSeconds` 21,094 en `RowsWritten` leeg. Daarna de entity teruggezet (`SourceFilter = NULL`, met een select gecontroleerd; geen rij met `FMD_TEST` over). Bijvangst: in `logging.PipelineExecution` stonden voor deze run alleen `StartPipeline`-records, geen Fail-record (alleen die run bekeken; niet onderzocht).
- *Getest in eigen omgeving* (2026-10-20, vijfde ronde, falend Bronze-notebook): `SourceColumns` van `LandingzoneEntityId` 38 tijdelijk op `CurrencyCode,Name` (was `NULL`), landing (run `92d97999`, Completed, smaller bestand zonder `ModifiedDate`), registratie direct teruggezet. `PL_FMD_LOAD_BRONZE` (run `becda796`) faalde met `DELTA_MERGE_UNRESOLVED_EXPRESSION`. `NotebookExecution` heeft een `EndNotebookActivity` met `{"Action": "Error", "ErrorMessage": "[DELTA_MERGE_UNRESOLVED_EXPRESSION] ..."}`; de view toont `Status = Failed`, 16,897 s en geen rijen. De Bronze-tabel bleef ongewijzigd (de merge faalde vóór het schrijven). Opruimen: wachtrijrij `PipelineLandingzoneEntityId` 291 (het smalle bestand) met `IsProcessed = 1` gesloten; daarna 0 onverwerkt in beide wachtrijen. Zonder die stap pakt de volgende Bronze-run het smalle bestand en faalt opnieuw.
- *Correctie 2026-10-20 (zesde ronde) op de bijvangst bij de falende Landing-run:* het Fail-record ontbrak niet. `logging.PipelineExecution` heeft voor run `f65bb077` een `FailPipeline`-record (12:53:32, na de `StartPipeline` van 12:50); de eerdere controle keek te vroeg of te smal. De activity runs (Fabric REST `queryactivityruns`) tonen `SP_FAIL_AUDIT_PIPELINE` Succeeded. **Wel vastgesteld:** het LogType verschilt per niveau. De orchestratiepipelines loggen `FailPipeline`/`EndPipeline`, de COMMAND- en COPY-pipelines `FailedPipeline` (zie de rijen van 12:52). Filter dus op `LogType LIKE 'Fail%'`, niet op een exacte waarde. `vw_ExecutionSummary` gebruikt `PipelineExecution` niet en is hierdoor niet geraakt. Bij de falende Bronze-run (`becda796`) staat ook een `FailPipeline`-record.

- *Getest in eigen omgeving* (2026-10-20, derde ronde): `PL_FMD_LDZ_COPY_FROM_ASQL_01` in trial-Dev met de komma-fix (via `updateDefinition`, back-up in de scratchpad `nbbackup`) en `PL_FMD_LOAD_LANDINGZONE` met `Entities = Currency` (run `aa627314`, Completed, 4:58 min): één entity (`LandingzoneEntityId` 38) liep, het End-record is geldige JSON zonder correctie (`ISJSON = 1`), de view toont 105 rijen gelezen en geschreven.

---

## De selectie van een brontabel wijzigen (`SourceFilter`, venster per omgeving)

*Toegevoegd 2026-11-02 (klant, Snowflake-database `DB_04268_SENPVOLMACHTCONCERN`).*

**Hoe het filter werkt (*vastgesteld*, `FMD/src/Config_Database/execution/Views/vw_LoadSourceToLandingzone.sql`):**
- `integration.LandingzoneEntity.SourceFilter` is een predicaat zonder `WHERE` en zonder variabelen. Het staat per entiteit, dus per omgeving (`LakehouseId`). Een "parameter per omgeving" is daarom een andere waarde in de rij van die omgeving.
- De view zet er de incrementele voorwaarde met `AND` bij (`kolom > watermark`), en gebruikt het filter ook in de query die het nieuwe watermark bepaalt. `copy_registration` kopieert `SourceFilter` niet naar T en P: een wijziging doe je per omgeving.
- Een kindtabel filtert met een semijoin op de ouder, bijvoorbeeld `(RELNR, VOLG, VOLG_SUB) IN (SELECT RELNR, VOLG, VOLG_SUB FROM "<db>"."ODS"."POLBES" WHERE <filter van de ouder>)`.

**Afspraak voor de klant (besluit Mitchell, 2026-11-02):** een kalenderjaarvenster in plaats van het rollende jaar, `>= DATE_FROM_PARTS(YEAR(CURRENT_DATE()) - n, 1, 1)`: D n = 1, T n = 3, P geen filter (`NULL`).

| Keten | Entiteiten (D / T / P) | Filter |
|---|---|---|
| Polis: `POLBES` en `DEKKING`, `DEKKINGVARDEEL`, `DEKKINGVERD`, `POLBESVARDEEL`, `WACBESVARDEEL`, `WACDEKVARDEEL`, `VERDEEL`, `VERDHIS`, `POLHIS`, `POLHISVARDEEL` | 177, 179 tot en met 186, 189, 190 / 357, 369 tot en met 371, 377, 386, 387, 391, 392, 438, 439 / 440, 452 tot en met 454, 460, 469, 470, 474, 475, 521, 522 | `(WIJZREDEN NOT BETWEEN '00040' AND '00049' OR WIJZ_DATUM >= DATE_FROM_PARTS(YEAR(CURRENT_DATE()) - n, 1, 1))`; kindtabellen met dit predicaat in de subquery op `POLBES`; P leeg |
| `WERKLYST` | 188 / 437 / 520 | `TAAK_DATUM >= DATE_FROM_PARTS(YEAR(CURRENT_DATE()) - n, 1, 1)`; P leeg |
| `AGENDA` | 187 / 434 / 517 | het bestaande `CASE`-filter op `DATUM_TIJD` met de nieuwe datumgrens; P leeg |

- Het predicaat voor de polis telt een polis mee als hij huidig is (`WIJZREDEN` buiten 00040 tot en met 00049) of recent gewijzigd is. *Vastgesteld* (Silver `ODS_POLBES`, huidige rijen): `WIJZREDEN` is `varchar`; van 979.308 rijen met 5 tekens liggen er 326.595 in 00040 tot 00049, 15 zijn `NULL`, de overige korte waardes zijn letter-gevolgd (`D90`, `D100`, `B95`) en vallen dus buiten het bereik. Een `NULL` telt niet als huidig (keuze Mitchell): zo'n rij komt alleen mee als `WIJZ_DATUM` recent is.
- Bij 28 entiteiten met een semijoin-filter zitten alle filterkolommen in de `PrimaryKeys` van de entiteit en de subquery-kolommen zijn de PK van de ouder (`ALGSCH01`, `POLBES`, `FACTUUR`); uitzondering `VERDSCH`, dat filtert op een afgeleide kolom (`LEFT(TO_VARCHAR(SCHADEKEY), LENGTH(...) - 2)`). `SourceFilter` was in D, T en P identiek (*vastgesteld*, configdb, 2026-11-02).

**Een verbreed filter haalt oude rijen niet binnen.** De delta is `EVENT_TIMESTAMP > watermark`; rijen die nu in het filter vallen maar een oudere `EVENT_TIMESTAMP` hebben, komen alleen met een volle load.
- Zet het watermark op `NULL` (`LoadValue`, de rij niet verwijderen, zie *Een watermark resetten*): *vastgesteld* in de view dat de incrementele voorwaarde alleen meekomt bij `LoadValue IS NOT NULL`, anders is het een volle selectie met alleen het filter.
- **Volgorde:** eerst het filter, dan het watermark. Andersom haalt de volle load nog met het oude filter op.
- Doe beide in één transactie met een controle op de oude waarde (`UPDATE ... WHERE SourceFilter = <oud>` gevolgd door `IF @@ROWCOUNT <> 1 ROLLBACK`). Zo verandert er niets als een omgeving intussen is aangepast. Leg de oude waarden vast om terug te kunnen draaien.
- **Schedule:** alleen `PL_FMD_SCHEDULE_D` bestaat (dagelijks 06:00). Een `NULL`-watermark in D start dus de volle load van de eerstvolgende nacht; T en P draaien alleen handmatig.
- Een PK die hierbij verandert, vraagt een rebuild van Bronze en Silver (zie `11_troubleshooting.md`, *Bronze faalt op `Source file contains duplicated rows for PK`*).

**Uitgevoerd 2026-11-02 (klant, door Mitchell; daarna teruggelezen door Claude):**
- Polis, `WERKLYST` en `AGENDA` in D, T en P met de filters uit de tabel; het watermark van D en T (polis, `WERKLYST`) en van D, T en P (`AGENDA`) op `NULL`. `WERKLYST` in P heeft geen watermark-rij (nooit geladen).
- P, `WERKLYST` (520): `TIJD` werd `TIJD::VARCHAR` in `SourceColumns`, nu gelijk aan D en T (de `TIME`-fout, zie `11_troubleshooting.md`). P blijft inactief tot de fractiecheck gedaan is.
- P, `EABSVERT` (503) en `RCAGSAL` (507): `PrimaryKeys` gelijk aan D en T (`X_FILLER_2`, respectievelijk `KANTOORCODE` en `SAL_TIJD` erbij); daarna op actief gezet. Beide waren in P nooit geladen (geen watermark-rij).
- *Controle D, T, P (alle entiteiten, configdb):* de PK's zijn gelijk in alle drie de omgevingen; `RCPRSAL` en `RCVOSAL` staan alleen in D en T, `STORNO` alleen in D.
- *Controle P:* `AGENDA` (517), `NAWBESVARDEEL` (459) en `POLBESVARDEEL` (460) zijn op 2026-11-02 tussen 11:41 en 12:10 opnieuw geladen (Landing, Bronze, Silver `Succeeded`, `logging.vw_ExecutionSummary`). Bronze en Silver hebben evenveel rijen als de landingzone en elke PK-hash is uniek (23.746.372, 39.552.949 en 401.789; Silver 0 verwijderd), dus een rebuild is niet meer nodig.

**Status:**
- *Vastgesteld:* de view, de filters en watermarks in de configdb na de wijziging (teruggelezen), de aantallen hierboven.
- *Niet getest:* een run met de nieuwe filters in Snowflake (de syntaxis van `DATE_FROM_PARTS` en het `CASE`-filter), de volle loads van D en T, en het volume van `POLBESVARDEEL`, `POLHIS` en `DEKKINGVARDEEL` zonder venster in P.
- *Nog open:* de controle dat `TIJD` geen fracties van een seconde heeft (`SELECT COUNT(*) FROM WERKLYST WHERE TIJD <> DATE_TRUNC('SECOND', TIJD)`, moet 0 zijn; `TIJD` zit in de PK) en het activeren van `WERKLYST` in P (520).
- Bronnen: `Progress.md` P-016, de scripts in de scratchpad van de sessie (`update_polis_selectie_*.sql`, `reset_watermark_polis_*.sql`, `werklyst_selectie_D_T_P.sql`, `agenda_selectie_D_T_P.sql`, `update_pk_P_eabsvert_rcagsal.sql`, `activeer_P_eabsvert_rcagsal.sql`; sessie-gebonden).

---

## Versiegeschiedenis

- v1 (2026-09-22): eerste versie.
- v2 (2026-09-25), naar aanleiding van review 1 (F1, F2, V3) en review 2 (M-F4, M-R1, M-R2, M-V1):
  - `FA_THROW_ERROR_*` gecorrigeerd: een echte fout, geen "valse fout", met de datakwaliteitsoorzaak erbij;
  - de `Completed`-ketening en de parameters van `PL_FMD_LOAD_ALL` toegevoegd;
  - het watermarkcontract gesplitst in het standaardpad en het custom-notebookpad (het was ten onrechte als één contract beschreven);
  - nieuwe secties *Een watermark resetten*, *Herstarten na een fout* en *Harde timeouts*;
  - de monitoringquery toegevoegd, en de kanttekening over `EndNotebookActivity`.
- v3 (2026-09-28), demoklant op de trial: secties *Na elke promotie* en *De setup opnieuw draaien als update*.
- v3.1 (2026-10-05): draft van de documentatie-impact-check (2026-09-28) verwerkt: *Een watermark resetten* gebruikt de notatie van PR #24 (stijl 121). *Na elke promotie* stap 2 bijgewerkt na PR #31.
- v3.2 (2026-10-07): *Watermarkmechanisme*: het Snowflake-pad, ook een run zonder wijzigingen (`FMD_FRAMEWORK#40`, `testplan-trial.md` T-F04).
- v3.3 (2026-10-07): *Samenvatting operationele routine*: wekelijks onderhoud met `PL_FMD_MAINTENANCE` (`FMD_FRAMEWORK#42`, `15_opslagbeheer.md`).
- v3.4 (2026-10-09): nieuwe sectie *Historie in Silver per tabel* (`IsHistorized`, ADR-016).
- v3.6 (2026-10-13, ADR-016 *Herzien*): *Historie in Silver per tabel*: standaard geen historie (`IsHistorized` default 0, leeg in de lijst is 0), SCD2 per tabel met 1; gevolg voor bestaande installaties erbij (branch `feature/silver-default-zonder-historie`, `FMD_FRAMEWORK#62`).
- v3.5 (2026-10-12, `FMD_FRAMEWORK#58`): nieuwe namen `PL_FMD_ORCHESTRATION` en `PL_FMD_LOAD_GOLD`. *De setup opnieuw draaien als update*: `PL_FMD_LOAD_GOLD` wordt niet meer overschreven (correctie), en een bestaande installatie hernoemt de twee pipelines vóór de setup-run.
- v3.7 (2026-10-13, branch `feature/subset-laden`): nieuwe sectie *Een subset van tabellen laden* (`DataSourceName`, `Entities`); parameters van `PL_FMD_LOAD_ALL` aangevuld.
- v3.8 (2026-10-14, `testplan-trial.md` T-D11): nieuwe sectie *Silver opnieuw opbouwen na een gewijzigde cleansing rule*.
- v3.10 (2026-10-15, `FMD_FRAMEWORK#70`, gemerged): *De setup opnieuw draaien als update*: `load_demo_data` uit het manifest.
- v3.9 (2026-10-15, `FMD_FRAMEWORK#66` en `#67` gemerged): verwijzingen naar de nieuwe procedure en de workspace-fallback bijgewerkt.
- (2026-10-15, `FMD_FRAMEWORK#68` gemerged): geen wijziging in deze tekst; zie `11_troubleshooting.md` voor `fill_nulls`, CSV en `LoadEndDateTime`.
- (2026-10-26, `testplan-trial.md` T-E08): *Na elke promotie* stap 4: parameter rule voor een Direct Lake-model op OneLake.
- v3.11 (2026-10-20, `FMD_FRAMEWORK#80`, gemerged als `4c1c4c5`): nieuwe sectie *Duur en aantal rijen per laag* (`logging.vw_ExecutionSummary`).
- (2026-11-02, klant): nieuwe sectie *De selectie van een brontabel wijzigen* (`SourceFilter`, kalenderjaarvenster per omgeving, volle load via het watermark).
