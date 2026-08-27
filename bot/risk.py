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
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from bot.config import Config
from bot.executor import StopOrderGone  # exception only — no cycle (executor imports nothing here)
from bot.indicators import RibbonSnapshot
from bot.sizing import round_price

if TYPE_CHECKING:  # avoid a runtime import cycle (executor imports nothing from here)
    from bot.executor import ExecutionResult, OrderExecutor

log = logging.getLogger("ustradebot.risk")


class TrailResult(Enum):
    """Outcome of a :meth:`RiskManager.update_trailing_stop` pass.

    ``HELD``      — the stop was left where it was (no room to ratchet, or no stop leg).
    ``MOVED``     — the broker stop leg was ratcheted up to a new level.
    ``STOP_GONE`` — the stop leg is no longer open (it filled broker-side); the position
                    is flat, so the caller should reconcile the exit, not retry the move.
    """

    HELD = "held"
    MOVED = "moved"
    STOP_GONE = "gone"


@dataclass(frozen=True)
class ExitResult:
    """The outcome of an early exit (a discretionary close, not a bracket fill)."""

    symbol: str
    reason: str
    exit_price: float
    qty: int | None
    order_id: str | None
    entry_fill_price: float | None = None  # corrected entry fill, when a delayed fill needs it
    # In-trade excursion, % of entry, measured on managed 1-min closes (IMP-037).
    # ``None`` when the position was never managed (a startup-reconciled holding, or an
    # exit before its first managed candle) — absence of measurement, not a zero excursion.
    mfe_pct: float | None = None
    mae_pct: float | None = None


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
        # In-trade excursion (IMP-037): symbol -> (high-water close, low-water close).
        # Keyed by SYMBOL, not by stop-leg id, so a position whose stop leg can't be
        # moved (a startup-reconciled holding) is still measured. Cleared on exit, so it
        # never leaks across re-entries.
        self._excursion: dict[str, tuple[float, float]] = {}
        # Broad-adverse-day stand-down (IMP-016). Session-scoped, reset each session
        # open via :meth:`roll_session`. Once tripped, ``entries_allowed`` goes False so
        # the strategy stops opening NEW positions (open ones are still managed/flattened)
        # for the rest of the session. See :meth:`_account_for_standdown`.
        self._session_day: date | None = None
        self._session_realized = 0.0
        self._consec_losses = 0
        self._standdown = False
        self._standdown_baseline_equity: float | None = None

    # --- feed-loss fail-safe ----------------------------------------------

    @property
    def entries_allowed(self) -> bool:
        """False while new entries are halted — either the market-data feed is down
        (feed-loss fail-safe) or the broad-adverse-day stand-down has tripped
        (IMP-016). Managing/flattening open positions is unaffected either way."""
        return self._feed_ok and not self._standdown

    @property
    def standdown_active(self) -> bool:
        """True once the session stand-down has tripped; cleared at the next session
        open by :meth:`roll_session`. (IMP-016)"""
        return self._standdown

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

    # --- broad-adverse-day stand-down (IMP-016) ---------------------------

    def roll_session(self, day: date) -> None:
        """Reset the stand-down accounting at the start of a new trading session.

        Driven from the strategy's per-candle path with the candle's US-Eastern session
        date; a no-op until the date actually changes, so it is safe (and cheap) to call
        on every candle. It clears the realized-loss tally, the consecutive-loss streak,
        the equity baseline, and — crucially — an active stand-down, so a halt from one
        session never bleeds into the next (the brief's "reset at the next session open").
        """
        if day == self._session_day:
            return
        self._session_day = day
        self._session_realized = 0.0
        self._consec_losses = 0
        self._standdown_baseline_equity = None
        if self._standdown:
            log.info("stand-down reset for new session %s — new entries re-enabled", day)
        self._standdown = False

    def _account_for_standdown(
        self, result: ExitResult, entry: ExecutionResult | None, entry_fill: float | None
    ) -> None:
        """Fold a closed trade into the session stand-down tally (IMP-016).

        Realized P/L is ``(exit - entry) * qty`` using the corrected entry fill when we
        have it (else the recorded entry price); a loss extends the consecutive-loss
        streak, any non-loss resets it. When either the cumulative session loss breaches
        ``standdown_max_loss_pct`` of the session-open equity (the executor's equity read
        at the session's first entry) OR the streak reaches
        ``standdown_max_consecutive_losses``, the stand-down latches and new entries halt
        for the rest of the session. A missing entry (a startup-reconciled holding with no
        entry price/qty) is skipped rather than guessed — it simply does not count. The
        two motivating sessions: 2026-07-07 (1W/10L, −$179) trips on the streak after the
        3rd loss, blocking ~7 later losers; 2026-07-17 (0W/5L, −$113) trips after the 3rd
        loss (TSM), blocking INTC (−$39.60) and NFLX (−$23.85).
        """
        if not self._cfg.standdown_enabled or self._standdown:
            return
        qty = getattr(entry, "qty", None)
        entry_ref = entry_fill if entry_fill is not None else getattr(entry, "entry_price", None)
        if qty is None or entry_ref is None:
            return  # no entry context to score this exit — don't guess a P/L
        pnl = (result.exit_price - entry_ref) * qty
        self._session_realized += pnl
        self._consec_losses = self._consec_losses + 1 if pnl < 0 else 0
        if self._standdown_baseline_equity is None:
            self._standdown_baseline_equity = getattr(self._executor, "last_equity", None)
        streak_breach = self._consec_losses >= self._cfg.standdown_max_consecutive_losses
        loss_breach = (
            self._standdown_baseline_equity is not None
            and self._session_realized
            <= -self._cfg.standdown_max_loss_pct * self._standdown_baseline_equity
        )
        if not (streak_breach or loss_breach):
            return
        self._standdown = True
        trigger = (
            f"{self._consec_losses} consecutive losing exits"
            if streak_breach
            else f"session realized {self._session_realized:+.2f} "
            f"(>= {self._cfg.standdown_max_loss_pct:.1%} of open equity "
            f"{self._standdown_baseline_equity:.2f})"
        )
        log.error(
            "STAND-DOWN tripped — %s; halting NEW entries for the rest of the session "
            "(open positions are still managed & flattened)",
            trigger,
        )
        self._alert(
            f"🛑 Stand-down: {trigger}. No new entries for the rest of the session "
            "(open positions still managed & flattened; resets at the next open)."
        )

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
    ) -> TrailResult:
        """Ratchet the broker stop up under a rising price; never lower it.

        Each managed candle we compute ``close * (1 - trail_percent)`` and, when that
        sits above the highest stop placed so far, move the bracket's stop leg up to
        it. This replaces the old first-bearish-cross exit: a winner now runs until it
        gives back ``trail_percent`` from its peak (the stop fills broker-side), rather
        than being cut on the first 1-min wobble well short of its potential.

        ``HELD`` without a known stop leg — e.g. a position adopted via startup
        reconcile, which simply keeps its original broker bracket. State is keyed by the
        trade's original stop-leg id, so it never leaks across re-entries; the *live*
        broker id (which Alpaca rotates on every replace) is tracked apart so each move
        targets the current order rather than a stale, already-replaced one.

        Returns ``STOP_GONE`` when the broker stop leg can no longer be moved because it
        has filled (``StopOrderGone``): the position is flat, so the caller reconciles
        the exit once instead of re-issuing the doomed move every candle (the 2026-06-30
        bug — AMD/SE stopped out broker-side at ~15:07 UTC yet the move 422'd ~minutely
        for ~4.5h while the symbols sat MANAGING and un-re-enterable).
        """
        # Measure BEFORE the early return: a position with no movable stop leg still has
        # an excursion worth recording, and the exit path reads this state (IMP-037).
        self._track_excursion(trigger, entry)
        key = getattr(entry, "stop_order_id", "") if entry is not None else ""
        if not key:
            return TrailResult.HELD
        current = self._trail_stops.get(key, entry.stop_price)
        width = self._cfg.trail_percent
        tighten_at = self._cfg.trail_tighten_after
        if tighten_at > 0.0 and trigger.close >= entry.entry_price * (1.0 + tighten_at):
            # The trade has proven itself by running `tighten_at` above entry; switch to
            # the narrower width so a winner banks its move instead of handing back a
            # full flat trail-width from the peak (IMP-021).
            width = self._cfg.trail_percent_tight
        new_stop = round_price(trigger.close * (1.0 - width))
        if new_stop <= current:
            return TrailResult.HELD
        live_id = self._live_stop_oid.get(key, key)  # replace the current order, not the original
        try:
            new_id = self._executor.replace_stop_price(live_id, new_stop)
        except StopOrderGone:
            return TrailResult.STOP_GONE  # the leg filled — the caller reconciles the exit
        if new_id is None:
            return TrailResult.HELD  # move failed; keep the old stop and retry next candle
        self._live_stop_oid[key] = new_id or live_id  # track the replacement id for next move
        self._trail_stops[key] = new_stop
        log.info("trailing stop %s: %.4f -> %.4f", entry.symbol, current, new_stop)
        return TrailResult.MOVED

    # --- in-trade excursion (IMP-037, observational) ----------------------

    def _track_excursion(
        self, trigger: RibbonSnapshot, entry: ExecutionResult | None
    ) -> None:
        """Carry this position's high/low-water **close** forward one candle.

        Measured on closes rather than intrabar highs/lows deliberately: the ratchet
        sets the stop from ``close``, so a close-based excursion is the move the exit
        structure could actually have banked. An intrabar high the trail can never reach
        would flatter every capture ratio computed off this column.

        Seeded at the entry price, so a trade that only ever goes against us records
        ``mfe_pct = 0`` (it reached its entry, no more) rather than a misleading negative.
        """
        entry_px = getattr(entry, "entry_price", 0.0) or 0.0
        symbol = getattr(entry, "symbol", "") if entry is not None else ""
        if entry_px <= 0 or not symbol:
            return  # no anchor to measure against (startup-reconciled holding)
        # Keyed off the POSITION's symbol, not the candle's, so this side and the
        # exit-side pop (which is handed the strategy's symbol) agree by construction.
        hi, lo = self._excursion.get(symbol, (entry_px, entry_px))
        self._excursion[symbol] = (max(hi, trigger.close), min(lo, trigger.close))

    def _excursion_pct(
        self, symbol: str, entry: ExecutionResult | None
    ) -> tuple[float | None, float | None]:
        """Pop this position's excursion and express it as % of entry.

        Popping is what keeps the state from leaking into a later re-entry of the same
        symbol; ``(None, None)`` when the position was never managed.
        """
        watermarks = self._excursion.pop(symbol, None)
        entry_px = getattr(entry, "entry_price", 0.0) or 0.0
        if watermarks is None or entry_px <= 0:
            return None, None
        hi, lo = watermarks
        return (hi / entry_px - 1.0) * 100.0, (lo / entry_px - 1.0) * 100.0

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
            reconciled = self._executor.reconcile_exit(
                symbol, after=self._entry_filled_at(entry)
            )
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
        return self._record_exit(symbol, exit_price, reason, entry, order_id)

    def reconcile_if_closed(
        self, symbol: str, entry: ExecutionResult | None = None
    ) -> ExitResult | None:
        """Record a broker-side stop/target fill on a still-``MANAGING`` symbol *without*
        attempting a close — the poll-driven counterpart to :meth:`exit_position`.

        The trailing stop only surfaces a filled stop leg when a *higher high* triggers a
        replace that 422s (``StopOrderGone`` → the ``_manage`` reconcile path). When the
        stop instead fills on a **down move**, no replace is ever attempted, so the fill
        goes undetected until the EOD flatten reconciles it hours later — the symbol sits
        ``MANAGING`` (un-re-enterable) and its exit is mistimed/mislabelled (the 2026-07-10
        SE case: the broker-side stop filled @14:33 UTC yet was booked @19:45 as an
        "end-of-day flatten" — IMP-012's residual gap). This polls order history through the
        read-only :meth:`OrderExecutor.reconcile_exit`, which returns ``None`` while the
        broker still holds the position, so it is safe to call on an open position (it never
        submits a sell). On a real fill it records the exit at the true broker price, tags it
        ``stop/target filled broker-side``, and returns it; otherwise ``None``.

        Guard (2026-07-20 NVDA): a bracket entry can fill **seconds-to-minutes late**
        (NVDA's buy filled ~2.5 min after submission — the same delayed-fill pattern
        IMP-010 handles). During that gap the symbol is already ``MANAGING`` but the
        broker holds **no** position yet, so ``reconcile_exit``'s ``get_open_position``
        404s just like an already-flat position — and it would then match a **stale
        prior-session sell** as a phantom exit (NVDA booked a +$41 win on a trade that
        was really a −$58 stop-out, and the bot marked itself flat while the broker
        actually held the position). So we first confirm the **entry buy has filled**
        (``entry_fill_price`` returns a price only once it has); until then the position
        simply hasn't opened — return ``None`` and leave it ``MANAGING`` to re-check next
        tick. When there's no entry order to check (a startup-reconciled holding), the
        position was confirmed held at startup, so the guard is skipped.
        """
        entry_oid = getattr(entry, "order_id", "") if entry is not None else ""
        if entry_oid and self._executor.entry_fill_price(entry_oid) is None:
            return None  # entry not filled yet → position not open → don't book an exit
        reconciled = self._executor.reconcile_exit(
            symbol, after=self._entry_filled_at(entry)
        )
        if reconciled is None:
            return None
        order_id, exit_price = reconciled
        return self._record_exit(
            symbol, exit_price, "stop/target filled broker-side", entry, order_id
        )

    def _entry_filled_at(self, entry: ExecutionResult | None) -> datetime | None:
        """When this trade's entry buy filled — the recency anchor both reconcile paths
        hand to :meth:`OrderExecutor.reconcile_exit` so a *previous* trade's sell can
        never be booked as this one's exit (IMP-027; see that method for the MU case).

        ``None`` when there is no entry order to anchor on (a startup-reconciled holding)
        or the timestamp can't be read — the guard then stands down rather than blocking
        a legitimate exit.
        """
        entry_oid = getattr(entry, "order_id", "") if entry is not None else ""
        return self._executor.entry_filled_at(entry_oid) if entry_oid else None

    def _record_exit(
        self,
        symbol: str,
        exit_price: float,
        reason: str,
        entry: ExecutionResult | None,
        order_id: str | None,
    ) -> ExitResult:
        """Build, log, persist (via ``on_exit``) and return the :class:`ExitResult` — the
        shared tail of :meth:`exit_position` and :meth:`reconcile_if_closed`.
        """
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
        mfe_pct, mae_pct = self._excursion_pct(symbol, entry)
        result = ExitResult(
            symbol=symbol,
            reason=reason,
            exit_price=exit_price,
            qty=getattr(entry, "qty", None),
            order_id=order_id or None,
            entry_fill_price=entry_fill,
            mfe_pct=mfe_pct,
            mae_pct=mae_pct,
        )
        log.info(
            "EXIT %s @ %.4f (%s)%s%s",
            result.symbol,
            result.exit_price,
            result.reason,
            f" qty={result.qty}" if result.qty is not None else "",
            "" if mfe_pct is None else f" mfe={mfe_pct:+.2f}% mae={mae_pct:+.2f}%",
        )
        self._account_for_standdown(result, entry, entry_fill)
        if self._on_exit is not None:
            try:
                self._on_exit(result)
            except Exception:  # a downstream alert/DB bug must not kill the exit
                log.exception("on_exit callback failed for %s", symbol)
        return result
