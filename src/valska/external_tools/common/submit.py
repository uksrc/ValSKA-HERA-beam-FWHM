"""Submission helpers for prepared run directories."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    """Resolved paths needed to submit a prepared run."""

    run_dir: Path
    manifest_path: Path


def load_manifest(run_dir: Path) -> dict[str, Any]:
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
