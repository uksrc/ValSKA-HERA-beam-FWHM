# ValSKA-HERA-beam-FWHM

**An open-source, reproducible, flexible, and extensible package for validating the sensitivity of 21-cm power spectrum forward modeling approaches to imperfect knowledge of the FWHM of the interferometric primary beam.**

## Overview

ValSKA-HERA-beam-FWHM provides a Bayesian science validation case study modelling the Hydrogen Epoch of Reionization Array (HERA) using the BayesEoR modeling framework.

The focus of this repository is **validation tooling**: enabling controlled, inspectable, and reproducible studies of how modelling assumptions (here, primary-beam FWHM uncertainty) propagate through a full 21-cm power-spectrum inference pipeline.

## Features

- **Bayesian Analysis**
  BayesEoR enables a joint Bayesian analysis of models for large-spectral-scale foreground emission and a stochastic signal from redshifted 21-cm emission emitted by neutral Hydrogen during the Epoch of Reionization (EoR).

- **Sensitivity Testing**
  This package tests the extent to which errors in beam modelling, parameterized in terms of the beam FWHM, can be tolerated without biasing the recovery of the 21-cm power spectrum.

- **Reproducible HPC Workflows**
  Explicit separation of run preparation and job submission enables resumable, auditable, and HPC-appropriate execution.

## Contents

ValSKA-HERA-beam-FWHM includes:
- Results from **BaNTER** (Bayesian Null-Test Evidence Ratio) validation of the forward modelling pipeline.
- Chain files from **BayesEoR** power-spectrum estimation analyses of mock HERA foreground validation data and full-sky (foregrounds + 21-cm signal) science data.
- Links to data artifacts and full provenance records.

## Installation

General guidance:

- Clone the repository.
- All dependencies can be installed with `conda` or `mamba` using the included `valska_env.yaml` file:

    conda env create -f valska_env.yaml

- `valska_env.yaml` is configured for **Galahad** by default.
  To install on **Azimuth**, comment out `cudatoolkit` and uncomment `cuda` in the environment file.

**Note:**
This repository provides *validation tooling and job orchestration*.
It does **not** automatically create conda environments, clone BayesEoR, or manage HPC accounts.

## BayesEoR validation workflow

This repository provides tooling to **prepare, submit, and re-run** BayesEoR analyses in a reproducible and HPC-appropriate way.
The workflow is intentionally split into two explicit stages.

### 1. Prepare a run (no execution)

Use `valska-bayeseor-prepare` to generate a self-contained *run directory* containing:

- Rendered BayesEoR configuration YAMLs
- SLURM submit scripts (CPU precompute + GPU run stages)
- A `manifest.json` capturing full provenance

Example (stable run directory, suitable for resuming):

    valska-bayeseor-prepare \
        --data /path/to/dataset.uvh5 \
        --scenario GSM_beam \
        --run-label fwhm_-1.0e-03 \
        --run-id baseline

This creates a directory of the form:

    <results_root>/bayeseor/<scenario>/<run_label>/<run_id>/

No jobs are submitted at this stage.
The run directory can be inspected, archived, copied, or re-used.

### 2. Submit a prepared run

Once a run directory exists, jobs can be submitted using:

    valska-bayeseor-submit <run_dir>

This will:
- submit the CPU precompute stage
- submit GPU stages with appropriate `afterok` dependencies
- record SLURM job IDs in `jobs.json`

You may also submit stages explicitly:

    # CPU only
    valska-bayeseor-submit <run_dir> --stage cpu

    # GPU only (after CPU has completed)
    valska-bayeseor-submit <run_dir> --stage gpu

### Resubmitting after walltime

If a job hits walltime, BayesEoR / MultiNest can resume from existing output.

To requeue cleanly without regenerating configs:

    valska-bayeseor-submit <run_dir> --stage gpu --resubmit

This archives the previous `jobs.json` (timestamped) and submits a new job, preserving a clear history of attempts.

Manual submission via `sbatch submit_*.sh` remains fully supported at all times.

## Contributing

ValSKA-HERA-beam-FWHM is an open-source project, and contributions in any form are very welcome
(e.g. new features, feature requests, bug reports, documentation improvements).

Please make contributions via issues and/or pull requests.

For questions or discussion, contact the UKSRC science validation tooling team:

- Peter Sims (PO) — ps550 [at] cam.ac.uk
- Tianyue Chen (SM) — tianyue.chen [at] manchester.ac.uk
- Quentin Gueuning — qdg20 [at] cam.ac.uk
- Ed Polehampton — edward.polehampton [at] stfc.ac.uk
- Vlad Stolyarov — vs237 [at] cam.ac.uk
