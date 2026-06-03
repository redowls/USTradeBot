"""Data ingestion (Phase 1).

Two responsibilities:

1. ``check_account`` — hit the Alpaca paper REST endpoint, confirm the account
   responds, and log a startup snapshot of equity / buying power / open
   positions (the beginning of the "reconcile against Alpaca" requirement).
2. ``MarketDataClient.run_forever`` — hold the market-data WebSocket (IEX feed),
   subscribe to the watchlist's trades, feed every tick into a
   :class:`~bot.candles.CandleAggregator`, and reconnect with exponential
   backoff if the connection drops.

The alpaca-py ``StockDataStream`` already retries transient socket drops inside
its own loop; we add backoff *between* connection attempts (via
``_BackoffStockDataStream``) and a supervisor loop that restarts the whole
stream if it crashes outright.

Factories for the trading client and stream are injectable so tests can run the
wiring without a network or real keys.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from alpaca.data.enums import DataFeed
from alpaca.data.live.stock import StockDataStream
from alpaca.trading.client import TradingClient

from bot.candles import DEFAULT_WINDOW, Candle, CandleAggregator
from bot.config import Config

log = logging.getLogger("ustradebot.data")

# Supervisor reconnect tuning.
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_CAP_SECONDS = 60.0
# A stream that stayed up at least this long counts as "healthy"; the next drop
# starts backoff over from the base delay rather than escalating forever.
HEALTHY_RUN_SECONDS = 120.0


def backoff_delay(
    attempt: int,
    *,
    base: float = BACKOFF_BASE_SECONDS,
    cap: float = BACKOFF_CAP_SECONDS,
) -> float:
    """Exponential backoff: ``base * 2**attempt``, clamped to ``cap``.

    ``attempt`` is 0-based (first retry waits ``base`` seconds).
    """
    if attempt < 0:
        attempt = 0
    return min(cap, base * (2.0**attempt))


class _BackoffStockDataStream(StockDataStream):
    """``StockDataStream`` that sleeps with exponential backoff before retrying a
    failed connect, instead of hammering reconnects in a tight loop."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._reconnect_attempt = 0

    async def _start_ws(self) -> None:  # type: ignore[override]
        try:
            await super()._start_ws()
        except Exception:
            delay = backoff_delay(self._reconnect_attempt)
            self._reconnect_attempt += 1
            log.warning(
                "market-data connect failed (attempt %d); retrying in %.0fs",
                self._reconnect_attempt,
                delay,
            )
            await asyncio.sleep(delay)
            raise
        else:
            self._reconnect_attempt = 0


