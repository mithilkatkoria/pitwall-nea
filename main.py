"""Stage 10: full illustrative race model and shared-condition comparison."""
import argparse

from circuits import load_circuits

from model import COMPOUND_PACE, lap_time, tyre_loss, simulate, Strategy, compare, optimise, Conditions

def main():
    parser = argparse.ArgumentParser(description="Pitwall: compound lap calculation")
    parser.add_argument("--base", type=float, default=None, help="Base lap seconds (30-200)")
    parser.add_argument("--compound", default="S", choices=COMPOUND_PACE, help="S=Soft, M=Medium, H=Hard")
    parser.add_argument("--age", type=int, default=0, help="Completed laps on these tyres (0-1000)")
    parser.add_argument("--laps", type=int, help="Simulate a full race of 10-100 laps")
    parser.add_argument("--compounds", nargs="+", choices=COMPOUND_PACE, help="One compound per stint")
    parser.add_argument("--stops", nargs="*", type=int, default=[], help="Increasing pit laps, at most two")
    parser.add_argument("--pit-loss", type=float, default=None, help="Pit lane loss in seconds (0-60)")
    parser.add_argument("--compare", action="store_true", help="Compare with plan B under shared settings")
    parser.add_argument("--compounds-b", nargs="+", choices=COMPOUND_PACE)
    parser.add_argument("--stops-b", nargs="*", type=int, default=[])
    parser.add_argument("--optimise", action="store_true", help="Search every different-compound one-stop plan")
    parser.add_argument("--wear", type=float, default=None)
    parser.add_argument("--temperature", type=int, default=30)
    parser.add_argument("--weather", choices=("Dry", "Damp", "Wet"), default="Dry")
    parser.add_argument("--pace", type=float, default=0, help="Driver A offset in seconds per racing lap")
    parser.add_argument("--pace-b", type=float, default=0)
    parser.add_argument("--sc-start", type=int, default=0, help="0 disables safety car")
    parser.add_argument("--sc-duration", type=int, default=3)
    parser.add_argument("--circuit", help="silverstone, monza or bahrain")
    args = parser.parse_args()
    try:
        profile = None
        if args.circuit:
            profile = next((c for c in load_circuits() if c.key == args.circuit), None)
            if profile is None:
                raise ValueError("Unknown circuit. Choose silverstone, monza or bahrain.")
        args.base = args.base if args.base is not None else (profile.base_time if profile else 90)
        args.laps = args.laps if args.laps is not None else (profile.laps if profile else None)
        args.wear = args.wear if args.wear is not None else (profile.wear if profile else 1)
        args.pit_loss = args.pit_loss if args.pit_loss is not None else (profile.pit_loss if profile else 22.5)
        conditions = Conditions(args.wear, args.temperature, args.weather, args.sc_start, args.sc_duration)
        if args.laps is None and (conditions != Conditions() or args.pace or args.pace_b):
            raise ValueError("Race conditions need --laps.")
        if args.pace_b and not args.compare:
            raise ValueError("Driver B pace needs --compare.")
        if args.optimise:
            if args.compare or args.compounds is not None or args.stops or args.compounds_b is not None or args.stops_b or args.age:
                raise ValueError("Search chooses the strategy; do not combine it with plan or age settings.")
            if args.laps is None:
                raise ValueError("Search needs --laps.")
            search = optimise(args.base, args.laps, args.pit_loss, conditions, args.pace)
            best = search.best
            print("PITWALL / stage 10 / one-stop search")
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
                result = compare(args.base, args.laps, plan, plan_b, args.pit_loss, conditions, args.pace, args.pace_b)
                print("PITWALL / stage 10 / comparison")
                print(f"A: {result.a.total:.3f} s; B: {result.b.total:.3f} s")
                print(f"B minus A: {result.gap:+.3f} s; faster: {result.winner}")
                print("Positive gap favours A; negative gap favours B. Same race settings.")
                print("LAP     A TIME      B TIME     CUMULATIVE B-A")
                for a, b, gap in zip(result.a.laps, result.b.laps, result.gaps):
                    print(f"{a.number:3}  {a.time:9.3f}   {b.time:9.3f}   {gap:+16.3f}")
                return
            result = simulate(args.base, args.laps, plan, args.pit_loss, conditions, args.pace)
            print("PITWALL / stage 10 / strategy")
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
    print("Use --laps for race simulation. Single-lap mode excludes race conditions; use --laps for the full model.")


if __name__ == "__main__":
    main()
