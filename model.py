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
    pit: float = 0.0


@dataclass(frozen=True)
class Result:
    laps: tuple[Lap, ...]

    @property
    def total(self):
        return self.laps[-1].elapsed


def validate_laps(laps):
    if type(laps) is not int or not 10 <= laps <= 100:
        raise ValueError("Race laps must be a whole number from 10 to 100.")


@dataclass(frozen=True)
class Strategy:
    compounds: tuple[str, ...] = ("S",)
    stops: tuple[int, ...] = ()

    def validate(self, laps):
        validate_laps(laps)
        if not isinstance(self.compounds, tuple) or not isinstance(self.stops, tuple):
            raise ValueError("Compounds and stops must be tuples in stint order.")
        if not 0 <= len(self.stops) <= 2 or len(self.compounds) != len(self.stops) + 1:
            raise ValueError("Choose 0-2 stops and one compound per stint.")
        for compound in self.compounds:
            validate_compound(compound)
        previous = 0
        for stop in self.stops:
            if type(stop) is not int or not previous < stop < laps:
                raise ValueError("Pit laps must increase uniquely from 1 to the penultimate lap.")
            previous = stop


def simulate(base_time, laps, plan=Strategy(), pit_loss=22.5):
    """Validate once, then record each lap before changing stint or age."""
    number_in_range(base_time, "Base lap time", 30, 200)
    if not isinstance(plan, Strategy):
        raise ValueError("A Strategy is required.")
    plan.validate(laps)
    number_in_range(pit_loss, "Pit loss", 0, 60)
    elapsed = 0.0
    records = []
    age = 0
    stint = 0
    for number in range(1, laps + 1):
        compound = plan.compounds[stint]
        stopping = number in plan.stops
        pit = pit_loss if stopping else 0.0
        seconds = lap_time(base_time, compound, age) + pit
        elapsed += seconds
        records.append(Lap(number, compound, age, seconds, elapsed, tyre_loss(compound, age), pit))
        if stopping:
            stint += 1
            age = 0
        else:
            age += 1
    return Result(tuple(records))
