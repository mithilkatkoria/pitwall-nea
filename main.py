"""Stage 4: compound pace and tyre degradation at a chosen age."""
import argparse
from math import isfinite

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


def main():
    parser = argparse.ArgumentParser(description="Pitwall: compound lap calculation")
    parser.add_argument("--base", type=float, default=90, help="Base lap seconds (30-200)")
    parser.add_argument("--compound", default="S", choices=COMPOUND_PACE, help="S=Soft, M=Medium, H=Hard")
    parser.add_argument("--age", type=int, default=0, help="Completed laps on these tyres (0-1000)")
    args = parser.parse_args()
    try:
        seconds = lap_time(args.base, args.compound, args.age)
    except ValueError as error:
        parser.error(str(error))
    print("PITWALL / stage 4 / tyre degradation")
    print(f"Compound: {args.compound}; age: {args.age}; lap time: {seconds:.3f} s")
    print(f"Tyre degradation: {tyre_loss(args.compound, args.age):.3f} s")
    print("Fuel, warmup, conditions and pit stops arrive in later versions.")


if __name__ == "__main__":
    main()
