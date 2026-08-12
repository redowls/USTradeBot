"""Historical replay harness (backtest).

Drives the bot's **real** engines — ``RibbonEngine``, ``evaluate_entry``,
``bot.sizing``, ``RiskManager`` and ``StrategyEngine`` — over historical bars, with
a simulated broker standing in for Alpaca. Nothing here reimplements the strategy:
the entry decision, confidence scoring, position sizing, trailing ratchet, EOD
flatten and stand-down all execute the same code the live service runs, so a replay
result is a statement about the shipped logic rather than about a model of it.

Fidelity limits (read these before trusting a number):

* Live candles are **activity-driven** off the trade stream; replay candles are
  regular historical 1m/5m bars from the same IEX feed. Bar boundaries therefore
  differ slightly from what the live stream produced.
* Bracket legs are filled **intrabar** from the bar's high/low. When a bar's range
  covers both the stop and the target, the replay fills the **stop** — the
  pessimistic assumption, since intrabar sequence is unknowable from OHLC.
* Fills are assumed at the exact stop/target price with **no slippage or gap-through
  modelling** inside the session, and entries fill at the signal candle's close.
* Alpaca's asynchronous order lifecycle (partial fills, rejects, the delayed-fill
  corrections behind IMP-009/IMP-010) is not simulated.

Usage::

    python -m bot.replay --days 30 [--symbols AAPL,MSFT,...] [--entry-start 09:30]

With no ``--symbols`` the universe is the enabled ``dbo.watchlist`` — the same source
the live service uses — so a bare invocation backtests what the bot actually trades.
The header line names the source it resolved.
"""
from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from bot.candles import Candle
from bot.config import Config
from bot.executor import ExecutionResult, StopOrderGone
from bot.risk import RiskManager
from bot.sizing import plan_model_a, plan_model_b
from bot.strategy import StrategyEngine

log = logging.getLogger("ustradebot.replay")


@dataclass
class SimFill:
    """A resting bracket leg that the simulated broker has filled."""

    order_id: str
    price: float
    leg: str  # "stop" | "target"
    at: datetime


@dataclass
class SimTrade:
    symbol: str
    entry_time: datetime
    entry_price: float
    qty: int
    notional: float
    stop_price: float
    target_price: float
    confidence: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_reason: str = ""

    @property
    def pnl(self) -> float:
        if self.exit_price is None:
            return 0.0
        return (self.exit_price - self.entry_price) * self.qty

    @property
    def pnl_pct(self) -> float:
        if self.exit_price is None or not self.entry_price:
            return 0.0
        return (self.exit_price / self.entry_price - 1.0) * 100.0


