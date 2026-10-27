"""Posted Pygame events exercise controls, not physical OS keyboard delivery."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
import unittest
from ui import App


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.app=App();self.app.draw()

    def tearDown(self):
        pygame.quit()

    def click(self,key):
        self.app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=self.app.controls[key].center))
        self.app.draw()

    def test_compound_stop_count_and_simulation(self):
        self.click('tyre00')
        self.assertEqual(self.app.compounds[0][0],'M')
        self.click('count0')
        self.assertEqual(self.app.counts[0],2)
        self.click('simulate')
        self.assertFalse(self.app.error)
        self.assertEqual(len([lap for lap in self.app.result.a.laps if lap.pit]),2)

    def test_bad_input_preserves_last_result_then_retry(self):
        before=self.app.result
        self.click('laps')
        self.app.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_a,mod=pygame.KMOD_CTRL))
        self.app.handle(pygame.event.Event(pygame.TEXTINPUT,text='bad'))
        self.click('simulate')
        self.assertTrue(self.app.error)
        self.assertIs(self.app.result,before)
        self.app.fields['laps']='52'
        self.click('simulate')
        self.assertFalse(self.app.error)

    def test_profile_and_advanced_inputs(self):
        self.click('profile');self.assertEqual(self.app.profile.key,'monza')
        self.click('advanced');self.click('weather')
        self.assertEqual(self.app.fields['weather'],'Damp')
        self.click('simulate');self.assertFalse(self.app.error)

    def test_search_changes_plan_and_keeps_valid_result(self):
        self.click('optimise')
        self.assertEqual(self.app.counts[0],1)
        self.assertIn('optimised',self.app.status)
        self.assertFalse(self.app.error)

    def test_replay_controls_and_timeline(self):
        total=self.app.result.a.total
        self.click('play');self.app.update(1)
        self.assertEqual(self.app.replay.elapsed,120)
        self.click('play');self.app.update(1)
        self.assertEqual(self.app.replay.elapsed,120)
        self.click('timeline')
        self.assertAlmostEqual(self.app.replay.elapsed,self.app.replay.duration/2)
        self.click('restart');self.assertEqual(self.app.replay.elapsed,0)
        self.assertEqual(self.app.result.a.total,total)

    def test_load_failure_keeps_settings_and_result(self):
        import tempfile
        from pathlib import Path
        from storage import save_session
        before=self.app.session();result=self.app.result
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'test.json';path.write_text('{')
            self.assertFalse(self.app.load_from(path))
            self.assertEqual(self.app.session(),before)
            self.assertIs(self.app.result,result)
            save_session(path,before)
            self.app.fields['base']='99'
            self.assertTrue(self.app.load_from(path))
            self.assertEqual(self.app.session(),before)

    def test_chart_selection_and_hover_readout(self):
        self.click('metric_tyre')
        self.assertEqual(self.app.metric,'tyre')
        self.assertIn('0.000 s',self.app.chart_readout(0))
        self.click('metric_gap')
        self.assertIn(f'{self.app.result.gap:.3f}',self.app.chart_readout(51))

    def test_driver_navigation_filter_and_failed_import(self):
        self.click('driver_view')
        self.assertEqual(self.app.view,'drivers')
        self.click('filter');self.assertFalse(self.app.exclude_pits)
        before=self.app.driver_rows
        self.assertFalse(self.app.import_from('missing-driver-data.csv'))
        self.assertIs(self.app.driver_rows,before)
        self.click('strategy_view');self.assertEqual(self.app.view,'strategy')

    def test_keyboard_views_and_visible_control_focus(self):
        for key,view in ((pygame.K_F3,'notes'),(pygame.K_F2,'drivers'),(pygame.K_F1,'strategy')):
            self.app.handle(pygame.event.Event(pygame.KEYDOWN,key=key,mod=0));self.app.draw()
            self.assertEqual(self.app.view,view)
            self.app.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,mod=0))
            self.assertIn(self.app.focus,self.app.controls)
            self.app.handle(pygame.event.Event(pygame.TEXTINPUT,text='x')) # buttons must not act as text fields
        self.app.focus=None
        self.app.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,mod=0))
        self.assertTrue(self.app.replay.playing)
        self.app.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_r,mod=0))
        self.assertFalse(self.app.replay.playing)
