from pathlib import Path

from valska_hera_beam.external_tools.bayeseor.runner import (
    BayesEoRInstall,
    CondaRunner,
)
from valska_hera_beam.external_tools.bayeseor.slurm import render_submit_script


def _render_script(mode: str) -> str:
    return render_submit_script(
        runner=CondaRunner(
            conda_activate="source /opt/conda/etc/profile.d/conda.sh",
            env_name="bayeseor",
        ),
        install=BayesEoRInstall(repo_path=Path("/opt/BayesEoR")),
        config_yaml=Path("/tmp/config.yaml"),
        run_dir=Path("/tmp/run"),
        slurm={"partition": "a100_gpu", "cpus_per_task": 4, "ntasks": 1},
        mode=mode,
    )


def test_render_submit_script_gpu_run_includes_non_blocking_gpu_diagnostics():
    script = _render_script("gpu_run")

    assert 'echo "Hostname:          $(hostname)"' in script
    assert (
        'echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-<unset>}"'
        in script
    )
    assert "if command -v nvidia-smi >/dev/null 2>&1; then" in script
    assert "nvidia-smi -L || true" in script
    assert 'echo "nvidia-smi not found on PATH"' in script


def test_render_submit_script_cpu_omits_gpu_diagnostics():
    script = _render_script("cpu")

    assert "CUDA_VISIBLE_DEVICES" not in script
    assert "nvidia-smi -L || true" not in script
