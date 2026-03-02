# BayesEoR reporting workflows (ValSKA)

This page documents the `valska-bayeseor-report` post-processing workflow for completed (or partially completed) sweep directories.

It is designed to work **retroactively** on older sweeps, so you do not need to rerun BayesEoR to generate report artefacts.

Naming conventions used in this page:

- `run_id`: identifier for a sweep campaign
- `sweep_dir`: `_sweeps/<run_id>` directory containing `sweep_manifest.json`
- `run_dir`: one per-point directory listed in the sweep manifest

---

## What this command does

Given a sweep directory containing `sweep_manifest.json`, it can generate:

- sweep summary tables:
  - `sweep_report_summary.csv`
  - `sweep_report_summary.json`
- evidence comparison plots:
  - `delta_log_evidence_vs_perturb_frac.png`
  - `log_evidence_by_model_vs_perturb_frac.png`
- optional extended outputs:
  - `plot_analysis_results_signal_fit.png` (from `BeamAnalysisPlotter.plot_analysis_results`)
  - `complete_analysis_results.json` and `complete_analysis_successful.csv` (from `run_complete_bayeseor_analysis`)

By default, output files are written under:

    <sweep_dir>/report/

Plot styling conventions (for publication-quality readability):

- math variables are rendered with LaTeX-style mathtext (for example `$\ln Z$`)
- hypothesis labels use spaced names (`signal fit`, `no signal`) in legends
- in `delta_log_evidence_vs_perturb_frac.png`, points with `\Delta\ln Z > 0`
  are highlighted in red to indicate preference for a spurious detection

---

## CLI usage

Basic run (tables + default evidence plots):

    valska-bayeseor-report /path/to/_sweeps/<run_id>

Airy sweep helper can trigger this automatically after sweep preparation/submission:

  bash_scripts/valska-bayeseor-sweep-airy_diam14m-GSM_plus_GLEAM.sh --submit all --report

Use `--report-no-plots` on the helper for table-only reporting.

JSON summary payload:

    valska-bayeseor-report /path/to/_sweeps/<run_id> --json

Skip evidence plots (tables only):

    valska-bayeseor-report /path/to/_sweeps/<run_id> --no-plots

Choose evidence estimator used for ΔlnZ/Bayes factor:

    valska-bayeseor-report /path/to/_sweeps/<run_id> --evidence-source ns
    valska-bayeseor-report /path/to/_sweeps/<run_id> --evidence-source ins

Enable extended outputs:

    valska-bayeseor-report /path/to/_sweeps/<run_id> \
      --include-plot-analysis-results \
      --include-complete-analysis-table

Custom output directory:

    valska-bayeseor-report /path/to/_sweeps/<run_id> \
      --out-dir /path/to/custom_report_dir

---

## Wrapper script usage

ValSKA also provides a convenience wrapper:

    bash_scripts/valska-bayeseor-report-sweep.sh --sweep-dir /path/to/_sweeps/<run_id>

To discover available sweep directories quickly, use:

  valska-bayeseor-list-sweeps

JSON output mode (for scripting):

  valska-bayeseor-list-sweeps --json

Filter examples:

  valska-bayeseor-list-sweeps --beam airy --sky GSM_plus_GLEAM
  valska-bayeseor-list-sweeps --run-id sweep_airy_init --latest

Shell helper equivalent:

  bash_scripts/valska-list-sweeps.sh

The shell helper is a thin wrapper around `valska-bayeseor-list-sweeps`.

JSON output mode (for scripting):

  bash_scripts/valska-list-sweeps.sh --json

---

## Sweep health helpers

For quick, command-local usage examples, run:

  valska-bayeseor-list-sweeps --help
  valska-bayeseor-sweep-status --help
  valska-bayeseor-validate-sweep --help
  valska-bayeseor-sweep-audit --help

Check per-point output completeness for a sweep:

  valska-bayeseor-sweep-status /path/to/_sweeps/<run_id>

Machine-readable status payload:

  valska-bayeseor-sweep-status /path/to/_sweeps/<run_id> --json

Validate sweep integrity with exit-code semantics:

  valska-bayeseor-validate-sweep /path/to/_sweeps/<run_id>

Allow partial sweeps (at least one complete point):

  valska-bayeseor-validate-sweep /path/to/_sweeps/<run_id> --allow-partial

Require `jobs.json` for every point:

  valska-bayeseor-validate-sweep /path/to/_sweeps/<run_id> --require-jobs-json

JSON validation payload (includes `exit_code` and `failures`):

  valska-bayeseor-validate-sweep /path/to/_sweeps/<run_id> --json

Aggregate audit across discovered sweeps (list + status + validate):

  valska-bayeseor-sweep-audit

Filter and machine-readable output:

  valska-bayeseor-sweep-audit --beam airy --sky GSM_plus_GLEAM --json

Fail non-zero when any audited sweep is invalid:

  valska-bayeseor-sweep-audit --fail-on-invalid

### Wrapper defaults

The wrapper now enables by default:

- standard evidence plots/tables
- `plot_analysis_results` output
- `run_complete_bayeseor_analysis` table/json output

Opt out of extended outputs if needed:

    bash_scripts/valska-bayeseor-report-sweep.sh \
      --sweep-dir /path/to/_sweeps/<run_id> \
      --no-plot-analysis-results \
      --no-complete-analysis-table

Skip all plotting:

    bash_scripts/valska-bayeseor-report-sweep.sh \
      --sweep-dir /path/to/_sweeps/<run_id> \
      --no-plots

### Environment fallback behavior

The wrapper will:

1. use `valska-bayeseor-report` directly if available on `PATH`, else
2. fall back to `conda run -n <env> valska-bayeseor-report ...`

Set the conda env name with:

    export VALSKA_CONDA_ENV=valska

---

## Handling incomplete sweeps

Reporting is resilient to partial/incomplete points.

If required chain artefacts are missing (for example `data-.txt`), the command does **not** crash the full report. Instead, that point is marked:

- `status: "incomplete"`
- `note: "...Missing chain file..."`

Only complete points are used for computed evidence metrics and extended outputs.

---

## Recommended validation checks

After running a report:

1. confirm `rows_total` and `rows_complete` in JSON output
2. inspect `sweep_report_summary.csv` for per-point status
3. verify expected PNG files exist in the report directory
4. if using extended outputs, check:
   - `plot_analysis_results_signal_fit.png`
   - `complete_analysis_results.json`
   - `complete_analysis_successful.csv`
