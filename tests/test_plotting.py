# Unit tests for plotting

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest

from valska_hera_beam.plotting import BeamAnalysisPlotter
from constants import CHAINS_DIR

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
    """Test creating beam plotter with different options"""

    with tempfile.NamedTemporaryFile(mode="w+t") as yaml_file:
        yaml_file.writelines(
            "Test1: test/directory1/\n" "Test2: test/directory2/"
        )
        yaml_file.seek(0)

        beam_analysis_plotter = BeamAnalysisPlotter(
            base_chains_dir = CHAINS_DIR,
            paths_file = yaml_file.name,
        )

        yaml_file.close()

        assert beam_analysis_plotter.paths["Test1"] == "test/directory1/"
        assert beam_analysis_plotter.paths["Test2"] == "test/directory2/"


def test_add_analysis_path(beam_analysis):
    """Test adding an analysis path to BeamAnalysisPlotter"""

    key = "test3"
    value = "test/directory3/"

    beam_analysis.add_analysis_path(key, value)

    assert (key, value) in beam_analysis.paths.items()