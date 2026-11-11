# python/03_fixed_point.py
# Run from project root:  .\venv\Scripts\python.exe python\03_fixed_point.py
import os
import numpy as np
import wfdb
from scipy.signal import firwin

FS, NTAPS = 360, 16
FC = 35.0                 # [DECISION] chosen from the sweep
QF = 15                   # coefficient fraction bits (Q1.15)
SCALE = 1 << QF
SNR_DB = 6.0
OUT, TABLES = "data/processed", "results/tables"
NST = "data/raw/nstdb"


# ---------- fixed-point FIR: this IS the golden model for the RTL ----------
def quantize(h):
    hq = np.round(h * SCALE).astype(np.int64)
    d = SCALE - int(hq.sum())          # make DC gain exactly 1.0
    assert d % 2 == 0, "odd correction, handle manually"
    hq[7] += d // 2                    # keep symmetry: add equally to centre taps
    hq[8] += d // 2
    return hq


def fir_fixed(x, hq):
    """x: int array (int16 range). Returns (acc, y).
    acc : full-precision sum of products (32-bit in hardware)
    y   : round-to-nearest, >>15, saturated to int16
    Zero initial state, same as an empty delay line after reset."""
    acc = np.convolve(x.astype(np.int64), hq)[:len(x)]
    y = (acc + (1 << (QF - 1))) >> QF          # arithmetic shift (floors)
    y = np.clip(y, -32768, 32767)
    return acc, y


def write_mem(path, arr, bits):
    """One hex word per line, two's complement. Verilog: $readmemh."""
    mask, digits = (1 << bits) - 1, bits // 4
    with open(path, "w") as f:
        for v in arr:
            f.write(f"{int(v) & mask:0{digits}X}\n")


def save_set(name, x, hq):
    acc, y = fir_fixed(x, hq)
    write_mem(f"{OUT}/x_{name}.mem", x, 16)
    write_mem(f"{OUT}/y_{name}_fixed.mem", y, 16)
    write_mem(f"{OUT}/acc_{name}_fixed.mem", acc, 32)
    np.savetxt(f"{OUT}/x_{name}_dec.txt", x, fmt="%d")
    np.savetxt(f"{OUT}/y_{name}_fixed_dec.txt", y, fmt="%d")
    np.save(f"{OUT}/x_{name}.npy", x)
    np.save(f"{OUT}/y_{name}_fixed.npy", y)
    return acc, y


def add_noise_int(x_clean, nz, snr_db):
    ps = np.mean((x_clean - x_clean.mean()) ** 2)
    k = np.sqrt(ps / (np.mean(nz ** 2) * 10 ** (snr_db / 10)))
    return np.round(x_clean + k * nz).astype(np.int64)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    # ---------- 1. coefficients ----------
    h = firwin(NTAPS, FC, window="hamming", fs=FS)
    hq = quantize(h)
    print("tap | float        | Q1.15 int | hex")
    for i in range(NTAPS):
        print(f"{i:3d} | {h[i]: .8f} | {hq[i]:7d}   | {hq[i] & 0xFFFF:04X}")
    print("\nsymmetric        :", np.array_equal(hq, hq[::-1]))
    print("sum(hq)          :", hq.sum(), "(must be", SCALE, ")")
    print("max coef error   : %.2e (LSB = %.2e)" % (np.max(np.abs(hq / SCALE - h)), 1 / SCALE))
    bound = 32768 * int(np.abs(hq).sum())
    print(f"acc bound        : {bound:,}  < 2^31 = {2**31:,} ->", bound < 2**31)
    assert bound < 2**31, "32-bit accumulator not enough!"
    with open(f"{TABLES}/fir_coefficients_q15.txt", "w") as f:
        for i in range(NTAPS):
            f.write(f"{i} {hq[i]} {hq[i] & 0xFFFF:04X}\n")
    np.save(f"{OUT}/hq.npy", hq)

    # ---------- 2. signals (re-use Step 2 data, add 50 Hz case) ----------
    x_clean = np.load(f"{OUT}/x_clean.npy")
    x_em = np.load(f"{OUT}/x_em.npy")
    x_ma = np.load(f"{OUT}/x_ma.npy")
    t = np.arange(len(x_clean)) / FS
    x_50 = add_noise_int(x_clean, np.sin(2 * np.pi * 50 * t), SNR_DB)

    # ---------- 3. stress vector (checks overflow and saturation) ----------
    rng = np.random.default_rng(1)
    rand_part = rng.integers(-32768, 32768, 500)
    s = np.where(hq >= 0, 1, -1)                     # worst case: sign(x[n-k]) = sign(h[k])
    worst = (s[::-1] * 32767).astype(np.int64)       # oldest sample first
    stress = np.concatenate([rand_part, np.zeros(16, dtype=np.int64), worst,
                             np.full(40, 32767), np.full(40, -32768)])

    sets = {"clean": x_clean, "em": x_em, "ma": x_ma, "50hz": x_50, "stress": stress}

    # ---------- 4. run, save, compare with float ----------
    print("\nset     | N    | max|acc|      | max err vs float (LSB) | rms err")
    for name, x in sets.items():
        acc, y = save_set(name, x, hq)
        assert np.abs(acc).max() < 2**31
        if name != "stress":
            yf = np.convolve(x.astype(float), h)[:len(x)]
            e = y - yf
            print(f"{name:7s} | {len(x):4d} | {np.abs(acc).max():13,d} | "
                  f"{np.abs(e).max():8.3f}               | {np.sqrt(np.mean(e**2)):.3f}")
        else:
            print(f"{name:7s} | {len(x):4d} | {np.abs(acc).max():13,d} | (no float compare)")
    print("\nSaved .mem / _dec.txt files in", OUT)


if __name__ == "__main__":
    main()