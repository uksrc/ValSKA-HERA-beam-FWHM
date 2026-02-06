"""Utility functions for the ValSKA-HERA-beam-FWHM package."""

import inspect

# import os
from pathlib import Path
from typing import Dict, Optional, Union

import yaml


class PathManager:
    """Manages paths for the ValSKA-HERA-beam-FWHM package."""

    def __init__(
        self,
        base_dir: Optional[Union[str, Path]] = None,
        chains_dir: Optional[Union[str, Path]] = None,
        data_dir: Optional[Union[str, Path]] = None,
        results_dir: Optional[Union[str, Path]] = None,
    ):
        """Initialize the PathManager with configurable directories.

        If directories are not specified, they will be automatically
        determined relative to the package location.

        Parameters
        ----------
        base_dir : str or Path, optional
            Base directory of the project. If None, it's determined
            automatically.
        chains_dir : str or Path, optional
            Directory containing chain files. If None, defaults to
            {base_dir}/chains
            or falls back to BayesEoR default location.
        data_dir : str or Path, optional
            Directory containing data files. If None, defaults to
            {base_dir}/data.
        results_dir : str or Path, optional
            Directory for storing results. If None, defaults to
            {base_dir}/results.
        """
        # Get the directory of this file
        self.utils_dir = Path(inspect.getfile(self.__class__)).parent.resolve()

        # Determine package src directory (one level up from utils_dir)
        self.package_dir = self.utils_dir

        # Determine base directory (two levels up from utils_dir)
        if base_dir is None:
            self.base_dir = self.utils_dir.parent.parent.resolve()
        else:
            self.base_dir = Path(base_dir).resolve()

        # Set up chains directory
        if chains_dir is None:
            self.chains_dir = self.base_dir / "chains"
            # Create if it doesn't exist
            self.chains_dir.mkdir(exist_ok=True, parents=True)
        else:
            self.chains_dir = Path(chains_dir).resolve()

        # Set up data directory
        if data_dir is None:
            self.data_dir = self.base_dir / "data"
            # Create if it doesn't exist
            self.data_dir.mkdir(exist_ok=True, parents=True)
        else:
            self.data_dir = Path(data_dir).resolve()

        # Set up results directory
        if results_dir is None:
            self.results_dir = self.base_dir / "results"
            # Create if it doesn't exist
            self.results_dir.mkdir(exist_ok=True, parents=True)
        else:
            self.results_dir = Path(results_dir).resolve()

    def get_paths(self) -> Dict[str, Path]:
        """Get a dictionary of all managed paths.

        Returns
        -------
        dict
            Dictionary mapping path names to Path objects
        """
        return {
            "utils_dir": self.utils_dir,
            "package_dir": self.package_dir,
            "base_dir": self.base_dir,
            "chains_dir": self.chains_dir,
            "data_dir": self.data_dir,
            "results_dir": self.results_dir,
        }

    def get_path(self, name: str) -> Path:
        """Get a specific path by name.

        Parameters
        ----------
        name : str
            Name of the path to retrieve

        Returns
        -------
        Path
            Requested path

        Raises
        ------
        KeyError
            If the requested path name doesn't exist
        """
        paths = self.get_paths()
        if name not in paths:
            valid_keys = list(paths.keys())
            raise KeyError(
                f"Path '{name}' not found. Valid paths are: {valid_keys}"
            )
        return paths[name]

    def create_subdir(self, parent: str, name: str) -> Path:
        """Create and return a subdirectory in one of the managed directories.

        Parameters
        ----------
        parent : str
            Name of the parent directory (one of the managed paths)
        name : str
            Name of the subdirectory to create

        Returns
        -------
        Path
            Path to the created subdirectory

        Raises
        ------
        KeyError
            If the parent directory name is invalid
        """
        parent_dir = self.get_path(parent)
        new_dir = parent_dir / name
        new_dir.mkdir(exist_ok=True, parents=True)
        return new_dir

    def find_file(
        self, pattern: str, path_name: Optional[str] = None
    ) -> list[Path]:
        """Find files matching a pattern in a specified directory.

        Parameters
        ----------
        pattern : str
            Glob pattern to match files
        path_name : str, optional
            Name of the directory to search in. If None, searches in base_dir.

        Returns
        -------
        list of Path
            List of paths to files matching the pattern
        """
        if path_name is None:
            search_dir = self.base_dir
        else:
            search_dir = self.get_path(path_name)

        return list(search_dir.glob(pattern))

    def __repr__(self) -> str:
        """Return a string representation of the PathManager.

        Returns
        -------
        str
            String representation showing all managed paths
        """
        paths = self.get_paths()
        path_strs = [f"  {name}: {path}" for name, path in paths.items()]
        return "PathManager:\n" + "\n".join(path_strs)


# Example function that demonstrates how to use the PathManager
def get_default_path_manager() -> PathManager:
    """Get a PathManager instance with default settings.

    Returns
    -------
    PathManager
        A PathManager instance with automatically determined paths
    """
    return PathManager()


