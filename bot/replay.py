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
* Gap-through is not modelled: a leg that the bar's range covers fills at the leg
  price plus friction, never at the (worse) open of a gapping bar.
* Alpaca's asynchronous order lifecycle (partial fills, rejects, the delayed-fill
  corrections behind IMP-009/IMP-010) is not simulated.

Friction (IMP-044): every fill pays ``--slippage-bps`` per side, **10 bps (0.10%) by
default** — buys fill above the price that triggered them, sells below it. Until
2026-09-08 this harness was frictionless, and that single omission explains the
expectancy gap the 09-04 weekly could not close: on the config-matched 30d window
live booked **+$5.17/trade** against replay's **+$9.43**, ≈$4 on ~$2,000 of notional,
≈0.2% per round trip — an entirely ordinary market-order cost. A frictionless harness
does not merely inflate every net; it **systematically over-rewards high-frequency,
scratch-heavy configs**, because friction is charged per trade while this strategy's
edge is not. With 88–94% of trades scratching near break-even, friction is not a
rounding error, it is the P&L. ``--slippage-bps 0`` reproduces the old numbers exactly
when an old result has to be re-derived; nothing else should use it.

Scoring (IMP-043): the summary reports the **stop-exit doctrine** — stop rate, the
WIN/SCRATCH/FAIL split and the true win rate — beside the headline ``pnl > 0`` win
rate, using the same :mod:`bot.doctrine` classifier the live report uses. Until
2026-09-07 this harness graded a win as ``pnl > 0``, the exact test the doctrine
exists to abolish, while acting as the court of appeal for live verdicts: the live
book was scored honestly (IMP-039) and the backtest was not, so a config could look
like a 62% winner here and a 12% winner there on identical trade quality. Reading
both numbers off one summary is what stops that happening again.

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
from bot.doctrine import format_stop_exits
from bot.doctrine import summarize as summarize_stop_exits
from bot.doctrine import verdicts_for
from bot.executor import ExecutionResult, StopOrderGone
from bot.risk import RiskManager
from bot.sizing import plan_model_a, plan_model_b
from bot.strategy import StrategyEngine

log = logging.getLogger("ustradebot.replay")

