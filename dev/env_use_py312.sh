#!/bin/bash
set -euo pipefail
# Switch Poetry environment to Python 3.12
# Tries system Python 3.12 first, then falls back to mise

# Try system python3.12 first (avoid mise-managed paths), then mise
PY312_PATH=""
# Check common system locations
for POSSIBLE_PATH in /usr/bin/python3.12 /usr/local/bin/python3.12; do
  if [ -x "$POSSIBLE_PATH" ] && "$POSSIBLE_PATH" --version 2>&1 | grep -q "3.12"; then
    PY312_PATH="$POSSIBLE_PATH"
    break
  fi
done
# If not in system locations, check PATH but exclude mise-managed paths
if [ -z "$PY312_PATH" ]; then
  CMD_PATH=$(command -v python3.12 2>/dev/null)
  if [ -n "$CMD_PATH" ] && ! echo "$CMD_PATH" | grep -qE "(mise|\.mise)"; then
    if "$CMD_PATH" --version 2>&1 | grep -q "3.12"; then
      PY312_PATH="$CMD_PATH"
    fi
  fi
fi
# Use system Python if found
if [ -n "$PY312_PATH" ]; then
  poetry env use "$PY312_PATH" && poetry install
# Fall back to mise
elif command -v mise >/dev/null 2>&1; then
  # Try to find Python 3.12 via mise
  MISE_PYTHON=$(mise which python3.12 2>/dev/null || true)
  if [ -n "$MISE_PYTHON" ] && [ -x "$MISE_PYTHON" ]; then
    poetry env use "$MISE_PYTHON" && poetry install
  else
    echo "❌ Python 3.12 not found via mise."
    echo "   Install with: mise install python@3.12"
    echo "   Or run: poetry run poe setup:python:check"
    exit 1
  fi
else
  echo "❌ Python 3.12 not found. Run: poetry run poe setup:python:check"
  exit 1
fi

