# BayesEoR CLI workflows (ValSKA)

This page is a practical, “example gallery”-style guide to running BayesEoR validation workflows using ValSKA.

It is written to be:
- copy/paste friendly (commands shown as indented code blocks)
- HPC-friendly (explicit about dry-runs, SLURM submission, and dependencies)
- reproducible (paths, templates, and variants recorded in manifests)

If you are new, start with **Quick Start**. If you are iterating on a validation campaign, use **Detailed examples**.

---

## Contents

- Quick Start
  - 1) Prepare a single run kit (no jobs submitted)
  - 2) Submit CPU stage
  - 3) Submit GPU stage (after CPU completes)
  - 4) Prepare & submit a sweep
- Concepts
  - Beam / sky taxonomy (directory layout)
  - Template + variant concept (collision-free template differences)
  - What gets created where
- Lifecycle diagram
- Detailed examples
  - A) Prepare (dry-run vs real)
  - B) Sweep (dry-run vs real)
  - C) Submitting with dependency handling (CPU → GPU)
  - D) Resubmitting (GPU stage) and job records
  - E) Submit CPU across sweep points
  - F) Submit GPU across sweep points (after CPU)
  - G) Submit CPU+GPU together (fresh sweep)
  - H) Advanced: per-point submission with valska-bayeseor-submit
  - I) Monitoring jobs
  - J) Post-processing reports (valska-bayeseor-report)
  - K) Sweep health/status checks
  - L) Aggregate sweep audit
  - M) Backwards compatibility: deprecated --scenario

---

## Quick Start

For sweep post-processing and retroactive report generation, see:

- [BayesEoR reporting workflows](./bayeseor_reporting.md)

For operational commands (resume, batch report, comparison, cleanup), see:

- [BayesEoR operations CLI](./bayeseor_operations.md)

### CLI quick reference

| Command | Purpose | Detailed docs |
|---|---|---|
| `valska-bayeseor-prepare` | Prepare one run directory and artefacts | This page |
| `valska-bayeseor-submit` | Submit CPU/GPU stages for one prepared run | This page |
| `valska-bayeseor-sweep` | Prepare and/or submit sweep points | This page |
| `valska-bayeseor-help` | Print command index and common workflows | [bayeseor_operations](./bayeseor_operations.md) |
| `valska-bayeseor-report` | Generate report tables/plots for one sweep | [bayeseor_reporting](./bayeseor_reporting.md) |
| `valska-bayeseor-list-sweeps` | Discover available sweep directories | [bayeseor_reporting](./bayeseor_reporting.md) |
| `valska-bayeseor-sweep-status` | Inspect per-point completeness for one sweep | [bayeseor_reporting](./bayeseor_reporting.md) |
| `valska-bayeseor-validate-sweep` | Validate sweep integrity with exit-code semantics | [bayeseor_reporting](./bayeseor_reporting.md) |
| `valska-bayeseor-sweep-audit` | Aggregate discovery + status + validation | [bayeseor_reporting](./bayeseor_reporting.md) |
| `valska-bayeseor-resume` | Generate exact submit commands for incomplete points | [bayeseor_operations](./bayeseor_operations.md) |
| `valska-bayeseor-report-all` | Batch-generate reports across discovered sweeps | [bayeseor_operations](./bayeseor_operations.md) |
| `valska-bayeseor-compare-sweeps` | Compare metrics between two sweep summaries | [bayeseor_operations](./bayeseor_operations.md) |
| `valska-bayeseor-cleanup` | Safe cleanup workflow (dry-run by default) | [bayeseor_operations](./bayeseor_operations.md) |

### Which command should I use?

