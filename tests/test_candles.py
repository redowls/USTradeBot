"""Tests for the candle aggregator (Phase 1)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bot.candles import Candle, CandleAggregator


def _ts(minute: int, second: int = 0) -> datetime:
    return datetime(2026, 6, 2, 14, minute, second, tzinfo=UTC)


def test_single_trade_does_not_close():
    agg = CandleAggregator()
    agg.add_trade("NFLX", _ts(30, 5), price=100.0, size=10)
    assert agg.closed_candles("NFLX") == ()
    cur = agg.current("NFLX")
    assert cur is not None and cur.open == 100.0 and cur.volume == 10


def test_ohlcv_within_one_minute():
    agg = CandleAggregator()
    agg.add_trade("NFLX", _ts(30, 1), 100.0, 5)
    agg.add_trade("NFLX", _ts(30, 20), 102.0, 3)  # high
    agg.add_trade("NFLX", _ts(30, 40), 99.0, 2)  # low
    agg.add_trade("NFLX", _ts(30, 59), 101.0, 1)  # close
    cur = agg.current("NFLX")
    assert (cur.open, cur.high, cur.low, cur.close) == (100.0, 102.0, 99.0, 101.0)
    assert cur.volume == 11 and cur.trades == 4


def test_new_minute_closes_previous():
    closed: list[Candle] = []
    agg = CandleAggregator(on_close=closed.append)
    agg.add_trade("NFLX", _ts(30, 10), 100.0, 5)
    agg.add_trade("NFLX", _ts(31, 2), 101.0, 4)  # rolls over -> closes minute 30

    assert len(closed) == 1
    bar = closed[0]
    assert bar.start == _ts(30)
    assert bar.close == 100.0 and bar.volume == 5
    # minute 31 is now the open (not yet closed) candle
    assert agg.latest_closed("NFLX") is bar
    assert agg.current("NFLX").start == _ts(31)


def test_late_out_of_order_trade_dropped():
    agg = CandleAggregator()
    agg.add_trade("NFLX", _ts(31, 5), 101.0, 4)
    agg.add_trade("NFLX", _ts(30, 5), 100.0, 99)  # belongs to an earlier minute
    cur = agg.current("NFLX")
    assert cur.start == _ts(31) and cur.volume == 4  # late tick ignored


def test_flush_closes_elapsed_candle():
    closed: list[Candle] = []
    agg = CandleAggregator(on_close=closed.append)
    agg.add_trade("NFLX", _ts(30, 10), 100.0, 5)
    agg.flush(_ts(30, 59))  # still inside minute 30 -> no close
    assert closed == []
    agg.flush(_ts(31, 1))  # minute 30 has fully elapsed -> close
    assert len(closed) == 1 and closed[0].start == _ts(30)
    assert agg.current("NFLX") is None


def test_flush_is_per_symbol():
    agg = CandleAggregator()
    agg.add_trade("NFLX", _ts(30, 10), 100.0, 5)
    agg.add_trade("WPM", _ts(31, 10), 50.0, 5)
    agg.flush(_ts(31, 30))  # closes NFLX (minute 30 done), keeps WPM (minute 31 live)
    assert len(agg.closed_candles("NFLX")) == 1
    assert agg.closed_candles("WPM") == ()
    assert agg.current("WPM") is not None


def test_symbols_are_independent():
    agg = CandleAggregator()
    agg.add_trade("NFLX", _ts(30, 1), 100.0, 5)
    agg.add_trade("WPM", _ts(30, 1), 50.0, 7)
    agg.add_trade("NFLX", _ts(31, 1), 101.0, 1)
    assert len(agg.closed_candles("NFLX")) == 1
    assert agg.closed_candles("WPM") == ()  # WPM never rolled over


def test_rolling_window_is_bounded():
    agg = CandleAggregator(window=3)
    # one trade per minute for 6 minutes -> 5 closes, window keeps last 3
    for m in range(30, 36):
        agg.add_trade("NFLX", _ts(m, 1), 100.0 + m, 1)
    bars = agg.closed_candles("NFLX")
    assert len(bars) == 3
    assert [b.start.minute for b in bars] == [32, 33, 34]


def test_naive_timestamp_treated_as_utc():
    agg = CandleAggregator()
    naive = datetime(2026, 6, 2, 14, 30, 5)  # no tzinfo
    agg.add_trade("NFLX", naive, 100.0, 1)
    assert agg.current("NFLX").start == _ts(30)


def test_gap_minutes_do_not_synthesize_candles():
    agg = CandleAggregator()
    agg.add_trade("NFLX", _ts(30, 1), 100.0, 1)
    agg.add_trade("NFLX", _ts(45, 1), 101.0, 1)  # 15-minute gap
    bars = agg.closed_candles("NFLX")
    assert len(bars) == 1 and bars[0].start == _ts(30)  # no empty filler bars


def test_custom_interval():
    agg = CandleAggregator(interval_seconds=300)  # 5-minute candles
    agg.add_trade("NFLX", _ts(30, 1), 100.0, 1)
    agg.add_trade("NFLX", _ts(34, 59), 102.0, 1)  # same 5-min bucket [30,35)
    assert agg.closed_candles("NFLX") == ()
    agg.add_trade("NFLX", _ts(35, 1), 103.0, 1)  # next bucket -> close
    assert len(agg.closed_candles("NFLX")) == 1


def test_invalid_construction():
    with pytest.raises(ValueError):
        CandleAggregator(interval_seconds=0)
    with pytest.raises(ValueError):
        CandleAggregator(window=0)


def test_interval_aligns_to_epoch_grid():
    agg = CandleAggregator()
    # 14:30:30 must floor to 14:30:00 regardless of the seconds offset
    agg.add_trade("NFLX", _ts(30, 30), 100.0, 1)
    assert agg.current("NFLX").start == datetime(2026, 6, 2, 14, 30, tzinfo=UTC)
