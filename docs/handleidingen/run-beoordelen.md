---
title: Een run beoordelen en een fout herstellen
sidebar_position: 3
---

# Een run beoordelen en een fout herstellen

Deze handleiding beschrijft wat je doet nadat een run klaar is of is mislukt: de run in de Monitor bekijken, de falende tabel vinden, de soort fout bepalen en herstellen. Hoe je een run met de hand start, staat in [Een tabel of bron handmatig laden](handmatig-laden.md). De vaste controle na elke geplande run staat in [Dagelijkse routine en schedules](dagelijkse-routine.md).

Waar de handleiding een scherm van de portal beschrijft dat nog niet is vastgelegd, staat dat erbij.

## Wat je eerst moet weten

- **Een groene run bewijst niet dat alles is geladen.** `PL_FMD_LOAD_ALL` ketent de lagen op `Completed`, niet op `Succeeded`. Bronze draait dus ook als Landingzone faalde, en Silver ook als Bronze faalde. Dat isoleert fouten per tabel: de tabellen die wel zijn geland, lopen door. Een groene run kan dus tabellen missen, en een rode run betekent niet dat er niets is geladen.
- **Een rode run is bijna altijd een echte fout.** De fout-activiteiten (`FA_THROW_ERROR_*`) maken de run pas rood nadat de fout in de logging is weggeschreven. Behandel ze als een incident.
- **Een fout per tabel staat in de logging, niet alleen in de portal.** De Monitor toont de keten; de falende tabel en de reden staan in de configuratiedatabase.

## Stap 1: de run vinden in de Monitor

1. Kies links **Monitor** en daarna **Activities**.
2. Zoek de run met *Filter by keyword*, bijvoorbeeld op `PL_FMD_SCHEDULE` voor een geplande run of op `PL_FMD_LOAD_ALL` voor een handmatige. Open de run met de gewenste starttijd.
3. Rechts staan de details van de run: eigenaar, starttijd, eindtijd, status en het aantal parameters. Onderaan staat de lijst *Activity runs*, met per activiteit de naam, de status, de starttijd, de duur en de pictogrammen *Input* en *Output*.
4. Bovenin staan de knoppen **Rerun**, **Cancel**, **Refresh** en **Update pipeline**, en een schakelaar tussen **List** en **Gantt**. Tijdens een run ververst de lijst vanzelf (de portal meldt dat voor 5 minuten).

Een geplande run start eerst de schedule-pipeline, die de orchestratie aanroept, die weer `PL_FMD_LOAD_ALL` aanroept. Open bij een aangeroepen pipeline de bijbehorende run om te zien welke activiteit in die pipeline faalde. De portal toont naar verwachting een link van de aanroep naar de onderliggende run; dat is nog niet vastgelegd.

## Stap 2: lees de keten

`PL_FMD_LOAD_ALL` bestaat uit de volgende onderdelen:

| Activiteit | Wat hij doet |
|---|---|
| `SP_START_AUDIT_PIPELINE` | Schrijft de start van de run in de logging. |
| `PL_FMD_LOAD_LANDINGZONE`, `_BRONZE`, `_SILVER` | Laden de drie lagen. Elke laag start ook als de vorige faalde. |
| `SP_FAIL_*_AUDIT_PIPELINE` | Schrijft een fout van een laag in de logging. |
| `FA_THROW_ERROR_LDZ`, `_BRZ`, `_SLV` | Maken de run rood nadat de fout is gelogd. |
| `SP_END_AUDIT_PIPELINE` | Schrijft het einde van een geslaagde run in de logging. |

De foutcodes van de drie fout-activiteiten zijn `LandingzoneFailed`, `BronzeFailed` en `SilverFailed`. Daarmee weet je in welke laag het misging. De meldingstekst zegt het zelf: *"The Bronze layer failed. The failure is already recorded in logging.PipelineExecution; query it for the failing entity."*

Faalt een kopieer- of commandopipeline (`PL_FMD_LDZ_COMMAND_*`, `PL_FMD_LDZ_COPY_FROM_*`), dan staat de reden van de onderliggende fout in de Fail-melding van die pipeline.

## Stap 3: de falende tabel vinden

Faalt de landingzone, dan staat in `PipelineExecution` alleen de keten, zonder tabel. De tabel en de echte fout staan in `CopyActivityExecution` (`LogType = 'FailedCopyActivity'`). Faalt Bronze of Silver, dan staat de fout per tabel in `NotebookExecution` met `"Action": "Error"` in `LogData`.

