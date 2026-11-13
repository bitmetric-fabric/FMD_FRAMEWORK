---
title: Een Direct Lake-model laten verwijzen naar het juiste lakehouse na promotie
sidebar_position: 4
---

# Een Direct Lake-model laten verwijzen naar het juiste lakehouse na promotie

Een Direct Lake-model leest uit het lakehouse waarvan het pad in de expressie staat. Promoveer je het model van Dev naar Test, dan neemt de promotie dat pad mee: het model in Test leest dan nog uit Gold van Dev. Deze handleiding beschrijft hoe je het pad in een **parameter** zet, zodat een **parameter rule** in de deployment pipeline het pad per stage kan vervangen. Je voegt de parameter toe in de TMDL view van de web-editor.

Het gaat om een model op **OneLake** (`AzureStorage.DataLake`). Voor een model op het SQL-endpoint van het lakehouse geldt een andere route, een data source rule, die hier niet wordt beschreven.

De labels *vastgesteld* (uit de definitie of de documentatie van Microsoft gelezen), *getest in eigen omgeving* (met datum) en *aanname* geven aan hoe zeker een bewering is. De schermafbeeldingen komen uit een referentie-installatie van november 2026.

## Wat vaststaat en wat niet

- **Verversen van de data werkt**, ook met de parameter actief (*getest in eigen omgeving*, 10 november 2026).
- **Promoveer alleen met de parameter actief.** Staat het letterlijke pad actief tijdens de promotie, dan herkoppelt de parameter rule niet en leest Test uit Dev (*getest in eigen omgeving*, 9 november 2026).
- **Het schema bijwerken werkt met de parameter actief** (**Refresh → Schema** en **Edit tables**), mits elke tabel in het model een `sourceLineageTag` heeft. Ontbreekt die op een tabel, dan faalt het schema verversen, met of zonder parameter (*getest in eigen omgeving*, 10 november 2026). Zie *Het schema bijwerken*.

## Vooraf

- Gold van de omgeving waar je naartoe promoveert bestaat en is gevuld. Het model in Test moet naar Gold van Test kunnen wijzen.
- Je bent eigenaar van het model. Alleen de eigenaar kan een rule maken (*vastgesteld*, Microsoft Learn, *Create deployment rules*).
- Je bent admin van de deployment pipeline van de SEMANTIC-workspace.
- Een Apply in de TMDL view kan een compatibiliteitsniveau van minimaal 1707 vragen. Het niveau verhogen is eenmalig en niet terug te draaien. Het referentiemodel stond op 1707.
- Je kent het OneLake-pad van het lakehouse `LH_GOLD_LAYER` van de omgeving, in de vorm `https://onelake.dfs.fabric.microsoft.com/<WorkspaceId>/<LakehouseId>` (het item van het type **Lakehouse**, niet het SQL-endpoint met dezelfde naam, en zonder slash aan het eind).

## Stap 1: de parameter toevoegen (Dev)

1. Open het semantisch model in de bewerkmodus. Staat rechtsboven **Viewing**, kies dan het menu en daarna **Editing**. In de modus Viewing worden wijzigingen niet opgeslagen.

   ![Het menu rechtsboven in de modelweergave met de keuzes Editing, Viewing en Edit in Desktop](afbeeldingen/direct-lake-parameter/01-editing-modus.png)

   *Afbeelding 1: schakel van Viewing naar Editing.*

2. Kies onderaan **TMDL View**. Kies rechts in het paneel **Data** het tabblad **Model** en klap **Expressions** open. Er staat één expressie: `DirectLake - LH_GOLD_LAYER`. De melding *TMDL scripts are discarded on close* betekent dat een script niet wordt bewaard als je het venster sluit.

   ![De TMDL view met het paneel Data, tabblad Model en de knop om Expressions open te klappen](afbeeldingen/direct-lake-parameter/02-tmdl-view-expressions.png)

   *Afbeelding 2: TMDL View, tabblad Model, onderdeel Expressions.*

