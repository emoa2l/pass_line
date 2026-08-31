"""Eric's ladder vs. his 2+2 and baselines."""
import random, statistics, os, sys
from concurrent.futures import ProcessPoolExecutor
from craps_engine import Game
import craps_strategies as S

SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 40_000
ROLLS, BANKROLL = 120, 1000

SPECS = [
    ("Eric ladder",             lambda: S.EricLadder()),
    ("2c+2dc flat cap100 ($25)",lambda: S.ComeDontComeCapped(25, 100)),
    ("1c+1dc flat cap100 ($25)",lambda: S.CappedFlex(unit=25, cap=100, n_come=1, n_dc=1)),
    ("Pass line only ($10)",    lambda: S.PassOnly()),
]

def run_one(args):
    label, idx, seed, n = args
    rng = random.Random(seed)
    nets, actions, busts, troughs = [], [], 0, []
    for _ in range(n):
        g = Game(SPECS[idx][1](), bankroll=BANKROLL, unit=10, rng=rng, max_rolls=ROLLS)
        r = g.run()
        tail = 0
        while g.bets.at_risk() > 0 and tail < 60:
            g.t.roll(); g.resolve(); tail += 1
        nets.append(g.bankroll + g.bets.at_risk() - BANKROLL)
        actions.append(g.action); busts += 1 if r["busted"] else 0
        troughs.append(r["trough"] - BANKROLL)
    return label, nets, actions, busts, troughs

if __name__ == "__main__":
    CHUNKS = 8
    per = SESSIONS // CHUNKS
    jobs = [(label, i, abs(hash((label, c))) % (2**31), per)
            for i, (label, _) in enumerate(SPECS) for c in range(CHUNKS)]
    agg = {l: {"nets": [], "actions": [], "busts": 0, "troughs": []} for l, _ in SPECS}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for label, nets, actions, busts, troughs in ex.map(run_one, jobs):
            a = agg[label]; a["nets"] += nets; a["actions"] += actions
            a["busts"] += busts; a["troughs"] += troughs
    print(f"{SESSIONS:,} sessions x {ROLLS} rolls | ${BANKROLL} bankroll\n")
    print(f"{'strategy':<28}{'mean$':>8}{'med$':>6}{'edge%':>7}{'win%':>6}{'bust%':>6}"
          f"{'p05':>7}{'p95':>6}{'sd':>5}{'act$':>7}{'maxDD':>7}")
    print("-" * 100)
    for label, _ in SPECS:
        a = agg[label]; nets = sorted(a["nets"]); n = len(nets)
        mean = statistics.mean(nets); act = statistics.mean(a["actions"])
        print(f"{label:<28}{mean:>8.1f}{nets[n//2]:>6.0f}{(-mean/act*100 if act else 0):>7.3f}"
              f"{sum(1 for x in nets if x>0)/n*100:>6.1f}{a['busts']/n*100:>6.2f}"
              f"{nets[int(n*0.05)]:>7.0f}{nets[int(n*0.95)]:>6.0f}{statistics.pstdev(nets):>5.0f}"
              f"{act:>7.0f}{statistics.mean(a['troughs']):>7.0f}")
