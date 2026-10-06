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
own parameter values. `PL_FMD_ORCHESTRATION_TEMPLATE` takes a `LoadGroup`
parameter, so one pipeline carries all schedules: for example a nightly one
without a group and an intraday one with `LoadGroup = INTRADAY`
([Run, schedule, or use events to trigger a pipeline](https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-runs)).

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

### 2. Schedule `PL_FMD_ORCHESTRATION_TEMPLATE`, once per cadence (recommended)

`PL_FMD_ORCHESTRATION_TEMPLATE` runs `PL_FMD_LOAD_ALL` and then the Gold
pipeline of every business domain (the setup wires those in). It takes a
`LoadGroup` parameter and passes it to `PL_FMD_LOAD_ALL`.

In the Fabric portal, open the pipeline's **Schedule** and add one schedule
per cadence, each with its own parameter value:

| Schedule | Cadence (example) | `LoadGroup` |
|---|---|---|
| Nightly | daily at 02:00 | *(empty: all sources)* |
| Intraday | every 2 hours, 08:00–18:00 | `INTRADAY` |

Through the REST API, a schedule takes the parameter as
`"executionData": {"parameters": {"LoadGroup": "INTRADAY"}}`. The value is
stored in the item definition (`.schedules`), not in the schedule list that
`GET …/schedules` returns.

- **Overlap:** the pipeline has `concurrency: 1`. A run that starts while
  another one is busy waits until it is done, so the nightly and an intraday
  run never load the same entities at the same time.
- **Gold runs after every run**, also after an intraday run. On a small
  capacity, keep that in mind when choosing the intraday cadence.
- **Promotion:** schedules are part of the item definition, so a
  Deployment-Pipeline promotion copies them (with their parameters) to the
  target stage, enabled. *Failure notifications* are **not** copied: add the
  recipients again in every stage, and check the times.

### 3. Alternative: one thin wrapper pipeline per schedule

These wrappers call `PL_FMD_LOAD_ALL` directly, so they **do not run Gold**,
and nothing prevents two of them from overlapping. Prefer step 2.

The framework ships two ready-to-use examples of this pattern:
`PL_FMD_SCHEDULE_NIGHTLY` and `PL_FMD_SCHEDULE_INTRADAY`. Each is a single
`InvokePipeline` activity calling `PL_FMD_LOAD_ALL` with `LoadGroup` hard-coded
to a literal:

| Wrapper pipeline | Invokes | `LoadGroup` |
|---|---|---|
| `PL_FMD_SCHEDULE_NIGHTLY` | `PL_FMD_LOAD_ALL` | `"NIGHTLY"` |
| `PL_FMD_SCHEDULE_INTRADAY` | `PL_FMD_LOAD_ALL` | `"INTRADAY"` |

Rename or duplicate these for whatever group names and cadences your
implementation actually needs — `NIGHTLY`/`INTRADAY` are examples, not
reserved values. A new one is a copy-paste of the folder plus one entry in
`config/item_deployment.json` placed after `PL_FMD_LOAD_ALL`'s entry (so its
real object ID is already known when the wrapper's placeholder reference to
it gets resolved at deploy time) — the same recipe as any other new pipeline
entering the framework. If you only need one layer filtered rather than the
full chain, point the wrapper at `PL_FMD_LOAD_LANDINGZONE` / `_BRONZE` /
`_SILVER` instead.

`Data_WorkspaceGuid` still has to be passed through as usual.

Schedule each wrapper on its own pipeline. Note that `PL_FMD_SCHEDULE_NIGHTLY`
passes `NIGHTLY`, so it skips every source with `LoadGroup = ''`.

---

## Design notes

- **Bronze and Silver are filtered too, not just Landingzone.** A group's
  intraday run only reprocesses Bronze/Silver entities belonging to that
  group's sources — it does not re-touch the nightly sources' Bronze/Silver
  tables. This keeps a frequent schedule cheap and keeps the audit log
  readable per run.
- **Gold is not filtered by `LoadGroup`.** Through
  `PL_FMD_ORCHESTRATION_TEMPLATE`, every run refreshes Gold for all business
  domains, after `PL_FMD_LOAD_ALL` succeeded.
- **Overlap.** On `PL_FMD_ORCHESTRATION_TEMPLATE`, `concurrency: 1` queues a
  second run. With the wrapper pipelines, two groups can run at the same time
  and share the same Spark capacity (`NB_FMD_PROCESSING_PARALLEL_MAIN`);
  stagger their cadences.
- **A source not yet tagged behaves exactly as before.** `LoadGroup = ''` is
  the column default, so upgrading the framework requires no metadata
  migration for existing sources.

---

## Related Resources

- [FMD Business Domain Deployment Guide](../FMD_BUSINESS_DOMAIN_DEPLOYMENT.md)
- [Job Scheduler — Create Item Schedule (REST API)](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/create-item-schedule)
- [FMD Framework documentation](https://erwindekreuk.com/fmd-framework/)