- Need to create run inputs/scripts for a single point? → `valska-bayeseor-prepare`
- Need to submit stages for one prepared run dir? → `valska-bayeseor-submit`
- Need to prepare/submit multiple perturbation points together? → `valska-bayeseor-sweep`
- Need a quick command map before you start? → `valska-bayeseor-help`
- Need to inspect one sweep health quickly? → `valska-bayeseor-sweep-status`
- Need pass/fail validation semantics for one sweep? → `valska-bayeseor-validate-sweep`
- Need campaign-wide health and validation overview? → `valska-bayeseor-sweep-audit`
- Need restart suggestions for incomplete points? → `valska-bayeseor-resume`
- Need reports for one sweep? → `valska-bayeseor-report`
- Need reports for many sweeps? → `valska-bayeseor-report-all`
- Need side-by-side metric comparison between two sweeps? → `valska-bayeseor-compare-sweeps`
- Need maintenance cleanup (dry-run first)? → `valska-bayeseor-cleanup`

For command-local examples of helper CLIs, run each command with `--help`.

Assumptions:
- You have configured `config/runtime_paths.yaml` (see your repo’s example).
- You have a BayesEoR checkout and conda env accessible to batch jobs (also configured in runtime_paths.yaml).
- You are on a SLURM cluster (e.g. Galahad).

Replace:
- `achromatic_Gaussian` with your beam model label
- `GLEAM` with your sky model label
- `...uvh5` with your dataset
- `RUN_ID` / `SWEEP_ID` with something meaningful

### 1) Prepare a single run kit (no jobs submitted)

This creates a run directory containing:
- BayesEoR config YAML(s)
- SLURM submit scripts for CPU and GPU stages
- a manifest recording provenance and resolved paths

    valska-bayeseor-prepare \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id RUN_ID \
      --fwhm-perturb-frac 0.01

If you want to see what would happen without creating files:

    valska-bayeseor-prepare \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id RUN_ID \
      --fwhm-perturb-frac 0.01 \
      --dry-run

### 2) Submit CPU stage

If you are using the submit CLI:

    valska-bayeseor-submit /path/to/run_dir --stage cpu

Or manually (inside the run_dir output from prepare):

    sbatch /path/to/run_dir/submit_cpu_precompute.sh

### 3) Submit GPU stage (after CPU completes)

GPU stage submissions should depend on the CPU job finishing successfully (`afterok:<CPU_JOBID>`).
If you submitted CPU using `valska-bayeseor-submit`, it records the CPU job id in `jobs.json`,
which GPU submission can then use.

Using the submit CLI:

    valska-bayeseor-submit /path/to/run_dir --stage gpu

Or manually:

    sbatch --dependency=afterok:<CPU_JOBID> /path/to/run_dir/submit_signal_fit_gpu_run.sh
    sbatch --dependency=afterok:<CPU_JOBID> /path/to/run_dir/submit_no_signal_gpu_run.sh

### 4) Prepare & submit a sweep

A sweep prepares N run dirs (one per FWHM perturbation) and can optionally submit CPU/GPU stages
across all points.

Prepare only (no submission):

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id SWEEP_ID \
      --fwhm-fracs 0.01 0.0 \
      --submit none

Submit CPU stage across all points:

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id SWEEP_ID \
      --fwhm-fracs 0.01 0.0 \
      --submit cpu

Submit GPU stage across all points (after CPU job IDs have been recorded in each point’s `jobs.json`):

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id SWEEP_ID \
      --fwhm-fracs 0.01 0.0 \
      --submit gpu

Dry-run submission (show `sbatch` commands but do not submit):

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id SWEEP_ID \
      --fwhm-fracs 0.01 0.0 \
      --submit cpu \
      --submit-dry-run

---

## Concepts

### Beam / sky taxonomy (directory layout)

We organise results by the two “observation-defining” axes:

- `beam_model`: instrument / beam model label (e.g. `achromatic_Gaussian`, `chromatic_Gaussian`, `airy`)
- `sky_model`: sky model label (e.g. `GLEAM`, `GSM`, `GLEAM_plus_GSM`)

This keeps campaigns predictable when you explore multiple sky models and multiple beam models.

### Template + variant concept (collision-free template differences)

Many BayesEoR runs differ only by template-level settings (chromatic vs achromatic, alternate priors, etc).
To avoid collisions, we include a `<variant>` directory level.

