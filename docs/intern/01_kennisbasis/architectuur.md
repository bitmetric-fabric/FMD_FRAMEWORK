# Architectuur

Legenda status: `vastgesteld` (expliciet zo gesteld in de bron) · `getest in eigen omgeving` (expliciet beschreven als getest/gevalideerd bij Bitmetric) · `aanname` (afgeleid, niet expliciet) · `open vraag` (onduidelijk, tegenstrijdig of ontbrekend) · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

## Repository- en versiestrategie

- **Punt:** Het framework wordt uitgerold als GitHub *template repository* (`gh repo create --template`), niet als fork per klant; klantrepo's hebben geen upstream-koppeling.
  **Bron:** `FMD/docs/adr/001-template-repository.md` (ADR-001, Accepted). **Status:** vastgesteld.
- **Punt:** Een klantimplementatie neemt na oplevering géén framework-updates meer over. Enige uitzonderingspad: `git remote add framework … && git cherry-pick <sha>`, gevolgd door de normale route naar Test/Prod (met migratiescript bij schemawijziging).
  **Bron:** `FMD/docs/adr/002-geen-updates-naar-bestaande-implementaties.md` (ADR-002, Accepted). Trigger tot heroverweging: ±5 klanten met supportafspraak, of 3× dezelfde fix handmatig overgezet. **Status:** vastgesteld.
- **Punt:** De generieke laag (Landingzone/Bronze/Silver) mag geen klant- of omgevingsspecifieke waarden bevatten. Alles wat per klant/omgeving verschilt gaat naar precies één van drie bestemmingen: **manifest** (alleen vóór oplevering), **variable library** (per omgeving), **metadata `integration.*`** (tijdens gebruik).
  **Bron:** `FMD/docs/adr/003-generieke-laag-vrij-van-klantcode.md` (ADR-003, Accepted). **Status:** vastgesteld.
