"""Tests for the risk manager (Phase 5).

The executor is a fake that records close_position calls and scripts the outcome,
so these exercise the exit decision, the close wiring, and the feed-loss fail-safe
without a network.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from bot.config import Config
from bot.executor import ExecutionResult, StopOrderGone
from bot.indicators import RibbonSnapshot
from bot.risk import RiskManager, TrailResult

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

    def __init__(
        self, order_id="close-1", replace_ok=True, reconciled=None, close_fill=None,
        entry_fill=None, replace_gone=False, last_equity=None,
    ):
        self._order_id = order_id
        self._replace_ok = replace_ok
        self._replace_gone = replace_gone  # replace_stop_price raises StopOrderGone (leg filled)
        self._reconciled = reconciled  # (order_id, price) of a broker-side fill, or None
        self._close_fill = close_fill  # actual fill price of the bot's own close, or None
        self._entry_fill = entry_fill  # corrected entry buy fill (delayed fill), or None
        self.last_equity = last_equity  # session-open equity baseline for the stand-down
        self.closed = []
        self.moved = []
        self.reconcile_calls = []
        self.entry_fill_calls = []

    def close_position(self, symbol):
        self.closed.append(symbol)
        return self._order_id

    def close_fill_price(self, order_id):
        return self._close_fill

    def entry_fill_price(self, order_id):
        self.entry_fill_calls.append(order_id)
        return self._entry_fill

    def reconcile_exit(self, symbol):
        self.reconcile_calls.append(symbol)
        return self._reconciled

    def replace_stop_price(self, stop_order_id, new_stop_price):
        self.moved.append((stop_order_id, new_stop_price))
        if self._replace_gone:
            raise StopOrderGone(stop_order_id)  # the leg already filled broker-side
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
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.MOVED
    assert ex.moved == [("stop-1", 108.62)]  # 110 * (1 - 0.0125)


def test_trailing_stop_never_lowers(cfg):
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    rm.update_trailing_stop(_rising(110.0), _entry())  # stop -> 108.62
    # price pulls back to 105 -> 103.69 < 108.62, so the stop is left where it is
    assert rm.update_trailing_stop(_rising(105.0), _entry()) is TrailResult.HELD
    assert ex.moved == [("stop-1", 108.62)]


def test_trailing_stop_noop_without_stop_leg(cfg):
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry(stop_order_id="")) is TrailResult.HELD
    assert rm.update_trailing_stop(_rising(110.0), None) is TrailResult.HELD
    assert ex.moved == []


def test_trailing_stop_retries_after_failed_move(cfg):
    ex = _FakeExecutor(replace_ok=False)
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.HELD
    # the failed move isn't cached as the current stop, so it retries next candle
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.HELD
    assert ex.moved == [("stop-1", 108.62), ("stop-1", 108.62)]


def test_trailing_stop_targets_replacement_id_on_next_move(cfg):
    # Regression for the 422 "order already replaced" loop: Alpaca rotates the order id
    # on every replace, so the second ratchet must target the replacement ("stop-1-r"),
    # not the now-dead original ("stop-1") which would 422 forever.
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.MOVED  # 108.62 stop-1
    assert rm.update_trailing_stop(_rising(115.0), _entry()) is TrailResult.MOVED  # 113.56 stop-1-r
    assert ex.moved == [("stop-1", 108.62), ("stop-1-r", 113.56)]


def test_trailing_stop_reports_stop_gone_when_leg_filled(cfg):
    # IMP-012 regression: 2026-06-30 AMD/SE stopped out broker-side intraday, so the
    # stop leg was no longer open and every trailing move 422'd "order is not open"
    # (504 tracebacks, symbols stuck MANAGING ~4.5h). The risk manager must surface
    # that as STOP_GONE so the strategy reconciles the exit instead of retrying forever.
    ex = _FakeExecutor(replace_gone=True)
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.STOP_GONE
    assert ex.moved == [("stop-1", 108.62)]  # the move was attempted, then reported gone


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


def test_exit_position_recovers_delayed_entry_fill(cfg):
    # Regression (2026-06-25): AMD's market buy filled ~2 min after submission, past IMP-009's
    # short submit-time readback budget, so the entry was recorded at the candle-close estimate
    # (544.71) not the real broker fill (547.873) — understating the loss by ~$19. By exit time
    # the entry order is filled, so exit_position re-reads it and carries the corrected price.
    ex = _FakeExecutor(order_id="close-9", close_fill=538.88, entry_fill=547.873)
    rm = RiskManager(cfg, executor=ex)
    result = rm.exit_position("AMD", 539.0, "end-of-day flatten", _entry())
    assert result is not None
    assert result.entry_fill_price == 547.873  # the true broker buy fill, recovered at exit
    assert ex.entry_fill_calls == ["o1"]  # re-read the entry parent order by its id


def test_exit_position_entry_fill_none_when_unreadable_or_no_entry(cfg):
    # No entry (reconciled position) → no re-read, no fabricated price; and an unreadable
    # fill (None) leaves entry_fill_price None so persistence keeps the stored entry price.
    ex = _FakeExecutor(order_id="close-9", close_fill=538.88, entry_fill=None)
    rm = RiskManager(cfg, executor=ex)
    no_entry = rm.exit_position("AMD", 539.0, "end-of-day flatten")
    assert no_entry is not None and no_entry.entry_fill_price is None
    assert ex.entry_fill_calls == []  # never called without an entry order id
    unreadable = rm.exit_position("AMD", 539.0, "end-of-day flatten", _entry())
    assert unreadable.entry_fill_price is None  # None → stored entry price untouched


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


def test_reconcile_if_closed_records_broker_side_fill(cfg):
    # IMP-014 regression (2026-07-10 SE): a broker-side stop that fills on a DOWN move is
    # never surfaced by the trailing ratchet (no higher-high replace to 422), so the
    # wall-clock sweep polls order history to detect it. reconcile_if_closed must record the
    # exit at the real fill, tag it a broker-side fill, and NEVER submit a close.
    ex = _FakeExecutor(reconciled=("stop-se", 113.21), entry_fill=108.0)  # entry did fill
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    result = rm.reconcile_if_closed("SE", _entry())
    assert result is not None
    assert ex.closed == []  # read-only: never attempted a close
    assert ex.reconcile_calls == ["SE"]
    assert result.exit_price == 113.21  # the true broker-side fill
    assert "stop/target filled broker-side" in result.reason
    assert result.order_id == "stop-se"
    assert result.qty == 10  # carried from the entry
    assert seen == [result]  # persisted via on_exit


def test_reconcile_if_closed_none_when_still_open(cfg):
    # reconcile_exit returns None while the broker still holds the position, so a still-open
    # MANAGING symbol is left untouched — no exit recorded, no close submitted.
    ex = _FakeExecutor(reconciled=None, entry_fill=108.0)  # entry filled, but still held
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    assert rm.reconcile_if_closed("SE", _entry()) is None
    assert ex.closed == []
    assert ex.reconcile_calls == ["SE"]
    assert seen == []


def test_reconcile_if_closed_skips_while_entry_unfilled(cfg):
    # 2026-07-20 NVDA regression (IMP-015): the entry buy filled ~2.5 min late, so the
    # wall-clock MANAGING sweep fired while the position had NOT yet opened. The broker
    # 404'd (no position yet), and reconcile_exit would have matched a STALE prior-session
    # sell as a phantom exit (+$41 booked on a trade that was really a −$58 stop-out),
    # desyncing bot state from the broker. Until the entry is confirmed filled, the sweep
    # must NOT reconcile — never even consult order history — and leave the symbol MANAGING.
    ex = _FakeExecutor(reconciled=("stale-sell", 209.615), entry_fill=None)  # entry unfilled
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    assert rm.reconcile_if_closed("NVDA", _entry()) is None
    assert ex.entry_fill_calls == ["o1"]  # checked the entry fill first
    assert ex.reconcile_calls == []  # never looked at order history → no phantom exit
    assert seen == []  # nothing recorded


def test_reconcile_if_closed_clears_trailing_state(cfg):
    # A reconciled exit is a completed trade, so it must drop the trade's trailing-stop
    # state (like exit_position) so the maps don't grow unbounded across re-entries.
    ex = _FakeExecutor(reconciled=("stop-se", 113.21), entry_fill=108.0)  # entry did fill
    rm = RiskManager(cfg, executor=ex)
    rm.update_trailing_stop(_rising(110.0), _entry())
    assert rm._trail_stops  # populated by the ratchet
    rm.reconcile_if_closed("NFLX", _entry())
    assert rm._trail_stops == {} and rm._live_stop_oid == {}


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


# --- broad-adverse-day stand-down (IMP-016) -------------------------------


def _cfg_standdown(monkeypatch, **overrides):
    """A Config with the stand-down env vars set (used to disable it / retune it)."""
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    for k, v in overrides.items():
        monkeypatch.setenv(k, v)
    return Config.load(dotenv=False)


def _lose(rm, exit_price=98.0):
    """Drive one losing exit through the risk manager (entry 100 × qty 10)."""
    return rm.exit_position("NFLX", exit_price, "stop", _entry())


def _win(rm, exit_price=102.0):
    return rm.exit_position("NFLX", exit_price, "target", _entry())


def test_standdown_trips_after_consecutive_losses(cfg):
    # 2026-07-17 regression: 0W/5L risk-off selloff kept opening fresh longs that faded.
    # After the 3rd consecutive losing exit the stand-down must halt NEW entries (the
    # default streak trigger = 3), while managing/flattening open ones is unaffected.
    alerts: list[str] = []
    rm = RiskManager(cfg, executor=_FakeExecutor(), on_feed_alert=alerts.append)
    rm.roll_session(date(2026, 7, 17))
    _lose(rm)
    assert rm.entries_allowed is True  # 1 loss — not yet
    _lose(rm)
    assert rm.entries_allowed is True  # 2 losses — not yet
    _lose(rm)
    assert rm.entries_allowed is False  # 3rd consecutive loss trips the stand-down
    assert rm.standdown_active is True
    assert len(alerts) == 1 and "Stand-down" in alerts[0]  # paged exactly once


def test_standdown_winner_resets_the_streak(cfg):
    # A non-losing exit resets the consecutive-loss counter, so L,L,W,L,L does NOT trip
    # (only 2 in a row at the end) — the stand-down targets a genuine losing run.
    rm = RiskManager(cfg, executor=_FakeExecutor())
    rm.roll_session(date(2026, 7, 21))
    _lose(rm)
    _lose(rm)
    _win(rm)  # resets the streak
    _lose(rm)
    _lose(rm)
    assert rm.entries_allowed is True
    assert rm.standdown_active is False


def test_standdown_trips_on_session_loss_pct(cfg):
    # The catastrophic backstop: even below the consecutive-loss count, a session realized
    # loss past standdown_max_loss_pct (default 2.5%) of the session-open equity halts new
    # entries. Two −$150 losses = −$300 <= 2.5% of $10,000 ($250) → trips at 2 (< 3 streak).
    rm = RiskManager(cfg, executor=_FakeExecutor(last_equity=10_000.0))
    rm.roll_session(date(2026, 7, 21))
    _lose(rm, exit_price=85.0)  # (85-100)*10 = -150
    assert rm.entries_allowed is True
    _lose(rm, exit_price=85.0)  # cumulative -300 <= -250 floor
    assert rm.entries_allowed is False
    assert rm.standdown_active is True


def test_standdown_resets_at_next_session(cfg):
    # A halt from one session must NOT bleed into the next: roll_session on a new date
    # clears the stand-down, the realized tally, and the streak.
    rm = RiskManager(cfg, executor=_FakeExecutor())
    rm.roll_session(date(2026, 7, 17))
    _lose(rm); _lose(rm); _lose(rm)
    assert rm.entries_allowed is False
    rm.roll_session(date(2026, 7, 18))  # new session
    assert rm.entries_allowed is True
    assert rm.standdown_active is False
    _lose(rm)  # streak starts fresh — one loss doesn't re-trip
    assert rm.entries_allowed is True


def test_standdown_disabled_never_trips(monkeypatch):
    # The feature has a kill-switch: STANDDOWN_ENABLED=false leaves entries always allowed
    # regardless of the loss run (pre-IMP-016 behavior).
    cfg = _cfg_standdown(monkeypatch, STANDDOWN_ENABLED="false")
    rm = RiskManager(cfg, executor=_FakeExecutor())
    rm.roll_session(date(2026, 7, 17))
    for _ in range(5):
        _lose(rm)
    assert rm.entries_allowed is True
    assert rm.standdown_active is False


def test_standdown_skips_exit_without_entry(cfg):
    # A startup-reconciled holding exits with no entry price/qty to score — it must not be
    # guessed into the loss streak (could false-trip the halt). Three entry-less exits, no trip.
    rm = RiskManager(cfg, executor=_FakeExecutor())
    rm.roll_session(date(2026, 7, 21))
    for _ in range(3):
        rm.exit_position("NFLX", 98.0, "end-of-day flatten")  # no entry arg
    assert rm.entries_allowed is True
    assert rm.standdown_active is False


def test_standdown_and_feed_halt_compose(cfg):
    # The two entry halts are independent latches AND'd together: restoring the feed does
    # not lift a tripped stand-down, and clearing the stand-down does not lift a feed halt.
    rm = RiskManager(cfg, executor=_FakeExecutor())
    rm.roll_session(date(2026, 7, 17))
    _lose(rm); _lose(rm); _lose(rm)  # stand-down tripped
    rm.notify_feed_lost()  # feed also down
    assert rm.entries_allowed is False
    rm.notify_feed_restored()  # feed back, but stand-down still latched
    assert rm.entries_allowed is False
    rm.roll_session(date(2026, 7, 18))  # stand-down cleared, feed already ok
    assert rm.entries_allowed is True
