-- Registreert bronnen en entiteiten in de configdb voor één omgeving. Herhaalbaar.
--
-- Gebruik: kopieer dit bestand naar de klantrepo, vul @E in en draai het per omgeving,
-- na de setup en na elke promotie naar die omgeving (registraties gaan niet mee met een promotie):
--
--   sqlcmd -S <server> -d <database> --authentication-method ActiveDirectoryAzCli -b \
--          -v DataWorkspace="<PREFIX> INTEGRATION DATA (T)" -i registreer_entiteiten.sql
--
-- - Alles of niets: bij een fout wordt niets geregistreerd.
-- - De lijst is de waarheid voor LoadGroup (per bron) en IsActive (per entiteit). Zet een entiteit
--   uit met IsActive = 0 in de lijst, niet met de hand in de database, anders zet de volgende run hem weer aan.
-- - Een bestaande entiteit wordt gevonden op bron + SourceSchema + SourceName. Een andere SourceName
--   geeft een nieuwe entiteit (zie 11_troubleshooting, "Herregistratie onder een andere DataSource").
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @DataWorkspace NVARCHAR(200) = N'$(DataWorkspace)';
DECLARE @Description   NVARCHAR(200) = N'Geregistreerd met registreer_entiteiten.sql';

DECLARE @E TABLE ([Nr] INT IDENTITY, [ConnectionName] NVARCHAR(200), [DataSourceName] NVARCHAR(100), [Namespace] VARCHAR(100),
                  [DataSourceType] VARCHAR(30), [LoadGroup] VARCHAR(50), [SourceSchema] NVARCHAR(100), [SourceName] NVARCHAR(200),
                  [TargetSchema] NVARCHAR(100), [TargetName] NVARCHAR(200), [FileName] NVARCHAR(200), [FileType] NVARCHAR(20),
                  [IsIncremental] BIT, [IsIncrementalColumn] NVARCHAR(50), [CustomNotebookName] VARCHAR(200),
                  [PrimaryKeys] NVARCHAR(200), [IsActive] BIT);

-- ===== Entiteiten (vul in) =====================================================================================
-- FileName = <TargetSchema>_<TargetName> is de gebruikelijke keuze. CustomNotebookName alleen bij type NOTEBOOK.
INSERT INTO @E ([ConnectionName],[DataSourceName],[Namespace],[DataSourceType],[LoadGroup],[SourceSchema],[SourceName],
                [TargetSchema],[TargetName],[FileName],[FileType],[IsIncremental],[IsIncrementalColumn],[CustomNotebookName],
                [PrimaryKeys],[IsActive]) VALUES
 (N'CON_FMD_<BRON>', N'<BronDatabase>', '<ns>', 'ASQL_01', '', N'Sales', N'Customer', N'Sales', N'Customer', N'Sales_Customer', N'parquet', 0, NULL, NULL, N'CustomerID', 1)
;
-- ===============================================================================================================

-- 1. Controles vooraf: niets wordt geschreven als er één faalt.
-- Zonder -v DataWorkspace stopt sqlcmd zelf; buiten sqlcmd blijft de variabele staan en faalt de check hieronder.
DECLARE @WsGuid UNIQUEIDENTIFIER = (SELECT [WorkspaceGuid] FROM [integration].[Workspace] WHERE [Name] = @DataWorkspace);
IF @WsGuid IS NULL OR NOT EXISTS (SELECT 1 FROM [integration].[Lakehouse] WHERE [WorkspaceGuid] = @WsGuid AND [Name] = 'LH_DATA_LANDINGZONE')
    THROW 50002, 'Workspace of LH_DATA_LANDINGZONE niet geregistreerd: draai eerst de setup voor deze omgeving.', 1;

