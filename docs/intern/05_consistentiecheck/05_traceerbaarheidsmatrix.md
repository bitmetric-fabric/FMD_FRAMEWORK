# Consistentiecheck — Traceerbaarheidsmatrix en bevindingen

> **Historisch document (gemarkeerd 2026-10-05).** Dit is de stand van 2026-09-22. De matrix dekt alleen de 12 besluiten van Deel B van het beslisregister, niet de 16 klantbeslissingen van Deel A (v2.0), en niet ADR-010/ADR-011 of de bevindingen uit de hertest. Hij wordt niet meer bijgewerkt. De actuele stand staat in `02_beslisdocument/02_beslisregister.md`, `testplan-trial.md` en het draaiboek. Een nieuwe consistentiecheck hoort bij review 3.

**Fase:** 5 (Consistentiecheck)
**Datum:** 2026-09-22
**Status:** v1.1 — bevindingen G1, G2, G4, G5, T1, T2, T3 opgevolgd en verwerkt; alleen G3 blijft open (vereist input van Mitchell)
**Doel:** voor elke besluit uit `02_beslisdocument/02_beslisregister.md` vaststellen welk architectuurcomponent het raakt, waar het technisch is gedocumenteerd (Fase 3) en waar het als implementatiestap terugkomt (Fase 4). Daarna: rapporteren welke besluiten geen vervolgstap hebben, welke stappen geen onderbouwing hebben, en welke tegenstrijdigheden tussen documenten bestaan.

**Methode:** elk van de 12 geaccepteerde besluiten (`B-*`) en de 4 operationele bevindingen uit het beslisregister is doorzocht in `03_technische_documentatie/` en `04_implementatieplan/` (inclusief `Bijlage A` van `draaiboek_detail.md`). Waar een verwijzing ontbreekt of tegenstrijdig is, is dat expliciet vermeld — niet stilzwijgend genegeerd.

---

## Traceerbaarheidsmatrix — besluiten (`B-*`)

