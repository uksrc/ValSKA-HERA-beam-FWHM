#!/usr/bin/env python3
"""Pre-flight inspection of UVH5 data files.

Runs cheap consistency checks (currently: does a file's name agree with
what its cited telescope config actually declares as the beam type)
against one or more files, or every ``*.uvh5`` file under a directory,
before they are used in an expensive analysis.

This is advisory only: it reports findings and, by default, always
exits 0. Pass --strict to exit non-zero when any check FAILs, e.g. for
use as a script-level gate later.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from valska.data_preflight.inspect import read_uvh5_header
from valska.data_preflight.registry import (
    CheckContext,
    CheckStatus,
    CheckTier,
    run_checks,
)

_STATUS_ORDER = {
    CheckStatus.FAIL: 0,
    CheckStatus.WARN: 1,
    CheckStatus.SKIP: 2,
    CheckStatus.PASS: 3,
}


def default_config_search_dirs() -> tuple[Path, ...]:
    """Directories to search for telescope configs cited in a file's
    history, by default: this repo's own shipped pyuvsim telescope
    configs.
    """

    try:
        import valska.external_tools.pyuvsim as pyuvsim_pkg

        templates_dir = Path(pyuvsim_pkg.__file__).parent / "templates"
        return (templates_dir / "telescope_config", templates_dir)
    except Exception:
        return ()


def discover_uvh5_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.uvh5")))
        elif path.is_file():
            files.append(path)
    return files


def inspect_file(
    path: Path,
    *,
    config_search_dirs: tuple[Path, ...],
    expected_beam_type: str | None,
    tiers: tuple[CheckTier, ...],
) -> dict[str, Any]:
    try:
        header = read_uvh5_header(path)
    except Exception as exc:  # noqa: BLE001
        return {
            "path": str(path),
            "error": f"failed to read header: {exc}",
            "checks": [],
        }

    ctx = CheckContext(
        path=path,
        header=header,
        config_search_dirs=config_search_dirs,
        expected_beam_type=expected_beam_type,
    )
    results = run_checks(ctx, tiers)
    results.sort(key=lambda r: _STATUS_ORDER[r.status])
    return {
        "path": str(path),
        "error": None,
        "checks": [r.to_dict() for r in results],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-data-preflight",
        description=(
            "Run cheap pre-flight consistency checks against UVH5 data "
            "files before using them in an expensive analysis."
        ),
        epilog=(
            "Examples:\n"
            "  valska-data-preflight path/to/file.uvh5\n"
            "  valska-data-preflight path/to/file.uvh5 "
            "--expected-beam-type airy\n"
            "  valska-data-preflight path/to/directory --json\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more UVH5 files, or directories to scan recursively.",
    )
    parser.add_argument(
        "--config-search-dir",
        dest="config_search_dirs",
        action="append",
        type=Path,
        default=None,
        help=(
            "Additional directory to search for telescope configs cited "
            "in a file's history. May be repeated. Added to (not "
            "replacing) the built-in default search directories."
        ),
    )
    parser.add_argument(
        "--expected-beam-type",
        default=None,
        choices=["gaussian", "airy", "uniform", "short_dipole"],
        help=(
            "If given, flag any file whose cited config declares a "
            "different beam type. Most useful in single-file mode."
        ),
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print machine-readable JSON payload instead of text.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit with a non-zero status if any check result is FAIL. "
            "Default is advisory-only: always exits 0 (I/O errors "
            "aside)."
        ),
    )
    return parser


def _print_text(reports: list[dict[str, Any]]) -> None:
    counts = {status.value: 0 for status in CheckStatus}
    flagged: list[str] = []

    for report in reports:
        print(f"=== {report['path']} ===")
        if report["error"]:
            print(f"  ERROR: {report['error']}")
            continue
        for check in report["checks"]:
            status = check["status"]
            counts[status] += 1
            print(
                f"  {check['check_id']}: {status.upper()} - {check['message']}"
            )
            for key, value in check["details"].items():
                if key == "history_tail":
                    continue
                print(f"      {key}: {value}")
        if any(c["status"] in ("fail", "warn") for c in report["checks"]):
            flagged.append(report["path"])

    print()
    print(
        "Summary: " + ", ".join(f"{k.upper()}={v}" for k, v in counts.items())
    )
    if flagged:
        print(f"Files with FAIL or WARN ({len(flagged)}):")
        for path in flagged:
            print(f"  - {path}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    search_dirs = default_config_search_dirs()
    if args.config_search_dirs:
        search_dirs = tuple(args.config_search_dirs) + search_dirs

    files = discover_uvh5_files(args.paths)
    if not files:
        print(
            "ERROR: no .uvh5 files found among the given paths",
            file=sys.stderr,
        )
        return 2

    reports = [
        inspect_file(
            path,
            config_search_dirs=search_dirs,
            expected_beam_type=args.expected_beam_type,
            tiers=(CheckTier.FAST,),
        )
        for path in files
    ]

    if args.json_out:
        print(json.dumps(reports, indent=2))
    else:
        _print_text(reports)

    if args.strict:
        any_fail = any(
            check["status"] == "fail"
            for report in reports
            for check in report["checks"]
        ) or any(report["error"] for report in reports)
        if any_fail:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
