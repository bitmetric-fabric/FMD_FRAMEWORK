# Gold-laag en semantisch model

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

## Principe: Gold is handmatig, niet metadata-gedreven

- **Punt:** In tegenstelling tot Landingzone/Bronze/Silver (generiek, config-driven via `integration.*`) wordt de Gold-laag per business-domein **handmatig** gebouwd via notebooks die `CREATE MATERIALIZED LAKE VIEW` (MLV) gebruiken. Er is geen `GoldLayerEntity`-tabel of vergelijkbaar in het configuratieschema — dit is een bewuste architecturale grens van het framework.
  **Bron:** projectcontext + bevestiging via de afwezigheid van een Gold-tabel in het `integration`-schema (zie `configdb.md`). **Status:** vastgesteld.
- **Punt:** De FINANCE-domein-implementatie (`NB_MLV_ADVENTUREWORKS` of vergelijkbaar genaamd notebook) is de concrete, geteste referentie-implementatie van dit patroon bij Bitmetric zelf.
  **Bron:** onderzoek naar de FINANCE-domein-notebooks in de fork. **Status:** getest in eigen omgeving.

## Shortcuts naar Silver en de Deployment-Pipeline-beperking

- **Punt:** De Gold-laag van een business-domein (bv. FINANCE DATA's `LH_GOLD_LAYER`) leest via Lakehouse-**shortcuts** de Silver-laag van INTEGRATION DATA, in plaats van data te dupliceren. Deze shortcuts worden aangemaakt/hersteld via een apart notebook, `NB_CREATE_SHORTCUTS`.
  **Bron:** projectinstructies + bevestiging in de onderzochte bronnen. **Status:** vastgesteld.
- **Punt:** Dit is de kernreden achter de bekende Fabric-platformbeperking: Lakehouse-shortcuts worden **niet** meegenomen door Deployment Pipelines (ongeacht of Deployment Pipelines of fabric-cicd als promotiemechanisme wordt gebruikt — zie `cicd.md`). Na elke deployment die een Lakehouse-met-shortcuts raakt, moet `NB_CREATE_SHORTCUTS` handmatig opnieuw gedraaid worden in de doelomgeving. Dit hoort expliciet **niet** in de reguliere load-pipeline thuis (shortcuts wijzigen zelden; load draait vaak).
  **Correctie (2026-09-28, getest in eigen omgeving, `testplan-trial.md` T-E04):** shortcuts gaan wél mee met de promotie van de DATA-workspace, en de deployment pipeline zet de Gold → Silver-shortcuts om naar Silver van het doel, ook nieuwe shortcuts (D → T, operaties `99aef0f1`/`ac49239f`). `NB_CREATE_SHORTCUTS` is na een promotie niet meer nodig; alleen als terugval, bijvoorbeeld bij de eerste uitrol van een omgeving. Microsoft Learn (2026-08-04) noemt alleen het omzetten binnen dezelfde workspace.
  **Bron:** `FMD/docs/adr/006-promotie-via-fabric-cicd.md` + Microsoft Learn-documentatie (zie projectinstructies) + bevestigd in `cicd.md`. **Status:** vastgesteld.
- **Punt:** De shortcut-doelen (welke paden/lakehouses per omgeving) worden beheerd via een Variable Library specifiek voor dit doel: `VAR_GOLD_SHORTCUTS_FMD`.
  **Bron:** onderzoek naar Variable Libraries in de FINANCE DATA-workspace. **Status:** getest in eigen omgeving.
- **Punt (praktijkincident):** Er is een incident geweest waarbij per ongeluk het verkeerde item werd bijgewerkt omdat twee gelijknamige variabele-libraries bestaan (`VAR_GOLD_CODE_FMD` vs. `VAR_GOLD_SHORTCUTS_FMD`) en het item-ID van de verkeerde library werd gebruikt bij een `updateDefinition`-call — dit overschreef stilzwijgend het verkeerde item. Vandaar de projectinstructie om item-ID's altijd te dubbelchecken vóór een updateDefinition-call.
  **Bron:** onderzoek naar variabele-library-incidenten in de operationele geschiedenis. **Status:** getest in eigen omgeving (het incident heeft daadwerkelijk plaatsgevonden).
- **Punt (praktijkincident):** Er is een incident geweest waarbij Test- en/of Prod-value-sets van een Variable Library als lege structuur bleken te bestaan zonder ooit gevuld te zijn — de opleverregel dat value sets voor Test/Prod daadwerkelijk gevuld moeten zijn (niet leeg-maar-bestaand) komt direct uit dit incident. **Update (2026-09-25):** opgelost vanaf fork-commit `81fe912`. De setup vult de value sets per omgeving en activeert per workspace de juiste; een promotie liet de oude defaults naar Development wijzen (ADR-010).
  **Bron:** zelfde onderzoek als hierboven; herhaald als expliciete waarschuwing in de projectinstructies. **Status:** getest in eigen omgeving.

## Direct Lake / semantisch model

- **Punt:** Het semantische model in de REPORTING-workspace gebruikt Direct Lake tegen de Gold-laag. Cross-workspace-referenties (van het semantisch model naar de Gold-Lakehouse) worden door Fabric intern als **letterlijke object-ID's** opgeslagen, die bij promotie naar Test/Prod **niet automatisch herbinden** aan de juiste omgevingsspecifieke Lakehouse.
  **Bron:** algemene Fabric-platformkennis + bevestiging in de onderzochte bronnen dat dit een bekend, terugkerend probleem is. **Status:** vastgesteld.
- **Punt:** Twee oplossingsroutes zijn bekend: (1) de Variable Library-patroon met `notebookutils.variableLibrary` / `libraryVariables` in pipelines — werkt voor notebook-/pipeline-gebaseerde referenties, niet voor het semantisch model zelf; (2) voor het semantisch model specifiek: handmatige Direct Lake-pointer-swap na deployment, óf een Deployment Pipeline "deployment rule" (alleen via de Fabric-portal in te stellen, geen REST API-ondersteuning op moment van onderzoek).
  **Bron:** onderzoek naar cross-workspace-referentieproblematiek in de Fabric-documentatie en de eigen implementatie-ervaring. **Status:** vastgesteld (het probleem en de twee routes); **aanname** voor de exacte stappen van de handmatige pointer-swap (niet als stap-voor-stap procedure in de bronnen aangetroffen — nader uit te werken in fase 3/4).
- **Punt:** Dit cross-workspace-referentieprobleem is één van drie bekende "live defects" die zijn vastgesteld in de eigen Bitmetric-omgeving (de andere twee betreffen andere onderdelen van de keten — zie `registratie.md` voor de volledige lijst van drie).
  **Bron:** onderzoek naar de configuratiedatabase en registratieketen. **Status:** getest in eigen omgeving.

## Samenvatting voor fase 3

Voor de technische documentatie (fase 3) is dit onderwerp een van de weinige plekken waar een concreet, stap-voor-stap "wat te doen na deployment"-recept nodig is: (1) de shortcuts in de doelomgeving controleren (*correctie 2026-09-28, T-E04:* ze gaan mee met de promotie; herdraaien van `NB_CREATE_SHORTCUTS` alleen als terugval), (2) Direct Lake-pointers in het semantisch model controleren/herstellen, (3) Variable-Library value sets voor de doelomgeving verifiëren als daadwerkelijk gevuld. Dit sluit aan bij de bekende Fabric-platformbeperkingen uit de projectinstructies en wordt in fase 4 (implementatieplan) een expliciete checklist-stap na elke deployment.
