from pathlib import Path

import lmfit
import matplotlib.axes
import matplotlib.lines
import matplotlib.pyplot as plt
import numpy
import yaml
from matplotlib.ticker import FuncFormatter, MultipleLocator
from pyuvdata import UVData
from scipy.constants import c as speed_of_light
from scipy.special import j1

CORR_SAMPLES = 5
# Compatibility with older pyuvsim config file syntax:
TYPE_TO_CLASS = {
    "gaussian": "GaussianBeam",
    "airy": "AiryBeam",
    "uniform": "UniformBeam",
    "short_dipole": "ShortDipoleBeam",
}


def _airy(
    theta: numpy.typing.NDArray,
    freq_hz: float,
    A: float,
    theta0: float,
    diam: float,
) -> numpy.typing.NDArray:
    """
    Airy power beam for a circular aperture.
    """
    lam = speed_of_light / freq_hz

    x = numpy.pi * diam * numpy.sin(theta - theta0) / lam
    beam = numpy.ones_like(x)
    mask = numpy.abs(x) > 1e-12

    beam[mask] = (2 * j1(x[mask]) / x[mask]) ** 2

    return A * beam


class SimulationConfig:
    def __init__(
        self,
        latitude: float | None = None,
        sigma: float | None = None,
        beam_shape: str | None = None,
        diameter: float | None = None,
    ):

        self.latitude = latitude
        self.sigma = sigma
        self.beam_shape = beam_shape
        self.diameter = diameter


class Loader(yaml.SafeLoader):
    pass


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

    def read_simulation_config(
        self,
        beam_parameters: str,
    ):
        """Read in the simulation config information"""

        # Custom constructor to handle !AnalyticBeam
        def analytic_beam_constructor(loader, node):
            return loader.construct_mapping(node)

        Loader.add_constructor("!AnalyticBeam", analytic_beam_constructor)

        with open(beam_parameters, encoding="utf-8") as file:
            values = yaml.load(file, Loader=Loader)

        lat = float(values["telescope_location"].strip("()").split(",")[0])

        beam_paths = values["beam_paths"][0]

        beam_shape = beam_paths.get("class")
        if beam_shape is None:
            beam_type = beam_paths.get("type")
            if beam_type is None:
                raise ValueError(
                    "beam_paths must contain either 'class' or 'type'"
                )
            beam_shape = TYPE_TO_CLASS[beam_type]

        self.simulation_config = SimulationConfig(
            latitude=lat,
            sigma=beam_paths.get("sigma", None),
            beam_shape=beam_shape,
            diameter=beam_paths.get("diameter", None),
        )

    def check_beam(
        self,
        save_path: str | Path | None = None,
        show: bool = True,
    ):
        """
        Check beam parameters from pyuvsim data and produce
        validation report and plots.
        """

        uvd = UVData.from_file(self.uv_filename)
        self.prepare_uv_data(uvd)
        gauss_result, airy_result, fit_vs_freq = self.compute_beam_metrics()
        self.make_plots(
            gauss_result,
            airy_result,
            fit_vs_freq,
            save_path=save_path,
            show=show,
        )

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
        # print(f"Stokes I shape: {stokes_I.shape}")

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

        print(f"Fitting for {self.simulation_config.beam_shape}")
        f_mid_idx = self.freq_array.shape[0] // 2
        mid_freq = self.freq_array[f_mid_idx]

        # Beam width at every frequency
        fit_vs_freq, gauss_result, airy_result = fit_beam_width_vs_frequency(
            self.freq_array,
            self.theta_deg,
            numpy.abs(self.v_auto),
            self.simulation_config.beam_shape,
        )
        if self.simulation_config.beam_shape == "GaussianBeam":
            print(
                f"   Gaussian at {mid_freq / 1e6:0.1f} MHz: "
                f"FWHM = {fit_vs_freq[f_mid_idx]:0.3f} deg; "
                f"sigma = {fit_vs_freq[f_mid_idx] / (2 * numpy.sqrt(2 * numpy.log(2))):0.3f} deg"
            )

            if self.simulation_config.sigma is not None:
                fwhm_power_expected = (
                    2 * numpy.sqrt(numpy.log(2)) * self.simulation_config.sigma
                )
                print(
                    f"   Expected Gauss FWHM = {numpy.rad2deg(fwhm_power_expected):0.3f} "
                    f"deg; sigma = {numpy.rad2deg(self.simulation_config.sigma / numpy.sqrt(2)):0.3f} deg"
                )
        if self.simulation_config.beam_shape == "Airy":
            print(
                f"   Airy at {mid_freq / 1e6:0.1f} MHz: "
                f"Diameter = {fit_vs_freq[f_mid_idx]:0.3f} m"
            )
            if self.simulation_config.diameter is not None:
                print(
                    f"   Expected diameter = {self.simulation_config.diameter} m"
                )

        spread = numpy.nanstd(fit_vs_freq)
        print(f"   Fit-parameter scatter over frequency: {spread:.4f}")

        # Chromaticity
        chromaticity_test(self.freq_array, fit_vs_freq)

        return gauss_result, airy_result, fit_vs_freq

    def make_plots(
        self,
        gauss_result,
        airy_result,
        fit_vs_freq,
        save_path: str | Path | None = None,
        show: bool = True,
    ):
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

        if gauss_result is not None:
            y_label = "FWHM (deg)"
            plot_title = "Beam width vs frequency"
            plot_text = f"FWHM at {mid_freq / 1e6:0.1f} MHz: {fit_vs_freq[f_mid_idx]:0.2f} deg"
        if airy_result is not None:
            y_label = "Telescope diameter (m)"
            plot_title = "Diameter vs frequency"
            plot_text = f"Diameter at {mid_freq / 1e6:0.1f} MHz: {fit_vs_freq[f_mid_idx]:0.2f} m"

        plot_spectrum(
            ax[1, 0],
            self.freq_array / 1e6,
            fit_vs_freq,
            y_label,
            plot_title,
        )

        ax[1, 0].text(
            0.4,
            0.8,
            plot_text,
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
        if save_path is not None:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=200, bbox_inches="tight")
        if show:
            plt.show()

        return fig


