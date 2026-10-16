# Assignment 1 – Basic Matrix Multiplication in Python, Java and C

BIG DATA · Grado en Ciencia e Ingeniería de Datos · ULPGC · 2026-2027

**Research question.** How does the matrix size *n* affect the runtime and the memory use of the same
basic i-j-k triple-loop multiplication of n × n float64 matrices when it is implemented in C
(gcc, `-O2`), Java (HotSpot JVM) and Python (CPython), on one specific laptop?

All numbers in this repository come from one machine (see [`results/environment.md`](results/environment.md)):
AMD Ryzen 3 3200U (2 cores / 4 logical processors), 7.46 GB RAM, Windows 11.

## 1. Repository layout

```
assignment_1/
├── c/matmul.c                  triple loop in C        (flat row-major double array)
├── java/MatMul.java            triple loop in Java     (flat row-major double[])
├── python/matmul_basic.py      triple loop in Python   (list of row lists, no NumPy in the kernel)
├── scripts/
│   ├── config.py               ALL experimental settings (sizes, seed, repetitions, timeout, flags)
│   ├── build.py                compiles the C and Java programs
│   ├── generate_inputs.py      shared input matrices (binary files) + SHA-256 manifest
│   ├── capture_environment.py  hardware / software description
│   ├── run_benchmarks.py       benchmark harness (warm-up, repetitions, memory, timeout)
│   └── analyze.py              tables (summary.csv / summary.md) and figures
├── tests/test_correctness.py   correctness tests
├── data/manifest.csv           SHA-256 of every input file (the .bin files are NOT committed)
├── results/                    raw_measurements.csv, runs.csv, environment.*, summary.*, figures/
├── requirements.txt            pinned Python dependencies
└── AI_DISCLOSURE.md            generative-AI disclosure required by the course
```

## 2. Requirements

The versions below are the ones used for the reported results.

| Tool | Version used | Check with |
|---|---|---|
| Python | CPython 3.13.14 | `python --version` |
| Python packages | see `requirements.txt` (numpy 2.4.3, pandas 2.3.3, matplotlib 3.10.8, psutil 7.2.2) | `pip list` |
| C compiler | gcc 16.1.0 (MSYS2 UCRT64) | `gcc --version` |
| JDK | Temurin 25.0.2 (needs `javac`, not only a JRE) | `javac -version` |

NumPy is used only to create the inputs and the reference checksums. It is **not** used inside any timed
multiplication.

## 3. Build and run (Windows PowerShell; on Linux/macOS use `source .venv/bin/activate`)

From the repository root:

```
cd assignment_1
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python scripts/build.py                   # compile C and Java
python tests/test_correctness.py          # must finish with OK before benchmarking
python scripts/generate_inputs.py         # create data/*.bin (done automatically by the runner too)
python scripts/run_benchmarks.py --quick  # ~1 min smoke test, writes to results/smoke/
python scripts/run_benchmarks.py --out-dir results_rerun   # full experiment (about 50 minutes on my laptop)
python scripts/analyze.py --results results_rerun          # tables and figures
```

* If PowerShell refuses to run the activation script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
* If `python` is not found, use `py`.
* `gcc` not found: install MinGW-w64 (for example MSYS2: `pacman -S mingw-w64-ucrt-x86_64-gcc`) and add
  `C:\msys64\ucrt64\bin` to `PATH`; open a new terminal.
* The committed results in `results/` are the data used in the report. A rerun goes to a different folder
  (`--out-dir`) so they are not overwritten. `--overwrite` replaces existing CSV files in the chosen folder.
* To get the figures and tables of the committed data without re-running anything:
  `python scripts/analyze.py` (reads `results/`, rewrites `summary.*` and `figures/`).

### Regenerating and verifying the inputs

The input files (`data/A_n<N>.bin`, `data/B_n<N>.bin`, 126 MB in total) are not stored in Git.
`python scripts/generate_inputs.py` recreates them: float64, uniform [0, 1), written little-endian
row-major; matrix A of size n uses `numpy.random.default_rng([2026, n, 0])` and B uses
`[2026, n, 1]`. The committed `data/manifest.csv` lists the SHA-256 of each file.

To check that you got identical inputs, regenerate them and run `git diff --ignore-cr-at-eol --stat data/manifest.csv`:
no output means every hash is identical (the flag ignores Windows/Linux line-ending differences). (I verified that the files regenerate with identical hashes with
NumPy 2.5.3 as well as with 2.4.3.)

## 4. Experimental design

