# Complete Setup Guide: Automated Ingestion with Systemd Timers

All components are now ready for fully automated ingestion with notifications!

## Complete File Structure

```
/home/jingyi/PycharmProjects/strategy-tester/
├── cli/
│   ├── ingest_options.py           # Main ingestion script
│   └── ingest_snapshots.py         # Main ingestion script
├── scripts/
│   ├── ingest_options.zsh          # Wrapper with notifications
│   ├── ingest_options.service      # Systemd service
│   ├── ingest_options.timer        # Systemd timer (daily 2 AM)
│   ├── ingest_snapshots.zsh        # Wrapper with notifications
│   ├── ingest_snapshots.service    # Systemd service
│   └── ingest_snapshots.timer      # Systemd timer (every 10 min)
└── pyproject.toml                   # Poetry config with scripts
```

## One-Time Installation

### Step 1: Create Symlinks

```bash
# Create systemd user directory
mkdir -p ~/.config/systemd/user

# Create symlinks for services
ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.service \
  ~/.config/systemd/user/

ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.service \
  ~/.config/systemd/user/

# Create symlinks for timers
ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.timer \
  ~/.config/systemd/user/

ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.timer \
  ~/.config/systemd/user/

# Verify symlinks
ls -l ~/.config/systemd/user/ingest_*
```

### Step 2: Reload Systemd

```bash
systemctl --user daemon-reload
```

### Step 3: Enable Timers

```bash
# Enable timers to start on user login
systemctl --user enable ingest_options.timer
systemctl --user enable ingest_snapshots.timer

# Start timers immediately
systemctl --user start ingest_options.timer
systemctl --user start ingest_snapshots.timer
```

### Step 4: Verify Installation

```bash
# Check timer status
systemctl --user list-timers ingest_*.timer

# Output should show:
# NEXT                        LEFT        LAST PASSED UNIT
# Mon 2025-10-27 02:00:00 EST 5h 26min   ...  ingest_options.timer
# Mon 2025-10-27 10:40:00 EST 2min 14s   ...  ingest_snapshots.timer
```

## How It Works

### Complete Flow

```
1. Timer fires at scheduled time
   ↓
2. Timer starts ingest_snapshots.service
   ↓
3. Service calls: /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.zsh
   ↓
4. ZSH script sends desktop notification
   ↓
5. ZSH script runs: poetry run ingest_snapshots
   ↓
6. Python script ingests data (with pool logging)
   ↓
7. On completion/error/timeout:
   - ZSH script sends completion notification
   - Journal logs the result
   ↓
8. Timer waits for next scheduled time
```

### Timing

**ingest_options.timer**:
- Fires: Every day at 2:00 AM
- Service runs for: ~5-15 minutes (fetches ~1000 contracts)
- Notifications: Start + Success/Error/Timeout

**ingest_snapshots.timer**:
- Fires: Every 10 minutes, Mon-Fri, 9:30 AM - 4:00 PM
- Service runs for: ~30 seconds - 2 minutes per run
- Notifications: Start + Success/Error/Timeout

## Daily Operation

### View Scheduled Tasks

```bash
# Show all active timers and next run times
systemctl --user list-timers

# Show all timers including inactive
systemctl --user list-timers --all
```

### Monitor Execution

```bash
# Real-time logs for service (executed by timer)
journalctl --user -u ingest_snapshots.service -f

# Real-time logs for timer itself
journalctl --user -u ingest_snapshots.timer -f

# Both timer and service logs together
journalctl --user --unit=ingest_snapshots.timer --unit=ingest_snapshots.service -f
```

### Manual Triggers (Anytime)

```bash
# Manually run ingest_snapshots (doesn't affect timer schedule)
systemctl --user start ingest_snapshots.service

# Manually run ingest_options
systemctl --user start ingest_options.service

# Check if it's running
systemctl --user is-active ingest_snapshots.service
```

## Notifications

You'll receive desktop notifications at:

1. **Start**: `📥 Ingesting Option Snapshots - Starting at 10:30:45...`
2. **Success**: `✅ Ingesting Option Snapshots Completed - Finished at 10:30:52`
3. **Error**: `❌ Ingesting Option Snapshots Failed - Exit code: 1`
4. **Timeout**: `⏱️ Ingesting Option Snapshots Timed Out - Killed after 30 minutes`

Notifications appear as desktop popups (if `notify-send` is installed).

## Viewing Results

### Check Last Run

```bash
# Last 50 lines of service logs
journalctl --user -u ingest_snapshots.service -n 50

# Just the last run
journalctl --user -u ingest_snapshots.service --since "10 minutes ago"

# See connection pool stats
journalctl --user -u ingest_snapshots.service -f | grep "pool stats"
```

### Parse Output

Look for in logs:
```
Starting option snapshots ingestion at 2025-10-27 10:30:15
Database pool stats - Active: 42, Min: 10, Max: 300
Retrieved batch at offset 0 for session 2025-10-27 10:30:15
Process completed successfully at 2025-10-27 10:30:52
```

## Management

### Enable/Disable Timers

