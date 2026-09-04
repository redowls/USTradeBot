"""Maximum favourable / adverse excursion analysis (IMP-025).

Answers the one question every exit-structure decision on this bot has turned on:
*how far did each trade actually run in our favour, and how much of that did we
keep?* The trail gives back a fixed width (``trail_percent``, 1.25%, tightening to
``trail_percent_tight`` once a trade is ``trail_tighten_after`` in profit — IMP-018 /
IMP-021), so a trade whose peak never exceeds that width **cannot** be a winner no
matter how the ratchet is tuned. Whether the fault lies with the exit structure or
with the entry signal is therefore decided by the *distribution of MFE*, not by P&L.

That distribution has never been recorded. IMP-021 was specified off a hand-built
MFE table, and its own validation criterion (b) — "the MFE-capture rerun should lift
the 1.0-2.0% bucket well above 17%" — went unmeasured for a week precisely because
rebuilding the table meant fetching bars and joining them to trades by hand. This
module makes it a command:

    python -m bot.report --days 7 --mfe

Structure mirrors the rest of the bot: the arithmetic is **pure** and unit-tested
(:func:`compute_excursion`, :func:`bucket_of`, :func:`summarize`,
:func:`format_excursions`); the only I/O is a bar fetcher, injected as a callable so
tests run without a network. Read-only — nothing here touches the trading path.

Buckets are deliberately the *same* edges IMP-021 used (0.5% / 1.0% / 2.0%) so new
tables are directly comparable with the one in that entry.

**The R ladder (IMP-042).** Those percent bands answer "how far did it run"; they
cannot answer "did it reach the doctrine's WIN line", because that line is **+1R**
and R is per-trade (``entry - stop``, a median 2.01% of price but ranging from well
under 1% to over 4%). A 1.5% MFE clears +1R on a tight-stop trade and misses it on a
wide-stop one, so no fixed percent band separates the two. The 2026-09-03 review
needed exactly that split to size the escalation and had to rebuild it by hand over
275 rows — the same by-hand rebuild this module was created to end, one level up.

:func:`ceiling_table` therefore expresses MFE in R and reports the share of entries
that ever printed 0.5R / 1.0R / 1.5R / 2.0R. The +1R row is the load-bearing one: a
trade that never prints +1R cannot be scored a WIN by *any* exit rule, so that share
is a hard ceiling on the true win rate, and the gap between it and the realized true
win rate is the part an exit change could actually recover. It bounds the strategy
from above without reference to what the exits happened to do.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger("ustradebot.excursion")

# (symbol, start, end) -> the high/low of each bar in the holding window.
FetchBars = Callable[[str, datetime, datetime], Sequence[tuple[float, float]]]

# Upper edges of the MFE buckets, in percent. Same edges as the IMP-021 table.
_BUCKET_EDGES: tuple[float, ...] = (0.5, 1.0, 2.0)
_BUCKET_LABELS: tuple[str, ...] = ("<0.5%", "0.5-1.0%", "1.0-2.0%", ">2.0%")

# Rungs of the R ladder (IMP-042). 1.0 is the doctrine's WIN line and the reason the
# ladder exists; the neighbours are carried so a shift in the distribution is visible
# rather than inferred from one number moving.
R_LADDER: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0)
WIN_LINE_R = 1.0


@dataclass(frozen=True)
class Excursion:
    """How far one closed trade ran, and what it kept.

    All three percentages are relative to the entry price and signed the way a long
    experiences them: ``mfe_pct >= 0`` (best unrealised gain), ``mae_pct <= 0``
    (worst unrealised loss), ``realized_pct`` whatever we actually booked.
    """

    symbol: str
    entry_price: float
    exit_price: float
    mfe_pct: float
    mae_pct: float
    realized_pct: float
    pnl: float
    # 1R for this trade in price terms, from the ORIGINAL bracket stop. Optional
    # because rows written before IMP-042 (and the percent-only callers) have no
    # stop to divide by; those are excluded from the R ladder rather than guessed at.
    risk_per_share: float | None = None

    @property
    def mfe_r(self) -> float | None:
        """Peak unrealised gain expressed in R, or ``None`` without a known 1R.

        The percent bands cannot be converted to R in aggregate — R varies per trade —
        so the conversion has to happen here, on the individual row, before anything
        is summed.
        """
        if not self.risk_per_share or self.risk_per_share <= 0:
            return None
        return (self.mfe_pct / 100.0) * self.entry_price / self.risk_per_share

    @property
    def capture(self) -> float | None:
        """Fraction of the favourable excursion actually banked, in percent.

        ``None`` when the trade never traded above its entry (no excursion to
        capture — dividing by ~0 would manufacture a meaningless number). Negative
        when a trade that ran green was closed red, which is the signature this
        whole module exists to surface.
        """
        if self.mfe_pct <= 0:
            return None
        return self.realized_pct / self.mfe_pct * 100.0

    @property
    def bucket(self) -> str:
        return bucket_of(self.mfe_pct)


@dataclass(frozen=True)
class ExcursionBucket:
    """One MFE band, aggregated. ``capture`` is avg-realized / avg-MFE, as IMP-021."""

    label: str
    trades: int
    avg_mfe: float
    avg_realized: float
    capture: float | None
    total_pnl: float


def bucket_of(mfe_pct: float) -> str:
    """Label the MFE band ``mfe_pct`` falls in (edges are upper-exclusive)."""
    for edge, label in zip(_BUCKET_EDGES, _BUCKET_LABELS):
        if mfe_pct < edge:
            return label
    return _BUCKET_LABELS[-1]


def compute_excursion(
    symbol: str,
    entry_price: float,
    exit_price: float,
    pnl: float,
    bars: Sequence[tuple[float, float]],
    risk_per_share: float | None = None,
) -> Excursion | None:
    """Reduce a trade's holding-window bars to its excursion figures.

    ``bars`` is ``(high, low)`` per bar over the holding window. Returns ``None``
    when there are no bars (a same-minute round trip, or a symbol the IEX tape did
    not print) — the caller drops those rather than scoring them as zero, because a
    missing window is not a flat one.
    """
    if entry_price <= 0 or not bars:
        return None
    high = max(h for h, _ in bars)
    low = min(low for _, low in bars)
    # Clamp to the entry: a trade that never traded above entry has no favourable
    # excursion (0), not a negative one — the two are different questions and the
    # bucket edges assume MFE >= 0.
    mfe = max(0.0, (high - entry_price) / entry_price * 100.0)
    mae = min(0.0, (low - entry_price) / entry_price * 100.0)
    realized = (exit_price - entry_price) / entry_price * 100.0
    return Excursion(
        symbol=symbol,
        entry_price=entry_price,
        exit_price=exit_price,
        mfe_pct=mfe,
        mae_pct=mae,
        realized_pct=realized,
        pnl=pnl,
        risk_per_share=risk_per_share if risk_per_share and risk_per_share > 0 else None,
    )


def summarize(excursions: Iterable[Excursion]) -> list[ExcursionBucket]:
    """Aggregate excursions into the IMP-021 buckets, lowest band first.

    Empty bands are omitted — a table of mostly-zero rows reads worse than a short
    one, and the band edges are fixed so absence is unambiguous.
    """
    by_label: dict[str, list[Excursion]] = {label: [] for label in _BUCKET_LABELS}
    for e in excursions:
        by_label[e.bucket].append(e)
    out: list[ExcursionBucket] = []
    for label in _BUCKET_LABELS:
        group = by_label[label]
        if not group:
            continue
        n = len(group)
        avg_mfe = sum(e.mfe_pct for e in group) / n
        avg_realized = sum(e.realized_pct for e in group) / n
        out.append(
            ExcursionBucket(
                label=label,
                trades=n,
                avg_mfe=avg_mfe,
                avg_realized=avg_realized,
                capture=(avg_realized / avg_mfe * 100.0) if avg_mfe > 0 else None,
                total_pnl=sum(e.pnl for e in group),
            )
        )
    return out


def _pct(x: float) -> str:
    return f"{x:+.2f}%"


def _money(x: float) -> str:
    sign = "+" if x >= 0 else "−"
    return f"{sign}${abs(x):,.2f}"


@dataclass(frozen=True)
class CeilingRung:
    """One rung of the R ladder: how many entries ever printed at least ``threshold_r``."""

    threshold_r: float
    reached: int
    total: int  # rows with a usable 1R, i.e. the ladder's denominator

    @property
    def share(self) -> float:
        return self.reached / self.total if self.total else 0.0


def ceiling_table(excursions: Iterable[Excursion]) -> list[CeilingRung]:
    """How far the entry signal runs, in R — the ceiling on what any exit can bank.

    Rows without a usable 1R are dropped rather than defaulted, so the denominator is
    always the population the ladder actually measured. Returns one rung per
    :data:`R_LADDER` entry, always the same length, so an empty window still renders a
    table (of zeros) instead of vanishing.
    """
    rs = [e.mfe_r for e in excursions]
    usable = [r for r in rs if r is not None]
    return [
        CeilingRung(threshold_r=t, reached=sum(1 for r in usable if r >= t), total=len(usable))
        for t in R_LADDER
    ]


def format_ceiling(rungs: Sequence[CeilingRung], true_win_rate: float | None = None) -> str:
    """Render the R ladder. ``true_win_rate`` (0-1) is drawn as the realized floor.

    Printing the two together is the whole point: alone, the +1R share looks like a
    verdict on the exits, and the true win rate looks like a verdict on the strategy.
    Side by side they separate: the ceiling indicts the *entry*, and the distance
    below it is the only part an exit change could ever recover.
    """
    if not rungs or not rungs[0].total:
        return "  MFE ladder in R — unavailable (no trade in this window carries a stop)."
    lines = [f"  {'MFE >= ':<10}{'trades':>9}{'share':>8}   (n={rungs[0].total} with a known 1R)"]
    for r in rungs:
        mark = "  <-- doctrine WIN line" if r.threshold_r == WIN_LINE_R else ""
        lines.append(
            f"  {r.threshold_r:>6.1f}R   {r.reached:>4}/{r.total:<4}{r.share * 100:>7.1f}%{mark}"
        )
    win = next((r for r in rungs if r.threshold_r == WIN_LINE_R), None)
    if win is not None:
        lines.append(
            f"  CEILING: {win.share * 100:.1f}% of entries ever print +1R — no exit change "
            f"can lift the true win rate above that."
        )
        if true_win_rate is not None:
            gap = win.share - true_win_rate
            lines.append(
                f"  realized true win rate {true_win_rate * 100:.1f}% vs ceiling "
                f"{win.share * 100:.1f}% -> {gap * 100:.1f}pp is exit-recoverable, "
                f"the remaining {(1 - win.share) * 100:.1f}pp is the entry signal."
            )
    return "\n".join(lines)


def format_excursions(
    excursions: Sequence[Excursion],
    buckets: Sequence[ExcursionBucket],
    trail_percent: float,
    skipped: int = 0,
) -> str:
    """Render the per-trade lines and the bucket table. Pure."""
    if not excursions:
        return "— MFE/MAE — no closed trades with bars in this window."
    trail_pct = trail_percent * 100.0
    lines = [
        f"— MFE / MAE (trail give-back {trail_pct:.2f}%) —",
        f"  {'sym':<6}{'MFE':>8}{'MAE':>8}{'exit':>8}{'capture':>9}{'P&L':>11}",
    ]
    for e in excursions:
        cap = "—" if e.capture is None else f"{e.capture:.0f}%"
        lines.append(
            f"  {e.symbol:<6}{_pct(e.mfe_pct):>8}{_pct(e.mae_pct):>8}"
            f"{_pct(e.realized_pct):>8}{cap:>9}{_money(e.pnl):>11}"
        )
    lines.append(f"  {'by MFE band':<12}{'n':>4}{'avg MFE':>9}{'avg exit':>10}"
                 f"{'capture':>9}{'net':>11}")
    for b in buckets:
        cap = "—" if b.capture is None else f"{b.capture:.0f}%"
        lines.append(
            f"  {b.label:<12}{b.trades:>4}{_pct(b.avg_mfe):>9}{_pct(b.avg_realized):>10}"
            f"{cap:>9}{_money(b.total_pnl):>11}"
        )
    # The headline number: a trade that never runs further than the give-back is
    # structurally unable to finish green, so this share bounds the win rate.
    unreachable = sum(1 for e in excursions if e.mfe_pct < trail_pct)
    lines.append(
        f"  {unreachable}/{len(excursions)} trades peaked below the "
        f"{trail_pct:.2f}% give-back (cannot finish green on the trail)."
    )
    if skipped:
        lines.append(f"  ({skipped} closed trade(s) skipped — no bars in the holding window)")
    return "\n".join(lines)


def excursions_for(
    trades: Iterable,
    fetch_bars: FetchBars,
    stop_loss: float | None = None,
) -> tuple[list[Excursion], int]:
    """Map closed trades to excursions via ``fetch_bars``; returns (rows, skipped).

    Each trade needs ``symbol``, ``entry_price``, ``exit_price``, ``pnl``,
    ``entry_time_utc`` and ``exit_time_utc`` (i.e. a
    :class:`~bot.persistence.ClosedTrade`). A fetch that raises is logged and
    skipped — this is a reporting tool, one bad symbol must not lose the table.

    ``stop_loss`` (the configured fraction) enables the R ladder: 1R comes from the
    trade's own recorded ``stop_price`` via :func:`bot.doctrine.risk_per_share`, which
    is the same denominator the WIN/SCRATCH/FAIL buckets use — the two studies must
    not disagree about what one R is. Omit it and the percent tables are unchanged.
    """
    from bot.doctrine import risk_per_share  # local: keeps the pure core import-light

    rows: list[Excursion] = []
    skipped = 0
    for t in trades:
        try:
            bars = fetch_bars(t.symbol, t.entry_time_utc, t.exit_time_utc)
        except Exception:
            log.exception("excursion bar fetch failed for %s", t.symbol)
            bars = []
        risk = None
        if stop_loss is not None:
            risk = risk_per_share(t.entry_price, getattr(t, "stop_price", None), stop_loss)
        e = compute_excursion(t.symbol, t.entry_price, t.exit_price, t.pnl, bars, risk)
        if e is None:
            skipped += 1
            continue
        rows.append(e)
    return rows, skipped


def alpaca_bar_fetcher(cfg) -> FetchBars:
    """Build a :data:`FetchBars` backed by Alpaca's historical 1-minute bars.

    Same feed the live stream trades on (``cfg.alpaca_data_feed``), so the highs and
    lows are the ones the bot could actually have seen — an excursion measured on a
    richer feed than the bot trades would overstate what was reachable.
    """
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(cfg.alpaca_key_id, cfg.alpaca_secret)
    feed = cfg.alpaca_data_feed

    def _fetch(symbol: str, start: datetime, end: datetime) -> list[tuple[float, float]]:
        req = StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=TimeFrame.Minute,
            start=start, end=end, feed=feed,
        )
        barset = client.get_stock_bars(req)
        return [(float(b.high), float(b.low)) for b in barset.data.get(symbol, [])]

    return _fetch
