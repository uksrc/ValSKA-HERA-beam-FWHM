#!/usr/bin/env python3
"""Suggest re-run commands for incomplete BayesEoR sweep points."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from valska_hera_beam.cli_format import (
    CliColors,
    add_color_argument,
    resolve_color_mode,
)

from .sweep_health import inspect_sweep_health, sweep_health_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-bayeseor-resume",
        description=(
            "Inspect one sweep and generate exact valska-bayeseor-submit "
            "commands for incomplete points."
        ),
        epilog=(
            "Examples:\n"
            "  valska-bayeseor-resume /path/to/_sweeps/sweep_airy_init\n"
            "  valska-bayeseor-resume /path/to/_sweeps/sweep_airy_init --stage gpu\n"
            "  valska-bayeseor-resume /path/to/_sweeps/sweep_airy_init --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "sweep_dir",
        type=Path,
        help="Path to sweep directory containing sweep_manifest.json.",
    )
    parser.add_argument(
        "--stage",
        choices=["cpu", "gpu", "all"],
        default="all",
        help="Which stage(s) to generate commands for (default: all).",
    )
    parser.add_argument(
        "--hypothesis",
        choices=["signal_fit", "no_signal", "both"],
        default="both",
        help="GPU hypothesis filter (default: both).",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print machine-readable JSON payload.",
    )
    add_color_argument(parser)
    return parser


def _load_cpu_job_id(run_dir: Path) -> str | None:
    jobs_json = run_dir / "jobs.json"
    if not jobs_json.exists():
        return None
    try:
        payload = json.loads(jobs_json.read_text(encoding="utf-8"))
        jobs = payload.get("jobs", {})
        cpu = jobs.get("cpu_precompute", {})
        jid = cpu.get("job_id")
        return str(jid) if jid else None
    except Exception:
        return None


def _point_needs(row: Any) -> dict[str, bool]:
    signal_ok = bool(row.signal_chain_exists and row.signal_stats_exists)
    no_signal_ok = bool(
        row.no_signal_chain_exists and row.no_signal_stats_exists
    )
    any_chain = bool(row.signal_chain_exists or row.no_signal_chain_exists)

    return {
        "cpu": not any_chain,
        "gpu_signal_fit": not signal_ok,
        "gpu_no_signal": not no_signal_ok,
    }


def _build_point_commands(
    *, row: Any, stage: str, hypothesis: str
) -> tuple[list[str], list[str], dict[str, bool]]:
    run_dir = Path(str(row.run_dir))
    needs = _point_needs(row)
    notes: list[str] = []
    commands: list[str] = []

    if stage in {"cpu", "all"} and needs["cpu"]:
        commands.append(f'valska-bayeseor-submit "{run_dir}" --stage cpu')

    if stage in {"gpu", "all"}:
        want_signal = hypothesis in {"signal_fit", "both"}
        want_no_signal = hypothesis in {"no_signal", "both"}

        need_signal = needs["gpu_signal_fit"] and want_signal
        need_no_signal = needs["gpu_no_signal"] and want_no_signal

        if need_signal and need_no_signal:
            commands.append(
                f'valska-bayeseor-submit "{run_dir}" --stage gpu --hypothesis both'
            )
        elif need_signal:
            commands.append(
                f'valska-bayeseor-submit "{run_dir}" --stage gpu --hypothesis signal_fit'
            )
        elif need_no_signal:
            commands.append(
                f'valska-bayeseor-submit "{run_dir}" --stage gpu --hypothesis no_signal'
            )

        if (need_signal or need_no_signal) and needs["cpu"]:
            notes.append("CPU outputs missing: run CPU stage before GPU")

        if (need_signal or need_no_signal) and not row.jobs_exists:
            notes.append(
                "No jobs.json: GPU dependency job-id may be unavailable"
            )

        if (need_signal or need_no_signal) and row.jobs_exists:
            cpu_job_id = _load_cpu_job_id(run_dir)
            if cpu_job_id is not None:
                notes.append(
                    f"Found CPU job id hint in jobs.json: {cpu_job_id}"
                )

    return commands, notes, needs


def _format_status(status: object, *, colors: CliColors) -> str:
    text = str(status)
    if text == "ok":
        return colors.success(text)
    if text == "partial":
        return colors.warning(text)
    if text in ("missing", "invalid", "error"):
        return colors.error(text)
    return text


def _print_text(payload: dict[str, Any], *, colors: CliColors) -> None:
    summary = payload["summary"]
    print(colors.heading("Sweep resume suggestions:"))
    print(f"  sweep_dir:       {colors.path(payload['sweep_dir'])}")
    print(f"  stage:           {payload['stage']}")
    print(f"  hypothesis:      {payload['hypothesis']}")
    print(f"  points_total:    {summary['points_total']}")
    print(f"  points_targeted: {colors.warning(summary['points_targeted'])}")
    print(f"  commands_total:  {colors.warning(summary['commands_total'])}")

    print("\n" + colors.heading("Per-point commands:"))
    rows = payload["points"]
    if not rows:
        print("  (none)")
        return

    for row in rows:
        print(
            "  - "
            f"{row['run_label']} ({row['perturb_parameter']}={row['perturb_frac']:+.3f})"
        )
        print(
            f"      status: "
            f"{_format_status(row['point_status'], colors=colors)}"
        )
        for cmd in row["commands"]:
            print(f"      {colors.success(cmd)}")
        for note in row["notes"]:
            print(f"      note: {colors.warning(note)}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        health = inspect_sweep_health(Path(args.sweep_dir))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    point_rows: list[dict[str, Any]] = []
    for row in health.point_rows:
        commands, notes, needs = _build_point_commands(
            row=row,
            stage=str(args.stage),
            hypothesis=str(args.hypothesis),
        )
        if not commands:
            continue
        point_rows.append(
            {
                "run_label": row.run_label,
                "perturb_parameter": row.perturb_parameter,
                "perturb_frac": row.perturb_frac,
                "run_dir": row.run_dir,
                "point_status": row.point_status,
                "needs": needs,
                "commands": commands,
                "notes": notes,
            }
        )

    payload = {
        "sweep_dir": str(health.sweep_dir),
        "stage": str(args.stage),
        "hypothesis": str(args.hypothesis),
        "summary": {
            "points_total": health.points_total,
            "points_targeted": len(point_rows),
            "commands_total": sum(len(row["commands"]) for row in point_rows),
        },
        "points": point_rows,
        "health": sweep_health_to_dict(health),
    }

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