# Per-side spread/slippage charged on every simulated fill, in basis points.
# 10 bps/side = 0.20% per round trip, which is what the 09-04 weekly measured as the
# live-vs-replay expectancy gap (≈$4 on ~$2,000 notional, 30d config-matched window).
# It is a default rather than a config key on purpose: friction is a property of the
# *simulation*, not of the deployed strategy, so it must never reach `.env`.
DEFAULT_SLIPPAGE_BPS = 10.0


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
    # Per-side friction rate this trade was filled under (IMP-044). Stored on the row
    # so `gross_pnl` can invert it exactly instead of the broker keeping a parallel
    # ledger of pre-slippage prices that a mis-ordered exit path could desynchronise.
    slippage: float = 0.0

    @property
    def pnl(self) -> float:
        """Realized P&L **net of friction** — the number every summary reports."""
        if self.exit_price is None:
            return 0.0
        return (self.exit_price - self.entry_price) * self.qty

    @property
    def gross_pnl(self) -> float:
        """What the frictionless harness would have reported for this same trade.

        Exact rather than approximate: friction is a fixed multiplicative markup on
        every fill, so dividing it back out recovers the untouched price.
        """
        if self.exit_price is None:
            return 0.0
        entry_ideal = self.entry_price / (1.0 + self.slippage)
        exit_ideal = self.exit_price / (1.0 - self.slippage)
        return (exit_ideal - entry_ideal) * self.qty

    @property
    def friction(self) -> float:
        """Dollars the round trip's spread/slippage cost. Never negative."""
        return self.gross_pnl - self.pnl

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

    def __init__(
        self,
        cfg: Config,
        *,
        equity: float,
        margin_multiple: float = 4.0,
        slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    ):
        self._cfg = cfg
        self.equity = equity
        self.last_equity = equity
        self._margin = margin_multiple
        self.slippage = slippage_bps / 10_000.0
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

    # --- friction (IMP-044) -------------------------------------------------
    # Applied to the *fill*, never to the trigger: a stop still triggers when the bar
    # trades through it, and then fills worse — which is what a stop order does. The
    # bracket legs and the sized quantity stay anchored to the signal-candle price
    # because that is what the live bot submits before it knows its own fill price.
    def _buy_fill(self, price: float) -> float:
        return price * (1.0 + self.slippage)

    def _sell_fill(self, price: float) -> float:
        return price * (1.0 - self.slippage)

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
        fill = self._buy_fill(plan.entry_price)
        self._entry_fill[oid] = fill
        self._entry_filled_at[oid] = self.now  # simulated clock: entries fill at the bar
        self._stop_price[stop_oid] = plan.stop_price
        self._stop_owner[stop_oid] = symbol
        result = ExecutionResult(
            symbol=symbol,
            order_id=oid,
            qty=plan.qty,
            notional=plan.notional,
            entry_price=fill,
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
            entry_price=fill,
            qty=plan.qty,
            notional=plan.notional,
            stop_price=plan.stop_price,
            target_price=plan.take_profit_price,
            confidence=confidence,
            slippage=self.slippage,
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
        self._close_fill[oid] = self._sell_fill(self._mark.get(symbol, pos.entry_price))
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
            # Hand back the stop leg's OWN id — the ratcheted one once the trail has moved,
            # exactly as Alpaca does. Minting a fresh synthetic id here would leave the
            # RiskManager unable to recognise its own stop, so every simulated exit would
            # collapse into the IMP-038 catch-all and replay could not answer the very
            # question the trail-retune study runs it for (trail hit vs -2% stop-out).
            self._filled[candle.symbol] = SimFill(
                stop_oid or pos.stop_order_id, self._sell_fill(stop), "stop", candle.start
            )
        elif candle.high >= pos.take_profit_price:
            self._filled[candle.symbol] = SimFill(
                self._next_id("fill"),
                self._sell_fill(pos.take_profit_price),
                "target",
                candle.start,
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
               warmup_days: int = 5, bars=None,
               slippage_bps: float = DEFAULT_SLIPPAGE_BPS):
    """Replay ``symbols`` over ``[start, end)`` and return the simulated broker.

    ``bars`` optionally supplies a pre-fetched ``(short, long)`` pair so a parameter
    sweep pays the download cost once instead of per variant.
    """
    if bars is None:
        fetch_start = start - timedelta(days=warmup_days + 4)
        bars = fetch_bars(cfg, symbols, fetch_start, end)
    short_bars, long_bars = bars

    broker = SimBroker(cfg, equity=equity, slippage_bps=slippage_bps)
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


def summarize(broker: SimBroker, equity0: float, *, stop_loss: float | None = None) -> str:
    """Format a replay run — money on the headline, trade quality underneath.

    ``win%``/``PF``/``net`` stay exactly as they were: they are money, and money was
    never the thing ``pnl > 0`` got wrong. What it got wrong was calling a scratch a
    win, so the doctrine block sits directly beneath them (IMP-043). ``stop_loss``
    is the fallback 1R width for rows whose bracket stop is missing; it defaults to
    the config the simulated broker was built with, so callers that already have a
    ``Config`` need not thread it through.
    """
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
    ]
    # Friction sits directly under the money line because it is the difference between
    # this result and every result this harness produced before 2026-09-08 (IMP-044).
    # Showing gross beside net makes an old frictionless figure directly comparable
    # instead of silently incommensurable.
    friction = sum(t.friction for t in T)
    gross = sum(t.gross_pnl for t in T)
    lines.append(
        f"friction={friction:,.2f} ({broker.slippage * 10_000:.0f} bps/side, "
        f"{friction / len(T):.2f}/trade)  gross={gross:+.2f} -> net={net:+.2f}"
        + (f"  [{friction / abs(gross) * 100:.0f}% of gross]" if gross else "")
    )
    # SimTrade.stop_price/target_price are written once at entry and never mutated —
    # the trail ratchets the broker's own order book, not the trade row — so they are
    # the original 1R anchor, exactly like dbo.trades.stop_price live. That is what
    # makes the live and replay R denominators the same measurement.
    if stop_loss is None:
        stop_loss = broker._cfg.stop_loss
    stops = summarize_stop_exits(verdicts_for(T, stop_loss))
    lines.append(format_stop_exits(stops))
    # F+S is the escalation metric (>= 60% over three sessions indicts the entry). The
    # live report shows it per-session; here the whole window is the population, so it
    # belongs on the summary rather than being re-derived by hand from the split.
    lines.append(
        f"⚠️ FAIL+SCRATCH: {stops.fails + stops.scratches}/{stops.trades} "
        f"({stops.fail_scratch_rate * 100:.0f}%)"
    )
    lines.append("exit reasons:")
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
    ap.add_argument("--slippage-bps", type=float, default=DEFAULT_SLIPPAGE_BPS,
                    help="per-side spread/slippage on every fill (default 10 = 0.20%% "
                         "round trip); 0 reproduces the pre-IMP-044 frictionless runs")
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
    broker = run_replay(cfg, symbols, start, end, equity=args.equity,
                        slippage_bps=args.slippage_bps)
    print(f"window {start.date()} -> {end.date()}  symbols={len(symbols)} ({source})  "
          f"entry_start={cfg.entry_start:%H:%M} trail={cfg.trail_percent} "
          f"tp={cfg.take_profit} stop={cfg.stop_loss} slippage={args.slippage_bps:g}bps/side")
    print(summarize(broker, args.equity, stop_loss=cfg.stop_loss))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
