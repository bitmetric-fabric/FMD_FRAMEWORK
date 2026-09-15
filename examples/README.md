# Examples

Demo material. Nothing in this folder is deployed: none of it appears in
`config/item_deployment*.json`, so `deploy_item()` never picks it up. Copy what
you need into `src/` and register it there.

It lives apart from `src/` because it carries identifiers from the tenant it was
built in — lakehouse and workspace bindings that resolve nowhere else. Inside
`src/` those would be deployed to every customer and silently point at a stranger's
tenant; here they are clearly examples to read, not code to ship. The GUID guard
(`scripts/guid_guard.py`) scans `src/`, `setup/` and `wiki/`, and deliberately not
this folder.

| | |
|---|---|
| `NB_CREATE_DIMDATE.Notebook` | Builds a date dimension. Rebind the default lakehouse before running. |
| `NB_MLV_DEMO_GOLD.Notebook` | A complete Materialized Lake View implementation on the demo dataset. The shipped template is `src/business_domain/NB_MLV_EXAMPLE.Notebook`. |
| `FMD_FABRIC_TASKFLOW.json` | Exported Fabric taskflow, as documentation of how the items hang together. |
