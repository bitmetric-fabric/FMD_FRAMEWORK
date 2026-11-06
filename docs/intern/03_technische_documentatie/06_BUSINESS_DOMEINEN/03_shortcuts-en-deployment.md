# Shortcuts naar Silver en de Deployment-Pipeline-beperking

**Bron:** `FMD/src/business_domain/NB_CREATE_SHORTCUTS.Notebook`, `VAR_GOLD_SHORTCUTS_FMD.VariableLibrary`, `VAR_GOLD_CODE_FMD.VariableLibrary` (fork-code, eigen inspectie 2026-09-22); aanvullend `output/01_kennisbasis/gold-en-semantic.md`, projectinstructies
**Status:** zie per punt — nu grotendeels code-geverifieerd

## Het patroon

De Gold-laag van een business-domein (bv. FINANCE DATA's `LH_GOLD_LAYER`) leest via **Lakehouse-shortcuts** de Silver-laag van INTEGRATION DATA, in plaats van data te dupliceren. Deze shortcuts worden aangemaakt/hersteld via een apart notebook: `NB_CREATE_SHORTCUTS`.

**Status:** vastgesteld.

### Hoe `NB_CREATE_SHORTCUTS` het daadwerkelijk doet (code-geverifieerd)

*Correctie 2026-10-29 (reden: `FMD_FRAMEWORK#79`, `b295a14`; *vastgesteld* in `NB_CREATE_SHORTCUTS` op `origin/main`): `ShortcutNames` is sindsdien standaard leeg en het notebook maakt dan één schema-shortcut per Silver-schema, zie de sectie "Schema-shortcuts" hieronder. De alinea hieronder beschrijft de stand vóór #79 en geldt nu alleen bij een gevulde lijst.*

Het notebook itereert over een lijst tabelnamen (`ShortcutNames`) en roept per tabel de Fabric REST API aan. **Die lijst is hardcoded en bevat negen WWI-demotabellen** (`Sales_BuyingGroups`, `Sales_CustomerCategories`, `Sales_InvoiceLines`, `Sales_Invoices`, `Sales_Orders`, `Sales_OrderLines`, `Sales_vCustomers`, `Warehouse_PackageTypes`, `Warehouse_StockItems`). Pas hem per domein aan, in de fork of in de CODE-workspace van het domein:

```
POST https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{lakehouse_id}/shortcuts
```

geauthenticeerd via `notebookutils.credentials.getToken("pbi")`, met `shortcutConflictPolicy=CreateOrOverwrite`. Alle bron-/doelparameters komen uit `notebookutils.variableLibrary.getLibrary("VAR_GOLD_SHORTCUTS_FMD")` — geen hardcoded GUID's in het notebook zelf.

**⚠️ In forks van vóór PR #31 slaagt het notebook ook als geen enkele shortcut wordt aangemaakt.** `create_shortcut` print bij een fout alleen `Failed: <status> <tekst>` en gaat door; er wordt niet geraised. Een groene run bewijst dan niets: controleer de celoutput op `Failed:` en controleer of de shortcuts in de Gold-lakehouse bestaan (`GET …/items/{lakehouse}/shortcuts`, of in de portal).

*Bijgewerkt 2026-10-06 (PR `FMD_FRAMEWORK#31`, gemerged 2026-10-05, squash `2e2155a`):* `create_shortcut` geeft nu terug of de POST met 200/201 antwoordde. Het notebook verzamelt de mislukte namen en eindigt met `RuntimeError: N of M shortcuts failed: [...]`. Een shortcut die niet lukt, laat de run dus rood eindigen, met de namen erbij. Voor een fork van vóór PR #31 blijft de handmatige controle hierboven nodig.

**Status:** vastgesteld (letterlijk overgenomen uit `notebook-content.py`). *Aangevuld 2026-09-25 (review 2 N-R2): de hardcoded demolijst en het ontbreken van foutafhandeling.*

### Schema-shortcuts: geen tabellenlijst meer (PR `FMD_FRAMEWORK#79`, gemerged 2026-10-20, squash `b295a14`)

*Aangevuld 2026-10-20 (reden: bij de klant moest elke nieuwe Silver-tabel met de hand in `ShortcutNames`).*

Met PR #79 is `ShortcutNames` standaard leeg. Bij een lege lijst maakt het notebook voor elk schema in Silver (behalve `dbo`) één **schema-shortcut** in Gold, met dezelfde naam: `path: "Tables"`, doel `Tables/<schema>`.
- Een tabel die later in Silver bijkomt, verschijnt vanzelf in Gold. Een nieuwe run is alleen nodig voor een nieuw Silver-schema (een nieuwe bron-namespace). *Aanname*: dit volgt uit de werking van een shortcut op een map, maar het is niet apart getest.
- Een gevulde `ShortcutNames` werkt zoals voorheen, per tabel. Dat is nodig voor lakehouses zonder schema's. `SourceSchema` en `Shortcut_TargetSchema` gelden alleen in die modus.
- Een MLV zet je in een eigen Gold-schema (bijvoorbeeld `gold`), niet in een schema-shortcut. Een schema-shortcut is een verwijzing naar Silver, je kunt er niets in schrijven.
- Een installatie met per-tabelshortcuts in Gold (bijvoorbeeld `Tables/aw/<tabel>`) moet die eerst weghalen. *Aanname:* een schema-shortcut met dezelfde naam als een bestaand schema faalt.

**Status:** getest in eigen omgeving, 2026-10-20 (`testplan-trial.md` T-E07):
- **Klant-dev:** handmatige schema-shortcut `anva`. Alle tabellen zichtbaar, 4.625.101 rijen in `anva.ODS_FACTUUR` via het SQL-endpoint.
- **Trial:** het nieuwe notebook naar een tijdelijke Gold-lakehouse. Runs `a0d88d73` en `891c0e8e` waren `Completed`, met vier schema's en `dbo` overgeslagen.
- **Promotie:** FINANCE DATA D → T met een schema-shortcut `sf` (operatie `44633f97`, `Succeeded`). In Gold (T) wijst `sf` naar Silver (T) en de tabellen zijn zichtbaar. Een schema-shortcut wordt dus omgezet zoals een per-tabelshortcut (zie hieronder). Testshortcut daarna verwijderd.
- **Niet getest:** T → P, en een MLV op tabellen achter een schema-shortcut.

## Shortcuts bij promotie

*Correctie 2026-09-28 (reden: Microsoft Learn is bijgewerkt). Hier stond: "Lakehouse-shortcuts worden niet meegenomen door Deployment Pipelines (Microsoft Learn)". Dat geldt niet meer.*

Wat Microsoft Learn nu zegt (*Lakehouse git integration and deployment pipelines*, bijgewerkt 2026-08-04; *Assign variables to shortcuts*):
- Shortcuts horen bij de definitie van de lakehouse (`shortcuts.metadata.json`). Git en Deployment Pipelines nemen ze mee (GA).
- Een OneLake-shortcut naar een doel in **dezelfde** workspace wordt bij een promotie omgezet naar de doelstage.
- Moet een shortcut per stage ergens anders naar wijzen, dan koppel je een eigenschap van de shortcut (doel, connectie) aan een variabele uit een Variable Library. Dat kan alleen via *Manage shortcut* in de portal, niet via de REST API.
- De doeltabellen worden niet aangemaakt. Een shortcut is pas geldig als het doel bestaat.
- **Een promotie vervangt alle shortcuts in de doel-lakehouse door die van de bron.**

**Status:** vastgesteld (Microsoft Learn); niet getest in eigen omgeving.

**Getest 2026-09-28 (`testplan-trial.md` T-E04 deel 1 en 1b, trial, FINANCE D → T, operaties `99aef0f1` en `ac49239f`):** een promotie van de DATA-workspace zet de Gold → Silver-shortcuts **wel** om naar Silver van de doelstage. Dat gold ook voor een nieuwe shortcut die alleen in Dev bestond. Na de promotie gaf de pipeline *Same as source*, hoewel D naar Silver (D) wijst en T naar Silver (T). Dit gaat verder dan Microsoft Learn, dat alleen omzetten binnen dezelfde workspace noemt.
- *Aanname:* het werkt doordat INTEGRATION DATA in zijn eigen deployment pipeline gekoppeld is, hetzelfde patroon als bij Invoke Pipeline (T-A07).
- *Niet getest:* T → P, en een promotie op een moment dat de Silver-tabel in het doel nog niet bestaat. *Bijgewerkt 2026-10-05:* T → P is end-to-end geslaagd in de ontwikkelflow-test (`testplan-devflow.md` F5, 2026-09-29: Prod geregistreerd en geladen, FINANCE gepromoveerd, MLV en refresh in P). De lege Silver-tabel in het doel blijft niet getest.
  - *Bijgewerkt 2026-10-06 (rookproef 2, stap 10):* ontbreekt de Silver-tabel in het doel, dan faalt de promotie van DATA (`CopyOverwriteResult.GenericError` op `LH_GOLD_LAYER`). Na de load in het doel slaagde dezelfde promotie (*getest in eigen omgeving*, T → P; `11_troubleshooting.md`).
- **Gevolg:** geen Variable Library en geen `NB_CREATE_SHORTCUTS` meer na een promotie, zolang de Silver-tabellen in het doel bestaan. Maak de shortcuts in Dev aan (met de notebook of in de portal), en promoveer DATA.

*De tekst hieronder was de verwachting vóór de test (2026-09-28). Het risico bleek niet op te treden; de tekst blijft staan zodat de geschiedenis leesbaar blijft.*

**Wat dit voor FMD betekent (aanname vóór de test):**
- De shortcuts van FMD wijzen van Gold (DATA van het domein) naar Silver (INTEGRATION DATA), dus naar een andere workspace. Die worden niet omgezet.
- **Vastgesteld 2026-09-28 (`getDefinition`, trial, `testplan-trial.md` T-E04 voorcontrole):** in de Gold-lakehouses die de setup aanmaakt, staat shortcut-tracking aan (`alm.settings.json`: `Shortcuts` `Enabled`). `shortcuts.metadata.json` bevat de shortcuts met een letterlijk `workspaceId`/`itemId` van Silver.
- **Risico:** promoveer je de DATA-workspace van het domein, dan krijgt Gold in de doelstage de shortcuts uit Dev, die naar Silver (D) wijzen. Die overschrijven de shortcuts die `NB_CREATE_SHORTCUTS` daar heeft gemaakt. Draai `NB_CREATE_SHORTCUTS` daarom na **elke** promotie van die DATA-workspace. Dat stond hier al, maar met een andere reden.
- **Mogelijke structurele oplossing:** een Variable Library in de DATA-workspace van het domein, met per omgeving de Silver-workspace en -lakehouse als override (ADR-010), en de shortcut in Dev via de portal aan die variabelen koppelen. Een item leest alleen een library uit zijn eigen workspace, dus `VAR_GOLD_SHORTCUTS_FMD` in de CODE-workspace volstaat niet. `NB_CREATE_SHORTCUTS` is dan alleen nodig voor de eerste aanmaak.
- **Alternatief (optie A):** zet shortcut-tracking uit op de Gold-lakehouses. Een promotie laat de shortcuts dan waarschijnlijk met rust, en `NB_CREATE_SHORTCUTS` maakt ze per omgeving. Dat is een *aanname*, die T-E04 deel 3 test.

Hoe dan ook hoort dit **niet** thuis in de reguliere load-pipeline: shortcuts wijzigen zelden, de load draait vaak (nightly/intraday).

## Variable Library: `VAR_GOLD_SHORTCUTS_FMD`

De shortcut-doelen worden beheerd via een Variable Library specifiek voor dit doel, met zes variabelen (`variables.json`):

| Variabele | Betekenis |
|---|---|
| `SourceWorkspaceId` | Workspace waarin de shortcut wordt aangemaakt (de Gold-lakehouse) |
| `SourceLakehouseId` | De Gold-lakehouse zelf |
| `SourceSchema` | Schema-pad binnen de Gold-lakehouse waar de shortcut komt te staan |
| `Shortcut_TargetWorkspaceId` | Workspace van de bron (INTEGRATION DATA) |
| `Shortcut_TargetLakehouseId` | Bron-lakehouse (`LH_SILVER_LAYER`) |
| `Shortcut_TargetSchema` | Schema-pad binnen de bron-lakehouse |

Dit volgt het algemene Variable-Library-patroon: vier value sets (Development/Test/Acceptance/Production, volgorde vastgelegd in `settings.json`) en een actieve value set per workspace. Vanaf fork-commit `81fe912` vult `NB_SETUP_BUSINESS_DOMAINS` de vier ID-variabelen voor elke omgeving uit het manifest: de waarden van de eerste omgeving als default, die van de andere omgevingen als override. Daarna activeert hij in elke CODE-workspace de eigen value set (ADR-010). `SourceSchema` en `Shortcut_TargetSchema` zijn in elke omgeving gelijk en blijven gewone defaults.

**Hertest 2026-09-26 (`testplan-trial.md` T-E01):**
- `SourceSchema` en `Shortcut_TargetSchema` waren na de setup **leeg**. Met schema-lakehouses staan de Silver-tabellen onder de namespace (`Tables/aw/Sales_Customer`). Zet beide op die namespace, in de Dev-library; de promotie neemt ze mee.
- `ShortcutNames` in `NB_CREATE_SHORTCUTS` gebruikt de Silver-tabelnamen `<Schema>_<Tabel>`.
- Een shortcut naar een tabel die in die omgeving nog niet bestaat, faalt met *"Target path doesn't exist"*. Draai het notebook dus pas na de eerste load van die omgeving. In forks van vóór PR #31 eindigt het notebook ook dan groen; sinds PR #31 faalt het met de naam van de tabel erbij.
- Met die aanpassingen maakte het notebook in Dev en in Test de shortcuts, elk naar Silver van de eigen omgeving.

**Status:** vastgesteld (structuur/variabelnamen code-geverifieerd); welke waarden er in de live Bitmetric-omgeving daadwerkelijk in staan is niet geverifieerd (geen toegang tot de live Variable Library-waarden in deze sessie, alleen tot de lege repo-template).

**Naamsverwarring is inherent aan de template zelf:** `VAR_GOLD_CODE_FMD` bevat maar één variabele (`key_vault_uri_name`) en heeft dus een compleet andere inhoud/doel dan `VAR_GOLD_SHORTCUTS_FMD` — de twee libraries lijken alleen op elkaar door de gedeelde `VAR_GOLD_*_FMD`-naamgeving, niet door hun inhoud. Dat verklaart waarom een verwisseld item-ID zo makkelijk over het hoofd wordt gezien (zie incident 1 hieronder).

## Twee bekende praktijkincidenten

**1. Item-ID-verwisseling tussen twee gelijkend genaamde variabele-libraries.**
Er is een incident geweest waarbij per ongeluk het verkeerde item werd bijgewerkt. `VAR_GOLD_CODE_FMD` (CODE-workspace-variabelen) en `VAR_GOLD_SHORTCUTS_FMD` (shortcut-doelen) hebben namen die op elkaar lijken, en bij een handmatige `POST …/items/{id}/updateDefinition` werd het item-ID van de verkeerde library gebruikt. Dat overschreef **stilzwijgend** het verkeerde item. Vandaar de projectinstructie om item-ID's altijd te dubbelchecken vóór zo'n call. Het risico geldt alleen voor handmatige calls: de setup zoekt het ID zelf op naam op. (Concreet incident-verhaal: zie `../13_referentie-implementatie-bitmetric.md`.)

**Status:** getest in eigen omgeving (incident heeft daadwerkelijk plaatsgevonden).

**2. Leeg-maar-bestaande value sets voor Test/Prod.**
Er is een incident geweest waarbij Test- en/of Prod-value-sets van een Variable Library als lege structuur bleken te bestaan, zonder ooit gevuld te zijn. De regel "controleer bij problemen altijd of de value sets voor Test/Prod daadwerkelijk gevuld zijn — ze kunnen als lege structuur bestaan zonder ooit ingevuld te zijn" (zie projectinstructies) komt direct uit dit incident.

**Structurele bevestiging (code-geverifieerd, 2026-09-22):** dit was geen eenmalig ongeluk maar een **inherent risico van hoe de template was opgezet**. `VAR_GOLD_SHORTCUTS_FMD.VariableLibrary/valueSets/Test.json` (en Acceptance/Production) bevatten in de fork letterlijk `"variableOverrides": []`, en de setup schreef de waarden per omgeving als default. Een promotie overschrijft die defaults met de Dev-waarden (getest op 2026-09-25).

**Opgelost vanaf fork-commit `81fe912`:** de setup vult de value sets zelf en activeert per workspace de juiste (zie hierboven en ADR-010). Wat overblijft: kan de setup een lakehouse niet vinden, dan schrijft hij een lege override en print hij een `❌`-regel. Omgevingen die met een oudere fork zijn opgebouwd, hebben het oude risico nog.

**Status:** getest in eigen omgeving (het incident en de promotietest) + vastgesteld in code (de fix). De volledige keten wordt getest in `testplan-trial.md` (T-A03, T-A05).

## Wat dit betekent voor een implementatieplan (fase 4)

Als expliciete post-deployment-checklist-stap, telkens na een deployment die een Gold-Lakehouse met shortcuts raakt:

1. `NB_CREATE_SHORTCUTS` handmatig herdraaien in de doelomgeving. De promotie heeft de shortcuts daar vervangen door de Dev-shortcuts, die naar Silver (D) wijzen (zie *Shortcuts bij promotie*). *Bijgewerkt 2026-09-28 na T-E04:* deze stap is niet nodig als DATA wordt gepromoveerd en de Silver-tabellen in het doel al bestaan. Controleer dan alleen het aantal shortcuts en hun doel (`GET …/shortcuts`).
2. `VAR_GOLD_SHORTCUTS_FMD` in de doelomgeving controleren: is de actieve value set die van de doelomgeving, en is de override voor die omgeving niet leeg?
3. Bij het aanpassen van een Variable-Library-item: het item-ID dubbelchecken tegen de juiste library (`VAR_GOLD_CODE_FMD` vs. `VAR_GOLD_SHORTCUTS_FMD`) vóórdat een `updateDefinition`-call wordt gedaan.
