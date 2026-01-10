from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ... import __version__
from .runner import BayesEoRInstall, CondaRunner, ContainerRunner
from .slurm import render_submit_script


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# -----------------------------------------------------------------------------
# YAML IO (ruamel.yaml)
# -----------------------------------------------------------------------------

_YAML = YAML(typ="rt")  # round-trip
_YAML.preserve_quotes = True
_YAML.indent(mapping=2, sequence=4, offset=2)
_YAML.width = 4096  # avoid wrapping compact priors blocks


def _load_yaml(path: Path) -> CommentedMap:
    with path.open("r", encoding="utf-8") as f:
        data = _YAML.load(f)
    if not isinstance(data, CommentedMap):
        raise ValueError(f"Expected a mapping at top-level of YAML: {path}")
    return data


def _dump_yaml(data: Mapping[str, Any], path: Path) -> None:
    if isinstance(data, CommentedMap):
        out = data
    else:
        out = CommentedMap(dict(data))

    with path.open("w", encoding="utf-8") as f:
        _YAML.dump(out, f)


def _as_flow_seq(seq: Any) -> CommentedSeq:
    if isinstance(seq, CommentedSeq):
        out = seq
    else:
        out = CommentedSeq(seq)

    out.fa.set_flow_style()
    for i, item in enumerate(list(out)):
        if isinstance(item, (list, tuple, CommentedSeq)):
            inner = (
                item if isinstance(item, CommentedSeq) else CommentedSeq(item)
            )
            inner.fa.set_flow_style()
            out[i] = inner
    return out


# -----------------------------------------------------------------------------
# FWHM perturbation
# -----------------------------------------------------------------------------


def _apply_fwhm_perturbation(
    cfg: CommentedMap,
    *,
    fwhm_perturb_frac: float | None,
) -> dict[str, Any] | None:
    if fwhm_perturb_frac is None:
        return None

    if "fwhm_deg" not in cfg:
        raise KeyError(
            "Cannot apply FWHM perturbation: config has no 'fwhm_deg' key."
        )

    try:
        base = float(cfg["fwhm_deg"])
    except Exception as e:
        raise ValueError(
            f"Config 'fwhm_deg' is not numeric: {cfg['fwhm_deg']}"
        ) from e

    factor = 1.0 + float(fwhm_perturb_frac)
    new_val = base * factor
    cfg["fwhm_deg"] = new_val

    return {
        "type": "multiplicative",
        "fwhm_deg_base": base,
        "fwhm_perturb_frac": float(fwhm_perturb_frac),
        "factor": factor,
        "fwhm_deg_new": new_val,
    }


# -----------------------------------------------------------------------------
# Hypothesis materialisation
# -----------------------------------------------------------------------------


def _materialise_hypothesis_config(
    base_cfg: CommentedMap,
    *,
    hypothesis: str,
    run_dir: Path,
) -> CommentedMap:
    if hypothesis not in {"signal_fit", "no_signal"}:
        raise ValueError("hypothesis must be one of: 'signal_fit', 'no_signal'")

    cfg = CommentedMap(base_cfg)

    base_out = run_dir / "output" / hypothesis
    cfg["output_dir"] = str(base_out)

    if hypothesis == "signal_fit":
        pri = cfg.get("signal_fit_priors", cfg.get("priors", None))
        if pri is None:
            raise KeyError(
                "signal_fit hypothesis requested but no priors found "
                "(expected 'signal_fit_priors' or 'priors')."
            )
        cfg["priors"] = _as_flow_seq(pri)
    else:
        pri = cfg.get("no_signal_priors", cfg.get("priors", None))
        if pri is None:
            raise KeyError(
                "no_signal hypothesis requested but no priors found "
                "(expected 'no_signal_priors' or 'priors')."
            )
        cfg["priors"] = _as_flow_seq(pri)

    for k in (
        "signal_fit_priors",
        "no_signal_priors",
        "signal_fit_output_dir",
        "no_signal_output_dir",
    ):
        if k in cfg:
            del cfg[k]

    return cfg


# -----------------------------------------------------------------------------
# Runner manifest
# -----------------------------------------------------------------------------


