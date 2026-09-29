# Sjabloon voor een repository per workspace (ADR-011)

Kopieer `.github/` naar de root van elke repo die bindingen tussen workspaces
bevat: DATA (shortcuts), CODE en INTEGRATION CODE (Variable Libraries met ID's),
SEMANTIC (model naar de SQL-endpoint van Gold) en REPORTING (rapport naar het model).
Fabric negeert `.github/`, dus het komt niet in de workspace terecht.

| Bestand | Wat |
|---|---|
| `.github/fabric-bindings.dev.json` | De Dev-waarden van de bindingen in deze repo. Neem ze over uit `dev` direct na de eerste sync. Laat de secties weg die deze repo niet heeft. |
| `.github/scripts/normalize_bindings.py` | `--report` meldt afwijkingen, `--fix` zet ze terug naar Dev, `--check` faalt bij een afwijking. Alleen de waarde wordt vervangen, zodat de opmaak van Fabric blijft staan. |
| `.github/workflows/normalize-bindings.yml` | Bij een PR naar `dev`: alleen `--report`. Na de merge (push naar `dev`): `--fix`, een commit, en `--check`. |

Waarom zo: een developer-workspace koppelt model, rapport, shortcuts en de
defaults van de libraries aan de eigen workspaces
(`setup/NB_SETUP_DEVELOPER_WORKSPACES`, mode `bind`). Die bindingen gaan mee in de
feature-branch, maar horen niet op `dev`. De feature-branch blijft ongewijzigd,
zodat de developer-workspace geïsoleerd blijft; `dev` wordt na de merge hersteld.

Voorwaarden:
- De workflow moet naar `dev` kunnen pushen. Een branch protection op `dev` moet
  de bot uitzonderen.
- Werk de Dev-workspaces pas bij na de commit *Bindingen tussen workspaces
  teruggezet naar Dev*.
- Controleer na het invullen van `fabric-bindings.dev.json` lokaal op `dev`:
  `python .github/scripts/normalize_bindings.py --check` moet *Alle bindingen
  staan op Dev* geven.
