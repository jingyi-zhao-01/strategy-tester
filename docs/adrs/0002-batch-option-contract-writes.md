# ADR 0002: Batch Option Contract Writes to Reduce DB Burst Pressure

- Status: Accepted
- Date: 2026-06-09
- Implemented: 2026-06-09
- Owners: strategy-tester option ingestion runtime

## Context

`option-ingestor` currently retrieves all contracts for one underlying and writes them with:

- one Prisma `upsert` per contract
- one large `asyncio.gather(...)` over the full contract list

This design is logically correct and remains idempotent because writes are keyed by ticker, but it creates an avoidable burst pattern:

- a large number of pending coroutines are created at once
- a single underlying can fan out into many short-lived DB write attempts
- transient Neon / pooler transport faults affect a wider slice of the run
- failures are more likely to leave the job in a partially completed state before retry

Observed production symptoms include transient database connectivity faults such as:

- `Can't reach database server`
- `ClientNotConnectedError`
- transport-layer read / protocol errors

Connection count evidence did not clearly show a saturated Postgres backend. That suggested the immediate bottleneck was not only raw database capacity, but also the ingestion write pattern itself.

## Decision

For `option-ingestor`, contract writes will be submitted in smaller batches instead of one full-list `gather`.

The runtime now:

1. splits contract writes into bounded batches
2. executes one batch at a time
3. keeps the existing per-contract `upsert` semantics
4. keeps the existing DB retry / backoff behavior
5. keeps `INGEST_DB_CONCURRENCY_LIMIT` as the hard concurrency guard

A new runtime knob is introduced:

- `INGEST_DB_WRITE_BATCH_SIZE`

This controls how many write coroutines are created per batch for one underlying.

## Sequence Diagram

This diagram highlights the behavioral change from one large write burst to bounded sequential batches.

- red box: previous full-list fan-out
- green box: current batched write pattern

![ADR 0002 batch option contract writes sequence](./diagrams/0002-batch-option-contract-writes-sequence.svg)

## Consequences

Expected benefits:

- fewer pending DB write coroutines at once
- lower burst pressure against Neon / pooler
- smaller blast radius when a transient DB error happens mid-run
- easier tuning through Helm values without changing code

Integrity impact:

- successful writes still commit normally
- failed writes still fail the job rather than being silently ignored
- because the write path remains `upsert`-based, rerunning the job should not create duplicate contract rows
- the main remaining integrity risk is partial completion during a failed run, not data corruption

Tradeoffs:

- one underlying may take slightly longer to finish because writes are no longer launched all at once
- the optimization reduces burstiness, but it does not replace the need for sensible DB concurrency limits
- this is not yet a true bulk SQL upsert implementation

## Alternatives Considered

1. Increase Neon compute first

Rejected as the first move because connection graphs did not clearly show backend saturation, and a code-level burst reduction is cheaper and safer to try first.

2. Leave full-list `gather` in place and only reduce `INGEST_DB_CONCURRENCY_LIMIT`

Rejected because semaphore-only control still creates a large number of pending coroutines and keeps the same bursty scheduling shape.

3. Rewrite the write path to raw SQL bulk upsert immediately

Deferred. This may still be worthwhile later, but batching the current Prisma path is a smaller change with lower rollout risk.

## Implementation

Implemented in:

- [microservices/option_ingestor/ingestor.py](../../../microservices/option_ingestor/ingestor.py)
- [charts/strategy-tester/values.yaml](../../../charts/strategy-tester/values.yaml)

## Follow-Up

1. Observe whether transient Neon connectivity failures drop after batching.
2. If failures remain, consider reducing `INGEST_DB_CONCURRENCY_LIMIT` further.
3. If runtime becomes too slow, evaluate a true bulk upsert path for contracts.
