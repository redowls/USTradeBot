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
    in_open_blackout,
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
    atr=0.35,  # 0.35% of close — a live tape, full marks after IMP-036
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


def test_volatility_dead_tape_low_live_tape_high():
    """IMP-036 reversed this: range availability, not spread sanity.

    A 1-min ATR of 0.1% of price cannot reach the 1.25% trail before the flatten, so
    it now scores 0.0 where it used to score full marks.
    """
    assert score_volatility(_snap(atr=0.1, close=100.0)) == 0.0  # 0.10% — dead tape
    assert score_volatility(_snap(atr=0.35, close=100.0)) == 1.0  # 0.35% — travels
    assert score_volatility(_snap(atr=2.0, close=100.0)) == 1.0  # lively stays lively
    mid = score_volatility(_snap(atr=0.25, close=100.0))  # 0.25% — on the ramp
    assert 0.0 < mid < 1.0


def test_volatility_is_monotone_non_decreasing_in_atr():
    """The whole point of IMP-036 is the sign. Guard the direction, not one value.

    Reverting the ramp makes this fail, which is the regression that matters — a
    future edit that "restores tight-is-good" cannot pass silently.
    """
    ratios = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 1.0, 2.0]
    scores = [score_volatility(_snap(atr=r, close=100.0)) for r in ratios]
    assert scores == sorted(scores)
    assert scores[0] == 0.0 and scores[-1] == 1.0


def test_pltr_2026_08_26_dead_tape_entry_no_longer_clears_the_bar():
    """The 2026-08-26 session's only trade, kept as the motivating regression.

    PLTR 18:34 UTC entered on a 1-min ATR of 0.090% of price — deep dead tape — and
    did exactly what 77% of that cohort does: drifted to the end-of-day flatten for
    +0.27% (+$5.28) without ever arming the trail. Recorded sub-scores were
    crossover 0.3304, trend 1.0000, rsi 0.5968, volume 1.0000, volatility 1.0000,
    total 65.82 against ENTRY_THRESHOLD 60.

    Under IMP-036 the volatility term reads 0.0 instead of 1.0, so the same candle
    scores 50.82 and is refused. Losing this winner is the acknowledged cost of the
    change; the cohort it belongs to lost −$328.91 over 161 live-regime trades.
    """
    weights = ScoreWeights()
    recorded = dict(crossover=0.3304, trend=1.0000, rsi=0.5968, volume=1.0000)
    old_total = (
        recorded["crossover"] * weights.crossover
        + recorded["trend"] * weights.trend
        + recorded["rsi"] * weights.rsi
        + recorded["volume"] * weights.volume
        + 1.0 * weights.volatility  # what the old tight-is-good ramp returned
    )
    assert old_total == pytest.approx(65.82, abs=0.01)

    # The tape it actually entered on now scores zero, not full marks.
    assert score_volatility(_snap(atr=0.090, close=100.0)) == 0.0
    new_total = old_total - weights.volatility
    assert new_total == pytest.approx(50.82, abs=0.01)
    assert old_total >= 60.0 > new_total


def test_confidence_weighted_total_in_range():
    weights = ScoreWeights()
    strong = _snap(
        ribbon=(101.0, 100.4, 100.0),
        prev_ribbon=(99.9, 100.4, 100.0),
        close=100.0,
        rsi=55.0,
        volume=200.0,
        avg_volume=100.0,
        atr=0.35,
    )
    gate = _snap(ribbon=(102.0, 101.0, 100.0), prev_ribbon=(101.0, 100.5, 100.0), close=100.0)
    breakdown = confidence(strong, gate, weights)
    assert 0.0 <= breakdown.total <= 100.0
    assert breakdown.total > 60.0  # a strong, confirmed setup clears the threshold


# --- IMP-034: volume is measured but unweighted ----------------------------


def test_weights_still_sum_to_100():
    """Renormalising after dropping volume keeps ENTRY_THRESHOLD semantics intact."""
    w = ScoreWeights()
    total = w.crossover + w.trend + w.rsi + w.volume + w.volatility
    assert total == pytest.approx(100.0)
    assert w.volume == 0.0


def test_volume_subscore_is_reported_but_does_not_move_the_total():
    """The inverted component stays observable and stops paying (IMP-034).

    Volume scored 1.00 on 79 live trades for −$377.93 and 0.00 on 51 for +$185.99, so
    the scorer was paying for the wrong thing. The sub-score must still be recorded —
    ``dbo.trades.conf_volume`` and ``dbo.entry_refusals.conf_volume`` are what keep the
    decision falsifiable — but it must no longer change the ranking.
    """
    gate = _snap(ribbon=(102.0, 101.0, 100.0), prev_ribbon=(101.0, 100.5, 100.0), close=100.0)
    common = dict(
        ribbon=(101.0, 100.4, 100.0),
        prev_ribbon=(99.9, 100.4, 100.0),
        close=100.0,
        rsi=55.0,
        atr=0.35,
    )
    chased = confidence(_snap(volume=200.0, avg_volume=100.0, **common), gate)  # 2.0x
    quiet = confidence(_snap(volume=10.0, avg_volume=100.0, **common), gate)  # 0.1x

    assert chased.volume == pytest.approx(1.0)  # still computed
    assert quiet.volume == pytest.approx(0.0)  # still computed
    assert chased.total == pytest.approx(quiet.total)  # but no longer ranks them