- **Punt:** Het metadataschema (`integration.*`) wordt beheerd via genummerde, idempotente migratiescripts (`/metadata/migrations/001_….sql`), nooit gewijzigd na uitrol. Structurele metadata (bronnen/entiteiten) is seed-in-repo/PR-reviewbaar; operationele vlaggen (IsActive, watermarks) blijven database-only.
  **Bron:** `FMD/docs/adr/004-metadata-migratiescripts.md` (ADR-004, Accepted). **Status:** vastgesteld. *Correctie 2026-10-05: ADR-004 is vervangen door ADR-013 (besluit Mitchell 2026-10-05, PR #32, gemerged `9ae2182`): het schema loopt via de dacpac, er komen geen migratiescripts.*
  **Correctie (2026-09-25, review 1 F8):** ADR-004 is Accepted, maar niet geïmplementeerd: er bestaan geen migratiescripts. In de praktijk gaat een schemawijziging via de dacpac en een nieuwe setup-run. Zie `03_technische_documentatie/09_cicd-en-deployment.md`.
- **Punt:** Alleen de Dev-workspace is git-gekoppeld (branch `dev`); Test/Prod uitsluitend via promotie. Feature-workspaces: branch vanuit `dev` → tijdelijke workspace → PR terug → sync origineel → opruimen.
  **Bron:** `FMD/docs/adr/005-alleen-dev-git-gekoppeld.md` (ADR-005, Accepted). Deze ADR sluit alléén "branch per omgeving" uit en laat zowel Deployment Pipelines als fabric-cicd als promotiemechanisme open (dat is ADR-006, zie `cicd.md`). **Status:** vastgesteld.

## Workspace-topologie en naamgeving

- **Punt:** Business-domeinen (INTEGRATION verplicht + optioneel FINANCE/SALES/HR) × workspace-typen (CODE/DATA/SEMANTIC/REPORTING, niet elk domein heeft alle vier) × omgevingen (D/T/A/P) bepalen het aantal workspaces; elke workspace heeft een eigen Deployment Pipeline, rechtenmodel en Variable Library.
  **Bron:** `FMD/docs/adr/008-repo-en-mapstructuur.md`, sectie Context. **Status:** vastgesteld.
- **Punt:** Werkelijke workspace-naamgeving in de eigen tenant is `[DOMEIN] [LAAG] ([OMG])`, bv. `FINANCE DATA (D)`, `FINANCE DATA (P)`, `SALES CODE (D)`, `INTEGRATION CODE (D)` — dit is een live-observatie via de Fabric MCP-server, niet alleen een intentie.
  **Bron:** `bronnen/claude-code-transcripten/markdown/2026-08-28_is-fabric-mcp-verbonden.md` (tenant-scan) + bevestigd in setup-notebook-cellen (`' DATA (T)'`, `' CODE (T)'`) volgens `bronnen/claude-code-transcripten/markdown/2026-09-15_fmd-framework-afwijkingen-triage.md` §2.4. **Status:** getest in eigen omgeving.
  **Update (opgelost in Fase 2):** het concept-beslisdocument stelde als Bitmetric-*default* eerder een ánder patroon voor (`{DOMEIN}_{TYPE}_{OMGEVING}`, bv. `FINANCE_DATA_D`) — tegenstrijdig met wat feitelijk al in de eigen tenant/code stond. Dit is inmiddels een formeel besluit (**B-ARCH-01**, `02_beslisdocument/02_beslisregister.md`): de bestaande praktijk `[DOMEIN] [LAAG] ([OMG])` is bevestigd als standaard (Mitchell, OV-01, 2026-09-21), inclusief de regel dat Productie geen OMG-suffix krijgt. Het onderstrepingspatroon is expliciet verworpen. Niet langer een open vraag.
  **Update 2 (2026-09-23):** de bovenstaande `FINANCE DATA (P)`-observatie was op het moment van de tenant-scan feitelijk correct, maar de setup-notebook-code voegde toen inderdaad nog een `(P)`-suffix toe voor Productie — in tegenspraak met het net genoemde besluit. Dit gat is gedicht via PR #5, "Production-workspaces krijgen geen omgevingsmarker in de naam" (commit `f669a74`, 2026-09-22): een nieuwe `ws_suffix()`-helper zorgt dat nieuw aangemaakte of opnieuw uitgerolde Productie-workspaces voortaan zonder `(P)`-suffix heten. Reeds bestaande Productie-workspaces in de tenant (zoals de hierboven genoemde `FINANCE DATA (P)`) behouden hun huidige naam tot ze hernoemd of opnieuw uitgerold worden — zie `open-vragen.md` OV-01 en `02_beslisdocument/02_beslisregister.md` B-ARCH-01.
  **Bron 2:** `bronnen/chats-ruw/2026-09-16_fmd-implementatiekeuzes-en-gevolgen_bijlage-beslisdocument.md`, sectie 4.3.
- **Punt:** Manifest-structuur (`repository`, `naming`, `environments[]` met naam/short/capacity, `config_workspace`, `spark`, `shortcuts`, `framework.lakehouse_schema_enabled`, `security`, `key_vault`) is de enige plek voor per-klant-vaste configuratie; vier value sets (Development/Test/Acceptance/Production) worden altijd meegeleverd, het manifest bepaalt welke actief zijn en in welke volgorde (= stage-volgorde van de Deployment Pipeline).
  **Bron:** `FMD/manifest.example.yaml` (volledig bestand). **Status:** vastgesteld.

## Setup en deployment van het framework zelf

- **Punt (opgelost, 2026-09-22):** `docs/adr/README.md` vermeldde **ADR-009** (GUID-guard) als status "Accepted" in de indextabel, maar het bestand `docs/adr/009-guid-guard.md` ontbrak destijds op de onderzochte locatie. Dit is inmiddels opgelost: `docs/adr/009-guid-guard.md` staat op de conventionele plek (commit `703017b`, "Add ADR-009 (#6)"), consistent met de indextabel. De GUID-guard-implementatie zelf (`scripts/guid_guard.py`, `.github/workflows/guid-guard.yml`, `config/guid_allowlist.txt`) stond al eerder in de repo (commit `1e27391`).
  **Bron:** `FMD/docs/adr/009-guid-guard.md` + `FMD/docs/adr/README.md`, commit `703017b`. **Status:** vastgesteld — geen discrepantie meer.
