"""Position sizing + bracket levels (Phase 4).

Turns a confidence score and the current account state into a concrete order
plan: a **whole-share quantity** plus broker-side stop-loss and take-profit
prices for an Alpaca bracket order. Two models (see summary.md):

- **Model A — % of buying power** (default). ``alloc_fraction`` scales linearly
  from ``MIN_ALLOC`` to ``MAX_ALLOC`` across the confidence range above the entry
  threshold; ``notional = buying_power × alloc_fraction``. Worked example
  (bp $10k, min 0.10, max 0.40, threshold 60): conf 80 → $2,500, conf 60 → $1,000,
  conf 100 → $4,000.
- **Model B — risk budget** (optional). Size from the stop distance so each trade
  risks at most ``MAX_RISK_PER_TRADE`` of equity, scaled 0.25→1.0 by confidence,
  then capped so notional never exceeds ``MAX_ALLOC × buying_power``.

**Why whole shares, not notional.** Alpaca rejects bracket orders on
notional/fractional orders — a bracket needs an integer ``qty``. The broker-side
bracket (stop/target that fire even if the bot is down) is a hard requirement
(Phase 5), so we size to a dollar target, then floor to whole shares at the entry
price. Sub-share precision is the deliberate cost of keeping the bracket.

All functions are pure / no I/O — the executor supplies live ``buying_power`` /
``equity`` and the entry price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def confidence_fraction(confidence: float, threshold: float) -> float:
    """Map confidence onto 0–1 across ``[threshold, 100]`` (clamped).

    ``threshold`` → 0.0, ``100`` → 1.0. Below the threshold returns 0.0; this is
    the common scaling input for both sizing models.
    """
    span = 100.0 - threshold
    if span <= 0:
        return 1.0 if confidence >= threshold else 0.0
    return _clamp01((confidence - threshold) / span)


def alloc_fraction(
    confidence: float, *, threshold: float, min_alloc: float, max_alloc: float
) -> float:
    """Model-A wallet fraction: ``min_alloc`` at the threshold → ``max_alloc`` at 100."""
    return min_alloc + (max_alloc - min_alloc) * confidence_fraction(confidence, threshold)


def round_price(price: float) -> float:
    """Round to Alpaca's allowed sub-penny rule: 2 decimals at/above $1, else 4.

    Stocks priced ≥ $1.00 must use penny increments; sub-$1 names allow 4 dp.
    """
    return round(price, 2) if price >= 1.0 else round(price, 4)


def bracket_prices(
    entry_price: float, *, stop_loss: float, take_profit: float
) -> tuple[float, float]:
    """``(stop_price, take_profit_price)`` from fractional offsets around entry."""
    stop = round_price(entry_price * (1.0 - stop_loss))
    target = round_price(entry_price * (1.0 + take_profit))
    return stop, target


@dataclass(frozen=True)
class SizePlan:
    """A concrete, submittable order plan (whole shares + bracket levels)."""

    qty: int
    entry_price: float
    stop_price: float
    take_profit_price: float
    notional: float  # qty × entry_price (actual), after share rounding
    alloc_fraction: float  # Model A only (0.0 for Model B)
    model: str  # "A" or "B"


def plan_model_a(
    *,
    confidence: float,
    entry_price: float,
    buying_power: float,
    threshold: float,
    min_alloc: float,
    max_alloc: float,
    stop_loss: float,
    take_profit: float,
    size_confidence_cap: float = 100.0,
) -> SizePlan | None:
    """Size by % of buying power. ``None`` if it rounds to fewer than 1 share.

    ``size_confidence_cap`` caps the confidence used *for sizing only* (100 = no
    cap): a candidate scoring above it is sized as if it scored the cap, because the
    realized edge does not increase with confidence above the sweet spot (see the
    all-time confidence-outcome curve — IMP-013). This only ever *reduces* size on
    very-high-confidence entries; it never enlarges a position or blocks an entry.
    """
    if entry_price <= 0 or buying_power <= 0:
        return None
    eff_conf = confidence if confidence <= size_confidence_cap else size_confidence_cap
    frac = alloc_fraction(eff_conf, threshold=threshold, min_alloc=min_alloc, max_alloc=max_alloc)
    notional_target = buying_power * frac
    qty = math.floor(notional_target / entry_price)
    if qty < 1:
        return None
    stop, target = bracket_prices(entry_price, stop_loss=stop_loss, take_profit=take_profit)
    return SizePlan(
        qty=qty,
        entry_price=entry_price,
        stop_price=stop,
        take_profit_price=target,
        notional=qty * entry_price,
        alloc_fraction=frac,
        model="A",
    )


def plan_model_b(
    *,
    confidence: float,
    entry_price: float,
    buying_power: float,
    equity: float,
    threshold: float,
    max_risk_per_trade: float,
    max_alloc: float,
    stop_loss: float,
    take_profit: float,
    size_confidence_cap: float = 100.0,
) -> SizePlan | None:
    """Size by risk budget: shares from the stop distance, capped by ``max_alloc``.

    ``effective_risk = max_risk_per_trade × (0.25 → 1.0 by confidence)``; shares =
    ``equity × effective_risk / (entry − stop)``, then capped so the notional stays
    within ``max_alloc × buying_power``. ``None`` if it rounds below 1 share.

    ``size_confidence_cap`` caps the confidence used for the risk multiplier only
    (100 = no cap), mirroring :func:`plan_model_a` — see IMP-013.
    """
    if entry_price <= 0 or buying_power <= 0 or equity <= 0:
        return None
    stop, target = bracket_prices(entry_price, stop_loss=stop_loss, take_profit=take_profit)
    risk_per_share = entry_price - stop
    if risk_per_share <= 0:
        return None
    eff_conf = confidence if confidence <= size_confidence_cap else size_confidence_cap
    multiplier = 0.25 + 0.75 * confidence_fraction(eff_conf, threshold)
    effective_risk = max_risk_per_trade * multiplier
    risk_qty = math.floor((equity * effective_risk) / risk_per_share)
    cap_qty = math.floor((max_alloc * buying_power) / entry_price)
    qty = min(risk_qty, cap_qty)
    if qty < 1:
        return None
    return SizePlan(
        qty=qty,
        entry_price=entry_price,
        stop_price=stop,
        take_profit_price=target,
        notional=qty * entry_price,
        alloc_fraction=0.0,
        model="B",
    )
