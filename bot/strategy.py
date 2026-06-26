"""Strategy state machine (Phase 3).

A per-symbol deterministic state machine over ``WAITING → EVALUATING → EXECUTING
→ MANAGING`` (CLAUDE.md). It owns the two ribbon engines and drives entry
evaluation on each closed candle:

- ``on_long_candle`` folds a closed 5-min candle into the *gate* engine and stores
  the latest gate snapshot per symbol.
- ``on_short_candle`` folds a closed 1-min candle into the *trigger* engine, then
  — if the market is open and indicators are seeded — evaluates the gate+trigger
  rule and the confidence score. A qualifying entry emits a :class:`TradeSignal`.

When an ``executor`` is wired (Phase 4), a qualifying entry drives ``EVALUATING →
EXECUTING → MANAGING``: the executor sizes the position and submits an Alpaca
bracket order; on success the symbol is held as MANAGING (the bracket's stop/target
live broker-side), and a skip/reject falls back to EVALUATING. Without an executor
the machine cycles ``WAITING ↔ EVALUATING`` and merely reports signals (Phase 3
behavior).

When a ``risk`` manager is wired (Phase 5), a ``MANAGING`` symbol is risk-managed
rather than re-evaluated: each candle ratchets its broker stop up under a rising
price (a trailing stop), so winners run and exit broker-side when that stop is hit.
The risk manager's feed-loss fail-safe also gates new entries — while the feed is
down the machine stays ``WAITING`` and opens nothing.
``on_signal`` fires on every qualifying entry (Phase 7 Telegram hook); the
executor's ``on_result`` and the risk manager's ``on_exit`` carry the fill/exit
details for Phase 6/7.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from bot.candles import Candle
from bot.config import EASTERN, Config
from bot.executor import ExecutionResult, OrderExecutor
from bot.indicators import RibbonEngine, RibbonSnapshot
from bot.risk import RiskManager
from bot.signals import (
    ConfidenceBreakdown,
    EntryDecision,
    ScoreWeights,
    evaluate_entry,
    in_close_window,
    market_is_open,
    minutes_until_close,
)

log = logging.getLogger("ustradebot.strategy")

# When the EOD flatten still can't close a position this close (minutes) to the
# session close, there's no retry runway left before the DAY bracket legs expire
# and the position carries NAKED overnight — escalate once so a human can flatten
# it manually. 2026-06-16 (IMP-002): Alpaca returned persistent 504 Gateway
# Timeouts through all 12 close retries on 4 names (AAPL/ABNB/BABA/GOOG); the
# flatten failed silently (journald ERROR only, no Telegram) and the positions
# carried naked overnight. The threshold spans the final ~2 candles so a thin
# close (no further candle) is still caught, while early-window transient failures
# that self-heal on the next candle are not paged.
_FLATTEN_ESCALATE_MIN = 2.0

# The EOD flatten is normally driven by closed candles, but the IEX feed can go
# silent through the close window (observed 2026-06-19: zero candles 15:44–16:02 ET,
# so the flatten never ran and 5 names carried NAKED over the weekend). A wall-clock
# watchdog (:meth:`StrategyEngine.tick`) runs the flatten on real time instead. It
# also sweeps this many minutes *after* the close so a feed-dead carry still gets a
# final close attempt + naked-overnight page rather than silently riding overnight.
_POSTCLOSE_GRACE_MIN = 3.0


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
        executor: OrderExecutor | None = None,
        risk: RiskManager | None = None,
        trigger_engine: RibbonEngine | None = None,
        gate_engine: RibbonEngine | None = None,
    ) -> None:
        self._cfg = cfg
        self._on_signal = on_signal
        self._weights = weights or ScoreWeights()
        self._executor = executor
        self._risk = risk
        self._trigger = trigger_engine or RibbonEngine.trigger(cfg)
        self._gate = gate_engine or RibbonEngine.gate(cfg)
        self._state: dict[str, BotState] = {}
        self._gate_snap: dict[str, RibbonSnapshot] = {}
        self._positions: dict[str, ExecutionResult] = {}
        # Symbols already paged for a failed EOD flatten this session (dedup so a
        # naked-overnight position alerts once, not once per close-window candle).
        self._flatten_escalated: set[str] = set()
        # Serialises the EOD flatten: the candle thread (on_short_candle) and the
        # wall-clock watchdog thread (tick) both call _flatten_all_eod. Both paths
        # only ever flatten inside the close window, so this lock is the only shared
        # mutation point — re-entrant in case a future caller nests.
        self._flatten_lock = threading.RLock()

    def reconcile(self, positions) -> None:
        """Mark symbols already held at Alpaca as MANAGING (startup / post-reconnect).

        Prevents re-entering a name the broker still holds — e.g. after a restart
        mid-trade, where the bracket from a prior run is live broker-side. Accepts
        the position objects returned by ``MarketDataClient.check_account``.
        """
        for p in positions:
            symbol = getattr(p, "symbol", None)
            if symbol in self._cfg.watchlist:
                self._set(symbol, BotState.MANAGING)
                log.info(
                    "reconcile: %s held at Alpaca (qty=%s) -> MANAGING",
                    symbol,
                    getattr(p, "qty", "?"),
                )

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

    def warmup_trigger(self, candle: Candle) -> None:
        """Fold a *historical* short-timeframe candle into the trigger ribbon
        without evaluating or executing — the startup-warmup counterpart of
        :meth:`on_short_candle`.

        The live bot seeds its ribbons from the trade stream, so after a restart
        it cannot trade until the slow EMAs warm up (~3.5h for the 55-period 5m
        gate). Replaying recent history through this method (and the gate via
        :meth:`on_long_candle`) pre-seeds the indicators so the first *live*
        candle can already produce an entry. It must never place an order, emit a
        signal, or advance the state machine — it only updates indicator state.
        """
        self._trigger.update(candle)

    def on_short_candle(self, candle: Candle) -> TradeSignal | None:
        """Evaluate one closed trigger-timeframe candle; emit a signal on entry."""
        trigger = self._trigger.update(candle)
        symbol = candle.symbol
        state = self.state(symbol)

        # An order is in flight: don't re-evaluate or touch the position.
        if state is BotState.EXECUTING:
            return None

        # End-of-day: the strategy is intraday, so in the final minutes of the
        # session we flatten every open position and open nothing new. This is what
        # keeps positions from carrying overnight, where the DAY bracket stop/target
        # legs expire at the close and leave the position unprotected.
        if in_close_window(
            candle.start,
            self._cfg.market_open,
            self._cfg.market_close,
            self._cfg.flatten_before_close_min,
        ):
            self._flatten_all_eod(candle.start)
            return None

        # Holding a position: the Phase 5 risk manager owns it — check for an
        # early-exit reversal instead of evaluating a (re-)entry.
        if state is BotState.MANAGING:
            self._manage(symbol, trigger)
            return None

        if not market_is_open(candle.start, self._cfg.market_open, self._cfg.market_close):
            self._set(symbol, BotState.WAITING)
            return None

        # Phase 5 fail-safe: while the feed is down we can't trust the indicators,
        # so refuse to open new positions (existing ones keep their broker bracket).
        if self._risk is not None and not self._risk.entries_allowed:
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
            min_crossover=self._cfg.min_crossover,
            weights=self._weights,
        )
        if not decision.enter:
            self._log_skip(symbol, decision)
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

        if self._executor is not None:
            self._execute(signal)
        return signal

    def tick(self, now_utc: datetime) -> None:
        """Wall-clock EOD safety net, independent of the candle feed.

        The candle-driven flatten in :meth:`on_short_candle` only fires when a 1-min
        candle closes inside the window — but on a thin/stalled IEX feed no candle may
        arrive in the final minutes (observed 2026-06-19: a silent close window left
        positions naked over the weekend, with no Telegram page because no flatten was
        ever *attempted*). A watchdog thread calls this on a fixed cadence so the
        flatten runs on real time regardless of feed liveness. It also sweeps a short
        grace period *after* the close so a feed-dead carry still gets a final close
        attempt + naked-overnight escalation (``minutes_until_close`` is negative past
        the close, so :meth:`_escalate_failed_flatten` pages). Opens nothing — it only
        flattens, mirroring the close-window branch of ``on_short_candle``.
        """
        in_window = in_close_window(
            now_utc,
            self._cfg.market_open,
            self._cfg.market_close,
            self._cfg.flatten_before_close_min,
        )
        post_close = (
            -_POSTCLOSE_GRACE_MIN <= minutes_until_close(now_utc, self._cfg.market_close) <= 0.0
            and now_utc.astimezone(EASTERN).weekday() < 5
        )
        if in_window or post_close:
            self._flatten_all_eod(now_utc)

    def _log_skip(self, symbol: str, decision: EntryDecision) -> None:
        """Explain why a closed candle did not open a position, so a flat session is
        diagnosable from the logs. A near-miss — a scored candidate that fell short of
        the threshold — logs at INFO; the common gate-closed / no-fresh-cross
        rejections log at DEBUG to keep the ~10k-candle session readable.
        """
        if decision.confidence is not None:  # a scored candidate that missed the bar
            log.info(
                "no entry %s: %s (conf=%.1f%%)",
                symbol,
                decision.reason,
                decision.confidence.total,
            )
        else:
            log.debug("no entry %s: %s", symbol, decision.reason)

    def _execute(self, signal: TradeSignal) -> None:
        """Submit the bracket entry and advance the state machine.

        Success → MANAGING (position open, bracket live broker-side). A skip/reject
        (executor returns ``None``) falls back to EVALUATING so the next qualifying
        candle can retry. The executor swallows its own errors, so this won't raise.
        """
        symbol = signal.symbol
        self._set(symbol, BotState.EXECUTING)
        result = self._executor.execute(
            symbol=symbol,
            entry_price=signal.close,
            confidence=signal.confidence.total,
        )
        if result is None:
            self._set(symbol, BotState.EVALUATING)  # nothing opened; keep evaluating
            return
        self._positions[symbol] = result
        self._set(symbol, BotState.MANAGING)

    def _manage(self, symbol: str, trigger: RibbonSnapshot) -> None:
        """Risk-manage an open position (Phase 5): trail the broker stop up.

        Without a risk manager wired, a ``MANAGING`` symbol simply rides its
        broker-side bracket. With one, each candle ratchets the stop up under a rising
        price (``RiskManager.update_trailing_stop``) so winners run and lock in profit;
        the position then exits broker-side when that stop is hit. The symbol stays
        ``MANAGING`` here — it returns to ``WAITING`` via the end-of-day flatten or the
        next startup reconcile, not on a single 1-min pullback.
        """
        if self._risk is None:
            return
        self._risk.update_trailing_stop(trigger, self._positions.get(symbol))

    def _flatten_all_eod(self, now_utc: datetime) -> None:
        """Close every open position before the session ends (intraday flatten).

        Runs on each candle inside the close window; only ``MANAGING`` symbols are
        touched and a successful close drops them to ``WAITING``, so it is idempotent
        — already-closed names are skipped on the next candle. A symbol whose close
        fails stays ``MANAGING`` and is retried on the following candle. Exits route
        through the risk manager (so the ``on_exit`` persistence/alert hooks fire);
        without one we fall back to the executor's raw close. The exit price is the
        symbol's last trigger close (best-effort, for the P/L record only — the close
        itself is a market order).

        ``now_utc`` drives the naked-overnight escalation: if a close still fails
        inside the final ``_FLATTEN_ESCALATE_MIN`` minutes there is no retry runway
        left before the DAY bracket legs expire, so we page once. ``now_utc`` is the
        candle's start on the candle path and the wall clock on the watchdog path.

        The lock serialises the candle thread and the watchdog thread, which both
        reach this method inside the close window.
        """
        with self._flatten_lock:
            for symbol in list(self._state):
                if self.state(symbol) is not BotState.MANAGING:
                    continue
                snap = self._trigger.snapshot(symbol)
                entry = self._positions.get(symbol)
                price = (
                    snap.close
                    if snap is not None
                    else (entry.entry_price if entry is not None else 0.0)
                )
                reason = "end-of-day flatten"
                if self._risk is not None:
                    ok = self._risk.exit_position(symbol, price, reason, entry) is not None
                elif self._executor is not None:
                    ok = self._executor.close_position(symbol) is not None
                else:
                    ok = False
                if ok:
                    self._positions.pop(symbol, None)
                    self._set(symbol, BotState.WAITING)
                    self._flatten_escalated.discard(symbol)  # re-arm if re-entered later
                    log.info("EOD flatten: closed %s @ %.4f", symbol, price)
                else:
                    self._escalate_failed_flatten(symbol, now_utc)

    def _escalate_failed_flatten(self, symbol: str, now_utc: datetime) -> None:
        """Page once when a position can't be flattened with no retry runway left.

        Within ``_FLATTEN_ESCALATE_MIN`` of the close, a still-failing close means the
        position will almost certainly carry **naked overnight** (the DAY bracket
        stop/target legs expire at the close), so we send a single critical operator
        alert per symbol per session. Earlier-window failures are left to the next
        candle's retry — only the runway-exhausted case escalates. See IMP-002.
        """
        if symbol in self._flatten_escalated:
            return
        if minutes_until_close(now_utc, self._cfg.market_close) > _FLATTEN_ESCALATE_MIN:
            return  # still time for another candle to retry the close
        self._flatten_escalated.add(symbol)
        log.error(
            "EOD flatten could not close %s before the session close — "
            "NAKED OVERNIGHT risk, manual flatten required",
            symbol,
        )
        if self._risk is not None:
            self._risk.send_alert(
                f"🚨 EOD flatten FAILED for {symbol} — position will carry NAKED "
                "overnight (protective bracket legs expire at the close). "
                "Manual flatten required (python -m bot.flatten --yes)."
            )
