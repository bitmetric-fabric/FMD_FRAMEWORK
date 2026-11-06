# Ontwikkelproces: van developer-workspace tot Productie

**Fase:** 3 (Technische documentatie)
**Datum:** 2026-09-29
**Status:** in opbouw. Deze werkinstructie groeit met de test in `testplan-devflow.md`. Een stap zonder label "getest" is nog niet uitgevoerd.
**Bron:** Microsoft Learn (*Get started with Git integration*, 2026-09-08; *Development process*, 2026-07-21; *Branch workspace*, 2026-09-01), ADR-005, `testplan-devflow.md`, `testplan-trial.md` (T-A07b, T-E03, T-E04)

## Checklist in de UI

Getest in eigen omgeving (testplan-devflow F0 tot en met F8, 2026-09-29). ⌨ = nog geen UI: een script of SQL. Die stappen neemt `NB_SETUP_DEVELOPER_WORKSPACES` over (ADR-011). Het waarom en de valkuilen staan in de stappen hieronder.

**Met `NB_SETUP_DEVELOPER_WORKSPACES`** (FMD_FRAMEWORK, *getest in eigen omgeving*, testplan-devflow F10, 2026-09-29, runs `2c3cb406`, `c48584f4`, `9f669cbc`): de ⌨-stappen en het koppelen gaan via één notebook in de config-workspace.

| Checklist | Mode |
|---|---|
| 1 tot en met 4 | `create` (maakt de workspaces, neemt de rechten over, registreert INTEGRATION DATA, draait `bind`) |
| 5, zelfde domein | `new_feature` |
| 5, ander domein | `switch_domain` met `confirm_empty = True` |
| na elke *Update from Git* | `bind` |

- `new_feature` en `switch_domain` stoppen bij niet-gecommitte wijzigingen, ook als het alleen bindingen zijn. Commit eerst.
- Een afgebroken `create` of `switch_domain` kun je opnieuw draaien.
- De GitHub-token in de bootstrap-cel moet bij alle repo's per workspace kunnen (Contents: read and write). Anders: *GitHub 404 op …@dev*.
- Direct na het leeggooien houdt Fabric de naam van een verwijderd item nog enkele minuten vast; `updateFromGit` geeft dan `UnknownError`. De notebook probeert het daarom een paar keer opnieuw.

**Eenmalig per developer**
1. Maak je workspaces: in elke workspace (D) van het eerste domein, en in INTEGRATION DATA en CODE (D), *Source control → Branch out → New workspace*, met naam `DEV_<NAAM>_<PREFIX>_<TYPE>`, de capaciteit en een branch `feature/<onderwerp>` (stap 2).
2. Geef de service principals in *Manage access* dezelfde rol als op de workspace (D). ⌨ `dev_bind` kan dit ook.
3. ⌨ Registreer je INTEGRATION DATA in de configdb (`registreer_devworkspace.sql`).
4. ⌨ `dev_bind` (stap 3).

**Per feature**
5. **Start** (0 wijzigingen in *Source control*):
   - zelfde domein: *Branch out → Existing workspace*, met een nieuwe branch (stap 7);
   - ander domein: gooi je domein-workspaces leeg, koppel ze via *Workspace settings → Git integration* aan de nieuwe repo en branch, en klik *Update all* (stap 8);
   - daarna ⌨ `dev_bind`.
6. **Bouw**, van bron naar rapport (stap 4): ⌨ bron registreren voor je eigen INTEGRATION DATA → `PL_FMD_LOAD_ALL` in je eigen INTEGRATION CODE → shortcut in je eigen Gold → MLV-notebook (met `%%configure` en het vangnet) → model verversen → rapport controleren.
7. **Commit** in elke workspace met wijzigingen, ook als het alleen bindingen zijn: *Source control → Changes → Commit*.
8. **PR** op GitHub, per repo met een echte wijziging. De check `normalize-bindings` meldt de bindingen. Review, en merge met *Squash* (stap 5).
9. **Na de merge:** wacht op de commit van de bot op `dev` → ⌨ bron registreren voor (D) → `PL_FMD_LOAD_ALL` (D) → *Source control → Updates → Update all* in de Dev-workspaces (INTEGRATION, DATA, CODE, SEMANTIC, REPORTING) → MLV-notebook (D) → model (D) verversen → controleren.
10. **Promotie** naar Test, daarna naar Prod (stap 6): ⌨ bron registreren en het doel laden → *Deploy* per workspace (DATA, CODE, SEMANTIC, REPORTING; INTEGRATION CODE: selectief, zonder `NB_FMD_CUSTOM_DQ_CLEANSING`, zolang dat notebook niet gekoppeld is; zie stap 2 hieronder) → bij een nieuw model de data source rule → MLV-notebook → model verversen → controleren.
    - *Bijgewerkt 2026-10-06 (review 3, P3-R7):* de volledige volgorde staat in het runbook in draaiboek fase 7 stap 2.
    - Selectief promoveren van INTEGRATION CODE is achterhaald sinds `FMD_FRAMEWORK#28`. Rookproef 2 promoveerde hem zonder conflict D → T en T → P.
    - Vergeet na de promotie de schema's en de ontvangers van de faalmelding niet (draaiboek fase 7, stap 4e).
