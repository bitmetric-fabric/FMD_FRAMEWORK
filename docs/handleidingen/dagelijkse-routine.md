---
title: Dagelijkse routine en planning
sidebar_position: 2
---

# Dagelijkse routine en planning

Deze handleiding beschrijft hoe geplande uitvoeringen in een FMD-installatie werken, wat je na elke uitvoering controleert, hoe je een planning wijzigt en hoe je het wekelijkse onderhoud plant. Gegevens van één specifieke installatie (tijden, namen, aanpassingen) horen niet hier maar in de documentatie van die installatie.

## De keten van een geplande uitvoering

Een planning start een planningspipeline, die de rest aanroept:

1. `PL_FMD_SCHEDULE_<omgeving>` in de workspace INTEGRATION CONFIG start met de parameter `Target = LOAD`.
2. Die roept `PL_FMD_ORCHESTRATION` aan in de INTEGRATION CODE-workspace van de omgeving, met de parameters `LoadGroup` en `DataSourceName`.
3. De orchestratie start `PL_FMD_LOAD_ALL`: Landingzone, Bronze en Silver.
4. De setup van de business-domeinen hangt daarna per domein de Gold-pipeline `PL_FMD_LOAD_GOLD` van dat domein aan de orchestratie (als activiteit `PL_<DOMEIN>_LOAD_GOLD`). De standaard is dat die alleen draait als `PL_FMD_LOAD_ALL` **Succeeded** is; dan draait Gold niet na een fout in één entiteit. In deze installatie is dat anders: Gold draait altijd, ook na een fout (zie het hoofdstuk Schedules en afwijkingen in deze installatie).
5. Gold draait na elke uitvoering van de orchestratie, ook na een uitvoering met een filter op `LoadGroup` of `DataSourceName`.

`PL_FMD_SCHEDULE_<omgeving>` heeft de parameters `Target` (`LOAD` of `MAINTENANCE`), `LoadGroup` en `DataSourceName`. Een andere waarde van `Target` laat de pipeline falen met `UnknownTarget`. De pipeline heeft `concurrency: 1`: een uitvoering wacht zolang een andere van dezelfde pipeline loopt.

De planningen staan op deze pipeline in CONFIG en niet op de pipelines in de CODE-workspaces. CONFIG zit in geen deployment pipeline, dus een promotie raakt de planningen niet. De setup maakt de planningspipelines eenmalig aan en overschrijft ze nooit. Ze staan ook niet in git.

## Dagelijkse controle

Doe dit na elke geplande uitvoering, per omgeving die je beheert. Het kost ongeveer vijf minuten.

