"""
Variables and util functions for testing
"""

from pathlib import Path

BASE_DIR = Path("/dummy/base/dir/")
CHAINS_DIR = Path("/dummy/chains/dir/")
DATA_DIR = Path("/dummy/data/dir/")
RESULTS_DIR = Path("/dummy/results/dir/")

EOR_PS = 214777.66068216303  # mK^2 Mpc^3
NOISE_RATIO = 0.5


class MockDataContainer():
    """
    Mock class for reading and analyzing files output by BayesEoR.
    """
    def __init__(
        self,
        dirnames,
        dir_prefix=None,
        expected_ps=None,
        labels=None,
        additional_args=None
    ):
        
        self.Ndirs = len(dirnames)
        self.dirnames = dirnames
        self.dir_prefix = dir_prefix
        self.labels = labels
        self.expected_ps = expected_ps
        self.additional_args = additional_args
        