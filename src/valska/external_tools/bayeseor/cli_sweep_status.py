#!/usr/bin/env python3
"""Show health/status summary for a BayesEoR sweep directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .sweep_health import inspect_sweep_health, sweep_health_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-bayeseor-sweep-status",
        description=(
            "Inspect one sweep directory and summarise per-point output health."
        ),
        epilog=(
            "Examples:\n"
            "  valska-bayeseor-sweep-status /path/to/_sweeps/sweep_airy_init\n"
            "  valska-bayeseor-sweep-status /path/to/_sweeps/sweep_airy_init --show-notes\n"
            "  valska-bayeseor-sweep-status /path/to/_sweeps/sweep_airy_init --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "sweep_dir",
        type=Path,
        help="Path to sweep directory containing sweep_manifest.json.",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print machine-readable JSON payload.",
    )
    parser.add_argument(
        "--show-notes",
        action="store_true",
        help="Include per-point note details in text output.",
    )
    return parser


def _print_text(*, health, show_notes: bool) -> None:
    print("Sweep status summary:")
    print(f"  sweep_dir:      {health.sweep_dir}")
    print(f"  sweep_manifest: {health.sweep_manifest_path}")
    if health.run_id is not None:
        print(f"  run_id:         {health.run_id}")
    if health.beam_model is not None:
        print(f"  beam_model:     {health.beam_model}")
    if health.sky_model is not None:
        print(f"  sky_model:      {health.sky_model}")
    print(f"  sweep_status:   {health.sweep_status}")
    print(f"  points_total:   {health.points_total}")
    print(f"  points_ok:      {health.points_ok}")
    print(f"  points_partial: {health.points_partial}")
    print(f"  points_missing: {health.points_missing}")

    if health.messages:
        print("  messages:")
        for msg in health.messages:
            print(f"    - {msg}")

    print("\nPer-point:")
    if not health.point_rows:
        print("  (none)")
        return

    for row in health.point_rows:
        print(
            "  - "
            f"{row.run_label} "
            f"({row.perturb_parameter}={row.perturb_frac:+.3f}) "
            f"=> {row.point_status}"
        )
        if show_notes and row.notes:
            for note in row.notes:
                print(f"      note: {note}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        health = inspect_sweep_health(Path(args.sweep_dir))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json_out:
        print(json.dumps(sweep_health_to_dict(health), indent=2))
        return 0

    _print_text(health=health, show_notes=bool(args.show_notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
