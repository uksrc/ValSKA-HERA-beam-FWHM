import lmfit
import matplotlib.axes
import matplotlib.lines
import matplotlib.pyplot as plt
import numpy
from matplotlib.ticker import FuncFormatter, MultipleLocator
from pyuvdata import UVData

CORR_SAMPLES = 5


def airy(
    x: numpy.typing.NDArray, A: float, x0: float, w: float
) -> numpy.typing.NDArray:
    """Airy-like sinc² beam model."""
    r = (x - x0) / w
    return A * (numpy.sinc(r)) ** 2


class SimulationConfig:
    def __init__(
        self,
        latitude: float | None = None,
        sigma: float | None = None,
        beam_shape: str | None = None,
    ):

        self.latitude = latitude
        self.sigma = sigma
        self.beam_shape = beam_shape


class BeamMetrics:
    def __init__(self, filename: str):

        self.uv_filename = filename

        self.simulation_config = SimulationConfig()

        # derived quantities
        self.baseline_counts = numpy.array([])
        self.lsts_hours = numpy.array([])
        self.theta_deg = numpy.array([])
        self.freq_array = numpy.array([])
        self.v_auto = numpy.array([])
        self.v_time_bl = numpy.array([])

        # self.prepare_uv_data()

    def read_simulation_config(
        self, latitude: float, sigma: float, beam_shape: str
    ):
        """Read in the simulation config information"""

        self.simulation_config = SimulationConfig(
            latitude,
            sigma,
            beam_shape,
        )

    def check_beam(self):
        """
        Check beam parameters from pyuvsim data and produce
        validation report and plots.
        """

        uvd = UVData.from_file(self.uv_filename)
        self.prepare_uv_data(uvd)
        gauss_result, airy_result, gauss_fwhm_vs_freq = (
            self.compute_beam_metrics()
        )
        self.make_plots(gauss_result, airy_result, gauss_fwhm_vs_freq)

    def prepare_uv_data(self, uvd: UVData):
        """Resize and prepare UV data"""

        # Select autocorrelations only
        uv_auto = uvd.select(ant_str="auto", inplace=False)
        # Reorder so time is the fastest grouping
        # (i.e [t0 bl0,t0 bl1,t0 bl2....] )
        uv_auto.reorder_blts(order="time")

        # --- Find time and baseline structure
        unique_times, counts = numpy.unique(
            uv_auto.time_array, return_counts=True
        )

        self.baseline_counts = counts

        # Get LST for each time
        lsts_per_time = numpy.zeros(counts.size)
        start = 0
        for i, count in enumerate(counts):
            lsts_per_time[i] = uv_auto.lst_array[start]
            start += count

        lsts_unwrapped = numpy.unwrap(lsts_per_time, period=2 * numpy.pi)
        self.lsts_hours = lsts_unwrapped * 12.0 / numpy.pi

        # Check that number of baselines is constant with time
        if not numpy.all(counts == counts[0]):
            raise ValueError(
                "Baselines per time are not constant — cannot reshape safely."
            )

        # --- Reshape directly: (n_times, n_bls, n_freq, n_pol)
        self.freq_array = numpy.squeeze(uv_auto.freq_array)

        n_times = unique_times.size
        n_bls = counts[0]
        n_freq = self.freq_array.shape[0]

        data = uv_auto.data_array.reshape(n_times, n_bls, n_freq, -1)

        # --- Extract XX and YY polarisations
        data_xx = data[..., 0]
        data_yy = data[..., 1]

        # --- Stokes I (pyuvsim convention)
        stokes_I = data_xx + data_yy
        print(f"Stokes I shape: {stokes_I.shape}")
        print(f"UVData pol convention: {uvd.pol_convention}")

        # Average over baselines (axis=1) to get power
        self.v_auto = numpy.nanmean(stokes_I, axis=1)  # shape: (Ntimes, Nfreq)

        # Mid-frequency baseline amplitudes
        f_mid_idx = n_freq // 2
        self.v_time_bl = numpy.abs(
            stokes_I[:, :, f_mid_idx]
        )  # (Ntimes, Nbls_per_time)

        # Hour angle calculated from LST relative to mean LST
        hour_angle = numpy.deg2rad(
            (self.lsts_hours - numpy.mean(self.lsts_hours)) * 15.0
        )

        # Convert to real angle on the sky
        if self.simulation_config.latitude is None:
            raise ValueError("Please add the simulation config information.")
        else:
            lat = numpy.deg2rad(self.simulation_config.latitude)
            cos_theta = numpy.sin(lat) ** 2 + numpy.cos(lat) ** 2 * numpy.cos(
                hour_angle
            )

            # Get the sign correct so that it measures angle around mean LST
            self.theta_deg = numpy.sign(hour_angle) * numpy.rad2deg(
                numpy.arccos(cos_theta)
            )

    def compute_beam_metrics(self):
        """Compute beam metrics"""

        print(f"Fitting for {self.simulation_config.beam_shape} beam")
        f_mid_idx = self.freq_array.shape[0] // 2
        mid_freq = self.freq_array[f_mid_idx]

        # Beam width at every frequency
        gauss_fwhm_vs_freq, gauss_result, airy_result = (
            fit_beam_width_vs_frequency(
                self.theta_deg,
                numpy.abs(self.v_auto),
                self.simulation_config.beam_shape,
            )
        )
        print(
            f"   Gaussian at {mid_freq / 1e6} MHz: "
            f"FWHM = {gauss_fwhm_vs_freq[f_mid_idx]:0.3f} deg; "
            f"sigma = {gauss_fwhm_vs_freq[f_mid_idx] / (2 * numpy.sqrt(2 * numpy.log(2))):0.3f} deg"
        )

        if self.simulation_config.sigma is not None:
            fwhm_power_expected = (
                2 * numpy.sqrt(numpy.log(2)) * self.simulation_config.sigma
            )
            print(
                f"   Expected Gauss FWHM = {numpy.rad2deg(fwhm_power_expected):0.3f} "
                f"deg; sigma = {numpy.rad2deg(self.simulation_config.sigma):0.3f} deg"
            )

        spread = numpy.nanstd(gauss_fwhm_vs_freq)
        print(f"   Fitted Gaussian width stability: {spread:.4f}")

        # Chromaticity
        chromaticity_test(self.freq_array, gauss_fwhm_vs_freq)

        return gauss_result, airy_result, gauss_fwhm_vs_freq

    def make_plots(self, gauss_result, airy_result, gauss_fwhm_vs_freq):
        """Create diagnostic plots"""

        f_mid_idx = self.freq_array.shape[0] // 2
        mid_freq = self.freq_array[f_mid_idx]

        # Plot figure
        fig, ax = plt.subplots(2, 2, figsize=(10, 7))
        fig.suptitle(
            f"Simulation check: {numpy.abs(self.v_auto.max()):0.1f} "
            "Jy point source transiting zenith",
            fontsize=16,
        )

        # Heatmap of Amplitude at angle vs Baseline Index
        plot_baseline_heatmap(
            ax[0, 0],
            numpy.abs(self.v_time_bl),
            self.baseline_counts,
            self.lsts_hours,
            self.theta_deg,
            mid_freq,
        )

        plot_beam_shape(
            ax[0, 1],
            self.theta_deg,
            numpy.abs(self.v_auto[:, f_mid_idx]),
            mid_freq,
            gauss_result,
            airy_result,
        )

        plot_spectrum(
            ax[1, 0],
            self.freq_array / 1e6,
            gauss_fwhm_vs_freq,
            "FWHM (deg)",
            "Beam width vs frequency",
        )

        ax[1, 0].text(
            0.4,
            0.8,
            f"FWHM at {mid_freq / 1e6} MHz: {gauss_fwhm_vs_freq[f_mid_idx]:0.2f} deg",
            transform=ax[1, 0].transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
        )

        plot_waterfall_matplotlib(
            ax[1, 1],
            self.v_auto,
            self.freq_array,
            self.lsts_hours,
            self.theta_deg,
        )

        plt.tight_layout()
        plt.show()


