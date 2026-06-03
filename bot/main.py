"""Entrypoint.

Loads config, sets up logging, confirms the paper account responds, then holds
the market-data WebSocket. Each trade is aggregated into 1-min (trigger) and 5-min
(gate) candles; closed candles feed the :class:`~bot.strategy.StrategyEngine`,
which runs the dual-timeframe ribbon strategy and emits entry signals.

The executor (Phase 4), risk manager (Phase 5), persistence (Phase 6), and
Telegram alerts (Phase 7) hook into the ``on_signal`` callback and the strategy's
``EXECUTING``/``MANAGING`` states. The state machine is:

    WAITING -> EVALUATING -> EXECUTING -> MANAGING
"""

from __future__ import annotations

import logging

from bot.config import Config, ConfigError
from bot.market_data import MarketDataClient
from bot.strategy import StrategyEngine, TradeSignal

log = logging.getLogger("ustradebot")


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    )


def _on_signal(signal: TradeSignal) -> None:
    """Phase 3 sink for entry signals. Phases 4/6/7 add execution, DB, Telegram."""
    log.info(
        "TRADE SIGNAL %s @ %.4f conf=%.1f%% (executor not wired yet — Phase 4)",
        signal.symbol,
        signal.close,
        signal.confidence.total,
    )


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

    strategy = StrategyEngine(cfg, on_signal=_on_signal)
    data = MarketDataClient(
        cfg,
        on_candle=strategy.on_short_candle,
        on_long_candle=strategy.on_long_candle,
    )
    try:
        data.check_account()
    except Exception:
        log.exception("could not reach the Alpaca paper account — aborting.")
        return 1

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
