CREATE TABLE [logging].[ConfigChange] (
    [ChangeId]       BIGINT         IDENTITY (1, 1) NOT NULL,
    [ChangeDateTime] DATETIME2 (6)  NOT NULL CONSTRAINT [DF_logging_ConfigChange_ChangeDateTime] DEFAULT (SYSUTCDATETIME()),
    [ChangedBy]      NVARCHAR (256) NOT NULL,
    [Action]         VARCHAR (50)   NOT NULL,
    [ObjectType]     VARCHAR (50)   NOT NULL,
    [ObjectId]       BIGINT         NOT NULL,
    [OldValue]       NVARCHAR (200) NULL,
    [NewValue]       NVARCHAR (200) NULL,
    [Reason]         NVARCHAR (500) NOT NULL,
    CONSTRAINT [PK_logging_ConfigChange] PRIMARY KEY CLUSTERED ([ChangeId] ASC)
);


GO

