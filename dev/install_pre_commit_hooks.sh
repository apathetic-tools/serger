#!/bin/bash
set -euo pipefail
# Install pre-commit hooks if they're not already installed

if [ ! -f .git/hooks/pre-commit ] || ! grep -q 'pre-commit' .git/hooks/pre-commit 2>/dev/null; then
    poetry run pre-commit install --install-hooks
    poetry run pre-commit install --hook-type pre-push
fi

