"""Tests for the data-ingestion layer (Phase 1).

These exercise the wiring with injected fakes — no network, no real keys.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bot.config import Config
from bot.market_data import (
    BACKOFF_CAP_SECONDS,
    MarketDataClient,
    backoff_delay,
)

_ENV = {
    "ALPACA_KEY_ID": "k",
    "ALPACA_SECRET": "s",
    "TELEGRAM_TOKEN": "t",
    "TELEGRAM_CHAT_ID": "c",
    "WATCHLIST": "NFLX,WPM",
}


@pytest.fixture
def cfg(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    return Config.load(dotenv=False)


# --- backoff -------------------------------------------------------------


def test_backoff_grows_then_caps():
    assert backoff_delay(0, base=1.0) == 1.0
    assert backoff_delay(1, base=1.0) == 2.0
    assert backoff_delay(2, base=1.0) == 4.0
    assert backoff_delay(99, base=1.0) == BACKOFF_CAP_SECONDS
    assert backoff_delay(-5, base=1.0) == 1.0  # negative clamped to attempt 0


# --- account check -------------------------------------------------------


class _FakeTrading:
    def __init__(self, positions=()):
        self._positions = list(positions)
        self.account = SimpleNamespace(
            account_number="PA123",
            status="ACTIVE",
            equity="10000",
            buying_power="20000",
            cash="10000",
        )

    def get_account(self):
        return self.account

    def get_all_positions(self):
        return self._positions


def test_check_account_returns_account_and_positions(cfg):
    pos = SimpleNamespace(symbol="NFLX", qty="3", market_value="300", avg_entry_price="100")
    fake = _FakeTrading(positions=[pos])
    client = MarketDataClient(cfg, trading_factory=lambda: fake)
    account, positions = client.check_account()
    assert account.status == "ACTIVE"
    assert [p.symbol for p in positions] == ["NFLX"]


def test_check_account_handles_no_positions(cfg):
    client = MarketDataClient(cfg, trading_factory=lambda: _FakeTrading())
    _, positions = client.check_account()
    assert positions == []


# --- trade handling feeds the aggregator ---------------------------------


def _trade(symbol, minute, second, price, size):
    return SimpleNamespace(
        symbol=symbol,
        timestamp=datetime(2026, 6, 2, 14, minute, second, tzinfo=UTC),
        price=price,
        size=size,
    )


def test_on_trade_aggregates_and_closes_via_flush(cfg):
    seen = []
    client = MarketDataClient(cfg, on_candle=seen.append)
    asyncio.run(client._on_trade(_trade("NFLX", 30, 1, 100.0, 5)))
    asyncio.run(client._on_trade(_trade("NFLX", 30, 30, 101.0, 5)))
    assert seen == []  # same minute, still open
    # a later tick advances the clock and flush() closes minute 30
    asyncio.run(client._on_trade(_trade("NFLX", 31, 1, 102.0, 1)))
    assert len(seen) == 1
    assert seen[0].symbol == "NFLX" and seen[0].volume == 10


def test_on_trade_feeds_both_timeframes(cfg):
    short_seen, long_seen = [], []
    client = MarketDataClient(cfg, on_candle=short_seen.append, on_long_candle=long_seen.append)
    # minute 30 (5-min bucket 14:30), then minute 35 closes both the 1-min bar
    # for minute 30 and the 5-min bar for 14:30.
    asyncio.run(client._on_trade(_trade("NFLX", 30, 1, 100.0, 5)))
    asyncio.run(client._on_trade(_trade("NFLX", 35, 1, 105.0, 3)))
    assert len(short_seen) == 1 and short_seen[0].start.minute == 30
    assert len(long_seen) == 1 and long_seen[0].start.minute == 30
    assert long_seen[0].volume == 5  # only the minute-30 trade fell in the 14:30 bar


def test_on_candle_callback_error_does_not_propagate(cfg):
    def boom(_candle):
        raise RuntimeError("downstream bug")

    client = MarketDataClient(cfg, on_candle=boom)
    asyncio.run(client._on_trade(_trade("NFLX", 30, 1, 100.0, 5)))
    # closing the candle invokes the failing callback; it must be swallowed
    asyncio.run(client._on_trade(_trade("NFLX", 31, 1, 101.0, 1)))


# --- supervisor / reconnect ----------------------------------------------


class _FakeStream:
    """Records subscriptions; ``run`` behavior is scripted per instance."""

    def __init__(self, behavior):
        self._behavior = behavior  # "clean" | "crash"
        self.subscribed = []
        self.stopped = False

    def subscribe_trades(self, handler, *symbols):
        self.subscribed.append((handler, symbols))

    def run(self):
        if self._behavior == "crash":
            raise RuntimeError("socket exploded")
        # "clean" => return immediately (intentional stop / fatal sub error)

    def stop(self):
        self.stopped = True


def test_run_forever_subscribes_watchlist(cfg):
    made = []

    def factory():
        s = _FakeStream("clean")
        made.append(s)
        return s

    client = MarketDataClient(cfg, stream_factory=factory)
    client.run_forever()
    assert len(made) == 1  # clean return => no reconnect
    (_handler, symbols) = made[0].subscribed[0]
    assert symbols == ("NFLX", "WPM")


def test_run_forever_reconnects_on_crash_then_gives_up(cfg, monkeypatch):
    monkeypatch.setattr("bot.market_data.time.sleep", lambda _s: None)
    made = []

    def factory():
        s = _FakeStream("crash")
        made.append(s)
        return s

    client = MarketDataClient(cfg, stream_factory=factory)
    client.run_forever(max_restarts=2)
    # initial run + 2 restarts = 3 stream instances, then it gives up
    assert len(made) == 3


def test_stop_marks_stopped_and_stops_stream(cfg):
    stream = _FakeStream("clean")
    client = MarketDataClient(cfg, stream_factory=lambda: stream)
    client.run_forever()
    client.stop()
    assert client._stop is True
    assert stream.stopped is True


# --- feed-loss fail-safe (Phase 5) ---------------------------------------


def test_crash_fires_feed_lost_once(cfg, monkeypatch):
    monkeypatch.setattr("bot.market_data.time.sleep", lambda _s: None)
    events = []
    client = MarketDataClient(
        cfg,
        stream_factory=lambda: _FakeStream("crash"),
        on_feed_lost=lambda: events.append("lost"),
        on_feed_restored=lambda: events.append("restored"),
    )
    client.run_forever(max_restarts=2)
    assert events == ["lost"]  # latched once across the repeated crashes
    assert client._feed_down is True


def test_clean_run_does_not_fire_feed_lost(cfg):
    events = []
    client = MarketDataClient(
        cfg,
        stream_factory=lambda: _FakeStream("clean"),
        on_feed_lost=lambda: events.append("lost"),
    )
    client.run_forever()
    assert events == []
    assert client._feed_down is False


def test_first_tick_after_loss_fires_feed_restored(cfg):
    events = []
    client = MarketDataClient(
        cfg,
        on_feed_lost=lambda: events.append("lost"),
        on_feed_restored=lambda: events.append("restored"),
    )
    client._feed_down = True  # simulate a prior crash having latched the halt
    asyncio.run(client._on_trade(_trade("NFLX", 30, 1, 100.0, 5)))
    assert events == ["restored"]
    assert client._feed_down is False


def test_ticks_while_healthy_do_not_fire_restored(cfg):
    events = []
    client = MarketDataClient(cfg, on_feed_restored=lambda: events.append("restored"))
    asyncio.run(client._on_trade(_trade("NFLX", 30, 1, 100.0, 5)))
    assert events == []  # feed was never down -> nothing to restore
