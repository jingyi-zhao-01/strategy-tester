#!/usr/bin/env bash

# Build standalone CLI binary "strategy-tester" using PyInstaller
# Usage: scripts/build_binary.sh

# Ensure we're in repo root
cd "$(dirname "$0")/.."

# Ensure PyInstaller is available
if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "PyInstaller not found in PATH, installing locally..."
  python3 -m pip install --user pyinstaller || exit 1
  export PATH="$HOME/.local/bin:$PATH"
fi

# Clean previous builds
rm -rf build dist *.spec || true

# Build
pyinstaller \
  --name strategy-tester \
  --onefile \
  --hidden-import options.api.options \
  --hidden-import prisma \
  --hidden-import prisma.models \
  cli/cli.py || exit 1

# Result: dist/strategy-tester
ls -lh dist || true
