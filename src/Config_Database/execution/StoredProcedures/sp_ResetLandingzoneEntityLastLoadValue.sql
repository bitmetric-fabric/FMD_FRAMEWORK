CREATE PROCEDURE [execution].[sp_ResetLandingzoneEntityLastLoadValue] (
    @LandingzoneEntityId BIGINT,
    @LoadValue VARCHAR(50) = NULL,
    @Reason NVARCHAR(500),
    @ChangedBy NVARCHAR(256) = NULL
    )
    WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- NULL = volledige herlaad. Een waarde moet een datetime (style 121) of een getal zijn.
    -- De rij wordt nooit verwijderd: vw_LoadToBronzeLayer doet er een INNER JOIN op.
    IF ISNULL(@Reason, '') = ''
        THROW 50001, 'Een reden is verplicht.', 1;

    IF NOT EXISTS (SELECT 1 FROM [integration].[LandingzoneEntity] WHERE [LandingzoneEntityId] = @LandingzoneEntityId)
        THROW 50002, 'LandingzoneEntity bestaat niet.', 1;

    IF @LoadValue IS NOT NULL
       AND TRY_CONVERT(DATETIME2, @LoadValue, 121) IS NULL
       AND TRY_CONVERT(BIGINT, @LoadValue) IS NULL
        THROW 50003, 'LoadValue moet een datetime (yyyy-mm-dd hh:mi:ss.mmm) of een getal zijn.', 1;

    DECLARE @Old VARCHAR(50);
    SELECT @Old = [LoadValue]
    FROM [execution].[LandingzoneEntityLastLoadValue]
    WHERE [LandingzoneEntityId] = @LandingzoneEntityId;

    BEGIN TRANSACTION;

    IF EXISTS (SELECT 1 FROM [execution].[LandingzoneEntityLastLoadValue] WHERE [LandingzoneEntityId] = @LandingzoneEntityId)
        UPDATE [execution].[LandingzoneEntityLastLoadValue]
        SET [LoadValue] = @LoadValue,
            [LastLoadDatetime] = CONVERT(DATETIME2(7), GETDATE())
        WHERE [LandingzoneEntityId] = @LandingzoneEntityId;
    ELSE
        INSERT INTO [execution].[LandingzoneEntityLastLoadValue] ([LandingzoneEntityId], [LoadValue], [LastLoadDatetime])
        VALUES (@LandingzoneEntityId, @LoadValue, GETDATE());

    INSERT INTO [logging].[ConfigChange] ([ChangedBy], [Action], [ObjectType], [ObjectId], [OldValue], [NewValue], [Reason])
    VALUES (ISNULL(@ChangedBy, SUSER_SNAME()), 'ResetWatermark', 'LandingzoneEntity', @LandingzoneEntityId,
            @Old, @LoadValue, @Reason);

    COMMIT TRANSACTION;

    SELECT @LandingzoneEntityId AS LandingzoneEntityId, @LoadValue AS LoadValue;
END

GO

