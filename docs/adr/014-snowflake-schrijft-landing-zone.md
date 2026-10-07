# ADR-014: Snowflake schrijft de landing zone zelf, via een storage integration

Status: Proposed
Datum: 2026-10-07

## Context

Snowflake wordt een bron van het FMD, via een eigen pipelinepaar
(`PL_FMD_LDZ_COMMAND_SNOWFLAKE`, `PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01`) naar het voorbeeld
van ASQL. De klant wil geen extra kosten: geen eigen storage-account en geen Mirroring.
Het uitgangspunt is dat Snowflake zich gedraagt als elke andere bron: één parquet-bestand
per run in `Files/fmd/<namespace>/…` van `LH_DATA_LANDINGZONE`, dat als archief blijft
staan, en dat `NB_FMD_LOAD_LANDING_BRONZE` ongewijzigd leest.

De Copy-activiteit leest Snowflake altijd met `COPY INTO <locatie>`. Naar een lakehouse
gaat dat via de ingebouwde workspace staging: Snowflake exporteert CSV, Fabric kopieert
door. Getest in FMD_TRIAL, 2026-10-06:

| Doel van de Copy-activiteit | Types | Run |
|---|---|---|
| Parquet-bestand (Files), met of zonder mapping, ook via *Import schemas* | alles `string` | `16aa9c95`, `084e2897`, `ff178960` |
| Lakehousetabel (Tables), zonder mapping | `decimal(38,0)`, `decimal(12,2)`, `datetime2` | `856b4a1f` |

Een parquet-bestand met types uit de Copy-activiteit kan dus niet. Een tabel kan wel,
maar dan is de landing zone geen bestand meer.

Snowflake kan zelf parquet schrijven naar OneLake, als het daar mag schrijven via een
*storage integration*. Getest in FMD_TRIAL, 2026-10-07, run `16fa4303`: `NUMBER(38,0)` →
`decimal(38,0)`, `NUMBER(12,2)` → `decimal(12,2)`, `DATE` → `date`, `TIMESTAMP_NTZ` →
`timestamp` (milliseconden, gemarkeerd als UTC; de waarde is de tijd uit Snowflake).

## Beslissing

`COPY_FROM_SNOWFLAKE_01` laat Snowflake de landing zone zelf schrijven.

- **Activiteit.** Een Script-activiteit op de Snowflake-connectie
  (`@item().ConnectionGuid`) voert per entiteit uit:

  ```sql
  COPY INTO 'azure://onelake.blob.fabric.microsoft.com/<WorkspaceGuid>/<TargetLakehouseGuid>/Files/<TargetFilePath>/<TargetFileName>/'
  FROM (<SourceDataRetrieval>)
  STORAGE_INTEGRATION = <VAR_FMD.snowflake_storage_integration>
  FILE_FORMAT = (TYPE = PARQUET) HEADER = TRUE OVERWRITE = TRUE MAX_FILE_SIZE = 268435456
  ```

  Pad, bestandsnaam en query komen uit `vw_LoadSourceToLandingzone`, zoals bij elke bron.
  De view heeft voor Snowflake een eigen tak: `"DATABASE"."SCHEMA"."TABEL"` (hoofdletter-
  gevoelig; `DataSource.Name` is de database) en de watermark-query in Snowflake-syntax.
- **Bestand is een map.** Snowflake schrijft parallel meerdere bestanden in de map
  `<TargetFileName>/`. Bronze leest die map zoals een los bestand.
- **Integratienaam** in de Variable Library: `VAR_FMD.snowflake_storage_integration`,
  standaard `FMD_ONELAKE`.
- **Watermark-lookup** in het formaat dat de editor kan openen: `SnowflakeSource` met
  dataset `SnowflakeTable`, `"version": "1.1"`. `SnowflakeV2Source`/`SnowflakeV2Table`
  draait wel, maar de editor laadt de pipeline dan niet ("SnowflakeV2Table not found").
