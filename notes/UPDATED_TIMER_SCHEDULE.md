# Updated Timer Schedule

## New Schedule Based on Consumption Patterns

### ingest_options.timer
**Schedule**: Every 3 days at 21:00 PST (9 PM Pacific Time)
**UTC Time**: 05:00 UTC (next day)
**Purpose**: Fetch new option contracts as they're released by the market
**Files**: 
- Timer: `scripts/ingest_options.timer`
- Service: `scripts/ingest_options.service`
- Script: `scripts/ingest_options.zsh`
- Python: `cli/ingest_options.py`

**Run Days**:
- Day 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31 of each month
- Pattern: approximately every 3 days, accounting for month boundaries

### ingest_snapshots.timer
**Schedule**: Daily at 23:30 PST (11:30 PM Pacific Time)
**UTC Time**: 07:30 UTC (next day)
**Purpose**: Fetch daily snapshots of all active contracts
**Files**:
- Timer: `scripts/ingest_snapshots.timer`
- Service: `scripts/ingest_snapshots.service`
- Script: `scripts/ingest_snapshots.zsh`
- Python: `cli/ingest_snapshots.py`

**Run Days**: Every day

## Time Zone Reference

```
PST (Pacific Standard Time) = UTC - 8 hours

21:00 PST (Options)     = 05:00 UTC (next day)
23:30 PST (Snapshots)   = 07:30 UTC (next day)

Examples:
- Oct 26, 21:00 PST  = Oct 27, 05:00 UTC
- Oct 26, 23:30 PST  = Oct 27, 07:30 UTC
```

## Rationale

**Options (every 3 days at 21:00 PST)**:
- Market rolls out new options periodically (roughly every 3 days)
- Running at 21:00 PST (after market close) is efficient
- Less frequent updates reduce database churn

**Snapshots (daily at 23:30 PST)**:
- Daily snapshots capture end-of-day market state
- Running after market close (23:30 PST) ensures complete day's data
- Daily frequency matches data consumption requirements

## Configuration

### ingest_options.timer
```ini
[Timer]
# Run every 3 days at 21:00 PST (9 PM Pacific Time)
OnCalendar=*-*-1,4,7,10,13,16,19,22,25,28,31 05:00:00
Persistent=true
AccuracySec=1s
```

### ingest_snapshots.timer
```ini
[Timer]
# Run daily at 23:30 PST (11:30 PM Pacific Time)
OnCalendar=daily
OnCalendar=*-*-* 07:30:00
Persistent=true
AccuracySec=1s
```

## Verify Schedule

After updating, reload and verify:

```bash
# Reload systemd configuration
systemctl --user daemon-reload

# Verify timer schedules
systemd-analyze calendar "*-*-1,4,7,10,13,16,19,22,25,28,31 05:00:00"
systemd-analyze calendar "*-*-* 07:30:00"

# View next run times
systemctl --user list-timers ingest_*.timer
```

## Example Output

```bash
$ systemctl --user list-timers ingest_*.timer

NEXT                        LEFT        LAST PASSED UNIT
Sun 2025-10-26 05:00:00 UTC 1h 23min    ... ingest_options.timer
Sun 2025-10-26 07:30:00 UTC 3h 53min    ... ingest_snapshots.timer
```

## Quick Commands

```bash
# Reload after timer changes
systemctl --user daemon-reload

# Check next scheduled runs
systemctl --user list-timers

# View timer logs
journalctl --user -u ingest_options.timer -f
journalctl --user -u ingest_snapshots.timer -f

# Manually trigger (doesn't affect schedule)
systemctl --user start ingest_options.service
systemctl --user start ingest_snapshots.service

# Check timer status
systemctl --user status ingest_options.timer
systemctl --user status ingest_snapshots.timer
```

## Files Modified

```
✓ scripts/ingest_options.timer      (updated schedule)
✓ scripts/ingest_snapshots.timer    (updated schedule)
```

## Next Steps

1. Reload systemd: `systemctl --user daemon-reload`
2. Verify schedules: `systemctl --user list-timers ingest_*.timer`
3. Monitor first run: `journalctl --user -u ingest_snapshots.service -f`
4. Check logs: `journalctl --user -u ingest_snapshots.service -n 50`
