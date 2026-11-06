# Geleerde lessen

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

Dit bestand verzamelt de status van elke afzonderlijke "geleerde les" uit de oorspronkelijke lijst in de briefing. Voor lessen die al uitgebreid in een ander kennisbasisbestand staan, wordt hier alleen samengevat verwezen; het detail staat in het genoemde bestand.

## 1. Casing-inconsistenties

- **Punt:** Er leek een genuine bevinding te zijn gedaan (uit code-analyse van dit onderzoek zelf): in `PL_TOOLING_POST_ASQL_TO_FMD` bestaat op JSON-niveau een mismatch tussen camelCase-veldnamen die de brondataset oplevert en PascalCase-parameterverwijzingen in de ForEach-loop van de pipeline. Op basis van deze statische analyse werd dit als bug bestempeld.
  **Weerlegd (2026-09-22):** een empirische pipeline-testrun door Mitchell (job `50b62157`, `FMDTRIAL CODE (D)`) toont dat de pipeline hiermee toch correct registreert — Fabric's expressietaal evalueert `@`-strings ook zonder Expression-wrapper en dot-notation is case-insensitief. Dit is dus **geen bug**, maar wel een les op zich: statische codeanalyse van Fabric/ADF-pipelines is geen betrouwbare vervanging voor empirisch testen.
  **Bron:** eigen code-analyse van `PL_TOOLING_POST_ASQL_TO_FMD`; weerlegd door live test, zie volledige uitwerking in `registratie.md`. **Status:** getest in eigen omgeving — géén bug bevestigd.
- **Punt:** De oorspronkelijk aangeleverde claim ("casing-inconsistenties" als algemene les, mogelijk gerelateerd aan een ander scenario dan de bulk-pipeline) kon **niet** letterlijk zo worden teruggevonden binnen de 8 oorspronkelijk toegewezen bronnen voor dit onderwerp.
  **Status:** open vraag — de hierboven beschreven bulk-pipeline-casing-bug is mogelijk (een deel van) wat bedoeld werd, maar dat is niet met zekerheid vast te stellen. Aan de gebruiker voor te leggen of dit de bedoelde les is of dat er een ander, nog niet gevonden casing-probleem bestaat.

## 2. Bulk-pipeline parameterformaat

- **Punt:** Binnen de toegewezen bronnen is geen exacte bevestiging gevonden van een parameterformaat-probleem in `PL_TOOLING_POST_ASQL_TO_FMD` zelf. Wel is, buiten de oorspronkelijk toegewezen bronnenlijst, een verwant probleem aangetroffen: een **positional-parameter-bug in een ander bulk-script** (niet `PL_TOOLING_POST_ASQL_TO_FMD`) — parameters werden op positie in plaats van op naam doorgegeven, wat bij een gewijzigde volgorde tot verkeerde toewijzing leidde.
  **Bron:** aangetroffen buiten de toegewezen bronnenlijst, expliciet als zodanig gemarkeerd door het onderzoek. **Status:** open vraag voor de exacte, oorspronkelijk bedoelde claim; het gevonden verwante probleem is als apart punt vermeldenswaardig maar dekt niet exact dezelfde pipeline. (Geen nieuwe informatie hierover gevonden in de repo-audit van 2026-09-22 — `git log --all` bevat nog steeds geen commit met deze strekking.)
- **Punt:** Zie ook de casing-mismatch in `PL_TOOLING_POST_ASQL_TO_FMD` (punt 1 hierboven en `registratie.md`) — dit is het dichtstbijzijnde, wél vastgestelde parameter-gerelateerde probleem in díe specifieke pipeline.

## 3. Notebook-/branch-versiemismatch

- **Punt:** Geen exacte bevestiging van de oorspronkelijke claim ("notebook/branch version mismatch" in het algemeen) binnen de toegewezen bronnen. Wél is een **concreet, verwant geval** gevonden: een versieverschil tussen het lokale `NB_SETUP_BUSINESS_DOMAINS.ipynb` en de live main-branch-versie, dat ertoe leidde dat de eigen Bitmetric-omgeving expliciete Service Principal-credentials in Key Vault gebruikt in plaats van (uitsluitend) Workspace Identity.
  **Bron:** onderzoek naar de eigen tenant-configuratie, zie ook `security.md`. **Status:** getest in eigen omgeving (dit specifieke geval).
  **Update (repo-audit 2026-09-22):** dit is inmiddels geen tijdelijke versiemismatch meer, maar een vastgelegde platformbeperking: `FabricSql`-connecties weigeren `WorkspaceIdentity` hard (`UnsupportedCredentialType`) en accepteren alleen OAuth2/Service Principal-credentials; andere connectietypes (`FabricDataPipelines`, `Notebooks`) gebruiken wél `WorkspaceIdentity`. Zie `FMD/src/NB_UTILITIES_SETUP_FMD.Notebook/notebook-content.py` en commit `5e934ab` ("Create CON_FMD_FABRIC_SQL automatically with a service principal (#248)"). **Status:** vastgesteld (platformbeperking) — niet langer een open kwestie over versiemismatch.
