"""Submission helpers for prepared run directories."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

_JOBID_RE = re.compile(r"Submitted\s+batch\s+job\s+(\d+)\s*$", re.IGNORECASE)


class SubmissionError(RuntimeError):
    """Raised when submission cannot proceed safely or sbatch fails."""


class InvalidArgumentError(SubmissionError):
    """Raised when CLI arguments are invalid for submission."""


class MissingDependencyError(SubmissionError):
    """Raised when required inputs or artefacts are missing."""


class SbatchError(SubmissionError):
    """Raised when sbatch fails or returns unparseable output."""


class Stage(Enum):
    """Type to inherit for each tool's own Stage class"""


@dataclass()
class SubmitPlan:
    """Resolved paths, config, and methods needed to submit a prepared run."""

    run_dir: Path
    stage: Stage
    manifest_path: Path = field(init=False)

    def __post_init__(self):
        self.manifest_path = self.run_dir / "manifest.json"

    def load_manifest(self) -> dict[str, Any]:
        """
        Load and parse manifest.json from a prepared run directory.

        Parameters
        ----------
        run_dir
            Prepared run directory containing manifest.json.

        Returns
        -------
        dict
            Parsed manifest content.
        """
        if not self.manifest_path.exists():
            raise MissingDependencyError(
                f"Missing manifest.json in run_dir: {self.run_dir}"
            )
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                f"Failed to parse manifest.json: {self.manifest_path}\n{e}"
            ) from e

    def load_jobs(self) -> dict[str, Any] | None:
        p = _jobs_path(self.run_dir)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception as e:  # pragma: no cover
            raise SubmissionError(
                f"Failed to parse existing jobs.json: {p}\n{e}"
            ) from e

    def merge_jobs_record(self, new_result: dict[str, Any]) -> dict[str, Any]:
        """
        Merge a new submission result into an existing jobs.json record.

        - Keeps stable top-level metadata (run_dir, manifest)
        - Updates "jobs" by stage (cpu_precompute, gpu)
        - Appends to "history" so we don't lose what happened
        """
        merged: dict[str, Any] = {}

        # Start from existing, then overlay stable fields from new_result
        existing = self.load_jobs()
        if isinstance(existing, dict):
            merged.update(existing)

        # Always set these from new_result to reflect latest invocation context
        for k in ("run_dir", "manifest"):
            if k in new_result:
                merged[k] = new_result[k]

        merged["sbatch"] = new_result.get(
            "sbatch", merged.get("sbatch", "sbatch")
        )
        merged["dry_run"] = bool(new_result.get("dry_run", False))

        # Keep a full submission history (append-only)
        hist = merged.get("history")
        if not isinstance(hist, list):
            hist = []
        # store a compact record (not including any existing "history")
        hist_entry = {k: v for k, v in new_result.items() if k != "history"}
        hist.append(hist_entry)
        merged["history"] = hist

        # Merge jobs by stage
        merged_jobs = merged.get("jobs")
        if not isinstance(merged_jobs, dict):
            merged_jobs = {}

        new_jobs = new_result.get("jobs")
        if isinstance(new_jobs, dict):
            stage = new_jobs.get(self.stage.value)
            if isinstance(stage, dict):
                merged_jobs[self.stage.value] = stage

            # # CPU stage record
            # cpu = new_jobs.get("cpu_precompute")
            # if isinstance(cpu, dict):
            #     merged_jobs["cpu_precompute"] = cpu

            # # GPU stage record
            # gpu = new_jobs.get("gpu")
            # if isinstance(gpu, dict):
            #     merged_jobs["gpu"] = gpu

        merged["jobs"] = merged_jobs

        # Keep latest submitted timestamp and commands for convenience
        merged["submitted_utc"] = new_result.get(
            "submitted_utc", merged.get("submitted_utc")
        )
        merged["stage"] = new_result.get("stage", merged.get("stage"))
        merged["hypothesis"] = new_result.get(
            "hypothesis", merged.get("hypothesis")
        )
        merged["commands"] = new_result.get(
            "commands", merged.get("commands", [])
        )

        return merged


def get_path_from_artefacts(
    artefacts: dict[str, Any], key: str, required: bool = True
) -> Path | None:
    p = artefacts.get(key)
    if p is None:
        if required:
            raise MissingDependencyError(
                f"manifest artefact missing required key: {key}"
            )
        return None
    return Path(str(p)).expanduser()


def normalise_path(run_dir: Path, p: Path | None) -> Path | None:
    if p is None:
        return None
    return (run_dir / p).resolve() if not p.is_absolute() else p.resolve()


def ensure_script_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise MissingDependencyError(f"Missing {label} script: {path}")
    if not path.is_file():
        raise MissingDependencyError(f"{label} script is not a file: {path}")


def run_sbatch(
    script: Path,
    *,
    dependency_afterok: str | None = None,
    sbatch_exe: str = "sbatch",
    cwd: Path | None = None,
    dry_run: bool = False,
) -> tuple[str | None, str]:
    """
    Returns (job_id, command_str). If dry_run=True, job_id is None.
    """
    cmd: list[str] = [sbatch_exe]
    if dependency_afterok:
        cmd.append(f"--dependency=afterok:{dependency_afterok}")
    cmd.append(str(script))

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
