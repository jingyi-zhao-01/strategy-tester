# Systemd Timers for Automated Ingestion

Two systemd timer files have been created to automatically schedule the ingestion services.

## Timer Files

### 1. `ingest_options.timer`
**Schedule**: Daily at 2:00 AM
**Service**: `ingest_options.service`
**Purpose**: Fetch and update option contracts (heavy operation, run less frequently)

```ini
[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true
```

### 2. `ingest_snapshots.timer`
**Schedule**: Every 10 minutes during market hours (Mon-Fri, 9:30 AM - 4:00 PM)
**Service**: `ingest_snapshots.service`
**Purpose**: Fetch current market data for active contracts (frequent, lightweight)

```ini
[Timer]
OnCalendar=Mon-Fri *-*-* 09:30-16:00
OnUnitActiveSec=10min
Persistent=true
```

## Installation

### One-time Setup

```bash
# Create symlinks for timers in user systemd directory
mkdir -p ~/.config/systemd/user

ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_options.timer \
  ~/.config/systemd/user/

ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.timer \
  ~/.config/systemd/user/

# Reload systemd to recognize new timers
systemctl --user daemon-reload

# Enable timers to start automatically on user login
systemctl --user enable ingest_options.timer
systemctl --user enable ingest_snapshots.timer

# Start the timers immediately
systemctl --user start ingest_options.timer
systemctl --user start ingest_snapshots.timer
```

## Management Commands

### View Timer Status

```bash
# List all active timers
systemctl --user list-timers

# View next 10 scheduled runs
systemctl --user list-timers --all

# Check specific timer
systemctl --user status ingest_snapshots.timer
systemctl --user status ingest_options.timer
```

### View Scheduled Times

```bash
# Show when ingest_snapshots will run next
systemctl --user list-timers ingest_snapshots.timer

# Show when ingest_options will run next
systemctl --user list-timers ingest_options.timer
```

### Manual Trigger

```bash
# Manually trigger ingest_snapshots (doesn't wait for timer)
systemctl --user start ingest_snapshots.service

# Manually trigger ingest_options
systemctl --user start ingest_options.service

# Note: This doesn't reset the timer; the timer will still fire at its scheduled time
```

### View Logs

```bash
# View all timer events
journalctl --user -u ingest_snapshots.timer -f

# View all service execution logs
journalctl --user -u ingest_snapshots.service -f

# View both timer and service together
journalctl --user --unit=ingest_snapshots.timer --unit=ingest_snapshots.service -f

# View last 50 lines
journalctl --user -u ingest_snapshots.timer -n 50
journalctl --user -u ingest_snapshots.service -n 50
```

### Enable/Disable Timers

```bash
# Enable timer (start on user login)
systemctl --user enable ingest_snapshots.timer

# Disable timer (don't start on login, but keep for manual starts)
systemctl --user disable ingest_snapshots.timer

# Stop timer (immediately stop scheduled execution)
systemctl --user stop ingest_snapshots.timer

# Start timer (resume scheduled execution)
systemctl --user start ingest_snapshots.timer
```

## Schedule Details

### ingest_options.timer (Daily at 2 AM)

```
Time: 02:00:00 every day
Example runs:
- 2025-10-26 02:00:00
- 2025-10-27 02:00:00
- 2025-10-28 02:00:00
```

**Rationale**: 
- Runs at 2 AM (outside market hours, early in the morning)
- Once per day is sufficient (contracts update slowly)
- Doesn't interfere with intraday operations

### ingest_snapshots.timer (Every 10 minutes, Mon-Fri, 9:30 AM - 4:00 PM)

```
Time: Every 10 minutes during market hours
Days: Monday through Friday
Hours: 9:30 AM to 4:00 PM (16:00 in 24-hour format)

Example runs on a Friday:
- 2025-10-24 09:30:00
- 2025-10-24 09:40:00
- 2025-10-24 09:50:00
- 2025-10-24 10:00:00
... (continues every 10 minutes)
- 2025-10-24 15:50:00
- 2025-10-24 16:00:00
(No runs on Saturday/Sunday)
```

**Rationale**:
- 10-minute interval captures market movements
- Only during market hours (9:30 AM - 4:00 PM EST)
- Weekdays only (no trading on weekends)
- Lightweight operation, suitable for frequent execution

## Timer Properties

### Both Timers Have:

```ini
Persistent=true
```
- If systemd is restarted while a timer should have run, it will run immediately after restart
- Prevents missing scheduled jobs during system downtime

```ini
AccuracySec=1s
```
- Timer triggers within ±1 second of scheduled time
- More accurate than the default 1 minute tolerance

```ini
Requires=ingest_snapshots.service
```
- The service is required but not started by the timer
- Timer starts the service when scheduled

## How Timers Work

### Timer Lifecycle

```
1. Timer starts (systemctl start ingest_snapshots.timer)
2. Timer runs according to OnCalendar and OnUnitActiveSec rules
3. When trigger time arrives, timer starts the service
4. Service runs to completion
5. Timer waits for next trigger time
6. Repeat from step 3
```

### Example: ingest_snapshots.timer execution

