# ADR-005: Alleen Dev is git-gekoppeld

Status: Accepted
Datum: 2026-09-15

## Context

Fabric ondersteunt git-koppeling per workspace. Je kunt elke omgeving aan een
eigen branch koppelen (dev/test/main), of alleen Dev koppelen en Test en Prod
vullen via promotie.

Deze ADR gaat over **topologie**: welke workspaces hebben een git-koppeling.
Het mechanisme dat content naar Test en Prod duwt is ADR-006.

## Beslissing

Alleen de Dev-workspace is gekoppeld aan git (branch `dev`). Test en Prod zijn
niet git-gekoppeld en worden uitsluitend gevuld via promotie.

Feature-werk: branch vanuit `dev`, tijdelijke Fabric-workspace gekoppeld aan die
branch, terug naar `dev` via PR, originele Dev-workspace synct. Workspace en
branch worden daarna opgeruimd.

## Alternatieven

- **Branch per omgeving.** Verworpen, conform Microsoft's advies bij
  geautomatiseerde promotie: je krijgt twee concurrerende waarheden over wat er
  in Test hoort te staan — de branch en de promotie — die uit elkaar gaan lopen.

## Gevolgen

- Eén bron van waarheid per omgeving.
- Geen directe git-history op wat er in Prod draait; die traceerbaarheid komt uit
  het promotiemechanisme (ADR-006).
- Een hotfix rechtstreeks in Prod is niet mogelijk via git en moet altijd de
  route via Dev volgen.
- Deze beslissing sluit branch-per-omgeving uit, maar laat zowel Deployment
  Pipelines als fabric-cicd open. Beide laten Test en Prod ongekoppeld.
