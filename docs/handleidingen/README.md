# Handleidingen

Stap-voor-stap handleidingen voor wie een FMD-installatie beheert. Ze zijn generiek: geen gegevens van een specifieke klant of omgeving. Dat past bij de scheiding tussen de generieke laag en klantaanpassingen. Documentatie van een installatie hoort in de omgeving van die installatie.

| Handleiding | Inhoud |
|---|---|
| [Een tabel of bron handmatig laden](handmatig-laden.md) | `PL_FMD_LOAD_ALL` met `DataSourceName` en `Entities` starten, de run volgen, controleren en annuleren. Met schermafbeeldingen. |
| [Dagelijkse routine en schedules](dagelijkse-routine.md) | De keten van een geplande run, de dagelijkse en wekelijkse controle, een schedule wijzigen, meldingen en maintenance plannen. |

De interne documentatie van Bitmetric (kennisbasis, beslisregister, technische documentatie) staat in [`../intern/`](../intern/01_kennisbasis/index.md).

## Afspraken voor deze map

- **Platte Markdown**, in het Nederlands. De map is geen onderdeel van de Docusaurus-site in `docs/`.
- **Geen klantgegevens, geen ID's.** Geen GUID's, workspacenamen of bronnamen van een klant, en geen persoonsgegevens in schermafbeeldingen. De pagina's zijn zo geschreven dat ze zonder aanpassing in een klantdocument kunnen worden opgenomen: geen verwijzingen naar interne ADR's, interne testplannen of andere pagina's buiten deze map.
- **Statuslabels.** Elke bewering die niet uit de code of definitie is gelezen, krijgt het label *getest in eigen omgeving* (met datum) of *aanname*.
- **Schermafbeeldingen.** PNG, uitgesneden op het relevante deel van het scherm, zonder adresbalk (daar staan GUID's in), maximaal 1,5 MB, met een alt-tekst. Namen, profielfoto's en ID's zijn afgedekt met zwarte vlakken, niet vervaagd. Bewaar ze in `afbeeldingen/<handleiding>/`, genummerd per stap. Maak ze met een opname die elke klik en een schermafbeelding per stap vastlegt, en controleer elke afbeelding voordat je hem opneemt.
- **Veroudering.** De portal verandert. Noem in een handleiding de maand van de opnames en controleer ze na een grote wijziging van Fabric.
