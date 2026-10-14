#!/usr/bin/env python3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bench_common as bc

LANGS = ["c", "java", "python"]
RTOL = ATOL = 1e-10
X_RTOL = X_ATOL = 1e-12


class MatMulTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        problems = bc.executables_missing()
        if problems:
            raise unittest.SkipTest("Build first (python scripts/build.py): " + "; ".join(problems))
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_lang(self, lang, a, b):
        n = a.shape[0]
        pa, pb, pc = self.dir / "A.bin", self.dir / "B.bin", self.dir / "C.bin"
        np.ascontiguousarray(a, dtype="<f8").tofile(pa)
        np.ascontiguousarray(b, dtype="<f8").tofile(pb)
        if pc.exists():
            pc.unlink()
        cmd = bc.command(lang, pa, pb, n, 0, 1, pc)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, f"{lang} failed:\n{r.stderr}")
        parsed = bc.parse_output(r.stdout)
        self.assertEqual(len(parsed["reps"]), 1)
        c = np.fromfile(pc, dtype="<f8").reshape(n, n)
        self.assertAlmostEqual(parsed["checksum"], float(c.sum()), delta=1e-9 * max(1.0, abs(float(c.sum()))))
        return c

    def test_known_2x2(self):
        a = np.array([[1, 2], [3, 4]], dtype=float)
        b = np.array([[5, 6], [7, 8]], dtype=float)
        expected = np.array([[19, 22], [43, 50]], dtype=float)
        for lang in LANGS:
            with self.subTest(lang=lang):
                np.testing.assert_array_equal(self.run_lang(lang, a, b), expected)

    def test_known_3x3_non_symmetric(self):
        a = np.array([[2, 0, 1], [1, 3, 2], [0, 4, 5]], dtype=float)
        b = np.array([[1, 2, 0], [0, 1, 3], [4, 0, 1]], dtype=float)
        expected = np.array([[6, 4, 1], [9, 5, 11], [20, 4, 17]], dtype=float)
        for lang in LANGS:
            with self.subTest(lang=lang):
                np.testing.assert_array_equal(self.run_lang(lang, a, b), expected)

    def test_size_one(self):
        a, b = np.array([[3.5]]), np.array([[-2.0]])
        for lang in LANGS:
            with self.subTest(lang=lang):
                np.testing.assert_array_equal(self.run_lang(lang, a, b), np.array([[-7.0]]))

    def test_identity(self):
        rng = np.random.default_rng(1)
        n = 17
        m, eye = rng.random((n, n)), np.eye(n)
        for lang in LANGS:
            with self.subTest(lang=lang, case="A*I"):
                np.testing.assert_array_equal(self.run_lang(lang, m, eye), m)
            with self.subTest(lang=lang, case="I*B"):
                np.testing.assert_array_equal(self.run_lang(lang, eye, m), m)

    def test_zero(self):
        rng = np.random.default_rng(2)
        n = 11
        m, z = rng.random((n, n)), np.zeros((n, n))
        for lang in LANGS:
            with self.subTest(lang=lang):
                np.testing.assert_array_equal(self.run_lang(lang, m, z), z)
                np.testing.assert_array_equal(self.run_lang(lang, z, m), z)

    def test_integer_valued_exact(self):
        rng = np.random.default_rng(3)
        n = 24
        a = rng.integers(-9, 10, (n, n)).astype(float)
        b = rng.integers(-9, 10, (n, n)).astype(float)
        expected = (a.astype(np.int64) @ b.astype(np.int64)).astype(float)
        for lang in LANGS:
            with self.subTest(lang=lang):
                np.testing.assert_array_equal(self.run_lang(lang, a, b), expected)

    def test_random_vs_numpy_and_between_languages(self):
        for n in (2, 3, 7, 16, 33, 64):
            rng = np.random.default_rng(100 + n)
            a, b = rng.random((n, n)), rng.random((n, n))
            ref = a @ b
            results = {}
            for lang in LANGS:
                with self.subTest(lang=lang, n=n):
                    results[lang] = self.run_lang(lang, a, b)
                    np.testing.assert_allclose(results[lang], ref, rtol=RTOL, atol=ATOL)
            for other in ("java", "python"):
                with self.subTest(pair=f"c-vs-{other}", n=n):
                    np.testing.assert_allclose(results[other], results["c"], rtol=X_RTOL, atol=X_ATOL)

    def test_wrong_input_size_is_rejected(self):
        pa, pb = self.dir / "bad_A.bin", self.dir / "bad_B.bin"
        np.zeros(10, dtype="<f8").tofile(pa)  # 10 doubles, but n=4 needs 16
        np.zeros(16, dtype="<f8").tofile(pb)
        for lang in LANGS:
            with self.subTest(lang=lang):
                r = subprocess.run(bc.command(lang, pa, pb, 4, 0, 1), capture_output=True, text=True, timeout=60)
                self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
