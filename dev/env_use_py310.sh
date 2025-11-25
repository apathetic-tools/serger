#!/bin/bash
set -euo pipefail
# Switch Poetry environment to Python 3.10
# Tries system Python 3.10 first, then falls back to mise

# Try system python3.10 first (avoid mise-managed paths), then mise
PY310_PATH=""
# Check common system locations
for POSSIBLE_PATH in /usr/bin/python3.10 /usr/local/bin/python3.10; do
  if [ -x "$POSSIBLE_PATH" ] && "$POSSIBLE_PATH" --version 2>&1 | grep -q "3.10"; then
    PY310_PATH="$POSSIBLE_PATH"
    break
  fi
done
# If not in system locations, check PATH but exclude mise-managed paths
if [ -z "$PY310_PATH" ]; then
  CMD_PATH=$(command -v python3.10 2>/dev/null)
  if [ -n "$CMD_PATH" ] && ! echo "$CMD_PATH" | grep -qE "(mise|\.mise)"; then
    if "$CMD_PATH" --version 2>&1 | grep -q "3.10"; then
      PY310_PATH="$CMD_PATH"
    fi
  fi
fi
# Use system Python if found
if [ -n "$PY310_PATH" ]; then
  poetry env use "$PY310_PATH" && poetry install
# Fall back to mise
elif command -v mise >/dev/null 2>&1; then
  # Try to find Python 3.10 via mise
  MISE_PYTHON=$(mise which python3.10 2>/dev/null || true)
  if [ -n "$MISE_PYTHON" ] && [ -x "$MISE_PYTHON" ]; then
    poetry env use "$MISE_PYTHON" && poetry install
  else
    echo "❌ Python 3.10 not found via mise."
    echo "   Install with: mise install python@3.10"
    echo "   Or run: poetry run poe setup:python:check"
    exit 1
  fi
else
  echo "❌ Python 3.10 not found. Run: poetry run poe setup:python:check"
  exit 1
fi

