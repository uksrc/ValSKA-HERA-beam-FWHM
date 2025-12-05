# Unit tests for plotting

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest

from valska_hera_beam import plotting
from constants import (
    CHAINS_DIR,
    EOR_PS,
    NOISE_RATIO,
    MockDataContainer,
)

# @pytest.mark.parametrize(
#     "chains, paths_file, paths, eor_ps, noise_ratio, expected_ps",
#     [
#         (CHAINS_DIR, None, None, EOR_PS, NOISE_RATIO),
#         ("class", False),
#         ("method", True),
#         ("method", False),
#     ],
# )
def test_create_beam_plotter_with_paths_file():
    """Test creating beam plotter with paths in yaml file"""

    with tempfile.NamedTemporaryFile(mode="w+t") as yaml_file:
        yaml_file.writelines(
            "Test1: test/directory1/\n" "Test2: test/directory2/"
        )
        yaml_file.seek(0)

        beam_analysis_plotter = plotting.BeamAnalysisPlotter(
            base_chains_dir = CHAINS_DIR,
            paths_file = yaml_file.name,
        )

        yaml_file.close()

        assert beam_analysis_plotter.paths["Test1"] == "test/directory1/"
        assert beam_analysis_plotter.paths["Test2"] == "test/directory2/"

def test_create_beam_plotter_with_paths_dict():
    """Test creating beam plotter with paths in dictionary"""

    paths = {
        "Test1": "test/directory1/",
        "Test2": "test/directory2/",
    }

    beam_analysis_plotter = plotting.BeamAnalysisPlotter(
        base_chains_dir = CHAINS_DIR,
        paths = paths,
    )

    assert beam_analysis_plotter.paths["Test1"] == "test/directory1/"
    assert beam_analysis_plotter.paths["Test2"] == "test/directory2/"

def test_add_analysis_path(beam_analysis):
    """Test adding an analysis path to BeamAnalysisPlotter"""

    key = "test3"
    value = "test/directory3/"

    beam_analysis.add_analysis_path(key, value)

    assert (key, value) in beam_analysis.paths.items()


@pytest.mark.parametrize(
    "analysis_keys, labels, expected_ps, expected_results",
    [
        (
            ["Test1"], None, None, 
            {
                "dirnames": ["test/directory1/"], 
                "dir_prefix": Path(CHAINS_DIR),
                "exp_ps": EOR_PS * NOISE_RATIO, 
                "labels": ["Test1"]
            }
        ),
        (
            ["Test1", "Test2"], None, None, 
            {
                "dirnames": ["test/directory1/", "test/directory2/"], 
                "dir_prefix": Path(CHAINS_DIR),
                "exp_ps": EOR_PS * NOISE_RATIO, 
                "labels": ["Test1", "Test2"]
            }
        ),
        (
            ["Test1"], ["Label1"], 1.0, 
            {
                "dirnames": ["test/directory1/"], 
                "dir_prefix": Path(CHAINS_DIR),
                "exp_ps": 1.0, 
                "labels": ["Label1"]
            }
        ),
    ],
)
@patch("valska_hera_beam.plotting.DataContainer", MockDataContainer)
def test_get_data_container(beam_analysis, analysis_keys, labels, expected_ps, expected_results):
    """
    Test for get_data_container
    """

    data_container = beam_analysis.get_data_container(
            analysis_keys,
            labels,
            expected_ps,
    )

    assert data_container.Ndirs == len(expected_results["dirnames"])
    assert data_container.dirnames == expected_results["dirnames"]
    assert data_container.dir_prefix == expected_results["dir_prefix"]
    assert data_container.expected_ps == expected_results["exp_ps"]
    assert data_container.labels == expected_results["labels"]


