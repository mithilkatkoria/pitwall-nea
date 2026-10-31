"""Cross-feature checks added after the feature-specific validation tests."""
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest
from circuits import DATA_PATH,load_circuits,parse_circuit
from model import Conditions,Strategy,simulate,optimise


def independent_total(base,laps,plan,pit,conditions,pace):
    params={'S':('0','.095',18),'M':('.48','.060',28),'H':('1','.037',38)}
    total=D(0)
    boundaries=(0,)+plan.stops+(laps,)
    for stint,compound in enumerate(plan.compounds):
        offset,rate,life=params[compound]
        for lap in range(boundaries[stint]+1,boundaries[stint+1]+1):
            age=lap-boundaries[stint]-1
            fuel=D('.048')*(laps-lap)
            stop=lap in plan.stops
            sc=conditions.sc_start>0 and conditions.sc_start<=lap<conditions.sc_start+conditions.sc_duration
            if sc:
                seconds=D(str(base))*D('1.4')+fuel/4
                if stop:
                    service=min(D('2.5'),D(str(pit)))
                    seconds+=service+D('.6')*(D(str(pit))-service)
            else:
                wear=(D(rate)*age+D('.018')*max(0,age-life)**2)*D(str(conditions.wear))*(1+(conditions.temperature-30)*D('.018'))
                seconds=D(str(base))+D(offset)+wear+fuel+(D('.55') if age==0 else 0)+D(str(pace))+{'Dry':0,'Damp':5,'Wet':14}[conditions.weather]
                if stop: seconds+=D(str(pit))
            total+=seconds
    return float(total)


class RobustnessTests(unittest.TestCase):
    def test_combined_conditions_against_decimal_oracle(self):
        for laps in (10,35,100):
            for plan in (Strategy(('S',)),Strategy(('S','H'),(laps//2,)),Strategy(('M','H','S'),(1,laps-1))):
                for conditions in (Conditions(),Conditions(.1,15,'Wet',1,10),Conditions(3,50,'Damp',laps-4,5)):
                    for pit,pace in ((0,-2),(60,2)):
                        expected=independent_total(90,laps,plan,pit,conditions,pace)
                        self.assertAlmostEqual(simulate(90,laps,plan,pit,conditions,pace).total,expected,delta=1e-8)

    def test_search_every_candidate_under_safety_car(self):
        for laps in (10,25):
            conditions=Conditions(1.7,45,'Wet',4,5)
            search=optimise(92,laps,24,conditions,-.8)
            totals=[]
            for candidate in search.candidates:
                expected=independent_total(92,laps,candidate.plan,24,conditions,-.8)
                self.assertAlmostEqual(candidate.total,expected,delta=1e-8)
                totals.append(expected)
            self.assertAlmostEqual(search.best.total,min(totals),delta=1e-8)

    def test_degenerate_and_duplicate_key_profiles_rejected(self):
        row=json.loads(DATA_PATH.read_text())[0]
        with self.subTest(case='collinear'),self.assertRaises(ValueError):
            parse_circuit({**row,'points':[[0,0],[.5,.5],[1,1]]})
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'circuits.json'
            text=json.dumps([row]).replace('"laps": 52','"laps": 10, "laps": 52')
            path.write_text(text)
            with self.subTest(case='duplicate json key'),self.assertRaises(ValueError): load_circuits(path)
