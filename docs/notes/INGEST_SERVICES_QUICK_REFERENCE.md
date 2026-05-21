# Quick Reference: Split Ingestion Services with Notifications

## What Was Created

### Scripts (with desktop notifications)
- ✅ `scripts/ingest_options.zsh` - Ingests option contracts
- ✅ `scripts/ingest_snapshots.zsh` - Ingests option snapshots

### Service Files (updated)
- ✅ `scripts/ingest_options.service` - Calls the zsh script
- ✅ `scripts/ingest_snapshots.service` - Calls the zsh script

### Configuration
- ✅ `pyproject.toml` - Updated with poetry script entry points

## Notification Examples

When you run a service, you'll see:

```
📥 Ingesting Option Contracts
Starting at 14:30:45...
[...ingestion runs for 15 minutes...]
✅ Option Contracts Ingestion Completed
Finished successfully at 14:45:23
```

## Install & Use

### One-time setup:
```bash
# Create symlinks
mkdir -p ~/.config/systemd/user
ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.service \
  ~/.config/systemd/user/
ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.service \
  ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload
```

### Run services:
```bash
# Start ingestion
systemctl --user start ingest_options.service
systemctl --user start ingest_snapshots.service

# Check status
systemctl --user status ingest_snapshots.service

# View logs
journalctl --user -u ingest_snapshots.service -f
```

## Features

| Feature | Details |
|---------|---------|
| **Pre-start notification** | Sent immediately when job starts |
| **Success notification** | Sent with completion time |
| **Error notification** | Sent with exit code if failed |
| **Timeout notification** | Sent if job exceeds 30 minutes |
| **Console logging** | Timestamps for each action |
| **Systemd journal** | Full logs available via journalctl |
| **File descriptors** | Limited to 65,536 (prevents "too many open files") |

## Notification Icons

- 📥 Starting ingest_options
- 📊 Starting ingest_snapshots
- ✅ Success
- ❌ Error
- ⏱️ Timeout

## Example Commands

```bash
# Test ingest_options script directly
/home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.zsh

# Run via systemd
systemctl --user start ingest_options.service

# Check if running
systemctl --user is-active ingest_options.service

# View last 20 log lines
journalctl --user -u ingest_options.service -n 20

# Follow logs in real-time
journalctl --user -u ingest_options.service -f

# View logs since 1 hour ago
journalctl --user -u ingest_options.service --since "1 hour ago"
```

## File Locations

```
/home/jingyi/PycharmProjects/strategy-tester/
├── cli/
│   ├── ingest_options.py      (main script)
│   └── ingest_snapshots.py    (main script)
├── scripts/
│   ├── ingest_options.zsh     (wrapper with notifications)
│   ├── ingest_snapshots.zsh   (wrapper with notifications)
│   ├── ingest_options.service
│   └── ingest_snapshots.service
└── pyproject.toml             (poetry config)
```

## Environment

Both scripts use:
- **Database**: Loaded from `.env` file (DATABASE_URL)
- **API keys**: Loaded from `.env` file (POLYGON_API_KEY, etc.)
- **Observability**: Loaded from `.env` file (OTEL settings)
- **Timeout**: 30 minutes (configurable in service file)
- **File descriptors**: 65,536 limit

## Dependencies

For notifications to work, you need:
- `notify-send` command (from `libnotify-bin` package)
- DBUS session (automatic on desktop systems)
- X11 display (automatic on desktop systems)

Scripts work without notifications if these aren't available (graceful degradation).

## Troubleshooting

### Service not found
```bash
systemctl --user daemon-reload
systemctl --user list-unit-files | grep ingest
```

### Check if running
```bash
systemctl --user is-active ingest_snapshots.service
```

### View recent logs
```bash
journalctl --user -u ingest_snapshots.service -n 50
```

### See what systemd does
```bash
systemctl --user show ingest_snapshots.service
```

## Comparison: Old vs New

| Aspect | Old (`update_options.service`) | New (Split Services) |
|--------|---|---|
| Services | 1 (both operations) | 2 (separate) |
| Scheduling | Together | Independent |
| Notifications | Basic | ✓ Enhanced |
| Exit codes | Not handled | ✓ Comprehensive |
| Logging | Basic | ✓ Rich |
| Timeouts | Manual | ✓ 30 min in systemd |
| File descriptors | ✓ 65,536 | ✓ 65,536 |

## Next: Scheduling with Timers

Create `~/.config/systemd/user/ingest_snapshots.timer`:

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

Then:
```bash
systemctl --user daemon-reload
systemctl --user enable ingest_snapshots.timer
systemctl --user start ingest_snapshots.timer
systemctl --user list-timers ingest_snapshots.timer
```

## Documentation

For detailed information, see:
- `ZSH_SCRIPTS_SETUP.md` - Detailed zsh script documentation
- `SPLIT_INGESTION_SERVICES.md` - Services overview
- `SETUP_SPLIT_SERVICES.md` - Setup instructions
- `DATABASE_CONCURRENCY_CONFIG.md` - Database configuration
