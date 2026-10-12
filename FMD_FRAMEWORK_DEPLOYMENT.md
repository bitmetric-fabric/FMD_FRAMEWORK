---
Title: Deploy the FMD Framework
Description: Learn how to deploy the Fabric Metadata-Driven Framework (FMD) in Microsoft Fabric, including prerequisites, setup, and configuration.
Topic: how-to
Date: 07/2025
Author: edkreuk
---

# Deploy the FMD Framework

![FMD Overview](/Images/FMD_Overview.png)

This article describes how to deploy the Fabric Metadata-Driven Framework (FMD) in Microsoft Fabric. Follow these steps to configure your environment, set up required connections, and apply deployment settings.

## 📦 Installation

### Prerequisites

Before you begin, ensure the following prerequisites are met in the Admin Portal:
- Contributor role is assigned on the target capacity or capacities.

### Prerequisite: Enable access in the Fabric Admin portal

Sign in to the Fabric admin portal. You need to be a Fabric admin to see the tenant settings page.
Make sure the following settings are enabled:
**Microsoft Fabric settings:**
- Users can create Fabric items.
**Workspace settings:**
- Create Workspaces

Select the switch for the type of admin APIs you want to enable:
**Developer settings:**
- Service principals can create workspaces, connections, and deployment pipelines
- Service principals can call Fabric public APIs
**Admin API settings:**
- Service principals can access read-only admin APIs
- Service principals can access admin APIs used for update

> [!NOTE]
> In case you need to use a **security group**, add the security group to the settings above.
> Add Workspace identity (after deployment) or Service Principal to the security groups.


### Workspace identity or Service Principal used for execution must have the following role assigned:
- Workspace Contributor role on the workspace (Workspace Identity is automatically assigned during deployment, Service principal must be assigned manually)
- Workspace identity or Service Principal must be added to the correct security groups which have been assigned in the Prerequisite step

## Deployment steps

### 1. Download deployment assets

Download a single file from the `setup` folder to your local machine:

- `NB_BOOTSTRAP_FMD.ipynb` – fetches the setup notebooks from your fork and places them in the workspace.

This is the only file you import by hand. `NB_SETUP_FMD.ipynb` and
`NB_SETUP_BUSINESS_DOMAINS.ipynb` are placed by the bootstrap notebook, with the
location of your fork already filled in.

### 2. Create required connections

The setup creates these connections itself, in a single run, with the service principal whose secrets are in the Key Vault (`key_vault.secrets` in `manifest.yaml`). The setup makes that principal Contributor on every framework workspace (`security.service_principal_id`), so every pipeline-to-pipeline call works, also across workspaces (the schedule pipelines in the configuration workspace, the Gold pipelines of a business domain). Without those secrets the setup falls back to Workspace Identity for the pipeline and notebook connections, and cannot create the SQL connection.

The names below use the default prefix `CON_FMD`; set `naming.connection_prefix` in `manifest.yaml` to use your own (for example `CON_ACME_FMD`). Choose it before the first installation: connection names are tenant-wide. The setup registers every connection whose name starts with this prefix in the configuration database, so give the connections to your **sources** the same prefix (for example `CON_ACME_FMD_ASQL_ERP`); a source connection with another prefix is not registered, and the registration template stops with `connection … not registered`.

| Connection name              | Connection type            | Created by the setup with    |Remarks |
|------------------------------|----------------------------|------------------------------|--------|
| CON_FMD_FABRIC_PIPELINES     | Fabric Data Pipelines      | Service Principal            |  Workspace Identity when the SP secrets are not set |
| CON_FMD_FABRIC_SQL           | Fabric SQL database        | Service Principal            |  `FabricSql.Contents`, no database parameter, so the database does not have to exist yet |
| CON_FMD_FABRIC_NOTEBOOKS     | Fabric Notebooks           | Service Principal            |  Workspace Identity when the SP secrets are not set |

A connection that already exists with the same name is reused as it is, including its credential. Connection names are tenant-wide.

> [!IMPORTANT]
> Only when you create `CON_FMD_FABRIC_SQL` by hand in the portal: that kind of connection has to name an existing database, so run the deployment, create the connection against `SQL_FMD_FRAMEWORK`, and **run the deployment a second time**. Until then the pipelines have no SQL connection, their audit activities are marked inactive, and `logging` never receives a row.

If you use Azure Data Factory Pipelines, create this additional connection:

| Connection name              | Connection type            | Authentication                                    |Remarks |
|------------------------------|----------------------------|---------------------------------------------------|--------|
| CON_FMD_ADF_PIPELINES        | Azure Data Factory         | OAuth2  or Service Principal                      |You must add the Service Principal to the workspace_roles_code.        |         |

### 3. Create a configuration workspace

- Create a new workspace (for example, `FMD_FRAMEWORK_CONFIGURATION`).
- Import the bootstrap notebook into the workspace (ensure you are in the Fabric Experience):
  - `NB_BOOTSTRAP_FMD.ipynb`
  > [!NOTE]
> Make sure you set Set Spark session timeout to at least 1 hour in the workspace settings/Data Engineering/Jobs .

![Fabric Experience](/Images/FMD_Fabric_Experience.png)

### 4. Configure deployment settings

