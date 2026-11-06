# Beslisregister FMD Framework — Fase 2

**Datum:** 2026-09-25
**Versie:** 2.1
**Status:** Deel A (klantbeslissingen, 16 stuks) nieuw in v2.0; B-CICD-02, B-MON-01 en B-GOV-01 bevestigd door Mitchell; Deel B finaal (12 besluiten geaccepteerd; B-INFRA-02 herschreven en herbevestigd op 2026-09-25 (v1.8), fork-fix gemerged (v1.9); operationele bevindingen → Fase 3; B-ARCH-01-implementatiegat gedicht (v1.7); B-INFRA-03 gecorrigeerd n.a.v. Fase 5-consistentiecheck)

Dit register formaliseert alle architectuur- en operationele besluiten voor het FMD Framework bij Bitmetric, opgesteld op basis van Fase 1 (kennisbasis) en geverifieerd door Mitchell Krops (mitchell@bitmetric.nl).

> **Wijziging t.o.v. v1.1 (review door Sonnet):** een aantal `Akkoord`-verwijzingen naar OV-nummers in v1.1 bleek niet te kloppen met de daadwerkelijke antwoorden van Mitchell op OV-01 t/m OV-13 (zie `output/01_kennisbasis/open-vragen.md` en de oorspronkelijke chatinvoer). Gecorrigeerd: B-CICD-01 (verkeerde ADR-bron, geen echte OV-toewijzing), B-INFRA-01/B-GOLD-01/B-INFRA-03 (OV-12 was ten onrechte hergebruikt — OV-12 gaat uitsluitend over deactivering), B-EXT-01 (GA4-feit was onjuist weergegeven). Toegevoegd: OV-02 (referentie-implementatie bevestigd) en OV-13 (LDZ-FTP-bug → Fase 3) waren in v1.1 helemaal niet verwerkt. Zie versiegeschiedenis onderaan voor het volledige overzicht.

---

## Opbouw van dit register

- **Deel A — Klantbeslissingen:** de keuzes die per klant gemaakt worden, per categorie uit de opdracht (`Promp.txt` §Fase 2). Elke beslissing heeft de gevraagde velden: beslisvraag in klanttaal, opties met voor- en nadelen, impact, Bitmetric-default met onderbouwing, afhankelijkheden, fase en wie beslist.
- **Deel B — Vastgestelde besluiten:** de besluiten die Bitmetric intern al heeft genomen over het framework (B-ARCH-01 t/m B-INFRA-03). Die zijn voor een klant het uitgangspunt, geen keuze. Deel A verwijst ernaar.

**Status per klantbeslissing:** `default vastgesteld` (Bitmetric heeft een standaard; de klant kan afwijken) · `open, per klant` (geen standaard; kiezen in de intake) · `open, Bitmetric` (Bitmetric moet eerst zelf kiezen).

---

## Deel A — Klantbeslissingen

### Overzicht

| ID | Categorie | Beslisvraag (kort) | Status | Fase | Wie beslist | Hangt af van |
|---|---|---|---|---|---|---|
| B-CAP-01 | Capacity en licenties | Welke capaciteit, en wanneer pauzeren? | default vastgesteld (minimum F2, **geaccepteerd risico**: niet getest) | 1 | samen | B-WS-01, B-LOAD-02 |
| B-SEC-01 | Tenant, identiteit en security | Welke identiteit per connectie? | default vastgesteld (B-SECURITY-02) | 1–2 | Bitmetric, klant bevestigt | — |
| B-NET-01 | Tenant, identiteit en security | Netwerkisolatie, private endpoints, gateway? | open, per klant | 1 | klant | B-SRC-01 |
| B-WS-01 | Domeinen en workspace-topologie | Hoeveel domeinen, welke workspaces per domein? | default vastgesteld | 1 | samen | — |
| B-ENV-01 | Omgevingen | Welke omgevingen (DTAP)? | default vastgesteld | 1 | samen | B-CAP-01 |
| B-ENV-02 | Omgevingen | Eén configuratiedatabase voor alle omgevingen, of één per omgeving? | default vastgesteld (framework) | 1 | Bitmetric | B-ENV-01 |
| B-SRC-01 | Bronnen en connectiviteit | Hoe wordt elke bron ontsloten? | default vastgesteld (B-EXT-01) | 1, per bron in 4–5 | samen | B-NET-01 |
| B-LOAD-01 | Laadstrategie | Full of incrementeel, en historie in Silver? | default vastgesteld | 1, per bron in 4–5 | samen | B-SRC-01 |
| B-LOAD-02 | Laadstrategie | Hoe vaak laden? | open, per klant | 1 | klant | B-CAP-01 |
| B-GOLD-02 | Gold-laag en semantisch model | MLV of notebooks, Direct Lake of import? | default vastgesteld | 1, uitgewerkt in 6 | samen | B-WS-01 |
| B-CICD-01 | CI/CD | Hoe promoveren we naar Test en Prod? | default vastgesteld (Deel B) | 1 | Bitmetric, klant bevestigt | B-ENV-01 |
| B-CICD-02 | CI/CD en Git-provider | Waar staat de code, en wie keurt een promotie goed? | default vastgesteld | 1 | Bitmetric, klant kan afwijken | B-CICD-01 |
| B-MON-01 | Monitoring, logging en alerting | Wie krijgt een melding als het misgaat? | default vastgesteld | 1, ingericht in 5 (gecontroleerd in 7) | samen (klant kiest ontvangers) | B-OPS-01 |
| B-GOV-01 | Governance | Purview, naamconventies, eigenaarschap? | default vastgesteld | 1 | klant | B-WS-01 |
| B-UPG-01 | Frameworkversie en upgrades | Krijgt de klant later framework-updates? | default vastgesteld (ADR-002) | 1, vastgelegd in 8 | samen | B-OPS-01 |
| B-OPS-01 | Beheer en overdracht | Wie beheert het platform na oplevering? | open, per klant | 1, uitgevoerd in 8 | klant | B-UPG-01 |

De fasen zijn die van `04_implementatieplan/plan_hoogover.md`. Vrijwel alles wordt in fase 1 (intake) gekozen; de kolom noemt ook de fase waarin het wordt uitgewerkt.

---

### B-CAP-01 · Capacity en licenties

**Beslisvraag:** Op welke Fabric-capaciteit draait het platform, draaien Dev, Test en Prod op dezelfde of op aparte capaciteiten, en pauzeren we een capaciteit buiten kantoortijd?

**Opties:**
- **A. Eén capaciteit voor alle omgevingen.** + Goedkoopst, eenvoudig beheer. − Een zware Dev-run vertraagt Prod (capaciteitscontentie, zie `10_operations.md`).
- **B. Aparte capaciteit voor Prod.** + Prod wordt niet geraakt door Dev en Test. − Hogere kosten.
- **C. Gold op een eigen capaciteit per domein** (`capacity_business_domain` in het manifest). + Een domein kan apart worden geschaald of doorbelast. − Meer capaciteiten om te beheren.
- **Pauzeren:** een gepauzeerde capaciteit draait geen geplande loads. Alleen zinvol voor Dev/Test, of voor Prod als er alleen 's nachts wordt geladen en het pauzeren daarop is afgestemd.

**Impact:** capaciteitsnamen in `manifest.environments[].capacity`; Spark-sizing van `ENV_FMD` (standaard driver 4 cores/28g, maximaal 2 executors van 4/28g); kosten.

**Bitmetric-default:** optie A voor een kleine klant, B zodra Prod-loads niet vertraagd mogen worden. **Minimum-SKU: F2** (*tweedehands* (Mitchell, 2026-10-05); *correctie 2026-10-05*, hier stond "nog niet vastgesteld"). Achtergrond: de eigen omgeving draait op F2 (gemeten ~17% van 172.800 CU-seconden op één dag), maar of F2 de runtime-notebooks in `ENV_FMD` draagt, is niet zelf getest (testplan T-B01 blijft open als controle). Kostenbewaking: de Capacity Metrics-app.

**Afhankelijkheden:** B-WS-01 (aantal domeinen), B-LOAD-02 (frequentie), B-ENV-01 (aantal omgevingen).

**Fase / wie:** fase 1, samen. Minimum F2 (Bitmetric).

**Status:** minimum-SKU F2 (*tweedehands* (Mitchell, 2026-10-05)); de rest per klant.
- *Aanvulling 2026-10-12 (eindcontrole P3-R5, besluit Mitchell):* **geaccepteerd risico.**
  - Het framework is niet op F2 getest (T-B01 open). De rookproeven draaiden op de trial-capaciteit.
  - Kiest een klant F2, dan doen we in Dev eerst één volledige setup en load, en kijken we in de Capacity Metrics-app naar throttling, voordat Test en Prod volgen.
  - Het risico: trage of geknepen Spark-runs (`ENV_FMD` vraagt 4 cores per driver), en timeouts per laag. Zie `03_technische_documentatie/12_kosten-en-capaciteit.md`.

---

### B-SEC-01 · Identiteit per connectie

**Beslisvraag:** Met welke identiteit maakt het framework verbinding met zijn eigen configuratiedatabase en pipelines?

