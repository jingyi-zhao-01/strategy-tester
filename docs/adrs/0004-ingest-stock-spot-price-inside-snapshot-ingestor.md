# ADR 0004: Ingest Stock Spot Price Inside Snapshot Ingestor

- Status: Accepted
- Date: 2026-06-25
- Implemented: 2026-06-25
- Owners: strategy-tester snapshot ingestion runtime

## Context

`strategy-tester` stores option chain snapshots in `option_snapshots` and uses those rows to power volatility-surface and moneyness views.

We previously added `underlying_price` to the snapshot schema and wrote `snapshot.underlying_asset.price` into that column when present.

That path was insufficient in production because:

- the Massive / Polygon option snapshot payload frequently returns `underlying_asset.price = null`
- the current Polygon entitlement for this workload does not guarantee usable stock snapshot access through the option payload itself
- Grafana moneyness panels remain empty or degraded when `underlying_price` is missing

The remaining question was where to source stock spot price from.

## Decision

We will ingest stock spot price inside the existing `snapshot-ingestor` runtime instead of introducing a new ingestion service.

The runtime now:

1. collects distinct `underlying_ticker` values from the active option contracts for the current run
2. fetches one stock snapshot per underlying
3. throttles those stock snapshot requests with an explicit inter-request delay
4. retries bounded `429` rate-limit responses and transient network timeouts
5. logs rate-limit retries and exhausted rate-limit failures clearly
6. passes the fetched stock spot price into each option snapshot upsert for that underlying
7. falls back to the original option snapshot payload field only when no separate stock spot price is available

New runtime knob:

- `STOCK_SNAPSHOT_FETCH_INTERVAL_SECONDS`

## Why This Shape

This decision keeps the new behavior aligned with the existing snapshot lifecycle:

- stock spot price is only needed to enrich option snapshot rows
- the correct scope is one fetch per underlying per snapshot job
- keeping the fetch in `snapshot-ingestor` avoids a second CronJob, a second failure surface, and cross-job timing skew

It also keeps external API pressure bounded:

- one stock request per underlying, not per contract
- serial throttling is simple and predictable
- `429` handling is visible in logs instead of silently degrading data quality

## Consequences

Expected benefits:

- `underlying_price` can now come from a dedicated stock snapshot source instead of depending on a frequently-null option payload field
- moneyness calculations have a better chance of being populated correctly
- rate-limit behavior is observable in production logs
- no extra service, deployment, or database table is required

Tradeoffs:

- snapshot ingestion takes longer because stock snapshots are intentionally throttled
- if the API key lacks stock entitlement, the runtime will still log authorization failures and continue with fallback behavior
- one stock spot value is shared across all option snapshots for an underlying in that job run, so it is aligned by run cadence, not per-contract tick time

## Alternatives Considered

1. Create a separate stock-spot ingestion service

Rejected because it adds another CronJob, more operational wiring, and a synchronization problem between stock and option snapshots.

2. Keep relying only on `snapshot.underlying_asset.price`

Rejected because real production payloads frequently leave that field empty.

3. Fetch stock spot price per option contract

Rejected because it would multiply API traffic unnecessarily and immediately make free / delayed plan rate limits impractical.

## Implementation

Implemented in:

- [microservices/option_ingestor/api.py](../../../microservices/option_ingestor/api.py)
- [microservices/snapshot_ingestor/ingestor.py](../../../microservices/snapshot_ingestor/ingestor.py)
- [charts/strategy-tester/values.yaml](../../../charts/strategy-tester/values.yaml)

## Follow-Up

1. Confirm the production Polygon key has stocks entitlement; otherwise the new path will log authorization failures and still yield null `underlying_price`.
2. Observe whether `STOCK_SNAPSHOT_FETCH_INTERVAL_SECONDS=12.0` is conservative enough to avoid `429` events under current underlying counts.
3. If stock entitlement is not available, replace the stock snapshot source without changing the `snapshot-ingestor` ownership boundary.
