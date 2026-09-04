"""Deploy src/ (core framework code, excluding business_domain/) to an INTEGRATION CODE workspace.

Ongoing CI/CD for notebooks, pipelines, variable libraries and the environment — separate
from setup/NB_SETUP_FMD.ipynb, which only does the one-time initial provisioning.

Usage: python deploy_fabric_cicd.py <development|test|production>
Requires env vars: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
"""

import sys

from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, append_feature_flag, publish_all_items

# folder_path_exclude_regex (used below to keep business_domain/ out of this deploy)
# is experimental and needs both flags. Microsoft's docs warn selective deployment
# can miss dependencies; acceptable here since it's one self-contained subfolder.
append_feature_flag("enable_experimental_features")
append_feature_flag("enable_exclude_folder")

WORKSPACE_IDS = {
    "development": "830116ef-d6a0-405e-a2b8-d43a41bddb24",  # INTEGRATION CODE (D)
    "test": "db4ec291-fca7-415a-a6cd-4f1b34885701",  # INTEGRATION CODE (T)
    "production": "03e1bdd0-b4f4-4ae8-8616-50ad52d8bcdd",  # INTEGRATION CODE (P)
}

# business_domain/ deploys to FINANCE/SALES/HR CODE workspaces separately, not here.
BUSINESS_DOMAIN_EXCLUDE_REGEX = r"business_domain"

# Two pipelines that fail to publish, for reasons unrelated to this CI/CD setup - excluded
# so a real regression doesn't get lost in permanent noise. Revisit once fixed upstream:
#  - PL_FMD_LDZ_COPY_FROM_ADF: needs CON_FMD_ADF_PIPELINES, which was never set up in
#    this tenant (optional per the deployment docs - only needed if you use ADF).
#  - PL_TOOLING_POST_ASQL_TO_FMD: its connection is a runtime pipeline parameter
#    (@pipeline().parameters.ConnectionGuid) rather than a fixed GUID, which Fabric's
#    definition validation rejects with a generic error. Needs its own investigation.
BROKEN_PIPELINES_EXCLUDE_REGEX = r"^(PL_FMD_LDZ_COPY_FROM_ADF|PL_TOOLING_POST_ASQL_TO_FMD)$"


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in WORKSPACE_IDS:
        sys.exit(f"Usage: python {sys.argv[0]} <{'|'.join(WORKSPACE_IDS)}>")
    environment = sys.argv[1]

    credential = ClientSecretCredential(
        tenant_id=_require_env("AZURE_TENANT_ID"),
        client_id=_require_env("AZURE_CLIENT_ID"),
        client_secret=_require_env("AZURE_CLIENT_SECRET"),
    )

    workspace = FabricWorkspace(
        workspace_id=WORKSPACE_IDS[environment],
        # Capitalized to match the Development/Test/Production value set names in the
        # VariableLibrary items - fabric-cicd matches this case-sensitively to activate
        # the right value set, else it silently falls back to 'Default value set'.
        environment=environment.capitalize(),
        repository_directory="src",
        item_type_in_scope=["Notebook", "DataPipeline", "VariableLibrary", "Environment"],
        token_credential=credential,
    )

    publish_all_items(
        workspace,
        folder_path_exclude_regex=BUSINESS_DOMAIN_EXCLUDE_REGEX,
        item_name_exclude_regex=BROKEN_PIPELINES_EXCLUDE_REGEX,
    )
    # ponytail: no unpublish_all_orphan_items() yet — first pilot run, don't auto-delete
    # items on the target workspace. Add once a few deploys have gone through and you
    # trust the exclude regex isn't also catching something it shouldn't.


def _require_env(name: str) -> str:
    import os

    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required env var: {name}")
    return value


if __name__ == "__main__":
    main()
