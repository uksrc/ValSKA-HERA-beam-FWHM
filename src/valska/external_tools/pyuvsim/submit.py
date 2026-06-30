"""Submission helpers for pyuvsim prepared run directories."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

_STAGE = Literal["simulate", "all"]
_RECORD = Literal["jobs.json", "manifest"]

_JOBID_RE = re.compile(r"Submitted\s+batch\s+job\s+(\d+)\s*$", re.IGNORECASE)


class SubmissionError(RuntimeError):
    """Raised when submission cannot proceed safely or sbatch fails."""


class InvalidArgumentError(SubmissionError):
    """Raised when CLI arguments are invalid for submission."""


class MissingDependencyError(SubmissionError):
    """Raised when required inputs or artefacts are missing."""


class SbatchError(SubmissionError):
    """Raised when sbatch fails or returns unparseable output."""


@dataclass(frozen=True)
class SubmitPlan:
    """Resolved paths needed to submit a prepared pyuvsim run."""

    run_dir: Path
    manifest_path: Path
    simulate_script: Path


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(run_dir: Path) -> dict[str, Any]:
    """
    Load and parse manifest.json from a prepared run directory.
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise MissingDependencyError(
            f"Missing manifest.json in run_dir: {run_dir}"
        )
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        raise MissingDependencyError(
            f"Failed to parse manifest.json: {manifest_path}\n{e}"
        ) from e


def build_submit_plan(run_dir: Path) -> SubmitPlan:
    """
    Create a submission plan from an existing prepared run_dir.

    This reads manifest.json and uses manifest['artefacts'] paths rather than guessing filenames.
    """
    run_dir = Path(run_dir).expanduser().resolve()
    manifest_path = run_dir / "manifest.json"
    manifest = load_manifest(run_dir)

    artefacts = manifest.get("artefacts", {})
    if not isinstance(artefacts, dict):
        raise MissingDependencyError(
            "manifest['artefacts'] is missing or not a dict"
        )

    def _get_path(key: str, required: bool = True) -> Path | None:
        p = artefacts.get(key)
        if p is None:
            if required:
                raise MissingDependencyError(
                    f"manifest artefact missing required key: {key}"
                )
            return None
        return Path(str(p)).expanduser()

    simulate_script = _get_path("submit_sh_simulate", required=True)

    def _normalise(p: Path | None) -> Path | None:
        if p is None:
            return None
        return (run_dir / p).resolve() if not p.is_absolute() else p.resolve()

    simulate_script = _normalise(simulate_script)

    return SubmitPlan(
        run_dir=run_dir,
        manifest_path=manifest_path,
        simulate_script=simulate_script,  # type: ignore[arg-type]
    )


def _ensure_script_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise MissingDependencyError(f"Missing {label} script: {path}")
    if not path.is_file():
        raise MissingDependencyError(f"{label} script is not a file: {path}")


def _run_sbatch(
    script: Path,
    *,
    sbatch_exe: str = "sbatch",
    cwd: Path | None = None,
    dry_run: bool = False,
) -> tuple[str | None, str]:
    """
    Returns (job_id, command_str). If dry_run=True, job_id is None.
    """
    cmd: list[str] = [sbatch_exe, str(script)]
    cmd_str = " ".join(cmd)

    if dry_run:
        return None, cmd_str

    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
    )

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()

    if proc.returncode != 0:
        raise SbatchError(
            "sbatch failed.\n"
            f"Command: {cmd_str}\n"
            f"Return code: {proc.returncode}\n"
            f"stdout:\n{out}\n"
            f"stderr:\n{err}\n"
        )

    m = _JOBID_RE.search(out)
    if not m:
        raise SbatchError(
            "Could not parse job id from sbatch stdout.\n"
            f"Command: {cmd_str}\n"
            f"stdout:\n{out}\n"
            f"stderr:\n{err}\n"
        )

    return m.group(1), cmd_str


def _jobs_path(run_dir: Path) -> Path:
    return run_dir / "jobs.json"


def load_jobs(run_dir: Path) -> dict[str, Any] | None:
    p = _jobs_path(run_dir)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as e:  # pragma: no cover
        raise SubmissionError(
            f"Failed to parse existing jobs.json: {p}\n{e}"
        ) from e