Draai de query onder *Controleren* in [Een tabel of bron handmatig laden](handmatig-laden.md#controleren). Die toont de falende tabellen van de laatste dag uit beide logtabellen. Filter je alleen op `Fail*`, dan mis je notebookfouten per tabel.

Een kind dat faalt vóór zijn eigen logging (bijvoorbeeld een login-timeout naar de configuratiedatabase) staat nooit in `NotebookExecution`. Gebruik dan deze query:

```sql
SELECT [LogDateTime], [PipelineName], LEFT([LogData], 1000) AS [LogData]
FROM   [logging].[PipelineExecution]
WHERE  [LogDateTime] >= DATEADD(DAY, -1, SYSUTCDATETIME())
  AND  [LogType] IN ('FailPipeline', 'FailedPipeline')
ORDER BY [LogDateTime] DESC;
```

De reden van zo'n kind staat in `LogData` achter `Failed notebooks: [...]`.

## Stap 4: bepaal de soort fout

| Wat je ziet | Soort | Wie lost het op |
|---|---|---|
| `PK: <kolom> doesn't exist in the source.` | Registratie of bron: een sleutelkolom bestaat niet in de bron. | Beheerteam: corrigeer de `PrimaryKeys` in de registratie, of de bron. |
| `Source file contains duplicated rows for PK: …` | Datakwaliteit: de bron levert dezelfde sleutel twee keer. | Eigenaar van de brondata. Eerst bepalen of de rijen echt dubbel zijn: breid anders de sleutel uit. |
| Een time-out | Volume tegenover een vaste time-out, geen inhoudelijke fout. | Beheerteam: laad de bron apart (zie *Time-outs* in [Een tabel of bron handmatig laden](handmatig-laden.md#time-outs)). |
| `UserErrorWithLargeConcurrentRuns` op een kopieeractiviteit | Throttling op de gedeelde integration runtime van de regio. De Copy-activiteiten proberen het automatisch opnieuw. | Beheerteam: start de tabel opnieuw als de retry het niet oploste. |
| `Login timeout expired` bij veel parallelle notebooks | Te veel gelijktijdige verbindingen met de configuratiedatabase. | Beheerteam: draai loads van verschillende omgevingen niet tegelijk. |
| Een run of notebook staat lang op `Queued` of `NotStarted` | Drukte op de capaciteit, geen storing. | Wacht. Duurt het langer dan 20 tot 25 minuten, overleg dan. |
| Bronze logt `SourceFileName: FILE NOT FOUND` en de run is groen | Een run zonder wijzigingen bij een bron die parquet-bestanden schrijft. Dit is normaal. | Niets. |

De rij over de login-time-out en de capaciteit volgt uit de beschrijving van het framework en is niet apart opnieuw getest.

## Stap 5: herstellen

**Opnieuw starten mag altijd.** Start `PL_FMD_LOAD_ALL` (of één laag) opnieuw met dezelfde parameters. Bestanden in de landingzone die nog niet zijn verwerkt (`IsProcessed = 0`) worden in de volgende Bronze-run opgepakt, en een bestand wordt niet dubbel geregistreerd.

**Een bestand dat in Bronze faalt, blijft hangen.** Het wordt elke run één keer opnieuw geprobeerd en houdt de latere bestanden van dezelfde tabel tegen: die worden niet gestart maar tellen wel als gefaald (`Failed notebooks: ['<Tabel>_0_0', '<Tabel>_0_1']`). Een retry in de notebooks staat bewust uit, omdat een retry een eerste fout zou verbergen.

**Herstel via de configuratie.** Is de oorzaak een registratiefout (bijvoorbeeld verkeerde `PrimaryKeys`), corrigeer die dan met `NB_REGISTRATIE` en start opnieuw. De wachtende bestanden worden dan op volgorde verwerkt.

**Een bestand bewust overslaan.** Corrigeer eerst de bron en land opnieuw, of sla het bestand bewust over:

```sql
UPDATE [execution].[PipelineLandingzoneEntity]
SET    [IsProcessed]     = 1
      ,[LoadEndDateTime] = GETDATE()
WHERE  [LandingzoneEntityId] = <LandingzoneEntityId>
  AND  [FileName]            = '<bestandsnaam>'
```

Leg het overslaan vast. De data uit dat bestand komt dan niet in Bronze.

**Een tabel volledig opnieuw laden.** Maak de opgeslagen waarde van het watermark leeg:

```sql
UPDATE [execution].[LandingzoneEntityLastLoadValue]
SET    [LoadValue]        = NULL
      ,[LastLoadDatetime] = GETDATE()
WHERE  [LandingzoneEntityId] = <LandingzoneEntityId>
```

Verwijder de rij **niet**: zonder die rij komt de tabel na de volgende landing niet meer in Bronze. Start daarna de tabel met de hand (zie [Een tabel of bron handmatig laden](handmatig-laden.md)). Bij een incrementele tabel verwijdert een volledige herlading geen rijen die in de bron zijn verwijderd; die blijven in Bronze staan. Het gedrag staat in de beschrijving van het framework, maar is niet als vaste procedure getest.

**Silver opnieuw laten verwerken.** Een gewijzigde cleansing-regel voor Silver werkt alleen op rijen die daarna veranderen. Zet de entiteit terug in de wachtrij met `execution.sp_RequeueSilverLayerEntities(@WorkspaceId, @DataSourceName, @Entities, @DryRun)`. `@WorkspaceId` is de DATA-workspace, het filter werkt als bij [Een tabel of bron handmatig laden](handmatig-laden.md), en `@DryRun` staat standaard op 1: de procedure toont dan alleen wat er in de wachtrij zou komen. Verandert de regel het type of de kolommen van de Silver-tabel, verwijder dan eerst de Silver-tabel.

**Een tabel uitzetten.** Is een tabel niet meer nodig of kapot in de bron, zet haar dan uit via de registratie in plaats van elke nacht te laten falen. Zet de open bestanden in de wachtrij op verwerkt, zoals hierboven.

## Na het herstel

1. Start de tabel opnieuw en volg de run (zie stap 1).
2. Draai de query uit stap 3 en controleer dat er geen nieuwe fout voor de tabel staat.
3. Controleer in `logging.vw_ExecutionSummary` dat de tabel in alle drie de lagen is geladen en dat het aantal rijen klopt (zie [Een tabel of bron handmatig laden](handmatig-laden.md#controleren)).
4. Noteer de oorzaak en de oplossing, zeker bij een overgeslagen bestand of een rechtstreekse wijziging in de configuratiedatabase.