# Additional utility functions can be added below
def make_timestamp() -> str:
    """Create a timestamp string for naming files and directories.

    Returns
    -------
    str
        Current timestamp in format YYYY-MM-DD_HHMMSS
    """
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def load_paths(
    custom_paths_file: Optional[Union[str, Path]] = None,
) -> Dict[str, str]:
    """Load analysis paths from a YAML configuration file.

    Parameters
    ----------
    custom_paths_file : str or Path, optional
        Custom paths file to load. If None, loads the default paths file.

    Returns
    -------
    dict
        Dictionary of analysis path keys to paths
    """
    if custom_paths_file is None:
        # Get the directory of this file
        this_dir = Path(__file__).parent.resolve()
        paths_file = this_dir / "config" / "paths.yaml"
    else:
        paths_file = Path(custom_paths_file)

    if not paths_file.exists():
        raise FileNotFoundError(f"Paths file not found: {paths_file}")

    with open(paths_file, "r") as f:
        paths = yaml.safe_load(f)

    return paths


def _pp_key_to_percent_label(
    key: str,
    prefix: str,
    label_prefix: str | None = None,
) -> Optional[str]:
    """Convert '<prefix><pp>' key into a '<label_prefix> ±X%' label.

    Parameters
    ----------
    key : str
        Full analysis key (e.g. ``'GSM_FgEoR_-1e0pp'``, ``'GL_FgEoR_1.0e-01pp'``).
    prefix : str
        The prefix to strip before the numeric part
        (e.g. ``'GSM_FgEoR_'``, ``'GL_FgEoR_'``).
    label_prefix : str, optional
        Text to put in front of the percentage (default: derived from prefix).

    Returns
    -------
    str or None
        Human-readable label (e.g. 'GSM -1%', 'GL +0.1%') or None if
        not matched.
    """
    if not key.startswith(prefix):
        return None

    #  # e.g. '-1e0pp' or '1.0e-01pp'
    middle = key[len(prefix) :]  # noqa: E203
    if not middle.endswith("pp"):
        return None

    mag_str = middle[:-2]
    try:
        mag_float = float(mag_str)
    except ValueError:
        return None

    # In this project the 'pp' part is already percentage points
    percent = 1.0 * mag_float
    label_mag = f"{percent:.3g}%"
    sign = "+" if percent > 0 else ""

    if label_prefix is None:
        # Derive something short from the prefix, e.g. 'GSM' or 'GL'
        # 'GSM_FgEoR_' -> 'GSM', 'GL_FgEoR_' -> 'GL'
        label_prefix = prefix.split("_", 1)[0]

    return f"{label_prefix} {sign}{label_mag}"


def build_pp_groups_from_paths(
    prefixes: list[str],
    custom_paths_file: Optional[Union[str, Path]] = None,
    label_prefixes: Optional[Dict[str, str]] = None,
) -> Dict[str, list[str]]:
    """
    Build groups for perturbation runs from paths.yaml for one or more
    prefixes.

    Examples
    --------
    ``prefixes=['GSM_FgEoR_']`` -> GSM v5d0 EoR+Fg

    ``prefixes=['GL_FgEoR_']`` -> GSM+GLEAM v7d0 EoR+Fg

    ``prefixes=['GSM_FgEoR_', 'GL_FgEoR_']`` -> combined

    ``label_prefixes={'GSM_FgEoR_': 'GSM', 'GL_FgEoR_': 'GL'}``
    -> labels like 'GSM -1%', 'GL -1%' instead of both 'GSM ...'
    """
    paths = load_paths(custom_paths_file)
    raw_groups: Dict[str, list[str]] = {}

    for key in paths.keys():
        for prefix in prefixes:
            if not key.startswith(prefix):
                continue

            lp = None
            if label_prefixes is not None:
                lp = label_prefixes.get(prefix)

            label = _pp_key_to_percent_label(
                key, prefix=prefix, label_prefix=lp
            )
            if label is None:
                continue

            raw_groups.setdefault(label, []).append(key)

    def label_to_val(lbl: str) -> float:
        try:
            return float(lbl.split()[-1].strip("%"))
        except Exception:
            return 0.0

    groups: Dict[str, list[str]] = {}
    for label in sorted(raw_groups.keys(), key=label_to_val):
        groups[label] = sorted(raw_groups[label])

    return groups


def build_group_labels(groups: Dict[str, list[str]]) -> Dict[str, str]:
    """Simple label -> label mapping."""
    return {label: label for label in groups.keys()}


if __name__ == "__main__":
    # Example usage
    path_manager = get_default_path_manager()
    print(path_manager)

    # # Create a timestamped results directory
    # timestamp = make_timestamp()
    # results_subdir = path_manager.create_subdir(
    #    "results_dir", f"run_{timestamp}"
    # )
    # print(f"\nCreated results directory: {results_subdir}")
