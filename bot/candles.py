"""Candle aggregator.

Rolls a stream of trade ticks into fixed-interval OHLCV candles per symbol and
keeps a bounded rolling window of *closed* candles for the indicator engine
(Phase 2) to read.

Design notes / invariants:
- A candle is keyed by its interval-aligned start time (UTC). The candle for
  minute ``M`` covers ``[M, M+interval)``.
- ``add_trade`` closes the previous candle and opens a new one when a trade
  arrives in a later bucket. Late/out-of-order trades (older than the current
  open candle) are dropped — we never rewrite an already-closed candle.
- ``flush(now)`` closes any open candle whose interval has fully elapsed before
  ``now``. Callers drive this from market activity (the wall clock of incoming
  ticks) so a quiet symbol's last candle still closes once a later tick proves
  the minute is over.
- The still-forming candle is never exposed as closed — see the "closed candles
  only" invariant in CLAUDE.md. ``current()`` returns it read-only for
  inspection/logging.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_WINDOW = 200  # enough closed candles for a 50-period trend MA + headroom


@dataclass(frozen=True)
class Candle:
    """One closed OHLCV bar covering ``[start, start + interval)`` (UTC)."""

    symbol: str
    start: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int


class _Builder:
    """Mutable accumulator for the candle currently being formed."""

    __slots__ = ("start", "open", "high", "low", "close", "volume", "trades")

    def __init__(self, start: datetime, price: float, size: float) -> None:
        self.start = start
        self.open = price
        self.high = price
        self.low = price
        self.close = price
        self.volume = size
        self.trades = 1

    def update(self, price: float, size: float) -> None:
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += size
        self.trades += 1

    def finish(self, symbol: str) -> Candle:
        return Candle(
            symbol=symbol,
            start=self.start,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            trades=self.trades,
        )


class CandleAggregator:
    """Aggregates trades into closed candles, one rolling window per symbol."""

    def __init__(
        self,
        *,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        window: int = DEFAULT_WINDOW,
        on_close: Callable[[Candle], None] | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if window <= 0:
            raise ValueError("window must be positive")
        self._interval = interval_seconds
        self._window = window
        self._on_close = on_close
        self._building: dict[str, _Builder] = {}
        self._closed: dict[str, deque[Candle]] = {}

    # --- bucketing ---------------------------------------------------------

    def _floor(self, ts: datetime) -> datetime:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        epoch = ts.timestamp()
        aligned = math.floor(epoch / self._interval) * self._interval
        return datetime.fromtimestamp(aligned, tz=UTC)

    # --- ingestion ---------------------------------------------------------

    def add_trade(self, symbol: str, ts: datetime, price: float, size: float) -> None:
        """Fold one trade into ``symbol``'s candle, rolling over on a new bucket."""
        bucket = self._floor(ts)
        builder = self._building.get(symbol)

        if builder is None:
            self._building[symbol] = _Builder(bucket, price, size)
            return

        if bucket == builder.start:
            builder.update(price, size)
        elif bucket > builder.start:
            self._close(symbol)
            self._building[symbol] = _Builder(bucket, price, size)
        # bucket < builder.start: late tick for an already-closed candle — drop it.

    def flush(self, now: datetime) -> None:
        """Close any open candle whose interval has fully elapsed before ``now``."""
        now_floor = self._floor(now)
        for symbol, builder in list(self._building.items()):
            if builder.start < now_floor:
                self._close(symbol)

    def _close(self, symbol: str) -> None:
        builder = self._building.pop(symbol, None)
        if builder is None:
            return
        candle = builder.finish(symbol)
        self._closed.setdefault(symbol, deque(maxlen=self._window)).append(candle)
        if self._on_close is not None:
            self._on_close(candle)

    # --- reads -------------------------------------------------------------

    def closed_candles(self, symbol: str) -> tuple[Candle, ...]:
        """Closed candles for ``symbol``, oldest first (bounded by ``window``)."""
        return tuple(self._closed.get(symbol, ()))

    def latest_closed(self, symbol: str) -> Candle | None:
        bars = self._closed.get(symbol)
        return bars[-1] if bars else None

    def current(self, symbol: str) -> Candle | None:
        """The still-forming candle as a snapshot (NOT a closed bar), or None."""
        builder = self._building.get(symbol)
        return builder.finish(symbol) if builder is not None else None
