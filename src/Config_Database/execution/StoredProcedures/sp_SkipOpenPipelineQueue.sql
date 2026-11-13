CREATE PROCEDURE [execution].[sp_SkipOpenPipelineQueue] (
    @LandingzoneEntityId BIGINT,
    @Layer VARCHAR(20) = 'Both',
    @Reason NVARCHAR(500),
    @ChangedBy NVARCHAR(256) = NULL,
    @DryRun BIT = 1
    )
    WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Sets every open row of one table in the queue on IsProcessed = 1, without loading it: the files in
    -- execution.PipelineLandingzoneEntity ('Landingzone'), the rows in execution.PipelineBronzeLayerEntity ('Bronze', which
    -- vw_LoadToSilverLayer reads), or both. Use it after the primary key of a table changed and its Bronze and Silver table
    -- were dropped: the old files must not be loaded into the new table. For one stuck file use sp_SkipPipelineLandingzoneFile.
    -- @DryRun = 1 (default) only counts. Do not run it while a load of this table is busy: a row that is open then is not stuck.
    -- Every real run is written to logging.ConfigChange, with the number of rows as OldValue.
    IF ISNULL(@Reason, '') = ''
        THROW 50001, 'Een reden is verplicht.', 1;

    IF @Layer NOT IN ('Landingzone', 'Bronze', 'Both')
        THROW 50005, 'Layer moet Landingzone, Bronze of Both zijn.', 1;

    IF NOT EXISTS (SELECT 1 FROM [integration].[LandingzoneEntity] WHERE [LandingzoneEntityId] = @LandingzoneEntityId)
        THROW 50002, 'LandingzoneEntity bestaat niet.', 1;

    DECLARE @LandingzoneOpen INT, @BronzeOpen INT;

    SELECT @LandingzoneOpen = COUNT(*)
    FROM [execution].[PipelineLandingzoneEntity]
    WHERE [LandingzoneEntityId] = @LandingzoneEntityId
      AND [IsProcessed] = 0;

    SELECT @BronzeOpen = COUNT(*)
    FROM [execution].[PipelineBronzeLayerEntity] PB
    INNER JOIN [integration].[BronzeLayerEntity] BLE
        ON BLE.[BronzeLayerEntityId] = PB.[BronzeLayerEntityId]
    WHERE BLE.[LandingzoneEntityId] = @LandingzoneEntityId
      AND PB.[IsProcessed] = 0;

    DECLARE @DoLandingzone BIT = IIF(@Layer IN ('Landingzone', 'Both'), 1, 0);
    DECLARE @DoBronze BIT = IIF(@Layer IN ('Bronze', 'Both'), 1, 0);

    IF @DryRun = 0
    BEGIN
        DECLARE @Changed INT, @Who NVARCHAR(256) = ISNULL(@ChangedBy, SUSER_SNAME());

        BEGIN TRANSACTION;

        IF @DoLandingzone = 1 AND @LandingzoneOpen > 0
        BEGIN
            UPDATE [execution].[PipelineLandingzoneEntity]
            SET [IsProcessed] = 1,
                [LoadEndDateTime] = GETDATE()
            WHERE [LandingzoneEntityId] = @LandingzoneEntityId
              AND [IsProcessed] = 0;
            SET @Changed = @@ROWCOUNT;

            INSERT INTO [logging].[ConfigChange] ([ChangedBy], [Action], [ObjectType], [ObjectId], [OldValue], [NewValue], [Reason])
            VALUES (@Who, 'SkipQueueLandingzone', 'LandingzoneEntity', @LandingzoneEntityId, CAST(@Changed AS VARCHAR(20)), '0', @Reason);
        END

        IF @DoBronze = 1 AND @BronzeOpen > 0
        BEGIN
            UPDATE PB
            SET PB.[IsProcessed] = 1,
                PB.[LoadEndDateTime] = GETDATE()
            FROM [execution].[PipelineBronzeLayerEntity] PB
            INNER JOIN [integration].[BronzeLayerEntity] BLE
                ON BLE.[BronzeLayerEntityId] = PB.[BronzeLayerEntityId]
            WHERE BLE.[LandingzoneEntityId] = @LandingzoneEntityId
              AND PB.[IsProcessed] = 0;
            SET @Changed = @@ROWCOUNT;

            INSERT INTO [logging].[ConfigChange] ([ChangedBy], [Action], [ObjectType], [ObjectId], [OldValue], [NewValue], [Reason])
            VALUES (@Who, 'SkipQueueBronze', 'LandingzoneEntity', @LandingzoneEntityId, CAST(@Changed AS VARCHAR(20)), '0', @Reason);
        END

        COMMIT TRANSACTION;
    END

    SELECT [Layer], [OpenRows],
           CASE WHEN [Requested] = 0 THEN 'not requested'
                WHEN [OpenRows] = 0 THEN 'nothing open'
                WHEN @DryRun = 1 THEN 'dry run: would be skipped'
                ELSE 'skipped' END AS [Result]
    FROM (VALUES ('Landingzone', @LandingzoneOpen, @DoLandingzone),
                 ('Bronze', @BronzeOpen, @DoBronze)) AS t([Layer], [OpenRows], [Requested]);
END

GO

