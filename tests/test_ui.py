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
