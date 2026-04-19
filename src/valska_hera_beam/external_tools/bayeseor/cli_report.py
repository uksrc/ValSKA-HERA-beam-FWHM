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

_ProgressMode = str


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
        "--json",
        dest="json_out",
        action="store_true",
        help="Print report result payload as JSON.",
    )
    parser.add_argument(
        "--progress",
        choices=["auto", "always", "never"],
        default="auto",
        help=(
            "Show Rich progress output for long-running report steps. "
            "Default: auto (enabled only for interactive stderr)."
        ),
    )
    return parser


def _show_progress(mode: _ProgressMode, *, json_out: bool) -> bool:
    if json_out or mode == "never":
        return False
    if mode == "always":
        return True
    return bool(sys.stderr.isatty())


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
            ),
            show_progress=_show_progress(
                str(args.progress), json_out=bool(args.json_out)
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
        }
        print(json.dumps(payload, indent=2))
        return 0

    _print_summary(result)
    if result.rows_complete < result.rows_total:
        print(
            "\nNote: some points were incomplete and are marked in the summary table."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