def test_todays_refused_msft_no_longer_outranks_the_wider_cross():
    """Regression on a real 2026-08-24 pair the old weighting ordered backwards.

    Both candidates were refused on 2026-08-24. MSFT 15:07 scored 71.01 on a *narrow*
    cross (conf_crossover 0.2844) carried by volume 0.7110; GOOG 15:09 scored 78.21 on
    a genuinely wide cross (conf_crossover 0.2735, volume 1.0000). Under the old
    weighting a candidate could buy rank with volume alone. After IMP-034 the ranking
    must follow crossover and trend, the two components that discriminate correctly.
    """
    gate = _snap(ribbon=(102.0, 101.0, 100.0), prev_ribbon=(101.0, 100.5, 100.0), close=100.0)
    # Same cross geometry, same trend, same RSI/ATR — volume is the only difference.
    common = dict(
        ribbon=(100.28, 100.1, 100.0),
        prev_ribbon=(100.2, 100.1, 100.0),
        close=100.0,
        rsi=55.0,
        atr=0.35,
    )
    thin_volume = confidence(_snap(volume=50.0, avg_volume=100.0, **common), gate)
    heavy_volume = confidence(_snap(volume=300.0, avg_volume=100.0, **common), gate)
    assert heavy_volume.total == pytest.approx(thin_volume.total)

    # And a wider cross must now outrank a narrow one that is merely heavily traded.
    wide_thin = confidence(
        _snap(
            ribbon=(101.0, 100.4, 100.0),
            prev_ribbon=(99.9, 100.4, 100.0),
            close=100.0,
            rsi=55.0,
            atr=0.35,
            volume=50.0,
            avg_volume=100.0,
        ),
        gate,
    )
    assert wide_thin.total > heavy_volume.total


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


def _entry_start() -> time:
    return time(10, 0, tzinfo=EASTERN)


def test_open_blackout_blocks_the_first_thirty_minutes():
    """IMP-017: entries in the opening range are refused. Over 219 live trades the
    pre-10:00 ET bucket lost $407 (41 trades, 36.6% win) while the rest of the day
    made +$236 — the opening ribbon crosses are gap artifacts, not trends."""
    # 13:35 UTC == 09:35 EDT -> inside the blackout.
    assert in_open_blackout(
        datetime(2026, 6, 2, 13, 35, tzinfo=UTC), _open(), _close(), _entry_start()
    )


def test_open_blackout_boundary_opens_exactly_at_the_cutoff():
    # 13:59 UTC == 09:59 EDT -> still blacked out.
    assert in_open_blackout(
        datetime(2026, 6, 2, 13, 59, tzinfo=UTC), _open(), _close(), _entry_start()
    )
    # 14:00 UTC == 10:00 EDT -> the cutoff minute itself is tradeable.
    assert not in_open_blackout(
        datetime(2026, 6, 2, 14, 0, tzinfo=UTC), _open(), _close(), _entry_start()
    )


def test_open_blackout_disabled_when_cutoff_equals_open():
    """ENTRY_START == MARKET_OPEN restores the pre-IMP-017 behaviour (no blackout)."""
    assert not in_open_blackout(
        datetime(2026, 6, 2, 13, 35, tzinfo=UTC), _open(), _close(), _open()
    )


def test_open_blackout_false_outside_the_session():
    """Pre-market and weekends are already refused by market_is_open — the blackout
    must not claim them, or the caller could not tell the two cases apart."""
    # 12:00 UTC == 08:00 EDT -> pre-market, before the open.
    assert not in_open_blackout(
        datetime(2026, 6, 2, 12, 0, tzinfo=UTC), _open(), _close(), _entry_start()
    )
    # Saturday.
    assert not in_open_blackout(
        datetime(2026, 6, 6, 13, 35, tzinfo=UTC), _open(), _close(), _entry_start()
    )


def test_open_blackout_handles_est_edt_shift():
    # January (EST): 14:35 UTC == 09:35 EST -> inside the blackout.
    assert in_open_blackout(
        datetime(2026, 1, 6, 14, 35, tzinfo=UTC), _open(), _close(), _entry_start()
    )
    # 15:00 UTC == 10:00 EST -> clear of it. Same wall clock, different UTC offset.
    assert not in_open_blackout(
        datetime(2026, 1, 6, 15, 0, tzinfo=UTC), _open(), _close(), _entry_start()
    )


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
        atr=0.35,
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


