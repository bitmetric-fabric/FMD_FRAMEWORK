# Operationele aandachtspunten

**Versie:** 1.3
**Bron:** `output/01_kennisbasis/registratie.md`, `geleerde-lessen.md`, `02_beslisdocument/02_beslisregister.md`, plus eigen codeverificatie en een empirische pipeline-testrun bij Bitmetric — concrete commit-hashes, job-ID's en omgevingsnamen zijn verplaatst naar `../13_referentie-implementatie-bitmetric.md`
**Status:** zie per punt

Dit document werkt de vier operationele bevindingen uit die in Fase 2 bewust **niet** als architectuurbeslissing zijn behandeld, maar als technisch aandachtspunt voor Fase 3/4 zijn doorgeschoven (zie `02_beslisregister.md`, sectie "Operationele bevindingen → Fase 3").

**v1.1-update (2026-09-22):** punt 1 en punt 4 zijn direct tegen de fork-code geverifieerd, op verzoek van Mitchell. Punt 4 bleek een vals alarm (functioneel correct, alleen een misleidend label). Punt 1 werd op basis van uitsluitend statische codeanalyse ten onrechte als "vastgesteld, ernstig" bestempeld.

**v1.2-update (2026-09-22):** punt 1 is herzien. Mitchell heeft een echte pipeline-run uitgevoerd tegen de ongewijzigde (nog niet gefixte) pipeline-versie en de resultaten in de configdatabase opgevraagd: alle entiteiten zijn correct geregistreerd, met de echte tabelnamen. De eerdere conclusie ("met hoge zekerheid registreert de pipeline geen enkele entiteit correct") is dus **niet houdbaar gebleken** en is hieronder gecorrigeerd. Dit is een expliciete les over de grenzen van statische codeanalyse bij Fabric/ADF-pipelines — zie de toelichting in punt 1.

---

## 1. Casing-mismatch in `PL_TOOLING_POST_ASQL_TO_FMD` — statische analyse weerlegd door live test

**Status:** getest in eigen omgeving — **géén bug bevestigd**. Eerdere conclusie op basis van statische codeanalyse bleek onjuist na een empirische pipeline-testrun tegen de ongewijzigde pipeline-versie (de eventuele fix staat alleen in git, niet gedeployed). Concrete testevidentie (job-ID, omgevingsnaam, querybewijs): zie `../13_referentie-implementatie-bitmetric.md`.
**Mitchell (OV-09):** "De casing bug moeten we nog even bespreken" — met de testresultaten hieronder is dit gesprek nu gevoerd: de bug is niet aanwezig in praktijk.

### Wat er op het eerste gezicht mis leek

De `Copy metadata`-activity genereert JSON met **camelCase**-veldnamen: `sourceName`, `sourceSchema`, `primaryKeys`, `columnMappings`, `isView`. De `ForEach LZE`-activity roept `sp_UpsertLandingzoneBronzeSilver` aan met (letterlijk uit de pipeline-JSON):

```
FileName      -> @concat(item().sourceSchema,'_',item().sourceName)              -- lowercase
SourceName    -> {"value": "@item().SourceName",   "type": "Expression"}          -- PascalCase
SourceSchema  -> {"value": "@item().SourceSchema", "type": "Expression"}          -- PascalCase
PrimaryKeys   -> {"value": "@item().PrimaryKeys",  "type": "Expression"}          -- PascalCase
TargetName    -> "@item().SourceName"      -- geen "type":"Expression"-wrapper
TargetSchema  -> "@item().SourceSchema"    -- geen "type":"Expression"-wrapper
```

Op basis van deze JSON alleen werd verondersteld dat (A) `TargetName`/`TargetSchema` zonder Expression-wrapper als letterlijke string zouden worden doorgegeven, en (B) `SourceName`/`SourceSchema`/`PrimaryKeys` zouden falen op een niet-bestaande (verkeerd-hoofdlettergevoelige) JSON-property.

### Wat de live test daadwerkelijk laat zien

Een testrun tegen een SQL-databron is uitgevoerd en de resultaten zijn rechtstreeks in de configdatabase geverifieerd: alle entiteiten registreerden met de **echte tabelnamen** — niet de letterlijke tekst `@item().SourceName`. De pipeline liep volledig door zonder fouten. Geen van beide veronderstelde deelproblemen doet zich voor. Het volledige querybewijs staat in `../13_referentie-implementatie-bitmetric.md`.

**Gecorrigeerd begrip van het mechanisme:** Fabric's pipeline-expressietaal evalueert kennelijk (a) `@`-voorvoegsel-strings ook zónder de expliciete `{"value": ..., "type": "Expression"}`-omhulling — consistent met het bekende, gedocumenteerde `@@`-escape-mechanisme voor een letterlijke `@` (dat mechanisme impliceert dat een kale `@`-string standaard al als expressie wordt gelezen), en (b) dot-notation-eigenschapstoegang (`item().SourceName`) case-insensitief tegen de camelCase JSON-property (`sourceName`). Beide aannames waarop de oorspronkelijke analyse steunde, kloppen dus niet.

