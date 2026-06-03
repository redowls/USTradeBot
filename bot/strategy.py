"""Strategy state machine (Phase 3).

A per-symbol deterministic state machine over ``WAITING → EVALUATING → EXECUTING
→ MANAGING`` (CLAUDE.md). It owns the two ribbon engines and drives entry
evaluation on each closed candle:

- ``on_long_candle`` folds a closed 5-min candle into the *gate* engine and stores
  the latest gate snapshot per symbol.
- ``on_short_candle`` folds a closed 1-min candle into the *trigger* engine, then
  — if the market is open and indicators are seeded — evaluates the gate+trigger
  rule and the confidence score. A qualifying entry emits a :class:`TradeSignal`.

Phase 3 stops at the signal: there is no order executor yet, so the machine cycles
``WAITING ↔ EVALUATING`` and reports entry signals. The ``EXECUTING`` and
``MANAGING`` states exist in the enum and transition table; Phase 4 (executor) and
Phase 5 (risk manager) will drive them. The ``on_signal`` callback is where Phase 7
will hook Telegram alerts.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from bot.candles import Candle
from bot.config import Config
from bot.indicators import RibbonEngine, RibbonSnapshot
from bot.signals import (
    ConfidenceBreakdown,
    EntryDecision,
    ScoreWeights,
    evaluate_entry,
    market_is_open,
)

log = logging.getLogger("ustradebot.strategy")


class BotState(StrEnum):
    WAITING = "WAITING"  # market closed, warming up, or idle
    EVALUATING = "EVALUATING"  # market open, scoring each closed 1-min candle
    EXECUTING = "EXECUTING"  # order submission in flight (Phase 4)
    MANAGING = "MANAGING"  # position open, risk-managed (Phase 4/5)


@dataclass(frozen=True)
class TradeSignal:
    """A qualifying entry: confidence cleared the threshold on a closed candle."""

    symbol: str
    candle_start: datetime
    close: float
    confidence: ConfidenceBreakdown
    decision: EntryDecision


OnSignal = Callable[[TradeSignal], None]


class StrategyEngine:
    """Per-symbol state machine wiring the trigger + gate ribbons to entries."""

    def __init__(
        self,
        cfg: Config,
        *,
        on_signal: OnSignal | None = None,
        weights: ScoreWeights | None = None,
        trigger_engine: RibbonEngine | None = None,
        gate_engine: RibbonEngine | None = None,
    ) -> None:
        self._cfg = cfg
        self._on_signal = on_signal
        self._weights = weights or ScoreWeights()
        self._trigger = trigger_engine or RibbonEngine.trigger(cfg)
        self._gate = gate_engine or RibbonEngine.gate(cfg)
        self._state: dict[str, BotState] = {}
        self._gate_snap: dict[str, RibbonSnapshot] = {}

    def state(self, symbol: str) -> BotState:
        return self._state.get(symbol, BotState.WAITING)

    def _set(self, symbol: str, state: BotState) -> None:
        if self._state.get(symbol) is not state:
            log.debug("%s state %s -> %s", symbol, self.state(symbol).value, state.value)
        self._state[symbol] = state

    # --- candle sinks ------------------------------------------------------

    def on_long_candle(self, candle: Candle) -> None:
        """Refresh the gate ribbon from a closed higher-timeframe candle."""
        self._gate_snap[candle.symbol] = self._gate.update(candle)

    def on_short_candle(self, candle: Candle) -> TradeSignal | None:
        """Evaluate one closed trigger-timeframe candle; emit a signal on entry."""
        trigger = self._trigger.update(candle)
        symbol = candle.symbol

        # Phase 4/5 own these states; ingestion does not re-evaluate while a
        # position is being opened or managed.
        if self.state(symbol) in (BotState.EXECUTING, BotState.MANAGING):
            return None

        if not market_is_open(candle.start, self._cfg.market_open, self._cfg.market_close):
            self._set(symbol, BotState.WAITING)
            return None

        if not trigger.ribbon_ready:
            self._set(symbol, BotState.WAITING)  # still warming up indicator history
            return None

        self._set(symbol, BotState.EVALUATING)
        decision = evaluate_entry(
            trigger,
            self._gate_snap.get(symbol),
            threshold=self._cfg.entry_threshold,
            weights=self._weights,
        )
        if not decision.enter:
            return None

        assert decision.confidence is not None  # enter implies a scored candidate
        signal = TradeSignal(
            symbol=symbol,
            candle_start=candle.start,
            close=trigger.close,
            confidence=decision.confidence,
            decision=decision,
        )
        log.info(
            "ENTRY %s @ %.4f confidence=%.1f (xo=%.2f trend=%.2f rsi=%.2f vol=%.2f vlt=%.2f)",
            symbol,
            trigger.close,
            decision.confidence.total,
            decision.confidence.crossover,
            decision.confidence.trend,
            decision.confidence.rsi,
            decision.confidence.volume,
            decision.confidence.volatility,
        )
        if self._on_signal is not None:
            try:
                self._on_signal(signal)
            except Exception:  # a downstream alert bug must not kill the strategy
                log.exception("on_signal callback failed for %s", symbol)
        # Phase 4 will submit the order and transition to EXECUTING here.
        return signal
