# Semantisch model: Direct Lake en cross-workspace-referenties

**Bron:** `output/01_kennisbasis/gold-en-semantic.md`, `registratie.md`; `bronnen/notities/fmd-cross-workspace-references.md`; transcript `2026-09-11_fmd-agents-configuratie-vastleggen.md`
**Status:** zie per punt. **Let op:** de fork bevat geen semantisch model voor een business-domein. De setup maakt alleen de SEMANTIC-workspace en de deployment pipeline aan. Alles in dit document komt uit de eigen tenant, niet uit de repo. *(Correctie 2026-09-25, review 2 N-R4: de labels stonden op "vastgesteld".)*

## Direct Lake tegen de Gold-laag

Het semantische model in de SEMANTIC-workspace van een business-domein gebruikt **Direct Lake** tegen de Gold-laag (de DATA-workspace van datzelfde domein). Geen import-modus, geen dataduplicatie — het model leest rechtstreeks de Delta-tabellen die de Gold-notebooks produceren.

**Status:** Bitmetric-keuze, waargenomen in de eigen tenant (`Sales Analysis` in `FINANCE SEMANTIC`). Niet in de repo vastgelegd.

## Het cross-workspace-referentieprobleem

Cross-workspace-referenties (van het semantisch model naar de Gold-Lakehouse) worden door Fabric intern als **letterlijke object-ID's** opgeslagen. Bij promotie naar Test/Prod (via welk mechanisme dan ook) herbinden deze ID's **niet automatisch** aan de juiste omgevingsspecifieke Lakehouse — het model in Test blijft naar de Dev-Lakehouse wijzen, tenzij dit expliciet wordt opgelost.

**Status:** waargenomen in de eigen tenant. Op 2026-09-11 bleek het Productie-rapport `Sales Analysis` (`FINANCE SEMANTIC (P)`) via Direct Lake uit de Dev-lakehouse te lezen. Het is hersteld door de koppeling met de hand om te zetten; een deployment rule is nog niet ingesteld (zie "Openstaand actiepunt").

Dit is een van drie bekende **"live defects"** die in de eigen Bitmetric-omgeving zijn vastgesteld rond cross-workspace-referenties (zie `01_kennisbasis/registratie.md` voor de volledige lijst van drie — de andere twee betreffen andere onderdelen van de keten, niet het semantisch model).

## Twee bekende oplossingsroutes

