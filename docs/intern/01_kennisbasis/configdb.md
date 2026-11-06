# Configuratiedatabase (`integration` / `execution` / `logging`)

Legenda status: `vastgesteld` · `getest in eigen omgeving` · `aanname` · `open vraag` · `tweedehands` (alleen uit een samenvatting, zoektool of tutorial; niet teruggevonden in een origineel transcript, de code of een eigen test)

Primaire bron voor dit bestand is de fork-code zelf (`FMD/src/Config_Database/`), niet de chats — conform de projectinstructie om stored procedures op de fork-code te baseren.

## Structuur

- **Punt:** Het SQL-projectbestand `FMD/src/Config_Database/SQL_FMD_FRAMEWORK.sqlproj` bouwt exact 3 schema's: `integration`, `execution`, `logging` (`Security/integration.sql`, `Security/execution.sql`, `Security/logging.sql`, elk simpelweg `CREATE SCHEMA [x] AUTHORIZATION [dbo]`).
  **Bron:** `FMD/src/Config_Database/SQL_FMD_FRAMEWORK.sqlproj`. **Status:** vastgesteld.

## Schema `integration` — kernconfiguratie

| Tabel | Doel | Belangrijkste kolommen | PK / unieke constraint |
|---|---|---|---|
| `Connection` | Verbindingsdefinities (DB, ADLS, ADF, SFTP/FTP, Notebook, Oracle) | `ConnectionId` (PK, identity), `ConnectionGuid` (uniqueidentifier), `Name` varchar(200), `Type` varchar(50), `GatewayType` varchar(50) NULL, `DatasourceReference` varchar(max) NULL, `IsActive` bit | UC op `ConnectionGuid` |
| `DataSource` | Databronnen, elk gekoppeld aan een Connection | `DataSourceId` (PK), `ConnectionId`, `Name` varchar(100), `Namespace` varchar(100), `Type` varchar(30) NULL, `Description` nvarchar(200) NULL, `LoadGroup` varchar(50) DEFAULT '' NOT NULL, `IsActive` bit | UC op (`ConnectionId`,`Name`,`Type`) |
| `Workspace` | Fabric-workspace-registratie | `WorkspaceId` (PK), `WorkspaceGuid` (uniqueidentifier), `Name` varchar(100) | UC op `WorkspaceGuid` |
| `Lakehouse` | Lakehouse-registratie per workspace | `LakehouseId` (PK), `LakehouseGuid` (uniqueidentifier), `WorkspaceGuid` (FK → `Workspace.WorkspaceGuid`), `Name` varchar(100), `IsActive` bit | UC op `LakehouseGuid` |
| `Pipeline` | Pipeline-registratie per workspace | `PipelineId` (PK), `PipelineGuid` (uniqueidentifier), `WorkspaceGuid`, `Name` varchar(200), `IsActive` bit | UC op `PipelineGuid` (géén FK-constraint naar Workspace, in tegenstelling tot Lakehouse) |
| `LandingzoneEntity` | Bron-entiteit → landingzone-bestand-mapping | `LandingzoneEntityId` (PK, bigint), `DataSourceId`, `LakehouseId`, `SourceSchema` nvarchar(100) NULL, `SourceName` nvarchar(200), `FileName` nvarchar(200), `FileType` nvarchar(20), `FilePath` nvarchar(500), `IsIncremental` bit DEFAULT 0, `IsIncrementalColumn` nvarchar(50) NULL, `SourceCustomSelect` nvarchar(4000) NULL, `CustomNotebookName` varchar(200) NULL, `IsActive` bit | UC op (`SourceSchema`,`SourceName`,`DataSourceId`,`LakehouseId`) |
| `BronzeLayerEntity` | Bronze-laag tabelmetadata | `BronzeLayerEntityId` (PK, bigint), `LandingzoneEntityId` (FK → `LandingzoneEntity`), `LakehouseId`, `Schema` nvarchar(100), `Name` nvarchar(200), `PrimaryKeys` nvarchar(200), `FileType` DEFAULT 'Delta', `CleansingRules` nvarchar(max) NULL, `IsActive` bit | FK naar `LandingzoneEntity`; UC op (`LakehouseId`,`Schema`,`Name`) |
| `SilverLayerEntity` | Silver-laag tabelmetadata | `SilverLayerEntityId` (PK, bigint), `BronzeLayerEntityId` (FK → `BronzeLayerEntity`), `LakehouseId`, `Schema` nvarchar(100) NULL, `Name` nvarchar(200) NULL, `FileType` DEFAULT 'Delta', `CleansingRules` nvarchar(max) NULL, `IsActive` bit, `IsHistorized` bit NOT NULL DEFAULT 0 *(toegevoegd 2026-10-12, `FMD_FRAMEWORK#51`, ADR-016: 1 = SCD2-historie in Silver, 0 = alleen de huidige rij; correctie 2026-10-13: de default was 1, nu 0, ADR-016 *Herzien 2026-10-13*)* | FK naar `BronzeLayerEntity`; UC op (`LakehouseId`,`Schema`,`Name`) |

