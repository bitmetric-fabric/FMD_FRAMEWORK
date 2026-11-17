---
title: Een uitvoering beoordelen en een fout herstellen
sidebar_position: 3
---

# Een uitvoering beoordelen en een fout herstellen

Deze handleiding beschrijft wat je doet nadat een uitvoering klaar is of is mislukt: de uitvoering in de Monitor bekijken, de falende tabel vinden, de soort fout bepalen en herstellen. Hoe je een uitvoering met de hand start, staat in [Een tabel of bron handmatig laden](handmatig-laden.md). De vaste controle na elke geplande uitvoering staat in [Dagelijkse routine en planning](dagelijkse-routine.md).

## Wat je eerst moet weten

- **Een geslaagde uitvoering bewijst niet dat alles is geladen.** `PL_FMD_LOAD_ALL` ketent de lagen op `Completed`, niet op `Succeeded`. Bronze draait dus ook als Landingzone faalde, en Silver ook als Bronze faalde. Dat isoleert fouten per tabel: de tabellen die wel zijn aangeleverd, lopen door. Een geslaagde uitvoering kan dus tabellen missen, en een mislukte uitvoering betekent niet dat er niets is geladen.
- **Een mislukte uitvoering is bijna altijd een echte fout.** De fout-activiteiten (`FA_THROW_ERROR_*`) maken de uitvoering pas mislukt nadat de fout in de logging is weggeschreven. Behandel ze als een incident.
- **Een fout per tabel staat in de logging, niet alleen in de portal.** De Monitor toont de keten; de falende tabel en de reden staan in de configuratiedatabase.

## Stap 1: de uitvoering vinden in de Monitor

1. Kies links **Monitor** en daarna **Activities**.
2. Zoek de uitvoering met *Filter by keyword*, bijvoorbeeld op `PL_FMD_SCHEDULE` voor een geplande uitvoering of op `PL_FMD_LOAD_ALL` voor een handmatige. Open de uitvoering met de gewenste starttijd.
3. Rechts staan de details van de uitvoering: eigenaar, starttijd, eindtijd, status en het aantal parameters. Onderaan staat de lijst *Activity runs*, met per activiteit de naam, de status, de starttijd, de duur en de pictogrammen *Input* en *Output*.
4. Bovenin staan de knoppen **Rerun**, **Cancel**, **Refresh** en **Update pipeline**, en een schakelaar tussen **List** en **Gantt**. Tijdens een uitvoering ververst de lijst vanzelf (de portal meldt dat voor 5 minuten).

Een geplande uitvoering start eerst de planningspipeline, die de orchestratie aanroept, die weer `PL_FMD_LOAD_ALL` aanroept. Open bij een aangeroepen pipeline de bijbehorende uitvoering om te zien welke activiteit in die pipeline faalde. De portal toont naar verwachting een link van de aanroep naar de onderliggende uitvoering.

## Stap 2: lees de keten

`PL_FMD_LOAD_ALL` bestaat uit de volgende onderdelen:

| Activiteit | Wat hij doet |
|---|---|
| `SP_START_AUDIT_PIPELINE` | Schrijft de start van de uitvoering in de logging. |
| `PL_FMD_LOAD_LANDINGZONE`, `_BRONZE`, `_SILVER` | Laden de drie lagen. Elke laag start ook als de vorige faalde. |
| `SP_FAIL_*_AUDIT_PIPELINE` | Schrijft een fout van een laag in de logging. |
| `FA_THROW_ERROR_LDZ`, `_BRZ`, `_SLV` | Maken de uitvoering pas mislukt nadat de fout is gelogd. |
| `SP_END_AUDIT_PIPELINE` | Schrijft het einde van een geslaagde uitvoering in de logging. |

De foutcodes van de drie fout-activiteiten zijn `LandingzoneFailed`, `BronzeFailed` en `SilverFailed`. Daarmee weet je in welke laag het misging. De meldingstekst zegt het zelf: *"The Bronze layer failed. The failure is already recorded in logging.PipelineExecution; query it for the failing entity."*

Faalt een kopieer- of commandopipeline (`PL_FMD_LDZ_COMMAND_*`, `PL_FMD_LDZ_COPY_FROM_*`), dan staat de reden van de onderliggende fout in de Fail-melding van die pipeline.

## Stap 3: de falende tabel vinden

Faalt de landingzone, dan staat in `PipelineExecution` alleen de keten, zonder tabel. De tabel en de echte fout staan in `CopyActivityExecution` (`LogType = 'FailedCopyActivity'`). Faalt Bronze of Silver, dan staat de fout per tabel in `NotebookExecution` met `"Action": "Error"` in `LogData`.

