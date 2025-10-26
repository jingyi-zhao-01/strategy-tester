#!/usr/bin/env zsh
#
# ingest_options.zsh
# Purpose: Ingest option contracts from Polygon API into the database
# Dispatches desktop notifications before starting and upon completion

set -euo pipefail

# Optional: desktop notification support (safe to keep, harmless if it fails)
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

# cd to project root so poetry sees pyproject.toml
cd /home/jingyi/PycharmProjects/strategy-tester || exit 1

# Send a desktop notification before starting (best-effort)
if command -v notify-send >/dev/null 2>&1; then
    notify-send "📥 Ingesting Option Contracts" "Starting at $(date '+%H:%M:%S')..." --urgency=normal
fi

# Run job with timeout (30 minutes = 1800 seconds)
echo "Starting option contracts ingestion at $(date '+%Y-%m-%d %H:%M:%S')"

poetry run ingest_options
exit_code=$?

# Report result based on exit code
if [ $exit_code -eq 124 ]; then
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "⏱️ Option Contracts Ingestion Timed Out" "Killed after 30 minutes (timeout)" --urgency=critical
    fi
    echo "Process timed out after 30 minutes (exit code 124)"
    exit 124
elif [ $exit_code -ne 0 ]; then
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "❌ Option Contracts Ingestion Failed" "Exit code: $exit_code" --urgency=critical
    fi
    echo "Process failed with exit code: $exit_code"
    exit "$exit_code"
else
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "✅ Option Contracts Ingestion Completed" "Finished successfully at $(date '+%H:%M:%S')" --urgency=normal
    fi
    echo "Process completed successfully at $(date '+%Y-%m-%d %H:%M:%S')"
    exit 0
fi
