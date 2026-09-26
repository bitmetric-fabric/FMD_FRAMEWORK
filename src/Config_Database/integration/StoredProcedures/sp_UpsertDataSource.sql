



    CREATE   PROCEDURE [integration].[sp_UpsertDataSource](
        @ConnectionId INT 
        ,@DataSourceId INT = 0
        ,@Name NVARCHAR(100)
        ,@Namespace VARCHAR(100)
        ,@Type VARCHAR(30)
        ,@Description NVARCHAR(200)
        ,@LoadGroup VARCHAR(50) = ''
        ,@IsActive BIT = 1
        -- 1 = leave an existing data source untouched (bulk registration only adds)
        ,@OnlyInsert BIT = 0
    )
    WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @InternalConnectionId BIGINT;
    DECLARE @OutputTable TABLE (DataSourceId INT);

    SET @InternalConnectionId = (SELECT [C].[ConnectionId]
                                 FROM [integration].[Connection] [C]
                                 WHERE [C].ConnectionId = @ConnectionId);

    IF NOT EXISTS (SELECT 1
                   FROM [integration].[DataSource]
                   WHERE [DataSourceId] = @DataSourceId)
    BEGIN
        INSERT INTO [integration].[DataSource]
            ([Name]
            ,[Namespace]
            ,[ConnectionId]
            ,[Type]
            ,[Description]
            ,[LoadGroup]
            ,[IsActive])
        OUTPUT INSERTED.[DataSourceId] INTO @OutputTable
        VALUES (@Name
            ,@Namespace
            ,@InternalConnectionId
            ,@Type
            ,@Description
            ,@LoadGroup
            ,@IsActive);
    END
    ELSE IF @OnlyInsert = 1
    BEGIN
        INSERT INTO @OutputTable VALUES (@DataSourceId);
    END
    ELSE
    BEGIN
        UPDATE [integration].[DataSource]
        SET [Name] = @Name
            ,[ConnectionId] = @InternalConnectionId
            ,[Namespace] = @Namespace
            ,[Type] = @Type
            ,[Description] = @Description
            ,[LoadGroup] = @LoadGroup
            ,[IsActive] = @IsActive
        OUTPUT INSERTED.[DataSourceId] INTO @OutputTable
        WHERE [DataSourceId] = @DataSourceId;
    END

    SELECT DataSourceId FROM @OutputTable;
END

GO