Draai de query onder *Controleren* in [Een tabel of bron handmatig laden](handmatig-laden.md#controleren). Die toont de falende tabellen van de laatste dag uit beide logtabellen. Filter je alleen op `Fail*`, dan mis je notebookfouten per tabel.

Een onderliggende pipeline die faalt vóór zijn eigen logging (bijvoorbeeld een login-time-out naar de configuratiedatabase) staat nooit in `NotebookExecution`. Gebruik dan deze query:

```sql
SELECT [LogDateTime], [PipelineName], LEFT([LogData], 1000) AS [LogData]
FROM   [logging].[PipelineExecution]
WHERE  [LogDateTime] >= DATEADD(DAY, -1, SYSUTCDATETIME())
  AND  [LogType] IN ('FailPipeline', 'FailedPipeline')
ORDER BY [LogDateTime] DESC;
```

De reden van zo'n onderliggende pipeline staat in `LogData` achter `Failed notebooks: [...]`.

## Stap 4: bepaal de soort fout

| Wat je ziet | Soort | Wie lost het op |
|---|---|---|
| `PK: <kolom> doesn't exist in the source.` | Registratie of bron: een sleutelkolom bestaat niet in de bron. | Beheerteam: corrigeer de `PrimaryKeys` in de registratie, of de bron. |
| `Source file contains duplicated rows for PK: …` | Datakwaliteit: de bron levert dezelfde sleutel twee keer. | Eigenaar van de brondata. Eerst bepalen of de rijen echt dubbel zijn: breid anders de sleutel uit. |
| Een time-out | Volume tegenover een vaste time-out, geen inhoudelijke fout. | Beheerteam: laad de bron apart (zie *Time-outs* in [Een tabel of bron handmatig laden](handmatig-laden.md#time-outs)). |
| `UserErrorWithLargeConcurrentRuns` op een kopieeractiviteit | Throttling op de gedeelde integration runtime van de regio. De Copy-activiteiten proberen het automatisch opnieuw. | Beheerteam: start de tabel opnieuw als het automatisch opnieuw proberen het niet oploste. |
| `Login timeout expired` bij veel parallelle notebooks | Te veel gelijktijdige verbindingen met de configuratiedatabase. | Beheerteam: draai laadacties van verschillende omgevingen niet tegelijk. |
| Een uitvoering of notebook staat lang op `Queued` of `NotStarted` | Drukte op de capaciteit, geen storing. | Wacht. Duurt het langer dan 20 tot 25 minuten, overleg dan. |
| Bronze logt `SourceFileName: FILE NOT FOUND` en de uitvoering is geslaagd | Een uitvoering zonder wijzigingen bij een bron die parquet-bestanden schrijft. Dit is normaal. | Niets. |

## Stap 5: herstellen

**Opnieuw starten mag altijd.** Start `PL_FMD_LOAD_ALL` (of één laag) opnieuw met dezelfde parameters. Bestanden in de landingzone die nog niet zijn verwerkt (`IsProcessed = 0`) worden in de volgende Bronze-uitvoering opgepakt, en een bestand wordt niet dubbel geregistreerd.

**Een bestand dat in Bronze faalt, blijft hangen.** Het wordt elke uitvoering één keer opnieuw geprobeerd en houdt de latere bestanden van dezelfde tabel tegen: die worden niet gestart maar tellen wel als gefaald (`Failed notebooks: ['<Tabel>_0_0', '<Tabel>_0_1']`). Opnieuw proberen in de notebooks staat bewust uit, omdat een nieuwe poging een eerste fout zou verbergen.

**Herstel via de configuratie.** Is de oorzaak een registratiefout (bijvoorbeeld verkeerde `PrimaryKeys`), corrigeer die dan met `NB_REGISTRATIE` en start opnieuw. De wachtende bestanden worden dan op volgorde verwerkt.

**Een bestand bewust overslaan.** Corrigeer eerst de bron en lever opnieuw aan, of markeer de wachtrij bewust als verwerkt met de actie *Open wachtrij op verwerkt zetten* op tab 5 van de registratie-editor (zie [Registratie overzetten en beheren](overzetten-en-beheren.md)). De actie markeert alle open regels van de tabel als verwerkt, in de gekozen laag, en niet één bestand. Je vult een reden in en de actie begint met een proefdraai. Leg het overslaan vast: de data uit die bestanden komt dan niet in Bronze.

**Een tabel volledig opnieuw laden.** Kies de actie *Watermark resetten* op tab 5 (zie [Een watermark resetten](overzetten-en-beheren.md#een-watermark-resetten)). De registratie en de rij met het watermark blijven bestaan; alleen de opgeslagen waarde wordt leeg. Start daarna de tabel met de hand (zie [Een tabel of bron handmatig laden](handmatig-laden.md)) of wacht op het volgende schedule. Bij een incrementele tabel verwijdert een volledige herlading na een watermark-reset naar verwachting geen rijen die in de bron zijn verwijderd; die blijven in Bronze staan. Een tabel die je op volledig laden zet, werkt anders: een volledige load markeert rijen die in de bron ontbreken wel als verwijderd, zie [Een bestaande tabel wijzigen](tabel-wijzigen.md).

**Silver opnieuw laten verwerken.** Een gewijzigde cleansing-regel voor Silver werkt alleen op rijen die daarna veranderen. Zet de tabel terug in de wachtrij met de actie *Silver opnieuw laten verwerken* op tab 5 van de registratie-editor (zie [Registratie overzetten en beheren](overzetten-en-beheren.md#silver-opnieuw-laten-verwerken)). Verandert de regel het type of de kolommen van de Silver-tabel, verwijder dan eerst de Silver-tabel uit de Silver-lakehouse.

**Een tabel uitzetten.** Is een tabel niet meer nodig of kapot in de bron, zet haar dan uit via de registratie in plaats van elke nacht te laten falen. Markeer de open bestanden als verwerkt, zoals hierboven.

## Na het herstel

1. Start de tabel opnieuw en volg de uitvoering (zie stap 1).
2. Draai de query uit stap 3 en controleer dat er geen nieuwe fout voor de tabel staat.
3. Controleer in `logging.vw_ExecutionSummary` dat de tabel in alle drie de lagen is geladen en dat het aantal rijen klopt (zie [Een tabel of bron handmatig laden](handmatig-laden.md#controleren)).
4. Noteer de oorzaak en de oplossing, zeker bij een overgeslagen bestand of een rechtstreekse wijziging in de configuratiedatabase.
