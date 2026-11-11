
# STEP 2: Floating-Point FIR Reference
# File: python/01_fir_reference.py
# Run from project root:
# .\venv\Scripts\python.exe python\01_fir_reference.py

import os
import numpy as np
import matplotlib.pyplot as plt
import wfdb
from scipy.signal import firwin, freqz


# --------------------------------------------------
# 1. Project settings
# --------------------------------------------------

FS = 360
NTAPS = 16
FC_HZ = 30.0

MIT = "data/raw/mitdb"
NST = "data/raw/nstdb"

REC = "100"

START_S = 0
SEG_S = 10

SNR_DB = 6.0

OUT = "data/processed"
PLOTS = "results/plots"
TABLES = "results/tables"


# --------------------------------------------------
# 2. Load clean ECG
# --------------------------------------------------

def load_clean(rec, start_s, seg_s):

    # physical=False loads raw digital ADC samples
    r = wfdb.rdrecord(
        f"{MIT}/{rec}",
        physical=False
    )

    a = int(start_s * FS)
    b = int((start_s + seg_s) * FS)

    # Read channel 0 and remove ADC zero offset
    x = r.d_signal[a:b, 0].astype(np.int64)
    x = x - int(r.adc_zero[0])

    gain = float(r.adc_gain[0])

    return x, gain


# --------------------------------------------------
# 3. Add controlled noise to ECG
# --------------------------------------------------

def make_noisy(x_clean, noise_name, snr_db, gain,
               start_sample=0):

    n = len(x_clean)

    # Read noise record in physical units (mV)
    noise_record = wfdb.rdrecord(
        f"{NST}/{noise_name}",
        physical=True
    )

    nz = noise_record.p_signal[
        start_sample:start_sample + n, 0
    ]

    if len(nz) != n:
        raise ValueError(
            f"Noise record {noise_name} is too short. "
            f"Expected {n} samples, got {len(nz)}."
        )

    # Convert noise from mV to ADC units
    nz = (nz - nz.mean()) * gain

    # Calculate clean signal power and noise power
    ps = np.mean(
        (x_clean - x_clean.mean()) ** 2
    )

    pn = np.mean(nz ** 2)

    if pn == 0:
        raise ValueError(
            f"Noise record {noise_name} has zero power."
        )

    # Scale noise to achieve target SNR
    k = np.sqrt(
        ps / (pn * 10 ** (snr_db / 10))
    )

    # Add noise and round to integer ADC samples
    x_noisy = np.round(
        x_clean + k * nz
    ).astype(np.int64)

    return x_noisy


# --------------------------------------------------
# 4. Apply causal FIR filter
# --------------------------------------------------

def fir(x, h):

    # Zero initial state
    # Output length is same as input length
    return np.convolve(
        x.astype(float),
        h
    )[:len(x)]


# --------------------------------------------------
# 5. Calculate SNR
# --------------------------------------------------

def calculate_snr(signal, noise):

    signal_power = np.mean(signal ** 2)
    noise_power = np.mean(noise ** 2)

    if noise_power == 0:
        return float("inf")

    return 10 * np.log10(
        signal_power / noise_power
    )


# --------------------------------------------------
# 6. Main program
# --------------------------------------------------

