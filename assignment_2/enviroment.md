# Experimental Environment and Execution Protocol

## 1. Hardware Specifications
* **Processor (CPU):** x64 Multi-core Processor (Intel / AMD)
* **CPU Cache Hierarchy:** L3 Cache: 192 KB | L4 Cache: 1 MB | L5 Cache: 4 MB
* **Main Memory (RAM):** 16 GB System Memory

## 2. Software & Toolchain Specifications
* **Operating System:** Microsoft Windows 11 (x64)
* **Compiler:** GCC (MinGW-w64)
* **Compilation Flags:** `-O3 -std=c11 -Wall -Wextra -ffp-contract=off`
* **Scripting Runtime:** Python 3.13.14
* **Dependencies:** `numpy` v2.4.3, `matplotlib` v3.10.8

## 3. Experimental Control & Protocol
* **Power Plan:** Balanced (GUID: 381b4222-f694-41f0-9685-ff5bb260df2e) with active AC power connection to prevent dynamic CPU frequency scaling
* **In-Process Warm-up:** An initial unmeasured multiplication pass is executed internally within each C process runtime to pre-fault allocated virtual memory pages and populate L1/L2/L3 cache lines prior to high-precision timestamping (`clock_gettime`)
* **Memory Measurement Tool & Metric:** Peak Working Set Size (measured in Kilobytes) via Windows API (`GetProcessMemoryInfo` from `<psapi.h>`), recording maximum physical RAM allocated during runtime execution.
* **Statistical Rigor:** 7 independent process executions per matrix size ($n$), analyzing Median and Interquartile Range (IQR, Q25-Q75)
* **Data Generation & Pseudorandomness:** Custom 32-bit Xorshift PRNG (`seed=42`, period $2^{32}-1$) to replace platform-dependent `rand()` (avoiding Windows `RAND_MAX = 32767` precision bottleneck) and guarantee identical bitwise matrix generation across environments.
* **Sparsity Protocol:** Matrix $A$ is generated fully dense ($p=0.0$), while matrix $B$ enforces controlled target sparsity levels $p \in \{0.5, 0.8, 0.95\}$.