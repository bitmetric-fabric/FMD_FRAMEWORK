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
| [004](004-metadata-migratiescripts.md) | Metadata-schema via genummerde migratiescripts | Superseded by 013 |
| [005](005-alleen-dev-git-gekoppeld.md) | Alleen Dev is git-gekoppeld | Accepted |
| [006](006-promotie-via-fabric-cicd.md) | Promotiemechanisme Dev → Test → Prod | Superseded by 012 |
| [007](007-cicd-in-eigen-github-organisatie.md) | CI/CD gehost in een eigen GitHub-organisatie | Accepted |
| [008](008-repo-en-mapstructuur.md) | Eén repository per klant, één map per workspace | Superseded by 011 |
| [009](009-guid-guard.md) | CI-guard op niet-gemapte GUID's | Accepted |
| [010](010-variable-library-waarden-per-omgeving.md) | Waarden per omgeving in value sets, niet in defaults | Accepted |
| [011](011-ontwikkelflow-repo-per-workspace.md) | Eén repository per workspace, met generieke developer-workspaces | Accepted |
| [012](012-promotie-via-deployment-pipelines.md) | Promotie via Deployment Pipelines | Accepted |
| [013](013-configdb-schema-via-dacpac.md) | Schema van de configuratiedatabase via de dacpac | Accepted |
| [014](014-snowflake-schrijft-landing-zone.md) | Snowflake schrijft de landing zone zelf, via een storage integration | Proposed |
| [015](015-opslagbeheer.md) | Opslagbeheer: landing zone opruimen op de wachtrij, wekelijks VACUUM | Accepted |

## Openstaande triggers

- **Package-architectuur heroverwegen** bij ±5 klanten met supportafspraak, of
  zodra dezelfde fix voor de derde keer handmatig is overgezet (zie ADR-002, ADR-003).
- **GitHub Free → Team** zodra er twee of meer klanten zijn, of eerder als het
  secret-beheer onoverzichtelijk wordt (zie ADR-007).
- **fabric-cicd heroverwegen** als een klant rollback of approval gates eist, of als
  de naloopstappen bij drie of meer klanten meer dan een uur per release kosten
  (zie ADR-012).
