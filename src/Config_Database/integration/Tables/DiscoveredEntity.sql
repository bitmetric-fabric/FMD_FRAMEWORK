CREATE TABLE [integration].[DiscoveredEntity] (
    [DiscoveredEntityId] BIGINT         IDENTITY (1, 1) NOT NULL,
    [ConnectionId]        INT            NOT NULL,
    [DataSourceName]      NVARCHAR (100) NOT NULL,
    [SourceSchema]        NVARCHAR (100) NOT NULL,
    [SourceName]          NVARCHAR (200) NOT NULL,
    [ObjectType]          VARCHAR (10)   NOT NULL,
    [Columns]             NVARCHAR (MAX) NOT NULL,
    [PrimaryKeys]         NVARCHAR (200) NULL,
    [DiscoveredAt]        DATETIME2 (3)  DEFAULT (SYSUTCDATETIME()) NOT NULL,
    CONSTRAINT [PK_integration_DiscoveredEntity] PRIMARY KEY CLUSTERED ([DiscoveredEntityId] ASC),
    CONSTRAINT [FK_DiscoveredEntity_Connection] FOREIGN KEY ([ConnectionId]) REFERENCES [integration].[Connection] ([ConnectionId]),
    CONSTRAINT [UC_integration_DiscoveredEntity] UNIQUE NONCLUSTERED ([ConnectionId] ASC, [DataSourceName] ASC, [SourceSchema] ASC, [SourceName] ASC)
);


GO
