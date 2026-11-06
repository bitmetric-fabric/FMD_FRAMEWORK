# Kennisbasis FMD Framework — index

Dit is de kennisbasis voor het FMD Framework bij Bitmetric, opgebouwd in fase 1 van het documentatietraject. Elk bestand behandelt één onderwerp, met per feit een broncitatie en een statuslabel:

- `vastgesteld` — expliciet zo gesteld in de brondocumentatie of code.
- `getest in eigen omgeving` — expliciet beschreven als getest/gevalideerd bij Bitmetric.
- `aanname` — afgeleid of geïnterpreteerd, niet expliciet zo in een bron gesteld.
- `open vraag` — onduidelijk, tegenstrijdig of ontbrekend; zie `open-vragen.md`.

## Bestanden

| Bestand | Onderwerp |
|---|---|
| [`architectuur.md`](./architectuur.md) | Repository-/versiestrategie (ADR-001–005), workspace-topologie en naamgeving, setup/deployment van het framework, fork-vs-upstream-principe |
| [`configdb.md`](./configdb.md) | Configuratiedatabase: schema's `integration`/`execution`/`logging`, tabellen, views, relatiediagram |
| [`registratie.md`](./registratie.md) | Stored procedures voor registratie, bulkregistratiepipeline `PL_TOOLING_POST_ASQL_TO_FMD`, bekende bugs en live-defects |
| [`bronnen-en-extensies.md`](./bronnen-en-extensies.md) | `CustomNotebookName`-mechanisme (generiek, geen RDW-specifieke implementatie), GA4, Dataflow Gen2 (niet gebruikt), overige extensiepunten |
| [`gold-en-semantic.md`](./gold-en-semantic.md) | Gold-laag (Materialized Lake Views), shortcuts naar Silver, Direct Lake en cross-workspace-referentieproblematiek |
| [`security.md`](./security.md) | Secrets-toegang, managed identity vs. Service Principal, RBAC-rollenoverzicht |
| [`cicd.md`](./cicd.md) | Promotiemechanisme (ADR-006, gesloten door ADR-012 op 2026-10-05), ADR-007/008, de Deployment-Pipelines-vs-fabric-cicd-tegenstrijdigheid en de ontleding daarvan |
| [`operations.md`](./operations.md) | Monitoring (FMD_Logging-rapport), watermark-contract, orchestratiepatroon, troubleshooting, Livy-sessies, capaciteitscontentie |
| [`kosten.md`](./kosten.md) | Capaciteitsgebruik (F2), Spark-pool-sizing, Activator-kostenincident |
| [`geleerde-lessen.md`](./geleerde-lessen.md) | Status per oorspronkelijk aangeleverde "geleerde les", plus twee nieuw gevonden lessen |
| [`open-vragen.md`](./open-vragen.md) | Alle open vragen uit bovenstaande bestanden gebundeld, met voorstel voor afhandeling |

## Belangrijkste dwarsverbanden

- De naamgevingsconventie-discrepantie (`architectuur.md`, OV-01) raakt ook de intake-checklist in fase 2.
- Het promotiemechanisme (`cicd.md`) is het onderwerp met de grootste brontegenstrijdigheid en wordt in fase 2 een expliciete beslissing met Deployment Pipelines als voorlopige default.
- Shortcuts en Deployment Pipelines (`gold-en-semantic.md`, `cicd.md`) hangen samen via de promotie van shortcuts (*correctie 2026-09-28, T-E04:* shortcuts gaan wél mee en wijzen naar Silver van het doel; eerder stond hier "niet meegenomen") — relevant voor zowel de technische documentatie als het implementatieplan.
- Het RBAC-artefact (`security.md`, OV-07) is nog niet tegen de fork-code geverifieerd en moet in fase 2/3 als input, niet als waarheid, worden behandeld.

## Status

Fase 1 is inhoudelijk afgerond. Alle 10 onderwerpbestanden plus `open-vragen.md` zijn geschreven op basis van de bronnenset uit fase 0, aangevuld met gericht broncodeonderzoek (met name voor `configdb.md`/`registratie.md`, conform de projectinstructie om stored procedures op de fork-code te baseren). Zie `voortgang.md` voor de volledige sessiegeschiedenis en `open-vragen.md` voor de punten die aan Mitchell worden voorgelegd voordat fase 2 (beslisdocument) start.