```
09:30:00 - Timer triggers → starts ingest_snapshots.service
09:30:15 - Service completes (notification sent)
09:40:00 - Timer triggers again → starts ingest_snapshots.service
09:40:30 - Service completes
09:50:00 - Timer triggers again → starts ingest_snapshots.service
09:50:45 - Service completes
... (every 10 minutes until 16:00)
```

## Viewing Next Scheduled Runs

```bash
$ systemctl --user list-timers ingest_snapshots.timer

NEXT                        LEFT        LAST                        PASSED UNIT                        ACTIVATES
Mon 2025-10-27 10:40:00 EST 3min 22s    Mon 2025-10-27 10:30:12 EST 10s   ingest_snapshots.timer      ingest_snapshots.service

NEXT       - When the timer will fire next
LEFT       - How long until it fires
LAST       - When it last fired
PASSED     - How long ago it last fired
UNIT       - The timer unit
ACTIVATES  - What service it activates
```

## Common Patterns

### Check if timers are running

```bash
# Quick check
systemctl --user is-active ingest_snapshots.timer
# Output: active

# Detailed view
systemctl --user status ingest_snapshots.timer
```

### Temporarily disable a timer

```bash
# Stop the timer (won't fire again until manually started)
systemctl --user stop ingest_snapshots.timer

# Check it's stopped
systemctl --user is-active ingest_snapshots.timer
# Output: inactive

# Later, restart it
systemctl --user start ingest_snapshots.timer
```

### View when next run is scheduled

```bash
systemctl --user list-timers ingest_snapshots.timer --all
```

### See all recent timer activity

```bash
# Last 100 lines of timer/service logs
journalctl --user --unit=ingest_snapshots.timer --unit=ingest_snapshots.service -n 100

# Today's runs only
journalctl --user --unit=ingest_snapshots.service --since today
```

## Customizing Schedules

To change the schedule, edit the timer file and update systemd:

```bash
# Edit the timer
nano ~/.config/systemd/user/ingest_snapshots.timer

# Or edit the original file
nano /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_snapshots.timer

# Reload systemd
systemctl --user daemon-reload

# Restart the timer
systemctl --user restart ingest_snapshots.timer
```

### Schedule Format Examples

```ini
# Every hour
OnCalendar=*-*-* *:00:00

# Every 15 minutes
OnUnitActiveSec=15min

# Specific day of week (0=Sunday, 1=Monday, etc.)
OnCalendar=Mon,Wed,Fri *-*-* 09:00:00

# Specific date (run on October 26 at 2 AM)
OnCalendar=2025-10-26 02:00:00

# Last day of month at 11:59 PM
OnCalendar=*-*-~ 23:59:00

# Every weekday at 9 AM
OnCalendar=Mon-Fri *-*-* 09:00:00

# Twice a day (8 AM and 8 PM)
OnCalendar=*-*-* 08:00:00
OnCalendar=*-*-* 20:00:00
```

## Troubleshooting

### Timer not firing

```bash
# Check if timer is enabled
systemctl --user is-enabled ingest_snapshots.timer

# Check timer status
systemctl --user status ingest_snapshots.timer

# Check systemd logs
journalctl --user -u ingest_snapshots.timer -n 50

# Verify schedule syntax
systemd-analyze calendar "Mon-Fri *-*-* 09:30-16:00"
```

### Service fails when timer runs it

```bash
# Check service logs
journalctl --user -u ingest_snapshots.service -n 100

# Check for environment issues
systemctl --user show-environment | grep DATABASE_URL

# Run service manually to test
systemctl --user start ingest_snapshots.service

# View real-time output
journalctl --user -u ingest_snapshots.service -f
```

### Timer fires too frequently or not at all

```bash
# Verify the OnCalendar syntax
systemd-analyze calendar "Mon-Fri *-*-* 09:30-16:00"
# Output: Mon-Fri *-*-* 09:30-16:00
#         Iterations parsed: 42840

# Check if you're within market hours
date
# If outside 09:30-16:00, timer won't fire
```

## Files Reference

```
/home/jingyi/PycharmProjects/strategy-tester/
├── scripts/
│   ├── ingest_options.service
│   ├── ingest_options.timer      ← NEW
│   ├── ingest_options.zsh
│   ├── ingest_snapshots.service
│   ├── ingest_snapshots.timer    ← NEW
│   └── ingest_snapshots.zsh
└── ~/.config/systemd/user/
    ├── ingest_options.timer      (symlink)
    ├── ingest_options.service    (symlink)
    ├── ingest_snapshots.timer    (symlink)
    └── ingest_snapshots.service  (symlink)
```

## Next Steps

1. ✅ Timer files created
2. Install timers:
   ```bash
   ln -s /home/jingyi/PycharmProjects/strategy-tester/scripts/ingest_*.timer \
     ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable ingest_*.timer
   systemctl --user start ingest_*.timer
   ```
3. Verify timers are active:
   ```bash
   systemctl --user list-timers
   ```
4. Monitor execution:
   ```bash
   journalctl --user -u ingest_snapshots.service -f
   ```
