# Extensiepunten

**Fase:** 3 (Technische documentatie)
**Datum:** 2026-09-25
**Status:** Versie 2: gecorrigeerd na review 2 (M-F1, M-F2, M-R2, M-V1), zie versiegeschiedenis onderaan
**Bron:** `FMD/src/`: `PL_FMD_LDZ_COMMAND_*`, `PL_FMD_LDZ_COPY_FROM_*`, `NB_FMD_PROCESSING_LANDINGZONE_MAIN`, `NB_FMD_CUSTOM_NOTEBOOK_TEMPLATE`, `Config_Database/execution/Views/vw_LoadSourceToLandingzone.sql`, `Config_Database/integration/Tables/LandingzoneEntity.sql`

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

Dit document beschrijft de voorziene extensiepunten van het framework: de mechanismen waarmee je een klant- of bronspecifieke behoefte inbouwt **zonder** de generieke pipelines en notebooks te wijzigen (ADR-003). Het beschrijft ook de registratiewaarden die de pipelines verwachten. Een afwijking daarin geeft geen foutmelding, maar laadt stil niets.

## 1. `ConnectionType` en `DataSourceType`: een vaste lijst

De Landingzone kiest per bron een copy-pipeline in twee stappen:
1. `PL_FMD_LOAD_LANDINGZONE` roept per connectietype een `PL_FMD_LDZ_COMMAND_*`-pipeline aan. Die zoekt in `execution.vw_LoadSourceToLandingzone` op **`ConnectionType`** (`Connection.Type`).
2. De `PL_FMD_LDZ_COPY_FROM_*`-pipeline die daarna draait, filtert opnieuw, nu op een **hardcoded `DataSourceType`** (`DataSource.Type`).

Alleen deze combinaties worden geladen:

| `Connection.Type` | Toegestane `DataSource.Type` | Copy-pipeline |
|---|---|---|
| `SQL` | `ASQL_01`, `ASQL_02` | `PL_FMD_LDZ_COPY_FROM_ASQL_01` |
| `AZURESQLMI` | `SQLMI_01` | `PL_FMD_LDZ_COPY_FROM_SQLMI_01` |
| `ORACLE` | `ORACLE_01` | `PL_FMD_LDZ_COPY_FROM_ORACLE_01` |

*Toegevoegd 2026-10-29 (bron: `origin/main` `fbaf0c0`, pipeline-JSON gelezen; reden: review klantdocumentatie). Op verzoek van Mitchell staan deze drie typen niet in de klantdocumentatie.*
- **`SQLMI_01`** (*vastgesteld*, *niet getest*): `LK_GET_LASTLOADDATE` voert `@item().LastLoadValue` uit als `sqlReaderQuery`, maar `vw_LoadSourceToLandingzone` geeft voor `AZURESQLMI` daar de opgeslagen `LoadValue` (alleen `SQL`, `SNOWFLAKE` en `ODATA` krijgen een query). *Aanname:* de watermarkstap faalt, ook bij de eerste load (waarde `NULL`).
- **`ORACLE_01`** (*vastgesteld*, *niet getest*): de `oracleReaderQuery` van `CP_source_datalandingzone` is alleen het `WHERE`-deel (of leeg), zonder `SELECT`; de uitvoer van `LK_GET_COLUMNNAMES` wordt er niet in gebruikt en de dataset heeft geen tabel. *Aanname:* de kopie faalt.
- **`ADF`** (*vastgesteld*): `PL_FMD_LDZ_COPY_FROM_ADF` roept `PL_COPY_EXECUTE_FTP` aan via een placeholder-connectie (`config/guid_allowlist.txt`); faalt tot iemand hem met de hand aan een ADF-connectie koppelt.
- Volgende stap: PR's met een test in de trial, alleen als een klant deze typen nodig heeft (`.claude/Progress.md`, P-013).
| `ADLS` | `ADLS_01` | `PL_FMD_LDZ_COPY_FROM_ADLS_01` |
| `ONELAKE` | `ONELAKE_TABLES_01`, `ONELAKE_FILES_01` | `PL_FMD_LDZ_COPY_FROM_ONELAKE_TABLES_01` / `_FILES_01` |
| `SFTP` | `SFTP_01` | `PL_FMD_LDZ_COPY_FROM_SFTP_01` |
| `FTP` | `FTP_01` | `PL_FMD_LDZ_COPY_FROM_FTP_01` |
| `ADF` | `ADF` | `PL_FMD_LDZ_COPY_FROM_ADF` |
| `NOTEBOOK` | `NOTEBOOK` | `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB` |
| `SNOWFLAKE` | `SNOWFLAKE_01` | `PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01` (vanaf `FMD_FRAMEWORK#40`, ADR-014) |
| `ODATA` | `ODATA_01` | `PL_FMD_LDZ_COPY_FROM_ODATA_01` (branch `feature/odata-bron`, ADR-021, nog niet gemerged (bijgewerkt 2026-10-29: gemerged als `FMD_FRAMEWORK#84`, `fbaf0c0`; *vastgesteld* in `git log origin/main`); *getest in eigen omgeving* 2026-10-26 op de publieke Northwind OData V4, `testplan-trial.md` T-G01 en T-G02; niet getest met AFAS) |

