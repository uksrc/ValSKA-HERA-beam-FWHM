"""
BayesEoR integration helpers.

Primary entry points:
- prepare_bayeseor_run: render a BayesEoR config + SLURM submit script into a ValSKA results dir.
- submit_bayeseor_run: submit a prepared BayesEoR run directory to SLURM.
- get_template_path: access shipped validation templates.
"""

from ..common.runner import CondaRunner, ContainerRunner, ToolInstall
from .constants import TOOL_NAME
from .report import generate_sweep_report
from .setup import prepare_bayeseor_run
from .submit import submit_bayeseor_run
from .sweep_health import inspect_sweep_health
from .templates import get_template_path, list_templates

__all__ = [
    "prepare_bayeseor_run",
    "submit_bayeseor_run",
    "generate_sweep_report",
    "inspect_sweep_health",
    "get_template_path",
    "list_templates",
    "ToolInstall",
    "CondaRunner",
    "ContainerRunner",
    "TOOL_NAME",
]
