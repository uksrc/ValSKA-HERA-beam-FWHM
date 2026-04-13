#!/usr/bin/env python3
"""Command index/help for BayesEoR ValSKA CLIs."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from typing import Any


def _command_catalog() -> OrderedDict[str, dict[str, Any]]:
    return OrderedDict(
        {
            "valska-bayeseor-prepare": {
                "topic": "setup",
                "summary": "Prepare one BayesEoR run directory and scripts.",
            },
            "valska-bayeseor-submit": {
                "topic": "submission",
                "summary": "Submit CPU/GPU stages for one prepared run.",
            },
            "valska-bayeseor-sweep": {
                "topic": "submission",
                "summary": "Prepare and/or submit a parameter sweep.",
            },
            "valska-bayeseor-report": {
                "topic": "reporting",
                "summary": "Generate tables/plots for one sweep.",
            },
            "valska-bayeseor-list-sweeps": {
                "topic": "health",
                "summary": "Discover available sweep directories.",
            },
            "valska-bayeseor-sweep-status": {
                "topic": "health",
                "summary": "Inspect per-point completeness for one sweep.",
            },
            "valska-bayeseor-validate-sweep": {
                "topic": "health",
                "summary": "Validate one sweep with pass/fail exit codes.",
            },
            "valska-bayeseor-sweep-audit": {
                "topic": "health",
                "summary": "Aggregate discovery + status + validation across sweeps.",
            },
            "valska-bayeseor-resume": {
                "topic": "operations",
                "summary": "Suggest exact submit commands for incomplete points.",
            },
            "valska-bayeseor-report-all": {
                "topic": "operations",
                "summary": "Batch-generate reports across discovered sweeps.",
            },
            "valska-bayeseor-compare-sweeps": {
                "topic": "operations",
                "summary": "Compare report metrics between two sweeps.",
            },
            "valska-bayeseor-cleanup": {
                "topic": "operations",
                "summary": "Safe cleanup workflow (dry-run by default).",
            },
        }
    )


def _workflow_examples() -> list[dict[str, str]]:
    return [
        {
            "name": "Fresh sweep CPU+GPU submission",
            "command": (
                "valska-bayeseor-sweep --beam <beam> --sky <sky> --data <file.uvh5> "
                "--run-id <run_id> --fwhm-fracs 0.01 0.0 --submit all"
            ),
        },
        {
            "name": "Resume incomplete points",
            "command": "valska-bayeseor-resume /path/to/_sweeps/<run_id>",
        },
        {
            "name": "Batch reporting across sweeps",
            "command": "valska-bayeseor-report-all --beam <beam> --sky <sky>",
        },
        {
            "name": "Safe cleanup preview",
            "command": "valska-bayeseor-cleanup --all --json",
        },
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-bayeseor-help",
        description=(
            "Show a concise index of BayesEoR CLI commands and common workflows."
        ),
        epilog=(
            "Examples:\n"
            "  valska-bayeseor-help\n"
            "  valska-bayeseor-help --topic reporting\n"
            "  valska-bayeseor-help --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--topic",
        choices=["setup", "submission", "reporting", "health", "operations"],
        default=None,
        help="Filter commands by topic.",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    return parser


def _build_payload(topic: str | None) -> dict[str, Any]:
    catalog = _command_catalog()
    rows = []
    for command, info in catalog.items():
        if topic is not None and str(info["topic"]) != topic:
            continue
        rows.append(
            {
                "command": command,
                "topic": str(info["topic"]),
                "summary": str(info["summary"]),
            }
        )

    return {
        "topic_filter": topic,
        "available_topics": [
            "setup",
            "submission",
            "reporting",
            "health",
            "operations",
        ],
        "commands": rows,
        "workflows": _workflow_examples(),
        "notes": {
            "single_command_help": "Use '<command> --help' for command-local options.",
            "roadmap": (
                "Future idea: a single root 'valska-bayeseor' command with subcommands "
                "for all current tools."
            ),
        },
    }


def _print_text(payload: dict[str, Any]) -> None:
    topic = payload["topic_filter"]
    if topic is None:
        print("BayesEoR command index:")
    else:
        print(f"BayesEoR command index (topic={topic}):")

    if not payload["commands"]:
        print("  (no commands matched)")
    else:
        for row in payload["commands"]:
            print(f"  - {row['command']} [{row['topic']}]")
            print(f"      {row['summary']}")

    print("\nCommon workflows:")
    for wf in payload["workflows"]:
        print(f"  - {wf['name']}")
        print(f"      {wf['command']}")

    print("\nNotes:")
    print(f"  - {payload['notes']['single_command_help']}")
    print(f"  - {payload['notes']['roadmap']}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _build_payload(args.topic)

    if args.json_out:
        print(json.dumps(payload, indent=2))
        return 0

    _print_text(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
