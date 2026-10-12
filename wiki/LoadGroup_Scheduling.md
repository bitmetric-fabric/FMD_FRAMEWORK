# LoadGroup Scheduling — Different Cadences per Data Source

## Overview

`LoadGroup` lets you run **different data sources on different schedules** —
for example, two sources loaded only overnight and two other sources loaded
every two hours — without duplicating any pipeline. Every source keeps a
`LoadGroup` tag in the metadata; `PL_FMD_LOAD_ALL` (and its children) accept a
`LoadGroup` parameter and only pick up sources tagged with that value.

---

## Why this exists

The "which sources" decision lives in the metadata (a column on
`integration.DataSource`), so a schedule only has to say which group it runs.

A Fabric pipeline can have up to 20 schedules, and each schedule can pass its
own parameter values. The schedule pipeline of an environment
(`PL_FMD_SCHEDULE_<short>`, see below) takes a `LoadGroup` parameter, so one
pipeline carries all schedules of that environment: for example a nightly one
without a group and an intraday one with `LoadGroup = INTRADAY`
([Run, schedule, or use events to trigger a pipeline](https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-runs)).

The schedules do not sit on the pipelines in the CODE workspaces. A schedule is
part of the item definition, so a Deployment-Pipeline promotion would copy it,
enabled and with the times of the source stage, to the next stage. The schedule
pipelines live in the CONFIG workspace instead, which is in no deployment
pipeline.

An earlier version of this page said schedules could not carry parameters for
Data Pipelines. That is no longer true: a schedule created with
`executionData.parameters` passes them to the run (tested 2026-10-06).

---

## How it works

`DataSource.LoadGroup` (`VARCHAR(50)`, default `''`) tags each source.
`vw_LoadSourceToLandingzone`, `vw_LoadToBronzeLayer` and `vw_LoadToSilverLayer`
all expose it, and `sp_GetBronzelayerEntity` / `sp_GetSilverlayerEntity` take
a `@LoadGroup` parameter that filters by it.

Every pipeline in the load chain (`PL_FMD_LOAD_ALL`, `PL_FMD_LOAD_LANDINGZONE`,
`PL_FMD_LOAD_BRONZE`, `PL_FMD_LOAD_SILVER`, and every `PL_FMD_LDZ_COMMAND_*` /
`PL_FMD_LDZ_COPY_FROM_*` pipeline underneath them) now takes a `LoadGroup`
parameter, defaulting to `''`, and passes it down to the next pipeline in the
chain the same way it already passes `Data_WorkspaceGuid`.

**An empty `LoadGroup` on the run means "no filter".** Calling the top-level
pipeline with `LoadGroup = ''` (the default) loads *all* sources, whatever
their tag. This is what keeps existing deployments working unchanged.

A non-empty `LoadGroup` on the run is an exact match: a run with
`LoadGroup = 'NIGHTLY'` only picks up sources tagged `NIGHTLY`. **A source with
`LoadGroup = ''` is not picked up by such a run.** The filter in every load
pipeline is `'' = <run LoadGroup> OR LoadGroup = <run LoadGroup>`.

So: give the nightly schedule no group, so it loads everything, and tag only
the sources that need an extra cadence (for example `INTRADAY`).

---

## Setting it up

### 1. Tag your data sources

Pass `@LoadGroup` when registering or updating a source:

```sql
EXEC [integration].[sp_UpsertDataSource]
    @ConnectionId = 4,
    @Name = 'Customers',
    @Namespace = 'crm',
    @Type = 'ASQL_01',
    @Description = 'CRM customer export',
    @LoadGroup = 'NIGHTLY';
```

Leave `@LoadGroup` unset (or `''`) for sources that only need to load in the
run without a group (typically the nightly run).

### 2. Schedule `PL_FMD_SCHEDULE_<short>` in the CONFIG workspace, once per cadence

The setup creates one schedule pipeline per environment in the CONFIG
workspace, in the folder `SchedulePipelines`: `PL_FMD_SCHEDULE_D`, `_T` and `_P` for
Development, Test and Production. It creates each one once and never
overwrites it, so a setup update leaves your schedules and recipients alone.

A schedule pipeline has two parameters and one Switch on `Target`:

| `Target` | Invokes (in the CODE workspace of that environment) |
|---|---|
| `LOAD` (default) | `PL_FMD_ORCHESTRATION`, with `LoadGroup` |
| `MAINTENANCE` | `PL_FMD_MAINTENANCE` |
| anything else | fails with `UnknownTarget`, so a typo shows as a failed run |

`PL_FMD_ORCHESTRATION` runs `PL_FMD_LOAD_ALL` and then the Gold
pipeline of every business domain (the setup wires those in). The schedule
pipeline waits for the result, so a failure in the orchestration, in Gold or
in the maintenance notebook turns the schedule pipeline red.

