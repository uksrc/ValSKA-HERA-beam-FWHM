# Unit tests for utils

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from constants import (
    BASE_DIR,
    CHAINS_DIR,
    DATA_DIR,
    RESULTS_DIR,
)

import valska_hera_beam.utils
from valska_hera_beam.utils import load_paths, make_timestamp

UTILS_DIR = Path(
    os.path.abspath(valska_hera_beam.utils.__file__)
).parent.resolve()


def test_make_timestamp():
    """
    Test make timestamp gives current time to nearest
    minute
    """

    time_now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    timestamp = make_timestamp()

    assert time_now[0:4] == timestamp[0:4]
    assert time_now[5:6] == timestamp[5:6]
    assert time_now[8:9] == timestamp[8:9]
    assert time_now[11:15] == timestamp[11:15]


def test_load_paths_no_input():
    """Test load paths from default yaml file"""

    paths = load_paths()

    # Reads paths.yaml from config directory
    # Test first path
    assert (
        paths["EoRFg"]
        == "v4d0/EoRFg/MN-23-23-38-2-2.63-2.82-6.2E-03-lp-dPS-v1/"
    )


def test_load_paths_with_input():
    """Test load paths from yaml file"""

    with tempfile.NamedTemporaryFile(mode="w+t") as yaml_file:
        yaml_file.writelines(
            "Test1: test/directory1/\n" "Test2: test/directory2/"
        )
        yaml_file.seek(0)

        paths = load_paths(yaml_file.name)

        # Reads yaml_file
        assert paths["Test1"] == "test/directory1/"
        assert paths["Test2"] == "test/directory2/"

        yaml_file.close()


def test_path_manager_get_paths(path_manager):
    """
    Test PathManager get_paths method
    This returns a dictionary of all the paths
    """

    expected_dictionary = {
        "utils_dir": UTILS_DIR,
        "package_dir": UTILS_DIR,
        "base_dir": BASE_DIR,
        "chains_dir": CHAINS_DIR,
        "data_dir": DATA_DIR,
        "results_dir": RESULTS_DIR,
    }

    assert path_manager.get_paths() == expected_dictionary


@pytest.mark.parametrize(
    "name, value",
    [
        ("utils_dir", UTILS_DIR),
        ("package_dir", UTILS_DIR),
        ("base_dir", BASE_DIR),
        ("chains_dir", CHAINS_DIR),
        ("data_dir", DATA_DIR),
        ("results_dir", RESULTS_DIR),
    ],
)
def test_path_manager_get_path(path_manager, name, value):
    """
    Test PathManager get_path method
    This returns a dictionary of all the paths
    """

    assert path_manager.get_path(name) == value


def test_path_manager_get_path_error(path_manager):
    """Test get_path with incorrect name"""

    with pytest.raises(KeyError):
        path_manager.get_path("incorrect_name")
