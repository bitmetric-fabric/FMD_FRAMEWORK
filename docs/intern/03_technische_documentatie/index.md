# Technische documentatie FMD — Index

**Fase:** 3
**Datum:** 2026-09-22
**Status:** Uitgebreid — kernstructuur compleet, zie "Openstaand" onderaan

Dit is de generieke, klant-onafhankelijke technische documentatie voor een FMD-implementatie. Placeholders (`<KLANT>`, `<DOMEIN>`, `<WORKSPACE_GUID>`, `<KV_NAAM>`) worden gebruikt waar iets per klantimplementatie verschilt; de concrete Bitmetric-invulling staat apart in `13_referentie-implementatie-bitmetric.md`.

## Inhoud

| # | Document | Onderwerp |
|---|---|---|
| 00 | [`00_architectuur-overzicht.md`](./00_architectuur-overzicht.md) | Concepten, lagenoverzicht (Mermaid), orchestratie op hoog niveau (Mermaid) |
| 05 | [`05_INTEGRATION/`](./05_INTEGRATION/) | Configuratiedatabase (DDL + ER-diagram), bronregistratie, operationele aandachtspunten van de generieke ingestielaag |
| 06 | [`06_BUSINESS_DOMEINEN/`](./06_BUSINESS_DOMEINEN/) | Workspace-structuur, Gold-laag/MLV's, shortcuts, semantisch model per business-domein |
| 07 | [`07_extension-points.md`](./07_extension-points.md) | Extensiepunten (`CustomNotebookName`, `LoadGroup`), de vaste lijst `ConnectionType`/`DataSourceType`, en waarom `SourceCustomSelect` geen extensiepunt is |
| 08 | [`08_security-en-secrets.md`](./08_security-en-secrets.md) | Waar secrets worden opgehaald (Key Vault), de credentials van de Fabric-connecties, RBAC |
| 09 | [`09_cicd-en-deployment.md`](./09_cicd-en-deployment.md) | Deployment Pipelines vs. fabric-cicd, repo-hosting, schemawijzigingen aan de configdb (dacpac, ADR-013; ADR-004 vervangen), GUID-guard, Variable Libraries |
| 10 | [`10_operations.md`](./10_operations.md) | Monitoring, orchestratiepatroon, watermark (twee paden) en resetten, herstarten, timeouts, capaciteitscontentie |
| 11 | [`11_troubleshooting.md`](./11_troubleshooting.md) | Bekende foutpatronen met diagnose/oplossing + beslisboom (Mermaid) |
| 12 | [`12_kosten-en-capaciteit.md`](./12_kosten-en-capaciteit.md) | Spark-pool-sizing, capaciteitsplanning, kostenwaarschuwingen |
| 13 | [`13_referentie-implementatie-bitmetric.md`](./13_referentie-implementatie-bitmetric.md) | **Bijlage:** concrete Bitmetric-invulling (commits, job-ID's, omgevingsnamen, incidenten) |
| 15 | [`15_opslagbeheer.md`](./15_opslagbeheer.md) | **Voorstel (2026-10-07):** groei van de landing zone en van oude Delta-versies, wat Fabric biedt, opruimen op basis van de wachtrij en wekelijks `VACUUM` |

## Nummering

Genummerd 00/05/06/07–13 (geen 01-04) omdat 05_INTEGRATION en 06_BUSINESS_DOMEINEN als eerste zijn opgeleverd, direct volgend op de fase-indeling uit het projectbrondocument; de tussenliggende nummers zijn bewust niet met andere inhoud opgevuld.

## Openstaand

- **Fase 2 (`02_beslisdocument/03_architectuurvarianten.md`):** nog geen Mermaid-diagrammen voor de architectuurvarianten/beslisboom — apart traject, niet in deze Fase 3-ronde meegenomen.
- **Fase 4A (`plan_hoogover.md`):** hoog-over implementatieplan met vaste fasen/rollen/Gantt — nog niet gebouwd.
- **Fase 4B:** `draaiboek_detail.md` is nu nog trial-deployment-scoped, niet het volledige per-fase draaiboek met RACI/risicoregister/productie-acceptatiechecklist dat de brief vraagt.
- **Fase 5:** consistentiecheck/traceability-matrix nog niet gestart.
