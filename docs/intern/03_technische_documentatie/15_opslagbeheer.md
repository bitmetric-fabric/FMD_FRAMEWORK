# Opslagbeheer: landing zone en Delta-tabellen

**Fase:** 3 (Technische documentatie)
**Datum:** 2026-10-07
**Status:** ~~Voorstel, ter beslissing door Bitmetric (punt 1 t/m 4) en de klant (bewaartermijn)~~ *Correctie 2026-10-07:* besloten (Mitchell, alle vijf punten zoals voorgesteld) en gebouwd in `FMD_FRAMEWORK#42` (ADR-015). De bewaartermijn blijft per klant te kiezen via `VAR_FMD.landingzone_retention_days`. Zie *Besluit en uitvoering* onderaan.
**Bron:** `FMD/src/` (per punt genoemd), `testplan-trial.md` T-F03/T-F04, Microsoft Learn (per punt genoemd)

*Bijgewerkt 2026-10-12 (FMD_FRAMEWORK#58): `PL_FMD_ORCHESTRATION_TEMPLATE` heet nu `PL_FMD_ORCHESTRATION`, `PL_FMD_LOAD_GOLD_TEMPLATE` heet nu `PL_FMD_LOAD_GOLD`.*

Het FMD ruimt geen opslag op. Bij een klant met veel data groeien daardoor twee dingen zonder grens: de landing zone en de oude versies van de Delta-tabellen in Bronze en Silver. Dit document beschrijft wat er groeit, wat Fabric zelf biedt, en een voorstel.

## Wat er groeit

**1. De landing zone.** Elke run legt per entiteit een nieuwe levering neer onder `Files/fmd/<namespace>/<entiteit>/<jjjj/mm/dd>/`. Niets in het framework verwijdert die (*vastgesteld*: geen verwijdercode in `src/`; de AdventureWorks-bestanden van 2026-09-28 staan er nog). Een volledige load legt bij elke run een complete kopie neer: een tabel van 10 GB die dagelijks volledig laadt, is 300 GB per maand. Incrementele entiteiten leveren alleen wijzigingen, en die blijven klein.

**2. Oude versies van de Delta-tabellen.** Elke merge in Bronze en Silver schrijft nieuwe bestanden; de bestanden van de vorige versie blijven staan tot er een `VACUUM` draait. Het framework zet alleen `autoCompact` aan (`NB_FMD_LOAD_LANDING_BRONZE`, `NB_FMD_LOAD_BRONZE_SILVER`). De kop van `NB_FMD_LOAD_BRONZE_SILVER` noemt "Optimize and vacuum", maar er is geen `VACUUM`-aanroep (*vastgesteld*). In de trial was `TPCH_ORDERS` na twee loads 60 MB in de landing zone en 199 MB in Bronze (T-F03/T-F04). Hoeveel daarvan oude versies zijn en hoeveel de hashkolommen, is niet gemeten (*aanname*: het grootste deel na meerdere merges).

**Waarom het ertoe doet:**
- **Kosten.** OneLake-opslag wordt per workspace op de capaciteit gerekend (Fabric Capacity Metrics, pagina *Storage*).
- **Privacy.** De landing zone bevat de ruwe brondata, ook persoonsgegevens, zonder einddatum. Een bewaartermijn is ook een AVG-vraag.
- **Lezen.** Veel oude bestanden in een Delta-tabel vertragen het lezen niet (Delta leest alleen de actuele versie), maar het SQL-endpoint en `OPTIMIZE` hebben meer werk (*aanname*).

## Wat Fabric zelf biedt

| Mogelijkheid | Wat het doet | Geschikt voor |
|---|---|---|
| **Lifecycle management policy** (workspace-instelling *OneLake → Lifecycle management*, of de REST API) | Verplaatst bestanden na X dagen naar de cool- of cold-laag. **Verwijdert niets.** Eén policy per workspace, maximaal 10 regels, filter op padprefix, draait dagelijks. Cool heeft een minimum van 30 dagen, cold van 90 dagen. ([Microsoft Learn](https://learn.microsoft.com/en-us/fabric/onelake/onelake-lifecycle-management), *vastgesteld*) | De landing zone goedkoper bewaren, niet opruimen |
| **Table maintenance** (lakehouse-UI per tabel, of `POST …/lakehouses/{id}/jobs/instances?jobType=TableMaintenance`) | `OPTIMIZE` (V-Order, Z-Order) en `VACUUM` met een bewaartermijn van minimaal 7 dagen, per tabel ([Microsoft Learn](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/background-jobs/run-on-demand-table-maintenance), *vastgesteld*) | `VACUUM`, maar per tabel één aanroep |
| **Delete-activiteit** in een pipeline | Verwijdert bestanden en mappen, met wildcards ([Microsoft Learn](https://learn.microsoft.com/en-us/fabric/data-factory/delete-data-activity)). Een filter op leeftijd voor een lakehouse noemt de documentatie niet (*aanname*: werkt zoals in ADF) | Opruimen op leeftijd |

## Voorstel

**1. De landing zone opruimen op basis van de wachtrij, niet op leeftijd.**
Een levering mag pas weg als Bronze hem heeft verwerkt: `execution.PipelineLandingzoneEntity.IsProcessed = 1` en `LoadEndDateTime` ouder dan de bewaartermijn. Opruimen op leeftijd alleen (Delete-activiteit) kan een **onverwerkte** levering verwijderen, bijvoorbeeld van een entiteit die al dagen faalt (T-D04: een gefaald bestand blokkeert latere). Bij een incrementele entiteit is die data dan weg, want de watermark is al opgeschoven.
- Uitvoering: een onderhoudsnotebook dat de verwerkte leveringen ouder dan *N* dagen uit de configdb leest en verwijdert met `notebookutils.fs.rm(…, recurse=True)`. Bij Snowflake is een levering een map, bij de andere bronnen een bestand; `rm` met `recurse` doet beide.
- De rij in de wachtrij blijft staan, met een kolom of logregel dat het bestand is verwijderd. *Open:* een kolom erbij (dacpac) of alleen loggen.

**2. `VACUUM` op Bronze en Silver, wekelijks, bewaartermijn 7 dagen.**
- In hetzelfde onderhoudsnotebook: per tabel uit `integration.BronzeLayerEntity` en `integration.SilverLayerEntity` een `DeltaTable.forPath(…).vacuum(168)`. Eén notebook is eenvoudiger dan per tabel de table-maintenance-API aanroepen.
- **Gevolg:** *time travel* in Bronze en Silver gaat maximaal 7 dagen terug. De historie in Silver zit in de rijen (SCD2), niet in de Delta-versies, en blijft dus volledig.
- `OPTIMIZE` hoeft niet apart: `autoCompact` staat al aan.

**3. Een pipeline `PL_FMD_MAINTENANCE` met een eigen schema**, buiten de laadvensters. Het onderhoud draait niet mee in `PL_FMD_ORCHESTRATION`, zodat een fout in het onderhoud geen load laat falen.

**4. In de generieke laag (PR op FMD_FRAMEWORK), met de bewaartermijn als instelling.** Het probleem geldt voor elke klant. De termijn komt in `VAR_FMD` (bijvoorbeeld `landingzone_retention_days`, standaard 30), zodat de klant hem zonder codewijziging kiest.

**Optioneel, per klant:** wil een klant de landing zone langer bewaren (audit), dan een lifecycle policy op de DATA-workspace, prefix `LH_DATA_LANDINGZONE.Lakehouse/Files`, naar *cool* na 30 dagen. Dat kost transacties bij het verplaatsen, en lezen uit cool is duurder. Niet voor `Tables/`: Delta-bestanden horen in *hot*.

## Te beslissen

| # | Vraag | Voorstel | Wie |
|---|---|---|---|
| 1 | Bewaartermijn van de landing zone | 30 dagen | klant (AVG, audit, herverwerking) |
| 2 | Opruimen op wachtrij of op leeftijd | wachtrij | Bitmetric |
| 3 | `VACUUM` wekelijks met 7 dagen | ja | Bitmetric |
| 4 | Generiek (PR) of per klant | generiek, met de termijn in `VAR_FMD` | Bitmetric |
| 5 | Verwijderen vastleggen in de wachtrij (kolom) of alleen loggen | alleen loggen; kolom pas als iemand erom vraagt | Bitmetric |

## Testplan (na akkoord)

In trial-Dev:
1. Een verwerkte levering ouder dan de termijn wordt verwijderd; een onverwerkte niet, ook als hij ouder is.
2. Een Snowflake-levering (map) en een ASQL-levering (bestand) worden allebei verwijderd.
3. Na `VACUUM` zijn de oude Delta-bestanden weg, en lezen Bronze en Silver nog dezelfde aantallen. De grootte vóór en na wordt gemeten.
4. Een fout in het onderhoud laat geen load falen.

## Besluit en uitvoering (2026-10-07)

**Besluit** (Mitchell, 2026-10-07): punt 1 t/m 5 zoals voorgesteld. ADR-015.

**Uitvoering** (`FMD_FRAMEWORK#42`):
- `NB_FMD_MAINTENANCE`, gestart door `PL_FMD_MAINTENANCE`. Per omgeving een eigen schema, bijvoorbeeld wekelijks buiten het laadvenster (draaiboek fase 5 stap 4).
- `execution.sp_GetMaintenanceTargets(@WorkspaceId, @RetentionDays)`: de verwerkte leveringen ouder dan de termijn (nooit een levering die ook onverwerkt in de wachtrij staat), en de Bronze- en Silver-tabellen. Weigert een termijn kleiner dan 1.
- `VAR_FMD.landingzone_retention_days` (Integer, standaard 30). `VACUUM` met 168 uur.
- Parameters van het notebook voor een losse run: `RetentionDays` en `WorkspaceGuid` (leeg = de waarden uit de Variable Libraries), `VacuumHours` (standaard 168; Delta weigert minder).

**Getest in eigen omgeving** (`testplan-trial.md` T-D09, 2026-10-07): een verwerkte levering van 40 dagen werd verwijderd, een onverwerkte van 40 dagen en een levering van vandaag bleven staan (run `adf2f335`). `VACUUM` op 24 tabellen zonder fouten (run `e82020d9`): Bronze van 406 naar 375 bestanden, Silver van 230 naar 197. In megabytes scheelde het nog weinig, omdat de grote oude versies minder dan 7 dagen oud waren.

**Incrementele loads** (*vastgesteld*: de watermark staat in `execution.LandingzoneEntityLastLoadValue`, niet in de bestanden):
- Opruimen raakt de watermark en de volgende load niet.
- Een onverwerkte levering is bij een incrementele entiteit de enige kopie van die wijzigingen: de watermark is al opgeschoven. Daarom ruimt het onderhoud alleen verwerkte leveringen op. Faalt Bronze op een levering, dan blijven die en de latere leveringen van die entiteit staan (T-D03, T-D04).
- **Bronze opnieuw opbouwen** kan uit de landing zone alleen binnen de bewaartermijn (`IsProcessed` terug op 0). Daarbuiten: watermark resetten (`10_operations.md`, *Een watermark resetten*) en een volledige load uit de bron. Voor een volledige load is de laatste levering genoeg.
- De historie in Silver (SCD2) staat in de rijen en hangt niet af van de landing zone.

**Valkuil uit de test:** pyodbc geeft GUID's in hoofdletters. `notebookutils.fs` accepteert die in een OneLake-pad, Delta (Hadoop/ABFS) niet: `400 Bad Request` op `_delta_log`. De procedure zet de GUID's daarom om naar kleine letters, zoals de andere procedures.
