CREATE VIEW [logging].[vw_ExecutionSummary]
AS
-- One row per run, layer and entity: duration, status and row counts.
-- Landingzone comes from CopyActivityExecution (Copy activity output), Bronze and Silver from NotebookExecution.
-- LogData is VARCHAR(8000): when a row was truncated it is no longer valid JSON and the counts stay NULL.
WITH Events AS (
    SELECT [PipelineRunGuid], [PipelineParentRunGuid], [EntityLayer], CAST([EntityId] AS BIGINT) AS [EntityId],
           [LogType], [LogDateTime],
           -- Older pipeline versions wrote a trailing comma before the closing brace
           REPLACE([LogData], ',    }', '}') AS [LogData]
    FROM [logging].[CopyActivityExecution]
    UNION ALL
    SELECT [PipelineRunGuid], [PipelineParentRunGuid], [EntityLayer], CAST([EntityId] AS BIGINT),
           [LogType], [LogDateTime], [LogData]
    FROM [logging].[NotebookExecution]
),
Parsed AS (
    SELECT [PipelineRunGuid], [PipelineParentRunGuid], [EntityLayer], [EntityId], [LogType], [LogDateTime],
           CASE WHEN ISJSON([LogData]) = 1 THEN JSON_VALUE([LogData], '$.Action') END AS [Action],
           CASE WHEN ISJSON([LogData]) = 1 AND [LogType] = 'EndCopyActivity'
                THEN TRY_CAST(JSON_VALUE([LogData], '$.CopyOutput.rowsRead') AS BIGINT) END AS [CopyRowsRead],
           CASE WHEN ISJSON([LogData]) = 1 AND [LogType] = 'EndCopyActivity'
                THEN TRY_CAST(JSON_VALUE([LogData], '$.CopyOutput.rowsCopied') AS BIGINT) END AS [CopyRowsCopied],
           CASE WHEN ISJSON([LogData]) = 1 AND [LogType] = 'EndNotebookActivity'
                THEN TRY_CAST(JSON_VALUE([LogData], '$.CopyOutput.RowsWritten') AS BIGINT) END AS [NbRowsWritten],
           CASE WHEN ISJSON([LogData]) = 1 AND [LogType] = 'EndNotebookActivity'
                THEN TRY_CAST(JSON_VALUE([LogData], '$.CopyOutput.RowsInserted') AS BIGINT) END AS [NbRowsInserted],
           CASE WHEN ISJSON([LogData]) = 1 AND [LogType] = 'EndNotebookActivity'
                THEN TRY_CAST(JSON_VALUE([LogData], '$.CopyOutput.RowsUpdated') AS BIGINT) END AS [NbRowsUpdated],
           CASE WHEN ISJSON([LogData]) = 1 AND [LogType] = 'EndNotebookActivity'
                THEN TRY_CAST(JSON_VALUE([LogData], '$.CopyOutput.RowsDeleted') AS BIGINT) END AS [NbRowsDeleted]
    FROM Events
),
Runs AS (
    SELECT [PipelineRunGuid],
           MAX([PipelineParentRunGuid]) AS [PipelineParentRunGuid],
           [EntityLayer],
           [EntityId],
           MIN(CASE WHEN [LogType] LIKE 'Start%' THEN [LogDateTime] END) AS [StartTime],
           MAX(CASE WHEN [LogType] LIKE 'End%' OR [LogType] LIKE 'Failed%' THEN [LogDateTime] END) AS [EndTime],
           -- Notebooks log failures as End with Action = Error, copy pipelines as Failed
           MAX(CASE WHEN [LogType] LIKE 'Failed%' OR [Action] = 'Error' THEN 1 ELSE 0 END) AS [HasFailed],
           MAX(CASE WHEN [LogType] LIKE 'End%' THEN 1 ELSE 0 END) AS [HasEnded],
           MAX([CopyRowsRead]) AS [RowsRead],
           MAX(COALESCE([CopyRowsCopied], [NbRowsWritten])) AS [RowsWritten],
           MAX([NbRowsInserted]) AS [RowsInserted],
           MAX([NbRowsUpdated]) AS [RowsUpdated],
           MAX([NbRowsDeleted]) AS [RowsDeleted]
    FROM Parsed
    WHERE [EntityLayer] IN ('Landingzone', 'Bronze', 'Silver')
    GROUP BY [PipelineRunGuid], [EntityLayer], [EntityId]
)
SELECT R.[PipelineRunGuid],
       R.[PipelineParentRunGuid],
       R.[EntityLayer],
       R.[EntityId],
       COALESCE(LZ.[SourceSchema], BR.[Schema], SI.[Schema]) AS [EntitySchema],
       COALESCE(LZ.[SourceName], BR.[Name], SI.[Name]) AS [EntityName],
       R.[StartTime],
       R.[EndTime],
       CAST(DATEDIFF_BIG(MILLISECOND, R.[StartTime], R.[EndTime]) / 1000.0 AS DECIMAL(18, 3)) AS [DurationSeconds],
       CASE WHEN R.[HasFailed] = 1 THEN 'Failed'
            WHEN R.[HasEnded] = 1 THEN 'Succeeded'
            ELSE 'Running' END AS [Status],
       R.[RowsRead],
       R.[RowsWritten],
       R.[RowsInserted],
       R.[RowsUpdated],
       R.[RowsDeleted]
FROM Runs R
LEFT JOIN [integration].[LandingzoneEntity] LZ ON R.[EntityLayer] = 'Landingzone' AND LZ.[LandingzoneEntityId] = R.[EntityId]
LEFT JOIN [integration].[BronzeLayerEntity] BR ON R.[EntityLayer] = 'Bronze' AND BR.[BronzeLayerEntityId] = R.[EntityId]
LEFT JOIN [integration].[SilverLayerEntity] SI ON R.[EntityLayer] = 'Silver' AND SI.[SilverLayerEntityId] = R.[EntityId]
GO
