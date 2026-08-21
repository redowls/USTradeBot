"""Performance summary report (Phase 10).

Queries SQL Server for recent trading performance and pushes a digest to Telegram
(and stdout, so it also lands in the journal when run from the systemd timer):

    python -m bot.report --days 1          # daily (default)
    python -m bot.report --days 7          # weekly
    python -m bot.report --days 7 --mfe    # + max favourable/adverse excursion
    python -m bot.report --days 7 --refusals  # + what the entry filters declined

The headline figures (trades / win rate / P&L) cover the last ``--days``; the
confidence-band breakdown is all-time, answering the question the whole confidence
model exists for — *do higher-confidence trades actually pay off?*

``--mfe`` (IMP-025) appends the excursion table from :mod:`bot.excursion`: how far
each closed trade ran in our favour versus what it kept. It costs one historical-bars
call per trade, so it is opt-in, and it prints to **stdout only** — the Telegram
digest stays the short headline it has always been.

``--refusals`` (IMP-033) does the same for the other population: how far each
scored-but-refused candidate ran, grouped by the filter that refused it. Same opt-in,
same stdout-only rule.

Read-only. If persistence is disabled or unreachable, it logs and exits non-zero
without touching the trading path.
"""

from __future__ import annotations

import sys

from bot.config import Config, ConfigError
from bot.excursion import (
    alpaca_bar_fetcher,
    excursions_for,
    format_excursions,
    summarize,
)
from bot.notifier import open_notifier
from bot.persistence import PerformanceSummary, open_store
from bot.refusals import (
    alpaca_ohlc_fetcher,
    format_refusals,
    outcomes_for,
    summarize_by_reason,
)


def _money(x: float) -> str:
    sign = "+" if x >= 0 else "−"
    return f"{sign}${abs(x):,.2f}"


def format_summary(s: PerformanceSummary) -> str:
    span = "today" if s.days == 1 else f"last {s.days} days"
    lines = [
        f"📊 USTradeBot — {span}",
        f"closed trades: {s.trades}  ·  win rate: {s.win_rate * 100:.0f}%",
        f"P&L: {_money(s.total_pnl)}  ·  avg/trade: {_money(s.avg_pnl)}",
        f"open positions: {s.open_positions}",
    ]
    if s.bands:
        lines.append("— by confidence (all-time) —")
        for b in s.bands:
            lines.append(
                f"  {b.band}: {b.trades} tr · {b.win_rate * 100:.0f}% win · {_money(b.total_pnl)}"
            )
    return "\n".join(lines)


def _parse_days(argv: list[str]) -> int:
    if "--days" in argv:
        i = argv.index("--days")
        if i + 1 < len(argv):
            try:
                return max(1, int(argv[i + 1]))
            except ValueError:
                pass
    return 1


def excursion_report(store, cfg, days: int, fetch_bars=None) -> str:
    """Build the MFE/MAE table for the window. Never raises — reporting is optional."""
    try:
        trades = store.closed_trades(days)
        if not trades:
            return "— MFE/MAE — no closed trades in this window."
        fetch = fetch_bars if fetch_bars is not None else alpaca_bar_fetcher(cfg)
        rows, skipped = excursions_for(trades, fetch)
        return format_excursions(rows, summarize(rows), cfg.trail_percent, skipped)
    except Exception as e:  # a reporting extra must never break the report
        return f"— MFE/MAE — unavailable ({e.__class__.__name__}: {e})"


def refusal_report(store, cfg, days: int, fetch_ohlc=None) -> str:
    """Build the refused-candidate outcome table (IMP-033). Never raises."""
    try:
        refusals = store.refusals(days)
        if not refusals:
            return "— refused candidates — none recorded in this window."
        fetch = fetch_ohlc if fetch_ohlc is not None else alpaca_ohlc_fetcher(cfg)
        rows, skipped = outcomes_for(refusals, fetch, cfg.flatten_before_close_min)
        stats = summarize_by_reason(rows, cfg.trail_percent, cfg.stop_loss)
        return format_refusals(rows, stats, cfg.trail_percent, cfg.stop_loss, skipped)
    except Exception as e:  # a reporting extra must never break the report
        return f"— refused candidates — unavailable ({e.__class__.__name__}: {e})"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    days = _parse_days(args)
    want_mfe = "--mfe" in args
    want_refusals = "--refusals" in args
    try:
        cfg = Config.load()
    except ConfigError as e:
        print(f"config error: {e}")
        return 1
    store = open_store(cfg)
    if store is None:
        print("persistence disabled or unreachable — no report.")
        return 1
    summary = store.performance_summary(days)
    mfe_text = excursion_report(store, cfg, days) if want_mfe else None
    refusal_text = refusal_report(store, cfg, days) if want_refusals else None
    store.close()
    if summary is None:
        print("could not build the performance summary.")
        return 1
    text = format_summary(summary)
    print(text)
    if mfe_text:  # stdout/journal only — the Telegram digest stays short
        print(mfe_text)
    if refusal_text:  # same rule: study output never reaches Telegram
        print(refusal_text)
    notifier = open_notifier(cfg)
    if notifier is not None:
        notifier.send(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
