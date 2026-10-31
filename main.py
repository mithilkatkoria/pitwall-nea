"""Stage 5: single-lap calculations and a complete race loop."""
import argparse

from model import COMPOUND_PACE, lap_time, tyre_loss, simulate

def main():
    parser = argparse.ArgumentParser(description="Pitwall: compound lap calculation")
    parser.add_argument("--base", type=float, default=90, help="Base lap seconds (30-200)")
    parser.add_argument("--compound", default="S", choices=COMPOUND_PACE, help="S=Soft, M=Medium, H=Hard")
    parser.add_argument("--age", type=int, default=0, help="Completed laps on these tyres (0-1000)")
    parser.add_argument("--laps", type=int, help="Simulate a full race of 10-100 laps")
    args = parser.parse_args()
    try:
        if args.laps is not None:
            if args.age != 0:
                raise ValueError("A complete race starts on fresh tyres; use --age 0.")
            result = simulate(args.base, args.laps, args.compound)
            print("PITWALL / stage 5 / base, compound and degradation")
            print("LAP  TYRE  AGE     LAP TIME     ELAPSED     TYRE LOSS")
            for lap in result.laps:
                print(f"{lap.number:3}  {lap.compound:4}  {lap.age:3}  {lap.time:11.3f}  {lap.elapsed:10.3f}  {lap.degradation:12.3f}")
            print(f"Race total: {result.total:.3f} s")
            return
        seconds = lap_time(args.base, args.compound, args.age)
    except ValueError as error:
        parser.error(str(error))
    print("PITWALL / stage 4 / tyre degradation")
    print(f"Compound: {args.compound}; age: {args.age}; lap time: {seconds:.3f} s")
    print(f"Tyre degradation: {tyre_loss(args.compound, args.age):.3f} s")
    print("Fuel, warmup, conditions and pit stops arrive in later versions.")


if __name__ == "__main__":
    main()
