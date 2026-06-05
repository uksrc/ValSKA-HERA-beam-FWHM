"""Runner abstractions for executing pyuvsim via conda or containers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class pyuvsimInstall:
    install_path: Path | None = None


@dataclass(frozen=True)
class CondaRunner:
    """
    Run pyuvsim via a named conda environment.

    If conda_activate/env_name are both None, no activation lines are emitted.
    """

    conda_activate: str | None
    env_name: str | None

    def bash_prefix(self) -> str:
        """Return shell lines to activate the conda environment."""
        if not self.conda_activate and not self.env_name:
            return ""

        if not self.conda_activate or not self.env_name:
            raise ValueError(
                "conda_activate and env_name must both be set, or both be None"
            )

        return f"{self.conda_activate}\nconda activate {self.env_name}\n"


@dataclass(frozen=True)
class ContainerRunner:
    """
    Future: Run pyuvsim inside a container (Apptainer/Singularity).

    This is included now so we don’t need to redesign the API later.
    The only thing that should change is how we construct the command line;
    config rendering and output directory conventions stay identical.

    Example future command:
      apptainer exec --bind <binds> <image.sif> python -m pyuvsim.uvsim <obsparam.yaml>
    """

    apptainer_exe: str  # "apptainer" or "singularity"
    image_path: Path
    bind_paths: tuple[Path, ...] = ()
