from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

_STAGE = Literal["cpu", "gpu", "all"]
_HYP = Literal["signal_fit", "no_signal", "both"]
_RECORD = Literal["jobs.json", "manifest"]

_JOBID_RE = re.compile(r"Submitted\s+batch\s+job\s+(\d+)\s*$", re.IGNORECASE)
_AFTEROK_RE = re.compile(r"afterok:(\d+)")


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
    run_dir: Path
    manifest_path: Path
    cpu_script: Path
    gpu_signal_fit_script: Path | None
    gpu_no_signal_script: Path | None
    cpu_precompute_driver_hypothesis: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(run_dir: Path) -> dict[str, Any]:
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

    cpu_script = _get_path("submit_sh_cpu_precompute", required=True)
    gpu_signal = _get_path("submit_sh_signal_fit_gpu_run", required=False)
    gpu_nosig = _get_path("submit_sh_no_signal_gpu_run", required=False)

    cpu_driver = (
        manifest.get("bayeseor", {}).get(
            "cpu_precompute_driver_hypothesis", None
        )
        if isinstance(manifest.get("bayeseor", {}), dict)
        else None
    )

    def _normalise(p: Path | None) -> Path | None:
        if p is None:
            return None
        return (run_dir / p).resolve() if not p.is_absolute() else p.resolve()

    cpu_script = _normalise(cpu_script)  # type: ignore[assignment]
    gpu_signal = _normalise(gpu_signal)
    gpu_nosig = _normalise(gpu_nosig)

    return SubmitPlan(
        run_dir=run_dir,
        manifest_path=manifest_path,
        cpu_script=cpu_script,  # type: ignore[arg-type]
        gpu_signal_fit_script=gpu_signal,
        gpu_no_signal_script=gpu_nosig,
        cpu_precompute_driver_hypothesis=str(cpu_driver)
        if cpu_driver is not None
        else None,
    )


def _ensure_script_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise MissingDependencyError(f"Missing {label} script: {path}")
    if not path.is_file():
        raise MissingDependencyError(f"{label} script is not a file: {path}")


