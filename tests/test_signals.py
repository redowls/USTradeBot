"""Tests for the signal + confidence scorer (Phase 3)."""

from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

from bot.config import EASTERN
from bot.indicators import RibbonSnapshot
from bot.signals import (
    ScoreWeights,
    confidence,
    evaluate_entry,
    in_close_window,
    market_is_open,
    minutes_until_close,
    score_crossover,
    score_rsi,
    score_trend,
    score_volatility,
    score_volume,
)

_T = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)


def _snap(
    *,
    ribbon=(101.0, 100.5, 100.0),
    prev_ribbon=(100.4, 100.5, 100.0),
    close=101.0,
    volume=150.0,
    rsi=55.0,
    prev_rsi=50.0,
    avg_volume=100.0,
    atr=0.2,
    interval_seconds=60,
    symbol="NFLX",
) -> RibbonSnapshot:
    return RibbonSnapshot(
        symbol=symbol,
        candle_start=_T,
        interval_seconds=interval_seconds,
        close=close,
        volume=volume,
        ribbon=ribbon,
        prev_ribbon=prev_ribbon,
        rsi=rsi,
        prev_rsi=prev_rsi,
        avg_volume=avg_volume,
        atr=atr,
    )


# --- individual sub-scores -------------------------------------------------


def test_crossover_wider_ribbon_scores_higher():
    tight = _snap(ribbon=(100.05, 100.02, 100.0), prev_ribbon=(100.0, 100.02, 100.0), close=100.0)
    wide = _snap(ribbon=(100.5, 100.2, 100.0), prev_ribbon=(99.9, 100.2, 100.0), close=100.0)
    assert score_crossover(wide) > score_crossover(tight)


def test_crossover_zero_when_not_ready():
    s = _snap(ribbon=(None, None, None), prev_ribbon=(None, None, None))
    assert score_crossover(s) == 0.0


def test_trend_zero_when_unstacked_or_missing():
    assert score_trend(None) == 0.0
    unstacked = _snap(ribbon=(100.0, 100.5, 101.0), prev_ribbon=(100.0, 100.5, 101.0))
    assert score_trend(unstacked) == 0.0


def test_trend_rewards_stacked_and_rising():
    flat = _snap(ribbon=(100.1, 100.05, 100.0), prev_ribbon=(100.1, 100.05, 100.0), close=100.0)
    strong = _snap(ribbon=(101.0, 100.5, 100.0), prev_ribbon=(100.5, 100.4, 100.0), close=100.0)
    assert score_trend(strong) > score_trend(flat)
    assert score_trend(strong) <= 1.0


def test_rsi_zones():
    assert score_rsi(_snap(rsi=55.0)) == 1.0  # healthy band
    assert score_rsi(_snap(rsi=75.0)) == 0.0  # overbought
    # turning up from oversold gets a bonus over a flat low reading
    turning = _snap(rsi=35.0, prev_rsi=31.0)
    flat = _snap(rsi=35.0, prev_rsi=40.0)
    assert score_rsi(turning) > score_rsi(flat)


def test_volume_ratio_mapping():
    assert score_volume(_snap(volume=150.0, avg_volume=100.0)) == pytest.approx(1.0)  # 1.5x
    assert score_volume(_snap(volume=50.0, avg_volume=100.0)) == pytest.approx(0.0)  # 0.5x
    assert score_volume(_snap(volume=100.0, avg_volume=100.0)) == pytest.approx(0.5)
    assert score_volume(_snap(avg_volume=None)) == 0.0


def test_volatility_tight_high_spike_low():
    assert score_volatility(_snap(atr=0.1, close=100.0)) == 1.0  # 0.1% tight
    assert score_volatility(_snap(atr=2.0, close=100.0)) == 0.0  # 2% spike
    mid = score_volatility(_snap(atr=0.6, close=100.0))  # 0.6% between
    assert 0.0 < mid < 1.0


def test_confidence_weighted_total_in_range():
    weights = ScoreWeights()
    strong = _snap(
        ribbon=(101.0, 100.4, 100.0),
        prev_ribbon=(99.9, 100.4, 100.0),
        close=100.0,
        rsi=55.0,
        volume=200.0,
        avg_volume=100.0,
        atr=0.1,
    )
    gate = _snap(ribbon=(102.0, 101.0, 100.0), prev_ribbon=(101.0, 100.5, 100.0), close=100.0)
    breakdown = confidence(strong, gate, weights)
    assert 0.0 <= breakdown.total <= 100.0
    assert breakdown.total > 60.0  # a strong, confirmed setup clears the threshold


# --- market hours ----------------------------------------------------------


def _open() -> time:
    return time(9, 30, tzinfo=EASTERN)


def _close() -> time:
    return time(16, 0, tzinfo=EASTERN)


def test_market_open_during_session():
    # 2026-06-02 is a Tuesday; 14:00 UTC == 10:00 EDT -> open.
    assert market_is_open(datetime(2026, 6, 2, 14, 0, tzinfo=UTC), _open(), _close())


def test_market_closed_before_open():
    # 13:00 UTC == 09:00 EDT -> before the open.
    assert not market_is_open(datetime(2026, 6, 2, 13, 0, tzinfo=UTC), _open(), _close())


def test_market_closed_on_weekend():
    # 2026-06-06 is a Saturday.
    assert not market_is_open(datetime(2026, 6, 6, 14, 0, tzinfo=UTC), _open(), _close())


