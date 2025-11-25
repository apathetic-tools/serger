#!/bin/bash
set -euo pipefail
# Switch Poetry environment to the highest available Python 3.x version
# Tries system Python first, then falls back to mise

PYTHON_PATH=""
HIGHEST_MINOR=0

# Check system Python versions (avoid mise-managed paths)
# Try versioned python3.x in descending order (3.20 down to 3.10)
for MINOR in $(seq 20 -1 10); do
  # Check common system locations
  for POSSIBLE_PATH in "/usr/bin/python3.$MINOR" "/usr/local/bin/python3.$MINOR"; do
    if [ -x "$POSSIBLE_PATH" ]; then
      if "$POSSIBLE_PATH" --version 2>&1 | grep -q "3\.$MINOR" || "$POSSIBLE_PATH" --version 2>&1 | grep -q "^Python 3\.$MINOR"; then
        PYTHON_PATH="$POSSIBLE_PATH"
        HIGHEST_MINOR=$MINOR
        break 2
      fi
    fi
  done
  
  # Check PATH but exclude mise-managed paths
  CMD_PATH=$(command -v "python3.$MINOR" 2>/dev/null || true)
  if [ -n "$CMD_PATH" ] && ! echo "$CMD_PATH" | grep -qE "(mise|\.mise)"; then
    if "$CMD_PATH" --version 2>&1 | grep -q "3\.$MINOR" || "$CMD_PATH" --version 2>&1 | grep -q "^Python 3\.$MINOR"; then
      PYTHON_PATH="$CMD_PATH"
      HIGHEST_MINOR=$MINOR
      break
    fi
  fi
done

# Fallback to plain python3 if no versioned one found
if [ -z "$PYTHON_PATH" ]; then
  CMD_PATH=$(command -v python3 2>/dev/null)
  if [ -n "$CMD_PATH" ] && ! echo "$CMD_PATH" | grep -qE "(mise|\.mise)"; then
    if "$CMD_PATH" --version 2>&1 | grep -q "3\."; then
      PYTHON_PATH="$CMD_PATH"
    fi
  fi
fi

# Use system Python if found
if [ -n "$PYTHON_PATH" ]; then
  poetry env use "$PYTHON_PATH" && poetry install
# Fall back to mise - find highest version
elif command -v mise >/dev/null 2>&1; then
  HIGHEST_MISE_MINOR=0
  HIGHEST_MISE_PYTHON=""
  
  # Try to find highest Python version via mise
  for MINOR in $(seq 20 -1 10); do
    MISE_PYTHON=$(mise which "python3.$MINOR" 2>/dev/null || true)
    if [ -n "$MISE_PYTHON" ] && [ -x "$MISE_PYTHON" ]; then
      HIGHEST_MISE_MINOR=$MINOR
      HIGHEST_MISE_PYTHON="$MISE_PYTHON"
      break
    fi
  done
  
  # If no versioned Python found, try plain python3
  if [ -z "$HIGHEST_MISE_PYTHON" ]; then
    HIGHEST_MISE_PYTHON=$(mise which python3 2>/dev/null || true)
  fi
  
  if [ -n "$HIGHEST_MISE_PYTHON" ] && [ -x "$HIGHEST_MISE_PYTHON" ]; then
    poetry env use "$HIGHEST_MISE_PYTHON" && poetry install
  else
    echo "❌ No Python 3.x version found via mise."
    echo "   Install with: mise install python@3.12"
    echo "   Or run: poetry run poe setup:python:check"
    exit 1
  fi
else
  echo "❌ No Python 3.x version found. Please install Python 3.10 or newer."
  exit 1
fi

