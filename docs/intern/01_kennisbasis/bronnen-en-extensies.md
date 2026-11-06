# Bronnen en extensiepunten (Landingzone-laag)

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

## CustomNotebookName-mechanisme (aangepaste bronnen)

- **Punt:** Voor bronnen die niet via de generieke copy-activity kunnen worden opgehaald (bv. API's zonder standaard-connector), biedt de Landingzone-laag een extensiepunt via de kolom `LandingzoneEntity.CustomNotebookName`. Als `Connection.Type='NOTEBOOK'`, loopt de orchestratie via `PL_FMD_LDZ_COMMAND_NOTEBOOK` → `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB` → `NB_FMD_PROCESSING_LANDINGZONE_MAIN`, dat op zijn beurt `notebookutils.notebook.run(CustomNotebookName, …)` aanroept om het klant-/bronspecifieke notebook uit te voeren.
  **Bron:** end-to-end bevestigd met bestandscitaten door onderzoek in de fork-pipelines en -notebooks (`PL_FMD_LDZ_COMMAND_NOTEBOOK`, `PL_FMD_LDZ_COPY_FROM_CUSTOM_NB`, `NB_FMD_PROCESSING_LANDINGZONE_MAIN`). **Status:** vastgesteld.
- **Punt:** Belangrijke beperking: `notebookutils.notebook.run` kan alleen notebooks binnen **dezelfde workspace** aanroepen. Een custom notebook moet dus in dezelfde CODE-workspace staan als het framework zelf — cross-workspace aanroep van een custom notebook is niet mogelijk met dit mechanisme.
  **Bron:** zelfde onderzoek als hierboven, afgeleid uit het gedrag van `notebookutils.notebook.run`. **Status:** vastgesteld (technische eigenschap van de gebruikte API, niet expliciet als beperking gedocumenteerd maar functioneel dwingend).
  **Nuance (2026-09-25, review 2 M-V1):** de API zelf accepteert een workspace-argument; het framework geeft er alleen geen mee. In de fork klopt de conclusie dus wel.
- **Punt:** Het watermark-contract voor custom notebooks (hoe een custom notebook zijn incrementele stand doorgeeft aan het framework) wordt in `operations.md` behandeld (`LastLoadValue`/`LoadValue`/`notebookutils.notebook.exit`).

## Extensiepunt generiek beschikbaar — geen RDW-specifieke referentie-implementatie

- **Correctie (2026-09-22, bevestigd door Mitchell):** een eerdere versie van dit document claimde dat een RDW-notebook (Nederlandse voertuigregistratie) was aangetroffen, geïmplementeerd en getest via het `CustomNotebookName`-mechanisme. Dat klopt niet: Mitchell bevestigt dat er geen RDW-specifieke referentie-implementatie bestaat. "Er is gewoon een customnotebook beschikbaar. Maar niet specifiek voor RDW." Het `CustomNotebookName`-mechanisme zelf is generiek beschikbaar (zie boven) — er is alleen geen kant-en-klaar RDW-voorbeeld of -referentie.
  **Status:** vastgesteld (mechanisme generiek beschikbaar, geen brongebonden referentie-implementatie).
- **Punt:** Een vergelijkbare implementatie voor GA4 (Google Analytics 4) als bron is **niet aangetroffen** in de onderzochte bronnen — geen notebook, geen registratie, geen vermelding in chats binnen de onderzochte set.
  **Status:** beantwoord, zie `02_beslisdocument/02_beslisregister.md` B-EXT-01 — GA4 bestaat alleen als Mitchells eigen test, niet als gedocumenteerde referentie-implementatie.

## Snowflake als bron (2026-10-07)

- **Punt:** Snowflake laadt via `Connection.Type = 'SNOWFLAKE'` / `DataSource.Type = 'SNOWFLAKE_01'` en het pipelinepaar `PL_FMD_LDZ_COMMAND_SNOWFLAKE` → `PL_FMD_LDZ_COPY_FROM_SNOWFLAKE_01`. Snowflake schrijft het parquet-bestand zelf in de landing zone (`COPY INTO` via een storage integration naar OneLake); Bronze en Silver zijn ongewijzigd.
  **Bron:** `FMD_FRAMEWORK#40`, ADR-014, `testplan-trial.md` T-F03/T-F04. **Status:** getest in eigen omgeving.
- **Punt:** De Copy-activiteit is voor Snowflake niet geschikt als het doel een parquet-bestand is: via de workspace staging (CSV) wordt elke kolom tekst, ook met een mapping. Naar een lakehousetabel blijven de types wel.
  **Bron:** `testplan-trial.md` T-F02. **Status:** getest in eigen omgeving.
- **Punt:** Mirroring, een Copy job en een notebook met de Snowflake-connector zijn overwogen en niet gekozen (ADR-014, alternatieven). Mirroring blijft een optie per klant; de kosten hangen af van hoe vaak de data verandert.
  **Bron:** ADR-014; Microsoft Learn, *Snowflake mirroring FAQ*. **Status:** vastgesteld (afweging); kosten niet gemeten.

## Dataflow Gen2: expliciet niet gebruikt

- **Punt:** Dataflow Gen2 wordt **nergens** in de FMD-implementatie gebruikt — dit is geen omissie maar een expliciete architecturale keuze tegen Dataflow Gen2 (in de onderzochte bronnen wordt dit als bewuste afweging benoemd, niet als toekomstig werk).
  **Status:** vastgesteld (afwezigheid + expliciete afwijzing in de bronnen).
- **Punt:** De oorspronkelijke claim ("twee Dataflow Gen2-patronen") kon niet worden bevestigd. Vermoedelijk wordt hier een ander, niet-Dataflow-Gen2-gerelateerd onderwerp mee bedoeld: een discussie over twee routes (A/B) voor SharePoint/Excel-bronnen die in een van de chats voorkomt, maar dat gebruikt niet Dataflow Gen2 als mechanisme.
  **Status:** open vraag. Aan de gebruiker voor te leggen wat precies bedoeld werd met "twee Dataflow Gen2-patronen" — mogelijk een verwarring met de SharePoint/Excel-route-discussie.

## Overige extensiepunten (samenvattend, zie ook `configdb.md`/`registratie.md`)

- **Punt:** Naast `CustomNotebookName` is `DataSource.LoadGroup` het andere belangrijke fork-specifieke extensiepunt (scheduling-groepering), niet aanwezig in upstream.
  **Bron:** zie `configdb.md`. **Status:** vastgesteld.
- **Punt:** `LandingzoneEntity.SourceCustomSelect` (nvarchar(4000)) biedt een extensiepunt voor een aangepaste SQL-selectie bij databronnen, los van het notebook-mechanisme — voor bronnen die wél via de standaard-copy-activity lopen maar een niet-triviale selectiequery nodig hebben.
  **Bron:** kolomdefinitie in `FMD/src/Config_Database/integration/Tables/LandingzoneEntity.sql` (zie `configdb.md`). **Status:** vastgesteld (bestaan van de kolom); gebruik in de praktijk niet apart geverifieerd in dit onderzoek — aanname dat dit zo bedoeld is.
  **Correctie (2026-09-25, review 2 M-F1):** de aanname klopt niet. Het framework leest de kolom nergens; `vw_LoadSourceToLandingzone` bouwt de bronquery altijd als `SELECT * FROM [schema].[tabel]`. Zie `03_technische_documentatie/07_extension-points.md` §3.
