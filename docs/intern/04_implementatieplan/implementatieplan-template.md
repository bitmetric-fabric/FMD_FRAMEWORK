# Implementatieplan-template — FMD Klantimplementatie

**Fase:** 4 (Implementatieplan)
**Datum:** 2026-09-22
**Status:** Eerste versie
**Doel:** stap-voor-stap draaiboek voor een nieuwe FMD-klantimplementatie, van intake tot productie, gebaseerd op de vastgestelde besluiten (Fase 2) en de code-geverifieerde technische documentatie (Fase 3: `05_INTEGRATION/`, `06_BUSINESS_DOMEINEN/`).

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

Dit document is het **generieke sjabloon**. Voor een specifieke klant wordt dit gekopieerd en ingevuld; klantspecifieke afwijkingen horen in die kopie, niet hier.

**Verhouding tot `plan_hoogover.md` en `draaiboek_detail.md` (T3, Fase 5-consistentiecheck):** dit document is een technisch stap-voor-stap-sjabloon op een lager abstractieniveau (Fase 0, A-F), opgesteld vóór `plan_hoogover.md`/`draaiboek_detail.md` bestonden. `plan_hoogover.md` is het door de brief gevraagde hoog-over faseplan (8 fasen, rollen/doorlooptijd/go-no-go/risico's per fase) en `draaiboek_detail.md` het bijbehorende gedetailleerde draaiboek (voorwaarden/acties/verificatie/rollback per fase, plus RACI/risicoregister/productie-acceptatiechecklist). De documenten overlappen. Bij een verschil zijn `draaiboek_detail.md` en `03_technische_documentatie/` leidend; die zijn na review 1 en 2 gecorrigeerd. **Voor nieuw gebruik: begin bij `plan_hoogover.md` en `draaiboek_detail.md`** — die zijn vollediger en direct aan het beslisregister gekoppeld. Dit document blijft staan als aanvullend technisch naslagwerk (met name de setup-notebook-volgorde en de post-deployment-checklist), maar is niet langer het primaire startpunt.

---

## Fase 0 — Vooraf

- [ ] `02_beslisdocument/04_intake-checklist.md` volledig doorlopen en ondertekend (capaciteit, workspace-scope, naamgeving, security).
- [ ] Manifest (`manifest.yaml`, op basis van `FMD/manifest.example.yaml`) ingevuld voor deze klant: `repository`, `naming`, `environments[]` (naam/short/capacity), `config_workspace`, `spark`, `shortcuts`, `framework.lakehouse_schema_enabled`, `security`, `key_vault`.
- [ ] Business-domeinen voor deze klant bepaald (INTEGRATION verplicht + welke van FINANCE/SALES/HR/anders).

---

## Fase A — Provisioning & Setup (Dev)

1. ~~**Workspaces aanmaken**~~ **Workspacenamen vastleggen**, volgens **B-ARCH-01**: `[DOMEIN] [LAAG] ([OMG])`, bv. `INTEGRATION CODE (D)`, `FINANCE DATA (D)`. Geen onderstrepingen, geen OMG-suffix straks in Productie. *Correctie 2026-10-06 (review 3, P3-B3):* de setup maakt de workspaces aan (draaiboek fase 3). Maak ze niet met de hand aan, en zet `security.service_principal_id` in het manifest (draaiboek fase 2 stap 3).
2. **Git-koppeling:** elke Dev-workspace krijgt een eigen repository (ADR-011), bijvoorbeeld `<KLANT>_FINANCE_CODE` ↔ `FINANCE CODE (D)`, branch `dev`. De klantfork van `bitmetric-fabric/FMD_FRAMEWORK` is een aparte repo voor de framework-code en de setup. Test/Prod worden **niet** git-gekoppeld — die vullen zich uitsluitend via de Deployment Pipeline (ADR-005). Bij meerdere developers: `NB_SETUP_DEVELOPER_WORKSPACES` (zie `14_ontwikkelproces.md`). *Correctie 2026-10-05: hier stond "alleen de Dev-workspace van elke CODE-workspace, aan de `dev`-branch van de klant-repo (fork)"; dat was het model van ADR-008.*
3. **Spark-pool-sizing:** gebruik de repo-default `driver_cores: 4, driver_memory: 28g, executor_cores: 4, executor_memory: 28g` (reeds verlaagd vanaf 8/56g om binnen een F2-capaciteit te passen). Pas dit alleen aan als de klantcapaciteit dit toestaat/vereist — er is geen apart, lager "minimum"-cijfer (dat bleek bij verificatie onvindbaar in de bronnen).
4. **Setup-notebooks draaien, in deze volgorde:**
   1. `NB_BOOTSTRAP_FMD.ipynb` — **enige handmatige import**; plaatst de twee onderstaande notebooks met repo-configuratie al ingevuld.
   2. `NB_SETUP_FMD.ipynb` — generieke framework-setup (INTEGRATION).
   3. `NB_SETUP_BUSINESS_DOMAINS.ipynb` — setup per business-domein (één generiek bestand, geen los notebook per domein).

---

## Fase B — INTEGRATION: bronnen registreren

1. **Workspace + lakehouses registreren** (eenmalig per workspace): `sp_UpsertWorkspace` → `WorkspaceGuid`; `sp_UpsertLakehouse` ×3 → exact `LH_DATA_LANDINGZONE`, `LH_BRONZE_LAYER`, `LH_SILVER_LAYER` (geen vrije naamkeuze — `sp_UpsertLandingzoneBronzeSilver` zoekt hier hard op).
2. **Bron(nen) registreren:**
   - **Eén-of-enkele-tabellen:** handmatig via `sp_UpsertConnection` → `sp_UpsertDataSource` → `sp_UpsertLandingzoneBronzeSilver` per entiteit. Zie `05_INTEGRATION/02_configdb-registratie.md` voor de volledige parametersignaturen.
   - ~~**Hele Azure SQL-bron in bulk:** `PL_TOOLING_POST_ASQL_TO_FMD` (`ConnectionGuid`, `DatasourceName`, `DatasourceNamespace`, `DatasourceType`, `Tables`). **Zonder voorbehoud bruikbaar** — de eerder vermoede casing-bug bleek bij een live test geen bug (zie `05_INTEGRATION/03_operationele-aandachtspunten.md` punt 1). Verifieer na afloop wel altijd dat de daadwerkelijke namen zijn doorgekomen, als algemene goede praktijk.~~ *(Correctie 2026-10-15, `FMD_FRAMEWORK#71`. Reden: de setup rolt deze pipeline niet meer uit. Voor een bron met veel tabellen: `PL_FMD_DISCOVER_SOURCE` en daarna `NB_REGISTRATIE`, `02_configdb-registratie.md` Route 3. De pipeline werkt wel op een installatie die hem al heeft.)*
3. **Deactivering (niet verwijderen), B-INFRA-02:** `integration.LandingzoneEntity.IsActive = 0` stopt alle drie de lagen voor die entiteit. `Connection`/`DataSource.IsActive` hebben geen effect op de load. Vanaf dacpac `4dd41cf` (PR #8) laat herregistratie `IsActive` van een bestaande entiteit staan; met een oudere dacpac zet hij `IsActive` weer op 1. Procedure: `03_technische_documentatie/05_INTEGRATION/02_configdb-registratie.md` §Deactivering.
4. **Load draaien/plannen:** via `PL_FMD_LOAD_ALL` (roept `PL_FMD_LOAD_LANDINGZONE` → `PL_FMD_LOAD_BRONZE` → `PL_FMD_LOAD_SILVER` aan en ketent op `Completed`, dus een volgende laag draait ook als de vorige deels faalt; zie `03_technische_documentatie/10_operations.md`) of de wrapper `PL_FMD_ORCHESTRATION`. Plan dit volgens de klantafspraak (nightly/intraday). ~~Zie `PL_FMD_SCHEDULE_NIGHTLY`/`PL_FMD_SCHEDULE_INTRADAY`.~~ *Correctie 2026-10-06 (review 3):* plan `PL_FMD_ORCHESTRATION_TEMPLATE`, met één schema per cadans en een eigen `LoadGroup` per schema (draaiboek fase 5 stap 4).

---

## Fase C — Business-domein: Gold-laag bouwen

Voor elk business-domein (bv. FINANCE), zie `06_BUSINESS_DOMEINEN/`:

1. **Templates vullen, niet hernoemen:** `NB_LOAD_GOLD` en `NB_MLV_EXAMPLE` in de CODE-workspace van het domein. De setup hangt `PL_FMD_LOAD_GOLD` op naam aan de orchestratie, en de pipeline verwijst naar deze notebooks. *Aanvulling 2026-10-12 (`FMD_FRAMEWORK#58`, vastgesteld):* `PL_FMD_LOAD_GOLD` is klanteigendom en wordt door de setup niet meer overschreven. Extra Gold-notebooks voeg je in Dev als activity aan die pipeline toe; promoveer ze samen met of vóór de pipeline (draaiboek fase 6 stap 1). `NB_MLV_DEMO_GOLD` (`FMD/examples/`, niet gedeployd) is een voorbeeld van de MLV-syntax; het draagt koppelingen van een andere tenant mee.
2. **Shortcuts opzetten:** in `NB_CREATE_SHORTCUTS` de lijst `ShortcutNames` vervangen (standaard WWI-demotabellen) en het notebook draaien. Sinds PR #31 faalt het notebook als een shortcut niet lukt, met de namen erbij (*correctie 2026-10-05*; in een oudere fork eindigt het groen: controleer daar de output op `Failed:`). `NB_SETUP_BUSINESS_DOMAINS` heeft `VAR_GOLD_SHORTCUTS_FMD` dan al gevuld: de vier ID-variabelen per omgeving als value set, met de eigen value set actief in elke CODE-workspace (fork vanaf `81fe912`, ADR-010). `SourceSchema` en `Shortcut_TargetSchema` komen uit de manifest-instellingen.
   ⚠️ **Controleer de celoutput van de setup op `❌`-regels.** Kan de setup een lakehouse niet vinden, dan blijft de override voor die omgeving leeg. Met een fork van vóór `81fe912` blijven Test/Acceptance/Production helemaal leeg.
3. **MLV's schrijven:** `CREATE OR REPLACE MATERIALIZED LAKE VIEW`, volgens de conventie `gold.F_<Naam>` / `gold.D_<Naam>` in PascalCase (bijv. `F_Sales`, `D_Customer`), schema `gold` (kleine letters). De conventie wordt niet afgedwongen, en Fabric slaat MLV-namen in kleine letters op (`11_troubleshooting.md`). *Correctie 2026-10-05: hier stond `gold.Fact<Onderwerp>` / `gold.Dim<Onderwerp>`; Bitmetric-conventie vastgesteld door Mitchell op 2026-09-28.*
4. **MLV-refresh:** via de **API-route** (`POST .../lakehouses/{lakehouse_id}/jobs/RefreshMaterializedLakeViews/instances`) — **Bitmetric-standaard**. De cel staat in `NB_MLV_EXAMPLE` en draait in de Gold-pipeline. Sinds PR #21 neemt hij de ID's uit `VAR_GOLD_SHORTCUTS_FMD`, wacht hij op de job en faalt hij bij een fout; kopieer hem ongewijzigd naar het MLV-notebook van het domein. *Correctie 2026-10-05: hier stond dat de cel nog niet af was (placeholder-ID, geen foutafhandeling); dat is opgelost in PR #21 (getest in Dev en Test, `testplan-trial.md` T-E02).* Niet de handmatige UI-klik gebruiken in een klantimplementatie.

---

## Fase D — Semantisch model

1. Direct Lake-model bouwen in de SEMANTIC-workspace, tegen de Gold-laag (DATA-workspace van hetzelfde domein).
2. **Let op cross-workspace-referenties:** Fabric slaat deze intern op als letterlijke object-ID's die bij promotie **niet automatisch herbinden**. Twee routes:
   - Personal-workspace-scenario: handmatige Direct Lake-pointer-swap vóór commit (end-to-end getest).
   - Test/Prod: Deployment Pipeline **deployment rule**, alleen via de Fabric-portal instelbaar (geen REST API-ondersteuning) — dus niet automatiseerbaar in een script.

---

## Fase E — Promotie Dev → Test → Prod

**Mechanisme (B-CICD-01):** Microsoft Fabric Deployment Pipelines, één per CODE/DATA/SEMANTIC/REPORTING-workspace per domein. (fabric-cicd blijft een bewuste toekomstige heroverweging, geen actieve default.)

### Post-deployment checklist (uitvoeren na élke deployment die de betreffende workspace raakt)

Deployment raakt een **Gold-Lakehouse met shortcuts**:
1. Shortcuts in Gold controleren: aantal, en wijzen ze naar Silver van de doelomgeving? Ze gaan mee met de promotie van de DATA-workspace. Alleen als ze ontbreken of ongeldig zijn (bijvoorbeeld bij de eerste uitrol, als Silver bij de promotie nog leeg was): `NB_CREATE_SHORTCUTS` draaien en de shortcuts zelf controleren. *Aanvulling 2026-10-06 (rookproef 2):* promoveer DATA pas als Silver in het doel geladen is. Anders faalt de promotie (`CopyOverwriteResult.GenericError`). *Correctie 2026-09-28 (`testplan-trial.md` T-E04): shortcuts gaan wél mee met de promotie van DATA en wijzen daarna naar Silver van het doel.*
2. `VAR_GOLD_SHORTCUTS_FMD` en `VAR_CONFIG_FMD` in de doelomgeving controleren: is de actieve value set die van de doelomgeving, en is ~~de override voor die omgeving~~ de waarde die daarin geldt niet leeg? *(Correctie 2026-10-06, P3-V8: in Dev staan de waarden in de defaults, zonder override; vanaf `FMD_FRAMEWORK#34` controleert de setup dit zelf.)*
3. Bij het aanpassen van een Variable-Library-item: **item-ID dubbelchecken** tegen de juiste library (`VAR_GOLD_CODE_FMD` vs. `VAR_GOLD_SHORTCUTS_FMD` — gelijkende naam, compleet andere inhoud) vóórdat een `updateDefinition`-call wordt gedaan.

Deployment raakt een **SEMANTIC-workspace**:
4. Direct Lake-pointers controleren/herstellen (pointer-swap of deployment rule, zie Fase D).

Deployment raakt een **Gold-Lakehouse met MLV's**:
5. MLV-refresh (API-route) desgewenst herdraaien als de onderliggende data is gewijzigd.

Algemeen:
6. `DMTS_EntityNotFoundOrUnauthorized`/`RequestValidationFailed`: **niet blindelings retryen** — eerst via de operation-detail-API de onderliggende fout opzoeken; vaak een structurele "dode" GUID-referentie die alleen met een Variable-Library-fix permanent oplost, niet met een retry.

---

## Bijlage — Monitoring & troubleshooting

- **FMD_Logging Power BI-rapport**, bovenop de `logging`-schema-tabellen (`CopyActivityExecution`, `NotebookExecution`, `PipelineExecution`) — eerste aanlooppunt bij operationele vragen. Let op bekende datakwaliteitsissues: inconsistente `LogType`-spelling (`FailPipeline`/`FailedPipeline`), `EntityLayer` met 4 waarden, ongenormaliseerde `TriggerType`-waarde `"1"`.
- **Capaciteitscontentie:** notebook-jobs/Livy-sessies kunnen 15–30+ min in de wachtrij staan bij drukte. Geen fout — geduldig pollen (60–180s), bij >20–25 min aan de klant/gebruiker voorleggen of doorwachten gewenst is.
- **Livy-sessies** sterven na inactiviteit (`LIVY_JOB_TIMED_OUT`) — status checken vóór gebruik, zo nodig nieuwe sessie starten.
- **`FA_THROW_ERROR_*`** (`LandingzoneFailed`/`BronzeFailed`/`SilverFailed`): een echte fout van die laag, opnieuw gegooid nadat hij gelogd is. Altijd als incident behandelen. Oorzaak en handelwijze staan in `03_technische_documentatie/10_operations.md` en `11_troubleshooting.md`.
- **Watermark-contract voor custom notebooks** (via `CustomNotebookName`): ontvangt `LastLoadValue`, berekent de nieuwe stand, retourneert die via `notebookutils.notebook.exit` met een `LoadValue`-sleutel. ⚠️ `NB_FMD_CUSTOM_NOTEBOOK_TEMPLATE` zet `LoadValue = datetime.now()`; vervang dat door het maximum van de geladen data (`07_extension-points.md` §2).
- **Registratiewaarden:** alleen de combinaties `Connection.Type`/`DataSource.Type` uit `07_extension-points.md` §1 worden geladen; een andere waarde wordt stil overgeslagen. `SourceCustomSelect` wordt niet gelezen.

---

## Fase F — UAT & Sign-off

Zie `02_beslisdocument/04_intake-checklist.md`, sectie "User acceptance testing" en "Non-functional testing" (Spark-pool binnen limieten, geen datacorruptie bij incrementele loads, failover indien HA vereist).

---

## Verdieping: trial-/proefdeployment

Voor een concreet, praktijk-gebaseerd draaiboek van een trial-deployment (inclusief een herbruikbaar SQL-sjabloon voor snelle bronregistratie en een checklist voor wat een trial-validatie moet dekken), zie **`draaiboek_detail.md`** in deze map.

## Openstaande punten voor dit sjabloon

- **Twee bewust on hold gezette cosmetische opschoningen** (casing/Expression-wrapper in `PL_TOOLING_POST_ASQL_TO_FMD`, activity-label in `PL_FMD_LDZ_COMMAND_FTP`) hebben geen invloed op dit implementatieplan — functioneel geen probleem.
