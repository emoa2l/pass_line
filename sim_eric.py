"""Eric's 2-come/2-DC capped strategy vs. baselines, at his stakes."""
import random, statistics, os, sys
from concurrent.futures import ProcessPoolExecutor
from craps_engine import Game
import craps_strategies as S

SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
ROLLS, BANKROLL, UNIT = 120, 1000, 25

SPECS = [
    ("2 come + 2 DC, $100 cap", ("ComeDontComeCapped", (25, 100))),
    ("Pass line only",          ("PassOnly", ())),
    ("3-Pt Molly (2 come, 2x)", ("PassComeOdds", (2, 2))),
    ("Don't pass + 3x odds",    ("DontPassOdds", (3,))),
]

def run_one(args):
    label, cls, params, seed, n = args
    rng = random.Random(seed)
    ctor = getattr(S, cls)
    nets, actions, busts, troughs, shooters = [], [], 0, [], 0
    for _ in range(n):
        g = Game(ctor(*params), bankroll=BANKROLL, unit=UNIT, rng=rng, max_rolls=ROLLS)
        r = g.run()
        tail = 0
        while g.bets.at_risk() > 0 and tail < 60:
            g.t.roll(); g.resolve(); tail += 1
        net = g.bankroll + g.bets.at_risk() - BANKROLL
        nets.append(net); actions.append(g.action)
        busts += 1 if r["busted"] else 0
        troughs.append(r["trough"] - BANKROLL); shooters += r["shooters"]
    return label, nets, actions, busts, troughs, shooters

if __name__ == "__main__":
    CHUNKS = 10
    per = SESSIONS // CHUNKS
    jobs = [(label, cls, params, abs(hash((label, c))) % (2**31), per)
            for label, (cls, params) in SPECS for c in range(CHUNKS)]
    agg = {l: {"nets": [], "actions": [], "busts": 0, "troughs": [], "shooters": 0} for l, _ in SPECS}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for label, nets, actions, busts, troughs, shooters in ex.map(run_one, jobs):
            a = agg[label]
            a["nets"] += nets; a["actions"] += actions
            a["busts"] += busts; a["troughs"] += troughs; a["shooters"] += shooters
    print(f"{SESSIONS:,} sessions x {ROLLS} rolls | ${BANKROLL} bankroll | ${UNIT} unit\n")
    print(f"{'strategy':<28}{'mean$':>8}{'med$':>7}{'edge%':>7}{'win%':>7}{'bust%':>7}"
          f"{'p05':>8}{'p95':>7}{'sd':>7}{'action$':>9}{'maxDD':>8}")
    print("-" * 110)
    for label, _ in SPECS:
        a = agg[label]
        nets = sorted(a["nets"]); n = len(nets)
        mean = statistics.mean(nets)
        act = statistics.mean(a["actions"])
        print(f"{label:<28}{mean:>8.2f}{nets[n//2]:>7.0f}{(-mean/act*100 if act else 0):>7.3f}"
              f"{sum(1 for x in nets if x>0)/n*100:>7.1f}{a['busts']/n*100:>7.2f}"
              f"{nets[int(n*0.05)]:>8.0f}{nets[int(n*0.95)]:>7.0f}{statistics.pstdev(nets):>7.0f}"
              f"{act:>9.0f}{statistics.mean(a['troughs']):>8.0f}")
