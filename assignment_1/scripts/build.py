#!/usr/bin/env python3
import argparse
import subprocess
import sys

import config
from bench_common import C_EXE, JAVA_OUT, ROOT, find_cc, find_java

C_HINT = (
    "No C compiler (gcc/clang) found on PATH.\n"
    "  Windows: install a MinGW-w64 gcc, for example\n"
    "    winget install BrechtSanders.WinLibs.POSIX.UCRT\n"
    "  or MSYS2 (https://www.msys2.org, then 'pacman -S mingw-w64-ucrt-x86_64-gcc' and add\n"
    "  C:\\msys64\\ucrt64\\bin to PATH). Open a NEW terminal and check with: gcc --version"
)
JAVA_HINT = (
    "'javac' not found. e.g. Temurin 21: https://adoptium.net\n"
    "Open a NEW terminal afterwards and check with: javac -version"
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cc", help="C compiler to use (default: $CC, gcc, then clang)")
    args = ap.parse_args()
    failed = False

    cc = find_cc(args.cc)
    if not cc:
        print(C_HINT)
        failed = True
    else:
        cmd = [cc] + config.CFLAGS + ["-o", str(C_EXE), str(ROOT / "c" / "matmul.c")]
        print("C   :", " ".join(cmd))
        if subprocess.run(cmd).returncode != 0:
            failed = True

    javac = find_java("javac")
    if not javac:
        print(JAVA_HINT)
        failed = True
    else:
        JAVA_OUT.mkdir(parents=True, exist_ok=True)
        cmd = [javac, "-d", str(JAVA_OUT), str(ROOT / "java" / "MatMul.java")]
        print("Java:", " ".join(cmd))
        if subprocess.run(cmd).returncode != 0:
            failed = True

    print("Build FAILED" if failed else "Build OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