def test_market_hours_handle_est_edt_shift():
    # Standard time (January): 14:00 UTC == 09:00 EST -> before open.
    assert not market_is_open(datetime(2026, 1, 6, 14, 0, tzinfo=UTC), _open(), _close())
    # 15:00 UTC == 10:00 EST -> open. Same wall-clock gate, different UTC offset.
    assert market_is_open(datetime(2026, 1, 6, 15, 0, tzinfo=UTC), _open(), _close())


def test_close_window_only_in_final_minutes():
    # 19:54 UTC == 15:54 EDT -> 6 min to close, outside a 5-min window.
    assert not in_close_window(datetime(2026, 6, 2, 19, 54, tzinfo=UTC), _open(), _close(), 5)
    # 19:56 UTC == 15:56 EDT -> 4 min to close, inside it.
    assert in_close_window(datetime(2026, 6, 2, 19, 56, tzinfo=UTC), _open(), _close(), 5)


def test_close_window_15min_catches_late_thin_tape_candle():
    """IMP-005 regression: the 2026-06-18 naked-overnight carry.

    On a thin pre-close tape the flatten is driven by activity-driven candle closes
    that lag. GOOG's last candle events that day were ~15:49 and ~15:54 ET, then a
    22-min gap to 16:16 — so under the old 5-min window (opens 15:55) no liquid-tape
    candle fell inside it and the flatten only fired at 16:16, past the close, landing
    `accepted` and never filling. A 15-min window (opens 15:45 ET) puts the 15:49
    candle *inside* the flatten window, giving it time to fill before 16:00.
    19:49 UTC == 15:49 EDT.
    """
    late_candle = datetime(2026, 6, 2, 19, 49, tzinfo=UTC)
    assert not in_close_window(late_candle, _open(), _close(), 5)   # old window missed it
    assert in_close_window(late_candle, _open(), _close(), 15)      # IMP-005 catches it


def test_close_window_false_when_market_closed():
    # 21:00 UTC == 17:00 EDT -> after the close, no window.
    assert not in_close_window(datetime(2026, 6, 2, 21, 0, tzinfo=UTC), _open(), _close(), 5)
    # On a weekend, never.
    assert not in_close_window(datetime(2026, 6, 6, 19, 56, tzinfo=UTC), _open(), _close(), 5)


def test_close_window_disabled_when_zero():
    assert not in_close_window(datetime(2026, 6, 2, 19, 59, tzinfo=UTC), _open(), _close(), 0)


def test_minutes_until_close_counts_down_and_goes_negative():
    # 20:00 UTC == 16:00 EDT close. Drives the IMP-002 naked-overnight escalation.
    assert minutes_until_close(datetime(2026, 6, 2, 19, 59, tzinfo=UTC), _close()) == pytest.approx(1.0)
    assert minutes_until_close(datetime(2026, 6, 2, 19, 56, tzinfo=UTC), _close()) == pytest.approx(4.0)
    assert minutes_until_close(datetime(2026, 6, 2, 20, 1, tzinfo=UTC), _close()) == pytest.approx(-1.0)


# --- entry decision --------------------------------------------------------


def _fresh_trigger() -> RibbonSnapshot:
    # prev fast <= mid, now fast > mid > slow -> fresh cross, healthy confirmation.
    return _snap(
        ribbon=(101.0, 100.4, 100.0),
        prev_ribbon=(99.9, 100.4, 100.0),
        close=100.0,
        rsi=55.0,
        volume=200.0,
        avg_volume=100.0,
        atr=0.1,
    )


def _open_gate() -> RibbonSnapshot:
    return _snap(ribbon=(102.0, 101.0, 100.0), prev_ribbon=(101.0, 100.5, 100.0), close=100.0)


def test_entry_blocked_when_gate_closed():
    closed_gate = _snap(ribbon=(100.0, 100.5, 101.0), prev_ribbon=(100.0, 100.5, 101.0))
    d = evaluate_entry(_fresh_trigger(), closed_gate, threshold=60.0)
    assert not d.candidate and not d.enter
    assert d.confidence is None
    assert "gate" in d.reason


def test_entry_blocked_when_no_fresh_cross():
    stale = _snap(ribbon=(101.0, 100.5, 100.0), prev_ribbon=(100.8, 100.5, 100.0))  # already above
    d = evaluate_entry(stale, _open_gate(), threshold=60.0)
    assert not d.candidate and not d.enter


def test_entry_fires_when_gate_and_trigger_align_and_confident():
    d = evaluate_entry(_fresh_trigger(), _open_gate(), threshold=60.0)
    assert d.candidate and d.enter
    assert d.confidence is not None and d.confidence.total >= 60.0


def test_entry_candidate_below_threshold_does_not_enter():
    # A fresh cross but weak confirmation (thin volume, wide ATR, neutral RSI).
    weak = _snap(
        ribbon=(100.05, 100.02, 100.0),
        prev_ribbon=(99.99, 100.02, 100.0),
        close=100.0,
        rsi=40.0,
        prev_rsi=45.0,
        volume=40.0,
        avg_volume=100.0,
        atr=1.5,
    )
    d = evaluate_entry(weak, _open_gate(), threshold=60.0)
    assert d.candidate and not d.enter
    assert d.confidence is not None and d.confidence.total < 60.0
