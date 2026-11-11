# python/00_explore_data.py
# Run from the project root: python python/00_explore_data.py
import os
import numpy as np
import matplotlib.pyplot as plt
import wfdb

FS_EXPECTED = 360
MITDB_DIR = "data/raw/mitdb"
NSTDB_DIR = "data/raw/nstdb"

# [DECISION] documented subset. Dev records for tuning, test records held out.
DEV_RECORDS  = ["100", "101", "103"]
TEST_RECORDS = ["115", "117", "123"]
NOISE_RECORDS = ["bw", "em", "ma"]   # baseline wander, muscle, motion artifact


def download():
    os.makedirs(MITDB_DIR, exist_ok=True)
    os.makedirs(NSTDB_DIR, exist_ok=True)
    mit_files = []
    for r in DEV_RECORDS + TEST_RECORDS:
        mit_files += [f"{r}.dat", f"{r}.hea", f"{r}.atr"]
    wfdb.dl_files("mitdb", MITDB_DIR, mit_files)
    ns_files = []
    for r in NOISE_RECORDS:
        ns_files += [f"{r}.dat", f"{r}.hea"]
    wfdb.dl_files("nstdb", NSTDB_DIR, ns_files, keep_subdirs=False)


def main():
    if not os.path.exists(f"{MITDB_DIR}/100.dat"):
        print("Downloading data (needs internet)...")
        download()

    rec = wfdb.rdrecord(f"{MITDB_DIR}/100", physical=False)
    ann = wfdb.rdann(f"{MITDB_DIR}/100", "atr")

    print("--- MIT-BIH record 100 ---")
    print("fs            :", rec.fs)
    print("channels      :", rec.sig_name)
    print("total samples :", rec.sig_len)
    print("ADC resolution:", rec.adc_res, "bits")
    print("ADC zero      :", rec.adc_zero)
    print("ADC gain      :", rec.adc_gain, "ADC units per mV")
    d = rec.d_signal[:, 0]              # raw integer ADC values, channel 0
    print("digital min/max (ch0):", d.min(), d.max())

    # ---- plot first 10 s of record 100 with annotated beats ----
    n = 10 * rec.fs
    t = np.arange(n) / rec.fs
    plt.figure(figsize=(12, 4))
    plt.plot(t, d[:n], lw=0.8)
    beats = ann.sample[ann.sample < n]
    plt.plot(beats / rec.fs, d[beats], "rv", label="annotated beats")
    plt.xlabel("time (s)"); plt.ylabel("ADC units")
    plt.title(f"MIT-BIH 100, {rec.sig_name[0]}, first 10 s")
    plt.legend(); plt.tight_layout()
    plt.savefig("results/plots/step1_ecg_100.png", dpi=120)
    print("beats in first 10 s:", len(beats))

    # ---- plot noise records ----
    fig, axs = plt.subplots(3, 1, figsize=(12, 6), sharex=True)
    for ax, name in zip(axs, NOISE_RECORDS):
        nz = wfdb.rdrecord(f"{NSTDB_DIR}/{name}")
        x = nz.p_signal[:n, 0]
        ax.plot(t, x, lw=0.7); ax.set_ylabel(f"{name} (mV)")
        print(f"noise {name}: fs={nz.fs}, len={nz.sig_len}, std={x.std():.3f} mV")
    axs[-1].set_xlabel("time (s)")
    plt.tight_layout()
    plt.savefig("results/plots/step1_noise.png", dpi=120)
    plt.show()


if __name__ == "__main__":
    main()


    