"""Backfill ``mfe_pct`` / ``mae_pct`` onto the historical closed book (IMP-058).

**Why this exists.** The retire-or-rebuild decision pre-registered in ``todo.md`` is
judged on one number: the **+1R ceiling** — the share of entries that ever print +1R
while held. IMP-051 built that instrument, ``bot.report --mfe`` renders it, and the
09-28 pre-registration made it the sole acceptance criterion for a replacement entry
trigger. But on the **live** book it is readable on **10 of 283 closed trades**:
``mfe_pct`` is written by the live tracker (IMP-037) and that only started on
2026-08-28. Every ceiling claim about live trading therefore rests on n=10, while the
decision it feeds is whether to retire the strategy.

That is the wrong instrument for the weight being put on it, and it is fixable without
touching a line of trading logic: the holding window of every closed trade is recorded
(``entry_time_utc`` → ``exit_time_utc``), and the bars over that window are still
available from the same IEX feed. This module replays those windows and writes the two
observational columns. **Nothing here trades, sizes, or decides anything** — it fills in
measurements of trades that closed weeks ago.

**Measured on closes, not intrabar extremes.** This is the one design choice that
matters, and it is dictated by :meth:`bot.risk.RiskManager._track_excursion`, which
records high/low-water **closes**: the ratchet sets the stop from ``close``, so a
close-based excursion is the move the exit structure could actually have banked, and an
intrabar high the trail can never reach would flatter every capture ratio computed off
this column. Backfilled rows land in the same column as live-measured rows and are
aggregated together by ``bot.report``, so they must mean the same thing. They do: this
folds ``(close, close)`` per bar through the same :func:`bot.excursion.compute_excursion`
the live and replay paths use.

Note this makes the backfill **conservative about the ceiling** relative to an
intrabar measurement — it can only understate how far a trade ran, never overstate it.
Given the ceiling's job is to decide whether the strategy survives, a measurement that
cannot flatter it is the right bias.

**The holding window.** Live folds a candle when it closes *and* the position is still
held. The first such candle is the one whose minute contains the entry (its close prints
after the fill, so there is no look-back into pre-entry price); the last is the one whose
close triggered the exit, because ``_track_excursion`` runs before the exit check on that
candle. So the window is ``floor_minute(entry) <= bar_start <= floor_minute(exit)``.

**A window with no bars is left NULL, never zero.** ``compute_excursion`` returns
``None`` when a window produced no bars — a same-minute round trip, or a symbol the IEX
tape did not print into. Scoring those as ``mfe_pct = 0`` would manufacture fake entries
at the bottom of the ceiling ladder, biasing the very number this exists to measure.
They stay NULL and are reported as skipped.

**Self-validating.** ``--verify`` recomputes the excursion for the trades that already
carry a *live-measured* value and reports the agreement, without writing. That is a
direct test of the reconstruction against ground truth the bot recorded itself at the
time, on the same rows, and it is the check that says whether the backfilled 273 can be
trusted beside the live 10.

Usage::

    python -m bot.backfill --verify          # check reconstruction vs live-measured rows
    python -m bot.backfill --dry-run         # report what would be written
    python -m bot.backfill                   # write mfe_pct/mae_pct where NULL
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bot.config import Config
from bot.excursion import compute_excursion

log = logging.getLogger("ustradebot.backfill")

# One bar per minute; a holding window is fetched per (symbol, session date) so the
# number of API calls tracks the number of distinct trading days a symbol traded on
# rather than the number of trades or the calendar span between them.
_BAR_MINUTES = 1


@dataclass(frozen=True)
class OpenWindow:
    """A closed trade's holding window, with the anchors the excursion needs."""

    trade_id: int
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    pnl: float
    # The live-measured value when the row already has one; ``--verify`` compares
    # against it and the write path skips rows that carry it.
    live_mfe: float | None = None
    live_mae: float | None = None

    @property
    def session(self) -> str:
        """The UTC date the window opens on, used to batch bar fetches."""
        return self.entry_time.strftime("%Y-%m-%d")


