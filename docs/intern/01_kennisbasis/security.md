# Security en toegangsbeheer

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

## Secrets-toegang vanuit notebooks

- **Punt:** Notebooks halen secrets op via het patroon `notebookutils.credentials.getSecret(<key-vault-url>, <secret-naam>)`. Dit is het generieke mechanisme dat het framework gebruikt om te voorkomen dat secrets in code of configuratie terechtkomen.
  **Bron:** onderzoek naar credential-gebruik in de fork-notebooks. **Status:** vastgesteld.
- **Punt (claim: "managed identity voor automatische Key Vault-toegang"):** slechts **gedeeltelijk bevestigd**. De bronnen bevestigen dat authenticatie richting Key Vault via óf een Workspace Identity óf een Service Principal loopt, maar een expliciete, ondubbelzinnige bevestiging dat dit *automatisch* werkt zonder verdere configuratie is niet aangetroffen.
  **Status:** open vraag (deels). Behandel de exacte automatische-toegang-claim als aanname totdat expliciet bevestigd.
- **Punt (praktijksituatie bij Bitmetric zelf):** de eigen Bitmetric-omgeving gebruikt in de praktijk **expliciete Service Principal-credentials opgeslagen in Key Vault**, niet (alleen) Workspace Identity — dit bleek samen te hangen met een versieverschil tussen het lokale `NB_SETUP_BUSINESS_DOMAINS.ipynb` en de live main-branch-versie op het moment van onderzoek.
  **Bron:** onderzoek naar de eigen Bitmetric-tenant-configuratie en het geconstateerde versieverschil. **Status:** getest in eigen omgeving (dit is hoe het bij Bitmetric feitelijk werkt, niet per se de bedoelde/toekomstige architectuur).

## RBAC-rollenoverzicht (nieuw toegevoegde bron, fase 0)

- **Punt:** Het bijlage-document `fmd-admin-rechten.md` (toegevoegd in fase 0, zie `bronnen/00_bronnenoverzicht.md` sectie 4) geeft een overzicht van benodigde rollen op vier niveaus: Fabric Tenant-niveau, Azure-niveau, Fabric Workspace-rollen per workspace(-type), en SQL-configuratiedatabase-rechten, plus een vergelijking Key Vault RBAC vs. (klassieke) Access Policies en een minimaal-rechten-principe.
  **Bron:** `bronnen/chats-ruw/2026-05-05_bitmetric-fabric-project_bijlage-fmd-admin-rechten.md`. **Status:** aanname/input — expliciet in de herkomst-header van dat bestand gemarkeerd als **niet geverifieerd tegen de fork-code**; te behandelen als input voor de intake-checklist (fase 2) en de securiteitsdocumentatie (fase 3), niet als vastgestelde waarheid.
- **Punt:** Er is een discrepantie geconstateerd tussen de rolvereisten in dit RBAC-artefact en wat de eigen deploymentdocumentatie van de fork (`FMD_FRAMEWORK_DEPLOYMENT.md`, `FMD_BUSINESS_DOMAIN_DEPLOYMENT.md`) vermeldt over benodigde rechten tijdens setup.
  **Status:** open vraag. Vier concrete open vragen zijn hieruit voortgekomen (zie `open-vragen.md`) — met name rond welke rol exact nodig is voor het uitvoeren van `NB_BOOTSTRAP_FMD` en voor het aanmaken van Deployment Pipelines.

## Overig

- **Punt:** Het refresh-token van een OAuth-connectie verloopt na 90 dagen **inactiviteit** ("90-day inactivity timeout"), met foutcode `AADSTS700082`. Geen bug, maar onderhoud voor connecties die zelden draaien.
  **Bron:** alleen de samenvatting in de claude.ai-conversaties-export. **Status:** tweedehands. *(Correctie 2026-09-25, review 2 steekproef 4: "inactiviteit" ontbrak, en "terugkerend" en "SaaS-bronnen" waren eigen invulling.)*
- **Punt:** Voor het overkoepelende thema "welke rol/rechten heeft de service principal / managed identity nodig om de configuratiedatabase te benaderen" verwijst dit bestand door naar het RBAC-artefact hierboven — een volledige, geverifieerde matrix ontbreekt nog en is een open punt voor de intake-checklist.
  **Status:** open vraag.
