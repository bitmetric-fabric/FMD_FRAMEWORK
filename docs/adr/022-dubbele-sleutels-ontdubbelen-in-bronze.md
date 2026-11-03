# ADR-022: dubbele sleutels ontdubbelen in Bronze

Status: Proposed
Datum: 2026-11-03

## Context

- `NB_FMD_LOAD_LANDING_BRONZE` laat de load van een tabel falen zodra twee rijen in een landingbestand dezelfde
  `HashedPKColumn` hebben (`Source file contains duplicated rows for PK`). ADR-016 noemde dit als niet opgelost voor
  meerdere events per sleutel in één batch.
- Tot nu toe is elke melding per tabel opgelost met een langere primary key of een `SourceFilter`. Dat werkt niet als
  de bron rijen levert die alleen in een filler of in wijzigende bedrijfsvelden verschillen. Bij een klant
  (2026-11-03, `AGENDA`, 5,89 miljoen rijen) waren 51 sleutels dubbel. 4 paren verschilden alleen in `X_FILLER_1`
  (spaties tegenover leeg), en 46 paren alleen in `MEDEWERKER`, `DATUM_TIJD` en `UITGEVOERD`.

## Beslissing

- **Een ingebouwde cleansing-regel `deduplicate_keys`** in `NB_FMD_DQ_CLEANSING`, ingesteld als Bronze-regel in
  `BronzeLayerEntity.CleansingRules`:
  `{"function": "deduplicate_keys", "columns": "EVENT_TIMESTAMP", "parameters": {"keep": "last"}}`. De regel houdt per
  `HashedPKColumn` één rij.
- **Volgorde:** de kolommen in `columns`. Bij `keep = last` (standaard) wint de hoogste waarde, bij `first` de laagste.
  `NULL` telt als laagste waarde.
- **Gelijke volgorde:** daarna beslist een md5 van alle waarden van de rij. Een dump heeft één `EVENT_TIMESTAMP`;
  zonder deze tie-break is de winnaar willekeurig, en kan een herbouw een andere rij houden.
- **Alleen de dubbele sleutels gaan door het window.** De rest van de tabel gaat via een `left_anti`-join langs. Zonder
  dubbelen geeft de regel de DataFrame ongewijzigd terug.
- **De duplicaatcontrole staat na de cleansing**, niet ervoor. Een Bronze-regel kan een dubbele sleutel dan oplossen.
- **Geen limiet.** Het aantal weggevallen rijen en sleutels gaat naar de notebook-output en als `RowsDeduplicated` en
  `KeysDeduplicated` in `CopyOutput` van de `EndNotebookActivity`.
- **Alleen notebooks.** `sp_RegisterEntities` kent de functie niet; de dry run meldt hem als "not built in"
  (waarschuwing). De editor kent hem wel (`CLEANSING_FUNCTIONS`).

## Alternatieven

- **De primary key verlengen tot de rijen uniek zijn.** Blijft de eerste keus als er een stabiele kolom is (`VOLGORDE`
  bij `VERDSCH`). Verworpen als algemene oplossing: een wijzigend veld in de key maakt bij elke wijziging een nieuwe
  Bronze-rij en laat de oude staan, en rijen die alleen in een filler verschillen blijven dubbel.
- **Een kolom op `BronzeLayerEntity` (bijvoorbeeld `DuplicateKeyAction`).** Verworpen voor nu: dat vraagt een dacpac,
  de registratie, de views en de editor, voor iets wat de bestaande regelkolom al per tabel draagt.
- **`dropDuplicates`.** Verworpen: welke rij overblijft is niet bepaald.
- **Een limiet op het aantal weggevallen rijen.** Bewust niet gekozen: alleen loggen.

## Gevolgen

- **Een te korte primary key gooit stil rijen weg.** Alleen `RowsDeduplicated` in de log laat het zien. Zet de regel
  alleen op een tabel waarvan de dubbelen bekend en verklaard zijn.
- **Weggevallen rijen komen niet in Bronze of Silver.** Bij een paar dat echt verschilt, verdwijnt de ene versie.
- **Een fout bij een dubbele sleutel komt later in de run**, na de cleansing, en een Bronze-regel `exclude_rows` kan
  rijen weghalen voordat de controle ze als dubbel telt. Zonder zo'n regel verandert er niets.
- **Incrementeel:** de regel werkt binnen één landingbestand. Tussen batches doet de merge wat hij al deed.
- **`RowsDeduplicated` staat niet in `logging.vw_ExecutionSummary`.** Lees `LogData` in `logging.NotebookExecution`.
- **Open:** `sp_RegisterEntities` laten weten dat de functie ingebouwd is (dacpac), en de kolom in
  `vw_ExecutionSummary`.
- **Getest op 2026-11-03:** lokaal met pyspark 3.5.1 in Docker (`scripts/test_deduplicate_keys.py`): validatie, een
  dump-paar dat alleen in een filler verschilt, een paar dat in een bedrijfsveld verschilt, twee events voor één sleutel
  met `last` en `first`, `NULL` in de volgordekolom, een gelijke winnaar bij een andere invoervolgorde, en geen
  dubbelen.
- **Getest in FMD_TRIAL, D, 2026-11-03** (`TPCH.NATION` met PK `N_REGIONKEY`, dus 20 dubbele rijen; testplan T-D17):
  zonder regel faalt Bronze nog (run `f57940b1`); met regel en `N_NATIONKEY` als volgorde 5 rijen met per regio de hoogste
  sleutel, `RowsDeduplicated` 20 en `KeysDeduplicated` 5 (eerste load `0da74d8c`); Silver slaagt (`8b66b342`); hetzelfde
  bestand nog eens via de merge geeft 0 wijzigingen (`00aff5db`); een tabel zonder regel loopt ongewijzigd door
  (`TPCH.CUSTOMER`, `b6ad2371`). **Niet getest:** `keep = first` in Fabric, een incrementele tabel met meerdere events per
  sleutel, een grote tabel, en de klantomgeving.
