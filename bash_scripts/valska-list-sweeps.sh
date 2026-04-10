#!/bin/bash
# filepath: /home/ps550/ValSKA/bash_scripts/valska-list-sweeps.sh
#
# Wrapper for the Python CLI that lists ValSKA BayesEoR sweep directories.
#
# Usage:
#   ./bash_scripts/valska-list-sweeps.sh
#   ./bash_scripts/valska-list-sweeps.sh --results-root /path/to/results_root
#   ./bash_scripts/valska-list-sweeps.sh --json
#
# Optional environment variable:
#   VALSKA_CONDA_ENV=<name>  (default: valska)

set -euo pipefail

VALSKA_CONDA_ENV="${VALSKA_CONDA_ENV:-valska}"

if command -v valska-bayeseor-list-sweeps >/dev/null 2>&1; then
    exec valska-bayeseor-list-sweeps "$@"
fi

if command -v conda >/dev/null 2>&1; then
    exec conda run -n "$VALSKA_CONDA_ENV" valska-bayeseor-list-sweeps "$@"
fi

# Developer fallback when entry-point scripts are not installed yet.
if command -v python >/dev/null 2>&1 && [[ -d "src" ]]; then
    exec env PYTHONPATH=src python -m \
        valska.external_tools.bayeseor.cli_list_sweeps "$@"
fi

echo "Error: could not find valska-bayeseor-list-sweeps, conda fallback, or local module fallback." >&2
exit 127
