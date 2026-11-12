import argparse
import os
 
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--results-dir", default="results")
parser.add_argument("--physical", type=int, default=None, help="physical cores of the machine")
parser.add_argument("--logical", type=int, default=None, help="logical processors of the machine")
parser.add_argument("--main-size", type=int, default=None, help="size used in the single-size figures (default: largest)")
args = parser.parse_args()

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
results_dir = args.results_dir
raw_path = os.path.join(results_dir, "raw_data_detailed.csv")
if not os.path.exists(raw_path):
    raise SystemExit(f"{raw_path} not found. Run scripts/benchmark.py first.")

logical, physical = args.logical, args.physical
try:
    import psutil
    logical = logical or psutil.cpu_count(logical=True)
    physical = physical or psutil.cpu_count(logical=False)
except ImportError:
    logical = logical or os.cpu_count()
if logical is None:
    raise SystemExit("Could not detect the logical processors: pass --logical N")
print(f"Topology used: physical cores = {physical}, logical processors = {logical}")

df = pd.read_csv(raw_path)
df["BlockSize"] = df["BlockSize"].fillna(0).astype(int)
problems = df[df["Status"] != "OK"]
if len(problems):
    print("Non-OK rows in the raw data (excluded from statistics):")
    print(problems["Status"].str.replace(r"_REQ\d+_ACT\d+", "", regex=True).value_counts().to_string())

ok = df[(df["IsWarmup"] == "No") & (df["Status"] == "OK")].copy()
ok["TimeSeconds"] = ok["TimeSeconds"].astype(float)
ok["PeakMemoryKB"] = pd.to_numeric(ok["PeakMemoryKB"], errors="coerce")
if ok.empty:
    raise SystemExit("No valid measured runs found.")

keys = ["Size", "Build", "Variant", "BlockSize", "RequestedThreads"]
g = ok.groupby(keys).agg(
    MeasuredRuns=("TimeSeconds", "count"),
    MedianTime=("TimeSeconds", "median"),
    Q25Time=("TimeSeconds", lambda x: np.percentile(x, 25)),
    Q75Time=("TimeSeconds", lambda x: np.percentile(x, 75)),
    MinTime=("TimeSeconds", "min"),
    MaxTime=("TimeSeconds", "max"),
    PeakMemoryKB=("PeakMemoryKB", "max"),
).reset_index()
g["IQRTime"] = g["Q75Time"] - g["Q25Time"]
g["RelIQR"] = g["IQRTime"] / g["MedianTime"]          # variability relative to the median

seq = g[g["Build"] == "seq"].set_index(["Size", "Variant"])["MedianTime"].to_dict()
g["SeqMedian"] = [seq.get((s, v), np.nan) for s, v in zip(g["Size"], g["Variant"])]
g["Speedup"] = g["SeqMedian"] / g["MedianTime"]
g["Efficiency"] = g["Speedup"] / g["RequestedThreads"]
g["Oversubscribed"] = g["RequestedThreads"] > logical
g["BeyondPhysical"] = (g["RequestedThreads"] > physical) if physical else False
g["Overhead1T"] = np.where((g["Build"] == "omp") & (g["RequestedThreads"] == 1), g["MedianTime"] / g["SeqMedian"] - 1.0, np.nan)
g["GFLOPS"] = 2.0 * g["Size"] ** 3 / g["MedianTime"] / 1e9
g.to_csv(os.path.join(results_dir, "summary.csv"), index=False)
print(f"summary.csv written ({len(g)} rows)")

omp = g[g["Build"] == "omp"]
sizes = sorted(g["Size"].unique())
main_size = args.main_size or max(sizes)
if main_size not in sizes:
    raise SystemExit(f"--main-size {main_size} has no data; available: {sizes}")
threads = sorted(omp["RequestedThreads"].unique())
VAR = {"ikj": "Loop reordering (ikj)", "tile": "Cache tiling (B=64)"}
COL = {"ikj": "#0072B2", "tile": "#D55E00"}      # colour-blind-safe pair; variants also differ by marker
MARK = {"ikj": "o", "tile": "s"}


def topology_lines(ax):
    if physical:
        ax.axvline(physical, color="gray", linestyle=":", linewidth=1.2, label=f"Physical cores ({physical})")
    ax.axvline(logical, color="firebrick", linestyle=":", linewidth=1.2, label=f"Logical processors ({logical})")

