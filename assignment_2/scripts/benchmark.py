import subprocess
import re
import os
import csv
import argparse
import numpy as np
import matplotlib.pyplot as plt

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

parser = argparse.ArgumentParser()
parser.add_argument("--sizes", type=int, nargs="+", default=[200, 400, 600, 800, 1000, 1200, 1500])
parser.add_argument("--reps", type=int, default=7, help="runs per configuration (first one is discarded)")
parser.add_argument("--timeout", type=float, default=20.0, help="seconds per process (whole process)")
parser.add_argument("--results-dir", default="results")
args_cli = parser.parse_args()

sizes = args_cli.sizes
repetitions = args_cli.reps
TIMEOUT_S = args_cli.timeout
results_dir = args_cli.results_dir
sparsity_levels = [0.5, 0.8, 0.95]
tile_block_sizes = [16, 32, 64, 128]


configs = [
    {"label": "Baseline (dense)",        "exe": "baseline.exe",       "p": 0.0, "block": None},
    {"label": "Loop Reordering (dense)", "exe": "optimized_loop.exe", "p": 0.0, "block": None},
]
for b in tile_block_sizes:
    configs.append({"label": f"Cache Tiling B={b} (dense)", "exe": "optimized_tile.exe", "p": 0.0, "block": b})
for p in sparsity_levels:
    configs.append({"label": f"Loop Reordering (p={p})", "exe": "optimized_loop.exe", "p": p, "block": None})
    configs.append({"label": f"Sparse CSR (p={p})",      "exe": "sparse_mult.exe",    "p": p, "block": None})

FLOAT = r"([-+0-9.eE]+)"


def grab(pattern, text, cast=float):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None


def command_for(cfg, n):
    exe = os.path.join(".", cfg["exe"])
    cmd = [exe, str(n)]
    if cfg["exe"] == "optimized_tile.exe":
        cmd += [str(cfg["block"]), str(cfg["p"])]
    elif cfg["exe"] in ("optimized_loop.exe", "sparse_mult.exe"):
        cmd += [str(cfg["p"])]
    return cmd


def parse_output(cfg, out):
    sparse = cfg["exe"] == "sparse_mult.exe"
    return {
        "time": grab(r"MultTime\s*=\s*" + FLOAT, out) if sparse else grab(r"(?<![A-Za-z])Time\s*=\s*" + FLOAT, out),
        "conv": grab(r"ConvTime\s*=\s*" + FLOAT, out) if sparse else 0.0,
        "nnz_a": grab(r"NNZ\(A\)\s*=\s*([0-9]+)", out, int),
        "nnz_b": grab(r"NNZ\(B\)\s*=\s*([0-9]+)", out, int),
        "nnz_c": grab(r"NNZ\(C\)\s*=\s*([0-9]+)", out, int),
        "mem": grab(r"PeakMemory\s*=\s*([0-9]+)\s*KB", out, int),
        "chk": grab(r"Checksum\s*=\s*" + FLOAT, out),
    }


COLUMNS = ["Size", "Method", "BlockSize", "Sparsity", "Repetition", "IsWarmup", "TimeSeconds",
                "ConvTimeSeconds", "NNZ_A", "NNZ_B", "NNZ_C", "PeakMemoryKB", "Checksum", "Status"]

raw_rows = []
summary_rows = []
summary_data = {c["label"]: {"sizes": [], "median": [], "q25": [], "q75": []} for c in configs}
timeouts = []
reference_checksums = {} 
checksum_problems = []


def add_row(n, cfg, rep, warm, status, r=None):
    r = r or {}
    raw_rows.append({
        "Size": n, "Method": cfg["label"], "BlockSize": cfg["block"] if cfg["block"] else "",
        "Sparsity": cfg["p"], "Repetition": rep, "IsWarmup": warm,
        "TimeSeconds": "" if r.get("time") is None else f"{r['time']:.6f}",
        "ConvTimeSeconds": "" if r.get("conv") is None else f"{r['conv']:.6f}",
        "NNZ_A": r.get("nnz_a", ""), "NNZ_B": r.get("nnz_b", ""), "NNZ_C": r.get("nnz_c", ""),
        "PeakMemoryKB": r.get("mem", ""),
        "Checksum": "" if r.get("chk") is None else f"{r['chk']:.4f}",
        "Status": status,
    })


print("Starting performance tests (benchmarks)...")
print(f"sizes={sizes} reps={repetitions} (first discarded) timeout={TIMEOUT_S}s per process")

