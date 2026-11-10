import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

results_dir = "results"
raw_path = os.path.join(results_dir, "raw_data_detailed.csv")

if not os.path.exists(raw_path):
    print(f"Raw data file {raw_path} not found. Run benchmark.py first.")
    exit(1)

df = pd.read_csv(raw_path)

df_clean = df[(df["IsWarmup"] == "No") & (df["Status"] == "OK")].copy()
df_clean["TimeSeconds"] = df_clean["TimeSeconds"].astype(float)
df_clean["PeakMemoryKB"] = df_clean["PeakMemoryKB"].astype(float)

grouped = df_clean.groupby(["Size", "Build", "Method", "Variant", "BlockSize", "RequestedThreads"]).agg(
    MeasuredRuns=("TimeSeconds", "count"),
    MedianTime=("TimeSeconds", "median"),
    Q25Time=("TimeSeconds", lambda x: np.percentile(x, 25)),
    Q75Time=("TimeSeconds", lambda x: np.percentile(x, 75)),
    PeakMemoryKB=("PeakMemoryKB", "max")
).reset_index()

grouped["IQRTime"] = grouped["Q75Time"] - grouped["Q25Time"]

seq_refs = grouped[grouped["Build"] == "seq"].set_index(["Size", "Variant"])["MedianTime"].to_dict()

def calc_speedup(row):
    seq_t = seq_refs.get((row["Size"], row["Variant"]))
    if seq_t and row["MedianTime"] > 0:
        return seq_t / row["MedianTime"]
    return np.nan

grouped["Speedup"] = grouped.apply(calc_speedup, axis=1)
grouped["Efficiency"] = grouped["Speedup"] / grouped["RequestedThreads"]

summary_path = os.path.join(results_dir, "summary.csv")
grouped.to_csv(summary_path, index=False)
print(f"Summary data saved to '{summary_path}'.")

fig, ax = plt.subplots(figsize=(10, 6))
df_large = grouped[grouped["Size"] == 2000]

for variant in ["ikj", "tile"]:
    sub = df_large[df_large["Variant"] == variant].sort_values("RequestedThreads")
    label_name = "Loop Reordering (ikj)" if variant == "ikj" else "Cache Tiling (B=64)"
    ax.plot(sub["RequestedThreads"], sub["MedianTime"], marker="o", linewidth=2, label=label_name)

ax.set_xlabel("Thread Count (p)", fontsize=12)
ax.set_ylabel("Median Runtime (seconds)", fontsize=12)
ax.set_title("Parallel Scaling Performance at n = 2000", fontsize=14, fontweight="bold")
ax.grid(True, linestyle="--", alpha=0.6)
ax.legend(fontsize=10)
fig.savefig(os.path.join(results_dir, "scaling_n2000.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
sub_omp = grouped[(grouped["Size"] == 2000) & (grouped["Build"] == "omp")]

for variant in ["ikj", "tile"]:
    sub = sub_omp[sub_omp["Variant"] == variant].sort_values("RequestedThreads")
    label_name = "ikj" if variant == "ikj" else "Tile B=64"
    ax1.plot(sub["RequestedThreads"], sub["Speedup"], marker="s", linewidth=2, label=f"Speedup {label_name}")
    ax2.plot(sub["RequestedThreads"], sub["Efficiency"], marker="^", linewidth=2, label=f"Efficiency {label_name}")

threads_arr = np.array([1, 2, 3, 4, 6, 8])
ax1.plot(threads_arr, threads_arr, 'k--', label="Ideal Linear Speedup", alpha=0.7)
ax1.axvline(x=2, color='gray', linestyle=':', label="Physical Cores (2)")
ax1.axvline(x=4, color='red', linestyle=':', label="Logical Threads SMT (4)")

ax1.set_xlabel("Thread Count (p)")
ax1.set_ylabel("Speedup S(p)")
ax1.set_title("Speedup vs Threads (n=2000)")
ax1.grid(True, linestyle="--", alpha=0.6)
ax1.legend()

ax2.axhline(y=1.0, color='k--', label="Ideal Efficiency (1.0)", alpha=0.7)
ax2.axvline(x=2, color='gray', linestyle=':', label="Physical Cores (2)")
ax2.axvline(x=4, color='red', linestyle=':', label="Logical Threads SMT (4)")
ax2.set_xlabel("Thread Count (p)")
ax2.set_ylabel("Efficiency E(p)")
ax2.set_title("Efficiency vs Threads (n=2000)")
ax2.grid(True, linestyle="--", alpha=0.6)
ax2.legend()

fig.savefig(os.path.join(results_dir, "speedup_efficiency_n2000.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

print("Report plots generated successfully.")