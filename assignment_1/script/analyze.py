#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

STYLE = { 
    "c": ("#0072B2", "o", "C (gcc)"),
    "java": ("#E69F00", "s", "Java (JVM)"),
    "python": ("#009E73", "^", "Python (CPython)"),
}


def md_table(df, formats=None):
    formats = formats or {}
    if df.empty:
        return "Not enough data."
    df = df.astype(object)
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float) and np.isnan(v):
                cells.append("")
            elif c in formats and v != "":
                cells.append(format(v, formats[c]))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def load(results):
    raw = pd.read_csv(results / "raw_measurements.csv")
    runs = pd.read_csv(results / "runs.csv", encoding="latin-1")
    ok = runs[runs.status == "ok"]
    meas = raw[(raw.phase == "measured") & raw.run_id.isin(ok.run_id)]
    g = meas.groupby(["lang", "n"])["seconds"]
    st = g.agg(reps="count", median="median", min="min", max="max").reset_index()
    st["q1"] = g.quantile(0.25).values
    st["q3"] = g.quantile(0.75).values
    st["iqr"] = st.q3 - st.q1
    st = st.merge(
        ok[["lang", "n", "warmup_requested", "peak_mem_bytes", "java_heap_after_alloc_bytes",
            "theoretical_array_bytes"]], on=["lang", "n"], how="left")
    st["peak_mem_mb"] = st.peak_mem_bytes / 1e6
    st["ns_per_madd"] = st["median"] / st.n.astype(float) ** 3 * 1e9  # ns per multiply-add
    base = st.groupby("lang").peak_mem_mb.transform("first")  # smallest tested n per language
    st["mem_over_smallest_mb"] = st.peak_mem_mb - base
    return raw, runs, st.sort_values(["lang", "n"]).reset_index(drop=True)


def fig_runtime(st, out):
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for lang, (col, mk, label) in STYLE.items():
        d = st[st.lang == lang]
        if d.empty:
            continue
        yerr = np.vstack([d["median"] - d.q1, d.q3 - d["median"]])
        ax.errorbar(d.n, d["median"], yerr=yerr, color=col, marker=mk, capsize=3, label=label)
    anchor = st[st.n == st.n.max()].iloc[0] if not st.empty else None
    if anchor is not None:
        ns = np.array(sorted(st.n.unique()), dtype=float)
        ax.plot(ns, anchor["median"] * (ns / anchor.n) ** 3, "k:", lw=1,
                label=f"n³ reference (through {anchor.lang}, n={int(anchor.n)})")
    ax.set(xscale="log", yscale="log", xlabel="matrix size n (n × n, float64)",
           ylabel="kernel time per multiplication [s]",
           title="Runtime vs matrix size (median, bars = IQR)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "runtime_vs_n.png", dpi=150)
    plt.close(fig)


def fig_normalised(st, out):
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for lang, (col, mk, label) in STYLE.items():
        d = st[st.lang == lang]
        if not d.empty:
            ax.plot(d.n, d.ns_per_madd, color=col, marker=mk, label=label)
    ax.set(xscale="log", yscale="log", xlabel="matrix size n",
           ylabel="median time / n³ [ns per multiply-add]",
           title="Time per multiply-add (flat line = pure n³ scaling)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "time_per_madd_vs_n.png", dpi=150)
    plt.close(fig)


def fig_memory(st, out):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for lang, (col, mk, label) in STYLE.items():
        d = st[st.lang == lang].dropna(subset=["peak_mem_mb"])
        if d.empty:
            continue
        axes[0].plot(d.n, d.peak_mem_mb, color=col, marker=mk, label=label)
        grown = d[d.mem_over_smallest_mb > 0]  # the smallest size is the baseline itself (0)
        axes[1].plot(grown.n, grown.mem_over_smallest_mb, color=col, marker=mk, label=label)
    ns = np.array(sorted(st.n.unique()), dtype=float)
    for ax in axes:
        ax.plot(ns, 24 * ns**2 / 1e6, "k:", lw=1, label="3·8·n² bytes (raw arrays)")
        ax.set(xscale="log", yscale="log", xlabel="matrix size n")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
    axes[0].set(ylabel="peak resident memory of process [MB]", title="Peak process memory")
    axes[1].set(ylabel="peak memory − peak at smallest n [MB]",
                title="Growth over the smallest-size baseline (estimate)")
    fig.tight_layout()
    fig.savefig(out / "peak_memory_vs_n.png", dpi=150)
    plt.close(fig)


def exponents(st, min_n=100):
    rows = []
    for lang in STYLE:
        d = st[(st.lang == lang) & (st.n >= min_n)]
        if len(d) >= 3:
            slope, intercept = np.polyfit(np.log(d.n.astype(float)), np.log(d["median"]), 1)
            rows.append({"lang": lang, "sizes_used": f"n ≥ {min_n} ({len(d)} points)",
                         "fitted_exponent": slope})
    return pd.DataFrame(rows)


def ratios(st):
    p = st.pivot(index="n", columns="lang", values="median")
    out = pd.DataFrame(index=p.index)
    for num, den in (("java", "c"), ("python", "c"), ("python", "java")):
        if num in p and den in p:
            out[f"{num} / {den}"] = p[num] / p[den]
    return out.dropna(how="all").reset_index()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=config.RESULTS_DIR)
    args = ap.parse_args()
    res = args.results
    fig_dir = res / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    raw, runs, st = load(res)
    if st.empty:
        print("No successful runs to analyse.")
        return 1
    st.to_csv(res / "summary.csv", index=False)
    fig_runtime(st, fig_dir)
    fig_normalised(st, fig_dir)
    fig_memory(st, fig_dir)

    table = st[["lang", "n", "reps", "warmup_requested", "median", "iqr", "min", "max",
                "peak_mem_mb", "java_heap_after_alloc_bytes"]].copy()
    table["java_heap_after_alloc_bytes"] = table["java_heap_after_alloc_bytes"] / 1e6
    table = table.rename(columns={"warmup_requested": "warmup", "median": "median_s", "iqr": "iqr_s",
                                  "min": "min_s", "max": "max_s",
                                  "java_heap_after_alloc_bytes": "java_heap_MB"})
    fmt = {c: ".6g" for c in ("median_s", "iqr_s", "min_s", "max_s")}
    fmt.update(peak_mem_mb=".1f", java_heap_MB=".1f")

    problems = runs[runs.status != "ok"][["lang", "n", "status", "reps_completed", "timeout_s", "note"]]
    largest = st.groupby("lang").n.max().reset_index().rename(columns={"n": "largest_ok_n"})

    md = ["# Summary of measurements", "",
          "Times are kernel-only seconds per multiplication (median and IQR of measured repetitions, "
          "warm-up excluded). Memory is the peak resident set of the whole process (MB = 10^6 bytes).", "",
          "## Per-configuration results", "", md_table(table, fmt), "",
          "## Largest tested size that completed within the declared limits", "", md_table(largest), "",
          "## Fitted growth exponent (log-log slope of median time)", "",
          "A pure n³ algorithm gives 3; cache and runtime effects move the slope.", "",
          md_table(exponents(st), {"fitted_exponent": ".2f"}), "",
          "## Ratio of median times (language A / language B) at common sizes", "",
          md_table(ratios(st), {c: ".2f" for c in ratios(st).columns if c != "n"}), "",
          "## Runs that were not 'ok' (timeouts, failures, skipped sizes)", ""]
    md.append(md_table(problems) if not problems.empty else "None.")
    (res / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print((res / "summary.md").read_text(encoding="utf-8"))
    print(f"Figures written to {fig_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())