import astropy.units as u
import numpy
import pytest
from pyradiosky import SkyModel

from valska.catalog import read_skyh5_catalogue, write_skyh5_catalogue


def test_write_skyh5_creates_file(tmp_path):
    outfile = tmp_path / "test.skyh5"

    write_skyh5_catalogue(
        filename=outfile,
        ra_deg=[180.0],
        dec_deg=[-30.0],
        stokes_I=[1.5],
    )

    assert outfile.exists()


def test_write_skyh5_roundtrip(tmp_path):
    outfile = tmp_path / "test.skyh5"

    ra = numpy.array([180.0, 181.5])
    dec = numpy.array([-30.0, -31.2])
    flux = numpy.array([1.5, 2.3])

    write_skyh5_catalogue(
        filename=outfile,
        ra_deg=ra,
        dec_deg=dec,
        stokes_I=flux,
    )

    sm = SkyModel.from_file(outfile)

    numpy.testing.assert_allclose(sm.skycoord.ra.deg, ra)
    numpy.testing.assert_allclose(sm.skycoord.dec.deg, dec)
    numpy.testing.assert_allclose(sm.stokes[0, 0].value, flux)


def test_write_skyh5_source_names(tmp_path):
    outfile = tmp_path / "test.skyh5"

    names = numpy.array(["CasA", "CygA"])

    write_skyh5_catalogue(
        filename=outfile,
        ra_deg=[10.0, 20.0],
        dec_deg=[30.0, 40.0],
        stokes_I=[1.0, 2.0],
        source_names=names,
    )

    sm = SkyModel.from_file(outfile)

    assert numpy.array_equal(sm.name, names)


def test_default_source_names(tmp_path):
    outfile = tmp_path / "test.skyh5"

    write_skyh5_catalogue(
        filename=outfile,
        ra_deg=[10.0, 20.0, 30.0],
        dec_deg=[0.0, 1.0, 2.0],
        stokes_I=[1.0, 2.0, 3.0],
    )

    sm = SkyModel.from_file(outfile)

    expected = numpy.array(["src_000000", "src_000001", "src_000002"])

    assert numpy.array_equal(sm.name, expected)


def test_spectral_indices(tmp_path):
    outfile = tmp_path / "test.skyh5"

    alpha = numpy.array([-0.8, -0.5])

    write_skyh5_catalogue(
        filename=outfile,
        ra_deg=[0.0, 1.0],
        dec_deg=[0.0, 1.0],
        stokes_I=[1.0, 2.0],
        spectral_index=alpha,
    )

    sm = SkyModel.from_file(outfile)

    numpy.testing.assert_allclose(sm.spectral_index, alpha)


def test_reference_frequency(tmp_path):
    outfile = tmp_path / "test.skyh5"

    ref_freq = 200e6

    write_skyh5_catalogue(
        filename=outfile,
        ra_deg=[10.0],
        dec_deg=[20.0],
        stokes_I=[5.0],
        reference_frequency=ref_freq,
    )

    sm = SkyModel.from_file(outfile)

    assert sm.reference_frequency == ref_freq * u.Hz


def test_mismatched_array_lengths(tmp_path):
    outfile = tmp_path / "test.skyh5"

    with pytest.raises(ValueError):
        write_skyh5_catalogue(
            filename=outfile,
            ra_deg=[0.0, 1.0],
            dec_deg=[0.0],
            stokes_I=[1.0, 2.0],
        )


def test_skyh5_ra_dec_roundtrip(tmp_path):
    """RA/Dec should survive a SkyH5 write/read to machine precision."""

    ra = 157.12345678901234
    dec = -26.78901234567890

    filename = tmp_path / "roundtrip.skyh5"

    write_skyh5_catalogue(
        filename=filename,
        ra_deg=[ra],
        dec_deg=[dec],
        stokes_I=[1.0],
    )

    sky = read_skyh5_catalogue(filename)

    ra_read = sky.ra.deg[0]
    dec_read = sky.dec.deg[0]

    print(f"Written RA : {ra:.15f}")
    print(f"Read RA    : {ra_read:.15f}")
    print(f"Written Dec: {dec:.15f}")
    print(f"Read Dec   : {dec_read:.15f}")

    numpy.testing.assert_allclose(ra_read, ra, rtol=0.0, atol=1e-13)
    numpy.testing.assert_allclose(dec_read, dec, rtol=0.0, atol=1e-13)
