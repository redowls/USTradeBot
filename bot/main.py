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
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import TypeVar

from bot.config import Config, ConfigError
from bot.executor import ExecutionResult, OrderExecutor
from bot.market_data import MarketDataClient
from bot.notifier import AlertReporter, open_notifier
from bot.persistence import TradeRecorder, open_store
from bot.risk import ExitResult, RiskManager
from bot.strategy import StrategyEngine, TradeSignal
from bot.warmup import alpaca_fetchers, warm_up

log = logging.getLogger("ustradebot")

_T = TypeVar("_T")

# How often the EOD-flatten watchdog wakes. The flatten window is minutes wide and
# the escalation runway is the final ~2 minutes, so a 30s tick gives several flatten
# attempts inside it even if the candle feed is dead.
_WATCHDOG_INTERVAL_SEC = 30.0


def _run_flatten_watchdog(strategy: StrategyEngine, stop: threading.Event) -> None:
    """Drive the strategy's wall-clock EOD flatten on a fixed cadence.

    Decouples the safety-critical flatten from the live candle stream: even if the
    IEX websocket goes silent through the close (observed 2026-06-19, naked weekend
    carry), this guarantees the flatten + naked-overnight escalation still run on real
    time. Errors are swallowed so a transient Alpaca failure can't kill the thread —
    the next tick retries.
    """
    while not stop.wait(_WATCHDOG_INTERVAL_SEC):
        try:
            strategy.tick(datetime.now(UTC))
        except Exception:  # a watchdog tick must never die — the next one retries
            log.exception("EOD flatten watchdog tick failed")


def _chain(*callbacks: Callable[[_T], None] | None) -> Callable[[_T], None]:
    """Fan one event out to several sinks; one sink's failure never stops the rest."""
    sinks = [c for c in callbacks if c is not None]

    def run(arg: _T) -> None:
        for sink in sinks:
            try:
                sink(arg)
            except Exception:  # a logging/DB sink must not kill the trading path
                log.exception("event sink %r failed", sink)

    return run


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
    """Feed-loss/restore alert sink (Phase 5); also pushed to Telegram (Phase 7)."""
    log.warning("FEED ALERT: %s", message)


def main() -> int:
    try:
        cfg = Config.load()
    except ConfigError as e:
        # Logging may not be configured yet; print is fine for a fatal startup error.
        print(f"FATAL: configuration error: {e}")
        return 1

    setup_logging(cfg.log_level)

    # Persistence (Phase 6): a TradeRecorder logs entries/exits + confidence to SQL
    # Server. It rides alongside the existing log sinks via _chain; if SQLSERVER_CONN
    # is unset or the DB is unreachable, open_store returns None and the bot trades on.
    store = open_store(cfg)

    # The watchlist is sourced from dbo.watchlist when the DB is available and the
    # table is non-empty; otherwise we keep the WATCHLIST env var (cfg.watchlist), so
    # the DB stays an optional side-channel even though the watchlist is critical-path.
    watchlist_source = "WATCHLIST env"
    if store is not None:
        db_watchlist = store.load_watchlist()
        if db_watchlist:
            cfg = replace(cfg, watchlist=db_watchlist)
            watchlist_source = "dbo.watchlist"
        else:
            log.info("dbo.watchlist empty or unavailable — using WATCHLIST env var")

    log.info(
        "USTradeBot starting (paper). Watchlist (%s): %s",
        watchlist_source,
        ", ".join(cfg.watchlist),
    )
    log.info(
        "Strategy: %s ribbon %s (trigger) gated by %s ribbon %s, RSI %d, entry>=%.0f%%",
        cfg.candle_interval,
        "/".join(map(str, cfg.short_ma_periods)),
        cfg.long_candle_interval,
        "/".join(map(str, cfg.long_ma_periods)),
        cfg.rsi_period,
        cfg.entry_threshold,
    )

    recorder = TradeRecorder(store) if store is not None else None
    rec_signal = recorder.on_signal if recorder else None
    rec_result = recorder.on_result if recorder else None
    rec_exit = recorder.on_exit if recorder else None

    # Telegram alerts (Phase 7): an AlertReporter rides the same callbacks, fanned
    # in via _chain. open_notifier returns None if Telegram isn't configured, and a
    # failed POST is swallowed — alerts are a side-channel, never the trading path.
    notifier = open_notifier(cfg)
    reporter = AlertReporter(notifier) if notifier is not None else None
    alert_result = reporter.on_result if reporter else None
    alert_exit = reporter.on_exit if reporter else None
    alert_feed = reporter.on_feed_alert if reporter else None

    executor = OrderExecutor(cfg, on_result=_chain(_on_execution, rec_result, alert_result))
    risk = RiskManager(
        cfg,
        executor=executor,
        on_exit=_chain(_on_exit, rec_exit, alert_exit),
        on_feed_alert=_chain(_on_feed_alert, alert_feed),
    )
    strategy = StrategyEngine(
        cfg, on_signal=_chain(_on_signal, rec_signal), executor=executor, risk=risk
    )
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
    if store is not None:
        # Inverse reconcile: close DB rows left OPEN that the broker no longer holds
        # (phantom positions). Bookkeeping only — keeps the book honest so reports and
        # the EOD flatten don't act on positions that aren't really there.
        store.reconcile_open_positions({p.symbol for p in positions})

    # Indicator warmup: replay recent history through the ribbons so the bot can trade
    # from the open instead of waiting hours for the live stream to seed the 55-period
    # 5m gate (the daily restart otherwise reopens that blind window every session). A
    # warmup fetch failure is swallowed inside warm_up — the bot just starts cold.
    if cfg.warmup_lookback_days > 0:
        fetch_short, fetch_long = alpaca_fetchers(cfg, cfg.warmup_lookback_days)
        warm_up(strategy, cfg.watchlist, fetch_short=fetch_short, fetch_long=fetch_long)

    # Wall-clock EOD-flatten watchdog: fires the flatten on real time so a silent /
    # stalled candle feed at the close can't leave positions naked overnight.
    stop_watchdog = threading.Event()
    watchdog = threading.Thread(
        target=_run_flatten_watchdog,
        args=(strategy, stop_watchdog),
        name="eod-flatten-watchdog",
        daemon=True,
    )
    watchdog.start()

    try:
        data.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_watchdog.set()
        data.stop()
        if store is not None:
            store.close()
    log.info("USTradeBot stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
