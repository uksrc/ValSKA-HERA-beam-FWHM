from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

from valska_hera_beam.external_tools.bayeseor import (
    BayesEoRInstall,
    CondaRunner,
    get_template_path,
)
from valska_hera_beam.utils import get_default_path_manager, resolve_data_path

from .sweep import run_fwhm_sweep, sweep_root

_STAGE = Literal["none", "cpu", "gpu", "all"]
_HYP = Literal["signal_fit", "no_signal", "both"]


def _parse_fracs(vals: list[str]) -> list[float]:
    out: list[float] = []
    for v in vals:
        try:
            out.append(float(v))
        except Exception as e:
            raise SystemExit(
                f"ERROR: Could not parse fwhm frac '{v}' as float: {e}"
            )
    return out


def _parse_fracs_file(path: Path) -> list[float]:
    """
    Parse a text file containing one float per line.

    Supports:
    - blank lines
    - comments starting with '#'
    """
    p = Path(path).expanduser()
    if not p.exists():
        raise SystemExit(f"ERROR: fwhm fracs file does not exist: {p}")
    lines = p.read_text(encoding="utf-8").splitlines()
    vals: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        # allow inline comments: "0.01  # +1%"
        if "#" in s:
            s = s.split("#", 1)[0].strip()
        if s:
            vals.append(s)
    if not vals:
        raise SystemExit(
            f"ERROR: No numeric entries found in fwhm fracs file: {p}"
        )
    return _parse_fracs(vals)


