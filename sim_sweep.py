"""Sweep capped-strategy variants hunting for smooth: low sd, no busts, best mean."""
import random, statistics, os, sys
from concurrent.futures import ProcessPoolExecutor
from craps_engine import Game
import craps_strategies as S

SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 40_000
ROLLS, BANKROLL, UNIT = 120, 1000, 25

# (label, kwargs for CappedFlex)
SPECS = [
    ("A  2c+2dc flat, cap100 (yours)",   dict(n_come=2,n_dc=2)),
    ("B  1c+1dc flat, cap100",           dict(n_come=1,n_dc=1)),
    ("C  1c(2xO)+1dc, cap100",           dict(n_come=1,n_dc=1,come_odds=2)),
    ("D  1c(2xO)+1dc(2xL), cap150",      dict(n_come=1,n_dc=1,come_odds=2,dc_lay=2,cap=150)),
    ("E  pass2xO+1c(2xO), no dc, cap150",dict(n_come=1,n_dc=0,come_odds=2,pass_odds=2,cap=150)),
    ("F  2c(2xO), no dc, cap200",        dict(n_come=2,n_dc=0,come_odds=2,cap=200)),
    ("G  2c+2dc flat, cap150",           dict(n_come=2,n_dc=2,cap=150)),
    ("H  pass2xO only, cap100",          dict(n_come=0,n_dc=0,pass_odds=2)),
    ("I  1c+2dc flat, cap100",           dict(n_come=1,n_dc=2)),
    ("J  pass2xO+1c(2xO)+1dc, cap200",   dict(n_come=1,n_dc=1,come_odds=2,pass_odds=2,cap=200)),
]

def run_one(args):
    label, kw, seed, n = args
    rng = random.Random(seed)
    nets, actions, busts, troughs = [], [], 0, []
    for _ in range(n):
        g = Game(S.CappedFlex(unit=UNIT, **kw), bankroll=BANKROLL, unit=UNIT, rng=rng, max_rolls=ROLLS)
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
    jobs = [(label, kw, abs(hash((label, c))) % (2**31), per)
            for label, kw in SPECS for c in range(CHUNKS)]
    agg = {l: {"nets": [], "actions": [], "busts": 0, "troughs": []} for l, _ in SPECS}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for label, nets, actions, busts, troughs in ex.map(run_one, jobs):
            a = agg[label]; a["nets"] += nets; a["actions"] += actions
            a["busts"] += busts; a["troughs"] += troughs
    print(f"{SESSIONS:,} sessions x {ROLLS} rolls | ${BANKROLL} bankroll | ${UNIT} unit\n")
    print(f"{'variant':<36}{'mean$':>7}{'med$':>6}{'edge%':>7}{'win%':>6}{'bust%':>6}"
          f"{'p05':>6}{'p95':>6}{'sd':>5}{'act$':>6}{'maxDD':>7}")
    print("-" * 105)
    rows=[]
    for label, _ in SPECS:
        a = agg[label]; nets = sorted(a["nets"]); n = len(nets)
        mean = statistics.mean(nets); act = statistics.mean(a["actions"])
        sd = statistics.pstdev(nets)
        rows.append((label, mean, nets[n//2], (-mean/act*100 if act else 0),
                     sum(1 for x in nets if x>0)/n*100, a["busts"]/n*100,
                     nets[int(n*0.05)], nets[int(n*0.95)], sd, act,
                     statistics.mean(a["troughs"])))
    for r in sorted(rows, key=lambda r: r[1], reverse=True):
        print(f"{r[0]:<36}{r[1]:>7.1f}{r[2]:>6.0f}{r[3]:>7.3f}{r[4]:>6.1f}{r[5]:>6.2f}"
              f"{r[6]:>6.0f}{r[7]:>6.0f}{r[8]:>5.0f}{r[9]:>6.0f}{r[10]:>7.0f}")
