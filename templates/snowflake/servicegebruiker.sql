-- Leesrol, servicegebruiker en storage integration voor FMD in Snowflake (ADR-014).
-- Draai dit in Snowflake, niet in de configdb.
--
-- Gebruik: vervang <BRON_DB>, <WAREHOUSE>, <TENANT_ID> en de OneLake-locaties, en zet de publieke
-- sleutel in RSA_PUBLIC_KEY. Uitvoeren als ACCOUNTADMIN (de storage integration vraagt dat).
--
-- Sleutelpaar maken (lokaal; de private sleutel gaat naar Key Vault en de Fabric-connectie, nooit naar git):
--   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out fmd_rsa_key.p8 -nocrypt
--   openssl rsa -in fmd_rsa_key.p8 -pubout -out fmd_rsa_key.pub
-- Zonder wachtwoordzin (-nocrypt): Fabric accepteert geen versleutelde sleutel. Getest met -v2 des3 en
-- -v2 aes-256-cbc, wachtwoordzin via Key Vault en ingetypt: "Unable to connect" (trial 2026-10-07).
-- De sleutel staat daarom alleen in Key Vault.
--
-- - Gebruik het warehouse dat de klant al heeft: dan start er geen extra warehouse, en
--   AUTO_SUSPEND en de resource monitor van dat warehouse blijven gelden.
-- - Alleen SELECT: FMD schrijft niets in Snowflake. Snowflake schrijft wel naar de landing zone in OneLake.
-- - Heeft een schema eigen future grants, dan gaan die vóór de database-brede hieronder.
--   Geef in dat geval SELECT ON FUTURE TABLES/VIEWS IN SCHEMA per schema.

CREATE ROLE IF NOT EXISTS FMD_READER;

GRANT USAGE ON WAREHOUSE <WAREHOUSE> TO ROLE FMD_READER;
GRANT USAGE ON DATABASE <BRON_DB> TO ROLE FMD_READER;
GRANT USAGE ON ALL SCHEMAS IN DATABASE <BRON_DB> TO ROLE FMD_READER;
GRANT USAGE ON FUTURE SCHEMAS IN DATABASE <BRON_DB> TO ROLE FMD_READER;
GRANT SELECT ON ALL TABLES IN DATABASE <BRON_DB> TO ROLE FMD_READER;
GRANT SELECT ON ALL VIEWS IN DATABASE <BRON_DB> TO ROLE FMD_READER;
GRANT SELECT ON FUTURE TABLES IN DATABASE <BRON_DB> TO ROLE FMD_READER;
GRANT SELECT ON FUTURE VIEWS IN DATABASE <BRON_DB> TO ROLE FMD_READER;

CREATE USER IF NOT EXISTS SVC_FMD
    TYPE = SERVICE
    DEFAULT_ROLE = FMD_READER
    DEFAULT_WAREHOUSE = <WAREHOUSE>
    RSA_PUBLIC_KEY = '<inhoud van fmd_rsa_key.pub zonder de BEGIN/END-regels>';

GRANT ROLE FMD_READER TO USER SVC_FMD;

-- Storage integration: Snowflake schrijft de landing zone zelf (COPY INTO, ADR-014).
-- Eén locatie per DATA-workspace (D, T, P): Files/ van LH_DATA_LANDINGZONE. De naam staat in
-- VAR_FMD.snowflake_storage_integration (standaard FMD_ONELAKE).
CREATE STORAGE INTEGRATION IF NOT EXISTS FMD_ONELAKE
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'AZURE'
    ENABLED = TRUE
    AZURE_TENANT_ID = '<TENANT_ID>'
    STORAGE_ALLOWED_LOCATIONS = (
        'azure://onelake.blob.fabric.microsoft.com/<DATA_D_WORKSPACE_ID>/<LANDINGZONE_D_LAKEHOUSE_ID>/Files/',
        'azure://onelake.blob.fabric.microsoft.com/<DATA_T_WORKSPACE_ID>/<LANDINGZONE_T_LAKEHOUSE_ID>/Files/',
        'azure://onelake.blob.fabric.microsoft.com/<DATA_P_WORKSPACE_ID>/<LANDINGZONE_P_LAKEHOUSE_ID>/Files/');

GRANT USAGE ON INTEGRATION FMD_ONELAKE TO ROLE FMD_READER;

-- Daarna, buiten Snowflake:
--   1. Open AZURE_CONSENT_URL uit DESC STORAGE INTEGRATION en geef toestemming (Entra-beheerder).
--   2. Zoek in Fabric de app uit AZURE_MULTI_TENANT_APP_NAME (het deel vóór de underscore) en
--      maak hem Contributor op elke DATA-workspace.
DESC STORAGE INTEGRATION FMD_ONELAKE;

-- Controle: de grants van de rol, en de sleutel van de gebruiker (RSA_PUBLIC_KEY_FP is gevuld).
SHOW GRANTS TO ROLE FMD_READER;
DESC USER SVC_FMD;