**Bron:** alle bestanden onder `FMD/src/Config_Database/integration/Tables/*.sql`. **Status:** vastgesteld.

**Opvallend:**
- Geen van deze tabellen heeft een DB-`FOREIGN KEY`-constraint naar `Connection`/`DataSource`/`Lakehouse`/`Workspace`, behalve de drie expliciet genoemde (`Lakehouse→Workspace`, `BronzeLayerEntity→LandingzoneEntity`, `SilverLayerEntity→BronzeLayerEntity`). Referentiële integriteit voor `DataSource.ConnectionId` en `LandingzoneEntity.DataSourceId`/`LakehouseId` wordt dus **niet** door de database afgedwongen. **Status:** vastgesteld (afwezigheid geverifieerd in DDL).
- `DataSource.LoadGroup` bestaat in de fork maar **niet** in de upstream-wiki (`Data-Model.md`) — een Bitmetric-fork-toevoeging (feature "LoadGroup scheduling"). **Bron:** `bronnen/00_fork_vs_upstream.md` + afwezigheid in `bronnen/fmd-upstream-wiki/wiki-clone/Data-Model.md`. **Status:** vastgesteld.

## Schema `execution` — runtime/load-state

| Tabel | Doel | Belangrijkste kolommen |
|---|---|---|
| `LandingzoneEntityLastLoadValue` | Laatste incrementele waarde per landingzone-entiteit | `LandingzoneEntityValueId` (PK), `LandingzoneEntityId` (UC, effectief 1-op-1), `LoadValue` varchar(50), `LastLoadDatetime` datetime2(7) |
| `PipelineBronzeLayerEntity` | Load-tracking van bronzebestanden per pipeline-run | `PipelineBronzeLayerEntityId` (PK), `BronzeLayerEntityId`, `TableName` nvarchar(300), `SchemaName` nvarchar(max), `InsertDateTime`, `IsProcessed` bit, `LoadEndDateTime` |
| `PipelineLandingzoneEntity` | Load-tracking van landingzone-bestanden per pipeline-run | `PipelineLandingzoneEntityId` (PK), `LandingzoneEntityId`, `FilePath` nvarchar(300), `FileName` nvarchar(max), `InsertDateTime`, `IsProcessed` bit, `LoadEndDateTime` |

Drie views bouwen de effectieve "wat moet er geladen worden"-lijst:
- `vw_LoadSourceToLandingzone` — join `LandingzoneEntity`+`Lakehouse`+`Workspace`+`DataSource`+`Connection`(+optioneel `LandingzoneEntityLastLoadValue`), filtert `IsActive=1`, bouwt dynamisch `LastLoadValue`/`SourceDataRetrieval`-SQL-strings.
- `vw_LoadToBronzeLayer` — join `BronzeLayerEntity`+`LandingzoneEntity`+`PipelineLandingzoneEntity`+`LandingzoneEntityLastLoadValue`+`DataSource`+2× `Lakehouse`+2× `Workspace`, filtert `IsActive=1` (LZE+BLE) en `PLZE.IsProcessed=0`.
- `vw_LoadToSilverLayer` — join `SilverLayerEntity`+`BronzeLayerEntity`+`LandingzoneEntity`+`PipelineBronzeLayerEntity`+`DataSource`+2× `Lakehouse`+2× `Workspace`, filtert `IsActive=1` (LZE+BLE+SLE) en `PBLE.IsProcessed=0`.