| Item | Setting |
|---|---|
| Algorithm | straightforward i-j-k triple loop, O(n³); the k-loop accumulates in a local `sum` that is stored once per element. No library multiplication is used |
| Numeric type | float64 (IEEE 754 double) in all three languages |
| Inputs | the same binary input files are read by all three programs (identical logical inputs); seed 2026, uniform [0, 1) |
| Sizes | 10, 50, 100, 200, 300, 500, 750, 1000, 1500, 2000 (`config.SIZES`) |
| Storage layout | C and Java: one contiguous row-major array per matrix, element (i, j) at `i*n + j`. Python: list of row lists, each element a separate boxed `float` object (unavoidable difference) |
| Loop order | i-j-k in all three languages. B is read down a column (`b[k][j]` / `b[k*n+j]`), which is cache-unfriendly for large n in every language |
| Timers | monotonic: `QueryPerformanceCounter` (C on Windows), `System.nanoTime` (Java), `time.perf_counter` (Python) |
| **Timed region** | **only the multiplication kernel.** Reading the inputs, allocating and zero-initialising the output, process start-up and JVM start-up are not timed |
| Result use | after the timed runs each program sums all elements of C and prints the checksum; the runner compares it with a NumPy reference |
| Warm-up runs | C: 1, Java: 3 (JIT compilation), Python: 1 (0 for n ≥ 500 because runs are very long). Warm-ups are kept in the raw CSV (`phase = warmup`) but excluded from the statistics |
| Measured repetitions | 5 per configuration; Python with n ≥ 500: 3 (runs take minutes; the IQR of 3 values is only a rough indication of variability) |
| Statistic | median and IQR (Q3 − Q1, linear interpolation); min and max are also reported |
| Memory metric | **peak working set of the whole process** (Windows `PeakWorkingSetSize` read with psutil; Linux `VmHWM`). It includes the runtime itself (JVM about 44 MB, CPython about 20 MB before any matrix), so it is not array storage. Also reported: theoretical raw storage 3·8·n² bytes, and for Java the heap in use after loading the inputs. These quantities must not be compared as if they were identical |
| Limits | 900 s wall time per (language, size) process; planning memory budget 4 GB. A timeout is recorded as a timeout (no time is invented) and larger sizes of that language are skipped |
| C build | `gcc -O2 -std=c11 -ffp-contract=off -Wall -Wextra` (no `-O3`, no `-march=native`, no `-ffast-math`) |
| Java run | `java -XX:+UseSerialGC -Xmx4g -cp java/out MatMul ...` |
| Python | the interpreter that runs `run_benchmarks.py`; cyclic garbage collector disabled during the timed section (the kernel creates no container objects) |
| Threads | all three kernels are single-threaded. Java also runs JIT-compiler threads in the background and a single GC thread (`SerialGC`); NumPy is used only outside the timed region |

**What stays fixed:** algorithm, loop order, numeric type, inputs, sizes, compiler flags, JVM options,
timer boundary and the machine. **What varies:** the language implementation and the matrix size.

### Correctness checks

`tests/test_correctness.py` runs each program through its normal command line and compares the complete
result matrix:

* known 2×2 and 3×3 products, a 1×1 case, identity (A·I and I·B) and zero matrices (exact equality);
* integer-valued random matrices (exact equality, no rounding involved);
* random matrices of sizes 2 to 64 against NumPy `A @ B` with `rtol = atol = 1e-10`, and C against Java
  and Python with `rtol = atol = 1e-12`;
* an input file of the wrong size must be rejected.

*Why these tolerances:* the rounding error of a length-n dot product is bounded by about n·u·Σ|aₖbₖ| with
u = 2⁻⁵³ ≈ 1.1·10⁻¹⁶, so for n ≤ 64 the relative error stays below about 10⁻¹⁴. NumPy sums in a different
order (BLAS), which explains tiny differences, while 10⁻¹⁰ is far below the size of any real bug. The three
programs add the products in the same order without fused multiply-add, so they are expected to agree almost
bit for bit.

In every benchmark run the checksum of C is compared with the NumPy reference with
`rtol = 10·(n² + n)·2⁻⁵³ + 10⁻¹²` (n dot products with relative error ≤ n·u, summed over n² elements,
with a safety factor of 10). Every reported run passed (`checksum_ok = True` in `results/runs.csv`).

## 5. Results included in this repository

| File | Content |
|---|---|
| `results/raw_measurements.csv` | every single timing: `run_id, lang, n, dtype, phase (warmup/measured), repetition, seconds` |
| `results/runs.csv` | one row per (language, n): status, repetitions, peak memory, checksum check, protocol, exact command, timestamp |
| `results/environment.json` / `.md` | hardware, operating system, versions, flags and settings |
| `results/summary.csv` / `.md` | median, IQR, min, max, memory, fitted exponents, ratios, failures |
| `results/figures/` | `runtime_vs_n.png`, `time_per_madd_vs_n.png`, `peak_memory_vs_n.png` |

Limits found on this machine: C and Java completed every size up to **n = 2000**; Python completed up to
**n = 1000** (877 s of the 900 s budget). Python at n = 1500 reached the 900 s timeout with no completed
repetition, and n = 2000 was not attempted afterwards. Details are in `results/summary.md`.

### Known limitations

* One machine, one run per configuration; the Windows power plan during the run was *Balanced*, not
  *Best performance*. The variability is therefore visible in the IQR (for some C and Java sizes it is above
  30 % of the median). Treat small differences between languages as inside the noise.
* Python with n ≥ 500 has only 3 repetitions and no warm-up.
* The memory metric is the peak of the whole process, including the language runtime.
* Conclusions apply only to these implementations, settings, inputs and hardware, not to the languages in
  general.

## 6. Reuse

This is the first assignment. Later assignments reuse the input generator, the benchmark runner and the
analysis scripts from this folder, and will state the exact commit they reuse.
