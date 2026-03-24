import numpy
import matplotlib.pyplot as plt
import matplotlib.axes
from scipy.optimize import curve_fit
from typing import Tuple

TIME_PRECISION = 1e-12
CORR_SAMPLES = 5

def airy(x: numpy.ndarray, A: float, x0: float, w: float) -> numpy.ndarray:
    """
    Airy model function.

    Parameters:
    A : float
        Amplitude of the Airy function.
    x0 : float
        Center of the Airy function.
    w : float
        Width parameter of the Airy function.
    
    Returns:
    numpy.ndarray
        The calculated Airy function values at the given x.
    """
    r = (x - x0) / w
    return A * (numpy.sinc(r))**2


def gauss(
        x: numpy.ndarray, 
        H: float, 
        A: float, 
        x0: float, 
        sigma: float
    ) -> numpy.ndarray:
    """
    Gaussian model function.

    Parameters:
    H : float
        Baseline offset.
    A : float
        Amplitude of the Gaussian.
    x0 : float
        Center of the Gaussian.
    sigma : float
        Standard deviation (width) of the Gaussian.
    
    Returns:
    numpy.ndarray
        The calculated Gaussian function values at the given x.
    """
    return H + A * numpy.exp(-(x - x0) ** 2 / (2 * sigma ** 2))


def reduced_chi2(
        y: numpy.ndarray, yfit: numpy.ndarray, num_params: int
    ) -> float:
    """
    Calculate the reduced Chi squared statistic (χ²_red).

    Parameters:
    y : numpy.ndarray
        The observed data points.
    yfit : numpy.ndarray
        The fitted data points.
    num_params : int
        The number of parameters in the model being fitted.

    Returns:
    float
        The reduced chi-squared statistic.
    """
    # Compute regular chi-squared
    chi_squared = numpy.mean((y - yfit)**2)

    # Calculate degrees of freedom (N - p)
    degrees_of_freedom = len(y) - num_params

    # Compute and return reduced chi-squared
    return chi_squared / degrees_of_freedom if degrees_of_freedom > 0 else numpy.nan


def beam_width_vs_frequency(
        theta_deg: numpy.ndarray, 
        v_norm: numpy.ndarray
    ) -> Tuple[numpy.ndarray, numpy.ndarray|None, numpy.ndarray|None]:
    """
    Fit the beam shape with a Gaussian and Airy function at each frequency.

    Parameters:
    theta_deg : numpy.ndarray
        Angles (in degrees) corresponding to the beam shape.
    v_norm : numpy.ndarray
        Normalized visibility data.
    
    Returns:
    Tuple of:
    - numpy.ndarray: FWHM values from the Gaussian fit at each frequency.
    - Optional[numpy.ndarray]: Parameters from the Gaussian fit.
    - Optional[numpy.ndarray]: Parameters from the Airy fit.
    """
    n_f = v_norm.shape[1]
    f_mid_idx = n_f // 2
    gauss_fwhm_vs_freq = numpy.zeros(n_f)
    chi2_gauss_vs_freq = numpy.zeros(n_f)
    chi2_airy_vs_freq = numpy.zeros(n_f)

    params_gauss_mid = None
    params_airy_mid = None

    for freq_idx in range(n_f):
        # Gaussian fit
        try:
            p0 = [1.0, 1.0, 0.0, 5.0]
            params_gauss, _ = curve_fit(
                gauss, theta_deg, v_norm[:, freq_idx], p0=p0
            )
            sigma = abs(params_gauss[2])
            gauss_fwhm_vs_freq[freq_idx] = 2.35482 * sigma  # in degrees
            y_gauss = gauss(theta_deg, *params_gauss)
            chi2_gauss_vs_freq[freq_idx] = reduced_chi2(
                v_norm[:, freq_idx], y_gauss, num_params=4
            )
        except:
            gauss_fwhm_vs_freq[freq_idx] = numpy.nan
            chi2_gauss_vs_freq[freq_idx] = numpy.nan
            params_gauss = None

        # Airy fit
        try:
            params_airy, _ = curve_fit(
                airy, theta_deg, v_norm[:, freq_idx], p0=[1.0, 0.0, 5]
            )
            y_airy = airy(theta_deg, *params_airy)
            chi2_airy_vs_freq[freq_idx] = reduced_chi2(
                v_norm[:, freq_idx], y_airy, num_params=3
            )
        except:
            chi2_airy_vs_freq[freq_idx] = numpy.nan
            params_airy = None

        if freq_idx == f_mid_idx:
            params_gauss_mid = params_gauss
            params_airy_mid = params_airy

    print("Fitted Gaussian and Airy:")
    print(
        f"   mean Gaussian χ²: {numpy.mean(chi2_gauss_vs_freq):.3f} "
        "({numpy.std(chi2_gauss_vs_freq):.3f})"
    )
    print(
        f"   mean Airy χ²: {numpy.mean(chi2_airy_vs_freq):.3f} "
        "({numpy.std(chi2_airy_vs_freq):.3f})"
    )

    return gauss_fwhm_vs_freq, params_gauss_mid, params_airy_mid


