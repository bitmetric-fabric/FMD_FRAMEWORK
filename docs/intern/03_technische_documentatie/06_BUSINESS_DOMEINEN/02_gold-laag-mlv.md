# Gold-laag: principe en MLV-notebookpatroon

**Bron:** `FMD/src/business_domain/` (`NB_LOAD_GOLD`, `NB_MLV_EXAMPLE`, `NB_CREATE_SHORTCUTS`, `PL_FMD_LOAD_GOLD`), `FMD/examples/` (`NB_MLV_DEMO_GOLD`, `NB_CREATE_DIMDATE`, `README.md`), `NB_UTILITIES_SETUP_FMD` (`wire_domain_into_orchestration`), `FMD/wiki/NB_MLV_EXAMPLE.md`; aanvullend `output/01_kennisbasis/gold-en-semantic.md`
**Datum:** 2026-09-25
**Status:** Versie 2: gecorrigeerd na review 2 (N-R1, N-R3, N-V1), zie versiegeschiedenis onderaan

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

## Principe: Gold is handmatig, niet metadata-gedreven

Landingzone, Bronze en Silver zijn generiek en config-driven via `integration.*` (zie `05_INTEGRATION/`). De Gold-laag wordt **per business-domein met de hand gebouwd**, met notebooks die `CREATE MATERIALIZED LAKE VIEW` (MLV) gebruiken. Er is **geen** `GoldLayerEntity`-tabel of iets vergelijkbaars in de configuratiedatabase.

**Status:** vastgesteld (geen Gold-tabel in `integration`, zie `05_INTEGRATION/01_ddl-spec.md`; de template-notebooks zijn leeg).

## Wat de fork levert

**Gedeployd** (`src/business_domain/`, via `config/item_deployment_code_business_domain.json`):

| Item | Rol |
|---|---|
| `NB_LOAD_GOLD.Notebook` | Leeg notebook voor domeinspecifieke Gold-laadlogica vóór de MLV's |
| `NB_MLV_EXAMPLE.Notebook` | Template voor de `CREATE MATERIALIZED LAKE VIEW`-statements, plus een cel die de MLV-refresh start (zie hieronder) |
| `NB_CREATE_SHORTCUTS.Notebook` | Maakt de shortcuts naar Silver aan, zie `03_shortcuts-en-deployment.md` |
| `PL_FMD_LOAD_GOLD.DataPipeline` | Draait `NB_LOAD_GOLD` en daarna, bij `Succeeded`, `NB_MLV_EXAMPLE`. Vanaf `FMD_FRAMEWORK#58` klanteigendom, zie hieronder |
| `VAR_GOLD_CODE_FMD.VariableLibrary` | Eén variabele: `key_vault_uri_name` (zie `../08_security-en-secrets.md`) |
| `VAR_GOLD_SHORTCUTS_FMD.VariableLibrary` | Parameters voor de shortcuts, zie `03_shortcuts-en-deployment.md` |

