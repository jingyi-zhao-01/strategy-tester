# Quick Setup: Split Ingestion Services

## Summary of Changes

You now have **two separate, independent ingestion services**:

### New Scripts
1. **`cli/ingest_options.py`** - Ingests option contracts from Polygon API
   - Command: `poetry run ingest_options`
   - Systemd service: `ingest_options.service`

2. **`cli/ingest_snapshots.py`** - Ingests option snapshots (market data) for active contracts
   - Command: `poetry run ingest_snapshots`
   - Systemd service: `ingest_snapshots.service`

## One-Time Setup

### 1. Install Services

```bash
# Create user systemd directory
mkdir -p ~/.config/systemd/user

# Create symlinks for both services
ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.service \
  ~/.config/systemd/user/

ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.service \
  ~/.config/systemd/user/

# Reload systemd to recognize new services
systemctl --user daemon-reload

# Verify services are recognized
systemctl --user list-unit-files | grep ingest
```

### 2. Enable Services (Optional)

```bash
# Enable to start on user login
systemctl --user enable ingest_options.service
systemctl --user enable ingest_snapshots.service
```

## Usage

### Run Manually

```bash
# Ingest option contracts
systemctl --user start ingest_options.service

# Ingest option snapshots
systemctl --user start ingest_snapshots.service
```

### Check Status

```bash
systemctl --user status ingest_options.service
systemctl --user status ingest_snapshots.service
```

### View Logs

```bash
# Follow logs in real-time
journalctl --user -u ingest_options.service -f
journalctl --user -u ingest_snapshots.service -f

# Last 50 lines
journalctl --user -u ingest_options.service -n 50
journalctl --user -u ingest_snapshots.service -n 50

# Since specific time
journalctl --user -u ingest_snapshots.service --since "1 hour ago"
```

## Scheduling with Timers (Optional)

### Create `~/.config/systemd/user/ingest_options.timer`

```ini
[Unit]
Description=Run ingest_options daily at 2 AM

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Create `~/.config/systemd/user/ingest_snapshots.timer`

```ini
[Unit]
Description=Run ingest_snapshots every 10 minutes during market hours

[Timer]
# Mon-Fri, 9:30 AM to 4:00 PM
OnCalendar=Mon-Fri *-*-* 09:30-16:00
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable Timers

```bash
systemctl --user daemon-reload
systemctl --user enable ingest_options.timer
systemctl --user enable ingest_snapshots.timer
systemctl --user start ingest_options.timer
systemctl --user start ingest_snapshots.timer

# View timer status
systemctl --user status ingest_options.timer
systemctl --user status ingest_snapshots.timer

# List all timers
systemctl --user list-timers --all
```

## Configuration

Both services use:
- **Connection pool**: `DATA_BASE_CONCURRENCY_LIMIT = 300` (in `options/decorator.py`)
- **Database URL**: Add `?connection_limit=300` parameter
- **File descriptors**: `LimitNOFILE=65536` (in service files)
- **Timeout**: 30 minutes (can be changed in service files)

See `DATABASE_CONCURRENCY_CONFIG.md` for detailed database configuration.

## Monitoring Connection Pool

Both services log connection pool statistics:

```bash
journalctl --user -u ingest_snapshots.service -f | grep "pool stats"

# Output:
# Database pool stats - Active: 45, Min: 10, Max: 300
```

- **Active**: Current connections in use
- **Min**: Minimum pool size (10)
- **Max**: Maximum pool size (300)

## Troubleshooting

### Service not found
```bash
# Check if systemd can see the service
systemctl --user show-environment
systemctl --user daemon-reload
systemctl --user list-unit-files | grep ingest
```

### Command not found
```bash
# Ensure Poetry scripts are installed
poetry install
poetry run ingest_options --help  # Test the script

# Verify Poetry executable location
which poetry
ls -la ~/.local/bin/poetry
```

### Database connection errors
```bash
# Check environment variables
systemctl --user show-environment | grep DATABASE_URL

# Verify .env file
cat /home/jingyi/PycharmProjects/strategy-tester/.env | grep DATABASE_URL
```

### Too many open files
```bash
# Already set to 65536 in service files
# If still happening, increase LimitNOFILE in service file:
# LimitNOFILE=131072
```

## Old Service

The old `update_options.service` is still available and runs both operations sequentially. You can keep it or remove it:

```bash
# To remove old service
systemctl --user stop update_options.service
systemctl --user disable update_options.service
rm ~/.config/systemd/user/update_options.service
systemctl --user daemon-reload
```

## See Also

- `SPLIT_INGESTION_SERVICES.md` - Detailed documentation
- `DATABASE_CONCURRENCY_CONFIG.md` - Database configuration
- `ASYNC_GENERATOR_DECORATOR_FIX.md` - Technical details on async handling