- If you do not specify `--variant`, it is derived from the template filename stem by removing the first `_template`.

Examples:
- `validation_v1d0_template.yaml`            → `validation_v1d0`
- `validation_v1d0_template_achromatic.yaml` → `validation_v1d0_achromatic`
- `validation_achromatic_Gaussian.yaml`      → `validation_achromatic_Gaussian`

You can override the auto-derived value with `--variant`.

### What gets created where

Canonical single-run directory:

    <results_root>/bayeseor/<beam_model>/<sky_model>/<variant>/<run_label>/<run_id>[/<UTCSTAMP>]

Canonical sweep root and points:

    <results_root>/bayeseor/<beam_model>/<sky_model>/_sweeps/<sweep_id>/<variant>/<run_label>[/<UTCSTAMP>]

Notes:
- `<run_label>` is typically `fwhm_<value>` (e.g. `fwhm_1.0e-02`) and is auto-generated from FWHM frac.
- `--unique` appends a UTC timestamp suffix (useful for one-off runs; usually not recommended for resumable sweeps).

---

## Lifecycle diagram

This is the “mental model” for the typical workflow.

    +---------------------------+
    | Choose beam + sky + data  |
    | Choose template (optional)|
    +-------------+-------------+
                  |
                  v
    +---------------------------+
    | PREPARE (per run)         |
    | valska-bayeseor-prepare   |
    | - writes run_dir          |
    | - config_*.yaml           |
    | - submit_*.sh             |
    | - manifest.json           |
    +-------------+-------------+
                  |
                  v
    +---------------------------+
    | CPU stage (precompute)    |
    | valska-bayeseor-submit    |
    |   --stage cpu             |
    | or sbatch submit_cpu*.sh  |
    | - records CPU job id      |
    |   into jobs.json          |
    +-------------+-------------+
                  |
                  v
    +---------------------------+
    | GPU stage (run analyses)  |
    | valska-bayeseor-submit    |
    |   --stage gpu             |
    | - uses afterok:<CPU_JOBID>|
    | - submits signal/no-signal|
    | - records GPU job ids     |
    +---------------------------+

Sweeps are a thin wrapper that repeats PREPARE across multiple FWHM fractions:

    valska-bayeseor-sweep --submit none   (prepare all points)
    valska-bayeseor-sweep --submit cpu    (submit CPU across points)
    valska-bayeseor-sweep --submit gpu    (submit GPU across points; needs CPU job ids)
    valska-bayeseor-sweep --submit all    (submit CPU+GPU in one go per point)

---

## Detailed examples

The examples below are intentionally explicit, and many include abridged output snippets.

### A) Prepare (dry-run)

    valska-bayeseor-prepare \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id test_prepare1 \
      --fwhm-perturb-frac 0.01 \
      --dry-run

Example output (abridged):

    [DRY RUN] Prepare would be executed with:
      results_root:       /share/.../validation_results/UKSRC
      beam_model:         achromatic_Gaussian
      sky_model:          GLEAM
      run_id:             test_prepare1
      run_label:          fwhm_1.0e-02
      template:           .../templates/validation_achromatic_Gaussian.yaml
      variant:            validation_achromatic_Gaussian
      data:               /share/.../gsm_plus_gleam...uvh5
      run_dir (preview):  /share/.../bayeseor/achromatic_Gaussian/GLEAM/validation_achromatic_Gaussian/fwhm_1.0e-02/test_prepare1
      ...
    [DRY RUN] No files will be created.

### B) Prepare (real)

    valska-bayeseor-prepare \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id test_prepare1 \
      --fwhm-perturb-frac 0.01