**Bron:** `FMD/src/Config_Database/execution/Tables/*.sql` en `execution/Views/*.sql`. **Status:** vastgesteld.

## Schema `logging` — audit/executielogs (append-only, geen constraints)

Drie structureel identieke tabellen, geen PK: `CopyActivityExecution`, `NotebookExecution`, `PipelineExecution`. Elk met: `WorkspaceGuid`, `PipelineRunGuid`, `PipelineParentRunGuid`, een entiteitsspecifieke Guid+Name, een parameters-veld varchar(8000), `TriggerType`/`TriggerGuid`/`TriggerTime`, `LogType`, `LogDateTime` datetime2(6), `LogData` varchar(8000), `EntityId`, `EntityLayer`.

**Bron:** `FMD/src/Config_Database/logging/Tables/*.sql`. **Status:** vastgesteld.

**Bekende datakwaliteitsissues in de logging (zie ook `operations.md`):** inconsistente `LogType`-spelling (`FailPipeline` vs `FailedPipeline`); `EntityLayer` heeft 4 waarden (`Bronze`,`Control`,`Landingzone`,`Silver`); `TriggerType` bevat naast `"Manual"` ook de kale string `"1"` voor `PL_FMD_LOAD_ALL` (ongenormaliseerde trigger-code). Schema drift geconstateerd: `integration.DataSource.LoadGroup` bestaat in de repo-broncode maar niet in de live `SQL_INTEGRATION_FRAMEWORK`-database bij Bitmetric — de gedeployde DB liep op moment van onderzoek achter op de repo.
**Bron:** `bronnen/claude-code-transcripten/markdown/2026-09-14_fmd-logging-power-bi-rapportage.md` (live SQL-verificatie). **Status:** getest in eigen omgeving.

## Relatiediagram (voor Mermaid ER-diagram in fase 3)

```
Workspace 1---N Lakehouse
Workspace 1---N Pipeline
Connection 1---N DataSource
DataSource 1---N LandingzoneEntity
Lakehouse  1---N LandingzoneEntity   (LandingzoneEntity.LakehouseId, niet DB-afgedwongen)
LandingzoneEntity 1---N BronzeLayerEntity   (FK afgedwongen)
Lakehouse  1---N BronzeLayerEntity   (BronzeLayerEntity.LakehouseId, niet afgedwongen)
BronzeLayerEntity 1---N SilverLayerEntity   (FK afgedwongen)
Lakehouse  1---N SilverLayerEntity   (SilverLayerEntity.LakehouseId, niet afgedwongen)
LandingzoneEntity 1---1 LandingzoneEntityLastLoadValue   (execution schema)
LandingzoneEntity 1---N PipelineLandingzoneEntity         (execution schema)
BronzeLayerEntity  1---N PipelineBronzeLayerEntity         (execution schema)
```
**Status:** aanname (afgeleid uit kolomnamen + join-logica in de views; niet allemaal DB-FK's — zie hierboven).

## Verschillen fork vs. upstream-wiki

1. `DataSource.LoadGroup` + bijbehorende parameter/kolom in stored procedures en views: fork-only, niet in upstream. **Status:** vastgesteld.
2. Upstream (`Data-Integration.md`) beschrijft voor Connection/DataSource-registratie **directe INSERT-statements** als hoofdpad; de fork heeft daarnaast volwaardige `sp_UpsertConnection`/`sp_UpsertDataSource`-procs die in die wiki-pagina niet als aanbevolen pad staan. **Status:** vastgesteld (verschil in aanbevolen pad, niet in wat mogelijk is).
3. Upstream `Data-Model.md` documenteert alléén het `integration`-schema; de `execution`- en `logging`-schema's komen in geen van de gelezen wiki-pagina's voor. **Status:** vastgesteld (afwezigheid).
