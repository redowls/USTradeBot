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
            return None  # close failed; caller keeps the symbol MANAGING and retries
        result = ExitResult(
            symbol=symbol,
            reason=reason,
            exit_price=exit_price,
            qty=getattr(entry, "qty", None),
            order_id=order_id or None,
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