1. **Pipelinestatus.** Open in de monitor van INTEGRATION CONFIG de laatste uitvoering van `PL_FMD_SCHEDULE_<omgeving>`. `Failed` is een incident. `Completed` of `Succeeded` is nog niet genoeg (zie stap 2).
2. **Falende entiteiten.** Het framework ketent de lagen op `Completed`, dus een groene uitvoering kan toch tabellen missen. Draai de query onder *Controleren* in [Een tabel of bron handmatig laden](handmatig-laden.md#controleren), of kijk in het FMD_Logging-rapport.
3. **Wachtrij.** Bestanden die na enkele uren nog niet zijn verwerkt, wijzen op een fout in Bronze:
   ```sql
   SELECT PLE.[LandingzoneEntityId], PLE.[FileName], PLE.[InsertDateTime]
   FROM   [execution].[PipelineLandingzoneEntity] PLE
   WHERE  PLE.[IsProcessed] = 0
     AND  PLE.[InsertDateTime] < DATEADD(HOUR, -2, SYSUTCDATETIME());
   ```
   Een entiteit die bewust is uitgezet, kan hier nog open bestanden hebben.
4. **Gold.** Controleer dat de Gold-pipeline van elk domein in de eigen omgeving `Completed` is, en dat de laatste notebook-activiteit (de refresh) is geslaagd.
5. **Duur.** Vergelijk de duur met de vorige dagen (`logging.vw_ExecutionSummary`, zie [Een tabel of bron handmatig laden](handmatig-laden.md#controleren)). Een uitvoering die ruim langer duurt, wijst op drukte op de capaciteit of op een eerste volledig laden van een grote tabel.

## Wekelijks

- Controleer dat de onderhoudsuitvoering van de afgelopen week in elke omgeving `Completed` is. Een fout laat de pipeline falen met een lijst van de fouten.
- Loop de wachtrij na op entiteiten die al meerdere dagen open staan.
- Noteer de langste uitvoering van de week. Komt die in de buurt van de volgende planning, plan dan om.
- Controleer de geldigheid van de inloggegevens achter de connecties en de service principals.

## Een planning wijzigen

Doe dit in de portal, op het item `PL_FMD_SCHEDULE_<omgeving>` in INTEGRATION CONFIG, één omgeving per keer. De schermafbeeldingen zijn opgenomen in november 2026.

### Het paneel Schedule openen

1. Open het item `PL_FMD_SCHEDULE_<omgeving>` en kies op het tabblad **Home** de knop **Schedule**. Onder in beeld staan de parameters van de pipeline: `Target` (standaardwaarde `LOAD`), `LoadGroup` en `DataSourceName`. Dit zijn de namen die je in een planning kunt meegeven.

   ![De pipeline-editor van PL_FMD_SCHEDULE met de knop Schedule op het tabblad Home en de parameters Target, LoadGroup en DataSourceName onder in beeld gemarkeerd.](afbeeldingen/dagelijkse-routine/01-editor-schedule-knop.png)

2. Het paneel **Schedule** opent rechts. Bovenaan staan de *Failure notifications* (zie [Meldingen bij een mislukte uitvoering](#meldingen-bij-een-mislukte-uitvoering)). Daaronder staat de lijst *Schedules*: per planning de herhaling (bijvoorbeeld *Every day*), de status *Active*, de tijd, de volgende uitvoering (*Next update*) en de tijdzone, met de knoppen **Edit** en **Turn Off**. Onder de lijst staat **Add schedule**.

   ![Het paneel Schedule van PL_FMD_SCHEDULE met het veld Failure notifications, één schedule met de status Active, de knoppen Edit en Turn Off, en de knop Add schedule gemarkeerd.](afbeeldingen/dagelijkse-routine/02-schedule-paneel.png)

### Een planning toevoegen

1. Kies **Add schedule**. Kies bij **Repeat** een herhaling (*Daily* of *Weekly*; bij *Weekly* vink je de dagen aan), vul bij **Time of day** de tijd in en kies de **Time zone**. De start- en einddatum staan standaard op vandaag en 31-12-9999.
2. Laat bij een gewoon laden het gedeelte **Parameters** leeg.
3. Kies **Save**.

![Het formulier Add schedule met de herhaling Daily, de tijd 03:00, de tijdzone en de knop Save gemarkeerd; het gedeelte Parameters is leeg.](afbeeldingen/dagelijkse-routine/03-nieuw-schedule.png)

### Een planning wijzigen of uitzetten

1. Kies bij de planning **Edit**. Het formulier opent met de opgeslagen waarden, hier de herhaling *Daily* en de tijd 03:00.

   ![Het formulier Edit schedule met de opgeslagen herhaling Daily en de tijd 03:00 gemarkeerd.](afbeeldingen/dagelijkse-routine/04-schedule-bewerken.png)

2. Pas de herhaling, de tijd of de parameters aan en kies **Save**. Hier is de tijd gewijzigd naar 05:00. De lijst toont daarna de nieuwe tijd.

   ![Hetzelfde formulier met de tijd gewijzigd naar 05:00 en de knop Save gemarkeerd.](afbeeldingen/dagelijkse-routine/05-tijd-gewijzigd.png)

3. Wil je de planning tijdelijk niet laten draaien, kies dan **Turn Off** in de lijst (zie de tweede afbeelding onder [Het paneel Schedule openen](#het-paneel-schedule-openen)). Wil je het definitief weghalen, kies dan in het formulier **Delete schedule**.

   ![Het formulier Edit schedule met de knop Delete schedule gemarkeerd.](afbeeldingen/dagelijkse-routine/06-schedule-verwijderen.png)

### Parameters meegeven

Voor een onderhoudsplanning kies je bij **Repeat** *Weekly*, vink je een dag aan (hier *Sunday*) en vul je de tijd in. Kies daarna **Add parameter**, vul bij *Name* `Target` in, kies als *Type* **String** en vul bij *Value* `MAINTENANCE` in.

![Het formulier voor een weekly schedule met herhaling Weekly, de dag Sunday, de tijd 10:00 en de parameter Target van het type String met de waarde MAINTENANCE gemarkeerd.](afbeeldingen/dagelijkse-routine/07-parameter-target.png)

- Geef bij een planning voor het laden geen parameters op. Dan laadt het alles. Wil je een deel laden, vul dan `LoadGroup` of `DataSourceName` in. Zonder parameters gelden de standaardwaarden van de pipeline: `Target = LOAD` en geen filter.
- Geef bij een onderhoudsplanning altijd `Target = MAINTENANCE` mee. **Zonder die parameter draait de planning een gewoon laden, met Gold, in plaats van onderhoud**, omdat de standaardwaarde `LOAD` is.
- De naam van een parameter moet precies overeenkomen met een parameter van de pipeline (let op hoofdletters en spelling). Het formulier waarschuwt hiervoor in een regel onder de parameters, maar controleert de naam niet bij het opslaan. Een typefout, zoals `Targe`, wordt naar verwachting genegeerd: de planning draait dan met de standaardwaarde. Kopieer de naam daarom liever dan hem te typen, en controleer hem in het veld voor je opslaat.
- Controleer na het opslaan in de lijst de herhaling, de tijd en de volgende uitvoering (*Next update*). Open **Edit** om de parameters terug te zien.
- Een planning heeft een eigen tijdzone. Kies bewust dezelfde tijdzone voor alle planningen van een omgeving.
- Een nieuwe planning is direct actief en start op de ingestelde tijd een echte uitvoering. Zet een planning dat je alleen test, daarna uit of verwijder het.
- Leg elke wijziging vast: planningen staan niet in git en een promotie neemt ze niet mee. Een verwijderd of opnieuw aangemaakt planningspipeline-item verliest ze.

## Meldingen bij een mislukte uitvoering

Het framework stuurt zelf geen meldingen. Fabric kan dat wel voor een **geplande** pipeline: zet op `PL_FMD_SCHEDULE_<omgeving>` onder **Home → Schedule → Failure notifications** gebruikers of groepen, één keer per omgeving. Het veld staat bovenaan het paneel Schedule (zie de tweede afbeelding onder [Het paneel Schedule openen](#het-paneel-schedule-openen)); typ een naam of e-mailadres en kies de persoon of groep uit de lijst. Omdat CONFIG in geen deployment pipeline zit, blijven de ontvangers bij een promotie staan. Een handmatige uitvoering geeft geen e-mail.

In de Monitor staat daarnaast **Configure notifications → Schedule failures (Preview)**.

## Onderhoud plannen

`PL_FMD_MAINTENANCE` wordt gepland via dezelfde planningspipeline met `Target = MAINTENANCE`. Het ruimt verwerkte leveringen in de landingzone op die ouder zijn dan de bewaartermijn en draait `VACUUM` op Bronze en Silver. Eenmaal per week volstaat.

- **Moment.** Kies een moment zonder laadrun in dezelfde omgeving, en met ruime marge voor en na de laatste en de eerste uitvoering. Een gelijktijdige schrijfactie op dezelfde tabellen kan falen. Meestal is dat zondag, als er in het weekend niet wordt geladen.
- **Spreiding.** Plan de omgevingen op verschillende tijden als ze dezelfde capaciteit delen, zodat de Spark-sessies niet om dezelfde capaciteit strijden.
- **Duur.** De duur hangt af van het aantal tabellen en hun grootte, en is vooraf niet te schatten. De planningspipeline geeft het onderhoud een time-out van 4 uur. Draai de eerste keer met de hand, meet de duur en pas de tijd zo nodig aan.
- **Eerste uitvoering.** De opruiming van de landingzone verwijdert pas leveringen als ze ouder zijn dan de bewaartermijn (standaard 30 dagen). In een jonge installatie doet de eerste uitvoering dus waarschijnlijk niets op dat punt.
