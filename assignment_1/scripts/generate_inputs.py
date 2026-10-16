#!/usr/bin/env python3
import argparse
import csv
import hashlib
import sys
from pathlib import Path

import numpy as np

import config


def path_for(tag, n, data_dir=config.DATA_DIR):
    return Path(data_dir) / f"{tag}_n{n}.bin"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(n, seed=config.SEED, data_dir=config.DATA_DIR, force=False):
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, tag in enumerate(("A", "B")):
        p = path_for(tag, n, data_dir)
        if force or not p.exists() or p.stat().st_size != 8 * n * n:
            rng = np.random.default_rng([seed, n, idx])
            rng.random((n, n)).astype("<f8").tofile(p)
        rows.append((tag, n, seed, p.name, p.stat().st_size, sha256(p)))
    return rows


def write_manifest(rows, data_dir=config.DATA_DIR):
    with open(Path(data_dir) / "manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["matrix", "n", "seed", "file", "bytes", "sha256"])
        w.writerows(rows)


def ensure(sizes, force=False):
    manifest = {}
    mpath = config.DATA_DIR / "manifest.csv"
    if mpath.exists():
        with open(mpath, newline="") as f:
            for r in csv.DictReader(f):
                manifest[(r["matrix"], int(r["n"]))] = (
                    r["matrix"], int(r["n"]), int(r["seed"]), r["file"], int(r["bytes"]), r["sha256"])
    for n in sizes:
        for row in generate(n, force=force):
            manifest[(row[0], row[1])] = row
    write_manifest([manifest[k] for k in sorted(manifest, key=lambda k: (k[1], k[0]))])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", default=config.SIZES)
    ap.add_argument("--force", action="store_true", help="regenerate even if files exist")
    args = ap.parse_args()
    ensure(args.sizes, force=args.force)
    print(f"Inputs for sizes {args.sizes} are in {config.DATA_DIR} (manifest.csv updated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
