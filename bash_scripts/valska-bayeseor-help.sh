#!/bin/bash
# filepath: /home/ps550/ValSKA/bash_scripts/valska-bayeseor-help.sh
#
# Wrapper for valska-bayeseor-help.
#
# Usage:
#   ./bash_scripts/valska-bayeseor-help.sh
#   ./bash_scripts/valska-bayeseor-help.sh --topic operations
#   ./bash_scripts/valska-bayeseor-help.sh --json
#
# Optional environment variable:
#   VALSKA_CONDA_ENV=<name>  (default: valska)

set -euo pipefail

VALSKA_CONDA_ENV="${VALSKA_CONDA_ENV:-valska}"

if command -v valska-bayeseor-help >/dev/null 2>&1; then
    exec valska-bayeseor-help "$@"
fi

if command -v conda >/dev/null 2>&1; then
    if conda run -n "$VALSKA_CONDA_ENV" python -m \
        valska_hera_beam.external_tools.bayeseor.cli_help "$@"; then
        exit 0
    fi
fi

if command -v python >/dev/null 2>&1 && [[ -d "src" ]]; then
    exec env PYTHONPATH=src python -m \
        valska_hera_beam.external_tools.bayeseor.cli_help "$@"
fi

echo "Error: could not find valska-bayeseor-help, conda fallback, or local module fallback." >&2
exit 127
