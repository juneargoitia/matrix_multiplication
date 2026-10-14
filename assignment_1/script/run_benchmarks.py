#!/usr/bin/env python3
import argparse
import csv
import os
import shlex
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil

import capture_environment
import config
import generate_inputs
from bench_common import command, executables_missing, parse_output

RAW_FIELDS = ["run_id", "lang", "n", "dtype", "phase", "repetition", "seconds"]
RUN_FIELDS = [
    "run_id", "lang", "n", "dtype", "status", "warmup_requested", "reps_requested", "reps_completed",
    "peak_mem_bytes", "mem_metric", "theoretical_array_bytes", "java_heap_after_alloc_bytes",
    "checksum", "checksum_ref", "checksum_ok", "process_wall_s", "timeout_s", "command",
    "started_utc", "note",
]
MEM_METRIC = "peak resident set (Linux VmHWM / Windows PeakWorkingSetSize), whole process"


def sample_peak(proc):
    try:
        if sys.platform.startswith("linux"):
            with open(f"/proc/{proc.pid}/status") as f:
                for line in f:
                    if line.startswith("VmHWM:"):
                        return int(line.split()[1]) * 1024
        info = proc.memory_info()
        return int(getattr(info, "peak_wset", info.rss))
    except (psutil.Error, OSError, ValueError):
        return 0


def kill_tree(proc):
    try:
        for child in proc.children(recursive=True):
            child.kill()
        proc.kill()
    except psutil.Error:
        pass


def run_one(cmd, timeout_s):
    env = dict(os.environ, MATMUL_HOLD="1")
    proc = psutil.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, env=env)
    out_lines, err_lines, done = [], [], threading.Event()

    def pump(stream, sink, is_stdout):
        for line in stream:
            sink.append(line)
            if is_stdout and line.startswith("DONE"):
                done.set()

    threads = [threading.Thread(target=pump, args=(proc.stdout, out_lines, True), daemon=True),
               threading.Thread(target=pump, args=(proc.stderr, err_lines, False), daemon=True)]
    for t in threads:
        t.start()

    t0 = time.perf_counter()
    peak, status = 0, "ok"
    while True:
        if done.is_set():
            peak = max(peak, sample_peak(proc))  # final peak, process is still alive
            break
        try:
            proc.wait(timeout=0.005)
            break  # exited without DONE (error)
        except psutil.TimeoutExpired:
            pass
        peak = max(peak, sample_peak(proc))
        if time.perf_counter() - t0 > timeout_s:
            status = "timeout"
            kill_tree(proc)
            break
    wall = time.perf_counter() - t0
    try:
        proc.stdin.close()  # releases the held process
    except OSError:
        pass
    try:
        proc.wait(timeout=30)
    except psutil.TimeoutExpired:
        kill_tree(proc)
        proc.wait()
    for t in threads:
        t.join(timeout=5)
    return status, proc.returncode, "".join(out_lines), "".join(err_lines), peak, wall


def reference_checksums(sizes):
    ref = {}
    for n in sizes:
        a = np.fromfile(generate_inputs.path_for("A", n), dtype="<f8").reshape(n, n)
        b = np.fromfile(generate_inputs.path_for("B", n), dtype="<f8").reshape(n, n)
        ref[n] = float((a @ b).sum())
    return ref


