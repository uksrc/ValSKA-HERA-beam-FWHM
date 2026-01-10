from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from .runner import BayesEoRInstall, CondaRunner, ContainerRunner
from .setup import prepare_bayeseor_run
from .submit import SubmissionError, submit_bayeseor_run

_STAGE = Literal["none", "cpu", "gpu", "all"]
_HYP = Literal["signal_fit", "no_signal", "both"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _format_run_label_from_fwhm_frac(frac: float) -> str:
    """
    Must match cli_prepare.py formatting so directory layout is predictable.
    """
    s = f"{frac:+.1e}"
    if s.startswith("+"):
        s = s[1:]
    return f"fwhm_{s}"


def _default_fwhm_fracs() -> list[float]:
    return [-0.10, -0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05, 0.10]


def sweep_root(results_root: Path, scenario: str, run_id: str) -> Path:
    """
    Central sweep output location.

    Layout:
      <results_root>/bayeseor/<scenario>/_sweeps/<run_id>/
    """
    return results_root / "bayeseor" / scenario / "_sweeps" / run_id


def sweep_point_dir(
    results_root: Path, scenario: str, run_id: str, run_label: str
) -> Path:
    """
    Per-point run directory for sweeps.

    Layout:
      <results_root>/bayeseor/<scenario>/_sweeps/<run_id>/<run_label>/
    """
    return sweep_root(results_root, scenario, run_id) / run_label


def _jobs_path(run_dir: Path) -> Path:
    return run_dir / "jobs.json"


def archive_jobs_json(run_dir: Path) -> Path | None:
    """
    Archive run_dir/jobs.json -> run_dir/jobs_<UTCSTAMP>.json

    Returns the archived path if an archive was created, else None.
    """
    jp = _jobs_path(run_dir)
    if not jp.exists():
        return None
    archived = run_dir / f"jobs_{_utc_now_compact()}.json"
    jp.rename(archived)
    return archived


@dataclass(frozen=True)
class SweepPoint:
    fwhm_perturb_frac: float
    run_label: str
    run_dir: Path
    manifest_json: Path


@dataclass(frozen=True)
class SweepResult:
    results_root: Path
    scenario: str
    run_id: str
    data_path: Path
    created_utc: str
    sweep_dir: Path
    sweep_manifest_json: Path
    template_yaml: Path
    points: list[SweepPoint]
    submit_results: list[dict[str, Any]]


def write_sweep_manifest(
    *,
    results_root: Path,
    scenario: str,
    run_id: str,
    data_path: Path,
    template_yaml: Path,
    sweep_dir: Path,
    points: list[SweepPoint],
    submit_results: list[dict[str, Any]] | None = None,
) -> Path:
    sweep_dir.mkdir(parents=True, exist_ok=True)
    out_path = sweep_dir / "sweep_manifest.json"

    payload: dict[str, Any] = {
        "results_root": str(results_root),
        "scenario": scenario,
        "run_id": run_id,
        "data_path": str(data_path),
        "template_yaml": str(template_yaml),
        "created_utc": _utc_now_iso(),
        "sweep_dir": str(sweep_dir),
        "points": [
            {
                "fwhm_perturb_frac": p.fwhm_perturb_frac,
                "run_label": p.run_label,
                "run_dir": str(p.run_dir),
                "manifest_json": str(p.manifest_json),
                "jobs_json": str(p.run_dir / "jobs.json")
                if (p.run_dir / "jobs.json").exists()
                else None,
            }
            for p in points
        ],
    }

    if submit_results is not None:
        payload["submit_results"] = submit_results

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def run_fwhm_sweep(
    *,
    # Prepare inputs
    template_yaml: Path,
    install: BayesEoRInstall,
    runner: CondaRunner | ContainerRunner,
    results_root: Path,
    scenario: str,
    run_id: str,
    data_path: Path,
    slurm_cpu: dict[str, object] | None = None,
    slurm_gpu: dict[str, object] | None = None,
    overrides: dict[str, str] | None = None,
    fwhm_fracs: Iterable[float] | None = None,
    unique: bool = False,
    # Optional submit inputs
    submit: _STAGE = "none",
    hypothesis: _HYP = "both",
    depend_afterok: str | None = None,
    sbatch_exe: str = "sbatch",
    submit_dry_run: bool = False,
    force: bool = False,
    resubmit: bool = False,
    record: Literal["jobs.json", "manifest"] = "jobs.json",
    # Dry-run for the sweep as a whole (no prepare, no submit)
    dry_run: bool = False,
) -> SweepResult:
    """
    Orchestrate a sweep over multiple fwhm_perturb_frac values.

    Sweep directory layout
    ----------------------
    For sweeps we intentionally colocate all points so they can be archived/removed as a unit:

      <results_root>/bayeseor/<scenario>/_sweeps/<run_id>/<run_label>/

    (This differs from single-run layout, which is:
      <results_root>/bayeseor/<scenario>/<run_label>/<run_id>/ )

    Behaviour
    ---------
    - Prepares one run_dir per fwhm frac (stable by default unless unique=True).
    - Optionally submits per run_dir via submit_bayeseor_run with stage cpu/gpu/all.
    - Writes/updates sweep_manifest.json under:
        <results_root>/bayeseor/<scenario>/_sweeps/<run_id>/

    Resubmission behaviour
    ----------------------
    - If resubmit=True and submit_dry_run=False, for each point we archive jobs.json
      (if present) to jobs_<timestamp>.json before submitting.
    - This enables "GPU-only resubmit across sweep" safely:
        submit="gpu", resubmit=True
    """
    results_root = Path(results_root).expanduser().resolve()
    data_path = Path(data_path).expanduser().resolve()
    template_yaml = Path(template_yaml).expanduser().resolve()

    fracs = list(_default_fwhm_fracs() if fwhm_fracs is None else fwhm_fracs)
    if not fracs:
        raise ValueError("No FWHM fractions provided for sweep.")

    sweep_dir = sweep_root(results_root, scenario, run_id)
    sweep_manifest_path = sweep_dir / "sweep_manifest.json"

    points: list[SweepPoint] = []
    submit_results: list[dict[str, Any]] = []

    # --------------------
    # Dry-run: compute intended run_dirs only
    # --------------------
    if dry_run:
        for frac in fracs:
            run_label = _format_run_label_from_fwhm_frac(float(frac))
            base = sweep_point_dir(results_root, scenario, run_id, run_label)
            run_dir = base / _utc_now_compact() if unique else base
            manifest_json = run_dir / "manifest.json"
            points.append(
                SweepPoint(
                    fwhm_perturb_frac=float(frac),
                    run_label=run_label,
                    run_dir=run_dir,
                    manifest_json=manifest_json,
                )
            )

        return SweepResult(
            results_root=results_root,
            scenario=scenario,
            run_id=run_id,
            data_path=data_path,
            created_utc=_utc_now_iso(),
            sweep_dir=sweep_dir,
            sweep_manifest_json=sweep_manifest_path,
            template_yaml=template_yaml,
            points=points,
            submit_results=[],
        )

    # --------------------
    # Prepare each point
    # --------------------
    for frac in fracs:
        frac_f = float(frac)
        run_label = _format_run_label_from_fwhm_frac(frac_f)

        base_run_dir = sweep_point_dir(
            results_root, scenario, run_id, run_label
        )
        run_dir = base_run_dir / _utc_now_compact() if unique else base_run_dir

        out = prepare_bayeseor_run(
            template_yaml=template_yaml,
            install=install,
            runner=runner,
            results_root=results_root,
            scenario=scenario,
            run_label=run_label,
            run_dir=run_dir,  # explicit: sweep layout
            unique=False,  # unique already handled above (if desired)
            data_path=data_path,
            overrides=overrides or {},
            slurm_cpu=slurm_cpu or {},
            slurm_gpu=slurm_gpu or {},
            fwhm_perturb_frac=frac_f,
        )

        prepared_run_dir = Path(str(out["run_dir"])).expanduser().resolve()
        manifest_json = Path(str(out["manifest_json"])).expanduser().resolve()

        points.append(
            SweepPoint(
                fwhm_perturb_frac=frac_f,
                run_label=run_label,
                run_dir=prepared_run_dir,
                manifest_json=manifest_json,
            )
        )

    # --------------------
    # Submit stage(s) per point if requested
    # --------------------
    if submit != "none":
        for p in points:
            archived: Path | None = None

            # If resubmitting, archive per-run jobs.json first (unless submit_dry_run).
            if resubmit and not submit_dry_run:
                try:
                    archived = archive_jobs_json(p.run_dir)
                except Exception as e:
                    submit_results.append(
                        {
                            "run_dir": str(p.run_dir),
                            "error": f"Failed to archive jobs.json: {e}",
                            "stage": submit,
                            "hypothesis": hypothesis,
                            "dry_run": bool(submit_dry_run),
                        }
                    )
                    continue

            try:
                submit_force = bool(force or resubmit)

                res = submit_bayeseor_run(
                    p.run_dir,
                    stage="all" if submit == "all" else submit,  # type: ignore[arg-type]
                    hypothesis=hypothesis,
                    depend_afterok=depend_afterok,
                    sbatch_exe=sbatch_exe,
                    dry_run=submit_dry_run,
                    force=submit_force,
                    record=record,
                )

                if archived is not None:
                    res = dict(res)
                    res["archived_jobs_json"] = str(archived)

                submit_results.append(res)

            except SubmissionError as e:
                submit_results.append(
                    {
                        "run_dir": str(p.run_dir),
                        "error": str(e),
                        "stage": submit,
                        "hypothesis": hypothesis,
                        "dry_run": bool(submit_dry_run),
                        "archived_jobs_json": str(archived)
                        if archived is not None
                        else None,
                    }
                )

    # --------------------
    # Write sweep manifest (includes per-point jobs.json paths if present)
    # --------------------
    write_sweep_manifest(
        results_root=results_root,
        scenario=scenario,
        run_id=run_id,
        data_path=data_path,
        template_yaml=template_yaml,
        sweep_dir=sweep_dir,
        points=points,
        submit_results=submit_results if submit_results else None,
    )

    return SweepResult(
        results_root=results_root,
        scenario=scenario,
        run_id=run_id,
        data_path=data_path,
        created_utc=_utc_now_iso(),
        sweep_dir=sweep_dir,
        sweep_manifest_json=sweep_manifest_path,
        template_yaml=template_yaml,
        points=points,
        submit_results=submit_results,
    )
