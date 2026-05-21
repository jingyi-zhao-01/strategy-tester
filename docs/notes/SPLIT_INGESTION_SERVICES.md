# Split Ingestion Services

This document explains the two separate ingestion services.

## Services Overview

### 1. **Ingest Options** (`ingest_options`)
- **Purpose**: Fetches option contract data from Polygon API and stores it in the database
- **What it does**:
  - Retrieves all active option contracts for configured underlying assets
  - Filters by configured parameters (price ranges, expirations, etc.)
  - Inserts/updates contracts in the database
- **Duration**: ~5-15 minutes depending on the number of contracts
- **Frequency**: Run less frequently (e.g., daily or weekly)
- **Database operations**: Mostly writes (upserts)

**Service file**: `scripts/ingest_options.service`
**Script**: `cli/ingest_options.py`
**Command**: `poetry run ingest_options`

### 2. **Ingest Snapshots** (`ingest_snapshots`)
- **Purpose**: Fetches current market data (prices, Greeks, implied volatility) for active contracts
- **What it does**:
  - Iterates through all active (non-expired) option contracts
  - Fetches current snapshots from Polygon API
  - Stores snapshots in the database with timestamp
- **Duration**: Varies by number of contracts and API rate limits
- **Frequency**: Run frequently (e.g., every 5-15 minutes during market hours)
- **Database operations**: Mostly reads (retrieving contracts) and writes (snapshots)

**Service file**: `scripts/ingest_snapshots.service`
**Script**: `cli/ingest_snapshots.py`
**Command**: `poetry run ingest_snapshots`

## Systemd Setup

### Install Services

```bash
# Create symlinks for user services
mkdir -p ~/.config/systemd/user
ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.service ~/.config/systemd/user/
ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.service ~/.config/systemd/user/

# Reload systemd to recognize the new services
systemctl --user daemon-reload

# Enable services to start at user login
systemctl --user enable ingest_options.service
systemctl --user enable ingest_snapshots.service
```

### Run Services Manually

```bash
# Run ingest_options service
systemctl --user start ingest_options.service

# Run ingest_snapshots service
systemctl --user start ingest_snapshots.service

# Check status
systemctl --user status ingest_options.service
systemctl --user status ingest_snapshots.service

# View logs
journalctl --user -u ingest_options.service -f
journalctl --user -u ingest_snapshots.service -f
```

## Scheduling with Timers

Create systemd timer files to run on a schedule:

### `ingest_options.timer`
Run less frequently (e.g., daily at 2 AM):

```ini
[Unit]
Description=Run ingest_options daily

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### `ingest_snapshots.timer`
Run frequently during market hours (e.g., every 10 minutes, 9:30 AM - 4 PM):

```ini
[Unit]
Description=Run ingest_snapshots every 10 minutes during market hours

[Timer]
OnCalendar=Mon-Fri *-*-* 09:30-16:00
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
```

## Database Connection Management

Both services use the same connection pooling configuration:

- **Connection pool limit**: `DATA_BASE_CONCURRENCY_LIMIT = 300` (configured in `options/decorator.py`)
- **Database URL connection limit**: Add `?connection_limit=300` to your `DATABASE_URL`
- **File descriptor limit**: `LimitNOFILE=65536` (prevents "too many open files" errors)

See `DATABASE_CONCURRENCY_CONFIG.md` for detailed configuration.

## Environment Variables

Both services load from `/home/jingyi/PycharmProjects/strategy-tester/.env`:

```bash
DATABASE_URL=postgresql://...?connection_limit=300
POLYGON_API_KEY=...
OTEL_EXPORTER_OTLP_ENDPOINT=...
```

## Logging

Logs are sent to journalctl:

```bash
# Follow ingest_options logs
journalctl --user -u ingest_options.service -f

# Follow ingest_snapshots logs
journalctl --user -u ingest_snapshots.service -f

# View last 50 lines
journalctl --user -u ingest_options.service -n 50
journalctl --user -u ingest_snapshots.service -n 50
```

Logs include:
- Connection pool statistics: `Database pool stats - Active: X, Min: Y, Max: Z`
- Ingestion progress: `Retrieved batch at offset X...`
- Errors and exceptions with full traceback

## Timeout Behavior

Both services have a 30-minute timeout (`timeout 1800`):

- If the service completes successfully, it exits with code 0
- If the service takes > 30 minutes, it's killed and exits with code 124
- Exit code 124 is marked as `SuccessExitStatus=124` to avoid false alerts

## Resource Limits

### File Descriptors
- `LimitNOFILE=65536`: Allows up to 65,536 open file descriptors per service
- This is necessary because each database connection and socket uses a file descriptor
- Prevents "too many open files" errors during high concurrency

### Memory
- No explicit memory limit set
- Monitor actual usage with: `ps aux | grep ingest`

### CPU
- No explicit CPU limit set
- Services run with default CPU scheduling

## Monitoring

### Check if services are enabled
```bash
systemctl --user list-unit-files | grep ingest
```

### Monitor active connections during ingestion
```bash
# Terminal 1: Start the service
systemctl --user start ingest_snapshots.service

# Terminal 2: Watch logs in real-time
journalctl --user -u ingest_snapshots.service -f

# Look for lines like:
# Database pool stats - Active: 45, Min: 10, Max: 300
```

### Performance metrics
Check logs for:
- Total contracts processed: `Total contracts processed: X`
- Batches retrieved: `Retrieved batch at offset Y...`
- Time to complete: Check timestamps in logs

## Troubleshooting

### Service fails immediately
```bash
journalctl --user -u ingest_snapshots.service -n 50
# Check for environment variable issues, import errors, etc.
```

### Service times out
- Increase timeout in service file: `ExecStart=/usr/bin/timeout 3600 ...` (for 1 hour)
- Check if database is slow
- Check connection pool stats in logs

### "Too many open files" error
- Already fixed by `LimitNOFILE=65536` in service file
- If still happening, increase further: `LimitNOFILE=131072`

### "Event loop is closed" error
- Ensure both `@bounded_db_connection` and `@bounded_db_connection_asyncgen` decorators are used
- Already implemented in current code

## Migration from Old Setup

The old `update_options.service` script ran both operations sequentially.

New setup:
- `ingest_options.service` - Fetch contracts (run less frequently)
- `ingest_snapshots.service` - Fetch snapshots (run frequently)

You can now:
- Run snapshots every 10 minutes while only running full contract updates daily
- Run them independently without waiting for the other
- Schedule them at different times
- Debug them separately

## Scripts Reference

- `cli/ingest_options.py` - Standalone script for option contracts ingestion
- `cli/ingest_snapshots.py` - Standalone script for option snapshots ingestion
- `cli/lambda_handler.py` - Lambda handler functions (keeping for backward compatibility)

## Next Steps

1. Create the service files: `ingest_options.service` and `ingest_snapshots.service` ✓
2. Add scripts to `pyproject.toml` under `[tool.poetry.scripts]` ✓
3. Install the services: `systemctl --user enable ingest_options.service ingest_snapshots.service`
4. Create timer files for scheduling (optional, see examples above)
5. Monitor the logs to ensure correct behavior
