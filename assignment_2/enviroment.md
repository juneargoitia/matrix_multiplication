# Experimental Environment and Execution Protocol

## 1. Hardware Specifications
* **Processor (CPU):** AMD Ryzen 3 3200U with Radeon Vega Mobile Gfx (2 physical cores, 4 logical threads)
* **CPU Cache Hierarchy:** 
  * L1 Cache: 128 KB (64 KB instruction + 64 KB data per core)
  * L2 Cache: 1 MB (512 KB per core)
  * L3 Cache: 4 MB (shared)
* **Main Memory (RAM):** 8 GB (7.46 GB usable system memory)

## 2. Software & Toolchain Specifications
* **Operating System:** Microsoft Windows 11 x64
* **Compiler:** GCC (MinGW-w64) v14.1.0
* **Compilation Flags:** `-O3 -std=c11 -Wall -Wextra -ffp-contract=off -lpsapi`
* **Python Environment:** Python 3.13.14
* **Python Libraries:** `numpy` v2.4.3, `matplotlib` v3.10.8

## 3. Experimental Control & Protocol
* **Power Plan:** Balanced power plan with active AC power connection. While dynamic CPU frequency scaling (Boost/SpeedShift) remains active under Windows, operating on AC power mitigates aggressive thermal and power throttling policies associated with battery operation.
* **In-Process Warm-up:** An initial unmeasured multiplication pass is executed internally within each C process runtime to pre-fault allocated virtual memory pages and populate L1D/L2/L3 cache lines prior to high-precision timestamping (`clock_gettime`).
* **Data Generation & Pseudorandomness:** Custom 32-bit Xorshift PRNG (`seed=42`, period $2^{32}-1$) replacing platform-dependent `rand()` (avoiding Windows `RAND_MAX = 32767` precision bottleneck) to guarantee identical bitwise matrix generation across environments.
* **Sparsity Protocol:** Matrix $A$ is generated fully dense ($p=0.0$), while matrix $B$ enforces controlled target sparsity levels $p \in \{0.5, 0.8, 0.95\}$.
* **Memory Measurement Tool & Metric:** Peak Working Set Size (measured in Kilobytes) via Windows API (`GetProcessMemoryInfo` from `<psapi.h>`), recording maximum physical RAM allocated during runtime execution.
* **Statistical Rigor:** 7 independent process executions per matrix size ($n$), analyzing Median and Interquartile Range (IQR, $Q_{75} - Q_{25}$).