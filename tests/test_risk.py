"""Tests for the risk manager (Phase 5).

The executor is a fake that records close_position calls and scripts the outcome,
so these exercise the exit decision, the close wiring, and the feed-loss fail-safe
without a network.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bot.config import Config
from bot.executor import ExecutionResult
from bot.indicators import RibbonSnapshot
from bot.risk import RiskManager

_TS = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)

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


class _FakeExecutor:
    """Records close_position calls; returns a scripted id (or None for failure)."""

    def __init__(self, order_id="close-1"):
        self._order_id = order_id
        self.closed = []

    def close_position(self, symbol):
        self.closed.append(symbol)
        return self._order_id


def _snap(ribbon, prev_ribbon, *, close=100.0) -> RibbonSnapshot:
    return RibbonSnapshot(
        symbol="NFLX",
        candle_start=_TS,
        interval_seconds=60,
        close=close,
        volume=100.0,
        ribbon=ribbon,
        prev_ribbon=prev_ribbon,
        rsi=None,
        prev_rsi=None,
        avg_volume=None,
        atr=None,
    )


def _bearish_cross() -> RibbonSnapshot:
    # fast was >= mid, now fast < mid -> fresh bearish cross
    return _snap((99.9, 100.1, 100.0), (100.2, 100.1, 100.0))


def _no_cross() -> RibbonSnapshot:
    # still stacked bullishly, no inversion
    return _snap((101.0, 100.5, 100.0), (100.8, 100.4, 100.0))


def _entry() -> ExecutionResult:
    return ExecutionResult(
        symbol="NFLX",
        order_id="o1",
        qty=10,
        notional=1000.0,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        confidence=75.0,
        status="accepted",
        model="A",
    )


# --- early-exit decision --------------------------------------------------


def test_check_exit_flags_bearish_cross(cfg):
    rm = RiskManager(cfg, executor=_FakeExecutor())
    assert rm.check_exit(_bearish_cross()) == "bearish 1-min ribbon cross"


def test_check_exit_holds_without_cross(cfg):
    rm = RiskManager(cfg, executor=_FakeExecutor())
    assert rm.check_exit(_no_cross()) is None


def test_check_exit_ignores_unready_ribbon(cfg):
    rm = RiskManager(cfg, executor=_FakeExecutor())
    assert rm.check_exit(_snap((None, None, None), (None, None, None))) is None


# --- exit execution -------------------------------------------------------


def test_exit_position_closes_and_reports(cfg):
    ex = _FakeExecutor(order_id="close-9")
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    result = rm.exit_position("NFLX", 99.0, "bearish 1-min ribbon cross", _entry())
    assert result is not None
    assert ex.closed == ["NFLX"]
    assert result.qty == 10  # carried from the entry
    assert result.order_id == "close-9"
    assert seen == [result]  # on_exit fired


def test_exit_position_returns_none_when_close_fails(cfg):
    ex = _FakeExecutor(order_id=None)  # close didn't submit
    rm = RiskManager(cfg, executor=ex)
    assert rm.exit_position("NFLX", 99.0, "reason") is None


def test_exit_position_without_entry_has_no_qty(cfg):
    rm = RiskManager(cfg, executor=_FakeExecutor())
    result = rm.exit_position("NFLX", 99.0, "reason")  # reconciled position, no entry
    assert result is not None and result.qty is None


def test_exit_callback_error_is_swallowed(cfg):
    def boom(_r):
        raise RuntimeError("alert down")

    rm = RiskManager(cfg, executor=_FakeExecutor(), on_exit=boom)
    assert rm.exit_position("NFLX", 99.0, "reason") is not None  # must not raise


# --- feed-loss fail-safe --------------------------------------------------


def test_entries_allowed_toggles_with_feed(cfg):
    alerts = []
    rm = RiskManager(cfg, executor=_FakeExecutor(), on_feed_alert=alerts.append)
    assert rm.entries_allowed is True
    rm.notify_feed_lost()
    assert rm.entries_allowed is False
    rm.notify_feed_restored()
    assert rm.entries_allowed is True
    assert len(alerts) == 2  # one lost, one restored


def test_feed_notifications_are_idempotent(cfg):
    alerts = []
    rm = RiskManager(cfg, executor=_FakeExecutor(), on_feed_alert=alerts.append)
    rm.notify_feed_lost()
    rm.notify_feed_lost()  # already down -> no second alert
    rm.notify_feed_restored()
    rm.notify_feed_restored()  # already up -> no second alert
    assert len(alerts) == 2


def test_feed_alert_error_is_swallowed(cfg):
    def boom(_msg):
        raise RuntimeError("telegram down")

    rm = RiskManager(cfg, executor=_FakeExecutor(), on_feed_alert=boom)
    rm.notify_feed_lost()  # must not raise
    assert rm.entries_allowed is False