*Aanvulling 2026-10-12 (`FMD_FRAMEWORK#47` `5ec7b3c` en `#58` `1f12148`; draft van de repo-watch van 2026-10-08 verwerkt en bijgewerkt voor #58; vastgesteld in `NB_UTILITIES_SETUP_FMD`, `CUSTOMER_OWNED_ITEMS`):*
- `NB_LOAD_GOLD`, `NB_MLV_EXAMPLE` en `NB_CREATE_SHORTCUTS` (sinds #47), en `PL_FMD_LOAD_GOLD` (sinds #58), zijn klanteigendom. De setup maakt ze één keer aan in D, T en P, en overschrijft ze bij een volgende setup-run niet.
- Gevolg: een fix in deze templates bereikt een bestaande installatie niet vanzelf. Neem hem met de hand over in Dev, en promoveer.
- Zie `../10_operations.md`, *De setup opnieuw draaien als update*.

**Niet gedeployd** (`examples/`): `NB_MLV_DEMO_GOLD.Notebook` (een complete MLV-implementatie op een demoset) en `NB_CREATE_DIMDATE.Notebook` (bouwt een datumdimensie). Volgens `examples/README.md` dragen deze notebooks lakehouse- en workspace-koppelingen mee van de tenant waarin ze zijn gebouwd. Kopieer wat je nodig hebt naar `src/` en koppel de default lakehouse opnieuw.

**Status:** vastgesteld (`git ls-files`, `examples/README.md`). *Correctie 2026-09-25: `NB_CREATE_DIMDATE` staat niet in `src/business_domain/` en is geen leeg bestand; het staat in `examples/`.*

## De Gold-pipeline en de orchestratie

`NB_SETUP_BUSINESS_DOMAINS` hangt de Gold-pipeline van elk domein aan `PL_FMD_ORCHESTRATION` (`wire_domain_into_orchestration`). Die functie zoekt de pipeline **op naam**: `PL_FMD_LOAD_GOLD` in de CODE-workspace van het domein. De activity krijgt een letterlijke `workspaceId` en `pipelineId`, en hangt aan `PL_FMD_LOAD_ALL` met de voorwaarde `Succeeded` (zie `../00_architectuur-overzicht.md`).

De pipeline verwijst naar zijn notebooks met `notebookId` (logical ID). Daarom:

- **Hernoem de pipeline niet.** Een hernoemde pipeline vindt de setup niet meer. Hij valt dan uit de orchestratie; de setup print alleen "Could not resolve IDs … skip".
- ~~**Kopieer de notebooks niet naar nieuwe namen**, of pas de pipeline aan. De pipeline blijft anders de originele `NB_LOAD_GOLD` en `NB_MLV_EXAMPLE` draaien.~~ *Correctie 2026-10-12 (`FMD_FRAMEWORK#58`, vastgesteld in `NB_UTILITIES_SETUP_FMD`, `CUSTOMER_OWNED_ITEMS`):* **Voeg extra notebooks als activity toe aan `PL_FMD_LOAD_GOLD`, in Dev, en promoveer.** De pipeline is klanteigendom: de setup maakt hem één keer per stage (D/T/P) aan en overschrijft hem daarna niet. Promoveer de notebooks samen met of vóór de pipeline, anders faalt de promotie met *Missing Dependencies* (`testplan-trial.md` T-A07b).

De eenvoudigste route: vul `NB_LOAD_GOLD` en `NB_MLV_EXAMPLE` zelf, in de CODE-workspace van het domein. Die staan al per domein in een eigen workspace, dus domeinspecifieke namen zijn niet nodig. ~~Wil je toch andere namen, pas dan ook de pipeline en de aanroep van `wire_domain_into_orchestration` (parameter `gold_pipeline_name`) aan, in de fork.~~ *Correctie 2026-10-12 (`FMD_FRAMEWORK#58`):* andere of extra notebooks zet je in `PL_FMD_LOAD_GOLD` in Dev, niet in de fork. Alleen een andere naam voor de pipeline zelf vraagt een aanpassing in de fork (`gold_pipeline_name`, standaard `PL_FMD_LOAD_GOLD`).

Gevolg (*vastgesteld*, zelfde bron): een latere framework-wijziging aan de template van de Gold-pipeline bereikt een bestaande installatie niet. Neem zo'n wijziging met de hand over in Dev, en promoveer.

**Status:** vastgesteld in code. *Correctie 2026-09-25 (review 2 N-R3): de vorige versie adviseerde de notebooks en de pipeline te kopiëren of te hernoemen.*

## MLV-refresh: de API-route

Een `CREATE OR REPLACE MATERIALIZED LAKE VIEW` ververst de view **niet**. Er zijn twee routes:

1. Met de hand in de Fabric-UI: in de Gold-lakehouse, sectie "Materialized lake views", op **Refresh** klikken. Dat is de hoofdroute in de wiki (`NB_MLV_EXAMPLE.md`).
2. **Via de API.** De tweede cel van `NB_MLV_EXAMPLE` doet een `POST` naar `…/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/jobs/RefreshMaterializedLakeViews/instances`, met een token uit `notebookutils.credentials.getToken("https://api.fabric.microsoft.com")`.

**Bevestigd (Mitchell, 2026-09-22): Bitmetric gebruikt de API-route.** Die zit al in het pad: `PL_FMD_LOAD_GOLD` draait `NB_MLV_EXAMPLE`.

**Vanaf PR #21 (2026-09-26) is de cel af.** Hij haalt `SourceWorkspaceId`/`SourceLakehouseId` uit `VAR_GOLD_SHORTCUTS_FMD`, faalt als de POST geen 202 geeft, en pollt de job tot die klaar is. Getest in Dev en, na een promotie, in Test (`testplan-trial.md` T-E02). Zet wel de default-lakehouse van het notebook op `LH_GOLD_LAYER`, zodat de `CREATE`-statements daar terechtkomen. Een promotie zet die binding automatisch om naar Gold van de doelomgeving.

In forks van vóór PR #21 is de cel niet af:

```python
lakehouse_id = "<your Gold lakehouse id>"
...
response = requests.post(url, headers=headers)
print(response.status_code)
print(response.headers.get("Location"))
```

- **Het lakehouse-ID is een placeholder.** Met de placeholder faalt de POST. Het notebook, en dus de pipeline, blijft groen.
- **De workspace is verkeerd.** `workspace_id = currentWorkspaceId` is de CODE-workspace; de Gold-lakehouse staat in de DATA-workspace. Ook met een echt lakehouse-ID start er dan geen refresh (hertest T-E02, run `e4dd3a02`).
- **Er is geen foutafhandeling.** Er is geen `raise_for_status()`, dus een fout wordt alleen geprint.
- **Er wordt niet gewacht.** De refresh is een job; de cel print de `Location` van die job, maar volgt hem niet. Ook als de refresh faalt, is de pipeline al klaar.

**Wat je per domein aanpast:**
- Haal het lakehouse-ID uit `VAR_GOLD_SHORTCUTS_FMD` (`SourceLakehouseId`, de Gold-lakehouse; de setup vult hem per omgeving). Een ingevuld ID werkt alleen in één omgeving.
- Laat de cel falen als de POST niet `202` geeft.
- Poll de `Location`-URL tot de job klaar is, en laat de cel falen als de job niet `Completed` is.

Controleer de refresh tot die tijd via de **status van de job-instance**, niet via de pipeline (zie de productie-acceptatiechecklist in `04_implementatieplan/draaiboek_detail.md`).

**Status:** getest in eigen omgeving (2026-09-26, `testplan-trial.md` T-E02); opgelost in PR #21. *Correctie 2026-09-25 (review 2 N-R1): de vorige versie noemde de route "automatiseerbaar als extra stap". Hij zit al in het pad, maar kan stil falen.*

## Developer-workspace-isolatie: `%%configure` en het vangnet (ADR-011)

*Nieuw, 2026-09-30 (geautomatiseerde repo-watch), commit `5d59d6a` (#27).*

Sinds ADR-011 kan `NB_MLV_EXAMPLE` ook in een developer-workspace (`DEV_*`) draaien, niet alleen in Dev/Test/Prod. Daarvoor zijn er, **vóór** de bestaande refresh-cel, twee nieuwe cellen als eerste codecellen van het notebook:

1. **`%%configure`** zet de default lakehouse van de notebook expliciet op `LH_GOLD_LAYER`, met het lakehouse-ID en workspace-ID uit `VAR_GOLD_SHORTCUTS_FMD` (`SourceLakehouseId`/`SourceWorkspaceId`). Daardoor schrijft de notebook in elke omgeving — én in een developer-workspace na `bind` (zie `14_ontwikkelproces.md`) — in de Gold van díe workspace, in plaats van in een hardcoded of impliciete default lakehouse. `%%configure` werkt alleen als allereerste cel van een sessie; deze cel moet dus vóór de refresh-cel blijven staan.
2. **Het vangnet** (een `%%pyspark`-cel) leest `notebookutils.runtime.context` en vergelijkt de huidige workspace met de workspace van de default lakehouse. Begint de huidige workspace met `DEV_` terwijl de Gold-workspace dat niet doet, dan gooit de cel een `RuntimeError` ("zou schrijven in de Gold van …") in plaats van de MLV's te bouwen. Dit voorkomt dat een notebook die per ongeluk nog aan Gold (D) hangt (bijvoorbeeld omdat `bind` nog niet gedraaid is in de developer-workspace) daar ongemerkt in schrijft.

**Wat dit betekent voor een bestaande implementatie:** elke MLV-notebook die al vóór deze wijziging bestond, mist deze twee cellen totdat je ze er zelf aan toevoegt. Zonder de `%%configure`-cel blijft de notebook gewoon werken in Dev/Test/Prod (die hadden immers al een vaste binding); het risico zit specifiek in developer-workspaces, die zonder deze cellen niet bestonden. Buiten een `DEV_*`-workspace doet het vangnet niets.

**Status:** vastgesteld in code (`src/business_domain/NB_MLV_EXAMPLE.Notebook/notebook-content.sql`, commit `5d59d6a`); getest in eigen omgeving als onderdeel van de ontwikkelflow-test (`testplan-devflow.md`, F2 en F7 — zie `14_ontwikkelproces.md` voor de volledige uitwerking van de developer-workspace-flow zelf). Niet apart getest binnen de scope van dít document: het gedrag van de refresh-cel (hieronder) in combinatie met deze twee nieuwe cellen.

## Demo-implementatie: `NB_MLV_DEMO_GOLD`

`NB_MLV_DEMO_GOLD` (`examples/`, niet gedeployd) draait op een **Wide World Importers (WWI)-achtige demoset**, niet op AdventureWorks. Een notebook `NB_MLV_ADVENTUREWORKS` bestaat niet.

Vijf MLV's, allemaal in het schema `gold`:

| MLV | Inhoud |
|---|---|
| `gold.FactOrderLines` | Orderregels met orderheaders (`Sales_OrderLines` + `Sales_Orders`, gefilterd op `IsCurrent=1`) |
| `gold.DimOrders` | Orderdimensie (niet-gevoelige kolommen) |
| `gold.DimCustomer` | Klantdimensie, met buying groups |
| `gold.DimPackageType` | Verpakkingstype |
| `gold.DimStockItems` | Artikeldimensie |

De bronnen worden gelezen als `LH_GOLD_LAYER.dbo.<Tabelnaam>`: de shortcuts uit `NB_CREATE_SHORTCUTS`. `dbo` is het schema waarin de shortcuts in die demo-tenant stonden. Bij een klant is dat `manifest.shortcuts.source_schema`; `manifest.example.yaml` laat dat leeg (`''`). Elke SELECT filtert op `IsCurrent=1`, een SCD-achtig patroon.

**Gebruik:** goed als voorbeeld van de syntax. Neem het niet over zonder de lakehouse-koppeling en het schema aan te passen.

**Status:** vastgesteld (`notebook-content.sql`, `examples/README.md`). Of dit overeenkomt met de live FINANCE-implementatie van Bitmetric, is niet gecontroleerd.

## Naamgevingsconventie voor Gold-objecten

Uit de wiki (`NB_MLV_EXAMPLE.md`):

| Patroon | Voorbeeld |
|---|---|
| Feittabellen | `gold.Fact<Onderwerp>` |
| Dimensietabellen | `gold.Dim<Onderwerp>` |
| Schema | `gold` (kleine letters) |

**Status:** conventie, **niet afgedwongen** in de code. De demo volgt hem zelf niet helemaal: `DimOrders` en `DimStockItems` staan in het meervoud, naast `DimCustomer` en `DimPackageType`. Spreek per klant af of je enkelvoud of meervoud gebruikt.

**Bitmetric-conventie (aanvulling 2026-10-05):** afwijkend van de wiki gebruikt Bitmetric `gold.F_<Naam>` en `gold.D_<Naam>` in PascalCase, bijvoorbeeld `F_Sales`, `F_Target`, `D_Customer` en `D_CurrencyRate`. Mitchell stelde die vast op 2026-09-28 (demoklant). Fabric slaat MLV-namen in kleine letters op (`gold.f_sales`, zie `11_troubleshooting.md`). In het semantisch model krijgen de tabellen de PascalCase-naam.

## Wat dit betekent voor een nieuwe klantimplementatie

1. Vul `NB_LOAD_GOLD` en `NB_MLV_EXAMPLE` in de CODE-workspace van het domein. Hernoem niets, zie "De Gold-pipeline en de orchestratie". *Bijgewerkt 2026-09-30:* laat de `%%configure`- en vangnet-cellen (zie hierboven) als eerste twee codecellen staan als je met developer-workspaces werkt (ADR-011); zonder deze cellen kan een developer-workspace ongemerkt in de gedeelde Gold schrijven.
2. Pas in `NB_CREATE_SHORTCUTS` de lijst `ShortcutNames` aan (standaard negen WWI-demotabellen) en draai het notebook. Zie `03_shortcuts-en-deployment.md`.
3. Schrijf de `CREATE OR REPLACE MATERIALIZED LAKE VIEW`-statements volgens de afgesproken conventie. `NB_MLV_DEMO_GOLD` is een voorbeeld van de syntax.
4. Maak de refresh-cel van `NB_MLV_EXAMPLE` af: lakehouse-ID uit de Variable Library, falen op een fout, en wachten op de job.

**Status:** aanbeveling op basis van de code. De repo-documentatie heeft geen stap-voor-stap-procedure.

## Versiegeschiedenis

- v1 (2026-09-22): eerste versie.
- v2 (2026-09-25), na review 2:
  - `NB_CREATE_DIMDATE` en `NB_MLV_DEMO_GOLD` staan in `examples/`, worden niet gedeployd en dragen koppelingen van een andere tenant mee (N-V1);
  - nieuwe sectie over de auto-wiring: niet hernoemen of kopiëren (N-R3);
  - MLV-refresh: zit al in het pad, maar met een placeholder-ID, zonder foutafhandeling en zonder wachten (N-R1);
  - `dbo` hangt af van het manifest; de naamconventie wordt niet afgedwongen (N-V1).
- v3 (2026-09-30, geautomatiseerde repo-watch): nieuwe sectie over de `%%configure`- en vangnet-cellen die ADR-011 toevoegt aan `NB_MLV_EXAMPLE` voor developer-workspace-isolatie (commit `5d59d6a`); stap 1 van "Wat dit betekent voor een nieuwe klantimplementatie" aangevuld.
- v4 (2026-10-12, `FMD_FRAMEWORK#58`): de pipelines heten `PL_FMD_LOAD_GOLD` en `PL_FMD_ORCHESTRATION`. `PL_FMD_LOAD_GOLD` is klanteigendom: extra notebooks komen er in Dev als activity bij (correctie op het advies uit v2, N-R3).