def fit_beam_width_vs_frequency(
    freq: numpy.typing.NDArray,
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
    freq :
        Frequency in Hz
    theta_deg :
        Angular coordinate in degrees.
    v_auto :
        Visibility data with shape (angle, frequency).
    shape :
        Either "GaussianBeam" or "AiryBeam".

    Returns
    -------
    fit_vs_freq :
        Gaussian FWHM values at each frequency.
    gauss_result :
        Gaussian result at middle frequency.
    airy_result :
        Airy result at middle frequency.
    """

    n_f = freq.shape[0]
    f_mid_idx = n_f // 2

    fit_vs_freq = numpy.full(n_f, numpy.nan)
    chi2_gauss_vs_freq = numpy.full(n_f, numpy.nan)
    chi2_airy_vs_freq = numpy.full(n_f, numpy.nan)

    gauss_result_mid = None
    airy_result_mid = None

    # lmfit models
    gaussian_model = lmfit.models.GaussianModel(prefix="g_")
    airy_model = lmfit.Model(_airy, independent_vars=["theta", "freq_hz"])

    for freq_idx in range(n_f):
        # Gaussian fit
        if shape == "GaussianBeam":
            try:
                # Restrict fit to main lobe
                mask = numpy.abs(v_auto[:, freq_idx]) > 0.2
                theta_fit = theta_deg[mask]
                data_fit = numpy.abs(v_auto[:, freq_idx][mask])
                if len(theta_fit) == 0:
                    continue

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

                fit_vs_freq[freq_idx] = result.params["g_fwhm"].value
                chi2_gauss_vs_freq[freq_idx] = result.redchi

                if freq_idx == f_mid_idx:
                    gauss_result_mid = result

            except Exception as e:
                print(f"Gaussian fit failed at freq {freq_idx}: {e}")

        # Airy fit
        elif shape == "AiryBeam":
            try:
                params = airy_model.make_params(
                    A=1.0,
                    theta0=0.0,
                    diam=12.0,
                )
                params["A"].set(min=0.9, max=1.1)
                params["theta0"].set(
                    min=numpy.radians(-1), max=numpy.radians(1)
                )
                params["diam"].set(min=1, max=25)

                result = airy_model.fit(
                    v_auto[:, freq_idx],
                    params,
                    theta=numpy.radians(theta_deg),
                    freq_hz=freq[freq_idx],
                )

                fit_vs_freq[freq_idx] = result.params["diam"].value
                chi2_airy_vs_freq[freq_idx] = result.redchi

                if freq_idx == f_mid_idx:
                    airy_result_mid = result

            except Exception as e:
                print(f"Airy fit failed at freq {freq_idx}: {e}")

        else:
            raise ValueError(
                "shape must be either 'GaussianBeam' or 'AiryBeam'"
            )

    # Summary statistics
    if shape == "GaussianBeam" and numpy.any(~numpy.isnan(chi2_gauss_vs_freq)):
        print(
            f"   mean Gaussian χ²: "
            f"{numpy.nanmean(chi2_gauss_vs_freq):.3g} "
            f"({numpy.nanstd(chi2_gauss_vs_freq):.3g})"
        )
    elif shape == "AiryBeam" and numpy.any(~numpy.isnan(chi2_airy_vs_freq)):
        print(
            f"   mean Airy χ²: "
            f"{numpy.nanmean(chi2_airy_vs_freq):.3g} "
            f"({numpy.nanstd(chi2_airy_vs_freq):.3g})"
        )

    return fit_vs_freq, gauss_result_mid, airy_result_mid


def chromaticity_test(
    freq_array: numpy.typing.NDArray, test_param: numpy.typing.NDArray
) -> float:
    """
    Test the variation of a parameter with frequency.

    Parameters
    ----------
    freq_array :
        Frequency array.
    test_param :
        The parameter to test against frequency.
    """
    inv_freq = 1.0 / freq_array
    valid = ~numpy.isnan(test_param)

    print("\nVariation with frequency:\n")

    # Correlation to frequency
    if numpy.sum(valid) > CORR_SAMPLES and not numpy.isclose(
        numpy.std(test_param[valid]), 0.0
    ):
        # Measure variation across frequency
        freq_std = numpy.std(test_param[valid]) / numpy.mean(test_param[valid])
        p = numpy.polyfit(
            freq_array[valid], numpy.abs(test_param[valid]), deg=2
        )
        freq_grad = p[1] / numpy.mean(test_param[valid])
        trend = numpy.polyval(p, freq_array[valid])
        residual = test_param[valid] - trend
        frac_resid = numpy.std(residual) / numpy.mean(test_param[valid])

        print(
            f"   Std deviation = {100 * freq_std:.3f}%\n"
            f"   Gradient of fitted line = {100 * freq_grad:.3f}%\n"
            f"   Residual chromaticity = {100 * frac_resid:.3f}%"
        )
        corr = numpy.corrcoef(test_param[valid], inv_freq[valid])[0, 1]
    else:
        print("  Not enough valid test parameters")
        corr = numpy.nan

    print(f"   Correlation with 1/frequency: {corr:.3f}")

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

    Parameters
    ----------
    ax :
        The axes on which to plot the data.
    theta_deg :
        The angle array.
    ydata :
        The data to plot.
    gauss_result :
        Result from the Gaussian fit.
    airy_result :
        Result from the Airy fit.
    """
    x_fine = numpy.linspace(theta_deg.min(), theta_deg.max(), 200)

    lines = ax.plot(theta_deg, ydata, "xk", label="Beam data")

    if gauss_result is not None:
        gauss_fit = gauss_result.eval(x=x_fine)
        ax.plot(x_fine, gauss_fit, "-", label="Gaussian fit")

    if airy_result is not None:
        airy_fit = airy_result.eval(theta=numpy.radians(x_fine), freq_hz=freq)
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
