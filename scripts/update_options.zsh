#!/usr/bin/env zsh
#
# update_options.zsh
# Purpose: load env, then run the ingestion job via poetry under timeout

set -euo pipefail

# Optional: desktop notification support (safe to keep, harmless if it fails)
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

# cd to project root so poetry sees pyproject.toml
cd /home/jingyi/PycharmProjects/strategy-tester || exit 1

# Load .env into this shell using the loader script
# source /home/jingyi/PycharmProjects/strategy-tester/scripts/load_env.zsh /home/jingyi/PycharmProjects/strategy-tester/.env

# Debug (optional): dump env snapshot for verification
# Remove if you don't want secrets written to disk
# printenv | sort > /tmp/update_options_env.txt

# Send a desktop notification (best-effort)
if command -v notify-send >/dev/null 2>&1; then
    notify-send "⏰ Running update_options" "Starting at $(date '+%H:%M:%S')."
fi

# Run job with timeout to avoid hangs

poetry run update_options
exit_code=$?

# Report result
if [ $exit_code -eq 124 ]; then
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "⏰ update_options timed out" "Killed after 40s"
    fi
    echo "Process timed out after 40 seconds"
elif [ $exit_code -ne 0 ]; then
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "❌ update_options failed" "Exit code: $exit_code"
    fi
    echo "Process failed with exit code: $exit_code"
else
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "✅ update_options completed" "Finished successfully"
    fi
    echo "Process completed successfully"
fi
