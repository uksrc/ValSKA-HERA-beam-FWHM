#!/bin/bash
# filepath: /home/ps550/ValSKA-HERA-beam-FWHM/bash_scripts/valska-bayeseor-compare-sweeps.sh
#
# Wrapper for valska-bayeseor-compare-sweeps.
#
# Usage:
#   ./bash_scripts/valska-bayeseor-compare-sweeps.sh <left> <right> [--metric <name>] [--top N] [--json]
#
# Optional environment variable:
#   VALSKA_CONDA_ENV=<name>  (default: valska)

set -euo pipefail

VALSKA_CONDA_ENV="${VALSKA_CONDA_ENV:-valska}"

if command -v valska-bayeseor-compare-sweeps >/dev/null 2>&1; then
    exec valska-bayeseor-compare-sweeps "$@"
fi

if command -v conda >/dev/null 2>&1; then
    if conda run -n "$VALSKA_CONDA_ENV" python -m \
        valska_hera_beam.external_tools.bayeseor.cli_compare_sweeps "$@"; then
        exit 0
    fi
fi

if command -v python >/dev/null 2>&1 && [[ -d "src" ]]; then
    exec env PYTHONPATH=src python -m \
        valska_hera_beam.external_tools.bayeseor.cli_compare_sweeps "$@"
fi

echo "Error: could not find valska-bayeseor-compare-sweeps, conda fallback, or local module fallback." >&2
exit 127
