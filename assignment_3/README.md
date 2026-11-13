# Assignment 3 – Parallel Matrix Multiplication with OpenMP

BIG DATA · Grado en Ciencia e Ingeniería de Datos · ULPGC · 2026-2027

**Research question.** How does thread count $p$ affect the runtime, speedup, parallel efficiency, and memory footprint of a shared-memory OpenMP dense matrix multiplication implementation across different matrix sizes $n$ and cache-locality strategies (`ikj` loop reordering vs. cache tiling), and under what conditions does parallel execution provide an advantage over an equivalent sequential baseline?

All reported numbers in this repository were collected on a single reference machine (see [`results/environment.md`](results/environment.md)):
**Intel Core i3-10110U** (2 physical cores / 4 logical processors with Hyper-Threading, up to 4.10 GHz), 8.00 GB RAM, Windows 11.

---

## 1. Repository layout

```
assignment_3/
├── src/
│   ├── matmul.h                kernel interfaces and runtime configuration structures
│   ├── matmul_seq.c            sequential baseline implementation (ikj & tiled, no OpenMP)
│   ├── matmul_omp.c            parallel OpenMP implementation (ikj & tiled, #pragma omp parallel)
│   └── main.c                  CLI runner, monotonic timer, checksum verification, thread guard
├── tests/
│   └── test.c                  C unit & edge-case test suite (zero, identity, small, non-multiple n, n < threads)
├── scripts/
│   ├── benchmark.py            orchestrator: randomised execution order, warm-up, CSV logging, RSS memory
│   ├── analyze.py              statistical summary (median, IQR, speedup, efficiency) & LaTeX tables
│   └── plot_results.py         publication-quality plots (runtime, speedup, efficiency, memory, heatmaps)
├── results/
│   ├── benchmark_results.csv   raw measurements for all runs (warmup + measured)
│   ├── environment.md          captured hardware, OS, compiler, and OpenMP runtime metadata
│   └── figures/                generated PNG plots for the report
├── Makefile                    automated build and test targets (seq & omp binaries)
├── requirements.txt            pinned Python dependencies for orchestration and analysis
├── report.tex                  LaTeX source for the research report
└── README.md                   this documentation and reproducibility guide
```

---

## 2. Requirements & Environment

The reported measurements were produced using the following toolchain:

| Component | Version / Specification | Verification command |
|---|---|---|
| Operating System | Windows 11 (64-bit) | `systeminfo` |
| C Compiler | GCC 15.2.0 (MinGW-w64 / MSYS2) with OpenMP (`libgomp`) | `gcc --version` |
| Build Tool | GNU Make | `make --version` |
| Python | CPython 3.11+ | `python --version` |
| Python Packages | `numpy`, `pandas`, `matplotlib`, `seaborn`, `psutil` (see `requirements.txt`) | `pip list` |

NumPy and SciPy/Pandas are used strictly outside the timed C kernels for verification, statistical aggregation, and plotting.

---

## 3. Build, Test, and Run Instructions

From the `assignment_3/` directory:

### 3.1 Compile Binaries and Run Correctness Tests

```bash
make all
```

This compiles four executables inside `build/`:
* `build/run_matmul_seq.exe` — Sequential baseline compiled **without** `-fopenmp`.
* `build/run_matmul_omp.exe` — Parallel implementation compiled **with** `-fopenmp`.
* `build/test_seq.exe` & `build/test_omp.exe` — Automated unit test suites.

To execute the correctness verification suite before running benchmarks:

```bash
make test
```

*(Note: On Windows PowerShell, if `make` is not in your `PATH`, invoke `mingw32-make` or compile directly using the commands defined in `Makefile`.)*

### 3.2 Run the Benchmark Suite

Install the Python analysis dependencies:

```bash
pip install -r requirements.txt
```

Execute the full experimental sweep (writes incrementally to `results/benchmark_results.csv`):

```bash
python scripts/benchmark.py
```

### 3.3 Regenerate Tables and Figures

To recompute all summary statistics, speedup/efficiency metrics, and figures from the committed `results/benchmark_results.csv` without re-running the C benchmarks:

```bash
python scripts/analyze.py
python scripts/plot_results.py
```

---

## 4. Experimental Design & Protocol

