"""Boundary cases identified during the final repository review."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from pathlib import Path
import tempfile
import unittest

import pygame
from analysis import read_laps
from strategy_view import time_label
from ui import App


class ReviewDisplayTests(unittest.TestCase):
    def test_time_labels_carry_rounded_seconds_and_minutes(self):
        cases = ((0, "0:00:00.000"), (59.9996, "0:01:00.000"),
                 (3599.9996, "1:00:00.000"), (3661.234, "1:01:01.234"))
        for value, expected in cases:
            with self.subTest(seconds=value):
                self.assertEqual(time_label(value), expected)


class ReviewCSVTests(unittest.TestCase):
    def test_non_printable_driver_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "laps.csv"
            for character in ("\x7f", "\x85", "\u200b"):
                path.write_text(f"driver,lap,lap_time\nA{character}B,1,90\n", encoding="utf-8")
                with self.subTest(character=repr(character)), self.assertRaisesRegex(ValueError, "printable"):
                    read_laps(path)

    def test_printable_unicode_driver_names_remain_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "laps.csv"
            path.write_text("driver,lap,lap_time\nJos\u00e9,1,90\n", encoding="utf-8")
            self.assertEqual(read_laps(path)[0].driver, "Jos\u00e9")


class ReviewInteractionTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.draw()

    def tearDown(self):
        pygame.quit()

    def key(self, key, mod=0):
        self.app.handle(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))

    def test_oversized_replacement_preserves_field_and_allows_retry(self):
        before = self.app.fields["base"]
        result = self.app.result
        self.app.activate("base")
        self.app.handle(pygame.event.Event(pygame.TEXTINPUT, text="12345678901234567"))
        self.assertEqual(self.app.fields["base"], before)
        self.assertIs(self.app.result, result)
        self.assertFalse(self.app.stale)
        self.assertTrue(self.app.error)
        self.assertIn("16", self.app.status)
        self.app.handle(pygame.event.Event(pygame.TEXTINPUT, text="91.5"))
        self.assertEqual(self.app.fields["base"], "91.5")
        self.assertTrue(self.app.stale)
        self.assertTrue(self.app.calculate())

    def test_profile_change_marks_missing_results_as_stale(self):
        self.assertFalse(self.app.stale)
        self.app.activate("profile")
        self.assertIsNone(self.app.result)
        self.assertTrue(self.app.stale)
        self.assertEqual(self.app.replay.elapsed, 0)

    def test_profile_change_clears_an_old_input_error(self):
        self.app.fields["base"] = "bad"
        self.app.dirty()
        self.assertFalse(self.app.calculate())
        self.app.activate("profile")
        self.assertFalse(self.app.error)
        self.assertTrue(self.app.calculate())

    def test_reverse_tab_from_no_focus_starts_at_last_control(self):
        self.app.focus = None
        self.key(pygame.K_TAB, pygame.KMOD_SHIFT)
        self.assertEqual(self.app.focus, list(self.app.controls)[-1])
        self.key(pygame.K_TAB)
        self.assertEqual(self.app.focus, list(self.app.controls)[0])

    def test_focused_timeline_supports_keyboard_scrubbing(self):
        total = self.app.result.a.total
        self.app.focus = "timeline"
        self.key(pygame.K_RIGHT)
        self.assertAlmostEqual(self.app.replay.elapsed, self.app.replay.duration * .05)
        self.key(pygame.K_END)
        self.assertEqual(self.app.replay.elapsed, self.app.replay.duration)
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.app.replay.elapsed, self.app.replay.duration)
        self.key(pygame.K_HOME)
        self.assertEqual(self.app.replay.elapsed, 0)
        self.assertFalse(self.app.replay.playing)
        self.assertEqual(self.app.result.a.total, total)

    def test_driver_summaries_refresh_after_import_and_filter(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "laps.csv"
            path.write_text("driver,lap,lap_time,pit_lap\nA,1,90,0\nA,2,110,1\n", encoding="utf-8")
            self.assertTrue(self.app.import_from(path))
            self.app.view = "drivers"
            self.app.draw()
            stats = self.app.driver_summaries[0]
            self.assertEqual((stats.count, stats.mean), (1, 90))
            self.app.activate("filter")
            self.app.draw()
            stats = self.app.driver_summaries[0]
            self.assertEqual((stats.count, stats.mean), (2, 100))
            path.write_text("driver,lap,lap_time\nB,3,95\n", encoding="utf-8")
            self.assertTrue(self.app.import_from(path))
            self.app.draw()
            stats = self.app.driver_summaries[0]
            self.assertEqual((stats.driver, stats.count, stats.mean), ("B", 1, 95))
            summaries = self.app.driver_summaries
            self.assertFalse(self.app.import_from(Path(folder) / "missing.csv"))
            self.assertIs(self.app.driver_summaries, summaries)
