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

Set up the following connections and note their Connection IDs for later configuration:

| Connection name              | Connection type            | Authentication                                    |Remarks |
|------------------------------|----------------------------|---------------------------------------------------|--------|
| CON_FMD_FABRIC_PIPELINES     | Fabric Data Pipelines      | OAuth2/Service Principal/Workspace Identity       |  Connection is automatically created during deployment      |
| CON_FMD_FABRIC_SQL           | Fabric SQL database        | OAuth2                        |  See below: cannot be created before the first deployment run      |
| CON_FMD_FABRIC_NOTEBOOKS     | Fabric Notebooks           | OAuth2/Service Principal/Workspace Identity       |  For future use     |

> [!IMPORTANT]
> **`CON_FMD_FABRIC_SQL` cannot be created at this point.** A Fabric SQL database connection has to name an existing database, and `SQL_FMD_FRAMEWORK` is created by the deployment in step 5. So the order is:
>
> 1. Run the deployment (step 5). It creates the database. Every activity that needs this connection is left without one.
> 2. Create `CON_FMD_FABRIC_SQL` against the now existing `SQL_FMD_FRAMEWORK`, in the workspace `<domain_name> CONFIGURATION`.
> 3. **Run the deployment a second time**, so the pipelines are redeployed with the connection bound.
>
> The second run is not optional. Until it happens, Fabric writes the lookup error into the pipelines' `externalReferences.connection` field, marks all five audit activities `"state": "Inactive"` with `"onInactiveMarkAs": "Succeeded"`, and every pipeline then reports success while `logging` never receives a row. Nothing fails and nothing warns.

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
| `naming` | `domain_name` (the shared ingestion domain), `framework_pre_fix` (a prefix for every workspace and deployment pipeline name), and the list of business domains. |
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

#### 4b. Point the bootstrap at your fork

Open `NB_BOOTSTRAP_FMD.ipynb` and set:

```python
repo_owner    = "your-org"           # GitHub organisation or user
repo_name     = "FMD_FRAMEWORK"      # Repository name
branch        = "main"               # Branch to deploy from
folder_prefix = ""                   # Only if src/ and config/ live in a subfolder
```

These must match `repository:` in the manifest. The setup notebooks verify this
and stop with an error when the two disagree, because otherwise `src/` and
`config/` would come from a different repository than the manifest describes.

Run the bootstrap notebook. It creates or updates `NB_SETUP_FMD` and
`NB_SETUP_BUSINESS_DOMAINS` in the workspace, with these values stamped into
their bootstrap cell.

### 5. Run the deployment

Execute the **notebook** to apply your configuration and deploy the framework.

---

Check out the [wiki](https://github.com/edkreuk/FMD_FRAMEWORK/wiki) for more information and detailed guidance on using the FMD Framework and how to load demo data.




