import filecmp
import shutil
from copy import deepcopy
from importlib.resources import path
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy
import pytest
from pyradiosky import SkyModel
from ruamel.yaml.comments import CommentedSeq

from valska.external_tools.pyuvsim.constants import TOOL_NAME
from valska.external_tools.pyuvsim.runner import CondaRunner
from valska.external_tools.pyuvsim.setup import prepare_pyuvsim_run
from valska.external_tools.pyuvsim.setup_beamcheck import (
    prepare_beam_check_cfg,
)
from valska.utils_yaml import dump_yaml, load_yaml


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


def test_prepare_pyuvsim_run_beamcheck_creates_files(
    _pyuvsim_config, _run_dir
):
    prepare_pyuvsim_run(
        **_pyuvsim_config,
        make_beam_check=True,
    )

    assert (_run_dir / "obsparam_beamcheck.yaml").exists()
    assert (_run_dir / "submit_beamcheck.sh").exists()


def test_prepare_pyuvsim_run_beamcheck_returns_outputs(
    _pyuvsim_config, _run_dir
):

    out = prepare_pyuvsim_run(
        **_pyuvsim_config,
        make_beam_check=True,
    )

    assert out["obsparam_beamcheck_yaml"] == (
        _run_dir / "obsparam_beamcheck.yaml"
    )

    assert out["submit_sh_beamcheck"] == (_run_dir / "submit_beamcheck.sh")


def test_prepare_pyuvsim_run_beamcheck_preserves_main_configuration(
    _pyuvsim_config, _run_dir
):
    """The beam-check simulation should use a modified copy of the main
    configuration without altering the main obsparam.yaml.
    """

    prepare_pyuvsim_run(
        **_pyuvsim_config,
        make_beam_check=True,
    )

    main_cfg = load_yaml(_run_dir / "obsparam.yaml")
    beam_cfg = load_yaml(_run_dir / "obsparam_beamcheck.yaml")

    # The beam-check configuration should differ from the main one.
    assert main_cfg != beam_cfg

    # The catalogue should only be changed for the beam-check run.
    assert main_cfg["sources"]["catalog"] != beam_cfg["sources"]["catalog"]

    assert (
        beam_cfg["sources"]["catalog"].count(
            "catalog_files/zenith_single_source"
        )
        == 1
    )

    # The main configuration should still point at the original catalogue.
    assert (
        main_cfg["sources"]["catalog"].count(
            "catalog_files/zenith_single_source"
        )
        == 0
    )


def test_prepare_pyuvsim_run_beamcheck_extends_time_array(
    _pyuvsim_config, _run_dir
):
    prepare_pyuvsim_run(
        **_pyuvsim_config,
        make_beam_check=True,
        hours_each_side=2.0,
    )

    beam_cfg = load_yaml(_run_dir / "obsparam_beamcheck.yaml")

    times = numpy.asarray(beam_cfg["time"]["time_array"])

    duration_hours = (times[-1] - times[0]) * 24.0

    assert duration_hours >= 4.0


def test_prepare_pyuvsim_run_beamcheck_creates_zenith_catalog(
    _pyuvsim_config, _run_dir
):

    expected_dec = -30.72152777777791
    expected_ra = 2.2234363

    with patch(
        "valska.external_tools.pyuvsim.setup_beamcheck._lst_at_time"
    ) as mock_lst:
        mock_lst.side_effect = [expected_ra, 1.2, 4.7]

        prepare_pyuvsim_run(
            **_pyuvsim_config,
            make_beam_check=True,
        )

    sky_path = (
        _run_dir
        / "catalog_files"
        / f"zenith_single_source_{expected_ra:0.2f}_{expected_dec:0.2f}.skyh5"
    )

    assert sky_path.exists()

    sky = SkyModel.from_file(sky_path)

    assert len(sky.ra) == 1
    assert len(sky.dec) == 1

    assert numpy.isclose(sky.dec[0].deg, expected_dec)


def test_prepare_pyuvsim_run_beamcheck_missing_telescope_config(
    _pyuvsim_config, _run_dir, tmp_path
):
    cfg = load_yaml(_pyuvsim_config["template_yaml"])

    cfg["telescope"]["telescope_config_name"] = "does/not/exist.yaml"

    template = tmp_path / "bad_template.yaml"
    dump_yaml(cfg, template)

    with pytest.raises(FileNotFoundError):
        prepare_pyuvsim_run(
            **{
                **_pyuvsim_config,
                "template_yaml": template,
            },
            make_beam_check=True,
        )


def test_load_yaml_rejects_non_mapping(tmp_path):
    path = tmp_path / "list.yaml"
    path.write_text("- 1\n- 2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected a mapping"):
        load_yaml(path)


def test_prepare_beam_check_cfg_does_not_modify_input(
    _pyuvsim_config, tmp_path
):
    template = Path(_pyuvsim_config["template_yaml"])
    cfg = load_yaml(template)

    original = deepcopy(cfg)

    prepare_beam_check_cfg(
        cfg,
        run_dir=tmp_path,
        template_dir=template.parent,
        hours_each_side=None,
    )

    assert cfg == original


def test_prepare_beam_check_cfg_does_not_alter_times(
    _pyuvsim_config, tmp_path
):
    original_template = Path(_pyuvsim_config["template_yaml"])

    # Recreate the expected directory layout.
    shutil.copytree(
        original_template.parent,
        tmp_path,
        dirs_exist_ok=True,
    )

    template = tmp_path / "long_time_template.yaml"

    cfg = load_yaml(original_template)

    times = numpy.linspace(
        2458098.0 - 2 / 24,
        2458098.0 + 2 / 24,
        100,
    )

    cfg["time"]["time_array"] = CommentedSeq(times.tolist())

    dump_yaml(cfg, template)

    beam_cfg = prepare_beam_check_cfg(
        cfg,
        run_dir=tmp_path,
        template_dir=tmp_path,
        hours_each_side=None,
    )

    assert numpy.allclose(
        beam_cfg["time"]["time_array"],
        times,
    )
