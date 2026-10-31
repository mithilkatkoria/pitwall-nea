"""Independent Decimal oracle, using stint sums rather than the race loop."""
from decimal import Decimal as D
import unittest
from model import optimise, Strategy


def oracle(base, laps, compounds, stop, pit):
    pace = {'S': D('0'), 'M': D('.48'), 'H': D('1')}
    rate = {'S': D('.095'), 'M': D('.060'), 'H': D('.037')}
    life = {'S': 18, 'M': 28, 'H': 38}
    total = D(str(pit))
    for compound, length in zip(compounds, (stop, laps-stop)):
        k = max(0, length-1-life[compound])
        total += length*(D(str(base))+pace[compound])
        total += rate[compound]*length*(length-1)/2
        total += D('.018')*k*(k+1)*(2*k+1)/6
    return total


class SearchTests(unittest.TestCase):
    def test_every_candidate_against_separate_oracle(self):
        for laps in (10, 35, 100):
            search = optimise(90, laps)
            self.assertEqual(len(search.candidates), 6*(laps-1))
            self.assertEqual(len({row.plan for row in search.candidates}), 6*(laps-1))
            expected = []
            for row in search.candidates:
                self.assertNotEqual(*row.plan.compounds)
                value = oracle(90, laps, row.plan.compounds, row.plan.stops[0], 22.5)
                self.assertAlmostEqual(row.total, float(value), delta=1e-8)
                expected.append(value)
            self.assertAlmostEqual(search.best.total, float(min(expected)), delta=1e-8)

    def test_known_small_winner_and_tie_order(self):
        result = optimise(90, 10)
        self.assertEqual(result.best.plan, Strategy(('S','M'), (7,)))
        self.assertAlmostEqual(result.best.total, 926.115)
        reverse = next(c for c in result.candidates if c.plan == Strategy(('M','S'), (3,)))
        self.assertAlmostEqual(reverse.total, result.best.total)

    def test_first_and_last_legal_stops_present(self):
        stops = {c.plan.stops[0] for c in optimise(90, 10).candidates}
        self.assertEqual(stops, set(range(1,10)))

    def test_invalid_search_settings(self):
        for base, laps, pit in ((-1,10,22.5),(90,9,22.5),(90,True,22.5),(90,10,-1)):
            with self.subTest(base=base,laps=laps,pit=pit), self.assertRaises(ValueError):
                optimise(base,laps,pit)