| Parameter | Configuration |
|---|---|
| **Algorithms** | 1) Cache-friendly `ikj` triple loop; 2) Blocked/Tiled `ikj` loop with tile size $B = 64$ (`32 KB` L1d cache fit). Both share identical arithmetic work $O(n^3)$ across sequential and parallel variants. |
| **Numeric Type** | IEEE 754 `double` (`float64`), row-major contiguous 1D arrays (`i * n + j`). |
| **Matrix Sizes ($n$)** | $n \in \{128, 256, 512, 1024, 1536, 2048\}$ ($n \times n$ dense square matrices). |
| **Thread Counts ($p$)** | Sequential baseline (`seq`, $p=1$ without OpenMP) vs. OpenMP (`omp`) with $p \in \{1, 2, 3, 4, 6, 8\}$. Configurations $p \in \{6, 8\}$ explicitly evaluate thread oversubscription beyond the 4 logical processors. |
| **OpenMP Control** | `OMP_DYNAMIC=FALSE`, `OMP_SCHEDULE=STATIC`, `OMP_WAIT_POLICY=PASSIVE` (or controlled via `omp_set_num_threads(p)`). Runtime guard verifies `omp_get_num_threads() == p`. |
| **Input Generation** | Deterministic uniform random values in $[-1.0, 1.0]$ generated via fixed seed (`42`) inside C using identical buffers across methods. |
| **Timed Region** | **Multiplication kernel only** (including parallel zero-initialisation of output matrix $C$ inside the parallel region). Memory allocation, input generation, and checksum validation are excluded. |
| **Timer** | High-resolution monotonic clock (`clock_gettime(CLOCK_MONOTONIC)` / `QueryPerformanceCounter`). |
| **Repetitions & Order** | 1 discarded warm-up run + **7 measured repetitions** per `(algorithm, n, threads)` configuration. Within each repetition round, execution order is randomly shuffled using a fixed seed (`2026`) to mitigate thermal throttling and frequency drift bias. |
| **Summary Statistics** | Median runtime (ms) and Interquartile Range ($\text{IQR} = Q_{75} - Q_{25}$). Speedup $S(p) = \text{Median}(T_{\text{seq}}) / \text{Median}(T_p)$ and Efficiency $E(p) = S(p) / p$. |
| **Memory Metric** | Peak Resident Set Size (Peak RSS, in MB) measured at the OS process level via `psutil` (`peak_wset` on Windows / `ru_maxrss` on POSIX), compared against theoretical buffer footprint $3 \times 8n^2$ bytes. |
| **Compiler Flags** | Sequential: `gcc -O3 -std=c11 -Wall -Wextra`<br>Parallel: `gcc -O3 -std=c11 -fopenmp -Wall -Wextra` |

### Correctness Validation

1. **Pre-benchmark unit suite (`tests/test.c`):** Verifies exact results on $1 \times 1$, zero, and identity matrices ($A \cdot I = A$, $I \cdot B = B$), hand-calculated $3 \times 3$ and $4 \times 4$ matrices, non-block-multiple dimensions ($n = 65, 130$), and cases where $n < p$ ($n = 3, p = 8$). Floating-point equality is validated against a reference implementation with $\text{atol} = 10^{-11}$ and $\text{rtol} = 10^{-11}$.
2. **In-benchmark checksums:** Every benchmark run computes the full sum of matrix $C$ (`Checksum`) and compares it across sequential and parallel runs for identical $n$ to guarantee zero race conditions or silent truncation.

---

## 5. Summary of Main Findings

* **OpenMP 1-Thread Overhead:** Running `omp` with $p = 1$ introduces negligible fork-join overhead ($< 2\%$) for $n \ge 512$, while at $n = 128$ thread-pool management adds measurable relative overhead ($S(1) \approx 0.90$–$0.95$).
* **Physical vs. Logical Core Scaling:** Speedup scales sharply up to $p = 2$ (matching the 2 physical cores of the i3-10110U, achieving $S(2) \approx 1.85$–$1.92$, $E(2) > 92\%$). Between $p = 2$ and $p = 4$ (Hyper-Threading / SMT), speedup continues to grow modestly up to $S(4) \approx 2.35$–$2.55$ ($E(4) \approx 60\%$), bounded by shared execution units and DRAM memory bandwidth saturation.
* **Oversubscription ($p = 6, 8$):** Exceeding the 4 logical hardware threads yields no further speedup and slightly increases runtime variability (IQR) due to OS context switching.
* **Cache Tiling + OpenMP:** Combining cache blocking ($B = 64$) with OpenMP maintains higher parallel efficiency at large sizes ($n = 1536, 2048$) by reducing L3/DRAM contention across concurrent threads.

---

## 6. Generative AI Disclosure

In accordance with the Big Data course policy on generative AI tools:
* **Tools used:** Large Language Models (Google Gemini / ChatGPT).
* **Purpose & Scope:** Used as a technical assistant to structure the C project layout and `Makefile`, review OpenMP pragma scoping (`shared`/`private` clauses to prevent data races), design the randomised execution order in `scripts/benchmark.py`, and refine the English phrasing of `README.md` and `report.tex`.
* **Verification:** All C kernels, OpenMP thread-control logic, Python scripts, benchmark measurements, and statistical analyses were executed, verified against unit tests, and validated directly by the author on the target hardware.