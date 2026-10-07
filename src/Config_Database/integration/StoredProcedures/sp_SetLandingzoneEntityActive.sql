CREATE PROCEDURE [integration].[sp_SetLandingzoneEntityActive] (
    @LandingzoneEntityId BIGINT,
    @IsActive BIT,
    @Reason NVARCHAR(500),
    @ChangedBy NVARCHAR(256) = NULL
    )
    WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Tijdelijke override. De lijst in templates/registratie/registreer_entiteiten.sql blijft leidend en
    -- zet IsActive bij de volgende run weer terug.
    IF ISNULL(@Reason, '') = ''
        THROW 50001, 'Een reden is verplicht.', 1;

    DECLARE @Old BIT;
    SELECT @Old = [IsActive]
    FROM [integration].[LandingzoneEntity]
    WHERE [LandingzoneEntityId] = @LandingzoneEntityId;

    IF @Old IS NULL
        THROW 50002, 'LandingzoneEntity bestaat niet.', 1;

    BEGIN TRANSACTION;

    UPDATE [integration].[LandingzoneEntity]
    SET [IsActive] = @IsActive
    WHERE [LandingzoneEntityId] = @LandingzoneEntityId;

    INSERT INTO [logging].[ConfigChange] ([ChangedBy], [Action], [ObjectType], [ObjectId], [OldValue], [NewValue], [Reason])
    VALUES (ISNULL(@ChangedBy, SUSER_SNAME()), 'SetIsActive', 'LandingzoneEntity', @LandingzoneEntityId,
            CAST(@Old AS NVARCHAR(200)), CAST(@IsActive AS NVARCHAR(200)), @Reason);

    COMMIT TRANSACTION;

    SELECT @LandingzoneEntityId AS LandingzoneEntityId, @IsActive AS IsActive;
END

GO

