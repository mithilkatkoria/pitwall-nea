import unittest
from model import simulate, compare, Strategy, Conditions


class ConditionsTests(unittest.TestCase):
    def test_weather_offsets(self):
        dry = simulate(90,10).total
        self.assertAlmostEqual(simulate(90,10,conditions=Conditions(weather='Damp')).total-dry, 50)
        self.assertAlmostEqual(simulate(90,10,conditions=Conditions(weather='Wet')).total-dry, 140)

    def test_temperature_and_wear(self):
        race = simulate(90,10,conditions=Conditions(wear=2,temperature=40))
        self.assertAlmostEqual(race.laps[1].degradation, .2242)
        self.assertAlmostEqual(race.total, 900 + 4.275*2*1.18 + 2.16 + .55)

    def test_pace_is_explicit_per_driver(self):
        result = compare(90,10,Strategy(),Strategy(),pace_a=-1,pace_b=1)
        self.assertAlmostEqual(result.gap,20)

    def test_component_sum(self):
        race = simulate(90,10,Strategy(('M','H'),(4,)),conditions=Conditions(1.2,35,'Damp'),pace=-.7)
        for lap in race.laps:
            self.assertAlmostEqual(lap.time, sum((lap.base,lap.compound_pace,lap.degradation,lap.fuel,lap.warmup,lap.weather,lap.driver,lap.pit)))

    def test_invalid_conditions(self):
        for conditions in (None, Conditions(wear=True), Conditions(wear=float('nan')), Conditions(wear=.09), Conditions(temperature=30.0), Conditions(temperature=51), Conditions(weather=[]), Conditions(weather='Snow')):
            with self.subTest(conditions=conditions), self.assertRaises(ValueError):
                simulate(90,10,conditions=conditions)
        for pace in (True,3,float('inf'),'1'):
            with self.subTest(pace=pace), self.assertRaises(ValueError):
                simulate(90,10,pace=pace)


class SafetyCarTests(unittest.TestCase):
    def test_independent_stop_lap(self):
        race = simulate(90,10,Strategy(('S','H'),(4,)),conditions=Conditions(sc_start=4,sc_duration=1))
        self.assertAlmostEqual(race.laps[3].time, 140.572)
        self.assertAlmostEqual(race.laps[3].pit, 14.5)
        self.assertEqual(race.laps[4].age,0)
        self.assertAlmostEqual(race.total, 932.885-113.073+140.572)

    def test_whole_ten_lap_race_neutralised(self):
        race = simulate(90,10,conditions=Conditions(sc_start=1,sc_duration=10))
        self.assertTrue(all(lap.safety_car for lap in race.laps))
        self.assertAlmostEqual(race.total,1260+.54)
        self.assertEqual(race.laps[-1].age,9)

    def test_final_lap_and_boundaries(self):
        race = simulate(90,10,conditions=Conditions(sc_start=10,sc_duration=1))
        self.assertFalse(race.laps[-2].safety_car)
        self.assertTrue(race.laps[-1].safety_car)
        for conditions in (Conditions(sc_start=-1), Conditions(sc_start=True), Conditions(sc_start=10,sc_duration=2), Conditions(sc_duration=0), Conditions(sc_duration=11), Conditions(sc_duration=1.0)):
            with self.subTest(conditions=conditions), self.assertRaises(ValueError):
                simulate(90,10,conditions=conditions)

    def test_small_or_zero_pit_loss_never_increases(self):
        for pit in (0,1,2.5,22.5):
            race=simulate(90,10,Strategy(('S','H'),(4,)),pit,Conditions(sc_start=4,sc_duration=1))
            self.assertLessEqual(race.laps[3].pit,pit)
            self.assertEqual(race.laps[4].age,0)

    def test_unused_sc_terms_are_zero_and_trace_adds_up(self):
        race=simulate(90,10,Strategy(('S','H'),(4,)),conditions=Conditions(2,40,'Wet',1,5),pace=-2)
        for lap in race.laps:
            self.assertAlmostEqual(lap.time, sum((lap.base,lap.compound_pace,lap.degradation,lap.fuel,lap.warmup,lap.weather,lap.driver,lap.pit)))
            if lap.safety_car:
                self.assertEqual((lap.compound_pace,lap.degradation,lap.warmup,lap.weather,lap.driver),(0,0,0,0,0))