**Een afwijkende waarde wordt stil overgeslagen.** Registreer je een SQL-bron met `DataSource.Type = 'ASQL'` of `'SQL'`, dan vindt de COMMAND-pipeline hem wel, maar de copy-pipeline niet. De run is groen en er landt niets. De `DataSourceType`-parameter die de COMMAND-pipeline doorgeeft, gebruikt de copy-pipeline niet.

**Twee types onder één connectietype: dubbele run.** De COMMAND-pipeline loopt parallel (`isSequential: false`) over de distinct `DataSourceType`-waarden, en roept per waarde dezelfde copy-pipeline aan met dezelfde parameters. Staan er onder `SQL` bronnen met `ASQL_01` én met `ASQL_02`, dan draait de ASQL-copy twee keer over dezelfde set entiteiten. Dat is dubbele extractie en dubbel CU-verbruik, met kans op schrijfconflicten op dezelfde `TargetFileName`. Silver krijgt geen dubbele rijen zolang de merge op de primaire sleutel loopt. **Advies:** gebruik per connectietype één `DataSource.Type`, dus voor SQL alleen `ASQL_01`.

**Controlequery** (na elke registratieronde, en in de productie-acceptatiechecklist). Hij toont actieve entiteiten die geen copy-pipeline zullen vinden, en connectietypes met meer dan één type:

```sql
WITH [Toegestaan] AS (
    SELECT [ConnectionType], [DataSourceType]
    FROM (VALUES ('SQL', 'ASQL_01'), ('SQL', 'ASQL_02'), ('AZURESQLMI', 'SQLMI_01')
                ,('ORACLE', 'ORACLE_01'), ('ADLS', 'ADLS_01')
                ,('ONELAKE', 'ONELAKE_TABLES_01'), ('ONELAKE', 'ONELAKE_FILES_01')
                ,('SFTP', 'SFTP_01'), ('FTP', 'FTP_01'), ('ADF', 'ADF')
                ,('NOTEBOOK', 'NOTEBOOK'), ('SNOWFLAKE', 'SNOWFLAKE_01')
                ,('ODATA', 'ODATA_01')) AS t([ConnectionType], [DataSourceType])
)
SELECT
     v.[ConnectionType]
    ,v.[DataSourceType]
    ,COUNT(*) AS [AantalEntiteiten]
    ,CASE WHEN t.[DataSourceType] IS NULL THEN 'wordt stil overgeslagen' ELSE 'ok' END AS [Oordeel]
    ,COUNT(*) OVER (PARTITION BY v.[ConnectionType]) AS [TypesOnderConnectietype]
FROM [execution].[vw_LoadSourceToLandingzone] v
LEFT JOIN [Toegestaan] t
       ON  t.[ConnectionType] = v.[ConnectionType]
       AND t.[DataSourceType] = v.[DataSourceType]
GROUP BY
     v.[ConnectionType]
    ,v.[DataSourceType]
    ,t.[DataSourceType]
ORDER BY
     v.[ConnectionType]
    ,v.[DataSourceType]
-- verwacht: overal 'ok', en TypesOnderConnectietype = 1
```

