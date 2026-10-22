"""Stage 8: compare two strategies under shared race settings."""
import argparse

from model import COMPOUND_PACE, lap_time, tyre_loss, simulate, Strategy, compare, optimise

def main():
    parser = argparse.ArgumentParser(description="Pitwall: compound lap calculation")
    parser.add_argument("--base", type=float, default=90, help="Base lap seconds (30-200)")
    parser.add_argument("--compound", default="S", choices=COMPOUND_PACE, help="S=Soft, M=Medium, H=Hard")
    parser.add_argument("--age", type=int, default=0, help="Completed laps on these tyres (0-1000)")
    parser.add_argument("--laps", type=int, help="Simulate a full race of 10-100 laps")
    parser.add_argument("--compounds", nargs="+", choices=COMPOUND_PACE, help="One compound per stint")
    parser.add_argument("--stops", nargs="*", type=int, default=[], help="Increasing pit laps, at most two")
    parser.add_argument("--pit-loss", type=float, default=22.5, help="Pit lane loss in seconds (0-60)")
    parser.add_argument("--compare", action="store_true", help="Compare with plan B under shared settings")
    parser.add_argument("--compounds-b", nargs="+", choices=COMPOUND_PACE)
    parser.add_argument("--stops-b", nargs="*", type=int, default=[])
    parser.add_argument("--optimise", action="store_true", help="Search every different-compound one-stop plan")
    args = parser.parse_args()
    try:
        if args.optimise:
            if args.compare or args.compounds is not None or args.stops or args.compounds_b is not None or args.stops_b or args.age:
                raise ValueError("Search chooses the strategy; do not combine it with plan or age settings.")
            if args.laps is None:
                raise ValueError("Search needs --laps.")
            search = optimise(args.base, args.laps, args.pit_loss)
            best = search.best
            print("PITWALL / stage 9 / one-stop search")
            print(f"Checked {len(search.candidates)} candidates: 6 x (laps - 1).")
            print(f"Best: {' > '.join(best.plan.compounds)}, stop {best.plan.stops[0]}; {best.total:.3f} s")
            print("One stop, two different compounds only. Ties within 1e-8 s keep the first enumerated plan.")
            return
        if (args.compounds_b is not None or args.stops_b) and not args.compare:
            raise ValueError("Plan B needs --compare.")
        if args.compare and args.laps is None:
            raise ValueError("Comparison needs --laps.")
        if args.laps is None and (args.compounds is not None or args.stops or args.pit_loss != 22.5):
            raise ValueError("Pit settings need --laps.")
        if args.laps is not None:
            if args.age != 0:
                raise ValueError("A complete race starts on fresh tyres; use --age 0.")
            plan = Strategy(tuple(args.compounds or [args.compound]), tuple(args.stops))
            if args.compare:
                plan_b = Strategy(tuple(args.compounds_b or ["M"]), tuple(args.stops_b))
                result = compare(args.base, args.laps, plan, plan_b, args.pit_loss)
                print("PITWALL / stage 8 / comparison")
                print(f"A: {result.a.total:.3f} s; B: {result.b.total:.3f} s")
                print(f"B minus A: {result.gap:+.3f} s; faster: {result.winner}")
                print("Positive gap favours A; negative gap favours B. Same race settings.")
                print("LAP     A TIME      B TIME     CUMULATIVE B-A")
                for a, b, gap in zip(result.a.laps, result.b.laps, result.gaps):
                    print(f"{a.number:3}  {a.time:9.3f}   {b.time:9.3f}   {gap:+16.3f}")
                return
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
