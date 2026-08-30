"""Run every strategy over many sessions; report the outcome distribution.
Parallel across cores."""
import random, statistics, json, sys, os
from concurrent.futures import ProcessPoolExecutor
from craps_engine import Game
import craps_strategies as S

SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 20_000
ROLLS, BANKROLL, UNIT = 120, 1000, 10

SPECS = [
    ("Pass line only",          ("PassOnly", ())),
    ("Pass + 1x odds",          ("PassOdds", (1,))),
    ("Pass + 2x odds",          ("PassOdds", (2,))),
    ("Pass + 3x odds",          ("PassOdds", (3,))),
    ("Pass + 5x odds",          ("PassOdds", (5,))),
    ("Pass + 10x odds",         ("PassOdds", (10,))),
    ("Don't pass + 2x odds",    ("DontPassOdds", (2,))),
    ("Don't pass + 3x odds",    ("DontPassOdds", (3,))),
    ("3-Pt Molly (2 come, 2x)", ("PassComeOdds", (2, 2))),
    ("3-Pt Molly (2 come, 3x)", ("PassComeOdds", (2, 3))),
    ("Place 6 & 8",             ("Place68", ())),
    ("Inside numbers 5/6/8/9",  ("InsideNumbers", ())),
    ("Iron Cross",              ("IronCross", ())),
    ("Pass + craps hedge",      ("Hedged", ())),
    ("Pass + all hardways",     ("HardwaysAll", ())),
    ("Field every roll",        ("FieldOnly", ())),
    ("Martingale (pass)",       ("Martingale", ())),
    ("Any 7 every roll",        ("AnySeven", ())),
]

def run_one(args):
    label, cls, params, seed, n = args
    rng = random.Random(seed)
    nets, wagers, busts, troughs = [], [], 0, []
    ctor = getattr(S, cls)
    for _ in range(n):
        g = Game(ctor(*params), bankroll=BANKROLL, unit=UNIT, rng=rng, max_rolls=ROLLS)
        r = g.run()
        # Let standing bets play out rather than counting them undecided.
        tail = 0
        while g.bets.at_risk() > 0 and tail < 60:
            g.t.roll(); g.resolve(); tail += 1
        r["net"] = g.bankroll + g.bets.at_risk() - BANKROLL
        nets.append(r["net"]); wagers.append(g.action)
        busts += 1 if r["busted"] else 0
        troughs.append(r["trough"] - BANKROLL)
    return label, nets, wagers, busts, troughs

if __name__ == "__main__":
    CHUNKS = 10
    per = SESSIONS // CHUNKS
    jobs = []
    for label, (cls, params) in SPECS:
        for c in range(CHUNKS):
            jobs.append((label, cls, params, abs(hash((label, c))) % (2**31), per))

    agg = {label: {"nets": [], "wagers": [], "busts": 0, "troughs": []} for label, _ in SPECS}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for label, nets, wagers, busts, troughs in ex.map(run_one, jobs):
            a = agg[label]
            a["nets"] += nets; a["wagers"] += wagers
            a["busts"] += busts; a["troughs"] += troughs

    print(f"{SESSIONS:,} sessions x {ROLLS} rolls | ${BANKROLL} bankroll | ${UNIT} unit\n")
    print(f"{'strategy':<26}{'mean$':>8}{'med$':>7}{'edge%':>7}{'win%':>7}{'bust%':>7}"
          f"{'p05':>7}{'p95':>7}{'sd':>7}{'action$':>9}{'maxDD':>7}")
    print("-" * 105)
    results = {}
    for label, _ in SPECS:
        a = agg[label]
        nets = sorted(a["nets"]); n = len(nets)
        r = {
            "mean": statistics.mean(nets), "median": nets[n//2],
            "sd": statistics.pstdev(nets),
            "p05": nets[int(n*0.05)], "p95": nets[int(n*0.95)],
            "best": nets[-1], "worst": nets[0],
            "win_rate": sum(1 for x in nets if x > 0)/n*100,
            "bust_rate": a["busts"]/n*100,
            "avg_wagered": statistics.mean(a["wagers"]),
            "edge": -statistics.mean(nets)/statistics.mean(a["wagers"])*100,
            "avg_dd": statistics.mean(a["troughs"]),
        }
        results[label] = r
        print(f"{label:<26}{r['mean']:>8.1f}{r['median']:>7.0f}{r['edge']:>7.2f}{r['win_rate']:>7.1f}"
              f"{r['bust_rate']:>7.1f}{r['p05']:>7.0f}{r['p95']:>7.0f}{r['sd']:>7.0f}"
              f"{r['avg_wagered']:>9.0f}{r['avg_dd']:>7.0f}")
    json.dump(results, open("results.json", "w"), indent=1)
    print("\nSaved -> results.json")
