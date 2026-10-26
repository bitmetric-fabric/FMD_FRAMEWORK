# ADR-020: LoadGroup, kolommen en bronfilter per tabel

Status: Proposed
Datum: 2026-10-20

## Context

- **LoadGroup** stond alleen op `integration.DataSource`: één groep per bron. Een deel van een bron laden kon alleen
  met de pipelineparameters `DataSourceName` en `Entities`, en dan moest elke schedule de tabellen opsommen.
- De kopie-query was altijd `SELECT * FROM <tabel>`, met hooguit de watermark-`WHERE`. Een deel van de kolommen of
  van de rijen laden vroeg een view in de bron.
- `LandingzoneEntity.SourceCustomSelect` bestaat, maar geen view leest hem (`07_extension-points.md` §3), en
  `sp_RegisterEntities` schrijft er altijd `''` in.
- `HistoryDays` is een startwatermark op de bron, alleen voor een nieuwe incrementele tabel.

## Beslissing

- Drie kolommen op `integration.LandingzoneEntity`, alle drie NULL: `LoadGroup`, `SourceColumns` en `SourceFilter`.
- **LoadGroup per tabel.** De groep waarin een tabel laadt is die van de tabel, en anders die van de bron:
  `COALESCE(NULLIF(LZE.[LoadGroup], ''), DS.[LoadGroup])` in `vw_LoadSourceToLandingzone`, `vw_LoadToBronzeLayer` en
  `vw_LoadToSilverLayer`. De pipelines en de getters (`sp_GetBronzelayerEntity`, `sp_GetSilverlayerEntity`) filteren
  via die views en veranderen niet. Een lege `LoadGroup` bij de run blijft "geen filter".
- **Kolommen en filter per tabel.** `SourceColumns` is een kommalijst, in de volgorde waarin de kolommen
  geladen worden; leeg betekent alle kolommen. `SourceFilter` is een predicaat zonder `WHERE`.
  `vw_LoadSourceToLandingzone` bouwt `SELECT <kolommen of *> FROM <tabel> WHERE <watermark> AND (<filter>)`. De
  watermarkquery (`LastLoadValue`) krijgt hetzelfde filter, zodat de watermark over dezelfde rijen gaat.
- **Alleen ASQL_01, ASQL_02 en SNOWFLAKE_01.** Alleen de pipelines van die types voeren `SourceDataRetrieval` uit met
  een watermarkquery. `sp_RegisterEntities` en de editor weigeren kolommen en filter bij een ander type.
  SQLMI_01 valt af: zijn `LastLoadValue` in de view is de opgeslagen waarde, geen query.
- **Controles in `sp_RegisterEntities`** (de editor doet dezelfde vooraf): de primary key en de watermarkkolom staan in
  `SourceColumns`; de kolommen bestaan in de ontdekking (Snowflake hoofdlettergevoelig); een filter bevat geen `;`;
  een `LoadGroup` is hoogstens 50 tekens.
- **De lijst is de waarheid**, zoals bij `IsActive` (ADR-016): een tabel zonder deze velden in de lijst krijgt ze leeg.
- **`HistoryDays` blijft** een startwatermark per bron. "Alleen de laatste N dagen" schrijf je als filter.
- **`SourceCustomSelect` blijft ongebruikt.**

## Alternatieven

- **`SourceCustomSelect` als FROM-doel** (lokale branch `fix/sourcecustomselect-filter`, niet gepusht). Verworpen:
  een volledige `SELECT` geeft ongeldige SQL, de editor kan een vrije query niet controleren (een primary key of
  watermarkkolom die ontbreekt, valt pas bij de load op), en elke registratie wist de waarde.
- **`HistoryDays` als rollend venster bij elke load.** Verworpen: een filter per brontype, ook voor volledige
  loads. Het filter dekt dit al.
- **Alleen een view in de bron.** Blijft de weg voor joins en bronspecifieke SQL, maar vraagt rechten en wijzigingen
  in de bron voor elke selectie.

## Gevolgen

- **Een filter is vrije SQL op de bron**, met de rechten van de connectie. De registratie weigert alleen `;`; wie
  registreert wordt vertrouwd, zoals bij een view in de bron. De dry run voert het predicaat niet uit en meldt dat.
- **Een filter wijzigen verwijdert niets** in Bronze en Silver. Sluit het nieuwe filter oudere rijen in die eerder
  buiten beeld waren, dan laadt een incrementele tabel die niet alsnog: de watermark staat er al voorbij. Zet de
  watermark terug of laad volledig.
- **Een tijdvenster in het filter** (`OrderDate >= DATEADD(day, -30, GETDATE())`) laat rijen die eruit schuiven in
  Bronze en Silver staan.
- **Kolommen weghalen bij een tabel die al in Bronze staat laat de Bronze-merge falen**
  (`DELTA_MERGE_UNRESOLVED_EXPRESSION: Cannot resolve N_COMMENT in UPDATE clause`, getest in FMD_TRIAL op
  2026-10-20 met `TPCH.NATION`). De Bronze-tabel heeft de kolom nog, het landingbestand niet meer. Verwijder eerst de
  Bronze- en Silver-tabel, of begin met de kolomkeuze vóór de eerste load; dan gaat het goed (getest met een nieuwe
  tabel in DEV). Kolommen **erbij** is niet getest. De run faalt, en de wachtrijrij van het landingbestand blijft
  open staan: sluit hem, anders pakt de volgende Bronze-run dat bestand met de verkeerde kolomset alsnog op.
