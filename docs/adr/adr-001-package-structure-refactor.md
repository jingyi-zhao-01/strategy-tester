# ADR: Package Structure Refactor - Separating Ingestor from Trade Automation

## Status

**Proposed** | ⬜ Deprecated | ⬜ Superseded by ADR-002

---

## Context

The current project structure has all domain logic bundled under the `options/` directory, which mixes concerns:

- **Ingestion**: Option contracts, snapshots, API fetching
- **Retrieval**: Database queries
- **Utilities**: Time conversion, symbol parsing
- **Decorators**: Concurrency, DB connections, tracing

Additionally:
- The `trade/` package exists but is empty (just one comment)
- Prisma schema is global but lacks organization for multi-environment support
- No clear separation between data ingestion and trade automation logic

We need a structure that:
1. Clearly separates ingestion concerns from trade automation
2. Organizes Prisma for multi-environment database URLs
3. Provides clear boundaries for future development

---

## Decision

We will refactor into the following structure:

```
strategy-tester/
├── cli/                         # Entry points (unchanged)
│   ├── ingest_options.py
│   ├── ingest_snapshots.py
│   ├── run.py
│   ├── lambda_handler.py
│   └── targets.py
│
├── lib/                         # Shared utilities (unchanged)
│   └── observability/
│       ├── __init__.py
│       ├── log.py
│       └── tests/
│
├── prisma/                      # Global Prisma (single schema)
│   ├── schema.prisma           # Single source of truth
│   └── script.py
│
├── ingestor/                    # NEW TOP-LEVEL PACKAGE
│   ├── __init__.py
│   ├── option_ingestor.py      # OptionIngestor class
│   ├── snapshots_ingestor.py   # OptionSnapshotsIngestor class
│   ├── retriever.py            # OptionRetriever (moved)
│   │
│   ├── api/                    # Polygon API clients
│   │   ├── __init__.py
│   │   └── options.py          # Fetcher, snapshot fetching
│   │
│   ├── models/                 # Shared models for ingestion
│   │   ├── __init__.py
│   │   └── option_models.py    # OptionSymbol, OptionIngestParams
│   │
│   ├── decorator.py            # Bounded semaphores, tracing (moved)
│   ├── util.py                 # Time conversion, parsing (moved)
│   ├── errors.py               # Error types (moved)
│   │
│   └── tests/                  # Ingestor tests
│       ├── test_ingestor.py
│       ├── test_retriever.py
│       ├── test_decorator.py
│       └── test_util.py
│
├── trade/                       # EXPANDED - Trade automation
│   ├── __init__.py
│   │
│   ├── strategies/             # Trading strategy definitions
│   │   ├── __init__.py
│   │   ├── base.py            # BaseStrategy abstract class
│   │   └── examples/          # Example implementations
│   │       ├── __init__.py
│   │       ├── iron_condor.py
│   │       └── straddle.py
│   │
│   ├── execution/              # Order execution
│   │   ├── __init__.py
│   │   ├── broker.py          # Broker interface (TradeStation)
│   │   ├── order.py           # Order types & management
│   │   └── executor.py        # Order execution logic
│   │
│   ├── positions/              # Position management
│   │   ├── __init__.py
│   │   ├── portfolio.py       # Portfolio tracking
│   │   └── position.py        # Individual position state
│   │
│   ├── signals/               # Trading signal generation
│   │   ├── __init__.py
│   │   └── generator.py       # Signal generation logic
│   │
│   ├── automation/            # Automation workflows
│   │   ├── __init__.py
│   │   ├── scheduler.py      # Trade scheduling
│   │   └── executor.py        # Automated execution
│   │
│   └── tests/
│
├── .env                        # Default env (development)
├── .env.development
├── .env.staging
└── .env.production
```

---

## Migration Details

### File Movement Mapping

| Current Location | New Location |
|-----------------|--------------|
| `options/ingestor/option_contract_ingestor.py` | `ingestor/option_ingestor.py` |
| `options/ingestor/snapshots_ingestor.py` | `ingestor/snapshots_ingestor.py` |
| `options/retriever.py` | `ingestor/retriever.py` |
| `options/api/options.py` | `ingestor/api/options.py` |
| `options/models/` | `ingestor/models/` |
| `options/decorator.py` | `ingestor/decorator.py` |
| `options/util.py` | `ingestor/util.py` |
| `options/errors.py` | `ingestor/errors.py` |
| `options/tests/` | `ingestor/tests/` |
| `trade/api.py` | `trade/execution/broker.py` (rename) |

### Prisma Multi-Environment Configuration

```toml
# pyproject.toml additions

[tool.hatch.dotenv]
path = ".env"

[tool.hatch.envs.default]
dotenv = [".env.development"]

[tool.hatch.envs.staging]
dotenv = [".env.staging"]

[tool.hatch.envs.production]
dotenv = [".env.production"]
```

Environment files:
- `.env.development` - Local development database
- `.env.staging` - Staging database  
- `.env.production` - Production database

### Update pyproject.toml Build Targets

```toml
[tool.hatch.build.targets.wheel]
packages = ["ingestor", "trade", "lib"]
```

### Update Import Paths

After migration, update imports in:
- `cli/ingest_options.py` - Change `from options.ingestor import ...` to `from ingestor import ...`
- `cli/ingest_snapshots.py` - Same change
- All test files

---

## Consequences

### Positive

1. **Clear separation of concerns**: Ingestion vs. trade automation are distinct packages
2. **Scalability**: Trade package can grow independently with strategies, execution, positions
3. **Multi-environment support**: Easy to switch between dev/staging/prod databases
4. **Testability**: Clear boundaries make mocking easier
5. **Discoverability**: New developers can find what they need quickly

### Negative

1. **Migration effort**: Requires moving files and updating all imports
2. **Breaking changes**: CLI entry points will need import path updates
3. **Prisma remains global**: Single schema, but with better env organization

### Neutral

- Trade package starts empty - will need implementation in future PRs
- Prisma client still generated once (no per-package schema)

---

## Alternatives Considered

### 1. Per-Package Prisma Schemas
Rejected: Prisma doesn't support multiple schemas well; cross-domain queries become complex.

### 2. Keep options/ as-is, expand trade/
Rejected: `options/` name implies options trading only, not ingestion; better to have clear `ingestor/` name.

### 3. No trade/ package, keep everything in options/
Rejected: Trade automation has different concerns (strategies, execution) than data ingestion.

---

## References

- [Prisma Environment Variables Documentation](https://www.prisma.io/docs/orm/more/development-environment/environment-variables)
- [Prisma Multi-env .env files](https://www.prisma.io/docs/orm/more/development-environment/environment-variables#using-multiple-env-files)
- [hatch-dotenv plugin](https://github.com/babashka/hatch-dotenv)

---

## Notes

- ADR created: 2025-01
- This is a structural refactor only - no logic changes
- Trade automation implementation is out of scope for this ADR
- Prisma schema remains in `prisma/schema.prisma` with comments to delineate domains
