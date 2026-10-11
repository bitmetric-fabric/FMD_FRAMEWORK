# ADR-017: Schedules op een plan-pipeline in de CONFIG-workspace

Status: Proposed
Datum: 2026-10-11

## Context

Een schedule hoort bij de definitie van een item (`.schedules`). Staat hij op `PL_FMD_ORCHESTRATION_TEMPLATE`
of `PL_FMD_MAINTENANCE` in INTEGRATION CODE, dan neemt een promotie hem mee: ingeschakeld, met de tijden van
de bronstage en met zijn parameters. De ontvangers van de Failure notifications gaan niet mee. Getest in
FMD_SMOKE2, 2026-10-06 (promotie T → P, runs `ab159a08` en `8705689e`); het schema van `PL_FMD_MAINTENANCE`
ging op 2026-10-07 op dezelfde manier mee in de trial.

Dat geeft twee problemen:
- Test en Prod gaan draaien op de tijden van Dev, en elke promotie vraagt handwerk (ontvangers opnieuw
  instellen, tijden controleren). Een omgeving die niet moet draaien, draait toch, of mailt naar de verkeerde
  ontvangers.
- Een setup-run als update overschrijft beide pipelines in CODE. Of de schedules en ontvangers dat
  overleven, is niet getest.

De tijden en de `LoadGroup`'s verschillen per omgeving, dus ze horen niet in iets dat meepromoveert.

## Beslissing

- Per omgeving één **`PL_FMD_SCHEDULE_<short>`** in de CONFIG-workspace (`PL_FMD_SCHEDULE_D`, `_T`, `_P`), in
  de map `SchedulePipelines`. CONFIG zit in geen enkele deployment pipeline.
- De pipeline heeft de parameters `Target` (`LOAD` of `MAINTENANCE`, standaard `LOAD`) en `LoadGroup`. Een
  Switch op `Target` roept `PL_FMD_ORCHESTRATION_TEMPLATE` (met `LoadGroup`) of `PL_FMD_MAINTENANCE` aan in de
  CODE-workspace van die omgeving, en wacht op het resultaat. Elke andere waarde laat de pipeline falen
  (`UnknownTarget`). `concurrency` is 1.
- **De schedules en de Failure notifications staan op deze pipeline.** Nachtelijk, intraday en maintenance
  zijn elk een schedule op hetzelfde item, met `Target` en `LoadGroup` als schedule-parameters. De
  ontvangers stel je één keer per omgeving in.
- De setup (`create_schedule_pipeline` in `NB_UTILITIES_SETUP_FMD`, aangeroepen uit `NB_SETUP_FMD`) maakt
  de pipeline **eenmalig** aan en overschrijft hem nooit, omdat de schedule en de ontvangers eraan hangen.
- Op de pipelines in CODE staat geen schedule meer. `PL_FMD_SCHEDULE_NIGHTLY` en `PL_FMD_SCHEDULE_INTRADAY`
  zijn uit de repo gehaald; een bestaande installatie houdt ze, want de setup verwijdert niets (ADR-002).
- Dit past ADR-015 aan: het schema van `PL_FMD_MAINTENANCE` hangt voortaan aan `PL_FMD_SCHEDULE_<short>`
  met `Target = MAINTENANCE`, niet aan `PL_FMD_MAINTENANCE` zelf.

## Alternatieven

- **Schedules op de pipelines in CODE laten staan (de aanpak tot nu toe).** Verworpen: de problemen hierboven.
- **De enabled-status aan een boolean in een Variable Library koppelen** (`enabledVariableReference`).
  Verworpen: dat staat niet in Microsoft Learn, alleen in een issue van fabric-cicd (#1154), en is niet
  getest. Het lost bovendien alleen aan/uit op, niet de tijden of de ontvangers per omgeving.
- **Na elke promotie de schedules via de API zetten**, door de setup of een deployment plan (preview).
  Verworpen: handwerk of extra code per promotie, en een deployment plan kan de actieve value set niet
  wijzigen.
- **Eén plan-pipeline per omgeving én per schema** (`PL_SCHEDULE_PRD_NIGHTLY`, …). Verworpen: meer items,
  en de Failure notifications gelden per item, dus je stelt ze per schema opnieuw in.
- **Eén plan-pipeline voor alle omgevingen, met een parameter `Environment`.** Verworpen: een Dev-run en
  een Prod-run delen dan dezelfde ontvangers.

## Gevolgen

- De pipeline verwijst met letterlijke workspace- en pipeline-ID's naar CODE. Dat is hier toegestaan: het
  item wordt niet gepromoveerd en staat niet in `src/`, dus de guid-guard (ADR-009) raakt het niet. Krijgt
  een CODE-workspace of een van die pipelines een nieuw ID, dan moet je de plan-pipeline bijwerken of
  verwijderen en door de setup laten opnieuw aanmaken. Verwijderen neemt de schedules mee.
- Wie schrijfrechten heeft op CONFIG, kan ook de schedules van Prod wijzigen. Dezelfde groep kan al alles in
  de configdb.
- De schedules staan niet in git: CONFIG is niet aan git gekoppeld. Leg tijden, `LoadGroup`'s en ontvangers
  vast in het implementatieplan van de klant.
- De Invoke Pipeline die wacht, draait op de capaciteit van CONFIG; het werk zelf draait op die van CODE.
  Naar verwachting weinig, niet gemeten.
- Welke bron er geladen wordt, verandert niet: de orchestratie in elke CODE-workspace laadt de DATA-workspace
  van haar eigen omgeving, via `VAR_CONFIG_FMD`.

## Test

FMD_SMOKE3, 2026-10-11, met `PL_FMD_SCHEDULE_D` en `_P` met de hand aangemaakt (zelfde definitie als de setup):
- `Target = MAINTENANCE` in D: geslaagd (run `3ea62335`); de notebook-run staat in CODE (D).
- Ongeldige `Target`: `Failed`, errorCode `UnknownTarget` (run `152b56ed`).
- `Target = LOAD` in D en P (runs `f07c2dee`, `0908355d`): de orchestratie en Gold startten in de eigen
  CODE-workspace. Beide runs eindigden `Failed` doordat het Gold-notebook nog de sjabloon-SQL bevatte; de
  fout kwam door drie niveaus omhoog tot in de plan-pipeline.
- Een schedule met Failure notifications op `PL_FMD_SCHEDULE_P`: de mail kwam aan (Mitchell, portal).
- Promotie D → T van INTEGRATION CODE (operatie `5351536f`): in T geen plan-pipeline en op geen van de 31
  pipelines een schedule; het schedule in CONFIG bleef staan.

`create_schedule_pipeline` zelf, 2026-10-11 in een tijdelijke Python-notebook in FMD_SMOKE3_SETUP (run `91f84e4a`),
met de functies rechtstreeks uit de branch, tegen de echte `fab`-CLI, voor D, T en P:
- D en P bestonden al: overgeslagen (zelfde ID, definitie ongewijzigd). T bestond niet: aangemaakt (nieuw ID),
  in de map `SchedulePipelines`, met de beschrijving.
- De dry-run-regels voor de schedule-pipelines draaiden zonder fout.

Nog niet getest: de hele `NB_SETUP_FMD` als één run, en een volledig groene `LOAD`-run. Daarna wordt dit ADR
`Accepted`. `scripts/test_schedule_pipeline.py` test de functie ook met stubs.
