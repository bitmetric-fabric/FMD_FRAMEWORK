-- Registers sources and entities in the configuration database for one environment. Repeatable.
--
-- Usage: copy this file to the customer repo, fill in @Sources and @Entities, and run it per environment,
-- after the setup and after every promotion to that environment (registrations do not move with a promotion):
--
--   sqlcmd -S <server> -d <database> --authentication-method ActiveDirectoryAzCli -b \
--          -v DataWorkspace="<PREFIX> INTEGRATION DATA (T)" Environment=T -i registreer_entiteiten.sql
--
-- - All or nothing: on any error nothing is registered.
-- - @Sources binds a logical source to a connection and database per environment. A row with Environment '*'
--   applies to every environment without a row of its own. So by default every environment loads from the
--   same source; add a row for D or T to point that environment at e.g. a development or test database.
-- - The lists are the truth: LoadGroup per bound source, IsActive per entity. Switch an entity off with
--   IsActive = 0 in the list, not by hand in the database, or the next run switches it on again.
-- - LoadGroup lives on the data source. Environments that share a source binding share its LoadGroup.
-- - HistoryDays (optional, per binding): for incremental entities without a watermark yet, the first load
--   only fetches rows of the last N days. Only for a date/time IsIncrementalColumn. An existing watermark is
--   never changed. Full-load entities ignore it.
-- - An existing entity is found by data source + SourceSchema + SourceName. A different SourceName gives a new
--   entity (see 11_troubleshooting, "Herregistratie onder een andere DataSource").
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @DataWorkspace NVARCHAR(200) = N'$(DataWorkspace)';
DECLARE @Environment   VARCHAR(10)   = '$(Environment)';
DECLARE @Description   NVARCHAR(200) = N'Registered with registreer_entiteiten.sql';

DECLARE @Sources TABLE ([Environment] VARCHAR(10), [Source] NVARCHAR(100), [ConnectionName] NVARCHAR(200),
                        [DataSourceName] NVARCHAR(100), [Namespace] VARCHAR(100), [DataSourceType] VARCHAR(30),
                        [LoadGroup] VARCHAR(50), [HistoryDays] INT);

DECLARE @Entities TABLE ([Nr] INT IDENTITY, [Source] NVARCHAR(100), [SourceSchema] NVARCHAR(100), [SourceName] NVARCHAR(200),
                         [TargetSchema] NVARCHAR(100), [TargetName] NVARCHAR(200), [FileName] NVARCHAR(200), [FileType] NVARCHAR(20),
                         [IsIncremental] BIT, [IsIncrementalColumn] NVARCHAR(50), [CustomNotebookName] VARCHAR(200),
                         [PrimaryKeys] NVARCHAR(200), [IsActive] BIT);

-- ===== Sources (fill in) =======================================================================================
-- Environment: '*' (all environments) or the short of one environment (D, T, A, P). A specific row wins over '*'.
-- DataSourceName is the database for ASQL and Snowflake. Namespace must be the same for a Source in every environment.
INSERT INTO @Sources ([Environment],[Source],[ConnectionName],[DataSourceName],[Namespace],[DataSourceType],[LoadGroup],[HistoryDays]) VALUES
 ('*', N'ERP', N'CON_FMD_<SOURCE>', N'<SourceDatabase>', 'erp', 'ASQL_01', '', NULL)
-- ,('D', N'ERP', N'CON_FMD_<SOURCE>', N'<SourceDatabase>_DEV',  'erp', 'ASQL_01', '', 730)
-- ,('T', N'ERP', N'CON_FMD_<SOURCE>', N'<SourceDatabase>_TEST', 'erp', 'ASQL_01', '', 730)
;

