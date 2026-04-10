#!/bin/bash
# filepath: /home/ps550/ValSKA/bash_scripts/valska-bayeseor-report-sweep.sh
#
# Generate ValSKA BayesEoR sweep report artefacts (tables + plots)
# for an already-completed sweep directory.
#
# Usage:
#   ./valska-bayeseor-report-sweep.sh --sweep-dir <path> [--evidence-source ns|ins] [--no-plots] [--out-dir <path>] [--no-plot-analysis-results] [--no-complete-analysis-table]
#
# Optional environment variable:
#   VALSKA_CONDA_ENV=<name>   (default: valska)

set -euo pipefail

SWEEP_DIR=""
EVIDENCE_SOURCE="ins"
NO_PLOTS="false"
OUT_DIR=""
INCLUDE_PLOT_ANALYSIS_RESULTS="true"
INCLUDE_COMPLETE_ANALYSIS_TABLE="true"
VALSKA_CONDA_ENV="${VALSKA_CONDA_ENV:-valska}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sweep-dir)
            SWEEP_DIR="${2:-}"
            shift 2
            ;;
        --evidence-source)
            EVIDENCE_SOURCE="${2:-}"
            shift 2
            ;;
        --no-plots)
            NO_PLOTS="true"
            shift
            ;;
        --out-dir)
            OUT_DIR="${2:-}"
            shift 2
            ;;
        --include-plot-analysis-results)
            INCLUDE_PLOT_ANALYSIS_RESULTS="true"
            shift
            ;;
        --no-plot-analysis-results)
            INCLUDE_PLOT_ANALYSIS_RESULTS="false"
            shift
            ;;
        --include-complete-analysis-table)
            INCLUDE_COMPLETE_ANALYSIS_TABLE="true"
            shift
            ;;
        --no-complete-analysis-table)
            INCLUDE_COMPLETE_ANALYSIS_TABLE="false"
            shift
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            echo "Usage: $0 --sweep-dir <path> [--evidence-source ns|ins] [--no-plots] [--out-dir <path>] [--no-plot-analysis-results] [--no-complete-analysis-table]" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$SWEEP_DIR" ]]; then
    echo "Error: --sweep-dir is required." >&2
    exit 1
fi

if [[ ! "$EVIDENCE_SOURCE" =~ ^(ns|ins)$ ]]; then
    echo "Error: --evidence-source must be 'ns' or 'ins'." >&2
    exit 1
fi

cmd=(
    "$SWEEP_DIR"
    --evidence-source "$EVIDENCE_SOURCE"
)

if [[ "$NO_PLOTS" == "true" ]]; then
    cmd+=(--no-plots)
fi

if [[ -n "$OUT_DIR" ]]; then
    cmd+=(--out-dir "$OUT_DIR")
fi

if [[ "$INCLUDE_PLOT_ANALYSIS_RESULTS" == "true" ]]; then
    cmd+=(--include-plot-analysis-results)
fi

if [[ "$INCLUDE_COMPLETE_ANALYSIS_TABLE" == "true" ]]; then
    cmd+=(--include-complete-analysis-table)
fi

if command -v valska-bayeseor-report >/dev/null 2>&1; then
    valska-bayeseor-report "${cmd[@]}"
elif command -v conda >/dev/null 2>&1; then
    conda run -n "$VALSKA_CONDA_ENV" valska-bayeseor-report "${cmd[@]}"
else
    echo "Error: Could not find 'valska-bayeseor-report' on PATH and 'conda' is unavailable for fallback." >&2
    exit 127
fi
