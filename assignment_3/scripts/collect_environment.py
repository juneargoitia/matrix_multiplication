import os
import platform
import re
import shutil
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)


def run(cmd, shell=False):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=shell)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return f"(not available: {e})"


def powershell(query):
    return run(["powershell", "-NoProfile", "-Command", query])


lines = ["# Environment used for the Assignment 3 measurements", ""]

hw = []
logical = os.cpu_count()
physical = None
cpu_name = platform.processor()
try:
    import psutil
    physical = psutil.cpu_count(logical=False)
    mem = psutil.virtual_memory().total / 2**30
    hw.append(f"- RAM: {mem:.1f} GiB")
except ImportError:
    pass
if platform.system() == "Windows":
    out = powershell("Get-CimInstance Win32_Processor | "
                        "Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | Format-List")
    m = re.search(r"Name\s*:\s*(.+)", out)
    if m:
        cpu_name = m.group(1).strip()
    m = re.search(r"NumberOfCores\s*:\s*(\d+)", out)
    if m:
        physical = int(m.group(1))
    m = re.search(r"NumberOfLogicalProcessors\s*:\s*(\d+)", out)
    if m:
        logical = int(m.group(1))
    hw.append(f"- Power plan: {powershell('powercfg /getactivescheme')}")
lines += ["## Hardware", "", f"- CPU: {cpu_name}",
            f"- Physical cores: {physical if physical else 'unknown (pass --physical to make_report_assets.py)'}",
            f"- Logical processors: {logical}"] + hw + [""]

lines += ["## Software", ""]
lines.append(f"- OS: {platform.platform()}")
gcc = shutil.which("gcc")
lines.append(f"- gcc: `{run(['gcc', '--version']).splitlines()[0] if gcc else 'not found'}`")
lines.append(f"- Compiler flags (Makefile): `{[l for l in open('Makefile').read().splitlines() if l.startswith('CFLAGS')][0].split('=', 1)[1].strip()}` "
                "(+ `-fopenmp` for the OpenMP builds)")
if gcc:
    probe = os.path.join(ROOT, "_omp_probe.c")
    with open(probe, "w") as f:
        f.write('#include <stdio.h>\n#include <omp.h>\nint main(void){\n'
                '#ifdef _OPENMP\nprintf("_OPENMP=%d omp_get_num_procs=%d omp_get_max_threads=%d\\n",'
                '_OPENMP,omp_get_num_procs(),omp_get_max_threads());\n#endif\nreturn 0;}\n')
    exe = os.path.join(ROOT, "_omp_probe.exe")
    out = run(["gcc", "-fopenmp", probe, "-o", exe])
    lines.append(f"- OpenMP runtime: `{run([exe]) if os.path.exists(exe) else out}`")
    for p in (probe, exe):
        if os.path.exists(p):
            os.remove(p)
lines.append(f"- Python: {sys.version.split()[0]}")
for pkg in ("numpy", "pandas", "matplotlib", "psutil"):
    try:
        mod = __import__(pkg)
        lines.append(f"- {pkg}: {mod.__version__}")
    except ImportError:
        lines.append(f"- {pkg}: not installed")
lines.append("")

lines += ["## OpenMP settings", "",
            "Set by `scripts/benchmark.py` for every run: `OMP_DYNAMIC=FALSE` (the runtime may not change the thread count), "
            "`OMP_NUM_THREADS` removed (the thread count is passed explicitly and verified: `ActualThreads` column). "
            "Schedule is `static`, fixed in the source. Thread affinity is NOT set (`OMP_PROC_BIND` / `OMP_PLACES` "
            "unset): the OS scheduler places the threads.", "",
            "Variables present in the shell that launched this script:", ""]
found = False
for k in sorted(os.environ):
    if k.startswith("OMP_") or k.startswith("GOMP_") or k in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        lines.append(f"- `{k}={os.environ[k]}`")
        found = True
if not found:
    lines.append("- (none)")
lines += ["", "Oversubscription: runs with more threads than logical processors "
            f"(p > {logical}) are labelled `(oversubscribed)` in the raw data.", ""]

with open("environment.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("environment.md written:\n")
print("\n".join(lines))