| Besluit | Architectuurcomponent | Technische documentatie (Fase 3) | Implementatiestap (Fase 4) | Status |
|---|---|---|---|---|
| **B-ARCH-01** — Workspace-naamgeving | Workspace-topologie | `06_BUSINESS_DOMEINEN/01_workspace-structuur.md`, `00_architectuur-overzicht.md` | `plan_hoogover.md` fase 2 · `draaiboek_detail.md` fase 2, stap 2 | ✅ Volledig getraceerd |
| **B-ARCH-02** — Fork vs. klantrepo-wijzigingen | Repository-governance | `09_cicd-en-deployment.md` (categorie A/B/C-sectie toegevoegd) | `draaiboek_detail.md` fase 8, stap 3 (ADR-002-uitzonderingspad) | ✅ Opgelost (was G1) |
| **B-ARCH-03** — ADR-009 GUID-guard | CI/CD-guard | `09_cicd-en-deployment.md` | `draaiboek_detail.md` fase 2, stap 7 + verificatieregel | ✅ Opgelost (was G2) |
| **B-ARCH-04** — Referentie-implementatie | Gold-laag/referentie | `06_BUSINESS_DOMEINEN/02_gold-laag-mlv.md`, `13_referentie-implementatie-bitmetric.md` | `plan_hoogover.md` fase 6 (verwijzing naar `NB_MLV_DEMO_GOLD`) | ⚠️ Open detail — zie bevinding G3 (live tenant-locatie nog niet vastgelegd, al bekend uit Fase 2/3) |
| **B-CICD-01** — Deployment Pipelines als default | Promotiemechanisme | `09_cicd-en-deployment.md`, `02_beslisdocument/03_architectuurvarianten.md` | `plan_hoogover.md` fase 7 · `draaiboek_detail.md` fase 7 | ✅ Volledig getraceerd (best gedocumenteerde besluit) |
| **B-INFRA-01** — Configdb-registratieketen | Configuratiedatabase | `05_INTEGRATION/01_ddl-spec.md`, `02_configdb-registratie.md` | `plan_hoogover.md` fase 3/4/5 · `draaiboek_detail.md` fase 3/4/5 | ✅ Volledig getraceerd |
| **B-GOLD-01** — Shortcuts-workaround | Gold-laag/shortcuts | `06_BUSINESS_DOMEINEN/03_shortcuts-en-deployment.md` | `plan_hoogover.md` fase 6/7 · `draaiboek_detail.md` fase 6, stap 3 en fase 7, stap 4a | ✅ Volledig getraceerd |
| **B-SECURITY-01** — RBAC-matrix | Security/rechten | `08_security-en-secrets.md` (kernvereisten nu rechtstreeks tegen `FMD_FRAMEWORK_DEPLOYMENT.md`/`FMD_BUSINESS_DOMAIN_DEPLOYMENT.md` geverifieerd) | `plan_hoogover.md` fase 2 · `draaiboek_detail.md` fase 2, stap 4 | ✅ Grotendeels opgelost (was G4) — het bredere, aanvullende RBAC-brondocument blijft voor verfijndere vragen nog deels ongeverifieerd, dat is nu expliciet zo benoemd i.p.v. het hele onderwerp als open te laten |
| **B-EXT-01** — Extensiepunten | Bronaansluiting/extensies | `07_extension-points.md` | `plan_hoogover.md` fase 5 · `draaiboek_detail.md` fase 5, stap 2/3 | ✅ Volledig getraceerd |
| **B-SECURITY-02** — Expliciete Service Principal | Security | `08_security-en-secrets.md` | `plan_hoogover.md` fase 2, stap 3 · `draaiboek_detail.md` fase 2, stap 3 | ✅ Volledig getraceerd |
| **B-INFRA-02** — Deactiveringsprocedure | Operations | `05_INTEGRATION/01_ddl-spec.md` (`IsActive`), `10_operations.md`, `11_troubleshooting.md` | `plan_hoogover.md` fase 5 · `draaiboek_detail.md` fase 4/5 (rollback-secties) | ✅ Volledig getraceerd |
| **B-INFRA-03** — Livy/Spark-pool-sizing | Capaciteit | `12_kosten-en-capaciteit.md`, `10_operations.md` | `plan_hoogover.md` fase 2/3 · `draaiboek_detail.md` fase 3 | 🔴 **Tegenstrijdigheid** — zie bevinding T1 |

## Traceerbaarheidsmatrix — operationele bevindingen (geen `B-*`, wel uit het beslisregister)

| Bevinding | Technische documentatie | Implementatiestap | Status |
|---|---|---|---|
| Casing-mismatch `PL_TOOLING_POST_ASQL_TO_FMD` (OV-09) | `05_INTEGRATION/03_operationele-aandachtspunten.md`, `11_troubleshooting.md` | `draaiboek_detail.md` fase 4, stap 1 (pipeline zonder voorbehoud bruikbaar) | ✅ Volledig getraceerd, inclusief correctie (bleek géén bug) |
| Positional-parameter-bug (OV-10) | `05_INTEGRATION/03_operationele-aandachtspunten.md` | `draaiboek_detail.md`, risicoregister R8 + Bijlage A §A.4 (fix verwerkt in sjabloon) | ✅ Volledig getraceerd |
| Notebook-/branch-versiemismatch (OV-11) | `05_INTEGRATION/03_operationele-aandachtspunten.md` | `draaiboek_detail.md` fase 3, stap 5 | ✅ Opgelost (was G5) |
| `PL_FMD_LDZ_COMMAND_FTP`-verdenking (OV-13) | `05_INTEGRATION/03_operationele-aandachtspunten.md` | N.v.t. — vals alarm, geen actie vereist (correct zo gedocumenteerd) | ✅ Consistent, geen actie nodig |

---

## Bevindingen: besluiten zonder (volledige) vervolgstap — status na opvolging (2026-09-22)

