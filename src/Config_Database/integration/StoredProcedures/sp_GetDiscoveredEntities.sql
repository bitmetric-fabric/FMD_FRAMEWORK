-- Lists what PL_FMD_DISCOVER_SOURCE found for one connection + database, for NB_REGISTRATIE's
-- print_entity_list(). Read-only; sp_RegisterEntities does its own, separate metadata checks.
CREATE PROCEDURE [integration].[sp_GetDiscoveredEntities](
    @ConnectionName NVARCHAR(200),
    @DataSourceName NVARCHAR(100),
    @SchemaFilter NVARCHAR(100) = NULL
)
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    SELECT de.[SourceSchema], de.[SourceName], de.[ObjectType], de.[PrimaryKeys]
    FROM [integration].[DiscoveredEntity] de
    JOIN [integration].[Connection] c ON c.[ConnectionId] = de.[ConnectionId]
    WHERE c.[Name] = @ConnectionName
      AND de.[DataSourceName] = @DataSourceName
      AND (@SchemaFilter IS NULL OR de.[SourceSchema] = @SchemaFilter)
    ORDER BY de.[SourceSchema], de.[SourceName];
END

GO
