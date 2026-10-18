"""Stage 3: base pace and a chosen tyre compound."""
import argparse
from math import isfinite

COMPOUND_PACE = {"S": 0.0, "M": 0.48, "H": 1.0}


def number_in_range(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    # Compare bounds before converting huge integers through isfinite.
    if not lower <= value <= upper or not isfinite(value):
        raise ValueError(f"{name} must be between {lower} and {upper}.")
    return value


def lap_time(base_time, compound="S"):
    """Return base pace plus the compound offset, in seconds."""
    number_in_range(base_time, "Base lap time", 30, 200)
    if not isinstance(compound, str) or compound not in COMPOUND_PACE:
        raise ValueError("Compound must be S, M or H.")
    return base_time + COMPOUND_PACE[compound]


def main():
    parser = argparse.ArgumentParser(description="Pitwall: compound lap calculation")
    parser.add_argument("--base", type=float, default=90, help="Base lap seconds (30-200)")
    parser.add_argument("--compound", default="S", choices=COMPOUND_PACE, help="S=Soft, M=Medium, H=Hard")
    args = parser.parse_args()
    try:
        seconds = lap_time(args.base, args.compound)
    except ValueError as error:
        parser.error(str(error))
    print("PITWALL / stage 3 / base and compound")
    print(f"Compound: {args.compound}; lap time: {seconds:.3f} s")
    print("Wear, fuel and pit stops are not modelled in this version.")


if __name__ == "__main__":
    main()
