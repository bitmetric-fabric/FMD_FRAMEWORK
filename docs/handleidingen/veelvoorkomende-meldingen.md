---
title: Veelvoorkomende meldingen
sidebar_position: 6
---

# Veelvoorkomende meldingen

Een naslag om een melding op te zoeken: wat hij betekent, waar de oorzaak meestal zit en wat je doet. Zoek op de tekst van de melding. Hoe je een run beoordeelt en herstelt, staat in [Een run beoordelen en een fout herstellen](run-beoordelen.md).

## Een run of laag faalt

| Melding of verschijnsel | Betekenis en oplossing |
|---|---|
| *The Landingzone / Bronze / Silver layer failed. The failure is already recorded in logging.PipelineExecution…* | Een echte fout in die laag. De melding is een vaste tekst; de falende tabel en de reden staan in de logging. Zie [stap 3 van Een run beoordelen](run-beoordelen.md#stap-3-de-falende-tabel-vinden). De andere lagen en tabellen lopen door. |
| Alle drie de lagen falen binnen een à twee minuten, de logtabellen voor kopieer- en notebookacties zijn leeg. In de Monitor staat bij de aanroep van `PL_FMD_LOAD_LANDINGZONE` *InsufficientPrivileges* (HTTP 403) | De identiteit achter de connectie voor het aanroepen van pipelines heeft geen rechten op de CODE-workspace. Vraag een beheerder die identiteit (of een groep waar hij lid van is) **Contributor** te geven via *Manage access* van de workspace. Daarna volstaat een nieuwe run. |
| *PK: … doesn't exist in the source* | Een sleutelkolom bestaat niet in de bron. Corrigeer de primary key in de registratie. |
| *Source file contains duplicated rows for PK* | De bron levert dezelfde sleutel twee keer. Bepaal eerst of de rijen echt dubbel zijn; breid anders de sleutel uit. |
| *UserErrorWithLargeConcurrentRuns* op een kopieeractiviteit | Throttling op de gedeelde integration runtime van de regio. De kopieeractiviteiten proberen het automatisch opnieuw. Laad de gefaalde tabel zo nodig opnieuw met [Een tabel of bron handmatig laden](handmatig-laden.md). |
| *Login timeout expired* | Te veel gelijktijdige verbindingen met de configuratiedatabase. Draai loads van verschillende omgevingen niet tegelijk. |
| Een time-out | Een grote eerste load tegenover een vaste time-out. Laad de bron apart, zie [Time-outs](handmatig-laden.md#time-outs). |
| Een run of notebook blijft lang op *Queued* of *NotStarted* | Drukte op de capaciteit, geen storing. Duurt het langer dan 20 tot 25 minuten, overleg dan. |

## De run is groen, maar er is niets (of te weinig) geladen

| Verschijnsel | Betekenis en oplossing |
|---|---|
| Een nieuwe bron is geregistreerd, de run is groen en er landt niets | Het brontype past niet bij het connectietype (de copy-pipelines slaan een ander type stil over), of de tabel of een laag staat uit. Controleer het brontype en de kolom **Actief** in de registratie-editor. |
| Landingzone is geladen, maar Bronze en Silver duren elk maar enkele seconden en doen niets | Een laag-pipeline is los gestart zonder de parameter `Data_WorkspaceGuid` (de DATA-workspace). Start de run opnieuw met die waarde, of start via `PL_FMD_LOAD_ALL`. |
| De run in Test of Productie is groen, maar Test of Productie blijft leeg en Dev wordt geladen | De standaardwaarde van `Data_WorkspaceGuid` in `PL_FMD_LOAD_ALL` is niet leeg en wijst naar Dev, bijvoorbeeld na een promotie. Laat de standaardwaarde leeg en controleer de actieve value set van `VAR_CONFIG_FMD` in de workspace van het doel. |
| Een gefilterde run is groen, maar de tabel is niet geladen | De waarden van `DataSourceName` en `Entities` komen niet overeen met een actieve tabel. Zie [Veelgemaakte fouten](handmatig-laden.md#veelgemaakte-fouten). |
| Een tabel komt in Bronze of Silver niet vooruit | Een eerder mislukt bestand van dezelfde tabel houdt de latere bestanden tegen. Herstel de oorzaak of sla het bestand bewust over, zie [Herstellen](run-beoordelen.md#stap-5-herstellen). |

## Een geplande run

| Verschijnsel | Betekenis en oplossing |
|---|---|
| Een schedule draait niet meer, of een geplande run faalt op een verlopen token (*AADSTS700082*) | Een schedule draait naar verwachting onder het account van wie hem maakte. Is dat account lang niet actief geweest of weg, dan verloopt het token. Maak het schedule opnieuw aan met een account dat blijft, bijvoorbeeld een beheeraccount. Zie [Dagelijkse routine en schedules](dagelijkse-routine.md#een-schedule-wijzigen). |
| Een connectie faalt stil met *AADSTS700082* | Een OAuth-connectie verloopt na 90 dagen zonder gebruik. Autoriseer de connectie opnieuw. |
| Het schedule start de verkeerde run | Een ontbrekende of verkeerd gespelde parameter, zoals `Target`. Controleer de parameters van het schedule. |

## Een promotie

| Melding | Betekenis en oplossing |
|---|---|
| *Missing Dependencies* | Een item verwijst naar een item in een andere workspace dat in het doel nog niet bestaat. Promoveer eerst dat item en daarna het verwijzende item. |
| *CopyOverwriteResult.GenericError* op `LH_GOLD_LAYER` | Een Silver-tabel waar een shortcut naar wijst, bestaat in het doel nog niet. Registreer en laad eerst in het doel en promoveer daarna de DATA-workspace. |
| *TargetArtifactNameConflict* | In het doel staat een item met dezelfde naam dat niet aan het bronitem gekoppeld is. Beslis welk item blijft en koppel of verwijder het andere. |
| Test of Productie leest na de promotie uit Dev | De actieve value set van een Variable Library is niet die van het doel, of een Direct Lake-model heeft geen deployment rule. Zie het volgende deel. |

## Een semantisch model

De meldingen en oplossingen voor Direct Lake-modellen staan in de tabel *Valkuilen* van [Een Direct Lake-model laten verwijzen naar het juiste lakehouse na promotie](direct-lake-parameter.md#valkuilen). De meest voorkomende:

| Melding | Betekenis en oplossing |
|---|---|
| *We cannot access the source Delta table* | Het SQL-endpoint van het lakehouse kent de nieuwe tabellen nog niet. Ververs de metadata van het endpoint en ververs daarna het model. |
| *Query Evaluation failed for query: DirectLake - LH_GOLD_LAYER* bij **Refresh → Schema** | Een tabel mist `sourceLineageTag`. De parameter is niet de oorzaak. |
| Het model in Test leest uit Dev | De parameter rule ontbreekt of is niet toegepast. Controleer de lineage van het model in Test. |

## Registratie

| Melding in `NB_REGISTRATIE` | Betekenis en oplossing |
|---|---|
| *Expected one Fabric connection named … found 0* | De naam klopt niet, of je hebt geen rechten op de connectie. Vraag de eigenaar je toe te voegen. |
| *does not fit the type of connection* | Het FMD-type van de connectie of het brontype is verkeerd gekozen. |
| *PrimaryKeys is empty* of *not found* | De tabel heeft geen primary key in de bron, of de sleutel staat niet in de ontdekking. Kies de sleutel samen met de eigenaar van de bron, en let bij Snowflake op hoofdletters. |
