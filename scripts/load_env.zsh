#!/usr/bin/env zsh
#
# load_env.zsh
# Purpose: read .env in the project root and export all key=value pairs
# Behavior:
#   - Ignores blank lines
#   - Ignores lines starting with '#'
#   - Supports values that contain &, ?, =, %20, etc.
#   - Strips one pair of surrounding double quotes if present
# Output:
#   - Exports variables into the *current shell environment*
#
# Usage pattern (from another zsh script):
#   source /path/to/load_env.zsh /path/to/project/.env
#
# This must be sourced, not executed, so that exports affect the caller.

set -euo pipefail

# path to .env comes from $1, defaults to ./.env
if [ $# -lt 1 ]; then
    ENV_FILE="./.env"
else
    ENV_FILE="$1"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "load_env.zsh: file not found: $ENV_FILE" >&2
    return 1
fi

# Read the .env file line by line
while IFS= read -r line; do
    # skip empty lines
    [ -z "$line" ] && continue

    # skip pure comment lines (starting with '#')
    case "$line" in
        \#*) continue ;;
    esac

    # split on the first '='
    key="${line%%=*}"
    val="${line#*=}"

    # trim leading/trailing whitespace from key
    # (defensive: in case someone wrote 'FOO =bar')
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    # trim leading/trailing whitespace from val
    val="${val#"${val%%[![:space:]]*}"}"
    val="${val%"${val##*[![:space:]]}"}"

    # remove one pair of surrounding double quotes if present
    if [[ "$val" == \"*\" && "$val" == *\" ]]; then
        val="${val%\"}"
        val="${val#\"}"
    fi

    # export into caller shell
    export "$key=$val"
done < "$ENV_FILE"
