# Besluiten n.a.v. de triage van 2026-09-15

Antwoorden op de vragen uit `docs/triage.md`. Kleinere keuzes dan een ADR waard is;
de grote zijn doorgezet naar ADR-006 en ADR-009.

| # | Onderwerp | Besluit | Waar |
|---|---|---|---|
| V1 | `repo_owner` | Naar manifest | PR 3 |
| V2 | Sparkcompute | Naar manifest, met override per omgeving | PR 3 |
| V3 | `lakehouse_schema_enabled` | Bug fixen, default `true`, naar manifest | PR 3 |
| V4 | Stages | Vier valueSets meeleveren, manifest bepaalt actieve | PR 3 |
| V5 | MLV-refresh lakehouse-ID | Lezen uit Variable Library | los |
| V6 | Celvolgorde auto-fill | Verifiëren, geen besluit | los |
| V7 | GUID-guard | Bouwen | ADR-009, PR 2 |
| V8 | Demo-notebooks | Naar `examples/`, PR naar upstream | PR 1 |

## Toelichting waar die nodig is

**V2 — Sparkcompute.** De comment in `Sparkcompute.yml` verwees naar de pool-limiet
van onze eigen Dev/Test-capacity. Dat is een omgevingswaarde in een template. De
waarden gaan naar het manifest, met een override per omgeving omdat Dev en Prod bij
een klant zelden op dezelfde capacity draaien. Herschrijf de comment naar
"conservatieve default, verhoog bij grotere capacity".

**V3 — `lakehouse_schema_enabled`.** Upstream had `"value": ""` bij type `Boolean`.
Dat is geen geldige waarde en dus een echte bug — los van de vraag wat de default
moet zijn. Fix gaat ook terug naar upstream.

**V4 — stages.** Vier value sets meeleveren kost niets, en voorkomt dat een klant
met een echte Acceptance-omgeving een aanpassing aan het framework nodig heeft.
`deploy_deployment_pipeline()` neemt de stages al uit een lijst.

**V5 — MLV-refresh.** `NB_MLV_EXAMPLE` had `lakehouse_id = "<your Gold lakehouse id>"`
als handmatige invulplek, terwijl `set_variable_library_values()` in dezelfde branch
precies dat ID al automatisch invult in `VAR_GOLD_SHORTCUTS_FMD.SourceLakehouseId`.
Het notebook leest die variabele voortaan via `notebookutils.variableLibrary`. De
waarde van een voorbeeld zit in het patroon dat het laat zien; een handmatige
placeholder leert de verkeerde gewoonte aan.

**V6 — celvolgorde.** Openstaand risico, geen besluit. De auto-fill-cel schrijft
waarden ná deployment via de API; draait daarna nog een cel met
`overwrite_variable_library=True`, dan worden ze bij een her-run leeggemaakt.
Verifiëren met één setup-run op een schone workspace voordat we dit als werkend
beschouwen.

## Wat teruggaat naar upstream

Los van onze eigen mapindeling zijn dit generieke fixes en features:

- LoadGroup-feature (SQL, views, stored procedures, 26 pipelines)
- Orchestratie-template en Gold-template
- `lakehouse_schema_enabled: ""` → geldige Boolean (V3)
- De drie hardcoded tenant-ID's uit `NB_CREATE_DIMDATE`, `NB_MLV_DEMO_GOLD` en
  `Taskflow` (V8)

Hoe kleiner onze fork-delta, hoe beter we bij een volgende klant nog kunnen zien
wat van ons is.