def _weak_xo_trigger() -> RibbonSnapshot:
    # A genuine fresh cross but a NARROW, barely-accelerating ribbon -> low crossover
    # sub-score, while rsi/volume/volatility stay strong so the weighted total still
    # clears 60. This is 2026-06-26's QQQ/SPY/COST/AMZN/ABNB cohort: confident total,
    # crossover < 0.20, all of which lost. (prev fast 99.995 <= mid -> fresh cross up.)
    return _snap(
        ribbon=(100.02, 100.01, 100.0),
        prev_ribbon=(99.995, 100.01, 100.0),
        close=100.0,
        rsi=55.0,
        volume=200.0,
        avg_volume=100.0,
        atr=0.35,
    )


def test_weak_crossover_clears_total_but_below_floor():
    # Sanity: the fixture is a candidate whose total >= 60 yet crossover < 0.20.
    d = evaluate_entry(_weak_xo_trigger(), _open_gate(), threshold=60.0)
    assert d.candidate and d.confidence is not None
    assert d.confidence.total >= 60.0
    assert d.confidence.crossover < 0.20


def test_min_crossover_floor_blocks_weak_cross_chop_entry():
    # IMP-011: with the floor active, a confident-but-weak-cross candidate is turned
    # away even though its total clears the threshold (today's losing cohort).
    d = evaluate_entry(
        _weak_xo_trigger(), _open_gate(), threshold=60.0, min_crossover=0.20
    )
    assert d.candidate and not d.enter
    assert d.confidence is not None and d.confidence.total >= 60.0
    assert "crossover" in d.reason


def test_min_crossover_floor_disabled_lets_weak_cross_enter():
    # min_crossover=0.0 (default) preserves pre-IMP-011 threshold-only behavior.
    d = evaluate_entry(
        _weak_xo_trigger(), _open_gate(), threshold=60.0, min_crossover=0.0
    )
    assert d.candidate and d.enter
    assert "confidence" in d.reason


def test_min_crossover_floor_allows_strong_cross_entry():
    # A wide, accelerating cross (MSFT/NFLX on 2026-06-26: crossover > 0.40) clears the
    # floor and enters.
    d = evaluate_entry(
        _fresh_trigger(), _open_gate(), threshold=60.0, min_crossover=0.20
    )
    assert d.candidate and d.enter
    assert d.confidence is not None and d.confidence.crossover >= 0.20


def _midweak_xo_trigger() -> RibbonSnapshot:
    # A confident candidate whose crossover lands in the 0.20-0.25 band: a fresh cross
    # that is genuine but narrow/slow (width_score 0.30, slope_score 0.10 ->
    # 0.6*0.30 + 0.4*0.10 = 0.22). This is 2026-07-30's TSLA (crossover 0.206, conf
    # 69.4) — it cleared the old 0.20 floor, entered, and lost -$8.07. Post-floor the
    # 0.20-0.25 band was the single worst cohort (40 tr, -$165.93, avg -$4.15), so
    # IMP-020 raised the default floor to 0.25 to turn this cohort away.
    return _snap(
        ribbon=(100.06, 100.03, 100.0),
        prev_ribbon=(100.05, 100.06, 100.0),
        close=100.0,
        rsi=55.0,
        volume=200.0,
        avg_volume=100.0,
        atr=0.35,
    )


def test_midweak_crossover_lands_in_the_0_20_to_0_25_band():
    # Sanity: the fixture is a confident candidate (total >= 60) with crossover in the
    # cohort IMP-020 targets — above the old 0.20 floor but below the new 0.25 one.
    d = evaluate_entry(_midweak_xo_trigger(), _open_gate(), threshold=60.0)
    assert d.candidate and d.confidence is not None
    assert d.confidence.total >= 60.0
    assert 0.20 <= d.confidence.crossover < 0.25


def test_imp020_floor_blocks_the_0_20_to_0_25_band_that_0_20_admitted():
    # IMP-020 (2026-07-30): the old 0.20 floor ADMITS this cohort (as it did TSLA today),
    # but the new 0.25 default floor turns it away with the crossover reason.
    admitted = evaluate_entry(
        _midweak_xo_trigger(), _open_gate(), threshold=60.0, min_crossover=0.20
    )
    assert admitted.candidate and admitted.enter

    blocked = evaluate_entry(
        _midweak_xo_trigger(), _open_gate(), threshold=60.0, min_crossover=0.25
    )
    assert blocked.candidate and not blocked.enter
    assert "crossover" in blocked.reason


def test_entry_candidate_below_threshold_does_not_enter():
    # A fresh cross but weak confirmation (thin volume, dead tape, neutral RSI).
    # IMP-036 flipped which ATR is the weak one: 0.10% of close cannot travel far
    # enough to arm the trail, so it now scores 0.0 where a 1.5% spike scores 1.0.
    weak = _snap(
        ribbon=(100.05, 100.02, 100.0),
        prev_ribbon=(99.99, 100.02, 100.0),
        close=100.0,
        rsi=40.0,
        prev_rsi=45.0,
        volume=40.0,
        avg_volume=100.0,
        atr=0.1,
    )
    d = evaluate_entry(weak, _open_gate(), threshold=60.0)
    assert d.candidate and not d.enter
    assert d.confidence is not None and d.confidence.total < 60.0
