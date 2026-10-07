CREATE PROCEDURE [integration].[sp_UpsertAppUser] (
    @Email NVARCHAR(256),
    @Role VARCHAR(20),
    @IsActive BIT = 1,
    @Reason NVARCHAR(500),
    @ChangedBy NVARCHAR(256) = NULL
    )
    WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Gebruikersbeheer van de beheer-app. Bewust niet toegekend aan role_fmd_beheer: de app kan zichzelf
    -- of anderen dus geen toegang geven. Draai deze procedure als databasebeheerder (sqlcmd of SSMS).
    IF ISNULL(@Reason, '') = ''
        THROW 50001, 'Een reden is verplicht.', 1;

    IF @Role NOT IN ('lezer', 'beheerder')
        THROW 50005, 'Rol moet lezer of beheerder zijn.', 1;

    SET @Email = LOWER(LTRIM(RTRIM(@Email)));
    IF @Email IS NULL OR @Email NOT LIKE '_%@_%._%'
        THROW 50006, 'Het e-mailadres is ongeldig.', 1;

    DECLARE @Old NVARCHAR(200);
    SELECT @Old = [Role] + CASE WHEN [IsActive] = 1 THEN '' ELSE ' (uit)' END
    FROM [integration].[AppUser]
    WHERE [Email] = @Email;

    BEGIN TRANSACTION;

    IF @Old IS NULL
        INSERT INTO [integration].[AppUser] ([Email], [Role], [IsActive], [AddedBy])
        VALUES (@Email, @Role, @IsActive, ISNULL(@ChangedBy, SUSER_SNAME()));
    ELSE
        UPDATE [integration].[AppUser]
        SET [Role] = @Role, [IsActive] = @IsActive
        WHERE [Email] = @Email;

    -- ObjectId is verplicht in ConfigChange; AppUser heeft geen numerieke sleutel, dus 0 en het adres in NewValue.
    INSERT INTO [logging].[ConfigChange] ([ChangedBy], [Action], [ObjectType], [ObjectId], [OldValue], [NewValue], [Reason])
    VALUES (ISNULL(@ChangedBy, SUSER_SNAME()), 'UpsertAppUser', 'AppUser', 0, @Old,
            @Email + ': ' + @Role + CASE WHEN @IsActive = 1 THEN '' ELSE ' (uit)' END, @Reason);

    COMMIT TRANSACTION;

    SELECT @Email AS Email, @Role AS [Role], @IsActive AS IsActive;
END

GO

