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
- **Copy-activiteit naar een Delta-tabel per run, als enige route.** Werkt zonder inrichting bij
  de klant, maar is trager en kost Fabric-capaciteit. Daarom niet de standaard; wel een variant per
  entiteit (zie *Delta-variant*, aanvulling 2026-10-13).
- **Eén landingstabel per entiteit.** Verworpen: overschrijven verliest een levering als
  er twee runs in de wachtrij staan; toevoegen vraagt filterlogica in Bronze.
- **Tweede copy CSV → parquet met een mapping per entiteit.** Verworpen: een extra
  verplaatsing per run en een dynamische mapping.
- **Notebook met de Snowflake-connector.** Verworpen: eigen Snowflake-code in het
  framework en de limiet van 15 minuten per entiteit.
- **Copy job of Mirroring.** Verworpen: dubbel met de registratie, watermark en logging
  van het FMD; Mirroring hangt voor de kosten af van het wijzigingspatroon.
- **Directe copy naar een eigen storage-account.** Verworpen: extra kosten.

## Delta-variant (aanvulling 2026-10-13)

Een klant die geen storage integration kan of wil maken (dat vraagt `ACCOUNTADMIN` in Snowflake en een
Entra-beheerder) gebruikt de Delta-variant. Beide routes bestaan naast elkaar, **per entiteit** te kiezen
met `FileType` in de registratie:

| `FileType` | Route | Landing zone |
|---|---|---|
| `parquet` (standaard) | `COPY INTO` met storage integration (hierboven) | map met parquet in `Files/fmd/<namespace>/…` |
| `delta` | Copy-activiteit `CP_COPY_TO_LANDINGZONE`: Snowflake, via workspace-staging, naar een Delta-tabel | tabel `<namespace>_<FileName>_<jjjjmmddhhmm>` in `Tables/ldz` van `LH_DATA_LANDINGZONE` |

- **Vastgesteld in de code:** in `PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01` kiest een If (`IF_FILETYPE`, op
  `item().TargetFileType`) per entiteit tussen de Script-activiteit en de Copy-activiteit. De
  afhankelijkheden (`SP_FAIL_AUDIT_PIPELINE_CP`, `SP_UPDATE_PROCESS`) hangen aan de If; de audit-expressies
  lezen de uitvoer of de fout van de activiteit in de tak die draaide. De Copy-activiteit gebruikt
  `SnowflakeSource`/`SnowflakeTable` 1.1 (net als `LK_GET_LASTLOADDATE`): de pipeline-editor opent de V2-typen
  binnen een ForEach niet (testplan T-F05).
