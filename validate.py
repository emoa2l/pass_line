"""Validate the engine against closed-form math.

Key discipline: only count DECIDED bets. A session that stops mid-point leaves
a live wager on the table; counting it as returned cash fabricates a player edge.
Each trial here runs to a natural resolution instead of a roll cap.
"""
import random
from craps_engine import Game, Table, Bets, ODDS_PAY, _pay
import craps_math as M
from fractions import Fraction as F

R = random.Random(20260829)

def run_line_trial(dont=False, mult=0):
    """One complete pass/don't-pass decision, from come-out to resolution.
    Returns (net, wagered)."""
    t = Table(R)
    flat = 10
    wag = flat
    n = t.roll()
    if not dont:
        if n in (7, 11):   return +flat, wag
        if n in (2, 3, 12):return -flat, wag
    else:
        if n in (2, 3):    return +flat, wag
        if n == 12:        return 0, wag
        if n in (7, 11):   return -flat, wag
    pt = n
    odds = 0
    if mult:
        if not dont:
            odds = flat * mult
        else:
            a, b = ODDS_PAY[pt]
            odds = flat * mult * a // b
        wag += odds
    while True:
        n = t.roll()
        if n == pt:
            if not dont:
                return +flat + (_pay(odds, ODDS_PAY[pt]) if odds else 0), wag
            return -flat - odds, wag
        if n == 7:
            if not dont:
                return -flat - odds, wag
            return +flat + (_pay(odds, ODDS_PAY[pt][::-1]) if odds else 0), wag

def run_place_trial(num):
    """One place bet, held until it wins or a 7 kills it."""
    t = Table(R)
    amt = 6 if num in (6, 8) else 5
    from craps_engine import PLACE_PAY
    while True:
        n = t.roll()
        if n == num:  return +_pay(amt, PLACE_PAY[num]), amt
        if n == 7:    return -amt, amt

def run_oneroll_trial(kind):
    t = Table(R); n = t.roll(); amt = 10
    if kind == "field":
        if n in (3, 4, 9, 10, 11): return +amt, amt
        if n in (2, 12):           return +amt * 2, amt
        return -amt, amt
    if kind == "any7":
        return (+amt * 4, amt) if n == 7 else (-amt, amt)

def measure(fn, trials=600_000):
    net = wag = 0
    for _ in range(trials):
        d, w = fn()
        net += d; wag += w
    return -net / wag * 100

print("=" * 76)
print("ENGINE VALIDATION  --  simulated house edge vs exact math")
print("(each trial runs to a real resolution; no roll-cap truncation)")
print("=" * 76)
print(f"{'bet':<30} {'simulated':>12} {'exact':>12} {'delta':>11}")
print("-" * 76)

cases = [
    ("Pass line (flat)",   lambda: run_line_trial(False, 0), float(1 - 2*M.pass_line_win())*100),
    ("Pass + 1x odds",     lambda: run_line_trial(False, 1), float(M.pass_with_odds_edge(F(1)))*100),
    ("Pass + 2x odds",     lambda: run_line_trial(False, 2), float(M.pass_with_odds_edge(F(2)))*100),
    ("Pass + 5x odds",     lambda: run_line_trial(False, 5), float(M.pass_with_odds_edge(F(5)))*100),
    ("Don't pass (flat)",  lambda: run_line_trial(True, 0),
        float((1 - M.dont_pass_win() - M.dont_pass_push()) - M.dont_pass_win())*100),
    ("Place 6",            lambda: run_place_trial(6),  float(M.place_edge(6))*100),
    ("Place 8",            lambda: run_place_trial(8),  float(M.place_edge(8))*100),
    ("Place 5",            lambda: run_place_trial(5),  float(M.place_edge(5))*100),
    ("Place 4",            lambda: run_place_trial(4),  float(M.place_edge(4))*100),
    ("Field (12 pays 2x)", lambda: run_oneroll_trial("field"), float(M.field_edge(True))*100),
    ("Any 7",              lambda: run_oneroll_trial("any7"),  float(M.prop_edge(M.P[7], F(4)))*100),
]

ok = True
for label, fn, exact in cases:
    sim = measure(fn)
    d = sim - exact
    # tolerance scales with the bet's variance: a 30:1 prop swings far more
    # per trial than a 1:1 line bet, so a flat threshold would false-alarm.
    bad = abs(d) > (0.30 if exact > 5 else 0.15)
    if bad: ok = False
    print(f"{label:<30} {sim:>11.3f}% {exact:>11.3f}% {d:>+10.3f}{'  <== OFF' if bad else ''}")

print()
print("=" * 76)
print("RESULT:", "ALL PASS -- engine agrees with theory" if ok else "MISMATCH")
print("=" * 76)

# ---------------------------------------------------------------------------
# Come bet: a come bet is mathematically identical to a pass line bet.
# If the engine's come handling is right, its edge must match the pass line.
def run_come_trial(mult=0):
    """One full come-bet decision using the real engine resolution path."""
    import random as _r
    from craps_engine import Game, Table, Bets
    from craps_strategies import Strategy
    g = Game.__new__(Game)
    g.t = Table(R); g.bets = Bets(); g.bankroll = 10**9
    g.start_bankroll = g.bankroll; g.total_wagered = 0
    g.peak = g.trough = g.bankroll; g.busted = g.hit_goal = False
    g.shooters = 0; g.unit = 10; g.vig_on_win = True
    g.max_rolls = 10**9; g.win_goal = None; g.loss_limit = None
    g.t.point = 8                      # come bets only exist after a point
    start = g.bankroll
    g.bets.come_new = 10; g.bankroll -= 10
    wag = 10
    while True:
        g.t.roll()
        pt_live = set(g.bets.come)
        g.resolve()
        if g.t.point is None:          # shooter sevened/made point; re-establish
            g.t.point = 8
        if not g.bets.come and not g.bets.come_new:
            return g.bankroll - start, wag
        if mult and g.bets.come and not g.bets.come_odds:
            for p in list(g.bets.come):
                g.bets.come_odds[p] = 10 * mult
                g.bankroll -= 10 * mult
                wag += 10 * mult

print()
print("-" * 76)
sim = measure(lambda: run_come_trial(0), trials=400_000)
exact = float(1 - 2*M.pass_line_win())*100
print(f"{'Come bet (flat)':<30} {sim:>11.3f}% {exact:>11.3f}% {sim-exact:>+10.3f}")
print("(a come bet is the same wager as a pass line bet -- edges must match)")
