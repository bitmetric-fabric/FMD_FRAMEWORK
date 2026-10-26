# ADR-021: OData als brontype

Status: Proposed
Datum: 2026-10-26

## Context

Een klant laadt een OData-bron (AFAS) met een losse Fabric Copy Job. Die entiteiten staan buiten de configdb:
geen LoadGroup, geen audit in `logging`, geen watermark in `execution.LandingzoneEntityLastLoadValue` en geen
Bronze- en Silver-laag via het framework. Het FMD kent geen OData-, REST- of HTTP-bron.

De bestaande Copy Job (`CopyJob_AFAS_GebruikersAutorisatie`, gelezen 2026-10-26) gebruikt de OData-connector van Fabric,
geen REST: bron `ODataResource` met connectietype `OData`. De authenticatie zit dus in de Fabric-connectie. `path` is
de naam van de AFAS-connector (`Gebruikersautorisaties`), zonder query. Het is een volledige load met `Overwrite` naar
een lakehousetabel, zonder watermark. Dat de entiteiten in AFAS een sleutel hebben, staat er niet in.

Een Copy Job past niet in het FMD. Bron, entiteiten en incrementele kolom staan dan in het Copy Job-item, terwijl het
FMD die per entiteit uit de configdb leest. De entiteiten zouden op twee plekken worden beheerd.

## Beslissing

`OData` wordt een brontype naast ASQL en Snowflake, met een eigen pipelinepaar naar het voorbeeld van ASQL:
`PL_FMD_LDZ_COMMAND_ODATA` en `PL_FMD_LDZ_COPY_FROM_ODATA_01`.

- **Connectie en bron.** `Connection.Type = 'ODATA'`, `DataSource.Type = 'ODATA_01'`. De basis-URL en de
  authenticatie staan in de Fabric-connectie (`@item().ConnectionGuid`), niet in de configdb.
- **Entiteit.** `SourceName` is het pad achter de basis-URL: de entity set, of bij AFAS de connector.
  `SourceSchema` is een vrij label zonder betekenis voor de bron; het wordt het doelschema in Bronze en Silver.
- **Kopie.** `ODataSource` met `query = SourceDataRetrieval`, naar parquet in `LH_DATA_LANDINGZONE`, zoals bij elke bron.
  `vw_LoadSourceToLandingzone` bouwt de query: `$select=<SourceColumns>&$filter=<incrementeel> and (<SourceFilter>)`.
  Leeg betekent de hele entiteit.
- **Watermark.** Een kolom is in OData niet te hernoemen. `LastLoadValue` is daarom een query die de watermarkkolom
  zelf selecteert (`$select=<kolom>&$orderby=<kolom> desc&$top=1`, met hetzelfde filter). De pipeline leest die kolom
  op naam. Bij een volledige load neemt de pipeline de laadtijd (UTC) als watermark.
- **`ge` in plaats van `gt`.** De volgende run begint op de opgeslagen waarde. Een rij die precies op dat moment
  wijzigt, zou met `gt` blijven liggen. De dubbele rij is onschuldig: Bronze en Silver mergen op de `PrimaryKeys`.
- **Veiligheid van de URL.** De watermarkwaarde komt uit de bron en staat zonder aanhalingstekens in de URL. De view
  neemt hem alleen mee als hij uit de tekens van een ISO-datum of getal bestaat (`0-9 T Z : . + -`).
- **Registratie.** `('ODATA', 'ODATA_01')` staat in de lijst van `sp_RegisterEntities` en in de registratie-editor.
  `SourceColumns` en `SourceFilter` zijn toegestaan voor `ODATA_01`.
- **Deletes.** Een incrementele load ziet geen verwijdering, tenzij de bron die als rij met een vlag levert. Dan is
  `exclude_rows` (ADR-020 en `02_configdb-registratie.md`) de oplossing. Anders is een periodieke volledige load de
  enige manier: Silver sluit een rij af waarvan de sleutel ontbreekt (`df_deletes`).
- **Geen AFAS-code.** Alles hierboven is generiek OData. Een AFAS-specifieke aanpassing hoort in de klant-fork (ADR-003).

## Getest

Getest in FMD_TRIAL op 2026-10-26, in `DEV_MITCHELL_TRIAL_INTEGRATION_CODE`, tegen de publieke Northwind OData V4
(connectie `CON_FMD_ODATA_TEST`, anoniem; entity sets `Orders` en `Customers`):

- De `ODataSource`/`ODataResource`-JSON wordt geaccepteerd en onveranderd teruggelezen. Een Lookup geeft `firstRow` als
  object met de kolomnamen terug, en `firstRow['OrderDate']` werkt als indexer.
- De copy volgt `@odata.nextLink` (830 rijen in vijf pagina's van 200). `$orderby … desc` en `$filter … ge …` werken.
- De keten loopt: `PL_FMD_LOAD_LANDINGZONE` (de Switch stuurt naar `PL_FMD_LDZ_COMMAND_ODATA`), Bronze en Silver, met een
  eerste volledige run (`Orders` 830 en `Customers` 91 rijen, in Bronze en Silver unieke sleutels) en een tweede run
  waarin `Orders` incrementeel 4 rijen las en `Customers` opnieuw 91. Er kwamen geen dubbele rijen bij. De types blijven
  behouden (`int`, `datetime2`, `decimal`), en `SourceColumns` leverde precies de gekozen kolommen.
- De pipeline slaat het watermark op als `1998-05-06T00:00:00+00:00`, niet als `…Z`. Een kale `+` in de URL leest de
  bron als spatie en geeft een fout (`The DateTimeOffset text … should be in format …`). Daarom schrijft de view `+`
  als `%2B`. Met `%2B` geeft de bron de verwachte rijen.

## Niet getest

- AFAS zelf: `$orderby` en `ge` op een AFAS-datumkolom, het formaat van het watermark daar, de sleutel per connector, en
  of AFAS `@odata.nextLink` levert. Het connectietype `OData` ondersteunt `Anonymous`, `Basic`, `Key` en `OAuth2`; welk
  type de AFAS-connectie gebruikt, is niet nagegaan (de Copy Job van de klant noemt alleen het connectietype).
- Een wijziging in de bron tussen twee runs: Northwind is statisch, dus de tweede run toont alleen dat de incrementele
  query en de merge geen dubbele rijen geven, niet dat een gewijzigde rij wordt bijgewerkt.
- Een lege bron (de fout bij de eerste incrementele run, zie Gevolgen).
- De Fabric-pipelines zijn in de trial uitgerold in een oudere dev-workspace (`PL_FMD_LOAD_LANDINGZONE` met alleen de
  `ODATA`-case erbij), niet via de setup-notebooks vanaf `main`.

## Gevolgen

- *Aanname, niet getest:* een lege bron geeft een fout bij de eerste incrementele run, omdat de watermark-lookup dan geen rij geeft.
- De copy-activiteit heeft een timeout van 1 uur, zoals de andere brontypen.
- `SourceFilter` komt letterlijk in de URL. Een `&`, `#` of `%` erin moet al gecodeerd zijn.
- Er is geen discovery voor OData (`PL_FMD_DISCOVER_SOURCE`). Registratie werkt ook zonder.
- Een bron met een eigen connector (SAP, Dataverse) hoort daar een eigen brontype voor te krijgen, niet hierbij.