11. **Opruimen:** verwijder de oude feature-branch op GitHub pas als je workspaces op een nieuwe branch staan (stap 7).

## Het model in één oogopslag

```
developer-workspace (feature/<naam>)  ──commit──▶  repo, branch feature/<naam>
                                                        │ PR + review
                                                        ▼
Dev-workspace (dev)  ◀──update vanuit git──  repo, branch dev
        │
        ▼  deployment pipeline
Test  ──▶  Prod        (niet aan git gekoppeld, ADR-005)
```

- **Een repo per workspace** (keuze 2026-09-29, wijkt af van ADR-008). Voorbeeld: `FMD_TRIAL FINANCE CODE (D)` ↔ `bitmetric-fabric/FMD_TRIAL_FINANCE_CODE`, branch `dev`, root-map.
- Een developer heeft **één set generieke workspaces voor alle domeinen**, `DEV_<NAAM>_<prefix>_{DATA,CODE,SEMANTIC,REPORTING}` (keuze 2026-09-29). Je werkt aan één domein tegelijk, op een feature-branch met dezelfde naam in elke repo van dat domein. Van domein wisselen gaat via *Branch out* naar de bestaande workspace; eerst alles committen, want items die niet in git staan kunnen verloren gaan (Learn). De effecten van zo'n wissel test F7.

## Wat Fabric vastlegt (vastgesteld, Microsoft Learn)

- Een workspace is gekoppeld aan **één repo, één branch en één map** tegelijk.
- Bij de eerste koppeling kopieert Fabric de inhoud van de niet-lege kant naar de lege kant. Zijn beide gevuld, dan kies je de richting.
- Alleen een workspace-admin kan koppelen en ontkoppelen. Van branch wisselen ook, tenzij de workspace-instelling
  *Allow users with at least Contributor role to change Git branch* aanstaat.
- *Branch out* maakt een nieuwe branch van de gekoppelde branch, en een nieuwe (of bestaande) workspace die daaraan hangt.
  De bron- en de developer-workspace krijgen een relatie (zichtbaar in de workspace-boom).
- Bij branch out worden de instellingen van de bron **niet** meegenomen. Bij het wisselen van branch wordt een item dat in de
  nieuwe branch ontbreekt, verwijderd.
- Tenantinstellingen: *Users can synchronize workspace items with their Git repositories*, *… with GitHub repositories* en,
  voor branch out naar een nieuwe workspace, *Create workspaces*.
