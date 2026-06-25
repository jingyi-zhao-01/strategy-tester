[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=coverage)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=jingyi-zhao-01_strategy-tester&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=jingyi-zhao-01_strategy-tester)

### To understand US option market out of pure interest :D 

- Volatility Surface
<img width="3740" height="1652" alt="image" src="https://github.com/user-attachments/assets/985694fa-3a9c-4bd8-a164-c48fa098bac2" />


- Call & PUT
<img width="2152" height="1496" alt="image" src="https://github.com/user-attachments/assets/2b5884f8-17dc-4ee8-9230-8eb5d0a2c32d" />
<img width="2058" height="1575" alt="image" src="https://github.com/user-attachments/assets/0eea53ab-b42c-458d-88fc-83403842b1cb" />



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
