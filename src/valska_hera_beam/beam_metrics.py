import matplotlib.axes
import matplotlib.pyplot as plt
import numpy
from matplotlib.ticker import FuncFormatter, MultipleLocator
from pyuvdata import UVData
from scipy.optimize import curve_fit

CORR_SAMPLES = 5


def airy(
    x: numpy.typing.NDArray, A: float, x0: float, w: float
) -> numpy.typing.NDArray:
    """Airy model function with amplitude, centre and width"""
    r = (x - x0) / w
    return A * (numpy.sinc(r)) ** 2


def gauss(
    x: numpy.typing.NDArray, H: float, A: float, x0: float, sigma: float
) -> numpy.typing.NDArray:
    """
    Gaussian model function with baseline, amplitude, centre and sigma
    """
    return H + A * numpy.exp(-((x - x0) ** 2) / (2 * sigma**2))


def reduced_chi2(
    y: numpy.typing.NDArray, yfit: numpy.typing.NDArray, num_params: int
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
    chi_squared = numpy.mean((y - yfit) ** 2)

    # Calculate degrees of freedom (N - p)
    degrees_of_freedom = len(y) - num_params

    # Compute and return reduced chi-squared
    return (
        chi_squared / degrees_of_freedom
        if degrees_of_freedom > 0
        else numpy.nan
    )


def beam_width_vs_frequency(
    theta_deg: numpy.typing.NDArray, v_norm: numpy.typing.NDArray
) -> tuple[
    numpy.typing.NDArray,
    numpy.typing.NDArray | None,
    numpy.typing.NDArray | None,
]:
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
        # limit fit to main lobe
        mask = v_norm[:, freq_idx] > 0.2
        theta_fit = theta_deg[mask]
        data_fit = numpy.abs(v_norm[:, freq_idx][mask])

        # Gaussian fit
        try:
            peak = numpy.nanmax(data_fit)
            p0 = [peak, 0.0, 0.0, 3.0]
            params_gauss, _ = curve_fit(gauss, theta_fit, data_fit, p0=p0)
            sigma = abs(params_gauss[3])
            gauss_fwhm_vs_freq[freq_idx] = 2.35482 * sigma  # in degrees
            y_gauss = gauss(theta_deg, *params_gauss)
            chi2_gauss_vs_freq[freq_idx] = reduced_chi2(
                v_norm[:, freq_idx], y_gauss, num_params=4
            )
        except Exception as e:
            gauss_fwhm_vs_freq[freq_idx] = numpy.nan
            chi2_gauss_vs_freq[freq_idx] = numpy.nan
            params_gauss = None
            print(f"Gauss fit failed at freq {freq_idx}: {e}")

        # Airy fit
        try:
            params_airy, _ = curve_fit(
                airy,
                theta_fit,
                data_fit,
                p0=[1.0, 0.0, 5],
                bounds=([0, -1, 0], [2, 1, 50]),
            )
            y_airy = airy(theta_deg, *params_airy)
            chi2_airy_vs_freq[freq_idx] = reduced_chi2(
                v_norm[:, freq_idx], y_airy, num_params=3
            )
        except Exception as e:
            chi2_airy_vs_freq[freq_idx] = numpy.nan
            params_airy = None
            print(f"Airy fit failed at freq {freq_idx}: {e}")

        if freq_idx == f_mid_idx:
            params_gauss_mid = params_gauss
            params_airy_mid = params_airy

    print("Fitted Gaussian and Airy:")
    print(
        f"   mean Gaussian χ²: {numpy.mean(chi2_gauss_vs_freq):.3f} "
        f"({numpy.std(chi2_gauss_vs_freq):.3f})"
    )
    print(
        f"   mean Airy χ²: {numpy.mean(chi2_airy_vs_freq):.3f} "
        f"({numpy.std(chi2_airy_vs_freq):.3f})"
    )

    return gauss_fwhm_vs_freq, params_gauss_mid, params_airy_mid


def chromaticity_test(
    freq_array: numpy.typing.NDArray, test_param: numpy.typing.NDArray
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
        f"   Std deviation = {100 * freq_std:.3f}%\n"
        f"   Gradient of fitted line = {100 * freq_grad}%\n"
        f"   Residual chromaticity = {100 * frac_resid}%"
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
    theta_deg: numpy.typing.NDArray,
    ydata: numpy.typing.NDArray,
    freq: float,
    params_gauss: numpy.typing.NDArray | None = None,
    params_airy: numpy.typing.NDArray | None = None,
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

    ax.plot(theta_deg, ydata, "xk", label="Beam data")

    if params_gauss is not None:
        gauss_fit = gauss(x_fine, *params_gauss)
        ax.plot(x_fine, gauss_fit, "-", label="Gaussian fit")
    if params_airy is not None:
        airy_fit = airy(x_fine, *params_airy)
        ax.plot(x_fine, airy_fit, "--", label="Airy fit")

    ax.set_xlabel("Angle (deg)")
    ax.set_ylabel("Response")
    ax.set_title(f"Autocorrelation beam profile ({freq / 1e6} MHz)")

    ax.legend()


def plot_spectrum(
    ax: matplotlib.axes.Axes,
    freq_array: numpy.typing.NDArray,
    parameter: numpy.typing.NDArray,
    ylabel: str,
    title: str,
):
    """Plot spectrum"""

    ax.plot(freq_array, parameter, "o")
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    # --- find closest data point
    idx = freq_array.shape[-1] // 2
    mid_y = parameter[idx]

    # --- draw horizontal line
    ax.axhline(mid_y, color="red", linestyle="--", linewidth=1)
    ax.axvline(freq_array[idx], color="red", linestyle="--", linewidth=1)


def check_beam(uvd: UVData, latitude: float, exp_sigma_rad: float) -> None:
    """
    Check beam parameters from pyuvsim data and produce
    validation report and plots.
    """

    print("\n=== BEAM VALIDATION REPORT ===")

    # Select autocorrelations only
    uv_auto = uvd.select(ant_str="auto", inplace=False)
    # Reorder so time is the fastest grouping
    # (i.e [t0 bl0,t0 bl1,t0 bl2....] )
    uv_auto.reorder_blts(order="time")

    # --- Find time and baseline structure
    unique_times, bl_counts = numpy.unique(
        uv_auto.time_array, return_counts=True
    )

    lsts_per_time = numpy.zeros(bl_counts.size)
    start = 0
    for i, c in enumerate(bl_counts):
        lsts_per_time[i] = uv_auto.lst_array[start]
        start += c

    lsts_unwrapped = numpy.unwrap(lsts_per_time, period=2 * numpy.pi)
    lsts_hours = lsts_unwrapped * 12.0 / numpy.pi

    # --- Reshape directly: (n_times, n_bls, n_freq, n_pol)
    if not numpy.all(bl_counts == bl_counts[0]):
        raise ValueError(
            "Baselines per time are not constant — cannot reshape safely."
        )

    n_times = unique_times.size
    # Assumes that number of baselines per time is constant
    n_bls = bl_counts[0]
    n_freq = uv_auto.freq_array.shape[-1]

    data = uv_auto.data_array.reshape(n_times, n_bls, n_freq, -1)

    # --- Extract XX and YY polarisations
    data_xx = data[..., 0]
    data_yy = data[..., 1]

    # --- Stokes I
    stokes_I = 0.5 * (data_xx + data_yy)

    # Average over baselines (axis=1)
    v_auto = numpy.nanmean(stokes_I, axis=1)  # shape: (Ntimes, Nfreq)
    # Convert power to field and normalize
    v_field = numpy.sqrt(numpy.abs(v_auto))
    v_norm = v_field / numpy.nanmax(v_field, axis=0)

    # Mid-frequency baseline amplitudes
    f_mid_idx = n_freq // 2
    mid_freq = uv_auto.freq_array[f_mid_idx]
    V_time_bl = numpy.abs(stokes_I[:, :, f_mid_idx])  # (Ntimes, Nbls_per_time)

    lat = numpy.deg2rad(latitude)

    # Hour angle calculated from LST relative to mean LST
    hour_angle = numpy.deg2rad((lsts_hours - numpy.mean(lsts_hours)) * 15.0)

    # Convert to real angle on the sky
    cos_theta = numpy.sin(lat) ** 2 + numpy.cos(lat) ** 2 * numpy.cos(
        hour_angle
    )

    theta_deg = numpy.rad2deg(numpy.arccos(cos_theta))
    # Get the sign correct so that it measures angle around mean LST
    theta_deg = numpy.sign(hour_angle) * theta_deg

    # zenith indices
    zenith_idx = len(unique_times) // 2

    # Heatmap of Amplitude at angle vs Baseline Index
    fig, ax = plt.subplots(2, 2, figsize=(10, 7))

    plot_baseline_heatmap(
        numpy.abs(V_time_bl),
        bl_counts,
        lsts_hours,
        theta_deg,
        mid_freq,
        ax=ax[0, 0],
    )

    beam = "UNKNOWN"
    if numpy.std(v_norm[:, f_mid_idx]) == 0:
        beam = "UNIFORM"
        print(f"   {beam} beam found!")
        plot_beam_shape(ax[0, 1], theta_deg, v_norm[:, f_mid_idx], mid_freq)

        # Chromaticity
        chromaticity_test(uv_auto.freq_array, v_norm[zenith_idx, :])

        plot_spectrum(
            ax[1, 0],
            uv_auto.freq_array / 1e6,
            v_norm[zenith_idx, :].real,
            "Amplitude",
            "Amplitude spectrum at zenith",
        )

    else:
        beam = "NON-UNIFORM"
        print(f"   {beam} beam found - will check beam FWHM!")

        # Beam width at every frequency
        gauss_fwhm_vs_freq, p_gauss, p_airy = beam_width_vs_frequency(
            theta_deg, v_norm
        )
        print(
            f"Gaussian at {mid_freq / 1e6} MHz "
            f"FWHM = {gauss_fwhm_vs_freq[f_mid_idx]:.3f} deg; "
            f"sigma = {gauss_fwhm_vs_freq[f_mid_idx] / 2.35482}"
        )
        print(
            f"Expected Gauss FWHM = {numpy.rad2deg(exp_sigma_rad * 2.35482)}"
            f" deg; sigma = {numpy.rad2deg(exp_sigma_rad)}"
        )

        spread = numpy.nanstd(gauss_fwhm_vs_freq)
        print(f"Fitted Gaussian width stability: {spread:.4f}")

        # Chromaticity
        chromaticity_test(uv_auto.freq_array, gauss_fwhm_vs_freq)

        plot_beam_shape(
            ax[0, 1],
            theta_deg,
            v_norm[:, f_mid_idx],
            mid_freq,
            p_gauss,
            p_airy,
        )

        plot_spectrum(
            ax[1, 0],
            uv_auto.freq_array / 1e6,
            gauss_fwhm_vs_freq,
            "FWHM (deg)",
            "Beam width vs frequency",
        )

    plot_waterfall_matplotlib(
        v_auto, uv_auto.freq_array, lsts_hours, theta_deg, ax=ax[1, 1]
    )

    plt.tight_layout()
    plt.show()


def lst_formatter(x, pos):
    return f"{x % 24:.0f}"


def plot_waterfall_matplotlib(
    data,
    freqs,
    lsts_hours,
    theta_deg,
    ax=None,
    cmap="viridis",
):
    """
    Fully explicit waterfall plot with controlled axes.
    No hidden orientation conventions.
    """

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))

    # --- safety checks
    assert data.shape[0] == len(lsts_hours), "LST/time mismatch"
    assert data.shape[1] == len(freqs), "Frequency mismatch"

    # --- physical axis mapping
    extent = [
        freqs.min() / 1e6,  # MHz
        freqs.max() / 1e6,
        lsts_hours.min(),
        lsts_hours.max(),
    ]

    plot_2d_lst_deg(ax, data, extent, lsts_hours, theta_deg, cmap=cmap)

    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("LST (hours)")
    ax.set_title("Waterfall Plot")

    return ax


