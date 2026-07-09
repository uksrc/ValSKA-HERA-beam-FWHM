from pathlib import Path

import pytest

from valska.external_tools.pyuvsim.runner import (
    CondaRunner,
    pyuvsimInstall,
)
from valska.external_tools.pyuvsim.slurm import render_submit_script


def _render_script(mode: str) -> str:
    return render_submit_script(
        runner=CondaRunner(
            conda_activate="source /opt/conda/etc/profile.d/conda.sh",
            env_name="pyuvsim",
        ),
        install=pyuvsimInstall(install_path=Path("/opt/pyuvsim")),
        config_yaml=Path("/tmp/config.yaml"),
        run_dir=Path("/tmp/run"),
        slurm={"partition": "standard", "cpus_per_task": 4, "ntasks": 1},
        mode=mode,
    )


def test_render_submit_script_fails_if_not_simulate():
    with pytest.raises(ValueError):
        _render_script("cpu")


class TestSimulateStep:
    def test_render_submit_script_returns_script(self, simulate_script):
        assert simulate_script.startswith("#!/bin/bash")
        assert "#SBATCH" in simulate_script

    def test_render_submit_script_has_specified_conda_setup(
        self, simulate_script
    ):
        assert (
            "source /opt/conda/etc/profile.d/conda.sh\nconda activate pyuvsim"
            in simulate_script
        )

    def test_render_submit_script_has_specified_partition(
        self, simulate_script
    ):
        assert "#SBATCH --partition=standard" in simulate_script
