"""Tests for the order executor (Phase 4).

A fake trading client captures the submitted bracket request and scripts the
account / order responses — no network, no real keys.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from alpaca.trading.enums import (
    OrderClass,
    OrderSide,
    OrderType,
    QueryOrderStatus,
    TimeInForce,
)

from bot.config import Config
from bot.executor import OrderExecutor

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


class _FakeTrading:
    def __init__(
        self, *, buying_power="10000", equity="10000", status="accepted",
        raise_on=None, with_legs=False, open_orders=(), held_until_cancelled=False,
        qty_available_after=0, close_position_gone=False, position_open=True,
        closed_sell_orders=(), close_fills=True, close_fill=None, entry_fill=None,
    ):
        self.account = SimpleNamespace(buying_power=buying_power, equity=equity)
        self.submitted = []
        self.closed = []
        self.replaced = []
        self.cancelled = []
        self._status = status
        self._raise_on = raise_on  # "account"|"submit"|"close"|"replace"|"list_orders"|None
        self._with_legs = with_legs
        # Resting orders the close must clear first, keyed nowhere — just a flat list.
        self._open_orders = [SimpleNamespace(id=oid) for oid in open_orders]
        # When True, close_position 403s (held_for_orders) until the legs are cancelled,
        # mirroring Alpaca: the bracket reserves the whole qty until its legs are gone.
        self._held_until_cancelled = held_until_cancelled
        # Number of get_open_position polls that still report the qty held_for_orders
        # before the cancel "settles" and the qty frees — models Alpaca's async cancel
        # (the cancel call returns OK but qty_available stays 0 for a few seconds).
        self._qty_available_after = qty_available_after
        self.poll_count = 0
        self._released = qty_available_after == 0
        # 2026-06-17: a broker-side stop/target fill closed the position before the
        # bot's close ran, so close_position 404s "position not found" and
        # get_open_position raises the same — and the exit must be reconciled from the
        # most recent filled sell in order history.
        self._close_position_gone = close_position_gone
        self._position_open = position_open
        self._closed_sell_orders = list(closed_sell_orders)
        # When True the close's market sell fills, so the position goes flat (the broker
        # then 404s on a follow-up read — the confirm-flat check). When False the order is
        # accepted but never fills (e.g. submitted after the 16:00 close), so the position
        # lingers open — the 2026-06-18 EOD-flatten naked-carry scenario.
        self._close_fills = close_fills
        # filled_avg_price the close market order is reported to have filled at, read back
        # via get_order_by_id (2026-06-23: record the real fill, not the candle estimate).
        self._close_fill = close_fill
        # filled_avg_price the bracket entry's parent order ("order-1") is reported to have
        # filled at, read back via get_order_by_id (2026-06-24: record the real entry fill,
        # not the candle-close estimate the signal sized off).
        self._entry_fill = entry_fill

    def get_order_by_id(self, order_id):
        fill = self._entry_fill if order_id == "order-1" else self._close_fill
        return SimpleNamespace(id=order_id, filled_avg_price=fill)

    def get_account(self):
        if self._raise_on == "account":
            raise RuntimeError("account unreachable")
        return self.account

    def submit_order(self, order_data):
        if self._raise_on == "submit":
            raise RuntimeError("rejected by API")
        self.submitted.append(order_data)
        legs = None
        if self._with_legs:
            legs = [
                SimpleNamespace(id="tp-leg", order_type=OrderType.LIMIT),
                SimpleNamespace(id="stop-leg", order_type=OrderType.STOP),
            ]
        return SimpleNamespace(id="order-1", status=self._status, legs=legs)

    def get_orders(self, filter=None):
        if self._raise_on == "list_orders":
            raise RuntimeError("orders unreachable")
        if getattr(filter, "status", None) == QueryOrderStatus.CLOSED:
            return list(self._closed_sell_orders)
        return list(self._open_orders)

    def cancel_order_by_id(self, order_id):
        self.cancelled.append(order_id)
        self._open_orders = [o for o in self._open_orders if o.id != order_id]

    def get_open_position(self, symbol):
        if not self._position_open:
            raise RuntimeError(f'{{"code":40410000,"message":"position not found: {symbol}"}}')
        self.poll_count += 1
        if self.poll_count > self._qty_available_after:
            self._released = True
        return SimpleNamespace(
            symbol=symbol, qty="10", qty_available=("10" if self._released else "0")
        )

    def close_position(self, symbol):
        if self._close_position_gone:
            raise RuntimeError(f'{{"code":40410000,"message":"position not found: {symbol}"}}')
        if self._raise_on == "close":
            raise RuntimeError("no position")
        if self._held_until_cancelled and self._open_orders:
            raise RuntimeError("insufficient qty available (held_for_orders)")
        if not self._released:
            raise RuntimeError("insufficient qty available (held_for_orders)")
        self.closed.append(symbol)
        if self._close_fills:
            self._position_open = False  # the market sell filled → position goes flat
        return SimpleNamespace(id="close-1", status="accepted")

    def replace_order_by_id(self, order_id, order_data):
        if self._raise_on == "replace":
            raise RuntimeError("order not replaceable")
        self.replaced.append((order_id, float(order_data.stop_price)))
        # Alpaca cancels the old order and issues a new one with a NEW id.
        return SimpleNamespace(id=order_id + "-r", status="accepted")


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    # The close-position retry/poll loop sleeps between attempts; no-op it so the
    # suite stays fast without changing the retry logic under test.
    monkeypatch.setattr("bot.executor.time.sleep", lambda *_: None)


def _exec(cfg, fake, **kw):
    return OrderExecutor(cfg, trading_factory=lambda: fake, **kw)


def test_execute_submits_bracket_with_sized_qty(cfg):
    fake = _FakeTrading(buying_power="10000")
    seen = []
    ex = _exec(cfg, fake, on_result=seen.append)

    # conf 80 -> 0.25 * 10000 = $2500 -> 25 shares @ 100
    result = ex.execute(symbol="NFLX", entry_price=100.0, confidence=80.0)

    assert result is not None
    assert result.qty == 25
    assert result.order_id == "order-1"
    assert result.model == "A"
    assert seen == [result]  # on_result fired

    (req,) = fake.submitted
    assert req.symbol == "NFLX"
    assert req.qty == 25
    assert req.side == OrderSide.BUY
    assert req.time_in_force == TimeInForce.DAY
    assert req.order_class == OrderClass.BRACKET
    assert req.take_profit.limit_price == 104.0
    assert req.stop_loss.stop_price == 98.0


def test_execute_records_actual_entry_fill_price(cfg):
    # Regression (2026-06-24, IMP-009): the bracket buy fills at a real broker price
    # (INTC @134.7817) that differs from the candle-close estimate the signal sized off
    # (134.76). The recorded entry must be the true fill so P/L and the win/loss flag are
    # exact — the entry-side analogue of IMP-008's exit-fill fix.
    fake = _FakeTrading(entry_fill="134.781667")
    result = _exec(cfg, fake).execute(symbol="INTC", entry_price=134.76, confidence=80.0)
    assert result is not None
    assert result.entry_price == pytest.approx(134.781667)


def test_execute_falls_back_to_estimate_when_entry_fill_unreadable(cfg):
    # When the entry fill can't be read (unfilled within the budget / read error), the
    # recorded entry falls back to the sizing estimate — never a fabricated 0.0 entry.
    fake = _FakeTrading(entry_fill=None)
    result = _exec(cfg, fake).execute(symbol="NFLX", entry_price=100.0, confidence=80.0)
    assert result is not None
    assert result.entry_price == 100.0


def test_entry_fill_price_returns_actual_filled_avg(cfg):
    fake = _FakeTrading(entry_fill="134.781667")
    assert _exec(cfg, fake).entry_fill_price("order-1") == pytest.approx(134.781667)


def test_entry_fill_price_none_when_unreadable(cfg):
    # Empty id, or a parent order that never reports a fill within the poll budget, → None
    # so the caller keeps the sizing estimate.
    fake = _FakeTrading(entry_fill=None)
    ex = _exec(cfg, fake)
    assert ex.entry_fill_price("") is None  # no id to look up
    assert ex.entry_fill_price("order-1") is None  # never fills within the budget


def test_rejected_status_returns_none(cfg):
    fake = _FakeTrading(status="rejected")
    assert _exec(cfg, fake).execute(symbol="NFLX", entry_price=100.0, confidence=80.0) is None


def test_submit_error_is_swallowed(cfg):
    fake = _FakeTrading(raise_on="submit")
    assert _exec(cfg, fake).execute(symbol="NFLX", entry_price=100.0, confidence=80.0) is None


def test_account_error_skips_entry(cfg):
    fake = _FakeTrading(raise_on="account")
    assert _exec(cfg, fake).execute(symbol="NFLX", entry_price=100.0, confidence=80.0) is None
    assert fake.submitted == []  # never reached submit


def test_sub_one_share_skips_without_submitting(cfg):
    fake = _FakeTrading(buying_power="1000")  # 0.10*1000 = $100 target
    # price 150 -> 0 shares
    assert _exec(cfg, fake).execute(symbol="NFLX", entry_price=150.0, confidence=60.0) is None
    assert fake.submitted == []


def test_model_b_path(cfg, monkeypatch):
    monkeypatch.setenv("SIZING_MODEL", "B")
    cfg_b = Config.load(dotenv=False)
    fake = _FakeTrading(buying_power="10000", equity="10000")
    result = _exec(cfg_b, fake).execute(symbol="NFLX", entry_price=100.0, confidence=100.0)
    assert result is not None
    assert result.model == "B"
    assert result.qty == 40  # capped by max_alloc (see test_sizing)


def test_execute_captures_stop_leg_id(cfg):
    fake = _FakeTrading(with_legs=True)
    result = _exec(cfg, fake).execute(symbol="NFLX", entry_price=100.0, confidence=80.0)
    assert result is not None
    assert result.stop_order_id == "stop-leg"  # the STOP leg, not the take-profit leg


def test_execute_without_legs_has_empty_stop_id(cfg):
    fake = _FakeTrading()  # response carries no legs
    result = _exec(cfg, fake).execute(symbol="NFLX", entry_price=100.0, confidence=80.0)
    assert result is not None and result.stop_order_id == ""


def test_replace_stop_price_returns_new_order_id(cfg):
    # The replace must hand back the replacement order's id so the caller targets it
    # next time, instead of re-replacing the now-dead original (which 422s).
    fake = _FakeTrading()
    assert _exec(cfg, fake).replace_stop_price("stop-leg", 107.85) == "stop-leg-r"
    assert fake.replaced == [("stop-leg", 107.85)]


def test_replace_stop_price_empty_id_is_noop(cfg):
    fake = _FakeTrading()
    assert _exec(cfg, fake).replace_stop_price("", 107.85) is None
    assert fake.replaced == []


def test_replace_stop_price_error_returns_none(cfg):
    fake = _FakeTrading(raise_on="replace")
    assert _exec(cfg, fake).replace_stop_price("stop-leg", 107.85) is None


def test_close_position_returns_order_id(cfg):
    fake = _FakeTrading()
    order_id = _exec(cfg, fake).close_position("NFLX")
    assert order_id == "close-1"
    assert fake.closed == ["NFLX"]


def test_close_position_error_returns_none(cfg):
    fake = _FakeTrading(raise_on="close")
    assert _exec(cfg, fake).close_position("NFLX") is None


def test_close_position_cancels_bracket_legs_first(cfg):
    # Regression: the 06-08 overnight-loss bug. The resting bracket legs reserve the
    # whole qty (held_for_orders); without cancelling them first close_position 403s.
    fake = _FakeTrading(open_orders=("tp-leg", "stop-leg"), held_until_cancelled=True)
    order_id = _exec(cfg, fake).close_position("TSLA")
    assert order_id == "close-1"
    assert sorted(fake.cancelled) == ["stop-leg", "tp-leg"]  # both legs cleared
    assert fake.closed == ["TSLA"]  # and the liquidation went through


def test_close_position_waits_for_held_qty_to_release(cfg):
    # Regression (2026-06-15 EOD flatten): cancel_order returns OK but the broker keeps
    # the qty held_for_orders for several seconds; closing immediately 403s. All six open
    # names 403'd through the old ~0.8s budget and only closed on a *later* candle pass,
    # which on a thin close may never arrive — leaving the position naked (legs already
    # cancelled). The close must now poll qty_available and liquidate within the SAME call.
    fake = _FakeTrading(open_orders=("stop-leg",), qty_available_after=3)
    order_id = _exec(cfg, fake).close_position("MU")
    assert order_id == "close-1"
    assert fake.closed == ["MU"]  # liquidation went through, not abandoned
    assert fake.poll_count >= 3  # polled until the held qty actually released


def test_close_position_listing_orders_error_still_attempts_close(cfg):
    # A failure enumerating open orders must not block the close (e.g. an unbracketed
    # position, or a transient list error): we log and liquidate anyway.
    fake = _FakeTrading(raise_on="list_orders")
    assert _exec(cfg, fake).close_position("NFLX") == "close-1"
    assert fake.closed == ["NFLX"]


def test_close_position_already_flat_returns_none_without_retry(cfg):
    # Regression (2026-06-17 EOD flatten): the broker-side trailing stop filled before
    # this close ran, so close_position 404s "position not found". The old code retried
    # it 12× and logged an ERROR, leaving the trade phantom-open. It must now detect the
    # already-flat case and bail immediately so the caller reconciles the real exit.
    fake = _FakeTrading(close_position_gone=True)
    assert _exec(cfg, fake).close_position("TSLA") is None
    assert fake.closed == []  # nothing to liquidate — already flat broker-side


def test_close_position_confirms_flat_before_reporting_success(cfg):
    # The happy path: the market sell fills, the broker confirms the position is gone,
    # and only then does the close report success with the order id.
    fake = _FakeTrading(close_fills=True)
    assert _exec(cfg, fake).close_position("NFLX") == "close-1"
    assert fake.closed == ["NFLX"]
    assert fake._position_open is False  # confirmed flat


def test_close_position_unfilled_after_close_returns_none(cfg):
    # Regression (2026-06-18 EOD flatten): the flatten fired ~16:05 ET on a laggy feed,
    # so the market sells were ACCEPTED but never filled — yet the bot reported success,
    # recorded fake exits and carried seven positions NAKED into the weekend. A submit
    # ack is not a close: when the position is still open after submitting, close_position
    # must return None so the caller keeps it MANAGING and the naked-overnight page fires.
    fake = _FakeTrading(close_fills=False)  # order accepted but never fills; stays open
    assert _exec(cfg, fake).close_position("GOOG") is None
    assert fake.closed == ["GOOG"]  # the close WAS submitted...
    assert fake._position_open is True  # ...but the position never went flat


def test_close_fill_price_returns_actual_filled_avg(cfg):
    # Regression (2026-06-23): the bot's own EOD-flatten market sell fills at a real
    # broker price (GOOG @347.14) that differs from the candle-close estimate the caller
    # passed (346.72). close_fill_price reads the order's filled_avg_price so the exit can
    # be recorded at the true fill, not the estimate.
    fake = _FakeTrading(close_fill="347.14")
    assert _exec(cfg, fake).close_fill_price("close-1") == 347.14


def test_close_fill_price_none_when_unreadable(cfg):
    # Empty id, an unfilled order (filled_avg_price None), or a read error all return None
    # so the caller falls back to the price it already had — never a fabricated 0.0 exit.
    fake = _FakeTrading(close_fill=None)
    ex = _exec(cfg, fake)
    assert ex.close_fill_price("") is None  # no id to look up
    assert ex.close_fill_price("close-1") is None  # order present but not yet filled


def test_reconcile_exit_returns_broker_side_fill(cfg):
    # The trailing stop fills broker-side; reconcile recovers the real exit (order id +
    # fill price) from the most recent filled sell so the exit is recorded at its true
    # price — TSLA's stop filled @397.13 on 2026-06-17, not left phantom-open.
    fill = SimpleNamespace(id="stop-leg", filled_avg_price="397.13", status="filled")
    fake = _FakeTrading(position_open=False, closed_sell_orders=(fill,))
    assert _exec(cfg, fake).reconcile_exit("TSLA") == ("stop-leg", 397.13)


def test_reconcile_exit_none_when_position_still_open(cfg):
    # Safety: if the broker still reports a position, a transient close error must NOT
    # be mistaken for a fill — that would abandon a live position. Reconcile returns None.
    fill = SimpleNamespace(id="stop-leg", filled_avg_price="397.13", status="filled")
    fake = _FakeTrading(position_open=True, closed_sell_orders=(fill,))
    assert _exec(cfg, fake).reconcile_exit("TSLA") is None


def test_reconcile_exit_none_when_no_filled_exit(cfg):
    # Flat at the broker but no filled sell to attribute the exit to → None (caller
    # leaves the symbol MANAGING rather than inventing an exit price).
    unfilled = SimpleNamespace(id="x", filled_avg_price=None, status="canceled")
    fake = _FakeTrading(position_open=False, closed_sell_orders=(unfilled,))
    assert _exec(cfg, fake).reconcile_exit("TSLA") is None
