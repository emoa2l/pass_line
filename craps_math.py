"""Exact craps probabilities and house edges. No simulation -- closed form."""
from fractions import Fraction as F
from itertools import product

# --- Dice distribution -------------------------------------------------------
ROLLS = [(a + b) for a, b in product(range(1, 7), repeat=2)]
WAYS = {t: ROLLS.count(t) for t in range(2, 13)}
P = {t: F(WAYS[t], 36) for t in WAYS}

POINTS = (4, 5, 6, 8, 9, 10)

def p_make_point(pt):
    """P(roll pt before a 7), given point pt is established."""
    return F(WAYS[pt], WAYS[pt] + WAYS[7])

# --- Pass line ---------------------------------------------------------------
def pass_line_win():
    w = P[7] + P[11]
    for pt in POINTS:
        w += P[pt] * p_make_point(pt)
    return w

def dont_pass_win():
    """Bar 12: the 12 pushes."""
    w = P[2] + P[3]
    for pt in POINTS:
        w += P[pt] * (1 - p_make_point(pt))
    return w

def dont_pass_push():
    return P[12]

# --- Place / buy / lay odds --------------------------------------------------
PLACE_PAY = {4: F(9, 5), 5: F(7, 5), 6: F(7, 6), 8: F(7, 6), 9: F(7, 5), 10: F(9, 5)}
TRUE_ODDS = {4: F(2, 1), 5: F(3, 2), 6: F(6, 5), 8: F(6, 5), 9: F(3, 2), 10: F(2, 1)}

def place_edge(pt):
    p = p_make_point(pt)
    ev = p * PLACE_PAY[pt] - (1 - p)
    return -ev  # house edge as positive fraction of wager

def buy_edge(pt, commission=F(5, 100), on_win_only=False):
    """Buy bet: true odds minus 5% vig on the wager (or on wins only)."""
    p = p_make_point(pt)
    if on_win_only:
        ev = p * (TRUE_ODDS[pt] - commission) - (1 - p)
    else:
        ev = p * TRUE_ODDS[pt] - (1 - p) - commission
    return -ev

def lay_edge(pt, on_win_only=False):
    """Lay: bet against the point. Risk = TRUE_ODDS * win amount."""
    p = 1 - p_make_point(pt)          # P(7 first)
    risk = TRUE_ODDS[pt]              # laying this much to win 1
    vig = F(5, 100)                   # 5% of the win amount
    if on_win_only:
        ev = p * (1 - vig) - (1 - p) * risk
    else:
        ev = p * 1 - (1 - p) * risk - vig
    return -ev / risk                 # edge per unit at risk

# --- Field -------------------------------------------------------------------
def field_edge(double_12=True, triple_12=False):
    ev = F(0)
    for t, pr in P.items():
        if t in (3, 4, 9, 10, 11):
            ev += pr
        elif t == 2:
            ev += pr * 2
        elif t == 12:
            ev += pr * (3 if triple_12 else (2 if double_12 else 1))
        else:
            ev -= pr
    return -ev

# --- One-roll props ----------------------------------------------------------
PROPS = {
    "Any 7":       (P[7],                       F(4, 1)),
    "Any craps":   (P[2] + P[3] + P[12],        F(7, 1)),
    "Yo (11)":     (P[11],                      F(15, 1)),
    "Ace-deuce(3)":(P[3],                       F(15, 1)),
    "Snake eyes":  (P[2],                       F(30, 1)),
    "Boxcars(12)": (P[12],                      F(30, 1)),
    "C&E":         (None,                       None),
}

def prop_edge(p, pay):
    ev = p * pay - (1 - p)
    return -ev

# --- Hardways ----------------------------------------------------------------
HARD_PAY = {4: F(7, 1), 6: F(9, 1), 8: F(9, 1), 10: F(7, 1)}

def hardway_edge(n):
    """Hard n wins on hard n, loses on easy n or 7."""
    hard_ways = 1
    easy_ways = WAYS[n] - 1
    seven = WAYS[7]
    total = hard_ways + easy_ways + seven
    p = F(hard_ways, total)
    ev = p * HARD_PAY[n] - (1 - p)
    return -ev

