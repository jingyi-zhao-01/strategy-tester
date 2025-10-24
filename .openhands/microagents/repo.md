Project overview

Strategy Tester is a Python 3.12 project for ingesting options contract metadata and daily snapshots from Polygon.io, storing them in Postgres via Prisma ORM, and providing simple CLI/Lambda entrypoints. It includes observability via OpenTelemetry and a small logging helper. Core domain modules live under options/, and tests validate utilities, retrieval, ingestion, and decorators.

File structure (high level)
- cli/: entrypoints for local run (run.py) and AWS Lambda (lambda_handler.py), with predefined TARGETS in targets.py
- lib/: logging utilities (lib/log/log.py) and log file output
- options/: domain logic
  - api/options.py: Polygon fetcher, async snapshot fetch, price/year-range filter, batch snapshot retrieval
  - ingestor.py: orchestrates contract discovery and snapshot upserts, uses Prisma models Options and OptionSnapshot
  - retriever.py: streams active contracts from DB in batches and supports full retrieval
  - util.py: time conversion, symbol parsing, client helpers and formatting
  - decorator.py: concurrency limits, DB connection wrapper, and OpenTelemetry span helpers
  - models/: dataclasses and type re-exports (OptionsContract, OptionContractSnapshot, OptionSymbol)
  - tests/: pytest tests for util, retriever, ingestor, decorator
- prisma/: Prisma schema.prisma and helper script; targets PostgreSQL via DATABASE_URL
- qlib/: experiment scaffolding/config
- scripts/: misc scripts (e.g., run.zsh)
- pyproject.toml, pytest.ini, conftest.py: project config and test helpers

How to set up and run
- Requirements: Python 3.12, Poetry, PostgreSQL. Environment variables in .env:
  - POLYGON_API_KEY=... (required for real API calls)
  - DATABASE_URL=postgresql://user:pass@host:port/dbname
- Install deps: `poetry install` (dev: pytest, ruff, pytest-asyncio are included)
- Generate Prisma client (if schema changed): `poetry run prisma generate` and ensure DB reachable
- Run tests: `poetry run pytest -q` (conftest provides stubs to avoid hitting real Prisma/models; tests don’t require live API by default)
- Lint: `poetry run ruff check .` and format via black rules (line-length=100)

Common workflows
- Ingest options (contracts): call ingest_options_handler from cli/lambda_handler.py or run via opentelemetry-instrumented `cli/run.py` which invokes lambda_handler
- Ingest snapshots: invoke ingest_option_snapshots_handler (uses OptionRetriever.stream_retrieve_active and fetch_snapshots_batch)
- Local dev without DB/API: unit tests leverage stubs and monkeypatch; ensure POLYGON_API_KEY is set for any real fetches

Notes for new contributors
- Prefer importing prisma.models via import_module in production code to keep tests decoupled
- Batching and concurrency limits are defined in options/decorator.py (CONCURRENCY_LIMIT, DATA_BASE_CONCURRENCY_LIMIT, OPTION_BATCH_RETRIEVAL_SIZE)
- The repository includes OpenTelemetry setup; exporting to OTLP can be configured through env vars (e.g., OTEL_EXPORTER_OTLP_ENDPOINT)
- Be mindful of schema keys: OptionSnapshot has composite PK (ticker, last_updated) and references Options by ticker