def style(ax, xlabel="Threads (p)", ylabel="", title=""):
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title, fontweight="bold")
    ax.set_xticks(threads); ax.grid(True, linestyle="--", alpha=0.5)


def line(ax, sub, ycol, v, label=None, yerr=None):
    """Solid line; points beyond the logical processors are hollow (oversubscribed)."""
    sub = sub.sort_values("RequestedThreads")
    x, y = sub["RequestedThreads"].to_numpy(), sub[ycol].to_numpy()
    if yerr is not None:
        ax.errorbar(x, y, yerr=yerr(sub), color=COL[v], linewidth=1.8, capsize=3, label=label or VAR[v], fmt="none")
    ax.plot(x, y, color=COL[v], linewidth=1.8, label=None if yerr is not None and label is None else (label or VAR[v]))
    over = sub["Oversubscribed"].to_numpy()
    ax.plot(x[~over], y[~over], MARK[v], color=COL[v], markersize=7)
    ax.plot(x[over], y[over], MARK[v], color=COL[v], markerfacecolor="white", markersize=7, markeredgewidth=1.6)


def iqr_err(sub):
    return [(sub["MedianTime"] - sub["Q25Time"]).clip(lower=0).to_numpy(),
            (sub["Q75Time"] - sub["MedianTime"]).clip(lower=0).to_numpy()]


def save(fig, name):
    fig.savefig(os.path.join(results_dir, name), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}")


print("Figures:")
main = omp[omp["Size"] == main_size]

# 1. runtime vs threads (main size)
fig, ax = plt.subplots(figsize=(8, 5.5))
for v in ("ikj", "tile"):
    sub = main[main["Variant"] == v]
    line(ax, sub, "MedianTime", v, yerr=iqr_err)
    s = g[(g["Build"] == "seq") & (g["Variant"] == v) & (g["Size"] == main_size)]
    if len(s):
        ax.axhline(s["MedianTime"].iloc[0], color=COL[v], linestyle="--", linewidth=1, alpha=0.7,
                    label=f"Sequential build, {VAR[v]}")
topology_lines(ax)
style(ax, ylabel="Median runtime (s)", title=f"Runtime vs threads, n = {main_size} (bars: Q25-Q75; hollow = oversubscribed)")
ax.legend(fontsize=8)
save(fig, "scaling_runtime.png")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.5))
for v in ("ikj", "tile"):
    sub = main[main["Variant"] == v]
    line(a1, sub, "Speedup", v)
    line(a2, sub, "Efficiency", v)
a1.plot(threads, threads, color="k", linestyle="--", alpha=0.6, label="Ideal S(p) = p")
a2.axhline(1.0, color="k", linestyle="--", alpha=0.6, label="Ideal E(p) = 1")
for a in (a1, a2):
    topology_lines(a)
style(a1, ylabel="Speedup S(p) = T_seq / T_p", title=f"Speedup, n = {main_size}")
style(a2, ylabel="Efficiency E(p) = S(p) / p", title=f"Efficiency, n = {main_size}")
a1.legend(fontsize=8); a2.legend(fontsize=8)
save(fig, "speedup_efficiency.png")

cmap = plt.cm.viridis(np.linspace(0.05, 0.9, max(len(sizes), 1)))
for ycol, ylab, fname in (("Speedup", "Speedup S(p)", "speedup_by_size.png"),
                            ("Efficiency", "Efficiency E(p)", "efficiency_by_size.png")):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    for ax, v in zip(axes, ("ikj", "tile")):
        for color, n in zip(cmap, sizes):
            sub = omp[(omp["Variant"] == v) & (omp["Size"] == n)].sort_values("RequestedThreads")
            if sub.empty:
                continue
            ax.plot(sub["RequestedThreads"], sub[ycol], "o-", color=color, linewidth=1.5, markersize=5, label=f"n = {n}")
        if ycol == "Speedup":
            ax.plot(threads, threads, color="k", linestyle="--", alpha=0.6, label="Ideal S(p) = p")
        else:
            ax.axhline(1.0, color="k", linestyle="--", alpha=0.6, label="Ideal E(p) = 1")
        topology_lines(ax)
        style(ax, ylabel=ylab, title=VAR[v])
        ax.legend(fontsize=7, ncol=2)
    save(fig, fname)

