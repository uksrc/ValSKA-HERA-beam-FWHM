"""
BayesEoR integration helpers.

Primary entry points:
- prepare_bayeseor_run: render a BayesEoR config + SLURM submit script into a ValSKA results dir.
- get_template_path: access shipped validation templates.
"""

from .runner import BayesEoRInstall, CondaRunner, ContainerRunner
from .setup import prepare_bayeseor_run
from .templates import get_template_path, list_templates

__all__ = [
    "prepare_bayeseor_run",
    "get_template_path",
    "list_templates",
    "BayesEoRInstall",
    "CondaRunner",
    "ContainerRunner",
]
