"""SLURM submit-script rendering for pyuvsim runs."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .runner import pyuvsimInstall, CondaRunner, ContainerRunner


def render_submit_script(
    *,
    runner: CondaRunner | ContainerRunner,
    install: pyuvsimInstall,
    config_yaml: Path,
    run_dir: Path,
    slurm: Mapping[str, object] | None = None,
    mode: str = "simulate",
) -> str:
    """
    Render a SLURM submit script for a pyuvsim run.

    This function aims to be HPC-friendly and debugging-friendly:

    - emits clear "what am I running" information
    - prints SLURM_* environment variables
    - uses ``mpirun -n "$SLURM_NTASKS"`` by default

    Parameters
    ----------
    runner
        How pyuvsim is executed (currently conda; container support later).
    install
        Optional metadata describing where a local pyuvsim checkout lives.
        This is used for provenance/debug printing only; execution does not depend
        on a repo script in the MVP.
    config_yaml
        Path to the rendered pyuvsim obsparam YAML to run.
    run_dir
        Run directory containing configs/logs/manifests.
    slurm
        SLURM settings map. Usually derived from runtime_paths.yaml defaults plus CLI overrides.

        Any key set to ``None`` (or not present) will be omitted from the
        generated script.

        Supported keys (all optional)::

            Job identification:
              - ``job_name``: Full job name
              - ``job_name_prefix``: Prefix for auto-generated job name
                (default: "pyuvsim")
            Resource selection:
              - ``partition``
              - ``constraint``
              - ``qos``
              - ``account``
              - ``reservation``
            Time and memory:
              - ``time``: Wall time limit (default: "12:00:00")
              - ``mem``: Memory per node (default: "8G")
              - ``mem_per_cpu``
            CPU/task configuration:
              - ``nodes``: Number of nodes (default: 1)
              - ``ntasks``: Total number of tasks (default: 1)
              - ``ntasks_per_node``: Tasks per node (default: 1)
              - ``cpus_per_task``: CPUs per task (default: 4)
            Execution control:
              - ``mpi``: MPI type for srun (default: "pmi2")
              - ``exclusive``: Request exclusive node access
            Output:
              - ``output``: Stdout log path (default: ``run_dir/slurm-simulate-%j.out``)
              - ``error``: Stderr log path
            Extensibility:
              - ``extra_sbatch``: Additional ``#SBATCH`` lines
                (without the ``"#SBATCH "`` prefix)

    mode
        Execution mode. Currently only:
        - ``"simulate"``

    Notes
    -----
    Timing is implemented using only ``date`` for portability.
    """
    slurm = dict(slurm or {})

    if mode != "simulate":
        raise ValueError("mode must be: 'simulate'")

    def get_str_or_none(key: str, default: str | None = None) -> str | None:
        val = slurm.get(key, default)
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    def get_int_or_none(key: str, default: int | None = None) -> int | None:
        val = slurm.get(key, default)
        if val is None:
            return None
        return int(val)

    # -------------------------
    # Job identification
    # -------------------------
    job_name_prefix = get_str_or_none("job_name_prefix", "pyuvsim") or "pyuvsim"
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

    # -------------------------
    # CPU/task configuration
    # -------------------------
    nodes = get_int_or_none("nodes", 1)
    ntasks = get_int_or_none("ntasks", 1)
    ntasks_per_node = get_int_or_none("ntasks_per_node", 1)
    cpus_per_task = get_int_or_none("cpus_per_task", 4)

    # -------------------------
    # Execution control
    # -------------------------
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

    # -------------------------
    # Runner prefix
    # -------------------------
    if isinstance(runner, CondaRunner):
        prefix = runner.bash_prefix()
        python_exe = "python"
    else:
        bind_args = " ".join(f'-B "{p}"' for p in runner.bind_paths)
        prefix = ""
        python_exe = (
            f'{runner.apptainer_exe} exec {bind_args} "{runner.image_path}" python'
        ).strip()

    # -------------------------
    # pyuvsim command
    # -------------------------
    ntasks_for_mpi = ntasks if ntasks is not None else 1
    mpi_prefix = f'mpirun -n "${{SLURM_NTASKS:-{ntasks_for_mpi}}}"'

    pyuvsim_code = (
        "import pyuvsim; "
        "import pyuvsim.uvsim; "
        f"pyuvsim.uvsim.run_uvsim({str(config_yaml)!r}, "
        "quiet=False, block_nonroot_stdout=True)"
    )

    inner_cmd = f'{mpi_prefix} {python_exe} -u -c "{pyuvsim_code}"'
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
    if qos:
        sbatch_lines.append(f"#SBATCH --qos={qos}")
    if account:
        sbatch_lines.append(f"#SBATCH --account={account}")
    if reservation:
        sbatch_lines.append(f"#SBATCH --reservation={reservation}")

    if time:
        sbatch_lines.append(f"#SBATCH --time={time}")

    if mem:
        sbatch_lines.append(f"#SBATCH --mem={mem}")
    if mem_per_cpu:
        sbatch_lines.append(f"#SBATCH --mem-per-cpu={mem_per_cpu}")

    if nodes is not None:
        sbatch_lines.append(f"#SBATCH --nodes={nodes}")
    if ntasks is not None:
        sbatch_lines.append(f"#SBATCH --ntasks={ntasks}")
    if ntasks_per_node is not None:
        sbatch_lines.append(f"#SBATCH --ntasks-per-node={ntasks_per_node}")
    if cpus_per_task is not None:
        sbatch_lines.append(f"#SBATCH --cpus-per-task={cpus_per_task}")

    if exclusive is True:
        sbatch_lines.append("#SBATCH --exclusive")

    if out_log is not None:
        sbatch_lines.append(f"#SBATCH --output={out_log}")
    if err_log is not None:
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

    cpus_default = cpus_per_task if cpus_per_task is not None else 4
    install_path = (
        str(install.install_path)
        if install is not None and install.install_path is not None
        else "(not recorded)"
    )
    execution_interface = "pyuvsim.uvsim.run_uvsim"
    return f"""{sbatch_block}