- **Snowflake:** kolomnamen in het filter volgen de Snowflake-regels; zonder aanhalingstekens zijn het hoofdletters.
- **Een tabel in een andere groep dan haar bron** wordt niet geladen door een run voor de groep van de bron.
- **Getest op 2026-10-20:**
  - op SQL Server 2022 in Docker: views en procedure, 18 gevallen, waaronder de eerste load van een incrementele tabel;
  - met `scripts/test_registration_editor.py` en de echte editor met ipywidgets 8.1.9 (editorlogica, `ColumnPicker`);
  - in FMD_TRIAL, Fabric SQL database: de dacpac, de registratie en de views;
  - in FMD_TRIAL, DEV, ASQL_01 (nieuwe tabellen): `PL_FMD_LOAD_ALL` met groep `tst_a` en `tst_b` laadt alleen de tabellen
    van die groep; kolomkeuze, filter, een incrementele tabel met filter en watermark, en Bronze en Silver kloppen;
  - in FMD_TRIAL, D, SNOWFLAKE_01 (`TPCH.NATION`): Landing slaagt met kolommen en filter, Bronze faalt (zie boven).
  - **Niet getest:** kolommen erbij, Snowflake met een nieuwe tabel door Bronze en Silver, een promotie naar T of P, en de
    editor in de Fabric-frontend.

## Aanvulling 2026-10-26: een cast per kolom (Snowflake)

**Reden.** Een Snowflake-tabel met een `TIME`-kolom laadt niet: de Copy-activiteit naar de Delta-landing faalt met
`DeltaNotSupportedInterimDataType`, omdat Delta geen `TIME` kent. Bij een klanttabel zat die kolom in de key, dus weglaten
kon niet, en een view in de bron vraagt een object in de omgeving van de klant.

**Beslissing.** Bij `SNOWFLAKE_01` mag een item in `SourceColumns` de vorm `naam::TYPE` hebben. De view maakt er
`"naam"::TYPE AS "naam"` van, zodat de kolomnaam gelijk blijft: de key, de cleansing-regels en Bronze en Silver merken niets.
`TIJD::VARCHAR` geeft `HH24:MI:SS` als tekst.

- `TYPE` bestaat alleen uit letters, cijfers en `_`. Geen `(n)` of `(p,s)`: de komma scheidt kolommen, en het type komt in de query.
  Een cast met iets anders achter `::` weigert `sp_RegisterEntities`. De view laat zo'n tekst, als hij toch in de tabel staat,
  deel van de naam blijven, zodat Snowflake de kolom afwijst in plaats van de tekst uit te voeren.
- Alleen `SNOWFLAKE_01`; bij ASQL_01 en ASQL_02 een fout.
- De controles (key in de lijst, watermark in de lijst, kolom in de ontdekking) vergelijken de naam voor `::`.
- Geen cast op de watermarkkolom: de watermarkquery leest de kolom zoals hij is. Die kolom is `DATE` of `TIMESTAMP`, en Delta kent die.
- De dry run meldt een ontdekte `TIME`-kolom die zonder cast geladen wordt: als fout bij een `delta`-landing, als waarschuwing bij
  `parquet` (daar is `TIME` niet getest).
- De editor haalt de cast bij het laden van een tabel van de kolomkeuze en zet hem bij het opslaan terug, zodat hij niet verdwijnt.
  Een cast voeg je toe in de registratielijst.

**Gevolgen.**
- Een kolom met `::` in de naam kan niet meer gekozen worden. Niet verwacht in Snowflake-bronnen; niet gecontroleerd.
- `TIME::VARCHAR` volgt `TIME_OUTPUT_FORMAT` van de Snowflake-sessie en laat standaard de fracties weg. Staat `TIME` in de key
  met fracties van een seconde, dan kan de key na de cast dubbel zijn. Controleer dat vooraf in de bron.
- Een cast toevoegen of wijzigen bij een tabel die al in Bronze staat verandert het kolomtype in het landingbestand. Of de
  Bronze-merge dat aankan is niet getest.
- **Getest op 2026-10-26:**
  - lokaal, op SQL Server 2022 in Docker: de registratie en de view (10 gevallen), en de editor en dry run met `scripts/test_registration_editor.py`;
  - in FMD_TRIAL, D, SNOWFLAKE_01, met een testtabel `FMD_BRON.TSTTIME.WERKLYST_TEST` (`ID NUMBER`, `TIJD TIME`, key `ID,TIJD`, vier rijen):
    zonder cast faalt de landing met `DeltaNotSupportedInterimDataType` (`interim data type TimeSpan`, kolom `TIJD`, run `bbd8091b`);
    met `TIJD::VARCHAR` slagen Landing, Bronze en Silver (run `7d51748b`): vier rijen met vier unieke keys, `TIJD` als `varchar`
    (`08:00:00`, `13:30:15`, `08:00:00`, `23:59:59`);
  - een cast samen met `SourceFilter = TIJD > '9:00:00'` (run `269cb88d`): de landing leest twee rijen. Snowflake vergelijkt in de
    `WHERE` dus de `TIME`-kolom en niet de alias (een tekstvergelijking had nul rijen gegeven).
  - **Niet getest:** `parquet` met `TIME`, een cast bij een tabel die al in Bronze staat, een `TIME`-kolom met fracties van een
    seconde, de editor in de Fabric-frontend.