3. Sleep **Expressions** naar de editor. Het script verschijnt met de bestaande expressie.

   ![Het script in de TMDL view na het slepen van Expressions, met alleen de bestaande expressie](afbeeldingen/direct-lake-parameter/03-script-na-slepen.png)

   *Afbeelding 3: het script na het slepen. Het pad in `Source` is nog letterlijk; de ID's zijn afgedekt.*

4. Voeg boven de bestaande expressie de parameter toe, en laat in de expressie `DirectLake - LH_GOLD_LAYER` het letterlijke pad staan als commentaar. Het script wordt dan:

   ```
   createOrReplace

   	expression OneLakeUrl = "https://onelake.dfs.fabric.microsoft.com/<WorkspaceId Gold Dev>/<LakehouseId Gold Dev>" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
   	annotation PBI_ResultType = Text

   	expression 'DirectLake - LH_GOLD_LAYER' =
   			let
   				//Source = AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/<WorkspaceId Gold Dev>/<LakehouseId Gold Dev>", [HierarchicalNavigation=true])
   				Source = AzureStorage.DataLake(OneLakeUrl, [HierarchicalNavigation=true])
   			in
   				Source
   		lineageTag: <de bestaande lineageTag>

   		annotation PBI_IncludeFutureArtifacts = False
   ```

   Je doet het in twee delen: eerst het parameterblok toevoegen, daarna de regel `Source` aanpassen.

   ![Het script met het parameterblok boven de bestaande expressie, de regel Source nog letterlijk](afbeeldingen/direct-lake-parameter/04-parameterblok-toegevoegd.png)

   *Afbeelding 4: het parameterblok is toegevoegd; `Source` is nog letterlijk.*

   ![Het script met Source op de parameter en het letterlijke pad in commentaar](afbeeldingen/direct-lake-parameter/05-source-aangepast.png)

   *Afbeelding 5: `Source` gebruikt nu `OneLakeUrl`; het letterlijke pad staat in commentaar (met `//`).*

   - Laat de bestaande `lineageTag` en de annotaties (`PBI_IncludeFutureArtifacts`) staan. De editor beheert ze. Microsoft beschrijft `PBI_IncludeFutureArtifacts` niet; raak hem niet aan.
   - **De parameter moet in hetzelfde script staan** als de verwijzing erop. Staat `OneLakeUrl` niet in het model, dan geeft de Apply de foutmelding *Direct Lake mode requires a Direct Lake data source* (*getest in eigen omgeving*, 10 november 2026: die melding kwam doordat het script naar de parameter verwees zonder haar te definiëren).
   - De waarde achter het `=` bij `OneLakeUrl` is de huidige waarde van de parameter in Dev. Je hoeft hem nergens apart in te stellen.
   - Plak het script in één keer: de editor springt bij typen vanzelf in.

5. Kies **Preview** om het verschil met het model te zien, en daarna **Apply**.

   ![De TMDL view met het verschil tussen het huidige model en het script: links in rood de oude regel Source, rechts in groen de nieuwe regels](afbeeldingen/direct-lake-parameter/06-preview-verschil.png)

   *Afbeelding 6: Preview toont het verschil. Rood is wat verdwijnt (de actieve letterlijke regel), groen is wat erbij komt (de uitgecommentarieerde letterlijke regel en de regel met `OneLakeUrl`). De ID's zijn afgedekt.*

6. Controleer dat het model de parameter kent. Onder **Expressions** staan nu twee items (de expressie en de parameter), en de service geeft de waarde terug:

   ```
   GET https://api.powerbi.com/v1.0/myorg/groups/{ws}/datasets/{id}/parameters
   ```

   Dat toont `OneLakeUrl` met de huidige waarde (*getest in eigen omgeving*, 10 november 2026). Het eindpunt `datasources` toont voor dit model alleen het type (`AzureDataLakeStorage`) en niet het pad; gebruik het voor deze controle dus niet.

Getest in eigen omgeving (10 november 2026): de Apply slaagt, een data-verversing slaagt direct daarna (`Completed`, type `WebModeling`) en een DAX-query over het model geeft data.