def _runner_manifest(runner: CondaRunner | ContainerRunner) -> dict[str, Any]:
    if isinstance(runner, CondaRunner):
        return {
            "type": "conda",
            "conda_activate": runner.conda_activate,
            "env_name": runner.env_name,
        }
    return {
        "type": "container",
        "apptainer_exe": runner.apptainer_exe,
        "image_path": str(runner.image_path),
        "bind_paths": [str(p) for p in runner.bind_paths],
    }


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def prepare_bayeseor_run(
    *,
    template_yaml: Path,
    install: BayesEoRInstall,
    runner: CondaRunner | ContainerRunner,
    results_root: Path,
    scenario: str,
    run_label: str,
    data_path: Path,
    overrides: Mapping[str, Any] | None = None,
    slurm: Mapping[str, object] | None = None,
    slurm_cpu: Mapping[str, object] | None = None,
    slurm_gpu: Mapping[str, object] | None = None,
    run_dir: Path | None = None,
    unique: bool = False,
    fwhm_perturb_frac: float | None = None,
    hypothesis: str = "both",
) -> dict[str, Path]:
    """
    Prepare a BayesEoR run directory containing hypothesis-specific artefacts.

    By default (hypothesis="both"), this prepares:
      - two BayesEoR configs:
          config_signal_fit.yaml
          config_no_signal.yaml
      - one shared CPU precompute submit script:
          submit_cpu_precompute.sh
      - two GPU run submit scripts:
          submit_signal_fit_gpu_run.sh
          submit_no_signal_gpu_run.sh
      - manifest.json (provenance)

    SLURM configuration
    -------------------
    Backwards compatible behaviour:
      - If `slurm_cpu` / `slurm_gpu` are not provided, `slurm` is used for both stages.
      - If `slurm_cpu` / `slurm_gpu` are provided, they are used for their respective stages.

    Notes
    -----
    - We assume BayesEoR is already installed/available via the runner environment.
    - Container support later: only runner + command-line changes; run artefacts remain the same.

    - Run directory semantics:
        *Recommended (resumable):*
          Pass an explicit ``run_dir`` (computed by the caller) and this function will
          write artefacts there without adding timestamps.

        *Legacy behaviour (unique by timestamp):*
          If ``run_dir`` is not provided and ``unique=True``, a UTC timestamp is appended.

        *Default:*
          If ``run_dir`` is not provided and ``unique=False``, the run directory is
          stable at:
              <results_root>/bayeseor/<scenario>/<run_label>/

    - FWHM perturbation semantics:
        If provided, ``fwhm_perturb_frac`` applies a multiplicative perturbation
        to ``fwhm_deg`` in the rendered config at prepare time.

    - CPU precompute sharing:
        The instrument transfer matrix precompute is typically shared between
        signal_fit and no_signal. We therefore generate a single CPU submit script,
        driven by one of the hypothesis configs (prefer signal_fit if present).
    """
    overrides = dict(overrides or {})

    if hypothesis not in {"signal_fit", "no_signal", "both"}:
        raise ValueError(
            "hypothesis must be one of: 'signal_fit', 'no_signal', 'both'"
        )

    # Resolve SLURM mappings (backwards compatible)
    if slurm_cpu is None:
        slurm_cpu = slurm
    if slurm_gpu is None:
        slurm_gpu = slurm

    results_root = Path(results_root).expanduser().resolve()

    # Determine run_dir
    if run_dir is not None:
        run_dir = Path(run_dir).expanduser().resolve()
    else:
        base_dir = results_root / "bayeseor" / scenario / run_label
        run_dir = base_dir / _utc_stamp() if unique else base_dir

    run_dir.mkdir(parents=True, exist_ok=not unique)

    base_cfg = _load_yaml(template_yaml)

    # Required linkage between ValSKA and BayesEoR:
    base_cfg["data_path"] = str(data_path)

    # Apply FWHM perturbation before overrides so overrides can still force a value.
    fwhm_prov = _apply_fwhm_perturbation(
        base_cfg, fwhm_perturb_frac=fwhm_perturb_frac
    )

    # Apply simple top-level overrides
    for k, v in overrides.items():
        base_cfg[k] = v

    # Decide which hypotheses to materialise
    if hypothesis == "both":
        hypotheses = ["signal_fit", "no_signal"]
    else:
        hypotheses = [hypothesis]

    cpu_precompute_driver_hypothesis = (
        "signal_fit" if "signal_fit" in hypotheses else hypotheses[0]
    )

    outputs: dict[str, Path] = {"run_dir": run_dir}

    # Write configs + GPU run scripts per hypothesis
    for hyp in hypotheses:
        hyp_cfg = _materialise_hypothesis_config(
            base_cfg, hypothesis=hyp, run_dir=run_dir
        )

        config_yaml = run_dir / f"config_{hyp}.yaml"
        _dump_yaml(hyp_cfg, config_yaml)

        submit_gpu = run_dir / f"submit_{hyp}_gpu_run.sh"
        submit_gpu.write_text(
            render_submit_script(
                runner=runner,
                install=install,
                config_yaml=config_yaml,
                run_dir=run_dir,
                slurm=slurm_gpu,
                mode="gpu_run",
            ),
            encoding="utf-8",
        )
        submit_gpu.chmod(0o750)

        outputs[f"config_yaml_{hyp}"] = config_yaml
        outputs[f"submit_sh_{hyp}_gpu_run"] = submit_gpu

    # One shared CPU precompute script (driven by chosen hypothesis config)
    cpu_config_yaml = outputs[f"config_yaml_{cpu_precompute_driver_hypothesis}"]
    submit_cpu = run_dir / "submit_cpu_precompute.sh"
    submit_cpu.write_text(
        render_submit_script(
            runner=runner,
            install=install,
            config_yaml=cpu_config_yaml,
            run_dir=run_dir,
            slurm=slurm_cpu,
            mode="cpu",
        ),
        encoding="utf-8",
    )
    submit_cpu.chmod(0o750)
    outputs["submit_sh_cpu_precompute"] = submit_cpu

    # Manifest
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "valska_version": __version__,
        "scenario": scenario,
        "run_label": run_label,
        "results_root": str(results_root),
        "run_dir": str(run_dir),
        "template_yaml": str(template_yaml),
        "data_path": str(data_path),
        "overrides": overrides,
        "hypothesis": hypothesis,
        "slurm": {
            "cpu": dict(slurm_cpu or {}),
            "gpu": dict(slurm_gpu or {}),
        },
        "bayeseor": {
            "install": {
                "repo_path": str(install.repo_path),
                "run_script": str(install.run_script),
            },
            "runner": _runner_manifest(runner),
            "fwhm_perturbation": fwhm_prov,
            "cpu_precompute_driver_hypothesis": cpu_precompute_driver_hypothesis,
        },
        "artefacts": {k: str(v) for k, v in outputs.items() if k != "run_dir"},
    }
    manifest_json = run_dir / "manifest.json"
    manifest_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    outputs["manifest_json"] = manifest_json

    return outputs
