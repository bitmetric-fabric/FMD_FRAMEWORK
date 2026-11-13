# Handleidingen

Stap-voor-stap handleidingen voor wie een FMD-installatie beheert. Ze zijn generiek: geen gegevens van een specifieke klant of omgeving. Dat past bij de scheiding tussen de generieke laag en klantaanpassingen. Documentatie van een installatie hoort in de omgeving van die installatie.

| Handleiding | Inhoud |
|---|---|
| [Een tabel of bron handmatig laden](handmatig-laden.md) | `PL_FMD_LOAD_ALL` met `DataSourceName` en `Entities` starten, de run volgen, controleren en annuleren. Met schermafbeeldingen. |
| [Dagelijkse routine en schedules](dagelijkse-routine.md) | De keten van een geplande run, de dagelijkse en wekelijkse controle, een schedule wijzigen, meldingen en maintenance plannen. |
| [Een Direct Lake-model laten verwijzen naar het juiste lakehouse na promotie](direct-lake-parameter.md) | Een parameter toevoegen aan een Direct Lake-model op OneLake in de TMDL view, het schema bijwerken, promoveren met een parameter rule en controleren. Met schermafbeeldingen. |
| [Een run beoordelen en een fout herstellen](run-beoordelen.md) | De run in de Monitor bekijken, de falende tabel vinden, de soort fout bepalen en herstellen (opnieuw starten, bestand overslaan, watermark resetten, Silver opnieuw verwerken). |
| [Bronnen en tabellen registreren](registreren.md) | De registratie-editor in `NB_REGISTRATIE`: een bron kiezen, tabellen laden, een tabel selecteren en instellen (primary key, watermark, bronfilter, kolommen), controleren, proefdraaien en registreren. Met schermafbeeldingen. |
| [Registratie overzetten en beheren](overzetten-en-beheren.md) | Omgevingen vergelijken, de registratie van D naar T en P overzetten, de laadstatus bekijken, een watermark resetten, de wachtrij opruimen en een tabel opruimen na een PK-wijziging. Met schermafbeeldingen. |
| [Promoveren van Dev naar Test en Productie](promoveren.md) | De volgorde van een promotie, een promotie uitvoeren in de deployment pipeline (verschillen bekijken, deployen, geschiedenis), de controles na de promotie en herstel. Met schermafbeeldingen. |
| [Veelvoorkomende meldingen](veelvoorkomende-meldingen.md) | Naslag per melding: wat hij betekent en wat je doet, voor een run, een geplande run, een promotie, een semantisch model en de registratie. |

De interne documentatie van Bitmetric (kennisbasis, beslisregister, technische documentatie) staat in [`../intern/`](../intern/01_kennisbasis/index.md).

## Afspraken voor deze map

- **Platte Markdown**, in het Nederlands. De map is geen onderdeel van de Docusaurus-site in `docs/`.
- **Geen klantgegevens, geen ID's.** Geen GUID's, workspacenamen of bronnamen van een klant, en geen persoonsgegevens in schermafbeeldingen. De pagina's zijn zo geschreven dat ze zonder aanpassing in een klantdocument kunnen worden opgenomen: geen verwijzingen naar interne ADR's, interne testplannen of andere pagina's buiten deze map.
- **Geen statuslabels of bronverwijzingen in de tekst.** Schrijf alleen wat klopt. Wat niet is getest of nog niet is vastgelegd, staat niet in de handleiding maar in de interne documentatie. Formuleer een onzekere bewering voorzichtig ("naar verwachting", "mogelijk") of laat hem weg.
- **Schermafbeeldingen.** PNG, uitgesneden op het relevante deel van het scherm, zonder adresbalk (daar staan GUID's in), maximaal 1,5 MB, met een alt-tekst. Namen, profielfoto's, e-mailadressen en ID's zijn afgedekt met een Gaussian blur met straal 8. Dat maakt ze onleesbaar voor het oog, maar beschermt niet tegen iemand met een lijst kandidaten (getest op hex-ID's); toon daarom nooit secrets of tokens in beeld. Bewaar ze in `afbeeldingen/<handleiding>/`, genummerd per stap. Maak ze met een opname die elke klik en een schermafbeelding per stap vastlegt, en controleer elke afbeelding voordat je hem opneemt.
- **Veroudering.** De portal verandert. Noem in een handleiding de maand van de opnames en controleer ze na een grote wijziging van Fabric.