set -eo pipefail

# -----------------------------------------------------------------------------
# ValSKA-generated pyuvsim submit script
#
# Mode: {mode}
# Config: {config_yaml}
# Run dir: {run_dir}
# -----------------------------------------------------------------------------

echo "========================================"
echo "ValSKA / pyuvsim SLURM job starting"
echo "========================================"

START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Start time (UTC):  $START_ISO"
echo "Hostname:          $(hostname)"
echo "Working dir:       $(pwd)"
echo "Run dir:           {run_dir}"
echo "Config:            {config_yaml}"
echo "pyuvsim install:   {install_path}"
echo "pyuvsim interface: {execution_interface}"
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

echo "Preflight import checks:"
python -c "import pyuvsim; import pyuvsim.uvsim" || exit 3
echo "----------------------------------------"

echo "Command:"
printf '  %s\n' "{inner_cmd}"
echo "----------------------------------------"

JOBID="${{SLURM_JOB_ID:-unknown}}"
TIMING_FILE="{run_dir}/timing-{mode}-${{JOBID}}.txt"

echo "Timing file:       $TIMING_FILE"
echo "----------------------------------------"

START_EPOCH="$(date -u +%s)"
START_NS="$(date -u +%s%N || true)"

set +e
{inner_cmd}
RC=$?
set -e

END_EPOCH="$(date -u +%s)"
END_NS="$(date -u +%s%N || true)"
END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

ELAPSED_S="$((END_EPOCH - START_EPOCH))"
ELAPSED_NS=""

if [[ "$START_NS" =~ ^[0-9]+$ ]] && [[ "$END_NS" =~ ^[0-9]+$ ]]; then
  ELAPSED_NS="$((END_NS - START_NS))"
fi

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
  echo "ERROR: pyuvsim command failed with exit code $RC"
  exit $RC
fi

echo "----------------------------------------"
echo "ValSKA / pyuvsim SLURM job complete"
echo "========================================"
"""