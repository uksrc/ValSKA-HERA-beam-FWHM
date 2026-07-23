"""CLI entrypoint for submitting prepared pyuvsim runs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .submit import (
    InvalidArgumentError,
    SbatchError,
    SubmissionError,
    submit_pyuvsim_run,
)


def _utc_now_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _load_runtime_paths_yaml() -> dict[str, Any]:
    """
    Load config/runtime_paths.yaml from package data if available.

    We deliberately keep this lightweight:
    - If ruamel.yaml isn't available, we return {} and rely on CLI defaults.
    - If the file isn't found (e.g. during some dev layouts), we return {}.
    """
    try:
        from importlib.resources import files  # type: ignore
    except Exception:
        return {}

    try:
        runtime_path = files("valska").joinpath("config/runtime_paths.yaml")
    except Exception:
        return {}

    try:
        runtime_text = runtime_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    try:
        from ruamel.yaml import YAML  # type: ignore
    except Exception:
        return {}

    try:
        y = YAML(typ="safe")
        data = y.load(runtime_text) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def _runtime_submit_defaults() -> dict[str, Any]:
    """Extract submit defaults from runtime_paths.yaml if available."""
    data = _load_runtime_paths_yaml()
    pyuvsim = data.get("pyuvsim", {}) if isinstance(data, dict) else {}
    submit = pyuvsim.get("submit", {}) if isinstance(pyuvsim, dict) else {}

    sbatch_exe = submit.get("sbatch_exe", None)
    record = submit.get("record", None)
    refuse = submit.get("refuse_if_jobs_exist", None)

    defaults: dict[str, Any] = {}
    if isinstance(sbatch_exe, str) and sbatch_exe.strip():
        defaults["sbatch_exe"] = sbatch_exe.strip()
    if isinstance(record, str) and record.strip():
        defaults["record"] = record.strip()
    if isinstance(refuse, bool):
        defaults["refuse_if_jobs_exist"] = refuse

    return defaults


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for valska-pyuvsim-submit."""
    p = argparse.ArgumentParser(
        prog="valska-pyuvsim-submit",
        description=(
            "Submit a previously prepared pyuvsim run directory.\n\n"
            "Reads an existing run_dir (manifest.json + submit script) and "
            "submits the simulation stage via sbatch.\n\n"
            "Records job IDs to jobs.json by default."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    p.add_argument(
        "run_dir",
        type=str,
        help="Path to an existing prepared pyuvsim run directory (contains manifest.json).",
    )

    p.add_argument(
        "--stage",
        choices=["simulate", "all"],
        default="all",
        help="Which stage(s) to submit. For pyuvsim this is currently 'simulate' only.",
    )

    p.add_argument(
        "--sbatch-exe",
        default=None,
        help="sbatch executable name/path. Default comes from config/runtime_paths.yaml (pyuvsim.submit.sbatch_exe) or 'sbatch'.",
    )

    p.add_argument(
        "--record",
        choices=["jobs.json", "manifest"],
        default=None,
        help="Where to record job IDs. Default comes from config/runtime_paths.yaml (pyuvsim.submit.record) or 'jobs.json'.",
    )

    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the sbatch command that would be executed; do not submit jobs or write jobs.json.",
    )

    p.add_argument(
        "--force",
        action="store_true",
        help="Override guardrails (e.g. allow submission even if jobs.json already exists).",
    )

    p.add_argument(
        "--resubmit",
        action="store_true",
        help=(
            "Convenience flag for re-submission: if jobs.json exists, archive it "
            "(timestamped) then submit.\n"
            "Equivalent to --force plus archive."
        ),
    )

    p.add_argument(
        "--no-archive-existing-jobs",
        action="store_true",
        help="With --resubmit, do not archive an existing jobs.json (it may be overwritten).",
    )

    p.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print the full result object as JSON to stdout (useful for scripting).",
    )

    return p


