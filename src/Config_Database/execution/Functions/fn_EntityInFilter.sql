CREATE FUNCTION [execution].[fn_EntityInFilter]
(
     @DataSourceNameFilter NVARCHAR(100)
    ,@EntitiesFilter NVARCHAR(MAX)
    ,@DataSourceName NVARCHAR(100)
    ,@SourceSchema NVARCHAR(100)
    ,@SourceName NVARCHAR(200)
)
RETURNS BIT
AS
BEGIN
    -- Empty filter = no filter. Fabric passes an empty-string pipeline parameter to a procedure as NULL.
    -- @EntitiesFilter is a comma-separated list; an item matches SourceName or SourceSchema.SourceName.
    RETURN CASE
        WHEN (ISNULL(@DataSourceNameFilter, '') = '' OR @DataSourceName = @DataSourceNameFilter)
         AND (ISNULL(@EntitiesFilter, '') = '' OR EXISTS (
                SELECT 1 FROM STRING_SPLIT(@EntitiesFilter, ',') s
                WHERE LTRIM(RTRIM(s.[value])) IN (@SourceName, CONCAT(@SourceSchema, '.', @SourceName))))
        THEN 1 ELSE 0 END
END

GO