- **De wachtrij legt het pad vast.** Voor `delta` schrijft de pipeline `FilePath = Tables/ldz` (of `Tables` zonder
  schema's) en `FileName = <tabelnaam>` in `execution.PipelineLandingzoneEntity`. Een `FilePath` die met `Tables`
  begint, is relatief aan de lakehouse-root, anders aan `Files/`. `landing_path()` in `NB_FMD_UTILITY_FUNCTIONS`
  zet dat om, voor Bronze (die bij `SourceFileType = 'delta'` met `format('delta')` leest) en voor het onderhoud
  (ADR-015). Geen dacpac.
- **Een tabel per run**, niet één per entiteit: overschrijven verliest een levering als er twee runs in de
  wachtrij staan (zelfde reden als hierboven). **Beperking:** twee runs van dezelfde entiteit in dezelfde
  UTC-minuut geven dezelfde tabelnaam en dezelfde wachtrijsleutel. `sp_UpsertPipelineLandingzoneEntity` voegt dan
  niets toe en de tweede copy vervangt de tabel van de eerste. Is de eerste levering al verwerkt, dan bereikt de
  tweede Bronze nooit; bij een incrementele entiteit zijn dan de rijen tussen de twee watermarks kwijt. Dit
  bestond al bij `COPY INTO` (dezelfde minuutstempel in de bestandsnaam), de kans is klein; start een entiteit niet
  twee keer binnen een minuut. (*Vastgesteld in de code*, review 2026-10-13.)
- **Het formaat volgt de levering, niet de registratie.** Een entiteit die van `parquet` naar `delta` wordt
  omgezet (of terug) heeft nog oudere leveringen in de wachtrij. Bronze leidt het formaat af uit het pad
  (`landing_format()`: onder `Tables` is Delta, onder `Files/` nooit), en de volgorde van leveringen in
  `NB_FMD_PROCESSING_PARALLEL_MAIN` herkent ook een tabelnaam zonder extensie. Zonder dat faalt Bronze op een
  parquet-map (die geen Delta-tabel is) en blokkeert het de latere leveringen van die entiteit; of een
  oudere Delta-levering na een nieuwere parquet-levering wordt verwerkt.
- **Een volledige load met 0 rijen** maakt bij `delta` een lege landingtabel, en de Bronze-merge verwijdert dan alle
  rijen van die entiteit. Bij `parquet` schrijft Snowflake geen bestand, en Bronze slaat de levering over. Een
  bron die bewust leeg is, leegt Bronze dus alleen bij `delta` (*aanname* voor een volledige load; een
  incrementele load met 0 rijen is getest en laat Bronze ongemoeid).
- **Types blijven behouden** zonder mapping (`NUMBER(38,0)` naar `decimal(38,0)`, `NUMBER(12,2)` naar
  `decimal(12,2)`, `DATE` en `TIMESTAMP_NTZ` naar `timestamp`). *Getest in eigen omgeving, 2026-10-13.*
- **Kosten en duur.** Gemeten voor 1,5 miljoen rijen (`ORDERS`): 85 tot 99 s in de copy, 4 DIU, 0,27 DIU-uur
  per activiteit (*DataMovement*), tegen 5 s en geen DataMovement met `COPY INTO`. *Getest in eigen omgeving,
  2026-10-13.* Voor grote tabellen (`LINEITEM`, 6 miljoen rijen) is dat een veelvoud (*aanname*, niet gemeten).
  Gebruik `delta` dus alleen voor entiteiten die niet via de integration kunnen.
- **Beperkingen.** `FileName` en de namespace van de bron mogen bij `delta` alleen letters, cijfers en `_`
  bevatten (samen worden ze de tabelnaam `<namespace>_<FileName>_<tijdstempel>`; een spatie, punt of streepje
  laat de copy zichtbaar falen). `FileType` moet in kleine letters (`delta`) worden geregistreerd (*vastgesteld in
  de code*: de vergelijking is hoofdlettergevoelig). De Purview-lineage-extractor gaat voor `delta`-entiteiten uit
  van een map onder `Files/` die niet bestaat (alleen informatief). Een lakehouse zonder schema's (`lakehouse_schema_enabled = false`) is niet getest (*aanname*:
  de tabel komt dan direct onder `Tables/`). De accountparameters `PREVENT_UNLOAD_TO_INLINE_URL` en
  `REQUIRE_STORAGE_INTEGRATION_FOR_STAGE_OPERATION` kunnen een staged copy blokkeren; dat is niet getest en
  moet de klant bevestigen (*aanname*).
- **Inrichting.** Alleen een leesgebruiker met sleutelpaar in Snowflake en de Fabric-connectie; geen storage
  integration, geen Entra-toestemming, geen extra rol op de DATA-workspaces.

## Gevolgen

- **Snowflake gedraagt zich als elke bron.** Zelfde wachtrij, logging, watermark en
  archief; Bronze en Silver zijn ongewijzigd.
- **Eén stap, geen dataverplaatsing in Fabric.** Snowflake doet het werk (ORDERS, 1,5
  miljoen rijen: 5 s in Snowflake, tegen 49 s voor de copy via staging; runs `00939846`,
  Bronze `d3499a47`, Silver `112f96e5`, types tot in Silver behouden).
  De Fabric-kosten zijn alleen de activiteit, niet *DataMovement*.
- **Inrichting per klant** (drie stappen hierboven), met een Entra-beheerder en
  `ACCOUNTADMIN` in Snowflake. Een klant die dat niet toestaat, valt terug op de
  Delta-variant. *(Correctie 2026-10-13: de Delta-variant is nu ondersteund, per entiteit; zie hierboven.)*
- **Strenger beveiligde Snowflake-accounts** (`PREVENT_UNLOAD_TO_INLINE_URL`,
  `REQUIRE_STORAGE_INTEGRATION_FOR_STAGE_OPERATION`) werken, omdat dit al een storage
  integration gebruikt. Niet getest.
- **Tijdzone.** De watermark wordt in Snowflake berekend en vergeleken, in de tijdzone
  van het account (standaard `America/Los_Angeles`). Dat is consistent.
- **Tijdstempels** komen als `timestamp` met het label UTC; de waarde is de tijd uit
  Snowflake, niet omgerekend. Precisie boven milliseconden is niet getest.
