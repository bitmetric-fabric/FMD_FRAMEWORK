# ADR-006: Promotiemechanisme Dev → Test → Prod

Status: **Proposed** (was Accepted — herzien 2026-09-15 na de triage)
Datum: 2026-09-15

## Context

Test en Prod zijn niet git-gekoppeld (ADR-005). Er zijn twee mechanismen om ze
te vullen:

- **Deployment Pipelines** — native Fabric ALM, met deployment rules voor
  omgevingsspecifieke waarden.
- **fabric-cicd** — Microsoft's open-source Python-library, aangestuurd vanuit
  Azure DevOps of GitHub Actions, deployt vanuit de repo.

Het eerdere voorbehoud bij fabric-cicd — onvolledige itemdekking — geldt niet meer.
Notebook, DataPipeline, Lakehouse, Warehouse, SemanticModel, Report, Environment,
VariableLibrary, SQLDatabase en SparkJobDefinition worden ondersteund; dat is de
volledige set die FMD gebruikt. Daarnaast bestaat `deploy_with_config`, dat deployt
vanuit een YAML-bestand met omgevingsspecifieke instellingen.

### Waarom deze ADR is teruggezet naar Proposed

De eerste versie koos fabric-cicd, met als hoofdargument dat een Deployment
Pipeline klikwerk binnen één tenant is en dus niet meereist naar de volgende klant.

De triage van 2026-09-15 laat zien dat dat argument bij ons niet opgaat. In
`NB_UTILITIES_SETUP_FMD` zitten al `ensure_deployment_pipeline`,
`assign_deployment_pipeline_stage` en `deploy_deployment_pipeline`: de Deployment
Pipelines worden idempotent aangemaakt en ingericht vanuit de setup-notebooks. Het
omgevingsmodel (stage-namen Development/Test/Production, de valueSets van de
Variable Libraries) is daar inmiddels op gebouwd.

De beslissing is daarmee niet vanzelfsprekend genoeg om `Accepted` te blijven.

## Wat er nog van het verschil overblijft

| | Deployment Pipelines | fabric-cicd |
|---|---|---|
| Inrichting herhaalbaar | ja, via bestaande helpers | ja, via workflow |
| Bron van promotie | de live Dev-workspace | een git-tag |
| Wat je promoot | een *toestand* | een *release* |
| Rollback | nee | ja, herdeploy vorige tag |
| Bewijs achteraf van wat in Prod stond | nee | ja |
| Naloopstappen in dezelfde beweging | nee | ja |
| Itemdekking | breder (alles wat DP ondersteunt) | beperkt tot de ondersteunde types |

## Voorlopige positie

- De Deployment-Pipeline-helpers in `NB_UTILITIES_SETUP_FMD` **blijven staan**. Ze
  zijn hoe dan ook nodig voor de uitwijkoptie (klant zonder CI-omgeving of met
  eigen beheer), en verwijderen zou werk weggooien dat al af is.
- Er wordt **nog geen** fabric-cicd-workflow gebouwd voordat deze ADR gesloten is.

## Wat deze beslissing sluit

Drie dingen, in deze volgorde:

1. **Een proef met fabric-cicd** op de trial-omgeving: één workspace, één tag,
   deploy + naloopstappen (`NB_CREATE_SHORTCUTS`, value set activeren, migraties).
   Meet hoeveel werk de workflow daadwerkelijk is.
2. **Een eerlijke telling van de handmatige naloopstappen** bij de huidige
   Deployment-Pipeline-route. Als dat er in de praktijk twee zijn en ze duren
   samen vijf minuten, weegt release-traceerbaarheid mogelijk niet op tegen de
   bouwkosten.
3. **ADR-007** (CI/CD in eigen GitHub-organisatie). Blijkt daar dat we geen
   CI-omgeving per klant willen beheren, dan valt fabric-cicd sowieso af.

## Gevolgen bij keuze voor fabric-cicd

- Per klant een service principal met rechten op de workspaces; fabric-cicd
  deployt in de tenant van de uitvoerende identiteit.
- Deployt **altijd alles binnen scope**, zonder naar commit-diffs te kijken.
  Selectieve deployment bestaat niet.
- `unpublish_all_orphan_items` verwijdert alles in de doelworkspace dat niet in de
  repo staat. Op Prod uitgeschakeld, tenzij expliciet anders besloten.

## Gevolgen bij keuze voor Deployment Pipelines

- Geen rollback en geen herleidbaarheid van wat er in Prod stond.
- De naloopstappen blijven handwerk, of vragen een losse trigger via de REST API.
- Het huidige omgevingsmodel (stages, valueSets) blijft ongewijzigd.

## Geldt in beide gevallen

Lakehouse-shortcuts worden door geen enkel mechanisme meegenomen. Het
`NB_CREATE_SHORTCUTS`-notebook draait na elke deployment die een Lakehouse met
shortcuts raakt, en hoort niet in de reguliere load-pipeline.