def fmt_s(x):
    return f"{x:.4g} s"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", help=f"default: {config.SIZES}")
    ap.add_argument("--langs", nargs="+", choices=config.LANGS, default=config.LANGS)
    ap.add_argument("--quick", action="store_true",
                    help=f"smoke test: sizes {config.QUICK_SIZES}, results go to results/smoke/")
    ap.add_argument("--timeout", type=float, default=config.TIMEOUT_S, help="seconds per (language, n) run")
    ap.add_argument("--mem-budget-gb", type=float, default=config.MEM_BUDGET_GB)
    ap.add_argument("--out-dir", type=Path, help="default: results/ (results/smoke/ with --quick)")
    ap.add_argument("--overwrite", action="store_true", help="replace existing CSV files in out-dir")
    args = ap.parse_args()

    sizes = sorted(set(args.sizes or (config.QUICK_SIZES if args.quick else config.SIZES)))
    out_dir = args.out_dir or (config.RESULTS_DIR / "smoke" if args.quick else config.RESULTS_DIR)
    raw_path, runs_path = out_dir / "raw_measurements.csv", out_dir / "runs.csv"

    problems = executables_missing()
    if problems:
        print("Cannot start:\n  " + "\n  ".join(problems) + "\nRun: python scripts/build.py")
        return 1
    if (raw_path.exists() or runs_path.exists()) and not args.overwrite:
        print(f"{raw_path} or {runs_path} already exist. Use --overwrite to replace them "
              f"or --out-dir to write somewhere else.")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Capturing environment ...")
    capture_environment.write(capture_environment.capture(), out_dir)
    print("Generating / checking shared inputs ...")
    generate_inputs.ensure(sizes)
    print("Computing NumPy reference checksums ...")
    ref = reference_checksums(sizes)

    budget_bytes = args.mem_budget_gb * 1e9
    stopped = {}
    t_start = time.perf_counter()

    with open(raw_path, "w", newline="") as fraw, open(runs_path, "w", newline="") as fruns:
        raw_w, runs_w = csv.DictWriter(fraw, RAW_FIELDS), csv.DictWriter(fruns, RUN_FIELDS)
        raw_w.writeheader()
        runs_w.writeheader()

        for n in sizes:
            a_path, b_path = generate_inputs.path_for("A", n), generate_inputs.path_for("B", n)
            for lang in args.langs:
                run_id = f"{lang}_n{n}"
                warmup, reps = config.protocol(lang, n)
                row = {
                    "run_id": run_id, "lang": lang, "n": n, "dtype": config.DTYPE,
                    "warmup_requested": warmup, "reps_requested": reps, "reps_completed": 0,
                    "mem_metric": MEM_METRIC, "theoretical_array_bytes": 24 * n * n,
                    "timeout_s": args.timeout, "checksum_ref": ref[n],
                    "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
                if lang in stopped:
                    row.update(status=f"skipped_after_{stopped[lang]}",
                               note=f"not run: smaller size already ended with {stopped[lang]}")
                    runs_w.writerow(row); fruns.flush()
                    print(f"n={n:<5} {lang:<7} skipped (earlier {stopped[lang]})")
                    continue
                if config.planned_bytes(lang, n) > budget_bytes:
                    row.update(status="skipped_memory_budget",
                               note=f"planning estimate {config.planned_bytes(lang, n)/1e9:.2f} GB "
                                    f"> budget {args.mem_budget_gb} GB")
                    runs_w.writerow(row); fruns.flush()
                    print(f"n={n:<5} {lang:<7} skipped (memory budget)")
                    continue

                cmd = command(lang, a_path, b_path, n, warmup, reps)
                row["command"] = shlex.join(cmd) if hasattr(shlex, "join") else " ".join(cmd)
                status, rc, out, err, peak, wall = run_one(cmd, args.timeout)
                parsed = parse_output(out)

                note = ""
                if status == "ok" and rc != 0:
                    text = err + out
                    status = "memory_failure" if ("MemoryError" in text or "OutOfMemoryError" in text
                                                  or "allocation failed" in text) else "error"
                    note = err.strip()[-500:]
                elif status == "timeout":
                    note = f"killed after {args.timeout:.0f} s; {len(parsed['reps'])} measured reps finished"
                elif len(parsed["reps"]) != reps:
                    status, note = "error", f"expected {reps} reps, got {len(parsed['reps'])}"

                checksum_ok = ""
                if status == "ok":
                    if parsed["checksum"] is None:
                        status, note = "error", "no checksum printed"
                    else:
                        err_rel = abs(parsed["checksum"] - ref[n]) / abs(ref[n])
                        checksum_ok = err_rel <= config.checksum_rtol(n)
                        if not checksum_ok:
                            status, note = "wrong_result", f"checksum relative error {err_rel:.3e}"

                for phase, vals in (("warmup", parsed["warmup"]), ("measured", parsed["reps"])):
                    for i, secs in enumerate(vals):
                        raw_w.writerow({"run_id": run_id, "lang": lang, "n": n, "dtype": config.DTYPE,
                                        "phase": phase, "repetition": i, "seconds": f"{secs:.9f}"})
                fraw.flush()

                row.update(status=status, reps_completed=len(parsed["reps"]),
                           peak_mem_bytes=peak or "", java_heap_after_alloc_bytes=parsed["heap_after_alloc"] or "",
                           checksum=parsed["checksum"] if parsed["checksum"] is not None else "",
                           checksum_ok=checksum_ok, process_wall_s=f"{wall:.3f}", note=note)
                runs_w.writerow(row); fruns.flush()

                if status in ("timeout", "memory_failure", "error", "wrong_result"):
                    if status != "wrong_result":
                        stopped[lang] = status
                med = f"median {fmt_s(statistics.median(parsed['reps']))}" if parsed["reps"] else "no samples"
                print(f"n={n:<5} {lang:<7} {status:<15} {med:<22} reps={len(parsed['reps'])}/{reps} "
                      f"peak={peak/1e6:8.1f} MB  wall={wall:7.1f} s")

    print(f"\nDone in {(time.perf_counter() - t_start)/60:.1f} min. Results in {out_dir}")
    print("Next: python scripts/analyze.py" + (f" --results {out_dir}" if args.quick else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