# --- Combined pass + odds ----------------------------------------------------
def pass_with_odds_edge(mult):
    """House edge per unit of TOTAL action (flat + odds) at N x odds."""
    flat_ev = F(0)
    odds_ev = F(0)
    total_wagered = F(1)  # the flat bet, always
    flat_ev += P[7] + P[11] - P[2] - P[3] - P[12]
    odds_action = F(0)
    for pt in POINTS:
        p = p_make_point(pt)
        flat_ev += P[pt] * (p - (1 - p))
        # odds are a fair bet -> zero EV, but they add action
        odds_ev += 0
        odds_action += P[pt] * mult
    total_wagered += odds_action
    return -(flat_ev + odds_ev) / total_wagered

def pct(x):
    return float(x) * 100

if __name__ == "__main__":
    print("=" * 66)
    print("DICE DISTRIBUTION")
    print("=" * 66)
    for t in range(2, 13):
        bar = "#" * WAYS[t]
        print(f"  {t:>2}: {WAYS[t]} ways  {float(P[t])*100:5.2f}%  {bar}")

    print()
    print("=" * 66)
    print("POINT CONVERSION (P of making the point before a 7)")
    print("=" * 66)
    for pt in POINTS:
        p = p_make_point(pt)
        print(f"  Point {pt:>2}: {p}  = {float(p)*100:5.2f}%   true odds {TRUE_ODDS[pt]}")

    print()
    print("=" * 66)
    print("LINE BETS")
    print("=" * 66)
    pw = pass_line_win()
    print(f"  Pass line win prob : {pw} = {float(pw)*100:.4f}%")
    print(f"  Pass line edge     : {pct(1 - 2*pw):.4f}%")
    dw = dont_pass_win()
    dpush = dont_pass_push()
    dl = 1 - dw - dpush
    print(f"  Don't pass win     : {float(dw)*100:.4f}%  push {float(dpush)*100:.4f}%")
    print(f"  Don't pass edge    : {pct(dl - dw):.4f}%")

    print()
    print("=" * 66)
    print("PASS + FREE ODDS  (edge per unit of total action)")
    print("=" * 66)
    for m in [0, 1, 2, 3, 5, 10, 20, 100]:
        e = pass_with_odds_edge(F(m))
        print(f"  {m:>3}x odds : {pct(e):6.4f}%")

    print()
    print("=" * 66)
    print("PLACE BETS")
    print("=" * 66)
    for pt in POINTS:
        print(f"  Place {pt:>2}: pays {PLACE_PAY[pt]}  edge {pct(place_edge(pt)):6.3f}%")

    print()
    print("=" * 66)
    print("BUY / LAY  (5% vig on wager)")
    print("=" * 66)
    for pt in (4, 10):
        print(f"  Buy  {pt:>2}: edge {pct(buy_edge(pt)):6.3f}%   (vig on win only: {pct(buy_edge(pt, on_win_only=True)):6.3f}%)")
    for pt in (4, 10):
        print(f"  Lay  {pt:>2}: edge {pct(lay_edge(pt)):6.3f}%   (vig on win only: {pct(lay_edge(pt, on_win_only=True)):6.3f}%)")

    print()
    print("=" * 66)
    print("FIELD")
    print("=" * 66)
    print(f"  2:2x 12:2x : edge {pct(field_edge(double_12=True)):6.3f}%")
    print(f"  2:2x 12:3x : edge {pct(field_edge(triple_12=True)):6.3f}%")

    print()
    print("=" * 66)
    print("HARDWAYS")
    print("=" * 66)
    for n in (4, 6, 8, 10):
        print(f"  Hard {n:>2}: pays {HARD_PAY[n]}  edge {pct(hardway_edge(n)):6.3f}%")

    print()
    print("=" * 66)
    print("ONE-ROLL PROPS")
    print("=" * 66)
    for name, (p, pay) in PROPS.items():
        if p is None:
            continue
        print(f"  {name:<14}: pays {str(pay):<6} edge {pct(prop_edge(p, pay)):6.3f}%")
