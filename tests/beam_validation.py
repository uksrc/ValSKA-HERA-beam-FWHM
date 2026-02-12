import numpy
import h5py
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import curve_fit


def gauss(x, H, A, x0, sigma):
    """Gaussian"""
    return H + A * numpy.exp(-(x - x0) ** 2 / (2 * sigma ** 2))


def gauss_fit(x, y):
    """Gaussian fit using scipy curvefit"""
    # Estimate fit params
    mean = sum(x * y) / sum(y)
    sigma = numpy.sqrt(sum(y * (x - mean) ** 2) / sum(y))

    popt, pcov = curve_fit(gauss, x, y, p0=[min(y), max(y), mean, sigma])

    return popt


def check_beam(
    data_pyuv_xx,
    data_pyuv_yy,
    time_array,
    freq_array,
    ant1_array,
    ant2_array
):
    """Check beam parameters from pyuvsim data"""

    unique_times = numpy.unique(time_array)
    n_t = unique_times.size

    v_auto_i = numpy.zeros([n_t, freq_array.size], dtype=complex)

    for t_idx, tval in enumerate(unique_times):
        blt_sel = numpy.where(numpy.abs(time_array - tval) < 1e-12)[0]
        # Is this step needed, or can you always select baseline index 0?
        auto_sel = blt_sel[
            ant1_array[blt_sel] == ant2_array[blt_sel]
        ]

        for f in range(freq_array.size):
            v_auto_i[t_idx, f] = (
                0.5 * (
                    data_pyuv_xx[auto_sel, f] +
                    data_pyuv_yy[auto_sel, f]
                )
            )
    # Look for frequency behaviour 
    # select zenith
    zenith_idx = int(n_t/2) - 1
    v_auto_i_zenith = v_auto_i[zenith_idx,:]
    v_freq_std = numpy.std(v_auto_i_zenith) / numpy.mean(v_auto_i_zenith)
    v_freq_grad = (v_auto_i_zenith.max() - v_auto_i_zenith.min()) / numpy.mean(v_auto_i_zenith)
    print(
        "\nVariation with frequency at Zenith:\n"
        f"   Std deviation = {100*v_freq_std}%\n"
        f"   Gradient = {100*v_freq_grad}%"
    )

    # Look for shape, averaging over frequency, or select reference freq?
    print("Beam Profile shape:")
    f_idx = 15
    if numpy.std(v_auto_i[:, f_idx]) == 0:
        print("   UNIFORM")
    else:
        # Fit Gaussian and report FWHM
        time_idx = numpy.arange(unique_times.size)
        params = gauss_fit(time_idx, v_auto_i[:,f_idx].real)
        fwhm = 2.35482 * params[3]
        print(
            "   GAUSSIAN fitted params:\n"
            f"   > FWHM = {fwhm}"
        )


if __name__ == "__main__":

    # ============================================================
    # SETUP
    # ============================================================

    folder = Path("/Users/edward.polehampton/Downloads/")

    beams = ["uniform", "airy"]
    Nbeams = len(beams)

    # ============================================================
    # FIGURES
    # ============================================================

    fig_time, axes_time = plt.subplots(
        1, 4, figsize=(16, 4),
        constrained_layout=True
    )

    fig_freq, ax_freq = plt.subplots(figsize=(6, 4))

    Vlog_all = []  # store for common color limits (if needed later)

    # ============================================================
    # LOOP OVER BEAMS
    # ============================================================

    for ib, beam in enumerate(beams):

        file1 = folder / (
            "gleam-field-1-pld-mean-2.82-std-0.19-nf-38-nt-34-dt-11s-"
            f"fov-19.4deg-{beam}_beamtest.uvh5"
        )

        # ------------------------------------------------------------
        # LOAD DATA
        # ------------------------------------------------------------

        with h5py.File(file1, "r") as f:
            freq_array = f["/Header/freq_array"][:]
            time_array = f["/Header/time_array"][:]
            pol_array  = f["/Header/polarization_array"][:]
            ant1_array = f["/Header/ant_1_array"][:] + 1
            ant2_array = f["/Header/ant_2_array"][:] + 1

            raw = f["/Data/visdata"][:]

        # polarization indices
        ix_XX = numpy.where(pol_array == -5)[0][0]
        ix_YY = numpy.where(pol_array == -6)[0][0]

        # Is this necessary?
        data_pyuv = raw.real + 1j * raw.imag

        # not necessary
        # MATLAB: permute(data_pyuv,[3,2,1])
        #data_pyuv = numpy.transpose(data_pyuv, (2, 1, 0))

        # ============================================================
        # CHECK BEAM PROPERTIES
        # ============================================================

        check_beam(
            data_pyuv[:, :, ix_XX],
            data_pyuv[:, :, ix_XX],
            time_array,
            freq_array,
            ant1_array,
            ant2_array
        )

        # ============================================================
        # TIME × BASELINE INDEX
        # ============================================================

        i_freq = 15  # MATLAB index 16 ... Python index 15

        unique_times = numpy.unique(time_array)
        Nt = unique_times.size

        # Count baselines per time
        counts = numpy.array([
            numpy.sum(numpy.abs(time_array - t) < 1e-12)
            for t in unique_times
        ])
        Nbl_max = counts.max()

        V_time_bl = numpy.full((Nt, Nbl_max), numpy.nan, dtype=float)

        for t_idx, tval in enumerate(unique_times):
            blt_sel = numpy.where(numpy.abs(time_array - tval) < 1e-12)[0]

            V_time_bl[t_idx, :blt_sel.size] = 0.5 * (
                data_pyuv[blt_sel, i_freq, ix_XX] +
                data_pyuv[blt_sel, i_freq, ix_YY]
            )

        Vlog = numpy.log10(numpy.abs(V_time_bl) + 1e-6)
        Vlog_all.append(Vlog.ravel())



        # ------------------------------------------------------------
        # PLOT: TIME × BASELINE
        # ------------------------------------------------------------

        ax = axes_time[ib]
        im = ax.imshow(Vlog, origin="lower", aspect="auto")
        ax.set_xlabel("Baseline index")
        ax.set_ylabel("Time index")
        ax.set_title(beam)

    # ============================================================
    # AUTOCORRELATION SPECTRUM
    # ============================================================

        # Select the time sample at zenith.
        tval = unique_times[16]  # 34 time samples: MATLAB idx 17 ... Python 16
        blt_sel = numpy.where(numpy.abs(time_array - tval) < 1e-12)[0]

        auto_sel = blt_sel[
            ant1_array[blt_sel] == ant2_array[blt_sel]
        ]

        V_auto_I = numpy.zeros(freq_array.size, dtype=complex)

        for f in range(freq_array.size):
            V_auto_I[f] = numpy.mean(
                0.5 * (
                    data_pyuv[auto_sel, f, ix_XX] +
                    data_pyuv[auto_sel, f, ix_YY]
                )
            )

        ax_freq.plot(
            freq_array / 1e6,
            numpy.abs(V_auto_I),
            linewidth=1.5,
            label=beam
        )

    # ============================================================
    # FINALIZE FIGURES
    # ============================================================

    ax_freq.set_xlabel("Frequency (MHz)")
    ax_freq.set_ylabel("Amplitude")
    ax_freq.legend()

    plt.show()
