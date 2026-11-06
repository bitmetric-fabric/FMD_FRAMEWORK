# 06_BUSINESS_DOMEINEN — Technische documentatie

**Fase:** 3 (Technische documentatie per domein)
**Datum:** 2026-09-22
**Status:** Eerste versie
**Onderwerp:** het generieke patroon waarmee elk business-domein (FINANCE, SALES, HR, of een toekomstig ander domein) op INTEGRATION wordt gebouwd.

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

## Waarom generiek, niet per domein

Aanvankelijk was het plan om dit uit te werken als `05_FINANCE/`, met SALES en HR later als kopie/aanpassing daarvan. Bij nader inzien (Mitchell, 2026-09-22) is dat niet de juiste indeling: het patroon zelf — Gold-laag via handgeschreven MLV-notebooks, shortcuts naar de gedeelde INTEGRATION Silver-laag, een Direct Lake semantisch model erbovenop, en de vier-workspace-structuur (CODE/DATA/SEMANTIC/REPORTING) — is **niet domeinspecifiek**. Alleen de daadwerkelijke Gold-tabellen/MLV's en de businesslogica erin verschillen per domein.

Dit document beschrijft daarom het generieke patroon. **FINANCE is de concrete, geteste referentie-implementatie** bij Bitmetric zelf en wordt overal als voorbeeld gebruikt; SALES en HR volgen (voor zover bekend) hetzelfde patroon, maar zijn niet apart onderzocht.

## Bronbasis — update (2026-09-22)

**Correctie op de eerste versie van dit document:** aanvankelijk werd aangenomen dat er geen lokale code-toegang was tot dit onderwerp. Bij nader zoeken bleek `FMD/src/business_domain/` (in de reeds gekloonde fork-repo) de generieke Gold/MLV/shortcuts-template wél te bevatten, plus een uitgewerkt demo-notebook (`FMD/examples/NB_MLV_DEMO_GOLD.Notebook`) en wiki-documentatie. Alle vier de bestanden hieronder zijn hierop bijgewerkt en grotendeels nu code-geverifieerd, net als `05_INTEGRATION/`.

**Belangrijke nuance die blijft staan:** het gevonden materiaal is de **generieke template/demo uit de fork zelf** (met een Wide World Importers-achtige demoset), niet per se een 1-op-1 kopie van hoe de live Bitmetric FINANCE-tenant het daadwerkelijk heeft ingevuld (welke Gold-tabellen, welke Variable-Library-waarden). Waar dat onderscheid relevant is, staat het expliciet bij het betreffende punt.

**Les uit de eerdere casing-mismatch-correctie in `05_INTEGRATION/`, nog steeds relevant:** ook code-geverifieerde "vastgesteld"-claims kunnen onvolledig zijn zonder bevestiging van de daadwerkelijke praktijk bij Bitmetric — de MLV-refresh-route is hier een voorbeeld van (twee routes technisch mogelijk, Mitchell heeft bevestigd welke daadwerkelijk gebruikt wordt).

## Inhoud

| Bestand | Onderwerp |
|---|---|
| [`01_workspace-structuur.md`](./01_workspace-structuur.md) | Het generieke CODE/DATA/SEMANTIC/REPORTING-patroon per domein × D/T/A/P-omgevingen, en de (vastgestelde) naamgevingsconventie B-ARCH-01 |
| [`02_gold-laag-mlv.md`](./02_gold-laag-mlv.md) | Waarom Gold handmatig is, wat wel en niet wordt gedeployd, de auto-wiring van `PL_FMD_LOAD_GOLD` (niet hernoemen; vanaf #58 klanteigendom), de onafgemaakte MLV-refresh-cel, de demo `NB_MLV_DEMO_GOLD` en de naamgevingsconventie |
| [`03_shortcuts-en-deployment.md`](./03_shortcuts-en-deployment.md) | Lakehouse-shortcuts naar INTEGRATION Silver, `NB_CREATE_SHORTCUTS` (code-uitwerking), de Deployment-Pipeline-platformbeperking, `VAR_GOLD_SHORTCUTS_FMD`-variabelen en twee bekende praktijkincidenten (nu met structurele code-bevestiging) |
| [`04_semantisch-model-direct-lake.md`](./04_semantisch-model-direct-lake.md) | Direct Lake tegen de Gold-laag, het cross-workspace-referentieprobleem bij promotie (waargenomen in de eigen tenant, niet in de repo) en de oplossingsroutes |

## Zie ook

- **`../13_referentie-implementatie-bitmetric.md`** — concrete Bitmetric-invulling (WWI-demodataset-herkomst, item-ID-incident, Variable-Library-waarden) die uit deze generieke documentatie is geïsoleerd.

## Openstaand vanuit Fase 1/2 dat hier relevant is

- **Workspace-naamgeving:** al vastgesteld als formeel besluit (**B-ARCH-01**, `02_beslisdocument/02_beslisregister.md`) — `[DOMEIN] [LAAG] ([OMG])`, geen OMG-suffix in Productie. Zie `01_workspace-structuur.md`.
- De drie bekende "live defects" rond cross-workspace-referenties (zie `01_kennisbasis/registratie.md`) hangen samen met dit onderwerp — zie `04_semantisch-model-direct-lake.md`.
- Het item-ID-verwisselingsincident (`VAR_GOLD_CODE_FMD` vs. `VAR_GOLD_SHORTCUTS_FMD`) is een van de nieuw gevonden "geleerde lessen" — zie `03_shortcuts-en-deployment.md`, nu met code-bevestiging dat de twee libraries structureel verschillende inhoud hebben.

## Opgelost punt

- **MLV-refresh-route:** bevestigd door Mitchell (2026-09-22) — Bitmetric gebruikt de API-route (`RefreshMaterializedLakeViews`), niet de handmatige UI-klik. Zie `02_gold-laag-mlv.md`. Meegenomen als Bitmetric-standaard voor het implementatieplan (fase 4).
