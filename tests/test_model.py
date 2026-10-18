"""Independent examples and input boundaries for the current lap model."""
import subprocess
import sys
import unittest
from pathlib import Path

from main import lap_time


class LapTests(unittest.TestCase):
    def test_base_example(self):
        self.assertEqual(lap_time(90), 90)

    def test_inclusive_base_boundaries(self):
        for value in (30, 200):
            with self.subTest(value=value):
                self.assertEqual(lap_time(value), value)

    def test_fractional_base(self):
        self.assertEqual(lap_time(92.451), 92.451)

    def test_invalid_base_range(self):
        for value in (-1, 0, 29.999, 200.001, 10 ** 400):
            with self.subTest(value=value), self.assertRaises(ValueError):
                lap_time(value)

    def test_nonfinite_base(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                lap_time(value)

    def test_wrong_base_type(self):
        for value in (True, False, "90", None, [90]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                lap_time(value)

    def test_cli_output(self):
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run([sys.executable, "main.py", "--base", "90"],
                             cwd=root, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertIn("90.000 s", run.stdout)

    def test_cli_rejects_invalid_input_without_traceback(self):
        root = Path(__file__).resolve().parents[1]
        for value in ("-1", "nan", "not-a-time"):
            with self.subTest(value=value):
                run = subprocess.run([sys.executable, "main.py", "--base", value],
                                     cwd=root, text=True, capture_output=True)
                self.assertEqual(run.returncode, 2)
                self.assertIn("error:", run.stderr)
                self.assertNotIn("Traceback", run.stderr)