def main():

    # Create output folders if they do not exist
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PLOTS, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    # ----------------------------------------------
    # A. Design FIR filter
    # ----------------------------------------------

    h = firwin(
        NTAPS,
        FC_HZ,
        window="hamming",
        fs=FS
    )

    print("\n========== FIR COEFFICIENTS ==========")

    for i, value in enumerate(h):
        print(f"h[{i:2d}] = {value: .8f}")

    print(
        "\nSymmetric:",
        np.allclose(h, h[::-1])
    )

    print(
        "Sum of coefficients:",
        round(h.sum(), 6)
    )

    print(
        "Sum of absolute coefficients:",
        round(np.abs(h).sum(), 6)
    )

    # ----------------------------------------------
    # B. Frequency response
    # ----------------------------------------------

    frequencies_to_check = [
        1, 5, 15, 25, 30, 40, 50, 100, 150
    ]

    _, H_check = freqz(
        h,
        worN=frequencies_to_check,
        fs=FS
    )

    print("\n========== FILTER GAIN ==========")

    for f, response in zip(
        frequencies_to_check,
        np.abs(H_check)
    ):

        gain_db = 20 * np.log10(
            response + 1e-12
        )

        print(
            f"{f:4d} Hz : {gain_db:7.2f} dB"
        )

    # ----------------------------------------------
    # C. Load clean ECG
    # ----------------------------------------------

    x_clean, gain = load_clean(
        REC,
        START_S,
        SEG_S
    )

    print("\n========== ECG DATA ==========")

    print("Record:", REC)
    print("Samples:", len(x_clean))
    print("ADC gain:", gain)

    print(
        "Clean ECG range:",
        x_clean.min(),
        "to",
        x_clean.max(),
        "ADC units"
    )

    # ----------------------------------------------
    # D. Generate noisy ECG signals
    # ----------------------------------------------

    start_noise = 10 * FS

    x_em = make_noisy(
        x_clean,
        "em",
        SNR_DB,
        gain,
        start_noise
    )

    x_ma = make_noisy(
        x_clean,
        "ma",
        SNR_DB,
        gain,
        start_noise
    )

    print("\nNoisy ECG signals generated.")
    print("Target input SNR:", SNR_DB, "dB")

    # ----------------------------------------------
    # E. Apply FIR filter
    # ----------------------------------------------

    y_clean = fir(x_clean, h)
    y_em = fir(x_em, h)
    y_ma = fir(x_ma, h)

    print("\nFIR filtering completed.")

    # ----------------------------------------------
    # F. Calculate input and output SNR
    # ----------------------------------------------

    print("\n========== SNR RESULTS ==========")
    print("Noise   Input SNR   Output SNR   Improvement")

    for name, x_noisy, y_noisy in [
        ("em", x_em, y_em),
        ("ma", x_ma, y_ma)
    ]:

        # Actual injected noise
        input_noise = x_noisy - x_clean

        # Output noise using linearity
        output_noise = y_noisy - y_clean

        # Center signal for SNR calculation
        clean_centered = (
            x_clean - x_clean.mean()
        )

        clean_output_centered = (
            y_clean - y_clean.mean()
        )

        input_snr = calculate_snr(
            clean_centered,
            input_noise
        )

        output_snr = calculate_snr(
            clean_output_centered,
            output_noise
        )

        improvement = output_snr - input_snr

        print(
            f"{name:5s} "
            f"{input_snr:9.2f} dB "
            f"{output_snr:10.2f} dB "
            f"{improvement:+10.2f} dB"
        )

    # ----------------------------------------------
    # G. Save coefficients and signals
    # ----------------------------------------------

    np.save(
        f"{OUT}/h_float.npy",
        h
    )

    np.save(
        f"{OUT}/x_clean.npy",
        x_clean
    )

    np.save(
        f"{OUT}/x_em.npy",
        x_em
    )

    np.save(
        f"{OUT}/x_ma.npy",
        x_ma
    )

    np.save(
        f"{OUT}/y_clean_float.npy",
        y_clean
    )

    np.save(
        f"{OUT}/y_em_float.npy",
        y_em
    )

    np.save(
        f"{OUT}/y_ma_float.npy",
        y_ma
    )

    np.savetxt(
        f"{TABLES}/fir_coefficients_float.txt",
        h,
        fmt="%.12f"
    )

    print("\nSaved coefficients and signals.")

    # ----------------------------------------------
    # H. Plot frequency response
    # ----------------------------------------------

    f = np.linspace(
        0,
        FS / 2,
        512
    )

    _, H = freqz(
        h,
        worN=f,
        fs=FS
    )

    plt.figure(figsize=(9, 4))

    plt.plot(
        f,
        20 * np.log10(
            np.abs(H) + 1e-12
        )
    )

    plt.axvline(
        50,
        linestyle="--",
        label="50 Hz powerline"
    )

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Gain (dB)")
    plt.title(
        f"{NTAPS}-Tap FIR Frequency Response"
    )

    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        f"{PLOTS}/step2_freq_response.png",
        dpi=120
    )

    # ----------------------------------------------
    # I. Plot clean and noisy ECG
    # ----------------------------------------------

    n = 5 * FS

    t = np.arange(n) / FS

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(12, 8),
        sharex=True
    )

    ax[0].plot(
        t,
        x_clean[:n],
        label="Clean ECG input"
    )

    ax[0].plot(
        t,
        y_clean[:n],
        label="FIR output"
    )

    ax[1].plot(
        t,
        x_em[:n],
        label="EM noisy input"
    )

    ax[1].plot(
        t,
        y_em[:n],
        label="FIR output"
    )

    ax[2].plot(
        t,
        x_ma[:n],
        label="MA noisy input"
    )

    ax[2].plot(
        t,
        y_ma[:n],
        label="FIR output"
    )

    for axis in ax:

        axis.legend(loc="upper right")
        axis.set_ylabel("ADC units")
        axis.grid(True)

    ax[2].set_xlabel("Time (seconds)")

    plt.tight_layout()

    plt.savefig(
        f"{PLOTS}/step2_filtering.png",
        dpi=120
    )

    plt.show()

    print("\n========== STEP 2 COMPLETE ==========")

    print(
        "Frequency plot:",
        f"{PLOTS}/step2_freq_response.png"
    )

    print(
        "Filtering plot:",
        f"{PLOTS}/step2_filtering.png"
    )

    print(
        "Saved data:",
        OUT
    )


if __name__ == "__main__":
    main()
