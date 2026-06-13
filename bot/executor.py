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

    def close_position(self, symbol: str) -> str | None:
        """Liquidate ``symbol``, cancelling its open bracket first (Phase 5 early-exit).

        Alpaca's single-symbol ``close_position`` (``DELETE /v2/positions/{symbol}``)
        submits a market order for the full qty but does NOT cancel the associated
        bracket's unfilled stop/target legs — they keep the shares ``held_for_orders``
        so the close is rejected (403 ``insufficient qty available``). We therefore
        cancel the resting legs first, then liquidate, retrying briefly because the
        broker frees the held qty a moment after the cancel lands. Returns the close
        order's id on success (an empty string is still success — some responses omit
        the id), or ``None`` on any error so the risk manager leaves the symbol in
        ``MANAGING`` and retries on the next candle.
        """
        self._cancel_open_orders(symbol)
        client = self._client_or_build()
        last_exc: Exception | None = None
        for attempt in range(3):
            if attempt:
                time.sleep(0.4)  # give the cancel time to release held_for_orders
            try:
                order = client.close_position(symbol)
            except Exception as exc:  # noqa: BLE001 — retried, then logged below
                last_exc = exc
                continue
            order_id = str(getattr(order, "id", "") or "")
            log.info("CLOSE %s submitted (order=%s)", symbol, order_id or "?")
            return order_id
        log.error("could not close position for %s", symbol, exc_info=last_exc)
        return None
