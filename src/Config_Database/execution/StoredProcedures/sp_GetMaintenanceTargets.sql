    CREATE PROCEDURE [execution].[sp_GetMaintenanceTargets]
    (    @WorkspaceId UNIQUEIDENTIFIER
        ,@RetentionDays INT
    )
	WITH EXECUTE AS CALLER
AS
BEGIN
	SET NOCOUNT ON;

    -- Vangnet: 0 of minder zou elke verwerkte levering direct opruimen.
    IF ISNULL(@RetentionDays, 0) < 1
        THROW 50010, 'RetentionDays moet minimaal 1 zijn.', 1;

    -- 1. Leveringen in de landing zone die Bronze heeft verwerkt en die ouder zijn dan de bewaartermijn.
    --    Een levering die (ook) als onverwerkt in de wachtrij staat, blijft altijd staan.
    SELECT DISTINCT
         LOWER(CONVERT(NVARCHAR(36), LH.[WorkspaceGuid])) AS [WorkspaceGuid]
        ,LOWER(CONVERT(NVARCHAR(36), LH.[LakehouseGuid])) AS [LakehouseGuid]
        ,PLZE.[FilePath]
        ,PLZE.[FileName]
    FROM [execution].[PipelineLandingzoneEntity] PLZE
    INNER JOIN [integration].[LandingzoneEntity] LZE
        ON LZE.[LandingzoneEntityId] = PLZE.[LandingzoneEntityId]
    INNER JOIN [integration].[Lakehouse] LH
        ON LH.[LakehouseId] = LZE.[LakehouseId]
    WHERE LH.[WorkspaceGuid] = @WorkspaceId
      AND PLZE.[IsProcessed] = 1
      AND PLZE.[LoadEndDateTime] < DATEADD(DAY, -@RetentionDays, GETDATE())
      AND NOT EXISTS (SELECT 1 FROM [execution].[PipelineLandingzoneEntity] OPEN_
                      WHERE OPEN_.[FilePath] = PLZE.[FilePath]
                        AND OPEN_.[FileName] = PLZE.[FileName]
                        AND OPEN_.[IsProcessed] = 0);

    -- 2. Delta-tabellen in Bronze en Silver, voor VACUUM. Ook van inactieve entiteiten: hun tabel bestaat nog.
    --    GUID's in kleine letters: pyodbc geeft hoofdletters, en Delta (Hadoop/ABFS) weigert die in een OneLake-pad.
    --    De namespace zoals de notebooks het pad bouwen: kleine letters, Bronze max. 20 en Silver max. 30 tekens.
    SELECT
         'Bronze' AS [Layer]
        ,LOWER(CONVERT(NVARCHAR(36), LH.[WorkspaceGuid])) AS [WorkspaceGuid]
        ,LOWER(CONVERT(NVARCHAR(36), LH.[LakehouseGuid])) AS [LakehouseGuid]
        ,LOWER(CONVERT(NVARCHAR(20), DS.[Namespace])) AS [Namespace]
        ,BLE.[Schema]
        ,BLE.[Name]
    FROM [integration].[BronzeLayerEntity] BLE
    INNER JOIN [integration].[Lakehouse] LH
        ON LH.[LakehouseId] = BLE.[LakehouseId]
    INNER JOIN [integration].[LandingzoneEntity] LZE
        ON LZE.[LandingzoneEntityId] = BLE.[LandingzoneEntityId]
    INNER JOIN [integration].[DataSource] DS
        ON DS.[DataSourceId] = LZE.[DataSourceId]
    WHERE LH.[WorkspaceGuid] = @WorkspaceId
    UNION ALL
    SELECT
         'Silver'
        ,LOWER(CONVERT(NVARCHAR(36), LH.[WorkspaceGuid]))
        ,LOWER(CONVERT(NVARCHAR(36), LH.[LakehouseGuid]))
        ,LOWER(CONVERT(NVARCHAR(30), DS.[Namespace]))
        ,SLE.[Schema]
        ,SLE.[Name]
    FROM [integration].[SilverLayerEntity] SLE
    INNER JOIN [integration].[Lakehouse] LH
        ON LH.[LakehouseId] = SLE.[LakehouseId]
    INNER JOIN [integration].[BronzeLayerEntity] BLE
        ON BLE.[BronzeLayerEntityId] = SLE.[BronzeLayerEntityId]
    INNER JOIN [integration].[LandingzoneEntity] LZE
        ON LZE.[LandingzoneEntityId] = BLE.[LandingzoneEntityId]
    INNER JOIN [integration].[DataSource] DS
        ON DS.[DataSourceId] = LZE.[DataSourceId]
    WHERE LH.[WorkspaceGuid] = @WorkspaceId;
END

GO