def chromaticity_test(
        freq_array: numpy.ndarray, test_param: numpy.ndarray
    ) -> None:
    """
    Test the variation of a parameter with frequency.

    Parameters:
    freq_array : numpy.ndarray
        Frequency array.
    test_param : numpy.ndarray
        The parameter to test against frequency.
    """
    inv_freq = 1.0 / freq_array
    valid = ~numpy.isnan(test_param)

    # Measure variation across frequency
    freq_std = numpy.std(test_param) / numpy.mean(test_param)
    p = numpy.polyfit(freq_array, numpy.abs(test_param), deg=2)
    freq_grad = p[1] / numpy.mean(test_param)
    trend = numpy.polyval(p, freq_array)
    residual = test_param - trend
    frac_resid = numpy.std(residual) / numpy.mean(test_param)

    print(
        "\nVariation with frequency:\n"
        f"   Std deviation = {100*freq_std:.3f}%\n"
        f"   Gradient of fitted line = {100*freq_grad}%\n"
        f"   Residual chromaticity = {100*frac_resid}%"
    )

    # Correlation to frequency
    if numpy.sum(valid) > CORR_SAMPLES:
        corr = numpy.corrcoef(test_param[valid], inv_freq[valid])[0, 1]
    else:
        corr = numpy.nan

    print(f"Correlation with 1/frequency: {corr:.3f}")

    return corr


def plot_beam_shape(
        ax: matplotlib.axes.Axes, 
        theta_deg: numpy.array, 
        ydata: numpy.array, 
        params_gauss: list|None=None, 
        params_airy: list|None=None,
    ) -> None:
    """
    Plot the beam shape (normalized response) along with Gaussian
    and Airy fits.

    Parameters:
    ax : matplotlib.axes.Axes
        The axes on which to plot the data.
    theta_deg : numpy.ndarray
        The angle array.
    ydata : numpy.ndarray
        The data to plot.
    params_gauss : Optional[numpy.ndarray], optional
        Parameters from the Gaussian fit.
    params_airy : Optional[numpy.ndarray], optional
        Parameters from the Airy fit.
    """
    x_fine = numpy.linspace(theta_deg.min(), theta_deg.max(), 200)
    
    ax.plot(theta_deg, ydata, 'xk', label="Beam data")

    if params_gauss is not None:
        gauss_fit = gauss(x_fine, *params_gauss)
        ax.plot(x_fine, gauss_fit, '-', label="Gaussian fit")
    if params_airy is not None:
        airy_fit = airy(x_fine, *params_airy)
        ax.plot(x_fine, airy_fit, '--', label="Airy fit")

    ax.set_xlabel("Angle (deg)")
    ax.set_ylabel("Response")
    ax.set_title("Autocorrelation beam profile (mid frequency)")


def plot_spectrum(
        ax: matplotlib.axes.Axes, 
        freq_array: numpy.array, 
        parameter: numpy.array,
        ylabel: str,
        title: str,
    ):
    """Plot spectrum"""

    ax.plot(freq_array / 1e6, parameter, 'o')
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)


