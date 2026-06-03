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

All functions are pure. The volatility sub-score uses an ATR/price proxy because
the IEX trade feed gives us no bid/ask spread to measure directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

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

# Volatility / spread sanity: ATR/close. Tight is good; spikes score low.
_ATR_GOOD = 0.0020  # <= this -> 1.0
_ATR_BAD = 0.0100  # >= this -> 0.0


@dataclass(frozen=True)
class ScoreWeights:
    """Weights for the five confidence components (should sum to 100)."""

    crossover: float = 30.0
    trend: float = 20.0
    rsi: float = 20.0
    volume: float = 15.0
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
    """Volatility / spread sanity (ATR/price proxy): tight scores high, spikes low."""
    atr = trigger.atr
    if atr is None or trigger.close <= 0:
        return 0.0
    ratio = atr / trigger.close
    if ratio <= _ATR_GOOD:
        return 1.0
    if ratio >= _ATR_BAD:
        return 0.0
    return _clamp01((_ATR_BAD - ratio) / (_ATR_BAD - _ATR_GOOD))


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
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EntryDecision:
    """Apply the gate+trigger candidacy rule, then score qualifying candidates.

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
    enter = conf.total >= threshold
    reason = (
        f"confidence {conf.total:.1f} >= {threshold:.0f}"
        if enter
        else f"confidence {conf.total:.1f} < {threshold:.0f}"
    )
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
