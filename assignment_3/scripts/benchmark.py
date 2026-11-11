import subprocess
import re
import os
import random
import csv
import argparse

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

parser = argparse.ArgumentParser()
parser.add_argument("--sizes", type=int, nargs="+", default=[100, 200, 400, 800, 1000, 1500, 2000])
parser.add_argument("--reps", type=int, default=10, help="runs per configuration (first one is discarded)")
parser.add_argument("--timeout", type=float, default=60.0, help="seconds per process")
parser.add_argument("--results-dir", default="results")
parser.add_argument("--seed", type=int, default=42, help="random seed for shuffling execution order")
args_cli = parser.parse_args()

sizes = sorted(args_cli.sizes)
repetitions = args_cli.reps
TIMEOUT_S = args_cli.timeout
results_dir = args_cli.results_dir
base_seed = args_cli.seed

configs = []

configs.append({"Build": "seq", "label": "Sequential ikj (1 thread)", "variant": "ikj", "threads": 1, "block": 0})
configs.append({"Build": "seq", "label": "Sequential Tile B=64 (1 thread)", "variant": "tile", "threads": 1, "block": 64})

thread_counts = [1, 2, 3, 4, 6, 8]
for th in thread_counts:
    tag = " (oversubscribed)" if th > 4 else ""
    configs.append({"Build": "omp", "label": f"OpenMP ikj p={th}{tag}", "variant": "ikj", "threads": th, "block": 0})
    configs.append({"Build": "omp", "label": f"OpenMP Tile B=64 p={th}{tag}", "variant": "tile", "threads": th, "block": 64})

FLOAT = r"([-+0-9.eE]+)"

def grab(pattern, text, cast=float):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None

def exe_for(cfg):
    return os.path.join(".", f"run_matmul_{cfg['Build']}.exe")

def command_for(cfg, n):
    exe = exe_for(cfg)
    cmd = [exe, str(n), cfg["variant"], str(cfg["threads"])]
    if cfg["variant"] == "tile":
        cmd.append(str(cfg["block"]))
    return cmd

def parse_output(out):
    return {
        "time": grab(r"Time\s*=\s*" + FLOAT, out),
        "requested_threads": grab(r"RequestedThreads\s*=\s*([0-9]+)", out, int),
        "actual_threads": grab(r"ActualThreads\s*=\s*([0-9]+)", out, int),
        "nnz_a": grab(r"NNZ\(A\)\s*=\s*([0-9]+)", out, int),
        "nnz_b": grab(r"NNZ\(B\)\s*=\s*([0-9]+)", out, int),
        "nnz_c": grab(r"NNZ\(C\)\s*=\s*([0-9]+)", out, int),
        "mem": grab(r"PeakMemory\s*=\s*([0-9]+)\s*KB", out, int),
        "chk_trace": grab(r"ChecksumTrace\s*=\s*" + FLOAT, out),
        "chk_full": grab(r"ChecksumFull\s*=\s*" + FLOAT, out),
    }

COLUMNS = ["Size", "Build", "Method", "Variant", "BlockSize", "RequestedThreads", "ActualThreads", "Repetition", "ShuffleOrderIndex", "IsWarmup", "TimeSeconds", "PeakMemoryKB", "ChecksumTrace", "ChecksumFull", "Status"]

os.makedirs(results_dir, exist_ok=True)
raw_path = os.path.join(results_dir, "raw_data_detailed.csv")

csv_file = open(raw_path, "w", encoding="utf-8", newline="")
writer = csv.DictWriter(csv_file, fieldnames=COLUMNS)
writer.writeheader()
csv_file.flush()

reference_checksums = {}

print("Starting Assignment 3 performance benchmarks...")
print(f"sizes={sizes} reps={repetitions} (first discarded) timeout={TIMEOUT_S}s per process")

env = os.environ.copy()
env["OMP_DYNAMIC"] = "FALSE"
env.pop("OMP_NUM_THREADS", None)

timed_out_configs = {}

