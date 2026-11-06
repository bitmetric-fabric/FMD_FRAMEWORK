# Operations en troubleshooting

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

## Monitoring: FMD_Logging Power BI-rapport

- **Punt:** Er bestaat een Power BI-rapport ("FMD_Logging") bovenop de drie `logging`-schema-tabellen (`CopyActivityExecution`, `NotebookExecution`, `PipelineExecution`) dat gebruikt wordt voor operationeel inzicht en live diagnose van pipeline-/notebookfouten.
  **Bron:** onderzoek naar `bronnen/claude-code-transcripten/markdown/2026-09-14_fmd-logging-power-bi-rapportage.md`. **Status:** getest in eigen omgeving.
- **Punt:** Bekende datakwaliteitsissues in de onderliggende logging-data (zie ook `configdb.md`): inconsistente spelling van `LogType` (`FailPipeline` vs. `FailedPipeline`), `EntityLayer` met 4 waarden (`Bronze`, `Control`, `Landingzone`, `Silver`), en een ongenormaliseerde `TriggerType`-waarde (`"1"` naast `"Manual"` voor `PL_FMD_LOAD_ALL`). Deze issues zijn relevant voor iedereen die zelf rapportages/dashboards op de logging-tabellen bouwt.
  **Bron:** zelfde bron als hierboven. **Status:** getest in eigen omgeving.
- ~~**Punt:** Het rapport is in de praktijk gebruikt om de root cause van `DMTS_EntityNotFoundOrUnauthorized`-fouten te achterhalen.~~ **Ingetrokken (2026-09-25, review 2 steekproef 10):** chronologisch onmogelijk. Het rapport bestond pas op 14-09; de root cause was al op 04-09 gevonden, via de API en bisectie.

## Watermark-contract voor custom notebooks

- **Punt:** Een custom notebook (aangeroepen via het `CustomNotebookName`-mechanisme, zie `bronnen-en-extensies.md`) moet zich houden aan een vast contract om incrementeel laden te ondersteunen: het notebook ontvangt de vorige stand via `LastLoadValue`, berekent zelf de nieuwe stand, en geeft die terug via `notebookutils.notebook.exit` met een `LoadValue`-sleutel in de exit-payload, die het framework vervolgens wegschrijft naar `execution.LandingzoneEntityLastLoadValue`.
  **Bron:** onderzoek naar het custom-notebook-contract in de fork-code. **Status:** vastgesteld.

## Orchestratiepatroon — `PL_FMD_LOAD_ALL` / `PL_FMD_ORCHESTRATION`

- **Punt:** Er bestaat een overkoepelend orchestratiepatroon dat de onderliggende Landingzone/Bronze/Silver-pipelines in de juiste volgorde en afhankelijkheid aanroept, als alternatief voor het los aanroepen van individuele laag-pipelines. De pipeline heet in de fork **niet** `PL_MASTER_ORCHESTRATION` — die naam komt nergens in de repo voor — maar `PL_FMD_LOAD_ALL`, die op zijn beurt `PL_FMD_LOAD_LANDINGZONE` → `PL_FMD_LOAD_BRONZE` → `PL_FMD_LOAD_SILVER` aanroept, geketend op `Completed` (een volgende laag draait ook als de vorige faalt; zie `03_technische_documentatie/10_operations.md`). Daarnaast bestaat een losse wrapper-pipeline `PL_FMD_ORCHESTRATION`, die op zijn beurt `PL_FMD_LOAD_ALL` aanroept.
  **Bron:** `FMD/src/PL_FMD_LOAD_ALL.DataPipeline/`, `FMD/src/PL_FMD_ORCHESTRATION_TEMPLATE.DataPipeline/` (repo-audit 2026-09-22). **Status:** vastgesteld — naam gecorrigeerd t.o.v. de vorige versie van dit document (die abusievelijk `PL_MASTER_ORCHESTRATION` noemde); het patroon zelf (bestaan, volgorde) is bevestigd. Exacte configuratie-opties zijn niet in detail geverifieerd.

## Troubleshooting: `DMTS_EntityNotFoundOrUnauthorized`

