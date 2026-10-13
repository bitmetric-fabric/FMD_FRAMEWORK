-- Replaces the discovered metadata for one connection + database (+ optional schema filter).
-- Called by PL_FMD_DISCOVER_SOURCE after it reads the source's own metadata (sys.objects,
-- INFORMATION_SCHEMA, ...). Not a registration: NB_REGISTRATIE only reads this table, through
-- sp_RegisterEntities, to check a list before it is used to register.
--
-- @Json shape, one row per table/view:
-- [{"SourceSchema":"Sales","SourceName":"Customer","ObjectType":"U",
--   "Columns":[{"Name":"CustomerID","Type":"int"}, ...],"PrimaryKeys":"CustomerID"}, ...]
-- PrimaryKeys is a comma-separated list, empty when the source has none.
CREATE PROCEDURE [integration].[sp_UpsertDiscoveredEntities](
    @ConnectionName NVARCHAR(200),
    @DataSourceName NVARCHAR(100),
    @SchemaFilter NVARCHAR(100) = NULL,
    @Json NVARCHAR(MAX)
)
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ConnectionId INT = (SELECT [ConnectionId] FROM [integration].[Connection] WHERE [Name] = @ConnectionName);
    IF @ConnectionId IS NULL
        THROW 50004, 'sp_UpsertDiscoveredEntities: connection not registered.', 1;

    IF ISJSON(@Json) = 0
        THROW 50004, 'sp_UpsertDiscoveredEntities: @Json is not valid JSON.', 1;

    BEGIN TRANSACTION;

    -- Replace scope: this connection + database, optionally narrowed to one schema.
    -- A run without @SchemaFilter replaces everything discovered for this database.
    DELETE FROM [integration].[DiscoveredEntity]
    WHERE [ConnectionId] = @ConnectionId
      AND [DataSourceName] = @DataSourceName
      AND (@SchemaFilter IS NULL OR [SourceSchema] = @SchemaFilter);

    INSERT INTO [integration].[DiscoveredEntity]
        ([ConnectionId], [DataSourceName], [SourceSchema], [SourceName], [ObjectType], [Columns], [PrimaryKeys])
    SELECT
        @ConnectionId, @DataSourceName, j.[SourceSchema], j.[SourceName], j.[ObjectType],
        j.[Columns], NULLIF(j.[PrimaryKeys], '')
    FROM OPENJSON(@Json)
        WITH (
            [SourceSchema] NVARCHAR(100) '$.SourceSchema',
            [SourceName]   NVARCHAR(200) '$.SourceName',
            [ObjectType]   VARCHAR(10)   '$.ObjectType',
            [Columns]      NVARCHAR(MAX) '$.Columns' AS JSON,
            [PrimaryKeys]  NVARCHAR(200) '$.PrimaryKeys'
        ) j;

    COMMIT;

    SELECT COUNT(*) AS [DiscoveredCount]
    FROM [integration].[DiscoveredEntity]
    WHERE [ConnectionId] = @ConnectionId
      AND [DataSourceName] = @DataSourceName
      AND (@SchemaFilter IS NULL OR [SourceSchema] = @SchemaFilter);
END

GO
