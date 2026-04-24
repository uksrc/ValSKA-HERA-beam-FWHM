#!/usr/bin/env python3
"""Validate BayesEoR sweep integrity and return policy-based exit code."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from valska_hera_beam.cli_format import (
    CliColors,
    add_color_argument,
    resolve_color_mode,
)

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
    add_color_argument(parser)
    return parser


def _format_status(status: object, *, colors: CliColors) -> str:
    text = str(status)
    if text == "ok":
        return colors.success(text)
    if text == "partial":
        return colors.warning(text)
    if text in ("missing", "invalid", "error"):
        return colors.error(text)
    return text


def _print_text(
    *, health, failures: list[str], exit_code: int, colors: CliColors
) -> None:
    print(colors.heading("Sweep validation:"))
    print(f"  sweep_dir:    {colors.path(health.sweep_dir)}")
    print(
        f"  sweep_status: {_format_status(health.sweep_status, colors=colors)}"
    )
    print(
        "  points:       "
        f"total={health.points_total}, "
        f"ok={colors.success(health.points_ok)}, "
        f"partial={colors.warning(health.points_partial)}, "
        f"missing={colors.error(health.points_missing)}"
    )

    if failures:
        print(colors.heading("  failures:"))
        for item in failures:
            print(f"    - {colors.error(item)}")
    else:
        print(f"  failures:     {colors.success('none')}")

    exit_code_display = (
        colors.success(exit_code)
        if exit_code == 0
        else colors.error(exit_code)
    )
    print(f"  exit_code:    {exit_code_display}")


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

    colors = CliColors(
        resolve_color_mode(args.color), enabled=not bool(args.json_out)
    )
    _print_text(
        health=health,
        failures=failures,
        exit_code=exit_code,
        colors=colors,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