**Opties:** zie **B-SECURITY-02** in Deel B. Kort: A. Service Principal voor `CON_FMD_FABRIC_SQL` en Workspace Identity voor de rest (+ volgt de setup, niet aan een persoon gebonden; − SP-secret moet worden vernieuwd). B. Handmatige OAuth2-connectie voor `CON_FMD_FABRIC_SQL` (+ geen SP nodig; − hangt aan een persoon, verloopt na 90 dagen inactiviteit).

**Impact:** Key Vault met drie secrets vóór de setup; rechten van degene die de setup draait; rotatieprocedure.

**Bitmetric-default:** optie A (B-SECURITY-02, akkoord Mitchell 2026-09-25).

**Afhankelijkheden:** geen.

**Fase / wie:** fase 1 besluiten, fase 2 inrichten; Bitmetric, klant bevestigt (de klant maakt de SP aan).

**Status:** default vastgesteld.

---

### B-NET-01 · Netwerk, private endpoints en gateways

**Beslisvraag:** Mogen de data en de Fabric-omgeving alleen via een afgeschermd netwerk bereikbaar zijn, en staan er bronnen on-premises of achter een firewall?

**Opties:**
- **A. Geen netwerkisolatie.** + Werkt zoals de setup is gebouwd en getest. − Niet toegestaan bij klanten met strikte netwerkeisen.
- **B. On-premises data gateway voor specifieke bronnen.** De gateway hoort bij de Fabric-connectie (`ConnectionGuid`), dus de framework-pipelines hoeven niet te veranderen. + Alleen waar nodig. − Gateway-server moet door de klant worden beheerd. De wiki beschrijft dit voor Oracle.
- **C. Private endpoints / private link voor de tenant of workspaces.** + Maximale afscherming. − **Niet getest met FMD.** De setup gebruikt de Fabric REST-API en de `fab`-CLI vanuit notebooks; of dat werkt met private link, is onbekend.

**Impact:** optie B: gateway-installatie en connecties per bron. Optie C: mogelijk aanpassingen in de setup; vraagt een eigen proef.

**Bitmetric-default:** A, met B per bron waar nodig. C alleen na een proef.

**Afhankelijkheden:** B-SRC-01 (welke bronnen).

**Fase / wie:** fase 1; de klant beslist (security-eisen), Bitmetric beoordeelt de haalbaarheid.

**Status:** open, per klant. Optie C: open vraag voor Bitmetric.

---

### B-WS-01 · Domeinen en workspace-topologie

**Beslisvraag:** Voor welke bedrijfsonderdelen bouwen we een eigen rapportagedomein, en welke workspaces krijgt elk domein?

**Opties:**
- **A. Alleen INTEGRATION** (Landingzone, Bronze, Silver) plus één business-domein. + Klein, snel. − Later splitsen kost werk (nieuwe workspaces, Gold en semantische modellen verhuizen).
- **B. INTEGRATION plus één domein per bedrijfsonderdeel** (bijv. FINANCE, SALES, HR). + Eigenaarschap en rechten per domein. − Meer workspaces, deployment pipelines en Gold-onderhoud.
- **Per domein:** CODE en DATA zijn altijd nodig; SEMANTIC en REPORTING alleen als het domein eigen modellen en rapporten heeft.

**Impact:** `naming.business_domains` in het manifest; per domein en per omgeving tot vier workspaces en vier deployment pipelines; naamgeving volgens B-ARCH-01 (`[DOMEIN] [LAAG] ([OMG])`, Prod zonder marker).

**Bitmetric-default:** B met zo weinig domeinen als het eigenaarschap toelaat. De configuratiedatabase staat altijd in een aparte CONFIGURATION-workspace.

**Afhankelijkheden:** geen; B-CAP-01, B-GOLD-02 en B-GOV-01 hangen hiervan af.

**Fase / wie:** fase 1, samen.

**Status:** default vastgesteld. Zie `03_technische_documentatie/06_BUSINESS_DOMEINEN/01_workspace-structuur.md`.

---

### B-ENV-01 · Omgevingen (DTAP)

**Beslisvraag:** Welke omgevingen krijgt het platform: alleen ontwikkeling en productie, of ook test en acceptatie?

**Opties:**
- **A. D, T, P.** + Standaard in het manifest; testen gebeurt los van productie. − Drie keer de workspaces.
- **B. D, T, A, P.** + Aparte acceptatie door de business. − Vier keer de workspaces, een extra promotiestap. De Variable Libraries hebben al een value set `Acceptance`.
- **C. D en P.** + Minder werk. − Geen plek om een promotie te testen voordat Prod wordt geraakt.

**Impact:** `manifest.environments`; aantal workspaces, stages in de deployment pipelines, value sets die de setup vult.

**Bitmetric-default:** A.

**Afhankelijkheden:** B-CAP-01 (capaciteit per omgeving).

**Fase / wie:** fase 1, samen.

**Status:** default vastgesteld.

---

### B-ENV-02 · Gedeelde configuratiedatabase

**Beslisvraag:** Staat de metadata (welke bronnen en tabellen we laden) voor alle omgevingen in één database, of heeft elke omgeving een eigen database?

**Hoe het framework het doet (vastgesteld in code):** de setup maakt **één** configuratiedatabase (`SQL_FMD_FRAMEWORK`) in één CONFIGURATION-workspace (`manifest.config_workspace`). Alle omgevingen gebruiken die database. De metadata wordt per omgeving gescheiden via de workspace: de COMMAND-pipelines en de `execution`-views filteren op de `WorkspaceGuid` van de DATA-workspace van die omgeving. `VAR_CONFIG_FMD` wijst in elke omgeving naar dezelfde database.

**Opties:**
- **A. Gedeeld (framework-standaard).** + Eén plek voor registratie en logging; geen extra databases. − Een bron moet **per omgeving** worden geregistreerd (de rijen verwijzen naar de lakehouses van die omgeving; een promotie neemt geen metadata mee; schema via de dacpac, ADR-013). − **Een schemawijziging raakt alle omgevingen tegelijk:** de dacpac wordt geïmporteerd in de ene database, dus Prod krijgt een nieuw schema op hetzelfde moment als Dev. − Prod-metadata is bereikbaar voor wie Dev beheert.
- **B. Eén database per omgeving.** + Scheiding, een schemawijziging kan eerst in Dev. − **Wordt niet ondersteund door de setup**: dat vraagt een fork-aanpassing (categorie A, B-ARCH-02).

**Impact:** registratieproces (per omgeving), schemawijzigingen (zie `09_cicd-en-deployment.md`), toegangsrechten op de CONFIGURATION-workspace.

**Bitmetric-default:** A, omdat het framework zo is gebouwd. Maatregelen: registratie per omgeving in het draaiboek; een schemawijziging eerst testen op een kopie van de database; schrijfrechten op de CONFIGURATION-workspace beperken.

**Afhankelijkheden:** B-ENV-01.

**Fase / wie:** fase 1, Bitmetric (een afwijking is een fork-wijziging).

**Status:** default vastgesteld (framework). *Nieuw op 2026-09-25: dit was nog nergens als besluit vastgelegd (review 1 R1).*

---

### B-SRC-01 · Bronnen en connectiviteit

**Beslisvraag:** Welke bronnen willen we ontsluiten, en kunnen die met een standaardkoppeling of is maatwerk nodig?

**Opties per bron:**
- **A. Standaard copy-pipeline** (SQL, SQL MI, Oracle, ADLS, OneLake, SFTP, FTP). + Geen code, alleen registratie. − Alleen de vaste combinaties `ConnectionType`/`DataSourceType` uit `07_extension-points.md` §1; de hele tabel wordt geladen (`SourceCustomSelect` wordt niet gelezen).
- **B. Custom notebook** (`CustomNotebookName`). + Elke bron met een API. − Maatwerk per bron; zelf het watermark goed zetten; een deel van de fouten wordt geslikt (`07` §2).
- **C. Azure Data Factory** (`ADF`). + Bestaande ADF-pipelines hergebruiken. − Vraagt een ADF en een echte ADF-connectie; in de eigen tenant staat die op een placeholder.
- **Dataflow Gen2:** wordt in FMD niet gebruikt (B-EXT-01).

**Impact:** registratie in de configdb; bij B een notebook per bron in de CODE-workspace; bij on-premises bronnen een gateway (B-NET-01).

**Bitmetric-default:** A waar het kan, B voor bronnen zonder standaardkoppeling. Een selectie van rijen of kolommen via een view in de bron.

**Afhankelijkheden:** B-NET-01.

**Fase / wie:** bronlijst in fase 1, per bron uitgewerkt in fase 4 en 5; samen (klant levert toegang en bronkennis).

**Status:** default vastgesteld (B-EXT-01).

---

### B-LOAD-01 · Full of incrementeel, en historie in Silver

**Beslisvraag:** Laden we elke tabel steeds helemaal, of alleen wat er veranderd is? En willen we in Silver bijhouden hoe een rij er vroeger uitzag?

**Hoe het framework het doet (vastgesteld in code):** per entiteit `IsIncremental` en `IsIncrementalColumn`. Silver houdt standaard **historie bij (SCD type 2)**: een gewijzigde rij krijgt een nieuwe versie met `IsCurrent`, `RecordStartDate` en `RecordEndDate`; een verwijderde rij wordt gemarkeerd met `IsDeleted` (`NB_FMD_LOAD_BRONZE_SILVER`).

