# Quality-Aware ECG Signal Processing Using a RISC-V SoC and Hardware FIR Accelerator

**An FPGA-oriented ECG signal processing project using a fixed-point FIR filter, Verilog RTL implementation, and a Python reference model for functional verification.**

> **Project Status:** FIR filter design, fixed-point modelling, and Verilog behavioural simulation completed. FPGA implementation and RISC-V integration are planned future extensions.

---

## 1. Overview

Electrocardiogram (ECG) signals are often contaminated by different types of noise, including electrode motion artefacts, muscle activity, and power-line interference. These disturbances can affect important ECG characteristics, particularly the QRS complex and R-peaks.

This project focuses on developing a hardware-oriented ECG noise reduction system using a **16-tap Finite Impulse Response (FIR) low-pass filter**.

The filter is designed and evaluated using Python, converted into fixed-point representation, and implemented using Verilog HDL. The RTL implementation is verified against a Python fixed-point reference model using Xilinx Vivado simulation.

The long-term objective is to integrate the FIR hardware accelerator with a RISC-V soft processor to develop an FPGA-based ECG signal processing system.

## 2. Project Objectives

- Analyse ECG signals and different noise conditions.
- Design and evaluate an FIR filter using Python.
- Convert floating-point filter coefficients into fixed-point representation.
- Develop a pipelined FIR filter architecture using Verilog HDL.
- Verify RTL functionality against a Python fixed-point reference model.
- Explore FPGA implementation and RISC-V processor integration.

## 3. System Workflow

The current development workflow consists of:

1. **ECG Data Acquisition:** ECG recordings are obtained from the MIT-BIH Arrhythmia Database.
2. **Noise Analysis:** Different noise conditions are studied using the MIT-BIH Noise Stress Test Database and test signals.
3. **FIR Filter Design:** Filter coefficients are designed and evaluated using Python.
4. **Fixed-Point Quantization:** Floating-point coefficients are converted into signed Q1.15 representation.
5. **Reference Model:** A Python fixed-point model generates expected output samples.
6. **RTL Development:** A pipelined 16-tap FIR filter is implemented using Verilog HDL.
7. **Functional Verification:** Vivado behavioural simulation compares the RTL outputs against the Python reference outputs.

## 4. FIR Filter Specifications

| Parameter | Specification |
|---|---|
| Filter Type | Low-pass FIR |
| Number of Taps | 16 |
| Filter Order | 15 |
| Sampling Frequency | 360 Hz |
| Cutoff Frequency | 35 Hz (provisional) |
| Coefficient Format | Signed Q1.15 |
| Input Width | 16 bits |
| Output Width | 16 bits |
| Accumulator Width | 32 bits |
| RTL Implementation | Pipelined Verilog |
| Simulation Tool | Xilinx Vivado 2022.2 |

The 35 Hz cutoff frequency is a provisional design choice based on the current evaluation of filtering performance under different noise conditions.

## 5. Fixed-Point Implementation

The floating-point FIR coefficients are quantized into signed Q1.15 fixed-point representation.

The coefficient integer values used in the current implementation are:

```text
-113, -146, -98, 363,
1520, 3300, 5174, 6384,
6384, 5174, 3300, 1520,
363, -98, -146, -113
```

The FIR filter performs the following convolution operation:

\[
y[n] = \sum_{k=0}^{15} h[k]x[n-k]
\]

Where:

- \(x[n]\) represents the current input sample.
- \(h[k]\) represents the FIR filter coefficients.
- \(y[n]\) represents the filtered output sample.

The RTL datapath uses signed multiplication and accumulation, followed by fixed-point rounding, scaling, and output saturation.

## 6. RTL Architecture

The Verilog implementation uses a three-stage pipelined datapath.

### Stage 1: Multiplication
The current and previous input samples are multiplied by their corresponding FIR coefficients.

### Stage 2: Accumulation
The multiplication results are added to generate the accumulated FIR output.

### Stage 3: Output Processing
The accumulated result undergoes rounding, scaling, and saturation to produce a signed 16-bit output.

