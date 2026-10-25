import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from storage import Session, save_session, load_session, export_laps
from model import Strategy,Conditions


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.session=Session('silverstone',90,10,22.5,Conditions(1.2,35,'Damp',4,1),
                             (Strategy(('S','H'),(4,)),Strategy(('M','H'),(5,))),(-.5,.2))
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'session.json'

    def tearDown(self): self.temp.cleanup()

    def test_roundtrip(self):
        save_session(self.path,self.session)
        self.assertEqual(load_session(self.path),self.session)

    def test_missing_malformed_wrong_types_and_cardinality(self):
        with self.assertRaises(ValueError): load_session(self.path)
        for text in ('{','[]','{"version":1,"version":1}','{"value":NaN}', ' '*100001):
            self.path.write_text(text)
            with self.subTest(text=text[:30]),self.assertRaises(ValueError): load_session(self.path)
        save_session(self.path,self.session);data=json.loads(self.path.read_text())
        for key,value in [('version',True),('plans',data['plans'][:1]),('laps',True),('paces',[0]),('circuit','moon')]:
            self.path.write_text(json.dumps({**data,key:value}))
            with self.subTest(key=key),self.assertRaises(ValueError): load_session(self.path)

    def test_csv_row_count_and_every_component(self):
        result=export_laps(self.path,self.session)
        with self.path.open(newline='') as stream: rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),20)
        for row,lap in zip(rows,result.a.laps+result.b.laps):
            self.assertEqual(int(row['number']),lap.number)
            self.assertEqual(row['compound'],lap.compound)
            for name in ('time','elapsed','degradation','pit','fuel','warmup','base','compound_pace','weather','driver'):
                self.assertAlmostEqual(float(row[name]),getattr(lap,name),delta=.00051)
                self.assertRegex(row[name], r'^-?\d+\.\d{3}$')
        self.assertEqual([r['plan'] for r in rows],['A']*10+['B']*10)

    def test_failed_replace_preserves_original_and_unrelated_temp(self):
        self.path.write_text('original')
        unrelated=self.path.with_suffix('.tmp');unrelated.write_text('keep me')
        with patch('storage.os.replace',side_effect=OSError('test write failure')):
            with self.assertRaises(ValueError): save_session(self.path,self.session)
        self.assertEqual(self.path.read_text(),'original')
        self.assertEqual(unrelated.read_text(),'keep me')
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()),['session.json','session.tmp'])

    def test_invalid_session_never_overwrites(self):
        self.path.write_text('original')
        invalid=Session('silverstone',90,10,22.5,Conditions(),(Strategy(),))
        with self.assertRaises(ValueError): save_session(self.path,invalid)
        self.assertEqual(self.path.read_text(),'original')
