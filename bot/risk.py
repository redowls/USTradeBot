"""Risk manager (Phase 5).

The risk manager owns a position once it is open and decides when to bail out of
it ahead of the bracket. Three responsibilities, matching the phase's checklist:

1. **Broker-side stop/target** — handled at entry by the bracket order
   (:mod:`bot.executor`); the stop and take-profit execute even if the bot is
   down, so there is nothing to do here for the happy path. The bot only adds a
   *discretionary* early exit on top.
2. **Early-exit on reversal** — :meth:`check_exit` flags a fresh **bearish cross**
   in the 1-min 8/10/20 ribbon (``RibbonSnapshot.bearish_cross``);
   :meth:`exit_position` then flattens the position via the executor (which also
   cancels the live bracket), so we don't sit through a reversal waiting for the
   stop.
3. **Fail-safe on feed loss** — while the market-data feed is down we cannot trust
   the indicators, so :meth:`notify_feed_lost` latches ``entries_allowed`` to
   ``False`` (the state machine then refuses to open new positions) and raises an
   alert; :meth:`notify_feed_restored` clears it when ticks resume. Existing
   positions are left to their broker-side bracket — we stop *opening*, we don't
   blindly *close*.

Decisions are pure; the side effects (closing a position, alerting) go through the
injected executor and callbacks, mirroring the rest of the bot so tests stay
network-free.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bot.config import Config
from bot.indicators import RibbonSnapshot
from bot.sizing import round_price

if TYPE_CHECKING:  # avoid a runtime import cycle (executor imports nothing from here)
    from bot.executor import ExecutionResult, OrderExecutor

log = logging.getLogger("ustradebot.risk")


@dataclass(frozen=True)
class ExitResult:
    """The outcome of an early exit (a discretionary close, not a bracket fill)."""

    symbol: str
    reason: str
    exit_price: float
    qty: int | None
    order_id: str | None
    entry_fill_price: float | None = None  # corrected entry fill, when a delayed fill needs it


OnExit = Callable[[ExitResult], None]
OnFeedAlert = Callable[[str], None]


class RiskManager:
    """Manages open positions: early-exit on reversal + feed-loss fail-safe."""

    def __init__(
        self,
        cfg: Config,
        *,
        executor: OrderExecutor,
        on_exit: OnExit | None = None,
        on_feed_alert: OnFeedAlert | None = None,
    ) -> None:
        self._cfg = cfg
        self._executor = executor
        self._on_exit = on_exit
        self._on_feed_alert = on_feed_alert
        self._feed_ok = True
        # Trailing-stop state, both keyed by the trade's *original* stop-leg order id
        # (unique per trade, so values never leak across re-entries of the same symbol).
        # `_trail_stops`: highest stop price placed so far. `_live_stop_oid`: the order
        # id to replace next — Alpaca issues a fresh id on every replace, so the live id
        # drifts away from the original key and must be tracked separately.
        self._trail_stops: dict[str, float] = {}
        self._live_stop_oid: dict[str, str] = {}

    # --- feed-loss fail-safe ----------------------------------------------

    @property
    def entries_allowed(self) -> bool:
        """False while the market-data feed is considered down (halts new entries)."""
        return self._feed_ok

    def notify_feed_lost(self) -> None:
        """Latch the halt and alert (idempotent within a single down-spell)."""
        if not self._feed_ok:
            return
        self._feed_ok = False
        log.error("market-data feed lost — halting new entries until it recovers")
        self._alert("⚠️ market-data feed lost — no new entries until it recovers")

    def notify_feed_restored(self) -> None:
        """Clear the halt once ticks resume (idempotent)."""
        if self._feed_ok:
            return
        self._feed_ok = True
        log.info("market-data feed restored — new entries re-enabled")
        self._alert("✅ market-data feed restored — entries re-enabled")

    def send_alert(self, message: str) -> None:
        """Emit an operator alert through the Telegram feed-alert channel.

        Public seam for callers outside the feed-loss path (the strategy's
        EOD-flatten escalation uses it to page when a position can't be flattened
        and will carry naked overnight). Best-effort, like every alert here.
        """
        self._alert(message)

    def _alert(self, message: str) -> None:
        if self._on_feed_alert is None:
            return
        try:
            self._on_feed_alert(message)
        except Exception:  # a downstream alert bug must not kill risk management
            log.exception("feed-alert callback failed")

    # --- early exit on reversal -------------------------------------------

    def check_exit(self, trigger: RibbonSnapshot) -> str | None:
        """Return a human-readable reason to exit, or ``None`` to keep holding.

        The reversal signal is a fresh bearish cross in the 1-min trigger ribbon.
        Pure: it decides nothing about *whether the order goes through* — that's
        :meth:`exit_position`.
        """
        if trigger.ribbon_ready and trigger.bearish_cross:
            return "bearish 1-min ribbon cross"
        return None

    def update_trailing_stop(
        self, trigger: RibbonSnapshot, entry: ExecutionResult | None
    ) -> bool:
        """Ratchet the broker stop up under a rising price; never lower it.

        Each managed candle we compute ``close * (1 - trail_percent)`` and, when that
        sits above the highest stop placed so far, move the bracket's stop leg up to
        it. This replaces the old first-bearish-cross exit: a winner now runs until it
        gives back ``trail_percent`` from its peak (the stop fills broker-side), rather
        than being cut on the first 1-min wobble well short of its potential.

        No-ops (returns ``False``) without a known stop leg — e.g. a position adopted
        via startup reconcile, which simply keeps its original broker bracket. State is
        keyed by the trade's original stop-leg id, so it never leaks across re-entries;
        the *live* broker id (which Alpaca rotates on every replace) is tracked apart so
        each move targets the current order rather than a stale, already-replaced one.
        """
        key = getattr(entry, "stop_order_id", "") if entry is not None else ""
        if not key:
            return False
        current = self._trail_stops.get(key, entry.stop_price)
        new_stop = round_price(trigger.close * (1.0 - self._cfg.trail_percent))
        if new_stop <= current:
            return False
        live_id = self._live_stop_oid.get(key, key)  # replace the current order, not the original
        new_id = self._executor.replace_stop_price(live_id, new_stop)
        if new_id is None:
            return False  # move failed; keep the old stop and retry next candle
        self._live_stop_oid[key] = new_id or live_id  # track the replacement id for next move
        self._trail_stops[key] = new_stop
        log.info("trailing stop %s: %.4f -> %.4f", entry.symbol, current, new_stop)
        return True

    def exit_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str,
        entry: ExecutionResult | None = None,
    ) -> ExitResult | None:
        """Flatten ``symbol`` via the executor; ``None`` if the close didn't submit.

        ``entry`` is the original bracket result (when we have it) so the exit can
        carry the held quantity for alerts/persistence; on a position picked up via
        startup reconcile it may be ``None``.
        """
        order_id = self._executor.close_position(symbol)
        if order_id is None:
            # The close didn't submit. It may be that a broker-side stop/target leg
            # already filled (the trailing stop lives broker-side) — reconcile the real
            # exit from order history so we record it at its true fill price and release
            # the symbol, rather than leaving a phantom-open position (the 2026-06-17
            # bug). A genuine close failure (transient/outage) reconciles to None → the
            # caller keeps the symbol MANAGING and retries on the next candle.
            reconciled = self._executor.reconcile_exit(symbol)
            if reconciled is None:
                return None
            order_id, exit_price = reconciled
            reason = f"{reason} (stop/target filled broker-side)"
        else:
            # The bot's own market sell drove the exit; record it at the ACTUAL broker
            # fill price rather than the candle-close estimate passed in — they differ by
            # cents-to-dollars (2026-06-23 GOOG flatten: passed 346.72, filled 347.14), so
            # P/L and the win/loss flag are exact. Falls back to the passed-in price when
            # the fill can't be read (empty id / unfilled / read error).
            fill_price = self._executor.close_fill_price(order_id)
            if fill_price is not None:
                exit_price = fill_price
        # Correct the recorded entry price to the actual broker fill. IMP-009 reads the
        # parent buy's `filled_avg_price` moments after the submit ack, but a fill delayed
        # past that short budget falls back to the candle-close estimate and understates P/L
        # (2026-06-25 AMD: the market buy filled ~2 min after submission, recorded @544.71 vs
        # the real @547.873 → its loss was understated by ~$19, the exact DB↔equity gap that
        # day). By exit time the entry order is definitively filled, so a single read recovers
        # the true price with no candle-thread stall; ``None`` (no entry / unreadable) leaves
        # the stored entry price untouched. Entry-side completion of IMP-008/009.
        entry_oid = getattr(entry, "order_id", "") if entry is not None else ""
        entry_fill = self._executor.entry_fill_price(entry_oid) if entry_oid else None
        key = getattr(entry, "stop_order_id", "") if entry is not None else ""
        if key:  # trade is done — drop its trailing-stop state
            self._trail_stops.pop(key, None)
            self._live_stop_oid.pop(key, None)
        result = ExitResult(
            symbol=symbol,
            reason=reason,
            exit_price=exit_price,
            qty=getattr(entry, "qty", None),
            order_id=order_id or None,
            entry_fill_price=entry_fill,
        )
        log.info(
            "EXIT %s @ %.4f (%s)%s",
            result.symbol,
            result.exit_price,
            result.reason,
            f" qty={result.qty}" if result.qty is not None else "",
        )
        if self._on_exit is not None:
            try:
                self._on_exit(result)
            except Exception:  # a downstream alert/DB bug must not kill the exit
                log.exception("on_exit callback failed for %s", symbol)
        return result
