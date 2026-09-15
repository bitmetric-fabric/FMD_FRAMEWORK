# Triage: afwijkingen van upstream

Datum: 2026-09-15 · branch `feature/upstream-fork-candidates` · analyse-only, niets gewijzigd.

## 0. Let op: de juiste baseline

`git diff upstream/main` geeft **104 bestanden / 24.098 regels** — dat is misleidend.
`upstream/main` staat precies één commit vóór op ons merge-base: `1ff1684 "Docs1 (#282)"`
(Erwin de Kreuk, 8 sep 2026), die de Docusaurus-site `docs/` + `docsw/` weggooit en
`Images/Branding/fmd-cover.png` terugzet. Die ~24k regels zijn dus **upstream die zijn
eigen docs opruimt**, geen werk van jou.

De echte fork-delta is `git diff <merge-base>..HEAD`:

```
git merge-base upstream/main HEAD   # ebe97d4 "Docs (#281)"
git diff ebe97d4..HEAD --stat       # 60 files changed, 2319 insertions(+), 68 deletions(-)
```

Alles hieronder gaat over die 60 bestanden.

## 1. Samenvatting

| Categorie | Bestanden | Toelichting |
|---|---|---|
| **A** — generieke verbetering | 55 | LoadGroup-feature (SQL + 26 pipelines), deployment-pipeline-helpers, orchestratie-/Gold-templates, MLV-refresh, Development-valueSet |
| **B** — omgevingsconfig gelekt | 1 | `repo_owner = "bitmetric-fabric"` in beide setup-notebooks (1 logisch blok, 2 bestanden) |
| **C** — experiment/restant | 0 | de fabric-cicd-experimenten zijn al netjes teruggedraaid (`0ac7e1a`, `68561b3`) — netto nul t.o.v. upstream |
| **?** — twijfel | 4 | Sparkcompute-sizing, `lakehouse_schema_enabled: true`, `Acceptance`→`Development` rename, verwijderde `variable_parameters.update`-cel |

Nuance bij "B = 1": de generieke laag is **schoner dan verwacht**. Alle GUID's in de nieuwe
pipeline-JSON zijn de placeholder-GUID's uit `config/item_config.yaml` /
`config/item_deployment.json` die `deploy_item()` bij deployment vervangt (zie §3.1) —
geen trial-capacity-lek. De setup-notebooks staan nog volledig op `<your capacity name>`,
`business_domain_names = ['FINANCE','SALES']`, `00000000-…` group-ID's.

## 2. Tabel per wijziging

### 2.1 LoadGroup — plannen van bronnen op verschillende cadences

