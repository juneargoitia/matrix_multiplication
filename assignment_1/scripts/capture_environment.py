import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psutil

import bench_common as bc
import config


def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        lines = [l for l in (r.stdout + r.stderr).splitlines()
                 if l.strip() and not l.startswith("Picked up")]
        return "\n".join(lines).strip()
    except Exception as exc:
        return f"unavailable ({exc})"


def cpu_model():
    if sys.platform.startswith("win"):
        out = run(["powershell", "-NoProfile", "-Command",
                   "(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name) -join '; '"])
        if out and not out.startswith("unavailable"):
            return out
    elif sys.platform.startswith("linux"):
        try:
            for line in open("/proc/cpuinfo"):
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
    elif sys.platform == "darwin":
        return run(["sysctl", "-n", "machdep.cpu.brand_string"])
    return platform.processor() or "unknown"


def lib_version(name):
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "unknown")
    except Exception:
        return "not installed"


def capture():
    freq = psutil.cpu_freq()
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    cc = bc.find_cc()
    javac = bc.find_java("javac")
    java = bc.find_java()
    env = {
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "os": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_processors": psutil.cpu_count(logical=True),
        "cpu_max_mhz_reported": round(freq.max, 1) if freq and freq.max else None,
        "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 2),
        "power_plan": run(["powercfg", "/getactivescheme"]) if sys.platform.startswith("win") else "n/a",
        "plugged_in": None if battery is None else bool(battery.power_plugged),
        "python_runner": f"{platform.python_implementation()} {platform.python_version()}",
        "python_executable": sys.executable,
        "numpy": lib_version("numpy"),
        "pandas": lib_version("pandas"),
        "matplotlib": lib_version("matplotlib"),
        "psutil": psutil.__version__,
        "c_compiler": run([cc, "--version"]).splitlines()[0] if cc else "not found",
        "c_flags": " ".join(config.CFLAGS),
        "javac": run([javac, "-version"]) if javac else "not found",
        "java_runtime": run([java, "-version"]) if java else "not found",
        "java_options": " ".join(config.JAVA_OPTS),
        "settings": {
            "seed": config.SEED, "dtype": config.DTYPE, "value_range": config.VALUE_RANGE,
            "sizes": config.SIZES, "reps": config.REPS, "warmup": config.WARMUP,
            "costly_python": {"min_n": config.COSTLY_PYTHON_MIN_N,
                              "warmup": config.COSTLY_PYTHON_WARMUP,
                              "reps": config.COSTLY_PYTHON_REPS},
            "timeout_s": config.TIMEOUT_S, "mem_budget_gb": config.MEM_BUDGET_GB,
        },
    }
    return env


def write(env, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    lines = ["# Experimental environment", ""]
    for k, v in env.items():
        if k == "settings":
            continue
        lines.append(f"- **{k}**: {str(v).replace(chr(10), ' / ')}")
    lines += ["", "## Settings", "", "```json", json.dumps(env["settings"], indent=2), "```", ""]
    (out_dir / "environment.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    out = config.RESULTS_DIR
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    env = capture()
    write(env, out)
    print(json.dumps({k: v for k, v in env.items() if k != "settings"}, indent=2))
    print(f"\nWritten to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())