The design uses `in_valid` and `out_valid` signals to indicate valid input acceptance and output availability.

**Current pipeline characteristics:**
- Pipeline latency: 3 clock edges.
- Throughput: 1 sample per clock cycle under continuous valid input.
- Invalid input data is ignored when `in_valid` is LOW.

## 7. Verification and Simulation

The Verilog implementation is verified against a Python fixed-point reference model using generated test vectors.

### Test Cases

The following test scenarios are currently evaluated:

- Clean ECG signal.
- Electrode Motion (EM) noise.
- Muscle Artifact (MA) noise.
- 50 Hz power-line interference.
- Stress test sequence.
- Clean ECG with gaps between valid input samples.

### Simulation Results

| Test Case | Compared Outputs | Mismatches | Result |
|---|---:|---:|---|
| Clean, gap = 1 | 3600 | 0 | PASS |
| EM, gap = 1 | 3600 | 0 | PASS |
| MA, gap = 1 | 3600 | 0 | PASS |
| 50 Hz, gap = 1 | 3600 | 0 | PASS |
| Stress, gap = 1 | 612 | 0 | PASS |
| Clean, gap = 5 | 3600 | 0 | PASS |
| **Total** | **18,612** | **0** | **PASS** |

The RTL outputs matched the Python fixed-point reference outputs bit-for-bit across all tested vectors.

This demonstrates functional agreement between the Verilog implementation and the Python reference model for the tested simulation cases. FPGA hardware validation and timing closure have not yet been performed.

## 8. Tools and Technologies

- **Programming:** Python
- **Digital Design:** Verilog HDL, SystemVerilog
- **Numerical Processing:** NumPy, SciPy
- **ECG Data Processing:** WFDB
- **Simulation:** Xilinx Vivado 2022.2
- **Datasets:** MIT-BIH Arrhythmia Database, MIT-BIH Noise Stress Test Database

## 9. Repository Structure

```text
ECG_RISCV_FIR_Accelerator/
│
├── python/          # ECG preprocessing, FIR design and reference model
│
├── rtl/             # Verilog FIR filter implementation
│
├── tb/              # SystemVerilog testbench
│
├── data/            # Processed ECG input and expected output vectors
│
├── results/         # Simulation and evaluation results
│
├── constraints/     # FPGA constraint files
│
├── docs/            # Project documentation and screenshots
│
├── fir_projvlsi.xpr # Vivado project file
│
└── README.md
```

## 10. Running the Simulation

1. Clone or download this repository.
2. Open the Vivado project in Xilinx Vivado 2022.2.
3. Check that the testbench memory-file paths point to the repository's `data/processed/` directory.
4. Set `tb_fir16` as the simulation top module.
5. Run **Run Behavioral Simulation**.
6. Observe `clk`, `rst`, `in_valid`, `in_data`, `out_valid`, and `out_data` in the waveform.
7. Check the Tcl Console for test-case results and mismatch counts.

Note: The current testbench uses local file paths that may need to be updated when running the project on another system.

## 11. Future Work

- FPGA synthesis and implementation.
- Resource utilisation and timing analysis.
- Hardware validation on an FPGA development board.
- RISC-V soft processor integration.
- ECG signal quality assessment.
- Further FIR architecture optimisation for hardware efficiency.
- Integration with additional ECG processing stages and R-peak detection.

## 12. Project Development Status

| Component | Status |
|---|---|
| ECG data exploration | Completed |
| FIR filter design using Python | Completed |
| Fixed-point coefficient quantization | Completed |
| Python fixed-point reference model | Completed |
| Verilog FIR RTL | Implemented |
| Vivado behavioural simulation | Passed for current test vectors |
| FPGA synthesis and implementation | Planned |
| FPGA board validation | Planned |
| RISC-V integration | Planned |

---

**Project Focus:** Digital Signal Processing • Verilog RTL Design • FPGA-Based Acceleration • RISC-V SoC Integration

*This repository documents the ongoing development of an FPGA-oriented ECG signal processing project. Implementation details and results will be updated as development progresses.*