**Route 1 — Variable Library-patroon (voor notebooks/pipelines, niet voor het semantisch model zelf).**
`notebookutils.variableLibrary`/`libraryVariables` in pipelines lost dit op voor notebook- en pipeline-gebaseerde referenties (zie ook `05_INTEGRATION/`, waar dit al is toegepast voor workspace-/lakehouse-GUID's). **Dit werkt niet voor het semantisch model zelf** — een semantisch model kan geen Variable Library rechtstreeks uitlezen.

**Route 2 — specifiek voor het semantisch model:**
- **Handmatige Direct Lake-pointer-swap** na deployment, vóór het model in de doelomgeving bruikbaar is. Voor personal-workspace-scenario's is dit end-to-end getest ("proven end-to-end", 2026-09-12): vóór commit wordt de pointer handmatig gewisseld.
- **Deployment Pipeline "deployment rule"** — alleen via de Fabric-portal in te stellen, door de eigenaar van het model; **geen REST API-ondersteuning** (opnieuw nagekeken 2026-09-26 in Microsoft Learn, *The Microsoft Fabric deployment pipelines process*). Die pagina bevestigt ook dat een Direct Lake-model bij een promotie niet automatisch naar de lakehouse van de doelstage bindt. Een rule blijft staan voor volgende promoties.
- **Expressie herschrijven via `updateDefinition`** (getest 2026-09-26, `testplan-trial.md` T-E03). Na de promotie in `definition/expressions.tmdl` van het model in de doelstage de Gold-server en het SQL-endpoint-ID van die omgeving invullen. Daarna framen en controleren met `GET …/datasets/{id}/datasources`. Scriptbaar, maar de volgende promotie zet de Dev-verbinding terug, dus dit moet na elke promotie.

**Route 3 — fabric-cicd (later spoor volgens ADR-012, niet in gebruik):** fabric-cicd kan bij de deploy ID's in de itemdefinitie vervangen via `parameter.yml` (`find_replace`), ook in een semantisch model. Niet getest in de eigen omgeving; alleen relevant als een klant voor fabric-cicd kiest (`02_beslisdocument/03_architectuurvarianten.md`, Variant B).

**Status:** het probleem is opnieuw bevestigd in de hertest (2026-09-26, T-E03: het model in Test wees na de promotie naar het SQL-endpoint van Gold (D)), en de `updateDefinition`-route is getest. ~~De deployment rule zelf is nog niet uitgevoerd (T-E03 geparkeerd).~~ *Bijgewerkt 2026-10-06 (P3-V2):* de data source rule is getest op 2026-09-28 in de demoklant (`SM_SALES` en `SM_FINANCE` in Test en Prod, draaiboek fase 7 stap 4b, `plan-demoklant-trial.md`). Eerder: waargenomen in de eigen tenant (het probleem, en route 2 voor de personal workspace); **aanname** voor de exacte stap-voor-stap-procedure van de handmatige pointer-swap in een Test/Prod-scenario (alleen de personal-workspace-variant is expliciet als "proven end-to-end" gedocumenteerd — de Test/Prod-route via de deployment rule is beschreven als bestaand mechanisme, niet als zelf-uitgevoerde procedure).

## Variant: Direct Lake op OneLake, met een parameter rule

*Toegevoegd 2026-10-26 (T-E08, `testplan-trial.md`; bron: eigen test in `FMD_GR`, pipeline `FMD_GR FRAMEWORK SEMANTIC`, D → T).*

**Wanneer dit speelt:** het model staat op OneLake als `expressions.tmdl` een `AzureStorage.DataLake(…)`-expressie bevat en de partities `expressionSource: 'DirectLake - <lakehouse>'` hebben. Dat is bij een model dat via de rapport-editor (**OneLake catalog**) is gemaakt. Een model op het SQL-endpoint heeft `expressionSource: DatabaseQuery` en een `Sql.Database(…)`-expressie; voor dat model geldt de data source rule hierboven. Bitmetric-default blijft het SQL-endpoint (B-GOLD-02).

**Wat de test liet zien** (*getest in eigen omgeving*, 2026-10-26):
- Zonder maatregel wijst het model in Test na de promotie naar Gold (D).
- *Data source rules* en *Parameter rules* zijn voor een model met een letterlijk pad grijs. Of dat aan de OneLake-variant ligt, is niet bewezen (T-E08 punt 3).
- Met het pad in een **parameter** en een **parameter rule** in de doelstage wijst het model na de tweede promotie naar Gold van het doel. De rule bleef staan na een volgende promotie.

**Stappen**
1. **Parameter toevoegen in Dev.** Zet het pad in `definition/expressions.tmdl` in een parameter en laat de Direct Lake-expressie ernaar verwijzen:
   ```
   expression OneLakeUrl = "https://onelake.dfs.fabric.microsoft.com/<WorkspaceId Gold Dev>/<LakehouseId Gold Dev>" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
       lineageTag: <nieuwe GUID>

       annotation PBI_ResultType = Text

   expression 'DirectLake - LH_GOLD_LAYER' =
           let
               Source = AzureStorage.DataLake(OneLakeUrl, [HierarchicalNavigation=true])
           in
               Source

       annotation PBI_IncludeFutureArtifacts = False
   ```
   - Gebruik het ID van het **Lakehouse**-item, niet van het SQL-endpoint-item. Beide heten `LH_GOLD_LAYER`; kijk naar het type.
   - Zet geen `queryGroup` op de parameter als die groep niet bestaat. De parser weigert het model dan (*Property QueryGroup … refers to an object which cannot be found*).
   - *Getest* via `updateDefinition`. In de browser (web modeling, TMDL view, preview) zijn dit de stappen volgens Microsoft Learn (*Develop Direct Lake semantic models*, *Use TMDL view*); zelf niet uitgevoerd (*aanname*):
     1. Open het model in de bewerkmodus en open de **TMDL view**.
     2. Sleep in het Data-paneel, tabblad **Model**, het knooppunt **Expressions** naar de editor. Je krijgt een `createOrReplace`-script met de expressie `'DirectLake - <lakehouse>'`.
     3. Voeg de parameter toe en pas de `Source`-regel aan, zoals hierboven. Laat de bestaande `lineageTag` en annotaties staan.
     4. Kijk met **Preview** naar het verschil, kies de bewerkmodus en klik op **Apply**.
     5. Ververs het model: een wijziging aan een Power Query-expressie vraagt een handmatige refresh.
     6. Een script wordt in de browser niet bewaard; kopieer het naar een bestand als je het wilt houden.
   - De ribbon van het model heeft ook een knop **New parameter**. Of die een parameter maakt die de Direct Lake-expressie kan gebruiken, is niet getest; de expressie moet je hoe dan ook in de TMDL view aanpassen.
   - **Volgorde:** voeg eerst alle tabellen toe en zet de parameter er als laatste in. Bij de klant faalde **Edit tables** met *ConceptualSchemaSettings should not be provided for non-Direct Lake queries* zolang de expressie de parameter gebruikte; met het letterlijke pad werkte het (2026-10-26, `11_troubleshooting.md`). Dat komt door de parameter: gereproduceerd in `FMD_GR` (2026-10-26, T-E08). Het gaat om **Edit tables**; een model met de parameter vernieuwt en bevraagt gewoon, en tabellen toevoegen via `updateDefinition` werkte.
   - **Wisselknop (getest in eigen omgeving, `FMD_GR`, 2026-10-26):** laat beide regels in de expressie staan en commentarieer de ene uit met `//`. Letterlijk pad actief (parameterregel uitgecommentarieerd): **Edit tables** werkt. Parameterregel actief: promoveren met de parameter rule. De parameter-expressie `OneLakeUrl` zelf mag blijven staan.
     ```
     let
         Source = AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/<ws>/<lh>", [HierarchicalNavigation=true])
         // Source = AzureStorage.DataLake(OneLakeUrl, [HierarchicalNavigation=true])
     in
         Source
     ```
   - Een parameter rule omzet de parameterwaarde alleen als de actieve regel de parameter gebruikt. Zet die regel dus actief vóór de promotie.
   - **Stand bij de klant (2026-10-27, *vastgesteld* door teruglezen):** in alle vijf de modellen in Development staat de parameterregel actief en de letterlijke regel uitgecommentarieerd (`//`). Wisselen kan in de TMDL view; zie voor de fout bij een te laag compatibiliteitsniveau (*StringIndexingBehavior … 1707*) `11_troubleshooting.md`. Alle vijf de modellen staan op niveau 1707.
   - **Wissel alleen in Development.** Een promotie neemt de uitgecommentarieerde regel mee, dus in Test staat die op het pad van Gold (D) (gezien in `SM_FACTUUR` (T)). Haal je daar de `//` weg, dan leest Test uit Dev.
   - Microsoft Learn noemt parameters in een Direct Lake-expressie nergens, niet als ondersteund en niet als beperkt. Onze test (T-E08) is hier het enige bewijs. Controleer dit na een wijziging van het platform opnieuw.
2. **Controleren in Dev.** Frame het model, draai een DAX-query en controleer met `GET https://api.powerbi.com/v1.0/myorg/groups/{ws}/datasets/{id}/datasources` dat het pad naar Gold (D) wijst.
3. **Promoveren naar de doelstage** (bijvoorbeeld D → T). Het model moet in de doelstage bestaan voordat je er een rule op zet. In de test werd *Parameter rules* beschikbaar na deze promotie; of dat vóór de eerste promotie ook kan, is niet getest.
4. **Parameter rule maken (alleen portal; geen API).** Je moet de **eigenaar van het model** zijn (*vastgesteld*, Microsoft Learn, *Create deployment rules*, pagina bijgewerkt 2026-09-29). Is een ander de eigenaar, neem het model dan eerst over in de modelinstellingen.
   1. Open de deployment pipeline van de SEMANTIC-workspace van het domein.
   2. Ga naar de **doelstage** (Test of Production). In de Development-stage kun je geen rules maken.
   3. Kies in die stage **Deployment rules**.
   4. Zoek het model in de lijst (zoekveld of filter) en selecteer het.
   5. Klap **Parameter rules** uit en kies **Add rule**. Niet *Data source rules*.
   6. Kies de parameter `OneLakeUrl` uit de lijst. De huidige waarde (het pad van Dev) staat erbij.
   7. Vervang die waarde door het OneLake-pad van Gold in het **doel**: `https://onelake.dfs.fabric.microsoft.com/<WorkspaceId Gold doel>/<LakehouseId Gold doel>` (zonder slash aan het eind).
   - Volgens Microsoft Learn werkt een rule pas bij de eerstvolgende deployment naar die stage. Dat past bij onze test (promotie, rule, promotie).
   - De naam van de knop voor opslaan staat niet op de Microsoft-pagina; die heb ik niet vastgelegd (*aanname*).
   - Wordt de parameter in het model gewijzigd of verwijderd, dan is de rule ongeldig en faalt de deployment (Microsoft Learn).
   - De IDs vind je met `GET https://api.fabric.microsoft.com/v1/workspaces/{ws}/items?type=Lakehouse` (het Lakehouse-item van `LH_GOLD_LAYER` in de DATA-workspace van het doel).
5. **Opnieuw promoveren** naar die stage.
6. **Controleren in het doel:** `datasources` wijst naar Gold van het doel, frame `Completed`, DAX-uitkomst vergeleken met de bron. Een DAX-vergelijking bewijst alleen iets als de data in beide omgevingen verschilt; `datasources` is het eigenlijke bewijs.
7. **Herhaal stap 3 t/m 6 per stage** (Production heeft zijn eigen rule met het pad van Gold (P)). Elk nieuw model vraagt per stage een nieuwe rule.

**Terugval zonder parameter:** herschrijf de expressie in het doelmodel na **elke** promotie met `updateDefinition` (Gold-workspace- en lakehouse-ID van het doel). Een volgende promotie zet de bronwaarde terug.

**Niet getest:** T → P; een model met meerdere Direct Lake-expressies of bronnen; fabric-cicd (`parameter.yml`, Route 3).

**Bevestigd bij de klant** (*getest in eigen omgeving*, 2026-10-27, klanttenant, pipeline `NL FW SEMANTIC`, D → T): `SM_FACTUUR` met de parameter `OneLakeUrl` en een parameter rule in Test. Na promotie, rule en tweede promotie (uitgevoerd door Mitchell) wijst `OneLakeUrl` in het T-model naar `LH_GOLD_LAYER` van `NL FW DATA (T)`. *Vastgesteld* door de TMDL van het T-model terug te lezen (`getDefinition`). Niet gecontroleerd: refresh en data van het T-model.

## Een bestaand Direct Lake-model omzetten naar `LH_GOLD_LAYER`

*Toegevoegd 2026-10-27 (bron: klanttenant, `NL FW SEMANTIC (D)`; modellen `SM_DEBITEUREN`, `SM_ZURICH_PREMIE_SCHADERESERVE`, `SM_PORTEFEUILLEVERDELING`).*

**Aanpak** (*getest in eigen omgeving*, 2026-10-27): per oud model (`getDefinition`, TMDL) een nieuw model bouwen met `POST …/semanticModels`:
1. Sjabloon uit een bestaand nieuw model: `definition.pbism`, `expressions.tmdl` (met `OneLakeUrl`, zie hierboven) en `database.tmdl` (compatibiliteitsniveau 1707).
2. Per Direct Lake-tabel de partitie vervangen door `entity` op `'DirectLake - LH_GOLD_LAYER'` met het juiste schema (`gold_anva` of `gold_hulptabellen`). De kolomtypen komen uit de Delta-log van de Gold-tabel, niet uit het oude model.
3. Metingen, relaties, berekende kolommen en berekende tabellen letterlijk overnemen. `PBI_QueryOrder` uit het sjabloon.
4. Controleren dat elke `sourceColumn` en elke relatiekolom in Gold bestaat; het script faalt als dat niet zo is.
5. Teruglezen, verversen en elke meting met `executeQueries` evalueren (`INFO.MEASURES` werkt niet via de API; haal de namen uit de TMDL).

**Afwijkingen die telkens voorkomen** (*vastgesteld*):
- Gold levert vaak `decimal` waar het oude model `double` of `int64` had; een datum die in Gold als string staat krijgt geen datumformaat meer.
- Gold heeft soms kolommen die het oude model niet had; die worden niet overgenomen.
- Een tabel die in Gold ontbreekt (`Posten`, `polisverdelingsamengesteld`) blokkeert het model of moet worden weggelaten. In beide gevallen was de tabel later wel beschikbaar en toe te voegen via `updateDefinition`.
- `dekkingvardeel` heeft in Gold 14 kolommen (oud 520). Een kolom die ontbreekt en nergens gebruikt wordt, is weggelaten.
- `clausuletekst`: Gold heet `Regelnummer` en `Regeltekst`; het model volgt Gold en de metingen zijn aangepast.

**Past niet in deze aanpak:** een composite model met DirectQuery naar een Analysis Services-model en een import uit SharePoint (`Prolongatie Reaal Participatie`). Een Direct Lake-model kan geen importtabel uit SharePoint bevatten. De Excel moet dan eerst als Gold-tabel in het Lakehouse komen (dataflow); zie `Progress.md`, P-009.

**Niet getest:** een rapport op de nieuwe modellen, en een vergelijking van waarden met de oude modellen.

## Rapport in een eigen REPORTING-workspace: koppeling over pipelines heen

*Toegevoegd 2026-10-27 (bron: klanttenant, pipelines `NL FW REPORTING` en `NL FW SEMANTIC`, D → T).*

**Situatie:** elke laag heeft een eigen deployment pipeline. Een rapport in `… REPORTING (D)` heeft een live connection met een model in `… SEMANTIC (D)`. Dat is een andere workspace en een andere pipeline. Een deployment rule voor de koppeling tussen rapport en model bestaat niet. Rules zijn er alleen voor de bron van een model.

**Wat de test liet zien** (*getest in eigen omgeving*, 2026-10-27): na promotie van het model (SEMANTIC-pipeline) en daarna van het rapport (REPORTING-pipeline) wijst het rapport in `NL FW REPORTING (T)` naar het model in `NL FW SEMANTIC (T)`. *Vastgesteld* met `GET …/groups/{ws}/reports` (`datasetId`, `datasetWorkspaceId`): rapport `Facturenoverzicht` → `SM_FACTUUR` (T). De pipeline koppelt het rapport dus zelf aan het model in dezelfde stage van de andere pipeline.

**Voorwaarden:**
- Het rapport moet in Dev al naar het model in de SEMANTIC (D)-workspace van dezelfde pipeline-structuur wijzen. Wijst het naar een model buiten de pipelines (bij de klant eerst een model in de oude workspace `NL: Group Management [Dev]`), dan heeft de pipeline geen tegenhanger om naar om te zetten. *Aanname:* dan blijft het rapport naar dat oude model wijzen; niet getest.
- Promoveer het model eerst en het rapport daarna. *Aanname*, op basis van Microsoft Learn (*autobinding across pipelines*): bestaat het model nog niet in de doelstage, dan faalt de promotie van het rapport. Niet getest.
- Controleer na de eerste promotie `datasetId` van het rapport in het doel.

**Rapport omzetten naar een ander model (in Dev):** via Power BI Desktop (*Change source*), de REST API (`POST …/groups/{ws}/reports/{id}/Rebind` met `datasetId`) of `datasetReference` in `definition.pbir` (PBIR). Bij de klant leverde *Download this file* een 404 op voor een rapport met het model in een andere workspace. *Aanname:* de oorzaak is het model in een andere workspace; niet uitgezocht. De PBIR-definitie is wel te lezen met `POST …/reports/{id}/getDefinition`.

**Niet getest:** T → P; een rapport waarvan het model niet in de doelstage staat; meerdere rapporten op één model.

## Openstaand actiepunt

De Deployment Pipeline deployment rule voor Direct Lake-pointers (portal-only, geen REST API) is een apart openstaand actiepunt — zie `01_kennisbasis/operations.md`. Voor een klantimplementatie betekent dit: dit onderdeel van de post-deployment-checklist kan **niet** volledig geautomatiseerd worden en vereist een handmatige stap in de Fabric-portal.

## Wat dit betekent voor een implementatieplan (fase 4)

Als vervolg op de shortcuts-stap uit `03_shortcuts-en-deployment.md`, na elke deployment die de SEMANTIC-workspace raakt:

1. Controleren of de Direct Lake-pointers in het semantisch model nog naar de juiste, omgevingsspecifieke Gold-Lakehouse wijzen.
2. Zo niet: handmatige pointer-swap uitvoeren (personal-workspace-route, getest) óf de Deployment Pipeline deployment rule instellen/controleren via de portal (Test/Prod-route, niet API-automatiseerbaar).