**G1 — B-ARCH-02 (fork vs. klantrepo-wijzigingen). ✅ Opgelost.**
`09_cicd-en-deployment.md` heeft nu een eigen sectie "Wat mag worden aangepast: fork versus klantrepo (B-ARCH-02)" met de categorie A/B/C-indeling van fork-wijzigingen en het onderscheid fork vs. klantrepo.

**G2 — B-ARCH-03 (GUID-guard). ✅ Opgelost.**
`draaiboek_detail.md` fase 2 heeft nu een expliciete stap 7 ("Verificatiestap (G2, B-ARCH-03): controleer dat de GUID-guard-CI-check... actief staat") plus een aanvulling in de verificatieregel van die fase.

**G4 — B-SECURITY-01 (RBAC-brondocument gedeeltelijk ongeverifieerd). ✅ Grotendeels opgelost.**
`08_security-en-secrets.md` bevat nu een apart geverifieerd blok (rechtstreeks uit `FMD_FRAMEWORK_DEPLOYMENT.md`/`FMD_BUSINESS_DOMAIN_DEPLOYMENT.md`: Contributor-rol, Workspace Contributor-rol, tenant-instellingen, de Object-ID-valkuil bij Service Principals) dat het minimaal noodzakelijke voor bootstrap en Deployment Pipelines dekt. Het bredere, aanvullende RBAC-brondocument (SQL-configuratiedatabase-rechten, Key Vault RBAC vs. Access Policies in detail) blijft voor die specifieke onderdelen ongeverifieerd — dat is nu expliciet zo afgebakend in plaats van het hele RBAC-onderwerp als open te laten staan.

**G5 — Notebook-/branch-versiemismatch (OV-11). ✅ Opgelost.**
`draaiboek_detail.md` fase 3 heeft nu een expliciete stap 5 ("Verificatiestap (G5, geleerde les): controleer dat het lokaal/handmatig gebruikte setup-notebook overeenkomt met de main-branch-versie... vóórdat het wordt gedraaid").

---

## Bevindingen: tegenstrijdigheden tussen documenten

**T1 — Spark-pool-sizing: het beslisregister spreekt zichzelf tegen met de latere Fase 3/4-documentatie.** 🔴 Belangrijkste bevinding van deze consistentiecheck.

`02_beslisdocument/02_beslisregister.md`, besluit **B-INFRA-03**, stelt letterlijk (status: vastgesteld, geaccordeerd):
> "Spark-pool: min. **2 cores, 4 GB geheugen** per werknoot"

Dit exacte cijfer is echter later, bij het opstellen van `12_kosten-en-capaciteit.md` en de correctie van `02_beslisdocument/04_intake-checklist.md` (v1.4), **exhaustief nagezocht in alle bronnen** (kennisbasis, chat-transcripten, repo-manifest) en **niet teruggevonden** — de enige daadwerkelijk geverifieerde waarde is de repo-default van **4 cores/28GB** (`ENV_FMD.Environment/Setting/Sparkcompute.yml`, verlaagd vanaf 8 cores/56g). `12_kosten-en-capaciteit.md` zegt expliciet: *"een eerder vermoede ondergrens ('2 cores/4GB minimum') is bij exhaustieve verificatie... niet teruggevonden."*

**Conclusie:** het beslisregister (B-INFRA-03) is nooit bijgewerkt na deze correctie — het bevat nog steeds het niet-verifieerbare "2 cores/4GB"-cijfer als geaccordeerd besluit, terwijl twee latere, zorgvuldiger onderzochte documenten (`12_kosten-en-capaciteit.md`, `04_intake-checklist.md` v1.4) dit cijfer expliciet verwerpen.

**Aanbeveling:** `02_beslisregister.md` B-INFRA-03 corrigeren — het "2 cores/4GB"-cijfer verwijderen of expliciet markeren als niet-geverifieerd, en vervangen door een verwijzing naar de wél geverifieerde 4 cores/28GB-default. Dit is de enige bevinding in deze consistentiecheck die op besluitniveau (niet alleen documentatieniveau) gecorrigeerd moet worden.