Het registratiesjabloon in `04_implementatieplan/draaiboek_detail.md` Bijlage A controleert dezelfde lijst vooraf (`THROW 50001`).

**Status:** vastgesteld in code (filters in alle `PL_FMD_LDZ_COMMAND_*` en `PL_FMD_LDZ_COPY_FROM_*`). De dubbele run is statisch afgeleid, niet getest; zie `testplan-trial.md` T-C07 en T-C08. *Bijgewerkt 2026-10-05:* beide zijn getest in eigen omgeving (2026-09-26). T-C07 ✅: een onbekend type wordt stil overgeslagen. T-C08 ❌: de child draaide parallel twee keer en faalde op `ConcurrentWrite`; opgelost in PR #17 (`7ac0e02`, hooguit één child-run per command-pipeline).

## 2. `CustomNotebookName`: aangepaste bronnen via een custom notebook

Voor bronnen die niet via een standaard copy-activity kunnen (bijvoorbeeld een API zonder connector) heeft de Landingzone een extensiepunt: de kolom `LandingzoneEntity.CustomNotebookName` (zie `05_INTEGRATION/01_ddl-spec.md`).

**Registratie:** `Connection.Type = 'NOTEBOOK'` **en** `DataSource.Type = 'NOTEBOOK'` (zie §1). De aanroep loopt dan via:

```
PL_FMD_LDZ_COMMAND_NOTEBOOK → PL_FMD_LDZ_COPY_FROM_CUSTOM_NB → NB_FMD_PROCESSING_LANDINGZONE_MAIN
```

`NB_FMD_PROCESSING_LANDINGZONE_MAIN` roept `notebookutils.notebook.run(CustomNotebookName, 900, notebook_params)` aan. Het custom notebook krijgt onder meer `LastLoadValue`, `TargetFilePath`, `TargetFileName`, `TargetLakehouseGuid` en `WorkspaceGuid` mee. `NB_FMD_CUSTOM_NOTEBOOK_TEMPLATE` is het startpunt.

**Workspace:** het framework geeft bij `notebookutils.notebook.run` geen workspace mee. Het custom notebook moet dus in dezelfde CODE-workspace staan als het framework. De API zelf kent wel een workspace-argument, maar dat gebruikt het framework niet.

**Watermarkcontract (voor incrementeel laden):** het custom notebook ontvangt de vorige stand als `LastLoadValue`, bepaalt zelf de nieuwe stand, en geeft die terug via `notebookutils.notebook.exit` met een `LoadValue`-sleutel. `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB` schrijft die weg (`SP_UPDATE_LASTLOADVALIE`, via `exitValue).LoadValue`). Dit contract geldt alleen voor het custom-notebookpad; het standaardpad staat in `10_operations.md`.

**⚠️ De template zet de watermark op de klok.** `NB_FMD_CUSTOM_NOTEBOOK_TEMPLATE` zet `LoadValue = datetime.now()`: het tijdstip van de run, niet het maximum van de geladen data. Neem je dat over, dan worden records die met terugwerkende kracht of vertraagd in de bron verschijnen, nooit meer opgehaald. Zet `LoadValue` op het maximum van de incrementele kolom in de data die je daadwerkelijk hebt geladen, en laat hem ongewijzigd (`LastLoadValue`) als er niets is geladen.

**⚠️ Een deel van de fouten wordt geslikt.** De aanroep in `NB_FMD_PROCESSING_LANDINGZONE_MAIN`:

```python
try:
    result = notebookutils.notebook.run(CustomNotebookName, 900, notebook_params)
except Py4JJavaError as e:
    if "NotebookExecutionException" in str(e):
        fail = e
```

Een `Py4JJavaError` zonder die tekst wordt niet opnieuw gegooid. `result` blijft `None` en het notebook sluit af met `exit(None)`. De pipeline registreert daarna een landingzone-bestand dat mogelijk niet bestaat (`SP_UPDATE_PROCESS`), en faalt pas bij `SP_UPDATE_LASTLOADVALIE`, omdat `LoadValue` ontbreekt. De fout verschijnt dus een stap later en onder een andere naam. Kijk bij een fout in `SP_UPDATE_LASTLOADVALIE` daarom eerst naar de run van het custom notebook zelf.