-- ===== Entities (fill in) ======================================================================================
-- FileName = <TargetSchema>_<TargetName> is the usual choice. CustomNotebookName only for type NOTEBOOK.
INSERT INTO @Entities ([Source],[SourceSchema],[SourceName],[TargetSchema],[TargetName],[FileName],[FileType],
                       [IsIncremental],[IsIncrementalColumn],[CustomNotebookName],[PrimaryKeys],[IsActive]) VALUES
 (N'ERP', N'Sales', N'Customer', N'Sales', N'Customer', N'Sales_Customer', N'parquet', 0, NULL, NULL, N'CustomerID', 1)
;
-- ===============================================================================================================

-- 1. Checks first: nothing is written if one fails.
-- sqlcmd stops by itself when a -v variable is missing; outside sqlcmd the placeholder stays and the checks below fail.
DECLARE @WsGuid UNIQUEIDENTIFIER = (SELECT [WorkspaceGuid] FROM [integration].[Workspace] WHERE [Name] = @DataWorkspace);
IF @WsGuid IS NULL OR NOT EXISTS (SELECT 1 FROM [integration].[Lakehouse] WHERE [WorkspaceGuid] = @WsGuid AND [Name] = 'LH_DATA_LANDINGZONE')
    THROW 50002, 'Workspace or LH_DATA_LANDINGZONE not registered: run the setup for this environment first.', 1;
IF @Environment NOT IN ('D', 'T', 'A', 'P')
    THROW 50002, 'Pass the environment short with -v Environment=<D|T|A|P>.', 1;
-- The environment must match the DATA workspace: suffix (D)/(T)/(A), no suffix in production.
-- Otherwise e.g. a Test workspace would be registered with the production binding.
IF @Environment <> CASE WHEN @DataWorkspace LIKE N'% ([DTA])' THEN SUBSTRING(@DataWorkspace, LEN(@DataWorkspace) - 1, 1) ELSE 'P' END
    THROW 50002, 'Environment does not match the suffix of DataWorkspace: (D)/(T)/(A), or no suffix for P.', 1;

-- The binding that applies in this environment: its own row, otherwise the '*' row.
DECLARE @Bound TABLE ([Source] NVARCHAR(100), [ConnectionName] NVARCHAR(200), [DataSourceName] NVARCHAR(100), [Namespace] VARCHAR(100),
                      [DataSourceType] VARCHAR(30), [LoadGroup] VARCHAR(50), [HistoryDays] INT);
INSERT INTO @Bound
SELECT s.[Source], s.[ConnectionName], s.[DataSourceName], s.[Namespace], s.[DataSourceType], ISNULL(s.[LoadGroup], ''), s.[HistoryDays]
FROM @Sources s
WHERE s.[Environment] = @Environment
   OR (s.[Environment] = '*' AND NOT EXISTS (SELECT 1 FROM @Sources x WHERE x.[Source] = s.[Source] AND x.[Environment] = @Environment));

