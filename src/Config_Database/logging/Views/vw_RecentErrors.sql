CREATE VIEW [logging].[vw_RecentErrors]
AS
-- Samenvoeging van de foutqueries uit 10_operations.md. De log is niet consistent: FailPipeline en
-- FailedPipeline komen allebei voor, en een notebookfout staat als EndNotebookActivity met "Action":"Error".
SELECT [LogDateTime], 'Notebook' AS [Bron], [WorkspaceGuid], [EntityLayer], [EntityId],
       [NotebookName] AS [Onderdeel], [LogType], [LogData]
FROM [logging].[NotebookExecution]
WHERE [LogData] LIKE '%"Error"%' OR [LogType] LIKE 'Fail%'
UNION ALL
SELECT [LogDateTime], 'Copy', [WorkspaceGuid], [EntityLayer], [EntityId],
       [CopyActivityName], [LogType], [LogData]
FROM [logging].[CopyActivityExecution]
WHERE [LogType] LIKE 'Fail%'
UNION ALL
SELECT [LogDateTime], 'Pipeline', [WorkspaceGuid], [EntityLayer], [EntityId],
       [PipelineName], [LogType], [LogData]
FROM [logging].[PipelineExecution]
WHERE [LogType] LIKE 'Fail%'

GO