Example output (abridged):

    Run prepared:
      run_dir:      /share/.../bayeseor/achromatic_Gaussian/GLEAM/validation_achromatic_Gaussian/fwhm_1.0e-02/test_prepare1
      manifest:     /share/.../manifest.json
      beam_model:   achromatic_Gaussian
      sky_model:    GLEAM
      variant:      validation_achromatic_Gaussian
      run_label:    fwhm_1.0e-02
      run_id:       test_prepare1

    Next steps:
      Option A) Submit via ValSKA (recommended):
        valska-bayeseor-submit /share/.../test_prepare1 --stage cpu
        valska-bayeseor-submit /share/.../test_prepare1 --stage gpu
      Option B) Manual submission:
        sbatch /share/.../submit_cpu_precompute.sh
        sbatch /share/.../submit_signal_fit_gpu_run.sh
        sbatch /share/.../submit_no_signal_gpu_run.sh

### C) Sweep (dry-run with point directories)

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 0.0 \
      --dry-run

Example output (abridged):

    [DRY RUN] Sweep would be executed with:
      sweep_dir: /share/.../bayeseor/achromatic_Gaussian/GLEAM/_sweeps/sweep_test2
      variant:   validation_achromatic_Gaussian
      ...

    [DRY RUN] Points:
      +0.010  fwhm_1.0e-02  ->  /share/.../_sweeps/sweep_test2/validation_achromatic_Gaussian/fwhm_1.0e-02
      +0.000  fwhm_0.0e+00  ->  /share/.../_sweeps/sweep_test2/validation_achromatic_Gaussian/fwhm_0.0e+00

### D) Sweep (prepare only)

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 0.0 \
      --submit none

This writes:
- sweep manifest: `.../_sweeps/<sweep_id>/sweep_manifest.json`
- per-point run dirs containing `manifest.json`, configs, and SLURM scripts

### E) Submit CPU across sweep points

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 0.0 \
      --submit cpu

Typical output includes a “Submission summary” listing the sbatch calls per point.
It should also record job ids into each point’s `jobs.json` (real submit).

To preview the sbatch commands without submitting:

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 0.0 \
      --submit cpu \
      --submit-dry-run

### F) Submit GPU across sweep points (after CPU)

GPU-only submission needs a dependency job id per point (typically from that point’s `jobs.json`).

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 0.0 \
      --submit gpu

If you attempt GPU submission before CPU job ids exist, ValSKA should report an error explaining
you must either:
- submit CPU in the same invocation (`--submit all`), or
- pass `--depend-afterok <JOBID>` (advanced), or
- ensure `jobs.json` exists with a recorded CPU job id

Dry-run GPU submission (show commands, no jobs submitted):

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 0.0 \
      --submit gpu \
      --submit-dry-run

Example output (abridged; dependency read from jobs.json):

    sbatch --dependency=afterok:<CPU_JOBID> .../submit_signal_fit_gpu_run.sh
    sbatch --dependency=afterok:<CPU_JOBID> .../submit_no_signal_gpu_run.sh

### G) Submit CPU+GPU together (fresh sweep)

If you want “one command per point” orchestration (CPU then GPU dependent), use:

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 0.0 \
      --submit all

This is convenient for “fresh” runs, but some teams prefer splitting CPU and GPU stages into
separate invocations for clearer control.

### H) Advanced: per-point submission with valska-bayeseor-submit

Sometimes you only want to submit a subset of points or a single point, especially when testing.

Example: submit GPU for just one perturbation fraction (assuming CPU already submitted and recorded):

    valska-bayeseor-sweep \
      --beam achromatic_Gaussian \
      --sky GLEAM \
      --data gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1_quentin.uvh5 \
      --run-id sweep_test2 \
      --fwhm-fracs 0.01 \
      --submit gpu

Or, if you know the run_dir explicitly:

    valska-bayeseor-submit /share/.../_sweeps/sweep_test2/validation_achromatic_Gaussian/fwhm_1.0e-02 --stage gpu

### I) Monitoring jobs
Common SLURM checks:

    squeue -u $USER
    sacct -j <JOBID> --format=JobID,JobName,State,Elapsed,ExitCode
    tail -n 200 /path/to/run_dir/slurm-<JOBID>.out

ValSKA also records submission information into:
- per-point `jobs.json`
- sweep-level `sweep_manifest.json` (including submit results)

### J) Post-processing reports (tables + plots)

