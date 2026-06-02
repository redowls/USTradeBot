"""Tests for the indicator engine (Phase 2).

The indicator math is asserted against hand-computed values on small periods so
the expectations are checkable by eye.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bot.candles import Candle
from bot.indicators import (
    IndicatorEngine,
    _Ema,
    _Rsi,
    _Sma,
    _TrailingMean,
)

_START = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)


def _candle(i: int, close: float, *, volume: float = 100.0, symbol: str = "NFLX") -> Candle:
    """A closed candle at minute ``i`` with a flat O/H/L = close (only close/volume matter here)."""
    return Candle(
        symbol=symbol,
        start=_START + timedelta(minutes=i),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=volume,
        trades=1,
    )


# --- primitives ------------------------------------------------------------


def test_ema_seeds_from_sma_then_applies_recurrence():
    ema = _Ema(3)  # k = 2/(3+1) = 0.5
    assert ema.update(1.0) is None
    assert ema.update(2.0) is None
    assert ema.update(3.0) == pytest.approx(2.0)  # seed = mean(1,2,3)
    # next = 4 * 0.5 + 2.0 * 0.5 = 3.0
    assert ema.update(4.0) == pytest.approx(3.0)


def test_sma_is_none_until_full_then_windows():
    sma = _Sma(3)
    assert sma.update(1.0) is None
    assert sma.update(2.0) is None
    assert sma.update(3.0) == pytest.approx(2.0)
    assert sma.update(4.0) == pytest.approx(3.0)  # mean(2,3,4), oldest drops out


def test_rsi_all_gains_is_100():
    rsi = _Rsi(3)
    out = [rsi.update(p) for p in (10.0, 11.0, 12.0, 13.0)]
    assert out[:3] == [None, None, None]  # needs 3 changes -> 4 closes
    assert out[3] == pytest.approx(100.0)  # no losses -> avg_loss 0 -> RSI 100


def test_rsi_wilder_smoothing_matches_hand_calc():
    rsi = _Rsi(3)
    for p in (10.0, 11.0, 10.0, 11.0):  # changes +1, -1, +1 -> seed complete
        rsi.update(p)
    # seed: avg_gain = 2/3, avg_loss = 1/3 -> RS 2 -> RSI 66.667
    assert rsi.value == pytest.approx(66.6667, abs=1e-3)
    rsi.update(12.0)  # +1: avg_gain = 7/9, avg_loss = 2/9 -> RS 3.5 -> RSI 77.778
    assert rsi.value == pytest.approx(77.7778, abs=1e-3)


def test_rsi_rejects_degenerate_period():
    with pytest.raises(ValueError):
        _Rsi(1)


def test_trailing_mean_excludes_current_value():
    tm = _TrailingMean(2)
    assert tm.current() is None
    tm.push(10.0)
    assert tm.current() is None  # only one sample
    tm.push(20.0)
    assert tm.current() == pytest.approx(15.0)  # mean(10, 20)
    tm.push(30.0)
    assert tm.current() == pytest.approx(25.0)  # mean(20, 30), 10 aged out


# --- engine ----------------------------------------------------------------


def test_snapshot_not_ready_until_all_indicators_seeded():
    eng = IndicatorEngine(
        fast_period=2, slow_period=3, trend_period=4, rsi_period=2, volume_period=2
    )
    snaps = [eng.update(_candle(i, 100.0 + i)) for i in range(4)]
    # trend(4) is the longest -> ready on the 4th candle (index 3)
    assert [s.ready for s in snaps] == [False, False, False, True]
    last = snaps[-1]
    assert last.fast_ema is not None and last.slow_ema is not None
    assert last.trend_ma is not None and last.rsi is not None and last.avg_volume is not None


def test_snapshot_carries_previous_emas_for_crossover_detection():
    eng = IndicatorEngine(
        fast_period=2, slow_period=3, trend_period=3, rsi_period=2, volume_period=2
    )
    first = eng.update(_candle(0, 100.0))
    assert first.prev_fast_ema is None and first.prev_slow_ema is None
    second = eng.update(_candle(1, 101.0))
    assert second.prev_fast_ema == first.fast_ema
    assert second.prev_slow_ema == first.slow_ema


def test_fresh_bullish_cross_is_detectable_from_one_snapshot():
    # Fast EMA starts below slow, then a jump pushes it above: prev<=, curr>.
    eng = IndicatorEngine(
        fast_period=2, slow_period=3, trend_period=3, rsi_period=2, volume_period=2
    )
    closes = [10.0, 9.0, 8.0, 8.0, 20.0]  # decline (fast<=slow) then a spike up
    snap = None
    for i, c in enumerate(closes):
        snap = eng.update(_candle(i, c))
    assert snap.prev_fast_ema <= snap.prev_slow_ema
    assert snap.fast_ema > snap.slow_ema  # the cross happened on this candle


def test_avg_volume_is_trailing_not_self_inclusive():
    eng = IndicatorEngine(
        fast_period=2, slow_period=3, trend_period=2, rsi_period=2, volume_period=2
    )
    vols = [100.0, 200.0, 300.0, 400.0]
    snaps = [eng.update(_candle(i, 50.0 + i, volume=v)) for i, v in enumerate(vols)]
    assert snaps[0].avg_volume is None and snaps[1].avg_volume is None
    assert snaps[2].avg_volume == pytest.approx(150.0)  # mean(100, 200)
    assert snaps[3].avg_volume == pytest.approx(250.0)  # mean(200, 300), excludes 400


def test_symbols_are_independent():
    eng = IndicatorEngine(
        fast_period=2, slow_period=3, trend_period=3, rsi_period=2, volume_period=2
    )
    for i in range(3):
        eng.update(_candle(i, 100.0 + i, symbol="NFLX"))
    nflx = eng.snapshot("NFLX")
    eng.update(_candle(0, 50.0, symbol="WPM"))
    wpm = eng.snapshot("WPM")
    assert nflx.symbol == "NFLX" and nflx.fast_ema is not None
    assert wpm.symbol == "WPM" and wpm.fast_ema is None  # WPM only one candle in
    assert eng.snapshot("BIRD") is None  # never updated


def test_from_config_uses_config_periods():
    eng = IndicatorEngine.from_config(_FakeConfig())
    assert eng._fast == 9 and eng._slow == 21 and eng._trend == 50
    assert eng._rsi == 14 and eng._volume == 20


def test_engine_rejects_bad_periods():
    with pytest.raises(ValueError):
        IndicatorEngine(fast_period=21, slow_period=9)  # fast must be < slow
    with pytest.raises(ValueError):
        IndicatorEngine(trend_period=0)


class _FakeConfig:
    """Minimal stand-in exposing only the period fields the engine reads."""

    fast_ma_period = 9
    slow_ma_period = 21
    trend_ma_period = 50
    rsi_period = 14
    volume_ma_period = 20
