"""Stage 7: configurable zero-, one- and two-stop strategies."""
import argparse

from model import COMPOUND_PACE, lap_time, tyre_loss, simulate, Strategy

def main():
    parser = argparse.ArgumentParser(description="Pitwall: compound lap calculation")
    parser.add_argument("--base", type=float, default=90, help="Base lap seconds (30-200)")
    parser.add_argument("--compound", default="S", choices=COMPOUND_PACE, help="S=Soft, M=Medium, H=Hard")
    parser.add_argument("--age", type=int, default=0, help="Completed laps on these tyres (0-1000)")
    parser.add_argument("--laps", type=int, help="Simulate a full race of 10-100 laps")
    parser.add_argument("--compounds", nargs="+", choices=COMPOUND_PACE, help="One compound per stint")
    parser.add_argument("--stops", nargs="*", type=int, default=[], help="Increasing pit laps, at most two")
    parser.add_argument("--pit-loss", type=float, default=22.5, help="Pit lane loss in seconds (0-60)")
    args = parser.parse_args()
    try:
        if args.laps is None and (args.compounds is not None or args.stops or args.pit_loss != 22.5):
            raise ValueError("Pit settings need --laps.")
        if args.laps is not None:
            if args.age != 0:
                raise ValueError("A complete race starts on fresh tyres; use --age 0.")
            plan = Strategy(tuple(args.compounds or [args.compound]), tuple(args.stops))
            result = simulate(args.base, args.laps, plan, args.pit_loss)
            print("PITWALL / stage 7 / strategy")
            print("LAP  TYRE  AGE     LAP TIME     ELAPSED     TYRE LOSS     PIT LOSS")
            for lap in result.laps:
                print(f"{lap.number:3}  {lap.compound:4}  {lap.age:3}  {lap.time:11.3f}  {lap.elapsed:10.3f}  {lap.degradation:12.3f}  {lap.pit:11.3f}")
            print(f"Race total: {result.total:.3f} s")
            return
        seconds = lap_time(args.base, args.compound, args.age)
    except ValueError as error:
        parser.error(str(error))
    print("PITWALL / stage 4 / tyre degradation")
    print(f"Compound: {args.compound}; age: {args.age}; lap time: {seconds:.3f} s")
    print(f"Tyre degradation: {tyre_loss(args.compound, args.age):.3f} s")
    print("Use --laps for race simulation. Fuel, warmup and conditions arrive later.")


if __name__ == "__main__":
    main()
