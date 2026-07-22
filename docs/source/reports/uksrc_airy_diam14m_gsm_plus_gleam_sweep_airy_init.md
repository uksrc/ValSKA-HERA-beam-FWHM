# UKSRC Airy Beam BayesEoR Validation Report: airy_diam14m / GSM_plus_GLEAM / sweep_airy_v3

> **Data provenance warning (2026-07-22):** the input mock-visibility data used throughout this
> sweep was independently confirmed to be simulated with a **Gaussian** truth beam
> (`hex-37-14.6m-gauss-fwhm9.3.yml`), not an Airy beam, despite the `airy_diam14m` naming
> everywhere in this report. As a result, the previously stated plus-or-minus 2 per cent
> `antenna_diameter` accuracy specification is **not supported** and has been withdrawn; the
> numerical results below are retained as valid computational outputs but are reinterpreted as an
> Airy-model-vs-Gaussian-truth mismatch test, not an Airy-vs-Airy diameter-tolerance test. See
> [Appendix H](#appendix-h-data-provenance-note) for the full finding.

## Contents

- [Report Metadata](#report-metadata)
- [Executive Summary](#executive-summary)
- [Scope](#scope)
- [Evidence Diagnostics](#evidence-diagnostics)
- [Complete-Analysis Summary](#complete-analysis-summary)
- [Power-Spectrum and Posterior Diagnostics](#power-spectrum-and-posterior-diagnostics)
- [Limitations](#limitations)
- [Conclusions](#conclusions)
- [Appendix A: Inputs](#appendix-a-inputs)
- [Appendix B: Reproducibility Commands](#appendix-b-reproducibility-commands)
- [Appendix C: Campaign Completeness](#appendix-c-campaign-completeness)
- [Appendix D: Assumptions](#appendix-d-assumptions)
- [Appendix E: Artefact Register](#appendix-e-artefact-register)
- [Appendix F: Review Checklist](#appendix-f-review-checklist)
- [Appendix G: Limitations](#appendix-g-limitations)
- [Appendix H: Data Provenance Note](#appendix-h-data-provenance-note)

## Report Metadata

| Field | Value |
| --- | --- |
| Report title | UKSRC Airy beam BayesEoR validation report for `airy_diam14m` with `GSM_plus_GLEAM` |
| Campaign identifier | `sweep_airy_v3` (v2 campaign; originally drafted against `sweep_airy_init`, see [Appendix H](#appendix-h-data-provenance-note)) |
| Beam model | `airy_diam14m` |
| Sky model | `GSM_plus_GLEAM` |
| Validation target | Determine where the BayesEoR null test passes across the tested `antenna_diameter` sweep. **Originally intended** to use that pass window to set a provisional instrument-modelling accuracy specification for the Airy beam; this use is withdrawn, see the provenance warning above and [Appendix H](#appendix-h-data-provenance-note) |
| Report owner | UKSRC Science Enabling - Science Validation Tooling; P. Sims |
| Report date | 2026-04-25 (data refreshed to the v2 campaign 2026-07-15; see [Appendix H](#appendix-h-data-provenance-note)) |
| ValSKA branch or commit | `validation-report-drafts` @ `b529253` (original draft); refreshed against `validation-report-drafts` @ `ff7d999` |
| Report-generation environment versions | Python 3.12.12; `bayeseor` (report/plotting package) 1.1.1.dev126+g00f53dd3a; `valska` 0.1.1.dev310+gec8c89478 — the environment used to run `valska-bayeseor-report`, distinct from the BayesEoR analysis version below |
| BayesEoR analysis version (historical, `sweep_airy_init`) | `2.0.1.dev22+g3f5b6cd2f` (from each run's `output/{signal_fit,no_signal}/.../version.txt`, uniform across all 11 points) |
| BayesEoR analysis version (v2, `sweep_airy_v3`) | `2.0.1.dev31+g96e0d7db5` (uniform across all 11 points; 9 development commits ahead of the historical run — see [Appendix H](#appendix-h-data-provenance-note)) |
| Report status | `draft` |

## Executive Summary

This report assesses the UKSRC Airy beam BayesEoR validation sweep `sweep_airy_v3` (the v2 campaign), which perturbs the BayesEoR forward model's assumed `antenna_diameter` for the `airy_diam14m` beam with the `GSM_plus_GLEAM` sky model. The report was originally drafted against the historical campaign `sweep_airy_init`; see [Appendix H](#appendix-h-data-provenance-note) for that history and for why this file keeps the `sweep_airy_init` filename and asset-directory slug. All 11 sweep points completed successfully according to `sweep_report_summary.json`, and all 11 signal-fit versus no-signal pairings were processed successfully according to `complete_analysis_results.json`.

**The campaign's original purpose — using the null-test pass window to set an Airy antenna-diameter accuracy specification — is not achievable with this data.** A `valska-data-preflight` scan of `UKSRC_val_mock_vis` on 2026-07-20, independently confirmed against the file's own `pyuvsim` history via `h5py`, found that the mock visibility dataset used at every point in this sweep (`gsm_plus_gleam-...-airy_quentin.uvh5`) was in fact simulated against the telescope config `hex-37-14.6m-gauss-fwhm9.3.yml` — a **Gaussian** truth beam — not an Airy beam. The `antenna_diameter` parameter varied across the 11 sweep points is therefore only a property of the BayesEoR Airy *forward model*; the simulated data itself never changed and was never Airy. See [Appendix H](#appendix-h-data-provenance-note) for the full finding.

Reinterpreted in light of this, the sweep instead shows: the null test passes when the BayesEoR forward model assumes an `airy_diam14m` beam within -2 per cent to +2 per cent of its nominal diameter, and fails once the assumed diameter departs by 5 per cent or more, **when the data being analysed actually has a Gaussian truth beam of comparable nominal size**. This characterises how well an Airy model of a given diameter statistically mimics a fixed Gaussian beam under this pipeline — a model-family degeneracy result — not the sensitivity of an Airy null test to genuine Airy-diameter error. It cannot be used to set an Airy antenna-diameter accuracy specification; doing so would require rerunning this sweep against mock data with a confirmed Airy truth beam.

Inputs, reproducibility commands, campaign completeness, and assumptions are recorded in [Appendices A-D](#appendix-a-inputs).

## Scope

The campaign tests how sensitive the BayesEoR null-test outcome is to perturbations in the BayesEoR forward model's assumed `airy_diam14m` antenna diameter, analysing the fixed `GSM_plus_GLEAM` mock visibility data recorded in the sweep manifest. The original scientific objective was to identify the perturbation range over which the null test remains consistent with the no-signal hypothesis and to use that pass range to inform an instrument-modelling accuracy specification for the Airy beam.

**That objective is not achievable with the current data.** As detailed in [Appendix H](#appendix-h-data-provenance-note), the mock visibility data analysed throughout this sweep was independently confirmed to be simulated with a Gaussian truth beam, not an Airy beam. Only the BayesEoR forward model's assumed diameter varies across the 11 points; the underlying data does not. This report therefore reframes the sweep as a test of Airy-forward-model-versus-Gaussian-truth mismatch tolerance under this pipeline, and does not use it to set an Airy antenna-diameter accuracy specification.

The component under test is the BayesEoR evidence response to the beam-model perturbation parameter `antenna_diameter`. The sweep samples 11 perturbations from -20 per cent to +20 per cent, with finer spacing around the nominal model.

The decision enabled by this report is limited to characterising where this model-mismatch null test passes and fails; it does not, on its own, support defining an Airy antenna-diameter accuracy specification. Doing so would require rerunning an equivalent sweep against mock data with a confirmed Airy truth beam.

## Evidence Diagnostics

![Delta log evidence versus antenna-diameter perturbation fraction for the UKSRC Airy beam sweep](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/delta_log_evidence_vs_perturb_frac.png)

![Signal-fit and no-signal log evidences versus antenna-diameter perturbation fraction for the UKSRC Airy beam sweep](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/log_evidence_by_model_vs_perturb_frac.png)

*Figures 1 and 2. Top panel: delta log evidence versus perturbation fraction. Bottom panel: signal-fit and no-signal log evidences versus perturbation fraction. These two views present the same underlying Bayesian evidence data. Together they show that the null test passes for all sampled perturbations from -2 per cent to +2 per cent and fails for all sampled perturbations with magnitude 5 per cent or larger. As detailed in [Appendix H](#appendix-h-data-provenance-note), the analysed data has a Gaussian, not Airy, truth beam, so this pattern reflects Airy-model-versus-Gaussian-truth mismatch tolerance and does not support an Airy antenna-diameter specification.*

The trend is not perfectly symmetric: the negative extreme at -20 per cent is more severe than the positive extreme at +20 per cent, but both tails show the same qualitative behaviour. This leaves open the possibility that a slightly more relaxed mismatch tolerance between 2 per cent and 5 per cent may also pass, which would require additional testing to establish — though, per the provenance finding above, any such follow-up should first confirm it is being tested against genuinely Airy-truth data. A smooth fit to the `Delta ln Z` curve may also be worth exploring in future work as a way to estimate the boundary between sampled points.

## Complete-Analysis Summary

The generated complete-analysis outputs report 11 successful signal-fit versus no-signal comparisons, with 5 PASS classifications and 6 FAIL classifications. Table 1 reproduces the `Delta ln Z` (`ins`-selected `delta_log_evidence`) and PASS/FAIL classification recorded per point in [sweep_report_summary.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.csv) / [sweep_report_summary.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.json).

A second, independent computation is available in [complete_analysis_successful.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/complete_analysis_successful.csv) and [complete_analysis_results.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/complete_analysis_results.json), which report a BayesEoR-delegated `log_bayes_factor` per point. This is a different quantity from Table 1's `Delta ln Z` (they are computed by different code paths and do not match numerically point-for-point, typically by a few tenths of a nat), but it yields the same 5 PASS / 6 FAIL classification.

| Perturbation fraction | `Delta ln Z` | Validation |
| --- | ---: | --- |
| -0.20 | 874.95 | FAIL |
| -0.10 | 136.70 | FAIL |
| -0.05 | 5.60 | FAIL |
| -0.02 | -7.00 | PASS |
| -0.01 | -7.76 | PASS |
| 0.00 | -7.81 | PASS |
| +0.01 | -8.01 | PASS |
| +0.02 | -7.66 | PASS |
| +0.05 | 4.92 | FAIL |
| +0.10 | 112.54 | FAIL |
| +0.20 | 360.44 | FAIL |

*Table 1. `Delta ln Z` (`ins`-selected evidence difference) and PASS/FAIL classification per antenna-diameter perturbation, from [sweep_report_summary.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.csv). The independently computed BayesEoR-delegated log-Bayes-factor, which gives the same classification with different numeric values, is available in [complete_analysis_successful.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/complete_analysis_successful.csv).*

Taken at face value, these results identify a null-consistent region centred on the nominal assumed beam diameter. However, per [Appendix H](#appendix-h-data-provenance-note), the analysed data has a confirmed Gaussian truth beam rather than an Airy one, so this is a mismatch-tolerance result for an Airy forward model against Gaussian-truth data, not an Airy-versus-Airy diameter accuracy specification. No Airy antenna-diameter specification is supported by this table.

## Power-Spectrum and Posterior Diagnostics

![ValSKA-rendered BayesEoR signal-fit power spectra and posterior diagnostics for the UKSRC Airy beam sweep](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/plot_analysis_results_signal_fit_valska.png)

*Figure 3. ValSKA-rendered signal-fit power-spectrum and posterior comparison. This is the primary figure for the report. It supports the interpretation that perturbation-dependent changes are most visible in the lowest-k bins, while the higher-k posterior distributions overlap more substantially across the sweep. The figure is therefore most useful as qualitative support for where the pass and fail regions begin to separate, not as a standalone specification threshold.*

Draft interpretation from visual inspection: the lowest-k power-spectrum points and posterior panels show the clearest separation between the large-perturbation cases and the near-nominal cases. In contrast, several higher-k posterior distributions overlap broadly, which argues for caution when translating this figure into stronger scientific claims.

The current figure is best used as a qualitative diagnostic. It suggests that the perturbation response is concentrated in the lowest-k region, but it does not on its own establish a per-k Bayesian preference. The legacy BayesEoR-delegated figure is retained in the artefact register for comparison but is not reproduced here because it does not add material information beyond Figure 3.

## Limitations

Limitations relevant to the interpretation are summarised in [Appendix G](#appendix-g-limitations).

## Conclusions

- **Conclusion:** All 11 sweep points completed successfully. The null test passes at every tested point from -2 per cent to +2 per cent and fails at every tested point with magnitude 5 per cent or larger. This pattern is well established computationally, but **it does not support an Airy antenna-diameter accuracy specification**: the mock visibility data analysed at every sweep point was independently confirmed to have a Gaussian, not Airy, truth beam (see [Appendix H](#appendix-h-data-provenance-note)). The result is instead a mismatch-tolerance characterisation between the BayesEoR Airy forward model and Gaussian-truth data under this pipeline. The plus-or-minus-2-per-cent specification stated in earlier drafts of this report is **withdrawn**.
- **Evidence basis:** [sweep_report_summary.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.csv), [sweep_report_summary.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.json), [complete_analysis_successful.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/complete_analysis_successful.csv), and [complete_analysis_results.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/complete_analysis_results.json) all support the same 5 PASS / 6 FAIL split, while Figures 1 and 2 show the same behaviour visually. The Gaussian-truth finding is established by the `valska-data-preflight` `beam_type_consistency` check and independently confirmed via the file's own `pyuvsim` history (see [Appendix H](#appendix-h-data-provenance-note)).
- **Residual risk:** No Airy antenna-diameter specification currently exists for this beam/sky combination. A slightly more relaxed mismatch tolerance between 2 per cent and 5 per cent may also pass, but establishing either that or a genuine Airy-diameter specification requires data with a confirmed Airy truth beam, which does not yet exist for this campaign.
- **Recommended action:** Do not record or use a plus-or-minus-2-per-cent (or any other) Airy antenna-diameter specification from this campaign. Before any such specification can be set, regenerate (or otherwise obtain) mock visibility data with a confirmed Airy truth beam for the `airy_diam14m` configuration and rerun this sweep against it. Retain the current `sweep_airy_v3` results as a valid, separate model-mismatch characterisation.

## Appendix A: Inputs

| Input | Location or identifier | Notes |
| --- | --- | --- |
| Sweep directory | `validation_results/UKSRC/v2/bayeseor/airy_diam14m/GSM_plus_GLEAM/_sweeps/sweep_airy_v3` | Campaign root recorded in `sweep_manifest.json` |
| Report directory | `validation_results/UKSRC/v2/bayeseor/airy_diam14m/GSM_plus_GLEAM/_sweeps/sweep_airy_v3/report` | Contains all generated artefacts used in this report |
| Sweep manifest | `validation_results/UKSRC/v2/bayeseor/airy_diam14m/GSM_plus_GLEAM/_sweeps/sweep_airy_v3/sweep_manifest.json` | Records 11 `antenna_diameter` points and creation time `2026-04-28T19:09:57Z` |
| BayesEoR template YAML | `src/valska_hera_beam/external_tools/bayeseor/templates/validation_airy_diam14m.yaml` | Referenced directly by the sweep manifest (path recorded as-is; see [Appendix H](#appendix-h-data-provenance-note) on the `valska_hera_beam` naming) |
| Data product | `/shared/UKSRC-ST/ps550/BayesEoR/UKSRC_val_mock_vis/initial_data_set_from_Quentin/pyuvsims_airy_10022026/vis/diam14m/gsm_plus_gleam-158.30-167.10-MHz-nf-38-fov-19.4deg-circ-field-1-airy_quentin.uvh5` | Input visibility dataset recorded in the sweep manifest (unchanged from the original campaign). **Despite the `airy` filename, this file's own `pyuvsim` history cites `hex-37-14.6m-gauss-fwhm9.3.yml`, a Gaussian beam config** — see [Appendix H](#appendix-h-data-provenance-note) |
| Perturbation parameter | `antenna_diameter` | Sampled at 11 fractions from -0.20 to +0.20 |

## Appendix B: Reproducibility Commands

The report-generation command used for the v2 refresh is:

```bash
python -m valska.external_tools.bayeseor.cli_report \
  validation_results/UKSRC/v2/bayeseor/airy_diam14m/GSM_plus_GLEAM/_sweeps/sweep_airy_v3 \
  --include-plot-analysis-results \
  --include-complete-analysis-table \
  --export-report-assets docs/source/reports/uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets \
  --print-complete-analysis-table
```

If the ValSKA environment is already loaded, the equivalent CLI command is:

```bash
valska-bayeseor-report \
  validation_results/UKSRC/v2/bayeseor/airy_diam14m/GSM_plus_GLEAM/_sweeps/sweep_airy_v3 \
  --include-plot-analysis-results \
  --include-complete-analysis-table \
  --export-report-assets docs/source/reports/uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets \
  --print-complete-analysis-table
```

This command was run against the v2 sweep on 2026-07-15, exited successfully, and its `--export-report-assets` output (including `artefact_manifest.json`) is what populates this report's asset directory. The original draft's commands (against `sweep_airy_init`) are preserved in [Appendix H](#appendix-h-data-provenance-note) for the historical record.

## Appendix C: Campaign Completeness

All 11 sweep points are reported as `ok` in `sweep_report_summary.csv`, and `complete_analysis_results.json` reports 11 successful pointwise comparisons with zero errors. Report-local copies of these generated artefacts are stored under `uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/` so the documentation build can embed the associated figures directly.

| Quantity | Value |
| --- | --- |
| Total sweep points | 11 |
| Complete sweep points | 11 |
| Incomplete sweep points | 0 |
| Evidence source used for sweep interpretation | `ins` for all 11 points |
| PASS points | 5 |
| FAIL points | 6 |
| Error points | 0 |
| Notes | The sweep is complete, so the interpretation is not being driven by missing points; however, the sign change at plus or minus 5 per cent warrants follow-up |

Report-local copies of the completeness summaries are available at [sweep_report_summary.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.csv) and [sweep_report_summary.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.json). The source generated files remain in the sweep report directory listed in Appendix A.

## Appendix D: Assumptions

| Assumption | Why it matters | Status |
| --- | --- | --- |
| The input mock visibility data has an Airy truth beam matching `airy_diam14m` | Required for this sweep to characterise Airy antenna-diameter accuracy rather than Airy-versus-Gaussian model mismatch | **`failed`** — `valska-data-preflight` (2026-07-20) and an independent `h5py` history check both confirm the data's cited telescope config is `hex-37-14.6m-gauss-fwhm9.3.yml` (Gaussian); see [Appendix H](#appendix-h-data-provenance-note) |
| Signal-fit and no-signal chains are paired correctly for each perturbation label | The PASS and FAIL summary is only meaningful if each comparison matches like with like | `tested` via 11 successful pairings in `complete_analysis_results.json` |
| The `ins` evidence source is the intended source for sweep-level interpretation | The reported `Delta ln Z` values come from the selected evidence source in the summary outputs | `tested` via `selected_source = ins` for all 11 points in `sweep_report_summary.json` |
| Incomplete runs do not bias the interpretation | Missing points could distort the apparent safe region | `tested` because no incomplete points are reported |
| The expected noise-power reference drawn in the analysis figures is appropriate for this campaign | The visual significance of posterior and spectrum offsets depends on that reference | `open` in this draft |
| Current posterior summaries use log-uniform-prior chains | This constrains how non-detections may be described | `accepted` |
| Classified non-detections are not calibrated upper limits unless uniform-prior chains are run | Prevents overstating the result as a 95 per cent upper-limit statement | `accepted` |
| Using the largest tested pass point to guide a provisional Airy antenna-diameter specification is acceptable for this draft | The report uses the pass window to inform a modelling-accuracy bound rather than to infer an exact threshold | **`failed`** — blocked by the Gaussian-truth-data finding above; no Airy antenna-diameter specification can be set from this campaign until it is rerun against confirmed Airy-truth data |

## Appendix E: Artefact Register

| Artefact | Role in report | Path |
| --- | --- | --- |
| Sweep summary CSV | Campaign completeness and per-point evidence metrics; report-local copy for documentation rendering | [sweep_report_summary.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.csv) |
| Sweep summary JSON | Machine-readable sweep payload used for counts and `Delta ln Z` values; report-local copy | [sweep_report_summary.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/sweep_report_summary.json) |
| Complete-analysis CSV | Generated pass or fail table for successful signal-fit versus no-signal pairings; report-local copy | [complete_analysis_successful.csv](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/complete_analysis_successful.csv) |
| Complete-analysis JSON | Machine-readable complete-analysis payload used for PASS, FAIL, and error totals; report-local copy | [complete_analysis_results.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/complete_analysis_results.json) |
| Delta log evidence plot | Primary evidence-difference diagnostic; report-local copy used for embedding | [delta_log_evidence_vs_perturb_frac.png](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/delta_log_evidence_vs_perturb_frac.png) |
| Evidence-by-model plot | Supporting evidence diagnostic for hypothesis separation across the sweep; report-local copy used for embedding | [log_evidence_by_model_vs_perturb_frac.png](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/log_evidence_by_model_vs_perturb_frac.png) |
| ValSKA analysis figure | Primary power-spectrum and posterior diagnostic; report-local copy used for embedding | [plot_analysis_results_signal_fit_valska.png](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/plot_analysis_results_signal_fit_valska.png) |
| Legacy analysis figure | Comparison-only rendering retained for audit trail but not reproduced in the main text | [plot_analysis_results_signal_fit.png](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/plot_analysis_results_signal_fit.png) |
| Artefact export manifest | Provenance record written by `--export-report-assets`, recording the source sweep/report directories and export timestamp for the assets above | [artefact_manifest.json](uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/artefact_manifest.json) |

## Appendix F: Review Checklist

- [x] The report states a clear validation question.
- [x] All figures and tables are generated artefacts or clearly marked manual summaries.
- [x] Figure captions state what conclusion the artefact supports.
- [x] The report distinguishes detections, non-detections, and calibrated upper limits.
- [x] The evidence source (`ins`) is recorded.
- [x] The ValSKA branch and commit are recorded.
- [x] Known limitations are not hidden in prose.
- [x] An equivalent `valska-bayeseor-report` reproducibility command completed successfully in this workspace.
- [x] The report-generation environment version and the BayesEoR analysis version (which produced the chains) are recorded separately, and their difference between campaigns is noted rather than assumed benign.
- [x] The input data's actual beam type was checked against its filename/label claim (via `valska-data-preflight`, independently confirmed via `h5py`), rather than assumed from naming; see [Appendix H](#appendix-h-data-provenance-note).

## Appendix G: Limitations

| Limitation | Consequence | Follow-up |
| --- | --- | --- |
| The input mock visibility data has a confirmed Gaussian, not Airy, truth beam | No Airy antenna-diameter accuracy specification can be derived from this campaign; the PASS/FAIL pattern instead reflects Airy-model-versus-Gaussian-truth mismatch tolerance | Regenerate (or source) mock visibility data with a confirmed Airy truth beam for `airy_diam14m` and rerun this sweep before attempting any Airy antenna-diameter specification |
| No per-k Bayesian evidence comparison | Detection and non-detection classification remains a proxy rather than a mode-by-mode evidence test | Add a future per-k Bayesian comparison if campaign sign-off requires mode-resolved claims |
| Log-uniform-prior chains used for current posteriors | Classified non-detections are not calibrated 95 per cent upper limits | Run uniform-prior upper-limit chains for any bins that need publishable upper-limit statements |
| The transition between the largest tested pass point and the first tested fail point is not sampled | The sweep bounds the model-mismatch tolerance region but does not identify the exact threshold, and (per the row above) does not by itself support any Airy antenna-diameter specification | Run a finer sweep between 2 per cent and 5 per cent in magnitude, against confirmed Airy-truth data, before freezing a final specification |

## Appendix H: Data Provenance Note

This report was originally drafted on 2026-04-25 against the historical campaign `sweep_airy_init` (created `2026-02-27T23:36:40Z`, under `validation_results/UKSRC/bayeseor/...`). On 2026-07-15, as part of a merge and refresh of the `validation-report-drafts` branch, the report's title, executive summary, data, figures, and tables were updated to the v2 campaign `sweep_airy_v3` (created `2026-04-28T19:09:57Z`, under `validation_results/UKSRC/v2/bayeseor/...`), which uses the same beam model, sky model, input visibility dataset, and `antenna_diameter` sweep points as the original.

The report's filename (`uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init.md`) and asset-directory slug (`uksrc_airy_diam14m_gsm_plus_gleam_sweep_airy_init_assets/`) intentionally still say `sweep_airy_init`. These are referenced from `docs/source/reports.rst` (the toctree entry) and `docs/source/workflows/bayeseor_reporting.md` (an example asset path), plus the report's own embedded image/asset links; renaming them now would break those references for no content benefit, since the filename is only a slug and the report's title, H1, and body text are the parts that state which campaign the content actually describes. A future rename to a `sweep_airy_v3`-based slug, with the corresponding link updates, is a reasonable follow-up but was treated as out of scope for this focused content refresh.

Before updating this report, the following checks were performed to confirm the v2 campaign reproduces rather than changes the original result:

- **Structural completeness:** All 11 v2 sweep points report `status: ok` with zero errors, and `complete_analysis_results.json` reports 11/11 successful signal-fit-versus-no-signal pairings — matching the original campaign's completeness.
- **Point-by-point evidence comparison:** `delta_log_evidence` (`ins` source) was compared point-by-point between `sweep_airy_init` and `sweep_airy_v3`. Every point agrees to within approximately 0.05-1.0 nats (against magnitudes ranging from about 5 to 875 nats). The PASS/FAIL classification (5 PASS at 0, ±1%, ±2%; 6 FAIL at ±5%, ±10%, ±20%) is identical between the two campaigns. Note that the two campaigns were run with different BayesEoR analysis versions (`2.0.1.dev22+g3f5b6cd2f` for `sweep_airy_init` versus `2.0.1.dev31+g96e0d7db5` for `sweep_airy_v3` — see the Report Metadata table), and the generated signal-fit and no-signal configuration YAMLs are otherwise identical between the two campaigns at all 11 points (differing only in `output_dir`). This refresh does not attempt to attribute the small numerical differences to nested-sampling stochasticity versus the BayesEoR revision change specifically; either or both may contribute. What is established is that the PASS/FAIL classification is robust across both BayesEoR versions tested.
- **Visual comparison:** The delta-log-evidence plot, the evidence-by-model plot, and the ValSKA-rendered signal-fit/posterior figure were compared between the two campaigns. All three show the same qualitative pattern (same PASS/FAIL point colouring, same posterior shapes per `k` bin, same asymmetry between the -20% and +20% tails).

On this basis, the report's data, figures, and tables were refreshed to the v2 outputs using `valska-bayeseor-report ... --export-report-assets` (see [Appendix B](#appendix-b-reproducibility-commands)), and the resulting `artefact_manifest.json` is retained in [Appendix E](#appendix-e-artefact-register) as the record of that export. The report's scientific conclusions (Executive Summary, Conclusions) were **not** re-derived independently for this refresh; they are unchanged because the v2 numbers reproduce the same PASS/FAIL pattern and the same qualitative evidence trend as the original draft. This refresh does not constitute a scientific sign-off on the v2 campaign or on the plus-or-minus 2 per cent specification recommendation — that remains an open item, as recorded in Appendix D and Appendix F.

The historical campaign's own reproducibility commands, for reference, were:

```bash
valska-bayeseor-report \
  validation_results/UKSRC/bayeseor/airy_diam14m/GSM_plus_GLEAM/_sweeps/sweep_airy_init \
  --include-plot-analysis-results \
  --print-complete-analysis-table
```

### Update 2026-07-22: input data beam-type mismatch

A `valska-data-preflight` scan of `UKSRC_val_mock_vis` run on 2026-07-20 (see
`temp/tmp/airy_data_investigation_20260716/preflight_scan_summary.md` and the accompanying
`preflight_scan_UKSRC_val_mock_vis.json`) flagged the data product listed in
[Appendix A](#appendix-a-inputs) with a `beam_type_consistency` **FAIL**: the file's name and
directory claim an Airy beam, but its cited telescope config, `hex-37-14.6m-gauss-fwhm9.3.yml`,
declares a Gaussian beam. This is one of 31 files flagged FAIL in that scan, all under
`initial_data_set_from_Quentin/pyuvsims_airy_10022026/vis/`.

This finding was independently re-confirmed for this report by reading the file's `pyuvsim`
history directly with `h5py` rather than relying on the scan output alone:

```
Simulated with pyuvsim version: 1.4.1.dev96+g6b946d3.dirty. Sources from source list(s):
[gleam-158.30-167.10-MHz-nf-38-pld-mean-2.82-std-0.19-fov-19.4deg-circ-field-1.skyh5].
Based on config files: fov-19.4-oscar-sm.yml, telescope_config/hex-37-14.6m-gauss-fwhm9.3.yml,
telescope_config/hex-37-14.6m.csv Npus = 8. ...
```

`sweep_manifest.json` for `sweep_airy_v3` was also re-checked directly and confirms all 11
sweep points (`perturb_parameter: antenna_diameter`) use this exact `data_path`. Because this
report's own "structural completeness" and "point-by-point evidence comparison" checks
(above) already established that `sweep_airy_v3` reuses the same input data product as the
original `sweep_airy_init` campaign, this Gaussian-truth finding applies identically to both —
it is not a `sweep_airy_v3`-specific regression, and it was not caught by the earlier v2 refresh
because that refresh (see above) deliberately checked reproduction of the historical numeric
result rather than re-deriving the underlying beam-type assumption from first principles.

**Impact:** the `antenna_diameter` parameter sampled across all 11 points of this sweep is a
property of the BayesEoR Airy forward model only; the simulated visibility data itself has a
fixed Gaussian truth beam at every point and never varies. The PASS/FAIL pattern in
[Table 1](#complete-analysis-summary) is therefore valid as a computed result but does not test
what the Executive Summary, Scope, and Conclusions previously claimed (an Airy-versus-Airy
diameter accuracy specification). This report has been updated throughout to reframe the result
as an Airy-forward-model-versus-Gaussian-truth mismatch-tolerance characterisation, and the
previously stated plus-or-minus-2-per-cent specification is withdrawn. See the provenance
warning at the top of this report, the Executive Summary, Scope, Appendix D, and Appendix G for
the corresponding updates.