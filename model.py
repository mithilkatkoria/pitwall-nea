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
    fuel: float = 0.0
    warmup: float = 0.0
    base: float = 0.0
    compound_pace: float = 0.0
    weather: float = 0.0
    driver: float = 0.0
    safety_car: bool = False


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


@dataclass(frozen=True)
class Conditions:
    wear: float = 1.0
    temperature: int = 30
    weather: str = "Dry"
    sc_start: int = 0
    sc_duration: int = 3

    def validate(self, laps):
        validate_laps(laps)
        number_in_range(self.wear, "Wear multiplier", 0.1, 3)
        if type(self.temperature) is not int or not 15 <= self.temperature <= 50:
            raise ValueError("Track temperature must be a whole number from 15 to 50 C.")
        if not isinstance(self.weather, str) or self.weather not in ("Dry", "Damp", "Wet"):
            raise ValueError("Weather must be Dry, Damp or Wet.")
        if type(self.sc_start) is not int or not 0 <= self.sc_start <= laps:
            raise ValueError("Safety car start must be 0 (off) or a race lap.")
        if type(self.sc_duration) is not int or not 1 <= self.sc_duration <= 10:
            raise ValueError("Safety car duration must be 1-10 whole laps.")
        if self.sc_start and self.sc_start + self.sc_duration - 1 > laps:
            raise ValueError("Safety car period extends past the race.")

    def neutralised(self, lap):
        return self.sc_start > 0 and self.sc_start <= lap < self.sc_start + self.sc_duration


def simulate(base_time, laps, plan=Strategy(), pit_loss=22.5, conditions=Conditions(), pace=0.0):
    """Validate once, then record each lap before changing stint or age."""
    number_in_range(base_time, "Base lap time", 30, 200)
    if not isinstance(plan, Strategy):
        raise ValueError("A Strategy is required.")
    plan.validate(laps)
    number_in_range(pit_loss, "Pit loss", 0, 60)
    if not isinstance(conditions, Conditions):
        raise ValueError("Conditions are required.")
    conditions.validate(laps)
    number_in_range(pace, "Driver pace", -2, 2)
    elapsed = 0.0
    records = []
    age = 0
    stint = 0
    for number in range(1, laps + 1):
        compound = plan.compounds[stint]
        stopping = number in plan.stops
        pit = pit_loss if stopping else 0.0
        fuel = (laps - number) * 1.6 * 0.03
        warmup = 0.55 if age == 0 else 0.0
        degradation = tyre_loss(compound, age) * conditions.wear * (1 + (conditions.temperature-30)*.018)
        weather = {"Dry": 0, "Damp": 5, "Wet": 14}[conditions.weather]
        base, compound_pace, driver = base_time, COMPOUND_PACE[compound], pace
        safety_car = conditions.neutralised(number)
        if safety_car:
            base = base_time * 1.4
            fuel *= .25
            compound_pace = degradation = warmup = driver = weather = 0.0
            if stopping:
                service = min(2.5, pit_loss)
                pit = service + .6 * (pit_loss - service)
        seconds = base + compound_pace + degradation + pit + fuel + warmup + driver + weather
        elapsed += seconds
        records.append(Lap(number, compound, age, seconds, elapsed, degradation, pit, fuel, warmup, base, compound_pace, weather, driver, safety_car))
        if stopping:
            stint += 1
            age = 0
        else:
            age += 1
    return Result(tuple(records))


@dataclass(frozen=True)
class Comparison:
    a: Result
    b: Result

    @property
    def gap(self):
        return self.b.total - self.a.total

    @property
    def winner(self):
        if abs(self.gap) <= 1e-8:
            return "Tie"
        return "A" if self.gap > 0 else "B"

    @property
    def gaps(self):
        return tuple(b.elapsed - a.elapsed for a, b in zip(self.a.laps, self.b.laps))


def compare(base_time, laps, plan_a, plan_b, pit_loss=22.5, conditions=Conditions(), pace_a=0.0, pace_b=0.0):
    """Both simulations receive the same race settings."""
    return Comparison(simulate(base_time, laps, plan_a, pit_loss, conditions, pace_a),
                      simulate(base_time, laps, plan_b, pit_loss, conditions, pace_b))


@dataclass(frozen=True)
class Candidate:
    plan: Strategy
    total: float


@dataclass(frozen=True)
class Search:
    best: Candidate
    candidates: tuple[Candidate, ...]


def optimise(base_time, laps, pit_loss=22.5, conditions=Conditions(), pace=0.0):
    """Exhaustively search only one stop and two different compounds."""
    number_in_range(base_time, "Base lap time", 30, 200)
    validate_laps(laps)
    number_in_range(pit_loss, "Pit loss", 0, 60)
    candidates = []
    best = None
    for first in COMPOUND_PACE:
        for second in COMPOUND_PACE:
            if first == second:
                continue
            for stop in range(1, laps):
                plan = Strategy((first, second), (stop,))
                candidate = Candidate(plan, simulate(base_time, laps, plan, pit_loss, conditions, pace).total)
                candidates.append(candidate)
                if best is None or candidate.total < best.total - 1e-8:
                    best = candidate
    return Search(best, tuple(candidates))
