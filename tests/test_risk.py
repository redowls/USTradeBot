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
    """Records close_position / replace_stop_price calls; returns scripted outcomes."""

    def __init__(self, order_id="close-1", replace_ok=True, reconciled=None, close_fill=None):
        self._order_id = order_id
        self._replace_ok = replace_ok
        self._reconciled = reconciled  # (order_id, price) of a broker-side fill, or None
        self._close_fill = close_fill  # actual fill price of the bot's own close, or None
        self.closed = []
        self.moved = []
        self.reconcile_calls = []

    def close_position(self, symbol):
        self.closed.append(symbol)
        return self._order_id

    def close_fill_price(self, order_id):
        return self._close_fill

    def reconcile_exit(self, symbol):
        self.reconcile_calls.append(symbol)
        return self._reconciled

    def replace_stop_price(self, stop_order_id, new_stop_price):
        self.moved.append((stop_order_id, new_stop_price))
        if not self._replace_ok:
            return None
        return stop_order_id + "-r"  # Alpaca issues a new id on each replace


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


def _entry(stop_order_id="stop-1") -> ExecutionResult:
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
        stop_order_id=stop_order_id,
    )


def _rising(close) -> RibbonSnapshot:
    return _snap((close, close - 1.0, close - 2.0), (close - 1.0, close - 1.5, close - 2.0),
                 close=close)


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


# --- trailing stop --------------------------------------------------------


def test_trailing_stop_ratchets_up(cfg):
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is True
    assert ex.moved == [("stop-1", 107.8)]  # 110 * (1 - 0.02)


def test_trailing_stop_never_lowers(cfg):
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    rm.update_trailing_stop(_rising(110.0), _entry())  # stop -> 107.8
    # price pulls back to 105 -> 102.9 < 107.8, so the stop is left where it is
    assert rm.update_trailing_stop(_rising(105.0), _entry()) is False
    assert ex.moved == [("stop-1", 107.8)]


def test_trailing_stop_noop_without_stop_leg(cfg):
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry(stop_order_id="")) is False
    assert rm.update_trailing_stop(_rising(110.0), None) is False
    assert ex.moved == []


def test_trailing_stop_retries_after_failed_move(cfg):
    ex = _FakeExecutor(replace_ok=False)
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is False
    # the failed move isn't cached as the current stop, so it retries next candle
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is False
    assert ex.moved == [("stop-1", 107.8), ("stop-1", 107.8)]


def test_trailing_stop_targets_replacement_id_on_next_move(cfg):
    # Regression for the 422 "order already replaced" loop: Alpaca rotates the order id
    # on every replace, so the second ratchet must target the replacement ("stop-1-r"),
    # not the now-dead original ("stop-1") which would 422 forever.
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is True  # 107.8 on stop-1
    assert rm.update_trailing_stop(_rising(115.0), _entry()) is True  # 112.7 on stop-1-r
    assert ex.moved == [("stop-1", 107.8), ("stop-1-r", 112.7)]


def test_exit_clears_trailing_state(cfg):
    # A closed trade must drop its trail state so the maps don't grow unbounded and a
    # re-entry reusing the leg id starts fresh from its own bracket stop.
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    rm.update_trailing_stop(_rising(110.0), _entry())
    rm.exit_position("NFLX", 105.0, "manual", _entry())
    assert rm._trail_stops == {} and rm._live_stop_oid == {}


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


def test_exit_position_records_actual_close_fill(cfg):
    # Regression (2026-06-23): the bot's own EOD-flatten market sell fills at a real broker
    # price (GOOG @347.14) that differs from the candle-close estimate passed in (346.72).
    # exit_position must record the ACTUAL fill so P/L and the win/loss flag are exact.
    ex = _FakeExecutor(order_id="close-9", close_fill=347.14)
    rm = RiskManager(cfg, executor=ex)
    result = rm.exit_position("GOOG", 346.72, "end-of-day flatten", _entry())
    assert result is not None
    assert result.exit_price == 347.14  # the real broker fill, not the 346.72 estimate
    assert result.order_id == "close-9"


def test_exit_position_falls_back_to_passed_price_when_fill_unreadable(cfg):
    # When the close fill can't be read (empty id / unfilled / read error → None), the exit
    # records the candle-close estimate passed in — never a fabricated 0.0 exit.
    ex = _FakeExecutor(order_id="close-9", close_fill=None)
    rm = RiskManager(cfg, executor=ex)
    result = rm.exit_position("GOOG", 346.72, "end-of-day flatten", _entry())
    assert result is not None
    assert result.exit_price == 346.72  # fell back to the passed-in estimate


def test_exit_position_returns_none_when_close_fails(cfg):
    ex = _FakeExecutor(order_id=None)  # close didn't submit AND nothing to reconcile
    rm = RiskManager(cfg, executor=ex)
    assert rm.exit_position("NFLX", 99.0, "reason") is None
    assert ex.reconcile_calls == ["NFLX"]  # tried to reconcile, found no broker-side fill


def test_exit_position_reconciles_broker_side_stop_fill(cfg):
    # Regression (2026-06-17): the trailing stop filled broker-side, so close_position
    # 404'd (returns None). exit_position must reconcile the real fill from order
    # history, record the exit at THAT price (not the price passed in), tag the reason,
    # and release the symbol — instead of leaving a phantom-open position.
    ex = _FakeExecutor(order_id=None, reconciled=("stop-leg", 397.13))
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    result = rm.exit_position("TSLA", 410.0, "end-of-day flatten", _entry())
    assert result is not None
    assert result.exit_price == 397.13  # the real broker-side fill, not the 410.0 passed in
    assert "broker-side" in result.reason
    assert result.order_id == "stop-leg"
    assert ex.reconcile_calls == ["TSLA"]
    assert seen == [result]  # on_exit fired → the exit is persisted


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