- GitHub: een fine-grained token met **Contents: Read and write** op de repo('s). Een Fabric-connectie met een repo-URL kan
  alleen die repo gebruiken; zonder URL elke repo waar het token bij kan.
- Wat niet in git staat: de data in tabellen en bestanden, en de actieve value set van een Variable Library (die is workspace-status).

## Stappen

### 1. Eenmalig: git inrichten per workspace
*Status: getest in eigen omgeving (2026-09-29, `testplan-devflow.md` F0, FINANCE D).*

1. Maak per workspace een privé-repo, met `dev` als enige en default branch, en een README zodat de branch bestaat. De API (`git/connect`) maakt geen branch of map aan.
2. Maak in GitHub een fine-grained token op alleen die repo's, met **Contents: Read and write**.
3. Maak in Fabric één connectie *GitHub – Source control* met dat token en zonder repo-URL. Dan kan één connectie alle repo's van het domein bedienen.
4. Koppel elke Dev-workspace aan zijn repo, branch `dev`, map `/`. Via de API: `POST …/git/connect` met `myGitCredentials: {source: ConfiguredConnection, connectionId}`, daarna `POST …/git/initializeConnection` met `PreferWorkspace`. Geeft dat `requiredAction = CommitToGit`, commit dan alles (`commitToGit`, mode `All`). In de portal: *Workspace settings → Git integration*.
5. Controleer met `GET …/git/status` dat `workspaceHead` gelijk is aan `remoteCommitHash` en dat `changes` leeg is.

**Wat er in git komt (getest):** alle items, inclusief de mappen van de workspace. Een SQL-endpoint staat niet apart in git, maar hoort bij zijn lakehouse. Verwijzingen naar andere workspaces staan er letterlijk in:
- het semantisch model: het SQL-endpoint van Gold (D) in `expressions.tmdl`;
- het rapport: de workspacenaam en de model-ID van SEMANTIC (D) in `definition.pbir` (`byConnection`);
- de shortcuts: `workspaceId`/`itemId` van Silver (D);
- notebooks: `default_lakehouse` en de bijbehorende workspace.

**Tip voor Windows:** zet `git config --global core.longpaths true` vóór het clonen. Zonder die instelling mist een clone van INTEGRATION CODE ongemerkt items met een lang pad (getest, F0b).

Bij een promotie worden de shortcuts en de verwijzingen naar items omgezet (T-E04, T-A07b), het semantisch model alleen via een rule (T-E03). Wat dat in een developer-workspace betekent, staat onder stap 3.

### 2. Developer-workspaces maken (branch out)
*Status: getest in eigen omgeving (2026-09-29, `testplan-devflow.md` F1).*

1. Open de Dev-workspace van het domein, klik *Source control* en dan *Branch out*.
2. Kies *New workspace* (de eerste keer) of *Existing workspace* (bij een domeinwissel, zie stap 8). Vul de naam `DEV_<NAAM>_<prefix>_<TYPE>` en de branch `feature/<naam>` in. Gebruik dezelfde branchnaam in elke repo van het domein.
3. Doe dit in de volgorde DATA, CODE, SEMANTIC, REPORTING: eerst de workspaces waar de andere naar verwijzen.
4. Resultaat: een workspace op de gekozen capaciteit, gekoppeld aan de nieuwe branch, met een relatie *Base* naar de Dev-workspace (zichtbaar in de workspace-boom en via `GET …/git/workspaceRelations`).
5. **Rechten:** branch out neemt de rechten niet over. De developer-workspace heeft alleen jou als Admin. De framework-connecties voor pipelines en notebooks werken met de SP *Fabric Metadata‑Driven Framework (FMD)*, en die moet Contributor zijn, anders faalt `InvokePipeline` met *InsufficientPrivileges*. `dev_bind` neemt de rollen van service principals over van de Base-workspace (*getest*, 2026-09-29).
6. **INTEGRATION DATA van de developer:** registreer de workspace en zijn lakehouses in de configdb met `klant/sql/registreer_devworkspace.sql` (eenmalig, *getest*). Bronnen voor je feature registreer je daarna met de `WorkspaceGuid` van die workspace.

### 3. Isolatie in de developer-workspace
*Status: getest in eigen omgeving, 2026-09-29 (testplan-devflow F2, F7).*

> **Correctie 2026-09-29 (F7):** eerst maakte `dev_bind` per developer een value set `DEV_<NAAM>`. Die lekte via `dev` naar Test en Prod, en een domeinwissel faalde met `DependencyNotFound: no such ValueSet` zodra die value set in de nieuwe branch ontbrak. Nu past `dev_bind` de defaults aan, en zet normalize ze na de merge terug.

Direct na branch out werkt de developer-workspace grotendeels op Dev:

| Item | Na branch out | Wat de developer moet doen |
|---|---|---|
| Gold-lakehouse | Eigen lakehouse, shortcuts naar Silver (D) | Niets. De MLV's zelf bouwen (Spark-views gaan niet via git) |
| Pipeline → notebooks | Eigen notebooks | Niets |
| Notebook met een default lakehouse | Gold (D) | Omzetten naar de eigen Gold |
| Variable Library | Actieve value set is de default (Dev-waarden) | De defaults op de eigen ID's zetten (`dev_bind`) |
| Semantisch model | SQL-endpoint van Gold (D) | Omzetten naar het endpoint van de eigen Gold |
| Rapport | Model in SEMANTIC (D) | Opnieuw koppelen aan het eigen model |

Het principe: **git op `dev` bevat altijd de Dev-toestand**, en wat per workspace verschilt, wordt buiten git opgelost.

**Notebooks en pipelines: via de Variable Library** (*getest*, 2026-09-29, F2 toets 1)
1. `dev_bind` (hieronder) zet in `VAR_GOLD_SHORTCUTS_FMD` (developer-CODE) en `VAR_CONFIG_FMD` (developer-INTEGRATION CODE) de **defaults** op de ID's van je eigen workspaces, met `Default value set` als actieve value set. De defaults staan in git en gaan mee in je PR. Na de merge zet normalize ze op `dev` terug naar Dev (stap 5). `Test` en `Production` blijven onaangeroerd.
2. Een oude value set `DEV_<NAAM>` ruimt `dev_bind` op: eerst inactief, dan verwijderd.
3. Een notebook met een default lakehouse krijgt als eerste cel:
   ```
   %%configure
   {"defaultLakehouse": {"name": "LH_GOLD_LAYER",
     "id": {"variableName": "$(/**/VAR_GOLD_SHORTCUTS_FMD/SourceLakehouseId)"},
     "workspaceId": {"variableName": "$(/**/VAR_GOLD_SHORTCUTS_FMD/SourceWorkspaceId)"}}}
   ```
   Hij schrijft dan in elke workspace naar de Gold van die workspace. Getest: een run in de developer-workspace bouwde de MLV's in de eigen Gold, en Gold (D) bleef ongewijzigd. Let op: `%%configure` wordt genegeerd als de notebook via `notebookutils.notebook.run` wordt gestart.
4. **Elke** MLV-notebook heeft die cel nodig: een notebook zonder, zoals `NB_GOLD_MLV_SALES` vóór F7, schrijft vanuit je developer-workspace in de gedeelde Gold (D).
5. Direct daarna een **vangnet** (*getest*, F7). In een SQL-notebook moet de cel beginnen met `%%pyspark`:
   ```
   %%pyspark
   ctx = notebookutils.runtime.context
   ws, gold_ws = ctx.get("currentWorkspaceName"), ctx.get("defaultLakehouseWorkspaceName")
   if str(ws).startswith("DEV_") and not str(gold_ws).startswith("DEV_"):
       raise RuntimeError(f"{ws} zou schrijven in de Gold van {gold_ws}: draai eerst dev_bind")
   ```
   Buiten een `DEV_*`-workspace doet het vangnet niets.
6. Controleer waar een MLV-run schreef via `_mlv_system.sys_run_metrics` in de Gold. Een ongewijzigde MLV wordt niet opnieuw geschreven, dus de tijdstippen in OneLake zeggen niets.

**Semantisch model en rapport: `dev_bind`** (*getest*, 2026-09-29, F2 toets 2)

Die kunnen geen Variable Library lezen. `dev_bind` doet de defaults (hierboven) én model en rapport. Draai het na branch out, na een domeinwissel en na elke *Update from Git* in je developer-workspace:
```
python klant/tools/dev_bind.py --developer <NAAM> --prefix <PREFIX>          # omzetten
python klant/tools/dev_bind.py --developer <NAAM> --prefix <PREFIX> --check  # alleen tonen
```
- Het model gaat naar het SQL-endpoint van je eigen Gold, het rapport naar je eigen model (Power BI *Rebind*).
- Ververs daarna het model (framen).
- In git staan model en rapport dan als *Modified*, met per item één bindingsregel. Die commit je gewoon mee: na de merge wordt hij op `dev` teruggezet (stap 5).

**Terugzetten na de merge: `normalize-bindings`** (*getest in eigen omgeving*, 2026-09-29, F7: SALES_CODE, SALES_SEMANTIC en SALES_REPORTING #1)

Elke repo met een model, rapport, lakehouse met shortcuts of library met ID's heeft onder `.github/`:
- `fabric-bindings.dev.json`: de Dev-waarden van elke binding (`semanticModels`, `reports`, `lakehouseShortcuts`, `variableLibraries`). Een nieuw model, rapport of lakehouse met shortcuts voeg je hier toe; anders faalt de check.
- `scripts/normalize_bindings.py`: `--report` meldt afwijkingen (faalt alleen bij problemen), `--fix` zet de bindingen op de Dev-waarden, `--check` faalt bij een afwijking. Alleen de waarde wordt vervangen, zodat de opmaak van Fabric blijft staan, CRLF inbegrepen.
- `workflows/normalize-bindings.yml`:
  - bij een PR naar `dev` alleen `--report`, met het script en de Dev-waarden uit `dev`. De feature-branch blijft ongewijzigd, zodat je developer-workspace geïsoleerd blijft;
  - bij een push naar `dev` (de merge) `--fix`, een commit *Bindingen tussen workspaces teruggezet naar Dev*, en daarna `--check`.

> **Correctie 2026-09-29 (F7):** eerst herstelde de workflow bij de PR, met een commit op de PR-branch. Daardoor moest een tweede run goedgekeurd worden, en kreeg je developer-workspace na een *Update from Git* stilletjes de Dev-bindingen, waarmee een notebook in Gold (D) kon schrijven.

Fabric negeert `.github/` (getest: 0 wijzigingen na een update van de Dev-workspace).

### 4. Bouwen en end-to-end testen
*Status: getest in eigen omgeving, 2026-09-29 (testplan-devflow F3: load `d0d6bcf3`, MLV `04f54381`). Voorbeeld: de feature valutanamen.*

Werk van bron naar rapport, en controleer bij elke laag dat Dev ongewijzigd blijft.

1. **Nieuwe bron (INTEGRATION):** registreer de entiteit alleen voor je eigen INTEGRATION DATA-workspace. ~~Voorbeeld: `klant/sql/registreer_feature_currency.sql`, met `@Omgevingen` = `DEV_<NAAM>_<PREFIX>_INTEGRATION_DATA`.~~ *(Correctie 2026-10-15, `FMD_FRAMEWORK#71`. Reden: een los SQL-script had geen controles en geen dry run, en dezelfde entiteit moest na de merge nog eens in de lijst.)* Gebruik `NB_REGISTRATIE`: `register(sources, entities, domain="INTEGRATION", environments=["DEV_<NAAM>"], dry_run=True)`, en daarna met `dry_run=False`.
   - `DEV_<NAAM>` zoekt de workspace `DEV_<NAAM>_<PREFIX>_INTEGRATION_DATA` en gebruikt de bronbindingen van D. *Getest in eigen omgeving* (2026-10-15, trial-Dev, de procedure via `sqlcmd`, zie `testplan-trial.md` T-C11). De notebookroute zelf is niet gedraaid.
   - De workspace moet al in de configdb staan (`sp_UpsertWorkspace` en `sp_UpsertLakehouse`, bijvoorbeeld met `klant/sql/registreer_devworkspace.sql`). Dit werkt alleen voor `domain="INTEGRATION"`: de DATA-workspace van een business domain heet `DEV_<NAAM>_<PREFIX>_DATA`, zonder domeinnaam, en heeft geen landing zone.
   - De registratie staat in de configdb, niet in git. ~~Bewaar het script bij de feature; bij de merge draai je het voor (D), (T) en Prod (stap 5).~~ Je gebruikt dezelfde lijst in `NB_REGISTRATIE` voor de hele feature: `["DEV_<NAAM>"]` tijdens de feature, `["D"]` na de merge, en `["T"]` en `["P"]` vlak voor de promotie (stap 5 en 6).
   - De `DataSource`-rijen worden gedeeld met D. Een gewijzigde `LoadGroup` of `Namespace` vanuit een `DEV_`-run geldt dus ook voor D. Na de merge blijven je `DEV_`-rijen actief in de configdb staan; ze worden alleen in jouw developer-workspace geladen, maar ze stapelen zich op.
   - Start `PL_FMD_LOAD_ALL` in je eigen INTEGRATION CODE. Via `VAR_CONFIG_FMD` (defaults op je eigen ID's) laadt hij in je eigen lakehouses. Er worden alleen entiteiten geladen die voor jouw workspace geregistreerd zijn.
2. **Shortcut in je eigen Gold:** laat een nieuwe tabel naar je eigen Silver wijzen, de bestaande tabellen naar Silver (D). Die gedeelde data lees je alleen, en je hoeft niet alles zelf te laden. Normalize zet bij de PR alle shortcuts naar Silver (D).
3. **Gold (MLV-notebook):** pas de notebook aan in je eigen CODE en draai hem. Via `%%configure` (stap 3) schrijft hij in je eigen Gold.
   - Controle via het SQL-endpoint: eerst `refreshMetadata`. Let op: de MLV's staan daar in kleine letters (`gold.d_currencyrate`), en het endpoint is hoofdlettergevoelig.
4. **Model:** pas het aan in je eigen SEMANTIC (portal, Power BI Desktop of `updateDefinition`). Ververs het, en controleer het met een DAX-query.
5. **Rapport:** pas het aan in je eigen REPORTING. Draai daarna `dev_bind --check`: het rapport moet naar je eigen model wijzen, en het model naar je eigen Gold.

Alles wat je hier wijzigt (items, defaults van de libraries, bindingen) staat in `git/status` als *Modified*, en gaat in stap 5 mee.

### 4b. Alleen model en rapport
*Status: getest in eigen omgeving, 2026-09-29 (testplan-devflow F9).*

Voor een wijziging die geen nieuwe data in Gold nodig heeft: een maat, een kolom die al in Gold staat, een relatie, een rapportpagina.

1. Zet alleen je SEMANTIC- en/of REPORTING-workspace op een nieuwe branch (stap 7; bij een ander domein eerst leeggooien, stap 8). Je DATA, CODE en INTEGRATION blijven waar ze zijn, eventueel op een ander domein.
2. `dev_bind`. Het model blijft op Gold (D): lezen uit Dev is veilig, en je werkt met de echte Dev-data. Het rapport gaat naar je eigen model. `dev_bind` koppelt het model alleen aan je eigen Gold als je DATA bij hetzelfde domein hoort en die Gold gebouwd is.
3. Wijzig het model of rapport, ververs het model, en controleer met DAX of in de browser.
4. Commit beide workspaces. Een PR alleen voor de repo met de echte wijziging. Omdat het model op Dev bleef, meldt de check *Alle bindingen staan op Dev*.
5. Na de merge: *Update from Git* in SEMANTIC (D) en/of REPORTING (D), model (D) verversen, promoveren (alleen die workspaces). Registreren, laden en een MLV-run zijn niet nodig.

Alleen het rapport? Dan alleen REPORTING, en het rapport mag op het model (D) blijven.
Heeft je modelwijziging een kolom of tabel nodig die nog niet in Gold (D) staat, dan heb je de hele keten nodig (stap 4).

### 5. Commit, pull request en merge naar `dev`
*Status: getest in eigen omgeving, 2026-09-29 (testplan-devflow F4 en F7).*

1. **Commit** vanuit elke developer-workspace met wijzigingen naar je feature-branch (*Source control → Commit*, of `commitToGit`). De bindingen naar je eigen workspaces gaan gewoon mee.
   - Commit ook de workspaces waarin **alleen** bindingen gewijzigd zijn (model, rapport, defaults). Een PR is voor die repo's niet nodig: na de merge zou er netto niets veranderen. Maar een volgende wissel (stap 7 en 8) eist 0 wijzigingen (*getest*, F8).
2. **Een PR per repo** naar `dev`. `normalize-bindings` meldt welke bindingen na de merge worden teruggezet (*wijkt af van Dev (wordt na de merge teruggezet)*). Controleer in de diff dat er verder alleen je feature in staat.
3. **Merge** (squash) pas na review. De Action zet op `dev` de bindingen terug, met een eigen commit. Je feature-branch en je developer-workspace blijven ongewijzigd en geïsoleerd.
4. **Na de merge**, in deze volgorde:
   - wacht op de commit *Bindingen tussen workspaces teruggezet naar Dev* op `dev`;
   - registreer nieuwe bronnen in de configdb voor (D), en laad (D). Registreer (T) en Prod pas vlak vóór de promotie naar die omgeving, en laad ze dan ook. *(Bijgewerkt 2026-10-15: met `NB_REGISTRATIE` en dezelfde lijst als tijdens de feature, `environments=["D"]`, later `["T"]` en `["P"]`.)*;
     *Waarom:* welke tabellen geladen worden, staat als rijen in de gedeelde configdb, met een rij per omgeving. Git en de deployment pipeline nemen die rijen niet mee, en de dacpac bevat alleen het schema (*vastgesteld*). Dit is nu een handmatige stap. Een geautomatiseerde variant is een open punt (testplan-devflow, F5).
   - pas daarna *Update from Git* in de Dev-workspaces: INTEGRATION, DATA, CODE, SEMANTIC, REPORTING. Een shortcut in Gold (D) wijst anders naar een Silver-tabel die nog niet bestaat.

   **Waarom eerst laden en dan pas bijwerken of promoveren** (geldt voor elke omgeving):
   - De nieuwe shortcut in Gold wijst naar de nieuwe Silver-tabel. Bestaat die nog niet, dan wijst hij naar niets. Of de update of promotie dan faalt, of een kapotte shortcut aanmaakt, is niet getest (*aanname*).
     - *Bijgewerkt 2026-10-06 (rookproef 2):* een **promotie** faalt dan (`CopyOverwriteResult.GenericError`, *getest in eigen omgeving*, T → P; `11_troubleshooting.md`). Wat een Git-update in die situatie doet, blijft niet getest.
   - De nieuwe MLV-code doet een join met die tabel. Een MLV-refresh vóór de load faalt. Dan worden ook de afgeleide Gold-tabellen niet bijgewerkt (`F_SalesVsTarget` gebruikt `D_CurrencyRate`), en toont het rapport oude of geen data (*vastgesteld* uit `NB_GOLD_MLV_FINANCE`).
   - Het is dezelfde regel als bij de volgorde van promoveren: eerst wat verwezen wordt, dan wat verwijst.
   - Strikt nodig is het niet: je kunt ook eerst promoveren en daarna laden, zolang de MLV en het model in de tussentijd niet ververst worden. In Prod draaien geplande refreshes, dus daar laad je altijd eerst.
   - `PL_FMD_LOAD_ALL` laadt alle actieve entiteiten, ongeveer 20 minuten (*getest*, 2026-09-29: runs `dcebf05e`, `8132ff70`, `9f493dec`). Een manier om alleen de nieuwe entiteit te laden valt onder het open punt over de registratie (testplan-devflow, F5).

### 6. Promotie naar Test en Prod
*Status: getest in eigen omgeving, 2026-09-29 (testplan-devflow F5): D → T → P met de feature valutanamen. In elke omgeving wezen alle verwijzingen naar die omgeving, en de DAX-controle gaf overal hetzelfde resultaat.*

Per doelomgeving, in deze volgorde:
1. Registreer de nieuwe bronnen voor de doelomgeving (`NB_REGISTRATIE`, `environments=["T"]` of `["P"]`), en draai daar `PL_FMD_LOAD_ALL` (zie stap 5, *Waarom eerst laden*).
2. Promoveer in de portal alleen de workspaces met wijzigingen, in de volgorde DATA, CODE, SEMANTIC, REPORTING. INTEGRATION CODE sla je over als daar niets aan de code is veranderd. Promoveer je hem wel en staat `NB_FMD_CUSTOM_DQ_CLEANSING` niet gekoppeld in de pipeline (installatie zonder `FMD_FRAMEWORK#28` of de eenmalige fix), doe dat dan selectief, zonder dat notebook. *Bijgewerkt 2026-09-30:* in FMD_TRIAL is het notebook gekoppeld (D → T → P, *vastgesteld*) en is selectief niet meer nodig; ~~een volledige promotie daarna is niet apart getest~~ *(2026-10-06: in rookproef 2 slaagde INTEGRATION CODE D → T `5ef928ff` en T → P `ab159a08` op een schone setup)* (`11_troubleshooting.md`).
   - *Bijgewerkt 2026-10-06 (P3-R7):* "alleen DATA, CODE, SEMANTIC, REPORTING" volstaat alleen als er niets nieuws te laden is. Komt er een entiteit bij, volg dan het runbook in draaiboek fase 7 stap 2: eerst registreren en laden in het doel, en pas daarna DATA.
3. Draai de MLV-notebook in de doel-CODE. Ververs **daarna** het model. Andersom faalt de refresh, omdat een nieuwe modelkolom nog niet in Gold staat.
4. Controleer het model met een DAX-query, en bekijk het rapport.

Wat de promotie zelf regelt (getest, F5):
- De actieve value set blijft staan (`Test`, `Production`).
- De default lakehouse van de notebook wordt omgezet naar de Gold van het doel.
- Nieuwe shortcuts wijzen naar de Silver van het doel.
- De data source rule van het model blijft werken.

- Een verwijzing naar een item in een andere workspace wordt bij promotie omgezet naar de gekoppelde tegenhanger. Ontbreekt die, dan faalt de promotie met *Missing Dependencies* (getest, T-A07b).
- Shortcuts gaan mee met de promotie van DATA en wijzen naar Silver van het doel (getest, T-E04).
- Direct Lake-modellen: één data source rule per model per stage, alleen in de portal (getest, T-E03).

### 7. Opruimen
*Status: getest in eigen omgeving, 2026-09-29 (testplan-devflow F6).*

- **Na de merge blijft je developer-workspace op de feature-branch staan.** Verwijder een branch waar nog een workspace aan hangt niet: dat breekt de git-koppeling van die workspace.
- **Bij de volgende feature in hetzelfde domein:** zet je developer-workspaces op een nieuwe branch vanaf `dev`. Dat kan met een branch out in de portal naar je bestaande workspace, of via de API: branch aanmaken, `git/disconnect`, `git/connect`, `initializeConnection` (PreferRemote), `updateFromGit` en de relatie `Base` (*getest*, F8, INTEGRATION). Er is geen conflict, want de logical ID's zijn gelijk. Daarna `dev_bind`.
- **Bij een ander domein:** zie stap 8.
- **Pas daarna** verwijder je de oude branch. Controleer vooraf:
  - dat er geen workspace meer aan hangt (`git/connection` van je developer-workspaces);
  - dat alles in `dev` zit. Een squash-merge maakt de branch in git niet 'gemerged', dus kijk naar de gemergede PR, of naar *ahead 0* in `compare/dev...<branch>`.
- Verwijder ook hulpbranches, zoals opruim-PR's, zodra ze gemerged zijn. GitHub bewaart een verwijderde branch nog een tijd, dus je kunt hem terughalen.

### 8. Domeinwissel
*Status: getest in eigen omgeving, 2026-09-29 (testplan-devflow F7: FINANCE → SALES via de portal; F8: SALES → FINANCE via de API, met leeggooien).*

> **Aanvulling 2026-09-29 (F8): de voorkeursroute is leeggooien.** Via de API faalt een wissel naar een ander domein met `LogicalIdConflictDetected`. Items met dezelfde naam (`LH_GOLD_LAYER`, `NB_GOLD_SHORTCUTS`, `VAR_GOLD_*`) zijn per domein apart aangemaakt en hebben elk een eigen logical ID, en de API kiest niet. Leeggooien voorkomt dat, en ruimt meteen de verweesde MLV's op.

**Voorkeur: leeggooien (API, de basis voor `switch_domain` in de setup-notebook)**
1. **Controle:** in DATA, CODE, SEMANTIC en REPORTING is `git/status` 0 wijzigingen, en head is gelijk aan remote. Zo niet, dan stop je. Een item dat niet in git staat, telt ook als wijziging.
2. **Loskoppelen en leeggooien**, in de volgorde REPORTING, SEMANTIC, CODE, DATA. De workspace zelf blijft staan, met capaciteit, rechten en instellingen. De SQL-endpoint gaat mee met het lakehouse.
3. **Koppelen** aan de nieuwe branch (vanaf `dev` van het nieuwe domein), in de volgorde DATA, CODE, SEMANTIC, REPORTING: `initializeConnection` (PreferRemote) en `updateFromGit`. Bij een lege workspace laat je `workspaceHead` weg; `null` geeft `UnknownError`. Daarna de relatie `Base`.
4. **`dev_bind`:** het nieuwe lakehouse heeft een nieuw ID.
5. **De MLV-notebook draaien** om je eigen Gold op te bouwen. De shortcuts komen uit git. Ververs daarna het model.
6. De INTEGRATION-workspaces horen niet bij een domein: die zet je alleen op een nieuwe branch (stap 7).

**Alternatief: branch out in de portal** (F7). Die behoudt de items met dezelfde naam, inclusief je Gold-data, maar laat de MLV's van het oude domein verweesd achter:

1. **Vooraf:** commit alles. (Een oude value set `DEV_<NAAM>` moest je eerst op inactief zetten, anders faalde de wissel met `DependencyNotFound`. Met de huidige `dev_bind` bestaat die niet meer.)
2. **Branch out** vanuit elke workspace van het nieuwe domein (D) naar je **bestaande** `DEV_<NAAM>_<prefix>_<TYPE>`, met een nieuwe feature-branch.
   - Items met dezelfde naam in beide domeinen houden hun ID (`LH_GOLD_LAYER`, `NB_GOLD_SHORTCUTS`, `VAR_GOLD_*`). Items die alleen in het oude domein bestonden, worden verwijderd.
   - De shortcuts in je Gold worden vervangen door die van het nieuwe domein.
3. **`dev_bind`** opnieuw: de defaults, het model en het rapport van het nieuwe domein.
4. **Verweesde MLV's opruimen:** de MLV's van het oude domein blijven in je Gold staan, want Spark-objecten gaan niet via git. Hun bronnen zijn weg. Gooi ze weg met `DROP MATERIALIZED LAKE VIEW`, in een notebook met `%%configure` naar je eigen Gold.
5. **Controleer** of de MLV-notebooks van het nieuwe domein `%%configure` en het vangnet hebben (stap 3). Zo niet, voeg ze toe; dat is een wijziging die mee mag naar `dev`.
6. De relatie `Base` (`git/workspaceRelations`, preview) is na een wissel niet betrouwbaar: soms staat hij er, soms niet. `dev_bind` neemt de rechten dan niet over. Wat er al stond, blijft staan.
