# ADR 0003: Share an Async HTTP Client Across Snapshot Fetch Batches

- Status: Accepted
- Date: 2026-06-09
- Implemented: 2026-06-09
- Owners: strategy-tester snapshot ingestion runtime

## Context

`snapshot-ingestor` fetches option snapshots from Massive / Polygon over HTTPS.

The previous implementation created a new `httpx.AsyncClient` for every individual snapshot request. Under high snapshot fan-out, that had several undesirable effects:

- no effective connection reuse across requests in the same batch
- repeated TCP / TLS connection setup
- higher connect-stage latency under concurrency
- more `ConnectTimeout` risk during bursty fetch windows

This was especially wasteful because snapshot ingestion already groups contracts into batches and naturally has a batch-level execution boundary where an HTTP client can be safely shared.

## Decision

For snapshot fetching, the runtime will use one shared `httpx.AsyncClient` per fetch batch instead of one client per request.

The new design:

1. creates a single `AsyncClient` for the current snapshot batch
2. reuses that client for all snapshot fetches in the batch
3. closes the client after the batch finishes
4. configures explicit connection-pool limits and connect/read timeouts via environment variables

New runtime knobs:

- `SNAPSHOT_FETCH_CONNECT_TIMEOUT`
- `SNAPSHOT_FETCH_READ_TIMEOUT`
- `SNAPSHOT_HTTP_MAX_CONNECTIONS`
- `SNAPSHOT_HTTP_MAX_KEEPALIVE_CONNECTIONS`

## Consequences

Expected benefits:

- better HTTP connection reuse
- less connection setup overhead
- lower connect-stage timeout probability
- more predictable behavior under bounded snapshot concurrency

Tradeoffs:

- one misconfigured shared client now affects the whole batch instead of just one request
- tuning HTTP pool limits becomes part of runtime operations
- this improves transport efficiency, but does not by itself guarantee downstream data completeness

## Alternatives Considered

1. Keep one `AsyncClient` per request

Rejected because it defeats connection pooling and amplifies connect-stage overhead.

2. Migrate immediately to the official Massive Python client

Deferred. The currently documented stable Python client path is still the synchronous `RESTClient`, and we do not yet have enough evidence that an official async REST path is mature enough to replace the current ingestion code directly.

3. Increase timeout only

Rejected as the first move because it treats the symptom while keeping the wasteful connection pattern unchanged.

## Implementation

Implemented in:

- [microservices/option_ingestor/api.py](../../../microservices/option_ingestor/api.py)
- [charts/strategy-tester/values.yaml](../../../charts/strategy-tester/values.yaml)

## Follow-Up

1. Observe whether `ConnectTimeout` frequency drops after client reuse.
2. If snapshot fetches remain bursty, consider adding fetch chunking in addition to shared-client reuse.
3. Revisit official Massive async client support later if it becomes stable and documented.
