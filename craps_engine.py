"""Craps table simulation engine.

Models a real table: come-out vs point, pass/don't, come/don't-come with
travel, free odds, place/buy/lay, field, hardways, props. Tracks bankroll,
exposure, and per-roll history.
"""
import random
from dataclasses import dataclass, field as dc_field

POINTS = (4, 5, 6, 8, 9, 10)
PLACE_PAY = {4: (9, 5), 5: (7, 5), 6: (7, 6), 8: (7, 6), 9: (7, 5), 10: (9, 5)}
ODDS_PAY  = {4: (2, 1), 5: (3, 2), 6: (6, 5), 8: (6, 5), 9: (3, 2), 10: (2, 1)}
HARD_PAY  = {4: 7, 6: 9, 8: 9, 10: 7}


class Table:
    """Dice + table state. Strategies read this and mutate bets."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.point = None          # None == come-out
        self.d1 = self.d2 = 0
        self.total = 0
        self.roll_count = 0
        self.shooter_rolls = 0

    def roll(self):
        self.d1 = self.rng.randint(1, 6)
        self.d2 = self.rng.randint(1, 6)
        self.total = self.d1 + self.d2
        self.roll_count += 1
        self.shooter_rolls += 1
        return self.total

    @property
    def is_comeout(self):
        return self.point is None

    @property
    def is_hard(self):
        return self.d1 == self.d2


@dataclass
class Bets:
    """Every bet a player can have working, with amounts."""
    pass_line: int = 0
    pass_odds: int = 0
    dont_pass: int = 0
    dont_odds: int = 0
    # come bets: {point: amount}, plus the one riding the come-out
    come: dict = dc_field(default_factory=dict)
    come_odds: dict = dc_field(default_factory=dict)
    come_new: int = 0
    dont_come: dict = dc_field(default_factory=dict)
    dont_come_odds: dict = dc_field(default_factory=dict)
    dont_come_new: int = 0
    place: dict = dc_field(default_factory=dict)
    buy: dict = dc_field(default_factory=dict)
    lay: dict = dc_field(default_factory=dict)
    field_bet: int = 0
    hard: dict = dc_field(default_factory=dict)
    props: dict = dc_field(default_factory=dict)   # name -> amount
    place_working_comeout: bool = False            # place bets off on come-out by default

    def at_risk(self):
        return (self.pass_line + self.pass_odds + self.dont_pass + self.dont_odds
                + sum(self.come.values()) + sum(self.come_odds.values()) + self.come_new
                + sum(self.dont_come.values()) + sum(self.dont_come_odds.values()) + self.dont_come_new
                + sum(self.place.values()) + sum(self.buy.values()) + sum(self.lay.values())
                + self.field_bet + sum(self.hard.values()) + sum(self.props.values()))


def _pay(amount, ratio):
    n, d = ratio
    return amount * n // d


class Game:
    """Runs one session: a strategy against a table until a stop condition."""

    def __init__(self, strategy, bankroll=1000, unit=10, rng=None,
                 max_rolls=200, win_goal=None, loss_limit=None, vig_on_win=True):
        self.t = Table(rng)
        self.strategy = strategy
        self.bankroll = bankroll
        self.start_bankroll = bankroll
        self.unit = unit
        self.max_rolls = max_rolls
        self.win_goal = win_goal
        self.loss_limit = loss_limit
        self.vig_on_win = vig_on_win
        self.bets = Bets()
        self.total_wagered = 0   # cash moved from bankroll onto the felt
        self.action = 0          # true amount at risk across all decisions
        self.peak = bankroll
        self.trough = bankroll
        self.busted = False
        self.hit_goal = False
        self.shooters = 0

    # --- money helpers ---
    def wager(self, amt):
        """Move money from bankroll onto the table."""
        if amt <= 0:
            return 0
        if amt > self.bankroll:
            amt = self.bankroll
        self.bankroll -= amt
        self.total_wagered += amt
        return amt

    def collect(self, amt):
        self.bankroll += amt

    def _track(self):
        equity = self.bankroll + self.bets.at_risk()
        self.peak = max(self.peak, equity)
        self.trough = min(self.trough, equity)

    # --- resolution ---
    def _exposure_at_risk(self, n, comeout):
        """Money genuinely subject to a win/lose decision on THIS roll.

        A place bet that stays up is re-risked every decision roll, so counting
        only the initial buy-in understates action and inflates the apparent edge.
        """
        b = self.bets
        exp = 0
        # one-roll bets always decide
        exp += b.field_bet + sum(b.props.values())
        # hardways decide on their number or a 7
        for h, amt in b.hard.items():
            if amt and (n == 7 or n == h):
                exp += amt
        # place/buy decide on their number or a 7 (when working)
        working = (not comeout) or b.place_working_comeout
        if working:
            for pt, amt in b.place.items():
                if n == pt or n == 7:
                    exp += amt
            for pt, amt in b.buy.items():
                if n == pt or n == 7:
                    exp += amt
        for pt, amt in b.lay.items():
            if n == pt or n == 7:
                exp += amt
        # line/come bets decide on 7, 11, craps, or their point
        if comeout:
            # The flat line bet only faces a decision on a natural or craps;
            # on a point roll it simply travels, so it is not action yet.
            if n in (2, 3, 7, 11, 12):
                exp += b.pass_line + b.dont_pass
        else:
            if n == 7 or n == self.t.point:
                exp += b.pass_line + b.pass_odds + b.dont_pass + b.dont_odds
        exp += b.come_new + b.dont_come_new
        for pt, amt in b.come.items():
            if n == pt or n == 7:
                exp += amt + b.come_odds.get(pt, 0)
        for pt, amt in b.dont_come.items():
            if n == pt or n == 7:
                exp += amt + b.dont_come_odds.get(pt, 0)
        return exp

    def resolve(self):
        """Resolve every bet against the roll that just happened."""
        t, b = self.t, self.bets
        n = t.total
        comeout = t.is_comeout
        self.action += self._exposure_at_risk(n, comeout)

        # ---- one-roll bets first ----
        if b.field_bet:
            amt = b.field_bet
            if n in (3, 4, 9, 10, 11):
                self.collect(amt * 2)
            elif n == 2:
                self.collect(amt * 3)
            elif n == 12:
                self.collect(amt * 3)      # 2x on 12
            b.field_bet = 0

        for name, amt in list(b.props.items()):
            if not amt:
                continue
            win = {
                "any7":  n == 7,
                "craps": n in (2, 3, 12),
                "yo":    n == 11,
                "hi-lo": n in (2, 12),
            }.get(name, False)
            pay = {"any7": 4, "craps": 7, "yo": 15, "hi-lo": 15}.get(name, 0)
            if win:
                self.collect(amt + amt * pay)
            b.props[name] = 0

        # ---- hardways ----
        for h, amt in list(b.hard.items()):
            if not amt:
                continue
            if n == 7 or (n == h and not t.is_hard):
                b.hard[h] = 0
            elif n == h and t.is_hard:
                self.collect(amt + amt * HARD_PAY[h])
                b.hard[h] = 0

        # ---- established come bets ----
        # NOTE: these resolve BEFORE a new come bet travels, otherwise a come
        # bet moving to number N would be paid as a winner on the same roll.
        if n == 7:
            for pt, amt in list(b.come.items()):
                b.come.pop(pt, None); b.come_odds.pop(pt, None)
            for pt, amt in list(b.dont_come.items()):
                odds = b.dont_come_odds.pop(pt, 0)
                self.collect(amt * 2)
                if odds:
                    self.collect(odds + _pay(odds, ODDS_PAY[pt][::-1]))
                b.dont_come.pop(pt, None)
        elif n in POINTS:
            if n in b.come:
                amt = b.come.pop(n)
                self.collect(amt * 2)
                odds = b.come_odds.pop(n, 0)
                if odds:
                    self.collect(odds + _pay(odds, ODDS_PAY[n]))
            if n in b.dont_come:
                b.dont_come.pop(n)
                b.dont_come_odds.pop(n, None)

        # ---- come / don't-come travel (BEFORE point resolution) ----
        if b.come_new:
            if n in (7, 11):
                self.collect(b.come_new * 2)
                b.come_new = 0
            elif n in (2, 3, 12):
                b.come_new = 0
            elif n in POINTS:
                b.come[n] = b.come.get(n, 0) + b.come_new
                b.come_new = 0

        if b.dont_come_new:
            if n in (2, 3):
                self.collect(b.dont_come_new * 2)
                b.dont_come_new = 0
            elif n == 12:
                self.collect(b.dont_come_new)   # push
                b.dont_come_new = 0
            elif n in (7, 11):
                b.dont_come_new = 0
            elif n in POINTS:
                b.dont_come[n] = b.dont_come.get(n, 0) + b.dont_come_new
                b.dont_come_new = 0

        # ---- place / buy / lay ----
        working = (not comeout) or b.place_working_comeout
        if n == 7:
            # Place/buy bets are OFF on the come-out by default: if they cannot
            # win on this roll they must not lose on it either.
            if working:
                b.place.clear(); b.buy.clear()
            for pt, amt in list(b.lay.items()):
                win = _pay(amt, ODDS_PAY[pt][::-1])
                if self.vig_on_win:
                    win -= max(1, win * 5 // 100)
                self.collect(amt + win)
            b.lay.clear()
        elif n in POINTS:
            if working and n in b.place:
                self.collect(_pay(b.place[n], PLACE_PAY[n]))
            if working and n in b.buy:
                amt = b.buy.pop(n)
                win = _pay(amt, ODDS_PAY[n])
                if self.vig_on_win:
                    win -= max(1, win * 5 // 100)
                self.collect(amt + win)
            if n in b.lay:
                b.lay.pop(n)

        # ---- line bets ----
        if comeout:
            if n in (7, 11):
                if b.pass_line:
                    self.collect(b.pass_line * 2); b.pass_line = 0
                if b.dont_pass:
                    b.dont_pass = 0
            elif n in (2, 3):
                if b.pass_line:
                    b.pass_line = 0
                if b.dont_pass:
                    self.collect(b.dont_pass * 2); b.dont_pass = 0
            elif n == 12:
                if b.pass_line:
                    b.pass_line = 0
                if b.dont_pass:
                    self.collect(b.dont_pass)   # push
                    b.dont_pass = 0
            else:
                self.t.point = n
        else:
            pt = self.t.point
            if n == pt:
                if b.pass_line:
                    self.collect(b.pass_line * 2); b.pass_line = 0
                if b.pass_odds:
                    self.collect(b.pass_odds + _pay(b.pass_odds, ODDS_PAY[pt])); b.pass_odds = 0
                if b.dont_pass:
                    b.dont_pass = 0
                if b.dont_odds:
                    b.dont_odds = 0
                self.t.point = None
                self.t.shooter_rolls = 0
            elif n == 7:
                if b.pass_line:
                    b.pass_line = 0
                if b.pass_odds:
                    b.pass_odds = 0
                if b.dont_pass:
                    self.collect(b.dont_pass * 2); b.dont_pass = 0
                if b.dont_odds:
                    self.collect(b.dont_odds + _pay(b.dont_odds, ODDS_PAY[pt][::-1])); b.dont_odds = 0
                self.t.point = None
                self.t.shooter_rolls = 0
                self.shooters += 1

    def run(self):
        while self.t.roll_count < self.max_rolls:
            self.strategy.place_bets(self)
            self._track()
            if self.bets.at_risk() == 0 and self.bankroll < self.unit:
                self.busted = True
                break
            self.t.roll()
            self.resolve()
            self._track()
            if self.win_goal and self.bankroll + self.bets.at_risk() >= self.start_bankroll + self.win_goal:
                self.hit_goal = True
                break
            if self.loss_limit and self.bankroll + self.bets.at_risk() <= self.start_bankroll - self.loss_limit:
                break
            if self.bankroll < self.unit and self.bets.at_risk() == 0:
                self.busted = True
                break
        final = self.bankroll + self.bets.at_risk()
        return {
            "final": final,
            "net": final - self.start_bankroll,
            "rolls": self.t.roll_count,
            "wagered": self.total_wagered,
            "action": self.action,
            "peak": self.peak,
            "trough": self.trough,
            "busted": self.busted,
            "hit_goal": self.hit_goal,
            "shooters": self.shooters,
        }
