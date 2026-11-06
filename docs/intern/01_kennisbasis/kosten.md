# Kosten en capaciteit

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

## Capaciteitsgebruik (F2)

- **Punt:** Op de eigen F2-capaciteit is een CU-gebruik gemeten van circa 30.047 van 172.800 CU-seconden (één dag), ofwel ca. 17%.
  **Bron:** capaciteitsmetriek-onderzoek in de eigen tenant. **Status:** getest in eigen omgeving.
- **Punt:** De claim dat de F2-capaciteit specifiek is gebruikt om de LZ→Bronze→Silver-keten met AdventureWorks te valideren (full + incremental load) **niet** teruggevonden als zodanig in de onderzochte architectuurbronnen — F2 komt in de onderzochte bronnenset alleen naar voren in de context van Spark-pool-sizing (zie hieronder). Zie `open-vragen.md` OV-02 en `02_beslisregister.md` B-ARCH-04: Mitchell bevestigt dat de referentie-implementatie bestaat en op AdventureWorks draait (2026-09-25). De demo in de fork (`NB_MLV_DEMO_GOLD`) is een andere implementatie, op WWI.

## Spark-pool-sizing — de "Spark pool limits"-les

- **Punt:** Er is een geconstateerd en opgelost sizing-probleem met de standaard Spark-compute-instellingen: in `ENV_FMD.Environment/Setting/Sparkcompute.yml` zijn `driver_cores` van 8 naar 4 en `driver_memory` van 56g naar 28g aangepast, om binnen de pool-limiet van de Dev/Test- of trial-capaciteit (16 cores/112g) te passen. Het ging dus niet om F2; volgens de triage is 4/28g voor F2 nog steeds te groot. *(Correctie 2026-09-25, review 2 steekproef 7; getallen: commit `c2dbe90`.)*
  **Bron:** onderzoek naar `ENV_FMD.Environment/Setting/Sparkcompute.yml` en gerelateerde geschiedenis. **Status:** getest in eigen omgeving.
- **Punt (nuance):** Er is eerder geprobeerd om deze sizing **per omgeving** (Dev/Test/Prod apart) te configureren, maar dat is teruggedraaid — er is één gedeeld `ENV_FMD`-environment-item dat voor alle omgevingen dezelfde Spark-instellingen gebruikt. Dit is een bewuste vereenvoudiging, geen onopgelost issue.
  **Bron:** zelfde onderzoek. **Status:** getest in eigen omgeving.
- **Punt:** De oorspronkelijke claim uit de "geleerde lessen"-lijst ("Spark pool limits") wordt hiermee grotendeels bevestigd, al is de exacte formulering ("limits" i.p.v. concrete sizing-parameters) een generalisatie — de kern (een sizing-aanpassing was nodig en is doorgevoerd) klopt.
  **Status:** vastgesteld (kern van de les), met de sizing-details als vastgesteld en de per-omgeving-poging/terugdraai als aanvullende, niet expliciet gevraagde context.

## Activator-kostenincident

- **Punt:** Er is een "runaway"-kostenincident geweest met een Fabric Activator: deze triggerde de pipeline `PL_FINANCE_LOAD_GOLD` op **elk** workspace-event, in plaats van alleen op de bedoelde trigger-conditie — resulterend in veel te frequente, onbedoelde pipeline-runs en dus onnodig capaciteitsverbruik/kosten.
  **Bron:** een samenvatting uit de zoektool: `bronnen/chats-export/…/conversations.json` en memory `130bbeae…`. Oorzaak en pipelinenaam kloppen; bedragen, CU of duur staan nergens. **Status:** tweedehands. *(Correctie 2026-09-25, review 2 steekproef 1: stond op "getest in eigen omgeving".)*
- **Punt:** Dit incident wordt in de technische documentatie (fase 3) en het implementatieplan (fase 4) opgenomen als een expliciete waarschuwing/checklist-item bij het configureren van Activators: trigger-condities nauwkeurig scopen, niet op "elk event" laten staan.
  **Status:** aanname (redactionele aanbeveling op basis van het geconstateerde incident, geen letterlijk bronvoorschrift).

## Samenvatting "geleerde lessen" met kostenraakvlak

Van de oorspronkelijk aangeleverde lijst "geleerde lessen" heeft dit bestand er twee met een kostendimensie kunnen bevestigen: de Spark-pool-sizing-aanpassing (vastgesteld, met nuance) en het Activator-kostenincident (tweedehands; `Promp.txt` noemt het wel letterlijk in de lessenlijst). Zie `geleerde-lessen.md` voor de volledige set en `open-vragen.md` voor de lessen die niet geverifieerd konden worden.
