CREATE ROLE [role_fmd_beheer];


GO

-- De rol voor de identiteit van de beheer-app (de eigenaar van het Fabric App-item): alleen wat de app nodig heeft.
-- De procedures en views hebben dezelfde eigenaar (dbo) als de tabellen, dus EXECUTE en SELECT op deze objecten
-- volstaan via ownership chaining; de rol krijgt geen rechten op de tabellen zelf.
-- Lid maken gebeurt per omgeving, niet in de dacpac:
--   CREATE USER [<serviceaccount>] FROM EXTERNAL PROVIDER;  ALTER ROLE role_fmd_beheer ADD MEMBER [<serviceaccount>];
GRANT EXECUTE ON OBJECT::[integration].[sp_SetLandingzoneEntityActive] TO [role_fmd_beheer];


GO

GRANT EXECUTE ON OBJECT::[execution].[sp_ResetLandingzoneEntityLastLoadValue] TO [role_fmd_beheer];


GO

GRANT EXECUTE ON OBJECT::[execution].[sp_SkipPipelineLandingzoneFile] TO [role_fmd_beheer];


GO

GRANT SELECT ON OBJECT::[integration].[vw_EntityOverview] TO [role_fmd_beheer];


GO

GRANT SELECT ON OBJECT::[integration].[vw_LoadStatus] TO [role_fmd_beheer];


GO

GRANT SELECT ON OBJECT::[execution].[vw_StuckLandingzoneFiles] TO [role_fmd_beheer];


GO

GRANT SELECT ON OBJECT::[logging].[vw_RecentErrors] TO [role_fmd_beheer];


GO

GRANT SELECT ON OBJECT::[integration].[AppUser] TO [role_fmd_beheer];


GO

