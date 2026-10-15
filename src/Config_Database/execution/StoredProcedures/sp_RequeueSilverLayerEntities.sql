
CREATE PROCEDURE [execution].[sp_RequeueSilverLayerEntities]
(    @WorkspaceId UNIQUEIDENTIFIER
    ,@DataSourceName NVARCHAR(100) = ''
    ,@Entities NVARCHAR(MAX) = ''
    ,@DryRun BIT = 1
    )
WITH EXECUTE AS CALLER
AS
BEGIN
    -- Puts active Silver entities back in the queue, so the next PL_FMD_LOAD_SILVER run processes them again
    -- from the Bronze table, without a new delivery. Use it after a change to the Silver cleansing rules.
    -- @WorkspaceId is the DATA workspace, as Data_WorkspaceGuid in the pipeline; the filter is the one of
    -- fn_EntityInFilter (empty = no filter). @DryRun = 1 (default) only lists what would be queued.
    -- A change that alters the shape of the Silver table (a type, a new or renamed column) also needs the table
    -- dropped first: the merge writes the columns of the existing table only.
    SET NOCOUNT ON;

    DECLARE @Targets TABLE (
         [BronzeLayerEntityId] BIGINT
        ,[SchemaName] NVARCHAR(100)
        ,[TableName] NVARCHAR(200)
        ,[DataSourceName] VARCHAR(100)
        ,[SourceSchema] NVARCHAR(100)
        ,[SourceName] NVARCHAR(200)
        ,[AlreadyQueued] BIT
    );

    INSERT INTO @Targets
    SELECT BLE.[BronzeLayerEntityId]
          ,BLE.[Schema]
          ,BLE.[Name]
          ,DS.[Name]
          ,LZE.[SourceSchema]
          ,LZE.[SourceName]
          ,CASE WHEN EXISTS (SELECT 1
                             FROM [execution].[PipelineBronzeLayerEntity] PBLE
                             WHERE PBLE.[BronzeLayerEntityId] = BLE.[BronzeLayerEntityId]
                               AND PBLE.[IsProcessed] = 0)
                THEN 1 ELSE 0 END
    FROM [integration].[SilverLayerEntity] SLE
    INNER JOIN [integration].[BronzeLayerEntity] BLE
        ON BLE.[BronzeLayerEntityId] = SLE.[BronzeLayerEntityId]
    INNER JOIN [integration].[LandingzoneEntity] LZE
        ON LZE.[LandingzoneEntityId] = BLE.[LandingzoneEntityId]
    INNER JOIN [integration].[DataSource] DS
        ON DS.[DataSourceId] = LZE.[DataSourceId]
    INNER JOIN [integration].[Lakehouse] BLH
        ON BLH.[LakehouseId] = BLE.[LakehouseId]
    WHERE BLH.[WorkspaceGuid] = @WorkspaceId
      AND LZE.[IsActive] = 1
      AND BLE.[IsActive] = 1
      AND SLE.[IsActive] = 1
      AND [execution].[fn_EntityInFilter](@DataSourceName, @Entities, DS.[Name], LZE.[SourceSchema], LZE.[SourceName]) = 1;

    IF @DryRun = 0
    BEGIN
        -- Same row sp_UpsertPipelineBronzeLayerEntity adds after a Bronze load; one open row per entity.
        INSERT INTO [execution].[PipelineBronzeLayerEntity] ([BronzeLayerEntityId], [TableName], [SchemaName], [InsertDateTime], [IsProcessed])
        SELECT [BronzeLayerEntityId], [TableName], [SchemaName], GETDATE(), 0
        FROM @Targets
        WHERE [AlreadyQueued] = 0;
    END

    SELECT [DataSourceName]
          ,[SourceSchema]
          ,[SourceName]
          ,[BronzeLayerEntityId]
          ,CASE WHEN [AlreadyQueued] = 1 THEN 'already queued'
                WHEN @DryRun = 1 THEN 'dry run: would be queued'
                ELSE 'queued' END AS [Result]
    FROM @Targets
    ORDER BY [DataSourceName], [SourceSchema], [SourceName];
END;

GO
