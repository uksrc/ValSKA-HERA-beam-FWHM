#!/bin/bash
# filepath: /home/ps550/ValSKA-HERA-beam-FWHM/bash_scripts/valska-bayeseor-sweep-achromatic_Gaussian-GLEAM.sh
#
# Submit a BayesEoR FWHM perturbation sweep for achromatic_Gaussian beam + GLEAM sky.
#
# Usage:
#   ./valska-bayeseor-sweep-achromatic_Gaussian-GLEAM.sh [--submit none|cpu|all]
#
# Examples:
#   ./valska-bayeseor-sweep-achromatic_Gaussian-GLEAM.sh              # Submits all (default)
#   ./valska-bayeseor-sweep-achromatic_Gaussian-GLEAM.sh --submit none  # Prepare only, no submission

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration (edit these as needed)
# -----------------------------------------------------------------------------
BEAM="chromatic_Gaussian"
SKY="GLEAM"
# DATA="gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5"
DATA="gsm-nside256-158.3-167.1MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5"
RUN_ID="sweep"
TEMPLATE="validation_chromatic_Gaussian.yaml"

# FWHM perturbation fractions (negative = narrower, positive = wider)
FWHM_FRACS="-0.2 -0.1 -0.05 -0.02 -0.01 0.0 0.01 0.02 0.05 0.1 0.2"

# Default submission mode (can be overridden via CLI)
SUBMIT_MODE="${1:-all}"

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------
if [[ ! "$SUBMIT_MODE" =~ ^(none|cpu|all)$ ]]; then
    echo "Error: Invalid submit mode '$SUBMIT_MODE'. Use: none, cpu, or all" >&2
    exit 1
fi

# -----------------------------------------------------------------------------
# Run sweep
# -----------------------------------------------------------------------------
echo "Starting ValSKA BayesEoR sweep..."
echo "  Beam:     $BEAM"
echo "  Sky:      $SKY"
echo "  Template: $TEMPLATE"
echo "  Run ID:   $RUN_ID"
echo "  Submit:   $SUBMIT_MODE"
echo ""

valska-bayeseor-sweep \
  --beam "$BEAM" \
  --sky "$SKY" \
  --data "$DATA" \
  --template "$TEMPLATE" \
  --run-id "$RUN_ID" \
  --fwhm-fracs $FWHM_FRACS \
  --submit "$SUBMIT_MODE"