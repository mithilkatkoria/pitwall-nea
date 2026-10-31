"""Driver CSV data and descriptive statistics, without interface code."""
import csv
from dataclasses import dataclass
from math import fsum,isfinite,sqrt
from pathlib import Path

MAX_ROWS=20_000
SAMPLE_PATH=Path(__file__).resolve().parent/'data'/'sample_laps.csv'


@dataclass(frozen=True)
class DriverLap:
    driver: str
    lap: int
    time: float
    pit: bool


@dataclass(frozen=True)
class Stats:
    driver: str
    count: int
    best: float
    mean: float
    deviation: float
    trend: float


def read_laps(path):
    rows=[];seen=set();drivers=set()
    try:
        path=Path(path)
        if path.stat().st_size>2_000_000: raise ValueError('CSV file exceeds 2 MB.')
        with path.open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream,strict=True)
            header=reader.fieldnames
            if not header or not {'driver','lap','lap_time'}<=set(header) or len(set(header))!=len(header):
                raise ValueError('CSV needs unique driver, lap, lap_time columns; optional pit_lap.')
            for count,row in enumerate(reader,1):
                if count>MAX_ROWS: raise ValueError('CSV exceeds 20,000 rows.')
                try:
                    if None in row or any(value is None for value in row.values()): raise ValueError('Column count does not match header.')
                    name=row['driver'].strip()
                    lap=int(row['lap']);seconds=float(row['lap_time'])
                    pit=row.get('pit_lap','0').strip().lower()
                    if not name or len(name)>32 or not name.isprintable(): raise ValueError('Driver name must contain 1-32 printable characters.')
                    if not 1<=lap<=1000: raise ValueError('Lap number must be 1-1000.')
                    if not isfinite(seconds) or not 0<seconds<=600: raise ValueError('Lap time must be above 0 and at most 600 seconds.')
                    if pit not in ('','0','1','true','false','yes','no'): raise ValueError('Invalid pit_lap flag.')
                    if (name,lap) in seen: raise ValueError('Duplicate driver/lap.')
                    seen.add((name,lap));drivers.add(name)
                    if len(drivers)>12: raise ValueError('Import at most 12 drivers.')
                    rows.append(DriverLap(name,lap,seconds,pit in ('1','true','yes')))
                except (ValueError,TypeError) as error:
                    raise ValueError(f'CSV record {count}: {error}') from error
    except (OSError,UnicodeError,csv.Error) as error:
        raise ValueError(f'Cannot read CSV: {error}') from error
    if not rows: raise ValueError('CSV contains no lap records.')
    return tuple(sorted(rows,key=lambda row:(row.driver,row.lap)))


def filtered(rows,driver,exclude_pits=True):
    return tuple(row for row in rows if row.driver==driver and not (exclude_pits and row.pit))


def summarise(rows,exclude_pits=True):
    result=[]
    for driver in sorted({row.driver for row in rows}):
        laps=filtered(rows,driver,exclude_pits)
        if not laps: continue
        n=len(laps)
        mean=fsum(row.time for row in laps)/n
        mean_lap=fsum(row.lap for row in laps)/n
        variance=fsum((row.time-mean)**2 for row in laps)/n
        denominator=fsum((row.lap-mean_lap)**2 for row in laps)
        trend=fsum((row.lap-mean_lap)*(row.time-mean) for row in laps)/denominator if denominator else 0.0
        result.append(Stats(driver,n,min(row.time for row in laps),mean,sqrt(variance),trend))
    return tuple(sorted(result,key=lambda value:(value.mean,value.driver)))