class SimBroker:
    """Implements the executor contract that ``StrategyEngine`` and ``RiskManager``
    call, backed by simulated fills instead of Alpaca.

    Sizing runs through the real :mod:`bot.sizing` models, so allocation, the
    confidence ramp and the IMP-013 cap all behave exactly as they do live.
    """

    def __init__(self, cfg: Config, *, equity: float, margin_multiple: float = 4.0):
        self._cfg = cfg
        self.equity = equity
        self.last_equity = equity
        self._margin = margin_multiple
        self._seq = 0
        self.open_positions: dict[str, ExecutionResult] = {}
        # stop-leg order id (including ids minted by a trailing replace) -> live stop price
        self._stop_price: dict[str, float] = {}
        self._stop_owner: dict[str, str] = {}  # stop-leg id -> symbol
        self._filled: dict[str, SimFill] = {}  # symbol -> the leg that filled
        self._entry_fill: dict[str, float] = {}  # entry order id -> fill price
        self._entry_filled_at: dict[str, datetime] = {}  # entry order id -> fill time
        self._close_fill: dict[str, float] = {}  # close order id -> fill price
        self.trades: list[SimTrade] = []
        self._live: dict[str, SimTrade] = {}
        self._mark: dict[str, float] = {}  # symbol -> last seen close
        self.now: datetime | None = None

    # --- capital -----------------------------------------------------------
    @property
    def buying_power(self) -> float:
        deployed = sum(p.qty * p.entry_price for p in self.open_positions.values())
        return max(0.0, self.equity * self._margin - deployed)

    def _next_id(self, kind: str) -> str:
        self._seq += 1
        return f"{kind}-{self._seq}"

    # --- executor contract -------------------------------------------------
    def execute(self, *, symbol: str, entry_price: float, confidence: float):
        self.last_equity = self.equity
        common = dict(
            confidence=confidence,
            entry_price=entry_price,
            buying_power=self.buying_power,
            threshold=self._cfg.entry_threshold,
            max_alloc=self._cfg.max_alloc,
            stop_loss=self._cfg.stop_loss,
            take_profit=self._cfg.take_profit,
            size_confidence_cap=self._cfg.size_confidence_cap,
        )
        if self._cfg.sizing_model == "A":
            plan = plan_model_a(min_alloc=self._cfg.min_alloc, **common)
        else:
            plan = plan_model_b(
                equity=self.equity,
                max_risk_per_trade=self._cfg.max_risk_per_trade,
                **common,
            )
        if plan is None:
            return None
        if plan.notional > self.buying_power:
            return None  # not enough capital left — the live account would reject too

        oid = self._next_id("entry")
        stop_oid = self._next_id("stop")
        self._entry_fill[oid] = plan.entry_price
        self._entry_filled_at[oid] = self.now  # simulated clock: entries fill at the bar
        self._stop_price[stop_oid] = plan.stop_price
        self._stop_owner[stop_oid] = symbol
        result = ExecutionResult(
            symbol=symbol,
            order_id=oid,
            qty=plan.qty,
            notional=plan.notional,
            entry_price=plan.entry_price,
            stop_price=plan.stop_price,
            take_profit_price=plan.take_profit_price,
            confidence=confidence,
            status="filled",
            model=plan.model,
            stop_order_id=stop_oid,
        )
        self.open_positions[symbol] = result
        self._live[symbol] = SimTrade(
            symbol=symbol,
            entry_time=self.now,
            entry_price=plan.entry_price,
            qty=plan.qty,
            notional=plan.notional,
            stop_price=plan.stop_price,
            target_price=plan.take_profit_price,
            confidence=confidence,
        )
        return result

    def replace_stop_price(self, order_id: str, new_price: float) -> str | None:
        symbol = self._stop_owner.get(order_id)
        if symbol is not None and symbol in self._filled:
            raise StopOrderGone(f"{order_id} already filled")
        if order_id not in self._stop_price:
            return None
        new_id = self._next_id("stop")
        self._stop_price.pop(order_id)
        self._stop_price[new_id] = new_price
        self._stop_owner[new_id] = symbol
        return new_id

    def close_position(self, symbol: str) -> str | None:
        if symbol in self._filled:
            return None  # a bracket leg already filled — caller reconciles the real exit
        pos = self.open_positions.get(symbol)
        if pos is None:
            return None
        oid = self._next_id("close")
        self._close_fill[oid] = self._mark.get(symbol, pos.entry_price)
        return oid

    def reconcile_exit(self, symbol: str, *, after: datetime | None = None):
        # `after` is the live IMP-027 recency guard's anchor. The simulator books each
        # fill against the position that produced it, so a prior trade's sell can never
        # be offered here and there is nothing to filter — accepted for signature parity.
        fill = self._filled.get(symbol)
        if fill is None:
            return None
        return fill.order_id, fill.price

    def entry_filled_at(self, order_id: str) -> datetime | None:
        return self._entry_filled_at.get(order_id)

    def close_fill_price(self, order_id: str) -> float | None:
        return self._close_fill.get(order_id)

    def entry_fill_price(self, order_id: str) -> float | None:
        return self._entry_fill.get(order_id)

    # --- simulation ---------------------------------------------------------
    def on_bar(self, candle: Candle) -> None:
        """Fill resting bracket legs intrabar, before the strategy sees the bar."""
        self._mark[candle.symbol] = candle.close
        pos = self.open_positions.get(candle.symbol)
        if pos is None or candle.symbol in self._filled:
            return
        live = self._live.get(candle.symbol)
        if live is None or candle.start <= live.entry_time:
            return  # a position cannot be stopped on its own entry bar
        stop_oid = next(
            (k for k, s in self._stop_owner.items() if s == candle.symbol and k in self._stop_price),
            None,
        )
        stop = self._stop_price.get(stop_oid) if stop_oid else pos.stop_price
        # Pessimistic: when the bar covers both legs, assume the stop filled first.
        if stop is not None and candle.low <= stop:
            self._filled[candle.symbol] = SimFill(self._next_id("fill"), stop, "stop", candle.start)
        elif candle.high >= pos.take_profit_price:
            self._filled[candle.symbol] = SimFill(
                self._next_id("fill"), pos.take_profit_price, "target", candle.start
            )

    def book_exit(self, symbol: str, exit_price: float, reason: str) -> None:
        """Called from the RiskManager's on_exit hook — settle P&L and free capital."""
        live = self._live.pop(symbol, None)
        self.open_positions.pop(symbol, None)
        for k, s in list(self._stop_owner.items()):
            if s == symbol:
                self._stop_owner.pop(k, None)
                self._stop_price.pop(k, None)
        self._filled.pop(symbol, None)
        if live is None:
            return
        live.exit_time = self.now
        live.exit_price = exit_price
        live.exit_reason = reason
        self.equity += live.pnl
        self.trades.append(live)