def fit_beam_width_vs_frequency(
    theta_deg: numpy.typing.NDArray,
    v_auto: numpy.typing.NDArray,
    shape: str,
) -> tuple[
    numpy.typing.NDArray,
    lmfit.model.ModelResult | None,
    lmfit.model.ModelResult | None,
]:
    """
    Fit beam shape vs frequency using lmfit.

    Parameters
    ----------
    theta_deg
        Angular coordinate in degrees.
    v_auto
        Visibility data with shape (angle, frequency).
    shape
        Either "Gaussian" or "Airy".

    Returns
    -------
    gauss_fwhm_vs_freq
        Gaussian FWHM values at each frequency.
    gauss_result
        Gaussian result at middle frequency.
    airy_result
        Airy result at middle frequency.
    """

    n_f = v_auto.shape[1]
    f_mid_idx = n_f // 2

    gauss_fwhm_vs_freq = numpy.full(n_f, numpy.nan)
    chi2_gauss_vs_freq = numpy.full(n_f, numpy.nan)
    chi2_airy_vs_freq = numpy.full(n_f, numpy.nan)

    gauss_result_mid = None
    airy_result_mid = None

    # lmfit models
    gaussian_model = lmfit.models.GaussianModel(prefix="g_")
    airy_model = lmfit.Model(airy)

    for freq_idx in range(n_f):
        # Restrict fit to main lobe
        mask = numpy.abs(v_auto[:, freq_idx]) > 0.2
        theta_fit = theta_deg[mask]
        data_fit = numpy.abs(v_auto[:, freq_idx][mask])

        if len(theta_fit) == 0:
            continue

        # Gaussian fit
        if shape == "Gaussian":
            try:
                peak = numpy.nanmax(data_fit)
                params = gaussian_model.make_params(
                    g_amplitude=peak,
                    g_center=0.0,
                    g_sigma=3.0,
                )
                params["g_sigma"].min = 0

                result = gaussian_model.fit(
                    data_fit,
                    params,
                    x=theta_fit,
                )

                gauss_fwhm_vs_freq[freq_idx] = result.params["g_fwhm"].value
                chi2_gauss_vs_freq[freq_idx] = result.redchi

                if freq_idx == f_mid_idx:
                    gauss_result_mid = result

            except Exception as e:
                print(f"Gaussian fit failed at freq {freq_idx}: {e}")

        # Airy fit
        elif shape == "Airy":
            try:
                params = airy_model.make_params(
                    A=1.0,
                    x0=0.0,
                    w=5.0,
                )
                params["A"].set(min=0, max=2)
                params["x0"].set(min=-1, max=1)
                params["w"].set(min=0, max=50)

                result = airy_model.fit(
                    data_fit,
                    params,
                    x=theta_fit,
                )

                chi2_airy_vs_freq[freq_idx] = result.redchi

                if freq_idx == f_mid_idx:
                    gauss_result_mid = result

            except Exception as e:
                print(f"Airy fit failed at freq {freq_idx}: {e}")

        else:
            raise ValueError("shape must be either 'Gaussian' or 'Airy'")

    # Summary statistics
    if shape == "Gaussian":
        print(
            f"   mean Gaussian χ²: "
            f"{numpy.nanmean(chi2_gauss_vs_freq):.3g} "
            f"({numpy.nanstd(chi2_gauss_vs_freq):.3g})"
        )
    elif shape == "Airy":
        print(
            f"   mean Airy χ²: "
            f"{numpy.nanmean(chi2_airy_vs_freq):.3g} "
            f"({numpy.nanstd(chi2_airy_vs_freq):.3g})"
        )

    return gauss_fwhm_vs_freq, gauss_result_mid, airy_result_mid