| Bestand | Regel(s) | Cat. | Bestemming | Toelichting |
|---|---|---|---|---|
| [src/Config_Database/integration/Tables/DataSource.sql](../src/Config_Database/integration/Tables/DataSource.sql#L8) | 8 | A | — | `[LoadGroup] VARCHAR(50) DEFAULT('') NOT NULL`. Generiek, backwards compatible (lege default = huidig gedrag). Kolom is metadata-drager; de *waarden* horen in `integration.DataSource` — dat is precies waar ze staan. |
| [src/Config_Database/integration/StoredProcedures/sp_UpsertDataSource.sql](../src/Config_Database/integration/StoredProcedures/sp_UpsertDataSource.sql) | 12, 37, 45, 56 | A | — | `@LoadGroup VARCHAR(50) = ''` doorgezet naar INSERT en UPDATE. |
| [src/Config_Database/execution/Views/vw_LoadSourceToLandingzone.sql](../src/Config_Database/execution/Views/vw_LoadSourceToLandingzone.sql#L11) | 11 | A | — | `DS.[LoadGroup]` toegevoegd aan select-list. |
| [src/Config_Database/execution/Views/vw_LoadToBronzeLayer.sql](../src/Config_Database/execution/Views/vw_LoadToBronzeLayer.sql#L19-L21) | 19-21 | A | — | idem. |
| [src/Config_Database/execution/Views/vw_LoadToSilverLayer.sql](../src/Config_Database/execution/Views/vw_LoadToSilverLayer.sql#L28-L29) | 28-29 | A | — | idem. |
| [src/Config_Database/execution/StoredProcedures/sp_GetBronzelayerEntity.sql](../src/Config_Database/execution/StoredProcedures/sp_GetBronzelayerEntity.sql#L4) | 4, 30-32 | A | — | `@LoadGroup`-parameter + `(@LoadGroup = '' OR LoadGroup = @LoadGroup)`. Lege string = alles, dus bestaande aanroepen ongewijzigd. |
| [src/Config_Database/execution/StoredProcedures/sp_GetSilverlayerEntity.sql](../src/Config_Database/execution/StoredProcedures/sp_GetSilverlayerEntity.sql#L4) | 4, 39-41 | A | — | idem. |
| `src/PL_FMD_LDZ_COMMAND_*.DataPipeline/pipeline-content.json` (9×: ADF, ADLS, ASQL, FTP, NOTEBOOK, ONELAKE, ORACLE, SFTP, SQLMI) | ~245-250, ~287, ~471-477 | A | — | `LoadGroup`-parameter (defaultValue `""`) + doorgifte aan child-pipeline + `and (''='@{…LoadGroup}' or LoadGroup='@{…LoadGroup}')` in de `sqlReaderQuery`. Uniform patroon over alle 9. |
| `src/PL_FMD_LDZ_COPY_FROM_*.DataPipeline/pipeline-content.json` (10×) | parameterblok | A | — | Alleen parameter-doorgifte, geen logica. |
| [src/PL_FMD_LOAD_ALL.DataPipeline/pipeline-content.json](../src/PL_FMD_LOAD_ALL.DataPipeline/pipeline-content.json#L753-L759) | 11-14, 49-52, 549-552, 756-759 | A | — | `LoadGroup` doorgegeven aan Landingzone/Bronze/Silver + eigen parameter. |
| [src/PL_FMD_LOAD_LANDINGZONE.DataPipeline/pipeline-content.json](../src/PL_FMD_LOAD_LANDINGZONE.DataPipeline/pipeline-content.json#L642) | 9× doorgifte, 642 (query), 814-817 | A | — | `SELECT distinct [ConnectionType] … and (''='@{…}' or LoadGroup='@{…}')`. |
| [src/PL_FMD_LOAD_BRONZE.DataPipeline/pipeline-content.json](../src/PL_FMD_LOAD_BRONZE.DataPipeline/pipeline-content.json#L244-L250) | 244-250, 523-526 | A | — | `LoadGroup` als `String`-parameter naar `sp_GetBronzelayerEntity`. |
| [src/PL_FMD_LOAD_SILVER.DataPipeline/pipeline-content.json](../src/PL_FMD_LOAD_SILVER.DataPipeline/pipeline-content.json#L17-L23) | 17-23, 527-530 | A | — | idem voor `sp_GetSilverlayerEntity`. |
| [wiki/LoadGroup_Scheduling.md](../wiki/LoadGroup_Scheduling.md) | hele bestand (132) | A | — | Uitleg van de feature. Bevat geen omgevingswaarden (gecheckt op GUID's, workspace-namen, capacity). |
| [src/SQL_FMD_FRAMEWORK.SQLDatabase/SQL_FMD_FRAMEWORK.dacpac](../src/SQL_FMD_FRAMEWORK.SQLDatabase/SQL_FMD_FRAMEWORK.dacpac) | binair | A | — | Herbouwd uit bovenstaande `.sql`-bronnen. `.github/workflows/dacpac-guard.yml` (upstream) faalt als hij niet matcht, dus dit is een verplichte meeverandering, geen los artefact. |

### 2.2 Schedule-wrappers

| Bestand | Regel(s) | Cat. | Bestemming | Toelichting |
|---|---|---|---|---|
| [src/PL_FMD_SCHEDULE_NIGHTLY.DataPipeline/pipeline-content.json](../src/PL_FMD_SCHEDULE_NIGHTLY.DataPipeline/pipeline-content.json) | 1-40 | A | — | Wrapper die `PL_FMD_LOAD_ALL` aanroept met `"LoadGroup": "NIGHTLY"`. Hang er een Fabric-schedule aan. |
| [src/PL_FMD_SCHEDULE_INTRADAY.DataPipeline/pipeline-content.json](../src/PL_FMD_SCHEDULE_INTRADAY.DataPipeline/pipeline-content.json) | 1-40 | A | — | Idem met `"INTRADAY"`. |
| ↳ beide: `.platform` | 1-12 | A | — | `logicalId` 03ba9db4-… / 6beb329c-…, geregistreerd in `config/item_deployment.json`. Framework-conventie, geen omgevingswaarde. |
| ↳ beide: `"defaultValue": "40e27fdc-775a-4ee2-84d5-48893c92d7cc"` | 36 | **A** (was mijn B-verdenking) | — | Dít is niet jouw trial-workspace: exact dezelfde GUID staat als `workspaces.workspace_data` in upstream's [config/item_config.yaml:2](../config/item_config.yaml#L2) en in upstream's eigen `PL_FMD_LOAD_ALL` / `PL_FMD_LOAD_LANDINGZONE`. `deploy_item()` vervangt hem per environment (zie §3.1). Gekopieerd volgens de conventie — correct. |
| ↳ beide: `"connection": "6d8146c6-a438-47df-94e2-540c552eb6d7"` | 20 | A | — | = `CON_FMD_FABRIC_PIPELINES` in `item_config.yaml:10`, ook upstream-placeholder. |
| [config/item_deployment.json](../config/item_deployment.json#L172-L186) | 172-186 | A | — | Registratie van de 3 nieuwe pipelines. Vereist, anders worden ze niet gedeployed én niet ge-ID-remapt. |

### 2.3 Orchestratie- en Gold-templates

| Bestand | Regel(s) | Cat. | Bestemming | Toelichting |
|---|---|---|---|---|
| [src/PL_FMD_ORCHESTRATION_TEMPLATE.DataPipeline/pipeline-content.json](../src/PL_FMD_ORCHESTRATION_TEMPLATE.DataPipeline/pipeline-content.json) | 1-28 | A | — | Skelet met één `InvokePipeline` naar `PL_FMD_LOAD_ALL`; domeinen worden er per klant bij gegenereerd (§2.4). |
| ↳ `.platform` description | 7 | A | — | Beschrijft expliciet "copy/rename per customer" — goede template-hygiëne. |
| [src/business_domain/PL_FMD_LOAD_GOLD_TEMPLATE.DataPipeline/pipeline-content.json](../src/business_domain/PL_FMD_LOAD_GOLD_TEMPLATE.DataPipeline/pipeline-content.json) | 1-43 | A | — | `NB_LOAD_GOLD` → `NB_MLV_EXAMPLE`. `notebookId` c884e094-… en 7f3419e4-… komen uit `config/item_deployment_code_business_domain.json`, dus placeholders. |
| [config/item_deployment_code_business_domain.json](../config/item_deployment_code_business_domain.json#L27-L31) | 27-31 | A | — | Registratie van `PL_FMD_LOAD_GOLD_TEMPLATE`. |
| [src/business_domain/NB_MLV_EXAMPLE.Notebook/notebook-content.sql](../src/business_domain/NB_MLV_EXAMPLE.Notebook/notebook-content.sql#L37-L66) | 37-66 | A | — | Markdown + pyspark-cel die `RefreshMaterializedLakeViews` POST doet. `workspace_id` komt uit `notebookutils.runtime.context`. **Maar** `lakehouse_id = "<your Gold lakehouse id>"` is handmatig invulwerk — zie vraag V5. |

### 2.4 Setup-automatisering (`NB_UTILITIES_SETUP_FMD` + setup-notebooks)

| Bestand | Regel(s) | Cat. | Bestemming | Toelichting |
|---|---|---|---|---|
| [src/NB_UTILITIES_SETUP_FMD.Notebook/notebook-content.py](../src/NB_UTILITIES_SETUP_FMD.Notebook/notebook-content.py#L721-L800) | 721-800 | A | — | `get_deployment_pipeline_id_by_name`, `ensure_deployment_pipeline`, `assign_deployment_pipeline_stage`, `deploy_deployment_pipeline`. Native Fabric ALM scripten i.p.v. per klant klikken. Idempotent. |
| ↳ | 801-855 | A | — | `wire_domain_into_orchestration()` — voegt per business-domein een `InvokePipeline`-activity toe aan `PL_FMD_ORCHESTRATION_TEMPLATE` via getDefinition/updateDefinition. Idempotent op activity-naam. |
| ↳ | 856-890 | A | — | `set_variable_library_values()` — schrijft waarden in een gedeployde Variable Library. Dit is precies het mechanisme dat B-lekken *voorkomt*. |
| [setup/NB_SETUP_FMD.ipynb](../setup/NB_SETUP_FMD.ipynb) | cel `d6931af9`/`8f569535` | A | — | Roept `deploy_deployment_pipeline` aan voor `code` en `data`. Namen afgeleid van `domain_name` + `environments` — geen hardcoding. |
| [setup/NB_SETUP_BUSINESS_DOMAINS.ipynb](../setup/NB_SETUP_BUSINESS_DOMAINS.ipynb) | cel 47 | A | — | Idem voor `code/data/reporting/semantic` per business-domein. |
| ↳ | cel 49 | A | — | Wire-loop naar de orchestrator, met `integration_workspace_prefix` afgeleid uit `configuration_database_workspace`. |
| ↳ | cel 44 | A | — | Auto-fill van `VAR_GOLD_SHORTCUTS_FMD`: zoekt Gold/Silver workspace+lakehouse-ID's op per stage en zet ze via `set_variable_library_values`. Lakehouse-namen `LH_GOLD_LAYER`/`LH_SILVER_LAYER` zijn framework-conventie, niet omgevingsspecifiek. |
| [setup/NB_SETUP_FMD.ipynb](../setup/NB_SETUP_FMD.ipynb) | ~393-408 | A | — | TST-environment toegevoegd (`' DATA (T)'`, `' CODE (T)'`), capacity `capacity_name_dvlm`. Namen worden opgebouwd uit `domain_name` + `framework_post_fix`, dus generiek. |
| [setup/NB_SETUP_BUSINESS_DOMAINS.ipynb](../setup/NB_SETUP_BUSINESS_DOMAINS.ipynb) | cel 19 | A | — | Idem: `environment_name: 'test'`, `environment_short: 'T'`. |

### 2.5 De enige echte B

| Bestand | Regel(s) | Cat. | Bestemming | Aangetroffen waarde |
|---|---|---|---|---|
| [setup/NB_SETUP_FMD.ipynb](../setup/NB_SETUP_FMD.ipynb#L274) | 274 (cel "Repo Configuration") | **B** | `manifest` | `repo_owner = "bitmetric-fabric"  # Owner of the repository (bitmetric's fork, not upstream edkreuk)` |
| [setup/NB_SETUP_BUSINESS_DOMAINS.ipynb](../setup/NB_SETUP_BUSINESS_DOMAINS.ipynb#L288) | 288 (idem) | **B** | `manifest` | idem |

Toelichting: dit is niet je trial-capacity, maar het is wél een waarde die per
klantimplementatie vaststaat en nooit meer verandert — precies de definitie van `manifest`.
Een klant die dit template forkt naar `klant-x/FMD_FRAMEWORK` moet deze regel aanpassen,
anders trekt de setup-notebook code uit jullie repo. Nu staat het op regel 274 van een
`.ipynb`, waar niemand het vindt. Commit `cb748d8` laat zien dat het bewust is gedaan
(upstream stond op `edkreuk`), dus het is geen ongeluk — maar de plek klopt niet.
Zie vraag V1.

### 2.6 Twijfelgevallen

| Bestand | Regel(s) | Cat. | Toelichting |
|---|---|---|---|
| [src/ENV_FMD.Environment/Setting/Sparkcompute.yml](../src/ENV_FMD.Environment/Setting/Sparkcompute.yml#L2-L9) | 2-9 | **?** | `driver_cores: 8 → 4`, `driver_memory: 56g → 28g`, idem executors. De `ponytail:`-comment zegt het zelf: *"sized for the Dev/Test capacity's pool limit (16 cores / 112g)"* en *"If Prod has a bigger capacity, its pool limit may allow raising this back up"*. Dat is letterlijk een omgevingsafhankelijke waarde die als framework-default in de code staat. Maar upstream's 8/56g is óók een willekeurige keuze, en een default moet er zijn. Zie V2. |
| [src/VAR_FMD.VariableLibrary/variables.json](../src/VAR_FMD.VariableLibrary/variables.json#L14) | 14 | **?** | `"value": ""` → `"value": true` voor `lakehouse_schema_enabled` (type `Boolean`). Technisch een bugfix: `""` is geen geldige Boolean. Maar `true` is ook een inhoudelijke keuze; `false` is een legitieme klantkeuze en de setup-notebooks hebben er al een eigen `lakehouse_schema_enabled`-variabele voor. Zie V3. |
| `src/**/VariableLibrary/settings.json` (4×) + `valueSets/Acceptance.json → Development.json` (4×) | settings 3-6 | **?** | `valueSetsOrder` was `[Test, Acceptance, Production]`, is nu `[Development, Test, Production]`. Consistent met de TST-uitbreiding en met de deployment-pipeline-stages (`Development/Test/Production`). Maar het is wél een keuze over jullie DTAP-inrichting die je een klant oplegt. Zie V4. |
| [setup/NB_SETUP_BUSINESS_DOMAINS.ipynb](../setup/NB_SETUP_BUSINESS_DOMAINS.ipynb) | cel 33/34 | **?** | De cel `variable_parameters.update({"SourceWorkspaceId": …, "Shortcut_TargetLakehouseId": …})` is **verwijderd**, vervangen door de auto-fill-cel (cel 44). Ziet er bewust uit, maar de oude cel vulde die ID's vóór deployment in de library-definitie, de nieuwe ná deployment via de API. Als iets de oude route nog gebruikt (bijv. `overwrite_variable_library=True` die de library overschrijft ná de auto-fill) verdwijnen de waarden weer. Niet geverifieerd. Zie V6. |

Alle overige regels in de 4 variable-library-mappen zijn `\ No newline at end of file`-fixes
— ruis, geen categorie.

## 3. Sweep: hardcoded omgevingswaarden in *ongewijzigde* bestanden

Gescand: alle GUID's, `abfss://`-paden, e-mailadressen, connectiestrings, tenant-ID's,
capaciteitsverwijzingen en `*.fabric.microsoft.com`-endpoints in `src/`, `config/`,
`setup/`, `wiki/`, `Taskflow/`, `.github/` en de root-`.md`'s.

### 3.1 Placeholder-GUID's — geen probleem, maar wel goed om te weten

`config/item_config.yaml` is upstream's *vervang-tabel*: elke GUID daarin is een "old_id"
die `deploy_item()` → `replace_ids_and_mark_inactive()` tijdens deployment vervangt door de
echte ID in de doelworkspace (`notebook-content.py:707`, `:570-571`). Ze staan met opzet in
de JSON-bronnen.

| Waarde | Voorkomens | Betekenis |
|---|---|---|
| `372237f9-709a-48f8-8fb2-ce06940c990e` | 161 | `CON_FMD_FABRIC_SQL` |
| `6d8146c6-a438-47df-94e2-540c552eb6d7` | 26 | `CON_FMD_FABRIC_PIPELINES` |
| `40e27fdc-775a-4ee2-84d5-48893c92d7cc` | 9 | `workspaces.workspace_data` |
| `5929775e-aff1-430c-b56e-f855d0bc63b8` | 4 | `CON_FMD_FABRIC_NOTEBOOKS` |
| `00000000-0000-0000-0000-000000000000` | 57 | expliciet gemapt naar de doelworkspace |

**Wel een risico:** dit is een impliciete conventie zonder enige validatie. Als iemand een
nieuw item toevoegt met een GUID die *niet* in `item_config.yaml` of
`item_deployment*.json` staat, wordt hij niet vervangen en wijst het gedeployde artefact
stilletjes naar Erwins tenant. Zie V7.

### 3.2 Echte hardcoded waarden die al in upstream zitten

| Bestand | Regel | Waarde | Probleem |
|---|---|---|---|
| [config/item_config.yaml](../config/item_config.yaml#L19) | 19 | `nl7yhqnbrscude3yv6mas6bxpq-tndhi54vbs4urpccunwiydulzi.datawarehouse.fabric.microsoft.com,1433` | Echte SQL-endpoint-hostname van upstream's config-database. Wordt wel gemapt (`notebook-content.py:696`, old_id = `deployment_item["endpoint"]`), dus functioneel ok — maar het lekt een tenant-specifiek endpoint in een publiek template. |
| [src/business_domain/NB_CREATE_DIMDATE.Notebook/notebook-content.py](../src/business_domain/NB_CREATE_DIMDATE.Notebook/notebook-content.py#L11-L16) | 11, 13, 16 | `default_lakehouse: 63ddad67-a2c0-424b-bae6-d93db2fc592a`, `default_lakehouse_workspace_id: 89c45add-7ca9-4fdf-be0f-8e5665294031` | Deze twee GUID's staan **niet** in `item_config.yaml` en worden dus **niet** vervangen. Notebook opent bij een klant met een lakehouse-binding naar een vreemde tenant. |
| [src/business_domain/NB_MLV_DEMO_GOLD.Notebook/notebook-content.sql](../src/business_domain/NB_MLV_DEMO_GOLD.Notebook/notebook-content.sql#L11-L16) | 11, 13, 16 | `default_lakehouse: b6e09e2a-99d3-4a4a-9d6e-8d978cd44956`, `default_lakehouse_workspace_id: c90c9850-99fe-4050-899c-417cc30d7f70` | `c90c9850-…` ís `workspace_business_domain_data` uit `item_config.yaml:5` en wordt vervangen; `b6e09e2a-…` (de lakehouse) staat nergens in de mapping. Half-gemapt. |
| [Taskflow/FMD_FABRIC_TASKFLOW.json](../Taskflow/FMD_FABRIC_TASKFLOW.json) | meerdere | 9 unieke GUID's, o.a. `168cccc8-dca2-4ab6-a77a-8dece2129896`, `a3e2e795-cd83-4083-8f7d-a5f4cd906116`, `d544f540-9b4e-4b31-a936-aaaafb9d21f6` | Rauwe export van upstream's taskflow; geen enkele staat in de vervang-tabel. Wordt voor zover ik zie ook niet gedeployed — waarschijnlijk documentatie-artefact. |

Alle andere notebooks (`NB_FMD_LOAD_BRONZE_SILVER`, `NB_FMD_LOAD_LANDING_BRONZE`,
`NB_FMD_CUSTOM_NOTEBOOK_TEMPLATE`, `NB_FMD_LOAD_DEMO_DATA`, `NB_CREATE_SHORTCUTS`,
`NB_FMD_DQ_CLEANSING`, `NB_FMD_PROCESSING_*`) hebben `default_lakehouse: null` en bouwen
hun `abfss://`-paden volledig uit parameters. Schoon.

### 3.3 Schoon bevonden

- Geen e-mailadressen, tenant-ID's, connectiestrings of wachtwoorden in `src/`, `config/`, `setup/`, `wiki/`.
- Geen capaciteits-ID's; overal `'<your capacity name>'`.
- Alle group-/principal-ID's in de setup-notebooks en de root-`.md`'s staan op `00000000-0000-0000-0000-000000000000`.
- `business_domain_names = ['FINANCE','SALES']`, `domain_name = 'INTEGRATION'`, `framework_post_fix = ''` — upstream-defaults, ongewijzigd.
- Alle vier `variables.json` hebben lege `value`-velden (enige uitzondering: `lakehouse_schema_enabled`, zie V3).
- `wiki/LoadGroup_Scheduling.md` bevat geen GUID's, workspace-namen of capaciteitsverwijzingen.

### 3.4 Losse opmerking

`docs/fmd-readiness.md` staat untracked in de working tree (`git status`). Niet meegenomen
in deze analyse; laat weten of hij mee moet in het template of weg kan.

## 4. Vragen aan Mitchell

**V1 — `repo_owner`.** De setup-notebooks halen de framework-code uit
`github.com/{repo_owner}/{repo_name}`. Nu hardcoded op `bitmetric-fabric` op regel 274/288
van twee `.ipynb`'s. Wat wil je?
&nbsp;&nbsp;(a) Laten staan — klanten forken dit template en jij verwacht dat ze de regel zelf aanpassen.
&nbsp;&nbsp;(b) Naar `manifest` — één `manifest.yml`/`manifest.json` in de repo-root met `repo_owner`, `repo_name`, `branch`, `domain_name`, `framework_post_fix`, capaciteitsnamen; de notebooks lezen die. Eén plek die een klant bij oplevering invult.
&nbsp;&nbsp;(c) Terug naar `edkreuk` en klanten laten upstream trekken — lijkt me niet, want dan krijgen ze jullie fork-verbeteringen niet.

**V2 — Sparkcompute.** `driver/executor: 4 cores / 28g` is gekozen voor de pool-limiet van
jouw Dev/Test-capacity (16 cores / 112g). Bij een klant met een F64 is dat onnodig krap; bij
een klant met een F2 nog steeds te groot. Wat is de bedoeling?
&nbsp;&nbsp;(a) Zo laten als veilige ondergrens die op elke capacity start — dan de `ponytail:`-comment herschrijven naar "conservatieve default, verhoog bij grotere capacity" i.p.v. een verwijzing naar *jouw* Dev/Test.
&nbsp;&nbsp;(b) Naar `variable-library` / per-stage config — maar `Sparkcompute.yml` is een Environment-item, dat kan geen library-variabelen lezen; dan moet de setup-notebook het bestand per environment schrijven. Meer werk.
&nbsp;&nbsp;(c) Terug naar upstream's 8/56g en jouw trial-limiet als lokale afwijking behandelen die je niet commit.

**V3 — `lakehouse_schema_enabled`.** Upstream had `"value": ""` bij type `Boolean` — kapot.
Jij hebt er `true` van gemaakt. Is `true` de framework-default die je aan elke klant wil
meegeven, of moet dit `false` zijn, of moet het bij oplevering gezet worden (dan `manifest`,
want het verandert daarna nooit meer en de setup-notebooks hebben er al een eigen vlag voor)?

**V4 — `Acceptance` → `Development`.** Je hebt de valueSet hernoemd en de volgorde op
`[Development, Test, Production]` gezet, passend bij de drie deployment-pipeline-stages. Maar
sommige klanten hebben wél een echte Acceptance-omgeving (DTAP i.p.v. DTP).
&nbsp;&nbsp;(a) Drie stages vastzetten als framework-standaard.
&nbsp;&nbsp;(b) Vier valueSets meeleveren (`Development`, `Test`, `Acceptance`, `Production`) en de klant laat er één leeg — kost niets, `deploy_deployment_pipeline()` neemt de stages al uit een lijst.
&nbsp;&nbsp;(c) Stages uit `manifest` laten komen.

**V5 — MLV-refresh lakehouse-ID.** `NB_MLV_EXAMPLE` regel ~49 heeft
`lakehouse_id = "<your Gold lakehouse id>"` als handmatige invulplek. Je hebt in dezelfde
branch `set_variable_library_values()` gebouwd die precies dit soort ID's automatisch invult
(`VAR_GOLD_SHORTCUTS_FMD.SourceLakehouseId` ís de Gold-lakehouse-ID). Was het de bedoeling
dat het notebook die variabele leest via `notebookutils.variableLibrary`, of is de handmatige
placeholder bewust omdat de klant zijn eigen MLV-notebook schrijft en dit puur een voorbeeld is?

**V6 — verwijderde `variable_parameters.update`-cel.** In `NB_SETUP_BUSINESS_DOMAINS` is de
cel die `SourceWorkspaceId`/`Shortcut_TargetLakehouseId` etc. in `variable_parameters` zette
verdwenen, vervangen door de auto-fill-cel ná deployment. Bevestig je dat dit bewust is?
En: draait de auto-fill-cel gegarandeerd ná de cel die de VariableLibrary deployt met
`overwrite_variable_library=True`? Zo niet, worden de auto-ingevulde waarden bij een
her-run overschreven met leeg. Ik heb de celvolgorde niet geverifieerd tegen een echte run.

**V7 — placeholder-GUID-conventie.** Het hele deployment-model leunt erop dat elke GUID in
`src/` in `item_config.yaml` of `item_deployment*.json` staat. Er is geen check. De sweep
vond al drie GUID's die er doorheen glippen (`NB_CREATE_DIMDATE`, `NB_MLV_DEMO_GOLD`,
`Taskflow`). Wil je daar een CI-guard op, in de trant van `dacpac-guard.yml`: "elke GUID in
`src/` staat in de vervang-tabel, anders faalt de build"? Dat vangt precies het soort lek dat
je hier zoekt, automatisch, voor elke toekomstige wijziging. Dit is niet iets dat ik nu
gedaan heb — alleen een voorstel.

**V8 — `NB_CREATE_DIMDATE` / `NB_MLV_DEMO_GOLD` / `Taskflow`.** Deze drie dragen upstream's
tenant-ID's mee (§3.2). Ze zijn niet van jou en zaten er al in. Moeten ze in het template
blijven (demo-materiaal), of horen ze in een aparte `examples/`-map die je bij oplevering
weggooit? Dat is een upstream-fix die je als PR terug zou kunnen geven.
