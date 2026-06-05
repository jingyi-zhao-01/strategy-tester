# ADR 0001: Use Job-Scoped Prisma Connection Lifecycle for Ingestion Runtimes

- Status: Proposed
- Date: 2026-06-05
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

This ADR is documentation only at this stage.

No implementation is approved by this document alone, and the current decorator-based connection lifecycle remains in place until a separate code change is made.

## Consequences

Expected benefits:

- simpler mental model for CronJob runtime behavior
- lower chance of accidental mid-job disconnect behavior
- easier correlation between one job run and one database session lifecycle
- cleaner future instrumentation around job-level database health

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

Before implementation, a follow-up change should:

1. move `connect()` / `disconnect()` to the top-level runtime entrypoints
2. remove or narrow function-level connection wrappers
3. add tests for normal completion, exception handling, and async generator flows
4. verify that job-level lifecycle still respects existing database concurrency semaphores
