from ast import literal_eval
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import astropy.units as units
import numpy
from astropy.coordinates import Angle
from pyradiosky import SkyModel

from valska.catalog import read_skyh5_catalogue
from valska.utils_yaml import load_yaml

Loader = Callable[[Path], Any]
# Compatibility with older pyuvsim config file syntax:
TYPE_TO_CLASS = {
    "gaussian": "GaussianBeam",
    "airy": "AiryBeam",
    "uniform": "UniformBeam",
    "short_dipole": "ShortDipoleBeam",
}


class SimulationConfig:
    config: dict[str, Any]

    tel_cfg_path: Path
    array_layout_path: Path
    catalog_path: Path

    telescope_config: dict[str, Any]
    ref_antenna: int
    catalog: SkyModel

    def __init__(
        self, config_yaml: Path | Mapping, template_dir: Path | None = None
    ):

        if isinstance(config_yaml, Path):
            self.config = load_yaml(config_yaml)
        elif isinstance(config_yaml, Mapping):
            self.config = dict(config_yaml)
        else:
            raise TypeError(
                f"config_yaml must be a Path or mapping, not "
                f"{type(config_yaml).__name__}"
            )

        self._read_config_paths(template_dir)

    def _read_config_paths(self, template_dir: Path | None) -> None:

        required: dict[str, dict[str, tuple[str, str, Loader]]] = {
            "telescope": {
                "telescope_config_name": (
                    "tel_cfg_path",
                    "telescope_config",
                    load_yaml,
                ),
                "array_layout": (
                    "array_layout_path",
                    "ref_antenna",
                    self._find_reference_antenna,
                ),
            },
            "sources": {
                "catalog": ("catalog_path", "catalog", read_skyh5_catalogue),
            },
        }

        missing = []

        # Validate config structure
        for section, keys in required.items():
            cfg_section = self.config.get(section)
            if not isinstance(cfg_section, dict):
                missing.append(section)
                continue

            for key in keys:
                if key not in cfg_section:
                    missing.append(f"{section}.{key}")

        if missing:
            raise ValueError(
                f"Missing required configuration entries: {', '.join(missing)}"
            )

        # Resolve and store paths
        for section, keys in required.items():
            cfg_section = self.config[section]

            for key, (attr, _, _) in keys.items():
                path = Path(cfg_section[key])

                if template_dir is not None and not path.is_absolute():
                    path = template_dir / path

                setattr(self, attr, path)

        # Verify all files exist
        missing_files = []

        for keys in required.values():
            for key, (attr, name, loader) in keys.items():
                path = getattr(self, attr)
                if not path.exists():
                    missing_files.append(f"{key}: '{path}'")
                else:
                    setattr(self, name, loader(path))

        if missing_files:
            raise FileNotFoundError(
                "The following required configuration files do not exist:\n"
                + "\n".join(f"  - {msg}" for msg in missing_files)
            )

    def _find_reference_antenna(self, path: Path, atol: float = 1e-9) -> int:
        """Return antenna number at the array reference position."""

        rows = []

        with path.open() as file:
            next(file)  # skip header

            for line in file:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue

                parts = line.split()

                # Name Number BeamID E N U
                number = int(parts[1])
                east = float(parts[3])
                north = float(parts[4])
                up = float(parts[5])

                rows.append((number, east, north, up))

        rows_array = numpy.asarray(rows)

        mask = (
            numpy.isclose(rows_array[:, 1], 0.0, atol=atol)
            & numpy.isclose(rows_array[:, 2], 0.0, atol=atol)
            & numpy.isclose(rows_array[:, 3], 0.0, atol=atol)
        )

        refs = rows_array[mask, 0].astype(int)

        if len(refs) != 1:
            raise ValueError(
                f"Expected exactly one reference antenna, found {len(refs)}"
            )

        return int(refs[0])

    @property
    def source_ra(self) -> Angle:

        return self.catalog.ra

    @property
    def longitude(self) -> Angle:

        location = self.telescope_config.get("telescope_location")
        if location is None:
            raise ValueError("Telescope config missing 'telescope_location'")
        _, lon, _ = literal_eval(location)

        return Angle(lon, unit="deg")

    @property
    def latitude(self) -> Angle:

        location = self.telescope_config.get("telescope_location")
        if location is None:
            raise ValueError("Telescope config missing 'telescope_location'")
        lat, _, _ = literal_eval(location)

        return Angle(lat, unit="deg")

    @property
    def height(self) -> Angle:

        location = self.telescope_config.get("telescope_location")
        if location is None:
            raise ValueError("Telescope config missing 'telescope_location'")
        _, _, height = literal_eval(location)

        return height * units.m

    @property
    def beam_shape(self) -> str:

        beam_paths = self.telescope_config["beam_paths"][0]

        beam_shape = beam_paths.get("class")
        if beam_shape is None:
            beam_type = beam_paths.get("type")
            if beam_type is None:
                raise ValueError(
                    "beam_paths must contain either 'class' or 'type'"
                )
            beam_shape = TYPE_TO_CLASS[beam_type]

        return beam_shape

    @property
    def beam_sigma(self) -> Angle | None:

        sigma = self.telescope_config["beam_paths"][0].get("sigma", None)

        if sigma is None:
            return None

        return Angle(sigma, unit="rad")

    @property
    def diameter(self) -> units.Quantity | None:

        diameter = self.telescope_config["beam_paths"][0].get("diameter", None)

        if diameter is None:
            return None

        return diameter * units.m
