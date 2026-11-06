# 05_INTEGRATION — Technische documentatie

**Fase:** 3 (Technische documentatie per domein)
**Datum:** 2026-09-22
**Status:** Eerste versie
**Domein:** INTEGRATION (gedeelde ingestielaag — Landingzone/Bronze/Silver, generiek en config-driven)

Deze map documenteert de generieke ingestielaag van het FMD Framework: het datamodel van de configuratiedatabase, hoe bronnen en entiteiten daarin geregistreerd worden, en de operationele aandachtspunten die daarbij horen. In tegenstelling tot de Gold-laag (per business-domein handmatig gebouwd, zie `05_FINANCE/` etc.) is dit alles generiek en herbruikbaar over alle domeinen heen.

**Bronbasis:** deze documenten zijn direct afgeleid van `output/01_kennisbasis/configdb.md`, `registratie.md`, `geleerde-lessen.md` en `open-vragen.md`, die zelf weer op de fork-code (`FMD/src/Config_Database/`) zijn gebaseerd en op 2026-09-22 zijn geverifieerd tegen commit `b3fbed7` (repo-audit). Waar een fact-status relevant is, is die overgenomen (`vastgesteld` / `getest in eigen omgeving` / `aanname` / `open vraag`).

## Inhoud

| Bestand | Onderwerp |
|---|---|
| [`01_ddl-spec.md`](./01_ddl-spec.md) | DDL-specificatie van de drie configdb-schema's (`integration`/`execution`/`logging`): tabellen, kolommen, constraints, relaties, views, en de verschillen met de upstream-wiki |
| [`02_configdb-registratie.md`](./02_configdb-registratie.md) | Registratieketen: de drie kern-stored-procedures, de bulkregistratiepipeline `PL_TOOLING_POST_ASQL_TO_FMD`, hoe je een nieuwe bron end-to-end registreert, en deactiveren |
| [`03_operationele-aandachtspunten.md`](./03_operationele-aandachtspunten.md) | De vier operationele bevindingen uit Fase 1/2 (casing-mismatch, parameter-handling, versiecontrole, LDZ-FTP-bug) uitgewerkt tot concrete aandachtspunten voor implementatie en troubleshooting |

## Uitgangspunten

- **Geen FK-afdwinging door de database** op de meeste relaties (uitzonderingen: `Lakehouse→Workspace`, `BronzeLayerEntity→LandingzoneEntity`, `SilverLayerEntity→BronzeLayerEntity`). Referentiële integriteit voor de rest (`DataSource.ConnectionId`, `LandingzoneEntity.DataSourceId`/`LakehouseId`) is een applicatie-verantwoordelijkheid, niet een database-garantie.
- **`LoadGroup` op `DataSource` is een Bitmetric-fork-toevoeging**, niet aanwezig in de upstream FMD-wiki.
- **Lakehouse-namen zijn conventiegebonden, niet vrij te kiezen:** `sp_UpsertLandingzoneBronzeSilver` zoekt via `sp_GetLakehouse` naar lakehouses die letterlijk `LH_DATA_LANDINGZONE`, `LH_BRONZE_LAYER` en `LH_SILVER_LAYER` heten binnen de opgegeven workspace. Deze moeten dus al geregistreerd staan in `integration.Lakehouse` vóórdat je een entiteit registreert.
- **Workspace/lakehouse-referenties lopen via de Variable Library** (`VAR_CONFIG_FMD`, libraryvariabelen `fmd_data_workspace_guid`/`fmd_landingzone_lakehouse_guid`), niet via hardcoded GUID's of losse pipeline-parameters. Dit is de fix voor een eerder terugkerend `WorkspaceNotFound`/`EntityNotFound`-probleem bij Deployment-Pipeline-promotie.

## Zie ook

- **`../13_referentie-implementatie-bitmetric.md`** — concrete Bitmetric-testevidentie (job-ID's, commit-hashes, omgevingsnamen) die uit deze generieke documentatie is verplaatst.

## Openstaand vanuit Fase 2 dat hier relevant is

- **B-INFRA-01** (configdb-registratie via sp_Upsert*-procedures) is de basis voor `02_configdb-registratie.md`.
- **B-INFRA-02** (deactivering via `IsActive=0`) — zie `01_ddl-spec.md` voor de kolommen waarop dit van toepassing is.
- De vier operationele bevindingen (casing, parameter-handling, versiecontrole, LDZ-FTP-bug) uit `02_beslisdocument/02_beslisregister.md` zijn hier voor het eerst technisch uitgewerkt (`03_operationele-aandachtspunten.md`).
