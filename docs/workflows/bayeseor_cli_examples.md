# ValSKA BayesEoR CLI Examples

> ## Recommended workflow (quick start)
>
> For most validation tasks, we recommend the following pattern:
>
> 1. **Prepare runs explicitly** using `valska-bayeseor-prepare` or `valska-bayeseor-sweep`
>    - Use **stable run directories** (avoid `--unique`) for resumability
>    - Inspect generated configs and SLURM scripts before submission
>
> 2. **Submit via ValSKA** using `valska-bayeseor-submit`
>    - Submit CPU and GPU stages separately or together
>    - Let ValSKA record job IDs in `jobs.json`
>
> 3. **Resubmit GPU jobs as needed**
>    - Use `--resubmit` if GPU jobs hit walltime
>    - MultiNest will resume from existing output
>
> 4. **Use sweeps for validation**
>    - Encode physics parameters (e.g. FWHM perturbations) in `run_label`
>    - Encode experiments / batches in `run_id`
>    - Track sweep-wide provenance via `sweep_manifest.json`
>
> This workflow prioritises **inspectability, reproducibility, and safe resumption**
> over opaque automation.

---

This document provides a **gallery-style collection of tested, copy-pasteable CLI workflows**
for preparing, submitting, and sweeping BayesEoR validation runs using ValSKA.

The examples are organised by **intent**, not by exhaustive argument reference.
They are designed to answer:

  “What does a *reasonable*, *reproducible*, *resumable* workflow look like?”

All commands assume that:
- ValSKA is installed in an active environment
- BayesEoR is installed and configured via `runtime_paths.yaml` or CLI flags
- SLURM is available on the target system

---

## 1. Prepare a single resumable run (no submission)

This prepares a BayesEoR run directory with rendered configs and SLURM scripts,
but does not submit any jobs.

This is the safest and most inspectable workflow.

    valska-bayeseor-prepare \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-label fwhm_0.0 \
      --run-id default

Resulting directory structure:

    <results_root>/bayeseor/GLEAM_beam/fwhm_0.0/default/

This directory can be reused to resume runs (e.g. after walltime).

---

## 2. Prepare a unique run (parameter sweeps, experiments)

Use `--unique` when you want to avoid collisions and do not intend to resume
into the same directory.

    valska-bayeseor-prepare \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-label fwhm_1.0e-02 \
      --run-id sweep_test \
      --unique

This appends a UTC timestamp under the run directory.

---

## 3. Dry-run preparation (no filesystem changes)

Useful to verify directory layout, template resolution, and defaults.

    valska-bayeseor-prepare \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-id test \
      --fwhm-perturb-frac 0.01 \
      --dry-run

Nothing is written; all resolved paths are printed.

---

## 4. Using `data.root` to shorten `--data` paths

If your datasets live under a common directory, you can configure a default
data root in `config/runtime_paths.yaml`:

    data:
      root: /share/nas-0-3/psims/data/uvh5

Once this is set, `--data` may be given as a **relative path**:

    valska-bayeseor-prepare \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38.uvh5 \
      --scenario GLEAM_beam \
      --run-id sweep_v1 \
      --fwhm-perturb-frac 1e-1

ValSKA will resolve this internally as:

    <data.root>/gsm_plus_gleam-158.30-167.10-MHz-nf-38.uvh5

The fully resolved absolute path is recorded in:
- `manifest.json`
- `sweep_manifest.json`
- SLURM job logs

If `--data` is provided as an **absolute path**, it is used as-is and
`data.root` is ignored.

---

## 5. Manual submission (inspect scripts, then sbatch)

After preparation, you can submit manually using `sbatch`.

    cd <run_dir>

    sbatch submit_cpu_precompute.sh
    sbatch submit_signal_fit_gpu_run.sh
    sbatch submit_no_signal_gpu_run.sh

This mode is:
- fully supported
- maximally inspectable
- ideal for debugging SLURM behaviour

---

## 6. ValSKA-managed submission (recommended)

ValSKA can submit prepared runs and record job IDs in `jobs.json`.

### 6.1 Submit CPU stage only

    valska-bayeseor-submit <run_dir> --stage cpu

This records the CPU job ID and is safe to run multiple times with `--resubmit`.

---

### 6.2 Submit GPU stage only (after CPU)

