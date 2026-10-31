"""Versioned sessions and atomic local-file output."""
import csv
from dataclasses import asdict, dataclass, fields
import io
import json
import os
from pathlib import Path
import tempfile
from circuits import load_circuits
from model import Conditions, Strategy, Lap, compare


@dataclass(frozen=True)
class Session:
    circuit: str
    base: float
    laps: int
    pit: float
    conditions: Conditions
    plans: tuple[Strategy, Strategy]
    paces: tuple[float, float] = (0.0, 0.0)

    def validate(self):
        if not isinstance(self.circuit,str) or self.circuit not in {c.key for c in load_circuits()}:
            raise ValueError("Session circuit is unknown.")
        if not isinstance(self.plans,tuple) or len(self.plans)!=2 or not isinstance(self.paces,tuple) or len(self.paces)!=2:
            raise ValueError("A session needs exactly two plans and two pace values.")
        return compare(self.base,self.laps,*self.plans,self.pit,self.conditions,*self.paces)


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError(f"Duplicate JSON key: {key}")
        result[key]=value
    return result


def reject_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def session_from_data(data):
    required={'version','circuit','base','laps','pit','conditions','plans','paces'}
    if not isinstance(data,dict) or set(data)!=required:
        raise ValueError("Session fields are missing or unsupported.")
    if type(data['version']) is not int or data['version']!=1:
        raise ValueError("Unsupported session version.")
    conditions=data['conditions']
    if not isinstance(conditions,dict) or set(conditions)!={field.name for field in fields(Conditions)}:
        raise ValueError("Invalid saved conditions.")
    if not isinstance(data['plans'],list) or len(data['plans'])!=2:
        raise ValueError("Save exactly two plans.")
    plans=[]
    for plan in data['plans']:
        if not isinstance(plan,dict) or set(plan)!={'compounds','stops'} or not isinstance(plan['compounds'],list) or not isinstance(plan['stops'],list):
            raise ValueError("Invalid saved strategy.")
        plans.append(Strategy(tuple(plan['compounds']),tuple(plan['stops'])))
    if not isinstance(data['paces'],list) or len(data['paces'])!=2:
        raise ValueError("Save exactly two driver offsets.")
    session=Session(data['circuit'],data['base'],data['laps'],data['pit'],Conditions(**conditions),tuple(plans),tuple(data['paces']))
    session.validate()
    return session


def load_session(path):
    try:
        path=Path(path)
        if path.stat().st_size>100_000: raise ValueError("Session is larger than 100 KB.")
        data=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique_object,parse_constant=reject_constant)
        return session_from_data(data)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f"Cannot load session: {error}") from error


def atomic_text(path,text):
    path=Path(path)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='',dir=path.parent,
                                         prefix=f'.{path.name}.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    except OSError as error:
        raise ValueError(f"Cannot write file: {error}") from error
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()


def save_session(path,session):
    session.validate()
    data={'version':1,**asdict(session)}
    atomic_text(path,json.dumps(data,indent=2,allow_nan=False)+'\n')


def export_laps(path,session):
    comparison=session.validate()
    stream=io.StringIO(newline='')
    names=[field.name for field in fields(Lap)]
    writer=csv.DictWriter(stream,fieldnames=['plan',*names])
    writer.writeheader()
    for label,result in (('A',comparison.a),('B',comparison.b)):
        for lap in result.laps:
            row=asdict(lap)
            for name,value in row.items():
                if name not in ('number','compound','age','safety_car'):
                    row[name]=f'{value:.3f}'
            writer.writerow({'plan':label,**row})
    atomic_text(path,stream.getvalue())
    return comparison
