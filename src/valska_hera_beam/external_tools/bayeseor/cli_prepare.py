#!/usr/bin/env python3
"""
Prepare a BayesEoR validation run "kit" under the ValSKA results directory.

This module is the importable CLI entrypoint used by the console script:
  valska-bayeseor-prepare

It preserves the behaviour of the development driver script:
  scripts/prepare_bayeseor_run.py

What this does
--------------
This generates reproducible run artefacts for a BayesEoR analysis, without
actually running BayesEoR itself.

Specifically, it:

1) Selects a BayesEoR YAML template shipped with ValSKA (or a user-provided template path).
2) Writes rendered BayesEoR config YAMLs into a run directory under:
      <results_root>/bayeseor/<scenario>/<run_label>/<run_id>/
   Optionally (with --unique) appends a timestamp:
      <results_root>/bayeseor/<scenario>/<run_label>/<run_id>/<timestamp>/
3) Sets BayesEoR output directories so that chains/evidence/logs are written inside that run directory.
4) Writes SLURM submit scripts that activate a conda environment and run BayesEoR:
      - submit_cpu_precompute.sh                 (shared CPU precompute stage: --cpu)
      - submit_<hyp>_gpu_run.sh (signal_fit/no_signal; GPU run stage: --gpu --run)
5) Writes a manifest.json with provenance (template used, data path, overrides, etc.).

What it does NOT do
-------------------
- It does not create a conda environment.
- It does not clone BayesEoR.
- It does not submit the job automatically (you run `sbatch ...` yourself).

Results root resolution
-----------------------
If --results-root is omitted, results_root is resolved in this order:
  1) config/runtime_paths.yaml (results_root key)
  2) $VALSKA_RESULTS_ROOT
  3) $SCRATCH/UKSRC/ValSKA/results
  4) $HOME/UKSRC/ValSKA/results
  5) ./results

Data path resolution
--------------------
--data is always required, but may be provided as either an absolute path or a
relative path.

If --data is relative and config/runtime_paths.yaml contains:

  data:
    root: /path/to/datasets

then ValSKA will resolve:

  --data foo/bar.uvh5  ->  /path/to/datasets/foo/bar.uvh5

Absolute paths are used as-is. The resolved absolute path is recorded in the
manifest.

Future container support
------------------------
Today this assumes a conda-based runner. In the future we will support Apptainer/Singularity
containers by swapping the "runner" configuration; the produced run directory, config YAML,
and manifest stay the same.

Usage examples
--------------
Prepare a stable run directory you can re-use (good for resuming):

  valska-bayeseor-prepare \\
      --data /path/to/dataset.uvh5 \\
      --scenario GSM_beam \\
      --run-label fwhm_-1.0e-01 \\
      --run-id resume_test

Prepare a unique run directory (good for parameter sweeps):

  valska-bayeseor-prepare \\
      --data /path/to/dataset.uvh5 \\
      --scenario GSM_beam \\
      --run-label fwhm_-1.0e-01 \\
      --run-id sweep \\
      --unique

Check where a run would be created (no filesystem changes):

  valska-bayeseor-prepare \\
      --data /path/to/dataset.uvh5 \\
      --scenario GSM_beam \\
      --run-label fwhm_-1.0e-01 \\
      --run-id test \\
      --dry-run
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from valska_hera_beam.external_tools.bayeseor import (
    BayesEoRInstall,
    CondaRunner,
    get_template_path,
    list_templates,
    prepare_bayeseor_run,
)
from valska_hera_beam.utils import get_default_path_manager, resolve_data_path


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _format_run_label_from_fwhm_frac(frac: float) -> str:
    s = f"{frac:+.1e}"
    if s.startswith("+"):
        s = s[1:]
    return f"fwhm_{s}"


def _compute_run_dir(
    *,
    results_root: Path,
    scenario: str,
    run_label: str,
    run_id: str,
    unique: bool,
) -> Path:
    base = results_root / "bayeseor" / scenario / run_label / run_id
    return base / _utc_stamp() if unique else base


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-bayeseor-prepare",
        description=(
            "Prepare a BayesEoR run kit (configs + SLURM scripts + manifest) under a ValSKA results directory."
        ),
    )

    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help=(
            "Path to the UVH5 dataset to analyse with BayesEoR.\n"
            "May be absolute or relative. If relative, and runtime_paths.yaml sets data.root,\n"
            "the path is resolved as <data.root>/<data>."
        ),
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=None,
        help=(
            "ValSKA results root directory. If omitted, resolves via config/runtime_paths.yaml then environment/defaults."
        ),
    )
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        help="Scenario name used in the results directory structure (e.g. GSM_beam).",
    )

    parser.add_argument(
        "--run-label",
        type=str,
        default=None,
        help=(
            "Run label used in the results directory structure.\n"
            "If omitted, a label is auto-generated from --fwhm-perturb-frac (e.g. fwhm_-1.0e-03).\n"
            "If omitted and no perturbation is supplied, defaults to 'default'."
        ),
    )

    parser.add_argument(
        "--run-id",
        type=str,
        default="default",
        help=(
            "Identifier for the run directory (default: 'default'). Use a stable run-id if you want to re-run/continue in the same directory."
        ),
    )
    parser.add_argument(
        "--unique",
        action="store_true",
        help=(
            "Append a UTC timestamp under the run-id directory. Useful for sweeps; less convenient for resuming. "
            "If omitted, may still be enabled via runtime_paths.yaml (bayeseor.unique_by_default)."
        ),
    )

    parser.add_argument(
        "--fwhm-perturb-frac",
        type=float,
        default=None,
        help=(
            "Apply a multiplicative perturbation to fwhm_deg at prepare time, specified as a fraction.\n"
            "Example: --fwhm-perturb-frac=-1e-3 means -0.1%% (multiply by 0.999).\n"
            "Example: --fwhm-perturb-frac=1e-1 means +10%% (multiply by 1.1).\n"
            "Note: if the value is negative, use either '--fwhm-perturb-frac=-1e-3' or "
            "place '--' before the value to prevent argparse confusion."
        ),
    )

    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help=(
            "Template name shipped with ValSKA OR a filesystem path to a template YAML.\n"
            "If omitted, uses bayeseor.default_template from config/runtime_paths.yaml, otherwise defaults to validation_v1d0_template.yaml.\n"
            "To list shipped templates, use --list-templates."
        ),
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List shipped BayesEoR validation templates and exit.",
    )

    parser.add_argument(
        "--bayeseor-repo",
        type=Path,
        default=None,
        help=(
            "Path to a local clone of the BayesEoR repository (used to locate scripts/run-analysis.py). If omitted, uses bayeseor.repo_path from config/runtime_paths.yaml."
        ),
    )

    parser.add_argument(
        "--conda-sh",
        type=str,
        default=None,
        help=(
            "Command to source conda.sh inside batch jobs. If omitted, uses bayeseor.conda_sh from config/runtime_paths.yaml."
        ),
    )
    parser.add_argument(
        "--conda-env",
        type=str,
        default=None,
        help=(
            "Name of the conda environment that has BayesEoR installed (e.g. bayeseor). If omitted, uses bayeseor.conda_env from config/runtime_paths.yaml."
        ),
    )

    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Override a top-level YAML key in the template (repeatable). Example: --override fwhm_deg=9.4\nValues are parsed as strings in this MVP; keep usage simple."
        ),
    )

    # SLURM knobs (caller-side overrides). These apply to BOTH cpu+gpu profiles for now.
    parser.add_argument(
        "--partition",
        type=str,
        default=None,
        help=(
            "SLURM partition. If omitted, uses bayeseor.slurm_defaults_cpu/gpu from config/runtime_paths.yaml."
        ),
    )
    parser.add_argument(
        "--time",
        type=str,
        default=None,
        help=(
            "SLURM walltime. If omitted, uses bayeseor.slurm_defaults_cpu/gpu from config/runtime_paths.yaml."
        ),
    )
    parser.add_argument(
        "--mem",
        type=str,
        default=None,
        help=(
            "SLURM memory request. If omitted, uses bayeseor.slurm_defaults_cpu/gpu from config/runtime_paths.yaml."
        ),
    )
    parser.add_argument(
        "--cpus",
        type=int,
        default=None,
        help=(
            "SLURM cpus-per-task. If omitted, uses bayeseor.slurm_defaults_cpu/gpu from config/runtime_paths.yaml."
        ),
    )
    parser.add_argument(
        "--job-name",
        type=str,
        default=None,
        help="Optional SLURM job name.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Resolve paths and configuration, but do not create directories or write files. Useful for checking where a run would be prepared."
        ),
    )

    return parser


def _parse_overrides(kvs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for kv in kvs:
        if "=" not in kv:
            raise ValueError(f"Invalid --override '{kv}'. Expected KEY=VALUE.")
        k, v = kv.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise ValueError(f"Invalid --override '{kv}'. Empty KEY.")
        out[k] = v
    return out


def _get_nested(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _slurm_defaults(runtime: dict[str, Any], profile: str) -> dict[str, Any]:
    """
    Return SLURM defaults for a given profile:
      profile="cpu" -> bayeseor.slurm_defaults_cpu
      profile="gpu" -> bayeseor.slurm_defaults_gpu

    Backwards-compatible fallbacks:
      - if *_cpu/gpu missing, fall back to bayeseor.slurm_defaults
      - if that missing, fall back to hard-coded MVP defaults
    """
    assert profile in {"cpu", "gpu"}
    key = "slurm_defaults_cpu" if profile == "cpu" else "slurm_defaults_gpu"

    cfg = _get_nested(runtime, "bayeseor", key)
    if not isinstance(cfg, dict):
        cfg = _get_nested(runtime, "bayeseor", "slurm_defaults")
    cfg = cfg if isinstance(cfg, dict) else {}

    # Keep conservative historical defaults as last resort
    out = {
        "partition": cfg.get("partition", None),
        "constraint": cfg.get("constraint", None),
        "time": cfg.get("time", "12:00:00"),
        "mem": cfg.get("mem", "8G"),
        "cpus_per_task": cfg.get("cpus_per_task", 4),
        "nodes": cfg.get("nodes", 1),
        "ntasks": cfg.get("ntasks", 1),
        "ntasks_per_node": cfg.get("ntasks_per_node", 1),
        "job_name_prefix": cfg.get("job_name_prefix", "bayeseor"),
        "mpi": cfg.get("mpi", "pmi2"),
        "extra_sbatch": cfg.get("extra_sbatch", []),
    }

    # Remove keys that are explicitly None so the renderer can omit them cleanly.
    if out.get("partition", None) in ("", None):
        out.pop("partition", None)
    if out.get("constraint", None) in ("", None):
        out.pop("constraint", None)

    return out


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_templates:
        for name in list_templates():
            print(name)
        return 0

    pm = get_default_path_manager()
    runtime = pm.runtime_paths

    if args.results_root is not None:
        results_root = args.results_root
        results_root_src = "CLI"
    else:
        results_root = pm.results_root
        results_root_src = (
            "runtime_paths.yaml" if "results_root" in runtime else "env/default"
        )

    # Resolve --data using runtime_paths.yaml (data.root) if provided.
    # Always record an absolute resolved path in manifests.
    data_provided = args.data
    data_resolved = resolve_data_path(data_provided, runtime)
    data_src = (
        "CLI(abs)"
        if Path(data_provided).expanduser().is_absolute()
        else "CLI(rel)"
    )
    if not Path(data_provided).expanduser().is_absolute():
        # Only meaningful to mention data.root if user gave a relative path.
        cfg_data = runtime.get("data", {}) if isinstance(runtime, dict) else {}
        cfg_root = cfg_data.get("root") if isinstance(cfg_data, dict) else None
        if isinstance(cfg_root, str) and cfg_root.strip():
            data_src = "runtime_paths.yaml:data.root"

    repo_path = args.bayeseor_repo
    repo_src = "CLI"
    if repo_path is None:
        cfg_repo = _get_nested(runtime, "bayeseor", "repo_path")
        if cfg_repo:
            repo_path = Path(str(cfg_repo)).expanduser()
            repo_src = "runtime_paths.yaml"
    if repo_path is None:
        raise SystemExit(
            "ERROR: BayesEoR repo path not provided. Pass --bayeseor-repo or set bayeseor.repo_path in config/runtime_paths.yaml."
        )

    conda_sh = args.conda_sh
    conda_sh_src = "CLI"
    if conda_sh is None:
        cfg_conda_sh = _get_nested(runtime, "bayeseor", "conda_sh")
        if cfg_conda_sh:
            conda_sh = str(cfg_conda_sh)
            conda_sh_src = "runtime_paths.yaml"
    if conda_sh is None:
        raise SystemExit(
            "ERROR: conda.sh activation command not provided. Pass --conda-sh or set bayeseor.conda_sh in config/runtime_paths.yaml."
        )

    conda_env = args.conda_env
    conda_env_src = "CLI"
    if conda_env is None:
        cfg_conda_env = _get_nested(runtime, "bayeseor", "conda_env")
        if cfg_conda_env:
            conda_env = str(cfg_conda_env)
            conda_env_src = "runtime_paths.yaml"
    if conda_env is None:
        raise SystemExit(
            "ERROR: conda env not provided. Pass --conda-env or set bayeseor.conda_env in config/runtime_paths.yaml."
        )

    template_arg = args.template
    template_src = "CLI"
    if template_arg is None:
        cfg_t = _get_nested(runtime, "bayeseor", "default_template")
        if cfg_t:
            template_arg = str(cfg_t)
            template_src = "runtime_paths.yaml"
        else:
            template_arg = "validation_v1d0_template.yaml"
            template_src = "default"

    template_path = Path(template_arg)
    if template_path.exists():
        template_yaml = template_path
    else:
        template_yaml = get_template_path(template_arg)

    install = BayesEoRInstall(repo_path=repo_path)
    runner = CondaRunner(conda_activate=conda_sh, env_name=conda_env)

    overrides = _parse_overrides(args.override)

    unique = bool(args.unique)
    unique_src = "CLI" if args.unique else "default"
    if not args.unique:
        cfg_unique = _get_nested(runtime, "bayeseor", "unique_by_default")
        if isinstance(cfg_unique, bool):
            unique = cfg_unique
            unique_src = "runtime_paths.yaml"

    scenario = args.scenario
    run_id = args.run_id

    if args.run_label is not None:
        run_label = args.run_label
        run_label_src = "CLI"
    else:
        if args.fwhm_perturb_frac is not None:
            run_label = _format_run_label_from_fwhm_frac(
                float(args.fwhm_perturb_frac)
            )
            run_label_src = "auto(fwhm_perturb_frac)"
        else:
            run_label = "default"
            run_label_src = "default"

    run_dir = _compute_run_dir(
        results_root=Path(results_root).expanduser(),
        scenario=scenario,
        run_label=run_label,
        run_id=run_id,
        unique=unique,
    )

    # Build separate SLURM profiles, then apply CLI overrides to BOTH profiles for now.
    slurm_cpu = _slurm_defaults(runtime, "cpu")
    slurm_gpu = _slurm_defaults(runtime, "gpu")

    if args.partition is not None:
        slurm_cpu["partition"] = args.partition
        slurm_gpu["partition"] = args.partition
    if args.time is not None:
        slurm_cpu["time"] = args.time
        slurm_gpu["time"] = args.time
    if args.mem is not None:
        slurm_cpu["mem"] = args.mem
        slurm_gpu["mem"] = args.mem
    if args.cpus is not None:
        slurm_cpu["cpus_per_task"] = args.cpus
        slurm_gpu["cpus_per_task"] = args.cpus

    if args.job_name:
        slurm_cpu["job_name"] = args.job_name
        slurm_gpu["job_name"] = args.job_name

    if args.dry_run:
        print("\n[DRY RUN] BayesEoR run would be prepared with:")
        print(f"  results_root:  {results_root}   [{results_root_src}]")
        print(
            f"  run_dir:       {run_dir}   [{'unique' if unique else 'stable'}; {unique_src}]"
        )
        print(f"  run_label:     {run_label}   [{run_label_src}]")
        print(f"  template_yaml: {template_yaml}   [{template_src}]")
        if data_resolved != Path(data_provided).expanduser().resolve():
            # This branch is unlikely because resolve() will normalize, but keep logic explicit.
            print(f"  data_path:     {data_resolved}   [{data_src}]")
        else:
            # Still show the resolved absolute path (it is what will be recorded).
            print(f"  data_path:     {data_resolved}   [{data_src}]")
        print(f"  bayeseor_repo: {install.repo_path}   [{repo_src}]")
        print(f"  conda_sh:      {conda_sh}   [{conda_sh_src}]")
        print(f"  conda_env:     {runner.env_name}   [{conda_env_src}]")
        print(
            f"  fwhm_perturb:  {args.fwhm_perturb_frac if args.fwhm_perturb_frac is not None else '(none)'} (frac)"
        )
        print(f"  overrides:     {overrides or '{}'}")
        print("  slurm_cpu:     " + str(slurm_cpu))
        print("  slurm_gpu:     " + str(slurm_gpu))
        print("\n[DRY RUN] No files or directories have been created.")
        return 0

    out = prepare_bayeseor_run(
        template_yaml=template_yaml,
        install=install,
        runner=runner,
        results_root=Path(results_root).expanduser(),
        scenario=scenario,
        run_label=run_label,
        run_dir=run_dir,
        unique=unique,
        data_path=data_resolved,
        overrides=overrides,
        slurm_cpu=slurm_cpu,
        slurm_gpu=slurm_gpu,
        fwhm_perturb_frac=args.fwhm_perturb_frac,
    )

    print("\nPrepared BayesEoR run artefacts:")
    print(f"  run_dir:       {out['run_dir']}")
    print(f"  manifest_json: {out['manifest_json']}")

    if "submit_sh_cpu_precompute" in out:
        print("\n  [shared]")
        print(f"    submit_cpu_precompute: {out['submit_sh_cpu_precompute']}")

    for hyp in ("signal_fit", "no_signal"):
        cfg_key = f"config_yaml_{hyp}"
        gpu_key = f"submit_sh_{hyp}_gpu_run"
        if cfg_key in out:
            print(f"\n  [{hyp}]")
            print(f"    config_yaml:    {out[cfg_key]}")
            if gpu_key in out:
                print(f"    submit_gpu_run: {out[gpu_key]}")

    print("\nNext steps (typical BayesEoR two-stage workflow):")

    print("  Option A) Submit via ValSKA (recommended):")
    print(f"     valska-bayeseor-submit {out['run_dir']}")
    print("     # CPU only:")
    print(f"     valska-bayeseor-submit {out['run_dir']} --stage cpu")
    print(
        "     # GPU only (depends on recorded CPU job ID, or provide --depend-afterok):"
    )
    print(f"     valska-bayeseor-submit {out['run_dir']} --stage gpu")
    print(
        "     # If a job hits walltime, you can requeue easily (MultiNest should resume):"
    )
    print(
        f"     valska-bayeseor-submit {out['run_dir']} --stage gpu --resubmit"
    )

    print("\n  Option B) Manual submission (inspect scripts, then sbatch):")
    if "submit_sh_cpu_precompute" in out:
        print("     1) CPU precompute stage (shared):")
        print(f"        sbatch {out['submit_sh_cpu_precompute']}")

    gpu_cmds: list[str] = []
    for hyp in ("signal_fit", "no_signal"):
        kgpu = f"submit_sh_{hyp}_gpu_run"
        if kgpu in out:
            gpu_cmds.append(f"sbatch {out[kgpu]}")

    if gpu_cmds:
        print("     2) GPU run stage (after CPU stage completes successfully):")
        for c in gpu_cmds:
            print(f"        {c}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
