import subprocess
import re
import os
import csv
import argparse
import numpy as np

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

parser = argparse.ArgumentParser()
parser.add_argument("--sizes", type=int, nargs="+", default=[100, 200, 400, 800, 1000, 1500, 2000])
parser.add_argument("--reps", type=int, default=10, help="runs per configuration (first one is discarded)")
parser.add_argument("--timeout", type=float, default=20.0, help="seconds per process")
parser.add_argument("--results-dir", default="results")
args_cli = parser.parse_args()

sizes = args_cli.sizes
repetitions = args_cli.reps
TIMEOUT_S = args_cli.timeout
results_dir = args_cli.results_dir

configs = []

configs.append({"Build": "seq", "label": "Sequential ikj", "exe": "run_matmul_seq.exe", "variant": "ikj", "threads": 1, "block": 0})
configs.append({"Build": "seq", "label": "Sequential Tile B=64", "exe": "run_matmul_seq.exe", "variant": "tile", "threads": 1, "block": 64})

thread_counts = [1, 2, 3, 4, 6, 8]
for th in thread_counts:
    tag = " (oversubscribed)" if th > 4 else ""
    configs.append({"Build": "omp", "label": f"OpenMP ikj p={th}{tag}", "exe": "run_matmul_omp.exe", "variant": "ikj", "threads": th, "block": 0})
    configs.append({"Build": "omp", "label": f"OpenMP Tile B=64 p={th}{tag}", "exe": "run_matmul_omp.exe", "variant": "tile", "threads": th, "block": 64})

FLOAT = r"([-+0-9.eE]+)"

def grab(pattern, text, cast=float):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None

def command_for(cfg, n):
    exe = os.path.join(".", cfg["exe"])
    cmd = [exe, str(n), cfg["variant"], str(cfg["threads"])]
    if cfg["variant"] == "tile":
        cmd.append(str(cfg["block"]))
    return cmd

def parse_output(out):
    return {
        "time": grab(r"Time\s*=\s*" + FLOAT, out),
        "actual_threads": grab(r"ActualThreads\s*=\s*([0-9]+)", out, int),
        "nnz_a": grab(r"NNZ\(A\)\s*=\s*([0-9]+)", out, int),
        "nnz_b": grab(r"NNZ\(B\)\s*=\s*([0-9]+)", out, int),
        "nnz_c": grab(r"NNZ\(C\)\s*=\s*([0-9]+)", out, int),
        "mem": grab(r"PeakMemory\s*=\s*([0-9]+)\s*KB", out, int),
        "chk": grab(r"Checksum\s*=\s*" + FLOAT, out),
    }

COLUMNS = ["Size", "Build", "Method", "Variant", "BlockSize", "RequestedThreads", "ActualThreads", "Repetition", "IsWarmup", "TimeSeconds", "PeakMemoryKB", "Checksum", "Status"]

raw_rows = []
reference_checksums = {}

print("Starting Assignment 3 performance benchmarks...")
print(f"sizes={sizes} reps={repetitions} (first discarded) timeout={TIMEOUT_S}s per process")

env = os.environ.copy()
env["OMP_DYNAMIC"] = "FALSE"
env["OMP_WAIT_POLICY"] = "PASSIVE"
env["OMP_SCHEDULE"] = "STATIC"

for rep in range(repetitions):
    warm = "Yes" if rep == 0 else "No"
    print(f"\n--- Executing Repetition {rep} (IsWarmup: {warm}) ---")
    
    for cfg in configs:
        exe_path = os.path.join(".", cfg["exe"])
        if not os.path.exists(exe_path):
            print(f"  [Warning] Executable {exe_path} not found. Run make first.")
            continue
            
        for n in sizes:
            cmd = command_for(cfg, n)
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=TIMEOUT_S, env=env)
                r = parse_output(res.stdout)
                
                if r["time"] is None or r["chk"] is None:
                    status = "PARSE_ERROR"
                else:
                    ref = reference_checksums.setdefault(n, r["chk"])
                    if abs(ref - r["chk"]) > 1e-6 * max(1.0, abs(ref)):
                        status = "CHECKSUM_MISMATCH"
                    else:
                        status = "OK"
                        
                raw_rows.append({
                    "Size": n, "Build": cfg["Build"], "Method": cfg["label"], "Variant": cfg["variant"],
                    "BlockSize": cfg["block"] if cfg["block"] > 0 else "",
                    "RequestedThreads": cfg["threads"], "ActualThreads": r.get("actual_threads", cfg["threads"]),
                    "Repetition": rep, "IsWarmup": warm,
                    "TimeSeconds": f"{r['time']:.6f}" if r.get("time") else "",
                    "PeakMemoryKB": r.get("mem", ""),
                    "Checksum": f"{r['chk']:.4f}" if r.get("chk") else "",
                    "Status": status
                })
            except subprocess.TimeoutExpired:
                raw_rows.append({
                    "Size": n, "Build": cfg["Build"], "Method": cfg["label"], "Variant": cfg["variant"],
                    "BlockSize": cfg["block"] if cfg["block"] > 0 else "",
                    "RequestedThreads": cfg["threads"], "ActualThreads": cfg["threads"],
                    "Repetition": rep, "IsWarmup": warm,
                    "TimeSeconds": "", "PeakMemoryKB": "", "Checksum": "", "Status": "TIMEOUT"
                })
            except Exception as e:
                raw_rows.append({
                    "Size": n, "Build": cfg["Build"], "Method": cfg["label"], "Variant": cfg["variant"],
                    "BlockSize": cfg["block"] if cfg["block"] > 0 else "",
                    "RequestedThreads": cfg["threads"], "ActualThreads": cfg["threads"],
                    "Repetition": rep, "IsWarmup": warm,
                    "TimeSeconds": "", "PeakMemoryKB": "", "Checksum": "", "Status": f"ERROR: {e}"
                })

os.makedirs(results_dir, exist_ok=True)
raw_path = os.path.join(results_dir, "raw_data_detailed.csv")

with open(raw_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(raw_rows)

print(f"\nRaw runs saved in '{raw_path}' ({len(raw_rows)} rows).")