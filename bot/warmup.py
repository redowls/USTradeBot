"""Startup indicator warmup.

The live :class:`~bot.market_data.MarketDataClient` builds candles from the trade
stream, so after every restart the strategy's ribbons start empty and the bot
cannot trade until the slow EMAs warm up — ~3.5h for the 55-period 5m gate. Since
the daily-review routine restarts the service every evening, that blind window
recurs *every trading day*, suppressing morning entries.

This module replays recent historical bars through the strategy's indicator state
(``warmup_gate`` for the 5m gate, ``warmup_trigger`` for the 1m trigger) so the
first live candle can already produce an entry. Warmup never trades — both sinks
only fold candles into indicator state, and (IMP-032) neither emits an
observation, so replayed history never reaches the database as if it were live.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime, timedelta

from bot.candles import Candle
from bot.config import Config

log = logging.getLogger("ustradebot.warmup")

FetchBars = Callable[[str], Iterable[Candle]]


def warm_up(strategy, symbols: Sequence[str], *, fetch_short: FetchBars,
            fetch_long: FetchBars) -> int:
    """Pre-seed ``strategy``'s ribbons from historical bars; never places orders.

    ``fetch_long(symbol)`` yields closed 5m gate candles and ``fetch_short(symbol)``
    yields closed 1m trigger candles, both oldest-first. Returns the number of
    symbols primed. Both sinks are the *warmup* variants, which update indicator
    state only — they never emit a signal, a refusal or a gate sample.
    """
    primed = 0
    for symbol in symbols:
        long_bars = list(fetch_long(symbol))
        for candle in long_bars:
            strategy.warmup_gate(candle)
        short_bars = list(fetch_short(symbol))
        for candle in short_bars:
            strategy.warmup_trigger(candle)
        if long_bars or short_bars:
            primed += 1
        log.debug("warmed %s: %d gate + %d trigger bars", symbol, len(long_bars),
                  len(short_bars))
    log.info("warmup primed %d/%d symbols from history", primed, len(symbols))
    return primed


def alpaca_fetchers(cfg: Config, lookback_days: int) -> tuple[FetchBars, FetchBars]:
    """Build (fetch_short, fetch_long) backed by Alpaca's historical bars REST API.

    Bars are requested per-call from the same IEX feed the live stream uses, so the
    warmed ribbons match what the live stream would have produced. ``lookback_days``
    of calendar history comfortably covers the 56 5m bars the gate needs even across
    a weekend/holiday gap.
    """
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    client = StockHistoricalDataClient(cfg.alpaca_key_id, cfg.alpaca_secret)
    feed = cfg.alpaca_data_feed

    def _fetch(symbol: str, timeframe) -> list[Candle]:
        start = datetime.now(UTC) - timedelta(days=lookback_days)
        req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=timeframe,
                               start=start, feed=feed)
        try:
            barset = client.get_stock_bars(req)
        except Exception:  # a warmup fetch failure must not block startup
            log.exception("warmup fetch failed for %s", symbol)
            return []
        out: list[Candle] = []
        for b in barset.data.get(symbol, []):
            out.append(Candle(
                symbol=symbol, start=b.timestamp.astimezone(UTC),
                open=float(b.open), high=float(b.high), low=float(b.low),
                close=float(b.close), volume=float(b.volume),
                trades=int(getattr(b, "trade_count", 0) or 0),
            ))
        return out

    five_min = TimeFrame(5, TimeFrameUnit.Minute)
    return (
        lambda s: _fetch(s, TimeFrame.Minute),
        lambda s: _fetch(s, five_min),
    )
