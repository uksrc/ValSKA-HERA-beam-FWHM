#!/usr/bin/env python3
"""Validate BayesEoR sweep integrity and return policy-based exit code."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .sweep_health import (
    inspect_sweep_health,
    sweep_health_to_dict,
    validation_exit_code,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-bayeseor-validate-sweep",
        description=(
            "Validate one sweep directory and return a policy-based exit code."
        ),
        epilog=(
            "Examples:\n"
            "  valska-bayeseor-validate-sweep /path/to/_sweeps/sweep_airy_init\n"
            "  valska-bayeseor-validate-sweep /path/to/_sweeps/sweep_airy_init --allow-partial\n"
            "  valska-bayeseor-validate-sweep /path/to/_sweeps/sweep_airy_init --require-jobs-json --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "sweep_dir",
        type=Path,
        help="Path to sweep directory containing sweep_manifest.json.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Validation policy: accept partial sweeps.",
    )
    parser.add_argument(
        "--require-jobs-json",
        action="store_true",
        help="Validation policy: require jobs.json in all point run directories.",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print machine-readable JSON payload.",
    )
    return parser


def _print_text(*, health, failures: list[str], exit_code: int) -> None:
    print("Sweep validation:")
    print(f"  sweep_dir:    {health.sweep_dir}")
    print(f"  sweep_status: {health.sweep_status}")
    print(
        "  points:       "
        f"total={health.points_total}, "
        f"ok={health.points_ok}, "
        f"partial={health.points_partial}, "
        f"missing={health.points_missing}"
    )

    if failures:
        print("  failures:")
        for item in failures:
            print(f"    - {item}")
    else:
        print("  failures:     none")

    print(f"  exit_code:    {exit_code}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        health = inspect_sweep_health(Path(args.sweep_dir))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    exit_code, failures = validation_exit_code(
        health,
        allow_partial=bool(args.allow_partial),
        require_jobs_json=bool(args.require_jobs_json),
    )

    if args.json_out:
        payload = sweep_health_to_dict(health)
        payload["validation"] = {
            "allow_partial": bool(args.allow_partial),
            "require_jobs_json": bool(args.require_jobs_json),
            "failures": failures,
            "exit_code": exit_code,
        }
        print(json.dumps(payload, indent=2))
        return exit_code

    _print_text(health=health, failures=failures, exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
