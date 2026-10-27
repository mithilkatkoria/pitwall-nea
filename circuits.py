"""Validated circuit profiles, independent of graphics."""
from dataclasses import dataclass
import json
from pathlib import Path
from model import number_in_range, validate_laps

DATA_PATH = Path(__file__).resolve().parent / "data" / "circuits.json"


def unique_fields(pairs):
    row = {}
    for key, value in pairs:
        if key in row:
            raise ValueError(f"Duplicate circuit field: {key}")
        row[key] = value
    return row


@dataclass(frozen=True)
class Circuit:
    key: str
    name: str
    country: str
    laps: int
    length: float
    base_time: float
    pit_loss: float
    wear: float
    points: tuple[tuple[float, float], ...]


def parse_circuit(row):
    fields = {"key", "name", "country", "laps", "length", "base_time", "pit_loss", "wear", "points"}
    if not isinstance(row, dict) or set(row) != fields:
        raise ValueError("Circuit fields are missing or unsupported.")
    for field in ("key", "name", "country"):
        if not isinstance(row[field], str) or not row[field].strip() or len(row[field]) > 60:
            raise ValueError(f"Circuit {field} must contain 1-60 characters.")
    validate_laps(row["laps"])
    for field, low, high in (("length", .5, 15), ("base_time",30,200), ("pit_loss",0,60), ("wear",.1,3)):
        number_in_range(row[field], field, low, high)
    points = row["points"]
    if not isinstance(points, list) or not 3 <= len(points) <= 500:
        raise ValueError("Circuit needs 3-500 coordinate pairs.")
    checked = []
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("Each circuit point needs x and y.")
        checked.append(tuple(number_in_range(value, "Coordinate", 0, 1) for value in point))
    if len(set(checked)) < 3 or any(a == b for a,b in zip(checked, checked[1:]+checked[:1])):
        raise ValueError("Circuit points must define distinct consecutive vertices.")
    if max(p[0] for p in checked) == min(p[0] for p in checked) or max(p[1] for p in checked) == min(p[1] for p in checked):
        raise ValueError("Circuit must have width and height.")
    twice_area = sum(a[0]*b[1] - b[0]*a[1] for a,b in zip(checked, checked[1:]+checked[:1]))
    if abs(twice_area) < 1e-10:
        raise ValueError("Circuit vertices must enclose a non-zero area.")
    return Circuit(**{**row, "points": tuple(checked)})


def load_circuits(path=DATA_PATH):
    try:
        path = Path(path)
        if path.stat().st_size > 200_000:
            raise ValueError("Circuit file is too large.")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f"Cannot read circuit data: {error}") from error
    if not isinstance(data, list) or not 1 <= len(data) <= 20:
        raise ValueError("Circuit data must contain 1-20 profiles.")
    profiles = tuple(parse_circuit(row) for row in data)
    if len({c.key for c in profiles}) != len(profiles):
        raise ValueError("Circuit keys must be unique.")
    return profiles
