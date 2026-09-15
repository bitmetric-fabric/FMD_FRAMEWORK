---
Title: Deploy the Business Domain for the FMD Framework
Description: Learn how to deploy the Fabric Metadata-Driven Framework (FMD) in Microsoft Fabric, including prerequisites, setup, and configuration.
Topic: how-to

Author: edkreuk
---

A modular extension of the Fabric Metadata-Driven Framework (FMD) designed to simplify, standardize, and automate deployment of Business Domains within Microsoft Fabric. The Business Domain Framework enables organizations to scale analytics through a governed, metadata-driven approach where each business domain (for example, Sales, HR, Finance, Operations) is deployed consistently using reusable patterns, automated provisioning, and ready-to-use template assets.

The FMD Business Domain Framework delivers everything needed to deploy a domain‑driven analytics workspace in Microsoft Fabric. It builds upon the core FMD Metadata Model by providing:

- Automated domain workspace provisioning
- Domain‑specific Lakehouse creation
- Standardized Gold‑layer table patterns (dimensions and facts)
- Deployment scripts using the Microsoft Fabric CLI
- Metadata‑driven orchestration for repeatable ingestion, transformation, and modeling
- Integration with existing FMD configuration and execution schemas

This framework ensures that every business domain is created in a consistent, scalable, and governed way, accelerating enterprise-grade analytics delivery.

# Deploy the FMD Business Domain Framework in Microsoft Fabric

![FMD Overview](/Images/FMD_DOMAIN_OVERVIEW.png)

This article describes how to deploy the Business Domains in Microsoft Fabric. Follow these steps to configure your environment, set up required connections, and apply deployment settings.

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

**Developer settings:**

- Service principals can create workspaces, connections, and deployment pipelines
- Service principals can call Fabric public APIs

**Admin API settings:**

- Service principals can access read-only admin APIs
- Service principals can access admin APIs used for update

> [!NOTE]
> In case you need to use a **security group**, add the security group to the settings above.
> Add Workspace identity (after deployment) or Service Principal to the security groups.

### Managed identity or Service Principal used for execution must have the following role assigned:

- Workspace Contributor role on the workspace (Workspace Identity is automatically assigned during deployment, Service principal must be assigned manually)
- Managed identity or Service Principal must be added to the correct security groups which have been assigned in the Prerequisite step

## Deployment steps

### 1. Download deployment assets

If you already deployed the integration framework, `NB_SETUP_BUSINESS_DOMAINS`
is already in your configuration workspace: the bootstrap notebook places both
setup notebooks at once. In that case skip to step 3.

Otherwise download a single file from the `setup` folder:

- `NB_BOOTSTRAP_FMD.ipynb` – fetches the setup notebooks from your fork and places them in the workspace.

### 2. Create a configuration workspace

- Create a new workspace (for example, `FMD_FRAMEWORK_CONFIGURATION`).
- Import the bootstrap notebook into the workspace (ensure you are in the Fabric Experience):
  - `NB_BOOTSTRAP_FMD.ipynb`

> [!NOTE]
> Make sure you set Spark session timeout to at least 1 hour in the workspace settings/Data Engineering/Jobs.

![Fabric Experience](/Images/FMD_Fabric_Experience.png)

### 3. Configure deployment settings

All per-customer configuration lives in **`manifest.yaml`** in the root of your
fork — the same file the integration framework uses. Nothing is configured by
editing notebook cells any more.

The keys this notebook needs on top of the integration ones:

| Key | What it holds |
|---|---|
| `naming.business_domains` | The business domains to create, for example `[FINANCE, SALES]`. Each gets a CODE, DATA, REPORTING and SEMANTIC workspace per environment. |
| `naming.domain_name` | Used to find the integration domain's CONFIG workspace and metadata database, so they are not configured separately here. |
| `environments[].capacity_business_domain` | Optional. The capacity the business-domain workspaces land on, per environment. Left out, they share `environments[].capacity` with the integration layer. |
| `security` | Object IDs of the Entra groups that get access to the business-domain workspaces. |

See `manifest.example.yaml` for the full structure, and
[FMD_FRAMEWORK_DEPLOYMENT.md](FMD_FRAMEWORK_DEPLOYMENT.md#4-configure-deployment-settings)
for how to fill in and commit the manifest.

> [!NOTE]
> Business-domain workspaces share `environments[].capacity` with the integration
> workspaces unless you set `capacity_business_domain` on that environment. Either
> way it is a manifest change, not a notebook change.

### 4. Run the deployment

Execute the **notebook** to apply your configuration and deploy the framework.

---

Check out the [wiki](https://github.com/edkreuk/FMD_FRAMEWORK/wiki) for more information and detailed guidance on using the FMD Framework and how to load demo data.




