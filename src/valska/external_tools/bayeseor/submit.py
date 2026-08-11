"""Submission helpers for BayesEoR prepared run directories."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from valska.external_tools.common.submit import (
    InvalidArgumentError,
    MissingDependencyError,
    Stage,
    SubmitPlan,
    _jobs_path,
    ensure_script_exists,
    get_path_from_artefacts,
    normalise_path,
    run_sbatch,
)
from valska.external_tools.common.utils import utc_now_iso

_STAGE = Literal["cpu", "gpu", "all"]
_HYP = Literal["signal_fit", "no_signal", "both"]
_RECORD = Literal["jobs.json", "manifest"]


_AFTEROK_RE = re.compile(r"afterok:(\d+)")
_CPU_MATRIX_MARKERS: dict[str, tuple[str, ...]] = {
    "Ninv": ("Ninv.h5", "Ninv.npz"),
    "T_Ninv_T": ("T_Ninv_T.h5", "T_Ninv_T.npz"),
}


class BayesEoRStage(Stage):
    CPU = "cpu_precompute"
    GPU = "gpu"
    # ALL = "all"


@dataclass()
class BayesEoRSubmitPlan(SubmitPlan):
    """Resolved paths needed to submit a prepared BayesEoR run."""

    cpu_script: Path = field(init=False)
    gpu_signal_fit_script: Path | None = field(init=False)
    gpu_no_signal_script: Path | None = field(init=False)
    cpu_precompute_driver_hypothesis: str | None = field(init=False)

    def __post_init__(self):
        super().__post_init__()

        artefacts = self.load_manifest().get("artefacts", {})
        if not isinstance(artefacts, dict):
            raise MissingDependencyError(
                "manifest['artefacts'] is missing or not a dict"
            )

        cpu_script = get_path_from_artefacts(
            artefacts, "submit_sh_cpu_precompute", required=True
        )
        gpu_signal = get_path_from_artefacts(
            artefacts, "submit_sh_signal_fit_gpu_run", required=False
        )
        gpu_nosig = get_path_from_artefacts(
            artefacts, "submit_sh_no_signal_gpu_run", required=False
        )

        self.cpu_precompute_driver_hypothesis = (
            self.load_manifest()
            .get("bayeseor", {})
            .get("cpu_precompute_driver_hypothesis", None)
            if isinstance(self.load_manifest().get("bayeseor", {}), dict)
            else None
        )

        self.cpu_script = normalise_path(self.run_dir, cpu_script)  # type: ignore[assignment]
        self.gpu_signal_fit_script = normalise_path(self.run_dir, gpu_signal)
        self.gpu_no_signal_script = normalise_path(self.run_dir, gpu_nosig)


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


def _find_completed_cpu_precompute_matrix_dir(run_dir: Path) -> Path | None:
    """
    Return a matrix-stack directory when CPU precompute outputs appear complete.

    BayesEoR GPU runs require the CPU-built matrix stack, most importantly the
    ``Ninv`` and ``T_Ninv_T`` artefacts. For the standard ValSKA-generated
    configs these are written beneath ``run_dir/matrices/...``.

    We treat CPU precompute as reusable only when both markers are present in
    the same matrix directory.
    """
    matrices_root = run_dir / "matrices"
    if not matrices_root.exists():
        return None

    candidate_dirs: list[set[Path]] = []
    for filenames in _CPU_MATRIX_MARKERS.values():
        dirs_for_marker: set[Path] = set()
        for filename in filenames:
            dirs_for_marker.update(
                p.parent for p in matrices_root.rglob(filename)
            )
        if not dirs_for_marker:
            return None
        candidate_dirs.append(dirs_for_marker)

    common_dirs = set.intersection(*candidate_dirs)
    if not common_dirs:
        return None

    return max(common_dirs, key=lambda p: p.stat().st_mtime)


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

    Parameters
    ----------
    run_dir
        Prepared run directory.
    stage
        Which stage(s) to submit: "cpu", "gpu", or "all".
    hypothesis
        Which GPU hypothesis to run: "signal_fit", "no_signal", or "both".
    depend_afterok
        Optional sbatch job id to depend on for GPU submissions.
    sbatch_exe
        sbatch executable to invoke.
    dry_run
        If True, do not submit jobs; return the commands that would run.
    force
        If True, allow resubmission even if jobs.json indicates prior submissions.
    record
        Where to record submission metadata. Currently only "jobs.json" is supported.

    Returns
    -------
    dict
        A jobs.json-style record of the submission (merged if not dry_run).

    Notes on jobs.json recording
    ----------------------------
    jobs.json is treated as a durable record that may be updated across invocations:
      - stage=cpu creates/updates jobs.cpu_precompute
      - stage=gpu appends/updates jobs.gpu
      - stage=all updates both

    We also keep a submission 'history' list so previous job ids are not lost.
    """

    plan = BayesEoRSubmitPlan(
        run_dir.expanduser().resolve(), BayesEoRStage.CPU
    )

    ensure_script_exists(plan.manifest_path, "manifest.json")
    ensure_script_exists(plan.cpu_script, "CPU precompute")

    if record == "manifest":
        raise InvalidArgumentError(
            "record='manifest' is not enabled in the MVP to avoid mutating provenance. "
            "Use record='jobs.json' (default)."
        )

    existing_jobs = plan.load_jobs()

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
        "submitted_utc": utc_now_iso(),
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
        jobid, cmd = run_sbatch(
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
        dependency_source: str | None = None
        verified_matrix_dir: Path | None = None

        if cpu_jobid:
            dep = cpu_jobid
            dependency_source = "same_invocation_cpu"
        elif depend_afterok is not None:
            dep = _safe_int_jobid(depend_afterok)
            if dep is None:
                raise InvalidArgumentError(
                    "--depend-afterok must be a numeric SLURM job id."
                )
            dependency_source = "explicit_depend_afterok"
        elif dry_run and stage == "all":
            dep = "<CPU_JOBID>"
            dependency_source = "dry_run_placeholder"
        else:
            verified_matrix_dir = _find_completed_cpu_precompute_matrix_dir(
                plan.run_dir
            )
            if verified_matrix_dir is not None:
                dependency_source = "cpu_precompute_outputs_verified"
            else:
                dep = _extract_cpu_jobid_from_existing(existing_jobs)
                if dep is not None:
                    dependency_source = "jobs_json"

        if dep is None:
            if verified_matrix_dir is None:
                raise MissingDependencyError(
                    "GPU submission requested but neither a reusable CPU dependency "
                    "job id nor completed CPU precompute outputs are available. "
                    "Either submit CPU in the same invocation (--stage all), "
                    "or pass --depend-afterok <JOBID>, "
                    "or ensure jobs.json exists with a recorded cpu_precompute.job_id "
                    "(or an existing jobs.gpu.dependency like 'afterok:<JOBID>'), "
                    "or rerun CPU so BayesEoR writes the required matrix stack under "
                    "run_dir/matrices/."
                )

        gpu_jobs: dict[str, Any] = {
            "dependency": f"afterok:{dep}" if dep is not None else None,
            "dependency_source": dependency_source,
        }
        if verified_matrix_dir is not None:
            gpu_jobs["cpu_precompute_matrix_dir"] = str(verified_matrix_dir)

        if hypothesis in ("signal_fit", "both"):
            if plan.gpu_signal_fit_script is None:
                raise MissingDependencyError(
                    "manifest does not contain a signal_fit GPU submit script artefact "
                    "(submit_sh_signal_fit_gpu_run)."
                )
            ensure_script_exists(plan.gpu_signal_fit_script, "signal_fit GPU")
            jobid, cmd = run_sbatch(
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
            ensure_script_exists(plan.gpu_no_signal_script, "no_signal GPU")
            jobid, cmd = run_sbatch(
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
        merged = plan.merge_jobs_record(result)
        write_jobs(plan.run_dir, merged)
        # Return the merged record to reflect what is now on disk
        return merged

    return result
