"""Tests for the preflight connectivity check (Phase 8).

Each check is exercised with injected fakes — no network, no DB, no real keys —
mirroring the rest of the suite.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bot.config import Config
from bot.market_data import MarketDataClient
from bot.notifier import TelegramNotifier
from bot.preflight import (
    Status,
    check_alpaca,
    check_database,
    check_market_hours,
    check_telegram,
    run_preflight,
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


class _FakeTrading:
    def __init__(self, *, status="ACTIVE", positions=()):
        self._positions = list(positions)
        self.account = SimpleNamespace(
            account_number="PA123",
            status=status,
            equity="10000",
            buying_power="20000",
            cash="10000",
        )

    def get_account(self):
        return self.account

    def get_all_positions(self):
        return self._positions


# --- Alpaca -----------------------------------------------------------------


def test_alpaca_active_account_passes(cfg):
    data = MarketDataClient(cfg, trading_factory=lambda: _FakeTrading())
    r = check_alpaca(data)
    assert r.status is Status.PASS
    assert r.critical
    assert "buying_power=20000" in r.detail


def test_alpaca_non_active_account_warns(cfg):
    data = MarketDataClient(cfg, trading_factory=lambda: _FakeTrading(status="ONBOARDING"))
    assert check_alpaca(data).status is Status.WARN


def test_alpaca_unreachable_fails_critically(cfg):
    def boom():
        raise RuntimeError("network down")

    data = MarketDataClient(cfg, trading_factory=boom)
    r = check_alpaca(data)
    assert r.status is Status.FAIL
    assert r.critical


# --- database ---------------------------------------------------------------


def test_database_connected_passes(cfg):
    store = SimpleNamespace(close=lambda: None)  # a live store object
    assert check_database(cfg, store).status is Status.PASS


def test_database_unset_warns(cfg):
    assert check_database(cfg, None).status is Status.WARN
    assert "disabled" in check_database(cfg, None).detail


def test_database_configured_but_unreachable_warns(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("SQLSERVER_CONN", "DRIVER=...")
    cfg = Config.load(dotenv=False)
    r = check_database(cfg, None)  # open_store returned None despite a conn string
    assert r.status is Status.WARN
    assert "unreachable" in r.detail


# --- Telegram ---------------------------------------------------------------


def test_telegram_delivers_passes():
    sent = []
    notifier = TelegramNotifier("TOK", "CHAT", poster=lambda *a: sent.append(a))
    r = check_telegram(notifier)
    assert r.status is Status.PASS
    assert sent  # a real test message was posted


def test_telegram_send_failure_warns():
    def boom(*_a):
        raise RuntimeError("boom")

    notifier = TelegramNotifier("TOK", "CHAT", poster=boom)
    assert check_telegram(notifier).status is Status.WARN


def test_telegram_disabled_warns():
    assert check_telegram(None).status is Status.WARN


# --- market hours -----------------------------------------------------------


def test_market_hours_open_passes(cfg):
    # 2026-06-03 14:00 UTC = 10:00 EDT on a Wednesday → session open.
    now = datetime(2026, 6, 3, 14, 0, tzinfo=UTC)
    r = check_market_hours(cfg, now)
    assert r.status is Status.PASS
    assert "OPEN" in r.detail


def test_market_hours_closed_warns(cfg):
    # 2026-06-03 02:00 UTC = 22:00 EDT the prior evening → closed.
    now = datetime(2026, 6, 3, 2, 0, tzinfo=UTC)
    r = check_market_hours(cfg, now)
    assert r.status is Status.WARN
    assert "CLOSED" in r.detail


# --- orchestration ----------------------------------------------------------


def test_run_preflight_runs_all_checks_and_closes_store(cfg):
    closed = []
    store = SimpleNamespace(close=lambda: closed.append(True))
    data = MarketDataClient(cfg, trading_factory=lambda: _FakeTrading())
    notifier = TelegramNotifier("TOK", "CHAT", poster=lambda *a: None)
    results = run_preflight(
        cfg,
        data=data,
        store=store,
        notifier=notifier,
        now_utc=datetime(2026, 6, 3, 14, 0, tzinfo=UTC),
    )
    names = [r.name for r in results]
    assert names == [
        "Alpaca paper account",
        "SQL Server persistence",
        "Telegram alerts",
        "Market hours",
    ]
    assert all(r.ok for r in results)
    assert closed == [True]  # the store connection was released
