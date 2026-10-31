"""Independent examples and input boundaries for the current lap model."""
import subprocess
import sys
import unittest
from pathlib import Path

from main import lap_time, tyre_loss


class WearTests(unittest.TestCase):
    def test_fresh_tyres_have_no_degradation(self):
        for compound in "SMH":
            self.assertEqual(tyre_loss(compound, 0), 0)

    def test_linear_wear_and_life_boundary(self):
        self.assertAlmostEqual(tyre_loss("S", 1), 0.095)
        self.assertAlmostEqual(tyre_loss("S", 18), 1.710)
        self.assertAlmostEqual(tyre_loss("M", 28), 1.680)
        self.assertAlmostEqual(tyre_loss("H", 38), 1.406)

    def test_quadratic_cliff_independent_example(self):
        self.assertAlmostEqual(tyre_loss("S", 20), 1.972)
        self.assertAlmostEqual(lap_time(90, "S", 20), 91.972)

    def test_wear_increases_across_twenty_laps(self):
        losses = [tyre_loss("S", age) for age in range(21)]
        self.assertTrue(all(b > a for a, b in zip(losses, losses[1:])))

    def test_invalid_age(self):
        for age in (-1, 1001, 1.5, True, "1", None, 10 ** 400):
            with self.subTest(age=age), self.assertRaises(ValueError):
                tyre_loss("S", age)


class CompoundTests(unittest.TestCase):
    def test_offsets_against_hand_calculation(self):
        for compound, expected in (("S", 90.0), ("M", 90.48), ("H", 91.0)):
            with self.subTest(compound=compound):
                self.assertAlmostEqual(lap_time(90, compound), expected)

    def test_invalid_compounds(self):
        for compound in ("X", "soft", "", "s", None, True, ["S"]):
            with self.subTest(compound=compound), self.assertRaises(ValueError):
                lap_time(90, compound)

    def test_compound_does_not_relax_base_validation(self):
        with self.assertRaises(ValueError):
            lap_time(-1, "H")


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
