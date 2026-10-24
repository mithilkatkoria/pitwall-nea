import unittest
from circuits import load_circuits
from track import fit_points


class TrackTests(unittest.TestCase):
    def test_all_profiles_fit_with_padding(self):
        for profile in load_circuits():
            points=fit_points(profile.points,(100,200,400,300))
            self.assertEqual(len(points),len(profile.points))
            self.assertTrue(all(130<=x<=470 and 230<=y<=470 for x,y in points))
            self.assertNotEqual(points[0],points[-1]) # renderer closes the final segment

    def test_square_preserves_aspect_ratio(self):
        points=fit_points(((0,0),(1,0),(1,1),(0,1)),(0,0,400,200),20)
        self.assertEqual(points,((120,20),(280,20),(280,180),(120,180)))

    def test_small_panel_rejected(self):
        with self.assertRaises(ValueError):
            fit_points(((0,0),(1,0),(1,1)),(0,0,50,50))
