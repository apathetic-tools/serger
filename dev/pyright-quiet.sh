#!/bin/bash
set -euo pipefail
# Run pyright and filter out the summary line only when all counts are 0, preserving exit code
# Accepts all pyright arguments and passes them through

pyright "$@" 2>&1 | grep -vE '^0 error(s)?, 0 warning(s)?, 0 information(s)?$' || exit ${PIPESTATUS[0]}

