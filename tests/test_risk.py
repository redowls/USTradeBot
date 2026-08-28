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
        entry_fill=None, replace_gone=False, last_equity=None, entry_filled_at=None,
    ):
        self._order_id = order_id
        self._replace_ok = replace_ok
        self._replace_gone = replace_gone  # replace_stop_price raises StopOrderGone (leg filled)
        self._reconciled = reconciled  # (order_id, price) of a broker-side fill, or None
        self._close_fill = close_fill  # actual fill price of the bot's own close, or None
        self._entry_fill = entry_fill  # corrected entry buy fill (delayed fill), or None
        self.last_equity = last_equity  # session-open equity baseline for the stand-down
        self._entry_filled_at = entry_filled_at  # IMP-027 recency anchor for reconcile
        self.closed = []
        self.moved = []
        self.reconcile_calls = []
        self.entry_fill_calls = []
        self.reconcile_afters = []  # `after=` each reconcile_exit was anchored on

    def close_position(self, symbol):
        self.closed.append(symbol)
        return self._order_id

    def close_fill_price(self, order_id):
        return self._close_fill

    def entry_fill_price(self, order_id):
        self.entry_fill_calls.append(order_id)
        return self._entry_fill

    def entry_filled_at(self, order_id):
        return self._entry_filled_at

    def reconcile_exit(self, symbol, *, after=None):
        self.reconcile_calls.append(symbol)
        self.reconcile_afters.append(after)
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
    assert ex.moved == [("stop-1", 108.9)]  # 110 * (1 - 0.010), past the tighten threshold


def test_trailing_stop_never_lowers(cfg):
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    rm.update_trailing_stop(_rising(110.0), _entry())  # stop -> 108.90
    # price pulls back to 105 -> 103.95 < 108.90, so the stop is left where it is
    assert rm.update_trailing_stop(_rising(105.0), _entry()) is TrailResult.HELD
    assert ex.moved == [("stop-1", 108.9)]


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
    assert ex.moved == [("stop-1", 108.9), ("stop-1", 108.9)]


def test_trailing_stop_targets_replacement_id_on_next_move(cfg):
    # Regression for the 422 "order already replaced" loop: Alpaca rotates the order id
    # on every replace, so the second ratchet must target the replacement ("stop-1-r"),
    # not the now-dead original ("stop-1") which would 422 forever.
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.MOVED  # 108.90 stop-1
    assert rm.update_trailing_stop(_rising(115.0), _entry()) is TrailResult.MOVED  # 113.85 stop-1-r
    assert ex.moved == [("stop-1", 108.9), ("stop-1-r", 113.85)]


