#!/bin/bash
# filepath: /home/ps550/ValSKA/bash_scripts/valska-bayeseor-resume-sweep.sh
#
# Wrapper for valska-bayeseor-resume.
#
# Usage:
#   ./bash_scripts/valska-bayeseor-resume-sweep.sh /path/to/_sweeps/<run_id> [--stage cpu|gpu|all] [--json]
#
# Optional environment variable:
#   VALSKA_CONDA_ENV=<name>  (default: valska)

set -euo pipefail

VALSKA_CONDA_ENV="${VALSKA_CONDA_ENV:-valska}"

if command -v valska-bayeseor-resume >/dev/null 2>&1; then
    exec valska-bayeseor-resume "$@"
fi

if command -v conda >/dev/null 2>&1; then
    if conda run -n "$VALSKA_CONDA_ENV" python -m \
        valska_hera_beam.external_tools.bayeseor.cli_resume "$@"; then
        exit 0
    fi
fi

if command -v python >/dev/null 2>&1 && [[ -d "src" ]]; then
    exec env PYTHONPATH=src python -m \
        valska_hera_beam.external_tools.bayeseor.cli_resume "$@"
fi

echo "Error: could not find valska-bayeseor-resume, conda fallback, or local module fallback." >&2
exit 127
