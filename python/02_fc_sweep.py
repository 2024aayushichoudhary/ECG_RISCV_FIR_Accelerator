# python/02_fc_sweep.py
# Run from project root:  .\venv\Scripts\python.exe python\02_fc_sweep.py
import numpy as np
import wfdb
from scipy.signal import firwin, freqz

FS, NTAPS, SNR_DB = 360, 16, 6.0
MIT, NST, REC = "data/raw/mitdb", "data/raw/nstdb", "100"
N = 10 * FS
WARM = NTAPS          # skip filter warm-up samples when measuring power


def load_clean():
    r = wfdb.rdrecord(f"{MIT}/{REC}", physical=False)
    return r.d_signal[:N, 0].astype(float) - r.adc_zero[0], float(r.adc_gain[0])


def noise_unit(name, gain):
    """Zero-mean noise sequence of length N (unscaled)."""
    if name == "50Hz":
        t = np.arange(N) / FS
        return np.sin(2 * np.pi * 50 * t)
    nz = wfdb.rdrecord(f"{NST}/{name}", physical=True).p_signal[10 * FS:10 * FS + N, 0]
    return (nz - nz.mean()) * gain


def fir(x, h):
    return np.convolve(x, h)[:len(x)]


def p(x):
    return np.mean(x[WARM:] ** 2)


def main():
    x, gain = load_clean()
    xc = x - x.mean()
    noises = {}
    for name in ["em", "ma", "50Hz"]:
        nz = noise_unit(name, gain)
        k = np.sqrt(p(xc) / (p(nz) * 10 ** (SNR_DB / 10)))   # hit 6 dB input SNR
        noises[name] = k * nz

    print(f"Input SNR = {SNR_DB} dB for every noise type\n")
    print(" FC(Hz) | SNR gain dB: em    ma    50Hz | 50Hz gain dB | R-peak kept")
    print("--------+---------------------------------+--------------+------------")
    for fc in [20, 25, 30, 35, 40, 45]:
        h = firwin(NTAPS, fc, window="hamming", fs=FS)
        y_sig = fir(xc, h)
        gains = []
        for name in ["em", "ma", "50Hz"]:
            s_out = 10 * np.log10(p(y_sig) / p(fir(noises[name], h)))
            gains.append(s_out - SNR_DB)
        _, H = freqz(h, worN=[50], fs=FS)
        g50 = 20 * np.log10(abs(H[0]))
        peak = fir(x, h)[WARM:].max() / x.max() * 100
        print(f"  {fc:3d}   |        {gains[0]:+6.2f} {gains[1]:+6.2f} {gains[2]:+6.2f}  |"
              f"   {g50:7.2f}    |  {peak:5.1f} %")


if __name__ == "__main__":
    main()