from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

SEED = 2026
DTYPE = "float64"
VALUE_RANGE = "uniform [0, 1)"
SIZES = [10, 50, 100, 200, 300, 500, 750, 1000, 1500, 2000]
QUICK_SIZES = [10, 50, 100, 200]

LANGS = ["c", "java", "python"]
CFLAGS = ["-O2", "-std=c11", "-ffp-contract=off", "-Wall", "-Wextra"]
JAVA_OPTS = ["-XX:+UseSerialGC", "-Xmx4g"]

REPS = 5
WARMUP = {"c": 1, "java": 3, "python": 1}
COSTLY_PYTHON_MIN_N = 500
COSTLY_PYTHON_WARMUP = 0
COSTLY_PYTHON_REPS = 3

TIMEOUT_S = 900
MEM_BUDGET_GB = 4.0
PLAN_BYTES_PER_ELEMENT = {"c": 24, "java": 24, "python": 96}

UNIT_ROUNDOFF = 1.1102230246251565e-16 


def protocol(lang, n):
    if lang == "python" and n >= COSTLY_PYTHON_MIN_N:
        return COSTLY_PYTHON_WARMUP, COSTLY_PYTHON_REPS
    return WARMUP[lang], REPS


def planned_bytes(lang, n):
    return PLAN_BYTES_PER_ELEMENT[lang] * n * n


def checksum_rtol(n):
    return 10.0 * (n * n + n) * UNIT_ROUNDOFF + 1e-12
