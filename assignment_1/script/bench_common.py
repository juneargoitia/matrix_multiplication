import os
import shutil
import sys
from pathlib import Path

import config

ROOT = config.ROOT
IS_WINDOWS = os.name == "nt"
C_EXE = ROOT / "c" / ("matmul_c.exe" if IS_WINDOWS else "matmul_c")
JAVA_OUT = ROOT / "java" / "out"
PY_SCRIPT = ROOT / "python" / "matmul_basic.py"


def find_java(tool="java"):
    home = os.environ.get("JAVA_HOME")
    if home:
        cand = Path(home) / "bin" / (tool + (".exe" if IS_WINDOWS else ""))
        if cand.exists():
            return str(cand)
    return shutil.which(tool)


def find_cc(preferred=None):
    return preferred or os.environ.get("CC") or shutil.which("gcc") or shutil.which("clang")


def executables_missing():
    problems = []
    if not C_EXE.exists():
        problems.append(f"C executable not found: {C_EXE}")
    if not (JAVA_OUT / "MatMul.class").exists():
        problems.append(f"Java class not found: {JAVA_OUT / 'MatMul.class'}")
    if find_java() is None:
        problems.append("'java' not found on PATH")
    if not PY_SCRIPT.exists():
        problems.append(f"Python script not found: {PY_SCRIPT}")
    return problems


def command(lang, a_path, b_path, n, warmup, reps, out_path=None):
    tail = [str(a_path), str(b_path), str(n), str(warmup), str(reps)]
    if out_path is not None:
        tail.append(str(out_path))
    if lang == "c":
        return [str(C_EXE)] + tail
    if lang == "java":
        return [find_java()] + list(config.JAVA_OPTS) + ["-cp", str(JAVA_OUT), "MatMul"] + tail
    if lang == "python":
        return [sys.executable, str(PY_SCRIPT)] + tail
    raise ValueError(f"unknown language {lang!r}")


def parse_output(text):
    result = {"info": {}, "warmup": [], "reps": [], "checksum": None, "heap_after_alloc": None}
    for line in text.splitlines():
        parts = line.strip().split(",", 2)
        tag = parts[0]
        try:
            if tag == "INFO" and len(parts) == 3:
                result["info"][parts[1]] = parts[2]
            elif tag == "WARMUP":
                result["warmup"].append(float(parts[2]))
            elif tag == "REP":
                result["reps"].append(float(parts[2]))
            elif tag == "CHECKSUM":
                result["checksum"] = float(parts[1])
            elif tag == "HEAP_USED_AFTER_ALLOC":
                result["heap_after_alloc"] = int(parts[1])
        except (ValueError, IndexError):
            continue
    return result
