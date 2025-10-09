# Unit tests for utils

import tempfile
from datetime import datetime

from valska_hera_beam.utils import load_paths, make_timestamp


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
