

    CREATE VIEW [execution].[vw_LoadSourceToLandingzone]
    AS
    SELECT 
    LZE.[LandingzoneEntityId] AS [EntityId],
    DS.[DataSourceId] AS [DataSourceId],
    DS.[Name] AS [DataSourceName],
    DS.[Namespace] AS [DataSourceNamespace],
    DS.[Type] AS [DataSourceType],
    COALESCE(NULLIF(LZE.[LoadGroup], ''), DS.[LoadGroup]) AS [LoadGroup],
    C.[Type] AS [ConnectionType],
    C.[ConnectionGuid] AS [ConnectionGuid],
    [SourceSchema],
    [SourceName],
    [FilePath] + '/' + DS.[Namespace]+ '/' +LZE.[FileName] + FORMAT(GETUTCDATE(), '/yyyy/MM/dd') AS [TargetFilePath],
    LZE.[FileName] + '_' + FORMAT(GETUTCDATE(), 'yyyyMMddHHmm') + '.' + [FileType] AS [TargetFileName],
    LZE.[FileType] AS [TargetFileType],
    LH.[LakehouseGuid] AS [TargetLakehouseGuid],
    W.[WorkspaceGuid] AS [WorkspaceGuid],
    [IsIncremental],
    [IsIncrementalColumn],
    [LastLoadValue] = CASE
        WHEN C.[Type] IN ('SQL') THEN
            'SELECT CASE WHEN ' + CONVERT(NVARCHAR(1), CASE WHEN LZE.[IsIncremental] = '' OR ISNULL(LZE.[IsIncrementalColumn], '') = '' THEN 0 ELSE LZE.[IsIncremental] END) + ' = 1 
            THEN CONVERT(VARCHAR(23), MAX(' + (
                CASE WHEN ISNULL(LZE.[IsIncrementalColumn], '') = '' THEN '1'
                ELSE LZE.[IsIncrementalColumn]
            END) + '), 121) 
            ELSE CONVERT(VARCHAR(23), GETDATE(), 121) 
            END AS [LastLoadValue] 
            FROM ' + QUOTENAME(ISNULL(
                CASE WHEN LZE.[SourceSchema] != '' THEN LZE.[SourceSchema]
                END, 'Unknown')) + '.' + QUOTENAME(LZE.[SourceName])
            + ISNULL(' WHERE ' + QF.[Filter], '')
        -- Snowflake: alias tussen aanhalingstekens, anders geeft Snowflake LASTLOADVALUE terug.
        -- Beperking: de watermarkkolom moet DATE of TIMESTAMP zijn (cast naar TIMESTAMP_NTZ); een numerieke kolom faalt in de copy.
        WHEN C.[Type] = 'SNOWFLAKE' THEN
            'SELECT TO_VARCHAR(' +
            CASE WHEN LZE.[IsIncremental] = 1 AND ISNULL(LZE.[IsIncrementalColumn], '') <> ''
                THEN 'MAX("' + REPLACE(LZE.[IsIncrementalColumn], '"', '""') + '")::TIMESTAMP_NTZ, ''YYYY-MM-DD HH24:MI:SS.FF3'') AS "LastLoadValue" FROM ' + SF.[SourceObject] + ISNULL(' WHERE ' + QF.[Filter], '')
                ELSE 'CURRENT_TIMESTAMP()::TIMESTAMP_NTZ, ''YYYY-MM-DD HH24:MI:SS.FF3'') AS "LastLoadValue"'
            END
        ELSE
            LZELV.[LoadValue]
    END,
    [SourceDataRetrieval] = CASE
        -- SourceColumns (kolomlijst) en SourceFilter (predicaat) per tabel; de incrementele voorwaarde komt erbij met AND.
        WHEN C.[Type] = 'SNOWFLAKE' THEN
            'SELECT ' + QF.[Columns] + ' FROM ' + SF.[SourceObject] +
            ISNULL(' WHERE ' + NULLIF(CONCAT_WS(' AND ',
                CASE WHEN LZE.[IsIncremental] = 1 AND ISNULL(LZE.[IsIncrementalColumn], '') <> '' AND LZELV.[LoadValue] IS NOT NULL THEN
                    '"' + REPLACE(LZE.[IsIncrementalColumn], '"', '""') + '" > ''' + REPLACE(LZELV.[LoadValue], '''', '''''') + ''''
                END, QF.[Filter]), ''), '')
        WHEN LZE.[IsIncremental] = 1 THEN
            'SELECT ' + QF.[Columns] + ' FROM ' + QUOTENAME(ISNULL(CASE WHEN LZE.[SourceSchema] != '' THEN LZE.[SourceSchema] END, 'Unknown')) + '.' + QUOTENAME(LZE.[SourceName]) + 
            ISNULL(' WHERE ' + NULLIF(CONCAT_WS(' AND ',
                CASE WHEN ISNULL(LZE.[IsIncrementalColumn], '') <> '' AND TRY_CONVERT(VARCHAR, [LoadValue]) IS NOT NULL THEN
                    LZE.[IsIncrementalColumn] + ' > ''' + TRY_CONVERT(VARCHAR, ISNULL([LoadValue], '1900-01-01')) + ''''
                END, QF.[Filter]), ''), '')
        WHEN ISNULL(LZE.[IsIncremental], 0) = 0 THEN 
            'SELECT ' + QF.[Columns] + ' FROM ' + QUOTENAME(ISNULL(CASE WHEN LZE.[SourceSchema] != '' THEN LZE.[SourceSchema] END, 'Unknown')) + '.' + QUOTENAME(LZE.[SourceName]) 
            + ISNULL(' WHERE ' + QF.[Filter], '')
        ELSE ''
    END,
CustomNotebookName
FROM [integration].[LandingzoneEntity] LZE
INNER JOIN [integration].[Lakehouse] LH
    ON LZE.[LakehouseId] = LH.[LakehouseId]
INNER JOIN [integration].[Workspace] W
    ON W.[WorkspaceGuid] = LH.[WorkspaceGuid]
INNER JOIN [integration].[DataSource] DS
    ON DS.[DataSourceId] = LZE.[DataSourceId]
INNER JOIN [integration].[Connection] C
    ON DS.[ConnectionId] = C.[ConnectionId]
LEFT JOIN [execution].[LandingzoneEntityLastLoadValue] LZELV
    ON LZELV.[LandingzoneEntityId] = LZE.[LandingzoneEntityId]
-- Snowflake: "DATABASE"."SCHEMA"."TABEL", hoofdlettergevoelig. DataSource.Name is de database.
CROSS APPLY (SELECT '"' + REPLACE(DS.[Name], '"', '""') + '"."'
    + REPLACE(ISNULL(CASE WHEN LZE.[SourceSchema] != '' THEN LZE.[SourceSchema] END, 'Unknown'), '"', '""') + '"."'
    + REPLACE(LZE.[SourceName], '"', '""') + '"' AS [SourceObject]) SF
-- Kolomlijst en filter van deze tabel. Kolommen: SourceColumns, gescheiden door komma's, in die volgorde; leeg = '*'.
-- Een naam wordt geciteerd zoals de bron dat wil (SQL: [naam]; Snowflake: "naam", hoofdlettergevoelig). Een filter is een predicaat zonder WHERE.
CROSS APPLY (SELECT
    ISNULL(CASE WHEN ISNULL(LTRIM(RTRIM(LZE.[SourceColumns])), '') = '' THEN NULL ELSE (
        SELECT STRING_AGG(q.[Name], ', ') WITHIN GROUP (ORDER BY q.[Nr])
        FROM (SELECT CAST(j.[key] AS INT) AS [Nr],
                     CASE WHEN C.[Type] = 'SNOWFLAKE'
                          THEN '"' + REPLACE(LTRIM(RTRIM(j.[value])), '"', '""') + '"'
                          ELSE QUOTENAME(LTRIM(RTRIM(j.[value]))) END AS [Name]
              FROM OPENJSON('["' + REPLACE(REPLACE(REPLACE(LZE.[SourceColumns], CHAR(92), CHAR(92) + CHAR(92)), '"', CHAR(92) + '"'), ',', '","') + '"]') j
              WHERE LTRIM(RTRIM(j.[value])) <> '') q) END, '*') AS [Columns],
    CASE WHEN ISNULL(LTRIM(RTRIM(LZE.[SourceFilter])), '') = '' THEN NULL
         ELSE '(' + LTRIM(RTRIM(LZE.[SourceFilter])) + ')' END AS [Filter]) QF
WHERE 1 = 1
    AND LZE.[IsActive] = 1

GO

