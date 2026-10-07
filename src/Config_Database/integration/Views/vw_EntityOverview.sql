CREATE VIEW [integration].[vw_EntityOverview]
AS
-- Eén rij per landingzone-entiteit, met omgeving (workspace), actief-vlaggen en het watermark.
-- vw_LoadSourceToLandingzone filtert alleen op LZE.IsActive; DS.IsActive telt daar niet mee.
SELECT
    LZE.[LandingzoneEntityId],
    W.[Name] AS [WorkspaceName],
    DS.[Name] AS [DataSourceName],
    DS.[LoadGroup],
    LZE.[SourceSchema],
    LZE.[SourceName],
    LZE.[IsIncremental],
    LZE.[IsIncrementalColumn],
    LZE.[IsActive],
    DS.[IsActive] AS [DataSourceIsActive],
    LZELV.[LoadValue],
    LZELV.[LastLoadDatetime]
FROM [integration].[LandingzoneEntity] LZE
INNER JOIN [integration].[DataSource] DS
    ON DS.[DataSourceId] = LZE.[DataSourceId]
INNER JOIN [integration].[Lakehouse] LH
    ON LH.[LakehouseId] = LZE.[LakehouseId]
INNER JOIN [integration].[Workspace] W
    ON W.[WorkspaceGuid] = LH.[WorkspaceGuid]
LEFT JOIN [execution].[LandingzoneEntityLastLoadValue] LZELV
    ON LZELV.[LandingzoneEntityId] = LZE.[LandingzoneEntityId]

GO

