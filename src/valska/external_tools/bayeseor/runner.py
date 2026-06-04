"""Runner abstractions for executing BayesEoR via conda or containers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BayesEoRInstall:
    """
    Where BayesEoR lives and which script to invoke.

    Notes:
    - For now we assume a BayesEoR clone exists (HPC-friendly).
    - Later, if BayesEoR provides a stable module/entrypoint, we can support that too.
    """

    repo_path: Path
    run_script: Path = Path("scripts/run-analysis.py")


@dataclass(frozen=True)
class CondaRunner:
    """
    Run BayesEoR via a named conda environment.

    conda_activate should point to conda.sh (or equivalent) so that `conda activate` works
    inside non-interactive batch shells (SLURM).
    """

    conda_activate: (
        str  # e.g. "source /path/to/miniconda3/etc/profile.d/conda.sh"
    )
    env_name: str  # e.g. "bayeseor"

    def bash_prefix(self) -> str:
        """Return shell lines to activate the conda environment."""
        return f"{self.conda_activate}\nconda activate {self.env_name}\n"


@dataclass(frozen=True)
class ContainerRunner:
    """
    Future: Run BayesEoR inside a container (Apptainer/Singularity).

    This is included now so we don’t need to redesign the API later.
    The only thing that should change is how we construct the command line;
    config rendering and output directory conventions stay identical.

    Example future command:
      apptainer exec --bind <binds> <image.sif> python <run-analysis.py> <config.yaml>
    """

    apptainer_exe: str  # "apptainer" or "singularity"
    image_path: Path
    bind_paths: tuple[Path, ...] = ()
