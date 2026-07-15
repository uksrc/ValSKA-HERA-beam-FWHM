# Catalogue utilities

from pathlib import Path

import astropy.units as units
import numpy
from astropy.coordinates import SkyCoord
from pyradiosky import SkyModel


def write_skyh5(
    *,
    filename,
    ra_deg,
    dec_deg,
    stokes_I,
    source_names=None,
    spectral_index=None,
    reference_frequency=150e6,
):
    """
    Write a SkyH5 catalogue.

    Parameters
    ----------
    filename : str
        Output .skyh5 filename.

    ra_deg, dec_deg : array_like
        Right Ascension and Declination in degrees.

    stokes_I : array_like
        Stokes I flux densities in Jy at the reference frequency.

    source_names : array_like of str, optional
        Names of the sources. If None, names are generated.

    spectral_index : array_like, optional
        Spectral indices. If None, assumes flat spectrum.

    reference_frequency : float
        Reference frequency in Hz.
    """

    ra_deg = numpy.asarray(ra_deg)
    dec_deg = numpy.asarray(dec_deg)
    stokes_I = numpy.asarray(stokes_I)

    nsrc = len(ra_deg)

    if not (len(dec_deg) == nsrc and len(stokes_I) == nsrc):
        raise ValueError(
            "ra_deg, dec_deg, and stokes_I must have the same length"
        )

    nsrc = len(ra_deg)

    if source_names is None:
        source_names = numpy.array([f"src_{i:06d}" for i in range(nsrc)])

    if spectral_index is None:
        spectral_index = numpy.zeros(nsrc)

    spectral_index = numpy.asarray(spectral_index)

    if spectral_index.shape != (nsrc,):
        raise ValueError("spectral_index must have one value per source")

    # One reference frequency per source
    reference_frequency = numpy.full(nsrc, reference_frequency) * units.Hz

    # Sky coordinates
    skycoord = SkyCoord(
        ra=ra_deg,
        dec=dec_deg,
        frame="icrs",
        unit="deg",
    )

    # Stokes array shape must be (4, Nfreqs, Ncomponents)
    stokes = numpy.zeros((4, 1, nsrc))
    stokes[0, 0, :] = stokes_I

    sm = SkyModel(
        name=source_names,
        skycoord=skycoord,
        stokes=stokes * units.Jy,
        spectral_type="spectral_index",
        reference_frequency=reference_frequency,
        spectral_index=numpy.asarray(spectral_index),
    )

    sm.check()
    sm.write_skyh5(filename, clobber=True)


def read_skyh5_catalogue(filename: str | Path) -> SkyModel:
    """
    Read a SkyH5 catalogue into a SkyModel.

    Parameters
    ----------
    filename
        Path to the .skyh5 catalogue.

    Returns
    -------
    SkyModel
        The loaded sky model.
    """
    sky = SkyModel()
    sky.read_skyh5(filename)
    return sky
