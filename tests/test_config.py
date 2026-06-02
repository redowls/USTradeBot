"""Sanity tests for the config layer (Phase 0)."""

from __future__ import annotations

import pytest

from bot.config import Config, ConfigError

_VALID_ENV = {
    "ALPACA_KEY_ID": "k",
    "ALPACA_SECRET": "s",
    "TELEGRAM_TOKEN": "t",
    "TELEGRAM_CHAT_ID": "c",
}


def _set_env(monkeypatch, **overrides):
    for k in list(_VALID_ENV) + [
        "ALPACA_BASE_URL", "FAST_MA_PERIOD", "SLOW_MA_PERIOD", "TREND_MA_PERIOD",
        "ENTRY_THRESHOLD", "MIN_ALLOC", "MAX_ALLOC", "WATCHLIST", "MARKET_OPEN",
    ]:
        monkeypatch.delenv(k, raising=False)
    for k, v in {**_VALID_ENV, **overrides}.items():
        monkeypatch.setenv(k, v)


def test_loads_defaults(monkeypatch):
    _set_env(monkeypatch)
    cfg = Config.load(dotenv=False)
    assert cfg.watchlist == ("NFLX", "BIRD", "WPM")
    assert cfg.fast_ma_period == 9
    assert cfg.slow_ma_period == 21
    assert cfg.entry_threshold == 60.0
    assert "paper" in cfg.alpaca_base_url


def test_missing_secret_raises(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.delenv("ALPACA_KEY_ID", raising=False)
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_rejects_live_endpoint(monkeypatch):
    _set_env(monkeypatch, ALPACA_BASE_URL="https://api.alpaca.markets")
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_rejects_bad_ma_ordering(monkeypatch):
    _set_env(monkeypatch, FAST_MA_PERIOD="21", SLOW_MA_PERIOD="9")
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_watchlist_parsing(monkeypatch):
    _set_env(monkeypatch, WATCHLIST=" aapl, msft ,tsla ")
    cfg = Config.load(dotenv=False)
    assert cfg.watchlist == ("AAPL", "MSFT", "TSLA")


def test_secrets_not_in_repr(monkeypatch):
    _set_env(monkeypatch, ALPACA_SECRET="supersecret")
    cfg = Config.load(dotenv=False)
    assert "supersecret" not in repr(cfg)


def test_market_hours_are_eastern(monkeypatch):
    _set_env(monkeypatch)
    cfg = Config.load(dotenv=False)
    assert cfg.market_open.hour == 9
    assert cfg.market_open.minute == 30
    assert cfg.market_open.tzinfo is not None
