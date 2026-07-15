import filecmp
from importlib.resources import path
from pathlib import Path
from typing import Any

import pytest

from valska.external_tools.pyuvsim.constants import TOOL_NAME
from valska.external_tools.pyuvsim.runner import CondaRunner
from valska.external_tools.pyuvsim.setup import prepare_pyuvsim_run


@pytest.fixture
def _pyuvsim_config(tmp_path) -> dict[str, Any]:
    """Return a minimal set of config to be passed through prepare_pyuvsim_run"""

    with path(
        "valska.external_tools.pyuvsim.templates", "fov-19.4-oscar-sm.yml"
    ) as file:
        template_yaml = file
    install = None
    runner = CondaRunner(
        "<placeholder conda activate>", "<placeholder env name>"
    )
    results_root = tmp_path
    beam_model = "achromatic_Gaussian"
    sky_model = "GLEAM"
    run_label = "default"
    run_id = "r001"
    return {
        "template_yaml": template_yaml,
        "install": install,
        "runner": runner,
        "results_root": results_root,
        "beam_model": beam_model,
        "sky_model": sky_model,
        "run_label": run_label,
        "run_id": run_id,
    }


@pytest.fixture
def _run_dir(_pyuvsim_config) -> Path:
    """The run directory that should be returned using the minimal config from _pyuvsim_config"""
    run_dir = (
        _pyuvsim_config["results_root"]
        / TOOL_NAME
        / _pyuvsim_config["beam_model"]
        / _pyuvsim_config["sky_model"]
        / _pyuvsim_config["template_yaml"].stem
        / _pyuvsim_config["run_label"]
        / _pyuvsim_config["run_id"]
    )
    return run_dir


def test_prepare_pyuvsim_run_minimal(_pyuvsim_config, _run_dir):
    """Pass the minimum required to prepare_pyuvsim_run to check it prepares and returns the correct paths"""

    test_run = prepare_pyuvsim_run(**_pyuvsim_config)

    assert isinstance(test_run, dict)

    run_dir = _run_dir

    assert test_run["manifest_json"] == run_dir / "manifest.json"
    assert test_run["obsparam_yaml"] == run_dir / "obsparam.yaml"
    assert test_run["run_dir"] == run_dir
    assert test_run["submit_sh_simulate"] == run_dir / "submit_simulate.sh"


def test_prepare_pyuvsim_run_creates_files(_pyuvsim_config, _run_dir):
    """Check it actually creates the files in the run directory"""

    prepare_pyuvsim_run(**_pyuvsim_config)

    run_dir = _run_dir

    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "obsparam.yaml").exists()
    assert (run_dir / "submit_simulate.sh").exists()


def test_prepare_pyuvsim_run_correct_manifest(_pyuvsim_config, _run_dir):
    """Check the manifest includes correct paths and other config"""

    prepare_pyuvsim_run(**_pyuvsim_config)

    run_dir = _run_dir

    manifest = (run_dir / "manifest.json").read_text()

    assert str(_pyuvsim_config["results_root"]) in manifest
    assert str(run_dir) in manifest
    assert str(_pyuvsim_config["template_yaml"]) in manifest
    assert _pyuvsim_config["sky_model"] in manifest
    assert _pyuvsim_config["runner"].conda_activate in manifest


@pytest.mark.parametrize(
    "optional_params, expected_configs",
    [
        ({"slurm": {"time": "12:00:00"}}, ["time", "12:00:00"]),
        ({"slurm_cpu": {"cpus_per_task": 4}}, ["cpus_per_task", "4"]),
        ({"fwhm_perturb_frac": 0.1}, ["fwhm_perturb_frac", "0.1"]),
    ],
)
def test_prepare_pyuvsim_run_optional_parameters(
    _pyuvsim_config, _run_dir, optional_params, expected_configs
):
    """Check that optional parameters are added to the manifest"""

    prepare_pyuvsim_run(**_pyuvsim_config, **optional_params)

    run_dir = _run_dir

    manifest = (run_dir / "manifest.json").read_text()

    # Check all expected configs appear in the manifest
    assert all(config in manifest for config in expected_configs)


def test_prepare_pyuvsim_run_copies_reference_files_with_default_template(
    _pyuvsim_config, _run_dir
):
    """Check the reference simulation config and catalogue files are copied when the default template fov-19.4-oscar-sm.yml is used"""

    prepare_pyuvsim_run(**_pyuvsim_config)

    run_dir = _run_dir

    with path("valska.external_tools.pyuvsim", "templates") as file:
        template_root = file

    folders = ["telescope_config", "catalog_files"]

    # Check the root reference folders exist in the run directory
    assert all((run_dir / folder).exists() for folder in folders)

    # Compare the reference folders with the ones in the run directory
    comparisons = list(
        filecmp.dircmp(run_dir / folder, template_root / folder)
        for folder in folders
    )

    # Assert no unique files on either side, and that there are files in common
    assert all(
        len(comparison.left_only) + len(comparison.right_only) == 0
        and len(comparison.common_files) > 0
        for comparison in comparisons
    )
