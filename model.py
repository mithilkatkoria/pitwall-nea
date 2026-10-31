"""Pure lap calculations; independent of command-line input and rendering."""
from math import isfinite
from dataclasses import dataclass

COMPOUND_PACE = {"S": 0.0, "M": 0.48, "H": 1.0}
TYRE_WEAR = {"S": (0.095, 18), "M": (0.060, 28), "H": (0.037, 38)}


def number_in_range(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    # Compare bounds before converting huge integers through isfinite.
    if not lower <= value <= upper or not isfinite(value):
        raise ValueError(f"{name} must be between {lower} and {upper}.")
    return value


def validate_compound(compound):
    if not isinstance(compound, str) or compound not in COMPOUND_PACE:
        raise ValueError("Compound must be S, M or H.")


def tyre_loss(compound, age):
    """Age is completed laps on this tyre set before the current lap."""
    validate_compound(compound)
    if type(age) is not int or not 0 <= age <= 1000:
        raise ValueError("Tyre age must be a whole number from 0 to 1000.")
    rate, life = TYRE_WEAR[compound]
    return rate * age + 0.018 * max(0, age - life) ** 2


def lap_time(base_time, compound="S", age=0):
    """Return base, compound offset and age-dependent degradation."""
    number_in_range(base_time, "Base lap time", 30, 200)
    loss = tyre_loss(compound, age)
    return base_time + COMPOUND_PACE[compound] + loss


@dataclass(frozen=True)
class Lap:
    number: int
    compound: str
    age: int
    time: float
    elapsed: float
    degradation: float


@dataclass(frozen=True)
class Result:
    laps: tuple[Lap, ...]

    @property
    def total(self):
        return self.laps[-1].elapsed


def validate_laps(laps):
    if type(laps) is not int or not 10 <= laps <= 100:
        raise ValueError("Race laps must be a whole number from 10 to 100.")


def simulate(base_time, laps, compound="S"):
    """Start on fresh tyres and keep the full race trace as they age."""
    number_in_range(base_time, "Base lap time", 30, 200)
    validate_laps(laps)
    validate_compound(compound)
    elapsed = 0.0
    records = []
    for number in range(1, laps + 1):
        age = number - 1
        seconds = lap_time(base_time, compound, age)
        elapsed += seconds
        records.append(Lap(number, compound, age, seconds, elapsed, tyre_loss(compound, age)))
    return Result(tuple(records))
