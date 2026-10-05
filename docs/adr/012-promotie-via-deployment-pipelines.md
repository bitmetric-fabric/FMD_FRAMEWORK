# ADR-012: Promotie via Deployment Pipelines

Status: Accepted
Datum: 2026-10-05
Vervangt: ADR-006 (Proposed)

## Context

ADR-006 liet de keuze tussen Deployment Pipelines en fabric-cicd open tot een
fabric-cicd-proef en een telling van de naloopstappen. Sindsdien is de
Deployment-Pipeline-route in de klantsimulatie (FMD_TRIAL) van Dev tot en met Prod
gebruikt: hertest, rookproef, demoklant en ontwikkelflow (2026-09-25 t/m 09-29).

Wat dat opleverde:

- De setup richt de pipelines en stages idempotent in, en koppelt de stages pas na
  de items (`NB_SETUP_FMD`).
- Waarden per omgeving staan in value sets met een actieve value set per workspace
  (ADR-010). Een promotie laat die staan.
- Shortcuts gaan wél mee met een promotie van DATA en wijzen daarna naar Silver van
  het doel (D → T → P getest). De bewering in ADR-006 ("Lakehouse-shortcuts worden
  door geen enkel mechanisme meegenomen") klopt niet.
- De naloopstappen per promotie zijn: registratie in de configdb voor die omgeving,
  een load, de MLV-refresh, en bij een nieuw Direct Lake-model één keer een data
  source rule in de portal. De rule werkt daarna bij elke promotie vanzelf.

## Beslissing

Deployment Pipelines is het promotiemechanisme voor klantimplementaties. Er wordt
geen fabric-cicd-workflow gebouwd. fabric-cicd blijft een later spoor, met de
triggers hieronder.

## Alternatieven

- **fabric-cicd nu.** Verworpen voor nu: het voegt release-traceerbaarheid en
  rollback toe, maar vraagt per klant een CI-omgeving en een service principal met
  rechten op alle workspaces. Het huidige omgevingsmodel is op stages gebouwd.
  De proef uit ADR-006 is niet gedaan.

## Gevolgen

- Er is geen rollback naar een eerdere versie. Herstel is een fix in Dev en opnieuw
  promoveren. Een promotie promoot de live toestand van de bronstage, dus promoveer
  alleen wat in Dev getest is.
- Er is geen bewijs achteraf van wat er in Prod stond, behalve de deploygeschiedenis
  van de pipeline en git op `dev`.
- De naloopstappen hierboven staan in het draaiboek (fase 7) en blijven handwerk.
- ADR-007 noemt fabric-cicd als promotiemechanisme ("Promotie verloopt via
  fabric-cicd (ADR-006)"). Lees dat als: de CI in de eigen GitHub-organisatie draait
  de guards en de PR-workflows, niet de promotie.
- Waar ADR-011 naar ADR-006 verwijst voor de data source rule van een Direct
  Lake-model, geldt nu deze ADR.

## Heroverwegen als

- een klant rollback, release-tags of formele approval gates eist;
- er drie of meer klanten zijn met elk eigen Test en Prod, en de handmatige
  naloopstappen samen meer dan een uur per release kosten;
- Microsoft de Deployment Pipelines voor een van de gebruikte itemtypes laat vallen.
