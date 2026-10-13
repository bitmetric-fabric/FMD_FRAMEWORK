# ADR-016: Historie in Silver per tabel instelbaar

Status: Accepted
Datum: 2026-10-09

## Context

`NB_FMD_LOAD_BRONZE_SILVER` bewaart van elke Silver-tabel de volledige historie (SCD2): een wijziging in de
bron wordt een nieuwe rij, de vorige versie krijgt `IsCurrent = 0` en een `RecordEndDate`. Dat stond vast
voor alle tabellen. Bij een klant met veel bronnen en tabellen levert dat historie op waar niemand om
vraagt, en die historie leest elke run mee: het notebook leest de hele Bronze- en de hele Silver-tabel en
vergelijkt ze. Dat kost het meest bij grote tabellen, en bij tabellen die elke run wijzigen (een
`LastModified`-kolom of een teller geeft elke run een nieuwe versie van elke geraakte rij).

Bij een delete sloot het notebook de rij pas in de volgende run af: run N zette `IsDeleted = 1` en liet
`IsCurrent = 1` staan, run N+1 zette `IsCurrent = 0`. Een query op `IsCurrent = 1` zag de verwijderde rij
daardoor nog één run lang. Dat is apart opgelost, vóór deze wijziging.

## Beslissing

- **`integration.SilverLayerEntity.IsHistorized`** (BIT, oorspronkelijk standaard 1; sinds 2026-10-13
  standaard 0, zie *Herzien*). Bij 1 houdt Silver SCD2.
- Bij `IsHistorized = 0` houdt Silver dezelfde kolommen (`IsCurrent`, `IsDeleted`, `RecordStartDate`,
  `RecordEndDate`, `RecordModifiedDate`), zodat een Gold-query op `IsCurrent = 1` voor beide werkt:
  - een gewijzigde rij wordt bijgewerkt, met een nieuwe `RecordModifiedDate`; `RecordStartDate` blijft;
  - een nieuwe rij wordt toegevoegd;
  - een verwijderde bronrij wordt een soft delete in één run: `IsDeleted = 1`, `IsCurrent = 0`.
- De waarde komt uit het lijstsjabloon (`templates/registratie/registreer_entiteiten.sql`, kolom
  `IsHistorized`, leeg betekent 0 sinds 2026-10-13), net als `IsActive`. De lijst is de bron van waarheid.
- `sp_GetSilverlayerEntity` geeft de waarde als parameter aan het notebook.

## Alternatieven

- **Overal SCD2 houden.** Verworpen: de kosten schalen met het aantal tabellen, niet met de waarde van de
  historie.
- **Overal geen historie, SCD2 pas in Gold.** Verworpen: Silver is voor het FMD de persistente laag. Historie
  die je niet vastlegt, krijg je niet terug als de bron die zelf niet bewaart.
- **Hard delete bij `IsHistorized = 0`.** Verworpen: een andere betekenis van `IsDeleted` per tabel dwingt
  Gold tot vertakken.

## Gevolgen

- **Omschakelen 1 naar 0:** de bestaande historie blijft staan; alleen de huidige rij wordt bijgewerkt. Wie
  de oude versies kwijt wil, ruimt ze zelf op (`IsCurrent = 0 AND IsDeleted = 0`).
- **Omschakelen 0 naar 1:** SCD2 begint vanaf dat moment; de historie van de tussentijd is er niet.
- **Een terugkerende sleutel** (verwijderd en later weer in de bron) geeft bij beide standen een nieuwe
  huidige rij naast de gesloten, verwijderde rij.
- Dit lost niet op dat Silver elke run de hele Bronze- en Silver-tabel leest. Change Data Feed staat aan,
  maar het notebook gebruikt het niet. Alleen de wijzigingen lezen is een apart voorstel.
- Een wijziging in de configdb-tabel bereikt een omgeving pas met een nieuwe dacpac (ADR-013).

## Herzien 2026-10-13: standaard geen historie

Reden: historie die niemand vraagt kost opslag en merge-tijd, ook als het een klant met veel tabellen
treft die er nooit om vroeg. SCD2 is daarom een bewuste keuze per tabel, geen standaard.

- **`IsHistorized` is standaard 0** (kolomdefault, notebookparameter en lijstsjabloon). De rest van de
  beslissing hierboven blijft gelden: dezelfde kolommen, `IsCurrent = 1` werkt voor beide.
- **Leeg in de registratielijst betekent 0, ook voor een entiteit die eerder met 1 is geregistreerd.**
  De lijst is de bron van waarheid (`sp_RegisterEntities`, `registreer_entiteiten.sql`). Wie SCD2 wil, zet
  `IsHistorized = 1` in de lijst. Een bestaande installatie die de historie nodig heeft, moet dat vóór de
  eerstvolgende registratierun doen; de historie die al in Silver staat blijft anders wel staan, maar
  groeit niet meer.
- Een entiteit die buiten de lijst om is geregistreerd (bijvoorbeeld via `sp_UpsertLandingzoneBronzeSilver`
  of `PL_TOOLING_POST_ASQL_TO_FMD`) krijgt bij aanmaak 0. Een bestaande rij houdt zijn waarde tot de
  lijst die verandert. De dacpac zet bestaande rijen niet om.

## Test

Zie het testplan in de implementatiedocumentatie (FMD_TRIAL, trial-Dev).
