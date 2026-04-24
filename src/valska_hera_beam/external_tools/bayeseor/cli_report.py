#!/usr/bin/env python3
"""Generate summary plots/tables for a completed BayesEoR sweep."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from valska_hera_beam.external_tools.bayeseor.report import (
    SweepReportResult,
    generate_sweep_report,
)

_TableStyle = str


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ``valska-bayeseor-report``."""
    parser = argparse.ArgumentParser(
        prog="valska-bayeseor-report",
        description=(
            "Generate report tables and plots from an existing ValSKA BayesEoR sweep.\n\n"
            "Typical input:\n"
            "  <results_root>/bayeseor/<beam>/<sky>/_sweeps/<run_id>/"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "sweep_dir",
        type=Path,
        help=(
            "Path to an existing sweep directory containing sweep_manifest.json.\n"
            "Example: /.../bayeseor/airy_diam14m/GSM_plus_GLEAM/_sweeps/sweep_airy_init"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory for generated report files (default: <sweep_dir>/report).",
    )
    parser.add_argument(
        "--evidence-source",
        choices=["ns", "ins"],
        default="ins",
        help="Which evidence estimate to use for ΔlnZ/Bayes factor (default: ins).",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Only write tabular report files (skip PNG plot generation).",
    )
    parser.add_argument(
        "--include-plot-analysis-results",
        action="store_true",
        help=(
            "Also generate a BeamAnalysisPlotter.plot_analysis_results figure "
            "for all complete signal_fit points."
        ),
    )
    parser.add_argument(
        "--include-complete-analysis-table",
        action="store_true",
        help=(
            "Also run run_complete_bayeseor_analysis across complete points "
            "and write summary table/json outputs."
        ),
    )
    parser.add_argument(
        "--print-complete-analysis-table",
        action="store_true",
        help=(
            "Print a terminal summary table for complete-analysis results. "
            "Implies --include-complete-analysis-table."
        ),
    )
    parser.add_argument(
        "--complete-analysis-table-style",
        choices=["emoji", "plain"],
        default="emoji",
        help=(
            "Terminal style for --print-complete-analysis-table. "
            "Use 'plain' for ASCII-only logs. Default: emoji."
        ),
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print report result payload as JSON.",
    )
    return parser


def _perturbation_fraction(raw_label: object) -> float | None:
    label = str(raw_label)
    try:
        return float(label.split("_", 1)[1])
    except Exception:
        return None


def _format_perturbation_label(raw_label: object) -> str:
    label = str(raw_label)
    frac = _perturbation_fraction(label)
    if frac is None:
        return label

    if label.startswith("antdiam_"):
        return f"ΔD/D = {frac * 100:+.2f}%"
    if label.startswith("fwhm_"):
        return f"ΔFWHM/FWHM = {frac * 100:+.2f}%"
    return f"Δ = {frac * 100:+.2f}%"


def _coerce_float(raw: object) -> float:
    if isinstance(raw, str | int | float):
        return float(raw)
    raise TypeError(f"Expected a numeric value, got {type(raw).__name__}")


def _plain_interpretation(log_bayes_factor: object) -> str:
    try:
        log_bf = _coerce_float(log_bayes_factor)
    except Exception:
        return "Unable to evaluate"
    if log_bf > 0:
        return "Strong evidence for spurious power detected"
    if log_bf < 0:
        return "Unbiased inferences recovered"
    return "Inconclusive"


def _format_log_bayes_factor(raw: object) -> str:
    try:
        return f"{_coerce_float(raw):.3f}"
    except Exception:
        return "N/A"


def _validation_display(validation: object, *, style: _TableStyle) -> str:
    text = str(validation)
    if style == "plain":
        return text
    if text == "PASS":
        return "✅ PASS"
    if text == "FAIL":
        return "❌ FAIL"
    return f"❌ {text}" if text else "❌ ERROR"


def _print_complete_analysis_table(
    rows: list[dict[str, object]], *, style: _TableStyle
) -> None:
    print("\nComplete BayesEoR Perturbation Analysis Summary")
    print("=" * 88)

    if not rows:
        print("No successful complete-analysis results to summarize.")
        return

    table_rows = [
        {
            "perturbation": _format_perturbation_label(
                row.get("perturbation", "unknown")
            ),
            "log_bf": _format_log_bayes_factor(row.get("log_bayes_factor")),
            "validation": _validation_display(
                row.get("validation", "ERROR"), style=style
            ),
            "interpretation": _plain_interpretation(
                row.get("log_bayes_factor")
            ),
            "sort_value": _perturbation_fraction(
                row.get("perturbation", "unknown")
            ),
        }
        for row in rows
    ]
    table_rows.sort(
        key=lambda row: (
            row["sort_value"] is None,
            row["sort_value"] if isinstance(row["sort_value"], float) else 0.0,
            str(row["perturbation"]),
        )
    )
    widths = {
        "perturbation": max(
            len("Perturbation"),
            *(len(str(row["perturbation"])) for row in table_rows),
        ),
        "log_bf": max(
            len("Log BF"), *(len(str(row["log_bf"])) for row in table_rows)
        ),
        "validation": max(
            len("Validation"),
            *(len(str(row["validation"])) for row in table_rows),
        ),
    }
    header = (
        f"{'Perturbation':<{widths['perturbation']}}  "
        f"{'Log BF':>{widths['log_bf']}}  "
        f"{'Validation':<{widths['validation']}}  Interpretation"
    )
    print(header)
    print("-" * len(header))

    pass_count = 0
    fail_count = 0
    for row in table_rows:
        validation = str(row["validation"])
        if "PASS" in validation:
            pass_count += 1
        elif "FAIL" in validation:
            fail_count += 1
        print(
            f"{row['perturbation']:<{widths['perturbation']}}  "
            f"{row['log_bf']:>{widths['log_bf']}}  "
            f"{row['validation']:<{widths['validation']}}  "
            f"{row['interpretation']}"
        )

    print("-" * len(header))
    print(
        f"TOTAL: {len(table_rows)} | PASS: {pass_count} | "
        f"FAIL: {fail_count} | ERROR: 0"
    )


def _print_summary(result: SweepReportResult) -> None:
    print("\nSweep report generated:")
    print(f"  sweep_dir:      {result.sweep_dir}")
    print(f"  out_dir:        {result.out_dir}")
    print(f"  evidence_source:{result.evidence_source}")
    print(f"  points_total:   {result.rows_total}")
    print(f"  points_complete:{result.rows_complete}")
    print(f"  summary_csv:    {result.summary_csv}")
    print(f"  summary_json:   {result.summary_json}")
    if result.delta_plot_png is not None:
        print(f"  delta_plot:     {result.delta_plot_png}")
    if result.evidence_plot_png is not None:
        print(f"  evidence_plot:  {result.evidence_plot_png}")
    if result.plot_analysis_results_png is not None:
        print(f"  plot_analysis_results: {result.plot_analysis_results_png}")
    if result.complete_analysis_json is not None:
        print(f"  complete_analysis_json: {result.complete_analysis_json}")
    if result.complete_analysis_csv is not None:
        print(f"  complete_analysis_csv:  {result.complete_analysis_csv}")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``valska-bayeseor-report``."""
    args = build_parser().parse_args(argv)

    if args.json_out and args.print_complete_analysis_table:
        print(
            "ERROR: --print-complete-analysis-table cannot be combined with --json.",
            file=sys.stderr,
        )
        return 2

    try:
        result = generate_sweep_report(
            sweep_dir=Path(args.sweep_dir),
            out_dir=Path(args.out_dir) if args.out_dir is not None else None,
            evidence_source=args.evidence_source,
            make_plots=not bool(args.no_plots),
            include_plot_analysis_results=bool(
                args.include_plot_analysis_results
            ),
            include_complete_analysis_table=bool(
                args.include_complete_analysis_table
                or args.print_complete_analysis_table
            ),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json_out:
        payload = {
            "sweep_dir": str(result.sweep_dir),
            "out_dir": str(result.out_dir),
            "evidence_source": result.evidence_source,
            "rows_total": result.rows_total,
            "rows_complete": result.rows_complete,
            "summary_csv": str(result.summary_csv),
            "summary_json": str(result.summary_json),
            "delta_plot_png": str(result.delta_plot_png)
            if result.delta_plot_png is not None
            else None,
            "evidence_plot_png": str(result.evidence_plot_png)
            if result.evidence_plot_png is not None
            else None,
            "plot_analysis_results_png": str(result.plot_analysis_results_png)
            if result.plot_analysis_results_png is not None
            else None,
            "complete_analysis_json": str(result.complete_analysis_json)
            if result.complete_analysis_json is not None
            else None,
            "complete_analysis_csv": str(result.complete_analysis_csv)
            if result.complete_analysis_csv is not None
            else None,
            "complete_analysis_rows": result.complete_analysis_rows,
        }
        print(json.dumps(payload, indent=2))
        return 0

    _print_summary(result)
    if args.print_complete_analysis_table:
        _print_complete_analysis_table(
            result.complete_analysis_rows,
            style=str(args.complete_analysis_table_style),
        )
    if result.rows_complete < result.rows_total:
        print(
            "\nNote: some points were incomplete and are marked in the summary table."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
