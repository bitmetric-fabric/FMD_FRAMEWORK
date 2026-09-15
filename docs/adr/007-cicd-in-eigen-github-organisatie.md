# ADR-007: CI/CD gehost in een eigen GitHub-organisatie

Status: Accepted
Datum: 2026-09-15

## Context

Promotie verloopt via fabric-cicd (ADR-006), aangestuurd vanuit een CI-omgeving.
Die omgeving kan bij de klant staan of bij ons. Klanten verschillen sterk in
devops-volwassenheid; niet elke klant heeft een ADO- of GitHub-organisatie, en
waar die er wel is, is toegang voor externen niet vanzelfsprekend.

Tegelijk is de deploy-workflow zelf iets dat we juist wél willen doorontwikkelen
en bij elke klant willen hergebruiken — in tegenstelling tot de framework-code,
waar ADR-002 dat expliciet uitsluit.

## Beslissing

CI/CD wordt standaard gehost in een **eigen GitHub-organisatie van Bitmetric**,
met één repository per klant (ADR-008).

De deploy-workflow staat als herbruikbare workflow in een eigen repo binnen die
organisatie. Klantrepo's verwijzen ernaar met een versietag, zodat een verbetering
aan de workflow alle klanten bereikt zonder dat de klantcode verandert.

**Plan:** starten op GitHub Free. Overstappen naar Team zodra er twee of meer
klanten zijn, of eerder als het secret-beheer onoverzichtelijk wordt.

**Afwijken** is toegestaan als een klant eist dat code in de eigen tenant staat,
of als de klant de omgeving zelf gaat beheren. Leg dat vast in een klant-specifieke
ADR; combineer het zo nodig met de uitwijkoptie uit ADR-006.

## Beperkingen van de gratis laag

- Environments en environment secrets in private repositories vereisen Pro, Team
  of Enterprise. Op Free gebruiken we repo secrets. Met één repo per klant is de
  isolatie in de praktijk gelijkwaardig, alleen minder overzichtelijk.
- Required reviewers en wait timers zijn op Free, Pro én Team alleen beschikbaar
  voor publieke repositories; voor private repo's is Enterprise nodig. Een
  geauditeerde goedkeuringsknop voor Prod is dus geen optie.
- **Vervanging:** de Prod-deploy draait als `workflow_dispatch` met de tag als
  input. Geen approval-registratie, wel een bewuste handeling.
- Actions-minuten zijn geen knelpunt; een fabric-cicd-run duurt minuten.

## Alternatieven

- **CI/CD in de omgeving van de klant.** Verworpen als standaard: hergebruik van
  de workflow over klanten heen vervalt, en we zijn afhankelijk van de
  devops-volwassenheid van de klant. Blijft geldig als klant-specifieke afwijking.
- **Azure DevOps in eigen tenant.** Gelijkwaardig alternatief met een vergelijkbare
  gratis laag en van oudsher directere ondersteuning in Fabric's git-integratie.
  Verworpen op werkcomfort, niet op techniek. Heroverwegen als de GitHub-beperkingen
  gaan knellen.
- **Enterprise-plan meteen.** Verworpen: niet te verantwoorden bij één klant.

## Gevolgen

- We beheren service principals met toegang tot de Fabric-omgeving van de klant,
  en hun credentials staan in onze organisatie. Dat vraagt om:
  1. **Toestemming** in de verwerkersovereenkomst.
  2. **Exit-scenario** als expliciete deliverable: repo én workflows worden
     overgedragen als de klant het overneemt.
  3. **Toegang tot Fabric-git**: wie bij de klant een git-sync doet heeft een
     account in onze organisatie nodig. Collaborators zijn gratis, maar moeten
     beheerd worden — inclusief offboarding.
- Verifieer bij inrichting dat gedeelde workflows tussen private repo's binnen
  de organisatie werken op het gekozen plan; dat is eerder een betaalde functie
  geweest.
