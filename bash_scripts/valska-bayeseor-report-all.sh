#!/bin/bash
# filepath: /home/ps550/ValSKA-HERA-beam-FWHM/bash_scripts/valska-bayeseor-report-all.sh
#
# Wrapper for valska-bayeseor-report-all.
#
# Usage:
#   ./bash_scripts/valska-bayeseor-report-all.sh [--beam <name>] [--sky <name>] [--only-new] [--json]
#
# Example (current airy analysis):
#   ./bash_scripts/valska-bayeseor-report-all.sh --beam airy_diam14m --sky GSM_plus_GLEAM --run-id sweep_airy_init
#
# Same example (current airy analysis) bu with plots:
#   ./bash_scripts/valska-bayeseor-report-all.sh --beam airy_diam14m --sky GSM_plus_GLEAM --run-id sweep_airy_init --include-plot-analysis-results --include-complete-analysis-table
#
# Optional environment variable:
#   VALSKA_CONDA_ENV=<name>  (default: valska)

set -euo pipefail

VALSKA_CONDA_ENV="${VALSKA_CONDA_ENV:-valska}"

if command -v valska-bayeseor-report-all >/dev/null 2>&1; then
    exec valska-bayeseor-report-all "$@"
fi

if command -v conda >/dev/null 2>&1; then
    if conda run -n "$VALSKA_CONDA_ENV" python -m \
        valska_hera_beam.external_tools.bayeseor.cli_report_all "$@"; then
        exit 0
    fi
fi

if command -v python >/dev/null 2>&1 && [[ -d "src" ]]; then
    exec env PYTHONPATH=src python -m \
        valska_hera_beam.external_tools.bayeseor.cli_report_all "$@"
fi

echo "Error: could not find valska-bayeseor-report-all, conda fallback, or local module fallback." >&2
exit 127
