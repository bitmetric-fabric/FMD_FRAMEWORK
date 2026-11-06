# Kosten en capaciteit

**Fase:** 3 (Technische documentatie)
**Datum:** 2026-09-25
**Status:** Eerste versie, bijgewerkt op 2026-09-25 (eenheid en periode van de CU-meting)
**Bron:** `output/01_kennisbasis/kosten.md`, `04_intake-checklist.md` (Spark-pool-sizing-correctie)

## Spark-pool-sizing

De repo-default in `ENV_FMD.Environment/Setting/Sparkcompute.yml` is `driver_cores: 4, driver_memory: 28g, executor_cores: 4, executor_memory: 28g`. Dit is een **verlaging** vanaf `8 cores / 56g`, doorgevoerd om binnen een kleinere capaciteit (zoals F2) te passen.

**Status:** getest in eigen omgeving.

**Belangrijk — geen apart, lager minimum:** een eerder vermoede ondergrens ("2 cores/4GB minimum") is bij exhaustieve verificatie tegen alle onderzochte bronnen (kennisbasis, chat-transcripten, repo-manifest) **niet teruggevonden**. Ga uit van de geverifieerde default (4 cores/28GB) als uitgangspunt, en pas dit alleen aan als de klantcapaciteit dit vereist/toestaat — niet op basis van een niet-bevestigd lager cijfer.

**Nuance — één gedeeld environment-item:** er is eerder geprobeerd om de sizing per omgeving (Dev/Test/Prod apart) te configureren, maar dat is bewust teruggedraaid. Er is één gedeeld `ENV_FMD`-environment-item dat voor alle omgevingen dezelfde Spark-instellingen gebruikt — een bewuste vereenvoudiging, geen onopgelost issue.

**Status:** getest in eigen omgeving.

## Capaciteitsgebruik (referentiepunt)

Op de eigen F2-referentiecapaciteit is een CU-gebruik gemeten van circa 17%: 30.047 van 172.800 **CU-seconden**, over **één dag** (F2 = 2 CU × 86.400 s). Bron: een screenshot van de Capacity Metrics-app, `bronnen/chats-ruw/2026-09-04_f2-capacity-cu-usage-interpretation.md`. Dit is een **indicatief referentiepunt**, geen garantie voor een andere klantomgeving — het feitelijke verbruik hangt af van datavolumes, laadfrequentie en het aantal actieve business-domeinen.

**Status:** getest in eigen omgeving (referentiepunt); niet generaliseerbaar zonder nadere validatie per klant.

## Capaciteitscontentie als kostenfactor

Zoals beschreven in `10_operations.md`/`11_troubleshooting.md`: notebook-jobs en Livy-sessies kunnen 15–30+ minuten wachten bij drukte op gedeelde capaciteit. Dit is primair een operationeel aandachtspunt, maar heeft ook een capaciteitsplanningsdimensie: bij structurele contentie is een grotere capaciteits-SKU (of een dedicated capaciteit) te overwegen, in plaats van uitsluitend te wachten.

**Status:** vastgesteld (het verschijnsel); de afweging "wanneer opschalen" is niet in de bronnen uitgewerkt — **aanname/aanbeveling**, per klant te beoordelen.

## Waarschuwing: Activator-kostenrisico

Een bekend geconstateerd incident: een Fabric Activator triggerde een Gold-laadpipeline op **elk** workspace-event in plaats van alleen de bedoelde trigger-conditie, met onnodig frequente pipeline-runs en dus onnodig capaciteitsverbruik tot gevolg.

**Actiepunt voor elke klantimplementatie die Activators gebruikt:** scope trigger-condities nauwkeurig — nooit op "elk event" laten staan zonder expliciete verificatie van de bedoelde trigger-conditie. Neem dit op als checklist-item bij het configureren van een Activator.

**Status:** getest in eigen omgeving (het incident); de aanbeveling zelf is een redactionele conclusie op basis van het incident, geen letterlijk bronvoorschrift.

## Samenvatting — kostenfactoren om vroeg te bespreken bij intake

| Factor | Aandachtspunt |
|---|---|
| Spark-pool-sizing | Start met de geverifieerde default (4 cores/28GB); pas aan op basis van daadwerkelijke capaciteit, niet op een niet-bevestigd minimum |
| Capaciteits-SKU | F2 is het geverifieerde referentiepunt bij Bitmetric zelf — niet automatisch geschikt voor elke klantomgeving |
| Structurele capaciteitscontentie | Kan een signaal zijn om capaciteit op te schalen, niet alleen een operationeel ongemak |
| Activator-triggers | Scope nauwkeurig, anders reëel risico op onnodig capaciteitsverbruik |
