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

_INTERVAL_UNITS = {"s": 1, "m": 60, "h": 3600}


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


def _periods3(name: str, default: str) -> tuple[int, int, int]:
    """Parse a 3-period EMA ribbon spec like ``8,10,20`` (fast, mid, slow)."""
    raw = os.environ.get(name, default)
    try:
        parts = tuple(int(p.strip()) for p in raw.split(",") if p.strip())
    except ValueError as e:
        raise ConfigError(f"{name} must be comma-separated integers, got {raw!r}.") from e
    if len(parts) != 3:
        raise ConfigError(f"{name} must list exactly 3 periods (fast,mid,slow), got {raw!r}.")
    return parts  # type: ignore[return-value]


def _interval_to_seconds(value: str, name: str) -> int:
    """Parse a candle interval like ``1m`` / ``5m`` / ``30s`` / ``1h`` into seconds."""
    v = value.strip().lower()
    if not v:
        raise ConfigError(f"{name} must not be empty.")
    if v[-1] in _INTERVAL_UNITS:
        num, mult = v[:-1], _INTERVAL_UNITS[v[-1]]
    else:
        num, mult = v, 1  # bare number = seconds
    try:
        n = int(num)
    except ValueError as e:
        raise ConfigError(f"{name} must look like '1m' / '5m' / '30s', got {value!r}.") from e
    if n <= 0:
        raise ConfigError(f"{name} must be positive, got {value!r}.")
    return n * mult


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

    # Strategy — dual-timeframe EMA ribbons (see summary.md)
    watchlist: tuple[str, ...]
    candle_interval: str  # trigger timeframe, e.g. "1m"
    long_candle_interval: str  # gate timeframe, e.g. "5m"
    interval_seconds: int  # candle_interval in seconds
    long_interval_seconds: int  # long_candle_interval in seconds
    short_ma_periods: tuple[int, int, int]  # 1-min trigger ribbon (fast/mid/slow EMA)
    long_ma_periods: tuple[int, int, int]  # 5-min gate ribbon (fast/mid/slow EMA)
    rsi_period: int
    volume_ma_period: int
    atr_period: int
    entry_threshold: float

    # Sizing
    sizing_model: str  # "A" (% of buying power) or "B" (risk budget)
    min_alloc: float
    max_alloc: float
    max_risk_per_trade: float

    # Bracket
    stop_loss: float
    take_profit: float
    # Trailing stop: once in profit, ratchet the broker stop up to
    # price * (1 - trail_percent) each candle (never down), so winners run and give
    # back at most this fraction from their peak instead of being cut on a 1-min wobble.
    trail_percent: float

    # Market hours (US Eastern)
    market_open: time
    market_close: time
    # Intraday flatten: close all positions and stop opening new ones within this
    # many minutes of the close, so nothing carries overnight (where the bracket's
    # DAY stop/target legs would otherwise expire and leave the position naked).
    flatten_before_close_min: int

    # Infra
    sqlserver_conn: str = field(repr=False)
    log_level: str = "INFO"

    @classmethod
    def load(cls, *, dotenv: bool = True) -> Config:
        """Build a Config from the environment, validating as we go."""
        if dotenv:
            load_dotenv()  # no-op if .env absent or dotenv not installed

        candle_interval = _str("CANDLE_INTERVAL", "1m")
        long_candle_interval = _str("LONG_CANDLE_INTERVAL", "5m")

        cfg = cls(
            alpaca_key_id=_req("ALPACA_KEY_ID"),
            alpaca_secret=_req("ALPACA_SECRET"),
            telegram_token=_req("TELEGRAM_TOKEN"),
            telegram_chat_id=_req("TELEGRAM_CHAT_ID"),
            alpaca_base_url=_str("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
            alpaca_data_feed=_str("ALPACA_DATA_FEED", "iex"),
            watchlist=_csv("WATCHLIST", "NFLX,BIRD,WPM"),
            candle_interval=candle_interval,
            long_candle_interval=long_candle_interval,
            interval_seconds=_interval_to_seconds(candle_interval, "CANDLE_INTERVAL"),
            long_interval_seconds=_interval_to_seconds(
                long_candle_interval, "LONG_CANDLE_INTERVAL"
            ),
            short_ma_periods=_periods3("SHORT_MA_PERIODS", "8,10,20"),
            long_ma_periods=_periods3("LONG_MA_PERIODS", "21,34,55"),
            rsi_period=_int("RSI_PERIOD", 14),
            volume_ma_period=_int("VOLUME_MA_PERIOD", 20),
            atr_period=_int("ATR_PERIOD", 14),
            entry_threshold=_float("ENTRY_THRESHOLD", 60.0),
            sizing_model=_str("SIZING_MODEL", "A").upper(),
            min_alloc=_float("MIN_ALLOC", 0.10),
            max_alloc=_float("MAX_ALLOC", 0.40),
            max_risk_per_trade=_float("MAX_RISK_PER_TRADE", 0.02),
            stop_loss=_float("STOP_LOSS", 0.02),
            take_profit=_float("TAKE_PROFIT", 0.04),
            trail_percent=_float("TRAIL_PERCENT", 0.02),
            market_open=_hhmm("MARKET_OPEN", "09:30"),
            market_close=_hhmm("MARKET_CLOSE", "16:00"),
            flatten_before_close_min=_int("FLATTEN_BEFORE_CLOSE_MIN", 5),
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
        for name, periods in (
            ("SHORT_MA_PERIODS", self.short_ma_periods),
            ("LONG_MA_PERIODS", self.long_ma_periods),
        ):
            a, b, c = periods
            if not 0 < a < b < c:
                raise ConfigError(
                    f"{name} must be three increasing positive periods (fast<mid<slow)."
                )
        if self.long_interval_seconds <= self.interval_seconds:
            raise ConfigError("LONG_CANDLE_INTERVAL must be longer than CANDLE_INTERVAL.")
        if not 0 <= self.entry_threshold <= 100:
            raise ConfigError("ENTRY_THRESHOLD must be in [0, 100].")
        if self.sizing_model not in ("A", "B"):
            raise ConfigError(f"SIZING_MODEL must be 'A' or 'B', got {self.sizing_model!r}.")
        if not 0 < self.min_alloc <= self.max_alloc <= 1:
            raise ConfigError("Require 0 < MIN_ALLOC <= MAX_ALLOC <= 1.")
        if not 0 < self.max_risk_per_trade <= 1:
            raise ConfigError("MAX_RISK_PER_TRADE must be in (0, 1].")
        for fld in ("stop_loss", "take_profit", "trail_percent"):
            v = getattr(self, fld)
            if not 0 < v < 1:
                raise ConfigError(f"{fld.upper()} must be a fraction in (0, 1).")
        if self.flatten_before_close_min < 0:
            raise ConfigError("FLATTEN_BEFORE_CLOSE_MIN must be >= 0.")
        if self.rsi_period <= 1:
            raise ConfigError("RSI_PERIOD must be > 1.")
        if self.volume_ma_period <= 0:
            raise ConfigError("VOLUME_MA_PERIOD must be positive.")
        if self.atr_period <= 0:
            raise ConfigError("ATR_PERIOD must be positive.")