DECLARE @Fout NVARCHAR(2000);
SELECT @Fout = STRING_AGG(CONCAT([SourceSchema], '.', [SourceName], ': ', [Reden]), '; ')
FROM (
    SELECT e.[SourceSchema], e.[SourceName], N'connectie ' + e.[ConnectionName] + N' niet geregistreerd' AS [Reden]
    FROM @E e WHERE NOT EXISTS (SELECT 1 FROM [integration].[Connection] c WHERE c.[Name] = e.[ConnectionName])
    UNION ALL
    SELECT [SourceSchema], [SourceName], N'IsIncrementalColumn is verplicht bij IsIncremental = 1'
    FROM @E WHERE [IsIncremental] = 1 AND ISNULL([IsIncrementalColumn], '') = ''
    UNION ALL
    SELECT [SourceSchema], [SourceName], N'PrimaryKeys is leeg' FROM @E WHERE ISNULL([PrimaryKeys], '') = ''
    UNION ALL
    SELECT [SourceSchema], [SourceName], N'CustomNotebookName is verplicht bij type NOTEBOOK'
    FROM @E WHERE [DataSourceType] = 'NOTEBOOK' AND ISNULL([CustomNotebookName], '') = ''
    UNION ALL
    SELECT MIN([SourceSchema]), MIN([SourceName]), N'twee keer in de lijst'
    FROM @E GROUP BY [DataSourceName], [DataSourceType], [SourceSchema], [SourceName] HAVING COUNT(*) > 1
    UNION ALL
    SELECT MIN([SourceSchema]), MIN([SourceName]), N'bron ' + [DataSourceName] + N' heeft meer dan één LoadGroup in de lijst'
    FROM @E GROUP BY [ConnectionName], [DataSourceName], [DataSourceType] HAVING COUNT(DISTINCT [LoadGroup]) > 1
) f;
IF @Fout IS NOT NULL THROW 50003, @Fout, 1;

-- 2. Registreren, in één transactie.
DECLARE @Nr INT = 1, @Max INT = (SELECT MAX([Nr]) FROM @E), @ConnectionId INT, @DataSourceId INT;
DECLARE @CN NVARCHAR(200), @DSN NVARCHAR(100), @NS VARCHAR(100), @DST VARCHAR(30), @LG VARCHAR(50), @SS NVARCHAR(100),
        @SN NVARCHAR(200), @TS NVARCHAR(100), @TN NVARCHAR(200), @FN NVARCHAR(200), @FT NVARCHAR(20), @Inc BIT,
        @IncCol NVARCHAR(50), @NB VARCHAR(200), @PK NVARCHAR(200), @Act BIT;

BEGIN TRY
    BEGIN TRANSACTION;
    WHILE @Nr <= @Max
    BEGIN
        SELECT @CN=[ConnectionName], @DSN=[DataSourceName], @NS=[Namespace], @DST=[DataSourceType], @LG=ISNULL([LoadGroup], ''),
               @SS=[SourceSchema], @SN=[SourceName], @TS=[TargetSchema], @TN=[TargetName], @FN=[FileName], @FT=[FileType],
               @Inc=[IsIncremental], @IncCol=[IsIncrementalColumn], @NB=[CustomNotebookName], @PK=[PrimaryKeys], @Act=[IsActive]
        FROM @E WHERE [Nr] = @Nr;

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

        UPDATE le SET [IsActive] = @Act
        FROM [integration].[LandingzoneEntity] le
        JOIN [integration].[Lakehouse] l ON l.[LakehouseId] = le.[LakehouseId]
        WHERE l.[WorkspaceGuid] = @WsGuid AND le.[DataSourceId] = @DataSourceId AND le.[SourceSchema] = @SS AND le.[SourceName] = @SN;

        SET @Nr += 1;
    END
    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;

-- 3. Resultaat: de entiteiten uit de lijst zoals ze nu in de configdb staan.
SELECT e.[SourceSchema], e.[SourceName], le.[LandingzoneEntityId], le.[IsActive], ds.[LoadGroup],
       CASE WHEN v.[EntityId] IS NULL THEN N'nee' ELSE N'ja' END AS [InLaadview]
FROM @E e
JOIN [integration].[Connection] c ON c.[Name] = e.[ConnectionName]
JOIN [integration].[DataSource] ds ON ds.[ConnectionId] = c.[ConnectionId] AND ds.[Name] = e.[DataSourceName] AND ds.[Type] = e.[DataSourceType]
JOIN [integration].[LandingzoneEntity] le ON le.[DataSourceId] = ds.[DataSourceId] AND le.[SourceSchema] = e.[SourceSchema] AND le.[SourceName] = e.[SourceName]
JOIN [integration].[Lakehouse] l ON l.[LakehouseId] = le.[LakehouseId] AND l.[WorkspaceGuid] = @WsGuid
LEFT JOIN [execution].[vw_LoadSourceToLandingzone] v ON v.[EntityId] = le.[LandingzoneEntityId]
ORDER BY e.[SourceSchema], e.[SourceName];