- **Punt:** Daarnaast is, eveneens buiten de toegewezen bronnenlijst, een **dacpac/CI-build-mismatch** aangetroffen: een verschil tussen het lokaal gebuilde `SQL_FMD_FRAMEWORK.dacpac` en wat de CI-pipeline daadwerkelijk bouwde/deployde — thematisch verwant aan "code en gedeployde staat lopen uit de pas", maar een ander mechanisme dan een notebook/branch-mismatch.
  **Bron:** aangetroffen buiten de toegewezen bronnenlijst.
  **Update (repo-audit 2026-09-22):** root cause en fix zijn inmiddels volledig gedocumenteerd in de commit-geschiedenis: DacFx bakte het platform-regeleinde in `SysCommentsObjectAnnotation` mee, waardoor een Windows-lokale build afweek van de Linux-CI-build. Zie commits `1434d2a` → `0ac7e1a` → `b6e63c2`. **Status:** vastgesteld (opgelost). Welke van deze twee gevallen de oorspronkelijk bedoelde "les" was, blijft onbekend — zie ook `open-vragen.md` (OV-11).

## 4. Spark-pool-limieten

- **Punt:** Deze les is wél bevestigd: sizing-aanpassing in `ENV_FMD.Environment/Setting/Sparkcompute.yml` (`driver_cores` 8→4, `driver_memory` 56g→28g), inclusief de nuance dat een poging tot per-omgeving-sizing is teruggedraaid ten gunste van één gedeeld environment-item.
  **Bron:** zie volledige uitwerking in `kosten.md`. **Status:** vastgesteld — opnieuw bevestigd in de repo-audit van 2026-09-22 (commits `c2dbe90` en `827692e`).

## 5. Activator-kostenprobleem

- **Punt:** Deze les is wél bevestigd: een Activator die `PL_FINANCE_LOAD_GOLD` op elk workspace-event triggerde in plaats van op de bedoelde conditie.
  **Bron:** zie volledige uitwerking in `kosten.md`. **Status:** getest in eigen omgeving.

## 6. OAuth 90-dagen token-verval

- **Punt:** Het refresh-token van een OAuth-connectie verloopt na 90 dagen inactiviteit, zichtbaar als `AADSTS700082`.
  **Bron:** zie `security.md`. **Status:** tweedehands.

## Samenvatting

Van de zes oorspronkelijk aangeleverde "geleerde lessen"-claims zijn er inmiddels **vier gevonden** (Spark-pool-limieten; Activator-kostenprobleem en OAuth-tokenverval alleen tweedehands; en — sinds de repo-audit van 2026-09-22 — het SP-credentials-vs-Workspace-Identity-geval onder punt 3, nu een vastgelegde platformbeperking) en **twee niet exact terug te vinden** binnen de toegewezen bronnen (casing-inconsistenties, bulk-pipeline-parameterformaat). Voor deze laatste twee, en voor de vraag welk van de twee kandidaat-incidenten in punt 3 de oorspronkelijk bedoelde les was, is telkens wel een thematisch verwant fenomeen gevonden, maar niet identiek aan de oorspronkelijke formulering. Zie `open-vragen.md` voor de exacte open vragen die hieruit voortkomen.

Daarnaast is er één **nieuwe** les bovengekomen die niet in de oorspronkelijke lijst stond maar wel het karakter van een geleerde les heeft: het item-ID-verwisselingsincident tussen `VAR_GOLD_CODE_FMD` en `VAR_GOLD_SHORTCUTS_FMD` (zie `gold-en-semantic.md`) — direct relevant voor de operationele/implementatiedocumentatie in fase 3 en 4. (De aanvankelijk als nieuw gevonden casing-mismatch in `PL_TOOLING_POST_ASQL_TO_FMD`, punt 1 hierboven, bleek bij empirisch testen geen bug te zijn en is dus geen aparte les meer, wel een methodologisch leerpunt over statische vs. empirische verificatie.)