DECLARE @Error NVARCHAR(2000);
SELECT @Error = STRING_AGG(CONVERT(NVARCHAR(MAX), CONCAT([Item], ': ', [Reason])), '; ')
FROM (
    SELECT CONCAT([Environment], '/', [Source]) AS [Item], N'unknown environment; use *, D, T, A or P' AS [Reason]
    FROM @Sources WHERE [Environment] NOT IN ('*', 'D', 'T', 'A', 'P')
    UNION ALL
    SELECT CONCAT(MIN([Environment]), '/', [Source]), N'source bound twice for the same environment'
    FROM @Sources GROUP BY [Environment], [Source] HAVING COUNT(*) > 1
    UNION ALL
    SELECT [Source], N'Namespace differs between environments; it must be the same, or Silver and Gold get other table names'
    FROM @Sources GROUP BY [Source] HAVING COUNT(DISTINCT [Namespace]) > 1
    UNION ALL
    SELECT [Source], N'HistoryDays must be 1 or more' FROM @Bound WHERE [HistoryDays] < 1
    UNION ALL
    SELECT b.[Source], N'connection ' + b.[ConnectionName] + N' not registered'
    FROM @Bound b WHERE NOT EXISTS (SELECT 1 FROM [integration].[Connection] c WHERE c.[Name] = b.[ConnectionName])
    UNION ALL
    SELECT MIN(b.[Source]), N'data source ' + b.[DataSourceName] + N' has more than one LoadGroup in this environment'
    FROM @Bound b GROUP BY b.[ConnectionName], b.[DataSourceName], b.[DataSourceType] HAVING COUNT(DISTINCT b.[LoadGroup]) > 1
    UNION ALL
    SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'source ' + e.[Source] + N' has no binding for environment ' + @Environment
    FROM @Entities e WHERE NOT EXISTS (SELECT 1 FROM @Bound b WHERE b.[Source] = e.[Source])
    UNION ALL
    SELECT CONCAT([SourceSchema], '.', [SourceName]), N'IsIncrementalColumn is required when IsIncremental = 1'
    FROM @Entities WHERE [IsIncremental] = 1 AND ISNULL([IsIncrementalColumn], '') = ''
    UNION ALL
    SELECT CONCAT([SourceSchema], '.', [SourceName]), N'PrimaryKeys is empty' FROM @Entities WHERE ISNULL([PrimaryKeys], '') = ''
    UNION ALL
    SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'CustomNotebookName is required for type NOTEBOOK'
    FROM @Entities e JOIN @Bound b ON b.[Source] = e.[Source]
    WHERE b.[DataSourceType] = 'NOTEBOOK' AND ISNULL(e.[CustomNotebookName], '') = ''
    UNION ALL
    SELECT CONCAT(MIN([SourceSchema]), '.', MIN([SourceName])), N'listed twice'
    FROM @Entities GROUP BY [Source], [SourceSchema], [SourceName] HAVING COUNT(*) > 1
) f;
IF @Error IS NOT NULL THROW 50003, @Error, 1;

-- 2. Register, in one transaction.
DECLARE @Nr INT = 1, @Max INT = (SELECT MAX([Nr]) FROM @Entities), @ConnectionId INT, @DataSourceId INT, @EntityId BIGINT;
DECLARE @CN NVARCHAR(200), @DSN NVARCHAR(100), @NS VARCHAR(100), @DST VARCHAR(30), @LG VARCHAR(50), @HD INT, @SS NVARCHAR(100),
        @SN NVARCHAR(200), @TS NVARCHAR(100), @TN NVARCHAR(200), @FN NVARCHAR(200), @FT NVARCHAR(20), @Inc BIT,
        @IncCol NVARCHAR(50), @NB VARCHAR(200), @PK NVARCHAR(200), @Act BIT;