All per-customer configuration lives in **`manifest.yaml`** in the root of your
fork. Nothing is configured by editing notebook cells any more: the setup
notebooks read the manifest and fail with a readable message when a required key
is missing.

#### 4a. Fill in the manifest

Copy `manifest.example.yaml` to `manifest.yaml`, fill it in, and commit it to
your fork. The setup notebooks fetch it over HTTPS from
`raw.githubusercontent.com`, so it must be committed and the repository must be
readable.

> [!IMPORTANT]
> This template repository lists `manifest.yaml` in `.gitignore`, so the template
> never carries a specific customer's values. In **your** fork, remove that line —
> the deployment depends on the file being in git. `manifest.example.yaml` stays
> in git in both.

| Section | What it holds |
|---|---|
| `repository` | Owner, name and branch of your fork. Must match the three values in the bootstrap notebook. |
| `naming` | `domain_name` (the shared ingestion domain), `framework_pre_fix` (a prefix for every workspace and deployment pipeline name), `connection_prefix` (the prefix of the framework connections, default `CON_FMD`; choose it before the first installation), and the list of business domains. |
| `environments` | One entry per environment: `name`, `short` (D/T/A/P), `capacity`, and optionally `capacity_business_domain` for the business-domain workspaces. The order is the stage order of the deployment pipelines, and it decides which value sets are deployed. |
| `config_workspace` | Capacity for the CONFIG workspace, which exists once per customer rather than once per environment. |
| `spark` | Runtime version and Spark sizing, written into the Environment item at deploy time. One `ENV_FMD.Environment` is deployed into the CONFIG workspace and shared by every environment, so this sizing applies everywhere. |
| `framework` | `lakehouse_schema_enabled`. |
| `security` | Object IDs of the Entra groups, and optionally a service principal. |
| `key_vault` | Key Vault name, and the **names** of the secrets holding the service principal credentials. |

> [!NOTE]
> The id of a User, Group or Service Principal is the Object ID in Microsoft Entra ID.
> For a Service Principal, find the Object ID in the Azure Portal under 'Enterprise
> applications' — not the Object ID of the App Registration.

> [!NOTE]
> If you are deploying on your own and have no groups or service principal to add,
> leave the IDs in `security` on all zeros. Those entries are skipped, and the
> deployer already owns the workspaces it creates, so nothing is lost. An ID that
> does not resolve in your tenant makes the role assignment fail silently.

> [!IMPORTANT]
> All zeros is only safe for the **first** FMD installation in a tenant. Connection
> names are tenant-wide and get no `framework_pre_fix`, so a second installation (a
> trial next to production, a reinstall) with the same `naming.connection_prefix` reuses the
> existing `CON_FMD_*` connections,
> including their credential. If `CON_FMD_FABRIC_PIPELINES` runs as a service principal
> that has no role on the new workspaces, every `InvokePipeline` in `PL_FMD_LOAD_ALL`
> fails with `InsufficientPrivileges` (403), while the setup run itself stays green.
>
> Before a second installation, check which identity the existing connections use,
> and give it a role on the new workspaces:
> - `security.service_principal_id` gets Contributor on the integration workspaces
>   (CODE, DATA, CONFIG), but `NB_SETUP_BUSINESS_DOMAINS` does not assign it to the
>   business-domain workspaces, where `PL_FMD_ORCHESTRATION` invokes the Gold
>   pipelines;
> - adding the identity to the group in `security.admin_group_id` covers both, because
>   that group is assigned everywhere;
> - `contributor_group_id` is not assigned on any CODE workspace, so it does not help.

#### 4b. Point the bootstrap at your fork

Open `NB_BOOTSTRAP_FMD.ipynb` and set:

```python
repo_owner    = "your-org"           # GitHub organisation or user
repo_name     = "FMD_FRAMEWORK"      # Repository name
branch        = "main"               # Branch to deploy from
folder_prefix = ""                   # Only if src/ and config/ live in a subfolder
github_token_key_vault = ""          # Key Vault name holding a GitHub PAT; empty = public repo
github_token_secret    = ""          # Secret name of that PAT in the vault above
```

These must match `repository:` in the manifest. The setup notebooks verify this
and stop with an error when the two disagree, because otherwise `src/` and
`config/` would come from a different repository than the manifest describes.

> [!NOTE]
> **Private fork.** `manifest.yaml` itself is fetched before it can be parsed, so
> the token cannot live in the manifest. Fill in `github_token_key_vault` and
> `github_token_secret` here instead; the bootstrap notebook stamps them into
> `NB_SETUP_FMD` and `NB_SETUP_BUSINESS_DOMAINS` alongside `repo_owner` etc., and
> every GitHub request (the manifest, the `src`/`config` zip, the demo data) is
> then sent with that token. Leave both empty for a public repo — nothing
> changes from before.

Run the bootstrap notebook. It creates or updates `NB_SETUP_FMD` and
`NB_SETUP_BUSINESS_DOMAINS` in the workspace, with these values stamped into
their bootstrap cell.

### 5. Run the deployment

Execute the **notebook** to apply your configuration and deploy the framework.

---

Check out the [wiki](https://github.com/edkreuk/FMD_FRAMEWORK/wiki) for more information and detailed guidance on using the FMD Framework and how to load demo data.




