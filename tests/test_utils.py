# Unit tests for utils

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest
from constants import (
    BASE_DIR,
    CHAINS_DIR,
    DATA_DIR,
    RESULTS_DIR,
)

from valska_hera_beam import utils

UTILS_DIR = Path(os.path.abspath(utils.__file__)).parent.resolve()


def test_make_timestamp():
    """
    Test make timestamp gives current time to nearest
    minute
    """

    time_now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    timestamp = utils.make_timestamp()

    assert time_now[0:4] == timestamp[0:4]
    assert time_now[5:6] == timestamp[5:6]
    assert time_now[8:9] == timestamp[8:9]
    assert time_now[11:15] == timestamp[11:15]


def test_load_paths_no_input():
    """Test load paths from default yaml file"""

    paths = utils.load_paths()

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

        paths = utils.load_paths(yaml_file.name)

        # Reads yaml_file
        assert paths["Test1"] == "test/directory1/"
        assert paths["Test2"] == "test/directory2/"

        yaml_file.close()


def test_load_paths_with_input_error():
    """Test load paths from non-existant yaml file"""

    with pytest.raises(FileNotFoundError):
        paths = utils.load_paths("nonexistant_yaml_file.yml")


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


def test_repr(path_manager):
    """Test __repr__ method"""

    expected_dictionary = {
        "utils_dir": UTILS_DIR,
        "package_dir": UTILS_DIR,
        "base_dir": BASE_DIR,
        "chains_dir": CHAINS_DIR,
        "data_dir": DATA_DIR,
        "results_dir": RESULTS_DIR,
    }

    repr_string = path_manager.__repr__()
    print(repr_string)

    expected_strs = [
        f"  {name}: {path}" for name, path in expected_dictionary.items()
    ]
    expected_string = "PathManager:\n" + "\n".join(expected_strs)
    print(expected_string)

    assert expected_string == repr_string


def test_path_manager_create_sub_dir(path_manager):
    """Test create sub directory"""

    new_dir = "new_directory"

    with tempfile.TemporaryDirectory() as base_dir:

        # Update the chains dir
        path_manager.chains_dir = Path(base_dir)

        returned_dir = path_manager.create_subdir("chains_dir", new_dir)

        assert returned_dir == Path(base_dir).joinpath(new_dir)
        assert returned_dir.exists()


def test_path_manager_find_file(path_manager):
    """Test find file with named directory"""

    with tempfile.NamedTemporaryFile(suffix=".dat") as test_file:

        path_manager.chains_dir = Path(test_file.name).parent

        result = path_manager.find_file("*.dat", path_name="chains_dir")

        assert result == [Path(test_file.name)]


def test_path_manager_find_file_default(path_manager):
    """Test find file from default directory"""

    with tempfile.NamedTemporaryFile(suffix=".dat") as test_file:

        path_manager.base_dir = Path(test_file.name).parent

        result = path_manager.find_file("*.dat")

        assert result == [Path(test_file.name)]


@pytest.mark.parametrize(
    "pm, chains",
    [
        ("class", True),
        ("class", False),
        ("method", True),
        ("method", False),
    ],
)
def test_create_path_manager_default(pm, chains):
    """
    Test creation of default path manager
    with or without default chains directory
    """

    with tempfile.TemporaryDirectory() as base_dir:

        test_dir = Path(base_dir + "/one/two/three/")

        if chains:
            os.mkdir(base_dir + "/chains")

        with patch("inspect.getfile", new_callable=PropertyMock) as getfile:

            getfile.return_value = str(test_dir)

            if pm == "class":
                path_manager = utils.PathManager()
            if pm == "method":
                path_manager = utils.get_default_path_manager()

            assert path_manager.utils_dir == test_dir.parent.resolve()
            assert path_manager.package_dir == test_dir.parent.resolve()
            assert path_manager.base_dir == Path(base_dir).resolve()
            assert (
                path_manager.chains_dir == Path(base_dir + "/chains").resolve()
            )
            assert path_manager.data_dir == Path(base_dir + "/data").resolve()
            assert (
                path_manager.results_dir
                == Path(base_dir + "/results").resolve()
            )

            assert Path(base_dir + "/data").exists()
            assert Path(base_dir + "/results").exists()
