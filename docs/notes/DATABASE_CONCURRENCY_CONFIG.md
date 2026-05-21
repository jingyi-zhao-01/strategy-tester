# Database Concurrency Configuration Guide

## Overview

This project now enforces a maximum database concurrency limit at both the Prisma connection pool level and the application level to prevent overwhelming the database and exhausting system resources.

## Configuration Layers

### 1. DATABASE_URL Connection String (Prisma Level)
**File**: `.env` (or environment variable)

Add the `connection_limit` parameter to your PostgreSQL connection string:

```bash
DATABASE_URL="postgresql://user:password@host:port/dbname?connection_limit=100"
```

**What it does**: Limits the size of Prisma's internal asyncpg connection pool. This is the hard limit at the Prisma library level.

### 2. Python Application Level (Semaphore)
**File**: `options/decorator.py`

The `DATA_BASE_CONCURRENCY_LIMIT` constant controls the application-level semaphore:

```python
# Maximum number of concurrent database connections Prisma can open
# This should match the connection_limit in the DATABASE_URL string
DATA_BASE_CONCURRENCY_LIMIT = 100
```

**What it does**: Creates an asyncio Semaphore that limits concurrent database operations. If too many async tasks try to run database queries simultaneously, they'll wait in a queue until a slot becomes available.

## How They Work Together

1. **URL Connection Limit** (`connection_limit=100`): Prevents Prisma from creating more than 100 physical database connections
2. **Semaphore** (`DATA_BASE_CONCURRENCY_LIMIT=100`): Prevents more than 100 async operations from attempting database queries at the same time
3. **Monitoring**: Connection pool statistics are logged before each database operation via `_log_connection_pool_stats()`

## Configuration Steps

### Step 1: Update DATABASE_URL
Edit your `.env` file or systemd service environment:

```bash
# Before
DATABASE_URL="postgresql://user:password@neon.tech/dbname"

# After (add connection_limit parameter)
DATABASE_URL="postgresql://user:password@neon.tech/dbname?connection_limit=100"
```

### Step 2: Adjust DATA_BASE_CONCURRENCY_LIMIT (if needed)
Edit `options/decorator.py`:

```python
# Change this value based on your workload
# Current value: 100
# Should NOT exceed the connection_limit in DATABASE_URL
DATA_BASE_CONCURRENCY_LIMIT = 100
```

### Step 3: Monitor Connection Pool Stats
The decorator logs connection pool statistics before each database operation:

```
Database pool stats - Active: 15, Min: 10, Max: 100
```

- **Active**: Current number of connections in use
- **Min**: Minimum pool size (typically 10)
- **Max**: Maximum pool size (matches your `connection_limit`)

## Recommended Values

| Scenario | Connection Limit | Notes |
|----------|------------------|-------|
| Low concurrency (< 50 concurrent async tasks) | 20-30 | Conservative setting |
| Medium concurrency (50-200 tasks) | 50-100 | Balanced approach |
| High concurrency (> 200 tasks) | 150-200 | Requires database to support this |
| Neon PostgreSQL limit | ≤ 1800 | Hard limit imposed by Neon |

## Troubleshooting

### "Connection pool exhausted" errors
- Increase `connection_limit` in DATABASE_URL
- Increase `DATA_BASE_CONCURRENCY_LIMIT` accordingly
- Verify both values match

### "Too many connections" from database
- The database is rejecting new connections
- Decrease both limits
- Check if other applications are also using the database

### "Too many open files" errors
- Indicates file descriptor exhaustion at OS level
- Increase systemd `LimitNOFILE` setting
- Already configured: `LimitNOFILE=65536` in `update_options.service`

## Example Configuration

For the options ingestion workload with ~700 concurrent API requests but limited DB connections:

```bash
# .env or systemd environment
DATABASE_URL="postgresql://user:password@host/dbname?connection_limit=100"

# options/decorator.py
CONCURRENCY_LIMIT = 700              # API request concurrency (httpx semaphore)
DATA_BASE_CONCURRENCY_LIMIT = 100    # DB connection concurrency (asyncio semaphore)
```

This way:
- The application can handle 700 concurrent API calls to Polygon
- Only 100 of them can actively query the database at a time
- The rest wait in a queue for a database slot to become available
- Database resource usage stays predictable and controlled

## For Development vs Production

### Development (.env file)
```bash
DATABASE_URL="postgresql://localhost:5432/options_dev?connection_limit=50"
```

### Production (systemd service environment)
```bash
DATABASE_URL="postgresql://production-host:5432/options?connection_limit=100"
```

## Monitoring & Alerts

Watch the application logs for these patterns:

- **Healthy**: `Active: 10-50, Min: 10, Max: 100` - Normal operation
- **High load**: `Active: 80-100, Min: 10, Max: 100` - Approaching limit
- **Bottleneck**: `Active: 100, Min: 10, Max: 100` - Pool fully utilized, requests queuing

If consistently at max, increase the limit or optimize queries.

## See Also

- Prisma Connection Pool: https://www.prisma.io/docs/orm/reference/connection-management
- PostgreSQL Maximum Connections: Documentation for your Postgres provider
- Systemd Service Configuration: `scripts/update_options.service`
