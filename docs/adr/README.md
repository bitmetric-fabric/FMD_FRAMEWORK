# Architecture Decision Records

Beslissingen over het FMD-framework en de klantimplementaties die erop gebouwd worden.

Elke ADR legt één beslissing vast: context, keuze, verworpen alternatieven en
gevolgen. ADR's worden nooit gewijzigd. Is een beslissing achterhaald, dan schrijf
je een nieuwe die de oude vervangt (`Superseded by ADR-0XX`).

Deze map reist mee naar elke klantimplementatie. Wie bij een klant werkt kan zo
zelf beoordelen of een afwijking verdedigbaar is.

| # | Beslissing | Status |
|---|---|---|
| [001](001-template-repository.md) | Framework als template repository | Accepted |
| [002](002-geen-updates-naar-bestaande-implementaties.md) | Geen framework-updates naar bestaande implementaties | Accepted |
| [003](003-generieke-laag-vrij-van-klantcode.md) | Generieke laag vrij van klantcode | Accepted |
| [004](004-metadata-migratiescripts.md) | Metadata-schema via genummerde migratiescripts | Accepted |
| [005](005-alleen-dev-git-gekoppeld.md) | Alleen Dev is git-gekoppeld | Accepted |
| [006](006-promotie-via-fabric-cicd.md) | Promotiemechanisme Dev → Test → Prod | **Proposed** |
| [007](007-cicd-in-eigen-github-organisatie.md) | CI/CD gehost in een eigen GitHub-organisatie | Accepted |
| [008](008-repo-en-mapstructuur.md) | Eén repository per klant, één map per workspace | Accepted |
| [009](009-guid-guard.md) | CI-guard op niet-gemapte GUID's | Accepted |

## Openstaande triggers

- **Package-architectuur heroverwegen** bij ±5 klanten met supportafspraak, of
  zodra dezelfde fix voor de derde keer handmatig is overgezet (zie ADR-002, ADR-003).
- **GitHub Free → Team** zodra er twee of meer klanten zijn, of eerder als het
  secret-beheer onoverzichtelijk wordt (zie ADR-007).

## Openstaande beslissingen

- **ADR-006 — promotiemechanisme.** Sluiten na een fabric-cicd-proef op de
  trial-omgeving en een telling van de handmatige naloopstappen bij de huidige
  Deployment-Pipeline-route. Hangt samen met ADR-007.