def _merge_jobs_record(
    existing: dict[str, Any] | None, new_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge a new submission result into an existing jobs.json record.

    - Keeps stable top-level metadata (run_dir, manifest)
    - Updates "jobs" by stage (simulate)
    - Appends to "history" so we don't lose what happened
    """
    merged: dict[str, Any] = {}

    if isinstance(existing, dict):
        merged.update(existing)

    for k in ("run_dir", "manifest"):
        if k in new_result:
            merged[k] = new_result[k]

    merged["sbatch"] = new_result.get("sbatch", merged.get("sbatch", "sbatch"))
    merged["dry_run"] = bool(new_result.get("dry_run", False))

    hist = merged.get("history")
    if not isinstance(hist, list):
        hist = []
    hist_entry = {k: v for k, v in new_result.items() if k != "history"}
    hist.append(hist_entry)
    merged["history"] = hist

    merged_jobs = merged.get("jobs")
    if not isinstance(merged_jobs, dict):
        merged_jobs = {}

    new_jobs = new_result.get("jobs")
    if isinstance(new_jobs, dict):
        sim = new_jobs.get("simulate")
        if isinstance(sim, dict):
            merged_jobs["simulate"] = sim

    merged["jobs"] = merged_jobs
    merged["submitted_utc"] = new_result.get(
        "submitted_utc", merged.get("submitted_utc")
    )
    merged["stage"] = new_result.get("stage", merged.get("stage"))
    merged["commands"] = new_result.get("commands", merged.get("commands", []))

    return merged


def write_jobs(run_dir: Path, jobs: dict[str, Any]) -> Path:
    p = _jobs_path(run_dir)
    p.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    return p


def submit_pyuvsim_run(
    run_dir: Path,
    *,
    stage: _STAGE = "all",
    sbatch_exe: str = "sbatch",
    dry_run: bool = False,
    force: bool = False,
    record: _RECORD = "jobs.json",
) -> dict[str, Any]:
    """
    Submit pyuvsim prepared scripts for a run_dir.

    Parameters
    ----------
    run_dir
        Prepared run directory.
    stage
        Which stage(s) to submit: "simulate" or "all".
    sbatch_exe
        sbatch executable to invoke.
    dry_run
        If True, do not submit jobs; return the command that would run.
    force
        If True, allow resubmission even if jobs.json indicates prior submissions.
    record
        Where to record submission metadata. Currently only "jobs.json" is supported.

    Returns
    -------
    dict
        A jobs.json-style record of the submission (merged if not dry_run).
    """
    plan = build_submit_plan(run_dir)

    _ensure_script_exists(plan.manifest_path, "manifest.json")
    _ensure_script_exists(plan.simulate_script, "simulate")

    if record == "manifest":
        raise InvalidArgumentError(
            "record='manifest' is not enabled in the MVP to avoid mutating provenance. "
            "Use record='jobs.json' (default)."
        )

    existing_jobs = load_jobs(plan.run_dir)

    # Second-line guardrail: refuse re-submission if simulate is already recorded,
    # unless force=True.
    if existing_jobs is not None and not force:
        jobs = (
            existing_jobs.get("jobs")
            if isinstance(existing_jobs, dict)
            else None
        )
        if isinstance(jobs, dict):
            sim = jobs.get("simulate")
            if isinstance(sim, dict) and sim.get("job_id"):
                raise InvalidArgumentError(
                    f"Simulate job already recorded in jobs.json for {plan.run_dir}. "
                    "Refusing to submit again. Use --force or --resubmit."
                )

    result: dict[str, Any] = {
        "run_dir": str(plan.run_dir),
        "manifest": str(plan.manifest_path),
        "submitted_utc": _utc_now_iso(),
        "sbatch": sbatch_exe,
        "dry_run": bool(dry_run),
        "stage": stage,
        "commands": [],
        "jobs": {},
    }

    if stage not in ("simulate", "all"):
        raise InvalidArgumentError(
            f"Unsupported stage for pyuvsim: {stage}. Expected 'simulate' or 'all'."
        )

    jobid, cmd = _run_sbatch(
        plan.simulate_script,
        sbatch_exe=sbatch_exe,
        cwd=plan.run_dir,
        dry_run=dry_run,
    )
    result["commands"].append(cmd)
    result["jobs"]["simulate"] = {
        "script": str(plan.simulate_script),
        "job_id": jobid,
    }

    if not dry_run:
        merged = _merge_jobs_record(existing_jobs, result)
        write_jobs(plan.run_dir, merged)
        return merged

    return result
