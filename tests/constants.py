"""
Variables and util functions for testing
"""
import matplotlib.pyplot as plt

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
        self.k_vals = [
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8],
        ]

    def plot_power_spectra_and_posteriors(self, **plot_args):

        
        fig = MockFig(**plot_args)


        return fig
    


class MockFig():

    def __init__(self, **plot_args):
        self.axes = [MockAx()]
        for a in plot_args:
            setattr(self, a, plot_args[a])  


class MockAx():
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
    
class MockLegend():
    def __init__(self):
        # Legend with default labels
        self.legendHandles = [1, 2, 3]
        self._loc = 1
        self._fontsize = 1
        self.texts = [MockText("A"), MockText("B"), MockText("Expected")]
        self.ncol = None

    def get_texts(self):

        return self.texts
    
class MockText():

    def __init__(self, text):
        self.text = text

    def get_text(self):

        return self.text
    
    def set_text(self, text):

        self.text = text
