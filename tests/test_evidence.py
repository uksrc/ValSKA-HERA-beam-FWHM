# Unit tests for evidence

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest

from valska_hera_beam.evidence import (
    interpret_bayes_factor,
)


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

    assert interpret_bayes_factor(log_bf) == result
