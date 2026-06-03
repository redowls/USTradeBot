"""Tests for position sizing + bracket levels (Phase 4).

Pure math, hand-checked against the worked examples in summary.md.
"""

from __future__ import annotations

from bot.sizing import (
    alloc_fraction,
    bracket_prices,
    confidence_fraction,
    plan_model_a,
    plan_model_b,
    round_price,
)

# Defaults matching the worked example: bp $10k, min 0.10, max 0.40, threshold 60.
_A = dict(threshold=60.0, min_alloc=0.10, max_alloc=0.40, stop_loss=0.02, take_profit=0.04)


# --- scaling helpers -------------------------------------------------------


def test_confidence_fraction_spans_threshold_to_100():
    assert confidence_fraction(60.0, 60.0) == 0.0
    assert confidence_fraction(80.0, 60.0) == 0.5
    assert confidence_fraction(100.0, 60.0) == 1.0
    assert confidence_fraction(50.0, 60.0) == 0.0  # below threshold clamps to 0


def test_alloc_fraction_matches_worked_example():
    assert (
        alloc_fraction(60.0, **{k: _A[k] for k in ("threshold", "min_alloc", "max_alloc")}) == 0.10
    )
    assert (
        alloc_fraction(80.0, **{k: _A[k] for k in ("threshold", "min_alloc", "max_alloc")}) == 0.25
    )
    assert (
        alloc_fraction(100.0, **{k: _A[k] for k in ("threshold", "min_alloc", "max_alloc")}) == 0.40
    )


# --- price rounding / bracket ----------------------------------------------


def test_round_price_penny_above_dollar_subpenny_below():
    assert round_price(98.123) == 98.12
    assert round_price(0.51234) == 0.5123


def test_bracket_prices():
    stop, target = bracket_prices(100.0, stop_loss=0.02, take_profit=0.04)
    assert stop == 98.0
    assert target == 104.0


# --- Model A ---------------------------------------------------------------


def test_model_a_worked_examples():
    # conf 80 -> 0.25 * 10000 = $2500 -> 25 shares @ 100
    plan = plan_model_a(confidence=80.0, entry_price=100.0, buying_power=10000.0, **_A)
    assert plan is not None
    assert plan.qty == 25
    assert plan.notional == 2500.0
    assert plan.alloc_fraction == 0.25
    assert (plan.stop_price, plan.take_profit_price) == (98.0, 104.0)
    assert plan.model == "A"

    # conf 60 -> 0.10 -> $1000 -> 10 shares
    assert plan_model_a(confidence=60.0, entry_price=100.0, buying_power=10000.0, **_A).qty == 10
    # conf 100 -> 0.40 -> $4000 -> 40 shares
    assert plan_model_a(confidence=100.0, entry_price=100.0, buying_power=10000.0, **_A).qty == 40


def test_model_a_floors_to_whole_shares():
    # 0.25 * 10000 = $2500; at $101 that's 24.75 -> floored to 24
    plan = plan_model_a(confidence=80.0, entry_price=101.0, buying_power=10000.0, **_A)
    assert plan.qty == 24
    assert plan.notional == 24 * 101.0


def test_model_a_returns_none_below_one_share():
    # $1000 * 0.10 = $100 target, price $150 -> 0 shares
    assert plan_model_a(confidence=60.0, entry_price=150.0, buying_power=1000.0, **_A) is None
    assert plan_model_a(confidence=80.0, entry_price=10.0, buying_power=0.0, **_A) is None


# --- Model B ---------------------------------------------------------------

_B = dict(threshold=60.0, max_risk_per_trade=0.02, max_alloc=0.40, stop_loss=0.02, take_profit=0.04)


def test_model_b_risk_budget_and_cap():
    # entry 100, stop 98 -> risk/share = 2. equity 10000.
    # conf 100 -> multiplier 1.0 -> risk 0.02 -> 10000*0.02/2 = 100 shares,
    # but capped by max_alloc: 0.40*10000/100 = 40.
    plan = plan_model_b(
        confidence=100.0, entry_price=100.0, buying_power=10000.0, equity=10000.0, **_B
    )
    assert plan is not None
    assert plan.qty == 40  # capped
    assert plan.model == "B"
    assert plan.alloc_fraction == 0.0

    # conf 60 -> multiplier 0.25 -> risk 0.005 -> 10000*0.005/2 = 25 (< cap 40)
    assert (
        plan_model_b(
            confidence=60.0, entry_price=100.0, buying_power=10000.0, equity=10000.0, **_B
        ).qty
        == 25
    )


def test_model_b_none_when_no_stop_distance_or_too_small():
    # stop_loss 0 -> entry == stop -> no risk distance
    bad = dict(_B, stop_loss=0.0)
    assert (
        plan_model_b(
            confidence=80.0, entry_price=100.0, buying_power=10000.0, equity=10000.0, **bad
        )
        is None
    )
    # tiny equity -> < 1 share
    assert (
        plan_model_b(confidence=60.0, entry_price=100.0, buying_power=10.0, equity=10.0, **_B)
        is None
    )
