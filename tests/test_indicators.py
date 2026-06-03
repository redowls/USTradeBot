"""Tests for the indicator engine (Phase 2, generalized to ribbons in Phase 3).

The indicator math is asserted against hand-computed values on small periods so
the expectations are checkable by eye.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bot.candles import Candle
from bot.indicators import (
    Ribbon,
    RibbonEngine,
    _Atr,
    _Ema,
    _Rsi,
    _Sma,
    _TrailingMean,
)

_START = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)


def _candle(
    i: int,
    close: float,
    *,
    high: float | None = None,
    low: float | None = None,
    volume: float = 100.0,
    symbol: str = "NFLX",
) -> Candle:
    """A closed candle at minute ``i``; O/H/L default to close unless given."""
    return Candle(
        symbol=symbol,
        start=_START + timedelta(minutes=i),
        open=close,
        high=close if high is None else high,
        low=close if low is None else low,
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


def test_atr_seeds_then_wilder_smooths():
    atr = _Atr(2)
    # bar1: no prev close -> TR = high-low = 2
    assert atr.update(11.0, 9.0, 10.0) is None
    # bar2: TR = max(12-11, |12-10|, |11-10|) = 2 -> seed = mean(2,2) = 2
    assert atr.update(12.0, 11.0, 11.5) == pytest.approx(2.0)
    # bar3: TR = max(13-12, |13-11.5|, |12-11.5|) = 1.5
    # Wilder: (2*(2-1) + 1.5)/2 = 1.75
    assert atr.update(13.0, 12.0, 12.5) == pytest.approx(1.75)


def test_trailing_mean_excludes_current_value():
    tm = _TrailingMean(2)
    assert tm.current() is None
    tm.push(10.0)
    assert tm.current() is None  # only one sample
    tm.push(20.0)
    assert tm.current() == pytest.approx(15.0)  # mean(10, 20)
    tm.push(30.0)
    assert tm.current() == pytest.approx(25.0)  # mean(20, 30), 10 aged out


# --- ribbon ----------------------------------------------------------------


def test_ribbon_rejects_bad_ordering():
    with pytest.raises(ValueError):
        Ribbon((20, 10, 8))


def test_ribbon_tracks_current_and_previous():
    r = Ribbon((1, 2, 3))  # period-1 EMA == price, others seed slower
    r.update(10.0)
    first = r.values
    r.update(11.0)
    assert r.prev == first


# --- engine: snapshot helpers ---------------------------------------------


def _engine(**kw) -> RibbonEngine:
    """Trigger-style engine with small periods for hand-checkable behavior."""
    opts = dict(rsi_period=2, volume_period=2, atr_period=2, interval_seconds=60)
    opts.update(kw)
    return RibbonEngine((2, 3, 4), **opts)


def test_ribbon_not_ready_until_seeded_with_prev():
    eng = _engine()
    snaps = [eng.update(_candle(i, 100.0 + i)) for i in range(6)]
    readys = [s.ribbon_ready for s in snaps]
    # slow EMA (period 4) seeds on candle index 3; prev-ribbon complete on index 4.
    assert readys[3] is False
    assert readys[4] is True


def test_stacked_and_fresh_cross_detection():
    eng = _engine()
    # Decline so fast<=mid, then a sharp spike to force a fresh bullish cross.
    closes = [20.0, 18.0, 16.0, 14.0, 12.0, 40.0]
    snap = None
    for i, c in enumerate(closes):
        snap = eng.update(_candle(i, c))
    assert snap.ribbon_ready
    assert snap.stacked  # fast > mid > slow after the spike
    assert snap.fresh_cross  # prev fast<=mid, now stacked above slow


def test_gate_open_requires_stacked_and_rising():
    eng = RibbonEngine((2, 3, 4), interval_seconds=300)
    snap = None
    for i, c in enumerate([10.0, 11.0, 12.0, 13.0, 14.0, 15.0]):
        snap = eng.update(_candle(i, c))
    assert snap.gate_open  # steadily rising -> stacked and fast rising
    assert snap.rsi is None and snap.atr is None  # gate engine has no extras


def test_avg_volume_is_trailing_not_self_inclusive():
    eng = _engine()
    vols = [100.0, 200.0, 300.0, 400.0]
    snaps = [eng.update(_candle(i, 50.0 + i, volume=v)) for i, v in enumerate(vols)]
    assert snaps[0].avg_volume is None and snaps[1].avg_volume is None
    assert snaps[2].avg_volume == pytest.approx(150.0)  # mean(100, 200)
    assert snaps[3].avg_volume == pytest.approx(250.0)  # mean(200, 300), excludes 400


def test_symbols_are_independent():
    eng = _engine()
    for i in range(5):
        eng.update(_candle(i, 100.0 + i, symbol="NFLX"))
    nflx = eng.snapshot("NFLX")
    eng.update(_candle(0, 50.0, symbol="WPM"))
    wpm = eng.snapshot("WPM")
    assert nflx.symbol == "NFLX" and nflx.ribbon_ready
    assert wpm.symbol == "WPM" and not wpm.ribbon_ready  # WPM only one candle in
    assert eng.snapshot("BIRD") is None  # never updated


def test_trigger_and_gate_from_config():
    cfg = _FakeConfig()
    trig = RibbonEngine.trigger(cfg)
    gate = RibbonEngine.gate(cfg)
    assert trig._periods == (8, 10, 20) and trig._interval == 60
    assert trig._rsi == 14 and trig._atr == 14 and trig._volume == 20
    assert gate._periods == (21, 34, 55) and gate._interval == 300
    assert gate._rsi == 0 and gate._atr == 0  # gate carries the ribbon only


class _FakeConfig:
    """Minimal stand-in exposing only the fields the engine factories read."""

    short_ma_periods = (8, 10, 20)
    long_ma_periods = (21, 34, 55)
    rsi_period = 14
    volume_ma_period = 20
    atr_period = 14
    interval_seconds = 60
    long_interval_seconds = 300
