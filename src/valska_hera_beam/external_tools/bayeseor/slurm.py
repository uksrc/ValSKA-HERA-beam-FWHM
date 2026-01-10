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
      - uses `srun --mpi=<mpi> -n "$SLURM_NTASKS"` by default to match common site setups
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
          - partition: str | None (if omitted/None/empty, no --partition line is emitted)
          - constraint: str | None (if provided, emits --constraint=<value>)
          - time: str
          - mem: str
          - cpus_per_task: int
          - ntasks: int
          - nodes: int
          - ntasks_per_node: int
          - mpi: str (srun --mpi=<mpi>; default: pmi2)
          - output: str (overrides default log file path)
          - error: str (optional separate stderr path)
          - extra_sbatch: list[str] (additional #SBATCH lines, without the "#SBATCH " prefix)

    mode
        Execution mode:
          - "cpu"     : precompute instrument transfer matrices (BayesEoR --cpu)
          - "gpu_run" : run sampling assuming precompute exists (BayesEoR --gpu --run)

    Notes on timing
    ---------------
    We intentionally do NOT rely on `/usr/bin/time` or shell `time`, since some
    compute-node images do not provide them. Timing is implemented using only:
      - date (UTC timestamps + epoch seconds)
    This should work essentially everywhere.
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

    partition = slurm.get("partition", None)
    if partition is not None:
        partition = str(partition).strip() or None

    constraint = slurm.get("constraint", None)
    if constraint is not None:
        constraint = str(constraint).strip() or None

    time = str(slurm.get("time", "12:00:00"))
    mem = str(slurm.get("mem", "8G"))
    cpus = int(slurm.get("cpus_per_task", 4))

    nodes = int(slurm.get("nodes", 1))
    ntasks = int(slurm.get("ntasks", 1))
    ntasks_per_node = int(slurm.get("ntasks_per_node", 1))

    mpi = str(slurm.get("mpi", "pmi2"))

    # Log files
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
        prefix = ""
        python_exe = "python  # TODO: container exec wrapper"

    # -------------------------
    # BayesEoR args by stage
    # -------------------------
    if mode == "cpu":
        stage_flags = "--cpu"
    else:
        stage_flags = "--gpu --run"

    srun_prefix = f'srun --mpi={mpi} -n "${{SLURM_NTASKS:-{ntasks}}}"'
    inner_cmd = f'{srun_prefix} {python_exe} -u "{run_py}" --config "{config_yaml}" {stage_flags}'

    # -------------------------
    # SBATCH header lines
    # -------------------------
    sbatch_lines: list[str] = [
        "#!/bin/bash",
        f"#SBATCH --job-name={job_name}",
    ]

    if partition:
        sbatch_lines.append(f"#SBATCH --partition={partition}")
    if constraint:
        sbatch_lines.append(f"#SBATCH --constraint={constraint}")

    sbatch_lines.extend(
        [
            f"#SBATCH --time={time}",
            f"#SBATCH --mem={mem}",
            f"#SBATCH --nodes={nodes}",
            f"#SBATCH --ntasks={ntasks}",
            f"#SBATCH --ntasks-per-node={ntasks_per_node}",
            f"#SBATCH --cpus-per-task={cpus}",
            f"#SBATCH --output={out_log}",
        ]
    )

    if err_log:
        sbatch_lines.append(f"#SBATCH --error={err_log}")

    for line in extra_sbatch:
        s = str(line).strip()
        if not s:
            continue
        if s.startswith("#SBATCH"):
            sbatch_lines.append(s)
        else:
            sbatch_lines.append(f"#SBATCH {s}")

    sbatch_block = "\n".join(sbatch_lines)

    # -------------------------
    # Script body (robust timing: no `time` dependency)
    # -------------------------
    return f"""{sbatch_block}

set -eo pipefail

# -----------------------------------------------------------------------------
# ValSKA-generated BayesEoR submit script
#
# Mode: {mode}
# Config: {config_yaml}
# Run dir: {run_dir}
# -----------------------------------------------------------------------------

echo "========================================"
echo "ValSKA / BayesEoR SLURM job starting"
echo "========================================"

START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Start time (UTC):  $START_ISO"
echo "Hostname:          $(hostname)"
echo "Working dir:       $(pwd)"
echo "Run dir:           {run_dir}"
echo "Config:            {config_yaml}"
echo "BayesEoR script:   {run_py}"
echo "Mode:              {mode}"
echo "----------------------------------------"

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
echo "  {inner_cmd}"
echo "----------------------------------------"

# -----------------------------------------------------------------------------
# Timing (UTC) - implemented without relying on /usr/bin/time or shell `time`.
# -----------------------------------------------------------------------------
JOBID="${{SLURM_JOB_ID:-unknown}}"
TIMING_FILE="{run_dir}/timing-{mode}-${{JOBID}}.txt"

echo "Timing file:       $TIMING_FILE"
echo "----------------------------------------"

# Epoch seconds (portable)
START_EPOCH="$(date -u +%s)"

# Best-effort nanoseconds (may not be supported everywhere; if not, returns non-numeric)
START_NS="$(date -u +%s%N || true)"

# Run BayesEoR command (do not let 'set -e' stop us before capturing RC)
set +e
{inner_cmd}
RC=$?
set -e

END_EPOCH="$(date -u +%s)"
END_NS="$(date -u +%s%N || true)"
END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

ELAPSED_S="$((END_EPOCH - START_EPOCH))"
ELAPSED_NS=""

# Compute ns elapsed only if both look numeric
if [[ "$START_NS" =~ ^[0-9]+$ ]] && [[ "$END_NS" =~ ^[0-9]+$ ]]; then
  ELAPSED_NS="$((END_NS - START_NS))"
fi

# Write timing file (overwrite each run)
{{
  echo "Start time (UTC):  $START_ISO"
  echo "End time (UTC):    $END_ISO"
  echo "Elapsed (s):       $ELAPSED_S"
  if [[ -n "$ELAPSED_NS" ]]; then
    echo "Elapsed (ns):      $ELAPSED_NS"
  fi
  echo "Exit code:         $RC"
}} > "$TIMING_FILE"

echo "End time (UTC):    $END_ISO"
echo "Elapsed (s):       $ELAPSED_S"
if [[ -n "$ELAPSED_NS" ]]; then
  echo "Elapsed (ns):      $ELAPSED_NS"
fi
echo "Exit code:         $RC"

if [[ $RC -ne 0 ]]; then
  echo "ERROR: BayesEoR command failed with exit code $RC"
  exit $RC
fi

echo "----------------------------------------"
echo "ValSKA / BayesEoR SLURM job complete"
echo "========================================"
"""
