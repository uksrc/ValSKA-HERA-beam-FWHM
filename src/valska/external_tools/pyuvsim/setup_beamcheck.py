# Setup for beam checking

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import astropy.units as units
import numpy
from astropy.coordinates import AltAz, Angle, EarthLocation, SkyCoord
from astropy.time import Time
from ruamel.yaml.comments import CommentedSeq

from valska.catalog import write_skyh5_catalogue
from valska.simulation_config import SimulationConfig

# -----------------------------------------------------------------------------
# Beam check config
# -----------------------------------------------------------------------------


def _adjust_time_array(
    cfg: dict,
    time_array: numpy.typing.NDArray,
    time_step_seconds: float | None = None,
    hours_each_side: float = 2.0,
) -> tuple[numpy.typing.NDArray, dict]:
    """
    Adjust the observation span to be ``hours_each_side`` either side
    of the observation midpoint.

    From pyuvsim: The entries in the time_array indicate the center
    of each time step in Julian date.
    """

    # Default to 10 second steps
    if time_step_seconds is None:
        time_step_seconds = 10.0

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

    return new_times, cfg


def _update_baselines(cfg: dict, ref_antenna: int):
    """Set autocorrelation baseline for reference antenna"""

    # Set up list of all autocorrelation baselines
    baselines = [[ref_antenna, ref_antenna]]

    select_cfg = cfg.get("select")
    if not isinstance(select_cfg, dict):
        raise ValueError(
            "Setting up baselines: Config contains no 'select' section."
        )

    if "bls" not in select_cfg:
        raise NotImplementedError(
            "Beam-check requires an explicit select.bls "
            "section to set autocorrelation baselines."
        )
    select_cfg["bls"] = CommentedSeq(baselines)
    # Ensure time array will be written in flow style
    select_cfg["bls"].fa.set_flow_style()


def _lst_at_time(jd: float, longitude: Angle) -> float:
    """Get LST at a time in Julian Days"""
    t = Time(jd, format="jd", scale="utc")
    return float(
        t.sidereal_time("apparent", longitude=longitude).to(units.deg).value
        % 360.0
    )


def get_config_times(cfg: dict) -> numpy.typing.NDArray:
    """Get times from the config dictionary"""

    # Are there any other options for specifying time that need to
    # be covered?

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


def get_ra_dec_at_mid_time(
    time_array: numpy.typing.NDArray, longitude: Angle, latitude: Angle
) -> tuple[float, float]:
    """
    Construct RA/Dec such that source will be overhead at
    the mid point of the time array at the telescope
    lon/lat
    This is the simple HA zenith method
    uses geodetic latitude from config file
    (GPS style on Earth ellipsoid)
    """
    t_mid = 0.5 * (time_array[0] + time_array[-1])

    ra = _lst_at_time(t_mid, longitude)
    dec = latitude

    return ra, dec


def zenith_radec(
    time_array: numpy.typing.NDArray,
    longitude: Angle,
    latitude: Angle,
    height: units.Quantity,
) -> tuple[float, float]:
    """
    Full calculation of RA and Dec to place source at
    celestial zenith
    Different to the simple HA method due to
    - geocentric latitude
    - Earth ellipsoid flattening
    - the exact Earth orientation transformation
    """
    location = EarthLocation(
        lat=latitude,
        lon=longitude,
        height=height,
    )

    obstime = Time(time_array, format="jd", scale="utc")

    altaz = SkyCoord(
        alt=90,
        az=0,
        unit="deg",
        frame=AltAz(
            obstime=obstime, location=location, pressure=0 * units.hPa
        ),
    )

    icrs = altaz.icrs

    return icrs.ra.deg[0], icrs.dec.deg[0]


def prepare_beam_check_cfg(
    cfg: dict,
    run_dir: Path,
    template_dir: Path,
    hours_each_side: float | None = None,
    step_seconds: float | None = None,
) -> dict:
    """
    Prepare configuration for beam check simulation

    Generate catalog with single source at zenith
    Optionally modify the observing times.
    """

    new_cfg = deepcopy(cfg)

    # Get the observation times
    time_array = get_config_times(cfg)

    # Load telescope config and catalogue files
    simulation_config = SimulationConfig(cfg, template_dir=template_dir)

    # Set up all autocorrelation baselines
    _update_baselines(new_cfg, simulation_config.ref_antenna)

    # Optional: specify new time array
    if hours_each_side is not None:
        time_array, new_cfg = _adjust_time_array(
            new_cfg,
            time_array,
            hours_each_side=hours_each_side,
            time_step_seconds=step_seconds,
        )

    # Build minimal sky catalogue
    # Set RA/Dec so that source transits zenith at t_mid
    ra, dec = zenith_radec(
        time_array,
        simulation_config.longitude,
        simulation_config.latitude,
        simulation_config.height,
    )

    zenith_sky_path = (
        run_dir
        / "catalog_files"
        / f"zenith_single_source_ra{ra:0.2f}_dec{dec:0.2f}.skyh5"
    )
    zenith_sky_path.parent.mkdir(parents=True, exist_ok=True)

    write_skyh5_catalogue(
        filename=zenith_sky_path,
        ra_deg=[ra],
        dec_deg=[dec],
        stokes_I=[1.0],
    )

    # Point config at new catalogue
    new_cfg["sources"]["catalog"] = str(zenith_sky_path)

    # Update output filename
    step_seconds = (time_array[1] - time_array[0]) * 86400
    lst_start_hours = (
        _lst_at_time(time_array[0], simulation_config.longitude) / 15.0
    )
    lst_end_hours = (
        _lst_at_time(time_array[-1], simulation_config.longitude) / 15.0
    )
    new_cfg["filing"]["outfile_name"] = (
        f"beamcheck_zenith_single_source_ra{ra:0.2f}_dec{dec:0.2f}"
        f"_lst{lst_start_hours:0.1f}h_{lst_end_hours:0.1f}h_step{step_seconds:0.1f}s"
    )

    return new_cfg
