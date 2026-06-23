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
        "ALPACA_BASE_URL",
        "SHORT_MA_PERIODS",
        "LONG_MA_PERIODS",
        "CANDLE_INTERVAL",
        "LONG_CANDLE_INTERVAL",
        "ENTRY_THRESHOLD",
        "MIN_ALLOC",
        "MAX_ALLOC",
        "WATCHLIST",
        "MARKET_OPEN",
    ]:
        monkeypatch.delenv(k, raising=False)
    for k, v in {**_VALID_ENV, **overrides}.items():
        monkeypatch.setenv(k, v)


def test_loads_defaults(monkeypatch):
    _set_env(monkeypatch)
    cfg = Config.load(dotenv=False)
    assert cfg.watchlist == ("NFLX", "BIRD", "WPM")
    assert cfg.short_ma_periods == (8, 10, 20)
    assert cfg.long_ma_periods == (21, 34, 55)
    assert cfg.interval_seconds == 60
    assert cfg.long_interval_seconds == 300
    assert cfg.entry_threshold == 60.0
    assert "paper" in cfg.alpaca_base_url


def test_warmup_lookback_days_default_and_override(monkeypatch):
    _set_env(monkeypatch)
    assert Config.load(dotenv=False).warmup_lookback_days == 5
    _set_env(monkeypatch, WARMUP_LOOKBACK_DAYS="0")  # 0 disables warmup
    assert Config.load(dotenv=False).warmup_lookback_days == 0


def test_missing_secret_raises(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.delenv("ALPACA_KEY_ID", raising=False)
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_rejects_live_endpoint(monkeypatch):
    _set_env(monkeypatch, ALPACA_BASE_URL="https://api.alpaca.markets")
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_rejects_bad_ribbon_ordering(monkeypatch):
    _set_env(monkeypatch, SHORT_MA_PERIODS="20,10,8")  # must be fast<mid<slow
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_rejects_wrong_ribbon_length(monkeypatch):
    _set_env(monkeypatch, SHORT_MA_PERIODS="8,10")  # needs exactly 3
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_rejects_long_interval_not_longer(monkeypatch):
    _set_env(monkeypatch, CANDLE_INTERVAL="5m", LONG_CANDLE_INTERVAL="1m")
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_interval_parsing(monkeypatch):
    _set_env(monkeypatch, CANDLE_INTERVAL="30s", LONG_CANDLE_INTERVAL="2m")
    cfg = Config.load(dotenv=False)
    assert cfg.interval_seconds == 30
    assert cfg.long_interval_seconds == 120


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
    # IMP-005: the EOD-flatten / no-new-entries window defaults to 15 min before the
    # close (was 5) so the flatten runs while the tape is still liquid and the close
    # market orders fill before 16:00 ET — preventing the 2026-06-18 naked-overnight carry.
    assert cfg.flatten_before_close_min == 15
