"""Entry-timing quality: how much of the day's move was still on the table (IMP-040).

Every structural question this bot now faces reduces to one number it has never
measured. :mod:`bot.excursion` answers *"how far did the trade run once we were
in?"*; :mod:`bot.refusals` answers *"how far did the ones we declined run?"*.
Neither answers the prior question: **was there anything to catch in the first
place, and had we already missed it by the time we committed?**

That distinction is the whole 2026-09-02 finding. On that session NVDA traded a
4.34% range and INTC a 3.35% range, yet the 37 candidates the bot scored averaged
+0.50% MFE and 25 of them never travelled half a percent. "The tape was dead" and
"the entry fired in the flat part of a name that moved" produce identical MFE
tables, and they have opposite fixes — the first says change the universe, the
second says change the signal. Guessing between them is how a review ships a
watchlist edit that was really an entry bug, or vice versa.

So this module decomposes the opportunity into a **ladder**, one rung per stage:

1. ``session_range_pct`` — the whole session's high-low range on that symbol.
   *Opportunity that existed at all.* Below the trail width, no entry timing and
   no exit structure can produce a winner: the name did not move far enough.
2. ``available_pct`` — the run from our entry price to the session high **after**
   we entered. *Opportunity still unspent when we committed.* The gap between
   rungs 1 and 2 is entry timing: range that had already happened, or that
   happened on the other side of our entry.
3. ``mfe_pct`` — the best unrealised gain over the **holding** window.
   The gap between rungs 2 and 3 is holding time: upside that arrived after we
   had already exited.
4. ``realized_pct`` — what we kept. The gap from rung 3 is profit capture, which
   is what :mod:`bot.excursion` already measures.

Read each rung against ``trail_percent``: a trade needs to clear that width to
finish green on the ratchet at all (IMP-018), so the share of trades whose *range*
clears it bounds the share that could ever have won. Where the ladder first
collapses names the binding constraint, and the three gaps map one-to-one onto the
stop-exit doctrine's three causes — entry quality, stop geometry, profit capture.

    python -m bot.report --days 30 --timing

Same shape as its siblings: the arithmetic is **pure** and unit-tested, the only
I/O is an injected session-bar fetcher, and it is read-only opt-in stdout — nothing
here touches the trading path or the Telegram digest.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from bot.config import EASTERN

log = logging.getLogger("ustradebot.timing")

# (symbol, session_start, session_end) -> (bar_start, high, low) per bar.
# Timestamps come back so the entry can be located within the session; the bot's
# own candles are keyed by bar START, and this follows that convention (IMP-024).
FetchSession = Callable[
    [str, datetime, datetime], Sequence[tuple[datetime, float, float]]
]


@dataclass(frozen=True)
class EntryTiming:
    """One closed trade's position within the opportunity its symbol offered.

    All percentages are relative to the entry price except ``session_range_pct``,
    which is relative to the session low — it is a property of the *tape*, not of
    our fill, and must stay comparable across trades in the same name on the same
    day regardless of where each one entered.

    ``available_pct`` and ``mfe_pct`` are clamped at zero for the same reason
    :func:`bot.excursion.compute_excursion` clamps: a name that never traded above
    our entry offered no favourable excursion, which is a different statement from
    a negative one and would corrupt the ratios below.
    """

    symbol: str
    entry_price: float
    session_high: float
    session_low: float
    available_pct: float
    mfe_pct: float
    realized_pct: float

    @property
    def session_range_pct(self) -> float:
        return (self.session_high - self.session_low) / self.session_low * 100.0

    @property
    def entry_percentile(self) -> float | None:
        """Where in the session's range we entered: 0.0 at the low, 1.0 at the high.

        ``None`` on a zero-range session (a halted or untraded name), where the
        question has no answer. High values are the signature of a late entry —
        the move happened, then we bought it.
        """
        span = self.session_high - self.session_low
        if span <= 0:
            return None
        return (self.entry_price - self.session_low) / span

    @property
    def unspent_share(self) -> float | None:
        """Share of the session's range still ahead of us at entry (rungs 2 / 1).

        ``None`` when the session had no range. Low values mean the tape moved and
        we were not positioned for it — entry timing, not a dead universe.
        """
        if self.session_range_pct <= 0:
            return None
        return self.available_pct / self.session_range_pct


def compute_timing(
    symbol: str,
    entry_price: float,
    exit_price: float,
    entry_time: datetime,
    exit_time: datetime,
    session_bars: Sequence[tuple[datetime, float, float]],
) -> EntryTiming | None:
    """Reduce a trade plus its symbol's full session to the four-rung ladder.

    ``session_bars`` is ``(bar_start, high, low)`` spanning the whole regular
    session the trade was entered in — not just the holding window, which is the
    point: the bars *before* the entry are what reveal a late one.

    Returns ``None`` when the session has no bars or the entry price is
    nonsensical. A missing session is not a flat one, so the caller drops the row
    rather than scoring it zero (same rule as :mod:`bot.excursion`).
    """
    if entry_price <= 0 or not session_bars:
        return None
    session_high = max(h for _, h, _ in session_bars)
    session_low = min(low for _, _, low in session_bars)
    if session_low <= 0:
        return None

    # Bars at or after the entry bar: what was still reachable once we committed.
    # ">=" not ">" — the entry bar's own high is reachable, the fill happens at
    # its close but the bar is still trading when the signal fires.
    after = [(h, low) for t, h, low in session_bars if t >= entry_time]
    high_after = max((h for h, _ in after), default=entry_price)

    # The holding window ends at the exit bar, inclusive for the same reason.
    holding = [(h, low) for t, h, low in session_bars if entry_time <= t <= exit_time]
    high_holding = max((h for h, _ in holding), default=entry_price)

    return EntryTiming(
        symbol=symbol,
        entry_price=entry_price,
        session_high=session_high,
        session_low=session_low,
        available_pct=max(0.0, (high_after - entry_price) / entry_price * 100.0),
        mfe_pct=max(0.0, (high_holding - entry_price) / entry_price * 100.0),
        realized_pct=(exit_price - entry_price) / entry_price * 100.0,
    )


@dataclass(frozen=True)
class TimingSummary:
    """The ladder, aggregated. ``*_reaching_trail`` are the rung-by-rung survival."""

    trades: int
    median_session_range: float
    median_available: float
    median_mfe: float
    median_realized: float
    range_reaching_trail: int
    available_reaching_trail: int
    mfe_reaching_trail: int
    median_unspent_share: float | None
    median_entry_percentile: float | None


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def summarize(rows: Sequence[EntryTiming], trail_percent: float) -> TimingSummary | None:
    """Aggregate the ladder. ``trail_percent`` is a fraction (0.0125), as in config.

    Medians rather than means throughout: the MFE distribution on this book is
    long-tailed (a handful of >2% runners carry the whole mean — see the IMP-025
    table), and the question here is what the *typical* trade was offered, which a
    mean of that distribution actively misreports.
    """
    if not rows:
        return None
    trail_pct = trail_percent * 100.0
    unspent = [r.unspent_share for r in rows if r.unspent_share is not None]
    percentiles = [r.entry_percentile for r in rows if r.entry_percentile is not None]
    return TimingSummary(
        trades=len(rows),
        median_session_range=_median([r.session_range_pct for r in rows]),
        median_available=_median([r.available_pct for r in rows]),
        median_mfe=_median([r.mfe_pct for r in rows]),
        median_realized=_median([r.realized_pct for r in rows]),
        range_reaching_trail=sum(1 for r in rows if r.session_range_pct >= trail_pct),
        available_reaching_trail=sum(1 for r in rows if r.available_pct >= trail_pct),
        mfe_reaching_trail=sum(1 for r in rows if r.mfe_pct >= trail_pct),
        median_unspent_share=_median(unspent) if unspent else None,
        median_entry_percentile=_median(percentiles) if percentiles else None,
    )


def _pct(x: float) -> str:
    return f"{x:+.2f}%"


def format_timing(
    summary: TimingSummary | None, trail_percent: float, skipped: int = 0
) -> str:
    """Render the ladder as the rung-by-rung table, widest opportunity first."""
    if summary is None:
        return "— entry timing — no closed trades with session bars in this window."
    trail_pct = trail_percent * 100.0
    n = summary.trades
    lines = [
        "— entry timing: how much of the move was still on the table —",
        f"  ladder over {n} closed trade(s); trail needs {trail_pct:.2f}% to finish green.",
        f"  {'rung':<26} {'median':>9} {'>= trail':>10}",
        f"  {'1 session range (tape)':<26} {summary.median_session_range:>8.2f}% "
        f"{summary.range_reaching_trail:>4}/{n:<5}",
        f"  {'2 available at entry':<26} {summary.median_available:>8.2f}% "
        f"{summary.available_reaching_trail:>4}/{n:<5}",
        f"  {'3 MFE while held':<26} {summary.median_mfe:>8.2f}% "
        f"{summary.mfe_reaching_trail:>4}/{n:<5}",
        f"  {'4 realized':<26} {_pct(summary.median_realized):>9}",
    ]
    if summary.median_unspent_share is not None:
        lines.append(
            f"  median unspent share (rung2/rung1): "
            f"{summary.median_unspent_share * 100:.0f}% of the day's range was still ahead"
        )
    if summary.median_entry_percentile is not None:
        lines.append(
            f"  median entry percentile: "
            f"{summary.median_entry_percentile * 100:.0f}% of the session range "
            f"(0% = bought the low, 100% = bought the high)"
        )
    lines.append(
        "  READ: rung 1 short of the trail = wrong universe; a big 1->2 drop = late entry; "
        "2->3 = exited early; 3->4 = profit capture."
    )
    if skipped:
        lines.append(f"  ({skipped} trade(s) skipped — no session bars)")
    return "\n".join(lines)


def timings_for(
    trades: Iterable,
    fetch_session: FetchSession,
) -> tuple[list[EntryTiming], int]:
    """Map closed trades to their timing ladder; returns ``(rows, skipped)``.

    Each trade needs the :class:`~bot.persistence.ClosedTrade` fields. A fetch that
    raises is logged and skipped — one bad symbol must never lose the table.
    """
    rows: list[EntryTiming] = []
    skipped = 0
    for t in trades:
        try:
            bars = fetch_session(t.symbol, t.entry_time_utc, t.exit_time_utc)
        except Exception:
            log.exception("session bar fetch failed for %s", t.symbol)
            bars = []
        row = compute_timing(
            t.symbol,
            t.entry_price,
            t.exit_price,
            t.entry_time_utc,
            t.exit_time_utc,
            bars,
        )
        if row is None:
            skipped += 1
            continue
        rows.append(row)
    return rows, skipped


def session_bounds_utc(entry: datetime) -> tuple[datetime, datetime]:
    """The 09:30–16:00 Eastern session containing ``entry``, as naive UTC.

    Naive in, naive out — trade timestamps are stored naive-UTC (see
    :class:`~bot.persistence.ClosedTrade`) and the bar timestamps this is compared
    against are normalized the same way, so introducing a tz-aware value here
    would raise on the first comparison.
    """
    aware = entry if entry.tzinfo is not None else entry.replace(tzinfo=UTC)
    local = aware.astimezone(EASTERN)
    open_local = local.replace(hour=9, minute=30, second=0, microsecond=0)
    close_local = local.replace(hour=16, minute=0, second=0, microsecond=0)
    to_utc = lambda d: d.astimezone(UTC).replace(tzinfo=None)  # noqa: E731
    return to_utc(open_local), to_utc(close_local)


def alpaca_session_fetcher(cfg) -> FetchSession:
    """Build a :data:`FetchSession` over Alpaca's 1-minute bars for the trade's day.

    Widens whatever holding window it is handed to the **full regular session**
    containing the entry: 09:30–16:00 *Eastern*, converted to UTC through
    :data:`bot.config.EASTERN` rather than a hardcoded offset, so the window does
    not silently shift by an hour across the DST boundary the way a fixed
    13:30–20:00 UTC span would (the lesson of IMP-026). Alpaca returns only bars
    that traded, so a half-day simply yields fewer. Uses ``cfg.alpaca_data_feed``
    — the same feed the bot trades on, so the range measured is the range it
    could have seen.
    """
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(cfg.alpaca_key_id, cfg.alpaca_secret)
    feed = cfg.alpaca_data_feed

    def _fetch(
        symbol: str, entry: datetime, _exit: datetime
    ) -> list[tuple[datetime, float, float]]:
        day_start, day_end = session_bounds_utc(entry)
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=day_start,
            end=day_end,
            feed=feed,
        )
        barset = client.get_stock_bars(req)
        return [
            (b.timestamp.replace(tzinfo=None), float(b.high), float(b.low))
            for b in barset.data.get(symbol, [])
        ]

    return _fetch
