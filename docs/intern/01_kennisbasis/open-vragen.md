# Open vragen — fase 1

Dit bestand verzamelt alle punten die tijdens fase 1 (kennisbasis) als `open vraag` zijn gelabeld. **Bijgewerkt (repo-audit 2026-09-22):** alle 13 vragen zijn inmiddels aan Mitchell voorgelegd en beantwoord — zie `02_beslisdocument/02_beslisregister.md` (v1.2) voor de letterlijke antwoorden en de daaruit voortvloeiende besluiten. Dit bestand blijft staan als Fase-1-uitgangspunt (waarom iets openstond, en het oorspronkelijke voorstel), met per vraag een verwijzing naar waar hij is afgehandeld.

## Architectuur

**OV-01 — Workspace-naamgevingsconventie: welke van de twee is de daadwerkelijke Bitmetric-standaard?**
De live tenant en de setup-notebooks gebruiken `[DOMEIN] [LAAG] ([OMG])` (bv. `FINANCE DATA (D)`), maar het concept-beslisdocument noemt als Bitmetric-*default* juist `{DOMEIN}_{TYPE}_{OMGEVING}` (bv. `FINANCE_DATA_D`). Deze twee zijn met elkaar in tegenspraak.
**Bron:** `architectuur.md`. **Voorstel:** in fase 2 als expliciete beslissing (`B-ARCH-xx`) opnemen; totdat Mitchell aangeeft welke de bedoelde standaard is, wordt in de documentatie de live/geteste variant (`[DOMEIN] [LAAG] ([OMG])`) als uitgangspunt gebruikt, met een aantekening dat het conceptdocument een alternatief noemt.
**Status (bijgewerkt 2026-09-23): beantwoord én de code-discrepantie is inmiddels opgelost.** Zie `02_beslisregister.md` B-ARCH-01 — Mitchell bevestigt `[DOMEIN] [LAAG] ([OMG])`, met geen OMG-suffix in Productie. **Aandachtspunt uit de repo-audit (2026-09-22), inmiddels verholpen:** de setup-notebooks in de fork implementeerden deze uitzondering aanvankelijk niet — ze voegden ook in Productie een `(P)`-suffix toe. PR #5, "Production-workspaces krijgen geen omgevingsmarker in de naam" (commit `f669a74`, gemerged 2026-09-22 11:40), heeft dit gerepareerd: een nieuwe `ws_suffix()`-helper in de manifest-bootstrap-cel van beide setup-notebooks (`NB_SETUP_FMD.ipynb`, `NB_SETUP_BUSINESS_DOMAINS.ipynb`) geeft nu `""` terug voor Production (short `P`) in plaats van `" (P)"`, en alle plekken die workspacenamen opbouwen (INTEGRATION en business-domains: CODE/DATA/REPORTING/SEMANTIC, deployment pipelines, orchestratie-wiring) gebruiken voortaan deze ene functie. Geen open actiepunt meer.

**OV-02 — F2/AdventureWorks-referentie-implementatie: bestaat het bewijs, en waar?**
De claim "referentie-implementatie op F2-capacity met AdventureWorks, LZ→Bronze→Silver gevalideerd met full en incremental loads" kon niet worden geverifieerd in de onderzochte architectuur-/CI-CD-bronnen.
**Bron:** `architectuur.md`. **Voorstel:** navragen bij Mitchell of dit in specifieke trial-capacity-testing-transcripten staat die nog niet zijn onderzocht, of dat de claim bijgesteld moet worden.
**Status (bijgewerkt 2026-09-22): beantwoord.** Zie `02_beslisregister.md` B-ARCH-04 — Mitchell bevestigt dat de referentie-implementatie bestaat, op zowel de Bitmetric- als de trial-capacity. (Buiten de open-source template-repo, dus niet los te verifiëren.) **Update (2026-09-25):** Mitchell bevestigt dat de referentie-implementatie op **AdventureWorks** draait. Het zijn dus twee verschillende dingen: de referentie-implementatie (AdventureWorks, op de Bitmetric- en de trial-capaciteit, buiten de repo) en de demo in de fork (`NB_MLV_DEMO_GOLD`, WWI). De discrepantie is daarmee opgelost. **Let op:** de trial-capaciteit wordt leeggehaald voor de hertest; de kopie op de trial verdwijnt dan. De workspace-locatie op de Bitmetric-capaciteit is nog niet vastgelegd.