In the Fabric portal, open the schedule pipeline's **Schedule** and add one
schedule per cadence, each with its own parameter values:

| Schedule | Cadence (example) | `Target` | `LoadGroup` |
|---|---|---|---|
| Nightly | daily at 02:00 | `LOAD` | *(empty: all sources)* |
| Intraday | every 2 hours, 08:00–18:00 | `LOAD` | `INTRADAY` |
| Maintenance | Sunday at 03:00 | `MAINTENANCE` | |

Through the REST API, a schedule takes the parameters as
`"executionData": {"parameters": {"Target": "LOAD", "LoadGroup": "INTRADAY"}}`.
The value is stored in the item definition (`.schedules`), not in the schedule
list that `GET …/schedules` returns.

Set **Failure notifications** on the schedule pipeline, once per environment.
They only cover scheduled runs and can only be set in the portal. Leave them
empty in Development to avoid mail for a failed development run.

- **Overlap:** the schedule pipeline has `concurrency: 1`, and so does the
  orchestration. A run that starts while another one is busy waits until it is
  done, so the nightly and an intraday run never load the same entities at the
  same time.
- **Gold runs after every `LOAD` run**, also after an intraday run. On a small
  capacity, keep that in mind when choosing the intraday cadence.
- **Promotion:** CONFIG is in no deployment pipeline, so a promotion never
  copies a schedule, its parameters or its recipients. Each environment keeps
  its own times.
- **Which source is loaded** is not decided here. The orchestration in each
  CODE workspace loads the DATA workspace of its own environment (via
  `VAR_CONFIG_FMD`, with the active value set).
- **Not in git.** The schedules live in the CONFIG workspace, which is not
  connected to git. Write the times, `Target` and `LoadGroup` values and
  recipients down in the implementation plan of the customer.
- **If an item is re-created.** The schedule pipeline refers to the CODE
  workspace and to the orchestration and maintenance pipelines by ID. If one
  of those gets a new ID (a re-created workspace or pipeline), update the
  schedule pipeline, or delete it and run the setup again to create it anew.
  Deleting it also deletes its schedules and recipients.

### 3. Existing installations: schedules on the pipelines in CODE

Installations from before the schedule pipelines have their schedules on
`PL_FMD_ORCHESTRATION` and `PL_FMD_MAINTENANCE` in the CODE
workspaces, and possibly the wrapper pipelines `PL_FMD_SCHEDULE_NIGHTLY` and
`PL_FMD_SCHEDULE_INTRADAY`. The setup does not remove them. They keep working,
with the drawbacks described above: a promotion copies the schedules, enabled,
to the next stage, without the recipients of the failure notifications.

To move over, add the schedules to the new schedule pipelines and delete them
from the old pipelines.

**Pipeline names.** `PL_FMD_ORCHESTRATION` and `PL_FMD_LOAD_GOLD` were called
`PL_FMD_ORCHESTRATION_TEMPLATE` and `PL_FMD_LOAD_GOLD_TEMPLATE` before. The setup looks
them up by name, so on an installation with the old names it would create new items next
to the old ones, and the schedule pipelines would keep invoking the old orchestration.
Rename the existing items in place first, in every stage (D, T, P): their IDs, the
deployment-pipeline pairing and every reference to them stay as they are. The wrappers call `PL_FMD_LOAD_ALL` directly, so they
do not run Gold, and `PL_FMD_SCHEDULE_NIGHTLY` passes `NIGHTLY`, so it skips
every source with `LoadGroup = ''`.

---

## Design notes

- **Bronze and Silver are filtered too, not just Landingzone.** A group's
  intraday run only reprocesses Bronze/Silver entities belonging to that
  group's sources — it does not re-touch the nightly sources' Bronze/Silver
  tables. This keeps a frequent schedule cheap and keeps the audit log
  readable per run.
- **Gold is not filtered by `LoadGroup`.** Through
  `PL_FMD_ORCHESTRATION`, every run refreshes Gold for all business
  domains, after `PL_FMD_LOAD_ALL` succeeded.
- **Overlap.** On the schedule pipeline and on
  `PL_FMD_ORCHESTRATION`, `concurrency: 1` queues a second run. Two
  runs started directly on `PL_FMD_LOAD_ALL` can run at the same time and
  share the same Spark capacity (`NB_FMD_PROCESSING_PARALLEL_MAIN`); stagger
  their cadences.
- **A source not yet tagged behaves exactly as before.** `LoadGroup = ''` is
  the column default, so upgrading the framework requires no metadata
  migration for existing sources.

---

## Related Resources

- [FMD Business Domain Deployment Guide](../FMD_BUSINESS_DOMAIN_DEPLOYMENT.md)
- [Job Scheduler — Create Item Schedule (REST API)](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/create-item-schedule)
- [FMD Framework documentation](https://erwindekreuk.com/fmd-framework/)
