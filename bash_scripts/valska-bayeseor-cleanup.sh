#!/bin/bash
# filepath: /home/ps550/ValSKA/bash_scripts/valska-bayeseor-cleanup.sh
#
# Wrapper for valska-bayeseor-cleanup.
#
# Usage:
#   ./bash_scripts/valska-bayeseor-cleanup.sh --prune-logs [--execute] [--json]
#   ./bash_scripts/valska-bayeseor-cleanup.sh --prune-runs --run-status missing --execute --confirm-runs DELETE
#
# Optional environment variable:
#   VALSKA_CONDA_ENV=<name>  (default: valska)

set -euo pipefail

VALSKA_CONDA_ENV="${VALSKA_CONDA_ENV:-valska}"

if command -v valska-bayeseor-cleanup >/dev/null 2>&1; then
    exec valska-bayeseor-cleanup "$@"
fi

if command -v conda >/dev/null 2>&1; then
    if conda run -n "$VALSKA_CONDA_ENV" python -m \
        valska_hera_beam.external_tools.bayeseor.cli_cleanup "$@"; then
        exit 0
    fi
fi

if command -v python >/dev/null 2>&1 && [[ -d "src" ]]; then
    exec env PYTHONPATH=src python -m \
        valska_hera_beam.external_tools.bayeseor.cli_cleanup "$@"
fi

echo "Error: could not find valska-bayeseor-cleanup, conda fallback, or local module fallback." >&2
exit 127