def _parse_overrides(kvs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for kv in kvs:
        if "=" not in kv:
            raise SystemExit(
                f"ERROR: Invalid --override '{kv}'. Expected KEY=VALUE."
            )
        k, v = kv.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise SystemExit(f"ERROR: Invalid --override '{kv}'. Empty KEY.")
        out[k] = v
    return out


def _get_nested(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="valska-bayeseor-sweep",
        description=(
            "Prepare (and optionally submit) a sweep of BayesEoR runs across multiple FWHM perturbations.\n\n"
            "Writes sweep_manifest.json under:\n"
            "  <results_root>/bayeseor/<scenario>/_sweeps/<run_id>/"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    p.add_argument(
        "--data", type=Path, required=True, help="Path to the UVH5 dataset."
    )
    p.add_argument(
        "--scenario",
        type=str,
        required=True,
        help="Scenario name (e.g. GLEAM_beam).",
    )
    p.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Sweep identifier used as run_id (e.g. sweep_v1). Keeps runs grouped and resumable.",
    )

    p.add_argument(
        "--fwhm-fracs",
        nargs="+",
        default=None,
        help=(
            "List of fractional FWHM perturbations to run (dimensionless).\n"
            "Example: --fwhm-fracs -0.10 -0.05 ... 0.10\n"
            "Precedence: --fwhm-fracs > --fwhm-fracs-file > runtime_paths.yaml > built-in default."
        ),
    )

    p.add_argument(
        "--fwhm-fracs-file",
        type=Path,
        default=None,
        help=(
            "Path to a text file listing fractional FWHM perturbations (one float per line).\n"
            "Blank lines and '#' comments are ignored.\n"
            "Precedence: --fwhm-fracs > --fwhm-fracs-file > runtime_paths.yaml > built-in default."
        ),
    )

    p.add_argument(
        "--results-root",
        type=Path,
        default=None,
        help="Results root. If omitted, resolves via config/runtime_paths.yaml then env/defaults.",
    )

    p.add_argument(
        "--template",
        type=str,
        default=None,
        help=(
            "Template name shipped with ValSKA OR a filesystem path to a template YAML.\n"
            "If omitted, uses bayeseor.default_template from config/runtime_paths.yaml, "
            "otherwise defaults to validation_v1d0_template.yaml."
        ),
    )

    p.add_argument(
        "--bayeseor-repo",
        type=Path,
        default=None,
        help="Path to local clone of BayesEoR (used to locate scripts/run-analysis.py).",
    )

    p.add_argument(
        "--conda-sh",
        type=str,
        default=None,
        help="Command to source conda.sh in batch jobs.",
    )
    p.add_argument(
        "--conda-env",
        type=str,
        default=None,
        help="Conda env name containing BayesEoR.",
    )

    p.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a top-level YAML key in the template (repeatable).",
    )

    p.add_argument(
        "--unique",
        action="store_true",
        help="Append a UTC timestamp beneath run_id for each point (not recommended for resumable sweeps).",
    )

    # Optional submission orchestration
    p.add_argument(
        "--submit",
        choices=["none", "cpu", "gpu", "all"],
        default="none",
        help="Optionally submit stages after preparing. Default: none.",
    )
    p.add_argument(
        "--hypothesis",
        choices=["signal_fit", "no_signal", "both"],
        default="both",
        help="Which GPU hypothesis scripts to submit (only used if submit includes GPU). Default: both.",
    )
    p.add_argument(
        "--depend-afterok",
        default=None,
        help="Explicit job id to depend on for GPU submissions (rare; usually per-run recorded CPU job id).",
    )
    p.add_argument(
        "--sbatch-exe",
        default=None,
        help="sbatch executable name/path. Default comes from config/runtime_paths.yaml or 'sbatch'.",
    )
    p.add_argument(
        "--submit-dry-run",
        action="store_true",
        help="Dry-run submission only: prepare for real, but print sbatch commands without submitting.",
    )
    p.add_argument(
        "--force", action="store_true", help="Pass through force to submission."
    )
    p.add_argument(
        "--resubmit",
        action="store_true",
        help=(
            "Resubmit across the sweep (archives each point's jobs.json then requeues).\n"
            "Typical: --submit gpu --resubmit"
        ),
    )

    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run the sweep: print what would be prepared/submitted; do not write files or submit.",
    )

    p.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print the full sweep result object as JSON.",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    pm = get_default_path_manager()
    runtime = pm.runtime_paths

    # results_root
    if args.results_root is not None:
        results_root = Path(args.results_root).expanduser()
        results_root_src = "CLI"
    else:
        results_root = Path(pm.results_root).expanduser()
        results_root_src = (
            "runtime_paths.yaml" if "results_root" in runtime else "env/default"
        )

    # Resolve data path (supports runtime_paths.yaml:data.root) for consistent display + execution
    try:
        data_resolved = resolve_data_path(args.data, runtime)
        data_src = "runtime_paths.yaml:data.root"
    except Exception:
        # Fallback: behave like before (but still expanduser)
        data_resolved = Path(args.data).expanduser()
        data_src = "CLI"

    # repo_path
    repo_path = args.bayeseor_repo
    if repo_path is None:
        cfg_repo = _get_nested(runtime, "bayeseor", "repo_path")
        if cfg_repo:
            repo_path = Path(str(cfg_repo)).expanduser()
    if repo_path is None and not args.dry_run:
        print(
            "ERROR: BayesEoR repo path not provided. Pass --bayeseor-repo or set bayeseor.repo_path in config/runtime_paths.yaml.",
            file=sys.stderr,
        )
        return 2

    # conda_sh/env
    conda_sh = args.conda_sh
    if conda_sh is None:
        cfg = _get_nested(runtime, "bayeseor", "conda_sh")
        if cfg:
            conda_sh = str(cfg)
    conda_env = args.conda_env
    if conda_env is None:
        cfg = _get_nested(runtime, "bayeseor", "conda_env")
        if cfg:
            conda_env = str(cfg)

    if not args.dry_run:
        if conda_sh is None:
            print(
                "ERROR: conda.sh activation command not provided (set bayeseor.conda_sh or pass --conda-sh).",
                file=sys.stderr,
            )
            return 2
        if conda_env is None:
            print(
                "ERROR: conda env not provided (set bayeseor.conda_env or pass --conda-env).",
                file=sys.stderr,
            )
            return 2

    # template
    template_arg = args.template
    if template_arg is None:
        cfg_t = _get_nested(runtime, "bayeseor", "default_template")
        if cfg_t:
            template_arg = str(cfg_t)
        else:
            template_arg = "validation_v1d0_template.yaml"

    template_path = Path(str(template_arg)).expanduser()
    if template_path.exists():
        template_yaml = template_path
    else:
        template_yaml = get_template_path(str(template_arg))

    # ---- fwhm fracs precedence ----
    fracs: list[float] | None = None

    if args.fwhm_fracs is not None:
        fracs = _parse_fracs(list(args.fwhm_fracs))
        fracs_src = "CLI(--fwhm-fracs)"
    elif args.fwhm_fracs_file is not None:
        fracs = _parse_fracs_file(Path(args.fwhm_fracs_file))
        fracs_src = "CLI(--fwhm-fracs-file)"
    else:
        cfg_fracs = _get_nested(runtime, "bayeseor", "sweep", "fwhm_fracs")
        if isinstance(cfg_fracs, list) and cfg_fracs:
            try:
                fracs = [float(x) for x in cfg_fracs]
                fracs_src = "runtime_paths.yaml(bayeseor.sweep.fwhm_fracs)"
            except Exception:
                fracs = None
                fracs_src = "default"
        else:
            fracs_src = "default"

    # submission defaults
    sbatch_exe = args.sbatch_exe
    if sbatch_exe is None:
        cfg = _get_nested(runtime, "bayeseor", "submit", "sbatch_exe")
        if isinstance(cfg, str) and cfg.strip():
            sbatch_exe = cfg.strip()
        else:
            sbatch_exe = "sbatch"

    overrides = _parse_overrides(args.override)

    if args.dry_run:
        sd = sweep_root(results_root, args.scenario, args.run_id)
        print("\n[DRY RUN] Sweep would be executed with:")
        print(f"  results_root: {results_root} [{results_root_src}]")
        print(f"  scenario:     {args.scenario}")
        print(f"  run_id:       {args.run_id}")
        print(f"  sweep_dir:    {sd}")
        print(f"  template:     {template_yaml}")
        print(f"  data:         {data_resolved} [{data_src}]")
        print(
            f"  fwhm_fracs:   {fracs if fracs is not None else '(built-in default 9-point set)'} [{fracs_src}]"
        )
        print(f"  unique:       {bool(args.unique)}")
        print(f"  submit:       {args.submit}")
        if args.submit != "none":
            print(f"  hypothesis:   {args.hypothesis}")
            print(f"  sbatch_exe:   {sbatch_exe}")
            print(f"  submit_dry:   {bool(args.submit_dry_run)}")
            print(f"  force:        {bool(args.force)}")
            print(f"  resubmit:     {bool(args.resubmit)}")
        print("\n[DRY RUN] No files or jobs will be created/submitted.")
        return 0

    install = BayesEoRInstall(repo_path=Path(str(repo_path)).expanduser())
    runner = CondaRunner(conda_activate=str(conda_sh), env_name=str(conda_env))

    sweep_res = run_fwhm_sweep(
        template_yaml=template_yaml,
        install=install,
        runner=runner,
        results_root=results_root,
        scenario=args.scenario,
        run_id=args.run_id,
        data_path=Path(data_resolved).expanduser(),
        overrides=overrides,
        fwhm_fracs=fracs,
        unique=bool(args.unique),
        submit=args.submit,  # type: ignore[arg-type]
        hypothesis=args.hypothesis,  # type: ignore[arg-type]
        depend_afterok=args.depend_afterok,
        sbatch_exe=str(sbatch_exe),
        submit_dry_run=bool(args.submit_dry_run),
        force=bool(args.force),
        resubmit=bool(args.resubmit),
        record="jobs.json",
        dry_run=False,
    )

    if args.json_out:
        payload = {
            "results_root": str(sweep_res.results_root),
            "scenario": sweep_res.scenario,
            "run_id": sweep_res.run_id,
            "data_path": str(sweep_res.data_path),
            "created_utc": sweep_res.created_utc,
            "sweep_dir": str(sweep_res.sweep_dir),
            "sweep_manifest_json": str(sweep_res.sweep_manifest_json),
            "template_yaml": str(sweep_res.template_yaml),
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
                for p in sweep_res.points
            ],
            "submit_results": sweep_res.submit_results,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("\nSweep prepared:")
    print(f"  sweep_dir:           {sweep_res.sweep_dir}")
    print(f"  sweep_manifest.json: {sweep_res.sweep_manifest_json}")
    print(f"  points:              {len(sweep_res.points)}")

    if args.submit != "none":
        n_err = sum(
            1
            for r in sweep_res.submit_results
            if isinstance(r, dict) and "error" in r
        )
        print(
            f"  submit:              {args.submit} ({'with errors' if n_err else 'ok'})"
        )
        if n_err:
            print(
                f"  submit_errors:       {n_err} (see sweep_manifest.json submit_results)"
            )

    print("\nPoints:")
    for p in sweep_res.points:
        print(f"  {p.fwhm_perturb_frac:+.3f}  {p.run_label}  ->  {p.run_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
