# Workspace-structuur per business-domein

**Bron:** `output/01_kennisbasis/architectuur.md`, sectie "Workspace-topologie en naamgeving"; `output/02_beslisdocument/02_beslisregister.md` (B-ARCH-01)
**Status:** zie per punt

## Het patroon

Elk business-domein — INTEGRATION (verplicht, gedeelde ingestielaag) plus optioneel FINANCE/SALES/HR/andere — bestaat uit maximaal vier workspace-typen:

| Workspace-type | Functie |
|---|---|
| **CODE** | Pipelines, notebooks, Variable Library — het "uitvoerende" deel |
| **DATA** | Lakehouses (Landingzone/Bronze/Silver voor INTEGRATION; Gold voor een business-domein) |
| **SEMANTIC** | Semantische modellen (Direct Lake tegen de Gold-laag) |
| **REPORTING** | Power BI-rapporten bovenop de semantische modellen |

**Niet elk domein heeft alle vier.** INTEGRATION heeft in elk geval CODE en DATA; of een business-domein SEMANTIC/REPORTING nodig heeft hangt af van of er zelfstandige rapportage op dat domein wordt gebouwd.

Elke workspace bestaat in een **(D)**ev-, **(T)**est- en **(P)**rod-variant (en mogelijk een vierde, Acceptance/(A), afhankelijk van het manifest — zie hieronder). Elke workspace heeft een eigen Deployment Pipeline, rechtenmodel en Variable Library.

**Status:** vastgesteld (het generieke patroon zelf, zoals beschreven in projectcontext en kennisbasis).

## Naamgeving — vastgesteld (B-ARCH-01)

**Standaard:** `[DOMEIN] [LAAG] ([OMG])`, waarbij OMG = D/T (en A indien van toepassing). **In productie wordt geen OMG-suffix gebruikt** — dus `FINANCE DATA (D)` in Dev, maar gewoon `FINANCE DATA` in Prod (geen `(P)`).

**Voorbeelden:** `FINANCE DATA (D)`, `SALES SEMANTIC (D)`, `INTEGRATION CODE (D)` in Dev/Test; `FINANCE DATA`, `SALES SEMANTIC` in Prod.

Dit is al in Fase 2 als formeel besluit vastgelegd (**B-ARCH-01** in `02_beslisdocument/02_beslisregister.md`), met Mitchells expliciete akkoord (OV-01, 2026-09-21): *"De naamgeving moet als volgt zijn: [DOMEIN] [LAAG] ([OMG])... bij productie zetten we geen [OMG]-verwijzing in de naam."* Het alternatieve onderstrepingspatroon (`{DOMEIN}_{TYPE}_{OMGEVING}`, bv. `FINANCE_DATA_D`) uit het conceptdocument is daarmee **expliciet verworpen**.

**Status:** vastgesteld (formeel besluit B-ARCH-01, niet meer open).

*(Correctie: een eerdere versie van dit document — en de onderliggende kennisbasis `architectuur.md` — presenteerde dit nog als een openstaande, onopgeloste tegenstrijdigheid. Dat was gedateerd: het beslisregister had dit al in Fase 2 opgelost. `architectuur.md` is hierop bijgewerkt.)*

## Manifest en value sets

De workspace-/omgevingsstructuur wordt bepaald door het manifest (`repository`, `naming`, `environments[]` met naam/short/capacity, `config_workspace`, `spark`, `shortcuts`, `framework.lakehouse_schema_enabled`, `security`, `key_vault`). Er worden standaard vier value sets meegeleverd (Development/Test/Acceptance/Production); het manifest bepaalt welke daadwerkelijk actief zijn en in welke volgorde — dit bepaalt tevens de stage-volgorde van de Deployment Pipeline.
**Status:** vastgesteld.

## Setup-notebooks

Setup verloopt via de volgende notebooks:

1. `NB_BOOTSTRAP_FMD.ipynb` — het **enige bestand dat handmatig wordt geïmporteerd**. Plaatst de onderstaande notebooks in de workspace, met repo-configuratie al ingevuld.
2. `NB_SETUP_FMD.ipynb` — generieke framework-setup.
3. `NB_SETUP_BUSINESS_DOMAINS.ipynb` — setup van een business-domein (één generiek bestand, niet per domein een eigen notebook).
4. `NB_SETUP_DEVELOPER_WORKSPACES.ipynb` — *toegevoegd 2026-09-30 (geautomatiseerde repo-watch), commit `5d59d6a`, ADR-011.* Maakt en beheert de generieke developer-workspaces van één developer (`DEV_<NAAM>_<prefix>_{DATA,CODE,SEMANTIC,REPORTING}` en `_INTEGRATION_{DATA,CODE}`), met de modes `create`, `new_feature`, `switch_domain` en `bind`. Dit notebook is geen onderdeel van de eenmalige domein-setup hierboven, maar wordt per developer en per feature opnieuw gebruikt — zie `03_technische_documentatie/14_ontwikkelproces.md` voor de volledige werkinstructie.

**Status:** vastgesteld (repo-audit 2026-09-22; punt 4 toegevoegd 2026-09-30, geautomatiseerde repo-watch).
