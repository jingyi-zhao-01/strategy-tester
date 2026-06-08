# ADR 0001: Use Job-Scoped Prisma Connection Lifecycle for Ingestion Runtimes

- Status: Accepted
- Date: 2026-06-05
- Implemented: 2026-06-08
- Owners: strategy-tester ingestion runtime

## Context

`strategy-tester` runs two independent ingestion runtimes as Kubernetes `CronJob`s:

- `option-ingestor`
- `snapshot-ingestor`

Each job runs as a short-lived process. The Prisma client is currently instantiated once per process in [microservices/shared/decorator.py](../../../microservices/shared/decorator.py), but connection management is handled by function-level decorators:

- `@bounded_db_connection`
- `@bounded_db_connection_asyncgen`

This means the process does not create a new Prisma client for every operation, but it can still enter multiple `connect()` / `disconnect()` boundaries during a single job execution. The behavior is especially subtle in the snapshot ingestion path, where nested database wrappers are involved:

- `ingest_option_snapshots()`
- `stream_retrieve_active()`

Current observed risks:

- connection lifecycle is harder to reason about than the process lifecycle
- nested wrappers make it less obvious when disconnects happen
- `ClientNotConnectedError` is plausible under async edge cases
- operationally, a CronJob batch worker is a better fit for connect-once / disconnect-once semantics

## Decision

For ingestion runtimes, the preferred design is:

1. Initialize the Prisma client once per process, as today.
2. Connect to the database once at job startup.
3. Reuse that connected client throughout the full ingestion run.
4. Disconnect once during orderly job shutdown.

Database concurrency limits should still be enforced separately through:

- `DATABASE_URL` `connection_limit`
- `INGEST_DB_CONCURRENCY_LIMIT`

This ADR does **not** approve removing concurrency controls. It only changes the recommended connection lifecycle boundary from function-scoped to job-scoped.

## Status of Implementation

This ADR is implemented.

The runtime now manages Prisma lifecycle at the top-level service entrypoints:

- [microservices/option_ingestor/service.py](../../../microservices/option_ingestor/service.py)
- [microservices/snapshot_ingestor/service.py](../../../microservices/snapshot_ingestor/service.py)

The shared decorators still enforce database concurrency boundaries, but they no longer own `connect()` / `disconnect()` transitions for each wrapped function call.

## Consequences

Expected benefits:

- simpler mental model for CronJob runtime behavior
- lower chance of accidental mid-job disconnect behavior
- easier correlation between one job run and one database session lifecycle
- cleaner future instrumentation around job-level database health
- lower likelihood that one transient database fault cascades into extra client lifecycle errors

Tradeoffs:

- a failed job may hold its database connection open for longer than a function-scoped pattern
- shutdown handling must be explicit and reliable
- implementation needs regression coverage for both normal completion and exception paths

## Non-Goals

This ADR does not:

- change the current Helm values
- change `connection_limit=1200` in the external `DATABASE_URL`
- define final production values for database concurrency
- address Polygon API authorization failures or network timeout behavior

## Follow-Up

Implemented by:

1. moving `connect()` / `disconnect()` to the top-level runtime entrypoints
2. narrowing function-level wrappers so they only enforce concurrency boundaries
3. adding regression tests for normal completion and exception handling at service runtime boundaries

Remaining follow-up:

1. review whether current DB concurrency defaults should be reduced further under production load
2. consider chunked writes for large option batches to reduce blast radius during database instability
