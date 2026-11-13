CREATE VIEW [integration].[vw_LoadStatus]
AS
-- Laadstatus per landingzone-entiteit. De status is een heuristiek, geen garantie:
--   Uitgeschakeld = LandingzoneEntity.IsActive = 0
--   Fout          = de laatste fout (in een laag) is nieuwer dan het laatste succes in Silver
--   Wachtrij      = er staan bestanden op IsProcessed = 0 (landingzone of Bronze)
--   Nooit geladen = nog geen succesvolle Silver-load gelogd
--   OK            = anders
-- De log is niet consistent: EntityLayer komt voor als 'Landingzone' en 'LandingZone', en een notebookfout
-- staat als EndNotebookActivity met "Action":"Error" in LogData (zie 10_operations.md).
WITH ev AS (
    SELECT CASE WHEN [EntityLayer] IN ('Landingzone', 'LandingZone') THEN 'L' WHEN [EntityLayer] = 'Bronze' THEN 'B' WHEN [EntityLayer] = 'Silver' THEN 'S' END AS [Layer],
           [EntityId], [LogDateTime],
           CASE WHEN [LogType] = 'EndCopyActivity' THEN 1 ELSE 0 END AS [IsEnd],
           CASE WHEN [LogType] = 'FailedCopyActivity' THEN 1 ELSE 0 END AS [IsErr]
    FROM [logging].[CopyActivityExecution]
    UNION ALL
    SELECT CASE WHEN [EntityLayer] IN ('Landingzone', 'LandingZone') THEN 'L' WHEN [EntityLayer] = 'Bronze' THEN 'B' WHEN [EntityLayer] = 'Silver' THEN 'S' END,
           [EntityId], [LogDateTime],
           CASE WHEN [LogType] = 'EndNotebookActivity' AND [LogData] NOT LIKE '%"Error"%' THEN 1 ELSE 0 END,
           CASE WHEN [LogData] LIKE '%"Error"%' OR [LogType] LIKE 'Fail%' THEN 1 ELSE 0 END
    FROM [logging].[NotebookExecution]
),
agg AS (
    SELECT [Layer], [EntityId],
           MAX(CASE WHEN [IsEnd] = 1 THEN [LogDateTime] END) AS [LastEnd],
           MAX(CASE WHEN [IsErr] = 1 THEN [LogDateTime] END) AS [LastErr]
    FROM ev
    WHERE [Layer] IS NOT NULL
    GROUP BY [Layer], [EntityId]
),
base AS (
    SELECT
        LZE.[LandingzoneEntityId],
        W.[Name] AS [WorkspaceName],
        DS.[Name] AS [DataSourceName],
        LZE.[SourceSchema],
        LZE.[SourceName],
        LZE.[IsActive],
        LZELV.[LoadValue],
        LZELV.[LastLoadDatetime],
        AL.[LastEnd] AS [LandingzoneLastEnd],
        AB.[LastEnd] AS [BronzeLastEnd],
        AS_.[LastEnd] AS [SilverLastEnd],
        (SELECT MAX(v) FROM (VALUES (AL.[LastErr]), (AB.[LastErr]), (AS_.[LastErr])) t(v)) AS [LastErrorAt],
        (SELECT COUNT(*) FROM [execution].[PipelineLandingzoneEntity] P WHERE P.[LandingzoneEntityId] = LZE.[LandingzoneEntityId] AND P.[IsProcessed] = 0) AS [PendingLandingzoneFiles],
        (SELECT COUNT(*) FROM [execution].[PipelineBronzeLayerEntity] PB WHERE PB.[BronzeLayerEntityId] = BLE.[BronzeLayerEntityId] AND PB.[IsProcessed] = 0) AS [PendingBronzeFiles]
    FROM [integration].[LandingzoneEntity] LZE
    INNER JOIN [integration].[DataSource] DS ON DS.[DataSourceId] = LZE.[DataSourceId]
    INNER JOIN [integration].[Lakehouse] LH ON LH.[LakehouseId] = LZE.[LakehouseId]
    INNER JOIN [integration].[Workspace] W ON W.[WorkspaceGuid] = LH.[WorkspaceGuid]
    LEFT JOIN [execution].[LandingzoneEntityLastLoadValue] LZELV ON LZELV.[LandingzoneEntityId] = LZE.[LandingzoneEntityId]
    LEFT JOIN [integration].[BronzeLayerEntity] BLE ON BLE.[LandingzoneEntityId] = LZE.[LandingzoneEntityId]
    LEFT JOIN [integration].[SilverLayerEntity] SLE ON SLE.[BronzeLayerEntityId] = BLE.[BronzeLayerEntityId]
    LEFT JOIN agg AL ON AL.[Layer] = 'L' AND AL.[EntityId] = LZE.[LandingzoneEntityId]
    LEFT JOIN agg AB ON AB.[Layer] = 'B' AND AB.[EntityId] = BLE.[BronzeLayerEntityId]
    LEFT JOIN agg AS_ ON AS_.[Layer] = 'S' AND AS_.[EntityId] = SLE.[SilverLayerEntityId]
)
SELECT *,
       CASE
           WHEN [IsActive] = 0 THEN 'Uitgeschakeld'
           WHEN [LastErrorAt] IS NOT NULL AND [LastErrorAt] > ISNULL([SilverLastEnd], '1900-01-01') THEN 'Fout'
           WHEN [PendingLandingzoneFiles] + [PendingBronzeFiles] > 0 THEN 'Wachtrij'
           WHEN [SilverLastEnd] IS NULL THEN 'Nooit geladen'
           ELSE 'OK'
       END AS [Status]
FROM base

GO

