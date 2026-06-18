"""Order executor (Phase 4).

Turns a qualifying :class:`~bot.strategy.TradeSignal` into a live Alpaca **bracket
order**: it reads the account for current buying power / equity, sizes the position
from the confidence score (Model A or B, see :mod:`bot.sizing`), and submits a
market entry with the stop-loss and take-profit attached in one call. The bracket
lives broker-side, so the stop/target execute even if the bot disconnects — which
is exactly what the Phase 5 risk manager relies on.

The trading client is injectable (a factory), mirroring
:class:`~bot.market_data.MarketDataClient`, so tests run without a network or keys.

Lifecycle scope: this handles the **submit ack** and **rejects** (a raised error or
a ``rejected`` status returns ``None`` and logs, without killing the strategy).
Fill / partial-fill tracking needs the trade-updates stream and is wired with
persistence (Phase 6); a freshly submitted bracket entry is typically
``pending_new`` / ``accepted`` here, not yet ``filled``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    MarketOrderRequest,
    ReplaceOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

from bot.config import Config
from bot.sizing import SizePlan, plan_model_a, plan_model_b, round_price

log = logging.getLogger("ustradebot.executor")

# Order statuses that mean the submission was refused outright.
_REJECTED = {"rejected", "canceled", "expired"}


def _is_position_gone(exc: Exception) -> bool:
    """True when an Alpaca error means the position no longer exists (already flat).

    A broker-side bracket stop/target leg fills *outside* the bot's control; a later
    close then 404s with ``code 40410000 "position not found"``. That is the outcome
    we wanted (flat), not a retryable failure — so the close path treats it as
    already-closed and the exit is reconciled from order history, rather than being
    retried 12× and abandoned as a phantom-open position (the 2026-06-17 bug).
    """
    text = str(exc).lower()
    return "position not found" in text or "40410000" in text


# Close retry/poll budget. After we cancel the bracket's resting legs the broker
# keeps the position's qty ``held_for_orders`` for a few seconds — the cancel settles
# asynchronously — so an immediate close 403s with "insufficient qty available". We
# poll the position until that held qty frees, then liquidate, all within one call.
# 2026-06-15: today's EOD flatten 403'd through the old 3-attempt / ~0.8s budget on
# all six open names and only closed on a *later* candle pass; on a thin close that
# pass may never arrive, leaving the position naked (the protective legs are already
# cancelled). The budget below (~6s) lets the first flatten pass finish on its own.
_CLOSE_ATTEMPTS = 12
_CLOSE_RETRY_DELAY = 0.5  # seconds between attempts


@dataclass(frozen=True)
class ExecutionResult:
    """The outcome of submitting one bracket entry."""

    symbol: str
    order_id: str
    qty: int
    notional: float
    entry_price: float
    stop_price: float
    take_profit_price: float
    confidence: float
    status: str
    model: str
    stop_order_id: str = ""  # the bracket's stop leg, so the trailing stop can move it


OnResult = Callable[[ExecutionResult], None]


class OrderExecutor:
    """Sizes and submits bracket entries against the Alpaca paper account."""

    def __init__(
        self,
        cfg: Config,
        *,
        trading_factory: Callable[[], TradingClient] | None = None,
        on_result: OnResult | None = None,
    ) -> None:
        self._cfg = cfg
        self._trading_factory = trading_factory or self._default_trading_client
        self._on_result = on_result
        self._client: TradingClient | None = None

    def _default_trading_client(self) -> TradingClient:
        return TradingClient(
            self._cfg.alpaca_key_id,
            self._cfg.alpaca_secret,
            paper=True,
            url_override=self._cfg.alpaca_base_url,
        )

    def _client_or_build(self) -> TradingClient:
        if self._client is None:
            self._client = self._trading_factory()
        return self._client

    # --- sizing ------------------------------------------------------------

    def plan(self, *, confidence: float, entry_price: float, account) -> SizePlan | None:
        """Build a :class:`SizePlan` from the confidence and the live account."""
        cfg = self._cfg
        buying_power = float(account.buying_power)
        if cfg.sizing_model == "B":
            return plan_model_b(
                confidence=confidence,
                entry_price=entry_price,
                buying_power=buying_power,
                equity=float(account.equity),
                threshold=cfg.entry_threshold,
                max_risk_per_trade=cfg.max_risk_per_trade,
                max_alloc=cfg.max_alloc,
                stop_loss=cfg.stop_loss,
                take_profit=cfg.take_profit,
            )
        return plan_model_a(
            confidence=confidence,
            entry_price=entry_price,
            buying_power=buying_power,
            threshold=cfg.entry_threshold,
            min_alloc=cfg.min_alloc,
            max_alloc=cfg.max_alloc,
            stop_loss=cfg.stop_loss,
            take_profit=cfg.take_profit,
        )

    # --- execution ---------------------------------------------------------

    def execute(
        self, *, symbol: str, entry_price: float, confidence: float
    ) -> ExecutionResult | None:
        """Size and submit a bracket entry. ``None`` on a skip, reject, or error."""
        try:
            client = self._client_or_build()
            account = client.get_account()
        except Exception:
            log.exception("could not read account before sizing %s — skipping entry", symbol)
            return None

        plan = self.plan(confidence=confidence, entry_price=entry_price, account=account)
        if plan is None:
            log.warning(
                "skip %s: position sizing (model %s) yields < 1 share at %.4f",
                symbol,
                self._cfg.sizing_model,
                entry_price,
            )
            return None

        request = MarketOrderRequest(
            symbol=symbol,
            qty=plan.qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=plan.take_profit_price),
            stop_loss=StopLossRequest(stop_price=plan.stop_price),
        )

        try:
            order = client.submit_order(order_data=request)
        except Exception:
            log.exception("order submission failed for %s", symbol)
            return None

        # Alpaca returns an enum; use its .value ("pending_new") not str() which
        # yields the repr ("OrderStatus.PENDING_NEW") — the repr overflows the
        # dbo.orders.status column and is never matched by the _REJECTED guard.
        raw_status = getattr(order, "status", "") or ""
        status = (getattr(raw_status, "value", None) or str(raw_status)).lower()
        if status in _REJECTED:
            log.error(
                "order for %s was %s by Alpaca (id=%s)", symbol, status, getattr(order, "id", "?")
            )
            return None

        result = ExecutionResult(
            symbol=symbol,
            order_id=str(getattr(order, "id", "")),
            qty=plan.qty,
            notional=plan.notional,
            entry_price=plan.entry_price,
            stop_price=plan.stop_price,
            take_profit_price=plan.take_profit_price,
            confidence=confidence,
            status=status or "submitted",
            model=plan.model,
            stop_order_id=self._stop_leg_id(order),
        )
        log.info(
            "BRACKET %s qty=%d notional=%.2f entry=%.4f stop=%.4f target=%.4f "
            "conf=%.1f%% (model %s, %s)",
            result.symbol,
            result.qty,
            result.notional,
            result.entry_price,
            result.stop_price,
            result.take_profit_price,
            result.confidence,
            result.model,
            result.status,
        )
        if self._on_result is not None:
            try:
                self._on_result(result)
            except Exception:  # a downstream alert/DB bug must not kill execution
                log.exception("on_result callback failed for %s", symbol)
        return result

    @staticmethod
    def _stop_leg_id(order) -> str:
        """Pull the stop-loss leg's order id out of a submitted bracket order.

        The bracket response carries its two exit legs in ``order.legs``; we want the
        stop leg (an ``OrderType.STOP``) so the risk manager can later move it to
        trail the price. Returns ``""`` if the legs aren't present (e.g. a fake in
        tests, or a response shape without nested legs).
        """
        for leg in getattr(order, "legs", None) or []:
            if "stop" in str(getattr(leg, "order_type", "")).lower():
                return str(getattr(leg, "id", "") or "")
        return ""

    # --- exit (Phase 5) ----------------------------------------------------

    def replace_stop_price(self, stop_order_id: str, new_stop_price: float) -> str | None:
        """Move an open stop order to ``new_stop_price`` (the trailing-stop ratchet).

        Returns the **replacement order's id** on success (Alpaca cancels the old order
        and issues a new one with a new id — the caller MUST track it and replace that
        next time, or the following move 422s with ``order already replaced``). Returns
        ``None`` on any error (or a missing id) so the risk manager keeps the previous
        stop and retries next candle — a failed move never leaves the position less
        protected than before. The returned id may be an empty string on a success
        whose response omitted the id; the caller then keeps using the prior id.
        """
        if not stop_order_id:
            return None
        try:
            client = self._client_or_build()
            order = client.replace_order_by_id(
                stop_order_id, ReplaceOrderRequest(stop_price=round_price(new_stop_price))
            )
        except Exception:
            log.exception("could not move stop order %s to %.4f", stop_order_id, new_stop_price)
            return None
        new_id = str(getattr(order, "id", "") or "")
        log.info(
            "STOP moved -> %.4f (order %s -> %s)",
            round_price(new_stop_price), stop_order_id, new_id or "?",
        )
        return new_id

    def _cancel_open_orders(self, symbol: str) -> int:
        """Cancel any resting orders for ``symbol`` (the bracket stop/target legs).

        Single-symbol ``close_position`` does NOT cancel the bracket first, so the
        position's whole qty stays ``held_for_orders`` and the close 403s with
        ``insufficient qty available``. We must clear the legs ourselves before
        liquidating. Returns the number cancelled; per-order errors are logged and
        swallowed so one stuck leg doesn't block the rest.
        """
        client = self._client_or_build()
        try:
            orders = client.get_orders(
                GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[symbol])
            )
        except Exception:
            log.exception("could not list open orders for %s", symbol)
            return 0
        cancelled = 0
        for order in orders or []:
            order_id = str(getattr(order, "id", "") or "")
            if not order_id:
                continue
            try:
                client.cancel_order_by_id(order_id)
                cancelled += 1
            except Exception:
                log.exception("could not cancel order %s for %s", order_id, symbol)
        if cancelled:
            log.info("cancelled %d open order(s) for %s before close", cancelled, symbol)
        return cancelled

    def _confirm_flat(self, symbol: str) -> bool:
        """True once the broker confirms ``symbol`` holds no position.

        ``close_position`` only acks the **submission** of a market order — not its
        fill. After the regular session closes Alpaca *accepts* a market DAY order but
        never fills it, so the position lingers open while the bot believes it closed
        (the 2026-06-18 EOD-flatten bug: the flatten fired a few minutes late on a
        quiet/laggy feed + a 504 storm, submitted seven market sells past 16:00 ET, and
        recorded seven fake exits while the positions carried NAKED into the weekend).
        We poll until the position is gone (``_is_position_gone`` → 404) and return
        ``True``; if it is still open when the budget is spent we return ``False`` so the
        close is treated as failed. A transient read error is inconclusive — we keep
        polling and, if it never clears, fail closed (report not-flat), the
        capital-protective choice (the caller keeps the symbol MANAGING and the
        naked-overnight escalation fires).
        """
        for attempt in range(_CLOSE_ATTEMPTS):
            if attempt:
                time.sleep(_CLOSE_RETRY_DELAY)
            try:
                self._client_or_build().get_open_position(symbol)
            except Exception as exc:  # noqa: BLE001
                if _is_position_gone(exc):
                    return True
                # transient read error — keep polling; never assume flat on a flaky read
        return False

    def _qty_released(self, symbol: str) -> bool:
        """True once the broker has freed the qty the cancelled bracket legs held.

        After ``cancel_order`` returns, Alpaca keeps the position's qty
        ``held_for_orders`` for a moment (the cancel settles asynchronously), so
        ``qty_available`` reads 0 until it lands; closing before then 403s. Polling
        this lets the close fire the instant the qty frees instead of guessing with a
        fixed sleep. On any error (no position, transient read failure) we return
        ``True`` so the close path still runs and decides — we never block a
        liquidation on a flaky status read.
        """
        try:
            pos = self._client_or_build().get_open_position(symbol)
        except Exception:
            return True
        try:
            return float(getattr(pos, "qty_available", 0) or 0) > 0
        except (TypeError, ValueError):
            return True

    def close_position(self, symbol: str) -> str | None:
        """Liquidate ``symbol``, cancelling its open bracket first (Phase 5 early-exit).

        Alpaca's single-symbol ``close_position`` (``DELETE /v2/positions/{symbol}``)
        submits a market order for the full qty but does NOT cancel the associated
        bracket's unfilled stop/target legs — they keep the shares ``held_for_orders``
        so the close is rejected (403 ``insufficient qty available``). We therefore
        cancel the resting legs first, then **poll until the broker releases the held
        qty** (the cancel settles asynchronously) before liquidating — so the close
        completes within this one call rather than depending on a later candle pass
        that may never arrive before the session ends (which would leave the position
        naked, its protective legs already cancelled). Returns the close order's id on
        success (an empty string is still success — some responses omit the id), or
        ``None`` on any error so the risk manager leaves the symbol in ``MANAGING``
        and retries on the next candle.
        """
        cancelled = self._cancel_open_orders(symbol)
        client = self._client_or_build()
        last_exc: Exception | None = None
        order_id: str | None = None
        for attempt in range(_CLOSE_ATTEMPTS):
            if attempt:
                time.sleep(_CLOSE_RETRY_DELAY)  # give the cancel time to release held_for_orders
            # Don't fire the close until the cancelled legs have released the qty,
            # otherwise it 403s on held_for_orders and burns an attempt for nothing.
            if cancelled and not self._qty_released(symbol):
                continue
            try:
                order = client.close_position(symbol)
            except Exception as exc:  # noqa: BLE001 — retried, then logged below
                if _is_position_gone(exc):
                    # Already flat: a broker-side stop/target leg filled before this
                    # close (the trailing stop lives broker-side). No position will
                    # ever come back, so stop retrying — the caller reconciles the real
                    # exit from order history rather than spamming 12 errors and leaving
                    # a phantom-open row (the 2026-06-17 EOD-flatten bug).
                    log.info("CLOSE %s: already flat (closed broker-side)", symbol)
                    return None
                last_exc = exc
                continue
            order_id = str(getattr(order, "id", "") or "")
            log.info("CLOSE %s submitted (order=%s)", symbol, order_id or "?")
            break
        if order_id is None:
            log.error(
                "could not close position for %s after %d attempts", symbol, _CLOSE_ATTEMPTS,
                exc_info=last_exc,
            )
            return None
        # A submit ack is NOT a close. Confirm the position actually went flat — past the
        # 16:00 close (e.g. a late EOD flatten on a laggy feed) Alpaca accepts the market
        # order but never fills it, so reporting success here would record a fake exit and
        # leave the position carrying NAKED overnight (the 2026-06-18 bug). If it didn't go
        # flat, fail the close so the caller keeps it MANAGING and the escalation pages.
        if self._confirm_flat(symbol):
            return order_id
        log.error(
            "CLOSE %s submitted (order=%s) but the position is still open — the close did "
            "not fill (market likely closed); treating as a failed close",
            symbol, order_id or "?",
        )
        return None

    def reconcile_exit(self, symbol: str) -> tuple[str, float] | None:
        """Recover an exit the bot didn't drive: a broker-side stop/target fill.

        The trailing stop lives broker-side; when it fills, the position vanishes and
        the bot's own close 404s (:func:`_is_position_gone`). To still record the exit
        — at its **real** fill price, so P/L and the win/loss flag are correct — and
        release the symbol from ``MANAGING`` instead of leaving a phantom-open row, this
        returns the most recent **filled sell** order's ``(id, avg_fill_price)``.

        Safety: it first confirms the broker holds **no** position for ``symbol``. A
        transient read error (the position may still be open) returns ``None`` so a
        flaky call is never mistaken for a fill — abandoning a live position. Returns
        ``None`` when a position remains or no filled exit can be found.
        """
        client = self._client_or_build()
        try:
            client.get_open_position(symbol)
            return None  # still holding — not an already-flat case
        except Exception as exc:  # noqa: BLE001
            if not _is_position_gone(exc):
                return None  # couldn't confirm flat (transient) — leave MANAGING, retry
        try:
            orders = client.get_orders(
                GetOrdersRequest(
                    status=QueryOrderStatus.CLOSED,
                    side=OrderSide.SELL,
                    symbols=[symbol],
                )
            )
        except Exception:
            log.exception("reconcile_exit: could not list closed orders for %s", symbol)
            return None
        for order in orders or []:  # Alpaca returns most-recent first
            price = getattr(order, "filled_avg_price", None)
            if price:
                oid = str(getattr(order, "id", "") or "")
                log.info(
                    "reconcile_exit %s: broker-side fill @ %s (order %s)", symbol, price, oid
                )
                return oid, float(price)
        return None