**OV-03 — ADR-009 (GUID-guard): ontbrekend bestand**
`docs/adr/README.md` vermeldt ADR-009 als "Accepted" in de indextabel, maar `docs/adr/009-guid-guard.md` bestaat niet. De implementatie zelf (guid_guard.py, workflow, allowlist) is wel gemerged.
**Bron:** `architectuur.md`, ook al gevonden in fase 0. **Voorstel:** navragen of dit bestand alsnog geschreven moet worden (aanbevolen, want de ADR-conventie schrijft dit voor), of dat de indexvermelding een fout is die gecorrigeerd moet worden.
**Status (bijgewerkt 2026-09-22, later op dezelfde dag): opgelost.** `docs/adr/009-guid-guard.md` staat inmiddels op de conventionele plek in de fork (commit `703017b`, "Add ADR-009 (#6)"), status "Accepted", en is correct opgenomen in de indextabel van `docs/adr/README.md`. Geen actie meer nodig.

**OV-04 — "We passen frameworkcode niet aan"-principe: geldt dit anders voor de fork dan voor een klantimplementatie?**
De fork wijzigt zelf bestaande frameworkcode (18 pipelines, configdb, Sparkcompute.yml, setup-notebooks), wat op het eerste gezicht ingaat tegen het principe. De bronnen classificeren dit als categorie A ("generieke verbetering", bedoeld voor upstream-PR), maar dat onderscheid ("de fork/het framework zelf mag wijzigen, een klantimplementatie niet") staat nergens letterlijk zo geformuleerd.
**Bron:** `architectuur.md`. **Voorstel:** in het beslisdocument (fase 2) expliciet vastleggen dat dit principe geldt voor klantimplementaties (repo's van het template), niet voor doorontwikkeling van het Bitmetric-framework zelf — ter bevestiging aan Mitchell voorleggen.
**Status (bijgewerkt 2026-09-22): beantwoord én inmiddels in de repo vastgelegd.** Zie `02_beslisregister.md` B-ARCH-02 — Mitchell: "Voorstel is correct." Sindsdien is dit ook expliciet vastgelegd in `docs/adr/002-geen-updates-naar-bestaande-implementaties.md` en `docs/adr/003-generieke-laag-vrij-van-klantcode.md` in de fork zelf.

## Bronnen en extensies

**OV-05 — GA4-implementatie: bestaat die, en zo ja waar?**
Een custom-notebook-implementatie voor GA4 is niet aangetroffen. *(De oorspronkelijke formulering "in tegenstelling tot de wel bevestigde RDW-implementatie" is op 2026-09-22 ingetrokken — zie de statusregel hieronder.)*
**Bron:** `bronnen-en-extensies.md`. **Voorstel:** navragen of GA4 daadwerkelijk gebouwd is (en zo ja, waar dat brondocument staat) of dat dit een toekomstig/gepland punt was.
**Status (bijgewerkt 2026-09-22): beantwoord.** Zie `02_beslisregister.md` B-EXT-01 — Mitchell: GA4 bestaat alleen als eigen test, niet als gedocumenteerde referentie-implementatie in FMD. **Aanvullend:** de destijds "bevestigde RDW-implementatie" bleek zelf onjuist — Mitchell (2026-09-22): "Er is gewoon een customnotebook beschikbaar. Maar niet specifiek voor RDW." Gecorrigeerd in `bronnen-en-extensies.md`.

**OV-06 — "Twee Dataflow Gen2-patronen": wat werd hiermee precies bedoeld?**
Dataflow Gen2 wordt nergens in FMD gebruikt (bewuste keuze); de vermoedelijke bedoelde discussie (twee routes A/B voor SharePoint/Excel-bronnen) gebruikt geen Dataflow Gen2.
**Bron:** `bronnen-en-extensies.md`. **Voorstel:** aan Mitchell voorleggen of de SharePoint/Excel-route-discussie inderdaad bedoeld werd, zodat dit correct in fase 3 terechtkomt.
**Status (bijgewerkt 2026-09-22): beantwoord.** Zie `02_beslisregister.md` B-EXT-01 — Mitchell bevestigt: dit was alleen een verkenning van SharePoint als bron; FMD doet vooralsnog niets met Dataflow Gen2.

## Security

**OV-07 — RBAC-artefact vs. fork-deploymentdocumentatie: rolvereisten wijken af**
Het nieuw toegevoegde RBAC-overzicht (`fmd-admin-rechten.md`) noemt andere rolvereisten dan de eigen deploymentdocumentatie van de fork, met name rond wie `NB_BOOTSTRAP_FMD` mag draaien en wie Deployment Pipelines mag aanmaken.
**Bron:** `security.md`. Het RBAC-artefact zelf is bovendien nog niet tegen de fork-code geverifieerd. **Voorstel:** in fase 2 (intake-checklist) een aparte rollen-/rechtenmatrix opnemen die deze discrepantie oplost; Mitchell om verduidelijking vragen welke bron leidend is.
**Status (bijgewerkt 2026-09-22): beantwoord.** Zie `02_beslisregister.md` B-SECURITY-01 — Mitchell: "Voorstel akkoord." De rollen-/rechtenmatrix staat in `04_intake-checklist.md`, Deel 5.

**OV-08 — Managed identity: automatische Key Vault-toegang niet volledig bevestigd**
De claim dat een Workspace Identity/Service Principal automatisch Key Vault-toegang krijgt zonder verdere configuratie, is niet expliciet in de bronnen bevestigd (en de eigen praktijk gebruikt sowieso expliciete SP-credentials wegens een versieverschil).
**Bron:** `security.md`. **Voorstel:** in fase 3 de veilige/geteste route (expliciete SP-credentials) als hoofdpad documenteren, de "automatisch"-claim als niet-geverifieerd aanmerken.
**Status (bijgewerkt 2026-09-22): beantwoord, en het "versieverschil" is inmiddels verklaard.** Zie `02_beslisregister.md` B-SECURITY-02 — Mitchell: "Voorstel akkoord" (expliciete SP i.p.v. Managed Identity). De repo-audit van 2026-09-22 bevestigt de onderliggende reden: `FabricSql`-connecties weigeren `WorkspaceIdentity` structureel (zie `geleerde-lessen.md`, punt 3) — dit is dus geen tijdelijk versieverschil, maar een platformbeperking. De specifieke "automatische Key Vault-toegang"-claim zelf wordt in de deploymentdocs nog steeds niet expliciet bevestigd.

## Geleerde lessen (drie oorspronkelijke claims niet exact bevestigd)

**OV-09 — Casing-inconsistenties: is de gevonden bulk-pipeline-casing-bug de bedoelde les, of bestaat er een ander geval?**
**Bron:** `geleerde-lessen.md` / `registratie.md`.
**Status (bijgewerkt 2026-09-22): deels beantwoord, niet afgesloten.** Zie `02_beslisregister.md`, sectie "Operationele bevindingen → Fase 3" — Mitchell: "De casing bug moeten we nog even bespreken." Doorgeschoven naar Fase 3 als technisch aandachtspunt, niet langer een blokkerende vraag aan Mitchell.

**OV-10 — Bulk-pipeline-parameterformaat: welk script/incident werd precies bedoeld?**
Er is wel een positional-parameter-bug gevonden, maar in een ander bulk-script dan `PL_TOOLING_POST_ASQL_TO_FMD`, buiten de oorspronkelijk toegewezen bronnen.
**Bron:** `geleerde-lessen.md`.
**Status (bijgewerkt 2026-09-22): voorgelegd, antwoord onbekend.** Zie `02_beslisregister.md` — Mitchell: "Deze weet ik niet." Dit is dus niet langer een vraag áán Mitchell, maar blijft feitelijk onopgehelderd; doorgeschoven als best-practice-aandachtspunt naar het implementatieplan (Fase 4).

**OV-11 — Notebook/branch-versiemismatch: welk exact incident werd bedoeld?**
Het gevonden geval (`NB_SETUP_BUSINESS_DOMAINS.ipynb` lokaal vs. main) en het dacpac/CI-build-verschil zijn beide kandidaten, maar geen van beide is expliciet als "de" bedoelde les bevestigd.
**Bron:** `geleerde-lessen.md`.
**Status (bijgewerkt 2026-09-22): voorgelegd, antwoord onbekend — beide kandidaten inmiddels wel zelf opgehelderd.** Zie `02_beslisregister.md` — Mitchell: "Weet ik ook niet" (welke van de twee de bedoelde les was). De repo-audit van 2026-09-22 heeft beide kandidaat-incidenten zelf inmiddels volledig verklaard/opgelost (zie `geleerde-lessen.md`, punt 3) — alleen de vraag "welke van de twee werd oorspronkelijk bedoeld" blijft onbeantwoord, en is nu vooral historisch relevant.

**Voorstel voor OV-09/10/11:** *(historisch — inmiddels uitgevoerd, zie statusregels hierboven)* deze drie samen met Mitchell doornemen.

## Registratie/configdb — losse operationele bevindingen

**OV-12 — Deactiveringsprocedure niet aangetroffen**
Er is geen expliciete, gedocumenteerde procedure gevonden voor het deactiveren van een bron/entiteit (bijv. het omgekeerde pad van registratie via `sp_UpsertConnection`/`sp_UpsertDataSource`/`sp_UpsertLandingzoneBronzeSilver` — wel `IsActive`-kolommen aanwezig in het schema, maar geen expliciet gedocumenteerd deactiveringspad of -procedure).
**Bron:** `registratie.md`. **Voorstel:** navragen of dit proces elders staat vastgelegd, of dat dit een gat is dat in fase 3/4 alsnog moet worden dichtgetimmerd (bijv. "zet `IsActive=0`" als minimale procedure).
**Status (bijgewerkt 2026-09-22): beantwoord.** Zie `02_beslisregister.md` B-INFRA-02 — Mitchell: "Voorstel akkoord" (`IsActive = 0` in de relevante `integration.*`-tabellen). De repo-audit van 2026-09-22 bevestigt dat er nog steeds geen `sp_Deactivate*`-procedure o.i.d. in de configdb-code bestaat — dit blijft dus een puur documentair/procedureel besluit, niet (nog) in code ondersteund. **Update 2026-09-25:** de procedure zoals oorspronkelijk voorgesteld (Connection/DataSource op 0) werkt niet; herschreven in B-INFRA-02 en op 2026-09-25 herbevestigd door Mitchell. De fork-fix (herregistratie laat `IsActive` van bestaande entiteiten staan) is gemerged als PR #8, commit `4dd41cf`. Zie `02_beslisregister.md` B-INFRA-02 en `03_technische_documentatie/05_INTEGRATION/02_configdb-registratie.md` §Deactivering.

**OV-13 — `PL_FMD_LDZ_COMMAND_FTP`: vermoeden van verkeerd doelwit-bug**
Tijdens het onderzoek naar de registratieketen is een vermoeden ontstaan dat `PL_FMD_LDZ_COMMAND_FTP` mogelijk naar een verkeerd doel(pad) verwijst in bepaalde configuraties — dit kon niet volledig worden bevestigd of weerlegd binnen de scope van dit onderzoek.
**Bron:** `registratie.md`. **Voorstel:** als aandachtspunt markeren voor gerichte verificatie (bijv. handmatige test) vóór dit in de technische documentatie als vastgesteld gedrag wordt opgenomen; niet als vastgestelde bug presenteren totdat bevestigd.
**Status (bijgewerkt 2026-09-22): beantwoord.** Zie `02_beslisregister.md`, sectie "Operationele bevindingen → Fase 3" — Mitchell: "Voorstel akkoord" (als aandachtspunt markeren, niet als bevestigde bug). De repo-audit van 2026-09-22 vond geen FTP-doelwit-gerelateerde commits (alleen commits die FTP/SFTP-deployment toevoegen) — het vermoeden is dus nog steeds niet bevestigd of weerlegd.

## Samenvatting voor Mitchell

*(Bijgewerkt 2026-09-22 — deze samenvatting beschreef eerder 13 nog te stellen vragen; die situatie is achterhaald.)*

Alle 13 oorspronkelijke open vragen zijn inmiddels aan Mitchell voorgelegd en beantwoord — de letterlijke antwoorden staan in `02_beslisregister.md` (v1.2), en zijn hierboven per vraag samengevat met een verwijzing. Eén categorie verdient nog vervolgactie, en is geen "open vraag" in de oorspronkelijke zin:

1. **Mitchell weet het antwoord zelf niet (OV-10, OV-11):** deze zijn niet alsnog op te lossen door verder te vragen; ze zijn doorgeschoven als technische aandachtspunten naar Fase 3/4, waar ze bij gelegenheid (bijv. tijdens implementatie) alsnog opgehelderd kunnen worden.
2. **Was actie, inmiddels afgerond (OV-01, OV-03, OV-09, OV-13):** het repo-audit-aandachtspunt bij OV-01 (de Productie-workspacenaamgeving werd door de setup-notebooks nog niet zo geïmplementeerd) is opgelost via PR #5 (commit `f669a74`, 2026-09-22); ADR-009 staat op de juiste plek (bevestigd 2026-09-22); de casing-bug bleek bij empirisch testen geen bug (zie `registratie.md`); de FTP-doelwit-bug bleek een vals alarm (zie `registratie.md`). Geen van de vier is nog een open actiepunt.
