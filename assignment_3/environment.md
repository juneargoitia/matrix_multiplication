# Environment used for the Assignment 3 measurements

## Hardware

- CPU: AMD Ryzen 3 3200U with Radeon Vega Mobile Gfx
- Physical cores: 2
- Logical processors: 4
- RAM: 6.9 GiB
- Power plan: GUID de plan de energ¡a: 381b4222-f694-41f0-9685-ff5bb260df2e  (Equilibrado)

## Software

- OS: Windows-11-10.0.26200-SP0
- gcc: `gcc (Rev5, Built by MSYS2 project) 16.1.0`
- Compiler flags (Makefile): `-O3 -std=c11 -Wall -Wextra -ffp-contract=off` (+ `-fopenmp` for the OpenMP builds)
- OpenMP runtime: `_OPENMP=202111 omp_get_num_procs=4 omp_get_max_threads=4`
- Python: 3.13.14
- numpy: 2.4.3
- pandas: 2.3.3
- matplotlib: 3.10.8
- psutil: 7.2.2

## OpenMP settings

Set by `scripts/benchmark.py` for every run: `OMP_DYNAMIC=FALSE` (the runtime may not change the thread count), `OMP_NUM_THREADS` removed (the thread count is passed explicitly and verified: `ActualThreads` column). Schedule is `static`, fixed in the source. Thread affinity is NOT set (`OMP_PROC_BIND` / `OMP_PLACES` unset): the OS scheduler places the threads.

Variables present in the shell that launched this script:

- (none)

Oversubscription: runs with more threads than logical processors (p > 4) are labelled `(oversubscribed)` in the raw data.
