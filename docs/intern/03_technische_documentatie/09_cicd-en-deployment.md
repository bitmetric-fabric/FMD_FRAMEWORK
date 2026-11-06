# CI/CD en deployment

**Fase:** 3 (Technische documentatie)
**Datum:** 2026-09-25
**Status:** Eerste versie, bijgewerkt op 2026-09-25 (Variable-Library-patroon volgens ADR-010, ADR-004 niet geïmplementeerd). *Bijgewerkt 2026-10-06 (review 3, P3-V5/V12): ADR-012 en ADR-013 verwerkt, runbook promotie in draaiboek fase 7.*
**Bron:** `output/01_kennisbasis/cicd.md`, `FMD/docs/adr/005-alleen-dev-git-gekoppeld.md` t/m `011-ontwikkelflow-repo-per-workspace.md`

**Vooraf, belangrijk:** dit is het onderwerp met de grootste onderlinge tegenstrijdigheid tussen de onderzochte bronnen. Wat hieronder staat, is het formeel vastgestelde (ADR-niveau) beeld; waar iets nog niet formeel is vastgesteld, is dat expliciet aangegeven — behandel het niet als afgesloten besluit.

## Topologie versus mechanisme — twee losse beslissingen

Er zijn twee te onderscheiden vragen, elk met een eigen ADR:

| Vraag | ADR | Status | Antwoord |
|---|---|---|---|
| **Welke workspaces** zijn git-gekoppeld? | ADR-005 | Accepted | Alleen Dev (branch `dev`); Test/Prod uitsluitend via promotie. Sluit alleen "branch per omgeving" uit. |
| **Welk mechanisme** promoot naar Test/Prod? | ADR-012 (vervangt ADR-006) | Accepted (2026-10-05) | Deployment Pipelines; fabric-cicd is een later spoor. |

## Promotiemechanisme: Deployment Pipelines (ADR-012)

