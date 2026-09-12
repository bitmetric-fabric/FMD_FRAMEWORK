# LoadGroup Scheduling — Different Cadences per Data Source

## Overview

`LoadGroup` lets you run **different data sources on different schedules** —
for example, two sources loaded only overnight and two other sources loaded
every two hours — without duplicating any pipeline. Every source keeps a
`LoadGroup` tag in the metadata; `PL_FMD_LOAD_ALL` (and its children) accept a
`LoadGroup` parameter and only pick up sources tagged with that value.

---

## Why this exists

Microsoft Fabric's own schedule trigger cannot carry parameters: every
scheduled run of an item uses that item's design-time default values, and the
job-scheduler API's `parameters` field is explicitly **not supported** for
Data Pipelines ([Job Scheduler REST API](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/create-item-schedule)).
So one pipeline cannot have two schedules that load two different sets of
sources — the schedule can't tell it which set to use.

`LoadGroup` works around this by moving the "which sources" decision into the
metadata (a column on `integration.DataSource`) and having each schedule
target its own thin wrapper pipeline that hard-codes only the group name. The
schedule still can't carry a parameter — but the wrapper pipeline it points
to needs exactly one.

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

**The empty string is not a group — it means "no filter".** A source with
`LoadGroup = ''` (the default) is picked up by *every* run regardless of what
`LoadGroup` the caller passed in, and calling the top-level pipeline with
`LoadGroup = ''` loads *all* sources exactly as before. This is what keeps
existing deployments working unchanged: nothing has to be tagged for the
framework to behave exactly as it did before this feature.

A non-empty `LoadGroup` is an exact match: a run with `LoadGroup = 'NIGHTLY'`
only picks up sources tagged `NIGHTLY`, never `''` or any other group.

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

Leave `@LoadGroup` unset (or `''`) for sources that should load on every run,
regardless of which schedule triggered it.

### 2. Create one thin wrapper pipeline per schedule

The framework does not ship one of these per business implementation —
the group names and cadences are yours to define. Each wrapper is a single
`InvokePipeline` activity calling `PL_FMD_LOAD_ALL` (or, if you only need one
layer, `PL_FMD_LOAD_LANDINGZONE` / `_BRONZE` / `_SILVER` directly) with
`LoadGroup` set to a literal:

| Wrapper pipeline | Invokes | `LoadGroup` |
|---|---|---|
| `PL_FMD_SCHEDULE_NIGHTLY` | `PL_FMD_LOAD_ALL` | `"NIGHTLY"` |
| `PL_FMD_SCHEDULE_INTRADAY` | `PL_FMD_LOAD_ALL` | `"INTRADAY"` |

`Data_WorkspaceGuid` still has to be passed through as usual.

### 3. Schedule each wrapper independently

In the Fabric portal, open each wrapper pipeline's **Settings → Schedule**
and configure its own cadence — e.g. `PL_FMD_SCHEDULE_NIGHTLY` daily at
02:00, `PL_FMD_SCHEDULE_INTRADAY` every 2 hours. Each schedule triggers its
own wrapper with its own baked-in `LoadGroup`, so the two cadences never
interfere with each other.

---

## Design notes

- **Bronze and Silver are filtered too, not just Landingzone.** A group's
  intraday run only reprocesses Bronze/Silver entities belonging to that
  group's sources — it does not re-touch the nightly sources' Bronze/Silver
  tables. This keeps a frequent schedule cheap and keeps the audit log
  readable per run.
- **Gold is untouched by this feature.** If a Gold model joins a nightly
  source with an intraday one, decide separately whether Gold refreshes per
  group or once after the nightly run — `LoadGroup` only reaches through
  Landingzone/Bronze/Silver.
- **Groups can overlap in time.** Two schedules with different groups share
  the same Spark capacity (`NB_FMD_PROCESSING_PARALLEL_MAIN`); staggering
  cadences avoids them competing for the same pool.
- **A source not yet tagged behaves exactly as before.** `LoadGroup = ''` is
  the column default, so upgrading the framework requires no metadata
  migration for existing sources.

---

## Related Resources

- [FMD Business Domain Deployment Guide](../FMD_BUSINESS_DOMAIN_DEPLOYMENT.md)
- [Job Scheduler — Create Item Schedule (REST API)](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/create-item-schedule)
- [FMD Framework documentation](https://erwindekreuk.com/fmd-framework/)
