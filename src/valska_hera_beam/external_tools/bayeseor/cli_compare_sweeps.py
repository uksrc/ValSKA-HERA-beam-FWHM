#!/usr/bin/env python3
"""Compare two BayesEoR sweep report summaries."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from valska_hera_beam.cli_format import (
    CliColors,
    add_color_argument,
    resolve_color_mode,
)

_Metric = (
    "delta_log_evidence",
    "log10_bayes_factor_signal_over_no_signal",
    "bayes_factor_signal_over_no_signal",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-bayeseor-compare-sweeps",
        description=(
            "Compare per-point evidence metrics from two "
            "sweep_report_summary.json outputs."
        ),
        epilog=(
            "Accepted input paths:\n"
            "  - sweep directory containing report/sweep_report_summary.json\n"
            "  - report directory containing sweep_report_summary.json\n"
            "  - direct path to sweep_report_summary.json\n\n"
            "Examples:\n"
            "  valska-bayeseor-compare-sweeps /path/to/sweep_a /path/to/sweep_b\n"
            "  valska-bayeseor-compare-sweeps a/report b/report --metric log10_bayes_factor_signal_over_no_signal --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("left", type=Path, help="Left sweep/report path.")
    parser.add_argument("right", type=Path, help="Right sweep/report path.")
    parser.add_argument(
        "--left-name",
        type=str,
        default="left",
        help="Display label for left input (default: left).",
    )
    parser.add_argument(
        "--right-name",
        type=str,
        default="right",
        help="Display label for right input (default: right).",
    )
    parser.add_argument(
        "--metric",
        choices=list(_Metric),
        default="delta_log_evidence",
        help="Per-point metric to compare (default: delta_log_evidence).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of largest absolute deltas to display (default: 10).",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print machine-readable JSON payload.",
    )
    add_color_argument(parser)
    return parser


def _resolve_summary_path(path: Path) -> Path:
    p = Path(path).expanduser().resolve()
    if p.is_file():
        return p
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")

    direct = p / "sweep_report_summary.json"
    if direct.exists():
        return direct

    nested = p / "report" / "sweep_report_summary.json"
    if nested.exists():
        return nested

    raise FileNotFoundError(
        f"Could not locate sweep_report_summary.json under input path: {p}"
    )


def _point_key(point: dict[str, Any]) -> str:
    run_label = point.get("run_label")
    if run_label is not None and str(run_label).strip():
        return str(run_label)
    perturb_parameter = str(point.get("perturb_parameter", "unknown"))
    perturb_frac = point.get("perturb_frac")
    return f"{perturb_parameter}:{perturb_frac}"


def _load_points(summary_json: Path) -> list[dict[str, Any]]:
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    points = payload.get("points")
    if not isinstance(points, list):
        raise ValueError(
            f"Invalid summary payload (missing list 'points'): {summary_json}"
        )
    out: list[dict[str, Any]] = []
    for point in points:
        if isinstance(point, dict):
            out.append(point)
    return out


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except Exception:
        return None
    if math.isnan(result):
        return None
    return result


def _build_payload(
    *,
    left_path: Path,
    right_path: Path,
    left_name: str,
    right_name: str,
    metric: str,
    top_n: int,
) -> dict[str, Any]:
    left_points = _load_points(left_path)
    right_points = _load_points(right_path)

    left_map = {_point_key(p): p for p in left_points}
    right_map = {_point_key(p): p for p in right_points}

    left_keys = set(left_map)
    right_keys = set(right_map)
    shared = sorted(left_keys & right_keys)
    left_only = sorted(left_keys - right_keys)
    right_only = sorted(right_keys - left_keys)

    compared_rows: list[dict[str, Any]] = []
    skipped_metric_missing = 0
    status_mismatch = 0

    for key in shared:
        left_row = left_map[key]
        right_row = right_map[key]
        left_status = str(left_row.get("status"))
        right_status = str(right_row.get("status"))
        if left_status != right_status:
            status_mismatch += 1

        left_value = _to_float_or_none(left_row.get(metric))
        right_value = _to_float_or_none(right_row.get(metric))
        if left_value is None or right_value is None:
            skipped_metric_missing += 1
            continue

        delta = right_value - left_value
        compared_rows.append(
            {
                "point_key": key,
                "perturb_parameter": left_row.get("perturb_parameter"),
                "perturb_frac": left_row.get("perturb_frac"),
                "left_status": left_status,
                "right_status": right_status,
                "left_value": left_value,
                "right_value": right_value,
                "delta": delta,
                "abs_delta": abs(delta),
            }
        )

    compared_rows.sort(key=lambda row: row["abs_delta"], reverse=True)
    top_rows = compared_rows[: max(0, top_n)]

    deltas = [row["delta"] for row in compared_rows]
    abs_deltas = [row["abs_delta"] for row in compared_rows]

    if deltas:
        delta_stats: dict[str, float | None] = {
            "mean_delta": statistics.fmean(deltas),
            "min_delta": min(deltas),
            "max_delta": max(deltas),
            "mean_abs_delta": statistics.fmean(abs_deltas),
        }
    else:
        delta_stats = {
            "mean_delta": None,
            "min_delta": None,
            "max_delta": None,
            "mean_abs_delta": None,
        }

    return {
        "metric": metric,
        "left": {"name": left_name, "summary_json": str(left_path)},
        "right": {"name": right_name, "summary_json": str(right_path)},
        "summary": {
            "left_points": len(left_map),
            "right_points": len(right_map),
            "shared_points": len(shared),
            "left_only_points": len(left_only),
            "right_only_points": len(right_only),
            "status_mismatch_points": status_mismatch,
            "compared_points": len(compared_rows),
            "skipped_missing_metric": skipped_metric_missing,
            **delta_stats,
        },
        "top_differences": top_rows,
        "left_only_keys": left_only,
        "right_only_keys": right_only,
    }


def _format_delta(value: object, *, colors: CliColors) -> str:
    if not isinstance(value, str | int | float):
        return str(value)
    delta = float(value)
    text = f"{delta:+.6g}"
    if delta == 0:
        return text
    return colors.warning(text)


def _print_text(payload: dict[str, Any], *, colors: CliColors) -> None:
    summary = payload["summary"]
    left = payload["left"]
    right = payload["right"]

    print(colors.heading("Sweep comparison summary:"))
    print(f"  metric:             {payload['metric']}")
    print(
        f"  left:               "
        f"{left['name']} ({colors.path(left['summary_json'])})"
    )
    print(
        f"  right:              "
        f"{right['name']} ({colors.path(right['summary_json'])})"
    )
    print(f"  left_points:        {summary['left_points']}")
    print(f"  right_points:       {summary['right_points']}")
    print(f"  shared_points:      {summary['shared_points']}")
    print(f"  compared_points:    {summary['compared_points']}")
    print(
        "  skipped_metric:     "
        f"{colors.warning(summary['skipped_missing_metric'])}"
    )
    print(
        "  status_mismatch:    "
        f"{colors.warning(summary['status_mismatch_points'])}"
    )
    print(
        f"  left_only_points:   {colors.warning(summary['left_only_points'])}"
    )
    print(
        f"  right_only_points:  {colors.warning(summary['right_only_points'])}"
    )

    if summary["mean_delta"] is not None:
        print(
            "  mean_delta:         "
            f"{_format_delta(summary['mean_delta'], colors=colors)}"
        )
        print(
            "  min_delta:          "
            f"{_format_delta(summary['min_delta'], colors=colors)}"
        )
        print(
            "  max_delta:          "
            f"{_format_delta(summary['max_delta'], colors=colors)}"
        )
        print(f"  mean_abs_delta:     {summary['mean_abs_delta']:+.6g}")

    print("\n" + colors.heading("Top differences (right - left):"))
    rows = payload["top_differences"]
    if not rows:
        print("  (none)")
    else:
        for row in rows:
            print(
                "  - "
                f"{row['point_key']}: "
                f"left={row['left_value']:+.6g}, "
                f"right={row['right_value']:+.6g}, "
                f"delta={_format_delta(row['delta'], colors=colors)}"
            )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        left_summary = _resolve_summary_path(Path(args.left))
        right_summary = _resolve_summary_path(Path(args.right))
        payload = _build_payload(
            left_path=left_summary,
            right_path=right_summary,
            left_name=str(args.left_name),
            right_name=str(args.right_name),
            metric=str(args.metric),
            top_n=int(args.top),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json_out:
        print(json.dumps(payload, indent=2))
        return 0

    colors = CliColors(
        resolve_color_mode(args.color), enabled=not bool(args.json_out)
    )
    _print_text(payload, colors=colors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
