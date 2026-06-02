"""Indicator engine (Phase 2).

Turns the stream of *closed* candles from :class:`~bot.candles.CandleAggregator`
into the technical indicators the signal/confidence scorer (Phase 3) needs:

- fast / slow **EMAs** (9 / 21) — the crossover trigger,
- a **trend MA** (50, simple) — the higher-timeframe filter,
- **RSI** (14, Wilder smoothing) — momentum confirmation,
- **trailing average volume** — volume confirmation.

Design notes / invariants:
- **Closed candles only.** ``update`` is meant to be fed each *closed* candle
  (wire it to ``MarketDataClient(on_candle=...)``). Acting on the still-forming
  candle would repaint — see CLAUDE.md.
- **Incremental, path-dependent.** EMAs and RSI are carried forward from the
  series' inception rather than recomputed over a sliding window, so their values
  do not drift as old bars age out of the aggregator's rolling window. Each
  indicator stays ``None`` until it has seen enough candles to seed (EMA/MA seed
  from a simple average of their first ``period`` closes; RSI seeds from the first
  ``period`` price changes, i.e. ``period + 1`` closes).
- **Trailing volume baseline.** ``avg_volume`` is the mean of the *preceding*
  ``volume_period`` candles (the current bar is excluded), so a confirmation ratio
  ``volume / avg_volume`` compares the new bar against its recent history rather
  than diluting it with itself.
- Pure / no I/O. State is per symbol; symbols are independent.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from bot.candles import Candle
from bot.config import Config

DEFAULT_VOLUME_PERIOD = 20


# --- incremental primitives ------------------------------------------------


class _Ema:
    """Exponential moving average, seeded from the SMA of its first ``period``
    values, then carried forward with ``k = 2 / (period + 1)``."""

    __slots__ = ("period", "_k", "_seed", "value")

    def __init__(self, period: int) -> None:
        if period <= 0:
            raise ValueError("EMA period must be positive")
        self.period = period
        self._k = 2.0 / (period + 1.0)
        self._seed: list[float] = []
        self.value: float | None = None

    def update(self, price: float) -> float | None:
        if self.value is None:
            self._seed.append(price)
            if len(self._seed) == self.period:
                self.value = sum(self._seed) / self.period
        else:
            self.value = price * self._k + self.value * (1.0 - self._k)
        return self.value


class _Sma:
    """Simple moving average over the last ``period`` values; ``None`` until full."""

    __slots__ = ("period", "_buf")

    def __init__(self, period: int) -> None:
        if period <= 0:
            raise ValueError("SMA period must be positive")
        self.period = period
        self._buf: deque[float] = deque(maxlen=period)

    def update(self, value: float) -> float | None:
        self._buf.append(value)
        if len(self._buf) < self.period:
            return None
        return sum(self._buf) / self.period


class _Rsi:
    """Wilder's RSI(period). ``None`` until ``period`` price changes are seen."""

    __slots__ = (
        "period",
        "_prev_close",
        "_seed_gains",
        "_seed_losses",
        "avg_gain",
        "avg_loss",
        "value",
    )

    def __init__(self, period: int) -> None:
        if period <= 1:
            raise ValueError("RSI period must be > 1")
        self.period = period
        self._prev_close: float | None = None
        self._seed_gains: list[float] = []
        self._seed_losses: list[float] = []
        self.avg_gain: float | None = None
        self.avg_loss: float | None = None
        self.value: float | None = None

    def update(self, close: float) -> float | None:
        if self._prev_close is None:
            self._prev_close = close
            return None  # no change to measure yet

        change = close - self._prev_close
        self._prev_close = close
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0

        if self.avg_gain is None:
            self._seed_gains.append(gain)
            self._seed_losses.append(loss)
            if len(self._seed_gains) == self.period:
                self.avg_gain = sum(self._seed_gains) / self.period
                self.avg_loss = sum(self._seed_losses) / self.period
                self.value = self._compute()
            return self.value

        # Wilder smoothing.
        n = self.period
        self.avg_gain = (self.avg_gain * (n - 1) + gain) / n
        self.avg_loss = (self.avg_loss * (n - 1) + loss) / n
        self.value = self._compute()
        return self.value

    def _compute(self) -> float:
        if self.avg_loss == 0:
            return 100.0  # no losses over the window -> maximally overbought
        rs = self.avg_gain / self.avg_loss
        return 100.0 - 100.0 / (1.0 + rs)


