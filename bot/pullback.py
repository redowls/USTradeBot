"""Pullback entry trigger (IMP-057) — buy the retracement, not the confirmation print.

**Why this module exists.** The shipped trigger enters on the 1-min bar where the
ribbon prints a fresh bullish cross. Three independent measurements say that bar is a
bad place to buy:

* 2026-09-21: AMD and INTC filled at the **83rd and 65th percentile** of the session
  range, with 81% / 59% of the day's move already spent, on a day both names ran 4–5%
  and closed at their highs.
* 2026-09-22: INTC filled at the **87.7th percentile** of the range that existed at
  that instant (IMP-046-clean, no lookahead) — within 0.22% of the high printed so far.
* 2026-09-28: the registered gate-veto study closed at **3 of 3**, with AMD's refused
  entry sitting at the **99th percentile** of the session's closes.

A 3-EMA cross confirmed by a 5-min ribbon is structurally a *confirmation* signal, and
confirmation arrives after the move. The consequence is the **+1R ceiling**: only
16–20% of entries ever print +1R (30/45/90d replay), which caps the true win rate no
exit change can lift — and the realized true win rate has been **0% for six weeks**.

**What this changes, and only this.** The setup is qualified exactly as before — same
gate, same fresh cross, same ``ENTRY_THRESHOLD``, same ``MIN_CROSSOVER`` and
``MIN_VOLATILITY`` floors, same blackout, same market gate. Instead of *buying* the
qualifying bar, the symbol is **armed**, and the fill waits for price to come back into
the ribbon while the bullish structure holds. Nothing about position size, the stop
fraction, the bracket, the trail ratchet or the EOD flatten moves — a lower fill simply
places the 2% stop lower with it, so 1R shrinks in dollars and the same tape travel is
worth more R.

**The trade-off this measures, honestly.** A pullback fill is a better price but a later
start: the bars between the cross and the retracement are given up, and on the runs that
never look back there is no fill at all. Whether the better price outweighs the lost
runway is an empirical question about the **ceiling**, which is why it is decided on
``bot.replay`` over three windows with friction on, against the pre-registered criteria
in ``todo.md`` — not on the ~2.6 live fills a week that IMP-054 proved cannot settle it.

**Carrying the cross-bar score forward is deliberate.** On a retracement bar
``fresh_cross`` is false by construction, so re-scoring would feed ``score_crossover`` a
non-cross bar and measure something the strategy never meant to ask. The setup was
qualified at the cross; the pullback is an execution refinement, not a re-qualification.
Sizing therefore sees the same confidence it would have seen in ``cross`` mode, which is
what isolates the experiment to entry *price* alone.

This module is pure: it holds no clock, no broker and no I/O, so the whole state machine
is unit-testable and the live path and replay path exercise the identical code.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from bot.config import CROSS, ENTRY_MODES, PULLBACK
from bot.indicators import RibbonSnapshot
from bot.signals import ConfidenceBreakdown

# ``CROSS`` (buy the qualifying cross bar — the behaviour shipped since Phase 3) and
# ``PULLBACK`` (arm on that bar, buy the retracement) are defined in ``bot.config`` to
# keep the import graph acyclic, and re-exported here so the trigger's own module is a
# complete place to read it from.
__all__ = [
    "CROSS",
    "PULLBACK",
    "ENTRY_MODES",
    "ENTER",
    "WAIT",
    "DISARM",
    "ArmedCross",
    "PullbackDecision",
    "arm",
    "advance",
]

# --- outcomes of advancing an armed cross ----------------------------------

ENTER = "enter"
WAIT = "wait"
DISARM = "disarm"


@dataclass(frozen=True)
class ArmedCross:
    """A qualifying cross that is waiting for its retracement.

    ``confidence`` is the score computed on the cross bar and is carried forward
    unchanged to the fill (see the module docstring). ``bars_waited`` counts *closed*
    trigger candles observed since the cross, so the arming bar itself is 0.
    """

    symbol: str
    armed_at: datetime
    armed_close: float
    confidence: ConfidenceBreakdown
    bars_waited: int = 0


@dataclass(frozen=True)
class PullbackDecision:
    """What one closed trigger candle did to an armed cross."""

    outcome: str
    armed: ArmedCross | None  # the advanced arm when still waiting, else None
    reason: str

    @property
    def enter(self) -> bool:
        return self.outcome == ENTER

    @property
    def disarmed(self) -> bool:
        return self.outcome == DISARM


def arm(
    symbol: str,
    trigger: RibbonSnapshot,
    confidence: ConfidenceBreakdown,
) -> ArmedCross:
    """Record a qualifying cross so later candles can look for its retracement."""
    return ArmedCross(
        symbol=symbol,
        armed_at=trigger.candle_start,
        armed_close=trigger.close,
        confidence=confidence,
    )


def advance(
    armed: ArmedCross,
    trigger: RibbonSnapshot,
    *,
    max_bars: int,
) -> PullbackDecision:
    """Advance ``armed`` by one closed trigger candle.

    Checks run in this order, and the order carries the risk logic:

    1. **Structure first.** If the ribbon is no longer stacked bullish the setup is
       dead — disarm. Checking price first could otherwise buy a retracement that is
       really the start of a breakdown, which is the exact failure the ``stacked``
       requirement exists to prevent.
    2. **Then the retracement.** ``close <= mid`` (the ribbon's middle EMA) is the
       fill: price has come back into the ribbon with the stack intact.
    3. **Then expiry.** After ``max_bars`` closed candles with no retracement the move
       has left without us; disarm rather than chase it.

    Only *closed*-candle values are read — no intrabar high/low — so this cannot
    introduce the IMP-046 lookahead that the ceiling measurement is careful about.
    """
    waited = armed.bars_waited + 1

    if not trigger.ribbon_ready or not trigger.stacked:
        return PullbackDecision(DISARM, None, "stack broke before the pullback")

    mid = trigger.mid
    if mid is not None and trigger.close <= mid:
        return PullbackDecision(
            ENTER, replace(armed, bars_waited=waited), f"pullback into ribbon after {waited} bars"
        )

    if waited >= max_bars:
        return PullbackDecision(DISARM, None, f"no pullback within {max_bars} bars")

    return PullbackDecision(WAIT, replace(armed, bars_waited=waited), "waiting for the pullback")