def check_beam(
    data_xx: numpy.ndarray,
    data_yy: numpy.ndarray,
    time_array: numpy.ndarray,
    freq_array: numpy.ndarray,
    ant1_array: numpy.ndarray,
    ant2_array: numpy.ndarray,
) -> None:
    """
    Check beam parameters from pyuvsim data and produce
    validation report and plots.

    Parameters:
    data_xx : numpy.ndarray
        XX polarization visibility data.
    data_yy : numpy.ndarray
        YY polarization visibility data.
    time_array : numpy.ndarray
        Time array.
    freq_array : numpy.ndarray
        Frequency array.
    ant1_array : numpy.ndarray
        Antenna 1 array.
    ant2_array : numpy.ndarray
        Antenna 2 array.
    """

    print("\n=== BEAM VALIDATION REPORT ===")

    unique_times = numpy.unique(time_array)
    # Convert Julian date to seconds
    dt_sec = (unique_times - unique_times[0]) * 86400
    omega_deg_per_sec = 360.0 / 86164.0  # deg/sec
    theta_deg = dt_sec * omega_deg_per_sec
    # Center around zenith
    theta_deg = theta_deg - numpy.mean(theta_deg)

    # Mid frequency and zenith indices
    f_mid_idx = len(freq_array) // 2
    zenith_idx = len(unique_times) // 2

    # Count baselines per time
    bl_counts = numpy.array([
        numpy.sum(numpy.abs(time_array - t) < TIME_PRECISION)
        for t in unique_times
    ])

    # Calculate amplitude at mid frequency for all baselines
    # Allocate matrix (angle x baseline index)
    V_time_bl = numpy.full(
        (unique_times.size, bl_counts.max()), numpy.nan, dtype=float
    )

    # Calculate autocorrelation (Stokes I approx)
    v_auto = numpy.zeros((unique_times.size, freq_array.size))

    for t_idx, tval in enumerate(unique_times):
        # Select all baseline-time indices for this time
        blt_sel = numpy.where(numpy.abs(time_array - tval) < TIME_PRECISION)[0]
        auto_sel = blt_sel[ant1_array[blt_sel] == ant2_array[blt_sel]]
        v_auto[t_idx, :] = numpy.mean(
            0.5 * (data_xx[auto_sel, :] + data_yy[auto_sel, :]), axis=0
        ).real

        # Store averaged XX+YY visibility amplitude
        V_time_bl[t_idx, :blt_sel.size] = 0.5 * (
            data_xx[blt_sel, f_mid_idx] +
            data_yy[blt_sel, f_mid_idx]
        )

    v_norm = v_auto / v_auto.max(axis=0)

    # Heatmap of Amplitude at angle vs Baseline Index
    fig, ax = plt.subplots(2, 2, figsize=(10, 7))

    ax[0, 0].imshow(
        numpy.log10(numpy.abs(V_time_bl) + 1e-6),
        origin="lower",
        aspect="auto",
        extent = [
            -0.5 , bl_counts.max()-0.5, theta_deg.min() , theta_deg.max()
        ],
    )
    ax[0, 0].set_xlabel("Baseline index")
    ax[0, 0].set_ylabel("Angle (deg)")

    beam = "UNKNOWN"
    if numpy.std(v_norm[:, f_mid_idx]) == 0:
        beam = "UNIFORM"
        print(f"   {beam} beam found!")
        plot_beam_shape(ax[0, 1], theta_deg, v_auto[:, f_mid_idx])
        fwhm = None

        # Chromaticity
        corr = chromaticity_test(freq_array, v_auto[zenith_idx, :])

        plot_spectrum(ax[1, 0], freq_array/1e6, v_auto[zenith_idx, :], "Amplitude", "Amplitude spectrum at zenith")

    else:
        beam = "NON-UNIFORM"
        print(f"   {beam} beam found - will check beam FWHM!")

        # Beam width at every frequency
        gauss_fwhm_vs_freq, p_gauss, p_airy = beam_width_vs_frequency(theta_deg, v_auto)
        fwhm = f"{numpy.mean(gauss_fwhm_vs_freq):.3f}"
        print(f"Mean Gaussian FWHM = {fwhm} deg")

        spread = numpy.nanstd(gauss_fwhm_vs_freq)
        print(f"Fitted Gaussian width stability: {spread:.4f}")

        # Chromaticity
        corr = chromaticity_test(freq_array, gauss_fwhm_vs_freq)

        plot_beam_shape(ax[0, 1], theta_deg, v_auto[:, f_mid_idx], p_gauss, p_airy)

        plot_spectrum(ax[1, 0], freq_array/1e6, gauss_fwhm_vs_freq, "FWHM (deg)", "Beam width vs frequency")

    # Add key parameters in the empty space (bottom-right corner)
    ax[1, 1].axis("off")  # Hide the empty plot
    ax[1, 1].text(
        0.5,
        0.5, 
        "Beam Parameters:\n\n"
        f"{beam} Beam\n"
        f"Mean Gaussian FWHM = {fwhm} deg\n"
        f"Correlation with 1/freq = {corr:.3f}", 
        ha='center',
        va='center',
        fontsize=12,
        bbox=dict(facecolor='white', alpha=0.7)
    )

    plt.tight_layout()
    plt.show()

    print("=== END REPORT ===\n")
