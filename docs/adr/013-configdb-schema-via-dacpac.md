# ADR-013: Schema van de configuratiedatabase via de dacpac

Status: Accepted
Datum: 2026-10-05
Vervangt: ADR-004

## Context

ADR-004 koos genummerde, idempotente migratiescripts onder `/metadata/migrations/`.
Die zijn nooit gebouwd. In de praktijk loopt het schema van `SQL_FMD_FRAMEWORK` al
via de dacpac:

- de bronnen staan in `src/Config_Database/` (een SQL-project), en
  `src/SQL_FMD_FRAMEWORK.SQLDatabase/` bevat alleen de gebouwde dacpac;
- `NB_SETUP_FMD` rolt die uit met `fab import` van het SQLDatabase-item, ook op een
  bestaande database (de setup als update);
- de dacpac-guard in CI faalt als de dacpac niet overeenkomt met de bronnen.

Zo zijn wijzigingen al uitgerold op een gevulde configdb, zonder dat registraties
verloren gingen (FMD_TRIAL, PR #16 en de setup als update, 2026-09-26 en 09-28).

## Beslissing

Het schema van de configdb wordt beheerd als SQL-project en uitgerold als dacpac.
Er komen geen losse migratiescripts.

- Een schemawijziging is een wijziging in `src/Config_Database/` plus een nieuw
  gebouwde dacpac in dezelfde PR (de guard dwingt dat af).
- Een klant krijgt de wijziging door de setup opnieuw te draaien, of door de dacpac
  in Dev uit te rollen en daarna te promoveren.
- **Vooraf een back-up of export** van de configdb bij elke wijziging die bestaande
  kolommen of tabellen raakt.
- Een wijziging die data moet omzetten (een kolom splitsen, waarden herschrijven),
  krijgt een eenmalig, idempotent script naast de dacpac, met de PR erbij. Dat is
  de uitzondering, geen migratieketen.

## Alternatieven

- **Migratiescripts (ADR-004).** Verworpen: dubbel werk naast het SQL-project, en
  een eigen bijhoudtabel per omgeving. Niemand heeft ze gebouwd, terwijl de
  dacpac-route werkt.

## Gevolgen

- De dacpac rekent het verschil zelf uit. Een destructieve wijziging (een kolom of
  tabel weg) is nog niet getest op een gevulde database. Test zo'n wijziging altijd
  eerst op een kopie.
- Wat ADR-004 over metadata als seed zei, staat los van het schema. De registratie
  van bronnen en entiteiten per omgeving blijft een eigen procedure (draaiboek).
- ADR-002 noemt een migratiescript (ADR-004) als drager van een framework-fix in de
  database. Lees dat als: een dacpac-wijziging, met zo nodig een eenmalig script.
- Bouwen kan alleen vanuit een LF-checkout (Docker, `mcr.microsoft.com/dotnet/sdk:8.0`).
  Een Windows-build geeft een ander `model.xml` en de guard faalt dan.