If CPU has already been submitted (or is still running):

    valska-bayeseor-submit <run_dir> --stage gpu

GPU jobs are submitted with an `afterok` dependency on the recorded CPU job ID.

---

### 6.3 Submit all stages at once

    valska-bayeseor-submit <run_dir> --stage all

CPU is submitted first; GPU jobs depend on it automatically.

---

### 6.4 Dry-run submission (print sbatch commands)

    valska-bayeseor-submit <run_dir> --stage all --dry-run

No jobs are submitted; commands are printed.

---

## 7. Resubmitting jobs (walltime, failures)

If a job hits walltime, MultiNest can resume safely.

### 7.1 GPU-only resubmission

    valska-bayeseor-submit <run_dir> --stage gpu --resubmit

This:
- archives the existing `jobs.json`
- requeues GPU jobs
- leaves CPU artefacts untouched

---

### 7.2 Full resubmission

    valska-bayeseor-submit <run_dir> --stage all --resubmit

Both CPU and GPU jobs are requeued.

---

## 8. FWHM validation sweeps (core use case)

Sweeps prepare *multiple independent run directories*, one per FWHM perturbation,
and write a single `sweep_manifest.json` for provenance.

---

### 8.1 Standard 9-point FWHM sweep (prepare only)

    valska-bayeseor-sweep \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-id sweep_v1 \
      --fwhm-fracs -0.10 -0.05 -0.02 -0.01 0.0 0.01 0.02 0.05 0.10

Directories created:

    .../GLEAM_beam/fwhm_-1.0e-01/sweep_v1/
    .../GLEAM_beam/fwhm_-5.0e-02/sweep_v1/
    ...
    .../GLEAM_beam/fwhm_1.0e-01/sweep_v1/

A sweep manifest is written under:

    <results_root>/bayeseor/GLEAM_beam/_sweeps/sweep_v1/sweep_manifest.json

---

### 8.2 Narrow sweep (quick smoke test)

    valska-bayeseor-sweep \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-id sweep_smoke_test \
      --fwhm-fracs -0.01 0.0 0.01 \
      --dry-run

Useful when testing templates or SLURM settings.

---

### 8.3 File-driven sweep

Create a file, e.g. `config/fwhm_fracs.txt`:

    # Standard FWHM sweep
    -0.10
    -0.05
    -0.02
    -0.01
    0.0
    0.01
    0.02
    0.05
    0.10

Then run:

    valska-bayeseor-sweep \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-id sweep_v1 \
      --fwhm-fracs-file config/fwhm_fracs.txt

---

### 8.4 Prepare and submit the entire sweep

    valska-bayeseor-sweep \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-id sweep_v1 \
      --fwhm-fracs -0.10 -0.05 -0.02 -0.01 0.0 0.01 0.02 0.05 0.10 \
      --submit all

Each sweep point is submitted independently with its own CPU → GPU dependency chain.

---

### 8.5 GPU-only resubmission across a sweep

If CPU stages already completed:

    valska-bayeseor-sweep \
      --data /path/to/data.uvh5 \
      --scenario GLEAM_beam \
      --run-id sweep_v1 \
      --fwhm-fracs -0.10 -0.05 -0.02 -0.01 0.0 0.01 0.02 0.05 0.10 \
      --submit gpu \
      --resubmit

This is the recommended pattern when GPU jobs hit walltime.

---

## 9. Naming conventions and directory layout

ValSKA uses two distinct naming axes:

- `run_label` → **physics parameter value**
  (e.g. `fwhm_-1.0e-02`)
- `run_id` → **experiment or sweep identifier**
  (e.g. `sweep_v1`, `jan2026_test`)

This separation allows:
- clean grouping of related runs
- safe repetition with updated templates or priors
- unambiguous provenance tracking

---

## 10. Debugging and inspection tips

- Use `--dry-run` aggressively
- Inspect generated SLURM scripts before submission
- Check `jobs.json` to understand submission state
- SLURM environment variables are printed at job start
- All logs are written inside each run directory

---

## Summary

This document is intended to be:
- practical
- explicit
- stable over time

If an example here stops working, that indicates a **regression** or **API break**
that should be addressed.

For questions or proposed additions, open an issue or extend this document
with another concrete, tested example.