def _to_candle(symbol: str, row) -> Candle:
    return Candle(
        symbol=symbol,
        start=row[0],
        open=row[1],
        high=row[2],
        low=row[3],
        close=row[4],
        volume=row[5],
        trades=row[6],
    )


def fetch_bars(cfg: Config, symbols, start: datetime, end: datetime):
    """(1m, 5m) bars per symbol from the same IEX feed the live stream uses."""
    from alpaca.data.enums import DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    client = StockHistoricalDataClient(cfg.alpaca_key_id, cfg.alpaca_secret)
    feed = DataFeed.IEX if cfg.alpaca_data_feed.lower() == "iex" else DataFeed.SIP
    out = {}
    for tf, key in (
        (TimeFrame(1, TimeFrameUnit.Minute), "short"),
        (TimeFrame(5, TimeFrameUnit.Minute), "long"),
    ):
        df = client.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=list(symbols), timeframe=tf, start=start, end=end, feed=feed
            )
        ).df.reset_index()
        by = defaultdict(list)
        for r in df.itertuples():
            by[r.symbol].append(
                _to_candle(
                    r.symbol,
                    (
                        r.timestamp.to_pydatetime().astimezone(UTC),
                        float(r.open),
                        float(r.high),
                        float(r.low),
                        float(r.close),
                        float(r.volume),
                        int(getattr(r, "trade_count", 0) or 0),
                    ),
                )
            )
        out[key] = by
    return out["short"], out["long"]


LONG, SHORT = 1, 2  # stream kinds; ordered so a gate bar folds before a trigger bar


