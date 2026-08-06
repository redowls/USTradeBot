"""Tests for the historical replay harness (bot.replay).

The harness is only useful if its simulated broker fills the way the real one does,
so these pin the fill semantics every backtest number rests on.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bot.candles import Candle
from bot.config import Config
from bot.executor import StopOrderGone
from bot.replay import SimBroker, resolve_symbols

_T0 = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)
_T1 = datetime(2026, 6, 2, 14, 1, tzinfo=UTC)

_ENV = {
    "ALPACA_KEY_ID": "k",
    "ALPACA_SECRET": "s",
    "TELEGRAM_TOKEN": "t",
    "TELEGRAM_CHAT_ID": "c",
}


@pytest.fixture
def cfg(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    return Config.load(dotenv=False)


@pytest.fixture
def broker(cfg):
    b = SimBroker(cfg, equity=10_000.0)
    b.now = _T0
    return b


def _bar(close, *, high=None, low=None, ts=_T1, symbol="NFLX") -> Candle:
    return Candle(
        symbol=symbol,
        start=ts,
        open=close,
        high=high if high is not None else close,
        low=low if low is not None else close,
        close=close,
        volume=100.0,
        trades=1,
    )


def test_execute_sizes_through_the_real_sizing_model(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    assert r is not None
    assert r.qty >= 1
    # -2% stop / +4% target: the real bracket_prices helper on the config DEFAULTS
    # (dotenv=False, so the live .env's TAKE_PROFIT=0.10 is deliberately not read).
    assert r.stop_price == pytest.approx(98.0)
    assert r.take_profit_price == pytest.approx(104.0)
    assert broker.open_positions["NFLX"] is r


def test_execute_refuses_when_buying_power_is_exhausted(cfg):
    b = SimBroker(cfg, equity=100.0, margin_multiple=1.0)
    b.now = _T0
    assert b.execute(symbol="NFLX", entry_price=5_000.0, confidence=75.0) is None


def test_position_cannot_be_stopped_on_its_own_entry_bar(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(97.0, low=90.0, ts=_T0))  # same timestamp as the entry
    assert broker.reconcile_exit("NFLX") is None


def test_stop_fills_intrabar_from_the_bar_low(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(99.0, low=97.5))  # low pierces the 98.00 stop
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(98.0)


def test_target_fills_intrabar_from_the_bar_high(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(103.0, high=105.0))  # high clears the 104.00 target
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(104.0)


def test_bar_covering_both_legs_fills_the_stop_pessimistically(broker):
    """Intrabar sequence is unknowable from OHLC, so the harness must assume the
    worse leg — otherwise every wide bar is scored as a winner."""
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(102.0, high=105.0, low=97.0))  # spans stop AND target
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(98.0)  # the stop, not the target


def test_close_position_returns_none_once_a_leg_has_filled(broker):
    """Mirrors the live executor: a broker-side fill makes the close a no-op, which
    is what routes the exit through reconcile_exit and produces the
    'stop/target filled broker-side' reasons seen in the live book."""
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(99.0, low=97.5))
    assert broker.close_position("NFLX") is None


def test_close_position_fills_at_the_last_mark_when_no_leg_filled(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(103.0))
    oid = broker.close_position("NFLX")
    assert oid is not None
    assert broker.close_fill_price(oid) == pytest.approx(103.0)


def test_replace_stop_price_rotates_the_order_id(broker):
    """The live Alpaca stop leg gets a NEW id on every replace (the 2026-06-30 422
    bug); the sim must rotate too or the trailing ratchet is tested against a lie."""
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    new_id = broker.replace_stop_price(r.stop_order_id, 99.0)
    assert new_id is not None and new_id != r.stop_order_id
    assert broker.replace_stop_price(r.stop_order_id, 99.5) is None  # stale id


def test_replace_stop_price_raises_when_the_leg_already_filled(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(99.0, low=97.5))
    with pytest.raises(StopOrderGone):
        broker.replace_stop_price(r.stop_order_id, 99.0)


def test_book_exit_settles_pnl_and_frees_capital(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    before = broker.buying_power
    broker.now = _T1
    broker.book_exit("NFLX", 105.0, "test exit")
    assert broker.equity == pytest.approx(10_000.0 + 5.0 * r.qty)
    assert "NFLX" not in broker.open_positions
    assert broker.buying_power > before  # capital released for later entries
    assert len(broker.trades) == 1
    assert broker.trades[0].pnl == pytest.approx(5.0 * r.qty)


def test_trailed_stop_fills_at_the_trailed_price_not_the_original(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.replace_stop_price(r.stop_order_id, 103.0)  # ratcheted up into profit
    broker.on_bar(_bar(104.0, low=102.5))  # pierces the TRAILED stop only
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(103.0)


# --- replay universe resolution (IMP-023) ---------------------------------
#
# Regression cohort for the 2026-08-06 review: a bare `python -m bot.replay` silently
# backtested the WATCHLIST bootstrap stub (NFLX,BIRD,WPM) instead of the 19 enabled
# dbo.watchlist rows. Because QQQ — the IMP-022 market-filter symbol — was absent from
# the stub, the gate failed OPEN in both arms of that night's A/B and the filter looked
# like a no-op. These pin the precedence so the harness can never again disagree with
# the deployed watchlist without saying so.


class _FakeStore:
    def __init__(self, symbols):
        self._symbols = tuple(symbols)
        self.closed = False

    def load_watchlist(self):
        return self._symbols

    def close(self):
        self.closed = True


@pytest.fixture
def db_watchlist(monkeypatch):
    """Patch bot.persistence.open_store; returns a setter for the DB's reply."""
    holder = {}

    def _set(symbols):
        store = _FakeStore(symbols) if symbols is not None else None
        holder["store"] = store
        monkeypatch.setattr("bot.persistence.open_store", lambda cfg: store)
        return store

    return _set