def _run_sbatch(
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


def _safe_int_jobid(x: Any) -> str | None:
    if x is None:
        return None
    s = str(x).strip()
    return s if s.isdigit() else None


def _extract_cpu_jobid_from_existing(
    existing: dict[str, Any] | None,
) -> str | None:
    """
    Try to locate a CPU job id from an existing jobs.json structure.
    """
    if not isinstance(existing, dict):
        return None
    jobs = existing.get("jobs")
    if isinstance(jobs, dict):
        cpu = jobs.get("cpu_precompute")
        if isinstance(cpu, dict):
            jid = _safe_int_jobid(cpu.get("job_id"))
            if jid:
                return jid
        gpu = jobs.get("gpu")
        if isinstance(gpu, dict):
            dep = gpu.get("dependency")
            if isinstance(dep, str):
                m = _AFTEROK_RE.search(dep)
                if m:
                    return m.group(1)
    return None


def _merge_jobs_record(
    existing: dict[str, Any] | None, new_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge a new submission result into an existing jobs.json record.

    - Keeps stable top-level metadata (run_dir, manifest)
    - Updates "jobs" by stage (cpu_precompute, gpu)
    - Appends to "history" so we don't lose what happened
    """
    merged: dict[str, Any] = {}

    # Start from existing, then overlay stable fields from new_result
    if isinstance(existing, dict):
        merged.update(existing)

    # Always set these from new_result to reflect latest invocation context
    for k in ("run_dir", "manifest"):
        if k in new_result:
            merged[k] = new_result[k]

    merged["sbatch"] = new_result.get("sbatch", merged.get("sbatch", "sbatch"))
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
        # CPU stage record
        cpu = new_jobs.get("cpu_precompute")
        if isinstance(cpu, dict):
            merged_jobs["cpu_precompute"] = cpu

        # GPU stage record
        gpu = new_jobs.get("gpu")
        if isinstance(gpu, dict):
            merged_jobs["gpu"] = gpu

    merged["jobs"] = merged_jobs

    # Keep latest submitted timestamp and commands for convenience
    merged["submitted_utc"] = new_result.get(
        "submitted_utc", merged.get("submitted_utc")
    )
    merged["stage"] = new_result.get("stage", merged.get("stage"))
    merged["hypothesis"] = new_result.get(
        "hypothesis", merged.get("hypothesis")
    )
    merged["commands"] = new_result.get("commands", merged.get("commands", []))

    return merged


def write_jobs(run_dir: Path, jobs: dict[str, Any]) -> Path:
    p = _jobs_path(run_dir)
    p.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    return p


def submit_bayeseor_run(
    run_dir: Path,
    *,
    stage: _STAGE = "all",
    hypothesis: _HYP = "both",
    depend_afterok: str | None = None,
    sbatch_exe: str = "sbatch",
    dry_run: bool = False,
    force: bool = False,
    record: _RECORD = "jobs.json",
) -> dict[str, Any]:
    """
    Submit BayesEoR prepared scripts for a run_dir.

    Notes on jobs.json recording
    ----------------------------
    jobs.json is treated as a durable record that may be updated across invocations:
      - stage=cpu creates/updates jobs.cpu_precompute
      - stage=gpu appends/updates jobs.gpu
      - stage=all updates both

    We also keep a submission 'history' list so previous job ids are not lost.
    """
    plan = build_submit_plan(run_dir)

    _ensure_script_exists(plan.manifest_path, "manifest.json")
    _ensure_script_exists(plan.cpu_script, "CPU precompute")

    if record == "manifest":
        raise InvalidArgumentError(
            "record='manifest' is not enabled in the MVP to avoid mutating provenance. "
            "Use record='jobs.json' (default)."
        )

    existing_jobs = load_jobs(plan.run_dir)

    # Second-line guardrail: refuse re-submission of a stage if that stage is already recorded,
    # unless force=True. (cli_submit.py also enforces guardrails; this protects programmatic calls.)
    if existing_jobs is not None and not force:
        jobs = (
            existing_jobs.get("jobs")
            if isinstance(existing_jobs, dict)
            else None
        )
        if isinstance(jobs, dict):
            if (
                stage in ("cpu", "all")
                and isinstance(jobs.get("cpu_precompute"), dict)
                and jobs["cpu_precompute"].get("job_id")
            ):
                raise InvalidArgumentError(
                    f"CPU precompute already recorded in jobs.json for {plan.run_dir}. "
                    "Refusing to submit CPU again. Use --force or --resubmit."
                )
            if stage in ("gpu", "all") and isinstance(jobs.get("gpu"), dict):
                gpu = jobs["gpu"]
                sf = gpu.get("signal_fit")
                ns = gpu.get("no_signal")
                if (isinstance(sf, dict) and sf.get("job_id")) or (
                    isinstance(ns, dict) and ns.get("job_id")
                ):
                    raise InvalidArgumentError(
                        f"GPU jobs already recorded in jobs.json for {plan.run_dir}. "
                        "Refusing to submit GPU again. Use --force or --resubmit."
                    )

    result: dict[str, Any] = {
        "run_dir": str(plan.run_dir),
        "manifest": str(plan.manifest_path),
        "submitted_utc": _utc_now_iso(),
        "sbatch": sbatch_exe,
        "dry_run": bool(dry_run),
        "stage": stage,
        "hypothesis": hypothesis,
        "commands": [],
        "jobs": {},
    }

    cpu_jobid: str | None = None

    # --------------------
    # CPU submission
    # --------------------
    if stage in ("cpu", "all"):
        jobid, cmd = _run_sbatch(
            plan.cpu_script,
            dependency_afterok=None,
            sbatch_exe=sbatch_exe,
            cwd=plan.run_dir,
            dry_run=dry_run,
        )
        result["commands"].append(cmd)
        result["jobs"]["cpu_precompute"] = {
            "script": str(plan.cpu_script),
            "job_id": jobid,
            "cpu_precompute_driver_hypothesis": plan.cpu_precompute_driver_hypothesis,
        }
        cpu_jobid = jobid

    # --------------------
    # GPU submission
    # --------------------
    if stage in ("gpu", "all"):
        dep: str | None = None

        if cpu_jobid:
            dep = cpu_jobid
        elif depend_afterok:
            dep = _safe_int_jobid(depend_afterok)
        else:
            dep = _extract_cpu_jobid_from_existing(existing_jobs)

        if dep is None:
            if dry_run and stage == "all":
                dep = "<CPU_JOBID>"
            else:
                raise MissingDependencyError(
                    "GPU submission requested but no dependency job id is available. "
                    "Either submit CPU in the same invocation (--stage all), "
                    "or pass --depend-afterok <JOBID>, "
                    "or ensure jobs.json exists with a recorded cpu_precompute.job_id "
                    "(or an existing jobs.gpu.dependency like 'afterok:<JOBID>') and use --force."
                )

        gpu_jobs: dict[str, Any] = {"dependency": f"afterok:{dep}"}

        if hypothesis in ("signal_fit", "both"):
            if plan.gpu_signal_fit_script is None:
                raise MissingDependencyError(
                    "manifest does not contain a signal_fit GPU submit script artefact "
                    "(submit_sh_signal_fit_gpu_run)."
                )
            _ensure_script_exists(plan.gpu_signal_fit_script, "signal_fit GPU")
            jobid, cmd = _run_sbatch(
                plan.gpu_signal_fit_script,
                dependency_afterok=dep,
                sbatch_exe=sbatch_exe,
                cwd=plan.run_dir,
                dry_run=dry_run,
            )
            result["commands"].append(cmd)
            gpu_jobs["signal_fit"] = {
                "script": str(plan.gpu_signal_fit_script),
                "job_id": jobid,
            }

        if hypothesis in ("no_signal", "both"):
            if plan.gpu_no_signal_script is None:
                raise MissingDependencyError(
                    "manifest does not contain a no_signal GPU submit script artefact "
                    "(submit_sh_no_signal_gpu_run)."
                )
            _ensure_script_exists(plan.gpu_no_signal_script, "no_signal GPU")
            jobid, cmd = _run_sbatch(
                plan.gpu_no_signal_script,
                dependency_afterok=dep,
                sbatch_exe=sbatch_exe,
                cwd=plan.run_dir,
                dry_run=dry_run,
            )
            result["commands"].append(cmd)
            gpu_jobs["no_signal"] = {
                "script": str(plan.gpu_no_signal_script),
                "job_id": jobid,
            }

        result["jobs"]["gpu"] = gpu_jobs

    # --------------------
    # Record jobs.json (MERGE, do not overwrite)
    # --------------------
    if not dry_run:
        merged = _merge_jobs_record(existing_jobs, result)
        write_jobs(plan.run_dir, merged)
        # Return the merged record to reflect what is now on disk
        return merged

    return result
