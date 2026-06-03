"""Tests for the order executor (Phase 4).

A fake trading client captures the submitted bracket request and scripts the
account / order responses — no network, no real keys.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce

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
    def __init__(self, *, buying_power="10000", equity="10000", status="accepted", raise_on=None):
        self.account = SimpleNamespace(buying_power=buying_power, equity=equity)
        self.submitted = []
        self._status = status
        self._raise_on = raise_on  # "account" | "submit" | None

    def get_account(self):
        if self._raise_on == "account":
            raise RuntimeError("account unreachable")
        return self.account

    def submit_order(self, order_data):
        if self._raise_on == "submit":
            raise RuntimeError("rejected by API")
        self.submitted.append(order_data)
        return SimpleNamespace(id="order-1", status=self._status)


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