def build_stream(symbols, short_bars, long_bars, start: datetime, end: datetime,
                 long_interval_seconds: int):
    """Interleave gate (5m) and trigger (1m) bars into the order live would see them.

    Returns ``(effective_time, kind, candle)`` tuples sorted by both, where *kind*
    is :data:`LONG` or :data:`SHORT`. Capital contention is therefore real: every
    symbol's bars compete for buying power in true chronological order.

    A gate bar is sequenced at its **close**, not its start (IMP-024). Live, a
    candle is emitted only once a trade lands in a later bucket, so the 5m bar
    spanning 14:45-14:50 first reaches ``on_long_candle`` at 14:50 — every 1m
    trigger bar from 14:45 to 14:49 is judged against gate data ending at 14:45.
    Keying the gate bar at ``candle.start`` handed the gate ribbon (and with it
    the IMP-022 market filter) a full gate interval of lookahead on every trigger
    bar. ``LONG`` sorts ahead of ``SHORT`` at equal stamps, which is also live's
    order: the 5m closing at 14:50 is folded before the 1m bar starting at 14:50
    is evaluated at 14:51.

    Both ends are filtered here, not only at fetch time — a pre-fetched ``bars``
    pair is usually wider than the requested window (a sweep fetches once and
    replays sub-windows), and letting bars past ``end`` through would silently
    replay the full span instead of the slice asked for. The window test stays on
    ``candle.start`` for both timeframes so the set of bars replayed is unchanged
    by the close-time sequencing; only their order moves.
    """
    long_step = timedelta(seconds=long_interval_seconds)
    stream = []
    for sym in symbols:
        stream += [
            (c.start + long_step, LONG, c)
            for c in long_bars.get(sym, [])
            if start <= c.start < end
        ]
        stream += [
            (c.start, SHORT, c) for c in short_bars.get(sym, []) if start <= c.start < end
        ]
    stream.sort(key=lambda x: (x[0], x[1]))
    return stream


def run_replay(cfg: Config, symbols, start: datetime, end: datetime, *, equity: float,
               warmup_days: int = 5, bars=None):
    """Replay ``symbols`` over ``[start, end)`` and return the simulated broker.

    ``bars`` optionally supplies a pre-fetched ``(short, long)`` pair so a parameter
    sweep pays the download cost once instead of per variant.
    """
    if bars is None:
        fetch_start = start - timedelta(days=warmup_days + 4)
        bars = fetch_bars(cfg, symbols, fetch_start, end)
    short_bars, long_bars = bars

    broker = SimBroker(cfg, equity=equity)
    risk = RiskManager(cfg, executor=broker,
                       on_exit=lambda r: broker.book_exit(r.symbol, r.exit_price, r.reason))
    strat = StrategyEngine(cfg, executor=broker, risk=risk)

    # Warm the ribbons on pre-window history exactly as bot.warmup does live.
    for sym in symbols:
        for c in (c for c in long_bars.get(sym, []) if c.start < start):
            strat.on_long_candle(c)
        for c in (c for c in short_bars.get(sym, []) if c.start < start):
            strat.warmup_trigger(c)

    stream = build_stream(
        symbols, short_bars, long_bars, start, end, cfg.long_interval_seconds
    )

    for ts, kind, candle in stream:
        broker.now = ts
        if kind == LONG:
            strat.on_long_candle(candle)
            continue
        broker.on_bar(candle)  # resting bracket legs fill intrabar first
        strat.on_short_candle(candle)

    # Settle anything still open at the end of the window at its last mark.
    for sym in list(broker.open_positions):
        px = broker._mark.get(sym, broker.open_positions[sym].entry_price)
        risk.exit_position(sym, px, "replay window ended", broker.open_positions[sym])
    return broker


def summarize(broker: SimBroker, equity0: float) -> str:
    T = broker.trades
    if not T:
        return "no trades"
    net = sum(t.pnl for t in T)
    wins = [t for t in T if t.pnl > 0]
    gross_loss = abs(sum(t.pnl for t in T if t.pnl <= 0))
    gross_win = sum(t.pnl for t in wins)
    by = defaultdict(lambda: [0, 0.0])
    for t in T:
        by[t.exit_reason][0] += 1
        by[t.exit_reason][1] += t.pnl
    lines = [
        f"trades={len(T)}  net={net:+.2f} ({net / equity0 * 100:+.2f}%)  "
        f"win%={len(wins) / len(T) * 100:.1f}  "
        f"PF={gross_win / gross_loss if gross_loss else float('inf'):.2f}  "
        f"avg={net / len(T):+.2f}",
        f"final equity={broker.equity:,.2f}",
        "exit reasons:",
    ]
    lines += [f"  {k:<52} n={c:>3} net={p:>+9.2f}"
              for k, (c, p) in sorted(by.items(), key=lambda kv: kv[1][1])]
    return "\n".join(lines)


