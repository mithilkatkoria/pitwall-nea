import unittest
from model import compare, Strategy
from charts import series,points,hover_index,limits


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.result=compare(90,10,Strategy(('S','H'),(4,)),Strategy(('M',)))

    def test_values_are_actual_records(self):
        self.assertEqual(series(self.result,'lap')[0][3],self.result.a.laps[3].time)
        self.assertEqual(series(self.result,'tyre')[0][4],0)
        self.assertEqual(series(self.result,'gap')[0][-1],self.result.gap)
        with self.assertRaises(ValueError): series(self.result,'bad')

    def test_transform_and_hover_boundaries(self):
        bounds=(10,20,100,200)
        self.assertEqual(points((0,5,10),bounds,(0,10)),((10,220),(60,120),(110,20)))
        self.assertEqual([hover_index(x,3,bounds) for x in (-1,10,60,110,999)],[0,0,1,2,2])
        low,high=limits(((5,5),));self.assertLess(low,5);self.assertGreater(high,5)
