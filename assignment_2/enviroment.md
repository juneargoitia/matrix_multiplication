# Experimental Environment and Execution Protocol

## 1. Hardware Specifications
* **Processor (CPU):** AMD Ryzen 3 3200U with Radeon Vega Mobile Gfx 
* **Physical Cores / Logical Threads:** 2 physical cores / 4 logical threads
* **CPU Cache:** L1, L2, and L3 cache hierarchy managed dynamically by the Windows OS kernel
* **Main Memory (RAM):** 8 GB DDR4/DDR5

## 2. Software & Toolchain Specifications
* **Operating System:** Microsoft Windows 11 (x64)
* **Compiler:** GCC (MinGW-w64) version 16.1.0
* **Compilation Flags:** `-O3 -std=c11 -Wall -Wextra -ffp-contract=off`
* **Scripting Runtime:** Python 3.x
* **Dependencies:** `numpy` (v1.20+), `matplotlib` (v3.5+)

## 3. Experimental Control & Protocol
* **Power Plan:** High Performance / Balanced mode with active AC power connection to prevent dynamic CPU frequency scaling
* **Process Warm-up:** Initial process execution (repetition 0) discarded as operational warm-up to stabilize memory allocation
* **Statistical Rigor:** 7 process repetitions per configuration matrix size ($n$), using Median and Interquartile Range (IQR, Q25-Q75)