def resolve_symbols(cfg: Config, explicit: str = "") -> tuple[list[str], str]:
    """Pick the replay universe the way the **live service** picks it (IMP-023).

    Precedence mirrors ``bot.main``: an explicit ``--symbols`` wins, otherwise the
    enabled rows of ``dbo.watchlist``, otherwise the ``WATCHLIST`` env var. Returns
    ``(symbols, source)`` so the caller can print which one was used.

    Why this exists: ``WATCHLIST`` is a three-name bootstrap stub (``NFLX,BIRD,WPM``,
    two of them long since parked) that the live bot overwrites from the DB on every
    start. Defaulting the harness to it meant a bare ``python -m bot.replay`` silently
    backtested a universe the bot has never traded — and, because the market-filter
    symbol was absent from the stub, the IMP-022 gate **failed open in both arms** of an
    A/B, making the filter look like a no-op. A backtest that quietly disagrees with the
    deployed watchlist is worse than no backtest, because it is trusted.
    """
    symbols = [s.strip().upper() for s in explicit.split(",") if s.strip()]
    if symbols:
        return symbols, "--symbols"

    # Local import: the harness stays usable (on the env fallback) in environments
    # without the DB driver installed, exactly like persistence is optional live.
    try:
        from bot.persistence import open_store

        store = open_store(cfg)
    except Exception:  # pragma: no cover - driver missing / unimportable
        log.exception("could not open the trade store — falling back to WATCHLIST env")
        store = None

    if store is not None:
        try:
            db_watchlist = store.load_watchlist()
        finally:
            store.close()
        if db_watchlist:
            return list(db_watchlist), "dbo.watchlist"

    log.warning(
        "dbo.watchlist empty or unavailable — replaying the WATCHLIST env var (%s), "
        "which is NOT what the live bot trades",
        ",".join(cfg.watchlist),
    )
    return list(cfg.watchlist), "WATCHLIST env"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Replay the live strategy over historical bars.")
    ap.add_argument("--days", type=int, default=30, help="window length ending now (default 30)")
    ap.add_argument("--symbols", default="", help="comma-separated; default = enabled watchlist")
    ap.add_argument("--equity", type=float, default=10_000.0, help="starting equity")
    ap.add_argument("--entry-start", default=None, help="override ENTRY_START, e.g. 09:30")
    ap.add_argument("--trail-percent", default=None, help="override TRAIL_PERCENT, e.g. 0.01")
    ap.add_argument("--take-profit", default=None, help="override TAKE_PROFIT, e.g. 0.03")
    ap.add_argument("--stop-loss", default=None, help="override STOP_LOSS, e.g. 0.02")
    ap.add_argument("--quiet", action="store_true", help="silence the strategy's own logging")
    args = ap.parse_args(argv)

    import os

    for flag, key in (
        (args.entry_start, "ENTRY_START"),
        (args.trail_percent, "TRAIL_PERCENT"),
        (args.take_profit, "TAKE_PROFIT"),
        (args.stop_loss, "STOP_LOSS"),
    ):
        if flag is not None:
            os.environ[key] = flag
    if args.quiet:
        logging.disable(logging.CRITICAL)

    cfg = Config.load()
    symbols, source = resolve_symbols(cfg, args.symbols)
    end = datetime.now(UTC)
    start = end - timedelta(days=args.days)
    broker = run_replay(cfg, symbols, start, end, equity=args.equity)
    print(f"window {start.date()} -> {end.date()}  symbols={len(symbols)} ({source})  "
          f"entry_start={cfg.entry_start:%H:%M} trail={cfg.trail_percent} "
          f"tp={cfg.take_profit} stop={cfg.stop_loss}")
    print(summarize(broker, args.equity))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
