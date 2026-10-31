"""Independent examples and input boundaries for the current lap model."""
import subprocess
import sys
import unittest
from pathlib import Path

from model import lap_time, tyre_loss, simulate, Strategy, compare


class RaceTests(unittest.TestCase):
    def test_ten_lap_total_against_independent_sum(self):
        self.assertAlmostEqual(simulate(90, 10).total, 904.275)

    def test_lap_age_and_cumulative_trace(self):
        result = simulate(90, 10)
        self.assertEqual([lap.number for lap in result.laps], list(range(1, 11)))
        self.assertEqual([lap.age for lap in result.laps], list(range(10)))
        self.assertAlmostEqual(result.laps[-1].time, 90.855)
        self.assertAlmostEqual(result.total, sum(lap.time for lap in result.laps))
        self.assertTrue(all(b.elapsed > a.elapsed for a, b in zip(result.laps, result.laps[1:])))

    def test_maximum_race_length(self):
        self.assertEqual(len(simulate(90, 100).laps), 100)

    def test_invalid_race_lengths(self):
        for laps in (0, 9, 101, -1, True, 10.0, "10", None):
            with self.subTest(laps=laps), self.assertRaises(ValueError):
                simulate(90, laps)

    def test_invalid_race_inputs(self):
        for base, compound in ((-1, "S"), (90, "X")):
            with self.subTest(base=base, compound=compound), self.assertRaises(ValueError):
                simulate(base, 10, Strategy((compound,)))

    def test_repeatable(self):
        self.assertEqual(simulate(90, 10, Strategy(("M",))), simulate(90, 10, Strategy(("M",))))


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


class PitTests(unittest.TestCase):
    def test_independent_total_and_transition(self):
        race = simulate(90, 10, Strategy(('S', 'H'), (4,)), 22.5)
        self.assertAlmostEqual(race.total, 929.625)
        self.assertEqual((race.laps[3].compound, race.laps[3].age, race.laps[3].pit), ('S', 3, 22.5))
        self.assertEqual((race.laps[4].compound, race.laps[4].age), ('H', 0))
        self.assertAlmostEqual(race.laps[3].time, 112.785)

    def test_first_and_penultimate_stops(self):
        for stop in (1, 9):
            race = simulate(90, 10, Strategy(('M', 'S'), (stop,)))
            self.assertEqual(race.laps[stop].age, 0)
            self.assertEqual(sum(lap.pit for lap in race.laps), 22.5)

    def test_zero_cost_still_changes_and_resets(self):
        race = simulate(90, 10, Strategy(('S', 'H'), (4,)), 0)
        self.assertEqual((race.laps[4].compound, race.laps[4].age), ('H', 0))
        self.assertAlmostEqual(race.total, 907.125)

    def test_invalid_stop_positions(self):
        for stop in (0, -1, 10, 11, True, 4.0, [4, 4]):
            with self.subTest(stop=stop), self.assertRaises(ValueError):
                simulate(90, 10, Strategy(('S', 'M'), (stop,)))

    def test_invalid_pit_loss(self):
        for loss in (-1, 61, float('nan'), float('inf'), True, '22'):
            with self.subTest(loss=loss), self.assertRaises(ValueError):
                simulate(90, 10, Strategy(('S', 'M'), (4,)), loss)

    def test_missing_or_orphaned_compound(self):
        for stop, compound in ((4, None), (None, 'M'), (4, 'X')):
            with self.subTest(stop=stop), self.assertRaises(ValueError):
                simulate(90, 10, Strategy(('S', compound), () if stop is None else (stop,)))


class StrategyTests(unittest.TestCase):
    def test_two_stops_independent_total(self):
        # Base 900 + offsets 5.44 + wear .285+.18+.222 + two pits 45.
        race = simulate(90, 10, Strategy(('S', 'M', 'H'), (3, 6)))
        self.assertAlmostEqual(race.total, 951.127)
        self.assertEqual([race.laps[i].age for i in (0, 3, 6)], [0, 0, 0])
        self.assertEqual([race.laps[i].compound for i in (0, 3, 6)], ['S', 'M', 'H'])

    def test_invalid_plan_combinations(self):
        plans = [Strategy((), ()), Strategy(('S','H'), (4,4)),
                 Strategy(('S','M','H'), (6,3)), Strategy(('S','M','H'), (3,3)),
                 Strategy(('S',)*4, (2,4,6)), Strategy(('S','X'), (4,)),
                 Strategy(['S'], ()), Strategy(('S',), []), None]
        for plan in plans:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                simulate(90, 10, plan)

    def test_same_compound_replacement_is_allowed(self):
        race = simulate(90, 10, Strategy(('S','S'), (5,)), 0)
        self.assertAlmostEqual(race.total, 901.9)


class ComparisonTests(unittest.TestCase):
    def test_independent_gap_and_reverse(self):
        soft, hard = Strategy(('S',)), Strategy(('H',))
        result = compare(90, 10, soft, hard)
        self.assertAlmostEqual(result.a.total, 904.275)
        self.assertAlmostEqual(result.b.total, 911.665)
        self.assertAlmostEqual(result.gap, 7.390)
        self.assertEqual(result.winner, 'A')
        reverse = compare(90, 10, hard, soft)
        self.assertAlmostEqual(reverse.gap, -7.390)
        self.assertEqual(reverse.winner, 'B')
        self.assertAlmostEqual(result.gaps[-1], result.gap)

    def test_identical_plans_tie(self):
        plan = Strategy(('M','H'), (5,))
        result = compare(90, 10, plan, plan)
        self.assertEqual(result.winner, 'Tie')
        self.assertEqual(result.gaps, (0,)*10)

    def test_one_against_two_stops(self):
        result = compare(90, 10, Strategy(('S','H'), (4,)), Strategy(('S','M','H'), (3,6)))
        self.assertAlmostEqual(result.gap, 21.502)
        self.assertEqual(len(result.a.laps), len(result.b.laps))

    def test_invalid_b_is_rejected(self):
        with self.assertRaises(ValueError):
            compare(90, 10, Strategy(), Strategy(('S','H'), (10,)))
