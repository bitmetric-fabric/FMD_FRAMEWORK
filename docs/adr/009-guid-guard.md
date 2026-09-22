# ADR-009: CI-guard op niet-gemapte GUID's

Status: Accepted
Datum: 2026-09-15

## Context

Het deployment-model van FMD leunt op een impliciete conventie: elke GUID in `src/`
is een placeholder die in `config/item_config.yaml` of `config/item_deployment*.json`
staat, en die `deploy_item()` → `replace_ids_and_mark_inactive()` tijdens deployment
vervangt door het echte ID in de doelworkspace.

Er is geen enkele validatie op die conventie. Staat een GUID niet in de vervang-tabel,
dan wordt hij niet vervangen en wijst het gedeployde artefact stilzwijgend naar een
vreemde tenant. Dat faalt niet — het werkt gewoon verkeerd.

De triage van 2026-09-15 vond drie gevallen die er al doorheen waren geglipt, allemaal
afkomstig uit upstream:

- `NB_CREATE_DIMDATE` — `default_lakehouse` en `default_lakehouse_workspace_id`, geen van beide gemapt
- `NB_MLV_DEMO_GOLD` — workspace-ID wél gemapt, lakehouse-ID niet
- `Taskflow/FMD_FABRIC_TASKFLOW.json` — negen GUID's, geen enkele gemapt

Dit is precies het soort fout dat je pas bij een klant ontdekt, en dan als
onverklaarbaar gedrag in plaats van als foutmelding.

## Beslissing

Een CI-guard in dezelfde vorm als upstream's `dacpac-guard.yml`: bij elke PR wordt
`src/` gescand op GUID's, en de build faalt als een GUID niet voorkomt in
`item_config.yaml` of `item_deployment*.json`.

Uitzonderingen staan in een expliciete allowlist met een reden erbij, zodat afwijken
een zichtbare handeling is in plaats van een stilzwijgende.

Dit is de geautomatiseerde handhaving van ADR-003: waar die ADR zegt dat de generieke
laag vrij blijft van omgevingswaarden, maakt deze guard dat afdwingbaar in plaats van
afhankelijk van oplettendheid tijdens review.

## Alternatieven

- **Handhaving via code review.** Verworpen als enige maatregel: de drie gevonden
  gevallen hebben jarenlang alle reviews overleefd.
- **Runtime-controle tijdens deployment.** Verworpen: dan ontdek je het pas bij de
  klant, en mogelijk pas nadat er data verkeerd is geland.

## Gevolgen

- Nieuwe items toevoegen vraagt registratie in de vervang-tabel voordat de PR kan
  mergen. Dat is de bedoeling — het is dezelfde stap die nu vergeten wordt.
- De drie bestaande gevallen moeten eerst opgelost of op de allowlist gezet worden,
  anders is de guard vanaf dag één rood. De demo-notebooks verhuizen naar `examples/`
  buiten de deployment-scope (zie triage V8); de fix gaat ook als PR naar upstream.
- De guard kent GUID's in comments of documentatie niet van echte verwijzingen.
  Vals-positieven worden opgelost via de allowlist, niet door de scan te versoepelen.
