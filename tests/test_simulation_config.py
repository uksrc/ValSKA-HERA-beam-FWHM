# tests/test_simulation_config.py

from pathlib import Path
from unittest.mock import Mock, patch

import numpy
import pytest
from astropy.coordinates import Angle

from valska.simulation_config import SimulationConfig

CONFIG_TEXT = (
    "beam_paths:\n"
    "  0: !AnalyticBeam\n"
    "{beam_spec}\n"
    "    reference_frequency: 150000000.0\n"
    "telescope_location: (-26.7, 20.0, 1073.0)\n"
    "telescope_name: Dummy"
)
BEAM_SPEC = "    class: GaussianBeam\n    sigma: 0.2"

ANTENNA_LAYOUT = (
    "Name Number BeamID E N U\n"
    "ANT0 0 0 0.0 0.0 0.0\n"
    "ANT1 1 0 10.0 0.0 0.0\n"
    "ANT2 2 0 20.0 0.0 0.0"
)


@pytest.fixture
def telescope_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "telescope.yaml"
    # path.write_text(CONFIG_TEXT.format(beam_spec=BEAM_SPEC))
    return path


@pytest.fixture
def array_layout(tmp_path: Path) -> Path:
    path = tmp_path / "array_layout.txt"
    path.write_text(ANTENNA_LAYOUT)
    return path


@pytest.fixture
def config(tmp_path, telescope_yaml, array_layout):
    catalog = tmp_path / "catalog.skyh5"
    catalog.touch()

    if not telescope_yaml.exists():
        telescope_yaml.write_text(CONFIG_TEXT.format(beam_spec=BEAM_SPEC))

    return {
        "telescope": {
            "telescope_config_name": str(telescope_yaml),
            "array_layout": str(array_layout),
        },
        "sources": {
            "catalog": str(catalog),
        },
    }


def test_loads_config_from_mapping(config, monkeypatch):
    monkeypatch.setattr(
        "valska.simulation_config.read_skyh5_catalogue",
        Mock(return_value="catalog"),
    )

    sim = SimulationConfig(config)

    assert sim.num_antennas == 3
    assert sim.catalog == "catalog"
    assert sim.telescope_config["beam_paths"][0]["sigma"] == 0.2


def test_loads_config_from_yaml(tmp_path, config, monkeypatch):
    yaml_path = tmp_path / "config.yaml"

    import yaml

    yaml_path.write_text(yaml.safe_dump(config))

    monkeypatch.setattr(
        "valska.simulation_config.read_skyh5_catalogue",
        Mock(return_value="catalog"),
    )

    sim = SimulationConfig(yaml_path)

    assert sim.num_antennas == 3


def test_missing_required_section(tmp_path):
    config = {
        "telescope": {},
    }

    with pytest.raises(ValueError, match="sources"):
        SimulationConfig(config)


def test_missing_required_key(config):
    del config["telescope"]["array_layout"]

    with pytest.raises(ValueError, match="telescope.array_layout"):
        SimulationConfig(config)


def test_relative_paths_use_template_dir(tmp_path, monkeypatch):
    template = tmp_path / "template"
    template.mkdir()

    (template / "telescope.yaml").write_text(
        "beam_paths:\n  - type: gaussian\n"
    )

    (template / "layout.txt").write_text(
        "Name Number BeamID E N U\nANT0 0 0 0 0 0\n"
    )

    (template / "catalog.skyh5").touch()

    config = {
        "telescope": {
            "telescope_config_name": "telescope.yaml",
            "array_layout": "layout.txt",
        },
        "sources": {
            "catalog": "catalog.skyh5",
        },
    }

    monkeypatch.setattr(
        "valska.simulation_config.read_skyh5_catalogue",
        Mock(return_value="catalog"),
    )

    sim = SimulationConfig(config, template)

    assert sim.tel_cfg_path == template / "telescope.yaml"
    assert sim.array_layout_path == template / "layout.txt"
    assert sim.catalog_path == template / "catalog.skyh5"


def test_missing_files_are_reported_together(tmp_path):
    config = {
        "telescope": {
            "telescope_config_name": "missing_tel.yaml",
            "array_layout": "missing_layout.txt",
        },
        "sources": {
            "catalog": "missing.skyh5",
        },
    }

    with pytest.raises(FileNotFoundError) as exc:
        SimulationConfig(config)

    message = str(exc.value)

    assert "missing_tel.yaml" in message
    assert "missing_layout.txt" in message
    assert "missing.skyh5" in message


def test_get_num_antennas_ignores_comments(tmp_path):
    layout = tmp_path / "layout.txt"
    layout.write_text(
        "Name Number BeamID E N U\n# comment\nANT0 0 0 0 0 0\n\nANT1 1 0 1 1 1"
    )
    sim = SimulationConfig.__new__(SimulationConfig)

    assert sim._get_num_antennas(layout) == 2


def test_source_ra():
    sim = SimulationConfig.__new__(SimulationConfig)

    sim.catalog = Mock()
    sim.catalog.ra = Angle("10d")

    assert sim.source_ra == sim.catalog.ra


def test_latitude():
    sim = SimulationConfig.__new__(SimulationConfig)

    sim.telescope_config = {"telescope_location": "(10, 20, 100)"}

    latitude = sim.latitude

    assert latitude.degree == 10


def test_beam_shape_from_type():
    sim = SimulationConfig.__new__(SimulationConfig)

    sim.telescope_config = {"beam_paths": [{"type": "gaussian"}]}

    assert sim.beam_shape == "GaussianBeam"


def test_beam_sigma():
    sim = SimulationConfig.__new__(SimulationConfig)

    sim.telescope_config = {"beam_paths": [{"sigma": 1.5}]}

    assert sim.beam_sigma.rad == 1.5


@pytest.mark.parametrize(
    ("beam_spec", "expected_shape", "expected_size"),
    [
        (
            "    class: GaussianBeam\n    sigma: 0.2",
            "GaussianBeam",
            0.2,
        ),
        (
            "    type: gaussian\n    sigma: 0.2",
            "GaussianBeam",
            0.2,
        ),
        (
            "    class: AiryBeam\n    diameter: 14.0",
            "AiryBeam",
            14.0,
        ),
        (
            "    type: airy\n    diameter: 14.0",
            "AiryBeam",
            14.0,
        ),
    ],
)
def test_simulation_config_beam_mapping(
    beam_spec, expected_shape, expected_size, telescope_yaml, config
):

    telescope_yaml.write_text(CONFIG_TEXT.format(beam_spec=beam_spec))

    with patch(
        "valska.simulation_config.read_skyh5_catalogue",
        return_value=Mock(),
    ):
        sim_config = SimulationConfig(config)

    assert sim_config.beam_shape == expected_shape

    if expected_shape == "GaussianBeam":
        numpy.testing.assert_allclose(sim_config.beam_sigma.rad, expected_size)
        assert sim_config.diameter is None

    elif expected_shape == "AiryBeam":
        assert sim_config.beam_sigma is None
        numpy.testing.assert_allclose(sim_config.diameter.value, expected_size)

    numpy.testing.assert_allclose(sim_config.latitude.deg, -26.7)
