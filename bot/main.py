"""Entrypoint.

Phase 0 scaffold: load config, set up logging, and confirm the environment is wired
correctly. The data feed, indicator engine, executor, and risk manager arrive in
later phases (see todo.md). The full state machine will live here:

    WAITING -> EVALUATING -> EXECUTING -> MANAGING
"""

from __future__ import annotations

import logging

from bot.config import Config, ConfigError


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
    log = logging.getLogger("ustradebot")
    log.info("USTradeBot starting (paper). Watchlist: %s", ", ".join(cfg.watchlist))
    log.info(
        "Strategy: EMA %d/%d, trend %d, RSI %d, entry>=%.0f%%",
        cfg.fast_ma_period,
        cfg.slow_ma_period,
        cfg.trend_ma_period,
        cfg.rsi_period,
        cfg.entry_threshold,
    )
    log.info("Config loaded and validated. (Data feed not yet implemented — Phase 1.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
