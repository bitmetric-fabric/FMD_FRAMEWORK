# Ontwerp: Snowflake-landing als Delta-tabel per run, naast COPY INTO met storage integration

Status: **concept ter review** (2026-10-13). Hoort bij `generale-repetitie.md` (GR-E3 vervalt; klant heeft alleen leesrechten in Snowflake) en wordt een aanvulling op ADR-014 (de "Delta-variant" gaat van terugvaloptie naar ondersteund).

## Doel
Een klant die geen storage integration kan of wil maken (dat vraagt `ACCOUNTADMIN`) kan Snowflake toch laden, zonder inrichting in Snowflake of Entra. Klanten die wel een integration hebben, houden de snelle route. De keuze is per entiteit.

## Uitgangspunten (vastgesteld in de code, 2026-10-13)
- `FileType` staat al per entiteit in `integration.LandingzoneEntity` (vrije tekst, default `parquet`) en komt als `TargetFileType` in het ForEach-item van `PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01` (`SELECT *` uit `vw_LoadSourceToLandingzone`).
- Bronze krijgt `SourceFileType`, `SourceFilePath`, `SourceFileName` uit `execution.PipelineLandingzoneEntity` en leest hard `Files/{SourceFilePath}/{SourceFileName}`.
- `NB_FMD_MAINTENANCE` ruimt verwerkte leveringen op onder `Files/{FilePath}/{FileName}`.
- Spike (run `f4516da7`): `SnowflakeV2Source` → `LakehouseTableSink` met `enableStaging: true`, dynamische tabelnaam en schema; types blijven behouden. 1,5 miljoen rijen: 85 s, 0,27 DIU-uur (*DataMovement*), tegen 5 s en geen DataMovement met COPY INTO.

## Ontwerp
1. **Keuze per entiteit:** `FileType = 'parquet'` (default) is COPY INTO, ongewijzigd. `FileType = 'delta'` is de nieuwe route. Geen nieuw brontype, geen wijziging in view of `LOAD_LANDINGZONE`.
2. **Pipeline** (`PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01`): in de ForEach vervangt een If-activiteit `IF_FILETYPE` (`@equals(item().TargetFileType,'delta')`) de directe Script-activiteit. Waar: Copy-activiteit `CP_COPY_TO_LANDINGZONE` (Snowflake → Delta-tabel). Onwaar: de bestaande Script-activiteit, ongewijzigd. De afhankelijkheden (`SP_FAIL_AUDIT_PIPELINE_CP`, `SP_UPDATE_PROCESS`) en de twee audit-expressies (`.output`, `.error`) wijzen naar de If; die geeft de uitvoer van de actieve tak door met een expressie per tak.
3. **Naamgeving van de landingtabel:** schema `ldz` (bij `lakehouse_schema_enabled = true`), tabel `<DataSourceNamespace>_<FileName>_<yyyyMMddHHmm>` (de namespace voorkomt botsingen tussen bronnen met dezelfde `FileName`). Zonder schema's: dezelfde naam direct onder `Tables/`. Alleen het eerste is getest.
4. **Wachtrij legt het pad vast.** Voor `delta` schrijft `SP_UPDATE_PROCESS` in `execution.PipelineLandingzoneEntity`: `FilePath` = `Tables/ldz` (of `Tables`), `FileName` = de tabelnaam. Een `FilePath` die met `Tables/` begint, betekent: pad vanaf de lakehouse-root, niet vanaf `Files/`. Dat is de enige regel die Bronze en het onderhoud delen. Geen dacpac, want de view en de procedures blijven gelijk.
5. **Bronze** (`NB_FMD_LOAD_LANDING_BRONZE`): het bronpad wordt `…/{SourceLakehouse}/{SourceFilePath}/{SourceFileName}` als `SourceFilePath` met `Tables/` begint, anders `…/Files/…` zoals nu. Bij `SourceFileType = 'delta'` leest hij met `spark.read.format('delta')`. De `convert_small_numeric_columns_to_int`-stap (voor parquet) wordt overgeslagen. De rest (hash, merge, Silver) blijft gelijk.
6. **Opruimen** (`NB_FMD_MAINTENANCE`, ADR-015): zelfde regel; bij een `FilePath` die met `Tables/` begint, verwijdert hij de tabelmap onder `Tables/` in plaats van onder `Files/`. Zelfde bewaartermijn en dezelfde regel dat een onverwerkte levering blijft staan.
7. **Registratie:** `FileType = 'delta'` in het lijstsjabloon (templates/registratie en `sp_RegisterEntities` accepteren dat al). Het sjabloon krijgt een opmerking.
8. **Documentatie:** ADR-014 (variant, keuzecriterium, kosten), draaiboek en intake-checklist (vraag: kan de klant een storage integration maken?), troubleshooting, log.

## Wat dit niet doet
- Geen automatische keuze: de ontwikkelaar kiest `FileType` per entiteit.
- Geen mapping van types: dat gebeurt door de copy (decimal-precisie blijft, `DATE` wordt `timestamp`).
- Geen `overwrite` van een landingtabel: elke run maakt een eigen tabel, zodat twee runs in de wachtrij elkaar niet overschrijven (reden uit ADR-014).

## Risico's en beperkingen
- **Kosten:** *DataMovement* in Fabric-capaciteit (0,27 DIU-uur per 1,5 miljoen rijen, 85 s). Grote tabellen (LINEITEM, 6 miljoen) ±4× (*aanname*). Alleen voor entiteiten die niet via de integration kunnen.
- **Twee codepaden** om te onderhouden en te testen.
- **Strenge accounts:** `PREVENT_UNLOAD_TO_INLINE_URL` en `REQUIRE_STORAGE_INTEGRATION_FOR_STAGE_OPERATION` kunnen een staged copy blokkeren. Niet getest; de klant moet dit bevestigen.
- **Workspace-staging** moet in de DATA-workspace beschikbaar zijn (in de spike werkte het zonder `stagingSettings`).
- **Onbekend:** Spark-leespad, het volledige pad via `PL_FMD_LDZ_COMMAND_SNOWFLAKE`, opruimen, en een lakehouse zonder schema's.

## Testplan (trial, vóór de PR)
1. Pipeline + Bronze + onderhoud aanpassen in een worktree; PR als concept.
2. In FMD_GR Dev (landing is schema-enabled): twee entiteiten, `CUSTOMER` volledig en `ORDERS` incrementeel, beide met `FileType = 'delta'`; `NATION` met `parquet` is niet mogelijk zonder integration, dus de mix (`parquet`+`delta`) test ik in de trial, waar de integration bestaat.
3. Aantallen en types tot in Silver; tweede run incrementeel (alleen delta); onderhoud met bewaartermijn 1 dag: landingtabellen weg, onverwerkte blijft.
4. Regressie: een `parquet`-entiteit in de trial laadt nog zoals voor de wijziging.
5. Dacpac-guard en guid-guard groen. Mergen alleen na akkoord.