class _TrailingMean:
    """Mean of the most recent ``period`` pushed values, read *before* the current
    value is added so it reflects the preceding bars only."""

    __slots__ = ("period", "_buf")

    def __init__(self, period: int) -> None:
        if period <= 0:
            raise ValueError("volume period must be positive")
        self.period = period
        self._buf: deque[float] = deque(maxlen=period)

    def current(self) -> float | None:
        if len(self._buf) < self.period:
            return None
        return sum(self._buf) / self.period

    def push(self, value: float) -> None:
        self._buf.append(value)


# --- snapshot --------------------------------------------------------------


@dataclass(frozen=True)
class IndicatorSnapshot:
    """Indicator values as of one closed candle. ``None`` fields are not yet seeded.

    ``prev_fast_ema`` / ``prev_slow_ema`` are the EMA values from the *previous*
    closed candle so the Phase 3 scorer can detect a *fresh* cross
    (``prev_fast <= prev_slow and fast > slow``) from a single snapshot — see the
    "crossover = the cross, not the state" invariant in CLAUDE.md.
    """

    symbol: str
    candle_start: datetime
    close: float
    volume: float
    fast_ema: float | None
    slow_ema: float | None
    trend_ma: float | None
    rsi: float | None
    avg_volume: float | None
    prev_fast_ema: float | None
    prev_slow_ema: float | None

    @property
    def ready(self) -> bool:
        """True once every indicator has enough history to produce a value."""
        return None not in (
            self.fast_ema,
            self.slow_ema,
            self.trend_ma,
            self.rsi,
            self.avg_volume,
        )


# --- per-symbol state + engine ---------------------------------------------


class _SymbolState:
    __slots__ = ("fast", "slow", "trend", "rsi", "volume", "last")

    def __init__(self, *, fast: int, slow: int, trend: int, rsi: int, volume: int) -> None:
        self.fast = _Ema(fast)
        self.slow = _Ema(slow)
        self.trend = _Sma(trend)
        self.rsi = _Rsi(rsi)
        self.volume = _TrailingMean(volume)
        self.last: IndicatorSnapshot | None = None

    def update(self, candle: Candle) -> IndicatorSnapshot:
        prev = self.last
        avg_volume = self.volume.current()  # preceding bars, before adding this one
        self.volume.push(candle.volume)

        snap = IndicatorSnapshot(
            symbol=candle.symbol,
            candle_start=candle.start,
            close=candle.close,
            volume=candle.volume,
            fast_ema=self.fast.update(candle.close),
            slow_ema=self.slow.update(candle.close),
            trend_ma=self.trend.update(candle.close),
            rsi=self.rsi.update(candle.close),
            avg_volume=avg_volume,
            prev_fast_ema=prev.fast_ema if prev else None,
            prev_slow_ema=prev.slow_ema if prev else None,
        )
        self.last = snap
        return snap


class IndicatorEngine:
    """Maintains indicator state per symbol; ``update`` it with each closed candle."""

    def __init__(
        self,
        *,
        fast_period: int = 9,
        slow_period: int = 21,
        trend_period: int = 50,
        rsi_period: int = 14,
        volume_period: int = DEFAULT_VOLUME_PERIOD,
    ) -> None:
        if not 0 < fast_period < slow_period:
            raise ValueError("require 0 < fast_period < slow_period")
        if trend_period <= 0:
            raise ValueError("trend_period must be positive")
        self._fast = fast_period
        self._slow = slow_period
        self._trend = trend_period
        self._rsi = rsi_period
        self._volume = volume_period
        self._states: dict[str, _SymbolState] = {}

    @classmethod
    def from_config(cls, cfg: Config) -> IndicatorEngine:
        return cls(
            fast_period=cfg.fast_ma_period,
            slow_period=cfg.slow_ma_period,
            trend_period=cfg.trend_ma_period,
            rsi_period=cfg.rsi_period,
            volume_period=cfg.volume_ma_period,
        )

    def update(self, candle: Candle) -> IndicatorSnapshot:
        """Fold one closed candle into ``candle.symbol``'s indicators."""
        state = self._states.get(candle.symbol)
        if state is None:
            state = _SymbolState(
                fast=self._fast,
                slow=self._slow,
                trend=self._trend,
                rsi=self._rsi,
                volume=self._volume,
            )
            self._states[candle.symbol] = state
        return state.update(candle)

    def snapshot(self, symbol: str) -> IndicatorSnapshot | None:
        """The most recent snapshot for ``symbol``, or ``None`` if never updated."""
        state = self._states.get(symbol)
        return state.last if state is not None else None


# A convenience type alias for code that wires the engine as an on_candle sink.
OnSnapshot = Callable[[IndicatorSnapshot], None]
