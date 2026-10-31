"""Stage 2: a validated base lap time, before tyre and race effects."""
import argparse
from math import isfinite


def number_in_range(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    # Compare bounds before converting huge integers through isfinite.
    if not lower <= value <= upper or not isfinite(value):
        raise ValueError(f"{name} must be between {lower} and {upper}.")
    return value


def lap_time(base_time):
    """The first model includes only base pace, in seconds."""
    return number_in_range(base_time, "Base lap time", 30, 200)


def main():
    parser = argparse.ArgumentParser(description="Pitwall: base lap calculation")
    parser.add_argument("--base", type=float, default=90, help="Base lap seconds (30-200)")
    args = parser.parse_args()
    try:
        seconds = lap_time(args.base)
    except ValueError as error:
        parser.error(str(error))
    print("PITWALL / stage 2 / base-only model")
    print(f"Base lap time: {seconds:.3f} s")
    print("Tyres, wear, fuel and pit stops are not modelled in this version.")


if __name__ == "__main__":
    main()
