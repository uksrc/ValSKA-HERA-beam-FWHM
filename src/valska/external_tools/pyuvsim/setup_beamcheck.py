# Setup for beam checking

from __future__ import annotations

from ast import literal_eval
from copy import deepcopy
from pathlib import Path

import astropy.units as units
import numpy
from astropy.coordinates import EarthLocation
from astropy.time import Time
from ruamel.yaml.comments import CommentedSeq

from valska.catalog import write_skyh5_new
from valska.utils_yaml import load_yaml

# -----------------------------------------------------------------------------
# Beam check config
# -----------------------------------------------------------------------------


def _adjust_time_array(
    cfg: dict, time_array: numpy.typing.NDArray, hours_each_side: float = 2.0
) -> dict:
    """
    Ensure the observation spans at least ``hours_each_side`` either side
    of the observation midpoint while preserving the original cadence.
    """

    step = numpy.median(numpy.diff(time_array))

    start = time_array[0]
    end = time_array[-1]
    midpoint = 0.5 * (start + end)

    required = hours_each_side / 24.0

    before = midpoint - start
    after = end - midpoint

    if before >= required and after >= required:
        return cfg

    new_start = midpoint - max(before, required)
    # Ensure that new_end is >= required by adding one step
    new_end = midpoint + max(after, required) + step

    new_times = numpy.arange(new_start, new_end, step)

    time_cfg = cfg.get("time")
    if not isinstance(time_cfg, dict):
        raise ValueError("Configuration contains no time section.")

    if "time_array" not in time_cfg:
        raise NotImplementedError(
            "Beam-check currently requires an explicit time.time_array."
        )
    time_cfg["time_array"] = CommentedSeq(new_times.tolist())
    # Ensure time array will be written in flow style
    time_cfg["time_array"].fa.set_flow_style()

    return cfg


def _lst_at_time(jd: float, location: EarthLocation) -> float:
    t = Time(jd, format="jd", scale="utc")
    return float(
        t.sidereal_time("apparent", longitude=location.lon).to(units.deg).value
        % 360.0
    )


def _read_config_times(cfg: dict):

    # Include other options for time too!

    time_cfg = cfg.get("time")

    if not isinstance(time_cfg, dict):
        raise ValueError("Configuration contains no time section.")

    if "time_array" not in time_cfg:
        raise NotImplementedError(
            "Beam-check currently requires an explicit time.time_array."
        )

    time_array = numpy.asarray(time_cfg["time_array"], dtype=float)

    if len(time_array) < 2:
        raise ValueError("time_array must contain at least two entries.")

    return time_array


def _read_config_location(cfg: dict, template_dir):

    telescope = cfg.get("telescope")
    if (
        not isinstance(telescope, dict)
        or "telescope_config_name" not in telescope
    ):
        raise ValueError("Config does not contain telescope_config_name")

    tel_cfg_path = Path(telescope["telescope_config_name"])

    if not tel_cfg_path.is_absolute():
        tel_cfg_path = template_dir / tel_cfg_path

    if not tel_cfg_path.exists():
        raise FileNotFoundError(
            f"Telescope config {tel_cfg_path} does not exist. "
            "If using a template, was valska_root supplied?"
        )

    tel_cfg = load_yaml(tel_cfg_path)

    location = tel_cfg.get("telescope_location")
    if location is None:
        raise ValueError("Telescope config missing 'telescope_location'")
    lat, lon, height = literal_eval(location)

    earth_location = EarthLocation(
        lat=lat * units.deg,
        lon=lon * units.deg,
        height=height * units.m,
    )

    return earth_location


def prepare_beam_check_cfg(
    cfg: dict,
    run_dir: Path,
    template_dir: Path,
    min_hours: float = 2.0,
):
    """
    1. Read the telescope latitude,
    2. Generate catalog with single source at zenith,
    3. Point the catalogue path in cfg to that file,
    4. Optionally modify the observing times.
    5. Update output filename
    """

    new_cfg = deepcopy(cfg)

    # 1. Load the observation time and telescope location from config
    time_array = _read_config_times(cfg)
    t_mid = 0.5 * (time_array[0] + time_array[-1])

    earth_location = _read_config_location(cfg, template_dir)

    # 2. Build minimal sky catalogue
    zenith_sky_path = run_dir / "catalog_files" / "zenith_single_source.skyh5"
    zenith_sky_path.parent.mkdir(parents=True, exist_ok=True)

    # Set RA/Dec so that source transits zenith at t_mid
    write_skyh5_new(
        filename=zenith_sky_path,
        ra_deg=[_lst_at_time(t_mid, earth_location)],
        dec_deg=[earth_location.lat.deg],
        stokes_I=[1.0],
    )

    # 3. Point config at new catalogue
    new_cfg["sources"]["catalog"] = str(zenith_sky_path)

    # 4. Optional time extension
    if min_hours is not None:
        new_cfg = _adjust_time_array(
            new_cfg, time_array, hours_each_side=min_hours
        )

    # 5. Update output filename
    new_cfg["filing"]["outfile_name"] += ".beamcheck"

    return new_cfg