all_tasks = []
for cfg in configs:
    for n in sizes:
        all_tasks.append((cfg, n))
        
try:
    for rep in range(repetitions):
        warm = "Yes" if rep == 0 else "No"
        print(f"\n--- Executing Repetition {rep} (IsWarmup: {warm}) ---")
        
        rep_rng = random.Random(base_seed + rep)
        shuffled_tasks = list(all_tasks)
        rep_rng.shuffle(shuffled_tasks)
        
        for shuffle_idx, (cfg, n) in enumerate(shuffled_tasks):
            cfg_key = (cfg["Build"], cfg["variant"], cfg["threads"], cfg["block"])
            
            if cfg_key in timed_out_configs and n >= timed_out_configs[cfg_key]:
                writer.writerow({
                    "Size": n, "Build": cfg["Build"], "Method": cfg["label"], "Variant": cfg["variant"],
                    "BlockSize": cfg["block"] if cfg["block"] > 0 else 0,
                    "RequestedThreads": cfg["threads"], "ActualThreads": cfg["threads"],
                    "Repetition": rep, "ShuffleOrderIndex": shuffle_idx, "IsWarmup": warm,
                    "TimeSeconds": "", "PeakMemoryKB": "", "ChecksumTrace": "", "ChecksumFull": "",
                    "Status": "SKIPPED_AFTER_TIMEOUT"
                })
                csv_file.flush()
                continue

            exe_path = exe_for(cfg)
            if not os.path.exists(exe_path):
                print(f"  [Warning] Executable {exe_path} not found. Run make first.")
                continue
                
            cmd = command_for(cfg, n)
            row_data = {
                "Size": n, "Build": cfg["Build"], "Method": cfg["label"], "Variant": cfg["variant"],
                "BlockSize": cfg["block"] if cfg["block"] > 0 else 0,
                "RequestedThreads": cfg["threads"], "ActualThreads": cfg["threads"],
                "Repetition": rep, "ShuffleOrderIndex": shuffle_idx, "IsWarmup": warm,
                "TimeSeconds": "", "PeakMemoryKB": "", "ChecksumTrace": "", "ChecksumFull": "", "Status": ""
            }
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=TIMEOUT_S, env=env)
                r = parse_output(res.stdout)
                
                if r["time"] is None or r["chk_full"] is None:
                    status = "PARSE_ERROR"
                else:
                    req_th = r.get("requested_threads", cfg["threads"])
                    act_th = r.get("actual_threads", cfg["threads"])
                    if req_th != act_th:
                        status = f"THREAD_MISMATCH_REQ{req_th}_ACT{act_th}"
                    else:
                        ref = reference_checksums.setdefault(n, r["chk_full"])
                        if abs(ref - r["chk_full"]) > 1e-6 * max(1.0, abs(ref)):
                            status = "CHECKSUM_MISMATCH"
                        else:
                            status = "OK"
                        
                row_data.update({
                    "ActualThreads": r.get("actual_threads", cfg["threads"]),
                    "TimeSeconds": f"{r['time']:.6f}" if r.get("time") is not None else "",
                    "PeakMemoryKB": r.get("mem", ""),
                    "ChecksumTrace": f"{r['chk_trace']:.4f}" if r.get("chk_trace") is not None else "",
                    "ChecksumFull": f"{r['chk_full']:.4f}" if r.get("chk_full") is not None else "",
                    "Status": status
                })
            except subprocess.TimeoutExpired:
                row_data["Status"] = "TIMEOUT"
                timed_out_configs[cfg_key] = min(n, timed_out_configs.get(cfg_key, n))
                print(f"  [TIMEOUT] Configuration {cfg['label']} exceeded {TIMEOUT_S}s at n={n}. Skipping larger sizes.")
            except Exception as e:
                row_data["Status"] = f"ERROR: {e}"
            
            writer.writerow(row_data)
            csv_file.flush()

finally:
    csv_file.close()

print(f"\nIncremental raw run data saved continuously in '{raw_path}' with shuffle order tracking.")