After sweep jobs complete (or partially complete), generate report artefacts with:

    valska-bayeseor-report /path/to/_sweeps/<run_id>

To include extended outputs (`plot_analysis_results` and `run_complete_bayeseor_analysis` table/json):

    valska-bayeseor-report /path/to/_sweeps/<run_id> \
      --include-plot-analysis-results \
      --include-complete-analysis-table

Wrapper equivalent (extended outputs enabled by default):

    bash_scripts/valska-bayeseor-report-sweep.sh --sweep-dir /path/to/_sweeps/<run_id>

Airy helper convenience (prepare/submit sweep and auto-run reporting at the end):

  bash_scripts/valska-bayeseor-sweep-airy_diam14m-GSM_plus_GLEAM.sh --submit all --report

Skip plot generation when auto-reporting:

  bash_scripts/valska-bayeseor-sweep-airy_diam14m-GSM_plus_GLEAM.sh --submit all --report-no-plots

For full reporting options and failure-handling behavior, see:

- [BayesEoR reporting workflows](./bayeseor_reporting.md)

### K) Sweep health/status checks

Inspect a sweep and summarize point completeness:

    valska-bayeseor-sweep-status /path/to/_sweeps/SWEEP_ID

JSON mode (scripting/automation):

    valska-bayeseor-sweep-status /path/to/_sweeps/SWEEP_ID --json

Validate and fail non-zero for incomplete sweeps:

    valska-bayeseor-validate-sweep /path/to/_sweeps/SWEEP_ID

If partial completion is acceptable:

    valska-bayeseor-validate-sweep /path/to/_sweeps/SWEEP_ID --allow-partial

If you also require `jobs.json` per point:

    valska-bayeseor-validate-sweep /path/to/_sweeps/SWEEP_ID --require-jobs-json

### L) Aggregate sweep audit

Run one command that discovers sweeps and evaluates status + validation:

  valska-bayeseor-sweep-audit

Apply filters and output JSON:

  valska-bayeseor-sweep-audit --beam airy --sky GSM_plus_GLEAM --json

Use non-zero exit if any audited sweep is invalid:

  valska-bayeseor-sweep-audit --fail-on-invalid

### M) Backwards compatibility: deprecated --scenario

Older scripts used `--scenario` as a single label that mixed multiple concepts.

ValSKA now prefers `--beam` and `--sky` explicitly.

If you must use `--scenario`, it is deprecated and must be unambiguous:

    --scenario <beam>/<sky>
    --scenario <beam>__<sky>

Examples:

    valska-bayeseor-sweep \
      --scenario achromatic_Gaussian/GLEAM \
      --data ...uvh5 \
      --run-id sweep_oldstyle \
      --fwhm-fracs 0.01 0.0 \
      --submit none

Ambiguous older patterns like `GLEAM_beam` are rejected to prevent silent misrouting.

---

## Notes for UKSRC users

- Keep beam/sky labels stable across campaigns. Your analysis notebooks, plots, and archiving will thank you.
- Prefer `--submit-dry-run` before real submissions when testing new templates or SLURM settings.
- For large sweeps, consider committing a standard `bayeseor.sweep.fwhm_fracs` set in runtime_paths.yaml
  and only override with `--fwhm-fracs` for special experiments.
- If you run into walltime, MultiNest is typically resumable; ValSKA supports resubmission patterns
  (see `--resubmit` in your CLI help).

---

## Related files (in this repo)

- `src/valska_hera_beam/external_tools/bayeseor/cli_prepare.py`
- `src/valska_hera_beam/external_tools/bayeseor/cli_sweep.py`
- `src/valska_hera_beam/external_tools/bayeseor/cli_submit.py`
- `src/valska_hera_beam/external_tools/bayeseor/setup.py`
- `src/valska_hera_beam/external_tools/bayeseor/sweep.py`
- `src/valska_hera_beam/external_tools/bayeseor/submit.py`
- `config/runtime_paths.yaml`
- `bash_scripts/valska-bayeseor-sweep-airy_diam14m-GSM_plus_GLEAM.sh`