for cfg in configs:
    exe_path = os.path.join(".", cfg["exe"])
    label = cfg["label"]
    if not os.path.exists(exe_path):
        print(f"  [Warning] Not found {exe_path}. Compile it first (make).")
        continue

    print(f"\n Running {label}...")
    failed_size = None

    for n in sizes:
        if failed_size is not None:
            add_row(n, cfg, "", "", f"SKIPPED_AFTER_TIMEOUT_AT_{failed_size}")
            print(f"  n = {n:4d} | skipped (timeout at n={failed_size})")
            continue

        measured = []
        timed_out = False

        for rep in range(repetitions):
            warm = "Yes" if rep == 0 else "No"
            try:
                res = subprocess.run(command_for(cfg, n), capture_output=True, text=True,
                                        check=True, timeout=TIMEOUT_S)
            except subprocess.TimeoutExpired:
                timed_out = True
                add_row(n, cfg, rep, warm, "TIMEOUT")
                print(f"    [Timeout] n={n}, rep={rep}: exceeded {TIMEOUT_S:g} s")
                break
            except subprocess.CalledProcessError as e:
                add_row(n, cfg, rep, warm, f"ERROR_EXIT_{e.returncode}")
                print(f"    [Error] n={n}, rep={rep}: exit code {e.returncode} {e.stderr.strip()[:120]}")
                continue
            except Exception as e:
                add_row(n, cfg, rep, warm, "ERROR")
                print(f"    [Error] n={n}, rep={rep}: {e}")
                continue

            r = parse_output(cfg, res.stdout)
            if r["time"] is None or r["chk"] is None:
                add_row(n, cfg, rep, warm, "PARSE_ERROR", r)
                print(f"    [Parse error] n={n}, rep={rep}: {res.stdout.strip()[:150]}")
                continue

            key = (n, cfg["p"])
            ref = reference_checksums.setdefault(key, r["chk"])
            if abs(ref - r["chk"]) > 1e-9 * max(1.0, abs(ref)):
                status = "CHECKSUM_MISMATCH"
                checksum_problems.append((label, n, rep, r["chk"], ref))
                print(f"    [CHECKSUM MISMATCH] {label} n={n}: {r['chk']} vs reference {ref}")
            else:
                status = "OK"
            add_row(n, cfg, rep, warm, status, r)
            if status == "OK" and rep > 0:
                measured.append(r)

        if timed_out:
            failed_size = n
            timeouts.append((label, n))
            continue

        if measured:
            t = np.array([m["time"] for m in measured])
            med, q25, q75 = float(np.median(t)), float(np.percentile(t, 25)), float(np.percentile(t, 75))
            conv_med = float(np.median([m["conv"] for m in measured]))
            mem = max(m["mem"] for m in measured if m["mem"] is not None) if any(m["mem"] is not None for m in measured) else ""
            summary_data[label]["sizes"].append(n)
            summary_data[label]["median"].append(med)
            summary_data[label]["q25"].append(q25)
            summary_data[label]["q75"].append(q75)
            summary_rows.append({"Size": n, "Method": label, "BlockSize": cfg["block"] or "", "Sparsity": cfg["p"],
                                    "MeasuredRuns": len(measured), "MedianSeconds": f"{med:.6f}",
                                    "Q25Seconds": f"{q25:.6f}", "Q75Seconds": f"{q75:.6f}",
                                    "IQRSeconds": f"{q75 - q25:.6f}", "MedianConvSeconds": f"{conv_med:.6f}",
                                    "PeakMemoryKB": mem})
            print(f"  n = {n:4d} | median = {med:.6f} s | IQR = {q75 - q25:.6f} s | runs = {len(measured)} | peak = {mem} KB")
        else:
            print(f"  n = {n:4d} | no valid measurements")

os.makedirs(results_dir, exist_ok=True)

raw_path = os.path.join(results_dir, "raw_data_detailed.csv")
with open(raw_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(raw_rows)
print(f"\nRaw runs saved in '{raw_path}' ({len(raw_rows)} rows)")

sum_path = os.path.join(results_dir, "summary.csv")
with open(sum_path, "w", encoding="utf-8", newline="") as f:
    cols = ["Size", "Method", "BlockSize", "Sparsity", "MeasuredRuns", "MedianSeconds", "Q25Seconds",
            "Q75Seconds", "IQRSeconds", "MedianConvSeconds", "PeakMemoryKB"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(summary_rows)
print(f"Summary saved in '{sum_path}'")

if checksum_problems:
    print(f"\n!! {len(checksum_problems)} run(s) disagreed with the reference checksum (see Status column).")

fig, ax = plt.subplots(figsize=(12, 7))
colors = plt.cm.tab20(np.linspace(0, 1, 20))
for idx, (label, dat) in enumerate(summary_data.items()):
    if dat["sizes"]:
        meds, q25s, q75s = (np.array(dat[k]) for k in ("median", "q25", "q75"))
        style = "-" if label.startswith("Sparse CSR") else "--"   # solid = sparse, dashed = dense
        ax.errorbar(dat["sizes"], meds, yerr=[meds - q25s, q75s - meds], color=colors[idx % 20],
                    marker="o", linestyle=style, linewidth=1.8, capsize=3, label=label)
ax.set_yscale("log")
ax.set_xlabel("Matrix size (n)", fontsize=12)
ax.set_ylabel("Multiplication time, median (s, log scale)", fontsize=12)
ax.set_title("Comparative performance (median and Q25-Q75)", fontsize=14, fontweight="bold")
ax.legend(fontsize=8, loc="upper left")
ax.grid(True, which="both", linestyle="--", alpha=0.6)
if timeouts:
    note = "Timeout (> %g s, not plotted): " % TIMEOUT_S + "; ".join(f"{l} at n={n}" for l, n in timeouts)
    fig.text(0.01, 0.005, note, fontsize=8, color="firebrick", ha="left", va="bottom")
plot_path = os.path.join(results_dir, "performance_plot_robust.png")
fig.savefig(plot_path, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Plot saved in '{plot_path}'")