class MarketDataClient:
    """Owns the Alpaca market-data WebSocket and the candle aggregator."""

    def __init__(
        self,
        cfg: Config,
        *,
        on_candle: Callable[[Candle], None] | None = None,
        on_long_candle: Callable[[Candle], None] | None = None,
        on_feed_lost: Callable[[], None] | None = None,
        on_feed_restored: Callable[[], None] | None = None,
        window: int = DEFAULT_WINDOW,
        long_window: int = DEFAULT_WINDOW,
        trading_factory: Callable[[], TradingClient] | None = None,
        stream_factory: Callable[[], StockDataStream] | None = None,
    ) -> None:
        self._cfg = cfg
        self._on_candle = on_candle
        self._on_long_candle = on_long_candle
        self._on_feed_lost = on_feed_lost
        self._on_feed_restored = on_feed_restored
        self._feed_down = False
        # Two timeframes off the same trade stream: a 1-min trigger ribbon and a
        # 5-min gate ribbon (see summary.md). Each trade feeds both aggregators.
        self.aggregator = CandleAggregator(
            interval_seconds=cfg.interval_seconds,
            window=window,
            on_close=self._handle_closed,
        )
        self.long_aggregator = CandleAggregator(
            interval_seconds=cfg.long_interval_seconds,
            window=long_window,
            on_close=self._handle_long_closed,
        )
        self._trading_factory = trading_factory or self._default_trading_client
        self._stream_factory = stream_factory or self._default_stream
        self._stream: StockDataStream | None = None
        self._stop = False

    # --- factories ---------------------------------------------------------

    def _default_trading_client(self) -> TradingClient:
        return TradingClient(
            self._cfg.alpaca_key_id,
            self._cfg.alpaca_secret,
            paper=True,
            url_override=self._cfg.alpaca_base_url,
        )

    def _default_stream(self) -> StockDataStream:
        return _BackoffStockDataStream(
            self._cfg.alpaca_key_id,
            self._cfg.alpaca_secret,
            feed=DataFeed(self._cfg.alpaca_data_feed.lower()),
        )

    # --- REST: account check / reconcile ----------------------------------

    def check_account(self):
        """Confirm the paper account responds; log equity, buying power, positions.

        Returns ``(account, positions)`` so later phases can reconcile against it.
        """
        client = self._trading_factory()
        account = client.get_account()
        log.info(
            "Alpaca paper account %s: status=%s equity=%s buying_power=%s cash=%s",
            getattr(account, "account_number", "?"),
            getattr(account, "status", "?"),
            getattr(account, "equity", "?"),
            getattr(account, "buying_power", "?"),
            getattr(account, "cash", "?"),
        )
        positions = list(client.get_all_positions())
        if positions:
            for p in positions:
                log.info(
                    "open position: %s qty=%s market_value=%s avg_entry=%s",
                    p.symbol,
                    p.qty,
                    getattr(p, "market_value", "?"),
                    getattr(p, "avg_entry_price", "?"),
                )
        else:
            log.info("no open positions.")
        return account, positions

    # --- WebSocket: stream trades -> candles ------------------------------

    async def _on_trade(self, trade) -> None:
        """Async handler invoked by the stream for each incoming trade tick."""
        # A tick arriving proves the feed is alive: clear any latched feed-loss
        # fail-safe (the first tick after a reconnect is our "back online" signal).
        if self._feed_down:
            self._mark_feed_restored()
        symbol, ts = trade.symbol, trade.timestamp
        price, size = float(trade.price), float(trade.size)
        for agg in (self.aggregator, self.long_aggregator):
            agg.add_trade(symbol, ts, price, size)
            # The freshest tick's timestamp is our wall clock: use it to close any
            # other symbol's candle whose interval has fully elapsed.
            agg.flush(ts)

    # --- feed-loss fail-safe (Phase 5) ------------------------------------

    def _mark_feed_lost(self) -> None:
        """Latch feed-down and notify once (the supervisor calls this on a crash)."""
        if self._feed_down:
            return
        self._feed_down = True
        self._fire_feed_callback(self._on_feed_lost, "on_feed_lost")

    def _mark_feed_restored(self) -> None:
        """Clear feed-down and notify once (first tick after a reconnect)."""
        if not self._feed_down:
            return
        self._feed_down = False
        self._fire_feed_callback(self._on_feed_restored, "on_feed_restored")

    @staticmethod
    def _fire_feed_callback(callback: Callable[[], None] | None, name: str) -> None:
        if callback is None:
            return
        try:
            callback()
        except Exception:  # a downstream alert bug must not kill ingestion
            log.exception("%s callback failed", name)

    def _handle_closed(self, candle: Candle) -> None:
        self._emit(candle, self._cfg.candle_interval, self._on_candle)

    def _handle_long_closed(self, candle: Candle) -> None:
        self._emit(candle, self._cfg.long_candle_interval, self._on_long_candle)

    def _emit(
        self, candle: Candle, interval: str, callback: Callable[[Candle], None] | None
    ) -> None:
        log.info(
            "candle %s [%s] %s O=%.4f H=%.4f L=%.4f C=%.4f V=%.0f n=%d",
            candle.symbol,
            interval,
            candle.start.isoformat(),
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
            candle.trades,
        )
        if callback is not None:
            try:
                callback(candle)
            except Exception:  # a downstream bug must not kill ingestion
                log.exception("candle callback failed for %s", candle.symbol)

    def _build_stream(self) -> StockDataStream:
        stream = self._stream_factory()
        stream.subscribe_trades(self._on_trade, *self._cfg.watchlist)
        return stream

    def run_forever(self, *, max_restarts: int | None = None) -> None:
        """Run the stream, restarting with backoff if it crashes.

        Returns normally when the stream stops cleanly (``stop()`` / fatal
        subscription error) or after ``max_restarts`` crash-restarts.
        """
        log.info(
            "subscribing to %s trades on the %s feed",
            ", ".join(self._cfg.watchlist),
            self._cfg.alpaca_data_feed,
        )
        attempt = 0
        restarts = 0
        while not self._stop:
            self._stream = self._build_stream()
            started = time.monotonic()
            try:
                self._stream.run()  # blocks; retries transient drops internally
            except KeyboardInterrupt:
                break
            except Exception:
                log.exception("market-data stream crashed")
                self._mark_feed_lost()  # halt new entries until ticks resume
            else:
                # A clean return means an intentional stop or a fatal error the
                # SDK won't retry (e.g. bad subscription) — don't reconnect.
                break

            if self._stop:
                break
            if time.monotonic() - started >= HEALTHY_RUN_SECONDS:
                attempt = 0  # was healthy; reset escalation
            delay = backoff_delay(attempt)
            attempt += 1
            restarts += 1
            if max_restarts is not None and restarts > max_restarts:
                log.error("giving up after %d stream restarts", restarts - 1)
                break
            log.warning("restarting market-data stream in %.0fs", delay)
            try:
                time.sleep(delay)
            except KeyboardInterrupt:
                break

    def stop(self) -> None:
        self._stop = True
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:
                log.debug("error while stopping stream", exc_info=True)
