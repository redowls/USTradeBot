"""Tests for the order executor (Phase 4).

A fake trading client captures the submitted bracket request and scripts the
account / order responses — no network, no real keys.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from alpaca.trading.enums import OrderClass, OrderSide, OrderType, TimeInForce

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
        return list(self._open_orders)

    def cancel_order_by_id(self, order_id):
        self.cancelled.append(order_id)
        self._open_orders = [o for o in self._open_orders if o.id != order_id]

    def close_position(self, symbol):
        if self._raise_on == "close":
            raise RuntimeError("no position")
        if self._held_until_cancelled and self._open_orders:
            raise RuntimeError("insufficient qty available (held_for_orders)")
        self.closed.append(symbol)
        return SimpleNamespace(id="close-1", status="accepted")

    def replace_order_by_id(self, order_id, order_data):
        if self._raise_on == "replace":
            raise RuntimeError("order not replaceable")
        self.replaced.append((order_id, float(order_data.stop_price)))
        # Alpaca cancels the old order and issues a new one with a NEW id.
        return SimpleNamespace(id=order_id + "-r", status="accepted")


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


def test_close_position_listing_orders_error_still_attempts_close(cfg):
    # A failure enumerating open orders must not block the close (e.g. an unbracketed
    # position, or a transient list error): we log and liquidate anyway.
    fake = _FakeTrading(raise_on="list_orders")
    assert _exec(cfg, fake).close_position("NFLX") == "close-1"
    assert fake.closed == ["NFLX"]
