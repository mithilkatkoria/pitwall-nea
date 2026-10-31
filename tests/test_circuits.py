import copy
import json
from pathlib import Path
import tempfile
import unittest
from circuits import load_circuits, parse_circuit, DATA_PATH
from model import simulate, Conditions


class CircuitTests(unittest.TestCase):
    def setUp(self):
        self.row=json.loads(DATA_PATH.read_text())[0]

    def test_three_profiles_run(self):
        profiles=load_circuits()
        self.assertEqual([c.key for c in profiles],['silverstone','monza','bahrain'])
        self.assertEqual([c.laps for c in profiles],[52,53,57])
        for c in profiles:
            race=simulate(c.base_time,c.laps,pit_loss=c.pit_loss,conditions=Conditions(wear=c.wear))
            self.assertEqual(len(race.laps),c.laps)
            self.assertAlmostEqual(race.laps[0].time,c.base_time+(c.laps-1)*.048+.55)

    def test_required_fields_and_numeric_bounds(self):
        row=copy.deepcopy(self.row);del row['name']
        with self.assertRaises(ValueError): parse_circuit(row)
        for key,value in [('laps',True),('laps',9),('base_time',float('nan')),('wear',0),('length',100),('name','')]:
            row={**self.row,key:value}
            with self.subTest(key=key),self.assertRaises(ValueError): parse_circuit(row)

    def test_coordinates(self):
        for points in ([],[[0,0]],[[0,0],[1,1],[2,2]],[[0,0],[1,1],[True,.5]],[[0,0],[0,0],[1,1]],[[0,0],[0,.5],[0,1]]):
            with self.subTest(points=points),self.assertRaises(ValueError):
                parse_circuit({**self.row,'points':points})

    def test_missing_malformed_and_duplicate_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'circuits.json'
            with self.assertRaises(ValueError): load_circuits(path)
            for text in ('{', '{}', '[]', json.dumps([self.row,self.row]), ' '*200001):
                path.write_text(text)
                with self.subTest(text=text[:20]),self.assertRaises(ValueError): load_circuits(path)
