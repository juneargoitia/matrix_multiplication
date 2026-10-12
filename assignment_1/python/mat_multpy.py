import array
import gc
import os
import platform
import sys
import time


def read_matrix(path, n):
    rows = []
    with open(path, "rb") as f:
        for _ in range(n):
            row = array.array("d")
            row.fromfile(f, n)
            if sys.byteorder == "big":
                row.byteswap()
            rows.append(row.tolist())
        if f.read(1):
            raise ValueError(f"{path}: file is longer than {n * n} doubles")
    return rows


def write_matrix(path, rows):
    with open(path, "wb") as f:
        for row in rows:
            r = array.array("d", row)
            if sys.byteorder == "big":
                r.byteswap()
            r.tofile(f)


def matmul(a, b, c, n):
    for i in range(n):
        ai = a[i]
        ci = c[i]
        for j in range(n):
            s = 0.0
            for k in range(n):
                s += ai[k] * b[k][j]
            ci[j] = s


def emit(line):
    print(line, flush=True)


def main(argv):
    if len(argv) not in (6, 7):
        print("usage: matmul_basic.py A.bin B.bin n warmup reps [out.bin]", file=sys.stderr)
        return 2
    path_a, path_b = argv[1], argv[2]
    n, warmup, reps = int(argv[3]), int(argv[4]), int(argv[5])
    if n < 1 or warmup < 0 or reps < 1:
        print("invalid n/warmup/reps", file=sys.stderr)
        return 2

    a = read_matrix(path_a, n)
    b = read_matrix(path_b, n)
    c = [[0.0] * n for _ in range(n)]

    emit("INFO,lang,python")
    emit(f"INFO,python_version,{platform.python_implementation()} {platform.python_version()}")
    emit(f"INFO,n,{n}")

    gc.collect()
    gc.disable()
    for w in range(warmup):
        t0 = time.perf_counter()
        matmul(a, b, c, n)
        t1 = time.perf_counter()
        emit(f"WARMUP,{w},{t1 - t0:.9f}")
    for r in range(reps):
        t0 = time.perf_counter()
        matmul(a, b, c, n)
        t1 = time.perf_counter()
        emit(f"REP,{r},{t1 - t0:.9f}")
    gc.enable()

    checksum = 0.0
    for row in c:
        for x in row:
            checksum += x
    emit(f"CHECKSUM,{checksum!r}")

    if len(argv) == 7:
        write_matrix(argv[6], c)
        
    if os.environ.get("MATMUL_HOLD"):
        emit("DONE")
        sys.stdin.read()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