**Opties per entiteit:**
- **A. Full load.** + Eenvoudig, altijd compleet. − Meer volume en CU bij grote tabellen; loopt eerder tegen de timeouts aan (`10_operations.md` §Timeouts).
- **B. Incrementeel** op een datum- of volgnummerkolom. + Minder volume. − De bron moet een betrouwbare kolom hebben; wijzigingen zonder bijgewerkte kolom worden gemist.
- **Historie:** de SCD2-historie in Silver is standaard. Wie alleen de actuele stand wil, filtert in Gold op `IsCurrent = 1`.
  - *Correctie 2026-10-13:* sinds ADR-016 *Herzien 2026-10-13* is het omgekeerd: Silver houdt standaard alleen de huidige rij (`IsHistorized = 0`); SCD2 is een keuze per tabel (`IsHistorized = 1` in het lijstsjabloon). Reden: historie die niemand vraagt kost opslag en merge-tijd. Een lege waarde in de lijst betekent 0, ook voor een entiteit die eerder met 1 is geregistreerd; de historie die er al staat blijft staan. Branch `feature/silver-default-zonder-historie` (`FMD_FRAMEWORK#62`); *getest in eigen omgeving* 2026-10-13 (trial-Dev, `testplan-trial.md`). De regel hieronder (2026-10-09) beschrijft de oorspronkelijke situatie met default 1.
  - *Correctie 2026-10-09:* dat gold als vaste eigenschap van elke Silver-tabel. Met `IsHistorized = 0` per entiteit (`integration.SilverLayerEntity`, in het lijstsjabloon; ADR-016) werkt Silver de huidige rij bij in plaats van een versie toe te voegen. De kolommen blijven gelijk, dus `IsCurrent = 1` werkt voor beide. Reden: bij veel bronnen en tabellen kost de historie rekentijd en opslag voor tabellen waar niemand haar gebruikt. Gebruik 0 voor grote tabellen zonder historiebehoefte. *Getest in eigen omgeving* (2026-10-09, `testplan-trial.md`).

**Impact:** registratie per entiteit; volume en CU; Gold-queries filteren op `IsCurrent`.

**Bitmetric-default:** full voor kleine tabellen, incrementeel voor grote tabellen met een betrouwbare kolom; historie in Silver zoals het framework doet.

**Afhankelijkheden:** B-SRC-01.

**Fase / wie:** principe in fase 1, per entiteit in fase 4 en 5; samen.

**Status:** default vastgesteld.

---

### B-LOAD-02 · Laadfrequentie

**Beslisvraag:** Hoe actueel moeten de rapporten zijn: is één keer per nacht genoeg, of moeten sommige bronnen vaker?

**Opties:**
- **A. Alleen nightly.** + Minste CU, één laadvenster. − Data is tot een dag oud.
- **B. Nightly plus intraday voor een deel van de bronnen.** ~~Het framework heeft `PL_FMD_SCHEDULE_NIGHTLY` en `PL_FMD_SCHEDULE_INTRADAY`, die `PL_FMD_LOAD_ALL` starten met `LoadGroup` `NIGHTLY` of `INTRADAY`.~~
  - *Correctie 2026-10-06 (review 3, `FMD_FRAMEWORK#35`):* twee schema's op `PL_FMD_ORCHESTRATION_TEMPLATE`. Nightly zonder groep laadt alles; intraday met `LoadGroup` `INTRADAY` laadt alleen die bronnen. Gold draait na elke run.
  - *Correctie 2026-10-11 (ontwerp `FMD_FRAMEWORK#52`, ADR-017; gemerged 2026-10-11, `4971d88`):* de schema's staan niet op `PL_FMD_ORCHESTRATION_TEMPLATE` in CODE maar op `PL_FMD_SCHEDULE_<short>` in INTEGRATION CONFIG, één per omgeving, met de parameters `Target` en `LoadGroup`. Reden: een promotie neemt een schedule mee (ingeschakeld, met de tijden van de bron), CONFIG zit in geen deployment pipeline. De keuze A/B en de `LoadGroup`-regels blijven; alleen de plek van het schema verandert. *Getest in eigen omgeving* (2026-10-11, `testplan-trial.md` T-D10).
  - \+ Actueel waar nodig.
  - − Meer CU, ook voor Gold na elke intraday-run.
  - − De intraday-bronnen moeten de juiste `LoadGroup` krijgen.

