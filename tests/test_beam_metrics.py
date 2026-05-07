"""Unit tests for beam metrics"""

from unittest.mock import MagicMock

import numpy
import pytest

from valska_hera_beam import beam_metrics

from .constants import make_airy_data, make_gaussian_data


def test_beam_width_gaussian_fit_recovers_fwhm():
    """
    Test beam_width_vs_frequency to verify gaussian returns FWHM
    """

    theta = numpy.linspace(-10, 10, 200)
    sigma = 2.0

    y = make_gaussian_data(theta, sigma=sigma)

    # shape: (angle, frequency)
    v_auto = y[:, numpy.newaxis]

    fwhm, params_gauss, params_airy = beam_metrics.beam_width_vs_frequency(
        theta_deg=theta,
        v_auto=v_auto,
        shape="Gaussian",
    )

    expected_fwhm = 2 * numpy.sqrt(2 * numpy.log(2)) * sigma

    assert numpy.isclose(
        fwhm[0],
        expected_fwhm,
        rtol=0.05,
    )

    assert params_gauss is not None
    assert params_airy is None


def test_beam_width_gaussian_fit_multiple_frequencies():
    """Test beam_width_vs_frequency with multiple freqs"""

    theta = numpy.linspace(-10, 10, 200)
    sigmas = [1.0, 2.0, 3.0]

    data = numpy.column_stack(
        [make_gaussian_data(theta, sigma=s) for s in sigmas]
    )

    fwhm, _, _ = beam_metrics.beam_width_vs_frequency(
        theta_deg=theta,
        v_auto=data,
        shape="Gaussian",
    )

    expected = [2 * numpy.sqrt(2 * numpy.log(2)) * s for s in sigmas]

    assert numpy.allclose(fwhm, expected, rtol=0.05)


def test_beam_width_airy_fit_returns_parameters():
    """Test beam_width_vs_frequency with Airy"""

    theta = numpy.linspace(-20, 20, 500)

    y = make_airy_data(theta, width=4.0)

    v_auto = y[:, numpy.newaxis]

    fwhm, params_gauss, params_airy = beam_metrics.beam_width_vs_frequency(
        theta_deg=theta,
        v_auto=v_auto,
        shape="Airy",
    )

    # Airy branch should not populate Gaussian params
    assert params_gauss is None

    # Airy fit should succeed
    assert params_airy is not None

    # Width should be approximately recovered
    assert numpy.isclose(
        params_airy["w"],
        4.0,
        rtol=0.1,
    )


def test_beam_width_invalid_shape_raises_value_error():
    """Test beam_width_vs_frequency error handling"""

    theta = numpy.linspace(-10, 10, 100)
    v_auto = numpy.ones((100, 1))

    with pytest.raises(ValueError):
        beam_metrics.beam_width_vs_frequency(
            theta_deg=theta,
            v_auto=v_auto,
            shape="NotARealShape",
        )


def test_beam_width_empty_mask_returns_nan():
    """Test beam_width_vs_frequency returns nan"""

    theta = numpy.linspace(-10, 10, 100)

    # Everything below mask threshold (0.2)
    v_auto = numpy.zeros((100, 1))

    fwhm, _, _ = beam_metrics.beam_width_vs_frequency(
        theta_deg=theta,
        v_auto=v_auto,
        shape="Gaussian",
    )

    assert numpy.isnan(fwhm[0])


def test_beam_width_gaussian_fit_with_noise():
    """Test beam_width_vs_frequency Gaussian with noise"""

    rng = numpy.random.default_rng(12345)

    theta = numpy.linspace(-10, 10, 300)

    sigma = 2.5

    clean = make_gaussian_data(theta, sigma=sigma)

    noisy = clean + rng.normal(0, 0.02, size=theta.size)

    v_auto = noisy[:, numpy.newaxis]

    fwhm, _, _ = beam_metrics.beam_width_vs_frequency(
        theta_deg=theta,
        v_auto=v_auto,
        shape="Gaussian",
    )

    expected = 2 * numpy.sqrt(2 * numpy.log(2)) * sigma

    assert numpy.isclose(
        fwhm[0],
        expected,
        rtol=0.1,
    )


def test_chromaticity_returns_expected_correlation(capsys):
    """
    Test that the function returns the expected correlation
    for a simple monotonic relationship.
    """
    freq = numpy.array([1, 2, 3, 4, 5], dtype=float)
    param = numpy.array([5, 4, 3, 2, 1], dtype=float)

    corr = beam_metrics.chromaticity_test(freq, param)

    expected = numpy.corrcoef(param, 1.0 / freq)[0, 1]

    assert numpy.isclose(corr, expected)

    captured = capsys.readouterr()
    assert "Variation with frequency" in captured.out
    assert "Correlation with 1/frequency" in captured.out


