"""Entrypoint.

Loads config, sets up logging, confirms the paper account responds, then holds
the market-data WebSocket, aggregates ticks into candles (Phase 1), and feeds
each closed candle to the indicator engine (Phase 2). The executor and risk
manager arrive in later phases (see todo.md). The full state machine will live
here:

    WAITING -> EVALUATING -> EXECUTING -> MANAGING
"""

from __future__ import annotations

import logging

from bot.candles import Candle
from bot.config import Config, ConfigError
from bot.indicators import IndicatorEngine, IndicatorSnapshot
from bot.market_data import MarketDataClient

log = logging.getLogger("ustradebot")


def _log_snapshot(snap: IndicatorSnapshot) -> None:
    if not snap.ready:
        return  # still warming up indicator history for this symbol
    log.info(
        "indicators %s C=%.4f fast=%.4f slow=%.4f trend=%.4f rsi=%.1f vol=%.0f avgvol=%.0f",
        snap.symbol,
        snap.close,
        snap.fast_ema,
        snap.slow_ema,
        snap.trend_ma,
        snap.rsi,
        snap.volume,
        snap.avg_volume,
    )


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
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
        "Strategy: EMA %d/%d, trend %d, RSI %d, entry>=%.0f%%",
        cfg.fast_ma_period,
        cfg.slow_ma_period,
        cfg.trend_ma_period,
        cfg.rsi_period,
        cfg.entry_threshold,
    )

    engine = IndicatorEngine.from_config(cfg)

    def on_candle(candle: Candle) -> None:
        _log_snapshot(engine.update(candle))

    data = MarketDataClient(cfg, on_candle=on_candle)
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
