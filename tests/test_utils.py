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
    """Test load paths from non-existent yaml file"""

    with pytest.raises(FileNotFoundError):
        load_paths("nonexistent_yaml_file.yml")


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

    expected_strs = [
        f"  {name}: {path}" for name, path in expected_dictionary.items()
    ]
    expected_string = "PathManager:\n" + "\n".join(expected_strs)

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
            elif pm == "method":
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


@pytest.mark.parametrize(
    "key, prefix, label_prefix, expected_result",
    [
        ("GSM_FgEoR_-1e0pp", "GSM_FgEoR_", None, "GSM -1%"),
        ("GSM_FgEoR_-1e1pp", "GSM_FgEoR_", None, "GSM -10%"),
        ("GSM_FgEoR_-1e-3pp", "GSM_FgEoR_", None, "GSM -0.001%"),
        ("GSM_FgEoR_-1.123e0pp", "GSM_FgEoR_", None, "GSM -1.12%"),
        ("GSM_FgEoR_1e0pp", "GSM_FgEoR_", None, "GSM +1%"),
        ("GSM_FgEoR_1e1pp", "GSM_FgEoR_", None, "GSM +10%"),
        ("GSM_FgEoR_-1e0pp", "GSM_FgEoR_", "MyPrefix", "MyPrefix -1%"),
        ("GSM_FgEoR_-1e0pp", "MyPrefix_", None, None),
        ("GSM_FgEoR_-1e0", "GSM_FgEoR_", None, None),
        ("GSM_FgEoR_-abcpp", "GSM_FgEoR_", None, None),
    ],
)
def test_pp_key_to_percent_label(key, prefix, label_prefix, expected_result):
    """Test to strip prefix from key to produce labels"""

    label = utils._pp_key_to_percent_label(key, prefix, label_prefix)

    assert label == expected_result


def test_build_pp_groups_from_paths_default():
    """Test with default input - i.e. reads from paths.yaml"""

    prefixes = ["GSM_FgEoR_"]

    expected_output = {
        "GSM -10%": ["GSM_FgEoR_-1e1pp"],
        "GSM -5%": ["GSM_FgEoR_-5e0pp"],
        "GSM -2%": ["GSM_FgEoR_-2e0pp"],
        "GSM -1%": ["GSM_FgEoR_-1e0pp"],
        "GSM -0.1%": ["GSM_FgEoR_-1e-1pp"],
        "GSM -0.01%": ["GSM_FgEoR_-1e-2pp"],
        "GSM -0.001%": ["GSM_FgEoR_-1e-3pp"],
        "GSM +0.001%": ["GSM_FgEoR_+1e-3pp"],
        "GSM +0.01%": ["GSM_FgEoR_+1e-2pp"],
        "GSM +0.1%": ["GSM_FgEoR_+1e-1pp"],
        "GSM +1%": ["GSM_FgEoR_+1e0pp"],
        "GSM +2%": ["GSM_FgEoR_+2e0pp"],
        "GSM +5%": ["GSM_FgEoR_+5e0pp"],
        "GSM +10%": ["GSM_FgEoR_+1e1pp"],
    }

    groups = utils.build_pp_groups_from_paths(prefixes)

    assert groups == expected_output


@pytest.mark.parametrize(
    "prefixes, label_prefixes, expected_result",
    [
        (
            ["Test1_"],
            {"Test1_": "T1", "Test2_": "T2"},
            {
                "T1 -0.001%": ["Test1_-1e-3pp"],
                "T1 -0.01%": ["Test1_-1e-2pp"],
                "T1 -0.1%": ["Test1_-1e-1pp"],
                "T1 -1%": ["Test1_-1e0pp"],
            },
        ),
        (
            ["Test2_"],
            {"Test1_": "T1", "Test2_": "T2"},
            {
                "T2 -2%": ["Test2_-2e0pp"],
                "T2 -5%": ["Test2_-5e0pp"],
                "T2 -10%": ["Test2_-1e1pp"],
            },
        ),
        (
            ["Test2_"],
            {"Dummy": "something"},
            {
                "Test2 -2%": ["Test2_-2e0pp"],
                "Test2 -5%": ["Test2_-5e0pp"],
                "Test2 -10%": ["Test2_-1e1pp"],
            },
        ),
        (
            ["Test2_"],
            None,
            {
                "Test2 -2%": ["Test2_-2e0pp"],
                "Test2 -5%": ["Test2_-5e0pp"],
                "Test2 -10%": ["Test2_-1e1pp"],
            },
        ),
        (["Test3_"], {"Test1_": "T1", "Test2_": "T2"}, {}),
        (["Test4_"], {"Test1_": "T1", "Test2_": "T2"}, {}),
    ],
)
def test_build_pp_groups_from_paths_with_input(
    prefixes, label_prefixes, expected_result
):
    """Test with input yaml file"""

    with tempfile.NamedTemporaryFile(mode="w+t") as yaml_file:
        yaml_file.writelines(
            [
                "Test1_-1e-3pp: test/directory1a/\n",
                "Test1_-1e-2pp: test/directory1b/\n",
                "Test1_-1e-1pp: test/directory1c/\n",
                "Test1_-1e0pp: test/directory1d/\n",
                "Test2_-2e0pp: test/directory2a/\n",
                "Test2_-5e0pp: test/directory2b/\n",
                "Test2_-1e1pp: test/directory2c/\n",
                "Test3_-ee1pp: test/directory3/",
            ]
        )

        yaml_file.seek(0)

        groups = utils.build_pp_groups_from_paths(
            prefixes,
            custom_paths_file=yaml_file.name,
            label_prefixes=label_prefixes,
        )

        yaml_file.close()

        assert groups == expected_result


def test_build_group_labels():
    """Test build group labels"""

    groups = {
        "key1": ["value1"],
        "key2": ["value2a", "value2b"],
        "key3": ["value3"],
    }

    expected_result = {
        "key1": "key1",
        "key2": "key2",
        "key3": "key3",
    }

    labels = utils.build_group_labels(groups)

    assert labels == expected_result
