"""
Variables and util functions for testing
"""

import tempfile
from pathlib import Path

# Use an ephemeral, writable temp directory for tests (not checked into VCS)
BASE_DIR = Path(tempfile.mkdtemp(prefix="valska_tests_")).resolve()
CHAINS_DIR = BASE_DIR / "chains"
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"

# Ensure required subdirs exist
for d in (CHAINS_DIR, DATA_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

EOR_PS = 214777.66068216303  # mK^2 Mpc^3
NOISE_RATIO = 0.5


class MockDataContainer:
    """
    Mock class for reading and analyzing files output by BayesEoR.
    """

    def __init__(
        self,
        dirnames,
        dir_prefix=None,
        expected_ps=None,
        labels=None,
        additional_args=None,
    ):
        self.Ndirs = len(dirnames)
        self.dirnames = dirnames
        self.dir_prefix = dir_prefix
        self.labels = labels
        self.expected_ps = expected_ps
        self.additional_args = additional_args
        self.k_vals = [
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8],
        ]

    def plot_power_spectra_and_posteriors(self, **plot_args):
        fig = MockFig(**plot_args)

        return fig


class MockFig:
    """Mock class for plot figure"""

    def __init__(self, **plot_args):
        self.axes = [MockAx()]
        for a in plot_args:
            setattr(self, a, plot_args[a])


class MockAx:
    """Mock class for plot axes"""

    def __init__(self):
        self.leg = MockLegend()

    def get_legend(self):
        return self.leg

    def legend(
        self,
        handles,
        labels,
        loc,
        fontsize,
        ncol,
        frameon,
        framealpha,
    ):
        self.leg.legendHandles = handles
        self.leg.texts = [MockText(label) for label in labels]
        self.leg._loc = loc
        self.leg._fontsize = fontsize
        self.leg.ncol = ncol
        self.leg.frameon = frameon
        self.leg.framealpha = framealpha


class MockLegend:
    """Mock class for plot legend"""

    def __init__(self):
        # Legend with 3 default labels
        self.legendHandles = [1, 2, 3]
        self._loc = 1
        self._fontsize = 1
        self.texts = [MockText("A"), MockText("B"), MockText("Expected")]
        self.ncol = None

    def get_texts(self):
        return self.texts


class MockText:
    """Mock class for legend text"""

    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text


class MockChain:
    """
    Mock class for chain
    (to mock output of anesthetic.read_chains)
    """

    def __init__(self, chain_path):
        self.read_chain(chain_path)

    def read_chain(self, chain_path):
        with open(chain_path) as file:
            self.logZ_value = file.read()

    def logZ(self):
        return self.logZ_value


def mock_read_chains(*args, **kwargs):
    """
    Mock method to replace anesthetic read_chains()
    """
    return MockChain(args[0])
