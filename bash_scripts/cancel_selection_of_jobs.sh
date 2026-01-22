#!/bin/bash
# filepath: /home/ps550/ValSKA-HERA-beam-FWHM/bash_scripts/cancel_selection_of_jobs.sh

# ==============================================================================
# Script: cancel_selection_of_jobs.sh
# Description: Cancels a range of SLURM jobs using scancel
# Usage: ./cancel_selection_of_jobs.sh [start_job_id] [end_job_id]
#        Or edit the default values below and run without arguments
# ==============================================================================

set -euo pipefail

# Default job ID range (modify these as needed)
DEFAULT_START_JOB=180
DEFAULT_END_JOB=207

# Parse command line arguments or use defaults
START_JOB="${1:-$DEFAULT_START_JOB}"
END_JOB="${2:-$DEFAULT_END_JOB}"

# Validate inputs are integers
if ! [[ "$START_JOB" =~ ^[0-9]+$ ]] || ! [[ "$END_JOB" =~ ^[0-9]+$ ]]; then
    echo "Error: Job IDs must be positive integers" >&2
    echo "Usage: $0 [start_job_id] [end_job_id]" >&2
    exit 1
fi

# Validate range
if [[ "$START_JOB" -gt "$END_JOB" ]]; then
    echo "Error: Start job ID ($START_JOB) must be <= end job ID ($END_JOB)" >&2
    exit 1
fi

# Calculate number of jobs to cancel
NUM_JOBS=$((END_JOB - START_JOB + 1))

echo "=============================================="
echo "SLURM Job Cancellation Script"
echo "=============================================="
echo "Job ID range: $START_JOB to $END_JOB"
echo "Total jobs to cancel: $NUM_JOBS"
echo "=============================================="

# Confirmation prompt
read -p "Are you sure you want to cancel these jobs? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operation cancelled by user."
    exit 0
fi

# Cancel jobs
echo "Cancelling jobs..."
CANCELLED=0
FAILED=0

for job_id in $(seq "$START_JOB" "$END_JOB"); do
    if scancel "$job_id" 2>/dev/null; then
        echo "  Cancelled job $job_id"
        ((CANCELLED++))
    else
        echo "  Failed to cancel job $job_id (may not exist or already completed)"
        ((FAILED++))
    fi
done

echo "=============================================="
echo "Summary:"
echo "  Successfully cancelled: $CANCELLED"
echo "  Failed/skipped: $FAILED"
echo "=============================================="