def _floor_minute(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


def select_bars(
    bars: Sequence[tuple[datetime, float]], window: OpenWindow
) -> list[tuple[float, float]]:
    """Slice ``bars`` to ``window`` and shape them for :func:`compute_excursion`.

    ``bars`` is ``(bar_start, close)`` ascending. Returns ``(close, close)`` pairs so
    the shared excursion helper's ``max(high) / min(low)`` reduces to the high- and
    low-water **close**, matching the live tracker exactly (see the module docstring).
    """
    lo = _floor_minute(window.entry_time)
    hi = _floor_minute(window.exit_time)
    return [(c, c) for ts, c in bars if lo <= ts <= hi]


def _windows_from_rows(rows) -> list[OpenWindow]:
    """Build windows from DB rows, dropping any that cannot be measured."""
    out: list[OpenWindow] = []
    for r in rows:
        entry_t, exit_t = r.entry_time_utc, r.exit_time_utc
        if entry_t is None or exit_t is None or r.entry_price is None:
            continue
        # Normalise BEFORE any comparison: pyodbc hands back naive datetimes, and
        # comparing a naive bound against an aware one raises rather than sorting.
        if entry_t.tzinfo is None:
            entry_t = entry_t.replace(tzinfo=timezone.utc)
        if exit_t.tzinfo is None:
            exit_t = exit_t.replace(tzinfo=timezone.utc)
        entry_px = float(r.entry_price)
        if entry_px <= 0 or exit_t < entry_t:
            continue
        out.append(
            OpenWindow(
                trade_id=int(r.id),
                symbol=str(r.symbol),
                entry_time=entry_t,
                exit_time=exit_t,
                entry_price=entry_px,
                exit_price=float(r.exit_price or 0.0),
                pnl=float(r.pnl or 0.0),
                live_mfe=None if r.mfe_pct is None else float(r.mfe_pct),
                live_mae=None if r.mae_pct is None else float(r.mae_pct),
            )
        )
    return out


def _alpaca_bar_fetcher(cfg: Config) -> Callable[[str, datetime, datetime], list]:
    """Return ``fetch(symbol, start, end) -> [(bar_start, close)]`` from the IEX feed.

    Same feed and client the live stream and the warmup path use, so a backfilled
    excursion is measured off the tape the bot actually traded against.
    """
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(cfg.alpaca_key_id, cfg.alpaca_secret)
    feed = cfg.alpaca_data_feed

    def _fetch(symbol: str, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=start,
            end=end,
            feed=feed,
        )
        try:
            barset = client.get_stock_bars(req)
        except Exception as exc:  # noqa: BLE001 - one bad symbol must not kill the run
            log.warning("bar fetch failed for %s %s: %s", symbol, start.date(), exc)
            return []
        rows = barset.data.get(symbol, []) if hasattr(barset, "data") else []
        out = []
        for b in rows:
            ts = b.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            out.append((ts.astimezone(timezone.utc), float(b.close)))
        out.sort()
        return out

    return _fetch


def measure(
    windows: Sequence[OpenWindow],
    fetch: Callable[[str, datetime, datetime], list],
) -> tuple[dict[int, tuple[float, float]], list[OpenWindow]]:
    """Reconstruct excursions for ``windows``. Returns ``({trade_id: (mfe, mae)}, skipped)``.

    Bars are fetched once per ``(symbol, session)`` and shared by every window that
    opens on it, so a day on which a symbol traded twice costs one call, not two.
    """
    by_day: dict[tuple[str, str], list[OpenWindow]] = defaultdict(list)
    for w in windows:
        by_day[(w.symbol, w.session)].append(w)

    measured: dict[int, tuple[float, float]] = {}
    skipped: list[OpenWindow] = []
    for (symbol, _session), group in sorted(by_day.items()):
        # Pad the fetch by a minute on each side so the boundary bars are never
        # clipped by the request window; `select_bars` does the exact slicing.
        start = min(w.entry_time for w in group) - timedelta(minutes=_BAR_MINUTES)
        end = max(w.exit_time for w in group) + timedelta(minutes=_BAR_MINUTES)
        bars = fetch(symbol, start, end)
        for w in group:
            window_bars = select_bars(bars, w)
            exc = compute_excursion(
                symbol=w.symbol,
                entry_price=w.entry_price,
                exit_price=w.exit_price,
                pnl=w.pnl,
                bars=window_bars,
            )
            if exc is None:
                skipped.append(w)  # no bars in the window — stays NULL, never zero
                continue
            measured[w.trade_id] = (exc.mfe_pct, exc.mae_pct)
    return measured, skipped


def _connect(cfg: Config):
    import pyodbc

    return pyodbc.connect(cfg.sqlserver_conn, timeout=15)


_SELECT = (
    "SELECT id, symbol, entry_time_utc, exit_time_utc, entry_price, exit_price, "
    "pnl, mfe_pct, mae_pct FROM dbo.trades WHERE exit_time_utc IS NOT NULL "
)


def load_windows(conn, *, only_missing: bool) -> list[OpenWindow]:
    """Read closed trades needing (or, for verify, already carrying) an excursion."""
    cur = conn.cursor()
    clause = "AND mfe_pct IS NULL" if only_missing else "AND mfe_pct IS NOT NULL"
    cur.execute(_SELECT + clause + " ORDER BY entry_time_utc")
    return _windows_from_rows(cur.fetchall())


def write_back(conn, measured: dict[int, tuple[float, float]]) -> int:
    """Persist reconstructed excursions. Only fills NULLs — never overwrites a
    live-measured value, which is ground truth this module is validated against."""
    cur = conn.cursor()
    n = 0
    for trade_id, (mfe, mae) in measured.items():
        cur.execute(
            "UPDATE dbo.trades SET mfe_pct = ?, mae_pct = ?, updated_at_utc = SYSUTCDATETIME() "
            "WHERE id = ? AND mfe_pct IS NULL",
            round(mfe, 4),
            round(mae, 4),
            trade_id,
        )
        n += cur.rowcount or 0
    conn.commit()
    return n


def verify_report(windows: Sequence[OpenWindow], measured: dict[int, tuple[float, float]]) -> str:
    """Compare reconstructed excursions against live-measured ones, as text."""
    lines = ["— backfill verification vs live-measured rows —"]
    deltas: list[float] = []
    for w in windows:
        got = measured.get(w.trade_id)
        if got is None or w.live_mfe is None:
            continue
        d_mfe = got[0] - w.live_mfe
        d_mae = got[1] - (w.live_mae if w.live_mae is not None else 0.0)
        deltas.append(abs(d_mfe))
        lines.append(
            f"  {w.symbol:5s} id={w.trade_id:<4d} live MFE {w.live_mfe:+.2f}% "
            f"vs rebuilt {got[0]:+.2f}% (Δ{d_mfe:+.2f}pp) | "
            f"MAE {(w.live_mae or 0.0):+.2f}% vs {got[1]:+.2f}% (Δ{d_mae:+.2f}pp)"
        )
    if deltas:
        worst = max(deltas)
        mean = sum(deltas) / len(deltas)
        agree = sum(1 for d in deltas if d <= 0.10)
        lines.append(
            f"  n={len(deltas)} · mean |ΔMFE| {mean:.3f}pp · worst {worst:.3f}pp · "
            f"within 0.10pp: {agree}/{len(deltas)}"
        )
    else:
        lines.append("  no comparable rows")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill trade excursions (IMP-058)")
    ap.add_argument("--verify", action="store_true",
                    help="recompute rows that already have a live-measured MFE and compare")
    ap.add_argument("--dry-run", action="store_true", help="measure but do not write")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = Config.load()
    fetch = _alpaca_bar_fetcher(cfg)
    conn = _connect(cfg)
    try:
        windows = load_windows(conn, only_missing=not args.verify)
        if not windows:
            print("nothing to do (no matching closed trades)")
            return 0
        print(f"measuring {len(windows)} closed trades…")
        measured, skipped = measure(windows, fetch)
        if args.verify:
            print(verify_report(windows, measured))
            return 0
        print(f"reconstructed {len(measured)} · skipped {len(skipped)} (no bars in window)")
        for w in skipped:
            print(f"  skipped {w.symbol} id={w.trade_id} {w.entry_time:%Y-%m-%d %H:%M}")
        if args.dry_run:
            print("dry run — nothing written")
            return 0
        written = write_back(conn, measured)
        print(f"wrote {written} rows")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
