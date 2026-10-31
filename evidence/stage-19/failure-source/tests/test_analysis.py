from math import sqrt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from analysis import DriverLap,read_laps,summarise,SAMPLE_PATH


class AnalysisTests(unittest.TestCase):
    def test_independent_statistics_and_filter(self):
        rows=tuple(DriverLap('A',lap,time,False) for lap,time in ((1,90),(3,92),(5,94)))+(DriverLap('A',6,112,True),)
        stats=summarise(rows)[0]
        self.assertEqual((stats.count,stats.best,stats.mean,stats.trend),(3,90,92,1))
        self.assertAlmostEqual(stats.deviation,sqrt(8/3))
        self.assertEqual(summarise(rows,False)[0].mean,97)
        self.assertEqual(summarise((DriverLap('A',1,90,True),)),())
        one=summarise((DriverLap('A',1,90,False),))[0]
        self.assertEqual((one.deviation,one.trend),(0,0))

    def test_sample(self):
        rows=read_laps(SAMPLE_PATH)
        self.assertEqual(len(rows),180)
        self.assertEqual([row.count for row in summarise(rows)],[59]*3)

    def test_invalid_csv(self):
        header='driver,lap,lap_time,pit_lap\n'
        bad=['','driver,lap\nA,1\n',header,header+'A,1,nan,0\n',header+'A,0,90,0\n',header+'A,1,0,0\n',header+'A,1,601,0\n',header+'A,1,90,x\n',header+'A,1,90,0\nA,1,91,0\n',header+'A,1,90\n',header+'"unfinished',header+'x'*140000]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'laps.csv'
            for text in bad:
                path.write_text(text)
                with self.subTest(text=text[:30]),self.assertRaises(ValueError): read_laps(path)
            with self.assertRaises(ValueError): read_laps(Path(temp)/'missing.csv')

    def test_driver_and_row_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'laps.csv'
            header='driver,lap,lap_time\n'
            path.write_text(header+''.join(f'D{i},{lap},90\n' for i in range(12) for lap in range(1,1001)))
            self.assertEqual(len(read_laps(path)),12000)
            path.write_text(header+''.join(f'D{i},1,90\n' for i in range(13)))
            with self.assertRaisesRegex(ValueError,'12 drivers'): read_laps(path)
            path.write_text(header+'A,1,90\nA,2,91\nA,3,92\n')
            with patch('analysis.MAX_ROWS',2),self.assertRaisesRegex(ValueError,'rows'): read_laps(path)
