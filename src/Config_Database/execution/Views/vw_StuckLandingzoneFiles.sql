CREATE VIEW [execution].[vw_StuckLandingzoneFiles]
AS
-- Bestanden die langer dan 2 uur op IsProcessed = 0 staan (zelfde grens als 10_operations.md).
-- GETDATE() is in Azure SQL UTC, dus de vergelijking met SYSUTCDATETIME() klopt.
SELECT
    PLE.[PipelineLandingzoneEntityId],
    PLE.[LandingzoneEntityId],
    W.[Name] AS [WorkspaceName],
    DS.[Name] AS [DataSourceName],
    LZE.[SourceSchema],
    LZE.[SourceName],
    PLE.[FileName],
    PLE.[InsertDateTime],
    DATEDIFF(HOUR, PLE.[InsertDateTime], SYSUTCDATETIME()) AS [AgeHours]
FROM [execution].[PipelineLandingzoneEntity] PLE
INNER JOIN [integration].[LandingzoneEntity] LZE
    ON LZE.[LandingzoneEntityId] = PLE.[LandingzoneEntityId]
INNER JOIN [integration].[DataSource] DS
    ON DS.[DataSourceId] = LZE.[DataSourceId]
INNER JOIN [integration].[Lakehouse] LH
    ON LH.[LakehouseId] = LZE.[LakehouseId]
INNER JOIN [integration].[Workspace] W
    ON W.[WorkspaceGuid] = LH.[WorkspaceGuid]
WHERE PLE.[IsProcessed] = 0
  AND PLE.[InsertDateTime] < DATEADD(HOUR, -2, SYSUTCDATETIME())

GO

