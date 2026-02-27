"""SLURM submit-script rendering for BayesEoR runs."""

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
    - uses ``srun --mpi=<mpi> -n "$SLURM_NTASKS"`` by default to match common site setups
    - uses BayesEoR's CLI flags:
      - CPU stage: ``--cpu``
      - GPU stage: ``--gpu --run``

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

        **Any key set to ``None`` (or not present) will be omitted from the
        generated script.** This allows cluster-specific suppression of
        directives that are not supported or not needed.

        Supported keys (all optional)::

            Job identification:
              - ``job_name``: Full job name (overrides prefix-based naming)
              - ``job_name_prefix``: Prefix for auto-generated job name
                (default: "bayeseor")
            Resource selection:
              - ``partition``: Partition/queue name (omit for constraint-based scheduling)
              - ``constraint``: Node feature constraint (e.g., "A100", "skylake")
              - ``qos``: Quality of service
              - ``account``: Account/project to charge
              - ``reservation``: Reservation name
            Time and memory:
              - ``time``: Wall time limit (default: "12:00:00")
              - ``mem``: Memory per node (default: "8G")
              - ``mem_per_cpu``: Memory per CPU (mutually exclusive with ``mem``)
              - ``mem_per_gpu``: Memory per GPU
            CPU/task configuration:
              - ``nodes``: Number of nodes (default: 1)
              - ``ntasks``: Total number of tasks (default: 1)
              - ``ntasks_per_node``: Tasks per node (default: 1)
              - ``cpus_per_task``: CPUs per task (default: 4)
            GPU configuration:
              - ``gpus``: Total GPUs (e.g., ``2`` or ``"a100:2"``)
              - ``gpus_per_node``: GPUs per node
              - ``gpus_per_task``: GPUs per task (common for single-GPU jobs)
              - ``gres``: Generic resources (e.g., ``"gpu:1"``, ``"gpu:a100:2"``)
            Execution control:
              - ``mpi``: MPI type for srun (default: "pmi2")
              - ``exclusive``: Request exclusive node access (True emits ``--exclusive``)
            Output:
              - ``output``: Stdout log path (default: ``run_dir/slurm-{mode}-%j.out``)
              - ``error``: Stderr log path (if separate from stdout)
            Extensibility:
              - ``extra_sbatch``: Additional ``#SBATCH`` lines
                (without the ``"#SBATCH "`` prefix)

    mode
        Execution mode:

        - ``"cpu"``: precompute instrument transfer matrices (BayesEoR ``--cpu``)
        - ``"gpu_run"``: run sampling assuming precompute exists
          (BayesEoR ``--gpu --run``)

    Notes on timing
    ---------------
    We intentionally do NOT rely on ``/usr/bin/time`` or shell ``time``, since
    some compute-node images do not provide them. Timing is implemented using
    only:

    - ``date`` (UTC timestamps + epoch seconds)

    This should work essentially everywhere.

    Notes on cluster portability
    ----------------------------
    Different HPC sites have different scheduling policies:

    - Some use ``--partition``, others use ``--constraint``
    - Some require ``--account``, others don't
    - GPU syntax varies: ``--gpus-per-task`` vs ``--gres=gpu:N``

    Set unsupported/unwanted directives to None in your runtime_paths.yaml
    to omit them from generated scripts.
    """
    slurm = dict(slurm or {})

    if mode not in {"cpu", "gpu_run"}:
        raise ValueError("mode must be one of: 'cpu', 'gpu_run'")

    # -------------------------
    # Helper to extract optional string values
    # -------------------------
    def get_str_or_none(key: str, default: str | None = None) -> str | None:
        """Return stripped string if present and non-empty, else None."""
        val = slurm.get(key, default)
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    def get_int_or_none(key: str, default: int | None = None) -> int | None:
        """Return int if present and not None, else None."""
        val = slurm.get(key, default)
        if val is None:
            return None
        return int(val)

    # -------------------------
    # Job identification
    # -------------------------
    job_name_prefix = get_str_or_none("job_name_prefix", "bayeseor") or "bayeseor"
    job_name = get_str_or_none("job_name") or f"{job_name_prefix}-{run_dir.name}-{mode}"

    # -------------------------
    # Resource selection
    # -------------------------
    partition = get_str_or_none("partition")
    constraint = get_str_or_none("constraint")
    qos = get_str_or_none("qos")
    account = get_str_or_none("account")
    reservation = get_str_or_none("reservation")

    # -------------------------
    # Time and memory
    # -------------------------
    time = get_str_or_none("time", "12:00:00")
    mem = get_str_or_none("mem", "8G")
    mem_per_cpu = get_str_or_none("mem_per_cpu")
    mem_per_gpu = get_str_or_none("mem_per_gpu")

    # -------------------------
    # CPU/task configuration
    # -------------------------
    nodes = get_int_or_none("nodes", 1)
    ntasks = get_int_or_none("ntasks", 1)
    ntasks_per_node = get_int_or_none("ntasks_per_node", 1)
    cpus_per_task = get_int_or_none("cpus_per_task", 4)

    # -------------------------
    # GPU configuration
    # -------------------------
    gpus = get_str_or_none("gpus")  # can be int-like "2" or "a100:2"
    gpus_per_node = get_str_or_none("gpus_per_node")
    gpus_per_task = get_int_or_none("gpus_per_task")
    gres = get_str_or_none("gres")

    # -------------------------
    # Execution control
    # -------------------------
    mpi = get_str_or_none("mpi", "pmi2") or "pmi2"
    exclusive = slurm.get("exclusive", None)

    # -------------------------
    # Output paths
    # -------------------------
    out_log_default = run_dir / f"slurm-{mode}-%j.out"
    out_log = slurm.get("output", out_log_default)
    if out_log is not None:
        out_log = Path(out_log)
    err_log = slurm.get("error", None)
    if err_log is not None:
        err_log = Path(err_log)

    # -------------------------
    # Extra SBATCH lines
    # -------------------------
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

    # Use ntasks default for srun if ntasks was None
    ntasks_for_srun = ntasks if ntasks is not None else 1
    srun_prefix = f'srun --mpi={mpi} -n "${{SLURM_NTASKS:-{ntasks_for_srun}}}"'
    inner_cmd = f'{srun_prefix} {python_exe} -u "{run_py}" --config "{config_yaml}" {stage_flags}'

    # -------------------------
    # SBATCH header lines
    # -------------------------
    sbatch_lines: list[str] = [
        "#!/bin/bash",
        f"#SBATCH --job-name={job_name}",
    ]

    # Resource selection (all optional)
    if partition:
        sbatch_lines.append(f"#SBATCH --partition={partition}")
    if constraint:
        sbatch_lines.append(f"#SBATCH --constraint={constraint}")
    if qos:
        sbatch_lines.append(f"#SBATCH --qos={qos}")
    if account:
        sbatch_lines.append(f"#SBATCH --account={account}")
    if reservation:
        sbatch_lines.append(f"#SBATCH --reservation={reservation}")

    # Time (optional, but almost always wanted)
    if time:
        sbatch_lines.append(f"#SBATCH --time={time}")

    # Memory (mutually exclusive options; mem is most common)
    if mem:
        sbatch_lines.append(f"#SBATCH --mem={mem}")
    if mem_per_cpu:
        sbatch_lines.append(f"#SBATCH --mem-per-cpu={mem_per_cpu}")
    if mem_per_gpu:
        sbatch_lines.append(f"#SBATCH --mem-per-gpu={mem_per_gpu}")

    # CPU/task configuration
    if nodes is not None:
        sbatch_lines.append(f"#SBATCH --nodes={nodes}")
    if ntasks is not None:
        sbatch_lines.append(f"#SBATCH --ntasks={ntasks}")
    if ntasks_per_node is not None:
        sbatch_lines.append(f"#SBATCH --ntasks-per-node={ntasks_per_node}")
    if cpus_per_task is not None:
        sbatch_lines.append(f"#SBATCH --cpus-per-task={cpus_per_task}")

    # GPU configuration (use whichever is appropriate for your site)
    if gpus:
        sbatch_lines.append(f"#SBATCH --gpus={gpus}")
    if gpus_per_node:
        sbatch_lines.append(f"#SBATCH --gpus-per-node={gpus_per_node}")
    if gpus_per_task is not None:
        sbatch_lines.append(f"#SBATCH --gpus-per-task={gpus_per_task}")
    if gres:
        sbatch_lines.append(f"#SBATCH --gres={gres}")

    # Exclusive access
    if exclusive is True:
        sbatch_lines.append("#SBATCH --exclusive")

    # Output files
    if out_log is not None:
        sbatch_lines.append(f"#SBATCH --output={out_log}")
    if err_log is not None:
        sbatch_lines.append(f"#SBATCH --error={err_log}")

    # Extra user-supplied SBATCH lines
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
    # Default cpus value for environment variables
    # -------------------------
    cpus_default = cpus_per_task if cpus_per_task is not None else 4

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

export OPENBLAS_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{cpus_default}}}"
export OMP_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{cpus_default}}}"

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
