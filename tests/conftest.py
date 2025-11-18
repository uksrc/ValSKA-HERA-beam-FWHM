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

    path_manager = PathManager(
        BASE_DIR,
        CHAINS_DIR,
        DATA_DIR,
        RESULTS_DIR,
    )

    yield path_manager
