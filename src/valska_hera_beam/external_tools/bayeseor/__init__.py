"""
BayesEoR integration helpers.

Primary entry points:
- prepare_bayeseor_run: render a BayesEoR config + SLURM submit script into a ValSKA results dir.
- submit_bayeseor_run: submit a prepared BayesEoR run directory to SLURM.
- get_template_path: access shipped validation templates.
"""

from .constants import TOOL_NAME
from .runner import BayesEoRInstall, CondaRunner, ContainerRunner
from .setup import prepare_bayeseor_run
from .submit import SubmissionError, submit_bayeseor_run
from .templates import get_template_path, list_templates

__all__ = [
    "prepare_bayeseor_run",
    "submit_bayeseor_run",
    "SubmissionError",
    "get_template_path",
    "list_templates",
    "BayesEoRInstall",
    "CondaRunner",
    "ContainerRunner",
    "TOOL_NAME",
]
