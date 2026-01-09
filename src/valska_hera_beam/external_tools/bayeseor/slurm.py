from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .runner import BayesEoRInstall, CondaRunner, ContainerRunner


def render_submit_script(
    *,
    runner: CondaRunner | ContainerRunner,
    install: BayesEoRInstall,
    config_yaml: Path,
    run_dir: Path,
    slurm: Mapping[str, object] | None = None,
    mode: str = "cpu",
) -> str:
    """
    Render a SLURM submit script for a BayesEoR run.

    This function aims to be HPC-friendly and debugging-friendly:
      - emits clear "what am I running" information
      - prints SLURM_* environment variables (helpful when diagnosing scheduling issues)
      - uses `srun --mpi=pmi2 -n "$SLURM_NTASKS"` by default to match common site setups
      - uses BayesEoR's CLI flags:
          * CPU stage:  --cpu
          * GPU stage:  --gpu --run

    Parameters
    ----------
    runner
        How BayesEoR is executed (currently conda; container support later).
    install
        Where BayesEoR lives and how to locate its run script.
    config_yaml
        Path to the rendered BayesEoR config YAML to run.
    run_dir
        Run directory containing configs/logs/manifests.
    slurm
        SLURM settings map. Usually derived from runtime_paths.yaml defaults plus CLI overrides.
        Supported keys (all optional):
          - job_name: str
          - job_name_prefix: str
          - partition: str
          - time: str
          - mem: str
          - cpus_per_task: int
          - ntasks: int
          - nodes: int
          - ntasks_per_node: int
          - output: str (overrides default log file path)
          - error: str (optional separate stderr path)
          - extra_sbatch: list[str] (additional #SBATCH lines, without the "#SBATCH " prefix)

    mode
        Execution mode:
          - "cpu"     : precompute instrument transfer matrices (BayesEoR --cpu)
          - "gpu_run" : run sampling assuming precompute exists (BayesEoR --gpu --run)

    Future container support
    ------------------------
    When we support Apptainer/Singularity, only the "runner prefix" and command line
    wrapper will change; the run directory structure and config paths remain identical.
    """
    slurm = dict(slurm or {})

    if mode not in {"cpu", "gpu_run"}:
        raise ValueError("mode must be one of: 'cpu', 'gpu_run'")

    # -------------------------
    # SLURM defaults (sane MVP)
    # -------------------------
    job_name_prefix = str(slurm.get("job_name_prefix", "bayeseor"))
    job_name = str(
        slurm.get("job_name", f"{job_name_prefix}-{run_dir.name}-{mode}")
    )

    partition = str(slurm.get("partition", "cpu"))
    time = str(slurm.get("time", "12:00:00"))
    mem = str(slurm.get("mem", "8G"))
    cpus = int(slurm.get("cpus_per_task", 4))

    # These are commonly needed for MPI-ish launches; keep conservative defaults.
    nodes = int(slurm.get("nodes", 1))
    ntasks = int(slurm.get("ntasks", 1))
    ntasks_per_node = int(slurm.get("ntasks_per_node", 1))

    # Log files
    # Use a run-dir local log by default, but allow override if user prefers slurm-out/%j.out etc.
    out_log = Path(str(slurm.get("output", run_dir / f"slurm-{mode}-%j.out")))
    err_log = slurm.get("error", None)

    extra_sbatch = slurm.get("extra_sbatch", [])
    if extra_sbatch is None:
        extra_sbatch = []
    if not isinstance(extra_sbatch, list):
        raise TypeError(
            "slurm['extra_sbatch'] must be a list of strings if provided"
        )

    # Where is BayesEoR's entrypoint script?
    run_py = install.repo_path / install.run_script

    # -------------------------
    # Runner prefix (conda now)
    # -------------------------
    if isinstance(runner, CondaRunner):
        prefix = runner.bash_prefix()
        python_exe = "python"
    else:
        # Future: construct a proper apptainer exec line with binds.
        # Example:
        #   bind_args = " ".join(f'--bind "{p}:{p}"' for p in runner.bind_paths)
        #   python_exe = f'{runner.apptainer_exe} exec {bind_args} "{runner.image_path}" python'
        prefix = ""
        python_exe = "python  # TODO: container exec wrapper"

    # -------------------------
    # BayesEoR args by stage
    # -------------------------
    # Use the "run-analysis.py <config>" calling style you currently have working.
    # Add flags to match your existing workflow.
    if mode == "cpu":
        stage_flags = "--cpu"
    else:
        stage_flags = "--gpu --run"

    # Use SLURM_NTASKS if available; otherwise fall back to configured ntasks.
    # Keep --mpi=pmi2 to match your previous script; allow site override via extra_sbatch if needed.
    srun_prefix = f'srun --mpi=pmi2 -n "${{SLURM_NTASKS:-{ntasks}}}"'

    cmd = f'{srun_prefix} {python_exe} -u "{run_py}" "{config_yaml}" {stage_flags}'

    # -------------------------
    # SBATCH header lines
    # -------------------------
    sbatch_lines: list[str] = [
        "#!/bin/bash",
        f"#SBATCH --job-name={job_name}",
        f"#SBATCH --partition={partition}",
        f"#SBATCH --time={time}",
        f"#SBATCH --mem={mem}",
        f"#SBATCH --nodes={nodes}",
        f"#SBATCH --ntasks={ntasks}",
        f"#SBATCH --ntasks-per-node={ntasks_per_node}",
        f"#SBATCH --cpus-per-task={cpus}",
        f"#SBATCH --output={out_log}",
    ]
    if err_log:
        sbatch_lines.append(f"#SBATCH --error={err_log}")

    # Allow user to provide extra SBATCH directives (e.g. constraints, QoS, account, gres)
    for line in extra_sbatch:
        # Be forgiving: if user included "#SBATCH", keep it; otherwise add it.
        s = str(line).strip()
        if not s:
            continue
        if s.startswith("#SBATCH"):
            sbatch_lines.append(s)
        else:
            sbatch_lines.append(f"#SBATCH {s}")

    sbatch_block = "\n".join(sbatch_lines)

    # -------------------------
    # Script body
    # -------------------------
    # Keep some of your original useful diagnostics and add a few more.
    return f"""{sbatch_block}

set -euo pipefail

# -----------------------------------------------------------------------------
# ValSKA-generated BayesEoR submit script
#
# Mode: {mode}
# Config: {config_yaml}
# Run dir: {run_dir}
#
# Notes:
# - CPU stage (--cpu) typically precomputes the instrument transfer matrix.
# - GPU stage (--gpu --run) assumes the CPU stage has completed successfully.
# -----------------------------------------------------------------------------

echo "========================================"
echo "ValSKA / BayesEoR SLURM job starting"
echo "========================================"
echo "Timestamp (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Hostname:        $(hostname)"
echo "Working dir:     $(pwd)"
echo "Run dir:         {run_dir}"
echo "Config:          {config_yaml}"
echo "BayesEoR script: {run_py}"
echo "Mode:            {mode}"
echo "----------------------------------------"

# Helpful for debugging threading behaviour
export OPENBLAS_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{cpus}}}"
export OMP_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{cpus}}}"

echo "OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "----------------------------------------"

echo "===== SLURM ENVIRONMENT (begin) ====="
env | sort | grep '^SLURM_' || echo "No SLURM_ variables found"
echo "===== SLURM ENVIRONMENT (end) ====="
echo "----------------------------------------"

{prefix}

echo "Python: $(which python || true)"
python -V || true
echo "----------------------------------------"

echo "Command:"
echo "  {cmd}"
echo "----------------------------------------"

{cmd}

echo "----------------------------------------"
echo "ValSKA / BayesEoR SLURM job complete"
echo "========================================"
"""
