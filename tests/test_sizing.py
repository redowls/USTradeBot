"""Tests for position sizing + bracket levels (Phase 4).

Pure math, hand-checked against the worked examples in summary.md.
"""

from __future__ import annotations

import pytest

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


def test_model_a_size_confidence_cap_shrinks_top_band():
    # IMP-013: 2026-07-06's AVGO scored conf 96 and, uncapped, drew the day's biggest
    # position (~0.37 of BP) → the biggest loss. The all-time curve shows edge does not
    # grow above the ~70s, so a cap sizes a > cap candidate as if it scored the cap.
    # Uncapped: conf 96 -> 0.10 + 0.30*((96-60)/40) = 0.37 -> $3700 -> 37 @ $100.
    uncapped = plan_model_a(confidence=96.0, entry_price=100.0, buying_power=10000.0, **_A)
    assert uncapped.qty == 37
    # Capped at 85: sized as conf 85 -> 0.10 + 0.30*((85-60)/40) = 0.2875 -> $2875 -> 28.
    capped = plan_model_a(
        confidence=96.0, entry_price=100.0, buying_power=10000.0, size_confidence_cap=85.0, **_A
    )
    assert capped.qty == 28
    assert capped.alloc_fraction == pytest.approx(0.2875)
    # A candidate exactly at the cap is sized identically to the > cap one.
    at_cap = plan_model_a(
        confidence=85.0, entry_price=100.0, buying_power=10000.0, size_confidence_cap=85.0, **_A
    )
    assert at_cap.qty == capped.qty


def test_model_a_size_confidence_cap_leaves_below_cap_and_default_unchanged():
    # Below the cap: sizing is untouched (conf 80 -> 0.25 -> 25 @ $100, same as no cap).
    below = plan_model_a(
        confidence=80.0, entry_price=100.0, buying_power=10000.0, size_confidence_cap=85.0, **_A
    )
    assert below.qty == 25
    # Default (100) disables the cap — identical to the pre-IMP-013 behavior.
    assert (
        plan_model_a(confidence=100.0, entry_price=100.0, buying_power=10000.0, **_A).qty
        == plan_model_a(
            confidence=100.0, entry_price=100.0, buying_power=10000.0,
            size_confidence_cap=100.0, **_A
        ).qty
        == 40
    )


def test_model_b_size_confidence_cap_limits_multiplier():
    # conf 100 uncapped -> multiplier 1.0 -> capped by max_alloc at 40 shares.
    # Capped at 80 -> multiplier 0.25 + 0.75*((80-60)/40) = 0.625 -> risk 0.0125 ->
    # 10000*0.0125/2 = 62 shares, still above the max_alloc cap (40) -> 40. Use a
    # smaller risk budget so the confidence cap (not max_alloc) binds.
    _Bsmall = dict(_B, max_risk_per_trade=0.005)
    uncapped = plan_model_b(
        confidence=100.0, entry_price=100.0, buying_power=10000.0, equity=10000.0, **_Bsmall
    )
    # conf 100 -> mult 1.0 -> risk 0.005 -> 10000*0.005/2 = 25 shares.
    assert uncapped.qty == 25
    capped = plan_model_b(
        confidence=100.0, entry_price=100.0, buying_power=10000.0, equity=10000.0,
        size_confidence_cap=80.0, **_Bsmall,
    )
    # sized as conf 80 -> mult 0.625 -> risk 0.003125 -> 10000*0.003125/2 = 15 shares.
    assert capped.qty == 15


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