def test_chromaticity_ignores_nan_values():
    """
    Test that NaN values are excluded from the correlation calculation.
    """
    freq = numpy.array([1, 2, 3, 4, 5], dtype=float)
    param = numpy.array([5, numpy.nan, 3, numpy.nan, 1], dtype=float)

    corr = beam_metrics.chromaticity_test(freq, param)

    valid = ~numpy.isnan(param)
    expected = numpy.corrcoef(param[valid], (1.0 / freq)[valid])[0, 1]

    assert numpy.isclose(corr, expected, equal_nan=True)


def test_chromaticity_returns_nan_when_not_enough_samples():
    """
    If the number of valid samples is <= CORR_SAMPLES,
    the function should return NaN.
    """
    freq = numpy.array([1, 2], dtype=float)
    param = numpy.array([1, 2], dtype=float)

    corr = beam_metrics.chromaticity_test(freq, param)

    assert numpy.isnan(corr)


def test_chromaticity_all_nan_input():
    """
    Test behavior when all parameter values are NaN.
    """
    freq = numpy.array([1, 2, 3], dtype=float)
    param = numpy.array([numpy.nan, numpy.nan, numpy.nan])

    corr = beam_metrics.chromaticity_test(freq, param)

    assert numpy.isnan(corr)


def test_chromaticity_constant_parameter():
    """
    Constant parameter arrays produce undefined correlation.
    """
    freq = numpy.array([1, 2, 3, 4, 5], dtype=float)
    param = numpy.ones(5)

    corr = beam_metrics.chromaticity_test(freq, param)

    assert numpy.isnan(corr)


def test_plot_beam_shape_basic():
    ax = MagicMock()

    theta = numpy.array([0, 1, 2])
    y = numpy.array([1, 2, 3])
    freq = 1e6

    beam_metrics.plot_beam_shape(ax, theta, y, freq)

    # Beam data plotted
    ax.plot.assert_called()
    ax.set_xlabel.assert_called_with("Angle (deg)")
    ax.set_ylabel.assert_called_with("Stokes I (XX+YY) Amplitude (Jy)")
    ax.set_title.assert_called_with("Autocorrelation beam profile (1.0 MHz)")
    ax.legend.assert_called_once()


def test_plot_beam_shape_with_fits():
    ax = MagicMock()

    theta = numpy.array([0, 1, 2])
    y = numpy.array([1, 2, 3])
    freq = 2e6

    gauss_result = MagicMock()
    airy_result = MagicMock()

    gauss_result.eval.return_value = numpy.array([0.1, 0.2, 0.3])
    airy_result.eval.return_value = numpy.array([0.2, 0.3, 0.4])

    beam_metrics.plot_beam_shape(ax, theta, y, freq, gauss_result, airy_result)

    # Ensure eval was called
    gauss_result.eval.assert_called()
    airy_result.eval.assert_called()

    # Check that fits were plotted
    assert ax.plot.call_count >= 3  # data + two fits


def test_plot_spectrum_basic():
    ax = MagicMock()

    freq = numpy.array([1, 2, 3, 4, 5])
    param = numpy.array([10, 20, 30, 40, 50])

    beam_metrics.plot_spectrum(ax, freq, param, "Power", "Test Spectrum")

    ax.plot.assert_called_with(freq, param, "o")
    ax.set_xlabel.assert_called_with("Frequency (MHz)")
    ax.set_ylabel.assert_called_with("Power")
    ax.set_title.assert_called_with("Test Spectrum")

    # Check midpoint marker lines
    mid_idx = len(freq) // 2
    mid_x = freq[mid_idx]
    mid_y = param[mid_idx]

    ax.axhline.assert_called_with(
        mid_y, color="red", linestyle="--", linewidth=1
    )
    ax.axvline.assert_called_with(
        mid_x, color="red", linestyle="--", linewidth=1
    )


def test_plot_spectrum_midpoint_is_correct():
    ax = MagicMock()

    freq = numpy.array([10, 20, 30, 40])
    param = numpy.array([1, 2, 3, 4])

    beam_metrics.plot_spectrum(ax, freq, param, "Y", "T")

    mid_idx = len(freq) // 2  # 2
    assert ax.axhline.call_args[0][0] == param[mid_idx]
    assert ax.axvline.call_args[0][0] == freq[mid_idx]
