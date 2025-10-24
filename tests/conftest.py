"""
Pytest Fixtures
"""

import pytest
from constants import (
    BASE_DIR,
    CHAINS_DIR,
    DATA_DIR,
    RESULTS_DIR,
)

from valska_hera_beam.utils import PathManager


@pytest.fixture(scope="package", name="path_manager")
def path_manager_fixture():
    """
    PathManager
    """

    base_dir = BASE_DIR
    chains_dir = CHAINS_DIR
    data_dir = DATA_DIR
    results_dir = RESULTS_DIR

    path_manager = PathManager(
        base_dir,
        chains_dir,
        data_dir,
        results_dir,
    )

    yield path_manager