ov = omp[omp["RequestedThreads"] == 1]
if not ov.empty:
    fig, ax = plt.subplots(figsize=(9, 5))
    w = 0.38
    xs = np.arange(len(sizes))
    for off, v in ((-w / 2, "ikj"), (w / 2, "tile")):
        vals = [ov[(ov["Size"] == n) & (ov["Variant"] == v)]["Overhead1T"].mean() * 100 for n in sizes]
        ax.bar(xs + off, vals, w, color=COL[v], label=VAR[v])
    ax.axhline(0, color="k", linewidth=0.8)
    ax.set_xticks(xs); ax.set_xticklabels([str(n) for n in sizes])
    ax.set_xlabel("Matrix size n"); ax.set_ylabel("T(omp, p=1) / T(seq) - 1  (%)")
    ax.set_title("Overhead of the OpenMP build with a single thread", fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5); ax.legend(fontsize=8)
    save(fig, "overhead_1thread.png")

os.makedirs(os.path.join(results_dir, "tables"), exist_ok=True)


def write_table(df_, name, caption, fmt):
    """CSV + a hand-written LaTeX tabular (no jinja2 dependency)."""
    df_.to_csv(os.path.join(results_dir, "tables", name + ".csv"), index=False)
    cols = list(df_.columns)
    lines = ["\\begin{table}[ht]", "\\centering", "\\small",
             "\\begin{tabular}{" + "r" * len(cols) + "}", "\\hline",
                " & ".join(c.replace("_", "\\_") for c in cols) + " \\\\", "\\hline"]
    for _, r in df_.iterrows():
        lines.append(" & ".join("--" if pd.isna(r[c]) else fmt.get(c, str)(r[c]) for c in cols) + " \\\\")
    lines += ["\\hline", "\\end{tabular}", f"\\caption{{{caption}}}", f"\\label{{tab:{name}}}", "\\end{table}"]
    with open(os.path.join(results_dir, "tables", name + ".tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


f3 = lambda x: f"{x:.3f}"
f4 = lambda x: f"{x:.4f}"
f1 = lambda x: f"{x:.1f}"
for v in ("ikj", "tile"):
    t = g[(g["Variant"] == v) & (g["Size"] == main_size)].sort_values(["Build", "RequestedThreads"]).copy()
    t["Config"] = np.where(t["Build"] == "seq", "seq", "omp")
    t = t[["Config", "RequestedThreads", "MedianTime", "IQRTime", "RelIQR", "Speedup", "Efficiency", "PeakMemoryKB"]]
    t.columns = ["Build", "p", "Median_s", "IQR_s", "RelIQR", "S(p)", "E(p)", "PeakMem_KB"]
    write_table(t, f"results_{v}_n{main_size}",
                f"{VAR[v]}, n = {main_size}: median runtime, IQR, speedup, efficiency and peak memory.",
                {"Median_s": f4, "IQR_s": f4, "RelIQR": f3, "S(p)": f3, "E(p)": f3, "PeakMem_KB": lambda x: f"{x:.0f}"})

for ycol, name in (("Speedup", "speedup_all_sizes"), ("Efficiency", "efficiency_all_sizes")):
    for v in ("ikj", "tile"):
        t = omp[omp["Variant"] == v].pivot(index="Size", columns="RequestedThreads", values=ycol).reset_index()
        t.columns = ["n"] + [f"p={c}" for c in t.columns[1:]]
        write_table(t, f"{name}_{v}", f"{ycol} of {VAR[v]} for every size and thread count.",
                    {c: f3 for c in t.columns if c != "n"})

if not ov.empty:
    t = ov.pivot(index="Size", columns="Variant", values="Overhead1T").reset_index()
    t.columns = ["n"] + [f"overhead_{c}_%" for c in t.columns[1:]]
    for c in t.columns[1:]:
        t[c] = t[c] * 100
    write_table(t, "overhead_1thread", "Overhead of the OpenMP build with one thread relative to the sequential build.",
                {c: f1 for c in t.columns if c != "n"})

print("\nDiagnostics:")
sup = omp[omp["Efficiency"] > 1.05]
if len(sup):
    print("  Superlinear candidates (E > 1.05): explain them with evidence (cache, noise) or discard:")
    print(sup[["Size", "Variant", "RequestedThreads", "Speedup", "Efficiency", "RelIQR"]].to_string(index=False))
else:
    print("  No superlinear speedups (E > 1.05).")
noisy = g[g["RelIQR"] > 0.10]
print(f"  Configurations with IQR > 10% of the median: {len(noisy)} of {len(g)}")
if g["PeakMemoryKB"].fillna(0).max() == 0:
    print("  Peak memory is 0/NaN everywhere: memory is only measured on Windows (psapi).")
print("\nDone.")