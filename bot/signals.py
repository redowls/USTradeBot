"""Signal + confidence scorer (Phase 3).

Combines the two ribbon snapshots (1-min trigger, 5-min gate) into an entry
decision. Two layers:

1. **Candidacy** — the hard gate+trigger rule (a binary yes/no):
   ``enter_candidate = gate_open AND fresh_cross`` (see the domain invariants in
   CLAUDE.md). Only candidates are scored.
2. **Confidence** — a 0–100 heuristic blend of five sub-scores, each normalized to
   0–1 and weighted. Enter only if ``confidence >= ENTRY_THRESHOLD``.

The confidence is a *relative ranking* of setups, **not** a probability of profit
(summary.md). Weights are illustrative — tune them on paper. The market-hours gate
lives here too but is applied by the state machine (it owns the clock).

All functions are pure. The volatility sub-score reads the 1-min ATR/price as a
proxy for *range availability* — how far the tape is likely to travel before the
flatten — not, as it originally did, as a stand-in for the bid/ask spread the IEX
trade feed does not give us (IMP-036).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from bot.config import EASTERN
from bot.indicators import RibbonSnapshot

# --- tunable thresholds (illustrative; tune on paper) ----------------------

# Crossover strength: ribbon width / fast-EMA slope, normalized by price.
_CROSS_WIDTH_FULL = 0.0020  # (fast-slow)/close at which the width score saturates
_CROSS_SLOPE_FULL = 0.0010  # (fast-prev_fast)/close at which the slope score saturates
_CROSS_WIDTH_WEIGHT = 0.6  # blend of width vs slope within the crossover sub-score

# Higher-TF trend: gate ribbon width when stacked.
_TREND_WIDTH_FULL = 0.0040  # (fast-slow)/close at which the gate width score saturates

# Volume confirmation: volume / avg_volume mapped from 0.5x..1.5x -> 0..1.
_VOL_RATIO_LOW = 0.5
_VOL_RATIO_HIGH = 1.5

# Range availability: 1-min ATR/close. A tape that does not travel cannot pay
# (IMP-036). Anchors reversed, not re-fitted — ``_ATR_DEAD`` is the incumbent
# ``_ATR_GOOD`` breakpoint, which is where the sign flips in both populations.
_ATR_DEAD = 0.0020  # <= this -> 0.0 (cannot reach the 1.25% trail before the flatten)
_ATR_LIVE = 0.0030  # >= this -> 1.0


@dataclass(frozen=True)
class ScoreWeights:
    """Weights for the five confidence components (should sum to 100).

    ``volume`` carries **zero** weight (IMP-034). Its sub-score is still computed and
    persisted on every entry and refusal — the relationship stays falsifiable — but it
    no longer moves the total, because live P&L says the score rewards it *backwards*:

    ==================  ===  =======  ==========
    conf_volume band      n  win %    total P&L
    ==================  ===  =======  ==========
    1.00 (full marks)    79    44.3%    −$377.93
    0.00 (zero marks)    51    43.1%    +$185.99
    ==================  ===  =======  ==========

    The band the scorer rewarded most was the worst-performing band by a wide margin,
    and the band it punished most was the best. That is consistent with IMP-017's
    finding that this bot's entire lifetime loss came from buying moves that had
    already happened: heavy volume on a 1-min ribbon cross means the move is being
    chased, not caught. First observed 2026-08-17, confirmed on both all-time and
    post-IMP-021 windows 2026-08-24.

    The freed 15 points are redistributed **proportionally** across the two components
    that discriminate in the correct direction — crossover (30→39) and trend (20→26),
    preserving their existing 3:2 ratio. Proportional redistribution is deliberate: it
    introduces no new free parameter to fit. Renormalising to 100 (rather than leaving
    the weights summing to 85) keeps ``ENTRY_THRESHOLD`` semantics unchanged, so this
    change isolates *which* setups score well and does not silently tighten the bar.

    Replay across four windows, current config, gate ON (net P&L, baseline → IMP-034):
    10d +$3.14 → −$1.78 (n=3, noise) · 20d +$48.28 → +$94.38 · 30d +$281.14 → +$356.08 ·
    45d +$370.21 → +$454.16. Trade count is essentially unchanged (48 → 50 over 45d),
    so the gain is selection quality, not more trading.
    """

    crossover: float = 39.0
    trend: float = 26.0
    rsi: float = 20.0
    volume: float = 0.0
    volatility: float = 15.0


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """The five 0–1 sub-scores and the weighted 0–100 total."""

    crossover: float
    trend: float
    rsi: float
    volume: float
    volatility: float
    total: float


# Default weights as a module-level singleton (avoids a call in arg defaults).
DEFAULT_WEIGHTS = ScoreWeights()


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


# --- sub-scores ------------------------------------------------------------


def score_crossover(trigger: RibbonSnapshot) -> float:
    """Strength of the 1-min cross: wide, accelerating ribbon scores high."""
    if not trigger.ribbon_ready or trigger.close <= 0:
        return 0.0
    fast, _mid, slow = trigger.ribbon
    width = (fast - slow) / trigger.close  # type: ignore[operator]
    width_score = _clamp01(width / _CROSS_WIDTH_FULL)

    prev_fast = trigger.prev_ribbon[0]
    slope = (fast - prev_fast) / trigger.close  # type: ignore[operator]
    slope_score = _clamp01(slope / _CROSS_SLOPE_FULL)

    return _CROSS_WIDTH_WEIGHT * width_score + (1.0 - _CROSS_WIDTH_WEIGHT) * slope_score


def score_trend(gate: RibbonSnapshot | None) -> float:
    """Higher-timeframe trend: 5-min ribbon stacked & expanding scores high."""
    if gate is None or not gate.ribbon_ready or gate.close <= 0:
        return 0.0
    if not gate.stacked:
        return 0.0
    fast, _mid, slow = gate.ribbon
    width = (fast - slow) / gate.close  # type: ignore[operator]
    width_score = _clamp01(width / _TREND_WIDTH_FULL)
    # A rising fast EMA earns the upper half; flat-but-stacked stays in the lower half.
    rising = 1.0 if gate.fast_rising else 0.0
    return 0.5 * width_score + 0.5 * rising


def score_rsi(trigger: RibbonSnapshot) -> float:
    """Momentum: healthy 45–65 zone or turning up from oversold scores high;
    overbought (>70) scores low."""
    rsi = trigger.rsi
    if rsi is None:
        return 0.0
    if rsi >= 70.0:
        return 0.0  # overbought
    if rsi >= 65.0:
        return _clamp01((70.0 - rsi) / 5.0)  # 65->1.0 down to 70->0.0
    if rsi >= 45.0:
        return 1.0  # healthy momentum zone
    if rsi >= 30.0:
        base = 0.3 + 0.7 * (rsi - 30.0) / 15.0  # 30->0.3 up to 45->1.0
        # Bonus for turning up out of the lower band (oversold reversal).
        if trigger.prev_rsi is not None and rsi > trigger.prev_rsi:
            base = max(base, 0.8)
        return _clamp01(base)
    # Deep oversold: risky falling knife unless clearly turning up.
    if trigger.prev_rsi is not None and rsi > trigger.prev_rsi:
        return 0.5
    return 0.2


def score_volume(trigger: RibbonSnapshot) -> float:
    """Volume confirmation: >=1.5x trailing average scores 1.0, well below 0.0."""
    avg = trigger.avg_volume
    if avg is None or avg <= 0:
        return 0.0
    ratio = trigger.volume / avg
    return _clamp01((ratio - _VOL_RATIO_LOW) / (_VOL_RATIO_HIGH - _VOL_RATIO_LOW))


def score_volatility(trigger: RibbonSnapshot) -> float:
    """Range availability (1-min ATR/price): a tape that travels scores high (IMP-036).

    This sub-score used to run the other way — it was written as a *spread* proxy
    ("tight is good, spikes are bad") because the IEX trade feed gives us no bid/ask.
    On a bot whose whole exit structure is a 1.25% trail, a 2% stop and a 10% target,
    that pointed 15 of 100 points at exactly the tape that cannot reach any of them.

    Two independent populations, measured 2026-08-26, agree on the direction *and* on
    the breakpoint — which is why the dead anchor below is the incumbent constant
    rather than a fitted one:

    **269 closed trades** (P&L), split at the old saturation point:

    ==========================  ===  =====  =========  =========
    1-min ATR/close               n  win %  net P&L    median %
    ==========================  ===  =====  =========  =========
    <= 0.20% ("full marks")     175    46%  −$253.62     −0.069%
    >  0.20%                     94    46%  +$245.68     −0.035%
    ==========================  ===  =====  =========  =========

    Restricted to the live regime (entries >= 10:00 ET, IMP-017): dead n=161 −$328.91
    against live n=67 +$728.32. Negative on the median and after trimming the extremes
    in every era cut, so it is not one blowup carrying the sign.

    **191 refused candidates** over 8 sessions — never traded, so no P&L, sizing or
    capital confound at all. How far the tape then ran:

    ==================  ===  =========  =========  ==========
    1-min ATR/close       n  avg MFE    avg fwd    hit trail
    ==================  ===  =========  =========  ==========
    <= 0.05%             37    +0.182%    −0.075%       0/37
    0.05 – 0.10%         92    +0.353%    −0.053%       2/92
    0.10 – 0.20%         51    +0.680%    −0.069%       6/51
    0.20 – 0.30%          8    +1.197%    +0.738%        3/8
    >  0.30%              3    +1.695%    +1.305%        3/3
    ==================  ===  =========  =========  ==========

    MFE rises monotonically across all five bands and the trail-reach rate goes 0% →
    2% → 12% → 38% → 100%. That is the mechanism stated directly: the 1-min ATR
    predicts how far the tape will travel, and every exit this bot owns needs travel.

    Kept as a **ranking** term at its existing 15 points rather than promoted to a
    veto: a dead-tape candidate now has to earn the full ``ENTRY_THRESHOLD`` from
    crossover, trend and rsi alone. On the live-regime population that soft form beat
    the hard veto on every window (n=69 / 61% win / PF 3.18 versus n=67 / 55% / 2.57),
    because the 11 dead-tape setups strong enough to clear the bar anyway were
    collectively profitable (+$28.77) while the 150 it declined lost −$357.68.

    No taper above ``_ATR_LIVE``: the highest observed band (0.40–1.00%) was the best
    performer (n=10, 70% win, +$235.22), so there is no evidence for one, and the 2%
    stop already bounds a single over-lively name. Revisit if the bot ever trades a
    genuinely spiky tape. Slippage control is the watchlist's liquidity floor, not
    this term — it never functioned as a spread guard anyway, being pinned at 1.00 for
    65% of all trades and only able to reach 0.0 at a 1-min ATR of 1% of price.
    """
    atr = trigger.atr
    if atr is None or trigger.close <= 0:
        return 0.0
    ratio = atr / trigger.close
    if ratio <= _ATR_DEAD:
        return 0.0
    if ratio >= _ATR_LIVE:
        return 1.0
    return _clamp01((ratio - _ATR_DEAD) / (_ATR_LIVE - _ATR_DEAD))


def confidence(
    trigger: RibbonSnapshot,
    gate: RibbonSnapshot | None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> ConfidenceBreakdown:
    """Weighted blend of the five sub-scores → a 0–100 confidence."""
    xo = score_crossover(trigger)
    tr = score_trend(gate)
    rs = score_rsi(trigger)
    vol = score_volume(trigger)
    vlt = score_volatility(trigger)
    total = (
        xo * weights.crossover
        + tr * weights.trend
        + rs * weights.rsi
        + vol * weights.volume
        + vlt * weights.volatility
    )
    return ConfidenceBreakdown(
        crossover=xo, trend=tr, rsi=rs, volume=vol, volatility=vlt, total=total
    )


# --- market hours ----------------------------------------------------------


def market_is_open(ts_utc: datetime, open_t: time, close_t: time) -> bool:
    """True if ``ts_utc`` falls within the regular session, US Eastern.

    Converts to America/New_York (handling EST/EDT) and checks Mon–Fri within
    ``[open_t, close_t)``. Exchange holidays are not modeled (Phase 8/10).
    """
    et = ts_utc.astimezone(EASTERN)
    if et.weekday() >= 5:  # Saturday/Sunday
        return False
    now = et.time()
    return open_t.replace(tzinfo=None) <= now < close_t.replace(tzinfo=None)


def in_open_blackout(
    ts_utc: datetime, open_t: time, close_t: time, entry_start_t: time
) -> bool:
    """True if ``ts_utc`` is in the open session but before ``entry_start_t`` — the
    opening-range blackout where new entries are refused (IMP-017).

    The ribbon strategy has no edge in the first 30 minutes: over 219 live trades the
    pre-10:00 ET bucket lost $407 (41 trades, 36.6% win) while the other 178 trades
    made +$236, and those 41 produced 48% of all stop-out damage. The 1-min ribbon is
    reading the opening auction gap and the first noise bars, so the crossovers it
    fires on are gap artifacts rather than trends.

    ``entry_start_t == open_t`` disables the blackout (nothing is before the open).
    Mirrors :func:`in_close_window` at the other end of the session; like it, this
    gates ENTRIES only — open positions keep being managed and flattened.
    """
    if not market_is_open(ts_utc, open_t, close_t):
        return False
    et = ts_utc.astimezone(EASTERN)
    return et.time() < entry_start_t.replace(tzinfo=None)


def in_close_window(
    ts_utc: datetime, open_t: time, close_t: time, minutes_before_close: int
) -> bool:
    """True if ``ts_utc`` is in the open session and within ``minutes_before_close``
    of the close — the end-of-day flatten / no-new-entries window.

    ``minutes_before_close == 0`` disables the window (the strict ``< close_t`` in
    :func:`market_is_open` means the close minute itself is already outside it).
    """
    if minutes_before_close <= 0:
        return False
    if not market_is_open(ts_utc, open_t, close_t):
        return False
    et = ts_utc.astimezone(EASTERN)
    close_dt = et.replace(
        hour=close_t.hour, minute=close_t.minute, second=0, microsecond=0
    )
    return et >= close_dt - timedelta(minutes=minutes_before_close)


def minutes_until_close(ts_utc: datetime, close_t: time) -> float:
    """Minutes from ``ts_utc`` to today's session close (US Eastern); negative once
    past it. Lets the EOD-flatten escalation tell whether any retry runway remains
    before the DAY bracket legs expire and an unclosed position carries overnight."""
    et = ts_utc.astimezone(EASTERN)
    close_dt = et.replace(
        hour=close_t.hour, minute=close_t.minute, second=0, microsecond=0
    )
    return (close_dt - et).total_seconds() / 60.0


# --- entry decision --------------------------------------------------------


@dataclass(frozen=True)
class EntryDecision:
    """The result of evaluating one closed 1-min candle for an entry."""

    symbol: str
    candle_start: datetime
    gate_open: bool
    fresh_cross: bool
    candidate: bool
    confidence: ConfidenceBreakdown | None
    enter: bool
    reason: str


def evaluate_entry(
    trigger: RibbonSnapshot,
    gate: RibbonSnapshot | None,
    *,
    threshold: float,
    min_crossover: float = 0.0,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EntryDecision:
    """Apply the gate+trigger candidacy rule, then score qualifying candidates.

    A candidate enters only if its weighted ``confidence.total >= threshold`` **and**
    its 1-min ``confidence.crossover >= min_crossover``. The crossover floor rejects
    setups that clear the total bar on trend/rsi/volume weight while riding a weak,
    non-accelerating cross — the chop-prone cohort that underperformed across the
    clean-book sessions (see ``Config.min_crossover``). ``min_crossover == 0.0``
    disables the floor (the threshold-only behavior prior to IMP-011).

    Does **not** apply the market-hours gate — the caller (state machine) owns the
    clock and checks it before evaluating.
    """
    gate_open = gate is not None and gate.ribbon_ready and gate.gate_open
    fresh = trigger.ribbon_ready and trigger.fresh_cross
    candidate = gate_open and fresh

    if not candidate:
        if not gate_open and not fresh:
            reason = "gate closed, no fresh cross"
        elif not gate_open:
            reason = "gate closed"
        else:
            reason = "no fresh cross"
        return EntryDecision(
            symbol=trigger.symbol,
            candle_start=trigger.candle_start,
            gate_open=gate_open,
            fresh_cross=fresh,
            candidate=False,
            confidence=None,
            enter=False,
            reason=reason,
        )

    conf = confidence(trigger, gate, weights)
    weak_cross = conf.crossover < min_crossover
    enter = conf.total >= threshold and not weak_cross
    if enter:
        reason = f"confidence {conf.total:.1f} >= {threshold:.0f}"
    elif weak_cross and conf.total >= threshold:
        # Cleared the total bar but the cross is too weak — the IMP-011 chop filter.
        reason = f"crossover {conf.crossover:.2f} < {min_crossover:.2f}"
    else:
        reason = f"confidence {conf.total:.1f} < {threshold:.0f}"
    return EntryDecision(
        symbol=trigger.symbol,
        candle_start=trigger.candle_start,
        gate_open=True,
        fresh_cross=True,
        candidate=True,
        confidence=conf,
        enter=enter,
        reason=reason,
    )
