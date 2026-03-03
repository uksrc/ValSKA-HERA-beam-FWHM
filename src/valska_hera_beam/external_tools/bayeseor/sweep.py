"""Sweep orchestration for BayesEoR perturbation studies."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .runner import BayesEoRInstall, CondaRunner, ContainerRunner
from .setup import prepare_bayeseor_run
from .submit import SubmissionError, submit_bayeseor_run

_STAGE = Literal["none", "cpu", "gpu", "all"]
_HYP = Literal["signal_fit", "no_signal", "both"]
_PERT = Literal["fwhm_deg", "antenna_diameter"]


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


def _format_run_label_from_antenna_diameter_frac(frac: float) -> str:
    """
    Must match cli_prepare.py formatting so directory layout is predictable.
    """
    s = f"{frac:+.1e}"
    if s.startswith("+"):
        s = s[1:]
    return f"antdiam_{s}"


def _format_run_label(*, perturb_parameter: _PERT, frac: float) -> str:
    if perturb_parameter == "fwhm_deg":
        return _format_run_label_from_fwhm_frac(frac)
    return _format_run_label_from_antenna_diameter_frac(frac)


def _default_fwhm_fracs() -> list[float]:
    return [-0.10, -0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05, 0.10]


def sweep_root(
    results_root: Path, beam_model: str, sky_model: str, run_id: str
) -> Path:
    """
    Central sweep output location.

    Layout:
      <results_root>/bayeseor/<beam_model>/<sky_model>/_sweeps/<run_id>/
    """
    return (
        results_root / "bayeseor" / beam_model / sky_model / "_sweeps" / run_id
    )


def sweep_point_dir(
    results_root: Path,
    beam_model: str,
    sky_model: str,
    run_id: str,
    *,
    variant: str,
    run_label: str,
) -> Path:
    """
    Per-point run directory for sweeps.

    Layout:
      <results_root>/bayeseor/<beam_model>/<sky_model>/_sweeps/<run_id>/<variant>/<run_label>/
    """
    return (
        sweep_root(results_root, beam_model, sky_model, run_id)
        / variant
        / run_label
    )


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
    """Metadata for a single sweep point."""

    perturb_parameter: _PERT
    perturb_frac: float
    run_label: str
    run_dir: Path
    manifest_json: Path

    @property
    def fwhm_perturb_frac(self) -> float | None:
        """Backward-compatible alias for legacy FWHM-only callers."""
        if self.perturb_parameter == "fwhm_deg":
            return self.perturb_frac
        return None


@dataclass(frozen=True)
class SweepResult:
    """Summary of a completed sweep run (prepare + optional submit)."""

    results_root: Path
    beam_model: str
    sky_model: str
    variant: str
    run_id: str
    perturb_parameter: _PERT
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
    beam_model: str,
    sky_model: str,
    variant: str,
    run_id: str,
    perturb_parameter: _PERT,
    data_path: Path,
    template_yaml: Path,
    sweep_dir: Path,
    points: list[SweepPoint],
    submit_results: list[dict[str, Any]] | None = None,
) -> Path:
    """
    Write sweep_manifest.json under the sweep directory.

    Parameters
    ----------
    results_root, beam_model, sky_model, variant, run_id
        Identify the sweep location and taxonomy.
    data_path
        Data path used for the sweep.
    template_yaml
        Template used for the sweep points.
    sweep_dir
        Target sweep directory.
    points
        Prepared sweep points.
    submit_results
        Optional submission results to include.

    Returns
    -------
    Path
        Path to the written sweep_manifest.json.
    """
    sweep_dir.mkdir(parents=True, exist_ok=True)
    out_path = sweep_dir / "sweep_manifest.json"

    payload: dict[str, Any] = {
        "results_root": str(results_root),
        "beam_model": beam_model,
        "sky_model": sky_model,
        "variant": variant,
        "run_id": run_id,
        "perturb_parameter": perturb_parameter,
        "data_path": str(data_path),
        "template_yaml": str(template_yaml),
        "created_utc": _utc_now_iso(),
        "sweep_dir": str(sweep_dir),
        "points": [
            {
                "perturb_parameter": p.perturb_parameter,
                "perturb_frac": p.perturb_frac,
                "fwhm_perturb_frac": p.perturb_frac
                if p.perturb_parameter == "fwhm_deg"
                else None,
                "antenna_diameter_perturb_frac": p.perturb_frac
                if p.perturb_parameter == "antenna_diameter"
                else None,
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
    beam_model: str,
    sky_model: str,
    variant: str,
    run_id: str,
    data_path: Path,
    slurm_cpu: dict[str, object] | None = None,
    slurm_gpu: dict[str, object] | None = None,
    overrides: dict[str, str] | None = None,
    perturb_parameter: _PERT = "fwhm_deg",
    perturb_fracs: Iterable[float] | None = None,
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
    Orchestrate a sweep over multiple perturbation values.

    Parameters
    ----------
    template_yaml
        BayesEoR template YAML to render.
    install
        BayesEoR installation metadata.
    runner
        Runner configuration (conda or container).
    results_root
        Root directory for results.
    beam_model, sky_model, variant, run_id
        Taxonomy fields and sweep identifier.
    data_path
        Input data path.
    slurm_cpu, slurm_gpu
        SLURM settings for CPU and GPU stages.
    overrides
        Template overrides applied to each run.
    perturb_parameter
        Which config key to perturb: ``fwhm_deg`` or ``antenna_diameter``.
    perturb_fracs
        Iterable of perturbation fractions to apply to ``perturb_parameter``.
    fwhm_fracs
        Backward-compatible alias for ``perturb_fracs`` when using
        ``perturb_parameter='fwhm_deg'``.
    unique
        If True, append a UTC timestamp to each run directory.
    submit
        Stage(s) to submit after prepare ("none", "cpu", "gpu", "all").
    hypothesis
        Which GPU hypothesis to submit ("signal_fit", "no_signal", "both").
    depend_afterok
        Optional sbatch job id to depend on for GPU submissions.
    sbatch_exe
        sbatch executable to invoke.
    submit_dry_run
        If True, do not submit; return the commands that would run.
    force
        If True, allow resubmission even if jobs.json indicates prior submissions.
    resubmit
        If True, archive jobs.json before submitting.
    record
        Where to record submission metadata. Currently only "jobs.json" is supported.
    dry_run
        If True, do not prepare or submit; only compute intended run paths.

    Returns
    -------
    SweepResult
        Summary of the sweep, including prepared points and submit results.

    Sweep directory layout
    ----------------------
    For sweeps we intentionally colocate all points so they can be archived/removed as a unit:

      <results_root>/bayeseor/<beam_model>/<sky_model>/_sweeps/<run_id>/<variant>/<run_label>/

    Behaviour
    ---------
    - Prepares one run_dir per perturbation frac (stable unless unique=True).
    - Optionally submits per run_dir via submit_bayeseor_run with stage cpu/gpu/all.
    - Writes/updates sweep_manifest.json under:
        <results_root>/bayeseor/<beam_model>/<sky_model>/_sweeps/<run_id>/

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

    beam_model = str(beam_model).strip()
    sky_model = str(sky_model).strip()
    variant = str(variant).strip()
    if not beam_model:
        raise ValueError("beam_model must be a non-empty string")
    if not sky_model:
        raise ValueError("sky_model must be a non-empty string")
    if not variant:
        raise ValueError("variant must be a non-empty string")
    if perturb_parameter not in {"fwhm_deg", "antenna_diameter"}:
        raise ValueError(
            "perturb_parameter must be one of: 'fwhm_deg', 'antenna_diameter'."
        )
    if perturb_fracs is not None and fwhm_fracs is not None:
        raise ValueError(
            "Provide either perturb_fracs or fwhm_fracs, not both."
        )

    fracs_in = perturb_fracs if perturb_fracs is not None else fwhm_fracs
    fracs = list(_default_fwhm_fracs() if fracs_in is None else fracs_in)
    if not fracs:
        raise ValueError("No perturbation fractions provided for sweep.")

    sweep_dir = sweep_root(results_root, beam_model, sky_model, run_id)
    sweep_manifest_path = sweep_dir / "sweep_manifest.json"

    points: list[SweepPoint] = []
    submit_results: list[dict[str, Any]] = []

    # --------------------
    # Dry-run: compute intended run_dirs only
    # --------------------
    if dry_run:
        for frac in fracs:
            run_label = _format_run_label(
                perturb_parameter=perturb_parameter, frac=float(frac)
            )
            base = sweep_point_dir(
                results_root,
                beam_model,
                sky_model,
                run_id,
                variant=variant,
                run_label=run_label,
            )
            run_dir = base / _utc_now_compact() if unique else base
            manifest_json = run_dir / "manifest.json"
            points.append(
                SweepPoint(
                    perturb_parameter=perturb_parameter,
                    perturb_frac=float(frac),
                    run_label=run_label,
                    run_dir=run_dir,
                    manifest_json=manifest_json,
                )
            )

        return SweepResult(
            results_root=results_root,
            beam_model=beam_model,
            sky_model=sky_model,
            variant=variant,
            run_id=run_id,
            perturb_parameter=perturb_parameter,
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
        run_label = _format_run_label(
            perturb_parameter=perturb_parameter, frac=frac_f
        )

        base_run_dir = sweep_point_dir(
            results_root,
            beam_model,
            sky_model,
            run_id,
            variant=variant,
            run_label=run_label,
        )
        run_dir = base_run_dir / _utc_now_compact() if unique else base_run_dir

        out = prepare_bayeseor_run(
            template_yaml=template_yaml,
            install=install,
            runner=runner,
            results_root=results_root,
            beam_model=beam_model,
            sky_model=sky_model,
            variant=variant,
            run_label=run_label,
            run_id=run_id,  # recorded provenance; run_dir is explicit sweep layout
            run_dir=run_dir,  # explicit: sweep layout
            unique=False,  # unique already handled above (if desired)
            data_path=data_path,
            overrides=overrides or {},
            slurm_cpu=slurm_cpu or {},
            slurm_gpu=slurm_gpu or {},
            fwhm_perturb_frac=frac_f
            if perturb_parameter == "fwhm_deg"
            else None,
            antenna_diameter_perturb_frac=frac_f
            if perturb_parameter == "antenna_diameter"
            else None,
            hypothesis="both",
        )

        prepared_run_dir = Path(str(out["run_dir"])).expanduser().resolve()
        manifest_json = Path(str(out["manifest_json"])).expanduser().resolve()

        points.append(
            SweepPoint(
                perturb_parameter=perturb_parameter,
                perturb_frac=frac_f,
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
    # Write sweep manifest
    # --------------------
    write_sweep_manifest(
        results_root=results_root,
        beam_model=beam_model,
        sky_model=sky_model,
        variant=variant,
        run_id=run_id,
        perturb_parameter=perturb_parameter,
        data_path=data_path,
        template_yaml=template_yaml,
        sweep_dir=sweep_dir,
        points=points,
        submit_results=submit_results if submit_results else None,
    )

    return SweepResult(
        results_root=results_root,
        beam_model=beam_model,
        sky_model=sky_model,
        variant=variant,
        run_id=run_id,
        perturb_parameter=perturb_parameter,
        data_path=data_path,
        created_utc=_utc_now_iso(),
        sweep_dir=sweep_dir,
        sweep_manifest_json=sweep_manifest_path,
        template_yaml=template_yaml,
        points=points,
        submit_results=submit_results,
    )