def plot_baseline_heatmap(
    data,
    bl_counts,
    lsts_hours,
    theta_deg,
    freq,
    ax=None,
    cmap="viridis",
):
    """
    Baseline vs angle heatmap with axes:
    - Left: LST (hours)
    - Right: Angle (deg)
    - External colorbar
    """

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))

    extent = [
        -0.5,
        bl_counts.max() - 0.5,
        lsts_hours.min(),
        lsts_hours.max(),
    ]

    plot_2d_lst_deg(ax, data, extent, lsts_hours, theta_deg, cmap=cmap)

    ax.set_xlabel("Baseline index")
    ax.set_ylabel("LST (hours)")
    ax.set_title(f"Autocorr per baseline at {freq / 1e6} MHz")
    ax.xaxis.set_major_locator(MultipleLocator(1))

    return ax


def plot_2d_lst_deg(ax, data, extent, lsts_hours, theta_deg, cmap="viridis"):

    im = ax.imshow(
        numpy.abs(data),
        origin="lower",
        aspect="auto",
        extent=extent,
        cmap=cmap,
    )

    ax.yaxis.set_major_formatter(FuncFormatter(lst_formatter))
    ax.yaxis.set_major_locator(MultipleLocator(1))

    ax.tick_params(
        axis="y",
        direction="out",
        length=3,
        pad=2,
    )

    # --- secondary axis with linear transform ---
    a, b = numpy.polyfit(lsts_hours, theta_deg, 1)

    secax = ax.secondary_yaxis(
        "right", functions=(lambda x: a * x + b, lambda x: (x - b) / a)
    )

    secax.set_ylabel("Angle (deg)", labelpad=0)
    secax.yaxis.set_major_locator(MultipleLocator(10))

    secax.tick_params(
        axis="y",
        direction="out",
        length=3,
        pad=2,
    )

    plt.colorbar(im, ax=ax, pad=0.16)

    return ax