BEGIN TRY
    BEGIN TRANSACTION;
    WHILE @Nr <= @Max
    BEGIN
        SELECT @CN=b.[ConnectionName], @DSN=b.[DataSourceName], @NS=b.[Namespace], @DST=b.[DataSourceType], @LG=b.[LoadGroup],
               @HD=b.[HistoryDays], @SS=e.[SourceSchema], @SN=e.[SourceName], @TS=e.[TargetSchema], @TN=e.[TargetName],
               @FN=e.[FileName], @FT=e.[FileType], @Inc=e.[IsIncremental], @IncCol=e.[IsIncrementalColumn],
               @NB=e.[CustomNotebookName], @PK=e.[PrimaryKeys], @Act=e.[IsActive]
        FROM @Entities e JOIN @Bound b ON b.[Source] = e.[Source] WHERE e.[Nr] = @Nr;

        SET @ConnectionId = (SELECT [ConnectionId] FROM [integration].[Connection] WHERE [Name] = @CN);
        SET @DataSourceId = ISNULL((SELECT [DataSourceId] FROM [integration].[DataSource]
                                    WHERE [ConnectionId] = @ConnectionId AND [Name] = @DSN AND [Type] = @DST), 0);
        EXEC [integration].[sp_UpsertDataSource] @ConnectionId = @ConnectionId, @DataSourceId = @DataSourceId, @Name = @DSN,
             @Namespace = @NS, @Type = @DST, @Description = @Description, @LoadGroup = @LG, @IsActive = 1;
        SET @DataSourceId = (SELECT [DataSourceId] FROM [integration].[DataSource]
                             WHERE [ConnectionId] = @ConnectionId AND [Name] = @DSN AND [Type] = @DST);

        EXEC [integration].[sp_UpsertLandingzoneBronzeSilver] @DataSourceId = @DataSourceId, @WorkspaceGuid = @WsGuid,
             @SourceSchema = @SS, @SourceName = @SN, @TargetSchema = @TS, @TargetName = @TN, @SourceCustomSelect = '',
             @FileName = @FN, @FilePath = 'fmd', @FileType = @FT, @IsIncremental = @Inc, @IsIncrementalColumn = @IncCol,
             @CustomNotebookName = @NB, @PrimaryKeys = @PK;

        SET @EntityId = (SELECT le.[LandingzoneEntityId]
                         FROM [integration].[LandingzoneEntity] le
                         JOIN [integration].[Lakehouse] l ON l.[LakehouseId] = le.[LakehouseId]
                         WHERE l.[WorkspaceGuid] = @WsGuid AND le.[DataSourceId] = @DataSourceId
                           AND le.[SourceSchema] = @SS AND le.[SourceName] = @SN);

        UPDATE [integration].[LandingzoneEntity] SET [IsActive] = @Act WHERE [LandingzoneEntityId] = @EntityId;

        -- HistoryDays: a start watermark for a new incremental entity, in the format the load pipelines write
        -- (yyyy-mm-dd hh:mi:ss.mmm). Never overwrites a watermark that is already there.
        IF @HD IS NOT NULL AND @Inc = 1
           AND NOT EXISTS (SELECT 1 FROM [execution].[LandingzoneEntityLastLoadValue] WHERE [LandingzoneEntityId] = @EntityId)
            INSERT INTO [execution].[LandingzoneEntityLastLoadValue] ([LandingzoneEntityId], [LoadValue], [LastLoadDatetime])
            VALUES (@EntityId, CONVERT(VARCHAR(23), DATEADD(DAY, -@HD, CAST(CAST(SYSUTCDATETIME() AS DATE) AS DATETIME2(3))), 121), NULL);

        SET @Nr += 1;
    END
    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;

-- 3. Result: the listed entities as they are now in the configuration database, for this environment.
SELECT e.[Source], b.[DataSourceName], e.[SourceSchema], e.[SourceName], le.[LandingzoneEntityId], le.[IsActive], ds.[LoadGroup],
       lv.[LoadValue] AS [Watermark], CASE WHEN v.[EntityId] IS NULL THEN 'no' ELSE 'yes' END AS [InLoadView]
FROM @Entities e
JOIN @Bound b ON b.[Source] = e.[Source]
JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
JOIN [integration].[DataSource] ds ON ds.[ConnectionId] = c.[ConnectionId] AND ds.[Name] = b.[DataSourceName] AND ds.[Type] = b.[DataSourceType]
JOIN [integration].[LandingzoneEntity] le ON le.[DataSourceId] = ds.[DataSourceId] AND le.[SourceSchema] = e.[SourceSchema] AND le.[SourceName] = e.[SourceName]
JOIN [integration].[Lakehouse] l ON l.[LakehouseId] = le.[LakehouseId] AND l.[WorkspaceGuid] = @WsGuid
LEFT JOIN [execution].[LandingzoneEntityLastLoadValue] lv ON lv.[LandingzoneEntityId] = le.[LandingzoneEntityId]
LEFT JOIN [execution].[vw_LoadSourceToLandingzone] v ON v.[EntityId] = le.[LandingzoneEntityId]
ORDER BY e.[Source], e.[SourceSchema], e.[SourceName];
