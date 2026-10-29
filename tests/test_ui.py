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
        self.app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=self.app.to_window(self.app.controls[key].center)))
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
        self.assertAlmostEqual(self.app.replay.elapsed,self.app.replay.duration/2,delta=15) # one display-pixel scrub tolerance
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

    def test_focus_replaces_value_and_marks_stale(self):
        self.click('base')
        self.app.handle(pygame.event.Event(pygame.TEXTINPUT,text='91'))
        self.assertEqual(self.app.fields['base'],'91')
        self.assertTrue(self.app.stale)
        self.click('simulate');self.assertFalse(self.app.stale)

    def test_long_text_fits_and_keeps_full_tooltip(self):
        from widgets import fit_text,wrap_text
        text='WIDE DRIVER NAME WITH 32 CHARS XX'
        fitted=fit_text(text,self.app.font,270)
        self.assertLessEqual(self.app.font.size(fitted)[0],270)
        self.assertNotEqual(text,fitted)
        self.assertTrue(all(self.app.small.size(line)[0]<=200 for line in wrap_text(text*4,self.app.small,200)))
        self.app.tooltips=[]
        self.app.button('long',text,(30,30,290,40))
        self.assertEqual(self.app.tooltips[0][1],text)

    def test_resize_pointer_mapping_and_graph_conditions_coexist(self):
        for width,height in ((1440,900),(1152,720),(1000,650),(864,540)):
            self.app.handle(pygame.event.Event(pygame.VIDEORESIZE,w=width,h=height));self.app.draw()
            point=self.app.controls['simulate'].center
            mapped=self.app.to_logical(self.app.to_window(point))
            self.assertAlmostEqual(mapped[0],point[0],delta=1)
            self.assertAlmostEqual(mapped[1],point[1],delta=1)
            self.click('simulate');self.assertFalse(self.app.error)
        self.click('advanced')
        self.assertIn('temperature',self.app.controls)
        self.assertIn('metric_gap',self.app.controls)

    def test_file_buttons_roundtrip_export_and_cancel(self):
        import csv
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from storage import load_session
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'session.json'
            before=self.app.session()
            with patch('ui.choose_path',return_value=str(path)):
                self.click('save')
                self.assertEqual(load_session(path),before)
                self.app.fields['base']='99'
                self.click('load')
                self.assertEqual(self.app.session(),before)
            target=Path(temp)/'laps.csv'
            self.app.fields['base']='91'
            self.app.dirty()
            with patch('ui.choose_path',return_value=str(target)):
                self.click('export')
            with target.open(newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),104)
            self.assertEqual(rows[0]['base'],'91.000')
            self.assertFalse(self.app.stale)
            result=self.app.result
            with patch('ui.choose_path',return_value=''):
                for action in ('save','load','export','import'):
                    self.app.file_action(action)
            self.assertIs(self.app.result,result)
            self.assertEqual(self.app.fields['base'],'91')

    def test_import_button_pagination_and_empty_pit_filter(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'drivers.csv'
            path.write_text('driver,lap,lap_time,pit_lap\n'+''.join(
                f'Driver {i:02},1,{90+i},1\n' for i in range(12)))
            self.click('driver_view')
            with patch('ui.choose_path',return_value=str(path)):
                self.click('import')
            self.assertFalse(self.app.error)
            self.assertIsNone(self.app.selected_driver)
            self.click('filter')
            self.assertEqual(len([k for k in self.app.controls if k.startswith('driver_') and k!='driver_view']),6)
            self.click('next_drivers')
            self.assertEqual(self.app.driver_page,1)
            self.click('driver_Driver 11')
            self.assertEqual(self.app.selected_driver,'Driver 11')
            self.click('next_drivers')
            self.assertEqual(self.app.driver_page,1)
            self.click('previous_drivers')
            self.assertEqual(self.app.driver_page,0)

    def test_full_control_layout_all_profiles_and_two_stops(self):
        for index in range(3):
            self.app.set_profile(index)
            self.app.counts=[2,2]
            self.app.advanced=True
            self.app.draw()
            self.click('simulate')
            self.assertFalse(self.app.error)
            canvas=self.app.screen.get_rect()
            controls=list(self.app.controls.items())
            for key,rect in controls:
                self.assertTrue(canvas.contains(rect),key)
            for i,(key,rect) in enumerate(controls):
                for other,target in controls[i+1:]:
                    self.assertFalse(rect.colliderect(target),(key,other))