```bash
# Disable (won't start on login, but manual runs still work)
systemctl --user disable ingest_snapshots.timer

# Re-enable
systemctl --user enable ingest_snapshots.timer

# Check if enabled
systemctl --user is-enabled ingest_snapshots.timer
```

### Stop/Start Timers

```bash
# Stop timer (no more scheduled runs)
systemctl --user stop ingest_snapshots.timer

# Start timer again
systemctl --user start ingest_snapshots.timer

# Restart timer
systemctl --user restart ingest_snapshots.timer

# Check if running
systemctl --user is-active ingest_snapshots.timer
```

### View Timer Details

```bash
# Full status
systemctl --user status ingest_snapshots.timer

# Show all properties
systemctl --user show ingest_snapshots.timer

# Show service configuration
systemctl --user show ingest_snapshots.service
```

## Customization

### Change Schedule

Edit the timer file and reload:

```bash
# Edit timer
nano /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.timer

# Or edit the symlink
nano ~/.config/systemd/user/ingest_snapshots.timer

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart ingest_snapshots.timer
```

### Change Timeout

Edit the service file:

```bash
# Current timeout: 30 minutes (1800 seconds)
# In ingest_snapshots.service, line with ExecStart

# Change if needed (example: 1 hour = 3600 seconds)
# Then reload: systemctl --user daemon-reload
```

### Add More Timers

Copy and modify the timer file:

```bash
# Example: Run ingest_snapshots every 5 minutes instead of 10
cp ~/.config/systemd/user/ingest_snapshots.timer \
   ~/.config/systemd/user/ingest_snapshots_5min.timer

nano ~/.config/systemd/user/ingest_snapshots_5min.timer
# Change: OnUnitActiveSec=5min

systemctl --user daemon-reload
systemctl --user enable ingest_snapshots_5min.timer
```

## Troubleshooting

### Timers not appearing

```bash
systemctl --user daemon-reload
systemctl --user list-timers --all
```

### Timer not firing

```bash
# Check timer status
systemctl --user status ingest_snapshots.timer

# Check timer logs
journalctl --user -u ingest_snapshots.timer -n 50

# Verify syntax
systemd-analyze calendar "Mon-Fri *-*-* 09:30-16:00"

# Check if you're in the right time window
date
```

### Service fails when timer runs

```bash
# Check service logs
journalctl --user -u ingest_snapshots.service -n 100

# Test manual run
systemctl --user start ingest_snapshots.service
journalctl --user -u ingest_snapshots.service -f

# Check environment
systemctl --user show-environment | grep DATABASE
```

### No notifications appearing

```bash
# Verify notify-send is available
which notify-send

# Install if needed
sudo apt install libnotify-bin  # Debian/Ubuntu

# Test notification
notify-send "Test notification"
```

## Summary of What's Running

| Component | File | Purpose |
|-----------|------|---------|
| **Poetry Script** | `cli/ingest_options.py` | Fetch option contracts |
| **Poetry Script** | `cli/ingest_snapshots.py` | Fetch market data |
| **ZSH Wrapper** | `scripts/ingest_options.zsh` | Add notifications + exit handling |
| **ZSH Wrapper** | `scripts/ingest_snapshots.zsh` | Add notifications + exit handling |
| **Systemd Service** | `scripts/ingest_options.service` | Run ZSH script with environment |
| **Systemd Service** | `scripts/ingest_snapshots.service` | Run ZSH script with environment |
| **Systemd Timer** | `scripts/ingest_options.timer` | Schedule daily at 2 AM |
| **Systemd Timer** | `scripts/ingest_snapshots.timer` | Schedule every 10 min (market hours) |

## Quick Reference Commands

```bash
# List all timers and next run times
systemctl --user list-timers

# Watch snapshots ingestion logs
journalctl --user -u ingest_snapshots.service -f

# Manually run snapshots
systemctl --user start ingest_snapshots.service

# Check if timer is active
systemctl --user is-active ingest_snapshots.timer

# View timer details
systemctl --user status ingest_snapshots.timer

# Stop/start timer
systemctl --user stop ingest_snapshots.timer
systemctl --user start ingest_snapshots.timer

# View service configuration
systemctl --user show ingest_snapshots.service

# Verify timer schedule
systemd-analyze calendar "Mon-Fri *-*-* 09:30-16:00"
```

## Next Steps

1. ✅ Run the installation steps above
2. ✅ Verify with `systemctl --user list-timers`
3. ✅ Monitor first run: `journalctl --user -u ingest_snapshots.service -f`
4. ✅ Check logs: `journalctl --user -u ingest_snapshots.service -n 50`
5. ✅ Receive desktop notifications

## Documents

- **`TIMERS_SETUP.md`** - Comprehensive timer documentation
- **`TIMERS_QUICK_REFERENCE.md`** - Quick reference for common commands
- **`ZSH_SCRIPTS_SETUP.md`** - ZSH wrapper script documentation
- **`SPLIT_INGESTION_SERVICES.md`** - Service overview and details
- **`SETUP_SPLIT_SERVICES.md`** - Initial setup guide
- **`DATABASE_CONCURRENCY_CONFIG.md`** - Database configuration
- **`INGEST_SERVICES_QUICK_REFERENCE.md`** - General quick reference
