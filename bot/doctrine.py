"""Stop-exit doctrine accounting (IMP-039).

**A stop is a failed trade whatever the sign of its realized P&L.** That is a
standing user directive (2026-09-01), and until now it lived only in the review
prompts — applied by hand, once a day, by whoever ran the routine. Everything the
bot itself printed (``bot.report``, and therefore the Telegram digest and every
figure quoted into the memory files) still scored a win as ``pnl > 0``.

That gap is not cosmetic, and the live book shows exactly how it misleads. Over the
last three sessions that traded (2026-08-26..28) the bot booked **5 green trades out
of 6** — an 83% headline win rate — while **not one** of them reached +1R:

    PLTR  +0.14R  end-of-day flatten                      +$5.28
    NVDA  +0.07R  broker stop leg                         +$3.78
    TSM   +0.15R  broker stop leg                         +$5.08
    TSLA  +0.48R  end-of-day flatten                     +$16.60
    PLTR  +0.52R  broker stop leg (EOD-labelled)         +$25.93
    SPOT  -0.35R  broker stop leg                        −$11.82

Three of those are stop-driven exits that handed back a proven move for a rounding
error. The doctrine's verdict is 0 WIN / 3 SCRATCH / 3 FAIL — a **true win rate of
0%** against a headline of 83%. A strategy with no demonstrated edge (all-time
expectancy **+0.008R/trade over 274 trades**) keeps reporting a respectable win rate
precisely because ``pnl > 0`` is the wrong question.

This module makes the bot answer the right one. Pure arithmetic, no I/O, mirroring
:mod:`bot.excursion`: the classification is unit-tested against the real rows above,
and the report layer merely formats what it returns. Nothing here touches the
trading path — it changes what we *count*, never what we *do*.

Note the direction of the change: every figure this produces is **harsher** than the
one it sits beside. It cannot flatter the strategy, which is the point.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# The IMP-038 catch-all: the bot knows a broker bracket leg filled but not which one.
# These rows historically carried the whole loss side of the book, so they are
# attributed by price rather than dropped.
_BROKER_CATCHALL = "stop/target filled broker-side"

# profit_R at or below which a stop-driven exit is a FAIL rather than a SCRATCH.
# +0.25R is "the thesis went nowhere": a break-even stop, a scratched trail, or a
# full stop all land here.
FAIL_MAX_R = 0.25
# profit_R at or above which any exit counts as a WIN on its own merits.
WIN_MIN_R = 1.0
# A flatten/reversal below this is a FAIL; between it and WIN_MIN_R it is a SCRATCH.
SCRATCH_MIN_R = -0.25
# A FAIL at or below this took (close to) the original 1R stop — a "full stop".
# Above it, the stop had already ratcheted up: a break-even or scratched trail.
FULL_STOP_MAX_R = -0.75
# Fraction of the target a fill must reach to be read as the take-profit leg rather
# than the stop leg. Loose enough to absorb ordinary fill slippage.
_TARGET_TOLERANCE = 0.995

WIN = "WIN"
SCRATCH = "SCRATCH"
FAIL = "FAIL"

FULL_STOP = "full-stop"
BE_SCRATCH = "BE-scratch"


@dataclass(frozen=True)
class Verdict:
    """How the doctrine scores one closed trade."""

    symbol: str
    bucket: str  # WIN / SCRATCH / FAIL
    profit_r: float
    stop_driven: bool
    fail_kind: str  # FULL_STOP / BE_SCRATCH, "" when not a FAIL
    resolved_reason: str  # the catch-all replaced by the leg that actually filled
    pnl: float

    @property
    def headline_win(self) -> bool:
        """What the old ``pnl > 0`` test would have said. Kept to show the gap."""
        return self.pnl > 0


@dataclass(frozen=True)
class StopExitSummary:
    """The block the doctrine requires every review to report."""

    trades: int
    stops: int  # stop-driven exits, any P&L sign
    wins: int
    scratches: int
    fails: int
    full_stops: int
    be_scratches: int
    headline_wins: int  # pnl > 0

    @property
    def stop_rate(self) -> float:
        return self.stops / self.trades if self.trades else 0.0

    @property
    def true_win_rate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0

    @property
    def headline_win_rate(self) -> float:
        return self.headline_wins / self.trades if self.trades else 0.0

    @property
    def fail_scratch_rate(self) -> float:
        """The escalation metric: >= 60% over 3 trading sessions indicts the entry."""
        return (self.fails + self.scratches) / self.trades if self.trades else 0.0


def risk_per_share(entry_price: float, stop_price: float | None, stop_loss: float) -> float:
    """1R for this trade, from the ORIGINAL bracket stop.

    The trail ratchets broker-side only, so ``dbo.trades.stop_price`` keeps holding
    the entry-time anchor and stays the honest denominator. Rows written before the
    column was populated (or with a nonsense non-positive width) fall back to the
    configured ``stop_loss`` fraction of entry.
    """
    if stop_price and stop_price > 0:
        r = entry_price - stop_price
        if r > 0:
            return r
    return entry_price * stop_loss


def resolve_reason(
    exit_reason: str, exit_price: float, target_price: float | None
) -> str:
    """Replace the IMP-038 catch-all with the leg that actually filled.

    A bracket has two legs and the catch-all means we did not observe which one; the
    fill price does though. Reaching the target is the take-profit leg, anything
    short of it is the stop leg. Reasons that already name their leg pass through.
    """
    reason = (exit_reason or "").strip().lower()
    if _BROKER_CATCHALL not in reason:
        return reason
    if target_price and target_price > 0 and exit_price >= target_price * _TARGET_TOLERANCE:
        return reason.replace(_BROKER_CATCHALL, "take profit")
    return reason.replace(_BROKER_CATCHALL, "trailing stop")


def is_stop_driven(resolved_reason: str) -> bool:
    """True when a stop being touched is what ended the trade.

    Reads the *resolved* reason, so a catch-all row already attributed to its stop
    leg counts — including one an end-of-day flatten merely discovered after the
    fact ("end-of-day flatten (trailing stop)"): the stop is what closed it.
    """
    return "stop" in resolved_reason and "take profit" not in resolved_reason


def classify(
    *,
    symbol: str,
    entry_price: float,
    exit_price: float,
    stop_price: float | None,
    target_price: float | None,
    exit_reason: str,
    pnl: float,
    stop_loss: float,
) -> Verdict:
    """Bucket one closed trade WIN / SCRATCH / FAIL per the doctrine.

    Deliberately independent of ``pnl``'s sign — ``pnl`` is carried only so the
    summary can show how far the headline number drifts from the true one.
    """
    r = risk_per_share(entry_price, stop_price, stop_loss)
    profit_r = (exit_price - entry_price) / r
    resolved = resolve_reason(exit_reason, exit_price, target_price)
    stop_driven = is_stop_driven(resolved)

    if "take profit" in resolved or profit_r >= WIN_MIN_R:
        bucket = WIN
    elif stop_driven:
        bucket = FAIL if profit_r <= FAIL_MAX_R else SCRATCH
    elif profit_r < SCRATCH_MIN_R:  # a flatten/reversal that gave back real money
        bucket = FAIL
    else:
        bucket = SCRATCH

    fail_kind = ""
    if bucket == FAIL:
        fail_kind = FULL_STOP if profit_r <= FULL_STOP_MAX_R else BE_SCRATCH

    return Verdict(
        symbol=symbol,
        bucket=bucket,
        profit_r=profit_r,
        stop_driven=stop_driven,
        fail_kind=fail_kind,
        resolved_reason=resolved,
        pnl=pnl,
    )


def verdicts_for(trades: Iterable, stop_loss: float) -> list[Verdict]:
    """Classify a run of :class:`~bot.persistence.ClosedTrade` rows."""
    return [
        classify(
            symbol=t.symbol,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            stop_price=getattr(t, "stop_price", None),
            target_price=getattr(t, "target_price", None),
            exit_reason=t.exit_reason,
            pnl=t.pnl,
            stop_loss=stop_loss,
        )
        for t in trades
    ]


def summarize(verdicts: Sequence[Verdict]) -> StopExitSummary:
    """Roll verdicts up into the block the doctrine requires."""
    return StopExitSummary(
        trades=len(verdicts),
        stops=sum(1 for v in verdicts if v.stop_driven),
        wins=sum(1 for v in verdicts if v.bucket == WIN),
        scratches=sum(1 for v in verdicts if v.bucket == SCRATCH),
        fails=sum(1 for v in verdicts if v.bucket == FAIL),
        full_stops=sum(1 for v in verdicts if v.fail_kind == FULL_STOP),
        be_scratches=sum(1 for v in verdicts if v.fail_kind == BE_SCRATCH),
        headline_wins=sum(1 for v in verdicts if v.headline_win),
    )


def format_stop_exits(s: StopExitSummary) -> str:
    """The two lines that go beside the headline, in the report and on Telegram.

    Short by design: this rides the digest that already goes to Telegram, and the
    true win rate is the number the doctrine says governs the verdict, so it has to
    travel with the headline rather than sit in a study only stdout ever sees.
    """
    if not s.trades:
        return "🛑 stop rate: n/a — no closed trades"
    return (
        f"🛑 stop rate: {s.stops}/{s.trades} ({s.stop_rate * 100:.0f}%) — "
        f"FAIL {s.fails} (full {s.full_stops} / BE-scratch {s.be_scratches}) · "
        f"SCRATCH {s.scratches} · WIN {s.wins}\n"
        f"✅ true win rate: {s.true_win_rate * 100:.0f}% "
        f"(headline {s.headline_win_rate * 100:.0f}%)"
    )
