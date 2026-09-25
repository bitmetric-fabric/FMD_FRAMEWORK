# ADR-010: Waarden per omgeving staan in value sets, niet in defaults

Status: Accepted
Datum: 2026-09-25

## Context

Pipelines en notebooks lezen een Variable Library alleen uit hun eigen workspace.
Een pipeline verwijst naar zijn library op naam (`libraryName`), zonder workspace.
Elke CODE-workspace heeft daarom een eigen exemplaar van `VAR_CONFIG_FMD` en
`VAR_GOLD_SHORTCUTS_FMD`. Een deel van de variabelen verschilt per omgeving: de
DATA-workspace, de landingzone en de Gold- en Silver-lakehouses.

De setup schreef die waarden als **default** (`variables.json`) in de library van
elke omgeving. Een test op 2026-09-25 liet zien dat een promotie via een
deployment pipeline de defaults in de doelstage overschrijft met die van de bron,
ook als de bron niet is gewijzigd. Na de eerste promotie lazen Test en Production
dus de Development-waarden.

Value sets en overrides horen bij de definitie en gaan mee met de promotie. De
**actieve** value set is item-state per workspace en blijft bij een deploy staan.

## Beslissing

Waarden die per omgeving verschillen, staan als override in
`valueSets/<Omgeving>.json` van één gedeelde definitie. De waarde van de eerste
omgeving uit `manifest.environments` is de default. Elke CODE-workspace activeert
de value set van zijn eigen omgeving.

De setup regelt dat via `set_variable_library_stage_values()`. Die functie bouwt
de definitie met `stage_value_overrides()`, schrijft hem in de library van elke
omgeving en zet de actieve value set. Waarden die in elke omgeving gelijk zijn,
blijven gewone defaults.

## Alternatieven

- **Library per omgeving, nooit meepromoveren.** Verworpen. Een deployment
  pipeline heeft geen regel om een itemtype permanent uit te sluiten. Een
  volledige deploy in de portal neemt de library gewoon mee en overschrijft de
  waarden. Dat voorkomen vraagt discipline bij elke promotie.
- **Setup opnieuw draaien na elke promotie.** Verworpen. De setup is geen
  onderdeel van de promotie, en tussen promotie en herstel wijst de omgeving naar
  de verkeerde bron.

## Gevolgen

- Een volledige promotie van een Variable Library is veilig: de doelstage houdt
  zijn eigen actieve value set, en daarmee zijn eigen waarden.
- Een nieuwe variabele die per omgeving verschilt, moet in de setup aan de
  waarden per omgeving worden toegevoegd. Anders wordt hij een default en gaat
  hij bij de promotie mee.
- Kan de setup een waarde voor een omgeving niet opzoeken, dan schrijft hij een
  lege override en valt hij niet stil terug op de waarde van Development.
- Een override die gelijk is aan de default wordt niet geschreven. Hij zou de
  waarde vastzetten en latere wijzigingen van de default blokkeren.
