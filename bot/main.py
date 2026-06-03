"""Entrypoint.

Loads config, sets up logging, confirms the paper account responds, then holds
the market-data WebSocket. Each trade is aggregated into 1-min (trigger) and 5-min
(gate) candles; closed candles feed the :class:`~bot.strategy.StrategyEngine`,
which runs the dual-timeframe ribbon strategy and emits entry signals.

The executor (Phase 4) sizes a qualifying signal and submits an Alpaca bracket
order, driving the symbol into ``MANAGING``. The risk manager (Phase 5),
persistence (Phase 6), and Telegram alerts (Phase 7) hook into the ``on_signal`` /
``on_result`` callbacks and the ``MANAGING`` state. The state machine is:

    WAITING -> EVALUATING -> EXECUTING -> MANAGING
"""

from __future__ import annotations

import logging

from bot.config import Config, ConfigError
from bot.executor import ExecutionResult, OrderExecutor
from bot.market_data import MarketDataClient
from bot.risk import ExitResult, RiskManager
from bot.strategy import StrategyEngine, TradeSignal

log = logging.getLogger("ustradebot")


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    )


def _on_signal(signal: TradeSignal) -> None:
    """Entry-signal sink. Phases 6/7 add DB persistence and Telegram alerts here."""
    log.info(
        "TRADE SIGNAL %s @ %.4f conf=%.1f%%",
        signal.symbol,
        signal.close,
        signal.confidence.total,
    )


def _on_execution(result: ExecutionResult) -> None:
    """Bracket-submission sink. Phases 6/7 persist this and alert on it."""
    log.info(
        "EXECUTED %s: %d sh, $%.2f notional, conf=%.1f%% (%s)",
        result.symbol,
        result.qty,
        result.notional,
        result.confidence,
        result.status,
    )


def _on_exit(result: ExitResult) -> None:
    """Early-exit sink (Phase 5). Phases 6/7 persist this and alert on it."""
    log.info(
        "EXITED %s @ %.4f (%s)",
        result.symbol,
        result.exit_price,
        result.reason,
    )


def _on_feed_alert(message: str) -> None:
    """Feed-loss/restore alert sink (Phase 5). Phase 7 pushes this to Telegram."""
    log.warning("FEED ALERT: %s", message)


def main() -> int:
    try:
        cfg = Config.load()
    except ConfigError as e:
        # Logging may not be configured yet; print is fine for a fatal startup error.
        print(f"FATAL: configuration error: {e}")
        return 1

    setup_logging(cfg.log_level)
    log.info("USTradeBot starting (paper). Watchlist: %s", ", ".join(cfg.watchlist))
    log.info(
        "Strategy: %s ribbon %s (trigger) gated by %s ribbon %s, RSI %d, entry>=%.0f%%",
        cfg.candle_interval,
        "/".join(map(str, cfg.short_ma_periods)),
        cfg.long_candle_interval,
        "/".join(map(str, cfg.long_ma_periods)),
        cfg.rsi_period,
        cfg.entry_threshold,
    )

    executor = OrderExecutor(cfg, on_result=_on_execution)
    risk = RiskManager(cfg, executor=executor, on_exit=_on_exit, on_feed_alert=_on_feed_alert)
    strategy = StrategyEngine(cfg, on_signal=_on_signal, executor=executor, risk=risk)
    data = MarketDataClient(
        cfg,
        on_candle=strategy.on_short_candle,
        on_long_candle=strategy.on_long_candle,
        on_feed_lost=risk.notify_feed_lost,
        on_feed_restored=risk.notify_feed_restored,
    )
    try:
        _account, positions = data.check_account()
    except Exception:
        log.exception("could not reach the Alpaca paper account — aborting.")
        return 1
    strategy.reconcile(positions)  # don't re-enter names the broker already holds

    try:
        data.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        data.stop()
    log.info("USTradeBot stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
