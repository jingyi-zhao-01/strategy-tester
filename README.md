[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=coverage)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)


- Volatility Surface
<iframe src="https://jingyizhao01.grafana.net/d-solo/jirsvqz/option-overview?orgId=1&from=1775026800000&to=1782889199999&timezone=browser&var-underlying_asset=CRWV&var-snapshot=1779517800757&var-oi_min=1000&var-oi_max=100000&panelId=panel-22" width="450" height="200" frameborder="0"></iframe>

## Ingestion Microservices

The ingestion workflow is split into two isolated services:

- `option-ingestor` for contract metadata ingestion
- `snapshot-ingestor` for market snapshot ingestion

Both services are configured only through environment variables.

### Required Variables

- `POLYGON_API_KEY`
- `DATABASE_URL`

### Option Targets Injection

Use one of:

- `OPTION_INGEST_TARGETS` as JSON array
- `OPTION_INGEST_SYMBOLS` as comma-separated symbols

Example:

```bash
export OPTION_INGEST_TARGETS='[
 {"symbol":"NVDA","price_range":[100,250],"year_range":[2026,2027]},
 {"symbol":"AAPL","year_range":[2026,2027]}
]'
```

## Helm Chart Quick Reference

Deploy `option-ingestor` and `snapshot-ingestor` with Helm:

```sh
helm install my-ingestor <chart> \
 --set databaseUrl="<db-url>" \
 --set polygonKey="<polygon-key>"
```

Only two required envs:

- `DATABASE_URL`
- `POLYGON_API_KEY`

Kubernetes Secret is recommended for sensitive values.

---

### Optional Runtime Variables

- `DOTENV_PATH`
- `OPTION_INGEST_SERVICE_NAME`
- `SNAPSHOT_INGEST_SERVICE_NAME`
- `OPTION_INGEST_ENABLE_OTEL`
- `SNAPSHOT_INGEST_ENABLE_OTEL`
- `OTEL_EXPORTER_OTLP_PROTOCOL`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_EXPORTER_OTLP_HEADERS`
- `INGEST_CONCURRENCY_LIMIT`
- `INGEST_DB_CONCURRENCY_LIMIT`
- `INGEST_OPTION_BATCH_SIZE`
- `SNAPSHOT_FETCH_CONCURRENCY`
- `INGEST_TIME_ZONE`

When deployed via Helm, these runtime variables are passed through each ingestor's
`env` block in `charts/strategy-tester/values.yaml`.
