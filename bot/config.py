"""Configuration layer.

All tunables and secrets are read from environment variables (loaded from a local
``.env`` in development via python-dotenv; supplied directly by the environment on
the VPS). ``Config.load()`` parses, validates, and freezes the values once at
startup so the rest of the bot can depend on typed, sane settings.

Secrets are never included in ``__repr__`` / logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional at runtime (env may be set directly)
    def load_dotenv(*_args, **_kwargs) -> bool:  # type: ignore[misc]
        return False

EASTERN = ZoneInfo("America/New_York")


class ConfigError(RuntimeError):
    """Raised when required config is missing or a value is out of range."""


# --- typed env-var readers -------------------------------------------------

def _req(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise ConfigError(f"Required environment variable {name} is missing or empty.")
    return val


def _str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ConfigError(f"{name} must be an integer, got {raw!r}.") from e


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as e:
        raise ConfigError(f"{name} must be a number, got {raw!r}.") from e


def _csv(name: str, default: str) -> tuple[str, ...]:
    raw = os.environ.get(name, default)
    items = tuple(s.strip().upper() for s in raw.split(",") if s.strip())
    if not items:
        raise ConfigError(f"{name} must list at least one symbol.")
    return items


def _hhmm(name: str, default: str) -> time:
    raw = os.environ.get(name, default).strip()
    try:
        hh, mm = (int(p) for p in raw.split(":", 1))
        return time(hour=hh, minute=mm, tzinfo=EASTERN)
    except (ValueError, TypeError) as e:
        raise ConfigError(f"{name} must be HH:MM, got {raw!r}.") from e


@dataclass(frozen=True)
class Config:
    # Secrets
    alpaca_key_id: str = field(repr=False)
    alpaca_secret: str = field(repr=False)
    telegram_token: str = field(repr=False)
    telegram_chat_id: str = field(repr=False)

    # Alpaca
    alpaca_base_url: str
    alpaca_data_feed: str

    # Strategy
    watchlist: tuple[str, ...]
    candle_interval: str
    fast_ma_period: int
    slow_ma_period: int
    trend_ma_period: int
    rsi_period: int
    entry_threshold: float

    # Sizing
    min_alloc: float
    max_alloc: float
    max_risk_per_trade: float

    # Bracket
    stop_loss: float
    take_profit: float

    # Market hours (US Eastern)
    market_open: time
    market_close: time

    # Infra
    sqlserver_conn: str = field(repr=False)
    log_level: str = "INFO"

    @classmethod
    def load(cls, *, dotenv: bool = True) -> Config:
        """Build a Config from the environment, validating as we go."""
        if dotenv:
            load_dotenv()  # no-op if .env absent or dotenv not installed

        cfg = cls(
            alpaca_key_id=_req("ALPACA_KEY_ID"),
            alpaca_secret=_req("ALPACA_SECRET"),
            telegram_token=_req("TELEGRAM_TOKEN"),
            telegram_chat_id=_req("TELEGRAM_CHAT_ID"),
            alpaca_base_url=_str("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
            alpaca_data_feed=_str("ALPACA_DATA_FEED", "iex"),
            watchlist=_csv("WATCHLIST", "NFLX,BIRD,WPM"),
            candle_interval=_str("CANDLE_INTERVAL", "1m"),
            fast_ma_period=_int("FAST_MA_PERIOD", 9),
            slow_ma_period=_int("SLOW_MA_PERIOD", 21),
            trend_ma_period=_int("TREND_MA_PERIOD", 50),
            rsi_period=_int("RSI_PERIOD", 14),
            entry_threshold=_float("ENTRY_THRESHOLD", 60.0),
            min_alloc=_float("MIN_ALLOC", 0.10),
            max_alloc=_float("MAX_ALLOC", 0.40),
            max_risk_per_trade=_float("MAX_RISK_PER_TRADE", 0.02),
            stop_loss=_float("STOP_LOSS", 0.02),
            take_profit=_float("TAKE_PROFIT", 0.04),
            market_open=_hhmm("MARKET_OPEN", "09:30"),
            market_close=_hhmm("MARKET_CLOSE", "16:00"),
            sqlserver_conn=_str("SQLSERVER_CONN", ""),
            log_level=_str("LOG_LEVEL", "INFO").upper(),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if "paper" not in self.alpaca_base_url:
            # Hard guard: this bot is paper-only by design (see CLAUDE.md).
            raise ConfigError(
                f"ALPACA_BASE_URL must be the paper endpoint, got {self.alpaca_base_url!r}."
            )
        if not 0 < self.fast_ma_period < self.slow_ma_period:
            raise ConfigError("Require 0 < FAST_MA_PERIOD < SLOW_MA_PERIOD.")
        if self.trend_ma_period <= self.slow_ma_period:
            raise ConfigError("TREND_MA_PERIOD should be > SLOW_MA_PERIOD.")
        if not 0 <= self.entry_threshold <= 100:
            raise ConfigError("ENTRY_THRESHOLD must be in [0, 100].")
        if not 0 < self.min_alloc <= self.max_alloc <= 1:
            raise ConfigError("Require 0 < MIN_ALLOC <= MAX_ALLOC <= 1.")
        if not 0 < self.max_risk_per_trade <= 1:
            raise ConfigError("MAX_RISK_PER_TRADE must be in (0, 1].")
        for fld in ("stop_loss", "take_profit"):
            v = getattr(self, fld)
            if not 0 < v < 1:
                raise ConfigError(f"{fld.upper()} must be a fraction in (0, 1).")
        if self.rsi_period <= 1:
            raise ConfigError("RSI_PERIOD must be > 1.")
