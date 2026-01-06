# Unit tests for evidence

import tempfile
from pathlib import Path

import pytest
from constants import MockChain

from valska_hera_beam import evidence


@pytest.mark.parametrize(
    "log_bf, result",
    [
        (6, "Very strong evidence for model 1"),
        (5, "Strong evidence for model 1"),
        (4, "Strong evidence for model 1"),
        (3, "Moderate evidence for model 1"),
        (2, "Moderate evidence for model 1"),
        (1, "Weak/inconclusive evidence"),
        (0, "Weak/inconclusive evidence"),
        (-1, "Moderate evidence for model 2"),
        (-2, "Moderate evidence for model 2"),
        (-3, "Strong evidence for model 2"),
        (-4, "Strong evidence for model 2"),
        (-5, "Very strong evidence for model 2"),
        (-6, "Very strong evidence for model 2"),
    ],
)
def test_interpret_bayes_factor(log_bf, result):
    """Test interpret_bayes_factor"""

    assert evidence.interpret_bayes_factor(log_bf) == result


def test_calculate_bayes_factor(monkeypatch):
    """Test calculate bayes factor"""

    def mock_read_chains(*args, **kwargs):
        return MockChain(args[0])

    monkeypatch.setattr(evidence, "read_chains", mock_read_chains)

    with tempfile.TemporaryDirectory() as chains_dir:

        with open(f"{chains_dir}/chains_1.txt", "a") as file:
            file.write("20")
        with open(f"{chains_dir}/chains_2.txt", "a") as file:
            file.write("10")

        result = evidence.calculate_bayes_factor(
            Path(f"{chains_dir}/chains_1.txt"),
            Path(f"{chains_dir}/chains_2.txt"),
            "Model 1",
            "Model 2",
        )

        expected_result = {
            "model_1": "Model 1",
            "model_2": "Model 2",
            "log_evidence_1": 20.0,
            "log_evidence_2": 10.0,
            "log_bayes_factor": 10.0,
            "interpretation": "Very strong evidence for model 1",
            "success": True,
            "error": None,
        }

        assert result == expected_result


def test_calculate_bayes_factor_error():
    """Test calculate bayes factor with error"""

    result = evidence.calculate_bayes_factor(
        Path("dummy/chains_1.txt"),
        Path("dummy/chains_2.txt"),
        "Model 1",
        "Model 2",
    )

    assert result["error"].split("Could not find any compatible chains:")[
        0
    ] == (
        "Error calculating Bayes factor:\n"
        "  model_1 path: dummy/chains_1.txt\n"
        "  model_2 path: dummy/chains_2.txt\n"
        "  exception: "
    )
    assert result["success"] is False


def test_find_single_mn_subdir():
    """Test find subdirectories under root"""

    with tempfile.TemporaryDirectory() as root:

        Path(f"{root}/subdir/").mkdir()
        # Should ignore files and only find subdirectories
        Path(f"{root}/dummy.txt").touch()

        subdirs = evidence._find_single_mn_subdir(Path(root))

        assert subdirs == Path(f"{root}/subdir/")


def test_find_single_mn_subdir_multiple_error():
    """Test find subdirectories under root with too many subdirs"""

    with tempfile.TemporaryDirectory() as root:

        Path(f"{root}/subdir/").mkdir()
        Path(f"{root}/subdir2/").mkdir()

        with pytest.raises(RuntimeError) as error:
            evidence._find_single_mn_subdir(Path(root))

            assert error.value == (
                f"Multiple subdirectories under {root}: "
                f"{root}/subdir/ {root}/subdir2/"
            )


def test_find_single_mn_subdir_empty_error():
    """Test find subdirectories under root with no subdirs"""

    with tempfile.TemporaryDirectory() as root:

        with pytest.raises(RuntimeError) as error:
            evidence._find_single_mn_subdir(Path(root))

            assert error.value == f"No subdirectories found under {root}"


def test_normalize_perturbation_key():
    """Test normalise key - function currently does nothing"""

    key = "+1e0pp"
    result = evidence._normalize_perturbation_key(key)

    assert result == key