**Impact:** `DataSource.LoadGroup` per bron; het schema zelf wordt in de portal ingesteld (het staat niet in de repo; sinds het ontwerp van #52 op `PL_FMD_SCHEDULE_<short>` in CONFIG, en daar ook niet in git); CU-gebruik.

**Bitmetric-default:** geen; per klant.

**Afhankelijkheden:** B-CAP-01.

**Fase / wie:** fase 1, klant; ingericht in fase 5.

**Status:** open, per klant.

---

### B-GOLD-02 · Gold-laag en semantisch model

**Beslisvraag:** Hoe bouwen we de rapportagetabellen, en hoe leest Power BI ze?

**Opties:**
- **Gold:** A. **Materialized lake views** (MLV) in `NB_MLV_EXAMPLE` (+ declaratief, het framework-patroon; ~~− refresh-cel moet nog worden afgemaakt~~ *correctie 2026-10-05: de refresh-cel is af sinds PR #21 (2026-09-26), zie `06_BUSINESS_DOMEINEN/02_gold-laag-mlv.md`*). B. **Notebooks** die Delta-tabellen schrijven (+ volledige vrijheid; − meer code, eigen foutafhandeling).
- **Semantisch model:** A. **Direct Lake** (+ geen import, geen dubbele data; − de koppeling naar de lakehouse wijst na een promotie nog naar Dev en moet per stage worden hersteld, zie B-GOLD-01 en `04_semantisch-model-direct-lake.md`). B. **Import** (+ bekend, onafhankelijk van de lakehouse-koppeling; − geplande refresh, dubbele data).
- **Variant van Direct Lake** *(toegevoegd 2026-10-12, generale repetitie GR-B5)*:
  - **A. Op het SQL-endpoint** (`Sql.Database(<endpoint>, <endpoint-ID>)`).
    - Voor: de data source rule bij een promotie is getest met server plus database (*getest in eigen omgeving*, `testplan-trial.md` T-E03). Dit is ook wat de portal maakt bij "New semantic model" vanaf een lakehouse. *(Correctie 2026-10-26: dat geldt niet altijd. Volgens Microsoft Learn bepaalt de identiteitsmodus van het SQL-endpoint de standaard in de dialoog, OneLake bij user identity mode en SQL bij delegated mode, en kan de Power BI-service alleen OneLake aanmaken. Kies het type bewust en controleer de expressie.)*
    - Tegen: één bron-item per model; valt terug op DirectQuery bij SQL-views of beveiliging in het SQL-endpoint (*tweedehands*: Microsoft-documentatie, niet zelf getest).
  - **B. Op OneLake** (`AzureStorage.DataLake`).
    - Voor: tabellen uit meerdere Fabric-items in één model, bijvoorbeeld Gold van meerdere domeinen; OneLake-beveiliging; niet afhankelijk van de metadata-sync van het SQL-endpoint (*tweedehands*, idem).
    - Tegen: ~~of een data source rule deze verbinding bij een promotie omzet, is **niet getest** (*aanname*). Zonder rule moet de expressie na elke promotie met `updateDefinition` worden herschreven.~~
      - *Bijgewerkt 2026-10-26 (T-E08, `testplan-trial.md`, *getest in eigen omgeving* in `FMD_GR`):* een **data source rule** is voor dit model niet beschikbaar (grijs in de portal; de oorzaak is niet bewezen, zie T-E08 punt 3). Een **parameter rule** werkt wel, mits het pad in een parameter staat (`expression OneLakeUrl = "…" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]`, gebruikt in `AzureStorage.DataLake(OneLakeUrl, …)`). De rule blijft staan na een volgende promotie. Een model met een letterlijk pad valt terug op `updateDefinition` na elke promotie.
      - Een model dat via de rapport-editor (OneLake catalog) is aangemaakt, krijgt een letterlijk pad. Dat model moet je omzetten (parameter toevoegen) of opnieuw maken.
      - Niet getest: T → P.

**Impact:** Gold-notebooks per domein; deployment rules per stage (alleen in de portal); refresh-planning.

**Bitmetric-default:** MLV en Direct Lake, **op het SQL-endpoint** *(2026-10-12, Mitchell)*. Direct Lake op OneLake alleen als de klant één model wil over meerdere domeinen of OneLake-beveiliging gebruikt, en pas nadat de promotie met een data source rule voor die variant is getest (generale repetitie, blok C, optionele stap GR-C2b). *Bijgewerkt 2026-10-26 (T-E08):* GR-C2b is uitgevoerd, maar met een parameter rule in plaats van een data source rule (zie variant B). De default blijft het SQL-endpoint; OneLake is toegestaan met een parameter in het model.

**Afhankelijkheden:** B-WS-01.

**Fase / wie:** fase 1, samen; uitgewerkt in fase 6.

**Status:** default vastgesteld.

---

### B-CICD-02 · Git-provider en goedkeuring van promoties

**Beslisvraag:** Waar staat de code van het platform, en wie moet een promotie naar productie goedkeuren?

**Opties:**
- **Provider:** A. **GitHub, in een eigen Bitmetric-organisatie** (ADR-007, Accepted). + Eén plek voor alle klanten; de deploy-workflow wordt hergebruikt. − De klant heeft geen eigen repo-omgeving; toegang voor de klant regelen. B. **Azure DevOps** van de klant. + Past bij klanten die al Azure DevOps gebruiken; approval gates en Key Vault-gekoppelde variable groups. − Toegang voor externen is niet vanzelfsprekend; per klant een andere omgeving. C. **GitLab:** niet mogelijk. Fabric Git-integratie ondersteunt alleen Azure DevOps, GitHub en GitHub Enterprise, en alleen de cloudversies (Microsoft Learn, "Overview of Fabric Git integration", 2026-07-21).
- **Goedkeuring:** Deployment Pipelines (B-CICD-01) hebben geen goedkeuringsstap. Wie minstens Contributor is op de bron- én de doelstage, kan promoveren (Microsoft Learn, "Deploy content"). Een goedkeuring regel je daarom via de rollen: alleen een beperkte groep is Contributor op de Prod-workspaces en Admin van de deployment pipeline. Formele approval gates kan alleen een Azure Pipelines- of GitHub-workflow die de Fabric-API aanroept (fabric-cicd; volgens ADR-012 een later spoor, trigger: een klant eist approval gates).

**Impact:** repo-locatie, toegang voor externen, het mechanisme voor goedkeuring.

**Bitmetric-default:** A, GitHub in een eigen Bitmetric-organisatie, volgens ADR-007 (bevestigd door Mitchell, 2026-09-25). Azure DevOps alleen als de klant dat eist. *De voorkeur voor Azure DevOps in de opdracht (`Promp.txt`) is hiermee bijgesteld.* Goedkeuring via de rollen op de Prod-workspaces.

**Afhankelijkheden:** B-CICD-01.

**Fase / wie:** fase 1; Bitmetric (standaard), de klant kan afwijken als hij een eigen Azure DevOps-omgeving eist.

**Status:** default vastgesteld.

---

### B-MON-01 · Monitoring, logging en alerting

**Beslisvraag:** Hoe merken we dat een nachtelijke load is mislukt, en wie lost het op?

**Hoe het framework het doet (vastgesteld in code):** de pipelines en notebooks loggen naar `logging.PipelineExecution`, `NotebookExecution` en `CopyActivityExecution`; het FMD_Logging-rapport toont die. Er is **geen alerting** en **geen opschoning** van de logtabellen (append-only, zonder PK).

**Opties:**
- **A. Alleen het rapport.** + Niets te bouwen. − Iemand moet elke ochtend kijken.
- **B. Een melding bij een gefaalde run**, bijvoorbeeld een mail- of Teams-activiteit na `PL_FMD_LOAD_ALL`, of een Fabric Activator-regel. + Actieve melding. − Maatwerk, of Activator-kosten. Let op het eigen Activator-incident: een te ruime triggerconditie startte een pipeline bij elk workspace-event (`12_kosten-en-capaciteit.md`).
- **Retentie:** afspreken hoe lang logging bewaard blijft, en wie opschoont.

**Impact:** een extra activiteit of Activator; beheertaak voor opschoning.

**Bitmetric-default:** B, een melding bij een gefaalde `PL_FMD_LOAD_ALL` (bevestigd door Mitchell, 2026-09-25). Hoe precies (mail, Teams of Activator), werken we per klant uit; de klant kiest de ontvangers. *Uitwerking 2026-10-05:* de standaard is de ingebouwde **Failure notifications** op het schema van ~~`PL_FMD_SCHEDULE_NIGHTLY`/`_INTRADAY`~~ `PL_FMD_ORCHESTRATION_TEMPLATE` *(correctie 2026-10-06, review 3; getest 2026-10-06, rookproef 2 stap 11, op de wrapper `PL_FMD_SCHEDULE_NIGHTLY` en niet op de orchestratie (preciezer 2026-10-11, E-V4); de ontvangers gaan niet mee met een promotie)* (mail naar een groep, alleen geplande runs, alleen in te stellen in de portal). Dat kost geen bouwwerk en geen Activator-capaciteit. Activator alleen als de klant Teams of meer wil. Zie draaiboek fase 5 stap 4 (*vastgesteld* via Microsoft Learn; ~~niet getest~~ *getest in eigen omgeving 2026-10-06*, rookproef 2 stap 11, run `884c289b`). *Correctie 2026-10-11 (ontwerp `FMD_FRAMEWORK#52`, ADR-017; gemerged 2026-10-11, `4971d88`):* de Failure notifications staan op `PL_FMD_SCHEDULE_<short>` in INTEGRATION CONFIG, één keer per omgeving, in plaats van op de orchestratie in CODE. Reden: de ontvangers gaan niet mee met een promotie, en met de schema's in CONFIG hoeft er na een promotie niets meer te worden ingesteld. *Getest in eigen omgeving* (2026-10-11): mail ontvangen bij een gefaalde geplande run van `PL_FMD_SCHEDULE_P` (gemeld door Mitchell, geen run-ID vastgelegd).

**Afhankelijkheden:** B-OPS-01 (wie de melding krijgt).

**Fase / wie:** fase 1, samen (klant kiest ontvangers en kanaal); ingericht in ~~fase 7~~ fase 5 stap 4, en na de laatste promotie gecontroleerd in fase 7 (stap 4e en de productie-acceptatiechecklist) *(correctie 2026-10-06, review 3 P3-V12)*.

**Status:** default vastgesteld.

---

### B-GOV-01 · Governance

**Beslisvraag:** Moet de klant kunnen zien waar data vandaan komt (lineage), en wie is eigenaar van welke data?

**Opties:**
- **Purview:** A. **Aan.** Het framework heeft `PL_FMD_TOOLING_LOAD_TO_PURVIEW` en `NB_FMD_FABRIC_PURVIEW_LINEAGE_TABLE_COLUMN_EXTRACTOR` (haalt Purview-credentials uit de Key Vault van `key_vault_uri_name`). + Lineage tot op kolomniveau. − Purview-account en -credentials nodig; niet getest in de eigen omgeving. B. **Uit.**
- **Naamconventies:** workspaces volgens B-ARCH-01; Gold-objecten `gold.Fact*`/`gold.Dim*` (conventie, niet afgedwongen).
- **Eigenaarschap:** per domein een data-eigenaar; die bepaalt toegang en accordeert Gold (productie-acceptatiechecklist).

**Impact:** Purview-inrichting en secrets; rollen per domein (B-SECURITY-01).

**Bitmetric-default:** Purview uit, tenzij de klant het al gebruikt (bevestigd door Mitchell, 2026-09-25). Eigenaarschap per domein.

**Afhankelijkheden:** B-WS-01.

**Fase / wie:** fase 1, klant.

**Status:** default vastgesteld. *Nieuw op 2026-09-25 (review 1 R2).*

---

### B-UPG-01 · Frameworkversie en upgrades

**Beslisvraag:** Krijgt de klant na oplevering nieuwe versies van het framework?

**Opties:** zie **B-ARCH-02** in Deel B en ADR-002. A. **Geen updates na oplevering** (standaard). + Stabiel, geen onverwachte wijzigingen. − Fixes in de Bitmetric-fork komen niet vanzelf bij de klant. B. **Supportafspraak met gerichte updates** (`git cherry-pick`, daarna de normale promotie; bij een schemawijziging dacpac en setup-run). + Belangrijke fixes bereiken de klant. − Beheerlast; per update testen.

**Impact:** supportcontract; bij B een procedure per update.

**Bitmetric-default:** A. Heroverwegen bij ±5 klanten met een supportafspraak (ADR-002).

**Afhankelijkheden:** B-OPS-01.

**Fase / wie:** fase 1, samen; vastgelegd in fase 8.

**Status:** default vastgesteld.

---

### B-OPS-01 · Beheer en overdracht

**Beslisvraag:** Wie beheert het platform na de oplevering: de klant zelf, Bitmetric, of samen?

**Opties:**
- **A. Klant beheert zelf**, na een overdracht. + Geen afhankelijkheid. − De klant moet de kennis in huis hebben (registratie, troubleshooting, capaciteit).
- **B. Bitmetric beheert** onder een supportafspraak. + Kennis blijft beschikbaar. − Kosten; afspraken over reactietijd nodig.
- **C. Samen:** klant doet dagelijks beheer, Bitmetric de tweede lijn.

**Impact:** overdrachtssessies (fase 8), toegangsrechten, alerting (B-MON-01), supportcontract (B-UPG-01).

**Bitmetric-default:** geen; per klant. Het draaiboek gaat uit van een overdracht (fase 8).

**Afhankelijkheden:** B-UPG-01, B-MON-01.

**Fase / wie:** fase 1, klant; uitgevoerd in fase 8.

**Status:** open, per klant. *Nieuw op 2026-09-25 (review 1 R1).*

---

## Deel B — Vastgestelde besluiten (12, geaccepteerd)

Deze besluiten gelden voor elke klant. Voor de ontbrekende velden: ze zijn genomen door **Bitmetric** (Mitchell), gelden **vóór fase 1**, en hun afhankelijkheden staan in de overzichtstabel van Deel A.

### **B-ARCH-01: Workspace-naamgeving**
**Onderwerp:** Standaard voor workspace-namen in Fabric-omgevingen
**Voorstel:** `[DOMEIN] [LAAG] ([OMG])` waar OMG = omgevingsmarker (D/T/P)
**Voorbeelden:**
- Dev: `FINANCE DATA (D)`, `SALES SEMANTIC (D)`
- Prod: `FINANCE DATA`, `SALES SEMANTIC` (geen OMG-suffix)

**Akkoord:** ✅ Mitchell, OV-01 (2026-09-21): "De naamgeving moet als volgt zijn: [DOMEIN] [LAAG] ([OMG])... bij productie zetten we geen [OMG]-verwijzing in de naam."
**Gevolgen:**
- Setup-notebooks implementeren deze conventie — zie de update hieronder voor de status van deze implementatie
- Intake-checklist: expliciet controleren in klantimplementaties
- Geen underscores, geen volledige omgevingscode (bijv. `FINANCE_DATA_D`) — dat was een afwijkende suggestie in het conceptdocument die hiermee is verworpen

**Update (v1.7, 2026-09-23):** de bewering hierboven dat de setup-notebooks deze conventie al gebruikten ("geen wijziging nodig") bleek niet te kloppen — een repo-audit (zie `01_kennisbasis/open-vragen.md`, OV-01) vond dat `NB_SETUP_FMD.ipynb`/`NB_SETUP_BUSINESS_DOMAINS.ipynb` ook in Productie een `(P)`-suffix toevoegden. Dit is inmiddels gerepareerd via PR #5, "Production-workspaces krijgen geen omgevingsmarker in de naam" (commit `f669a74`, gemerged 2026-09-22 11:40): een nieuwe `ws_suffix()`-helper in de manifest-bootstrap-cel van beide notebooks geeft `""` terug voor Production (short `P`) in plaats van `" (P)"`, en alle plekken die workspacenamen opbouwen gebruiken nu deze ene functie. `scripts/test_manifest_wiring.py` en `manifest.example.yaml` zijn in dezelfde PR bijgewerkt. Geen open actiepunt meer.

**Bron:** `architectuur.md` (OV-01) / live omgeving; update: commit `f669a74`

---

### **B-ARCH-02: Framework-wijzigingen — fork vs. klantrepo**
**Onderwerp:** Wat mag worden aangepast in FMD-code?
**Voorstel:**
- **Fork** (`bitmetric-fabric/FMD_FRAMEWORK`): volledig wijzigbaar als "generieke verbetering" (categorie A)
- **Klantrepo's** (op basis van FMD-template): geen wijzigingen aan frameworkcode, alleen configuratie

**Categorisering van fork-wijzigingen:**
- Categorie A (generiek, upstream-PR-kandidaat): ci/cd, configdb-DDL, setup-notebooks, tooling
- Categorie B (Bitmetric-specifiek, niet upstream): GUID-guard, RBAC-checks, monitoring-reports
- Categorie C (referentie-implementatie, niet generiek): business-domain-specifieke Gold-layer-notebooks

**Akkoord:** ✅ Mitchell, OV-04: "We passen de frameworkcode niet aan, slaat op de fork. We passen de code van de originele FMD-repo zo aan dat deze geschikt is voor klantimplementaties bij Bitmetric. Voorstel is correct."
**Gevolgen:**
- Klanten krijgen gefreezde fork-versie + configuratie-repo
- Upstream-PR's zijn verdedigbaar (categorie A)
- Geen "mag niets veranderen"-rigiditeit in operatie

**Bron:** `architectuur.md` (OV-04) / git log fork vs. upstream

---

### **B-ARCH-04: Referentie-implementatie bevestigd (F2/AdventureWorks)**
**Onderwerp:** Bestaat de referentie-implementatie waarnaar het conceptdocument verwijst ("F2-capacity met AdventureWorks, LZ→Bronze→Silver gevalideerd met full en incremental loads")?
**Situatie in Fase 1:** claim kon niet worden geverifieerd in de onderzochte architectuur-/CI-CD-bronnen (OV-02).

**Akkoord:** ✅ Mitchell, OV-02: "Referentie implementatie bestaat op zowel de Bitmetric als trial capacity."
**Gevolgen:**
- Claim is hiermee bevestigd — geen bijstelling van `architectuur.md` nodig
- Voor Fase 3: locatie/toegang tot deze referentie-implementatie (beide capaciteiten) vastleggen zodat klantimplementaties er als voorbeeld naar kunnen verwijzen

**Update (Fase 3, 2026-09-22) — deels uitgevoerd, met een discrepantie om te verifiëren:** in de fork-repo zelf staat een uitgewerkte demo-implementatie, `NB_MLV_DEMO_GOLD` (`FMD/examples/`), gedocumenteerd in `06_BUSINESS_DOMEINEN/02_gold-laag-mlv.md`. Deze draait echter op een **Wide World Importers (WWI)-achtige demoset**, niet op AdventureWorks zoals de oorspronkelijke claim stelde. Onduidelijk of dit dezelfde referentie-implementatie is als waar Mitchell in OV-02 naar verwees, of een andere (mogelijk is "AdventureWorks" een verspreking/verwarring met WWI, of gaat het om twee verschillende implementaties). De **live locatie/toegang** tot de referentie-implementatie op de Bitmetric- en trial-capacity (workspace-namen/links) is nog niet vastgelegd — dat vereist input van Mitchell, niet af te leiden uit de gekloonde fork-repo.

**Update (2026-09-25):** Mitchell bevestigt dat de referentie-implementatie op **AdventureWorks** draait. Het zijn dus twee verschillende dingen: de referentie-implementatie (AdventureWorks, op de Bitmetric- en de trial-capaciteit, buiten de repo) en de demo in de fork (`NB_MLV_DEMO_GOLD`, WWI). De discrepantie is daarmee opgelost. **Let op:** de trial-capaciteit wordt leeggehaald voor de hertest; de kopie op de trial verdwijnt dan. **Locatie (2026-09-25, read-only via de Fabric MCP):** namespace `aw` (AdventureWorks: `Production_Product`, `Production_ProductCategory`, `Production_ProductModel`, `Production_ProductSubcategory`, `Sales_Customer`) in `LH_DATA_LANDINGZONE` van `INTEGRATION DATA (D)` op de Bitmetric-capaciteit, sinds 2026-08-07. Op de trial: `FMDTRIAL DATA (D)`, dezelfde tabellen plus `Sales_SalesOrderHeader` en `Sales_SalesOrderDetail`, 2026-09-15. Alleen de landingzone is bekeken; Bronze en Silver niet.

**Bron:** `architectuur.md` (OV-02); `FMD/examples/NB_MLV_DEMO_GOLD.Notebook` (repo-audit 2026-09-22)

---

### **B-CICD-01: Promotiemechanisme — Deployment Pipelines als default (voor nu)**
**Onderwerp:** Dev → Test → Prod: hoe?
**Voorstel:** Microsoft Fabric **Deployment Pipelines** (native, no-code) als Bitmetric-standaard
**Alternatieven overwogen:**
- fabric-cicd als promotiemechanisme (ADR-006) — status **Proposed**, niet Accepted. *Correctie 2026-10-05: ADR-006 is gesloten door ADR-012 (besluit Mitchell 2026-10-05, PR #32, gemerged `9ae2182`): Deployment Pipelines is het promotiemechanisme, fabric-cicd een later spoor.* ADR-006 stond kort op Accepted maar is dezelfde dag heroverwogen: er bestaat al werkende Deployment-Pipeline-automatisering in `NB_UTILITIES_SETUP_FMD`, en een eerdere fabric-cicd-pilot voor INTEGRATION CODE is teruggedraaid omdat client-specifieke extensies ongetracked bleven.
- Een uitgewerkt plan voor fabric-cicd + GitHub Actions (n.a.v. een Reddit-post over onbetrouwbaarheid van Deployment Pipelines) is expliciet afgewezen via `ExitPlanMode` in een eerdere sessie.

**Akkoord:** ✅ Mitchell (2026-09-22): "Voor nu zijn deployment pipelines de default. Later wil ik dit misschien omzetten naar fabric-cicd." Hiermee is Deployment Pipelines definitief de huidige Bitmetric-standaard; ADR-006 (fabric-cicd) blijft bewust als toekomstige heroverweging staan, geen actief te plannen proef.

**Gevolgen:**
- Setup inclusief Deployment Pipeline-aanmaak
- ~~Shortcuts moeten **handmatig** opnieuw in Test/Prod (bekende Fabric-beperking, MS Learn — zie B-GOLD-01)~~ *Correctie 2026-10-05: shortcuts gaan mee met de promotie van DATA en wijzen daarna naar Silver van het doel (getest in eigen omgeving, `testplan-trial.md` T-E04, D → T; `testplan-devflow.md` F5, D → T → P). Na elke promotie alleen controleren; zie B-GOLD-01.*
- Geen git-driven deployment in Test/Prod (enkel Dev, conform ADR-005)
- Waarden per omgeving staan in value sets met een actieve value set per workspace, anders overschrijft de promotie ze met die van Dev (ADR-010, fork vanaf `81fe912`). Na elke promotie controleren.
- fabric-cicd is een bewuste toekomstige optie, geen actieve Fase 3/4-actie — wel het ADR-006-statusveld (Proposed) laten staan zodat een latere omzetting niet als "verrassing" voelt. *Bijgewerkt 2026-10-05: ADR-006 is gesloten door ADR-012; de triggers voor heroverweging staan daar en in de ADR-README.*

**Bron:** `cicd.md` — concept-beslisdocument §3.3 (Deployment Pipelines als Bitmetric-default) + ADR-006 (Proposed). *Niet* ADR-007: die ADR gaat over CI/CD-hosting in een eigen GitHub-organisatie (repo-structuur), niet over de keuze Deployment Pipelines vs. fabric-cicd — de v1.1-verwijzing naar "ADR-007 Accepted" was onjuist.

---

### **B-INFRA-01: Configuratiedatabase — schema's en registratieketen**
**Onderwerp:** Hoe worden bronnen/entiteiten geregistreerd?
**Voorstel:** Via de tabellen in het `integration`-schema (`Connection`, `DataSource`, `LandingzoneEntity`/`BronzeLayerEntity`/`SilverLayerEntity`). Die laatste drie worden in één keer gevuld door `sp_UpsertLandingzoneBronzeSilver`; `LandingzoneBronzeSilver` is een procedurenaam, geen tabel.
- `sp_UpsertConnection` → bronconnectie (database, file, etc.)
- `sp_UpsertDataSource` → logische source (tabel, schema, query)
- `sp_UpsertLandingzoneBronzeSilver` → transformatiestappen LZ→Bronze→Silver
- Bulk: `PL_TOOLING_POST_ASQL_TO_FMD`-pipeline

**Status:** vastgesteld feit uit de kennisbasis (dit was geen open vraag — de v1.1-verwijzing naar "Mitchell OV-12" was onjuist toegepast; OV-12 gaat uitsluitend over de deactiveringsprocedure, zie B-INFRA-02).
**Gevolgen:**
- Klanten voeren dezelfde registratieprocedure uit
- Configdb-DDL is vastgesteld in `configdb.md`
- Execution/Logging-schema's voor monitoring

**Bron:** `configdb.md` / `registratie.md`

---

### **B-GOLD-01: Shortcuts naar Silver + Deployment Pipelines — workaround**
**Onderwerp:** Gold-layer gebruikt shortcuts naar Silver. Hoe hiermee omgaan bij promotie?
**Voorstel:**
- Deployment Pipeline promoveert Gold-workspace zelf (de notebooks)
- Shortcuts worden **NIET** meegenomen (bekende MS-beperking)
- **Operationele workaround:** handmatig `NB_CREATE_SHORTCUTS` draaien na elke deployment naar Test/Prod

**Correctie 2026-09-28 (getest in eigen omgeving, `testplan-trial.md` T-E04):** de twee punten hierboven kloppen niet meer. Shortcuts staan in de definitie van de lakehouse en gaan mee met de promotie van de DATA-workspace. De deployment pipeline zet de Gold → Silver-shortcuts om naar Silver van het doel, ook nieuwe shortcuts (D → T getest; T → P niet). *Aangevuld 2026-10-05: T → P is end-to-end geslaagd in de ontwikkelflow-test (`testplan-devflow.md` F5, 2026-09-29: Prod geladen, gepromoveerd, MLV en refresh in P).* Nieuw voorstel: DATA gewoon promoveren en daarna de shortcuts controleren; `NB_CREATE_SHORTCUTS` alleen als terugval, bijvoorbeeld bij de eerste uitrol van een omgeving. De reden voor dit besluit vervalt daarmee grotendeels.

**Status:** ~~vastgesteld feit uit de kennisbasis (MS Learn-limitatie, bevestigd in meerdere bronnen — geen open vraag).~~ *Achterhaald door de correctie hierboven (getest in eigen omgeving, 2026-09-28/29).* De v1.1-verwijzing naar "Mitchell OV-13" was onjuist: OV-13 gaat over een vermoedelijke `PL_FMD_LDZ_COMMAND_FTP`-bug, niet over shortcuts. Zie de sectie "Operationele bevindingen → Fase 3" hieronder voor de juiste plek van OV-13.
**Gevolgen:**
- Documentatie expliciet ("na deployment deze notebooks handmatig draaien")
- Runbook voor Test/Prod-promotie
- Monitoring: cross-workspace references kunnen stuk zijn tot `NB_CREATE_SHORTCUTS` runt

**Bron:** `gold-en-semantic.md` / MS Learn Fabric limitations

---

### **B-SECURITY-01: RBAC — rollen en rechten per werkfunctie**
**Onderwerp:** Wie mag wat (bootstrap, deployment, monitoring, etc.)?
**Voorstel:** Rollen-/rechtenmatrix (zie `04_intake-checklist.md`, Deel 5):
- **Bootstrap-eigenaar:** Workspace-admin + Key Vault-owner + Fabric-capaciteitsadmin
- **Data-engineer:** Workspace-contributor (notebooks, pipelines aanmaken)
- **DevOps:** Deployment Pipeline-admin (setup, approvals)
- **Analyst:** Workspace-viewer (read-only reporting)
- **Monitoring:** Service Principal met Workspace-Reader + Log Analytics-toegang

**Akkoord:** ✅ Mitchell, OV-07: "Voorstel akkoord."
**Gevolgen:**
- RBAC-matrix wordt onderdeel van intake-checklist
- *Noot (2026-09-25):* twee onderdelen van het voorstel bestaan niet zoals beschreven. Deployment Pipelines hebben geen goedkeuringsstap ("approvals"): promoveren mag wie Contributor is op bron- en doelstage (Microsoft Learn, zie B-CICD-02). En het framework logt naar de configuratiedatabase, niet naar Log Analytics. De rollenmatrix in de intake-checklist v2.0 gaat daarom uit van rollen op de workspaces en de deployment pipelines.
- Foutief toegewezen rollen → bootstrap-fouten (mitigatie: pre-flight-checks)
- Key Vault IAM-samenstelling kritisch (zie `security.md`)

**Bron:** `security.md` (OV-07) / fmd-admin-rechten RBAC-artefact

---

### **B-EXT-01: Extensiepunten — wat is out-of-the-box, wat per klant?**
**Onderwerp:** CustomNotebookName, RDW, GA4, Dataflow Gen2?
**Voorstel:**
- **Out-of-the-box:** CustomNotebookName-mechanisme (parametriseerbaar, generiek beschikbaar — elke bron kan het gebruiken)
- **Referentie-implementatie:** **geen.** *(Correctie 2026-09-22, repo-audit + directe bevestiging door Mitchell: "Er is gewoon een customnotebook beschikbaar. Maar niet specifiek voor RDW."* Een eerdere versie van dit document en van `bronnen-en-extensies.md` claimde ten onrechte een RDW-referentie-implementatie met 3 voorbeeldnotebooks in `examples/` — die bestaat niet. De repo bevat wel `examples/` met 2 andere, niet-brongebonden notebooks (`NB_CREATE_DIMDATE`, `NB_MLV_DEMO_GOLD`).)*
- **GA4:** bestaat, maar uitsluitend als **eigen test** bij Mitchell — niet als gedocumenteerde referentie-implementatie in FMD.
- **Dataflow Gen2:** geen implementatie en bewust geen scope in FMD. De "twee Dataflow Gen2-patronen" uit de bronnen bleken bij navraag puur een verkenning te zijn geweest van SharePoint als bron — niet een Dataflow Gen2-beslissing.
- **Overige extensies:** per klant via configuratie in `integration.DataSource`

**Akkoord:**
- ✅ Mitchell, OV-05: "Beide bestaan ze, maar ze bestaan slechts als eigen test, niet als referentie" (GA4)
- ✅ Mitchell, OV-06: "Dit was slechts ter verkenning van het toevoegen van SharePoint als bron. We gaan vooralsnog in het FMD niets doen met dataflows."
- ✅ Mitchell (2026-09-22, n.a.v. repo-audit): geen RDW-referentie-implementatie

**Impact voor Fase 3:** `05_INTEGRATION/` mag geen RDW-voorbeeld als referentie-implementatie presenteren. Als er behoefte is aan een echt uitgewerkt voorbeeld (bijv. voor klant-onboarding), is dat nieuw werk, geen bestaande asset.

**Gevolgen:**
- Extensieverificatie in intake-checklist
- GA4 niet aanbieden als "getest, klaar voor gebruik" richting klanten — wél vermelden dat er interne ervaring mee is
- Richtlijn voor klantgerichte extensies (aanbevelingen in Fase 3)

**Bron:** `bronnen-en-extensies.md` (OV-05, OV-06)

---

### **B-SECURITY-02: Welke identiteit per framework-connectie**
**Onderwerp:** Workspace Identity of een expliciete Service Principal voor de connecties die de setup aanmaakt?
**Voorstel (herschreven 2026-09-25, volgt de code):**
- `CON_FMD_FABRIC_SQL` (`FabricSql`): **Service Principal**, met tenant-ID, client-ID en secret in Key Vault. De setup maakt de connectie daarmee automatisch aan.
- `CON_FMD_FABRIC_PIPELINES` en `CON_FMD_FABRIC_NOTEBOOKS`: **Workspace Identity**, zoals de setup ze aanmaakt.
- Een handmatige OAuth2-connectie voor `CON_FMD_FABRIC_SQL` alleen als bewuste uitzondering: die hangt aan een persoon en verloopt na 90 dagen inactiviteit.

**Reden:** `FabricSql` accepteert geen Workspace Identity (`UnsupportedCredentialType`, volgens de docstring van upstream-commit `5e934ab`; niet zelf getest). Een SP hangt niet aan een persoon en de setup kan hem automatisch gebruiken. Voor de andere twee connecties werkt Workspace Identity wel. *De oude reden ("een versieverschil in Fabric") is achterhaald, en het oude voorstel ("overal een SP") week af van de code (review 2, F6d).*

**Akkoord:** ✅ Mitchell, OV-08: "Voorstel akkoord" (oorspronkelijke formulering). ✅ Mitchell, 2026-09-25: herschreven voorstel "volg de code".
**Gevolgen:**
- Vóór de setup: SP aanmaken, toegang geven tot de CONFIGURATION-workspace, en de drie secrets in Key Vault zetten (`manifest.key_vault`). De setup stopt zonder `key_vault` in het manifest.
- Degene die de setup draait, heeft leesrechten op die secrets nodig.
- Rotatieprocedure: secret-update in Key Vault, en daarna de credential van `CON_FMD_FABRIC_SQL` bijwerken. De setup slaat een bestaande connectie over, dus een nieuw secret komt er niet vanzelf in. *(Aanname, niet getest.)*
- Zie `03_technische_documentatie/08_security-en-secrets.md`.

**Bron:** `security.md` (OV-08)

---

### **B-INFRA-02: Deactiveringsprocedure (entiteiten, bronnen)**
**Onderwerp:** Hoe een bron/entiteit deactiveren (reversibel)?
**Voorstel:** deactiveren met `IsActive = 0` op de **entiteitstabellen**, nooit met DELETE:
1. Eén entiteit of een hele bron stoppen: `integration.LandingzoneEntity.IsActive = 0` (per `LandingzoneEntityId` of per `DataSourceId`). Dat stopt Landingzone, Bronze en Silver, omdat alle drie de `execution`-views op `LZE.IsActive` filteren.
2. Fijnmaziger: `BronzeLayerEntity`/`SilverLayerEntity.IsActive = 0` stopt alleen die laag en de lagen erna.
3. `Connection.IsActive`/`DataSource.IsActive` zijn administratief. Ze stoppen de load **niet**, want geen enkele view of pipeline filtert erop.

De uitvoerbare SQL en de controlequery staan in `03_technische_documentatie/05_INTEGRATION/02_configdb-registratie.md` §Deactivering.

**Akkoord:** ✅ Mitchell, OV-12 (oorspronkelijke formulering) en opnieuw op 2026-09-25 voor de herschreven procedure: aanpak "documenteren + controlequery na elke registratieronde".
**Gevolgen:**
- Geen DELETE en geen cascading deletes nodig
- Monitoring: rapporteer op `integration.LandingzoneEntity WHERE IsActive = 0` voor archivering
- **Herregistratie zette de entiteit weer aan.** `sp_UpsertLandingzoneBronzeSilver` zette `IsActive = 1` hard, ook bij een bestaande entiteit. Met een oudere dacpac moet je daarom na elke registratieronde controleren of gedeactiveerde entiteiten nog gedeactiveerd zijn. **Fork-fix (categorie A, B-ARCH-02), besloten door Mitchell op 2026-09-25:** `sp_UpsertLandingzoneBronzeSilver` laat `IsActive` van bestaande entiteiten ongemoeid. Gemerged als PR #8 (fork-commit `4dd41cf`, 2026-09-25). **Opgelost vanaf `4dd41cf`**: de waarschuwing geldt alleen nog voor configdb's waarop een oudere dacpac staat. Wordt getest in `testplan-trial.md` (T-C04).

**Update (2026-09-25, review 1 F3 / review 2 M-F3):** de oorspronkelijke procedure zette `Connection` en `DataSource` op 0, zonder effect op de load, en noemde een tabel `integration.LandingzoneBronzeSilver` die niet bestaat (het is een procedurenaam). Herschreven naar de werkende procedure. Herbevestigd door Mitchell op 2026-09-25. De procedure wordt getest bij de eerste implementatietest (draaiboek fase 5, stap 5); tot die tijd is de status "vastgesteld in code, niet getest".

**Bron:** `registratie.md` (OV-12); `FMD/src/Config_Database/execution/Views/*.sql`; `integration/StoredProcedures/sp_UpsertLandingzoneBronzeSilver.sql`

---

### **B-ARCH-03: ADR-009 (GUID-guard) — locatie geverifieerd, opgelost**
**Onderwerp:** Waar staat de ADR-tekst voor GUID-guard?
**Situatie in Fase 1:** `docs/adr/README.md` noemt ADR-009 als "Accepted" in de indextabel, maar `docs/adr/009-guid-guard.md` was niet aangetroffen in de fork. De implementatie zelf (guid_guard.py, workflow, allowlist) is wél gemerged.

**Akkoord:** ✅ Mitchell, OV-03: "ADR-009 is geplaatst in de map bronnen."
**Update (Fase 3, 2026-09-22):** geverifieerd tegen de fork-code — `docs/adr/009-guid-guard.md` staat inmiddels op de conventionele plek (commit `703017b`, "Add ADR-009 (#6)"), status "Accepted", consistent met de indextabel in `docs/adr/README.md`. **Actie afgerond, geen open punt meer.**

**Bron:** `FMD/docs/adr/009-guid-guard.md`, commit `703017b`

---

### **B-INFRA-03: Livy-sessie-lifecycle en Spark-pool-sizing**
**Onderwerp:** Sessies, timeouts, capaciteitscontentie
**Voorstel:**
- Livy-sessies sterven na inactiviteit of een lange wachttijd (`LIVY_JOB_TIMED_OUT`) — check sessiestatus vóór gebruik, maak zo nodig een nieuwe sessie aan
- Spark-pool: gebruik de geverifieerde repo-default **4 cores/28GB** (`ENV_FMD.Environment/Setting/Sparkcompute.yml`, verlaagd vanaf 8 cores/56GB om binnen een F2-capaciteit te passen) — **er is geen apart, lager minimum**
- Bij vertraging (>20-25 min wachttijd in de queue) → geduldig pollen, bij structurele contentie capaciteit herplannen/opschalen
- Monitoring: FMD_Logging-rapport traceert NotStarted-jobs per domein

**Status:** vastgesteld feit uit de kennisbasis (`operations.md` / `kosten.md`, incl. het Activator-kostenincident) — geen open vraag. De v1.1-verwijzing naar "Mitchell OV-12" was hier onjuist toegepast (zie B-INFRA-02 voor de juiste OV-12-toewijzing).

**Correctie (v1.6, 2026-09-22, Fase 5-consistentiecheck):** deze regel bevatte tot v1.5 het cijfer "min. 2 cores, 4 GB geheugen per werknoot" als vastgesteld. Bij het opstellen van `03_technische_documentatie/12_kosten-en-capaciteit.md` en de correctie van `02_beslisdocument/04_intake-checklist.md` (v1.4) is dit cijfer **exhaustief nagezocht in alle bronnen** (kennisbasis, chat-transcripten, repo-manifest) en **niet teruggevonden** — vermoedelijk een niet-geverifieerde aanname uit een eerdere documentversie. De enige daadwerkelijk geverifieerde waarde is de repo-default van 4 cores/28GB. Dit besluit is hierop aangepast; zie `05_consistentiecheck/05_traceerbaarheidsmatrix.md`, bevinding T1, voor de volledige toelichting. De escalatiedrempel is tegelijk gelijkgetrokken naar >20-25 min (was >15-20 min), conform de rest van de documentatieset (bevinding T2).

**Gevolgen:**
- Setup-notitie: Spark-pool-configuratie (4 cores/28GB als startpunt, aanpassen op basis van daadwerkelijke capaciteit)
- Runbook: diagnostiek voor queue-items
- Intake-checklist: capaciteitsbepaling per klant-workload

**Bron:** `operations.md` / `kosten.md`; correctie: `03_technische_documentatie/12_kosten-en-capaciteit.md`, `02_beslisdocument/04_intake-checklist.md` v1.4

---

## Operationele bevindingen → Fase 3

Tijdens Fase 1 zijn vier operationele bevindingen gedaan die relevant zijn voor technische documentatie (Fase 3), maar geen architectuurbeslissing vergen:

1. **Casing-mismatch in `PL_TOOLING_POST_ASQL_TO_FMD`:** camelCase (JSON-velden) vs. PascalCase (pipeline-parameters).
   Mitchell (OV-09): "De casing bug moeten we nog even bespreken" → wordt in Fase 3 als technisch aandachtspunt uitgewerkt, met ruimte voor verdere bespreking.
   → Onderdeel van `05_INTEGRATION/`-technische spec (registratiefase)

2. **Positional-parameter-bug in bulk-script:** parameters doorgegeven op positie i.p.v. naam.
   Mitchell (OV-10): "Deze weet ik niet."
   → Best practice voor bulk-registratie in implementatieplan (Fase 4)

3. **Notebook-/branch-versiemismatch:** versieverschillen tussen lokale notebooks en main-branch.
   Mitchell (OV-11): "Weet ik ook niet."
   → Deel van CI/CD-checks en pre-deployment-verificatie in intake-checklist

4. **`PL_FMD_LDZ_COMMAND_FTP` — vermoeden van verkeerd-doelwit-bug:** tijdens onderzoek naar de registratieketen ontstond het vermoeden dat deze pipeline mogelijk naar een verkeerd doel(pad) verwijst in bepaalde configuraties; niet volledig bevestigd of weerlegd.
   Mitchell (OV-13): "Voorstel akkoord" — d.w.z. akkoord om dit als aandachtspunt te markeren voor gerichte verificatie, **niet** als vastgestelde bug te presenteren totdat bevestigd. *(In v1.1 stond dit ten onrechte niet vermeld — OV-13 was daar abusievelijk gekoppeld aan B-GOLD-01.)*
   → Gerichte verificatie (bijv. handmatige test) vóór dit als vastgesteld gedrag in `05_INTEGRATION/` wordt opgenomen
   **Uitkomst (2026-09-22, opnieuw gecontroleerd op 2026-09-25 tegen `81fe912`): vals alarm.** De `InvokePipeline`-activity in `PL_FMD_LDZ_COMMAND_FTP` heet `PL_FMD_LDZ_COPY_FROM_ADF`, maar zijn `pipelineId` (`4972831f-…`) is de `logicalId` van `PL_FMD_LDZ_COPY_FROM_FTP_01`. Alleen het label is misleidend. Zie `13_referentie-implementatie-bitmetric.md` §LDZ-FTP-verificatie.

Deze vier worden in Fase 3/4 als operationele aandachtspunten uitgewerkt, niet als openstaande architectuurvragen.

---

## Volgende stappen

**Fase 2 (Beslisdocument):**
- [x] Beslisregister finaal (12 besluiten, geen openstaande punten) *Correctie 2026-10-05: dit geldt voor Deel B. Open staan nog de klantbeslissingen in Deel A (B-CAP-01: minimum F2, Mitchell 2026-10-05), die per klant bij de intake worden ingevuld.*
- [x] Architectuurvarianten uitgewerkt (Deployment Pipelines, met correcte ADR-verwijzingen)
- [x] Intake-checklist klaar
- [x] B-CICD-01 bevestigd door Mitchell (2026-09-22): Deployment Pipelines is de default; fabric-cicd blijft een bewuste toekomstige optie

**Fase 3 (Technische documentatie):**
1. [x] `05_INTEGRATION/` — LZ/Bronze/Silver DDL-spec + configdb-registratie (incl. correctie casing-mismatch, zie punt 3)
2. [x] `06_BUSINESS_DOMEINEN/` — generiek Gold-layer-/shortcuts-/Semantic-model-patroon (i.p.v. losse 05_FINANCE/05_SALES/05_HR — zie B-ARCH-04-vervolg hieronder)
3. [x] Operationele bevindingen geïntegreerd: casing-mismatch (bleek géén bug na live test), parameter-handling, versiecontrole, LDZ-FTP-bug (vals alarm)
4. [x] Implementatieplan-template — staat als `04_implementatieplan/implementatieplan-template.md`
5. [x] ADR-009 in de fork op de conventionele locatie geverifieerd (B-ARCH-03) — opgelost, staat er (commit `703017b`)
6. [ ] Referentie-implementatie (B-ARCH-04) toegankelijk maken/documenteren voor klantgebruik — deels gedaan (fork-demo `NB_MLV_DEMO_GOLD` gedocumenteerd in `06_BUSINESS_DOMEINEN/`), live tenant-locatie (Bitmetric + trial capacity) nog niet vastgelegd
7. [x] B-ARCH-01-implementatiegat gedicht: setup-notebooks voegden nog een `(P)`-suffix toe aan Productie-workspaces — gefixt via PR #5 (commit `f669a74`, 2026-09-22)

**Versiegeschiedenis:**
- v1.0 (2026-09-21): Initial draft, 11 geaccepteerd + 2 open
- v1.1 (2026-09-21): Finaal, operationele bevindingen → Fase 3
- v1.2 (2026-09-21): Review — OV-nummers gecorrigeerd tegen de daadwerkelijke antwoorden van Mitchell; B-CICD-01 bron gecorrigeerd (ADR-007 → onterecht) en gemarkeerd als voorlopige default i.p.v. hard besluit; B-INFRA-01/B-GOLD-01/B-INFRA-03 ten onrechte aan OV-12 gekoppeld, nu gecorrigeerd; B-EXT-01 GA4-feit gecorrigeerd; B-ARCH-04 (OV-02, referentie-implementatie) en vierde Fase-3-bevinding (OV-13, LDZ-FTP-bug) toegevoegd — beide ontbraken in v1.1
- v1.3 (2026-09-22): B-CICD-01 definitief bevestigd door Mitchell — Deployment Pipelines is de huidige default, fabric-cicd blijft een bewuste toekomstige heroverweging (geen actieve proef gepland). Kanttekening verwijderd, geen openstaande punten meer.
- v1.4 (2026-09-22): B-EXT-01 gecorrigeerd n.a.v. de `_fmd-watch`-repo-audit — de RDW-referentie-implementatie bestaat niet (bevestigd door Mitchell); dit was al in `01_kennisbasis/bronnen-en-extensies.md` verwerkt maar nog niet in dit beslisregister.
- v1.5 (2026-09-22): B-ARCH-03 (ADR-009-locatie) opgelost — bestand staat op de juiste plek in de fork, geverifieerd tegen commit `703017b`. B-ARCH-04 (referentie-implementatie) aangevuld met de gevonden fork-demo `NB_MLV_DEMO_GOLD` (WWI-dataset, niet AdventureWorks — discrepantie gemarkeerd voor Mitchell); live tenant-locatie blijft open. Fase 3-roadmap bijgewerkt met de daadwerkelijke voortgang (`05_INTEGRATION/`, `06_BUSINESS_DOMEINEN/`, operationele bevindingen).
- v1.6 (2026-09-22): B-INFRA-03 gecorrigeerd n.a.v. de Fase 5-consistentiecheck (`05_consistentiecheck/05_traceerbaarheidsmatrix.md`, bevinding T1/T2): het niet-geverifieerde "2 cores/4GB minimum"-cijfer verwijderd en vervangen door de wél geverifieerde 4 cores/28GB-default; escalatiedrempel gelijkgetrokken naar >20-25 min.
- v1.7 (2026-09-23, geautomatiseerde repo-watch): B-ARCH-01 bijgewerkt — de "Gevolgen"-bullet die stelde dat de setup-notebooks al geen wijziging nodig hadden, bleek (per het reeds gesignaleerde OV-01-aandachtspunt) niet te kloppen; de daadwerkelijke code-fix is nu gemerged (PR #5, commit `f669a74`). Update-paragraaf en actiepunt 7 toegevoegd.
- v1.8 (2026-09-25, review 1 F3 / review 2 M-F3): B-INFRA-02 herschreven naar de werkende procedure (`LandingzoneEntity.IsActive`; `Connection`/`DataSource` zijn administratief), met de waarschuwing dat herregistratie entiteiten weer activeert. B-INFRA-01: `LandingzoneBronzeSilver` is een procedure, geen tabel. Herbevestigd door Mitchell op 2026-09-25.
- v1.9 (2026-09-25): B-SECURITY-02 herschreven naar de code (SP voor `CON_FMD_FABRIC_SQL`, Workspace Identity voor de andere twee), herbevestigd door Mitchell. B-ARCH-04: de referentie-implementatie draait op AdventureWorks, de fork-demo op WWI (twee verschillende implementaties). Operationele bevinding 4 (LDZ-FTP): uitkomst vals alarm vastgelegd. B-INFRA-02: de fork-fix voor herregistratie is gemerged (PR #8, `4dd41cf`). B-CICD-01: de gevolgen-regel over value sets vervangen door het mechanisme van ADR-010 (fork-commit `81fe912`).
- v2.0 (2026-09-25), review 1 R1 en review 2: nieuw Deel A met 16 klantbeslissingen over alle twaalf categorieën uit de opdracht, elk met de gevraagde velden (opties met voor- en nadelen, impact, default, afhankelijkheden, fase, wie beslist). Nieuwe besluiten: B-CAP-01, B-NET-01, B-WS-01, B-ENV-01, B-ENV-02 (gedeelde configdb, vastgesteld in code), B-LOAD-01/02, B-GOLD-02, B-CICD-02, B-MON-01, B-GOV-01, B-UPG-01, B-OPS-01. De bestaande besluiten staan nu als Deel B.
- v2.1 (2026-09-25): B-CICD-02 default GitHub in eigen organisatie (ADR-007); GitLab niet ondersteund en geen goedkeuringsstap in Deployment Pipelines, beide vastgesteld via Microsoft Learn. B-MON-01 (melding bij gefaalde run) en B-GOV-01 (Purview standaard uit) bevestigd door Mitchell.
- v2.2 (2026-10-12, generale repetitie GR-B5): B-GOLD-02 aangevuld met de variant van Direct Lake. Default: op het SQL-endpoint (Mitchell); op OneLake pas na een test van de promotie (GR-C2b).