**Methodologische les:** statische inspectie van pipeline-JSON is geen betrouwbare vervanging voor empirisch testen van Fabric/ADF-expressietaal-gedrag op runtime. Voor toekomstige bevindingen van dit type geldt: een conclusie als "vastgesteld" of "met hoge zekerheid" vereist een daadwerkelijke testrun, niet alleen code-lezen — ook niet wanneer de redenering intern consistent oogt.

### Aanbevolen actie (Fase 3/4)

1. **Geen blokkade meer voor gebruik van deze pipeline** — bulkregistratie via `PL_TOOLING_POST_ASQL_TO_FMD` functioneert correct zoals getest.
2. **De eerder voorgestelde fix (camelCase-correctie + Expression-wrapper) is niet noodzakelijk voor correctheid**, maar kan bij gelegenheid alsnog worden doorgevoerd voor leesbaarheid/consistentie (categorie A, geen haast, ter beoordeling aan Mitchell) — de huidige code werkt, maar is impliciet en verwarrend voor wie de JSON leest zonder het runtime-gedrag te kennen.
3. **Voor toekomstige, vergelijkbare bevindingen:** waar mogelijk een empirische testrun toevoegen vóór een conclusie als "vastgesteld" wordt gepubliceerd.

---

## 2. Positional-parameter-bug in bulk-registratiescript

**Status:** getest in eigen omgeving (het gevonden incident) · open vraag (of dit hetzelfde is als de oorspronkelijk bedoelde les)
**Mitchell (OV-10):** "Deze weet ik niet."

### Wat er is gevonden

**Niet** in `PL_TOOLING_POST_ASQL_TO_FMD` zelf, maar in een ander, handmatig bulk-registratiescript: `sp_UpsertDataSource` werd aangeroepen met **positionele** in plaats van **benoemde** parameters. Een bedoelde waarde `1` kwam daardoor in `@LoadGroup` terecht in plaats van in `@IsActive`. `IsActive` viel terug op zijn default, maar `LoadGroup` kreeg onbedoeld de waarde `'1'`. Daardoor laadt de bron wel in een run zonder groep, maar niet in `PL_FMD_SCHEDULE_NIGHTLY` of `_INTRADAY`.

**Waarschijnlijke herkomst (2026-09-25, review 2 N-F7):** het registratievoorbeeld in de upstream-wiki (`Supported-data-sources.md`) roept `sp_UpsertDataSource` precies zo aan: positioneel, zeven argumenten, eindigend op `1`. Upstream is de zevende parameter `@IsActive`, in de fork `@LoadGroup`. Zie `01_ddl-spec.md` §Verschillen fork vs. upstream-wiki.

### Aanbevolen actie (Fase 3/4)

1. **Best practice vastleggen in het implementatieplan:** altijd benoemde parameters gebruiken bij het aanroepen van `sp_Upsert*`-procedures in scripts, nooit positioneel — juist omdat deze procedures parameters met defaults hebben (`@DataSourceId INT = 0`, `@LoadGroup VARCHAR(50) = ''`, `@IsActive BIT = 1`), wat positionele aanroepen extra kwetsbaar maakt voor stille misalignment bij een gewijzigde signature.
2. **Als het bewuste script bekend is bij Bitmetric:** ergens vastleggen welk script dit was en het corrigeren, zodat het niet per ongeluk als voorbeeld voor een klantimplementatie wordt hergebruikt.
3. Dit blijft losstaand van punt 1 hierboven — het is een ander mechanisme (parameterhandigheid in scripts) dan de casing-mismatch (JSON-veldnaam-mismatch in de pipeline zelf).

---

## 3. Notebook-/branch-versiemismatch

**Status:** vastgesteld (platformbeperking, zie update) · open vraag blijft welke van de twee kandidaten de oorspronkelijk bedoelde les was
**Mitchell (OV-11):** "Weet ik ook niet."

### Twee kandidaat-incidenten gevonden

**Kandidaat A — Service Principal vs. Workspace Identity:** een versieverschil tussen een lokale en een live main-branch-versie van het business-domain-setup-notebook leidde er destijds toe dat de eigen omgeving expliciete Service Principal-credentials in Key Vault gebruikt in plaats van (uitsluitend) Workspace Identity.

Dit bleek achteraf **geen tijdelijke versiemismatch**, maar een vastgelegde platformbeperking: `FabricSql`-connecties weigeren `WorkspaceIdentity` hard (`UnsupportedCredentialType`) en accepteren alleen OAuth2/Service Principal-credentials. Andere connectietypes (`FabricDataPipelines`, `Notebooks`) gebruiken wél `WorkspaceIdentity` zonder probleem — zie `../08_security-en-secrets.md`. **Dit is dus consistent met en bevestigt B-SECURITY-02** (expliciete SP i.p.v. Managed Identity) — geen los actiepunt meer, wel relevante achtergrond voor de security-documentatie. Broncode-verwijzing en commit: zie `../13_referentie-implementatie-bitmetric.md`.

