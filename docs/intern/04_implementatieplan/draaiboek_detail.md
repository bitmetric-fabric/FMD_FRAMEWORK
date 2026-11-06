# Draaiboek detail — gedetailleerde stappen per implementatiefase

**Fase:** 4B (Implementatieplan — verdieping)
**Datum:** 2026-09-25
**Status:** Versie 2.22: gecorrigeerd na review 1, 2, 3 en de eindcontrole, bijgewerkt na rookproef 2 en PR #30–#49, plus PR #52 (gemerged 2026-10-11) en PR #58 (gemerged 2026-10-12; zie versiegeschiedenis onderaan)
**Bron:** `04_implementatieplan/plan_hoogover.md` (fase-indeling), `02_beslisdocument/02_beslisregister.md` (besluit-ID's), `03_technische_documentatie/` (technische onderbouwing per stap), plus de praktijkervaring uit `Bijlage A` (trial-deployment, 2026-09-15-sessie)

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

Dit document werkt elke fase uit `plan_hoogover.md` uit tot concrete stappen: voorwaarden, exacte acties, verificatie, rollback/herstel, en verwijzingen naar de technische documentatie en de sturende besluiten. Stappen die alleen gelden bij een specifieke besluitkeuze zijn expliciet gemarkeerd (bijv. "Alleen bij B-SECURITY-02 = expliciete Service Principal: …").

**Leeswijzer:** dit is het gedetailleerde niveau. Voor het hoog-over overzicht (doel/rollen/doorlooptijd/go-no-go per fase), zie `plan_hoogover.md`. Voor de onderliggende techniek, zie `03_technische_documentatie/`. Voor een reeds doorlopen, concreet voorbeeld van een trial-deployment (buiten deze fase-indeling om), zie `Bijlage A` onderaan dit document.

---

## RACI — rollen per fase

| Fase | Klant | Bitmetric — Consultant/Architect | Bitmetric — Data Engineer | Bitmetric — DevOps |
|---|---|---|---|---|
| 1. Intake en beslissessies | **A/R** (beslist) | **R** (faciliteert, legt vast) | C | C |
| 2. Fundament | C (levert toegang) | A | C | **R** |
| 3. FMD-installatie | I | A | **R** | C |
| 4. Eerste bron end-to-end | **R** (valideert data) | A | **R** (registreert) | C |
| 5. Opschalen van bronnen | C (levert bronkennis) | A | **R** | C |
| 6. Gold en semantisch model | **R** (valideert businesslogica) | A | **R** (bouwt) | I |
| 7. CI/CD en productie-inrichting | **A** (productie-akkoord) | A | C | **R** |
| 8. Overdracht en beheer | **R** (neemt over) | **R** (draagt over) | C | C |

*R = Responsible (voert uit), A = Accountable (eindverantwoordelijk), C = Consulted (geraadpleegd), I = Informed (geïnformeerd). Rolnamen zijn indicatief — bij een klein Bitmetric-team kunnen Consultant/Engineer/DevOps dezelfde persoon zijn; dit is dan ook een aanname/sjabloon, geen vastgestelde teamstructuur.*

---

## Risicoregister

| # | Risico | Fase | Kans | Impact | Mitigatie | Bron |
|---|---|---|---|---|---|---|
| R1 | Variable Library wijst na een promotie naar Development (waarden per omgeving als default, of verkeerde actieve value set) | 3, 7 | Laag vanaf fork-commit `81fe912` (ADR-010); *vanaf `FMD_FRAMEWORK#34` controleert de setup de actieve value set per workspace en faalt anders (2026-10-06)*; hoog met een oudere fork | Hoog (Test/Prod leest of schrijft in Dev) | Controle na de setup (fase 3, stap 7) en na elke promotie (fase 7, stap 3) | `11_troubleshooting.md`, `13_referentie-implementatie-bitmetric.md` |
| R2 | Item-ID-verwisseling tussen `VAR_GOLD_CODE_FMD` en `VAR_GOLD_SHORTCUTS_FMD` bij een `updateDefinition`-call | 6, 7 | Middel | Hoog (overschrijft stilzwijgend het verkeerde item) | Dubbelcheck item-ID tegen de juiste library vóór elke call (projectinstructie) | `06_BUSINESS_DOMEINEN/03_shortcuts-en-deployment.md` |
| R3 | Shortcuts in Gold zijn ongeldig na de eerste promotie van DATA naar een omgeving waar Silver nog leeg is (niet getest). *Correctie 2026-09-28 (T-E04): de shortcuts gaan wél mee met de promotie van DATA en wijzen naar Silver van het doel; het oude risico "shortcuts gaan niet mee" vervalt.* | 7 | Laag (alleen bij de eerste uitrol van een omgeving) | Middel (Gold leeg tot herstel, geen dataverlies) | Promoveer DATA na de eerste load (stap 3a), en controleer de shortcuts; terugval: `NB_CREATE_SHORTCUTS` | `03_shortcuts-en-deployment.md` |
| R4 | Cross-workspace Direct-Lake-pointers herbinden niet automatisch bij promotie | 6, 7 | Zeker (elke promotie die SEMANTIC raakt; bevestigd in hertest T-E03) | Middel (Test/Prod-rapporten tonen Dev-data, zonder fout) | Deployment rule (alleen portal, door de modeleigenaar; geen API) of de expressie na elke promotie herschrijven via `updateDefinition`; fase 7, stap 4b | `06_BUSINESS_DOMEINEN/04_semantisch-model-direct-lake.md`, `testplan-trial.md` T-E03 |
| R5 | Eigen, aan een template toegevoegde cross-workspace `InvokePipeline`-aanroep met hardcoded `workspaceId`/`pipelineId` | 5, 6 | Middel (afhankelijk van maatwerk) | Hoog (breekt bij promotie, lastig te diagnosticeren) | Altijd via Variable Library, nooit handmatig ingevulde GUID — zie `Bijlage A`, §3 punt 3 | `Bijlage A` |
| R6 | De setup vraagt een Key Vault met SP-secrets voor `CON_FMD_FABRIC_SQL`; `FabricSql` accepteert geen Workspace Identity (upstream-waarneming) | 2, 3 | Zeker (de setup stopt zonder `key_vault` in het manifest) | Middel (vertraging als dit niet vooraf is voorzien) | In fase 2 de Key Vault, de SP en de leesrechten van de setup-uitvoerder inrichten (B-SECURITY-02); handmatige OAuth2-connectie alleen als bewuste uitzondering | `08_security-en-secrets.md` |
| R7 | Capaciteitscontentie (15-30+ min wachtrij) bij drukte op gedeelde capaciteit | 3, 4, 5, 6 | Middel-hoog, schaalt met aantal parallelle jobs | Laag (vertraging, geen fout) | Geduldig pollen; bij >20-25 min escaleren naar klant/gebruiker; capaciteit-upgrade overwegen bij structurele contentie | `10_operations.md`, `12_kosten-en-capaciteit.md` |
| R8 | Positional-parameter-fout bij handmatige `sp_Upsert*`-aanroepen (waarde belandt in verkeerd parameter; het voorbeeld in de upstream-wiki zet in de fork `LoadGroup = '1'`) | 4, 5 | Middel (menselijke fout bij ad-hoc scripts) | Laag-middel (stille datakwaliteitsfout, geen crash) | Altijd benoemde parameters gebruiken; gebruik het sjabloon in `Bijlage A`, §4 (fix al verwerkt) | `05_INTEGRATION/03_operationele-aandachtspunten.md`, `Bijlage A` |
| R9 | RBAC-discrepantie tussen het interne RBAC-brondocument en de fork-deploymentdocumentatie | 2 | Middel | Middel (onverwacht rechten-probleem bij `NB_BOOTSTRAP_FMD`) | Vroeg in fase 2 expliciet valideren, niet aannemen dat het RBAC-document leidend is | `08_security-en-secrets.md` |
| R10 | Klant kan architectuurbeslissingen niet in één sessie afronden (met name security/netwerk) | 1 | Middel | Middel (planningsvertraging fase 2) | Vroeg plannen, beslissingen met langere doorlooptijd (netwerk/security) als eerste agenderen | `plan_hoogover.md`, fase 1 |
| R11 | Geen intern klantproces voor toekomstige framework-updates (ADR-002-uitzonderingspad vereist handmatige cherry-pick) | 8 | Laag (pas relevant na oplevering) | Laag-middel (technical debt, geen acute impact) | Expliciet bespreken tijdens overdracht of dit voor deze klant relevant is | `01_kennisbasis/architectuur.md` (ADR-002) |
| R12 | Tweede FMD-installatie in dezelfde tenant hergebruikt de bestaande `CON_FMD_*`-connecties, inclusief hun credential. Is dat een Service Principal zonder rechten op de nieuwe workspaces, dan faalt elke `InvokePipeline` in `PL_FMD_LOAD_ALL` met `InsufficientPrivileges` (403) | 2, 3 | Zeker bij een tweede installatie (proef naast productie, herinstallatie); nul bij de eerste | Hoog (geen enkele laag laadt; de setup-run is wel groen) | In fase 2 nagaan of de connecties al bestaan en met welke credential; die identiteit in de groep van `security.admin_group_id` zetten. `service_principal_id` dekt de domein-workspaces niet *(vanaf `FMD_FRAMEWORK#34` wel, CODE en DATA)*, en `contributor_group_id` geen enkele CODE-workspace (fase 3, stap 1) | `11_troubleshooting.md`, `testplan-trial.md` T-C03 |
| R13 | Loads in Test/Prod laden Dev: `Data_WorkspaceGuid` in `PL_FMD_LOAD_ALL`, `PL_FMD_LOAD_LANDINGZONE` en de schedules heeft de Dev-DATA-workspace als default, en een promotie neemt die mee | 7 | Zeker met een fork van vóór PR #20; nul daarna | Hoog (Test/Prod blijft leeg, zonder fout; Dev wordt opnieuw geladen) | Fork vanaf PR #20; na elke promotie de default controleren (fase 7, stap 3) | `11_troubleshooting.md`, `testplan-trial.md` T-E01 |

---

## Fase 1 — Intake en beslissessies

**Voorwaarden:** ingevulde bronnenlijst en globale scope-afbakening van de klant (welke business-domeinen, geschatte datavolumes).

**Exacte acties:**
1. Workshop plannen met klant-stakeholders (functioneel + technisch + security/netwerk-verantwoordelijke indien van toepassing).
2. `02_beslisdocument/04_intake-checklist.md` kopiëren naar een klantspecifieke versie en doorlopen, categorie voor categorie.
3. Voor elke `B-*`-beslissing in `02_beslisdocument/02_beslisregister.md`: Bitmetric-default voorleggen, klant laten kiezen of expliciet afwijken (met onderbouwing vastleggen).
4. Eerste versie van `manifest.yaml` opstellen op basis van de gemaakte keuzes (`repository`, `naming`, `environments[]`, `spark`, `key_vault`, etc.).

**Verificatie:** alle `B-*`-beslissingen hebben een ingevulde "gekozen optie"-kolom; klant heeft het ingevulde beslisregister schriftelijk geaccordeerd (e-mail/documentondertekening).

**Rollback/herstel:** n.v.t. (nog geen technische wijzigingen) — bij onvolledige besluitvorming: fase 1 verlengen, niet doorgaan naar fase 2 met open beslissingen.

**Verwijzing:** `02_beslisdocument/02_beslisregister.md`, `04_intake-checklist.md`.

---

## Fase 2 — Fundament (capacity, security, workspaces)

**Voorwaarden:** fase 1 afgerond en geaccordeerd; klant heeft Azure-tenant-toegang verleend aan het Bitmetric-implementatieteam.

**Exacte acties:**
1. Capaciteit bestellen/toewijzen conform de in fase 1 gekozen SKU (zie `12_kosten-en-capaciteit.md` voor het F2-referentiepunt als indicatie, niet als voorschrift).
2. ~~Workspaces aanmaken conform **B-ARCH-01**: `[DOMEIN] [LAAG] ([OMG])`, voor elk gekozen business-domein × CODE/DATA/SEMANTIC/REPORTING (niet elk domein heeft alle vier) × D/T/(A)/P.~~
   - *Correctie 2026-10-06 (review 3, P3-B3):* de workspaces **niet** met de hand aanmaken. De setup maakt ze aan in fase 3: `NB_SETUP_FMD` de integratie-workspaces, `NB_SETUP_BUSINESS_DOMAINS` die van de domeinen.
   - Leg hier alleen de namen vast, conform **B-ARCH-01**: `[PREFIX] [DOMEIN] [LAAG] ([D|T|A])`. Prod heeft geen suffix.
   - Een workspace die je vooraf met `(P)` aanmaakt, wordt een tweede, lege set naast de echte.
3. **Service Principal voor `CON_FMD_FABRIC_SQL`** (B-SECURITY-02, zie `08_security-en-secrets.md`): SP aanmaken, ~~toegang geven tot de CONFIGURATION-workspace,~~ en tenant-ID, client-ID en secret in Key Vault opslaan.
   - *Correctie 2026-10-06 (P3-B3):* de CONFIGURATION-workspace bestaat in deze fase nog niet. Noteer het **object-ID** van deze SP (Entra ID → Enterprise applications) voor `security.service_principal_id` in het manifest (fase 3 stap 1). De setup maakt de SP daarmee Contributor op CODE, DATA en CONFIG, vóór hij de connectie aanmaakt (vanaf `FMD_FRAMEWORK#37`). De setup haalt die secrets altijd op, ook als je de connectie later met de hand met OAuth2 aanmaakt. Geef degene die de setup draait leesrechten op de secrets.
4. Key Vault inrichten; RBAC toekennen conform **B-SECURITY-01** — expliciet valideren tegen de discrepantie tussen het RBAC-brondocument en de fork-deploymentdocumentatie (zie R9 hierboven) vóórdat fase 3 start.
5. Git-repository aanmaken conform ADR-007/ADR-011 (eigen GitHub-organisatie, één repository per workspace) — tenzij de klant een afwijkende eis heeft (vastleggen als afwijking van de default). *Bijgewerkt 2026-09-30 (geautomatiseerde repo-watch): ADR-008 ("één repo per klant, map per workspace") is per 2026-09-29 Superseded by ADR-011 ("één repo per workspace", commit `574029d`), na een end-to-end test van de ontwikkelflow in FMD_TRIAL (`testplan-devflow.md`, F0–F8) die drie problemen blootlegde met de map-per-workspace-structuur (verwijzingen die na een branch out naar Dev bleven wijzen, een lekkende value set per developer, en `LogicalIdConflictDetected` bij een domeinwissel). Bij meerdere developers hoort bij deze stap ook: repo's per workspace aanmaken volgens het sjabloon `templates/workspace-repo/` (inclusief de `normalize-bindings`-workflow), en `setup/NB_SETUP_DEVELOPER_WORKSPACES.ipynb` (mode `create`) gebruiken om de developer-workspaces van de eerste developer(s) aan te maken. Zie `03_technische_documentatie/09_cicd-en-deployment.md` en `03_technische_documentatie/14_ontwikkelproces.md` voor de volledige uitwerking.*
6. Dev-workspace(s) git-koppelen aan de `dev`-branch (alleen Dev, conform ADR-005). *Correctie 2026-10-06 (P3-B3): dat kan pas na fase 3, als de setup de workspaces heeft aangemaakt. Hier alleen de repository's klaarzetten.*
7. **Verificatiestap (G2, B-ARCH-03):** controleer dat de GUID-guard-CI-check (`.github/workflows/guid-guard.yml`, `scripts/guid_guard.py`) actief staat in de ~~klantrepo~~ **klantfork** van `FMD_FRAMEWORK` *(correctie 2026-10-06, review 3 P3-V9: de guard scant `src/`, en die map staat alleen in de fork, niet in de repo's per workspace van ADR-011)* — deze bewaakt dat de generieke laag vrij blijft van klant-/omgevingsspecifieke GUID's (ADR-003/009). Een ontbrekende of uitgeschakelde guard is geen harde blokkade voor deze fase, maar wel een risico dat vóór fase 7 (productie-promotie) hersteld moet zijn.
8. **Bestaande connecties in de tenant (R12).** Connectienamen zijn tenant-breed en krijgen geen `framework_pre_fix`. Vindt de setup al een `CON_FMD_FABRIC_PIPELINES`, `CON_FMD_FABRIC_SQL` of `CON_FMD_FABRIC_NOTEBOOKS`, dan hergebruikt hij die zonder melding, met de credential die eraan hangt. In een schone tenant maakt de setup ze zelf aan, met Workspace Identity; dan is deze stap klaar. *(Aanvulling 2026-10-06: `CON_FMD_FABRIC_SQL` met de SP uit stap 3, niet met Workspace Identity. Een installatie in een schone tenant is niet getest; zie fase 3 stap 4.)* Bestaan ze al (een tweede installatie, of een proef naast productie), controleer dan het credentialtype:
   ```
   GET https://api.fabric.microsoft.com/v1/connections   → displayName CON_FMD_*, credentialDetails.credentialType
   ```
   Is het `ServicePrincipal`, zoek dan het object-ID van die SP op (Entra ID → Enterprise applications) en neem het op in fase 3, stap 1.

**Verificatie:** ~~elke workspace bestaat met de exacte naam conform B-ARCH-01;~~ de workspacenamen conform B-ARCH-01 en het object-ID van de SP staan klaar voor het manifest *(correctie 2026-10-06, P3-B3: de workspaces maakt de setup in fase 3)*; een testnotebook kan een secret uit Key Vault ophalen; `git status` in de Dev-workspace toont een succesvolle koppeling aan `dev`; de GUID-guard-workflow is zichtbaar en actief in de repository-Actions-tab.

**Rollback/herstel:** workspace-naam fout → workspace hernoemen (geen dataverlies, want nog leeg in deze fase); git-koppeling mislukt → koppeling verwijderen en opnieuw uitvoeren (geen destructieve impact zolang de workspace nog leeg is).

**Verwijzing:** `08_security-en-secrets.md`, `09_cicd-en-deployment.md`, `06_BUSINESS_DOMEINEN/01_workspace-structuur.md`, besluiten B-ARCH-01, B-SECURITY-01, B-SECURITY-02.

---

## Fase 3 — FMD-installatie

**Voorwaarden:** fase 2 volledig afgerond en geverifieerd (met name: Key Vault-toegang werkt, git-koppeling staat).

**Exacte acties:**
1. `manifest.yaml` in de klantfork invullen met alle keuzes uit fase 1 en 2: namen, `environments[]`, capaciteiten, `spark`, `key_vault` inclusief de drie `sql_sp_*`-secrets, `shortcuts`, `naming.business_domains`. ~~In de setup-notebooks wordt niets meer in cellen geconfigureerd.~~ *(Correctie 2026-10-06, P3-V4: op vier instellingen in cel 5 na, zie stap 3, en `dry_run`.)*
   - **`security`: let op welke rol waar terechtkomt.** De CODE-workspaces, waar alle pipelines draaien, krijgen alleen `admin_group_id` (Admin) en `service_principal_id` (Contributor). `contributor_group_id` komt alleen op DATA en CONFIG *(2026-10-07, vastgesteld in `NB_SETUP_FMD` cel 15 en `NB_SETUP_BUSINESS_DOMAINS` cel 17 op `main`: alleen op INTEGRATION DATA en CONFIG. De workspaces van een domein krijgen `admin_group_id` (Admin), en CODE en DATA daarnaast `service_principal_id` (Contributor); REPORTING alleen de admingroep)*. Een identiteit die pipelines moet kunnen aanroepen, zoals de SP achter een hergebruikte `CON_FMD_FABRIC_PIPELINES` (fase 2, stap 8), hoort dus in de admingroep. Alleen in `contributor_group_id` is niet genoeg.
     - ~~`service_principal_id` dekt alleen de integratie-workspaces. `NB_SETUP_BUSINESS_DOMAINS` kent op de domein-workspaces alleen `admin_group_id` toe, terwijl `PL_FMD_ORCHESTRATION_TEMPLATE` daar de Gold-pipelines aanroept. Met alleen `service_principal_id` faalt Gold in de orchestratie dus alsnog met een 403.~~
     - ~~In de hertest is de SP daarom met de hand op alle 31 workspaces gezet (`testplan-trial.md` T-C03).~~
     - *Correctie 2026-10-06 (review 3 P3-V3, `FMD_FRAMEWORK#34`):* vanaf #34 krijgt `service_principal_id` ook Contributor op CODE en DATA van elk domein (*getest in eigen omgeving*, rookproef 2 stap 4). Het handwerk hierboven is alleen nodig in een fork van vóór #34.
   - ~~Alle ID's op nullen laten kan alleen als de connecties door deze setup vers worden aangemaakt.~~ Anders faalt de eerste load met `InsufficientPrivileges` (R12).
     - *Correctie 2026-10-08 (eindcontrole E-R6; vastgesteld in `NB_SETUP_FMD` op `main`, zie ook `08_security-en-secrets.md`):*
       - `service_principal_id` is verplicht zodra de setup `CON_FMD_FABRIC_SQL` zelf aanmaakt. De setup test die connectie, en de SP krijgt alleen via dit ID toegang tot CONFIG. Staat het op nullen, dan stopt de setup na de workspaces (vanaf #37).
       - De dry-run waarschuwt daar niet voor. Controleer het dus zelf. *(Bijgewerkt 2026-10-11: vanaf `FMD_FRAMEWORK#53` meldt de dry-run een lege of nul-`service_principal_id` wel.)*
       - *Aanvulling 2026-10-12 (generale repetitie GR-A3, getest in eigen omgeving):* **`service_principal_id` moet het object-ID zijn van de SP waarvan de secrets in `key_vault.secrets.sql_sp_*` staan.**
         - De setup maakt de connecties met die secrets, en geeft alleen `service_principal_id` workspacerechten.
         - Zijn het twee verschillende SP's, dan was de dry-run toch groen, en faalde de echte run na de workspaces met `MashupDataAccessError` (`11_troubleshooting.md`).
         - Controle: de app-ID (client-ID) van de secrets staat in Entra ID → Enterprise applications naast het object-ID. Vanaf `FMD_FRAMEWORK#59` (open) controleren de dry-run en de setup dit zelf.
       - Alleen de groeps-ID's mogen op nullen, met het risico uit R12.
   - **`fabric_domains.create`** (*toegevoegd 2026-10-06*, review 3 P3-R4, `FMD_FRAMEWORK#41`): standaard `false`. Alleen als de klant in de intake (2.4) voor Fabric-domeinen kiest, zet je hem op `true`.
     - Met `true` maken de setups tenant-brede Fabric-domeinen aan (`naming.domain_name`, en per business domain één), en hangen ze de workspaces eraan. Van een bestaand domein met dezelfde naam overschrijven ze de beschrijving en de contributors.
     - Dan moet de setup gedraaid worden door iemand met de rol Fabric Administrator. De dry-run (stap 3a) controleert dat.
     - Vóór #41 stond dit vast op `true` in een cel van beide setup-notebooks. Zet het daar op `False` als de klant het niet wil.
   - **`reassign_capacity`** (*toegevoegd 2026-10-08*, eindcontrole E-V3/P3-R4; *vastgesteld* in `NB_SETUP_FMD` cel 9 en in `NB_SETUP_BUSINESS_DOMAINS`): staat in beide setups op `True`. Een bestaande workspace met de naam uit het manifest wordt dus naar de capaciteit uit het manifest verhuisd.
     - De dry-run zet bij zo'n workspace "wordt omgezet" achter de capaciteit. Controleer dat bij een setup in een bestaande tenant.
     - Moet een workspace op zijn eigen capaciteit blijven, zet deze cel dan op `False`.
2. `NB_BOOTSTRAP_FMD.ipynb` **handmatig importeren** in een tijdelijke scaffolding-workspace. Dat is het enige handmatige import. De Dev-CODE-workspace bestaat op dit moment nog niet; die maakt de setup aan.
3. Bootstrap-notebook draaien. Dat plaatst `NB_SETUP_FMD.ipynb` en `NB_SETUP_BUSINESS_DOMAINS.ipynb` met de repoconfiguratie al ingevuld. Een eerdere versie wordt overschreven.
   - Is de klantfork privé (zie intake 2.11)? Vul in de bootstrap-cel dan ook `github_token_key_vault` en `github_token_secret` in (Key Vault-naam en secretnaam van een GitHub PAT met leesrechten op de fork, vanaf fork-commit `757d5c`, PR #12). Leeg laten bij een publieke fork; zonder token faalt de bootstrap-run bij een privé-fork op een 404 op het manifest. Zie `09_cicd-en-deployment.md` §Privé-fork.
   - *Correctie 2026-10-05 (vastgesteld, `NB_SETUP_FMD.ipynb` cel 5):* vier instellingen staan nog wél in een cel en niet in het manifest: `load_demo_data`, `assign_icons`, `overwrite_variable_library` en `driver`. **Zet bij een klant `load_demo_data = False`** (default `True`), anders krijgt ~~elke omgeving de demo-entiteit `in.customer` met tabel~~ de installatie de demo-entiteit `in.customer` *(correctie 2026-10-06, P3-V4, vastgesteld in `NB_SETUP_FMD` op `main`: de entiteit wordt één keer geregistreerd, op de eerste `LH_DATA_LANDINGZONE` (`SELECT top 1`); de demotabel komt in elke omgeving)*.
3a. **Eerst een dry-run** (vanaf PR #36): zet `dry_run = True` in cel 5 van `NB_SETUP_FMD` en draai het notebook. Er wordt niets aangemaakt. *Getest in eigen omgeving* (2026-10-06, jobs `93d6ebbb` en `281e77ee`, `testplan-trial.md` T-A10).
   - De output toont het domein, de connecties en elke workspace met naam, capaciteit en rollen. Per item staat erbij of het wordt aangemaakt, overschreven of blijft staan. Ook de deployment pipelines en de koppeling per stage staan erin. Bespreek dit plan met de klant: dit zijn de namen die blijven.
   - Problemen maken de run rood: een capaciteit die niet bestaat, waar je geen rechten op hebt of die niet Active is; een ontbrekende bron of dacpac; geen Fabric Admin bij ~~`create_domains = True`~~ `fabric_domains.create: true` *(correctie 2026-10-08, E-V3: vanaf #41 staat dit in het manifest)*; een stage of workspace die al aan een andere pipeline hangt. Los ze op en draai de dry-run opnieuw tot hij groen is.
   - Waarschuwingen (de run blijft groen): groeps-ID's op nullen (zie stap 1, R12), en `CON_FMD_ADF_PIPELINES` ontbreekt. Die laatste maakt de setup niet aan; maak hem handmatig als de klant ADF gebruikt.
   - Niet gedekt: een workspacenaam die al bestaat in een workspace waar jij geen toegang toe hebt, en of de groeps-ID's echt bestaan in Entra (*aanname*: alleen via Microsoft Graph te controleren). Die fouten zie je pas bij stap 4.
   - Zet daarna `dry_run = False`.
4. `NB_SETUP_FMD.ipynb` draaien (Python-kernel, geen Spark). Faalt de registratie in de configdb (connecties, workspaces, pipelines, lakehouses) of de demotabel, dan faalt de laatste cel met `Setup finished with N failed task(s)` (vanaf PR #31). Daarvoor eindigde de setup groen en stond de fout alleen in de takenlijst. Dan na herstel de setup opnieuw draaien.
   - *Aanvulling 2026-10-06 (`FMD_FRAMEWORK#37`, gemerged `636d561`):* de setup maakt de connecties pas na de workspaces. Ontbreekt er daarna een (`CON_FMD_FABRIC_PIPELINES`, `_NOTEBOOKS` of `_SQL`), dan stopt hij met `Connection … is not available` (`11_troubleshooting.md`); de ADF-connectie is optioneel.
   - Getest met een ongeldig secret (*getest in eigen omgeving*, rookproef 2 stap 15). Een echte schone tenant, met een SP die nog nergens lid van is, is niet getest.
   - *Aanvulling 2026-10-06 (`FMD_FRAMEWORK#39`, gemerged `9044f1a`):* ook een mislukte item-import (notebook, pipeline, Variable Library, environment) laat de laatste cel falen, met status `failed: x import: …` per item en omgeving. Dat geldt ook in `NB_SETUP_BUSINESS_DOMAINS` (met #38).
     - Een mislukte import van de configuratiedatabase stopt de setup direct.
     - Vóór #39 eindigde de setup dan groen, en bleef in die omgeving de oude versie van het item staan.
     - *Getest in eigen omgeving* (rookproef 2 stap 16): een ongeldige pipeline gaf 3 gefaalde taken (D/T/P) en verder geen. De normale runs bleven groen.
   - *Toegevoegd 2026-10-12 (`FMD_FRAMEWORK#58`, vastgesteld):* **draai je de setup op een bestaande installatie met de oude namen, hernoem dan eerst de bestaande items**, in elke stage (D, T, P) en in de workspace zelf: `PL_FMD_ORCHESTRATION_TEMPLATE` naar `PL_FMD_ORCHESTRATION` (INTEGRATION CODE) en `PL_FMD_LOAD_GOLD_TEMPLATE` naar `PL_FMD_LOAD_GOLD` (CODE van elk domein). De setup zoekt items op naam. Zonder hernoemen maakt hij nieuwe items naast de oude, en blijft `PL_FMD_SCHEDULE_<short>` de oude orchestratie aanroepen, want die verwijst op ID. Zie `10_operations.md`, *De setup opnieuw draaien als update*.

   Het maakt aan:
   - de workspaces per omgeving;
   - de drie connecties (`CON_FMD_FABRIC_SQL` via de SP uit Key Vault);
   - de configuratiedatabase (`integration`/`execution`/`logging`);
   - de drie lakehouses (`LH_DATA_LANDINGZONE`, `LH_BRONZE_LAYER`, `LH_SILVER_LAYER`);
   - de items en de Variable Libraries;
   - als laatste de Deployment Pipelines, inclusief stagekoppeling. Fabric koppelt de items van twee stages op naam op het moment dat een workspace aan een stage wordt gekoppeld. Een item dat daarna ontstaat, blijft ongekoppeld en de eerste promotie faalt met `TargetArtifactNameConflict` (getest op 2026-09-25). Vanaf fork-commit `81fe912` komt de koppeling daarom na de items.
5. `NB_SETUP_BUSINESS_DOMAINS.ipynb` **één keer** draaien. Het verwerkt alle domeinen uit `naming.business_domains`.
   - **Eerst een dry-run** (vanaf PR #38), net als in stap 3a: `dry_run = True` in cel 5. *Getest in eigen omgeving* (2026-10-06, jobs `34673169` en `3550d9f6`, `testplan-trial.md` T-A11).
     - Het plan toont per domein en omgeving de vier workspaces (CODE, DATA, REPORTING, SEMANTIC) met hun items, de vier deployment pipelines per domein, en het aanhaken van `PL_<DOMEIN>_LOAD_GOLD` aan `PL_FMD_ORCHESTRATION`.
     - De dry-run controleert ook wat stap 4 moet hebben neergezet: de configdb, en per omgeving `LH_SILVER_LAYER` en `PL_FMD_ORCHESTRATION`. Ontbreekt er iets, dan wordt de dry-run rood.
     - Let op de regels "wordt overschreven" bij `NB_LOAD_GOLD`, `NB_MLV_EXAMPLE` en `NB_CREATE_SHORTCUTS`. Bij een herhaalde run staat daar klantcode in, die verloren gaat, ook in T en P (review 3, P3-R1; ~~fix volgt~~ *opgelost in #47, zie hierna*). *Bijgewerkt 2026-10-08 (`FMD_FRAMEWORK#47`, gemerged `5ec7b3c`):* vanaf #47 blijven deze drie notebooks staan, en meldt de dry-run "bestaat, blijft staan". ~~`PL_FMD_LOAD_GOLD_TEMPLATE` wordt nog wel overschreven: zet daar geen klantcode in, maar in de notebooks of in een eigen pipeline.~~ *Correctie 2026-10-12 (`FMD_FRAMEWORK#58`, vastgesteld in `NB_UTILITIES_SETUP_FMD`, `CUSTOMER_OWNED_ITEMS`):* ook `PL_FMD_LOAD_GOLD` blijft staan. De setup maakt hem één keer per stage (D/T/P) aan en overschrijft hem daarna niet; zie fase 6 stap 1.
   - Vanaf PR #38 eindigt dit notebook rood als het aanhaken aan de orchestratie mislukt of als de registratie in de configdb faalt (review 3, P3-R2). Daarvoor bleef het groen, terwijl Gold in die omgeving nooit draaide.
6. **Verificatiestap (G5, geleerde les):** controleer dat het lokaal/handmatig gebruikte setup-notebook (met name `NB_SETUP_BUSINESS_DOMAINS.ipynb`) overeenkomt met de main-branch-versie van de fork, vóórdat het wordt gedraaid — een eerder geconstateerd versieverschil tussen een lokale en de live main-branch-versie leidde tot een onbedoelde security-praktijkkeuze (zie `08_security-en-secrets.md`). Een `git diff` tegen de main-branch van de fork volstaat.
7. Variable Libraries controleren. De setup maakt ze in elke CODE-workspace aan met dezelfde definitie. Waarden die per omgeving verschillen (`VAR_CONFIG_FMD`: DATA-workspace en landingzone; `VAR_GOLD_SHORTCUTS_FMD`: Gold- en Silver-lakehouse), staan als override in de value set van die omgeving, en elke workspace activeert zijn eigen value set (`set_variable_library_stage_values`, ADR-010). Controleer per CODE-workspace:
   - de actieve value set is die van de eigen omgeving (`GET …/variableLibraries/{id}`, veld `properties.activeValueSetName`);
   - de GUID's in die value set wijzen naar items in díe omgeving, ~~en geen override is leeg. Een lege override betekent dat de setup het item niet vond; de celoutput heeft dan een `❌`-regel.~~ *(correctie 2026-10-06, P3-V8)* en de waarde die in de actieve value set **geldt**, is niet leeg. In de eerste omgeving (Dev) staan de waarden by design in de defaults, zonder override (`stage_value_overrides`). Lees dus de geldende waarde, niet alleen de overrides.
   - *Aanvulling 2026-10-06 (P3-V3, `FMD_FRAMEWORK#34`):* vanaf #34 controleert de setup dit zelf per workspace, tot 3 pogingen, en faalt anders. Deze controle is dan een dubbelcheck; in een oudere fork is hij nodig (rookproef 2 stap 4: een groene setup met de verkeerde value set in Prod). `key_vault_uri_name` bevat na de setup de placeholder `val_key_vault_uri_name` (hardcoded in `NB_SETUP_FMD`); vul die zo nodig handmatig.

**Verificatie:**
- De drie lakehouses bestaan met de exacte, verplichte namen.
- `sp_GetConnection`/`sp_GetDataSource` geven geen fouten tegen een lege configdb.
- In de `tasks`-tabel die de setup-notebooks aan het eind tonen, staat geen regel met "failed" (onder meer `custom_sql_deployment` rapporteert daar; vanaf #39 ook de item-imports). Vanaf PR #38 staat daar per domein en omgeving ook een regel `Wire PL_<DOMEIN>_LOAD_GOLD into …`, met de status `success` of `already wired`.
- Ook de celoutput is doorgelezen op `❌`-regels. Fouten bij het aanmaken of koppelen van Deployment Pipelines worden alleen geprint, en de run blijft groen. Dat geldt ook voor de melding "item(s) in stage '…' are not paired": na het koppelen controleert de setup of items met dezelfde naam en hetzelfde type in twee opeenvolgende stages gekoppeld zijn (`report_unpaired_items`). Zie fase 7, stap 1 voor het herstel.

**Rollback/herstel:** bij een mislukte notebook-run: eerst Livy-sessiestatus checken (zie `10_operations.md`) — vaak volstaat een nieuwe sessie en herstart van de cel; bij een corrupte configdb-deploy: schema's droppen en de setup-notebooks opnieuw draaien (in deze fase nog geen productiedata, dus veilig).

**Verwijzing:** `05_INTEGRATION/01_ddl-spec.md`, `00_architectuur-overzicht.md`, besluit B-INFRA-01.

**Risico:** capaciteitscontentie kan deze fase vertragen (R7) — geen technisch probleem.

---

## Fase 4 — Eerste bron end-to-end (proof-of-value)

**Voorwaarden:** fase 3 afgerond; minstens één bron uit de intake geselecteerd als eerste, representatieve testcase (bij voorkeur een eenvoudige, goed gedocumenteerde bron).

**Exacte acties:**
*Bijgewerkt 2026-10-06 (review 3, P3-V7):* de standaard voor stap 1–3 is het lijstsjabloon (§A.4a), met de connectiestap daarin. De stappen hieronder beschrijven wat het sjabloon doet, en de route met losse aanroepen (§A.4). Meng de twee niet per omgeving. *(Bijgewerkt 2026-10-15, `FMD_FRAMEWORK#71`: het lijstsjabloon is vervangen door `NB_REGISTRATIE` met `integration.sp_RegisterEntities` (ADR-018, `02_configdb-registratie.md` Route 3). De stappen beschrijven nu wat die procedure doet.)*
1. Connectie registreren: `EXEC integration.sp_UpsertConnection` met als `@ConnectionGuid` het **ID van de bestaande Fabric-connectie** naar de bron. De copy-pipelines gebruiken die GUID als connectie; een verzonnen GUID faalt bij elke load. Zie Bijlage A, §A.4 voor het sjabloon, inclusief de controle op toegestane `ConnectionType`/`DataSourceType`-combinaties. ~~— **of**, bij een hele Azure SQL-bron met meerdere tabellen, bulkregistratie via `PL_TOOLING_POST_ASQL_TO_FMD` (parameters: `ConnectionGuid`, `DatasourceName`, `DatasourceNamespace`, `DatasourceType`, `Tables`).~~ *(Correctie 2026-10-15, `FMD_FRAMEWORK#71`. Reden: de setup rolt `PL_TOOLING_POST_ASQL_TO_FMD` niet meer uit. Voor een bron met veel tabellen: `PL_FMD_DISCOVER_SOURCE` en daarna `NB_REGISTRATIE`.)*
   - Vanaf PR #14 stopt de bulkregistratie vooraf als een object geen afleidbare PK heeft, of niet bestaat. Registreer zo'n object met het sjabloon, met expliciete `PrimaryKeys`.
   - Vanaf PR #16 voegt de bulkregistratie alleen toe; bestaande registraties blijven ongemoeid. In een oudere fork overschrijft een herhaalde run `IsIncremental`, `LoadGroup` en `IsActive`. Zet daar in `Tables` dus alleen nieuwe objecten.
2. DataSource registreren: `EXEC integration.sp_UpsertDataSource` — **altijd met benoemde parameters** (zie R8: positional-parameter-risico).
3. Landingzone/Bronze/Silver registreren: `EXEC integration.sp_UpsertLandingzoneBronzeSilver` (vereist dat Workspace + de drie lakehouses al geregistreerd staan, zie fase 3).
4. `PL_FMD_LOAD_ALL` draaien voor een **full load**.
5. Een tweede run draaien om het **incrementele** pad te valideren (watermark-mechanisme, `execution.LandingzoneEntityLastLoadValue`).
   - Een run zonder bronwijziging moet 0 rijen kopiëren.
   - Silver mag daarbij geen rijen als verwijderd markeren (`IsDeleted = 0`): Bronze slaat bij `IsIncremental = 1` de delete-stap over.
   - Kun je niet in de bron schrijven, zet dan `LoadValue` terug naar een eerdere waarde om "nieuwe" rijen na te bootsen (hertest T-D01).
6. Silver-tabel laten controleren door de klant (inhoudelijke validatie, geen technische check).

**Verificatie:** `SELECT COUNT(*) FROM <namespace>.<Schema>_<Tabel>` op het SQL-endpoint van `LH_SILVER_LAYER` komt overeen met de bronomvang (na een load eerst `POST …/sqlEndpoints/{id}/refreshMetadata`, anders geeft het endpoint `Invalid object name`); een tweede (incrementele) run verwerkt alleen de gewijzigde/nieuwe rijen, niet de volledige set opnieuw; klant bevestigt schriftelijk dat de Silver-data correct is.

**Rollback/herstel:** foutieve registratie → `UPDATE integration.LandingzoneEntity/BronzeLayerEntity/SilverLayerEntity SET IsActive = 0` op de betreffende entiteit (nooit DELETE, conform **B-INFRA-02**) en opnieuw registreren. Met een gecorrigeerde naam ontstaat een nieuwe entiteit en blijft de foutieve inactief. Registreer je met dezelfde `SourceSchema`/`SourceName`, dan blijft de entiteit inactief vanaf dacpac `4dd41cf` (PR #8); op een configdb met een oudere dacpac wordt hij weer actief; foutieve data in Silver → bron deactiveren, brondata/mapping corrigeren, heractiveren en opnieuw laden.

**Verwijzing:** `05_INTEGRATION/02_configdb-registratie.md`, `10_operations.md` (watermark-contract), besluiten B-INFRA-01, B-INFRA-02.

**Go/no-go:** dit is het eerste formele go/no-go-moment (zie `plan_hoogover.md`, fase 4) — bij "no-go" wordt deze fase herhaald, niet fase 5 gestart.

---

## Fase 5 — Opschalen van bronnen

**Voorwaarden:** fase 4 heeft een expliciet "go" opgeleverd.

**Exacte acties:**
1. Voor elke resterende, in de intake afgesproken bron: dezelfde registratieroute als fase 4 (handmatig of bulk, afhankelijk van bronomvang).
   - In een fork van vóór PR #17: gebruik per connectietype één `DataSource.Type`. Met `ASQL_01` én `ASQL_02` onder `SQL`, of met een ongeldig type naast een geldig, draait de copy-child parallel dubbel, en faalt de run soms op `LakehouseOperationFailedConcurrentWrite` (hertest T-C08).
2. **Alleen bij een bron die niet via de standaard-copy-activity kan lopen (API zonder connector e.d.):** `CustomNotebookName`-mechanisme toepassen, met `Connection.Type` én `DataSource.Type` op `'NOTEBOOK'`. Zie `07_extension-points.md` §2 voor het contract (`LastLoadValue`/`LoadValue` via `notebookutils.notebook.exit`), de beperking dat het custom notebook in dezelfde CODE-workspace moet staan, en twee valkuilen: de template zet de watermark op de klok, en een deel van de fouten wordt geslikt.
2a. **Alleen bij Snowflake als bron** (vanaf een fork met `FMD_FRAMEWORK#40`, ADR-014). Snowflake schrijft de landing zone zelf; eenmalig per klant:
   - **Snowflake** (`ACCOUNTADMIN`, script `templates/snowflake/servicegebruiker.sql`):
     - rol `FMD_READER` met alleen `USAGE`/`SELECT`, en servicegebruiker `SVC_FMD` (`TYPE = SERVICE`) met een sleutelpaar **zonder** wachtwoordzin;
     - storage integration `FMD_ONELAKE` met per DATA-workspace (D, T, P) de locatie `azure://onelake.blob.fabric.microsoft.com/<DATA-workspace-ID>/<ID van LH_DATA_LANDINGZONE>/Files/`, en `GRANT USAGE ON INTEGRATION` aan de rol.
   - **Entra:** `AZURE_CONSENT_URL` uit `DESC STORAGE INTEGRATION` openen en toestemming geven (een beheerder). In Entra heet de app zoals `AZURE_MULTI_TENANT_APP_NAME`, het deel vóór de underscore.
   - **Fabric:** die app **Contributor** op elke DATA-workspace. Connectie van het type Snowflake met KeyPair, de private sleutel als Key Vault-referentie; registreren met `sp_UpsertConnection … @Type = 'SNOWFLAKE'`.
   - **Registratie:** `DataSource.Type = 'SNOWFLAKE_01'`, `DataSource.Name` = de Snowflake-database, `SourceSchema`/`SourceName` exact zoals in Snowflake (meestal HOOFDLETTERS), `FileType = 'parquet'`, watermarkkolom `DATE` of `TIMESTAMP`.
     - *Aanvulling 2026-10-26:* heeft een tabel een `TIME`-kolom, dan laadt die niet naar Delta. Registreer hem met een cast in `SourceColumns` (`TIJD::VARCHAR`); zit hij in de key, controleer vooraf dat er geen fracties van een seconde in zitten (`11_troubleshooting.md`). *Getest in eigen omgeving* 2026-10-26 in FMD_TRIAL D (testtabel, runs `bbd8091b` en `7d51748b`).
   - Een andere naam voor de integration: `VAR_FMD.snowflake_storage_integration`.
     - *Aanvulling 2026-10-12 (`FMD_FRAMEWORK#48`, `f7df241`; draft van de repo-watch verwerkt):* een setup-run als update vervangt de variabelen van `VAR_FMD` niet meer als geheel. Een variabele die alleen in `variables.json` staat, zoals `snowflake_storage_integration`, blijft dus bestaan (*vastgesteld in code*). Vóór #48 verving de setup de hele lijst. *Getest in eigen omgeving:* verse installatie FMD_SMOKE3, `NB_SETUP_FMD` `937418e3` (2026-10-08), `VAR_FMD` 5/5 in D/T/P. Dat de waarde van een bestaande variabele een update-run overleeft, is niet apart getest.
   - **Status:** *getest in eigen omgeving* 2026-10-06/07 in Dev (`testplan-trial.md` T-F01 t/m T-F05). ~~De locaties voor T en P en het gedrag na een promotie zijn niet getest (*aanname*: de pipeline gebruikt de lakehouse-ID uit de configdb van die omgeving).~~
     - *Correctie 2026-10-07 (T-F06):* *getest in eigen omgeving* in T en P. Eén storage integration met de drie locaties werkt; na een selectieve promotie D → T → P wijzen de pipelines naar de eigen omgeving, en de data landt in de landingszone van die omgeving. Registreer per omgeving apart (lijstsjabloon), en maak de Snowflake-app Contributor op elke DATA-workspace.
2b. **Snowflake zonder storage integration** (de Delta-variant, `FMD_FRAMEWORK` branch `feature/snowflake-delta-landing` (PR volgt), ADR-014 aanvulling 2026-10-13). Gebruik dit als de klant geen storage integration kan of wil maken (het vraagt `ACCOUNTADMIN` en een Entra-beheerder), bijvoorbeeld bij alleen leesrechten in Snowflake.
   - **Inrichting:** alleen een leesgebruiker met sleutelpaar en de Fabric-connectie (stap 2a, regels *Fabric* en *Connectie*). Geen storage integration, geen Entra-toestemming, geen extra rol op de DATA-workspaces. De klant zet de publieke sleutel op de gebruiker (`ALTER USER … SET RSA_PUBLIC_KEY`); de private sleutel gaat alleen in Key Vault.
   - **Registratie:** per entiteit `FileType = 'delta'` (kleine letters) in plaats van `'parquet'`. Beide mogen in één bron door elkaar. `FileName` en de namespace alleen letters, cijfers en `_`.
   - **Kosten en trager (*getest in eigen omgeving* 2026-10-13):** 1,5 miljoen rijen in 85 tot 99 s, 0,27 DIU-uur *DataMovement* per activiteit, tegen 5 s met `COPY INTO`. Voor grote tabellen is dat een veelvoud (*aanname*). Gebruik `delta` alleen voor wat niet anders kan.
   - **Landing zone:** een Delta-tabel per run in `Tables/ldz` van `LH_DATA_LANDINGZONE`; het onderhoud (ADR-015) ruimt die op met dezelfde bewaartermijn.
   - **Niet getest:** een lakehouse zonder schema's, en de accountparameters `PREVENT_UNLOAD_TO_INLINE_URL` en `REQUIRE_STORAGE_INTEGRATION_FOR_STAGE_OPERATION` (laat de klant dat bevestigen).
   - **Status:** *getest in eigen omgeving* 2026-10-13 in FMD_GR Dev (runs `d82cfa7e`, `842361de`, `14beddb3`) en FMD_TRIAL Dev (`267c6701`, `0465c3a8`, `ccc01d32`, `f49c5fcb`, `8ebc3757`; opruimen `559f7d3c`, `8a52407e`); `generale-repetitie.md`. Ook getest: een incrementele delta-run met echte bronwijzigingen (`88fd6954`) en het openen van de pipeline in de editor.
3. **Alleen bij een bron waarvan maar een deel geladen mag worden (filter, join, kolomselectie):** een view in de bron registreren als `SourceName`, of een custom notebook gebruiken. **Niet** `SourceCustomSelect`: die kolom wordt niet gelezen, en de volledige tabel wordt geladen (`07_extension-points.md` §3).
4. Scheduling inrichten. ~~`PL_FMD_SCHEDULE_NIGHTLY`/`PL_FMD_SCHEDULE_INTRADAY`, eventueel met `LoadGroup`-indeling voor gedifferentieerde scheduling per brongroep.~~
   - *Correctie 2026-10-06 (review 3, P3-B1/B2; `FMD_FRAMEWORK#35`):* plan **`PL_FMD_ORCHESTRATION_TEMPLATE`** in INTEGRATION CODE, met één schema per cadans. Elk schema geeft zijn eigen parameter `LoadGroup` mee.
     - **Nachtelijk:** zonder `LoadGroup`. Dat laadt alle bronnen, ook die zonder groep.
     - **Vaker per dag, alleen als de intake dat vraagt:** met `LoadGroup = INTRADAY`, en die groep op de bronnen in de lijst (§A.4a).
     - Na elke run draait Gold van alle domeinen. `concurrency: 1` laat een overlappende run wachten.
     - **Waarom niet `PL_FMD_SCHEDULE_*`:** die roepen alleen `PL_FMD_LOAD_ALL` aan, dus Gold draait niet mee. `PL_FMD_SCHEDULE_NIGHTLY` geeft bovendien `NIGHTLY` mee, en slaat daardoor elke bron zonder groep stil over.
     - Vereist een fork met #35 (gemerged 2026-10-06, `3a2a3c1`). Zonder #35 heeft de orchestratie geen `LoadGroup`-parameter: plan haar dan zonder parameter, dus alleen nachtelijk.
     - *Getest in eigen omgeving 2026-10-06* (rookproef 2, stap 14): twee schema's op dezelfde minuut. Het schema zonder groep laadde alles plus Gold. Het schema met `INTRADAY` wachtte tot de eerste run klaar was, laadde niets (geen INTRADAY-bronnen) en draaide Gold. De promotie T → P nam de parameter, de schema's en de Gold-verwijzing goed mee.
   - **Melding bij een gefaalde run (B-MON-01), per omgeving met een schema:** open de ~~schedule-pipeline~~ *(2026-10-06: `PL_FMD_ORCHESTRATION_TEMPLATE`)* in INTEGRATION CODE van die omgeving, kies **Home → Schedule**, en voeg onder **Failure notifications** de ontvangers uit de intake toe (bij voorkeur een groep of distributielijst, geen persoon). De melding kan alleen in de portal. De REST API voor schema's kent er geen veld voor. ~~Een promotie zet het schema niet mee (*aanname*), dus doe dit per omgeving.~~
     - *Correctie 2026-10-06 (rookproef 2, stap 9b):*
       - **Een promotie neemt het schema wél mee, maar de ontvangers niet** (*getest in eigen omgeving*). Na een promotie van INTEGRATION CODE T → P stond in P een nieuw, ingeschakeld schema met hetzelfde tijdstip. Onder *Failure notifications* stond niemand.
       - Prod draait dus na de eerste promotie al op het tijdstip van Test, en zonder melding.
       - Daarom: na **elke** promotie van INTEGRATION CODE, in de doelomgeving, het tijdstip controleren en de ontvangers opnieuw toevoegen. Moet een omgeving niet gepland draaien, zet het schema daar dan uit.
   - **Onderhoud** (vanaf een fork met `FMD_FRAMEWORK#42`, ADR-015): plan ook **`PL_FMD_MAINTENANCE`** in INTEGRATION CODE, per omgeving, bijvoorbeeld wekelijks buiten het laadvenster. Het ruimt verwerkte leveringen in de landing zone op die ouder zijn dan `VAR_FMD.landingzone_retention_days` (standaard 30; de klant kiest de termijn, ook vanwege de AVG), en draait `VACUUM` op Bronze en Silver. Zet ook hier *Failure notifications*. Zonder schema groeit de opslag zonder grens (`15_opslagbeheer.md`). *Getest in eigen omgeving* 2026-10-07 (`testplan-trial.md` T-D09).
   - **Correctie 2026-10-11 (ontwerp `FMD_FRAMEWORK#52`, ADR-017; geldt vanaf een fork met #52, gemerged 2026-10-11, `4971d88`):** zet de schema's niet op de pipelines in CODE, maar op **`PL_FMD_SCHEDULE_<short>`** in **INTEGRATION CONFIG** (map `SchedulePipelines`), één per omgeving (D, T, P). De setup maakt ze eenmalig aan en overschrijft ze nooit.
     - **Waarom:** een schedule hoort bij de item-definitie en gaat dus mee met een promotie (zie hierboven, rookproef 2 stap 9b), de ontvangers niet. CONFIG zit in geen deployment pipeline, dus een promotie en een setup-update raken deze schema's niet. Daarmee vervalt het handwerk na elke promotie voor schema's en ontvangers (E-R2/E-R3).
     - **Inrichten, per omgeving:** open `PL_FMD_SCHEDULE_<short>` in INTEGRATION CONFIG, kies **Home → Schedule** en maak één schedule per cadans. Geef elk schedule parameters mee:
       - nachtelijk: `Target = LOAD`, `LoadGroup` leeg;
       - vaker per dag, alleen als de intake dat vraagt: `Target = LOAD`, `LoadGroup = INTRADAY`;
       - onderhoud: `Target = MAINTENANCE` (dit vervangt het schema op `PL_FMD_MAINTENANCE` hierboven).
     - **Melding bij een gefaalde run:** zet onder **Failure notifications** op `PL_FMD_SCHEDULE_<short>` de ontvangers uit de intake, één keer per omgeving. Laat Dev leeg als een gefaalde ontwikkelrun geen mail moet geven. Een mislukte run in CODE laat de schedule-pipeline falen (`waitOnCompletion`), dus de mail komt van die pipeline.
     - **Leg vast in het implementatieplan van de klant:** per omgeving de tijden, `Target`, `LoadGroup` en ontvangers. De schema's staan niet in git (CONFIG is niet aan git gekoppeld, ~~*aanname*, niet nagegaan~~ *getest in eigen omgeving*: `GET …/git/connection` op FMD_SMOKE3 INTEGRATION CONFIG gaf `NotConnected`, 2026-10-11).
     - **Let op:** de pipeline verwijst met letterlijke ID's naar de CODE-workspace van zijn omgeving. Krijgt die workspace of de orchestratie een nieuw ID, dan moet je de schedule-pipeline bijwerken, of verwijderen (met zijn schema's) en de setup opnieuw laten aanmaken.
     - **Een installatie van vóór #52** heeft haar schema's op de pipelines in CODE. De setup verwijdert ze niet. Zet ze over: maak de schema's op `PL_FMD_SCHEDULE_<short>`, en verwijder ze daarna van de pipelines in CODE. Tot die tijd blijft fase 7 stap 4e nodig.
     - **Status:** *getest in eigen omgeving* (2026-10-11, FMD_SMOKE3, `testplan-trial.md` T-D10): routering naar de juiste CODE-workspace (D, T, P), foutpropagatie, de mail bij een gefaalde geplande run (gemeld door Mitchell, geen run-ID), een promotie D → T zonder schedule in T (operatie `5351536f`), en `create_schedule_pipeline` tegen de echte `fab`-CLI (run `91f84e4a`). *Niet getest:* de hele setup in één run, een volledig groene `LOAD`-run, en een schedule met een `Target`-parameter via de portal (alleen handmatige runs met parameters).
   - Dit dekt alleen geplande runs. Een handmatig gestarte `PL_FMD_LOAD_ALL` geeft geen mail. `PL_FMD_SCHEDULE_*` roept `PL_FMD_LOAD_ALL` aan met `waitOnCompletion: true`, dus een gefaalde load laat ook de geplande pipeline falen (*vastgesteld*, pipeline-JSON). *2026-10-06:* `PL_FMD_ORCHESTRATION` doet dat ook (`waitOnCompletion: true`, *vastgesteld*).
   - Wil de klant Teams, meldingen van geslaagde runs, of één regel voor alle pipelines: Activator op de job-events, of workspace monitoring met een KQL-query (Microsoft Learn, *Create alerts for pipeline runs*). Scope de regel op het item en de status `Failed`, niet op "elk event" (het eigen Activator-kostenincident, `kosten.md`).
   - **Status:** *vastgesteld* via Microsoft Learn (2026-09-29) en de pipeline-JSON. *Toegevoegd 2026-10-05.*
     - *Getest in eigen omgeving 2026-10-06* (rookproef 2, stap 11): de geplande run `884c289b` in T faalde op een niet-bestaande bron, en de ontvanger kreeg de mail. *(Preciezer 2026-10-11, eindcontrole E-V4: die run was van de toenmalige wrapper `PL_FMD_SCHEDULE_NIGHTLY`, niet van de orchestratie. Voor het huidige mechanisme, `PL_FMD_SCHEDULE_<short>` in CONFIG, is de mail getest op 2026-10-11, zie hierboven.)*
5. Deactiveringsprocedure (**B-INFRA-02**) op minstens één bron testen, volgens `05_INTEGRATION/02_configdb-registratie.md` §Deactivering:
   - `integration.LandingzoneEntity.IsActive = 0` zetten. `Connection`/`DataSource` op 0 zetten heeft géén effect.
     - *Aanvulling 2026-10-05:* met het lijstsjabloon (§A.4a) zet je `IsActive = 0` in de lijst en draai je het sjabloon opnieuw. Een handmatige `UPDATE` wordt bij de volgende run van het sjabloon teruggedraaid.
   - Met de controlequery verifiëren dat de entiteit uit `vw_LoadSourceToLandingzone` verdwijnt en dat de volgende load de rest niet raakt.
   - **Daarna dezelfde bron opnieuw registreren en controleren dat de entiteit gedeactiveerd blijft.** Vanaf dacpac `4dd41cf` (PR #8) laat herregistratie `IsActive` van een bestaande entiteit staan; op een configdb met een oudere dacpac zet hij `IsActive` terug op 1. Noteer welk gedrag deze configdb laat zien.

**Verificatie:** de controlequery uit `07_extension-points.md` §1 geeft overal 'ok' en één type per connectietype; elke geregistreerde bron heeft minstens één succesvolle load doorlopen (zichtbaar in het FMD_Logging-rapport, geen `FailPipeline`/`FailedPipeline`); een gedeactiveerde bron levert geen nieuwe rijen meer aan, overige bronnen blijven ongestoord laden.

**Rollback/herstel:** bij een structurele fout op één bron: de entiteiten van die bron deactiveren (`integration.LandingzoneEntity.IsActive = 0` per `DataSourceId`) zonder de overige bronnen te raken. Dat is het isolatiemechanisme van de execution-views; bij herhaalde `DMTS_EntityNotFoundOrUnauthorized`: niet blindelings retryen, eerst via de operation-detail-API de onderliggende "dode" GUID-referentie identificeren (zie `11_troubleshooting.md`).

**Verwijzing:** `07_extension-points.md`, `10_operations.md`, `11_troubleshooting.md`, besluiten B-INFRA-02, B-EXT-01.

**Risico:** dit is de fase met de grootste tijdsonzekerheid (R7, capaciteitscontentie neemt toe met meer parallelle bronnen).

---

## Fase 6 — Gold-laag en semantisch model

**Voorwaarden:** minstens de kernbronnen voor het betreffende business-domein staan in fase 5 geregistreerd en gevalideerd.

**Exacte acties:**
1. `NB_LOAD_GOLD` en `NB_MLV_EXAMPLE` vullen in de CODE-workspace van het domein. **Niet hernoemen** ~~**of kopiëren**~~: de setup hangt `PL_FMD_LOAD_GOLD` op naam aan de orchestratie, en de pipeline verwijst naar de notebooks met hun logical ID (zie `06_BUSINESS_DOMEINEN/02_gold-laag-mlv.md`).
   - *Correctie 2026-10-12 (`FMD_FRAMEWORK#58`, vastgesteld in `NB_UTILITIES_SETUP_FMD`, `CUSTOMER_OWNED_ITEMS`):* extra Gold-notebooks mogen wel. `PL_FMD_LOAD_GOLD` is klanteigendom: de setup maakt hem één keer per stage (D/T/P) aan en overschrijft hem daarna niet.
     - Gold-code komt in `NB_LOAD_GOLD` en `NB_MLV_EXAMPLE`, of in extra notebooks die je in Dev als activity aan `PL_FMD_LOAD_GOLD` toevoegt. Promoveer daarna via fase 7.
     - Promoveer de notebooks samen met of vóór de pipeline. Anders faalt de promotie met *Missing Dependencies* (dat mechanisme: *getest in eigen omgeving*, 2026-09-28, `testplan-trial.md` T-A07b; voor deze pipeline *aanname*).
     - Gevolg: een latere framework-wijziging aan de Gold-pipeline bereikt een bestaande installatie niet. Neem hem met de hand over in Dev, en promoveer.
   - *Aanvulling 2026-10-08 (P3-R1, `FMD_FRAMEWORK#47`):* vanaf #47 overschrijft een nieuwe setup-run deze notebooks (en `NB_CREATE_SHORTCUTS`) niet meer. Dat geldt in geen enkele stage. Een fork van vóór #47 zet ze in D, T en P terug naar de template: draai daar na een setup-run een promotie vanuit Dev, of zet ze terug uit git.
2. `VAR_GOLD_SHORTCUTS_FMD` controleren. `NB_SETUP_BUSINESS_DOMAINS` heeft de vier ID-variabelen (`SourceWorkspaceId`, `SourceLakehouseId`, `Shortcut_TargetWorkspaceId`, `Shortcut_TargetLakehouseId`) al voor elke omgeving ingevuld. Vul met de hand aan als de setup-output een `❌`-regel voor dit domein toont (zie R1).
   - **`SourceSchema` en `Shortcut_TargetSchema` bleven in de hertest leeg.** Met schema-lakehouses staan de Silver-tabellen onder de namespace van de bron (bijvoorbeeld `Tables/aw/Sales_Customer`). ~~Zet beide defaults dan op die namespace (hertest T-E01).~~
     - *Correctie 2026-10-06 (review 3, P3-V6):* zet ze niet met de hand, maar in het manifest: `shortcuts.source_schema` en `shortcuts.target_schema`. De setup vult de library daaruit, en een volgende setup-run overschrijft een handmatige waarde (`overwrite_variable_library = True`).
     - *Getest in eigen omgeving:* rookproef 2 met `aw`/`aw` in het manifest; de waarden stonden daarna in de library (stap 4).
     - **Beperking:** het manifest heeft één `source_schema` en één `target_schema` per installatie. Een domein dat Silver uit twee namespaces leest, past daar niet in. Maak de shortcuts voor de tweede namespace dan met de hand of met een eigen notebook. Dat is klantcode (ADR-003).
3. In `NB_CREATE_SHORTCUTS` de lijst `ShortcutNames` vervangen (standaard negen WWI-demotabellen), met de Silver-tabelnamen `<Schema>_<Tabel>`, en het notebook draaien conform **B-GOLD-01**.
   - Pas draaien nadat Silver in díe omgeving geladen is. Een shortcut naar een tabel die nog niet bestaat, faalt met *"Target path doesn't exist"*.
   - Controleer daarna de shortcuts zelf (`GET …/items/{lakehouse}/shortcuts`). ~~Het notebook eindigt ook groen als er niets is aangemaakt.~~ *(Correctie 2026-10-06, P3-V1: vanaf PR #31 faalt het notebook bij een mislukte shortcut; in een oudere fork eindigt het groen.)*
4. `CREATE OR REPLACE MATERIALIZED LAKE VIEW`-statements schrijven, volgens de afgesproken conventie (`gold.F_<Naam>`/`gold.D_<Naam>` in PascalCase, schema `gold`; niet afgedwongen, dus spreek enkelvoud of meervoud af; Fabric slaat de namen in kleine letters op). *Correctie 2026-10-05: hier stond `gold.Fact<Onderwerp>`/`gold.Dim<Onderwerp>`; conventie vastgesteld door Mitchell op 2026-09-28.* `NB_MLV_DEMO_GOLD` (`examples/`, niet gedeployd) is een voorbeeld van de syntax; het draagt koppelingen van een andere tenant en het schema `dbo` mee.
5. In `NB_MLV_EXAMPLE` de default-lakehouse op `LH_GOLD_LAYER` van het domein zetten, zodat de `CREATE`-statements daar terechtkomen. Bij een promotie zet de deployment pipeline die binding automatisch om naar Gold van de doelomgeving (hertest T-E02).
   - De refresh-cel is vanaf PR #21 klaar: hij haalt workspace en lakehouse uit `VAR_GOLD_SHORTCUTS_FMD`, wacht op de job, en faalt bij een mislukte refresh.
   - In een oudere fork gebruikt die cel `currentWorkspaceId`, en dat is de CODE-workspace. Er wordt dan niets ververst, terwijl de pipeline groen blijft. Pas die cel dan aan.
   - `PL_FMD_LOAD_GOLD` draait dit notebook al na `NB_LOAD_GOLD`.
6. Semantisch model (Direct Lake) bouwen in de SEMANTIC-workspace tegen de Gold-laag. Na een promotie blijft het naar Gold van de bronomgeving wijzen (fase 7, stap 4b).
7. **Alleen bij een personal-workspace-scenario:** handmatige Direct Lake-pointer-swap vóór commit (end-to-end geteste route).

**Verificatie:** elke MLV retourneert data conform de businessverwachting (business valideert inhoudelijk); MLV-refresh via de API-route is aantoonbaar succesvol getest, gecontroleerd via de status van de job-instance (een groene pipeline bewijst dat niet); het semantisch model in Power BI Desktop/service toont correcte cijfers.

**Rollback/herstel:** foutieve MLV-definitie → `CREATE OR REPLACE MATERIALIZED LAKE VIEW` opnieuw uitvoeren met gecorrigeerde SQL (geen destructieve impact op de onderliggende Silver-data); verkeerd gevulde shortcuts → `NB_CREATE_SHORTCUTS` opnieuw draaien nadat de Variable Library is gecorrigeerd (dubbelcheck het item-ID, zie R2).

**Verwijzing:** `06_BUSINESS_DOMEINEN/02_gold-laag-mlv.md`, `03_shortcuts-en-deployment.md`, `04_semantisch-model-direct-lake.md`, besluit B-GOLD-01.

**Risico's:** R2 (item-ID-verwisseling), R5 (hardcoded cross-workspace-aanroep bij maatwerk-orchestratie).

---

## Fase 7 — CI/CD en productie-inrichting

**Voorwaarden:** fase 6 afgerond en door business gevalideerd in Dev.

**Exacte acties:**
1. **Bij B-CICD-01 = Deployment Pipelines (Bitmetric-default):** de Deployment Pipelines staan er al sinds fase 3. `NB_SETUP_FMD` en `NB_SETUP_BUSINESS_DOMAINS` maken ze aan en koppelen de stages via `deploy_deployment_pipeline()`. Controleer in de portal:
   - of elke stage aan de **juiste** workspace hangt. De helper slaat een stage die al gekoppeld is over, ook als die aan de verkeerde workspace hangt;
   - of de stages overeenkomen met `manifest.environments`. Een bestaande pipeline wordt niet aangepast;
   - of de setup-output een melding "not paired" bevat. Die ontstaat als een item in een stage-workspace is aangemaakt nádat die stage aan de pipeline was gekoppeld, bijvoorbeeld bij een tweede setup-run met nieuwe items, of na verwijderen en opnieuw aanmaken. De eerstvolgende promotie naar die stage faalt dan met `TargetArtifactNameConflict`. **Herstel:** de stage ontkoppelen en opnieuw koppelen (`unassignWorkspace`, daarna `assignWorkspace`). Dat wist de deploymentgeschiedenis en de deployment rules van die stage. Noteer de rules vooraf; ze zijn alleen in de portal te zien en opnieuw in te stellen.

   **Bij een klant die expliciet fabric-cicd kiest** (afwijking van de default; ADR-012 legt Deployment Pipelines vast en noemt fabric-cicd een later spoor): zie `02_beslisdocument/03_architectuurvarianten.md`, Variant B. Dat vraagt maatwerk; er is geen kant-en-klaar Bitmetric-pad.
2. Dev → Test promoveren. **Dit is handwerk** via de portal of de Fabric REST-API (`deploymentPipelines/{id}/deploy`). De framework-helpers doen geen promotie.

   **Runbook: promotie naar Test of Prod** (*toegevoegd 2026-10-06*, review 3 P3-R7).
   - Dit is de enige plek met de volgorde. `10_operations.md`, `09_cicd-en-deployment.md` en `14_ontwikkelproces.md` verwijzen hiernaar.
   - Bij Test → Prod alles opnieuw, na go/no-go van de klant.
   - *Getest in eigen omgeving:* rookproef 2 (2026-10-05/06) volgde deze volgorde voor D → T (stap 7 en 8) en T → P (stap 10), op stap 5 en 6 na in T → P. Daar ging FINANCE CODE vóór DATA, zonder probleem.

   | # | Stap | Waarom op deze plek |
   |---|---|---|
   | 1 | Promoveer **INTEGRATION DATA**. | Lakehouses; de CODE-workspaces verwijzen ernaar. |
   | 2 | Promoveer **INTEGRATION CODE**. | Uitzondering: verwijst `PL_FMD_ORCHESTRATION` naar een Gold-pipeline die in het doel nog niet bestaat, dan faalt dit met *Missing Dependencies*. Doe deze stap dan als laatste promotie, na stap 6. |
   | 3 | **Controleer in INTEGRATION CODE van het doel:** de actieve value set van `VAR_CONFIG_FMD`, en de lege default van `Data_WorkspaceGuid` (stap 3 hieronder). | Een promotie overschrijft defaults, maar niet de actieve value set. |
   | 4 | **Registreer en laad in het doel:** het lijstsjabloon (§A.4a) met `-v DataWorkspace=<DATA van het doel> Environment=<T\|P>`, daarna `PL_FMD_LOAD_ALL` in het doel. Controleer dat alleen de entiteiten van het doel laden (stap 3a hieronder). | Registraties gaan niet mee met een promotie. Zonder deze stap faalt stap 5. |
   | 5 | Promoveer de **DATA**-workspace van elk domein. | De shortcuts in Gold gaan mee en wijzen daarna naar Silver van het doel. Bestaat een Silver-tabel daar nog niet, dan faalt de promotie met `CopyOverwriteResult.GenericError`. |
   | 6 | Promoveer de **CODE**-workspace van elk domein; daarna SEMANTIC en REPORTING. | Gold-code. De default lakehouse van een notebook wordt omgezet naar Gold van het doel. |
   | 7 | **Controleer in de CODE-workspace van elk domein:** de actieve value set van `VAR_GOLD_SHORTCUTS_FMD`. | Zelfde reden als stap 3. |
   | 8 | Draai **Gold in het doel**: `PL_FMD_ORCHESTRATION`, of `PL_FMD_LOAD_GOLD` per domein. Controleer de MLV-refresh via de status van de job-instance. | Gold bestaat pas na een run in het doel. |
   | 9 | **Post-deployment-checklist** (stap 4 hieronder): shortcuts, Direct Lake-rule per model, de Gold-verwijzingen in de orchestratie, en de **schema's en ontvangers** (`10_operations.md`, *Na elke promotie*, punt 6), ook van `PL_FMD_MAINTENANCE` *(2026-10-08, E-R4)*. | De rule en de ontvangers gaan niet mee; het schema wel, en ingeschakeld. |
   | 10 | Spot-check (stap 5 hieronder). | |

   De stappen hieronder geven de achtergrond per onderdeel. Waar hun volgorde afwijkt van dit runbook, geldt het runbook.

   - **Volgorde** *(historisch; vervangen door het runbook hierboven, 2026-10-06)***:** promoveer eerst de workspaces waarnaar verwezen wordt en dan die welke verwijzen: INTEGRATION DATA, dan de DATA-workspaces van de domeinen (shortcuts naar Silver), dan de CODE-workspaces van de domeinen, en daarna INTEGRATION CODE (`PL_FMD_ORCHESTRATION_TEMPLATE` roept de Gold-pipelines aan). Deze volgorde is afgeleid uit de bekende verwijzingen (*aanname*); het principe erachter is getest. Een verwijzing naar een item in een andere workspace wordt omgezet naar de gekoppelde tegenhanger in de doelstage. Ontbreekt die, dan faalt de promotie met *Missing Dependencies* (*getest in eigen omgeving*, 2026-09-28, T-A07b; `11_troubleshooting.md`).
     - *Aanvulling 2026-10-06 (rookproef 2, stap 10):* **promoveer de DATA-workspace van een domein pas na stap 3a**, dus als de Silver-tabellen in de doelomgeving bestaan.
       - Bestaat een doeltabel van een shortcut daar nog niet, dan faalt de promotie met `DeploymentOperationFailed` / `CopyOverwriteResult.GenericError` op `LH_GOLD_LAYER` (*getest in eigen omgeving*, T → P, operatie `ca36bd65`). Na de load in de doelomgeving slaagde dezelfde promotie (`a78ac649`).
       - ~~De volgorde wordt daarmee: INTEGRATION DATA → stap 3a (registreren en laden in het doel) → DATA van de domeinen → CODE van de domeinen → INTEGRATION CODE.~~
       - ~~Moet INTEGRATION CODE vóór de load mee, omdat een framework-wijziging nodig is voor het laden: dat kon in de rookproef zonder problemen, want de Gold-pipelines bestonden al in het doel.~~
       - *Correctie 2026-10-06 (P3-R7):* de volgorde staat nu in het runbook hierboven. INTEGRATION CODE gaat daar vóór de load, zoals in de rookproef. Alleen bij een nieuwe Gold-verwijzing in de orchestratie gaat hij als laatste.
   - Faalt een volledige promotie van INTEGRATION CODE met `TargetArtifactNameConflict` op `NB_FMD_CUSTOM_DQ_CLEANSING`, promoveer dan selectief zonder dat notebook. `NB_FMD_PROCESSING_PARALLEL_MAIN` maakt het in elke omgeving zelf aan, ongekoppeld (`11_troubleshooting.md`; *getest in eigen omgeving*, 2026-09-28).
   - *Bijgewerkt 2026-09-30:* `FMD_FRAMEWORK#28` (gemerged 2026-09-30, `075c52b`) laat de setup het notebook aanmaken en koppelen zonder klantcode te overschrijven. Op een bestaande installatie maak je de koppeling eenmalig (zie `11_troubleshooting.md`); in FMD_TRIAL is dat gedaan en staat het notebook gekoppeld (D → T → P, *vastgesteld*, deployment pipeline 2026-09-30). Daarna is selectief promoveren niet meer nodig. ~~Een volledige promotie van INTEGRATION CODE na de fix is niet apart getest.~~ *Bijgewerkt 2026-10-06 (P3-V2):* in rookproef 2 slaagde de promotie van INTEGRATION CODE op een schone setup D → T (`5ef928ff`) en T → P (`ab159a08`, `8705689e`), zonder conflict op `NB_FMD_CUSTOM_DQ_CLEANSING` (*getest in eigen omgeving*; vermoedelijk volledig, de selectie is niet apart vastgelegd).
3. **Verplichte controle, ongeacht mechanisme:** een promotie overschrijft de defaults van een Variable Library in de doelstage met die van de bron, maar laat de actieve value set staan (getest op 2026-09-25). Controleer daarom in elke CODE-workspace van de doelomgeving dat de actieve value set van `VAR_CONFIG_FMD` en `VAR_GOLD_SHORTCUTS_FMD` die van de doelomgeving is, en dat de GUID's in die value set naar items in díe omgeving wijzen. `VAR_FMD` heeft geen waarden per omgeving; zet daar geen omgevingsspecifieke waarde als default, want die gaat met de promotie mee. Zo nodig corrigeren vóórdat je verder gaat (R1, `11_troubleshooting.md`).
   - Controleer ook de default van `Data_WorkspaceGuid` in `PL_FMD_LOAD_ALL`, `PL_FMD_LOAD_LANDINGZONE` en de schedule-pipelines in de doelomgeving. Die moet leeg zijn (vanaf PR #20). Staat daar de Dev-DATA-workspace, dan laadt de doelomgeving Dev (R13).
3a. **Registraties en eerste load in de doelomgeving.** De configdb is gedeeld (INTEGRATION CONFIG), en entiteiten gelden per DATA-workspace.
   - Registreer de bronnen ook met de `WorkspaceGuid` van DATA (T), respectievelijk (P), met hetzelfde sjabloon (§A.4).
   - *Bijgewerkt 2026-10-05:* gebruik bij voorkeur het lijstsjabloon (§A.4a). Dezelfde lijst uit de klantrepo, nu met `-v DataWorkspace="<PREFIX> INTEGRATION DATA (T)"` (of de Prod-naam) *(vanaf 2026-10-07 ook `Environment=T`, zie §A.4a)*, na elke promotie die nieuwe of gewijzigde entiteiten meeneemt. Een promotie neemt geen registraties mee.
   - Draai daarna `PL_FMD_LOAD_ALL` in de doelomgeving en controleer dat alleen de entiteiten van die omgeving laden. Zonder deze stap blijft Silver leeg, en kan stap 4a niets aanmaken (hertest T-E01).
4. Post-deployment-checklist uitvoeren (zie ook `09_cicd-en-deployment.md`):
   a. Shortcuts in Gold controleren (`GET …/items/{LH_GOLD_LAYER}/shortcuts`): aantal en doel. Ze gaan mee met de promotie van de DATA-workspace, en de deployment pipeline zet ze om naar Silver van het doel, ook nieuwe shortcuts (*getest in eigen omgeving*, 2026-09-28, D → T, `testplan-trial.md` T-E04). `NB_CREATE_SHORTCUTS` is daarvoor niet meer nodig.
      - Bij de **eerste** uitrol van een omgeving is Silver daar nog leeg. ~~Wat een promotie dan met de shortcuts doet, is niet getest.~~ *Correctie 2026-10-06 (rookproef 2):* de promotie van DATA faalt dan (`CopyOverwriteResult.GenericError`, zie stap 2). Promoveer DATA daarom (opnieuw) na stap 3a. Zijn de shortcuts daarna ongeldig of ontbreken ze, draai dan `NB_CREATE_SHORTCUTS` als terugval en controleer de shortcuts zelf. ~~Het notebook eindigt ook groen als er niets is aangemaakt.~~ *(Correctie 2026-10-06, P3-V1: vanaf PR #31 faalt het notebook bij een mislukte shortcut, met de namen in de melding.)*
      - *Correctie 2026-09-28: hier stond "`NB_CREATE_SHORTCUTS` handmatig opnieuw draaien (shortcuts gaan niet mee met Deployment Pipelines)". Reden: T-E04.*
   b. Direct Lake-modellen binden bij een promotie **nooit** automatisch om; het model blijft naar Gold van de bronomgeving wijzen (Microsoft Learn; hertest T-E03). Twee routes:
      - een data source rule per model per stage. Die kan alleen via de portal, door de eigenaar van het model; er is geen API voor. Een rule blijft staan voor volgende promoties;
      - de expressie van het model in de doelstage herschrijven via `updateDefinition` (Gold-server en SQL-endpoint-ID van die omgeving). Dat is scriptbaar, maar moet na **elke** promotie opnieuw.
      Controleer het resultaat met `GET …/datasets/{id}/datasources` (Power BI-API).
      - *Aanvulling 2026-10-26 (T-E08, *getest in eigen omgeving* in `FMD_GR`, D → T):* staat het model op **OneLake** (`AzureStorage.DataLake` in `expressions.tmdl`, `expressionSource: 'DirectLake - …'`) in plaats van het SQL-endpoint? Dan zijn de *Data source rules* grijs.
        - Zet het OneLake-pad in een parameter: `expression OneLakeUrl = "https://onelake.dfs.fabric.microsoft.com/<workspace>/<lakehouse>" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]`, en gebruik `AzureStorage.DataLake(OneLakeUrl, [HierarchicalNavigation=true])`.
        - Promoveer, zet in de portal de **Parameter rule** voor `OneLakeUrl` op het pad van Gold in het doel, en promoveer opnieuw. Controleer met `datasources`. De rule blijft staan.
        - Geen parameter? Herschrijf de expressie na elke promotie met `updateDefinition`.
        - Een model uit de rapport-editor (OneLake catalog) heeft een letterlijk pad. *Correctie 2026-10-26:* hier stond dat **New semantic model** vanaf een lakehouse het SQL-endpoint geeft. Volgens Microsoft Learn (*Develop Direct Lake semantic models*, bijgewerkt 2026-09-18) kies je het type in een dialoog op de pagina van het SQL-endpoint, en staat die standaard op OneLake als het endpoint in *user identity mode* staat, en op SQL-endpoint als het in *delegated mode* staat. Vanuit de Power BI-service en Desktop kan alleen Direct Lake op OneLake. Kies het type dus bewust en controleer de expressie. Reden: onderzoek bij T-E08.
        - Niet getest: T → P.
      **Volgorde bij een nieuw model** (Bitmetric-default is de rule): (1) promoveer het model, want een rule kan pas gezet worden als het model in de doelstage bestaat; (2) zet de data source rule op de doelstage, van Gold (bron) naar Gold (doel): server = `sqlEndpointProperties.connectionString`, database = het SQL-endpoint-ID van `LH_GOLD_LAYER` in de doelomgeving; (3) promoveer opnieuw en controleer met de datasources-call. *Getest in eigen omgeving* (2026-09-28, demoklant): `SM_SALES` en `SM_FINANCE` in Test en Prod wijzen na de tweede promotie naar Gold van de eigen omgeving (`plan-demoklant-trial.md`). Een nieuw model vraagt steeds nieuwe rules; reken per model per stage één portalhandeling.
      - *Aanvulling 2026-10-12 (generale repetitie GR-C2; getest in eigen omgeving):* in een omgeving waar Gold net voor het eerst is gedraaid, faalde de refresh van het model na de rule met *"We cannot access the source Delta table 'd_customer'"*. Ook een query gaf `Invalid object name`.
        - De MLV's stonden wel in OneLake, maar het SQL-endpoint van `LH_GOLD_LAYER` kende ze nog niet. De MLV's waren ±5 minuten eerder aangemaakt.
        - Direct Lake op het SQL-endpoint (B-GOLD-02) leunt op die metadata.
        - **Doe daarom na de eerste Gold-run in een omgeving `POST …/sqlEndpoints/{id}/refreshMetadata` op het Gold-endpoint.** Controleer in het resultaat dat elke `gold.*`-tabel "Success" of "NotRun" heeft. Ververs daarna pas het model.
        - Na de `refreshMetadata` slaagde de refresh, en gaf het model in Test dezelfde getallen als in Dev (`11_troubleshooting.md`).
   c. `PL_FMD_ORCHESTRATION`: de Gold-activities verwijzen met een letterlijke `workspaceId`/`pipelineId` naar de Gold-workspace. Controleer of die naar de doelomgeving wijzen.
   d. Bij het aanpassen van een Variable-Library-item: het item-ID dubbelchecken tegen de juiste library (R2).
   e. *Toegevoegd 2026-10-06:* de schema's van `PL_FMD_ORCHESTRATION` in het doel. Ze gaan ingeschakeld mee met de promotie van INTEGRATION CODE, met hun parameters, maar zonder de ontvangers van *Failure notifications* (fase 5 stap 4, rookproef 2 stap 9b en 14). Controleer de tijden, voeg de ontvangers toe, en zet uit wat in deze omgeving niet gepland hoort.
      - *Aanvulling 2026-10-08 (eindcontrole E-R4):* hetzelfde geldt voor het schema van **`PL_FMD_MAINTENANCE`**, ook in INTEGRATION CODE (fase 5 stap 4; dat het schema meegaat: *getest in eigen omgeving*, T-F06).
        - Controleer het tijdstip, buiten het laadvenster van deze omgeving, en de ontvangers.
        - Controleer ook dat de laatste run `Completed` is.
      - *Correctie 2026-10-11 (ontwerp `FMD_FRAMEWORK#52`, gemerged 2026-10-11, `4971d88`):* staan de schema's op `PL_FMD_SCHEDULE_<short>` in INTEGRATION CONFIG (fase 5 stap 4), dan vervalt deze controle voor de schema's en de ontvangers: een promotie raakt ze niet (*getest in eigen omgeving*, operatie `5351536f`). Controleer dan alleen dat de laatste run van `PL_FMD_SCHEDULE_<short>` `Completed` is. Een installatie die nog schema's op de pipelines in CODE heeft, houdt deze controle.
   - rijtelling per Silver-tabel;
   - Gold-MLV-refresh, gecontroleerd via de **status van de job-instance** (`GET …/workspaces/{DATA}/items/{Gold-lakehouse}/jobs/instances`, jobType `MaterializedLakeViews`). Vanaf PR #21 faalt `NB_MLV_EXAMPLE` zelf bij een mislukte refresh; in een oudere fork controleert het notebook dat niet.
6. Herhalen voor Test → Prod, na expliciet klantakkoord (go/no-go).
7. Productie-acceptatietest doorlopen (zie checklist onderaan dit document).

**Verificatie:** deployment-run toont `Completed` zonder fouten; post-deployment-checklist volledig afgevinkt; klant geeft schriftelijk productie-akkoord.

**Rollback/herstel:** reken **niet** op een ingebouwde rollback. Een "roll back"-optie in Fabric Deployment Pipelines is niet bevestigd, en de eerdere bewering daarover had geen bron. Het vangnet is de vorige versie in Git (Dev) plus een nieuwe promotie. Bij een subtielere fout die pas na deployment blijkt (bijv. verkeerde Variable-Library-waarde): waarde corrigeren en de betrokken post-deployment-stappen (shortcuts, pointer-swap) opnieuw uitvoeren, geen nieuwe volledige deployment nodig.

**Verwijzing:** `09_cicd-en-deployment.md`, `11_troubleshooting.md`, besluit B-CICD-01.

**Risico's:** R1, R2, R3, R4, R13 — dit is de fase met de meeste geconcentreerde risico's; behandel de post-deployment-checklist als niet-optioneel.

---

## Fase 8 — Overdracht en beheer

**Voorwaarden:** fase 7 succesvol afgerond, productie draait stabiel (minstens één volledige laadcyclus zonder incident).

**Exacte acties:**
1. Overdrachtssessie(s) plannen: monitoring/operations (`10_operations.md`), troubleshooting (`11_troubleshooting.md`), en hoe een nieuwe bron te registreren (fase 4/5-stappen herhalen).
2. Beheerdocumentatie/contactpunten vastleggen: wie lost welk type incident op (Bitmetric-support vs. klant-eigen beheer).
3. **Alleen indien relevant voor deze klant:** supportafspraak vastleggen conform ADR-002 (geen automatische framework-updates; uitzonderingspad is `git remote add framework && git cherry-pick <sha>`, gevolgd door de normale route naar Test/Prod. Bij een schemawijziging: dacpac opnieuw bouwen en de setup opnieuw draaien, eerst getest op een kopie van de configdb; de migratiescripts van ADR-004 bestaan niet, zie `09_cicd-en-deployment.md`).
4. Klant demonstreert zelfstandig (onder begeleiding) het registreren van een nieuwe bron of een vergelijkbare representatieve taak.

**Verificatie:** klant voltooit de gedemonstreerde taak zonder Bitmetric-tussenkomst; beheerdocumentatie/contactpunten zijn schriftelijk vastgelegd en gedeeld.

**Rollback/herstel:** n.v.t. — dit is een kennisoverdrachtsfase, geen technische wijziging.

**Verwijzing:** `01_kennisbasis/architectuur.md` (ADR-002), `10_operations.md`, `11_troubleshooting.md`.

---

## Productie-acceptatiechecklist

Te doorlopen vóór het formele productie-akkoord in fase 7:

Elke regel toetst of iets **werkt**, niet alleen of het is ingericht. Een groene `PL_FMD_LOAD_ALL` bewijst weinig: de lagen ketenen op `Completed`, een onbekend `DataSource.Type` wordt stil overgeslagen, en `NB_CREATE_SHORTCUTS` en de MLV-refresh eindigen ook groen als ze niets doen *(2026-10-06: geldt voor forks van vóór PR #31 en #21; daarna falen ze zichtbaar)*.

**Laden**
- [ ] De controlequery uit `07_extension-points.md` §1 geeft in Prod overal 'ok', en één `DataSource.Type` per connectietype.
- [ ] Elke actieve entiteit heeft in de laatste volledige cyclus een bestand geland en is doorgezet naar Silver (query hieronder). Rijtellingen van bron en Silver zijn voor de kerntabellen vergeleken.
- [ ] Er is in Prod ook een **tweede, incrementele** run gedaan, en die haalde alleen nieuwe of gewijzigde rijen op.
- [ ] De duur van de eerste full load is naast de timeouts gelegd (1 uur per laag, 10 minuten per notebookcel, 15 minuten per custom notebook; `10_operations.md` §Timeouts). Er is geen laag of cel in de buurt van een plafond.
- [ ] FMD_Logging-rapport toont geen openstaande `FailPipeline`/`FailedPipeline`-meldingen voor de laatste volledige laadcyclus.
- [ ] Scheduling (nightly/intraday) staat actief en conform de klantafspraak, en elke bron heeft de `LoadGroup` die bij zijn schema hoort.
  - *Aanvulling 2026-10-06 (review 3, P3-B1/B3; rookproef 2):* gecontroleerd **na** de laatste promotie, in Prod:
    - de schema's staan op `PL_FMD_ORCHESTRATION`, niet op `PL_FMD_SCHEDULE_*`;
    - de tijden zijn die van Prod;
    - het nachtelijke schema heeft geen `LoadGroup`;
    - onder *Failure notifications* staan de afgesproken ontvangers.
  - In Test en Dev staat geen schema dat niet nodig is.
  - *Correctie 2026-10-11 (ontwerp `FMD_FRAMEWORK#52`, gemerged 2026-10-11, `4971d88`):* met schema-pipelines controleer je in INTEGRATION CONFIG, niet in CODE: `PL_FMD_SCHEDULE_P` heeft de schema's van Prod (tijden, `Target`, `LoadGroup`, het nachtelijke zonder groep) en de afgesproken ontvangers onder *Failure notifications*. Op de pipelines in CODE staat geen schema.
- [ ] *Toegevoegd 2026-10-08 (eindcontrole E-R4):* in Prod staat een schema op `PL_FMD_MAINTENANCE`, buiten het laadvenster en met de afgesproken ontvangers. De eerste run in Prod is `Completed`. `VAR_FMD.landingzone_retention_days` is de bewaartermijn die met de klant is afgesproken (intake 2.7).

**Omgeving na de promotie**
- [ ] In elke Production-CODE-workspace is de value set `Production` actief voor `VAR_CONFIG_FMD` en `VAR_GOLD_SHORTCUTS_FMD`, en de GUID's daarin wijzen naar Production-items. Gecontroleerd **na** de laatste promotie.
- [ ] De Gold-activities in `PL_FMD_ORCHESTRATION` wijzen naar de Prod-workspaces (letterlijke `workspaceId`/`pipelineId`).
- [ ] De shortcuts in de Prod-Gold-lakehouse bestaan echt (lijst of portal) en wijzen naar Silver van Prod. Is `NB_CREATE_SHORTCUTS` als terugval gebruikt, dan bevat de output van de laatste run geen `Failed:`.
- [ ] Direct-Lake-pointers in het semantisch model wijzen aantoonbaar naar de Prod-Gold-lakehouse, niet naar Dev/Test.
- [ ] De MLV-refresh in Prod is gecontroleerd via de **status van de job-instance** (`Completed`), niet via de pipeline.

**Beheer**
- [ ] Deactiveringsprocedure is minstens éénmaal getest (op een niet-kritieke bron), **en** een herregistratie van die bron liet de entiteit uit (vereist een configdb met dacpac vanaf `4dd41cf`).
- [ ] Afgesproken wie een melding krijgt bij een gefaalde run, en hoe. ~~Het framework heeft geen alerting; het FMD_Logging-rapport is passief.~~ *(Correctie 2026-10-08, eindcontrole E-V3/P3-R3: de melding loopt via "Failure notifications" op de schema's van de orchestratie en het onderhoud (fase 5 stap 4, B-MON-01). Het FMD_Logging-rapport blijft passief.)*
- [ ] De vervaldatum van het SP-secret (`key_vault.secrets.sql_sp_secret`) staat genoteerd, met een eigenaar die hem vernieuwt. OAuth-connecties die zelden draaien, zijn bekend (90 dagen inactiviteit).
- [ ] Back-up en restore van de configuratiedatabase: de restoremogelijkheid is bekend en één keer uitgeprobeerd, of expliciet als risico geaccepteerd.
  - *Aanvulling 2026-10-05:* procedure in `10_operations.md`, *Back-up en herstel van de configuratiedatabase*. Bij de oplevering: de bewaartermijn van de back-ups op 35 dagen gezet, en een eerste bacpac-export gemaakt en buiten de tenant opgeslagen. De export en de import in een nieuwe database zijn getest (trial, 2026-10-05).
- [ ] Security: RBAC-rechten in Prod zijn gevalideerd tegen het daadwerkelijke rollenoverzicht (niet aangenomen op basis van het ongeverifieerde RBAC-brondocument).
- [ ] Business heeft de Gold-laag/het semantisch model in Prod inhoudelijk geaccordeerd.
- [ ] Overdrachtssessie(s) zijn gepland of al doorlopen.
- [ ] Rollback-pad voor deze deployment is bekend en getest (of expliciet als "niet getest, risico geaccepteerd" vastgelegd).

**Query: actieve entiteiten zonder bestand, of zonder doorzetting naar Silver.** `@Sinds` is het begin van de laatste volledige cyclus.

```sql
DECLARE @DataWorkspace NVARCHAR(200) = N'<PREFIX> INTEGRATION DATA'   -- de DATA-workspace van de omgeving, hier Prod
DECLARE @Sinds DATETIME = '<begin laatste cyclus>'

SELECT
     LZE.[LandingzoneEntityId]
    ,LZE.[SourceSchema]
    ,LZE.[SourceName]
    ,MAX(PLZE.[InsertDateTime])                               AS [LaatsteBestand]
    ,SUM(CASE WHEN PLZE.[IsProcessed] = 0 THEN 1 ELSE 0 END)  AS [BestandenNietInBronze]
    ,SUM(CASE WHEN PBLE.[IsProcessed] = 0 THEN 1 ELSE 0 END)  AS [TabellenNietInSilver]
FROM [integration].[LandingzoneEntity] LZE
JOIN [integration].[Lakehouse] LH
       ON LH.[LakehouseId] = LZE.[LakehouseId]
JOIN [integration].[Workspace] WS
       ON WS.[WorkspaceGuid] = LH.[WorkspaceGuid] AND WS.[Name] = @DataWorkspace
LEFT JOIN [execution].[PipelineLandingzoneEntity] PLZE
       ON PLZE.[LandingzoneEntityId] = LZE.[LandingzoneEntityId]
LEFT JOIN [integration].[BronzeLayerEntity] BLE
       ON BLE.[LandingzoneEntityId] = LZE.[LandingzoneEntityId]
LEFT JOIN [execution].[PipelineBronzeLayerEntity] PBLE
       ON PBLE.[BronzeLayerEntityId] = BLE.[BronzeLayerEntityId]
WHERE LZE.[IsActive] = 1
GROUP BY
     LZE.[LandingzoneEntityId]
    ,LZE.[SourceSchema]
    ,LZE.[SourceName]
HAVING MAX(PLZE.[InsertDateTime]) IS NULL
    OR MAX(PLZE.[InsertDateTime]) < @Sinds
    OR SUM(CASE WHEN PLZE.[IsProcessed] = 0 THEN 1 ELSE 0 END) > 0
    OR SUM(CASE WHEN PBLE.[IsProcessed] = 0 THEN 1 ELSE 0 END) > 0
-- verwacht: geen rijen
```

*Bijgewerkt 2026-10-07 (review 3, P3-V11):* de query filtert nu op de DATA-workspace van de omgeving (`@DataWorkspace`). Zonder dat filter verschenen in de gedeelde configdb ook de entiteiten van Dev en Test, die niet in de laatste Prod-cyclus laden.
- *Getest in eigen omgeving* (FMD_SMOKE2-configdb, 2026-10-07):
  - **zonder filter:** de drie Prod-entiteiten verschenen naast de rest van de configdb;
  - **met filter, `@Sinds` aan het begin van de laatste cyclus:** Prod, Dev en Test elk zonder rijen;
  - **met filter, `@Sinds` ná de laatste Test-load:** precies de vier actieve Test-entiteiten.
- Niet getest: een rij door `BestandenNietInBronze` of `TabellenNietInSilver`. Dat vraagt een bestand dat blijft hangen.

~~*Niet getest.*~~ *(2026-10-07: getest, zie hierboven.)* De query gaat ervan uit dat `InsertDateTime` het landingsmoment is *(bevestigd 2026-10-07: `InsertDateTime` valt tijdens de copy, ±16 s vóór het einde ervan; LZ 15 en 16 in FMD_SMOKE2)*. De join over twee `execution`-tabellen telt dubbel bij meerdere bestanden per entiteit; de tellingen zijn dus alleen als "0 of niet 0" te lezen.

---

## Bijlage A: Trial- en proefdeployment-stappenplan

**Status:** herschreven op 2026-09-25 tegen de fork (`main`, `703017b`), en bijgewerkt voor `81fe912` (volgorde van de setup, Variable Libraries). De vorige versie volgde de upstream-tutorial van juli, met verouderde celnummers, een handmatige connectiestap en een niet-geteste eis over de SKU (review 2, N-F2/N-F3). Die versie staat in `_archief/output-snapshot-2026-09-25/`.

### A.1 Stappenplan voor de fork

1. **Manifest invullen.** Alle klant- en omgevingswaarden (repository, `naming`, `environments[]`, capaciteitsnamen, `spark`, `key_vault` inclusief `secrets.sql_sp_tenant_id`/`sql_sp_client_id`/`sql_sp_secret`, `shortcuts`) staan in `manifest.yaml` in de root van de fork (voorbeeld: `manifest.example.yaml`). In de setup-notebooks hoef je ~~niets~~ bijna niets in cellen te configureren. `NB_SETUP_FMD` cel 2 zegt: *"Niets daarvan hoort nog in een notebookcel."* *(Correctie 2026-10-06, P3-V4: uitzondering zijn `load_demo_data`, `assign_icons`, `overwrite_variable_library`, `driver` en `dry_run` in cel 5; zie fase 3 stap 3.)*
2. **Scaffolding-workspace aanmaken** en `setup/NB_BOOTSTRAP_FMD.ipynb` daarin importeren. Dat is het enige handmatige import. Doe dit **niet** in de Dev-CODE-workspace: die bestaat op dit moment nog niet. De scaffolding-workspace mag na afloop weg (`FMD_FRAMEWORK_DEPLOYMENT.md` §3).
   - Bij een **privé** klantfork: vul in dezelfde cel ook `github_token_key_vault` en `github_token_secret` in (vanaf PR #12) — anders faalt de bootstrap-run met een 404 bij het ophalen van het manifest. Leeg laten bij een publieke fork.
3. **Bootstrap draaien.** Die haalt `NB_SETUP_FMD` en `NB_SETUP_BUSINESS_DOMAINS` uit de fork en zet ze, met de repoconfiguratie ingevuld, in de huidige workspace. Een eerder geïmporteerde versie wordt daarbij overschreven.
4. **`NB_SETUP_FMD` draaien.** Dit notebook draait op de Python-kernel, zonder Spark. Het doet, in deze volgorde:
   - workspaces aanmaken;
   - connecties aanmaken: `CON_FMD_FABRIC_PIPELINES` en `CON_FMD_FABRIC_NOTEBOOKS` met Workspace Identity, en `CON_FMD_FABRIC_SQL` met de Service Principal uit Key Vault;
   - lakehouses aanmaken;
   - de SQL-database deployen;
   - items deployen, en de Variable Libraries vullen met de waarden per omgeving en de actieve value set per workspace (ADR-010);
   - pipelines deployen;
   - Deployment Pipelines aanmaken en stages koppelen, als laatste, zodat Fabric de items van de stages op naam koppelt; ongekoppelde naamgenoten worden gemeld;
   - de SQL-queries uit `custom_sql_deployment` uitvoeren.

   Er is geen handmatige connectiestap en geen tweede run meer nodig, mits de SP-secrets in Key Vault staan. ~~*Niet live geverifieerd dat één run altijd volstaat.*~~ *Correctie 2026-10-12:* *getest in eigen omgeving* (2026-10-12, FMD_SMOKE4, `testplan-trial.md` B1): in de eerste en enige setup-run (`0b88e273`) maakte de setup `CON_FMD_S4_FABRIC_SQL` aan met een nieuwe SP die in geen enkele groep zat. Daarna stond geen enkele activity op `Inactive`, en verwees elke vaste connectieverwijzing naar een bestaande connectie. De tweede run die `FMD_FRAMEWORK_DEPLOYMENT.md` van upstream voorschrijft, is nodig bij de handmatige route (een connectie in de portal wijst naar een bestaande database). De route van de setup gebruikt `FabricSql.Contents` zonder database-parameter, en heeft die tweede run niet nodig. Dat de logging via deze connectie ook rijen krijgt, is nog niet getest.
5. **`NB_SETUP_BUSINESS_DOMAINS` draaien.** Eén run verwerkt alle domeinen uit `naming.business_domains`: CODE/DATA/SEMANTIC/REPORTING-workspaces, Gold-lakehouses, `VAR_GOLD_SHORTCUTS_FMD` per omgeving gevuld (value sets), Deployment Pipelines (na de items), en de Gold-pipelines gekoppeld aan `PL_FMD_ORCHESTRATION`.
6. **Demodata laden en `PL_FMD_LOAD_ALL` draaien.**
7. **Valideren per entiteit, niet per pipeline.** Gebruik de monitoringquery in `03_technische_documentatie/10_operations.md` en een rijtelling per Silver-tabel. Een groene run bewijst door de `Completed`-ketening niet dat alles geladen is.

**Capaciteit:** minimum-SKU **F2** (*tweedehands* (Mitchell, 2026-10-05); *correctie 2026-10-05*, hier stond "nog niet vastgesteld"). De eerdere eis "Fabric Trial, niet F2, de bootstrap vereist een Spark Medium pool" was overgenomen tutorialtekst over de oude sizing (8/56g) en is nooit op F2 getest. De setup-notebooks gebruiken geen Spark. De runtime-notebooks draaien in `ENV_FMD`, standaard met driver 4 cores/28g en maximaal 2 executors van 4/28g (`Sparkcompute.yml`, overschreven vanuit `manifest.yaml` → `spark.default`). Toets bij een andere SKU dan F2, of bij een zwaardere `spark`-sizing, vóór een klantvoorstel of een notebook in `ENV_FMD` start (B-INFRA-03).

**Status:** vastgesteld tegen `setup/*.ipynb`, `NB_UTILITIES_SETUP_FMD` en `FMD_FRAMEWORK_DEPLOYMENT.md`; capaciteit: open vraag.

### A.2 Wat de Bitmetric-fork toevoegt ten opzichte van upstream

- Deployment Pipelines-automatisering (`NB_UTILITIES_SETUP_FMD`: `ensure_deployment_pipeline`, `assign_deployment_pipeline_stage`, `deploy_deployment_pipeline`). Die maakt de pipeline aan en koppelt de stages. De **promotie zelf** (Dev → Test → Prod) doet hij niet: er is geen `/deploy`-aanroep, dus promoveren blijft handwerk via de portal of de REST-API.
- Orchestratie- en Gold-pipeline (`PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD`), plus het automatisch koppelen van elk domein.
- De MLV-refresh-cel in `NB_MLV_EXAMPLE`.
- Het Variable Library-patroon voor cross-workspace-referenties.
- `LoadGroup` voor scheduling per groep bronnen.

### A.3 Statusmoment 2026-09-15 (historisch voorbeeld van wat een validatie moet dekken)

**Wat er toen al stond:** het basisframework plus het FINANCE-domein, gedeployed op de `FMDTRIAL`-capaciteit; de orchestratie-wiring werkte.

**Wat er toen nog ontbrak (illustratief):**
1. Geen semantisch model gedeployed.
2. Run-historie niet geverifieerd zonder job-ID.
3. **Cross-workspace-verwijzing met een letterlijke ID:** een `InvokePipeline`-activity verwees met een letterlijke `workspaceId`/`pipelineId` naar de Finance CODE-workspace.
   ⚠️ **Les:** dat patroon maakt de setup zelf ook. `wire_domain_into_orchestration()` voegt per domein een `InvokePipeline` met de letterlijke Gold-`workspaceId`/`pipelineId` van díe omgeving toe aan `PL_FMD_ORCHESTRATION`. Binnen één omgeving is dat correct. Na een Deployment-Pipeline-promotie van die pipeline moet je controleren of de verwijzing naar de doelomgeving wijst. Zelf toegevoegde cross-workspace-aanroepen gaan via de Variable Library (zie R5).
4. Gold-tabellen niet gecontroleerd met een losse query.
5. Test/Prod nog niet op vergelijkbare status als Dev.

**Praktische les:** een validatie is niet compleet met "de pipeline is groen". Controleer expliciet:
- het semantisch model is aanwezig;
- de run-historie is per entiteit echt succesvol;
- elke cross-workspace-aanroep wijst naar de juiste omgeving;
- de Gold-tabellen zijn met een losse query gecontroleerd.

### A.4a Lijstsjabloon voor alle entiteiten van een omgeving (aanbevolen)

*Aanvulling 2026-10-20 (branch `feature/loadgroup-kolommen-filter`, ADR-020, nog niet gemerged):* per tabel kun je in `NB_REGISTRATIE` (tab 2) ook een eigen `LoadGroup`, een kolomkeuze (`SourceColumns`) en een bronfilter (`SourceFilter`) instellen, voor `ASQL_01`, `ASQL_02` en `SNOWFLAKE_01`. Stel de kolomkeuze vóór de eerste load in: kolommen weghalen bij een tabel die al in Bronze staat laat de Bronze-merge falen (*getest in eigen omgeving*, 2026-10-20); verwijder dan eerst de Bronze- en Silver-tabel. Een filter wijzigen haalt niets uit Bronze en Silver weg, en de proefdraai voert het predicaat niet uit.

*Correctie 2026-10-15 (`FMD_FRAMEWORK#71`, ADR-018 *Accepted*). Reden: het sqlcmd-sjabloon is verwijderd; `NB_REGISTRATIE` (CONFIG-workspace) met `integration.sp_RegisterEntities` is de enige route voor de lijst. Wat hieronder staat over bindingen per omgeving, `LoadGroup`, `HistoryDays`, `IsHistorized` en de controles, geldt onveranderd voor de lijsten `sources` en `entities` in het notebook (`02_configdb-registratie.md`, Route 3). Alleen de aanroep verandert: `register(sources, entities, domain="INTEGRATION", environments=["D"], dry_run=True)` in plaats van `sqlcmd … -i registreer_entiteiten.sql`. Tijdens een feature gebruik je `environments=["DEV_<NAAM>"]`. De `sqlcmd`-regels hieronder zijn historie.*

*Correctie 2026-10-16 (ADR-018, aanvulling "Interactieve editor"; bron: `FMD/src/NB_REGISTRATIE.Notebook/notebook-content.py`, `FMD/src/NB_FMD_REGISTRATION_FUNCTIONS.Notebook/notebook-content.py`). Reden: `NB_REGISTRATIE` bevat geen lijsten `sources`/`entities` meer maar de editor (`registration_ui()`). De werkwijze is nu: connectie registreren, editor openen en laden, bij een nieuwe bron **Ontdekking starten (pipeline)** (start `PL_FMD_DISCOVER_SOURCE` in de CODE-workspace van de gekozen omgeving), tabellen instellen, en op tab 3 controleren, proefdraaien en registreren. Uitleg en teststatus: `02_configdb-registratie.md`, Route 3, "Werkwijze met de editor" (getest in eigen omgeving, FMD_EIND, 2026-10-16). Voor wat hieronder staat over bronbinding per omgeving, `LoadGroup`, `HistoryDays`, `IsHistorized` en de controles maakt het niet uit: de editor roept dezelfde `register()` aan. De lijsten `sources` en `entities` bestaan nog voor wie `register()` rechtstreeks aanroept (geavanceerd). Een bestaande installatie houdt zijn oude `NB_REGISTRATIE` (klanteigendom, de setup overschrijft hem niet); neem de nieuwe cellen over of verwijder het item en laat de setup het opnieuw plaatsen.*

*Nieuw 2026-10-05 (A5, PR #33, gemerged `301aae8`).* `templates/registratie/registreer_entiteiten.sql` in de fork registreert een lijst bronnen en entiteiten voor één omgeving, in één transactie.
- **Gebruik:** kopieer het naar de klantrepo en vul ~~de lijst `@E` in. Die lijst is reviewbaar in een PR. Draai het per omgeving: `sqlcmd … -b -v DataWorkspace="<PREFIX> INTEGRATION DATA (D)" -i registreer_entiteiten.sql`.~~ *(Correctie 2026-10-12, `FMD_FRAMEWORK#43`; draft van de repo-watch van 2026-10-08 verwerkt. Reden: sinds #43 zijn er twee lijsten en is `Environment` verplicht.)* de lijsten `@Sources` en `@Entities` in. Die lijsten zijn reviewbaar in een PR. Draai het per omgeving: `sqlcmd … -b -v DataWorkspace="<PREFIX> INTEGRATION DATA (D)" Environment=D -i registreer_entiteiten.sql`. Dat doe je na de setup en na elke promotie die nieuwe of gewijzigde entiteiten meeneemt.
  - *Bijgewerkt 2026-10-07 (`FMD_FRAMEWORK#43`, gemerged `642b08e`, review 3 P3-R6):* het sjabloon is in het Engels, en heeft twee lijsten: `@Sources` (bronbinding per omgeving) en `@Entities` (de entiteiten, met alleen een logische `Source`). De aanroep krijgt er `Environment=<D|T|A|P>` bij:
    `sqlcmd … -b -v DataWorkspace="<PREFIX> INTEGRATION DATA (D)" Environment=D -i registreer_entiteiten.sql`.
- **Bron per omgeving** (*toegevoegd 2026-10-07*, P3-R6):
  - Een regel in `@Sources` bindt een logische bron (bijvoorbeeld `ERP`) aan een connectie, een database (`DataSourceName`; bij ASQL en Snowflake de database), een namespace, een type, een `LoadGroup` en een optionele `HistoryDays`.
  - `Environment = '*'` geldt voor elke omgeving zonder eigen regel. Een regel voor `D` of `T` gaat daarvoor. Zo laadt standaard elke omgeving uit dezelfde bron, en wijk je per bron en per omgeving af. Een voorbeeld: Dev uit `ERP_DEV`, Test uit `ERP_TEST`, en Prod uit de productiedatabase.
  - De `Namespace` moet voor een bron in elke omgeving gelijk zijn, anders krijgen Silver en Gold andere tabelnamen. Het sjabloon controleert dat.
  - ~~Een eigen binding per omgeving geeft ook een eigen `DataSource`-rij, en dus een eigen `LoadGroup` per omgeving.~~ *Correctie 2026-10-11 (eindcontrole E-V1):* een eigen binding geeft alleen een eigen `DataSource`-rij als connectie, database of type verschilt; de rij is uniek op die drie. Een `D`-regel met dezelfde database en een andere `LoadGroup` raakte dezelfde rij, en de laatste run won, ook voor de andere omgevingen. Vanaf `FMD_FRAMEWORK#53` weigert het sjabloon dat. Bij een gedeelde binding (`'*'`) is de `LoadGroup` gedeeld: een wijziging in de lijst van Dev geldt dan meteen ook voor Prod, zonder promotie.
  - `HistoryDays` geldt voor **alle** incrementele entiteiten van die bron. Die moeten dus allemaal een datum/tijd-watermark hebben; een numerieke of rowversion-watermark krijgt een datumstring en faalt bij de eerste load. Het sjabloon kan dat niet controleren, want het kent het kolomtype niet *(toegevoegd 2026-10-11, E-V1)*.
  - `HistoryDays`: een nieuwe incrementele entiteit krijgt bij de registratie een start-watermark van vandaag min N dagen, zodat de eerste load alleen die periode ophaalt. Een bestaande watermark blijft staan. Dit geldt alleen voor een datum/tijd-`IsIncrementalColumn`; een full-load-entiteit laadt alles (gebruik dan een view in de bron).
  - *Getest in eigen omgeving* (2026-10-07, rookproef 2 stap 18, ASQL):
    - binding per omgeving, met een terugdraai-test;
    - de controles op namespace, ontbrekende binding en ontbrekende `Environment`;
    - `HistoryDays` met een load.
  - *Aanname:* een aparte database per omgeving bij Snowflake. Er is maar één Snowflake-testdatabase.
- **Connectie vooraf** (*toegevoegd 2026-10-06*, review 3 P3-V7): de lijst verwijst naar een connectie op naam (`ConnectionName`), en die moet al in `integration.Connection` staan. Twee manieren:
  - geef de Fabric-connectie naar de bron een naam die met `CON_FMD_` begint. *(Aanvulling 2026-10-12, `FMD_FRAMEWORK#56`: kiest de klant een eigen `naming.connection_prefix`, bijvoorbeeld `CON_ACME_FMD`, dan moet de bronconnectie met dát voorvoegsel beginnen. De setup registreert alleen connecties met het voorvoegsel uit het manifest. *Vastgesteld in code*, niet in een volledige run getest.)* De setup registreert alle zulke connecties zelf in `integration.Connection` (*vastgesteld* in `NB_SETUP_FMD`; in rookproef 2 kwam `CON_FMD_ASQL_AW` zo in de configdb). Een connectie die ná de setup is aangemaakt, komt er pas bij de volgende setup-run in;
  - of registreer hem zelf: `EXEC integration.sp_UpsertConnection @ConnectionGuid = '<ID van de Fabric-connectie>', @Name = '<naam>', @Type = '<type>', @IsActive = 1`. Een verzonnen GUID faalt bij elke load.
- **Bekende beperking** (*toegevoegd 2026-10-06*, review 3 P3-V10; *vastgesteld in code*, `sp_GetBronzelayerEntity` op `main`):
  - gebruik geen `"` of `\` in `SourceName`, `TargetSchema`, `TargetName`, `FileName` of `PrimaryKeys`;
  - de Bronze-procedure bouwt daarmee een JSON-string, en haar escape (`REPLACE(x, '\', '\')`) vervangt niets. Zo'n teken breekt de JSON voor Bronze. Welke foutmelding dat geeft, is niet getest;
  - `sp_GetSilverlayerEntity` escapet wel goed. De fix is diezelfde escape in de Bronze-procedure (PR-kandidaat, met een nieuwe dacpac).
  - *Bijgewerkt 2026-10-07:* opgelost in `FMD_FRAMEWORK#44`, gemerged `10434d5` (zelfde escape als Silver, nieuwe dacpac). Getest in de FMD_SMOKE2-configdb in een teruggedraaide transactie: met de oude procedure gaf een bestandsnaam `test"quoteack.parquet` ongeldige JSON, met de nieuwe geldige. Met een fork vanaf #44 vervalt deze beperking.
- **Niet mengen met §A.4:** gebruik voor een omgeving óf de lijst, óf het losse sjabloon. Het losse sjabloon zet `LoadGroup` per bron opnieuw, en de volgende run van de lijst zet hem weer terug.
- **De lijst is de waarheid:**
  - `LoadGroup` staat per bron in de lijst *(vanaf 2026-10-07: per bronbinding in `@Sources`)* en `IsActive` per entiteit. Zet een entiteit uit in de lijst (`IsActive = 0`), niet met de hand in de database (B-INFRA-02). Anders zet de volgende run haar weer aan.
  - Een bestaande entiteit wordt gevonden op bron + `SourceSchema` + `SourceName`. Een andere `SourceName` geeft dus een nieuwe entiteit (zie `11_troubleshooting.md`).
- **Historie in Silver per entiteit** (*toegevoegd 2026-10-12*, `FMD_FRAMEWORK#51`, ADR-016; draft van de repo-watch verwerkt; *vastgesteld in code*, `registreer_entiteiten.sql`):
  - `@Entities` heeft een kolom `IsHistorized`: `1` is SCD2-historie, leeg of `0` is alleen de huidige rij. *(Correctie 2026-10-13: tot dan was leeg gelijk aan `1`; ADR-016 *Herzien 2026-10-13*, branch `feature/silver-default-zonder-historie`, `FMD_FRAMEWORK#62`. Reden: historie die niemand vraagt kost opslag en merge-tijd.)*
  - Ook hier is de lijst de waarheid: bij elke run zet het sjabloon de waarde terug naar wat in de lijst staat (leeg wordt `0`, ook voor een entiteit die eerder `1` had). Heeft de klant historie nodig voor een tabel, zet dan `1` in de lijst vóór de eerste registratierun na deze wijziging (*getest in eigen omgeving* 2026-10-13, trial-Dev).
  - Van `1` naar `0` laat de bestaande historie staan. Van `0` naar `1` haalt die niet terug; de historie begint dan vanaf dat moment.
  - Zie `10_operations.md`, *Historie in Silver per tabel (`IsHistorized`)*. `IsHistorized = 0` via de pipeline is getest in eigen omgeving (`plan-afronding-eerste-klant.md`, A2); een gewijzigde bronrij niet.
- **Controles vooraf, zonder dat er iets geschreven wordt:**
  - de workspace en `LH_DATA_LANDINGZONE` zijn geregistreerd;
  - elke connectie bestaat;
  - `IsIncrementalColumn` is gevuld bij een incrementele entiteit, en `PrimaryKeys` bij elke entiteit;
  - `CustomNotebookName` is gevuld bij type `NOTEBOOK`;
  - er staat geen entiteit dubbel in de lijst;
  - elke bron heeft één `LoadGroup`.
  - *Aanvulling 2026-10-08 (eindcontrole E-R5, `FMD_FRAMEWORK#49`):*
    - `Environment` is `D`, `T`, `A` of `P`, en past bij het suffix van `DataWorkspace` (`(D)`/`(T)`/`(A)`, geen suffix voor `P`);
    - elke `Environment` in `@Sources` is `*`, `D`, `T`, `A` of `P`.
    - Zonder deze controles gold bij `Environment=TEST`, of bij een niet-passende workspace, stil de `'*'`-binding.
  - *Aanvulling 2026-10-11 (eindcontrole E-V1/E-V5, `FMD_FRAMEWORK#53`):*
    - één `DataSource` (connectie + database + type) heeft in heel `@Sources` één `LoadGroup`, over alle omgevingen;
    - het `DataSourceType` past bij het type van de connectie, met dezelfde combinaties als §A.4, inclusief Snowflake. Een verkeerd type werd eerder stil overgeslagen (T-C07).
    - *Getest in eigen omgeving:* 6 gevallen, read-only tegen de FMD_SMOKE3-configdb. *Getest in eigen omgeving:* 11 gevallen, read-only tegen de FMD_SMOKE3-configdb (PR #49).
  - Sinds #43 controleert het sjabloon ook of de `Namespace` per bron gelijk is, of elke entiteit een binding heeft, en of `HistoryDays` 1 of meer is.
- **Resultaat:** per entiteit het ID, `IsActive`, `LoadGroup`, en of de entiteit in `vw_LoadSourceToLandingzone` staat. *(Vanaf #51 ook `IsHistorized`.)*
- **Status:** getest in eigen omgeving (2026-10-05, FMD_TRIAL INTEGRATION DATA (D), checksum van `DataSource`/`LandingzoneEntity`/`BronzeLayerEntity`/`SilverLayerEntity` vóór en na):
  - de 10 bestaande demo-entiteiten opnieuw registreren veranderde niets;
  - een onbekende connectie gaf fout 50003, en er werd niets geschreven;
  - een fout in de tweede entiteit (in de procedure) draaide ook de al aangemaakte eerste entiteit terug;
  - zonder `-v` faalde de workspacecheck (50002).
  - ~~Niet getest: Test en Prod (dezelfde code, andere parameter).~~ *Bijgewerkt 2026-10-06 (P3-V2):* getest in Test en Prod in rookproef 2 (stap 7 en 10): dezelfde lijst, run 2 telkens zonder wijziging.
  - De procedures geven per entiteit een eigen resultaatset; die ruis in de uitvoer is normaal.

### A.4 Herbruikbaar SQL-sjabloon voor bronregistratie

Voorwaarden:
- De workspace en de drie lakehouses (`LH_DATA_LANDINGZONE`, `LH_BRONZE_LAYER`, `LH_SILVER_LAYER`) zijn geregistreerd. De setup doet dat.
- De Fabric-connectie naar de bron bestaat al in Fabric.

Het sjabloon is **herhaalbaar**: een tweede run voor dezelfde bron werkt bij in plaats van te falen. Alle procedures worden met **benoemde parameters** aangeroepen (R8). Het sjabloon stopt met een foutmelding bij ongeldige invoer.

```sql
-- ============================================================
-- CONFIGURATIE: pas alleen dit blok aan
-- ============================================================
DECLARE @FabricConnectionGuid UNIQUEIDENTIFIER = '<id van de Fabric-connectie naar de bron>'  -- Fabric > Instellingen > Verbindingen beheren; NIET zelf verzinnen
DECLARE @ConnectionName       NVARCHAR(200)    = 'CON_FMD_<BRON>'
DECLARE @ConnectionType       NVARCHAR(50)     = 'SQL'        -- zie de lijst toegestane combinaties hieronder

DECLARE @DataSourceName       NVARCHAR(100)    = '<BRON>'     -- bij ASQL_01: exact de naam van de brondatabase (de copy-pipeline gebruikt hem als database)
DECLARE @DataSourceNamespace  VARCHAR(100)     = '<ns>'
DECLARE @DataSourceType       VARCHAR(30)      = 'ASQL_01'    -- moet passen bij @ConnectionType
DECLARE @Description          NVARCHAR(200)    = '<omschrijving>'
DECLARE @LoadGroup            VARCHAR(50)      = ''           -- '' = geen groep

DECLARE @WorkspaceGuid        UNIQUEIDENTIFIER = '<WORKSPACE_GUID van de DATA-workspace>'
DECLARE @SourceSchema         NVARCHAR(100)    = '<schema>'
DECLARE @SourceName           NVARCHAR(200)    = '<tabel>'
DECLARE @TargetSchema         NVARCHAR(100)    = '<schema>'
DECLARE @TargetName           NVARCHAR(200)    = '<Tabel>'
DECLARE @FileName             NVARCHAR(200)    = '<tabel>'
DECLARE @FilePath             NVARCHAR(100)    = 'fmd'        -- hoofdmap; het pad wordt fmd/<ns>/<FileName>/jjjj/mm/dd. Max. 100 tekens
DECLARE @FileType             NVARCHAR(20)     = 'parquet'
DECLARE @IsIncremental        BIT              = 0
DECLARE @IsIncrementalColumn  NVARCHAR(50)     = NULL         -- verplicht als @IsIncremental = 1
DECLARE @CustomNotebookName   VARCHAR(200)     = NULL         -- alleen bij @ConnectionType = 'NOTEBOOK'
DECLARE @PrimaryKeys          NVARCHAR(200)    = '<pk1,pk2>'

-- ============================================================
-- CONTROLES: hier hoef je niets te wijzigen
-- ============================================================
IF NOT EXISTS (SELECT 1
               FROM (VALUES ('SQL', 'ASQL_01')
                           ,('SQL', 'ASQL_02')
                           ,('AZURESQLMI', 'SQLMI_01')
                           ,('ORACLE', 'ORACLE_01')
                           ,('ADLS', 'ADLS_01')
                           ,('ONELAKE', 'ONELAKE_TABLES_01')
                           ,('ONELAKE', 'ONELAKE_FILES_01')
                           ,('SFTP', 'SFTP_01')
                           ,('FTP', 'FTP_01')
                           ,('ADF', 'ADF')
                           ,('NOTEBOOK', 'NOTEBOOK')
                           ,('SNOWFLAKE', 'SNOWFLAKE_01')) AS t([ConnectionType], [DataSourceType])  -- SNOWFLAKE: toegevoegd 2026-10-11, eindcontrole E-V5
               WHERE t.[ConnectionType] = @ConnectionType
                 AND t.[DataSourceType] = @DataSourceType)
    THROW 50001, 'Ongeldige combinatie ConnectionType/DataSourceType: de pipelines slaan deze bron stil over.', 1;

IF NOT EXISTS (SELECT 1
               FROM [integration].[Lakehouse]
               WHERE [WorkspaceGuid] = @WorkspaceGuid
                 AND [Name] = 'LH_DATA_LANDINGZONE')
    THROW 50002, 'Workspace/lakehouses niet geregistreerd voor @WorkspaceGuid.', 1;

IF @IsIncremental = 1 AND ISNULL(@IsIncrementalColumn, '') = ''
    THROW 50003, '@IsIncrementalColumn is verplicht bij een incrementele entiteit.', 1;

-- ============================================================
-- UITVOERING
-- ============================================================
DECLARE @ConnectionId INT
DECLARE @DataSourceId INT

EXEC [integration].[sp_UpsertConnection]
     @ConnectionGuid = @FabricConnectionGuid
    ,@Name           = @ConnectionName
    ,@Type           = @ConnectionType
    ,@IsActive       = 1

SET @ConnectionId = (SELECT [ConnectionId]
                     FROM   [integration].[Connection]
                     WHERE  [ConnectionGuid] = @FabricConnectionGuid)

-- Bestaande DataSource opzoeken, zodat een tweede run bijwerkt in plaats van te falen
-- op UC_integration_DataSource (ConnectionId, Name, Type)
SET @DataSourceId = ISNULL((SELECT [DataSourceId]
                            FROM   [integration].[DataSource]
                            WHERE  [ConnectionId] = @ConnectionId
                              AND  [Name]         = @DataSourceName
                              AND  [Type]         = @DataSourceType), 0)

EXEC [integration].[sp_UpsertDataSource]
     @ConnectionId = @ConnectionId
    ,@DataSourceId = @DataSourceId
    ,@Name         = @DataSourceName
    ,@Namespace    = @DataSourceNamespace
    ,@Type         = @DataSourceType
    ,@Description  = @Description
    ,@LoadGroup    = @LoadGroup
    ,@IsActive     = 1

SET @DataSourceId = (SELECT [DataSourceId]
                     FROM   [integration].[DataSource]
                     WHERE  [ConnectionId] = @ConnectionId
                       AND  [Name]         = @DataSourceName
                       AND  [Type]         = @DataSourceType)

-- IsActive = 1 alleen voor een nieuwe entiteit; een eerder gedeactiveerde entiteit
-- blijft uit (vanaf fork-commit 4dd41cf, PR #8; zie B-INFRA-02)
EXEC [integration].[sp_UpsertLandingzoneBronzeSilver]
     @DataSourceId        = @DataSourceId
    ,@WorkspaceGuid       = @WorkspaceGuid
    ,@SourceSchema        = @SourceSchema
    ,@SourceName          = @SourceName
    ,@TargetSchema        = @TargetSchema
    ,@TargetName          = @TargetName
    ,@SourceCustomSelect  = ''          -- wordt door het framework niet gebruikt, zie 07_extension-points.md
    ,@FileName            = @FileName
    ,@FilePath            = @FilePath
    ,@FileType            = @FileType
    ,@IsIncremental       = @IsIncremental
    ,@IsIncrementalColumn = @IsIncrementalColumn
    ,@CustomNotebookName  = @CustomNotebookName
    ,@PrimaryKeys         = @PrimaryKeys

-- ============================================================
-- RESULTAAT CONTROLEREN: de entiteit moet in de laadview staan
-- ============================================================
SELECT v.[EntityId]
      ,v.[ConnectionType]
      ,v.[DataSourceType]
      ,v.[DataSourceName]
      ,v.[SourceSchema]
      ,v.[SourceName]
      ,v.[IsIncremental]
      ,v.[IsIncrementalColumn]
      ,v.[CustomNotebookName]
      ,v.[TargetFilePath]
FROM   [execution].[vw_LoadSourceToLandingzone] v
WHERE  v.[DataSourceId] = @DataSourceId
```

**Wat er ten opzichte van de vorige versie van dit sjabloon is veranderd (review 1 F4/F5, review 2):**
- **`ConnectionGuid`:** de vorige versie maakte bij een nieuwe connectie `NEWID()` aan. De copy-pipelines gebruiken `ConnectionGuid` echter als Fabric-connectie (`"connection": "@item().ConnectionGuid"`). Een verzonnen GUID levert bij elke load `DMTS_EntityNotFoundOrUnauthorized` op. Nu is het ID van de bestaande Fabric-connectie verplichte invoer.
- **`DataSourceId`:** stond hard op `0`, waardoor een tweede run faalde op de unique constraint. Nu wordt het eerst opgezocht.
- **Aanroepen:** alle `EXEC`'s zijn nu **benoemd**. Voorheen positioneel, met een commentaarregel die ten onrechte "expliciet benoemd" zei.
- **Types:** gelijkgetrokken met de procedure-signatures. De velden die de procedure zelf beperkt, zijn nu expliciet begrensd en gemarkeerd:
  - `@FilePath` max. 100 tekens (de tabel staat 500 toe);
  - `@IsIncrementalColumn` max. 50 tekens.
- **Controle op `ConnectionType`/`DataSourceType`:** de pipelines filteren op een vaste lijst, en een afwijkende waarde wordt stil overgeslagen (zie `07_extension-points.md`).
- **`@SourceCustomSelect`:** vast op `''`, omdat het framework die kolom niet leest.
- **`@FilePath`:** standaard `'fmd'`, net als de setup en `PL_TOOLING_POST_ASQL_TO_FMD`. De view zet de namespace er zelf achter (`FilePath/Namespace/FileName/…`). De vorige waarde `'<ns>'` gaf een dubbel pad, zoals `aw/aw/customer/…` (hertest T-C06, 2026-09-26).

**Waar dit past in de setup:**
- **Optie 1, lichte route:** `custom_sql_deployment["queries_stored_procedures"]` in `NB_SETUP_FMD` accepteert kale T-SQL-strings (0-based: gedeclareerd in cel 65, aangevuld in 67 t/m 75, uitgevoerd in cel 78). Twee kanttekeningen:
  - ~~Cel 78 vangt fouten af en print ze alleen. Controleer de output, want de setup-run blijft groen.~~ *Correctie 2026-10-06 (P3-V1):* de SQL-cel vangt fouten af en zet de taak op `failed`; vanaf PR #31 laat de laatste cel de setup dan falen. In een oudere fork blijft de run groen: controleer daar de output.
  - Dit notebook wordt bij elke bootstrap uit de fork overschreven. Queries die je hier toevoegt, moeten dus in de fork staan, niet alleen in de workspace.
- **Optie 2, schema-beheerde route:** objecten toevoegen aan `src/Config_Database/SQL_FMD_FRAMEWORK.sqlproj` en de dacpac opnieuw bouwen (CI-guard `dacpac-guard.yml`). Alleen nodig voor echte schema-objecten.

**Belangrijk:** het sjabloon bevat placeholders. Voer het niet automatisch bij elke deployment uit zonder ze eerst in te vullen. Herhaald uitvoeren laat een gedeactiveerde entiteit uit (vanaf fork-commit `4dd41cf`, getest 2026-09-25 in `testplan-trial.md` T-C04). Op een oudere dacpac activeert het die entiteit wél opnieuw; zie `05_INTEGRATION/02_configdb-registratie.md` §Deactivering.

**Status:** getest in eigen omgeving (2026-09-25, `testplan-trial.md`): twee keer draaien werkt bij zonder fout (T-C01), de drie invoercontroles geven 50001/50002/50003 zonder iets te registreren (T-C02), en herregistratie laat een gedeactiveerde entiteit uit terwijl een nieuwe entiteit `IsActive = 1` krijgt (T-C04). De configdb draaide `SQL_FMD_FRAMEWORK` van fork-commit `757d5cc`.

### A.5 Samenvatting: checklist voor een trial- of proefdeployment

1. `manifest.yaml` ingevuld, en de SP-secrets staan in Key Vault.
   - Bestaan de `CON_FMD_*`-connecties al in de tenant (bij een proef naast productie is dat zo), dan zit de identiteit achter die connecties in de admingroep, of staat hij in `security.service_principal_id` én heeft hij met de hand een rol op de domein-workspaces *(vanaf `FMD_FRAMEWORK#34` zet de setup die rol zelf)* (R12, fase 2 stap 8, fase 3 stap 1). Anders faalt de eerste load met `InsufficientPrivileges`.
2. Bootstrap in een scaffolding-workspace, daarna `NB_SETUP_FMD`, daarna `NB_SETUP_BUSINESS_DOMAINS` (§A.1).
3. Capaciteit: minimaal F2 (B-CAP-01); bij een zwaardere `spark`-sizing vooraf getoetst of `ENV_FMD` start.
4. Na elke Deployment-Pipeline-promotie: cross-workspace-verwijzingen (`PL_FMD_ORCHESTRATION`, Variable Libraries) wijzen naar de doelomgeving.
5. Validatie compleet: het semantisch model is aanwezig, de run-historie is per entiteit succesvol, en de Gold-tabellen zijn met een losse query gecontroleerd.
6. Voor bronregistratie: `NB_REGISTRATIE` (aanbevolen, per omgeving; §A.4a) of het sjabloon voor één bron in §A.4. ~~Of `PL_TOOLING_POST_ASQL_TO_FMD` voor een hele Azure SQL-bron.~~ *(Correctie 2026-10-15, `FMD_FRAMEWORK#71`. Reden: het lijstsjabloon is vervangen door het notebook, en de setup rolt `PL_TOOLING_POST_ASQL_TO_FMD` niet meer uit; gebruik `PL_FMD_DISCOVER_SOURCE`.)*

---

## Versiegeschiedenis

- v1 (2026-09-22): eerste versie.
- v2 (2026-09-25), naar aanleiding van review 1 (F3, F4, F5) en review 2 (N-F1, N-F2, N-F3, N-F5, M-F3):
  - fase 3 herschreven naar de werkelijke setup-flow (manifest, scaffolding-workspace, één run per notebook) en de werkelijke opbouw van de Variable Libraries (defaults per omgeving);
  - fase 4 stap 1: het echte Fabric-connectie-ID is verplicht;
  - deactiveringsstappen gecorrigeerd;
  - fase 7: de framework-helpers promoveren niet, extra post-deployment-controles toegevoegd, en de onbevestigde rollback-optie geschrapt;
  - Bijlage A volledig herschreven: verouderde celnummers en de handmatige connectiestap verwijderd, de SKU-eis vervangen door een open vraag, en het SQL-sjabloon herhaalbaar gemaakt met benoemde parameters, de juiste types, voorloopkomma's en invoercontroles.
- v2.1 (2026-09-25), na fork-commit `81fe912` (PR #9 en #10):
  - fase 3 stap 4 en 7, fase 6 stap 2, fase 7 stap 1 en 3, R1 en de acceptatiechecklist: de Variable Libraries hebben waarden per omgeving in value sets met een actieve value set per workspace (ADR-010), niet langer defaults per omgeving. De promotievraag is beantwoord: een promotie overschrijft defaults, maar niet de actieve value set;
  - de setup koppelt de Deployment Pipelines pas na de items en meldt ongekoppelde items; fase 7 stap 1 beschrijft het herstel.
- v2.2 (2026-09-25), review 2 M-F1/M-F2/M-R2: fase 5 stap 2 en 3 (`SourceCustomSelect` wordt niet gelezen, valkuilen van het custom notebook) en de controlequery op `DataSource.Type` in de verificatie van fase 5.
- v2.3 (2026-09-25), review 2 N-F6: R6 en fase 2 stap 3 herschreven (de setup vraagt altijd een Key Vault; de weigering van Workspace Identity is een upstream-waarneming).
- v2.4 (2026-09-25), review 2 N-F7: R8 aangevuld met de waarschijnlijke herkomst (het wiki-voorbeeld).
- v2.5 (2026-09-25), review 2 N-R1/N-R2/N-R3/N-V1: fase 6 stap 1, 3, 4 en 5 en de verificatie (Gold-notebooks niet hernoemen, `ShortcutNames` aanpassen, de refresh-cel afmaken, de demo draagt koppelingen van een andere tenant mee).
- v2.6 (2026-09-25), review 1 F8 en review 2 M-R3: fase 8 stap 3 (geen migratiescripts, schemawijziging via dacpac en setup-run) en de productie-acceptatiechecklist herschreven: elke regel toetst of iets werkt, met zeven nieuwe regels (typecontrole, doorzetting per entiteit, incrementele run in Prod, timeouts, alerting, vervaldatum van secrets, back-up en restore) en een query.
- v2.7 (2026-09-25), hertest op de lege trial (`testplan-trial.md` T-C03): R12 toegevoegd, plus fase 2 stap 8, fase 3 stap 1 (welke `security`-ID op welke workspace terechtkomt) en A.5 punt 1. Een tweede installatie in dezelfde tenant hergebruikt de bestaande connecties, en met alle `security`-ID's op nullen faalt dan elke `InvokePipeline` met `InsufficientPrivileges`. Eerder gezien op 2026-09-13, toen niet in het draaiboek beland. Verder in §A.4: het sjabloon is nu uitgevoerd (T-C01, T-C02, T-C04), en de commentaarregel en de waarschuwing over het heractiveren van gedeactiveerde entiteiten zijn gecorrigeerd (sinds PR #8 blijft zo'n entiteit uit).
- v2.8 (2026-09-26), hertest T-C06: in §A.4 wordt `@FilePath` standaard `'fmd'`. De vorige waarde `'<ns>'` gaf een dubbel landingzone-pad, omdat de view de namespace er zelf al achter zet.
- v2.9 (2026-09-26), hertest blok C–E (PR #14 t/m #21):
  - R13 toegevoegd en R4 aangescherpt.
  - Fase 4: bulkregistratie (PK-controle, alleen toevoegen), de incrementele controle en de telling via het SQL-endpoint.
  - Fase 5: één type per connectietype in oudere forks.
  - Fase 6: schema's in `VAR_GOLD_SHORTCUTS_FMD`, shortcuts pas na de eerste load, en de default-lakehouse en refresh-cel van `NB_MLV_EXAMPLE`.
  - Fase 7: controle van `Data_WorkspaceGuid`, nieuwe stap 3a (registraties en eerste load per omgeving), en de twee routes voor Direct Lake (rule of `updateDefinition`).
- v2.10 (2026-09-28), demoklant op de trial (`plan-demoklant-trial.md`): fase 7 stap 2 (selectief promoveren zonder `NB_FMD_CUSTOM_DQ_CLEANSING`) en stap 4b (volgorde promoveren → rule → opnieuw promoveren, getest in Test en Prod).
- v2.11 (2026-09-28), `testplan-trial.md` T-E04: shortcuts gaan mee met de promotie van DATA en wijzen daarna naar Silver van het doel. R3 herschreven, fase 7 stap 4a (controle in plaats van `NB_CREATE_SHORTCUTS`) en de Prod-verificatie aangepast. Fase 7 stap 2: volgorde van promoveren (T-A07b, *Missing Dependencies*).
- Aanvulling (2026-09-30), `testplan-devflow.md` F10: fase 7 stap 2 noemt nu dat `NB_FMD_CUSTOM_DQ_CLEANSING` na `FMD_FRAMEWORK#28` en de eenmalige fix gekoppeld is, zodat selectief promoveren niet meer hoeft.
- v2.12 (2026-10-05): drafts van de repo-watch verwerkt: privé-fork met GitHub-token (fase 3 stap 3 en bijlage A, PR #12) en fase 2 stap 5 naar ADR-011. Fase 3 stap 1 en 4: instellingen in cel 5 en de faalcontrole van de setup (PR #31).
- v2.13 (2026-10-06): fase 3 stap 3a, de dry-run van `NB_SETUP_FMD` (PR #36, `testplan-trial.md` T-A10).
- v2.14 (2026-10-06): fase 3 stap 5 en de verificatie: de dry-run en de faalcontrole van `NB_SETUP_BUSINESS_DOMAINS` (PR #38, review 3 P3-R2, `testplan-trial.md` T-A11).
- v2.15 (2026-10-07): fase 5 stap 2a, Snowflake als bron (`FMD_FRAMEWORK#40`, ADR-014, `testplan-trial.md` T-F01 t/m T-F05).
- v2.16 (2026-10-06/07), rookproef 2 en review 3:
  - fase 5 stap 4: plannen via `PL_FMD_ORCHESTRATION_TEMPLATE`, met een `LoadGroup` per schema (P3-B1/B2, PR #35); de faalmelding is getest, en een promotie neemt het schema mee maar niet de ontvangers;
  - fase 2 en 3: de setup maakt de workspaces en daarna de connecties, en stopt als een connectie of een item-import mislukt (P3-B3, PR #37 en #39);
  - fase 7 stap 2: één runbook voor de promotie, met DATA van een domein pas na de load in het doel (P3-R7, rookproef 2 stap 10); stap 4e: schema's en ontvangers na elke promotie (P3-R3);
  - de V-punten van review 3: statuslabels, PR #34, demo-entiteit, schema's uit het manifest, connectiestap in §A.4a, de GUID-guard in de klantfork, en de escape-beperking in Bronze (P3-V1 t/m V10, V12).
- v2.16 (2026-10-07): fase 5 stap 4, het schema op `PL_FMD_MAINTENANCE` (`FMD_FRAMEWORK#42`, ADR-015, `testplan-trial.md` T-D09).
- v2.17 (2026-10-07): fase 5 stap 2a, Snowflake in T en P getest (`testplan-trial.md` T-F06).
- v2.18 (2026-10-08), eindcontrole (`06_review/eindcontrole-2026-10-08.md`):
  - fase 3 stap 1:
    - `service_principal_id` is verplicht als de setup `CON_FMD_FABRIC_SQL` aanmaakt (E-R6);
    - `reassign_capacity` (E-V3/P3-R4);
  - fase 3 stap 3a: `fabric_domains.create`;
  - fase 7 stap 2 en 4e, en de acceptatiechecklist: het schema van `PL_FMD_MAINTENANCE` en de bewaartermijn (E-R4);
  - de checklist *Beheer*: alerting via "Failure notifications" (P3-R3);
  - §A.4a: de controles op `Environment` (E-R5, PR #49).
- v2.19 (2026-10-11), schedules per omgeving in INTEGRATION CONFIG (`FMD_FRAMEWORK#52`, ADR-017, `testplan-trial.md` T-D10; gemerged 2026-10-11, `4971d88`):
  - fase 5 stap 4: schema's en Failure notifications op `PL_FMD_SCHEDULE_<short>` in CONFIG, met de parameters `Target` en `LoadGroup`;
  - fase 7 stap 4e en de acceptatiechecklist: schema's en ontvangers vervallen als promotiestap vanaf #52.
- v2.20 (2026-10-12), `FMD_FRAMEWORK#58` (gemerged 2026-10-12, `1f12148`):
  - nieuwe namen `PL_FMD_ORCHESTRATION` en `PL_FMD_LOAD_GOLD`, behalve in eerdere correcties en deze versiegeschiedenis;
  - fase 3 stap 4: een bestaande installatie hernoemt de twee pipelines in elke stage vóór de setup-run;
  - fase 3 stap 5 en fase 6 stap 1: `PL_FMD_LOAD_GOLD` is klanteigendom; extra Gold-notebooks komen als activity in die pipeline, in Dev, en gaan mee met de promotie.
- v2.21 (2026-10-12), draft van de repo-watch van 2026-10-12 verwerkt (`FMD_FRAMEWORK#48`, `#51`):
  - fase 5 stap 2a: `VAR_FMD` behoudt variabelen die alleen in `variables.json` staan (#48);
  - §A.4a: `IsHistorized` per entiteit in de lijst en in het resultaat (#51). De sjablooncontroles van #49 en #53 stonden er al;
  - §A.4a *Gebruik*: `@Sources`/`@Entities` en `Environment=D` (#43, uit de draft van 2026-10-08). Het punt over `fabric_domains.create` uit die draft stond er al (E-V3).
- v2.22 (2026-10-12), generale repetitie GR-A3: fase 3 stap 1, `service_principal_id` moet de SP van de Key Vault-secrets zijn (PR `FMD_FRAMEWORK#59`, open).
- v2.23 (2026-10-13), generale repetitie: fase 5 stap 2b, Snowflake zonder storage integration (Delta-variant per entiteit, ADR-014 aanvulling; `FMD_FRAMEWORK` branch `feature/snowflake-delta-landing` (PR volgt)).
- v2.24 (2026-10-13), ADR-016 *Herzien*: §A.4a, historie in Silver: leeg in de lijst is nu `0` (was `1`), met het gevolg voor bestaande installaties (`FMD_FRAMEWORK` branch `feature/silver-default-zonder-historie` (`FMD_FRAMEWORK#62`)).
