CREATE PROCEDURE [execution].[sp_SkipPipelineLandingzoneFile] (
    @PipelineLandingzoneEntityId BIGINT,
    @Reason NVARCHAR(500),
    @ChangedBy NVARCHAR(256) = NULL
    )
    WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Een vastgelopen bestand blokkeert de latere bestanden van dezelfde entiteit. Overslaan zet
    -- IsProcessed op 1 zonder dat het bestand naar Bronze gaat; de reden komt in logging.ConfigChange.
    IF ISNULL(@Reason, '') = ''
        THROW 50001, 'Een reden is verplicht.', 1;

    DECLARE @FileName NVARCHAR(MAX), @IsProcessed BIT;
    SELECT @FileName = [FileName], @IsProcessed = [IsProcessed]
    FROM [execution].[PipelineLandingzoneEntity]
    WHERE [PipelineLandingzoneEntityId] = @PipelineLandingzoneEntityId;

    IF @IsProcessed IS NULL
        THROW 50002, 'Het bestand bestaat niet in de wachtrij.', 1;

    IF @IsProcessed = 1
        THROW 50004, 'Het bestand is al verwerkt of overgeslagen.', 1;

    BEGIN TRANSACTION;

    UPDATE [execution].[PipelineLandingzoneEntity]
    SET [IsProcessed] = 1,
        [LoadEndDateTime] = GETDATE()
    WHERE [PipelineLandingzoneEntityId] = @PipelineLandingzoneEntityId
      AND [IsProcessed] = 0;

    INSERT INTO [logging].[ConfigChange] ([ChangedBy], [Action], [ObjectType], [ObjectId], [OldValue], [NewValue], [Reason])
    VALUES (ISNULL(@ChangedBy, SUSER_SNAME()), 'SkipFile', 'PipelineLandingzoneEntity', @PipelineLandingzoneEntityId,
            '0', '1', LEFT(@Reason, 400) + N' [' + LEFT(@FileName, 90) + N']');

    COMMIT TRANSACTION;

    SELECT @PipelineLandingzoneEntityId AS PipelineLandingzoneEntityId;
END

GO