**Kandidaat B — dacpac/CI-build-mismatch:** verschil tussen een lokaal gebuild dacpac en wat de CI-pipeline daadwerkelijk bouwde/deployde. Root cause (opgelost): DacFx bakte het platform-regeleinde in `SysCommentsObjectAnnotation` mee, waardoor een Windows-lokale build afweek van de Linux-CI-build. Commit-reeks van de fix: zie `../13_referentie-implementatie-bitmetric.md`.

### Aanbevolen actie (Fase 3/4)

1. Beide incidenten zijn **opgelost** — geen actieve bug meer om te fixen.
2. **Voor de intake-checklist / implementatieplan:** neem de dacpac/CI-build-les generiek op als waarschuwing ("bouw dacpac's altijd via CI, nooit lokaal voor een deploy-beslissing") — relevant voor elke klant die zelf aan de configdb-DDL sleutelt.
3. Dit blijft in de kennisbasis als open vraag staan welke van de twee de oorspronkelijk bedoelde "les" was — niet blokkerend, puur voor de volledigheid van de documentatie.

---

## 4. `PL_FMD_LDZ_COMMAND_FTP` — verdenking geverifieerd: VALS ALARM

**Status:** vastgesteld — geverifieerd tegen de fork-code (eigen inspectie van `FMD/src/PL_FMD_LDZ_COMMAND_FTP.DataPipeline/pipeline-content.json` + de `.platform`-bestanden van beide kandidaat-pipelines). Commit-referentie: zie `../13_referentie-implementatie-bitmetric.md`.
**Mitchell (OV-13):** "Voorstel akkoord" — akkoord om dit te verifiëren vóór opname als vastgesteld gedrag. Bij dezen geverifieerd: **het vermoeden klopt niet.**

### Wat het vermoeden inhield

Uit `bronnen/notities/fmd-open-actions.md` (actiepunt #6): het vermoeden dat `PL_FMD_LDZ_COMMAND_FTP` per ongeluk **`PL_FMD_LDZ_COPY_FROM_ADF`** aanroept in plaats van **`PL_FMD_LDZ_COPY_FROM_FTP_01`**.

### Wat de code daadwerkelijk laat zien

De `InvokePipeline`-activity binnen de ForEach van `PL_FMD_LDZ_COMMAND_FTP` heeft inderdaad het label (`"name"`) **`PL_FMD_LDZ_COPY_FROM_ADF`** — dat label is puur cosmetisch (een activity-naam in de canvas) en is wat het vermoeden heeft gevoed. Maar het daadwerkelijk aangeroepen item wordt bepaald door het `pipelineId`-GUID in de pipeline-JSON, dat exact gelijk is aan de `logicalId` in het `.platform`-bestand van **`PL_FMD_LDZ_COPY_FROM_FTP_01`** (niet die van `PL_FMD_LDZ_COPY_FROM_ADF`, die een andere `logicalId` heeft). De concrete GUID's staan ter referentie in `../13_referentie-implementatie-bitmetric.md`.

**Conclusie:** `PL_FMD_LDZ_COMMAND_FTP` roept functioneel wél de juiste FTP-pipeline aan. De activity-naam is een misleidend restant (vermoedelijk ontstaan doordat deze pipeline ooit is gekloond van de ADF-variant, waarna alleen het `pipelineId` is aangepast maar niet de activity-naam) — verwarrend voor wie de pipeline-JSON of -canvas leest, maar geen functionele bug.

### Aanbevolen actie (Fase 3/4)

1. **Geen functionele fix nodig** — de FTP-load werkt correct.
2. **Cosmetische opschoning (optioneel, lage prioriteit):** de activity binnen `PL_FMD_LDZ_COMMAND_FTP` hernoemen naar `PL_FMD_LDZ_COPY_FROM_FTP_01` om toekomstige verwarring te voorkomen — categorie A-wijziging (zie B-ARCH-02), geen haast bij.
3. **Voor de kennisbasis:** `registratie.md` actiepunt #6 kan als opgelost/vals-alarm gemarkeerd worden.
4. Niet opnemen in `04_implementatieplan/implementatieplan-template.md` als aandachtspunt — dit is geen risico voor klantimplementaties.

---

## Samenvattend overzicht

| # | Punt | Status | Blokkerend voor Fase 3/4? |
|---|---|---|---|
| 1 | Casing-mismatch `PL_TOOLING_POST_ASQL_TO_FMD` | **Getest in eigen omgeving: géén bug bevestigd** — live testrun toont correcte registratie voor alle entiteiten (statische analyse eerder ten onrechte anders) | Nee — pipeline functioneert correct, vrij te gebruiken; optionele leesbaarheidsfix mogelijk |
| 2 | Positional-parameter-bug (ander script) | Getest (incident) / open (of dit de bedoelde les is) | Nee — vastleggen als best practice volstaat |
| 3 | Notebook-/branch-versiemismatch | Vastgesteld (beide kandidaten opgelost) | Nee — informatief |
| 4 | `PL_FMD_LDZ_COMMAND_FTP`-verdenking | **Vastgesteld: vals alarm** — functioneel correct, alleen het activity-label is misleidend | Nee — geen actie vereist, optioneel cosmetisch op te schonen |