- **Inrichting per klant**, eenmalig:
  1. In Snowflake (`ACCOUNTADMIN`): `CREATE STORAGE INTEGRATION FMD_ONELAKE` met
     `STORAGE_ALLOWED_LOCATIONS` = `Files/` van de landing zone in elke DATA-workspace
     (D, T, P), en `GRANT USAGE ON INTEGRATION` aan de rol van de servicegebruiker.
  2. In Entra: toestemming voor de Snowflake-app (`AZURE_CONSENT_URL` uit
     `DESC STORAGE INTEGRATION`).
  3. In Fabric: die app als Contributor op elke DATA-workspace.

  Het script staat in `templates/snowflake/servicegebruiker.sql`.

## Alternatieven

- **Copy-activiteit naar een parquet-bestand.** Verworpen: alle kolommen `string`, ook
  met een mapping.
- **Copy-activiteit naar een Delta-tabel per run.** Werkt zonder inrichting bij de klant,
  maar de landing zone wordt een tabel: Bronze krijgt een tweede leespad, en Snowflake
  verliest het archief of krijgt een tabel per run. Terugvaloptie voor een klant die geen
  storage integration toestaat.
- **Eén landingstabel per entiteit.** Verworpen: overschrijven verliest een levering als
  er twee runs in de wachtrij staan; toevoegen vraagt filterlogica in Bronze.
- **Tweede copy CSV → parquet met een mapping per entiteit.** Verworpen: een extra
  verplaatsing per run en een dynamische mapping.
- **Notebook met de Snowflake-connector.** Verworpen: eigen Snowflake-code in het
  framework en de limiet van 15 minuten per entiteit.
- **Copy job of Mirroring.** Verworpen: dubbel met de registratie, watermark en logging
  van het FMD; Mirroring hangt voor de kosten af van het wijzigingspatroon.
- **Directe copy naar een eigen storage-account.** Verworpen: extra kosten.

## Gevolgen

- **Snowflake gedraagt zich als elke bron.** Zelfde wachtrij, logging, watermark en
  archief; Bronze en Silver zijn ongewijzigd.
- **Eén stap, geen dataverplaatsing in Fabric.** Snowflake doet het werk (ORDERS, 1,5
  miljoen rijen: 5 s in Snowflake, tegen 49 s voor de copy via staging; runs `00939846`,
  Bronze `d3499a47`, Silver `112f96e5`, types tot in Silver behouden).
  De Fabric-kosten zijn alleen de activiteit, niet *DataMovement*.
- **Inrichting per klant** (drie stappen hierboven), met een Entra-beheerder en
  `ACCOUNTADMIN` in Snowflake. Een klant die dat niet toestaat, valt terug op de
  Delta-variant.
- **Strenger beveiligde Snowflake-accounts** (`PREVENT_UNLOAD_TO_INLINE_URL`,
  `REQUIRE_STORAGE_INTEGRATION_FOR_STAGE_OPERATION`) werken, omdat dit al een storage
  integration gebruikt. Niet getest.
- **Tijdzone.** De watermark wordt in Snowflake berekend en vergeleken, in de tijdzone
  van het account (standaard `America/Los_Angeles`). Dat is consistent.
- **Tijdstempels** komen als `timestamp` met het label UTC; de waarde is de tijd uit
  Snowflake, niet omgerekend. Precisie boven milliseconden is niet getest.
- **Inlog.** De Fabric-connectie gebruikt een sleutelpaar zonder wachtwoordzin, met de
  private sleutel in Key Vault. Een met OpenSSL 3 versleutelde sleutel plus wachtwoordzin
  gaf "Unable to connect" (2026-10-06).
- **Watermarkkolom** moet `DATE` of `TIMESTAMP` zijn; een numerieke kolom faalt.

## Test

In FMD_TRIAL, trial-Dev:

1. Volledige load (`TPCH.CUSTOMER`) en incrementele load (`TPCH.ORDERS` op
   `GEWIJZIGD_OP`): map met parquet per run, Bronze en Silver met types, aantallen gelijk
   aan de bron.
2. Wijzig rijen in `ORDERS` en draai opnieuw: alleen de gewijzigde rijen komen mee.
3. `COPY_FROM_SNOWFLAKE_01` opent in de editor.