**Timeout:** het custom notebook heeft 900 seconden (15 minuten). De aanroep van `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB` heeft 1 uur, ook al staat de laag erboven op 12 uur. Zie `10_operations.md` §Timeouts.

**Wat er niet bestaat:** een kant-en-klare referentie-implementatie voor een specifieke externe bron. Zie `13_referentie-implementatie-bitmetric.md`.

**Status:** vastgesteld in code (de aanroepketen, de `try/except`, de template, de timeouts). Het foutpad en het watermarkcontract zijn niet getest; zie `testplan-trial.md` T-D07. *Bijgewerkt 2026-10-05:* getest in eigen omgeving (T-D07, 2026-09-26, runs `4af33c3d`, `f69ff8a0`, `94d0199d`, `55f53c75`). `LoadValue` wordt opgeslagen en als `LastLoadValue` (tekst) teruggegeven. Een exception in het notebook komt als `FailedCopyActivity` in `logging.CopyActivityExecution`, en `LoadValue` blijft dan staan. Niet getest: het pad waarop een fout die geen `NotebookExecutionException` is, wordt geslikt (`10_operations.md`).

## 3. `SourceCustomSelect`: géén extensiepunt

`LandingzoneEntity.SourceCustomSelect` (nvarchar(4000)) lijkt een plek voor een eigen selectiequery, maar **het framework leest de kolom nergens**. Er wordt alleen naar geschreven: door `sp_UpsertLandingzoneEntity`, `sp_UpsertLandingzoneBronzeSilver`, `PL_TOOLING_POST_ASQL_TO_FMD` (`''`) en `NB_SETUP_FMD` (`''`). `vw_LoadSourceToLandingzone` bouwt de bronquery (`SourceDataRetrieval`) altijd als `SELECT * FROM [schema].[tabel]`, eventueel met de watermark-`WHERE`. De kolom staat niet eens in de view.

**Gevolg:** een filter, join of kolomselectie in `SourceCustomSelect` wordt genegeerd, en de **volledige tabel** wordt geladen. Dat kost volume en CU, en het is een privacyrisico als het filter bedoeld was om kolommen of rijen uit te sluiten.

**Wat wel kan:**
- een view in de bron die de selectie doet, en die view registreren als `SourceName`;
- *(toegevoegd 2026-10-20, branch `feature/loadgroup-kolommen-filter`, ADR-020, nog niet gemerged; bijgewerkt 2026-10-29: gemerged als `FMD_FRAMEWORK#77`, `5a700f9`)* **`SourceColumns` en `SourceFilter` per tabel**: een kolomlijst en een predicaat zonder `WHERE`, alleen voor `ASQL_01`, `ASQL_02` en `SNOWFLAKE_01`, in `NB_REGISTRATIE`. Dit is een eigen mechanisme; `SourceCustomSelect` blijft ongebruikt. *Getest in eigen omgeving* (2026-10-20, `testplan-trial.md` T-D16), met een beperking: kolommen weghalen bij een tabel die al in Bronze staat laat de Bronze-merge falen;
- een custom notebook (§2);
- de selectie na de landing doen, in Bronze of Silver. Dat helpt niet als de data de lakehouse helemaal niet in mag.

Laat de kolom leeg (`''`). Het gebruik van de kolom inbouwen is een kandidaat voor een fork-fix (categorie A, B-ARCH-02). Er is nog niet over besloten.

**Status:** vastgesteld in code (grep over `src/` en `setup/`, viewdefinitie, `PL_FMD_LDZ_COPY_FROM_ASQL_01` gebruikt `sqlReaderQuery = @item().SourceDataRetrieval`). Zie `testplan-trial.md` T-C09.

*Aanvulling 2026-10-20:* er lag een lokale fix (`69915b0`, branch `fix/sourcecustomselect-filter`, nooit gepusht) die `SourceCustomSelect` als FROM-doel gebruikte. Die is niet gebruikt: een volledige `SELECT` geeft ongeldige SQL, `sp_RegisterEntities` schrijft de kolom bij elke registratie leeg (`''`), en de editor kan een vrije query niet controleren. Bron: `docs/adr/020-loadgroup-kolommen-filter-per-tabel.md` op de branch.

## 4. `LoadGroup`: scheduling-groepering

