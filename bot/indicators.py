"""Indicator engine (Phase 2 → generalized in Phase 3).

Turns the stream of *closed* candles from :class:`~bot.candles.CandleAggregator`
into the technical indicators the signal/confidence scorer (Phase 3) needs. The
strategy runs **two** engines, one per timeframe:

- a 1-minute **trigger** engine: an 8/10/20 EMA *ribbon* plus RSI(14), trailing
  average volume, and ATR(14) for the volatility sub-score,
- a 5-minute **gate** engine: a 21/34/55 EMA *ribbon* only.

Design notes / invariants:
- **Closed candles only.** ``update`` is meant to be fed each *closed* candle
  (wire it via ``MarketDataClient(on_candle=..., on_long_candle=...)``). Acting on
  the still-forming candle would repaint — see CLAUDE.md.
- **Incremental, path-dependent.** EMAs, RSI, and ATR are carried forward from the
  series' inception rather than recomputed over a sliding window, so their values
  do not drift as old bars age out of the aggregator's rolling window. Each
  indicator stays ``None`` until it has seen enough candles to seed.
- **Ribbon = stacked AND sloping.** A ribbon is bullish only when ordered
  (``fast > mid > slow``) *and* sloping up; ``RibbonSnapshot`` exposes both the
  state helpers and a *fresh-cross* detector (the entry trigger).
- **Trailing volume baseline.** ``avg_volume`` is the mean of the *preceding*
  ``volume_period`` candles (the current bar is excluded), so a confirmation ratio
  ``volume / avg_volume`` compares the new bar against its recent history.
- Pure / no I/O. State is per symbol; symbols are independent.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from bot.candles import Candle
from bot.config import Config

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


class _Atr:
    """Wilder's ATR(period) from (high, low, close). ``None`` until seeded.

    The first bar has no prior close, so its true range is just ``high - low``;
    subsequent bars use the full true-range definition. Seeds from the simple
    average of the first ``period`` true ranges, then Wilder-smooths.
    """

    __slots__ = ("period", "_prev_close", "_seed", "value")

    def __init__(self, period: int) -> None:
        if period <= 0:
            raise ValueError("ATR period must be positive")
        self.period = period
        self._prev_close: float | None = None
        self._seed: list[float] = []
        self.value: float | None = None

    def update(self, high: float, low: float, close: float) -> float | None:
        if self._prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self._prev_close), abs(low - self._prev_close))
        self._prev_close = close

        if self.value is None:
            self._seed.append(tr)
            if len(self._seed) == self.period:
                self.value = sum(self._seed) / self.period
        else:
            self.value = (self.value * (self.period - 1) + tr) / self.period
        return self.value


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


# --- ribbon ----------------------------------------------------------------

_Triple = tuple[float | None, float | None, float | None]
_NONE3: _Triple = (None, None, None)


class Ribbon:
    """Three EMAs (fast < mid < slow periods) carried forward together.

    Tracks the current and previous closed-candle values so callers can test for
    a *fresh cross* and rising slope from a single snapshot.
    """

    __slots__ = ("_emas", "values", "prev")

    def __init__(self, periods: tuple[int, int, int]) -> None:
        fast, mid, slow = periods
        if not 0 < fast < mid < slow:
            raise ValueError("ribbon periods must be increasing positive (fast<mid<slow)")
        self._emas = (_Ema(fast), _Ema(mid), _Ema(slow))
        self.values: _Triple = _NONE3
        self.prev: _Triple = _NONE3

    def update(self, price: float) -> _Triple:
        self.prev = self.values
        self.values = tuple(e.update(price) for e in self._emas)  # type: ignore[assignment]
        return self.values


# --- snapshot --------------------------------------------------------------


@dataclass(frozen=True)
class RibbonSnapshot:
    """Indicator values for one symbol as of one closed candle on one timeframe.

    ``ribbon`` / ``prev_ribbon`` are ``(fast, mid, slow)`` EMA tuples (the current
    and previous closed candle). ``rsi`` / ``avg_volume`` / ``atr`` are only
    populated on the trigger (1-min) timeframe; on the gate timeframe they are
    ``None``. Fields are ``None`` until they have enough history to seed.
    """

    symbol: str
    candle_start: datetime
    interval_seconds: int
    close: float
    volume: float
    ribbon: _Triple
    prev_ribbon: _Triple
    rsi: float | None
    prev_rsi: float | None
    avg_volume: float | None
    atr: float | None

    @property
    def fast(self) -> float | None:
        return self.ribbon[0]

    @property
    def mid(self) -> float | None:
        return self.ribbon[1]

    @property
    def slow(self) -> float | None:
        return self.ribbon[2]

    @property
    def ribbon_ready(self) -> bool:
        """True once all three EMAs (this candle and the previous) are seeded."""
        return None not in self.ribbon and None not in self.prev_ribbon

    @property
    def stacked(self) -> bool:
        """Ribbon ordered bullishly: ``fast > mid > slow``."""
        if None in self.ribbon:
            return False
        f, m, s = self.ribbon
        return f > m > s  # type: ignore[operator]

    @property
    def fast_rising(self) -> bool:
        """The fast EMA is above its previous closed-candle value."""
        f, pf = self.ribbon[0], self.prev_ribbon[0]
        return f is not None and pf is not None and f > pf

    @property
    def sloping_up(self) -> bool:
        """Every EMA is above its previous value (the whole ribbon rising)."""
        if not self.ribbon_ready:
            return False
        pairs = zip(self.ribbon, self.prev_ribbon, strict=True)
        return all(c > p for c, p in pairs)  # type: ignore[operator]

    @property
    def bullish(self) -> bool:
        """Stacked *and* sloping up — the strong-ribbon condition (CLAUDE.md)."""
        return self.stacked and self.sloping_up

    @property
    def gate_open(self) -> bool:
        """Gate state: stacked bullishly with the fast EMA rising (summary.md)."""
        return self.stacked and self.fast_rising

    @property
    def fresh_cross(self) -> bool:
        """A fresh bullish cross of fast over mid, with the full stack above slow.

        ``prev_fast <= prev_mid`` (was not yet bullish) and now ``fast > mid``,
        and the whole ribbon is stacked above the slow anchor. The ``prev`` term
        makes this fire **once** per cross, not every candle it stays stacked.
        """
        if not self.ribbon_ready:
            return False
        f, m, s = self.ribbon
        pf, pm, _ps = self.prev_ribbon
        return pf <= pm and f > m and f > s and m > s  # type: ignore[operator]

    @property
    def bearish_cross(self) -> bool:
        """A fresh bearish cross of the fast EMA *below* the mid EMA — the Phase 5
        early-exit trigger (risk manager).

        Mirror of :attr:`fresh_cross`: ``prev_fast >= prev_mid`` (was not yet
        bearish) and now ``fast < mid``. Unlike the entry, the exit deliberately
        does **not** require the whole ribbon to invert (``fast < mid < slow``):
        the first fast/mid inversion is the earliest reversal warning, and bailing
        on it is the point of an *early* exit. Fires once per cross, not every
        candle the fast stays below the mid.
        """
        if not self.ribbon_ready:
            return False
        f, m, _s = self.ribbon
        pf, pm, _ps = self.prev_ribbon
        return pf >= pm and f < m  # type: ignore[operator]


# --- per-symbol state + engine ---------------------------------------------


class _RibbonState:
    __slots__ = ("ribbon", "rsi", "volume", "atr", "last")

    def __init__(
        self,
        periods: tuple[int, int, int],
        *,
        rsi_period: int,
        volume_period: int,
        atr_period: int,
    ) -> None:
        self.ribbon = Ribbon(periods)
        self.rsi = _Rsi(rsi_period) if rsi_period else None
        self.volume = _TrailingMean(volume_period) if volume_period else None
        self.atr = _Atr(atr_period) if atr_period else None
        self.last: RibbonSnapshot | None = None

    def update(self, candle: Candle, interval_seconds: int) -> RibbonSnapshot:
        prev = self.last
        avg_volume = self.volume.current() if self.volume else None  # preceding bars only
        if self.volume:
            self.volume.push(candle.volume)

        ribbon_vals = self.ribbon.update(candle.close)
        snap = RibbonSnapshot(
            symbol=candle.symbol,
            candle_start=candle.start,
            interval_seconds=interval_seconds,
            close=candle.close,
            volume=candle.volume,
            ribbon=ribbon_vals,
            prev_ribbon=self.ribbon.prev,
            rsi=self.rsi.update(candle.close) if self.rsi else None,
            prev_rsi=prev.rsi if prev else None,
            avg_volume=avg_volume,
            atr=self.atr.update(candle.high, candle.low, candle.close) if self.atr else None,
        )
        self.last = snap
        return snap


class RibbonEngine:
    """Maintains one EMA ribbon (plus optional RSI/volume/ATR) per symbol over a
    single timeframe. Feed it each closed candle for that timeframe."""

    def __init__(
        self,
        periods: tuple[int, int, int],
        *,
        rsi_period: int = 0,
        volume_period: int = 0,
        atr_period: int = 0,
        interval_seconds: int = 60,
    ) -> None:
        Ribbon(periods)  # validate periods eagerly
        self._periods = periods
        self._rsi = rsi_period
        self._volume = volume_period
        self._atr = atr_period
        self._interval = interval_seconds
        self._states: dict[str, _RibbonState] = {}

    @classmethod
    def trigger(cls, cfg: Config) -> RibbonEngine:
        """The 1-min trigger engine: short ribbon + RSI + volume + ATR."""
        return cls(
            cfg.short_ma_periods,
            rsi_period=cfg.rsi_period,
            volume_period=cfg.volume_ma_period,
            atr_period=cfg.atr_period,
            interval_seconds=cfg.interval_seconds,
        )

    @classmethod
    def gate(cls, cfg: Config) -> RibbonEngine:
        """The 5-min gate engine: long ribbon only (no RSI/volume/ATR)."""
        return cls(cfg.long_ma_periods, interval_seconds=cfg.long_interval_seconds)

    def update(self, candle: Candle) -> RibbonSnapshot:
        """Fold one closed candle into ``candle.symbol``'s ribbon."""
        state = self._states.get(candle.symbol)
        if state is None:
            state = _RibbonState(
                self._periods,
                rsi_period=self._rsi,
                volume_period=self._volume,
                atr_period=self._atr,
            )
            self._states[candle.symbol] = state
        return state.update(candle, self._interval)

    def snapshot(self, symbol: str) -> RibbonSnapshot | None:
        """The most recent snapshot for ``symbol``, or ``None`` if never updated."""
        state = self._states.get(symbol)
        return state.last if state is not None else None


# A convenience type alias for code that wires the engine as an on_candle sink.
OnSnapshot = Callable[[RibbonSnapshot], None]