- **Inlog.** De Fabric-connectie gebruikt een sleutelpaar zonder wachtwoordzin, met de
  private sleutel alleen in Key Vault. Een versleutelde sleutel accepteert Fabric niet:
  3DES en AES-256-CBC (het formaat van Snowflake), met de wachtwoordzin via Key Vault en
  ingetypt, gaven "Unable to connect" zonder inlogpoging in Snowflake (2026-10-07).
- **Watermarkkolom** moet `DATE` of `TIMESTAMP` zijn; een numerieke kolom faalt.

## Test

In FMD_TRIAL, trial-Dev:

1. Volledige load (`TPCH.CUSTOMER`) en incrementele load (`TPCH.ORDERS` op
   `GEWIJZIGD_OP`): map met parquet per run, Bronze en Silver met types, aantallen gelijk
   aan de bron.
2. Wijzig rijen in `ORDERS` en draai opnieuw: alleen de gewijzigde rijen komen mee.
3. `COPY_FROM_SNOWFLAKE_01` opent in de editor.

Delta-variant (aanvulling 2026-10-13), *getest in eigen omgeving*:

4. FMD_GR Dev (landing met schema's, alleen `delta`; connectie `CON_GR_SNOWFLAKE`): `TPCH.CUSTOMER` volledig en
   `TPCH.ORDERS` incrementeel op `GEWIJZIGD_OP`. Eerste run `d82cfa7e`: Silver `CUSTOMER` 150.000 en `ORDERS`
   1.500.001 rijen, gelijk aan de bron, types behouden; de audit in `logging.CopyActivityExecution` bevat de
   copy-metrics (de `if()` in de audit-expressies wordt lui geëvalueerd). Tweede run `842361de`: `ORDERS`
   kopieert 0 rijen (watermark), `CUSTOMER` volledig opnieuw; beide leveringen verwerkt.
5. Opruimen (ADR-015), FMD_GR Dev, notebook-run `559f7d3c`: oudere verwerkte landingtabellen weg, nieuwere blijven.
6. FMD_TRIAL Dev (met storage integration): `CUSTOMER` en `ORDERS` als `parquet`, `NATION` als `delta`, in één
   run `267c6701`: de parquet-leveringen komen onder `Files/`, `NATION` onder `Tables/ldz`, Silver
   `NATION` 25 rijen. Omschakelen van `CUSTOMER` naar `delta` (run `0465c3a8`) en terug naar `parquet`
   (run `ccc01d32`): oude en nieuwe leveringen worden allemaal verwerkt en de aantallen blijven kloppen.
   Onderhoud, notebook-run `8a52407e`: een verwerkte delta-tabel en een verwerkt parquet-bestand van dezelfde
   entiteit gaan allebei weg, de nieuwste levering blijft.
7. Review 2026-10-13 (onafhankelijke reviewer) vond twee fouten bij omschakelen van `FileType` met leveringen in de wachtrij;
   beide zijn hersteld en getest. FMD_TRIAL Dev: een onverwerkte parquet-levering van `CUSTOMER`, daarna omgezet
   naar `delta` en `LOAD_ALL` (run `f49c5fcb`): de parquet-levering werd als parquet verwerkt en daarna de
   delta-levering (`landing_format()`). Die run faalde op `NATION` door een tijdelijke `Login timeout expired` van de
   configdb-verbinding (los van deze wijziging); een tweede Bronze-run (`8ebc3757`) verwerkte de twee
   delta-leveringen van `NATION` in de juiste volgorde, daarna stond er niets open. Daarna is `CUSTOMER` terug
   op `parquet` gezet.
8. FMD_GR Dev, na de overstap van de Copy-activiteit naar `SnowflakeSource`/`SnowflakeTable` 1.1 (editor-compatibel),
   run `14beddb3`: Completed, Silver `CUSTOMER` 150.000 en `ORDERS` 1.500.001, `ORDERS` kopieert 0 rijen, types
   ongewijzigd. *Getest in eigen omgeving, 2026-10-13.*
9. Incrementele delta-run met echte bronwijzigingen, FMD_GR Dev, run `88fd6954` (2026-10-13): 10 rijen in `ORDERS`
   gewijzigd (`GEWIJZIGD_OP` en `O_TOTALPRICE`). De copy haalt precies 10 rijen op (landingtabel
   `sf_TPCH_ORDERS_202610131134`), de watermark schuift op, en Silver krijgt 10 nieuwe versies (1.500.011 rijen, waarvan
   1.500.001 actueel). *Getest in eigen omgeving.*
10. **Nog niet getest:** het openen van de pipeline in de editor (T-F05) met de Copy-activiteit in de If.