def test_trailing_stop_reports_stop_gone_when_leg_filled(cfg):
    # IMP-012 regression: 2026-06-30 AMD/SE stopped out broker-side intraday, so the
    # stop leg was no longer open and every trailing move 422'd "order is not open"
    # (504 tracebacks, symbols stuck MANAGING ~4.5h). The risk manager must surface
    # that as STOP_GONE so the strategy reconciles the exit instead of retrying forever.
    ex = _FakeExecutor(replace_gone=True)
    rm = RiskManager(cfg, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.STOP_GONE
    assert ex.moved == [("stop-1", 108.9)]  # the move was attempted, then reported gone


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
    # The fill is this trade's own stop leg ("stop-1") at 97.94 — below the 98.0 bracket
    # stop and never ratcheted — so IMP-038 names it `stop loss`, not the old catch-all.
    ex = _FakeExecutor(order_id=None, reconciled=("stop-1", 97.94))
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    result = rm.exit_position("TSLA", 99.5, "end-of-day flatten", _entry())
    assert result is not None
    assert result.exit_price == 97.94  # the real broker-side fill, not the 99.5 passed in
    assert result.reason == "end-of-day flatten (stop loss)"
    assert result.order_id == "stop-1"
    assert ex.reconcile_calls == ["TSLA"]
    assert seen == [result]  # on_exit fired → the exit is persisted


def test_reconcile_if_closed_records_broker_side_fill(cfg):
    # IMP-014 regression (2026-07-10 SE): a broker-side stop that fills on a DOWN move is
    # never surfaced by the trailing ratchet (no higher-high replace to 422), so the
    # wall-clock sweep polls order history to detect it. reconcile_if_closed must record the
    # exit at the real fill, tag it a broker-side fill, and NEVER submit a close.
    # SE's stop filled on a DOWN move, so the fill is the stop leg below the entry — the
    # narrative this fixture has always described. IMP-038 books it as `stop loss`.
    ex = _FakeExecutor(reconciled=("stop-1", 97.88), entry_fill=100.0)  # entry did fill
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    result = rm.reconcile_if_closed("SE", _entry())
    assert result is not None
    assert ex.closed == []  # read-only: never attempted a close
    assert ex.reconcile_calls == ["SE"]
    assert result.exit_price == 97.88  # the true broker-side fill
    assert result.reason == "stop loss"
    assert result.order_id == "stop-1"
    assert result.qty == 10  # carried from the entry
    assert seen == [result]  # persisted via on_exit


# --- which leg actually filled? (IMP-038) ----------------------------------
#
# Every broker-side exit used to book one phrase, `stop/target filled broker-side`, which
# conflates a trail hit, the original stop, the target and (via the still-open close/fill
# race) the bot's own EOD sell. 87 of 274 lifetime exits sat in those buckets holding
# −$1,060 — the entire loss side of the book — while `trailing stop` read n=2.


def _spot_0828() -> ExecutionResult:
    """The real 2026-08-28 SPOT trade: entry 549.99 x3, bracket stop 538.65, target 604.60."""
    return ExecutionResult(
        symbol="SPOT",
        order_id="spot-entry",
        qty=3,
        notional=1648.92,
        entry_price=549.99,
        stop_price=538.65,
        take_profit_price=604.60,
        confidence=63.94,
        status="accepted",
        model="A",
        stop_order_id="b4eac2b5",  # the original bracket stop leg
    )


def test_ratcheted_stop_fill_is_booked_as_trailing_stop(cfg):
    # 2026-08-28 SPOT, the trade that motivated IMP-038. The trail ratcheted eight times
    # (538.65 -> 543.47 -> ... -> 546.05), Alpaca issuing a fresh order id each replace, and
    # the EIGHTH order filled @546.05 — 1.37% ABOVE the original stop, with the take-profit
    # leg cancelled unfilled. The broker record is unambiguous; the bot booked it
    # `stop/target filled broker-side` and the trail took no credit for the exit.
    ex = _FakeExecutor(reconciled=("trail-8", 546.05), entry_fill=549.99)
    seen = []
    rm = RiskManager(cfg, executor=ex, on_exit=seen.append)
    entry = _spot_0828()
    # Replay the ratchet into the manager's bookkeeping, exactly as the live moves left it.
    rm._trail_stops["b4eac2b5"] = 546.05
    rm._live_stop_oid["b4eac2b5"] = "trail-8"

    result = rm.reconcile_if_closed("SPOT", entry)
    assert result is not None
    assert result.reason == "trailing stop"  # NOT the old catch-all
    assert result.exit_price == 546.05
    assert result.order_id == "trail-8"
    assert ex.closed == []  # attribution only: still read-only


def test_unratcheted_stop_fill_is_booked_as_stop_loss(cfg):
    # Same shape, but the trail never moved: the original bracket stop is still the live
    # leg, so this is a genuine -2% stop-out and must NOT be credited to the trail.
    ex = _FakeExecutor(reconciled=("b4eac2b5", 538.65), entry_fill=549.99)
    rm = RiskManager(cfg, executor=ex, on_exit=lambda _: None)
    result = rm.reconcile_if_closed("SPOT", _spot_0828())
    assert result is not None
    assert result.reason == "stop loss"


def test_target_fill_is_booked_as_take_profit(cfg):
    # The other resting leg: a limit sell that clears the take-profit price.
    ex = _FakeExecutor(reconciled=("tp-leg", 604.60), entry_fill=549.99)
    rm = RiskManager(cfg, executor=ex, on_exit=lambda _: None)
    result = rm.reconcile_if_closed("SPOT", _spot_0828())
    assert result is not None
    assert result.reason == "take profit"


def test_unattributable_fill_keeps_the_honest_catch_all(cfg):
    # An id we cannot place, filling between the stop and the target — the shape of the
    # close/fill race still open in todo.md (the bot's own sell, re-found by reconcile).
    # We must NOT guess a leg; the catch-all stays so the ambiguity is visible in SQL.
    ex = _FakeExecutor(reconciled=("who-knows", 551.00), entry_fill=549.99)
    rm = RiskManager(cfg, executor=ex, on_exit=lambda _: None)
    result = rm.reconcile_if_closed("SPOT", _spot_0828())
    assert result is not None
    assert result.reason == "stop/target filled broker-side"


def test_startup_reconciled_holding_has_no_entry_to_attribute_against(cfg):
    # No ExecutionResult (a position adopted at startup) → nothing to compare the fill to.
    ex = _FakeExecutor(reconciled=("mystery", 100.0))
    rm = RiskManager(cfg, executor=ex, on_exit=lambda _: None)
    result = rm.reconcile_if_closed("NFLX", None)
    assert result is not None
    assert result.reason == "stop/target filled broker-side"


def test_eod_flatten_that_finds_a_trail_fill_names_the_trail(cfg):
    # The `exit_position` fallback path: the EOD flatten's close 404s because the trail had
    # already filled broker-side. The caller's reason is kept AND the leg is named, so
    # `end-of-day flatten (stop/target filled broker-side)` (n=34, -$550 lifetime) splits
    # into the real causes instead of one opaque bucket.
    ex = _FakeExecutor(order_id=None, reconciled=("trail-8", 546.05), entry_fill=549.99)
    rm = RiskManager(cfg, executor=ex, on_exit=lambda _: None)
    entry = _spot_0828()
    rm._trail_stops["b4eac2b5"] = 546.05
    rm._live_stop_oid["b4eac2b5"] = "trail-8"
    result = rm.exit_position("SPOT", 545.0, "end-of-day flatten", entry)
    assert result is not None
    assert result.reason == "end-of-day flatten (trailing stop)"


def test_stop_gone_caller_reason_is_not_duplicated(cfg):
    # The STOP_GONE path already passes "trailing stop"; naming the leg must not produce
    # `trailing stop (trailing stop)`.
    ex = _FakeExecutor(order_id=None, reconciled=("trail-8", 546.05), entry_fill=549.99)
    rm = RiskManager(cfg, executor=ex, on_exit=lambda _: None)
    entry = _spot_0828()
    rm._trail_stops["b4eac2b5"] = 546.05
    rm._live_stop_oid["b4eac2b5"] = "trail-8"
    result = rm.exit_position("SPOT", 545.0, "trailing stop", entry)
    assert result is not None
    assert result.reason == "trailing stop"


def test_attribution_does_not_move_price_or_pnl(cfg):
    # Guard the "observational only" claim: the recorded price and qty are identical to
    # what the old catch-all produced — only `reason` changes.
    ex = _FakeExecutor(reconciled=("trail-8", 546.05), entry_fill=549.99)
    rm = RiskManager(cfg, executor=ex, on_exit=lambda _: None)
    entry = _spot_0828()
    rm._trail_stops["b4eac2b5"] = 546.05
    rm._live_stop_oid["b4eac2b5"] = "trail-8"
    result = rm.reconcile_if_closed("SPOT", entry)
    assert result is not None
    assert result.exit_price == 546.05  # the broker fill, untouched
    assert result.qty == 3
    assert result.entry_fill_price == 549.99
    # ...and the real trade's P/L still reconciles to the broker's -$11.82.
    assert round((546.05 - 549.99) * 3, 2) == -11.82


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


def test_both_reconcile_paths_anchor_on_the_entry_fill_time(cfg):
    # IMP-027 (2026-08-12 MU): reconcile_exit can only refuse a previous trade's sell if it
    # is told when THIS trade's entry filled. Both paths that reach it — the poll-driven
    # sweep and the close-failed fallback in exit_position — must pass that anchor; an
    # unanchored call is exactly the bug (it booked an 08-10 fill as the 08-12 exit).
    filled = datetime(2026, 8, 12, 14, 8, 1, 582526, tzinfo=UTC)
    ex = _FakeExecutor(
        order_id=None,  # close didn't submit → exit_position falls back to reconcile
        reconciled=("c94f6f32", 926.31), entry_fill=924.08, entry_filled_at=filled,
    )
    rm = RiskManager(cfg, executor=ex)
    rm.reconcile_if_closed("MU", _entry())
    rm.exit_position("MU", 926.31, "trailing stop", _entry())
    assert ex.reconcile_calls == ["MU", "MU"]
    assert ex.reconcile_afters == [filled, filled]  # neither path went unanchored


def test_reconcile_anchor_is_none_without_an_entry(cfg):
    # A startup-reconciled holding has no entry order, so there is nothing to anchor on and
    # the guard must stand down (None) rather than block a legitimate exit.
    ex = _FakeExecutor(reconciled=("stop-se", 113.21), entry_filled_at=None)
    RiskManager(cfg, executor=ex).reconcile_if_closed("SE", None)
    assert ex.reconcile_afters == [None]


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


# --- two-stage trail (IMP-021) -------------------------------------------


@pytest.fixture
def cfg_two_stage(monkeypatch):
    """Live IMP-021 settings: trail 1.25%, tightening to 1.0% once +1.0% in profit."""
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("TRAIL_TIGHTEN_AFTER", "0.010")
    monkeypatch.setenv("TRAIL_PERCENT_TIGHT", "0.010")
    return Config.load(dotenv=False)


def test_two_stage_trail_uses_wide_width_below_threshold(cfg_two_stage):
    # +0.5% is not yet "proven": the trade keeps the full 1.25% width, i.e. behaviour
    # below the threshold is byte-identical to the flat trail.
    ex = _FakeExecutor()
    rm = RiskManager(cfg_two_stage, executor=ex)
    assert rm.update_trailing_stop(_rising(100.5), _entry()) is TrailResult.MOVED
    assert ex.moved == [("stop-1", 99.24)]  # 100.5 * (1 - 0.0125)


def test_two_stage_trail_tightens_once_in_profit(cfg_two_stage):
    # At +1.0% the trade has proven itself and the width drops to 1.0%.
    ex = _FakeExecutor()
    rm = RiskManager(cfg_two_stage, executor=ex)
    assert rm.update_trailing_stop(_rising(110.0), _entry()) is TrailResult.MOVED
    assert ex.moved == [("stop-1", 108.9)]  # 110 * (1 - 0.010), not 108.62


def test_two_stage_trail_is_the_shipped_default(cfg):
    # IMP-021 ships the two-stage trail on by default, so a bare config already
    # tightens; this pins the shipped values so silent config drift fails loudly.
    assert cfg.trail_tighten_after == 0.010
    assert cfg.trail_percent_tight == 0.010
    assert cfg.trail_percent == 0.0125


def test_two_stage_trail_can_be_disabled(monkeypatch):
    # TRAIL_TIGHTEN_AFTER=0 -> single flat width, i.e. the pre-IMP-021 behaviour.
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("TRAIL_TIGHTEN_AFTER", "0")
    flat = Config.load(dotenv=False)
    ex = _FakeExecutor()
    rm = RiskManager(flat, executor=ex)
    rm.update_trailing_stop(_rising(110.0), _entry())
    assert ex.moved == [("stop-1", 108.62)]  # 110 * (1 - 0.0125)


def test_two_stage_trail_never_lowers_after_tightening(cfg_two_stage):
    # The ratchet invariant must survive the width switch: once the tight stop is set,
    # a pullback back below the threshold must not hand the position a looser stop.
    ex = _FakeExecutor()
    rm = RiskManager(cfg_two_stage, executor=ex)
    rm.update_trailing_stop(_rising(110.0), _entry())            # tight -> 108.90
    assert rm.update_trailing_stop(_rising(100.4), _entry()) is TrailResult.HELD
    assert ex.moved == [("stop-1", 108.9)]


def test_two_stage_trail_amd_2026_08_03_regression(cfg_two_stage):
    """Regression for the trade that motivated IMP-021.

    AMD entered 2026-08-03 16:31 UTC @ $482.498, ran to a high of ~$490.85 (+1.69%),
    then gave back a full 1.25% trail width and exited @ $484.68 for +$10.91 — banking
    27% of the move it had actually earned. Under the two-stage trail the position is
    past the +1.0% threshold at the peak, so the stop rides 1.0% behind instead.
    """
    ex = _FakeExecutor()
    entry = ExecutionResult(
        symbol="AMD", order_id="o1", qty=5, notional=2412.49,
        entry_price=482.498, stop_price=472.85, take_profit_price=530.75,
        confidence=77.96, status="accepted", model="A", stop_order_id="stop-1",
    )
    rm = RiskManager(cfg_two_stage, executor=ex)
    rm.update_trailing_stop(_rising(490.85), entry)
    tightened = ex.moved[-1][1]
    assert tightened == pytest.approx(485.94, abs=0.01)  # 490.85 * (1 - 0.010)
    # Strictly better than what actually happened, and still below the peak.
    assert tightened > 484.68
    assert tightened < 490.85


# --- in-trade excursion (IMP-037) ---------------------------------------


def test_excursion_tracks_high_and_low_water_closes(cfg):
    """MFE/MAE follow the running extremes of the managed closes, not the last one."""
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    entry = _entry()
    for close in (101.0, 103.0, 99.0, 100.5):  # up, up, down, back up
        rm.update_trailing_stop(_rising(close), entry)

    result = rm.exit_position("NFLX", 100.5, "test", entry)

    assert result.mfe_pct == pytest.approx(3.0)  # 103.0 vs 100.0 entry
    assert result.mae_pct == pytest.approx(-1.0)  # 99.0 vs 100.0 entry


def test_excursion_is_seeded_at_entry_so_a_pure_loser_reports_zero_mfe(cfg):
    """A trade that never trades above entry reports mfe 0, not a negative."""
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    entry = _entry()
    for close in (99.5, 98.5):
        rm.update_trailing_stop(_rising(close), entry)

    result = rm.exit_position("NFLX", 98.5, "test", entry)

    assert result.mfe_pct == pytest.approx(0.0)
    assert result.mae_pct == pytest.approx(-1.5)


def test_excursion_is_none_when_the_position_was_never_managed(cfg):
    """Absence of measurement is None — never a zero excursion (startup-reconciled)."""
    rm = RiskManager(cfg, executor=_FakeExecutor())

    result = rm.exit_position("NFLX", 100.0, "test", _entry())

    assert result.mfe_pct is None
    assert result.mae_pct is None


def test_excursion_is_measured_without_a_movable_stop_leg(cfg):
    """A holding whose stop leg can't be moved still gets measured: the tracker runs
    before update_trailing_stop's no-key early return."""
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    entry = _entry(stop_order_id="")  # adopted holding: nothing to replace

    assert rm.update_trailing_stop(_rising(102.0), entry) is TrailResult.HELD
    result = rm.exit_position("NFLX", 102.0, "test", entry)

    assert result.mfe_pct == pytest.approx(2.0)


def test_excursion_does_not_leak_across_a_re_entry(cfg):
    """State is popped at exit, so the next trade in the same symbol starts clean."""
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    entry = _entry()
    rm.update_trailing_stop(_rising(105.0), entry)
    first = rm.exit_position("NFLX", 105.0, "test", entry)
    assert first.mfe_pct == pytest.approx(5.0)

    second_entry = _entry(stop_order_id="stop-2")
    rm.update_trailing_stop(_rising(101.0), second_entry)
    second = rm.exit_position("NFLX", 101.0, "test", second_entry)

    assert second.mfe_pct == pytest.approx(1.0)  # not the 5.0 the previous trade reached


def test_nvda_2026_08_27_giveback_is_now_measurable(cfg):
    """The trade that motivated IMP-037, from the real fills.

    NVDA entered @224.5875 on 2026-08-27, ran to a 227.17 high-water close (+1.15%),
    tripped the +1% tighten so the stop landed at 224.90, and booked +0.14%. The whole
    give-back was invisible in dbo.trades: pnl_pct said +0.14% and nothing recorded that
    the move had been there at all. Capture = realized / mfe must now be reconstructable
    from the row alone.
    """
    ex = _FakeExecutor()
    rm = RiskManager(cfg, executor=ex)
    entry = ExecutionResult(
        symbol="NVDA", order_id="o-nvda", qty=12, notional=2695.05,
        entry_price=224.5875, stop_price=220.25, take_profit_price=247.23,
        confidence=82.43, status="accepted", model="A", stop_order_id="stop-nvda",
    )
    for close in (225.40, 226.27, 227.17, 225.34):
        rm.update_trailing_stop(_rising(close), entry)

    result = rm.exit_position("NVDA", 224.9025, "stop/target filled broker-side", entry)

    assert result.mfe_pct == pytest.approx(1.15, abs=0.01)
    realized_pct = (224.9025 / 224.5875 - 1.0) * 100.0
    assert realized_pct / result.mfe_pct < 0.15  # capture under 15% — the finding
