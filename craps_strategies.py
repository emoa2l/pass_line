"""Craps strategies, each a class with place_bets(game) called before every roll."""
from craps_engine import POINTS

def _six_eight_amt(unit):
    """Place 6/8 in multiples of 6 so the 7:6 pays clean."""
    return max(6, (unit // 6) * 6 or 6)

def _five_nine_amt(unit):
    return max(5, (unit // 5) * 5 or 5)


class Strategy:
    name = "base"
    desc = ""
    def place_bets(self, g): raise NotImplementedError


# ---------------------------------------------------------------- LINE ONLY
class PassOnly(Strategy):
    name = "Pass Line only"
    desc = "Flat pass line, no odds. The baseline."
    def place_bets(self, g):
        if g.t.is_comeout and not g.bets.pass_line:
            g.bets.pass_line = g.wager(g.unit)


class PassOdds(Strategy):
    name = "Pass + {m}x Odds"
    desc = "Pass line backed with free odds -- the lowest-edge play in the house."
    def __init__(self, mult=3):
        self.mult = mult
        self.name = f"Pass + {mult}x Odds"
    def place_bets(self, g):
        b = g.bets
        if g.t.is_comeout and not b.pass_line:
            b.pass_line = g.wager(g.unit)
        if not g.t.is_comeout and b.pass_line and not b.pass_odds:
            b.pass_odds = g.wager(g.unit * self.mult)


class DontPassOdds(Strategy):
    name = "Don't Pass + {m}x Odds"
    desc = "Betting against the shooter, laying odds behind."
    def __init__(self, mult=3):
        self.mult = mult
        self.name = f"Don't Pass + {mult}x Odds"
    def place_bets(self, g):
        b = g.bets
        if g.t.is_comeout and not b.dont_pass:
            b.dont_pass = g.wager(g.unit)
        if not g.t.is_comeout and b.dont_pass and not b.dont_odds:
            pt = g.t.point
            # lay odds: risk more to win less
            from craps_engine import ODDS_PAY
            n, d = ODDS_PAY[pt]
            b.dont_odds = g.wager(g.unit * self.mult * n // d)


# ---------------------------------------------------------------- COME
class PassComeOdds(Strategy):
    """The classic 'three-point molly': pass + two come bets, all with odds."""
    def __init__(self, comes=2, mult=2):
        self.comes = comes
        self.mult = mult
        self.name = f"3-Point Molly ({comes} come, {mult}x)"
        self.desc = "Pass + come bets covering multiple numbers, all backed with odds."
    def place_bets(self, g):
        b, t = g.bets, g.t
        if t.is_comeout and not b.pass_line:
            b.pass_line = g.wager(g.unit)
        if not t.is_comeout:
            if b.pass_line and not b.pass_odds:
                b.pass_odds = g.wager(g.unit * self.mult)
            active = len(b.come) + (1 if b.come_new else 0)
            if active < self.comes and not b.come_new:
                b.come_new = g.wager(g.unit)
            for pt in list(b.come):
                if pt not in b.come_odds or not b.come_odds[pt]:
                    amt = g.wager(g.unit * self.mult)
                    if amt:
                        b.come_odds[pt] = amt


# ---------------------------------------------------------------- PLACE
class Place68(Strategy):
    name = "Place 6 & 8"
    desc = "The two best place numbers, 1.52% edge each."
    def place_bets(self, g):
        b = g.bets
        amt = _six_eight_amt(g.unit)
        if not g.t.is_comeout:
            for n in (6, 8):
                if not b.place.get(n):
                    got = g.wager(amt)
                    if got:
                        b.place[n] = got


class IronCross(Strategy):
    name = "Iron Cross"
    desc = "Field + place 5,6,8 -- wins on everything except 7. Bleeds 2.4%/roll."
    def place_bets(self, g):
        b = g.bets
        if g.t.is_comeout and not b.pass_line:
            b.pass_line = g.wager(g.unit)
            return
        if not g.t.is_comeout:
            if not b.place.get(6):
                a = g.wager(_six_eight_amt(g.unit));  b.place[6] = a if a else 0
            if not b.place.get(8):
                a = g.wager(_six_eight_amt(g.unit));  b.place[8] = a if a else 0
            if not b.place.get(5):
                a = g.wager(_five_nine_amt(g.unit));  b.place[5] = a if a else 0
            if not b.field_bet:
                b.field_bet = g.wager(g.unit)


class InsideNumbers(Strategy):
    name = "Inside Numbers (5,6,8,9)"
    desc = "Cover the four inside numbers. Lots of hits, lots of exposure."
    def place_bets(self, g):
        b = g.bets
        if not g.t.is_comeout:
            for n in (6, 8):
                if not b.place.get(n):
                    a = g.wager(_six_eight_amt(g.unit))
                    if a: b.place[n] = a
            for n in (5, 9):
                if not b.place.get(n):
                    a = g.wager(_five_nine_amt(g.unit))
                    if a: b.place[n] = a


# ---------------------------------------------------------------- PROGRESSION
class Martingale(Strategy):
    name = "Martingale (Pass)"
    desc = "Double after every loss. Table limits and bankroll kill it."
    def __init__(self, cap=8):
        self.level = 0
        self.cap = cap
        self.prev = None
    def place_bets(self, g):
        b = g.bets
        if g.t.is_comeout and not b.pass_line:
            if self.prev is not None:
                if g.bankroll + b.at_risk() < self.prev:
                    self.level = min(self.level + 1, self.cap)
                else:
                    self.level = 0
            amt = g.unit * (2 ** self.level)
            b.pass_line = g.wager(amt)
            self.prev = g.bankroll + b.at_risk()


class Hedged(Strategy):
    name = "Pass + Any-Craps Hedge"
    desc = "Pass line hedged with any-craps on the come-out. The hedge costs more than it saves."
    def place_bets(self, g):
        b = g.bets
        if g.t.is_comeout:
            if not b.pass_line:
                b.pass_line = g.wager(g.unit)
            if not b.props.get("craps"):
                b.props["craps"] = g.wager(max(1, g.unit // 5))
        elif b.pass_line and not b.pass_odds:
            b.pass_odds = g.wager(g.unit * 2)


class HardwaysAll(Strategy):
    name = "Pass + All Hardways"
    desc = "Pass line plus all four hardways. The hardways are a 9-11% tax."
    def place_bets(self, g):
        b = g.bets
        if g.t.is_comeout and not b.pass_line:
            b.pass_line = g.wager(g.unit)
        if not g.t.is_comeout:
            for h in (4, 6, 8, 10):
                if not b.hard.get(h):
                    a = g.wager(max(1, g.unit // 5))
                    if a: b.hard[h] = a


class FieldOnly(Strategy):
    name = "Field every roll"
    desc = "Bet the field on every roll. 5.56% edge, every single roll."
    def place_bets(self, g):
        if not g.bets.field_bet:
            g.bets.field_bet = g.wager(g.unit)


class AnySeven(Strategy):
    name = "Any 7 every roll"
    desc = "The worst bet on the table: 16.67% edge. Included as the floor."
    def place_bets(self, g):
        if not g.bets.props.get("any7"):
            g.bets.props["any7"] = g.wager(g.unit)


ALL = [
    PassOnly(),
    PassOdds(1), PassOdds(2), PassOdds(3), PassOdds(5), PassOdds(10),
    DontPassOdds(2), DontPassOdds(3),
    PassComeOdds(2, 2), PassComeOdds(2, 3),
    Place68(),
    InsideNumbers(),
    IronCross(),
    Hedged(),
    HardwaysAll(),
    FieldOnly(),
    Martingale(),
    AnySeven(),
]


# ---------------------------------------------------------------- ERIC'S 2+2
class ComeDontComeCapped(Strategy):
    """$25 pass on the come-out, then keep 2 come AND 2 don't-come points
    working (come side first), funded by at most $100 of fresh bankroll per
    shooter -- money returned during the shooter (stakes back, winnings) is
    re-bettable without touching the cap, like the app's stake meter."""
    name = "25 pass + 2 come + 2 DC ($100 fresh/shooter)"
    desc = "Both sides of the come, capped at $100 new money per shooter."

    def __init__(self, unit=25, cap=100):
        self.unit, self.cap = unit, cap
        self._sh = None
        self._base = 0     # bankroll when this shooter started
        self._fresh = 0    # new money out of the rack this shooter

    def _fund(self, g, amt):
        if amt > g.bankroll:
            return 0
        # Anything above (base - fresh spent) is money that came back this
        # shooter; it funds bets before fresh money does.
        pool = g.bankroll - (self._base - self._fresh)
        fresh_needed = max(0, amt - max(0, pool))
        if self._fresh + fresh_needed > self.cap:
            return 0
        w = g.wager(amt)
        self._fresh += fresh_needed
        return w

    def place_bets(self, g):
        if self._sh != g.shooters:
            self._sh, self._base, self._fresh = g.shooters, g.bankroll, 0
        b = g.bets
        if g.t.is_comeout:
            if not b.pass_line:
                b.pass_line = self._fund(g, self.unit)
            return
        come_ct = len(b.come) + (1 if b.come_new else 0)
        if come_ct < 2 and not b.come_new:
            b.come_new = self._fund(g, self.unit)
            if b.come_new:
                come_ct += 1
        if come_ct >= 2:
            dc_ct = len(b.dont_come) + (1 if b.dont_come_new else 0)
            if dc_ct < 2 and not b.dont_come_new:
                b.dont_come_new = self._fund(g, self.unit)


class CappedFlex(Strategy):
    """Parameterized capped strategy for sweeps: pass (+odds), n come (+odds),
    n don't-come (+lay), all funded returns-first with a fresh-money cap per
    shooter (see ComeDontComeCapped for the funding rule)."""
    def __init__(self, unit=25, cap=100, n_come=2, n_dc=2,
                 come_odds=0, pass_odds=0, dc_lay=0):
        self.unit, self.cap = unit, cap
        self.n_come, self.n_dc = n_come, n_dc
        self.come_odds, self.pass_odds, self.dc_lay = come_odds, pass_odds, dc_lay
        self.name = (f"{unit} pass{'+'+str(pass_odds)+'xO' if pass_odds else ''}"
                     f" {n_come}come{'+'+str(come_odds)+'xO' if come_odds else ''}"
                     f" {n_dc}dc{'+'+str(dc_lay)+'xL' if dc_lay else ''} cap{cap}")
        self._sh = None; self._base = 0; self._fresh = 0

    def _fund(self, g, amt):
        if amt <= 0 or amt > g.bankroll:
            return 0
        pool = g.bankroll - (self._base - self._fresh)
        fresh_needed = max(0, amt - max(0, pool))
        if self._fresh + fresh_needed > self.cap:
            return 0
        w = g.wager(amt)
        self._fresh += fresh_needed
        return w

    def place_bets(self, g):
        from craps_engine import ODDS_PAY
        if self._sh != g.shooters:
            self._sh, self._base, self._fresh = g.shooters, g.bankroll, 0
        b = g.bets
        if g.t.is_comeout:
            if not b.pass_line:
                b.pass_line = self._fund(g, self.unit)
            return
        if self.pass_odds and b.pass_line and not b.pass_odds:
            b.pass_odds = self._fund(g, self.unit * self.pass_odds)
        # odds behind established come points first (cheapest edge on the felt)
        if self.come_odds:
            for pt in list(b.come):
                if not b.come_odds.get(pt):
                    o = self._fund(g, self.unit * self.come_odds)
                    if o: b.come_odds[pt] = o
        if self.dc_lay:
            for pt in list(b.dont_come):
                if not b.dont_come_odds.get(pt):
                    n_, d_ = ODDS_PAY[pt]
                    o = self._fund(g, self.unit * self.dc_lay * n_ // d_)
                    if o: b.dont_come_odds[pt] = o
        come_ct = len(b.come) + (1 if b.come_new else 0)
        if come_ct < self.n_come and not b.come_new:
            b.come_new = self._fund(g, self.unit)
            if b.come_new: come_ct += 1
        if come_ct >= self.n_come:
            dc_ct = len(b.dont_come) + (1 if b.dont_come_new else 0)
            if dc_ct < self.n_dc and not b.dont_come_new:
                b.dont_come_new = self._fund(g, self.unit)


class EricLadder(Strategy):
    """Eric's ladder (sim request 2026-08-31):
    open: $10 pass + $5 yo. Point set: $75 don't come, $40 pass odds, place
    every number but the point ($12 on 6/8, $10 elsewhere), then $10 come every
    roll; a come landing on a placed number takes $10 odds and the place bet
    comes down ("drag"). If the DC point hits (the DC "drops") or the pass
    point is made: pull the places and pass odds, everything that cannot come
    down (comes + odds, the DC) keeps working, sit out to the next come-out
    and run the opening again."""
    name = "Eric ladder (pass+yo, DC75, places->comes)"

    def __init__(self, yo=True, place_410=True, dc=75):
        self.yo = yo                 # $5 yo ritual on come-out rolls
        self.place_410 = place_410   # include the 6.67%-edge outside numbers
        self.dc = dc                 # don't-come size
        self.paused = False
        self.opened = False          # this point-cycle's opening bets are up
        self._prev_point = None
        self._prev_dc = set()
        self._sh = None

    def _pull_down(self, g):
        b = g.bets
        for n_, amt in list(b.place.items()):
            g.collect(amt); del b.place[n_]
        if b.pass_odds:
            g.collect(b.pass_odds); b.pass_odds = 0
        self.paused = True

    def place_bets(self, g):
        b = g.bets
        if self._sh != g.shooters:              # new shooter: fresh cycle
            self._sh, self.paused = g.shooters, False
            self._prev_point, self._prev_dc = None, set()

        # ---- detect last roll's events (same shooter) ----
        point_made = self._prev_point and g.t.point is None
        dc_dropped = any(d not in b.dont_come for d in self._prev_dc)
        if (point_made or dc_dropped) and not self.paused:
            self._pull_down(g)
        self._prev_point = g.t.point
        self._prev_dc = set(b.dont_come)

        if g.t.is_comeout:
            self.paused = False                  # the opening runs again
            self.opened = False
            if not b.pass_line:
                b.pass_line = g.wager(10)
            if self.yo:
                b.props["yo"] = b.props.get("yo", 0) or g.wager(5)
            return
        if self.paused:
            return

        # ---- point is on, machine running ----
        pt = g.t.point
        if not self.opened:
            self.opened = True
            b.pass_odds = g.wager(40)
            b.dont_come_new = g.wager(self.dc)
            nums = (4, 5, 6, 8, 9, 10) if self.place_410 else (5, 6, 8, 9)
            for n_ in nums:
                if n_ != pt and n_ not in b.place and n_ not in b.come:
                    b.place[n_] = g.wager(12 if n_ in (6, 8) else 10)
        # comes that landed on placed numbers: odds up, place down (drag)
        for n_ in list(b.come):
            if not b.come_odds.get(n_):
                b.come_odds[n_] = g.wager(10)
            if n_ in b.place:
                g.collect(b.place.pop(n_))
        # $10 come every roll
        if not b.come_new:
            b.come_new = g.wager(10)


class InsideRegress(Strategy):
    """440-inside regression: place 100/120/120/100 across 5/6/8/9 once the
    point is on; first hit regresses to 220 (50/60), second to 110 (25/30).
    after='ride' leaves 110 working until the seven-out; after='down' takes
    everything down on the third hit and sits out the shooter."""
    LEVELS = ((100, 120), (50, 60), (25, 30))

    def __init__(self, after="ride"):
        self.after = after
        self.name = f"440 inside regress ({after})"
        self._sh = None
        self.level = 0
        self.placed = False
        self.done = False
        self.armed = False

    def _set_level(self, g):
        a, bamt = self.LEVELS[self.level]
        b = g.bets
        for n_ in (5, 9):
            cur = b.place.get(n_, 0)
            if cur > a: g.collect(cur - a); b.place[n_] = a
            elif cur < a: b.place[n_] = cur + g.wager(a - cur)
        for n_ in (6, 8):
            cur = b.place.get(n_, 0)
            if cur > bamt: g.collect(cur - bamt); b.place[n_] = bamt
            elif cur < bamt: b.place[n_] = cur + g.wager(bamt - cur)

    def place_bets(self, g):
        b = g.bets
        if self._sh != g.shooters:
            self._sh = g.shooters
            self.level, self.placed, self.done, self.armed = 0, False, False, False
        # did the last roll hit one of our working numbers?
        if self.armed and g.t.total in (5, 6, 8, 9) and b.place.get(g.t.total):
            if self.level < 2:
                self.level += 1
                self._set_level(g)
            elif self.after == "down":
                for n_, amt in list(b.place.items()):
                    g.collect(amt); del b.place[n_]
                self.done = True
        self.armed = False
        if self.done or g.t.is_comeout:
            return
        if not self.placed:
            self._set_level(g)
            self.placed = True
        self.armed = True


class DarkPressLadder(Strategy):
    """Eric's dark-side press ladder: $25 don't pass every come-out. On the
    point: place two inside numbers dodging the point (6&8; 6&9 if 8 is the
    point; 5&8 if 6 is the point), $6 units on 6/8 and $5 on 5/9. Hits advance
    one shared per-shooter script: pull, pull, press, pull, press, pull,
    spread, pull, spread, pull, then press the hit number every hit.
    Pull = collect the win, bet stays. Press = win onto that number in clean
    units (change pocketed) but the bet NEVER exceeds $21 -- 6/8 cap at $18,
    5/9 at $20 -- and after THREE presses on a number (or hitting the cap) it collects forever. Spread = the win
    buys the next uncovered inside number (5,9,6,8 priority, never the point)."""
    name = "Dark press ladder (25 DP + press/pull, cap 21)"

    SCRIPT = ["pull","pull","press","pull","press","pull","spread","pull","spread","pull"]
    CAP = 21

    def __init__(self):
        self._sh = None; self.hits = 0; self.placed = False; self.armed = False
        self._had = {}; self._pressed = {}

    @staticmethod
    def _unit(n): return 6 if n in (6, 8) else 5

    def _pairs(self, pt):
        if pt == 8: return (6, 9)
        if pt == 6: return (5, 8)
        return (6, 8)

    def _press(self, g, n, win):
        # Three presses on a number retires it to collect-only, as does the cap.
        if self._pressed.get(n, 0) >= 3:
            return
        b = g.bets; u = self._unit(n)
        room = ((self.CAP - b.place[n]) // u) * u      # stay at or under $21
        add = min((win // u) * u, max(0, room))
        if add:
            b.place[n] += g.wager(add)
            self._pressed[n] = self._pressed.get(n, 0) + 1

    def place_bets(self, g):
        from craps_engine import PLACE_PAY, _pay
        b = g.bets
        if self._sh != g.shooters:
            self._sh = g.shooters
            self.hits = 0; self.placed = False; self.armed = False
            self._had = {}; self._pressed = {}

        # ---- detect last roll's place hit (bet stays up; win hit the bankroll) ----
        n = g.t.total
        if self.armed and n in self._had and n in b.place:
            self.hits += 1
            win = _pay(self._had[n], PLACE_PAY[n])
            act = self.SCRIPT[self.hits-1] if self.hits <= len(self.SCRIPT) else "press"
            if act == "press":
                self._press(g, n, win)
            elif act == "spread":
                pt = g.t.point
                for cand in (5, 9, 6, 8):
                    if cand != pt and cand not in b.place:
                        u = self._unit(cand)
                        amt = min((win // u) * u, ((self.CAP // u) * u))
                        if amt: b.place[cand] = g.wager(amt)
                        break
        self.armed = False

        if g.t.is_comeout:
            if not b.dont_pass:
                b.dont_pass = g.wager(25)
            self._had = dict(b.place)
            return
        if not self.placed:
            self.placed = True
            for n_ in self._pairs(g.t.point):
                if n_ not in b.place:
                    b.place[n_] = g.wager(self._unit(n_))
        self._had = dict(b.place)
        self.armed = True
