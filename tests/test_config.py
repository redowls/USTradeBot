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
        "MIN_CROSSOVER",
        "MIN_ALLOC",
        "MAX_ALLOC",
        "SIZE_CONFIDENCE_CAP",
        "WATCHLIST",
        "MARKET_OPEN",
        "MARKET_CLOSE",
        "ENTRY_START",
        "TRAIL_PERCENT",
        "TRAIL_PERCENT_TIGHT",
        "TRAIL_TIGHTEN_AFTER",
        "STOP_LOSS",
        "TAKE_PROFIT",
        "MARKET_FILTER_SYMBOL",
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


def test_min_crossover_default_and_override(monkeypatch):
    # IMP-011: crossover floor introduced (default 0.20, the xo<0.20 chop dead zone);
    # IMP-020 (2026-07-30) raised the default to 0.25 after the 0.20-0.25 band proved
    # the single worst post-floor cohort (40 tr, -$165.93, avg -$4.15). 0 disables it;
    # out-of-range values are rejected by validate().
    _set_env(monkeypatch)
    assert Config.load(dotenv=False).min_crossover == 0.25
    _set_env(monkeypatch, MIN_CROSSOVER="0")  # 0 disables the floor
    assert Config.load(dotenv=False).min_crossover == 0.0
    _set_env(monkeypatch, MIN_CROSSOVER="1.5")  # > 1 is invalid
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_size_confidence_cap_default_and_override(monkeypatch):
    # IMP-013: sizing-confidence cap defaults to 85 (edge does not grow above the
    # 70s band; 90-100 loses). Must lie in [ENTRY_THRESHOLD, 100]; 100 disables it.
    _set_env(monkeypatch)
    assert Config.load(dotenv=False).size_confidence_cap == 85.0
    _set_env(monkeypatch, SIZE_CONFIDENCE_CAP="100")  # 100 disables the cap
    assert Config.load(dotenv=False).size_confidence_cap == 100.0
    _set_env(monkeypatch, SIZE_CONFIDENCE_CAP="50")  # below ENTRY_THRESHOLD (60) is invalid
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)
    _set_env(monkeypatch, SIZE_CONFIDENCE_CAP="120")  # > 100 is invalid
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_missing_secret_raises(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.delenv("ALPACA_KEY_ID", raising=False)
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_trail_default_is_tighter_than_the_stop(monkeypatch):
    """IMP-018: a trail at or wider than the stop can never lock in profit, because
    price must run a full stop-width before the ratchet clears breakeven. The old
    2%/2% pairing made the trail inert — 2 of 219 live trades ever exited on it."""
    _set_env(monkeypatch)
    cfg = Config.load(dotenv=False)
    assert cfg.trail_percent == 0.0125
    assert cfg.trail_percent < cfg.stop_loss
    assert not cfg.trail_is_inert


def test_trail_is_inert_when_it_matches_the_stop(monkeypatch):
    _set_env(monkeypatch, TRAIL_PERCENT="0.02", STOP_LOSS="0.02")
    assert Config.load(dotenv=False).trail_is_inert


def test_trail_is_inert_when_wider_than_the_stop(monkeypatch):
    _set_env(monkeypatch, TRAIL_PERCENT="0.03", STOP_LOSS="0.02")
    assert Config.load(dotenv=False).trail_is_inert


def test_entry_start_defaults_to_ten_am(monkeypatch):
    """IMP-017: the opening-range blackout is on by default."""
    _set_env(monkeypatch)
    cfg = Config.load(dotenv=False)
    assert (cfg.entry_start.hour, cfg.entry_start.minute) == (10, 0)


def test_entry_start_is_tunable(monkeypatch):
    _set_env(monkeypatch, ENTRY_START="09:50")
    cfg = Config.load(dotenv=False)
    assert (cfg.entry_start.hour, cfg.entry_start.minute) == (9, 50)


def test_rejects_entry_start_before_the_open(monkeypatch):
    _set_env(monkeypatch, ENTRY_START="09:00")  # earlier than MARKET_OPEN
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_rejects_entry_start_at_or_after_the_close(monkeypatch):
    _set_env(monkeypatch, ENTRY_START="16:00")  # would block the whole session
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


def test_two_stage_trail_may_not_widen(monkeypatch):
    # Hard invariant (IMP-021): stage two may only tighten. A wider second stage is a
    # stealth stop-widening, the direction the 2026-07-31 A/B refuted decisively.
    _set_env(monkeypatch, TRAIL_PERCENT="0.0125", TRAIL_PERCENT_TIGHT="0.02",
             TRAIL_TIGHTEN_AFTER="0.01")
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


def test_two_stage_trail_accepts_tighter_second_stage(monkeypatch):
    _set_env(monkeypatch, TRAIL_PERCENT="0.0125", TRAIL_PERCENT_TIGHT="0.010",
             TRAIL_TIGHTEN_AFTER="0.010")
    cfg = Config.load(dotenv=False)
    assert cfg.trail_percent_tight == 0.010
    assert cfg.trail_tighten_after == 0.010


def test_trail_tighten_after_must_be_fraction(monkeypatch):
    _set_env(monkeypatch, TRAIL_TIGHTEN_AFTER="1.5")
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)


# --- IMP-022: market-regime filter symbol ---------------------------------------


def test_market_filter_symbol_defaults_to_qqq(monkeypatch):
    _set_env(monkeypatch)
    assert Config.load(dotenv=False).market_filter_symbol == "QQQ"


def test_market_filter_symbol_is_normalised(monkeypatch):
    _set_env(monkeypatch, MARKET_FILTER_SYMBOL="  spy ")
    assert Config.load(dotenv=False).market_filter_symbol == "SPY"


def test_market_filter_symbol_empty_disables_the_gate(monkeypatch):
    _set_env(monkeypatch, MARKET_FILTER_SYMBOL="")
    assert Config.load(dotenv=False).market_filter_symbol == ""


def test_market_filter_symbol_rejects_a_non_ticker(monkeypatch):
    """Catch a typo'd/quoted value at startup rather than failing open all session."""
    _set_env(monkeypatch, MARKET_FILTER_SYMBOL="QQQ,SPY")
    with pytest.raises(ConfigError):
        Config.load(dotenv=False)