**T2 — Escalatiedrempel voor capaciteitscontentie: kleine numerieke afwijking.**
`B-INFRA-03` (beslisregister) noemt "bij vertraging (>15-20 min wachttijd)" als escalatiedrempel. De projectinstructies en alle latere Fase 3-documenten (`10_operations.md`, `11_troubleshooting.md`) hanteren consistent ">20-25 minuten". Dit is een kleine, waarschijnlijk onschuldige afronding/aanscherping, maar wel een letterlijke inconsistentie tussen het beslisregister en de rest van de documentatieset.
**Aanbeveling:** lage prioriteit — bij een volgende revisie van B-INFRA-03 gelijktrekken naar ">20-25 minuten" conform de rest van de set.

**T3 — Twee implementatieplan-documenten op verschillend abstractieniveau. ✅ Opgevolgd (kruisverwijzing toegevoegd, geen document verwijderd).**
`implementatieplan-template.md` heeft nu een expliciete paragraaf die de verhouding tot `plan_hoogover.md`/`draaiboek_detail.md` uitlegt en aangeeft dat nieuw gebruik bij die twee moet beginnen. `plan_hoogover.md`'s verwijzingentabel verwijst nu ook terug. Het document zelf is bewust **niet** verwijderd — dat zou een structurele wijziging zijn die eerst met Mitchell afgestemd moet worden; de kruisverwijzing lost de verwarring op zonder dat te hoeven doen.

**Geen andere tegenstrijdigheden gevonden.** De overige negen besluiten (B-ARCH-01, B-ARCH-04, B-CICD-01, B-INFRA-01, B-GOLD-01, B-SECURITY-01, B-EXT-01, B-SECURITY-02, B-INFRA-02) zijn inhoudelijk consistent doorgevoerd van beslisregister → technische documentatie → implementatieplan, zonder gevonden tegenspraak.

---

## Nog openstaand — vereist input van Mitchell (kan niet zelfstandig worden opgelost)

- **G3 — B-ARCH-04:** de live locatie/toegang tot de referentie-implementatie op de Bitmetric- en trial-capacity is nog niet vastgelegd. Dit stond al zo in het beslisregister zelf vermeld (v1.5). Dit is het **enige punt uit deze consistentiecheck dat niet zelfstandig op te lossen is** — het vereist dat Mitchell de daadwerkelijke workspace-namen/links op de Bitmetric- en trial-capacity aanlevert; dat is niet af te leiden uit de gekloonde fork-repo.
- **On hold (bewust, buiten scope van deze consistentiecheck, ongewijzigd):** de twee cosmetische codeopschoningen (`PL_TOOLING_POST_ASQL_TO_FMD`-Expression-wrapper, `PL_FMD_LDZ_COMMAND_FTP`-activity-label) blijven op verzoek van Mitchell liggen.

---

## Samenvatting (bijgewerkt na opvolging, 2026-09-22)

| Categorie | Aantal |
|---|---|
| Besluiten volledig getraceerd, geen bevinding | 9 van 12 |
| Besluiten met traceerbaarheidslacune, **inmiddels opgelost** (G1, G2, G4, G5) | 4 |
| Besluit met traceerbaarheidslacune die **input van Mitchell vereist** (G3) | 1 (B-ARCH-04) |
| Tegenstrijdigheden gevonden, **direct gecorrigeerd** (T1, T2) | 2 (`02_beslisregister.md` → v1.6) |
| Structuurrisico, **opgevolgd met kruisverwijzing** (T3) | 1 |

**Status na deze opvolgingsronde:** alle bevindingen uit de eerste consistentiecheck zijn afgehandeld, op één na. **G3 (B-ARCH-04, live referentie-implementatie-locatie) blijft openstaan totdat Mitchell de workspace-namen/links op de Bitmetric- en trial-capacity aanlevert.**