## Stap 2: verversen

Kies in de modelweergave **Refresh** (het pijltje ernaast opent het menu). Er zijn drie opties:

![Het Refresh-menu met de opties Schema and data, Schema en Data](afbeeldingen/direct-lake-parameter/07-refresh-menu.png)

*Afbeelding 7: het menu bij Refresh.*

| Optie | Met de parameter actief |
|---|---|
| **Data** | Werkt (*getest in eigen omgeving*, 10 november 2026). |
| **Schema** | Werkt (*getest in eigen omgeving*, 10 november 2026), mits elke tabel een `sourceLineageTag` heeft; zie *Het schema bijwerken*. |
| **Schema and data** | Idem (het schema is het eerste deel). |

Tijdens een verversing kun je het model niet bekijken of bewerken, en de portal waarschuwt daarvoor.

## Het schema bijwerken

Is er in Gold een tabel of kolom bijgekomen, of wil je tabellen aan het model toevoegen, dan ververs je het schema met **Refresh → Schema** of **Edit tables**. Dat kan met de parameter actief; je hoeft hem niet uit te zetten (*getest in eigen omgeving*, 10 november 2026, op drie modellen, met en zonder parameter).

Faalt het met de melding *Underlying Error: Query Evaluation failed for query: DirectLake - LH_GOLD_LAYER*, controleer dan de tabellen in het model:

![De foutmelding Query Evaluation failed for query DirectLake - LH_GOLD_LAYER bij het verversen van het schema](afbeeldingen/direct-lake-parameter/08-schema-fout.png)

*Afbeelding 8: de melding bij Refresh, Schema. Het Activity ID is afgedekt.*

**Oorzaak: een tabel zonder `sourceLineageTag`** (*getest in eigen omgeving*, 10 november 2026). Met die tag koppelt de editor een tabel aan de tabel in het lakehouse. Een tabel die via een script of de API is aangemaakt, kan hem missen. Het gevolg: Refresh → Schema faalt met bovenstaande melding, ook als de parameter niet in het model staat. In ons referentiemodel was dat de enige afwijking: dezelfde tabel faalde zonder de tag en slaagde na het toevoegen ervan; een data-verversing slaagde in beide gevallen.

Herstel in de TMDL view (**Apply**) of via de definitie: zet de tag direct onder `lineageTag` van de tabel, in de vorm `[schema].[tabel]` van de tabel in het lakehouse:

```
table Sales
	lineageTag: <de bestaande lineageTag>
	sourceLineageTag: [gold].[f_salesorder]
```

Open het model daarna opnieuw in Editing en ververs het schema. Wijzig je het model buiten de editor om terwijl het openstaat, dan meldt de editor *The change you were making failed to apply*; sluit het model dan en open het opnieuw.

Controleer vooraf in de TMDL view (sleep **Tables** naar de editor) of elke tabel de regel `sourceLineageTag` heeft.

*Aanname:* eerdere mislukte schema-verversingen op andere modellen (26 oktober en 9 november 2026) hadden dezelfde oorzaak. Dat is niet nagegaan.

Promoveer ook hier alleen met de parameter actief: staat het letterlijke pad actief tijdens de promotie, dan herkoppelt de parameter rule niet (*getest in eigen omgeving*, 9 november 2026: het model in Test wees naar Gold van Dev).

## Stap 3: promoveren naar Test

1. Open de deployment pipeline van de SEMANTIC-workspace.
2. Kies de stage Development en kies **Deploy** naar Test. Vul een notitie in en wacht op `Succeeded`.

Een rule kan pas worden gemaakt als het model in Test bestaat. Het model moet dus eerst naar Test. *Getest in eigen omgeving* (27 oktober 2026, D naar T). Een schermafbeelding van deze stap volgt.

## Stap 4: de parameter rule in Test

Deployment rules werken pas bij de volgende deployment naar die stage (*vastgesteld*, Microsoft Learn).