`DataSource.LoadGroup` (varchar(50), fork-specifiek, niet in upstream) deelt bronnen in groepen in, bijvoorbeeld voor een apart nightly- en intraday-schema, zonder dat dit in de generieke laadlogica wordt gecodeerd. ~~`PL_FMD_SCHEDULE_NIGHTLY`/`_INTRADAY` geven de groep mee aan `PL_FMD_LOAD_ALL`~~ *(Correctie 2026-10-11, eindcontrole E-V2: de wrappers `PL_FMD_SCHEDULE_NIGHTLY`/`_INTRADAY` zijn vervallen in `FMD_FRAMEWORK#52`, ADR-017.)* De groep gaat als schedule-parameter van `PL_FMD_SCHEDULE_<short>` (in INTEGRATION CONFIG) naar `PL_FMD_ORCHESTRATION` en `PL_FMD_LOAD_ALL`, dat hem doorgeeft aan de drie lagen; de `execution`-views van Landingzone, Bronze en Silver hebben de kolom.
- *Aanvulling 2026-10-06 (`FMD_FRAMEWORK#35`):* `PL_FMD_ORCHESTRATION` heeft nu ook een parameter `LoadGroup`, en die route is de standaard. Een schema geeft de groep mee, en Gold draait daarna mee.
- Let op: een run met een groep laadt geen bronnen met `LoadGroup = ''`.

**Status:** vastgesteld.

## 5. Wat expliciet niet wordt gebruikt: Dataflow Gen2

Dataflow Gen2 wordt nergens in de FMD-implementatie gebruikt. Dat is een bewuste keuze tegen Dataflow Gen2 als ingestiemechanisme.

**Status:** vastgesteld (afwezigheid en expliciete afwijzing in de bronnen). De precieze onderbouwing (performance, beheersbaarheid of iets anders) is niet teruggevonden. **Aanname:** het is een blijvende keuze, geen tijdelijke omissie.

## Samenvatting: wanneer welk extensiepunt

| Situatie | Oplossing |
|---|---|
| Bron met een standaardconnector | Registreren met een toegestane combinatie uit §1 |
| Bron zonder standaardconnector (API, maatwerkintegratie) | `CustomNotebookName` (§2) |
| Bron met standaardconnector, maar alleen een deel van de data | Een view in de bron registreren, of een custom notebook. **Niet** `SourceCustomSelect` (§3) |
| Bronnen groeperen voor verschillende schema's | `DataSource.LoadGroup` (§4) |
| Complexe transformatie vóór de landing | **Niet** Dataflow Gen2: via `CustomNotebookName` of na de landing in de Bronze- en Silver-regels |

## Versiegeschiedenis

- v1 (2026-09-22): eerste versie.
- v2 (2026-09-25), na review 2:
  - nieuw §1: de vaste lijst `ConnectionType`/`DataSourceType`, het stil overslaan, de dubbele run en een controlequery (M-F2);
  - §2 custom notebook: registratie met `DataSource.Type = 'NOTEBOOK'`, de watermark op de klok in de template, de geslikte fouten, de timeout, en de workspace-beperking genuanceerd (M-R2, M-V1);
  - `SourceCustomSelect` is geen extensiepunt: de kolom wordt nergens gelezen (M-F1). Uit de samenvattingstabel gehaald.
- v2.1 (2026-10-07): §1 `SNOWFLAKE`/`SNOWFLAKE_01` toegevoegd aan de tabel en de controlequery (`FMD_FRAMEWORK#40`; *getest in eigen omgeving*, `testplan-trial.md` T-F03).
- v2.2 (2026-10-12): §4 de nieuwe naam `PL_FMD_ORCHESTRATION` (`FMD_FRAMEWORK#58`).
- v2.4 (2026-10-29): merge-status van #77 en #84 bijgewerkt; bevindingen `SQLMI_01`, `ORACLE_01` en `ADF` toegevoegd aan §1.
- v2.3 (2026-10-26): §1 `ODATA`/`ODATA_01` toegevoegd aan de tabel en de controlequery (branch `feature/odata-bron`, ADR-021, nog niet gemerged; *getest in eigen omgeving* op Northwind, `testplan-trial.md` T-G01 en T-G02; AFAS niet getest).
