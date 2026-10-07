# ADR-015: Opslagbeheer: landing zone opruimen op de wachtrij, wekelijks VACUUM

Status: Accepted
Datum: 2026-10-07

## Context

Het FMD ruimt geen opslag op. Elke run legt per entiteit een levering neer in de landing zone, en die
blijft voor altijd staan; een volledige load legt elke run een complete kopie neer. In Bronze en Silver
schrijft elke merge nieuwe Delta-bestanden, en de oude blijven staan tot er een `VACUUM` draait. Het
framework zet alleen `autoCompact` aan. Bij een klant met veel data groeien beide zonder grens, en de
landing zone bewaart ruwe (persoons)gegevens zonder einddatum.

Fabric biedt zelf: een OneLake lifecycle policy (alleen verplaatsen naar cool/cold, niet verwijderen),
table maintenance per tabel (`VACUUM` minimaal 7 dagen), en de Delete-activiteit (op leeftijd).

## Beslissing

- **`NB_FMD_MAINTENANCE`**, gestart door **`PL_FMD_MAINTENANCE`** met een eigen schema, los van de loads.
- **Landing zone:** een levering gaat weg als Bronze hem heeft verwerkt (`IsProcessed = 1`) en
  `LoadEndDateTime` ouder is dan `VAR_FMD.landingzone_retention_days` (standaard 30). Een levering die
  ook als onverwerkt in de wachtrij staat, blijft. `execution.sp_GetMaintenanceTargets` levert de lijst
  en weigert een termijn kleiner dan 1.
- **`VACUUM`** op alle Bronze- en Silver-tabellen van de DATA-workspace, met 168 uur (het minimum van Delta).
- Het verwijderen wordt gelogd in de uitvoer van het notebook, niet in de wachtrij.

## Alternatieven

- **Opruimen op leeftijd (Delete-activiteit).** Verworpen: dat verwijdert ook een onverwerkte levering
  van een entiteit die al dagen faalt. Bij een incrementele entiteit is die data dan weg, want de
  watermark is al opgeschoven.
- **Table maintenance via de REST API.** Verworpen: één aanroep per tabel; het notebook leest de tabellen
  al uit de configdb.
- **Lifecycle policy.** Geen alternatief voor opruimen; wel een optie per klant om de landing zone langer
  en goedkoper te bewaren (cool na 30 dagen).
- **Een kolom "verwijderd" in de wachtrij.** Niet nu: elke run controleert de oude leveringen opnieuw
  met `fs.exists`. Pas als dat traag wordt.

## Gevolgen

- **Time travel** in Bronze en Silver gaat maximaal 7 dagen terug. De historie in Silver zit in de rijen
  (SCD2) en blijft.
- **Herverwerken** van een levering kan alleen binnen de bewaartermijn; daarna opnieuw laden uit de bron.
- Het schema van `PL_FMD_MAINTENANCE` richt de klant in per omgeving (draaiboek). Zonder schema groeit
  de opslag zoals voorheen.
- GUID's in een OneLake-pad voor Delta moeten kleine letters zijn; pyodbc geeft hoofdletters. De
  procedure zet ze om.

## Test

FMD_TRIAL trial-Dev, 2026-10-07: een verwerkte levering van 40 dagen werd verwijderd, een onverwerkte van
40 dagen bleef, een nieuwe bleef (runs `adf2f335`, `e82020d9`). `VACUUM` op 24 tabellen zonder fouten.
Een fout (hoofdletter-GUID's, eerste run) liet de pipeline zichtbaar falen met de lijst van fouten.