def test_default_universe_comes_from_the_db_watchlist_not_the_env_stub(cfg, db_watchlist):
    live = ["AAPL", "AMD", "INTC", "MSFT", "MU", "QQQ"]
    store = db_watchlist(live)
    symbols, source = resolve_symbols(cfg)
    assert symbols == live
    assert source == "dbo.watchlist"
    assert cfg.watchlist == ("NFLX", "BIRD", "WPM")  # the stub it must NOT have used
    assert store.closed  # connection released, harness is a short-lived CLI


def test_default_universe_includes_the_market_filter_symbol(cfg, db_watchlist):
    """The 08-06 failure in one assertion: the gate needs QQQ's bars to evaluate."""
    db_watchlist(["AAPL", "AMD", "INTC", "MSFT", "MU", "QQQ"])
    symbols, _ = resolve_symbols(cfg)
    assert cfg.market_filter_symbol in symbols
    assert cfg.market_filter_symbol not in cfg.watchlist  # stub would have failed open


def test_explicit_symbols_win_over_the_db(cfg, db_watchlist):
    db_watchlist(["AAPL", "QQQ"])
    symbols, source = resolve_symbols(cfg, "mu, intc ")
    assert symbols == ["MU", "INTC"]  # upper-cased, trimmed, order preserved
    assert source == "--symbols"


def test_falls_back_to_env_when_the_db_is_unavailable(cfg, db_watchlist):
    db_watchlist(None)  # open_store returns None (SQLSERVER_CONN unset / init failed)
    symbols, source = resolve_symbols(cfg)
    assert symbols == ["NFLX", "BIRD", "WPM"]
    assert source == "WATCHLIST env"


def test_falls_back_to_env_when_the_watchlist_table_is_empty(cfg, db_watchlist):
    store = db_watchlist([])
    symbols, source = resolve_symbols(cfg)
    assert symbols == ["NFLX", "BIRD", "WPM"]
    assert source == "WATCHLIST env"
    assert store.closed