def chromaticity_test(
    freq_array: numpy.typing.NDArray, test_param: numpy.typing.NDArray
) -> float:
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

    print(f"  Correlation with 1/frequency: {corr:.3f}")

    return corr


def plot_beam_shape(
    ax: matplotlib.axes.Axes,
    theta_deg: numpy.typing.NDArray,
    ydata: numpy.typing.NDArray,
    freq: float,
    gauss_result: lmfit.model.ModelResult | None = None,
    airy_result: lmfit.model.ModelResult | None = None,
) -> list[matplotlib.lines.Line2D]:
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
    gauss_result : lmfit.model.ModelResult , optional
        Result from the Gaussian fit.
    airy_result : lmfit.model.ModelResult , optional
        Result from the Airy fit.
    """
    x_fine = numpy.linspace(theta_deg.min(), theta_deg.max(), 200)

    lines = ax.plot(theta_deg, ydata, "xk", label="Beam data")

    if gauss_result is not None:
        gauss_fit = gauss_result.eval(x=x_fine)
        ax.plot(x_fine, gauss_fit, "-", label="Gaussian fit")
    if airy_result is not None:
        airy_fit = airy_result.eval(x=x_fine)
        ax.plot(x_fine, airy_fit, "--", label="Airy fit")

    ax.set_xlabel("Angle (deg)")
    ax.set_ylabel("Stokes I (XX+YY) Amplitude (Jy)")
    ax.set_title(f"Autocorrelation beam profile ({freq / 1e6} MHz)")

    ax.legend()

    return lines


def plot_spectrum(
    ax: matplotlib.axes.Axes,
    freq_array: numpy.typing.NDArray,
    parameter: numpy.typing.NDArray,
    ylabel: str,
    title: str,
) -> list[matplotlib.lines.Line2D]:
    """Plot spectrum"""

    lines = ax.plot(freq_array, parameter, "o")
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    # --- find closest data point
    idx = freq_array.shape[-1] // 2
    mid_y = parameter[idx]

    # --- draw horizontal line
    ax.axhline(mid_y, color="red", linestyle="--", linewidth=1)
    ax.axvline(freq_array[idx], color="red", linestyle="--", linewidth=1)

    return lines


def lst_formatter(x: float, pos: int) -> str:
    """Format LST in hours, wrapped to [0, 24)."""
    return f"{x % 24:.0f}"


def plot_waterfall_matplotlib(
    ax: matplotlib.axes.Axes,
    data: numpy.typing.NDArray[numpy.floating | numpy.complexfloating],
    freqs: numpy.typing.NDArray[numpy.floating],
    lsts_hours: numpy.typing.NDArray[numpy.floating],
    theta_deg: numpy.typing.NDArray[numpy.floating],
    cmap: str = "viridis",
) -> matplotlib.axes.Axes:
    """
    Create a waterfall plot (frequency vs LST).
    """

    # --- safety checks
    if data.shape[0] != len(lsts_hours):
        raise ValueError("Mismatch between data time axis and lsts_hours")
    if data.shape[1] != len(freqs):
        raise ValueError("Mismatch between data frequency axis and freqs")

    # --- physical axis mapping
    extent = (
        freqs.min() / 1e6,  # MHz
        freqs.max() / 1e6,
        lsts_hours.min(),
        lsts_hours.max(),
    )

    plot_2d_lst_deg(ax, data, extent, lsts_hours, theta_deg, cmap=cmap)

    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("LST (hours)")
    ax.set_title("Waterfall Plot")

    return ax


def plot_baseline_heatmap(
    ax: matplotlib.axes.Axes,
    data: numpy.typing.NDArray[numpy.floating | numpy.complexfloating],
    bl_counts: numpy.typing.NDArray[numpy.integer],
    lsts_hours: numpy.typing.NDArray[numpy.floating],
    theta_deg: numpy.typing.NDArray[numpy.floating],
    freq: float,
    cmap: str = "viridis",
) -> matplotlib.axes.Axes:
    """
    Baseline vs angle heatmap with axes:
    - Left: LST (hours)
    - Right: Angle (deg)
    - External colorbar
    """

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))

    extent = (
        -0.5,
        bl_counts.max() - 0.5,
        lsts_hours.min(),
        lsts_hours.max(),
    )

    plot_2d_lst_deg(ax, data, extent, lsts_hours, theta_deg, cmap=cmap)

    ax.set_xlabel("Baseline index")
    ax.set_ylabel("LST (hours)")
    ax.set_title(f"Autocorr per baseline at {freq / 1e6} MHz")
    ax.xaxis.set_major_locator(MultipleLocator(1))

    return ax


def plot_2d_lst_deg(
    ax: matplotlib.axes.Axes,
    data: numpy.typing.NDArray[numpy.floating | numpy.complexfloating],
    extent: tuple[float, float, float, float],
    lsts_hours: numpy.typing.NDArray[numpy.floating],
    theta_deg: numpy.typing.NDArray[numpy.floating],
    cmap: str = "viridis",
) -> matplotlib.axes.Axes:
    """
    Plot a 2D image with:
    - Left y-axis: LST (hours)
    - Right y-axis: angular separation (degrees)
    """

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

    secax.set_ylabel("Anglular Separation (deg)", labelpad=0)
    secax.yaxis.set_major_locator(MultipleLocator(10))

    secax.tick_params(
        axis="y",
        direction="out",
        length=3,
        pad=2,
    )

    cbar = plt.colorbar(im, ax=ax, pad=0.16)
    vmin, vmax = im.get_clim()
    ticks = [vmin + i * (vmax - vmin) / 5 for i in range(6)]
    cbar.set_ticks(ticks)
    cbar.ax.set_title("Stokes I", fontsize=8)

    return ax