1. Ga in de deployment pipeline naar de stage **Test**. In de stage Development kun je geen rules maken.
2. Kies **Deployment rules** en selecteer het model.
3. Klap **Parameter rules** uit (niet *Data source rules*) en kies **Add rule**.
4. Kies de parameter `OneLakeUrl`. De huidige waarde, het pad van Dev, staat erbij.
5. Vervang de waarde door het pad van Gold van Test: `https://onelake.dfs.fabric.microsoft.com/<WorkspaceId Gold Test>/<LakehouseId Gold Test>`. Gebruik het Lakehouse-item van `LH_GOLD_LAYER` in de DATA-workspace van Test.
6. Sla de rule op.

De rule wordt ongeldig als de parameter in het model wordt hernoemd of verwijderd. De deployment faalt dan (*vastgesteld*, Microsoft Learn). Microsoft Learn noemt parameters in een Direct Lake-expressie niet; dat de rule hier werkt, is alleen door onze test bevestigd (*getest in eigen omgeving*, 27 oktober 2026). Schermafbeeldingen van deze stap volgen.

## Stap 5: opnieuw promoveren en controleren

1. Promoveer het model opnieuw van Dev naar Test. De rule werkt bij deze deployment.
2. Controleer dat de parameter in Test het pad van Gold van Test heeft:

   ```
   GET https://api.powerbi.com/v1.0/myorg/groups/{ws}/datasets/{id}/parameters
   ```

3. Ververs het model in Test (**Refresh → Data**); de refresh moet `Completed` zijn.
4. Een DAX-vergelijking bewijst alleen iets als de data in beide omgevingen verschilt. Gebruik de parameterwaarde als bewijs.
5. Promoveer een rapport pas nadat het model in Test staat. Controleer daarna dat het `datasetId` van het rapport het model in Test is.

## Valkuilen

| Verschijnsel | Oorzaak en oplossing |
|---|---|
| *Direct Lake mode requires a Direct Lake data source … Failed to save modifications* bij een Apply | Het script verwijst naar `OneLakeUrl` zonder dat de parameter in het model of in hetzelfde script staat. Neem de parameter in het script op. Dezelfde melding is eerder bij andere modellen gezien; de oorzaak is daar niet vastgesteld. |
| *Query Evaluation failed for query: DirectLake - LH_GOLD_LAYER* bij **Refresh → Schema** of **Schema and data** | Een tabel mist `sourceLineageTag`. Voeg hem toe (zie *Het schema bijwerken*). De parameter is niet de oorzaak. |
| **Edit tables** faalt met *ConceptualSchemaSettings* | Op 26 oktober 2026 gezien; oorzaak niet vastgesteld. Op 10 november 2026 werkte Edit tables met de parameter actief. Controleer eerst de `sourceLineageTag` van de tabellen. |
| Het model in Test leest uit Dev | Het letterlijke pad was actief tijdens de promotie, of de rule is nog niet van kracht. Controleer de parameterwaarde in Test, zet de parameter aan in Dev en promoveer opnieuw. |
| De deployment faalt na het hernoemen van de parameter | De rule is ongeldig. Maak de rule opnieuw. |
| Parameter rules zijn niet zichtbaar | Het model is nog niet naar die stage gepromoveerd. Promoveer eerst. |
| Een verversing faalt met *We cannot access the source Delta table* | Het SQL-endpoint van het lakehouse kent de nieuwe tabellen nog niet. Ververs de metadata van het endpoint. |
| Een Apply vraagt om een hoger compatibiliteitsniveau | Verhoog het niveau naar 1707. Dat is eenmalig en niet terug te draaien. |

## Nog niet getest of nog niet vastgelegd

- Schermafbeeldingen van het promoveren en van de parameter rule (stap 3 en 4).
- Het mappen van een cloud connectie voor het model in Test: er is geen procedure gevonden, en niet vastgesteld of het nodig is.
- Promotie van Test naar Productie met dezelfde rule.
- Meerdere rapporten op één model.