def _archive_jobs_json(run_dir: Path) -> Path | None:
    """Archive jobs.json with a UTC timestamp suffix."""
    jobs_path = run_dir / "jobs.json"
    if not jobs_path.exists():
        return None
    archived = run_dir / f"jobs_{_utc_now_compact()}.json"
    jobs_path.rename(archived)
    return archived


def _load_jobs_json(path: Path) -> dict[str, Any] | None:
    """Best-effort load of jobs.json. Returns None if missing or unreadable."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _has_simulate_job(existing: dict[str, Any] | None) -> bool:
    """Return True if jobs.json already records a simulate job."""
    if not isinstance(existing, dict):
        return False
    jobs = existing.get("jobs")
    if not isinstance(jobs, dict):
        return False
    sim = jobs.get("simulate")
    return isinstance(sim, dict) and bool(sim.get("job_id"))


def _print_human(result: dict[str, Any]) -> None:
    """Print a human-readable submission summary."""
    run_dir = result.get("run_dir", "")
    dry_run = bool(result.get("dry_run", False))

    print(f"Run dir: {run_dir}")
    print(f"Dry run: {dry_run}")

    print("\nCommands:")
    for cmd in result.get("commands", []):
        print(f"  {cmd}")

    jobs = result.get("jobs", {}) or {}
    if not jobs:
        print("\nNo jobs recorded.")
        return

    print("\nJob IDs:")
    sim = jobs.get("simulate")
    if isinstance(sim, dict):
        jid = sim.get("job_id")
        print(f"  simulate: {jid if jid is not None else '(dry-run)'}")

    if not dry_run:
        print("\nRecorded:")
        print(f"  {Path(run_dir) / 'jobs.json'}")

    print("\nNext steps:")
    print("  - Check `squeue -u $USER` to see submitted jobs.")
    print(
        "  - Inspect logs referenced by the submit script in the run directory."
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for valska-pyuvsim-submit."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir).expanduser().resolve()
    jobs_path = run_dir / "jobs.json"

    # Apply runtime_paths.yaml defaults unless user explicitly provided CLI values.
    rt = _runtime_submit_defaults()

    sbatch_exe = (
        args.sbatch_exe
        if args.sbatch_exe is not None
        else rt.get("sbatch_exe", "sbatch")
    )
    record = (
        args.record
        if args.record is not None
        else rt.get("record", "jobs.json")
    )

    # Guardrail policy: default from YAML, but user can override with --force/--resubmit.
    refuse_if_jobs_exist = rt.get("refuse_if_jobs_exist", True)
    force = bool(args.force)

    existing = _load_jobs_json(jobs_path)
    sim_exists = _has_simulate_job(existing)

    # Resubmit convenience: archive jobs.json + proceed.
    if args.resubmit:
        force = True
        if not args.no_archive_existing_jobs:
            try:
                archived = _archive_jobs_json(run_dir)
                if archived is not None and not args.dry_run:
                    print(f"Archived existing jobs.json -> {archived}")
                existing = None
                sim_exists = False
            except Exception as e:
                print(
                    f"ERROR: Failed to archive existing jobs.json: {e}",
                    file=sys.stderr,
                )
                return 1

    # Stage-aware guardrails.
    if refuse_if_jobs_exist and not force and jobs_path.exists():
        if args.stage in {"simulate", "all"}:
            if sim_exists:
                print(
                    "ERROR: jobs.json already records a simulate job; refusing to submit again.\n"
                    "Use --force to override, or --resubmit to archive and requeue.",
                    file=sys.stderr,
                )
                return 2

            print(
                "ERROR: jobs.json already exists; refusing to submit to avoid accidental double submission.\n"
                "Use --force to override, or --resubmit to archive and requeue.",
                file=sys.stderr,
            )
            return 2

    try:
        result = submit_pyuvsim_run(
            run_dir,
            stage=args.stage,
            sbatch_exe=sbatch_exe,
            dry_run=args.dry_run,
            force=force,
            record=record,
        )
    except SbatchError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4
    except InvalidArgumentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except SubmissionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130

    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        _print_human(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
