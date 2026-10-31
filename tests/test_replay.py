import unittest
from replay import Replay,progress
from model import simulate
from track import point_at


class ReplayTests(unittest.TestCase):
    def test_play_pause_finish_restart(self):
        clock=Replay(1000)
        clock.advance(1);self.assertEqual(clock.elapsed,0)
        clock.toggle();clock.advance(1);self.assertEqual(clock.elapsed,120)
        clock.toggle();clock.advance(1);self.assertEqual(clock.elapsed,120)
        clock.toggle();clock.advance(10);self.assertEqual(clock.elapsed,1000)
        self.assertFalse(clock.playing)
        clock.restart();self.assertEqual(clock.elapsed,0);self.assertFalse(clock.playing)

    def test_speeds_and_scrubbing(self):
        clock=Replay(1000)
        for speed in (300,60,120):
            clock.cycle_speed();self.assertEqual(clock.speed,speed)
        for fraction,value in ((-.1,0),(.5,500),(1.1,1000)):
            clock.scrub(fraction);self.assertEqual(clock.elapsed,value)
            self.assertFalse(clock.playing)

    def test_lap_boundaries_and_shared_seconds(self):
        race=simulate(90,10)
        self.assertEqual(progress(race,0),(0,0))
        self.assertEqual(progress(race,race.laps[0].elapsed),(1,1))
        self.assertEqual(progress(race,race.total),(10,9))
        self.assertAlmostEqual(progress(race,race.laps[0].time/2)[0],.5)
        slower=simulate(100,10)
        self.assertLess(progress(slower,100)[0],progress(race,100)[0])

    def test_closed_polyline_uses_distance(self):
        rectangle=((0,0),(2,0),(2,1),(0,1))
        self.assertEqual(point_at(rectangle,0),(0,0))
        self.assertEqual(point_at(rectangle,1),(0,0))
        self.assertEqual(point_at(rectangle,.5),(2,1))
