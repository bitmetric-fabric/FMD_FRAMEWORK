-- Registers sources and entities for one domain's DATA workspace in one environment. Repeatable.
-- The only registration route (ADR-018; it replaced the sqlcmd template registreer_entiteiten.sql): one
-- "all or nothing" transaction, driven by JSON from NB_REGISTRATIE, with the DATA workspace resolved
-- from @Domain + @Environment instead of typed by name (removes the customer-prefix guesswork and the
-- mismatch risk the template had, E-R5).
--
-- @Domain: the workspace name without DATA/(D)/(T)/(A), e.g. 'INTEGRATION' or 'FINANCE'.
-- @Environment: D, T, A or P. Resolves to the one workspace matching '<DOMAIN> DATA%' with that
-- suffix (none for P) and an active LH_DATA_LANDINGZONE. Errors if that is not exactly one workspace.
-- Or DEV_<NAME>: a developer's own DATA workspace, named DEV_<NAME>_<prefix>_<DOMAIN>_DATA (so
-- 'DEV_MITCHELL' finds DEV_MITCHELL_TRIAL_INTEGRATION_DATA), registered in the configdb like any other.
-- It uses the bindings of D, because a developer workspace reads from the same source as Dev. The
-- data source rows are shared with D: a DEV_ run that changes a source's LoadGroup or Namespace changes it for D.
-- @Sources / @Entities: JSON arrays. Per-column rules (HistoryDays, LoadGroup, IsHistorized, ...): see
-- the markdown of NB_REGISTRATIE and the docstring of register() in NB_FMD_REGISTRATION_FUNCTIONS.
-- An unknown field in a row is an error: a typo in a key would be silently ignored by JSON otherwise.
-- BronzeCleansingRules / SilverCleansingRules (optional, a JSON array of {"function", "columns", "parameters"},
-- as NB_FMD_DQ_CLEANSING reads them): a row without the field leaves the rules as they are; with the field the
-- list is the truth, and [] or null clears them. A rule that is not valid is an error; a function that is not
-- built in is only a warning in the dry run (it may be registered in NB_FMD_CUSTOM_DQ_CLEANSING).
-- exclude_rows needs "columns" and a non-empty "parameters.values", or the layer would fail on every run.
-- @DryRun: 1 runs every check and the registration, then rolls back and returns a preview
-- (New / Changed / Unchanged per entity with what a Changed changes, plus active entities in this
-- scope that the list omits)
-- instead of committing.
CREATE PROCEDURE [integration].[sp_RegisterEntities](
    @Domain NVARCHAR(100),
    @Environment VARCHAR(100),
    @Sources NVARCHAR(MAX),
    @Entities NVARCHAR(MAX),
    @DryRun BIT = 0
)
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Description NVARCHAR(200) = N'Registered with sp_RegisterEntities';

    -- DEV_<NAME>: letters, digits, '_' and '-' only. The name goes into a LIKE pattern below, so a
    -- wildcard ('%', '[') must never get through.
    DECLARE @IsDev BIT = IIF(@Environment LIKE 'DEV[_]_%' AND @Environment NOT LIKE '%[^A-Za-z0-9_-]%', 1, 0);
    IF @Environment NOT IN ('D', 'T', 'A', 'P') AND @IsDev = 0
        THROW 50002, 'sp_RegisterEntities: @Environment must be D, T, A, P or DEV_<NAME> (letters, digits, underscore and hyphen).', 1;
    -- A developer workspace reads from the same source as Dev, so it uses the D bindings.
    DECLARE @BindingEnv VARCHAR(10) = IIF(@IsDev = 1, 'D', @Environment);
    IF ISJSON(@Sources) = 0
        THROW 50002, 'sp_RegisterEntities: @Sources is not valid JSON.', 1;
    IF ISJSON(@Entities) = 0
        THROW 50002, 'sp_RegisterEntities: @Entities is not valid JSON.', 1;

    -- ===== Resolve the DATA workspace from @Domain + @Environment ============================
    DECLARE @WsCandidates TABLE ([WorkspaceGuid] UNIQUEIDENTIFIER, [Name] VARCHAR(100));
    INSERT INTO @WsCandidates
    SELECT W.[WorkspaceGuid], W.[Name]
    FROM [integration].[Workspace] W
    JOIN [integration].[Lakehouse] L ON L.[WorkspaceGuid] = W.[WorkspaceGuid] AND L.[Name] = 'LH_DATA_LANDINGZONE' AND L.[IsActive] = 1
    -- Workspace names carry a customer prefix ("FMD_TRIAL INTEGRATION DATA (D)"), so the domain
    -- is matched as a substring, not an exact prefix. Getest in FMD_TRIAL, 2026-10-13: zonder de
    -- leading '%' vond dit niets, want elke workspace heeft een prefix voor het domein.
    WHERE (@IsDev = 0
           AND UPPER(W.[Name]) LIKE '%' + UPPER(@Domain) + ' DATA%'
           AND (
                (@Environment IN ('D', 'T', 'A') AND W.[Name] LIKE '% (' + @Environment + ')')
             OR (@Environment = 'P' AND W.[Name] NOT LIKE '% (D)' AND W.[Name] NOT LIKE '% (T)' AND W.[Name] NOT LIKE '% (A)')
           ))
       -- A developer workspace is named DEV_<NAME>_<prefix>_<DOMAIN>_DATA: underscores, no suffix.
       -- Every '_' is written as '[_]' so it matches a literal underscore, not any character.
       OR (@IsDev = 1
           AND UPPER(W.[Name]) LIKE REPLACE(UPPER(@Environment), '_', '[_]') + '[_]%[_]' + REPLACE(REPLACE(UPPER(@Domain), ' ', '_'), '_', '[_]') + '[_]DATA');

    DECLARE @WsCount INT = (SELECT COUNT(*) FROM @WsCandidates);
    IF @WsCount = 0
        -- No literal '%' here: a THROW message with one renders blank via sqlcmd/ODBC Driver 18
        -- (getest in FMD_TRIAL, 2026-10-13; PRINT shows the same string fine, THROW does not).
        THROW 50002, 'sp_RegisterEntities: no DATA workspace found for this @Domain and @Environment (workspace name containing "<DOMAIN> DATA", with the (D)/(T)/(A) suffix or none for P; for DEV_<NAME> a workspace named DEV_<NAME>_<prefix>_<DOMAIN>_DATA; and an active LH_DATA_LANDINGZONE).', 1;
    IF @WsCount > 1
    BEGIN
        DECLARE @Candidates NVARCHAR(500) = (SELECT STRING_AGG([Name], ', ') FROM @WsCandidates);
        DECLARE @WsError NVARCHAR(2000) = CONCAT('sp_RegisterEntities: more than one DATA workspace matches this @Domain and @Environment: ', @Candidates, '. Use a more specific @Domain.');
        THROW 50002, @WsError, 1;
    END
    DECLARE @WsGuid UNIQUEIDENTIFIER, @WsName VARCHAR(100);
    SELECT @WsGuid = [WorkspaceGuid], @WsName = [Name] FROM @WsCandidates;
    SELECT @WsName AS [ResolvedWorkspace], @WsGuid AS [WorkspaceGuid];

    -- ===== Parse the lists =====================================================================
    DECLARE @SourcesT TABLE ([Environment] VARCHAR(10), [Source] NVARCHAR(100), [ConnectionName] NVARCHAR(200),
                             [DataSourceName] NVARCHAR(100), [Namespace] VARCHAR(100), [DataSourceType] VARCHAR(30),
                             [LoadGroup] VARCHAR(50), [HistoryDays] INT);
    INSERT INTO @SourcesT
    SELECT [Environment], [Source], [ConnectionName], [DataSourceName], [Namespace], [DataSourceType], [LoadGroup], [HistoryDays]
    FROM OPENJSON(@Sources)
        WITH (
            [Environment]     VARCHAR(10)   '$.Environment',
            [Source]          NVARCHAR(100) '$.Source',
            [ConnectionName]  NVARCHAR(200) '$.ConnectionName',
            [DataSourceName]  NVARCHAR(100) '$.DataSourceName',
            [Namespace]       VARCHAR(100)  '$.Namespace',
            [DataSourceType]  VARCHAR(30)   '$.DataSourceType',
            [LoadGroup]       VARCHAR(50)   '$.LoadGroup',
            [HistoryDays]     INT           '$.HistoryDays'
        );

    DECLARE @EntitiesT TABLE ([Nr] INT IDENTITY, [Source] NVARCHAR(100), [SourceSchema] NVARCHAR(100), [SourceName] NVARCHAR(200),
                             [TargetSchema] NVARCHAR(100), [TargetName] NVARCHAR(200), [FileName] NVARCHAR(200), [FileType] NVARCHAR(20),
                             [IsIncremental] BIT, [IsIncrementalColumn] NVARCHAR(50), [CustomNotebookName] VARCHAR(200),
                             [PrimaryKeys] NVARCHAR(200), [IsActive] BIT, [IsHistorized] BIT,
                             [BronzeRulesSet] BIT, [BronzeRules] NVARCHAR(MAX), [BronzeRulesText] NVARCHAR(MAX),
                             [SilverRulesSet] BIT, [SilverRules] NVARCHAR(MAX), [SilverRulesText] NVARCHAR(MAX));
    INSERT INTO @EntitiesT ([Source], [SourceSchema], [SourceName], [TargetSchema], [TargetName], [FileName], [FileType],
                            [IsIncremental], [IsIncrementalColumn], [CustomNotebookName], [PrimaryKeys], [IsActive], [IsHistorized],
                            [BronzeRulesSet], [BronzeRules], [BronzeRulesText], [SilverRulesSet], [SilverRules], [SilverRulesText])
    SELECT
        e.[Source], e.[SourceSchema], e.[SourceName],
        ISNULL(NULLIF(e.[TargetSchema], ''), e.[SourceSchema]) AS [TargetSchema],
        ISNULL(NULLIF(e.[TargetName], ''), e.[SourceName]) AS [TargetName],
        ISNULL(NULLIF(e.[FileName], ''), CONCAT(ISNULL(NULLIF(e.[TargetSchema], ''), e.[SourceSchema]), '_', ISNULL(NULLIF(e.[TargetName], ''), e.[SourceName]))) AS [FileName],
        ISNULL(NULLIF(e.[FileType], ''), 'parquet') AS [FileType],
        ISNULL(e.[IsIncremental], 0) AS [IsIncremental],
        e.[IsIncrementalColumn], e.[CustomNotebookName], e.[PrimaryKeys],
        ISNULL(e.[IsActive], 1) AS [IsActive],
        e.[IsHistorized],
        JSON_PATH_EXISTS(r.[value], '$.BronzeCleansingRules'),
        CASE WHEN REPLACE(REPLACE(REPLACE(e.[BronzeRules], ' ', ''), CHAR(13), ''), CHAR(10), '') = '[]' THEN NULL ELSE e.[BronzeRules] END,
        e.[BronzeRulesText],
        JSON_PATH_EXISTS(r.[value], '$.SilverCleansingRules'),
        CASE WHEN REPLACE(REPLACE(REPLACE(e.[SilverRules], ' ', ''), CHAR(13), ''), CHAR(10), '') = '[]' THEN NULL ELSE e.[SilverRules] END,
        e.[SilverRulesText]
    FROM OPENJSON(@Entities) r
    CROSS APPLY OPENJSON(r.[value])
        WITH (
            [Source]              NVARCHAR(100) '$.Source',
            [SourceSchema]        NVARCHAR(100) '$.SourceSchema',
            [SourceName]          NVARCHAR(200) '$.SourceName',
            [TargetSchema]        NVARCHAR(100) '$.TargetSchema',
            [TargetName]          NVARCHAR(200) '$.TargetName',
            [FileName]            NVARCHAR(200) '$.FileName',
            [FileType]            NVARCHAR(20)  '$.FileType',
            [IsIncremental]       BIT           '$.IsIncremental',
            [IsIncrementalColumn] NVARCHAR(50)  '$.IsIncrementalColumn',
            [CustomNotebookName]  VARCHAR(200)  '$.CustomNotebookName',
            [PrimaryKeys]         NVARCHAR(200) '$.PrimaryKeys',
            [IsActive]            BIT           '$.IsActive',
            [IsHistorized]        BIT           '$.IsHistorized',
            [BronzeRules]         NVARCHAR(MAX) '$.BronzeCleansingRules' AS JSON,
            [BronzeRulesText]     NVARCHAR(MAX) '$.BronzeCleansingRules',
            [SilverRules]         NVARCHAR(MAX) '$.SilverCleansingRules' AS JSON,
            [SilverRulesText]     NVARCHAR(MAX) '$.SilverCleansingRules'
        ) e
    ORDER BY CAST(r.[key] AS INT);

    -- ===== 0. Unknown fields: a typo in a key is silently ignored by JSON otherwise ===========
    DECLARE @KeyError NVARCHAR(2000);
    SELECT @KeyError = STRING_AGG(CONVERT(NVARCHAR(MAX), [Item]), '; ')
    FROM (
        SELECT CONCAT('Sources[', s.[key], ']: unknown field ', k.[key]) AS [Item]
        FROM OPENJSON(@Sources) s
        CROSS APPLY OPENJSON(s.[value]) k
        WHERE k.[key] NOT IN ('Environment', 'Source', 'ConnectionName', 'DataSourceName', 'Namespace', 'DataSourceType', 'LoadGroup', 'HistoryDays')
        UNION ALL
        SELECT CONCAT('Entities[', e.[key], ']: unknown field ', k.[key])
        FROM OPENJSON(@Entities) e
        CROSS APPLY OPENJSON(e.[value]) k
        WHERE k.[key] NOT IN ('Source', 'SourceSchema', 'SourceName', 'TargetSchema', 'TargetName', 'FileName', 'FileType',
                              'IsIncremental', 'IsIncrementalColumn', 'CustomNotebookName', 'PrimaryKeys', 'IsActive', 'IsHistorized',
                              'BronzeCleansingRules', 'SilverCleansingRules')
    ) f;
    IF @KeyError IS NOT NULL THROW 50003, @KeyError, 1;

    -- The binding that applies in this environment: its own row, otherwise the '*' row. DEV_<NAME> uses D.
    DECLARE @Bound TABLE ([Source] NVARCHAR(100), [ConnectionName] NVARCHAR(200), [DataSourceName] NVARCHAR(100), [Namespace] VARCHAR(100),
                          [DataSourceType] VARCHAR(30), [LoadGroup] VARCHAR(50), [HistoryDays] INT);
    INSERT INTO @Bound
    SELECT s.[Source], s.[ConnectionName], s.[DataSourceName], s.[Namespace], s.[DataSourceType], ISNULL(s.[LoadGroup], ''), s.[HistoryDays]
    FROM @SourcesT s
    WHERE s.[Environment] = @BindingEnv
       OR (s.[Environment] = '*' AND NOT EXISTS (SELECT 1 FROM @SourcesT x WHERE x.[Source] = s.[Source] AND x.[Environment] = @BindingEnv));

    -- ===== 1. Checks: the same ones as the template, plus the metadata check below ============
    DECLARE @Error NVARCHAR(2000);
    SELECT @Error = STRING_AGG(CONVERT(NVARCHAR(MAX), CONCAT([Item], ': ', [Reason])), '; ')
    FROM (
        SELECT CONCAT([Environment], '/', [Source]) AS [Item], N'unknown environment; use *, D, T, A or P' AS [Reason]
        FROM @SourcesT WHERE [Environment] NOT IN ('*', 'D', 'T', 'A', 'P')
        UNION ALL
        SELECT CONCAT(MIN([Environment]), '/', [Source]), N'source bound twice for the same environment'
        FROM @SourcesT GROUP BY [Environment], [Source] HAVING COUNT(*) > 1
        UNION ALL
        SELECT [Source], N'Namespace differs between environments; it must be the same, or Silver and Gold get other table names'
        FROM @SourcesT GROUP BY [Source] HAVING COUNT(DISTINCT [Namespace]) > 1
        UNION ALL
        SELECT [Source], N'HistoryDays must be 1 or more' FROM @Bound WHERE [HistoryDays] < 1
        UNION ALL
        SELECT b.[Source], N'connection ' + b.[ConnectionName] + N' not registered'
        FROM @Bound b WHERE NOT EXISTS (SELECT 1 FROM [integration].[Connection] c WHERE c.[Name] = b.[ConnectionName])
        UNION ALL
        SELECT MIN(s.[Source]), N'data source ' + s.[DataSourceName] + N' has more than one LoadGroup in @Sources; '
             + N'environments that bind to the same connection, database and type share one LoadGroup'
        FROM @SourcesT s GROUP BY s.[ConnectionName], s.[DataSourceName], s.[DataSourceType] HAVING COUNT(DISTINCT ISNULL(s.[LoadGroup], '')) > 1
        UNION ALL
        SELECT b.[Source], N'DataSourceType ' + b.[DataSourceType] + N' does not fit the type of connection ' + b.[ConnectionName]
        FROM @Bound b
        WHERE EXISTS (SELECT 1 FROM [integration].[Connection] c WHERE c.[Name] = b.[ConnectionName])
          AND NOT EXISTS (SELECT 1 FROM [integration].[Connection] c
                          JOIN (VALUES ('SQL', 'ASQL_01'), ('SQL', 'ASQL_02'), ('AZURESQLMI', 'SQLMI_01'), ('ORACLE', 'ORACLE_01'),
                                       ('ADLS', 'ADLS_01'), ('ONELAKE', 'ONELAKE_TABLES_01'), ('ONELAKE', 'ONELAKE_FILES_01'),
                                       ('SFTP', 'SFTP_01'), ('FTP', 'FTP_01'), ('ADF', 'ADF'), ('NOTEBOOK', 'NOTEBOOK'),
                                       ('SNOWFLAKE', 'SNOWFLAKE_01')) t([ConnectionType], [DataSourceType])
                            ON t.[ConnectionType] = c.[Type]
                          WHERE c.[Name] = b.[ConnectionName] AND t.[DataSourceType] = b.[DataSourceType])
        UNION ALL
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'source ' + e.[Source] + N' has no binding for environment ' + @BindingEnv
        FROM @EntitiesT e WHERE NOT EXISTS (SELECT 1 FROM @Bound b WHERE b.[Source] = e.[Source])
        UNION ALL
        SELECT CONCAT([SourceSchema], '.', [SourceName]), N'IsIncrementalColumn is required when IsIncremental = 1'
        FROM @EntitiesT WHERE [IsIncremental] = 1 AND ISNULL([IsIncrementalColumn], '') = ''
        UNION ALL
        SELECT CONCAT([SourceSchema], '.', [SourceName]), N'PrimaryKeys is empty' FROM @EntitiesT WHERE ISNULL([PrimaryKeys], '') = ''
        UNION ALL
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'CustomNotebookName is required for type NOTEBOOK'
        FROM @EntitiesT e JOIN @Bound b ON b.[Source] = e.[Source]
        WHERE b.[DataSourceType] = 'NOTEBOOK' AND ISNULL(e.[CustomNotebookName], '') = ''
        UNION ALL
        SELECT CONCAT(MIN([SourceSchema]), '.', MIN([SourceName])), N'listed twice'
        FROM @EntitiesT GROUP BY [Source], [SourceSchema], [SourceName] HAVING COUNT(*) > 1
        UNION ALL
        -- Cleansing rules: a JSON array of objects, as handle_cleansing_functions reads them.
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), CONCAT(l.[Layer], N'CleansingRules must be a JSON array of rules, not a string or an object')
        FROM @EntitiesT e
        CROSS APPLY (VALUES ('Bronze', e.[BronzeRulesSet], e.[BronzeRules], e.[BronzeRulesText]),
                            ('Silver', e.[SilverRulesSet], e.[SilverRules], e.[SilverRulesText])) l([Layer], [IsSet], [Rules], [Text])
        WHERE l.[IsSet] = 1 AND ((l.[Text] IS NOT NULL) OR (l.[Rules] IS NOT NULL AND LEFT(LTRIM(l.[Rules]), 1) <> '['))
        UNION ALL
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]),
               CONCAT(l.[Layer], N'CleansingRules[', CONVERT(NVARCHAR(10), x.[key]) COLLATE DATABASE_DEFAULT, N']: ',
                      CASE WHEN x.[type] <> 5 THEN N'a rule must be an object with "function", "columns" and "parameters"'
                           WHEN ISNULL(JSON_VALUE(x.[value], '$.function'), '') = '' THEN N'"function" is missing'
                           WHEN EXISTS (SELECT 1 FROM OPENJSON(x.[value]) k WHERE k.[key] = 'columns' AND k.[type] NOT IN (0, 1))
                                THEN N'"columns" must be text, columns separated by a semicolon'
                           ELSE N'"parameters" must be an object' END)
        FROM @EntitiesT e
        CROSS APPLY (VALUES ('Bronze', e.[BronzeRules]), ('Silver', e.[SilverRules])) l([Layer], [Rules])
        CROSS APPLY OPENJSON(CASE WHEN LEFT(LTRIM(l.[Rules]), 1) = '[' THEN l.[Rules] END) x
        WHERE x.[type] <> 5
           OR ISNULL(JSON_VALUE(x.[value], '$.function'), '') = ''
           OR EXISTS (SELECT 1 FROM OPENJSON(x.[value]) k WHERE k.[key] = 'columns' AND k.[type] NOT IN (0, 1))
           OR EXISTS (SELECT 1 FROM OPENJSON(x.[value]) k WHERE k.[key] = 'parameters' AND k.[type] NOT IN (0, 5))
        UNION ALL
        -- exclude_rows without a column or without a non-empty "values" would fail every run of the layer.
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]),
               CONCAT(l.[Layer], N'CleansingRules[', CONVERT(NVARCHAR(10), x.[key]) COLLATE DATABASE_DEFAULT, N']: ',
                      CASE WHEN ISNULL(JSON_VALUE(x.[value], '$.columns'), '') = '' THEN N'exclude_rows needs "columns"'
                           ELSE N'exclude_rows needs a non-empty "values" list in "parameters"' END)
        FROM @EntitiesT e
        CROSS APPLY (VALUES ('Bronze', e.[BronzeRules]), ('Silver', e.[SilverRules])) l([Layer], [Rules])
        CROSS APPLY OPENJSON(CASE WHEN LEFT(LTRIM(l.[Rules]), 1) = '[' THEN l.[Rules] END) x
        WHERE x.[type] = 5 AND JSON_VALUE(x.[value], '$.function') = 'exclude_rows'
          AND (ISNULL(JSON_VALUE(x.[value], '$.columns'), '') = ''
               OR (ISNULL(JSON_VALUE(x.[value], '$.parameters.values'), '') = ''
                   AND NOT EXISTS (SELECT 1 FROM OPENJSON(JSON_QUERY(x.[value], '$.parameters.values')) v WHERE ISNULL(v.[value], '') <> '')))
        UNION ALL
        -- Metadata check: only when PL_FMD_DISCOVER_SOURCE has already read this SCHEMA. Scoped to
        -- SourceSchema, not just the connection+database: a scoped discovery (@SchemaFilter) must
        -- not block an already-working entity in a schema nobody has discovered (found in
        -- FMD_TRIAL, 2026-10-13: discovering TPCH.REGION alone broke re-registering TPCH.CUSTOMER,
        -- which was never part of that discovery run). A Snowflake name must match the exact case
        -- the source reported (ADR-014); other sources compare case-insensitively.
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'not found by PL_FMD_DISCOVER_SOURCE for this schema; check the name and case'
        FROM @EntitiesT e JOIN @Bound b ON b.[Source] = e.[Source]
        JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
        WHERE EXISTS (SELECT 1 FROM [integration].[DiscoveredEntity]
                      WHERE [ConnectionId] = c.[ConnectionId] AND [DataSourceName] = b.[DataSourceName] AND [SourceSchema] = e.[SourceSchema])
          AND NOT EXISTS (
              SELECT 1 FROM [integration].[DiscoveredEntity] de
              WHERE de.[ConnectionId] = c.[ConnectionId] AND de.[DataSourceName] = b.[DataSourceName]
                AND (CASE WHEN b.[DataSourceType] = 'SNOWFLAKE_01'
                          THEN IIF(de.[SourceSchema] COLLATE Latin1_General_100_CS_AS = e.[SourceSchema] COLLATE Latin1_General_100_CS_AS
                                AND de.[SourceName] COLLATE Latin1_General_100_CS_AS = e.[SourceName] COLLATE Latin1_General_100_CS_AS, 1, 0)
                          ELSE IIF(de.[SourceSchema] = e.[SourceSchema] AND de.[SourceName] = e.[SourceName], 1, 0)
                     END) = 1)
        UNION ALL
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'PrimaryKeys column ' + pk.[value] + N' not found by PL_FMD_DISCOVER_SOURCE'
        FROM @EntitiesT e JOIN @Bound b ON b.[Source] = e.[Source]
        JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
        JOIN [integration].[DiscoveredEntity] de ON de.[ConnectionId] = c.[ConnectionId] AND de.[DataSourceName] = b.[DataSourceName]
            AND de.[SourceSchema] = e.[SourceSchema] AND de.[SourceName] = e.[SourceName]
        CROSS APPLY STRING_SPLIT(ISNULL(e.[PrimaryKeys], ''), ',') pk
        WHERE LTRIM(RTRIM(pk.[value])) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM OPENJSON(de.[Columns]) WITH ([Name] NVARCHAR(200) '$.Name') col
              WHERE (CASE WHEN b.[DataSourceType] = 'SNOWFLAKE_01'
                          THEN IIF(col.[Name] COLLATE Latin1_General_100_CS_AS = LTRIM(RTRIM(pk.[value])) COLLATE Latin1_General_100_CS_AS, 1, 0)
                          ELSE IIF(col.[Name] = LTRIM(RTRIM(pk.[value])), 1, 0)
                     END) = 1)
        UNION ALL
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'IsIncrementalColumn ' + e.[IsIncrementalColumn] + N' not found by PL_FMD_DISCOVER_SOURCE'
        FROM @EntitiesT e JOIN @Bound b ON b.[Source] = e.[Source]
        JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
        JOIN [integration].[DiscoveredEntity] de ON de.[ConnectionId] = c.[ConnectionId] AND de.[DataSourceName] = b.[DataSourceName]
            AND de.[SourceSchema] = e.[SourceSchema] AND de.[SourceName] = e.[SourceName]
        WHERE e.[IsIncremental] = 1 AND ISNULL(e.[IsIncrementalColumn], '') <> ''
          AND NOT EXISTS (
              SELECT 1 FROM OPENJSON(de.[Columns]) WITH ([Name] NVARCHAR(200) '$.Name') col
              WHERE (CASE WHEN b.[DataSourceType] = 'SNOWFLAKE_01'
                          THEN IIF(col.[Name] COLLATE Latin1_General_100_CS_AS = e.[IsIncrementalColumn] COLLATE Latin1_General_100_CS_AS, 1, 0)
                          ELSE IIF(col.[Name] = e.[IsIncrementalColumn], 1, 0)
                     END) = 1)
        UNION ALL
        -- Snowflake-beperking (ADR-014): de watermarkkolom moet DATE of TIMESTAMP zijn.
        SELECT CONCAT(e.[SourceSchema], '.', e.[SourceName]), N'IsIncrementalColumn ' + e.[IsIncrementalColumn] + N' is type ' + col.[Type] + N', must be DATE or TIMESTAMP for Snowflake'
        FROM @EntitiesT e JOIN @Bound b ON b.[Source] = e.[Source] AND b.[DataSourceType] = 'SNOWFLAKE_01'
        JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
        JOIN [integration].[DiscoveredEntity] de ON de.[ConnectionId] = c.[ConnectionId] AND de.[DataSourceName] = b.[DataSourceName]
            AND de.[SourceSchema] = e.[SourceSchema] AND de.[SourceName] = e.[SourceName]
        CROSS APPLY OPENJSON(de.[Columns]) WITH ([Name] NVARCHAR(200) '$.Name', [Type] VARCHAR(50) '$.Type') col
        WHERE e.[IsIncremental] = 1 AND col.[Name] COLLATE Latin1_General_100_CS_AS = e.[IsIncrementalColumn] COLLATE Latin1_General_100_CS_AS
          AND UPPER(col.[Type]) NOT LIKE 'DATE%' AND UPPER(col.[Type]) NOT LIKE 'TIMESTAMP%'
    ) f;
    IF @Error IS NOT NULL THROW 50003, @Error, 1;

    -- ===== 2. Dry-run preview: computed against the current state, before any write ===========
    DECLARE @Preview TABLE ([SourceSchema] NVARCHAR(100), [SourceName] NVARCHAR(200), [Action] VARCHAR(10), [Changes] NVARCHAR(2000), [Warning] NVARCHAR(2000));
    DECLARE @Orphans TABLE ([DataSourceName] NVARCHAR(100), [SourceSchema] NVARCHAR(100), [SourceName] NVARCHAR(200));
    IF @DryRun = 1
    BEGIN
        INSERT INTO @Preview
        SELECT e.[SourceSchema], e.[SourceName],
            CASE WHEN le.[LandingzoneEntityId] IS NULL THEN 'New'
                 WHEN chg.[Changes] <> '' THEN 'Changed'
                 ELSE 'Unchanged'
            END,
            CASE WHEN le.[LandingzoneEntityId] IS NOT NULL THEN chg.[Changes] END,
            NULLIF(CONCAT_WS('; ', wrn.[Unknown], wrn.[Rebuild]), '')
        FROM @EntitiesT e
        JOIN @Bound b ON b.[Source] = e.[Source]
        JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
        LEFT JOIN [integration].[DataSource] ds ON ds.[ConnectionId] = c.[ConnectionId] AND ds.[Name] = b.[DataSourceName] AND ds.[Type] = b.[DataSourceType]
        -- DataSourceId is shared by every environment bound to the same connection+database (by
        -- design, see the template header), so LandingzoneEntity must be scoped to @WsGuid's own
        -- LH_DATA_LANDINGZONE here too, same as the registration loop below (step 3). Without it,
        -- a source already registered in another environment's workspace fanned out into one
        -- Preview row per workspace instead of reflecting only @WsGuid (found in FMD_TRIAL, 2026-10-13).
        LEFT JOIN [integration].[Lakehouse] lh ON lh.[WorkspaceGuid] = @WsGuid AND lh.[Name] = 'LH_DATA_LANDINGZONE' AND lh.[IsActive] = 1
        LEFT JOIN [integration].[LandingzoneEntity] le ON le.[DataSourceId] = ds.[DataSourceId] AND le.[LakehouseId] = lh.[LakehouseId]
            AND le.[SourceSchema] = e.[SourceSchema] AND le.[SourceName] = e.[SourceName]
        LEFT JOIN [integration].[BronzeLayerEntity] ble ON ble.[LandingzoneEntityId] = le.[LandingzoneEntityId]
        LEFT JOIN [integration].[SilverLayerEntity] sle ON sle.[BronzeLayerEntityId] = ble.[BronzeLayerEntityId]
        -- What a "Changed" changes, old -> new, so the dry run shows e.g. that an omitted IsHistorized
        -- turns history off (ADR-016: an empty field means 0, also for an entity registered with 1).
        CROSS APPLY (SELECT CONCAT_WS(', ',
            CASE WHEN le.[FileName] <> e.[FileName] THEN CONCAT('FileName ', le.[FileName], ' -> ', e.[FileName]) END,
            CASE WHEN le.[IsIncremental] <> e.[IsIncremental] THEN CONCAT('IsIncremental ', le.[IsIncremental], ' -> ', e.[IsIncremental]) END,
            CASE WHEN ISNULL(le.[IsIncrementalColumn], '') <> ISNULL(e.[IsIncrementalColumn], '')
                 THEN CONCAT('IsIncrementalColumn ', ISNULL(le.[IsIncrementalColumn], '(none)'), ' -> ', ISNULL(e.[IsIncrementalColumn], '(none)')) END,
            CASE WHEN ble.[PrimaryKeys] <> e.[PrimaryKeys] THEN CONCAT('PrimaryKeys ', ble.[PrimaryKeys], ' -> ', e.[PrimaryKeys]) END,
            CASE WHEN le.[IsActive] <> e.[IsActive] THEN CONCAT('IsActive ', le.[IsActive], ' -> ', e.[IsActive]) END,
            CASE WHEN ISNULL(sle.[IsHistorized], 0) <> ISNULL(e.[IsHistorized], 0)
                 THEN CONCAT('IsHistorized ', ISNULL(sle.[IsHistorized], 0), ' -> ', ISNULL(e.[IsHistorized], 0)) END,
            CASE WHEN e.[BronzeRulesSet] = 1 AND ISNULL(ble.[CleansingRules], '') <> ISNULL(e.[BronzeRules], '') THEN 'BronzeCleansingRules changed' END,
            CASE WHEN e.[SilverRulesSet] = 1 AND ISNULL(sle.[CleansingRules], '') <> ISNULL(e.[SilverRules], '') THEN 'SilverCleansingRules changed' END
        ) AS [Changes]) chg
        -- Warnings, never errors: a function that is not built in may be a custom one, and a changed Silver
        -- rule only reaches the rows that change afterwards unless the entity is put back in the queue.
        CROSS APPLY (SELECT
            (SELECT STRING_AGG(CONVERT(NVARCHAR(MAX), CONCAT(l.[Layer], ' function ', f.[Name], ' is not built in; fine if NB_FMD_CUSTOM_DQ_CLEANSING registers it')), '; ')
             FROM (VALUES ('Bronze', e.[BronzeRules]), ('Silver', e.[SilverRules])) l([Layer], [Rules])
             CROSS APPLY OPENJSON(CASE WHEN LEFT(LTRIM(l.[Rules]), 1) = '[' THEN l.[Rules] END) x
             CROSS APPLY (SELECT JSON_VALUE(x.[value], '$.function') AS [Name]) f
             WHERE f.[Name] IS NOT NULL AND f.[Name] NOT IN ('normalize_text', 'fill_nulls', 'parse_datetime', 'exclude_rows')) AS [Unknown],
            CASE WHEN le.[LandingzoneEntityId] IS NOT NULL AND e.[SilverRulesSet] = 1 AND ISNULL(sle.[CleansingRules], '') <> ISNULL(e.[SilverRules], '')
                 THEN 'a changed Silver rule only reaches rows that change afterwards; to apply it to the whole table, run execution.sp_RequeueSilverLayerEntities (and drop the Silver table if the rule changes a type or the columns)' END AS [Rebuild]) wrn;

        -- Active in this workspace's scope, but not in this list: this run would leave them as is.
        INSERT INTO @Orphans
        SELECT ds.[Name] AS [DataSourceName], le.[SourceSchema], le.[SourceName]
        FROM [integration].[LandingzoneEntity] le
        JOIN [integration].[Lakehouse] lh ON lh.[LakehouseId] = le.[LakehouseId] AND lh.[WorkspaceGuid] = @WsGuid
        JOIN [integration].[DataSource] ds ON ds.[DataSourceId] = le.[DataSourceId]
        WHERE le.[IsActive] = 1
          AND NOT EXISTS (
              SELECT 1 FROM @EntitiesT e JOIN @Bound b ON b.[Source] = e.[Source]
              JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
              JOIN [integration].[DataSource] ds2 ON ds2.[ConnectionId] = c.[ConnectionId] AND ds2.[Name] = b.[DataSourceName] AND ds2.[Type] = b.[DataSourceType]
              WHERE ds2.[DataSourceId] = ds.[DataSourceId] AND e.[SourceSchema] = le.[SourceSchema] AND e.[SourceName] = le.[SourceName]);
    END

    -- ===== 3. Register, in one transaction. Rolled back at the end when @DryRun = 1. ==========
    DECLARE @Nr INT = 1, @Max INT = (SELECT MAX([Nr]) FROM @EntitiesT), @ConnectionId INT, @DataSourceId INT, @EntityId BIGINT;
    DECLARE @CN NVARCHAR(200), @DSN NVARCHAR(100), @NS VARCHAR(100), @DST VARCHAR(30), @LG VARCHAR(50), @HD INT, @SS NVARCHAR(100),
            @SN NVARCHAR(200), @TS NVARCHAR(100), @TN NVARCHAR(200), @FN NVARCHAR(200), @FT NVARCHAR(20), @Inc BIT,
            @IncCol NVARCHAR(50), @NB VARCHAR(200), @PK NVARCHAR(200), @Act BIT, @Hist BIT, @Desc NVARCHAR(200),
            @BrSet BIT, @BrRules NVARCHAR(MAX), @SiSet BIT, @SiRules NVARCHAR(MAX);

    -- A savepoint, not a plain BEGIN/ROLLBACK: a caller with autocommit off (pyodbc's default, so
    -- NB_FMD_REGISTRATION_FUNCTIONS) already holds a transaction, and a plain ROLLBACK for the dry
    -- run ended that one too: error 266 (found in FMD_TRIAL, 2026-10-13; sqlcmd autocommits, so it
    -- did not show there). Rolling back to the savepoint leaves the caller's transaction count as is.
    BEGIN TRY
        BEGIN TRANSACTION;
        SAVE TRANSACTION RegisterEntities;
        WHILE @Nr <= @Max
        BEGIN
            SELECT @CN=b.[ConnectionName], @DSN=b.[DataSourceName], @NS=b.[Namespace], @DST=b.[DataSourceType], @LG=b.[LoadGroup],
                   @HD=b.[HistoryDays], @SS=e.[SourceSchema], @SN=e.[SourceName], @TS=e.[TargetSchema], @TN=e.[TargetName],
                   @FN=e.[FileName], @FT=e.[FileType], @Inc=e.[IsIncremental], @IncCol=e.[IsIncrementalColumn],
                   @NB=e.[CustomNotebookName], @PK=e.[PrimaryKeys], @Act=e.[IsActive], @Hist=e.[IsHistorized],
                   @BrSet=e.[BronzeRulesSet], @BrRules=e.[BronzeRules], @SiSet=e.[SilverRulesSet], @SiRules=e.[SilverRules]
            FROM @EntitiesT e JOIN @Bound b ON b.[Source] = e.[Source] WHERE e.[Nr] = @Nr;

            SET @ConnectionId = (SELECT [ConnectionId] FROM [integration].[Connection] WHERE [Name] = @CN);
            SET @DataSourceId = ISNULL((SELECT [DataSourceId] FROM [integration].[DataSource]
                                        WHERE [ConnectionId] = @ConnectionId AND [Name] = @DSN AND [Type] = @DST), 0);
            -- An existing source keeps its description (e.g. one set by hand); only a new one gets ours.
            SET @Desc = ISNULL((SELECT [Description] FROM [integration].[DataSource] WHERE [DataSourceId] = @DataSourceId), @Description);
            EXEC [integration].[sp_UpsertDataSource] @ConnectionId = @ConnectionId, @DataSourceId = @DataSourceId, @Name = @DSN,
                 @Namespace = @NS, @Type = @DST, @Description = @Desc, @LoadGroup = @LG, @IsActive = 1;
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

            UPDATE sle SET sle.[IsHistorized] = ISNULL(@Hist, 0)
            FROM [integration].[SilverLayerEntity] sle
            JOIN [integration].[BronzeLayerEntity] ble ON ble.[BronzeLayerEntityId] = sle.[BronzeLayerEntityId]
            WHERE ble.[LandingzoneEntityId] = @EntityId;

            -- Cleansing rules: only when the row has the field; [] and null clear them.
            IF @BrSet = 1
                UPDATE [integration].[BronzeLayerEntity] SET [CleansingRules] = @BrRules WHERE [LandingzoneEntityId] = @EntityId;
            IF @SiSet = 1
                UPDATE sle SET sle.[CleansingRules] = @SiRules
                FROM [integration].[SilverLayerEntity] sle
                JOIN [integration].[BronzeLayerEntity] ble ON ble.[BronzeLayerEntityId] = sle.[BronzeLayerEntityId]
                WHERE ble.[LandingzoneEntityId] = @EntityId;

            -- HistoryDays: a start watermark for a new incremental entity. Never overwrites one that is already there.
            IF @HD IS NOT NULL AND @Inc = 1
               AND NOT EXISTS (SELECT 1 FROM [execution].[LandingzoneEntityLastLoadValue] WHERE [LandingzoneEntityId] = @EntityId)
                INSERT INTO [execution].[LandingzoneEntityLastLoadValue] ([LandingzoneEntityId], [LoadValue], [LastLoadDatetime])
                VALUES (@EntityId, CONVERT(VARCHAR(23), DATEADD(DAY, -@HD, CAST(CAST(SYSUTCDATETIME() AS DATE) AS DATETIME2(3))), 121), NULL);

            SET @Nr += 1;
        END

        IF @DryRun = 1
            ROLLBACK TRANSACTION RegisterEntities;
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH;

    -- ===== 4. Result =============================================================================
    -- Always the last result set(s): sp_UpsertDataSource and sp_UpsertLandingzoneBronzeSilver
    -- return their own result sets per entity during step 3, so callers read these from the end.
    IF @DryRun = 1
    BEGIN
        SELECT * FROM @Preview ORDER BY [SourceSchema], [SourceName];
        SELECT * FROM @Orphans ORDER BY [DataSourceName], [SourceSchema], [SourceName];
        RETURN;
    END

    SELECT e.[Source], b.[DataSourceName], e.[SourceSchema], e.[SourceName], le.[LandingzoneEntityId], le.[IsActive], ds.[LoadGroup],
           ISNULL(e.[IsHistorized], 0) AS [IsHistorized], lv.[LoadValue] AS [Watermark], CASE WHEN v.[EntityId] IS NULL THEN 'no' ELSE 'yes' END AS [InLoadView]
    FROM @EntitiesT e
    JOIN @Bound b ON b.[Source] = e.[Source]
    JOIN [integration].[Connection] c ON c.[Name] = b.[ConnectionName]
    JOIN [integration].[DataSource] ds ON ds.[ConnectionId] = c.[ConnectionId] AND ds.[Name] = b.[DataSourceName] AND ds.[Type] = b.[DataSourceType]
    JOIN [integration].[LandingzoneEntity] le ON le.[DataSourceId] = ds.[DataSourceId] AND le.[SourceSchema] = e.[SourceSchema] AND le.[SourceName] = e.[SourceName]
    JOIN [integration].[Lakehouse] l ON l.[LakehouseId] = le.[LakehouseId] AND l.[WorkspaceGuid] = @WsGuid
    LEFT JOIN [execution].[LandingzoneEntityLastLoadValue] lv ON lv.[LandingzoneEntityId] = le.[LandingzoneEntityId]
    LEFT JOIN [execution].[vw_LoadSourceToLandingzone] v ON v.[EntityId] = le.[LandingzoneEntityId]
    ORDER BY e.[Source], e.[SourceSchema], e.[SourceName];
END

GO
