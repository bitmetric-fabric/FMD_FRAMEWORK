# ADR-008: Eén repository per klant, één map per workspace

Status: Accepted
Datum: 2026-09-15

## Context

Een klantimplementatie bestaat uit meerdere workspaces: per business-domein
(INTEGRATION, FINANCE, SALES, HR) tot vier varianten (CODE, DATA, SEMANTIC,
REPORTING), elk in Dev, Test en Prod.

Fabric's git-integratie koppelt per workspace, wat de indruk wekt dat elke
workspace een eigen repository nodig heeft. Dat klopt niet: bij het koppelen geef
je repo, branch **én map** op. De 1-op-1-relatie die Fabric afdwingt geldt tussen
workspace en *branch*, niet tussen workspace en *repository*.

## Beslissing

Eén repository per klant, met een map per workspace:

```
klant-x/
├── workspaces/
│   ├── integration-code/      → WS_INTEGRATION_CODE_D
│   ├── integration-data/      → WS_INTEGRATION_DATA_D
│   ├── finance-code/          → WS_FINANCE_CODE_D
│   ├── finance-data/          → WS_FINANCE_DATA_D
│   └── finance-reporting/     → WS_FINANCE_REPORTING_D
├── metadata/migrations/
├── .deploy/                   parameterbestanden per omgeving
├── .github/workflows/
└── docs/                      ADR's, runbooks
```

Alle Dev-workspaces koppelen aan branch `dev`, elk aan hun eigen map onder
`workspaces/`.

Deploy-scripts, migraties en documentatie staan bewust **buiten** `workspaces/`:
fabric-cicd deployt alles onder de directory die het meekrijgt, en die bestanden
zijn geen Fabric-items.

## Alternatieven

- **Eén repository per workspace.** Verworpen: tot zestien repo's per klant,
  gedupliceerde secrets en workflows, ADR's op zestien plekken, en een wijziging
  die meerdere workspaces raakt wordt evenzoveel PR's.
- **Eén branch per workspace binnen één repo.** Verworpen: lost niets op dat de
  map-instelling niet al oplost, en maakt het mergen onnodig ingewikkeld.

## Gevolgen

- Map-per-workspace vertaalt één-op-één naar fabric-cicd's `repository_directory`:
  één deploy-aanroep per workspace, dezelfde structuur bij elke klant.
- Een wijziging die meerdere workspaces raakt (bijvoorbeeld een nieuwe bron die
  zowel INTEGRATION CODE als FINANCE DATA aanpast) is één PR.
- Repo secrets zijn per klant geïsoleerd, wat het gemis van environment secrets
  op GitHub Free (ADR-007) verder relativeert.
- **Feature-workspaces:** je brancht vanuit `dev` en koppelt de tijdelijke
  workspace aan die branch én dezelfde map. Werk je in één feature aan meerdere
  workspaces, dan heb je meerdere tijdelijke workspaces op dezelfde branch nodig.
  Dit hoort expliciet in het runbook.
- De mapnamen liggen vast in het klant-manifest, zodat bootstrap en deploy-workflow
  ze delen en niet uit elkaar kunnen lopen.
