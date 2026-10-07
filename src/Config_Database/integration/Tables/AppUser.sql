CREATE TABLE [integration].[AppUser] (
    [Email]         NVARCHAR (256) NOT NULL,
    [Role]          VARCHAR (20)   NOT NULL,
    [IsActive]      BIT            NOT NULL CONSTRAINT [DF_integration_AppUser_IsActive] DEFAULT (1),
    [AddedBy]       NVARCHAR (256) NULL,
    [AddedDateTime] DATETIME2 (6)  NOT NULL CONSTRAINT [DF_integration_AppUser_AddedDateTime] DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT [PK_integration_AppUser] PRIMARY KEY CLUSTERED ([Email] ASC),
    CONSTRAINT [CK_integration_AppUser_Role] CHECK ([Role] IN ('lezer', 'beheerder')),
    CONSTRAINT [CK_integration_AppUser_EmailLower] CHECK ([Email] = LOWER([Email]))
);


GO

