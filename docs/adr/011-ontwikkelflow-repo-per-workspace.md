# ADR-011: Eén repository per workspace, met generieke developer-workspaces

Status: Proposed
Datum: 2026-09-29
Vervangt: ADR-008

## Context

ADR-008 koos voor één repository per klant, met een map per workspace. Die
beslissing is genomen voordat de ontwikkelflow getest was. Op 2026-09-29 is die
flow in de klantsimulatie FMD_TRIAL van begin tot eind getest (testplan-devflow,
F0 tot en met F8): developer-workspaces, isolatie, commit, PR, merge, update van
Dev, promotie naar Test en Prod, een domeinwissel en een tweede feature.

Wat die tests lieten zien:

- Na een branch out wijzen de verwijzingen tussen workspaces naar Dev: het model
  naar de SQL-endpoint van Gold (D), het rapport naar het model in SEMANTIC (D),
  de shortcuts naar Silver (D), en de Variable Libraries naar de Dev-workspaces.
  Een notebook in een developer-workspace schrijft dan in de gedeelde Gold.
- Een value set per developer lekt via `dev` naar Test en Prod. Een domeinwissel
  faalt als de actieve value set in de nieuwe branch ontbreekt
  (`DependencyNotFound`).
- Items met dezelfde naam in verschillende domeinen (`LH_GOLD_LAYER`,
  `NB_GOLD_SHORTCUTS`, `VAR_GOLD_*`) hebben per domein een eigen logical ID.
  Koppelen via de API aan een ander domein faalt dan met
  `LogicalIdConflictDetected`.
- Een deployment pipeline zet verwijzingen naar gekoppelde items om. Een
  Direct Lake-model heeft een data source rule nodig (ADR-006).

## Beslissing

1. **Eén repository per workspace.** Per domein en type, bijvoorbeeld
   `<KLANT>_FINANCE_CODE` en `<KLANT>_FINANCE_DATA`. De Dev-workspace is in de
   root gekoppeld aan branch `dev`. Reden: maximale controle. Toegang, review en
   historie staan per workspace, en een PR raakt precies de workspace die ook
   per workspace wordt gepromoveerd.
2. **Generieke developer-workspaces per developer.** Eén set per developer, voor
   alle domeinen: `DEV_<NAAM>_<PREFIX>_{DATA,CODE,SEMANTIC,REPORTING}`, plus vaste
   `DEV_<NAAM>_<PREFIX>_INTEGRATION_{DATA,CODE}`. Ze hangen aan een feature-branch
   van het domein waaraan de developer werkt.
3. **Isolatie zonder value set per developer.**
   - Elke notebook met een default lakehouse krijgt `%%configure`, met het
     lakehouse uit de Variable Library, en daarna een vangnet. Draait de
     notebook in `DEV_*` terwijl de default lakehouse niet in `DEV_*` staat, dan
     stopt hij.
   - In de developer-workspace zet een hulpmiddel (`bind`) de **defaults** van de
     libraries op de eigen ID's, met `Default value set` actief. Hetzelfde
     hulpmiddel koppelt het model aan de eigen Gold en het rapport aan het eigen
     model.
   - Dit past bij ADR-010. Op `dev` zijn de defaults altijd de Dev-waarden, en
     Test en Prod lezen hun eigen value set. Alleen de developer-workspace wijkt
     tijdelijk af.
4. **`normalize-bindings` in elke repo met bindingen.** Bij een PR meldt de
   workflow alleen welke bindingen afwijken. Na de merge zet hij ze op `dev`
   terug naar Dev, met een eigen commit. De feature-branch blijft ongewijzigd,
   zodat de developer-workspace geïsoleerd blijft. Het script en de Dev-waarden
   komen uit `dev`.
5. **Een nieuwe feature in hetzelfde domein** zet de developer-workspaces op een
   nieuwe branch vanaf `dev`. **Een domeinwissel** gooit de domein-workspaces van
   de developer eerst leeg, en koppelt ze dan aan het nieuwe domein. Voorwaarde:
   alles is gecommit.
6. Het framework levert dit als `setup/NB_SETUP_DEVELOPER_WORKSPACES.ipynb`, met
   de modes `create`, `new_feature`, `switch_domain` en `bind`, plus een sjabloon
   voor `normalize-bindings`.

## Alternatieven

- **Eén repository per klant, met een map per workspace (ADR-008).** Een feature
  wordt dan één PR, en workflows staan op één plek. Verworpen ten gunste van de
  controle per workspace. Op GitHub zijn rechten en verplichte reviews per
  repository in te stellen, niet per map.
- **Developer-workspaces per domein** (`DEV_<NAAM>_FINANCE_*`). Er is geen
  domeinwissel nodig, en de Gold-data blijft bewaard. Verworpen: per developer
  vier workspaces per domein.
- **Een value set per developer.** Verworpen: hij lekt naar Test en Prod, en
  een domeinwissel faalt erop.
- **Normalize op de PR-branch** (herstellen vóór de merge). Verworpen: de commit
  van de bot vraagt een goedkeuring, en na een *Update from Git* krijgt de
  developer-workspace stilletjes de Dev-bindingen. Een notebook kan dan in de
  gedeelde Gold schrijven.
- **Domeinwissel met branch out in de portal.** Die behoudt de items met
  dezelfde naam, en de Gold-data. Maar hij laat de MLV's van het oude domein
  verweesd achter, en is niet te automatiseren. Blijft beschikbaar als
  handmatig alternatief.

## Gevolgen

- Een feature die meerdere workspaces raakt, geeft meerdere PR's: één per repo.
  Review en merge gebeuren per repo. Workspaces waarin alleen bindingen
  veranderden, worden wel gecommit, maar krijgen geen PR.
- Het script en de workflow van normalize staan in elke repo. Het framework
  levert het sjabloon. Een verbetering zet je per klant zelf over (ADR-002).
- De workflow moet naar `dev` kunnen pushen. Een branch protection op `dev`
  moet de bot uitzonderen.
- Werk de Dev-workspaces pas bij na de commit van de bot op `dev`.
- Een domeinwissel kost de developer de eigen Gold-data. Eén MLV-run bouwt die
  weer op, via de shortcuts naar Silver (D).
- De relatie `Base` (`git/workspaceRelations`, preview) is geen betrouwbare
  bron. Het hulpmiddel haalt de Base-workspace uit de configuratie.
- Voor fabric-cicd (ADR-006) is elke repository één `repository_directory`: één
  deploy per repository.
- Nog open, buiten deze ADR: de registratie van nieuwe bronnen in de configdb
  staat buiten git en buiten de promotie, en is per omgeving een handmatige stap.
