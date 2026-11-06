# Plan: MySQL als brontype in FMD

**Status:** geparkeerd 2026-10-13 (Mitchell). Stap 0 is nog niet uitgevoerd, er is niets gebouwd of getest.
**Keuze Mitchell:** zowel on-prem/VM (via gateway) als Azure Database for MySQL ondersteunen. Testbron nog niet bepaald; een nieuwe Azure MySQL-server aanmaken kan alleen na akkoord.

Alle paden hieronder zijn relatief aan `FMD/`.

## Context
FMD kent nu de brontypes SQL, AZURESQLMI, ORACLE, SNOWFLAKE, ADLS, ONELAKE, (S)FTP, ADF en NOTEBOOK. MySQL ontbreekt.

Bronze en Silver lezen parquet uit de landing zone en zijn bronneutraal (*vastgesteld*: geen bronspecifieke takken in de Bronze/Silver-notebooks). Alleen de stap bron → landing zone heeft MySQL-specifiek werk nodig.

Precedent: Snowflake (commit 6acb39d, PR #40) raakte dezelfde plekken (*vastgesteld*, `git show --stat`). ASQL is het beste sjabloon voor de copy-pipeline: die haalt `SourceDataRetrieval` en `LastLoadValue` kant-en-klaar uit de view. Oracle bouwt zijn query's inline en is meer werk (*vastgesteld*, `PL_FMD_LDZ_COPY_FROM_ORACLE_01`).

## Stap 0: eerst uitzoeken
*Aanname, te verifiëren in de Fabric-editor:* bereikt de generieke Fabric-connector **MySQL** ook Azure Database for MySQL (cloudconnectie, SSL)?
- **Ja**: één `Connection.Type` `MYSQL`, één DataSourceType `MYSQL_01`, één pipelinepaar. Voorkeur.
- **Nee**: een tweede tak `AZUREMYSQL` / `AZUREMYSQL_01` met `AzureMySqlSource`/`AzureMySqlTable`, naar het voorbeeld van ASQL_01/ASQL_02 binnen één copy-pipeline, plus een tweede Switch-case. De typecontrole in `sp_RegisterEntities` houdt de twee uit elkaar.

Leg ook vast welke JSON de editor schrijft voor source en dataset: type, `connectionType`, `connectionVersion`. Bij Snowflake vulde de editor bij een connectie als expressie anders zelf een verkeerd type in (`src/PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01.DataPipeline/pipeline-content.json`, regel 134-148).

## Wijzigingen

### 1. Configdb (dacpac)
- `src/Config_Database/execution/Views/vw_LoadSourceToLandingzone.sql`: een `MYSQL`-tak in `LastLoadValue` en `SourceDataRetrieval`, naast de Snowflake-tak.
  - Quoting met backticks, escape `` ` `` → ``` `` ```. `QUOTENAME` geeft `[]`, en dat accepteert MySQL niet.
  - Watermark: `DATE_FORMAT(MAX(`col`), '%Y-%m-%d %H:%i:%s.%f')`, of `NOW(3)` als de bron niet incrementeel is.
  - `SourceSchema` = MySQL-database (MySQL kent geen schemalaag).
- `src/Config_Database/integration/StoredProcedures/sp_RegisterEntities.sql` (regel 171-174): `('MYSQL', 'MYSQL_01')` toevoegen aan de typecontrole. Hetzelfde in `templates/registratie/registreer_entiteiten.sql` (regel 114).
- Dacpac opnieuw bouwen in Docker vanuit een LF-checkout (procedure in `FMD/CLAUDE.md`), `model.xml` controleren op `&#xD;`.

### 2. Pipelines (2 nieuw, 1 aangepast)
- `src/PL_FMD_LDZ_COPY_FROM_MYSQL_01.DataPipeline/`: kopie van `PL_FMD_LDZ_COPY_FROM_ASQL_01` (alleen de `_01`-tak).
  - Source `MySqlSource` met `query: @item().SourceDataRetrieval`; watermark-lookup met `@item().LastLoadValue`.
  - Dataset `MySqlTable`, connectie `@item().ConnectionGuid`, plus de `connectionType` uit stap 0.
  - Filter `DataSourceType='MYSQL_01'`. Nieuwe `.platform` met eigen logicalId.
- `src/PL_FMD_LDZ_COMMAND_MYSQL.DataPipeline/`: kopie van `PL_FMD_LDZ_COMMAND_ORACLE`, met `ConnectionType='MYSQL'`, `DatasourceType IN ('MYSQL_01')` en de InvokePipeline naar de nieuwe copy-pipeline.
- `src/PL_FMD_LOAD_LANDINGZONE.DataPipeline/pipeline-content.json`: Switch-case `"MYSQL"`, gekopieerd van de case `ORACLE` (regel 302-339).
- `config/item_deployment.json`: twee entries, naar het voorbeeld van Oracle/Snowflake (regel 103-121).
- Guid-guard draaien. De nieuwe logicalIds zijn verwijzingen binnen de repo, dus de allowlist zou niet nodig moeten zijn (*aanname*).
- Bij een setup-PR ook `PYTHONIOENCODING=utf-8 python -X utf8 scripts/test_manifest_wiring.py` draaien (staat niet in CI).

### 3. Connectie (per installatie, geen code)
- Fabric-connectie van het type MySQL, via gateway of als cloudconnectie. Wachtwoord bij voorkeur uit Key Vault.
- Registreren via `sp_UpsertConnection` met `Type = 'MYSQL'`. De `CON_FMD_*`-connecties blijven ongemoeid.

### 4. Documentatie
- `output/`: operations ("MySQL-bron toevoegen") en troubleshooting (MySQL-valkuilen), met statuslabels.
- Geen ADR nodig, het volgt het bestaande patroon. Alleen als stap 0 "nee" oplevert en we afwijken, een korte ADR.

## Bekende risico's (*aanname*, te testen)
- **Nuldatums** (`0000-00-00`) in DATE/DATETIME laten de copy falen of geven null. Mogelijke oplossing: `zeroDateTimeBehavior=convertToNull` in de connectie, of een cast in de query.
- `TINYINT(1)` komt mogelijk als boolean binnen; `BIGINT UNSIGNED` past niet in een signed long. Controleren in de Bronze-schema's.
- De MySQL-connector heeft voor on-prem een gateway nodig. Dat raakt de netwerkinrichting bij de klant, niet de code.

## Bewust overgeslagen
- `MYSQL`-case in `PL_FMD_DISCOVER_SOURCE` (SW_CONNECTION_TYPE kent alleen SQL/SNOWFLAKE). Toevoegen als discovery voor MySQL nodig is.
- Partitioned copy voor grote tabellen. Toevoegen als de doorlooptijd een probleem wordt.
- Alternatief zonder frameworkwijziging: brontype `NOTEBOOK` met een eigen extractienotebook per klant. Werkt nu al, maar is klantcode en vraagt een eigen driver en credentials. Voor een eenmalige bron kan dat volstaan.

## Verificatie (later, met akkoord voor een testbron)
1. Testbron: Azure Database for MySQL Flexible Server (Burstable B1ms), aanmaken en verwijderen alleen met akkoord; of een bestaande bron achter de trial-gateway.
2. Testtabel met DATETIME, nuldatum, TINYINT(1), BIGINT UNSIGNED, DECIMAL en een kolomnaam met backtick/quote.
3. Registreren met `registreer_entiteiten.sql`: één volledige en één incrementele entiteit.
4. `PL_FMD_LOAD_ALL` in de trial draaien via de jobs-API en controleren: parquet in de landing zone, rijen in Bronze/Silver, watermark in `execution.LandingzoneEntityLastLoadValue`, bij een tweede run alleen de delta.
5. Vastleggen in `testplan-trial.md` (met run-ID), in `output/` en als PR op FMD_FRAMEWORK (merge alleen na expliciet akkoord).
