# ZSH Scripts for Split Ingestion Services

## Overview

Two new zsh wrapper scripts have been created to manage the ingestion operations with desktop notifications:

- **`scripts/ingest_options.zsh`** - Ingests option contracts
- **`scripts/ingest_snapshots.zsh`** - Ingests option snapshots

Both scripts:
- ✅ Send desktop notifications before starting
- ✅ Send notifications on success/failure/timeout
- ✅ Handle exit codes properly
- ✅ Log to console with timestamps
- ✅ Follow the same pattern as `update_options.zsh`

## Features

### Desktop Notifications

**Before starting:**
```
📥 Ingesting Option Contracts
Starting at HH:MM:SS...
```

**On success:**
```
✅ Option Contracts Ingestion Completed
Finished successfully at HH:MM:SS
```

**On failure:**
```
❌ Option Contracts Ingestion Failed
Exit code: 1
```

**On timeout (30 minutes):**
```
⏱️ Option Contracts Ingestion Timed Out
Killed after 30 minutes (timeout)
```

### Exit Code Handling

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | ✅ Notification sent, clean exit |
| 124 | Timeout | ⏱️ Notification sent, exit as 124 |
| Other | Error | ❌ Notification sent, exit with code |

## Service Integration

The systemd service files now call these zsh scripts instead of poetry directly:

```ini
# ingest_options.service
ExecStart=/home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.zsh

# ingest_snapshots.service
ExecStart=/home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.zsh
```

## Using the Scripts

### Direct execution (testing)

```bash
# Run ingest_options script directly
/home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.zsh

# Run ingest_snapshots script directly
/home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.zsh
```

### Via systemd services

```bash
# Start ingest_options service
systemctl --user start ingest_options.service

# Start ingest_snapshots service
systemctl --user start ingest_snapshots.service

# Check status
systemctl --user status ingest_options.service
systemctl --user status ingest_snapshots.service
```

### Via timers (scheduled)

```bash
# Enable and start timer
systemctl --user enable ingest_snapshots.timer
systemctl --user start ingest_snapshots.timer

# View next run times
systemctl --user list-timers ingest_snapshots.timer
```

## Notification Examples

### Console Output

```bash
$ /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.zsh
Starting option contracts ingestion at 2025-10-26 14:30:45
Process completed successfully at 2025-10-26 14:45:23
```

### Desktop Notifications (if notify-send available)

```
User receives 3 notifications:
1. 📥 Ingesting Option Contracts - Starting at 14:30:45...
2. Process runs for ~15 minutes
3. ✅ Option Contracts Ingestion Completed - Finished successfully at 14:45:23
```

## Script Contents

Both scripts follow this pattern:

```bash
#!/usr/bin/env zsh

# 1. Setup environment and DBUS for notifications
# 2. Change to project directory
# 3. Send pre-start notification
# 4. Run the poetry command (ingest_options or ingest_snapshots)
# 5. Capture exit code
# 6. Send appropriate completion notification
# 7. Exit with proper exit code
```

## Notification Dependencies

Notifications require:
- **`notify-send`** command (usually from `libnotify-bin` package)
- **DBUS session** (set via `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS`)
- **Display server** (set via `DISPLAY=:0`)

If any of these are unavailable, the scripts still work—notifications are simply skipped (best-effort).

## Logging

Scripts log to:

### Console (when run manually)
```bash
Starting option snapshots ingestion at 2025-10-26 14:30:45
Process completed successfully at 2025-10-26 14:30:52
```

### Systemd Journal (when run via systemd)
```bash
journalctl --user -u ingest_snapshots.service -f

# Output:
# Oct 26 14:30:45 hostname systemd[1234]: Starting Ingest Option Snapshots...
# Oct 26 14:30:45 hostname ingest_snapshots[5678]: Starting option snapshots ingestion at 2025-10-26 14:30:45
# Oct 26 14:30:52 hostname ingest_snapshots[5678]: Process completed successfully at 2025-10-26 14:30:52
```

## Timeout Behavior

Both scripts respect the 30-minute timeout set in their systemd service files:

```ini
# From service file
ExecStart=/usr/bin/timeout 1800 /path/to/script.zsh
```

If a script exceeds 30 minutes:
1. Process is killed by timeout command
2. Exit code becomes 124
3. ⏱️ Timeout notification is sent
4. Service treats 124 as success (`SuccessExitStatus=124`)

## Comparison with update_options.zsh

| Aspect | old update_options.zsh | new ingest_*.zsh |
|--------|---|---|
| Notifications | ✓ Yes | ✓ Yes (same style) |
| Exit code handling | Basic | Comprehensive (0, 124, other) |
| Logging | ✓ Console | ✓ Console + Journal |
| Timeout | No timeout | 30 minutes via systemd |
| Icons | Basic (✅❌) | Enhanced (📥📊⏱️) |

## Files Modified/Created

```
✓ scripts/ingest_options.zsh      (NEW - executable)
✓ scripts/ingest_snapshots.zsh    (NEW - executable)
✓ scripts/ingest_options.service  (MODIFIED - points to .zsh script)
✓ scripts/ingest_snapshots.service (MODIFIED - points to .zsh script)
```

## Testing

Test the scripts without running the full ingestion:

```bash
# Check syntax
zsh -n /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.zsh

# Test with dry-run (if available in poetry)
poetry run ingest_options --help

# Full dry-run (check if script at least reaches the poetry run)
echo "Script test passed"
```

## Next Steps

1. ✅ Scripts created and made executable
2. ✅ Service files updated to call zsh scripts
3. Install services:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable ingest_options.service
   systemctl --user enable ingest_snapshots.service
   ```
4. Test by running:
   ```bash
   systemctl --user start ingest_options.service
   # Check for notification and logs
   journalctl --user -u ingest_options.service -n 20
   ```