- **Punt:** Dit is de bekende, intermitterende fout bij dynamische connection-resolutie (`@item().ConnectionGuid`) die in de projectinstructies al als platformbeperking wordt genoemd. De onderzochte bronnen bevestigen een concrete troubleshooting-procedure: via de Fabric operation-detail-API de onderliggende fout opzoeken, de "dode" (niet meer bestaande of ontoegankelijke) GUID identificeren als root cause, en het probleem oplossen door de referentie te verplaatsen naar een library-variable (Variable Library-patroon) in plaats van een hardcoded of dynamisch herberekende GUID.
  **Bron:** `bronnen/claude-code-transcripten/markdown/2026-09-14_fmd-logging-power-bi-rapportage.md` en gerelateerde troubleshooting-transcripten. **Status:** getest in eigen omgeving.
- **Punt:** Dit bevestigt en verscherpt de projectinstructie "niet blindelings retrien zonder eerst te verifiëren dat het probleem niet structureel is" — een deel van de gevallen die op het eerste gezicht intermitterend lijken, blijkt bij troubleshooting een structurele dode GUID-referentie te zijn die alleen met een Variable-Library-fix permanent opgelost wordt, niet met een retry.
  **Status:** vastgesteld (op basis van de hierboven geciteerde procedure).

## `FA_THROW_ERROR_*`: foutpropagatie per laag

- **Punt:** `FA_THROW_ERROR_LDZ`/`_BRZ`/`_SLV` in `PL_FMD_LOAD_ALL` zijn gewone Fail-activities. Ze maken de run rood nadat de fout van die laag in `logging.PipelineExecution` is gelogd (foutcodes `LandingzoneFailed`/`BronzeFailed`/`SilverFailed`). Het is een **echte** fout, geen "valse fout". Een Bronze-fout kan wel een datakwaliteitsoorzaak hebben: `NB_FMD_LOAD_LANDING_BRONZE` stopt bewust bij een ontbrekende of dubbele PK. Maar ook dan is de entiteit niet geladen.
  **Bron:** `FMD/src/PL_FMD_LOAD_ALL.DataPipeline/pipeline-content.json`; `FMD/src/NB_FMD_LOAD_LANDING_BRONZE.Notebook` (cel "Check for Duplicates"). **Status:** vastgesteld. *Correctie 2026-09-25 (review 1 F1, review 2): de eerdere tekst "bewust valse fout, niet als storing behandelen" was onjuist.*

## Livy-sessies

- **Punt:** Livy-sessies (gebruikt door notebooks) sterven na inactiviteit of lange wachttijd, resulterend in `LIVY_JOB_TIMED_OUT`. De projectinstructie "check status voor gebruik, maak zo nodig een nieuwe aan" is een directe praktijkles hieruit.
  **Bron:** het optreden staat in `bronnen/claude-code-transcripten/origineel/7e1e81a3….jsonl`; `markdown/2026-09-04_fabric-fmd.md` bevat alleen de werkinstructie (review 2 steekproef 11). **Status:** getest in eigen omgeving (het optreden van `LIVY_JOB_TIMED_OUT` is in die transcript concreet gedocumenteerd), met de kanttekening dat deze bron buiten de oorspronkelijk toegewezen bronnenlijst voor dit onderwerp viel.

## Capaciteitscontentie (herhaling projectinstructie, bevestigd)

- **Punt:** Notebook-jobs en Livy-sessies kunnen 15–30+ minuten in de wachtrij staan (`NotStarted`/`queued`) bij drukte op de gedeelde capaciteit. Dit is geen fout, maar vereist geduldig pollen (elke 60–180s); bij meer dan 20–25 minuten moet aan de gebruiker worden voorgelegd of doorwachten gewenst is.
  **Bron:** projectinstructies, bevestigd door herhaalde observatie in de onderzochte operationele transcripten. **Status:** vastgesteld.

## Trial-deployment stepbook

- **Punt:** Er bestaat een stapsgewijs "stepbook" (draaiboek) voor het uitvoeren van een trial-deployment (proefdeployment) van het framework, gebruikt om nieuwe klantimplementaties of grote wijzigingen te valideren vóór productie-uitrol.
  **Bron:** onderzoek naar trial-deployment-documentatie in de bronnen. **Status:** vastgesteld (bestaan); dit stepbook is een directe input voor `output/04_implementatieplan/draaiboek_detail.md` in fase 4.

## `RequestValidationFailed`

- **Punt:** Naast `DMTS_EntityNotFoundOrUnauthorized` is `RequestValidationFailed` een andere, gerelateerde foutcategorie met een vergelijkbare troubleshooting-aanpak (operation-detail-API raadplegen, root cause identificeren, library-variable-fix).
  **Bron:** zelfde troubleshooting-onderzoek als bij `DMTS_EntityNotFoundOrUnauthorized`. **Status:** getest in eigen omgeving.
