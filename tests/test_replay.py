"""Tests for the historical replay harness (bot.replay).

The harness is only useful if its simulated broker fills the way the real one does,
so these pin the fill semantics every backtest number rests on.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bot.candles import Candle
from bot.config import Config
from bot.executor import StopOrderGone
from bot.replay import LONG, SHORT, SimBroker, build_stream, resolve_symbols

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


# --- gate-bar sequencing (IMP-024) -----------------------------------------
#
# Regression cohort for the 2026-08-07 failure: replay entered ABNB 14:45 and MSFT
# 14:47 because the 5m gate bar starting 14:45 had already been folded into the
# ribbon. Live, that bar does not exist until 14:50, and live correctly refused
# both entries ("market gate closed"). The harness was reading the future.

_GATE_SECONDS = 300


def _stamped_bar(symbol: str, start: datetime) -> Candle:
    """A flat bar that exists only to carry a timestamp — these tests assert on
    sequencing, never on price."""
    return Candle(
        symbol=symbol, start=start, open=1.0, high=1.0, low=1.0, close=1.0,
        volume=1.0, trades=1,
    )


def _session(minutes: int, *, at: datetime, symbol: str = "ABNB"):
    """(short, long) bar maps for ``minutes`` of one session, 1m and 5m."""
    short = {
        symbol: [_stamped_bar(symbol, at + timedelta(minutes=i)) for i in range(minutes)]
    }
    long = {
        symbol: [
            _stamped_bar(symbol, at + timedelta(minutes=i)) for i in range(0, minutes, 5)
        ]
    }
    return short, long


def test_gate_bar_is_sequenced_at_its_close_not_its_start():
    """The 08-07 bug in one assertion: the 14:45 gate bar must land at 14:50."""
    at = datetime(2026, 8, 7, 14, 45, tzinfo=UTC)
    short, long = _session(10, at=at)
    stream = build_stream(["ABNB"], short, long, at, at + timedelta(hours=1), _GATE_SECONDS)

    gate_bars = [(ts, c.start) for ts, kind, c in stream if kind == LONG]
    assert gate_bars == [
        (at + timedelta(minutes=5), at),
        (at + timedelta(minutes=10), at + timedelta(minutes=5)),
    ]


def test_trigger_bars_never_see_a_gate_bar_that_has_not_closed():
    """The invariant itself, over a full session: no lookahead at any bar."""
    at = datetime(2026, 8, 7, 13, 30, tzinfo=UTC)
    short, long = _session(390, at=at)
    stream = build_stream(["ABNB"], short, long, at, at + timedelta(days=1), _GATE_SECONDS)

    folded: list[datetime] = []
    for ts, kind, candle in stream:
        if kind == LONG:
            folded.append(candle.start)
            continue
        # Every gate bar the ribbon has seen must already have closed by ``ts``.
        assert all(s + timedelta(seconds=_GATE_SECONDS) <= ts for s in folded), (
            f"trigger bar {ts:%H:%M} saw gate bar {folded[-1]:%H:%M} before its close"
        )
    assert folded, "sanity: the session must contain gate bars"


def test_gate_bar_folds_before_the_trigger_bar_of_the_same_minute():
    """Live's order at the boundary: 5m closing at 14:50 lands before 1m 14:50."""
    at = datetime(2026, 8, 7, 14, 45, tzinfo=UTC)
    short, long = _session(10, at=at)
    stream = build_stream(["ABNB"], short, long, at, at + timedelta(hours=1), _GATE_SECONDS)

    boundary = at + timedelta(minutes=5)
    kinds = [kind for ts, kind, _ in stream if ts == boundary]
    assert kinds == [LONG, SHORT]


def test_sequencing_does_not_change_which_bars_are_replayed():
    """Close-time keying moves order only — the window must select the same bars."""
    at = datetime(2026, 8, 7, 13, 30, tzinfo=UTC)
    end = at + timedelta(minutes=60)
    short, long = _session(390, at=at)
    stream = build_stream(["ABNB"], short, long, at, end, _GATE_SECONDS)

    replayed_long = {c.start for _, kind, c in stream if kind == LONG}
    replayed_short = {c.start for _, kind, c in stream if kind == SHORT}
    assert replayed_long == {c.start for c in long["ABNB"] if at <= c.start < end}
    assert replayed_short == {c.start for c in short["ABNB"] if at <= c.start < end}


def test_multiple_symbols_stay_in_true_chronological_order():
    """Capital contention is only real if symbols interleave by time, not by name."""
    at = datetime(2026, 8, 7, 14, 45, tzinfo=UTC)
    short_a, long_a = _session(10, at=at, symbol="ABNB")
    short_m, long_m = _session(10, at=at, symbol="MSFT")
    short = {**short_a, **short_m}
    long = {**long_a, **long_m}
    stream = build_stream(
        ["ABNB", "MSFT"], short, long, at, at + timedelta(hours=1), _GATE_SECONDS
    )

    stamps = [ts for ts, _, _ in stream]
    assert stamps == sorted(stamps)
    assert len(stream) == 2 * (10 + 2)  # both symbols, 10 trigger + 2 gate bars each
