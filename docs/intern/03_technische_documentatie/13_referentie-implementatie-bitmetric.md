# Bijlage — Referentie-implementatie Bitmetric

**Fase:** 3 (Technische documentatie)
**Datum:** 2026-09-25
**Status:** Eerste versie, bijgewerkt op 2026-09-25 (CU-meting)
**Doel:** dit document isoleert alle **concrete, Bitmetric-specifieke details** (repo-commits, job-ID's, omgevingsnamen, incidenten, testresultaten) die in de generieke technische documentatie (`00_architectuur-overzicht.md`, `05_INTEGRATION/`, `06_BUSINESS_DOMEINEN/`, `07`–`12`) bewust zijn weggelaten of vervangen door placeholders. De generieke documentatie is bedoeld als herbruikbaar sjabloon voor elke toekomstige klantimplementatie; dit document is het tegenovergestelde — het is precies wát er bij Bitmetric zelf staat en getest is, als concreet naslagwerk en bewijsmateriaal.

**Placeholders die in de generieke documentatie worden gebruikt, met hun Bitmetric-invulling:**

| Placeholder | Betekenis | Bitmetric-invulling (voorbeeld) |
|---|---|---|
| `<KLANT>` | Klantnaam / tenant | Bitmetric (eigen interne referentie-omgeving, incl. trial-capaciteit `FMDTRIAL`) |
| `<DOMEIN>` | Business-domeinnaam | FINANCE (de enige tot nu toe uitgewerkte/geteste business-domein-implementatie) |
| `<WORKSPACE_GUID>` | Workspace-object-ID (Fabric) | Niet in dit document opgenomen — zie live Variable Library-waarden in de tenant zelf, niet gedeeld in de onderzochte bronnen |
| `<KV_NAAM>` | Key Vault-naam/-URI | Niet in dit document opgenomen — zie `VAR_GOLD_CODE_FMD`/`VAR_CONFIG_FMD`-waarden in de tenant zelf |

---

## Repository en verificatiebasis

- Fork: `bitmetric-fabric/FMD_FRAMEWORK`, branch `main` — 37 commits vóór, 1 commit áchter upstream (`bronnen/00_fork_vs_upstream.md`).
- Laatste repo-audit in dit onderzoek: commit `b3fbed7` (05_INTEGRATION-verificatie), commit `f669a74` ("Production-workspaces krijgen geen omgevingsmarker in de naam (#5)") en commit `703017b` (ADR-009-verificatie, "Add ADR-009 (#6)").
  **Aanvulling (2026-09-30, geautomatiseerde repo-watch):** drie nieuwe commits op `main`: `574029d` (ADR-011: één repository per workspace, met generieke developer-workspaces, #26), `5d59d6a` (NB_SETUP_DEVELOPER_WORKSPACES, #27) en `075c52b` (NB_FMD_CUSTOM_DQ_CLEANSING uitrollen zonder klantcode te overschrijven, #28). Zie de aparte paragraaf hieronder.
- GUID-guard-implementatie (`scripts/guid_guard.py`, `.github/workflows/guid-guard.yml`, `config/guid_allowlist.txt`): al aanwezig sinds commit `1e27391`.

## Omgevingen bij Bitmetric

- **Trial/testcapaciteit:** `FMDTRIAL` — gebruikt voor pipeline- en capaciteitstests buiten de vaste Dev/Test/Prod-omgevingen om. Workspace-voorbeeld: `FMDTRIAL CODE (D)`. Bijbehorende configuratiedatabase: `SQL_FMDTRIAL_FRAMEWORK`.
- **Reguliere framework-database:** `SQL_FMD_FRAMEWORK` (dacpac-doel voor de generieke laag).
- **Eigen productiecapaciteit:** F2 — gemeten CU-gebruik ca. 30.047 van 172.800 CU-seconden (~17%), over één dag.
- **Workspace-naamgeving in de live tenant** (bevestigd via Fabric MCP-server-scan + setup-notebook-cellen): `FINANCE DATA (D)`, `FINANCE DATA (P)`, `SALES CODE (D)`, `INTEGRATION CODE (D)` — dit is de praktijkbevestiging achter **B-ARCH-01**. **Kanttekening (2026-09-23):** dit is een momentopname van workspaces die al bestonden op het moment van de tenant-scan. De setup-notebook-code is sindsdien aangepast (PR #5, commit `f669a74`) zodat nieuw aangemaakte of opnieuw uitgerolde Productie-workspaces géén `(P)`-suffix meer krijgen; `FINANCE DATA (P)` behoudt zijn naam totdat die workspace wordt hernoemd of opnieuw uitgerold.

## Empirische testresultaten (casing-mismatch, job `50b62157`)
*Noot (2026-09-25, review 2): job `50b62157` en de verklaring zijn niet terug te vinden in `bronnen/` (het nieuwste transcript is van 15-09). Mitchell handhaaft het label op basis van de test zelf.*

Op 2026-09-22 heeft Mitchell `PL_TOOLING_POST_ASQL_TO_FMD` gedraaid tegen de **ongewijzigde** pipeline-versie in `FMDTRIAL CODE (D)` (job-ID `50b62157`) en de resultaten rechtstreeks in `SQL_FMDTRIAL_FRAMEWORK` opgevraagd:

```
BronzeLayerEntity: Schema=Sales, Name=SalesOrderDetail, PrimaryKeys=SalesOrderID,SalesOrderDetailID
SilverLayerEntity: Schema=Production, Name=Product
LandingzoneEntity: SourceSchema=Sales, SourceName=Customer, FileName=Sales_Customer
```

Alle 5 `LKP_INSERT_UPDATE_ENTITIE`-iteraties: `Succeeded`. Pipeline-status: `Completed`. Dit weerlegde de eerder — op basis van statische codeanalyse — aangenomen casing-bug (zie `05_INTEGRATION/03_operationele-aandachtspunten.md` in de generieke documentatie voor de volledige technische duiding van het mechanisme).

## LDZ-FTP-verificatie (activity-label vals alarm)

Geverifieerd tegen fork-commit `703017b`: de `InvokePipeline`-activity in `PL_FMD_LDZ_COMMAND_FTP` heeft het misleidende label `PL_FMD_LDZ_COPY_FROM_ADF`, maar roept via `"pipelineId": "4972831f-6320-ab73-46e2-336d0bc59199"` daadwerkelijk `PL_FMD_LDZ_COPY_FROM_FTP_01` aan (diens `logicalId` komt exact overeen; `PL_FMD_LDZ_COPY_FROM_ADF` heeft een andere `logicalId`: `bfe7a852-2306-4ea1-8605-0cd7473dadf8`). Functioneel geen bug — alleen een verwarrend activity-label, ontstaan doordat de pipeline ooit is gekloond van de ADF-variant.

## Notebook-/versiemismatch-incidenten

- **Service Principal vs. Workspace Identity:** de eigen Bitmetric-omgeving gebruikt in de praktijk expliciete Service Principal-credentials in Key Vault, niet Workspace Identity. Dit bleek geen tijdelijk versieverschil maar een vastgelegde platformbeperking: `FabricSql`-connecties weigeren `WorkspaceIdentity` hard (`UnsupportedCredentialType`); zie `FMD/src/NB_UTILITIES_SETUP_FMD.Notebook/notebook-content.py`, commit `5e934ab`. Bevestigt B-SECURITY-02.
- **Dacpac/CI-build-mismatch (opgelost):** verschil tussen lokaal gebuilde `SQL_FMD_FRAMEWORK.dacpac` en de CI-build, veroorzaakt door platform-regeleindes in `SysCommentsObjectAnnotation` (DacFx). Opgelost via commits `1434d2a` → `0ac7e1a` → `b6e63c2`.

## Item-ID-verwisseling tussen Variable Libraries (incident)

Getest/voorgevallen in eigen omgeving: bij een `updateDefinition`-call werd het item-ID van `VAR_GOLD_CODE_FMD` verward met dat van `VAR_GOLD_SHORTCUTS_FMD` — twee gelijk-genoemde maar inhoudelijk compleet verschillende Variable Libraries (respectievelijk 1 variabele: `key_vault_uri_name`, versus 6 variabelen voor shortcut-doelen). Dit overschreef stilzwijgend het verkeerde item. Structurele oorzaak (niet incidenteel): `VAR_GOLD_SHORTCUTS_FMD.VariableLibrary/valueSets/Test.json` (en Acceptance/Production) bevatten in de fork-template letterlijk `"variableOverrides": []`.

## Positional-parameter-bug (bulk-registratiescript)

Gevonden in een handmatig bulk-registratiescript (niet in `PL_TOOLING_POST_ASQL_TO_FMD` zelf, zie trial-sessie 2026-09-15): `sp_UpsertDataSource` werd aangeroepen met positionele in plaats van benoemde parameters, waardoor een bedoelde `@IsActive`-waarde in `@LoadGroup` terechtkwam. Functioneel bleef het werken (`IsActive` viel terug op zijn default), maar `LoadGroup` kreeg onbedoeld `'1'`. Gefixt in het SQL-registratiesjabloon van `output/04_implementatieplan/draaiboek_detail.md`.

## Referentie-implementatie Gold-laag: `NB_MLV_DEMO_GOLD`

De code-geverifieerde demo-implementatie in de fork zelf (`FMD/examples/NB_MLV_DEMO_GOLD.Notebook`) draait op een **Wide World Importers (WWI)-achtige demoset**, niet op AdventureWorks. Dat is een andere implementatie dan de Bitmetric-referentie-implementatie: die draait wel op AdventureWorks, op de Bitmetric- en de trial-capaciteit, buiten de repo (bevestigd door Mitchell, 2026-09-25; zie B-ARCH-04). Vijf MLV's, schema `gold`:

| MLV | Inhoud |
|---|---|
| `gold.FactOrderLines` | Orderregels gejoined met orderheaders (`Sales_OrderLines` + `Sales_Orders`, `IsCurrent=1`) |
| `gold.DimOrders` | Orderdimensie |
| `gold.DimCustomer` | Klantdimensie, gejoined met buying groups |
| `gold.DimPackageType` | Verpakkingstype-lookup |
| `gold.DimStockItems` | Artikeldimensie |

**Niet geverifieerd:** of dit exact overeenkomt met wat in de live Bitmetric FINANCE-tenant staat (geen toegang tot die workspace in dit onderzoek) — dit is de demo/referentie-implementatie uit de fork zelf.

## MLV-refresh: Bitmetric-praktijkkeuze

Bevestigd door Mitchell (2026-09-22): Bitmetric gebruikt de **API-route** (`POST .../lakehouses/{lakehouse_id}/jobs/RefreshMaterializedLakeViews/instances`), niet de handmatige UI-klik. Dit is meegenomen als Bitmetric-standaard in het generieke implementatieplan.

## Capaciteit en kosten

- F2-capaciteit, CU-gebruik ~17% gemeten.
- Spark-pool-sizing verlaagd van `driver_cores: 8/driver_memory: 56g` naar `4/28g` (`ENV_FMD.Environment/Setting/Sparkcompute.yml`) om binnen F2 te passen — één gedeeld environment-item voor alle omgevingen (per-omgeving sizing is bewust teruggedraaid).
- **Activator-kostenincident:** een Fabric Activator triggerde `PL_FINANCE_LOAD_GOLD` op élk workspace-event i.p.v. de bedoelde trigger-conditie, met onnodig capaciteitsverbruik tot gevolg. Zie `12_kosten-en-capaciteit.md` voor de generieke waarschuwing die hieruit is afgeleid.

## CI/CD-praktijk bij Bitmetric

- CI/CD wordt gehost in een **eigen GitHub-organisatie** van Bitmetric (ADR-007) — Azure DevOps is expliciet overwogen en verworpen ("werkcomfort, niet techniek").
- **Bijgewerkt 2026-09-30 (geautomatiseerde repo-watch):** de repo-structuur is niet langer "één repo per klant" (ADR-008) — dat is per 2026-09-29 **Superseded by ADR-011**: **één repository per workspace** (bijv. `<KLANT>_FINANCE_CODE`), plus generieke developer-workspaces per developer. Aanleiding was de end-to-end test van de ontwikkelflow in FMD_TRIAL (`testplan-devflow.md`, F0–F10, commit `574029d`), die drie problemen blootlegde met de oude structuur: verwijzingen tussen workspaces bleven na een *branch out* naar Dev wijzen, een value set per developer lekte naar Test/Prod, en items met dezelfde naam in verschillende domeinen hadden elk een eigen logical ID (`LogicalIdConflictDetected` bij een domeinwissel via de API). Het framework levert de nieuwe flow als `setup/NB_SETUP_DEVELOPER_WORKSPACES.ipynb` (commit `5d59d6a`, #27) en een sjabloon `templates/workspace-repo/.github/` met een `normalize-bindings`-workflow. Zie `09_cicd-en-deployment.md` en `14_ontwikkelproces.md` voor de generieke uitwerking, en `11_troubleshooting.md` voor het gerelateerde `TargetArtifactNameConflict`-issue op `NB_FMD_CUSTOM_DQ_CLEANSING` (commit `075c52b`, #28, in FMD_TRIAL gemerged en gedeployed D → T → P op 2026-09-30).
- Eerdere fabric-cicd-pilot voor INTEGRATION CODE (commits `1cb68ba`…`0d0c2e9`) is teruggedraaid (`68561b3`) ten gunste van native Fabric Git-integratie — fabric-cicd pushte alleen `src/`, klantspecifieke extensies bleven ongetracked.
- ~~ADR-006 (promotiemechanisme) staat op **Proposed**, niet Accepted~~ *Correctie 2026-10-05: ADR-006 is gesloten door ADR-012 (besluit Mitchell 2026-10-05, PR #32, gemerged `9ae2182`): Deployment Pipelines is het promotiemechanisme, fabric-cicd een later spoor.* Oorspronkelijk — Deployment Pipelines is de praktijk-default, geen definitief afgesloten besluit. Zie `09_cicd-en-deployment.md` voor de generieke uitwerking.

## Extensiepunten: wat er wél en niet bestaat

- Het `CustomNotebookName`-mechanisme is generiek beschikbaar, maar er bestaat **geen** kant-en-klare RDW-referentie-implementatie (eerdere aanname hierover was onjuist, gecorrigeerd door Mitchell: "Er is gewoon een customnotebook beschikbaar. Maar niet specifiek voor RDW.").
- GA4 (Google Analytics 4) als bron: niet aangetroffen als gedocumenteerde referentie-implementatie — bestaat alleen als Mitchells eigen test.
