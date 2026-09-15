# ADR-003: Generieke laag vrij van klantcode

Status: Accepted
Datum: 2026-09-15

## Context

FMD's Landingzone-, Bronze- en Silver-lagen zijn generiek en config-driven. De
Gold-laag is per definitie klantwerk. In de praktijk lekt klantconfiguratie
makkelijk de generieke laag in: hardcoded workspace-ID's, lakehouse-namen,
connectie-GUID's, `abfss://`-paden.

Dit is de beslissing waar de rest aan hangt. Laat je hem los, dan is een gerichte
fix naar een bestaande klant niet moeilijk maar onmogelijk — je kunt dan niet meer
vaststellen wat generiek was. Ook de latere overstap naar een package-architectuur
(ADR-002) wordt daarmee een herbouw in plaats van een refactor.

## Beslissing

In de generieke laag staan geen klant- of omgevingsspecifieke waarden en geen
klantspecifieke vertakkingen. Alles wat per klant of omgeving verschilt gaat naar
één van drie bestemmingen:

| Bestemming | Verandert | Voorbeelden |
|---|---|---|
| **Manifest** | Nooit meer na oplevering | workspace-namen, domeinen, capaciteits-ID, naming-prefix |
| **Variable library** | Per omgeving binnen één klant | connectie-ID's, shortcut-doelen, lakehouse-verwijzingen |
| **Metadata (`integration.*`)** | Tijdens gebruik | bronnen, entiteiten, load-instellingen |

Het onderscheid manifest vs. variable library is kritisch: zet je iets in het
manifest dat eigenlijk per omgeving verschilt, dan blijkt dat pas bij de
deployment naar Prod.

## Alternatieven

- **Klantspecifieke `if`-takken in framework-notebooks.** Verworpen: elke tak is
  een permanente afwijking die niemand later nog durft te verwijderen.

## Gevolgen

- Handhaving hoort in code review. Een nieuwe hardcoded GUID in de generieke laag
  is een blokkerende bevinding.
- Bij de opschoning van de huidige framework-repo is dit het classificatiecriterium
  (zie `docs/triage.md`).
- Nieuwe configuratie vraagt telkens een bewuste keuze tussen de drie bestemmingen.
