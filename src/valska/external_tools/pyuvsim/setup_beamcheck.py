# Setup for beam checking

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import astropy.units as units
import numpy
from astropy.coordinates import Angle
from astropy.time import Time
from ruamel.yaml.comments import CommentedSeq

from valska.catalog import write_skyh5
from valska.simulation_config import SimulationConfig

# -----------------------------------------------------------------------------
# Beam check config
# -----------------------------------------------------------------------------


def _adjust_time_array(
    cfg: dict,
    time_array: numpy.typing.NDArray,
    time_step_seconds: float = 10.0,
    hours_each_side: float = 2.0,
) -> dict:
    """
    Adjust the observation span to be ``hours_each_side`` either side
    of the observation midpoint.
    """

    midpoint = 0.5 * (time_array[0] + time_array[-1])

    required_days = hours_each_side / 24
    step_days = time_step_seconds / 86400

    # Number of steps on each side
    steps_each_side = numpy.ceil(required_days / step_days)

    # Number of steps is odd, and midpoint falls exactly at centre
    time_offsets = (
        numpy.arange(-steps_each_side, steps_each_side + 1) * step_days
    )
    new_times = midpoint + time_offsets

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


def _lst_at_time(jd: float, longitude: Angle) -> float:
    t = Time(jd, format="jd", scale="utc")
    return float(
        t.sidereal_time("apparent", longitude=longitude).to(units.deg).value
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
    simulation_config = SimulationConfig(cfg, template_dir=template_dir)

    time_array = _read_config_times(cfg)
    t_mid = 0.5 * (time_array[0] + time_array[-1])

    # 2. Build minimal sky catalogue
    zenith_sky_path = run_dir / "catalog_files" / "zenith_single_source.skyh5"
    zenith_sky_path.parent.mkdir(parents=True, exist_ok=True)

    # Set RA/Dec so that source transits zenith at t_mid
    write_skyh5(
        filename=zenith_sky_path,
        ra_deg=[_lst_at_time(t_mid, simulation_config.longitude.deg)],
        dec_deg=[simulation_config.latitude.deg],
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
