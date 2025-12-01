"""
Pytest Fixtures
"""

import pytest
from constants import (
    BASE_DIR,
    CHAINS_DIR,
    DATA_DIR,
    EOR_PS,
    NOISE_RATIO,
    RESULTS_DIR,
)

from valska_hera_beam.plotting import BeamAnalysisPlotter
from valska_hera_beam.utils import PathManager


@pytest.fixture(scope="package", name="path_manager")
def path_manager_fixture():
    """
    PathManager
    """

    path_manager = PathManager(
        BASE_DIR,
        CHAINS_DIR,
        DATA_DIR,
        RESULTS_DIR,
    )

    yield path_manager


@pytest.fixture(scope="package", name="beam_analysis")
def beam_analysis_fixture():
    """
    BeamAnalysisPlotter
    """

    paths = {
        "Test1": "test/directory1/",
        "Test2": "test/directory2/",
    }

    beam_analysis_plotter = BeamAnalysisPlotter(
        base_chains_dir = CHAINS_DIR,
        paths = paths,
        eor_ps = EOR_PS,
        noise_ratio = NOISE_RATIO,
    )

    yield beam_analysis_plotter