*Correctie 2026-10-05: ADR-006 is gesloten door ADR-012 (besluit Mitchell 2026-10-05, PR #32, gemerged `9ae2182`): Deployment Pipelines is het promotiemechanisme, fabric-cicd een later spoor.* De tekst hieronder beschrijft de stand tot die datum.

**ADR-006 staat op status Proposed**, niet Accepted. Reden (letterlijk uit de ADR): een eerdere triage toonde dat `NB_UTILITIES_SETUP_FMD` al werkende, idempotente Deployment-Pipeline-helpers bevat (`ensure_deployment_pipeline`, `assign_deployment_pipeline_stage`, `deploy_deployment_pipeline`), waardoor het hoofdargument vóór het alternatief (fabric-cicd — "Deployment Pipelines is niet-herbruikbaar klikwerk") niet meer opgaat. De ADR-README noemt expliciet: "Sluiten na een fabric-cicd-proef op de trial-omgeving en een telling van de handmatige naloopstappen."

**Status:** vastgesteld dat dit open staat; de onderliggende keuze zelf is dus expliciet **niet** vastgesteld.

**Praktijk-default (Bitmetric):** het concept-beslisdocument noemt Deployment Pipelines expliciet als Bitmetric-default voor promotie ("alleen Dev git-gekoppeld, promotie via Deployment Pipelines") — het alternatief (branch per omgeving, code-gedreven via fabric-cicd) is overwogen maar niet gekozen, vanwege significant meer bouw- en onderhoudswerk. Een eerdere fabric-cicd-pilot voor INTEGRATION CODE is bovendien teruggedraaid: fabric-cicd pushte alleen `src/`, klantspecifieke extensies bleven ongetracked. Zie `13_referentie-implementatie-bitmetric.md` voor de commit-referenties.

**Voor een klantimplementatie:** ga uit van Deployment Pipelines als default (conform de huidige praktijk en het concept-beslisdocument), ~~maar behandel dit expliciet als een **herzienbare keuze per klant** — niet als een onwrikbaar architectuurprincipe — juist omdat de ADR zelf nog open staat.~~ *Correctie 2026-10-06 (P3-V5): ADR-012 legt Deployment Pipelines vast (Accepted, 2026-10-05). Een klant die fabric-cicd wil, is een afwijking met maatwerk (draaiboek fase 7 stap 1).*

## Waar CI/CD gehost wordt

Formeel vastgesteld via ADR-007 (Accepted) en ADR-011 (Accepted; tot 2026-09-29 ADR-008):

- **CI/CD in een eigen GitHub-organisatie**, niet Azure DevOps. Azure DevOps is expliciet overwogen en verworpen — "gelijkwaardig alternatief, verworpen op werkcomfort, niet op techniek. Heroverwegen als de GitHub-beperkingen gaan knellen."
- **Eén repository per workspace** (bijv. `<KLANT>_FINANCE_CODE`, `<KLANT>_FINANCE_DATA`), elk met `dev` als root-branch van de bijbehorende Dev-workspace. **Bijgewerkt 2026-09-30 (geautomatiseerde repo-watch):** dit was tot 2026-09-29 "één repository per klant, met een map per workspace" (ADR-008). ADR-008 is Superseded door **ADR-011** (`docs/adr/011-ontwikkelflow-repo-per-workspace.md`, commit `574029d`), na een end-to-end test van de ontwikkelflow in de klantsimulatie FMD_TRIAL (`testplan-devflow.md`, F0–F8). Reden voor de wissel: bij "map per workspace" wijzen de verwijzingen tussen workspaces na een *branch out* nog naar Dev (risico dat een developer-workspace in de gedeelde Gold schrijft), een value set per developer lekte naar Test/Prod, en items met dezelfde naam in verschillende domeinen (`LH_GOLD_LAYER`, `NB_GOLD_SHORTCUTS`, `VAR_GOLD_*`) hebben per domein een eigen logical ID, wat een domeinwissel via de API laat falen met `LogicalIdConflictDetected`. Zie de nieuwe sectie "Developer-workspaces en de repo-per-workspace-flow (ADR-011)" hieronder voor de uitwerking.
- **GitHub Free-beperking:** geen environment-secrets/approvals/branch-protection voor private repo's op de gratis laag (pas vanaf Pro/Team/Enterprise). Praktische vervanging: de Prod-deploy draait als `workflow_dispatch` met de tag als input — "geen approval-registratie, wel een bewuste handeling." *(2026-10-06, P3-V5: dit geldt alleen voor de fabric-cicd-route. Met Deployment Pipelines (ADR-012) is de Prod-deploy een handeling in de portal of via de REST API, door wie rechten heeft op de stage; GitHub doet daar geen deploy.)* Plan: starten op Free, overstappen naar Team bij ≥2 klanten.

**Status:** vastgesteld (beide ADR's Accepted).

## Developer-workspaces en de repo-per-workspace-flow (ADR-011)

*Nieuw, 2026-09-30 (geautomatiseerde repo-watch), commits `574029d`/`5d59d6a`.*

Naast de repo-structuur zelf (hierboven) regelt ADR-011 ook hoe een individuele developer isolatie krijgt zonder een eigen omgeving per persoon:

- **Generieke developer-workspaces per developer**, niet per domein: `DEV_<NAAM>_<prefix>_{DATA,CODE,SEMANTIC,REPORTING}` voor het domein waaraan de developer werkt, plus vaste `DEV_<NAAM>_<prefix>_INTEGRATION_{DATA,CODE}`. Ze hangen aan een feature-branch in de repo van hun Dev-workspace (*Branch out*).
- **Isolatie via de defaults van de Variable Libraries, niet via een value set per developer.** Een eerdere aanpak met een value set `DEV_<NAAM>` lekte via `dev` naar Test en Prod en liet een domeinwissel falen (`DependencyNotFound`) als die value set in de nieuwe branch ontbrak. De huidige aanpak zet in de developer-workspace de **defaults** van `VAR_GOLD_SHORTCUTS_FMD` en `VAR_CONFIG_FMD` op de eigen workspace-ID's (`Default value set` actief), en herbindt semantisch model en rapport aan de eigen Gold/eigen model.
- **Elke MLV-notebook met een default lakehouse krijgt twee extra cellen** (zie ook `06_BUSINESS_DOMEINEN/02_gold-laag-mlv.md`): een `%%configure`-cel die de default lakehouse uit `VAR_GOLD_SHORTCUTS_FMD` haalt, en een vangnet-cel die de notebook laat falen als hij in een `DEV_*`-workspace draait terwijl de gekoppelde Gold niet ook een `DEV_*`-workspace is — dat voorkomt dat een developer per ongeluk in de gedeelde Gold (D) schrijft.
- **`normalize-bindings` (nieuw sjabloon `templates/workspace-repo/.github/`):** elke repo met een model, rapport, lakehouse-shortcuts of library-ID's die tussen workspaces verschillen, krijgt een workflow die bij een PR naar `dev` alleen de afwijkingen *meldt* (de feature-branch blijft ongewijzigd, zodat de developer-workspace geïsoleerd blijft na een *Update from Git*), en na de merge (push naar `dev`) de bindingen automatisch terugzet naar de Dev-waarden uit `.github/fabric-bindings.dev.json`, met een eigen commit. De workflow heeft dus schrijfrechten op `dev` nodig; een branch protection op `dev` moet de bot-commit uitzonderen.
- **Het framework levert dit als `setup/NB_SETUP_DEVELOPER_WORKSPACES.ipynb`** (modes `create`, `new_feature`, `switch_domain`, `bind`), aangeroepen via `NB_BOOTSTRAP_FMD.ipynb` net als de bestaande setup-notebooks.

**Status:** vastgesteld (ADR-011, Accepted; getest in eigen omgeving, FMD_TRIAL, `testplan-devflow.md` F0–F10). Zie `03_technische_documentatie/14_ontwikkelproces.md` voor de volledige stap-voor-stap-werkinstructie (checklist, commit/PR/merge-flow, promotie, domeinwissel).

## Wat mag worden aangepast: fork versus klantrepo (B-ARCH-02)

Een terugkerende vraag bij klantimplementaties: "mogen wij dit aanpassen?" Het antwoord verschilt fundamenteel tussen de **fork** en een **klantrepo**:

| Repo | Mag frameworkcode aanpassen? |
|---|---|
| **Fork** (`bitmetric-fabric/FMD_FRAMEWORK`) | Ja, volledig — mits geclassificeerd als een van de categorieën hieronder |
| **Klantrepo's** (op basis van de FMD-template) | **Nee** — alleen configuratie (manifest, Variable Library, metadata), geen wijzigingen aan frameworkcode/-pipelines zelf |

**Categorisering van fork-wijzigingen:**

| Categorie | Betekenis | Voorbeelden |
|---|---|---|
| **A — generieke verbetering** | Upstream-PR-kandidaat; verbetert het framework voor iedereen | CI/CD-tooling, configdb-DDL-uitbreidingen, setup-notebooks, orchestratie-/Gold-templates |
| **B — Bitmetric-specifiek** | Niet bedoeld voor upstream, wel generiek binnen Bitmetric's eigen klantimplementaties | GUID-guard, RBAC-checks, monitoring-rapportages (FMD_Logging) |
| **C — referentie-implementatie** | Niet generiek — een concreet voorbeeld, geen herbruikbaar framework-onderdeel | Business-domain-specifieke Gold-laag-notebooks (bijv. `NB_MLV_DEMO_GOLD`) |

**Status:** vastgesteld (B-ARCH-02, geaccordeerd door Mitchell — "we passen de code van de originele FMD-repo zo aan dat deze geschikt is voor klantimplementaties bij Bitmetric").

**Praktisch gevolg voor een klantimplementatie:** de klant krijgt een **gefreezde fork-versie** plus een eigen configuratie-repo. Klantspecifieke wensen gaan via de voorziene extensiepunten (zie `07_extension-points.md`) of via configuratie — niet via een directe wijziging aan de gekopieerde frameworkcode. Categorie A-wijzigingen die tijdens een klantimplementatie worden gevonden (bijv. een generieke bugfix) zijn kandidaat voor een PR terug naar de fork, niet voor een losse patch in de klantrepo.

---

## Metadata-database: schemawijzigingen

**Voornemen (ADR-004, ~~Accepted, niet geïmplementeerd~~ Superseded by ADR-013 op 2026-10-05):** het metadataschema (`integration.*`) wordt beheerd via genummerde, idempotente migratiescripts (`/metadata/migrations/001_….sql`) die nooit worden gewijzigd na uitrol. Structurele metadata (bronnen, entiteiten) als seed in de repo; operationele vlaggen (`IsActive`, watermarks) alleen in de database. **Die scripts bestaan niet:** de fork heeft geen `metadata/`-map, geen migratiebestand en geen tabel die bijhoudt welke migraties zijn toegepast.

**Huidige praktijk: de dacpac.** De `.sql`-bestanden onder `src/Config_Database/` zijn de bron van `SQL_FMD_FRAMEWORK.sqlproj`. Die bouwt `src/SQL_FMD_FRAMEWORK.SQLDatabase/SQL_FMD_FRAMEWORK.dacpac`, en `.github/workflows/dacpac-guard.yml` laat een PR falen als de gecommitte dacpac niet overeenkomt met de bronnen. `NB_SETUP_FMD` importeert de dacpac (`fab import … -f`, "Creating or updating SQLDatabase"). Een schemawijziging bereikt een omgeving dus door de setup opnieuw te draaien met de nieuwe fork.

**Open vraag:** ~~wat een dacpac-import doet met een configdb waarin al data staat, is niet getest.~~ *Correctie 2026-10-06 (P3-V5):* een **additieve** wijziging op een gevulde configdb is wel getest. Elke setup-run als update importeert de dacpac op een gevulde database, zonder verlies van registraties (PR #16 op 2026-09-26, en rookproef 2). Niet getest is een **destructieve** wijziging (kolom of tabel weg). Een dacpac-publish vergelijkt het schema en past het aan; of Fabric een wijziging met dataverlies weigert of uitvoert, is niet vastgesteld. Test een schemawijziging daarom eerst op een kopie. ~~Hoe Bitmetric dit structureel wil regelen (ADR-004 alsnog bouwen of de dacpac-route vastleggen), is een open besluit.~~ *Correctie 2026-10-05: ADR-004 is vervangen door ADR-013 (besluit Mitchell 2026-10-05, PR #32, gemerged `9ae2182`): het schema loopt via de dacpac, er komen geen migratiescripts.* Vooraf een back-up of export van de configdb bij elke wijziging die bestaande kolommen of tabellen raakt. *Aanvulling 2026-10-05:* zo'n kopie maak je met een bacpac-export en een import in een nieuwe database (getest, `10_operations.md`, *Back-up en herstel van de configuratiedatabase*). Rol de nieuwe dacpac eerst op die kopie uit.

**Uitrollen en testen (toegevoegd 2026-10-06, review 3 P3-V5):**
- **Uitrollen:** ADR-013 noemt twee routes: de setup opnieuw draaien, of *"de dacpac in Dev uitrollen en daarna promoveren"*. De tweede route bestaat in deze opzet niet. De configdb is één database voor alle omgevingen (B-ENV-02) en hangt niet aan een deployment pipeline; `NB_SETUP_FMD` maakt alleen pipelines voor CODE en DATA. Gebruik dus de setup als update. De ADR zelf blijft ongewijzigd.
- **Een destructieve wijziging eerst op een kopie testen:**
  1. maak een bacpac-export van de configdb en importeer die in een nieuwe database (`10_operations.md`, *Back-up en herstel*; getest in A7);
  2. publiceer de nieuwe dacpac naar die kopie: `sqlpackage /a:Publish /sf:SQL_FMD_FRAMEWORK.dacpac /tsn:"tcp:<server>,1433" /tdn:"<kopie>" /at:<token> /p:BlockOnPossibleDataLoss=true`;
  3. controleer of de publish data zou wissen (dan stopt hij), en tel de rijen in de registratietabellen vóór en na.
  - *Aanname:* de import door de setup (`fab import` van het SQLDatabase-item) gedraagt zich als een dacpac-publish. Dat is niet getest; review 3 §4 punt 8.

**Status:** vastgesteld in code (dacpac, guard, `deploy_item`); ~~het gedrag op een gevulde database is niet getest~~ een additieve wijziging op een gevulde database is getest (setup als update), een destructieve niet *(2026-10-06)*. *Correctie 2026-09-25 (review 1 F8): de vorige versie presenteerde ADR-004 als werkend mechanisme.*

## GUID-guard (ADR-009): CI-bewaking op omgevingsspecifieke waarden

Een CI-guard (`scripts/guid_guard.py`, workflow `.github/workflows/guid-guard.yml`, allowlist `config/guid_allowlist.txt`) scant `src/` op GUID's die niet in `item_config.yaml`/`item_deployment*.json` zijn gemapt, en handhaaft daarmee ADR-003 (de generieke laag blijft vrij van klant-/omgevingsspecifieke waarden). Een hardcoded GUID die de generieke laag insluipt, faalt de CI-build.

**Status:** vastgesteld — `docs/adr/009-guid-guard.md` aanwezig, geverifieerd tegen commit `703017b`; de implementatie zelf was al aanwezig sinds commit `1e27391`.

## Privé-fork: toegang met een GitHub-token (vanaf PR #12)

Vóór fork-commit `757d5c` haalden de setup-notebooks het manifest, de `src`/`config`-zipball en de demodata altijd **anoniem** op bij `raw.githubusercontent.com`/`api.github.com`. Bij een privé-repository gaf dat een 404, ook als de uitvoerder zelf wel leesrechten had — het notebook draait in Fabric, niet in de browser van de uitvoerder, en verstuurde geen credential mee.

Sinds PR #12 kan dat wel:

- `NB_BOOTSTRAP_FMD.ipynb` krijgt twee nieuwe, optionele velden naast `repo_owner`/`repo_name`/`branch`/`folder_prefix`: `github_token_key_vault` (de Key Vault-naam) en `github_token_secret` (de secretnaam daarin, van een GitHub Personal Access Token met leesrechten op de fork). Dit is bewust de plek waar dit wordt ingevuld: `manifest.yaml` zelf moet nog worden opgehaald, dus het token kan niet uit het manifest komen.
- De bootstrap stempelt beide velden mee in `NB_SETUP_FMD` en `NB_SETUP_BUSINESS_DOMAINS`. Die notebooks halen de token-waarde op met `notebookutils.credentials.getSecret(...)` en sturen hem als `Authorization: Bearer <token>`-header mee bij het ophalen van het manifest, de `src`/`config`-zipball en (in `NB_FMD_LOAD_DEMO_DATA`) de demodata-CSV's.
- Leeg laten (de default) verandert niets: dan wordt precies als vóór PR #12 anoniem opgehaald, wat voor een publieke fork blijft werken.

**Voor een klantimplementatie:** de klantfork van het framework is doorgaans privé. Vraag bij de intake na of dat zo is, en zo ja: zorg dat er een GitHub PAT met leesrechten op die repo in de Key Vault van de klant staat, met de secretnaam bekend vóórdat `NB_BOOTSTRAP_FMD.ipynb` wordt gedraaid. Zonder token faalt de bootstrap-run op een 404 bij het ophalen van het manifest, met een expliciete foutmelding die naar een privé-repo wijst.

**Status:** vastgesteld in code (`NB_BOOTSTRAP_FMD.ipynb`, `NB_SETUP_FMD.ipynb`, `NB_SETUP_BUSINESS_DOMAINS.ipynb`, `NB_FMD_LOAD_DEMO_DATA.Notebook`, `FMD_FRAMEWORK_DEPLOYMENT.md` §4b). Genoemd als geverifieerd tijdens de hertest op de lege trial (`testplan-trial.md` T-A01, `bitmetric-fabric/FMD_TRIAL`) in de PR-omschrijving; niet apart teruggevonden als eigen testrun-referentie in `bronnen/`.

## Post-deployment handwerk (geldt ongeacht promotiemechanisme)

Twee categorieën handwerk zijn nodig **ongeacht** of Deployment Pipelines of fabric-cicd wordt gebruikt:

1. **Lakehouse-shortcuts** ~~gaan wel mee met een promotie, maar een shortcut naar een andere workspace (Gold → Silver) wordt niet omgezet. De promotie vervangt de shortcuts in de doelstage door de Dev-shortcuts, die naar Silver (D) wijzen. Draai daarom `NB_CREATE_SHORTCUTS` na elke deployment die een Lakehouse-met-shortcuts raakt.~~
   - *Correctie 2026-10-06 (review 3, P3-R7):* de shortcuts gaan mee met de promotie van DATA en wijzen daarna naar Silver van het doel. `NB_CREATE_SHORTCUTS` is alleen een terugvaloptie.
   - De promotie faalt (`CopyOverwriteResult.GenericError`) zolang een doeltabel in Silver van het doel niet bestaat (*getest in eigen omgeving*, T → P, rookproef 2 stap 10).
   - De volgorde staat in het runbook in draaiboek fase 7 stap 2. De rest van deze alinea is historisch. *Bijgewerkt 2026-09-28 (getest, `testplan-trial.md` T-E04, trial D → T):* de promotie zet de shortcuts wél om naar Silver van de doelstage, ook een nieuwe shortcut. Promoveer DATA dus gewoon; `NB_CREATE_SHORTCUTS` is na een promotie niet nodig zolang de Silver-tabellen in het doel bestaan. ~~Niet getest: T → P en een doeltabel die nog niet bestaat.~~ *(2026-10-06: beide getest in rookproef 2, zie hierboven.)* Het mechanisme erachter is getest in T-A07b (2026-09-28): een verwijzing naar een item in een andere workspace wordt omgezet naar de gekoppelde tegenhanger in de doelstage. Ontbreekt die tegenhanger, dan faalt de promotie met *Missing Dependencies*. Promoveer daarom eerst het item waarnaar verwezen wordt (`11_troubleshooting.md`). Zie `06_BUSINESS_DOMEINEN/03_shortcuts-en-deployment.md`. *Correctie 2026-09-28: hier stond "worden door geen enkel promotiemechanisme meegenomen". Dat klopt niet meer volgens Microsoft Learn (bijgewerkt 2026-08-04).*
2. **Direct Lake-pointers** in het semantisch model herbinden niet automatisch bij promotie. Zie `06_BUSINESS_DOMEINEN/04_semantisch-model-direct-lake.md`.

**Status:** vastgesteld — bevestigd in ADR-006 zelf ("geldt in beide gevallen") en in het concept-beslisdocument. *Correctie 2026-10-05: voor de shortcuts achterhaald door de test hierboven; ADR-012 neemt dat over. T → P is end-to-end geslaagd in `testplan-devflow.md` F5.*

## Variable Library-patroon (herhaling, cross-cutting)

Pipelines en notebooks lezen een Variable Library alleen uit hun eigen workspace, dus elke CODE-workspace heeft een eigen exemplaar. Vanaf fork-commit `81fe912` (ADR-010) hebben die exemplaren in alle omgevingen dezelfde definitie:
- Waarden die per omgeving verschillen, staan als override in `valueSets/<Omgeving>.json`. De waarde van de eerste omgeving uit `manifest.environments` is de default.
- Elke workspace heeft zijn eigen actieve value set (`activeValueSetName`, via `PATCH /v1/workspaces/{ws}/variableLibraries/{id}`).

De setup regelt dit met `set_variable_library_stage_values()`, voor `VAR_CONFIG_FMD` (DATA-workspace en landingzone) en `VAR_GOLD_SHORTCUTS_FMD` (Gold- en Silver-lakehouse per domein). Een promotie overschrijft de definitie in de doelstage, maar niet de actieve value set. Dat is getest op 2026-09-25 (`bronnen/notities/2026-09-25_test-variable-library-promotie.md`).

*Aanvulling 2026-10-07 (`FMD_FRAMEWORK#34`, `aaa1772`; draft van de repo-watch verwerkt):*
- **Hoe het werkt:** sinds #34 wacht `set_variable_library_stage_values()` op `updateDefinition` (202) voordat hij de actieve value set zet. Daarna leest hij per workspace de actieve value set en de geldende waarden terug. Lukt dat niet, dan probeert hij het tot drie keer, met oplopende wachttijd. Klopt een omgeving daarna nog niet, dan faalt de setup.
- **Vóór #34:** een fout gaf alleen een print, en de setup eindigde groen. In rookproef 2 (2026-10-05) stond daardoor `VAR_CONFIG_FMD` in Prod op de default (de DATA-workspace van Dev), en was `VAR_GOLD_SHORTCUTS_FMD` in Test leeg.
- **Na een promotie:** de handmatige opleverregel hieronder blijft zinvol.

**Opleverregel:** na de setup en na elke promotie: controleer per CODE-workspace (1) dat de actieve value set die van de eigen omgeving is, teruggelezen met `GET …/variableLibraries/{id}` (`/items/{id}` toont hem niet), en (2) dat ~~de override voor die omgeving niet leeg is~~ de waarde die in de actieve value set geldt niet leeg is *(2026-10-08, eindcontrole E-V3)*. Kan de setup een GUID niet opzoeken, dan schrijft hij bewust `""` en print hij een `❌`-regel. *(Correctie 2026-10-06, review 3 P3-V8: controleer de waarde die in de actieve value set **geldt**. In de eerste omgeving (Dev) staan de waarden by design in de defaults, zonder override. Vanaf `FMD_FRAMEWORK#34` controleert de setup dit zelf en faalt anders.)*

Een nieuwe variabele die per omgeving verschilt, hoort in de setup bij de waarden per omgeving. Als default gaat hij met de promotie mee, en dan wijst de doelomgeving naar Development.

**Vóór `81fe912`** schreef de setup de waarden per omgeving als default en bleven de value sets leeg. Na de eerste promotie wezen Test en Production dan naar Development. Een omgeving die met een oudere fork is opgebouwd, heeft die fout nog: draai daar de setup opnieuw met de nieuwe fork.

**Status:** vastgesteld in code (ADR-010). Het promotiegedrag is getest in een testomgeving; de volledige keten wordt getest in `testplan-trial.md` (T-A03, T-A05, T-A06).

## Samenvattend: wat dit betekent voor een klantimplementatie

1. Start met **Deployment Pipelines** als promotiemechanisme ~~(praktijk-default), maar leg dit vast als **herzienbaar per klant**, niet als vast architectuurprincipe.~~ *(ADR-012, Accepted 2026-10-05; correctie 2026-10-06, P3-V5)*. Volg het runbook in draaiboek fase 7 stap 2.
2. **Eigen GitHub-organisatie, één repo per workspace** (ADR-011, tot 2026-09-29 map-per-workspace-structuur onder ADR-008) — tenzij de klant een harde eis heeft die hiervan afwijkt (bijv. een bestaande Azure DevOps-verplichting). Bij meerdere developers: generieke developer-workspaces per developer (`NB_SETUP_DEVELOPER_WORKSPACES`) en een `normalize-bindings`-workflow per repo, zie hierboven.
3. Schemawijzigingen aan de configdb via de fork (bronbestanden, dacpac opnieuw bouwen, setup opnieuw draaien), nooit losse DDL tegen een live database. Test een destructieve wijziging eerst op een kopie (zie *Uitrollen en testen* hierboven). ~~Het gedrag van een dacpac-import op een gevulde database is niet getest. De migratiescripts van ADR-004 bestaan nog niet.~~ *(Correctie 2026-10-06, P3-V5: additief is getest; ADR-013 vervangt ADR-004, er komen geen migratiescripts.)*
4. Vertrouw op de GUID-guard om per ongeluk hardcoded omgevingswaarden in de generieke laag te voorkomen — controleer bij intake of deze guard actief is in de CI-pipeline van de klantrepo.
5. Bouw de shortcuts- en Direct-Lake-herstelstappen expliciet in als post-deployment-checklist-item, ongeacht promotiemechanisme.
6. Is de klantfork privé? Regel dan vóór de bootstrap-run een GitHub PAT in Key Vault en vul `github_token_key_vault`/`github_token_secret` in `NB_BOOTSTRAP_FMD.ipynb` in — zie *Privé-fork* hierboven.
