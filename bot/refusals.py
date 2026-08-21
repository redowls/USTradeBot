"""What the entry filters actually declined (IMP-033).

``dbo.entry_refusals`` has recorded every scored-but-rejected candidate since IMP-030,
with the gate state since IMP-031 — the *decision* and the pre-entry feature vector it
was made on. What it has never carried is the **outcome**: whether the tape then went
up or down. Without that, a refusal row proves only that we did not trade; it cannot
say whether the filter saved money or cost it.

That number has now been rebuilt by hand two reviews running (08-20's "MU 14:20 ran
+1.56% to the flatten and was stopped by the gate alone"), which is precisely the
failure mode IMP-025 was written to end for excursion. This module does for refusals
what :mod:`bot.excursion` did for closed trades: makes the measurement repeatable.

The counterfactual is deliberately the bot's own: **enter at the refusal candle's
close, hold to that session's flatten** (the bot never holds overnight), scored on
``cfg.alpaca_data_feed`` — the feed it actually trades. Reuses
:func:`bot.excursion.compute_excursion` so the MFE/MAE arithmetic and the bucket edges
are the same ones every prior study used.

**This is an upper bound on the recoverable population, and must be read as one.**
Three reasons, all printed in the footer so no reader can miss them: admitting a
candidate past one filter only advances it to the *next* one (a loosened crossover
floor does not buy the trade, it merely sends it to the gate); the trail and stop would
have closed many of these long before the flatten; and capital is finite, so the bot
could not have taken every one. ``reached_trail`` and ``stopped_out`` are reported for
exactly that reason — a cohort whose MFE never reaches the trail give-back could not
have finished green no matter how the entry filter was set.

Read-only, offline-testable (the bar fetcher is injected), and touches nothing in the
trading path.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from bot.excursion import bucket_of, compute_excursion

log = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")
_MARKET_CLOSE_ET = time(16, 0)

# ``(high, low, close)`` per bar over the counterfactual holding window.
FetchOHLC = Callable[[str, datetime, datetime], list[tuple[float, float, float]]]

# The free-text ``reason`` embeds the numbers that produced it ("crossover 0.11 < 0.25"),
# so grouping needs the filter's identity rather than the string. Prefix-matched against
# the wording bot/strategy.py emits; anything unrecognised stays visible as "other"
# instead of being silently folded into a neighbouring cohort.
_REASON_CLASSES: tuple[tuple[str, str], ...] = (
    ("crossover", "crossover"),
    ("confidence", "confidence"),
    ("market gate", "gate"),
)


def classify_reason(reason: str) -> str:
    """Bucket a refusal ``reason`` string to the filter that produced it."""
    text = (reason or "").strip().lower()
    for prefix, label in _REASON_CLASSES:
        if text.startswith(prefix):
            return label
    return "other"


def session_flatten_utc(candle_start: datetime, flatten_before_close_min: int) -> datetime:
    """The naive-UTC instant the bot would have flattened the candle's own session.

    Computed through ``America/New_York`` rather than a fixed UTC offset so the
    horizon stays correct across the DST boundary — a hardcoded 19:45Z is right in
    August and an hour wrong in December, which would quietly extend or truncate every
    winter counterfactual.
    """
    et = candle_start.replace(tzinfo=ZoneInfo("UTC")).astimezone(_ET)
    close_et = et.replace(
        hour=_MARKET_CLOSE_ET.hour, minute=_MARKET_CLOSE_ET.minute,
        second=0, microsecond=0,
    ) - timedelta(minutes=flatten_before_close_min)
    return close_et.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


@dataclass(frozen=True)
class RefusalOutcome:
    """One refused candidate, paired with what the tape did afterwards."""

    symbol: str
    reason_class: str
    reason: str
    confidence: float | None
    market_gate_open: bool | None
    atr_pct: float | None
    ribbon_spread_pct: float | None
    mfe_pct: float
    mae_pct: float
    forward_pct: float  # close at the flatten, relative to the refusal candle's close

    @property
    def bucket(self) -> str:
        return bucket_of(self.mfe_pct)


@dataclass(frozen=True)
class ReasonStats:
    """One refusal cohort, aggregated."""

    label: str
    n: int
    avg_mfe: float
    avg_mae: float
    avg_forward: float
    never_green: int  # MFE < 0.5% — the cohort the 08-14 weekly named the last real leak
    reached_trail: int  # MFE >= the trail give-back: could plausibly have banked something
    stopped_out: int  # MAE <= -stop: the stop would have cut it regardless of entry filter


def outcomes_for(
    refusals: Iterable,
    fetch_ohlc: FetchOHLC,
    flatten_before_close_min: int,
) -> tuple[list[RefusalOutcome], int]:
    """Score each refusal against its own session's tape; returns (rows, skipped).

    Each refusal needs ``symbol``, ``candle_start_utc``, ``close_price``, ``reason``
    (i.e. a :class:`~bot.persistence.RefusedCandidate`). A refusal at or after its own
    flatten has no forward window and is skipped, as is one the tape did not print —
    a missing window is not a flat one, the same rule :mod:`bot.excursion` applies.
    """
    rows: list[RefusalOutcome] = []
    skipped = 0
    for r in refusals:
        start = r.candle_start_utc
        end = session_flatten_utc(start, flatten_before_close_min)
        if end <= start:
            skipped += 1
            continue
        try:
            bars = fetch_ohlc(r.symbol, start, end)
        except Exception:
            log.exception("refusal bar fetch failed for %s", r.symbol)
            bars = []
        if not bars:
            skipped += 1
            continue
        forward_close = bars[-1][2]
        exc = compute_excursion(
            r.symbol, r.close_price, forward_close, 0.0,
            [(h, low) for h, low, _ in bars],
        )
        if exc is None:
            skipped += 1
            continue
        rows.append(
            RefusalOutcome(
                symbol=r.symbol,
                reason_class=classify_reason(r.reason),
                reason=r.reason,
                confidence=getattr(r, "confidence", None),
                market_gate_open=getattr(r, "market_gate_open", None),
                atr_pct=getattr(r, "atr_pct", None),
                ribbon_spread_pct=getattr(r, "ribbon_spread_pct", None),
                mfe_pct=exc.mfe_pct,
                mae_pct=exc.mae_pct,
                forward_pct=exc.realized_pct,
            )
        )
    return rows, skipped


def summarize_by_reason(
    outcomes: Sequence[RefusalOutcome],
    trail_percent: float,
    stop_loss: float,
) -> list[ReasonStats]:
    """Aggregate outcomes per refusal cohort, plus an ``ALL`` row.

    ``trail_percent`` and ``stop_loss`` arrive as the config's fractions (0.0125) and
    are compared in percent, matching ``mfe_pct``/``mae_pct``.
    """
    trail_pct = trail_percent * 100.0
    stop_pct = stop_loss * 100.0

    def _stats(label: str, rows: Sequence[RefusalOutcome]) -> ReasonStats:
        n = len(rows)
        return ReasonStats(
            label=label,
            n=n,
            avg_mfe=sum(r.mfe_pct for r in rows) / n,
            avg_mae=sum(r.mae_pct for r in rows) / n,
            avg_forward=sum(r.forward_pct for r in rows) / n,
            never_green=sum(1 for r in rows if r.mfe_pct < 0.5),
            reached_trail=sum(1 for r in rows if r.mfe_pct >= trail_pct),
            stopped_out=sum(1 for r in rows if r.mae_pct <= -stop_pct),
        )

    out: list[ReasonStats] = []
    for label in ("crossover", "confidence", "gate", "other"):
        rows = [r for r in outcomes if r.reason_class == label]
        if rows:
            out.append(_stats(label, rows))
    if outcomes:
        out.append(_stats("ALL", list(outcomes)))
    return out


def _pct(x: float) -> str:
    return f"{x:+.2f}%"


def format_refusals(
    outcomes: Sequence[RefusalOutcome],
    stats: Sequence[ReasonStats],
    trail_percent: float,
    stop_loss: float,
    skipped: int = 0,
) -> str:
    """Render the refusal-outcome table for stdout/journal."""
    if not outcomes:
        return "— refused candidates — nothing scored in this window."
    trail_pct = trail_percent * 100.0
    lines = [
        "— refused candidates: what the filters declined —",
        f"  counterfactual: enter at the refusal candle's close, flatten with the session.",
        f"  {'cohort':<11} {'n':>3} {'avgMFE':>8} {'avgMAE':>8} {'avgFwd':>8} "
        f"{'<0.5%MFE':>9} {'hitTrail':>9} {'stopped':>8}",
    ]
    for s in stats:
        lines.append(
            f"  {s.label:<11} {s.n:>3} {_pct(s.avg_mfe):>8} {_pct(s.avg_mae):>8} "
            f"{_pct(s.avg_forward):>8} "
            f"{s.never_green:>4}/{s.n:<4} {s.reached_trail:>4}/{s.n:<4} {s.stopped_out:>3}/{s.n:<4}"
        )
    best = max(outcomes, key=lambda r: r.mfe_pct)
    lines.append(
        f"  best declined: {best.symbol} MFE {best.mfe_pct:+.2f}% "
        f"(fwd {best.forward_pct:+.2f}%, conf {best.confidence}, {best.reason})"
    )
    lines.append(
        f"  UPPER BOUND — passing one filter only advances a candidate to the next; the "
        f"trail ({trail_pct:.2f}%) / stop ({stop_loss * 100:.1f}%) would have exited many "
        f"before the flatten; capital is finite."
    )
    if skipped:
        lines.append(f"  ({skipped} refusal(s) skipped — no forward window on the tape)")
    return "\n".join(lines)


def alpaca_ohlc_fetcher(cfg) -> FetchOHLC:
    """Build a :data:`FetchOHLC` backed by Alpaca's 1-minute bars.

    Same feed as :func:`bot.excursion.alpaca_bar_fetcher` and for the same reason:
    scoring a declined candidate on a richer tape than the bot trades would overstate
    what it could actually have captured.
    """
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(cfg.alpaca_key_id, cfg.alpaca_secret)
    feed = cfg.alpaca_data_feed

    def _fetch(symbol: str, start: datetime, end: datetime) -> list[tuple[float, float, float]]:
        req = StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=TimeFrame.Minute,
            start=start, end=end, feed=feed,
        )
        barset = client.get_stock_bars(req)
        return [
            (float(b.high), float(b.low), float(b.close))
            for b in barset.data.get(symbol, [])
        ]

    return _fetch
