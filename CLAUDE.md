# FMD Framework: werkafspraken voor Claude

@.github/copilot-instructions.md

Architectuur en repo-layout staan in `copilot-instructions.md` hierboven. Beslissingen staan in `docs/adr/`.
Dit bestand bevat alleen wat je niet uit de code haalt.

## Bestanden bewerken
- De blobs zijn LF; een Windows-checkout is CRLF. Schrijf LF terug, anders is de hele file gewijzigd.
- `setup/*.ipynb` is JSON: bewerk cellen via een JSON-parser, niet als platte tekst.
- De generieke laag bevat geen klantcode (ADR-003). Klantaanpassingen horen in de klant-fork.

## SQL en dacpac
- De dacpac is het enige dat wordt uitgerold. Een `.sql`-wijziging onder `src/Config_Database/` bereikt niemand zonder een nieuwe dacpac, en de dacpac-guard faalt dan.
- Bouwen: `dotnet build src/Config_Database/SQL_FMD_FRAMEWORK.sqlproj -c Release`, en daarna `bin/Release/SQL_FMD_FRAMEWORK.dacpac` kopiëren naar `src/SQL_FMD_FRAMEWORK.SQLDatabase/`.
- Op Windows: bouw in Docker (`mcr.microsoft.com/dotnet/sdk:8.0`) vanuit een LF-checkout. Een CRLF-checkout geeft een ander `model.xml`.

## Verwijzingen tussen items
- Geen letterlijke workspace- of item-GUID's: gebruik de Variable Libraries (ADR-009, ADR-010). De guid-guard controleert dat; uitzonderingen staan met reden in `config/guid_allowlist.txt`.
- Een promotie overschrijft de defaults van een library, maar laat de actieve value set staan. Omgevingswaarden horen daarom in de value sets, niet in de defaults.
- Een Direct Lake-model wordt bij een promotie niet opnieuw gekoppeld. De default lakehouse van een notebook wordt dat wel. Een Invoke Pipeline naar een item dat in dezelfde deployment pipeline gekoppeld is, werd in de tests ook omgezet; dat is niet als garantie bevestigd.

## Testen tegen Fabric
- Configdb: `sqlcmd -S <server> -d <database> --authentication-method ActiveDirectoryAzCli`.
- Tel via een SQL-endpoint pas na `POST …/sqlEndpoints/{id}/refreshMetadata`, anders zie je oude metadata.
- Items lezen en patchen: `getDefinition` / `updateDefinition` (LRO: 200 of 202 met `Location`).
- Jobs: `POST …/items/{id}/jobs/instances?jobType=Pipeline|RunNotebook`, daarna pollen op `Location`.

## Bekende valkuilen
- Fabric geeft een lege pipelineparameter aan een stored procedure door als `NULL`, niet als `''`. Filter met `ISNULL(@p, '') = ''`.
- Een pipelineparameter met een default van een specifieke omgeving blijft na promotie naar die omgeving wijzen. Laat de default leeg en val terug op `libraryVariables`.
- De `fab` CLI meldt fouten met exit code 1 en de melding op stdout. Stderr bevat ook onschuldige waarschuwingen, en `set` met een onbekende property geeft toch exit code 0.
- Een retry in `runMultiple` (`NB_FMD_PROCESSING_PARALLEL_MAIN`) verbergt een eerste fout, omdat de tweede poging slaagt. Laat `retry` op 0.
