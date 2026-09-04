"""Performance summary report (Phase 10).

Queries SQL Server for recent trading performance and pushes a digest to Telegram
(and stdout, so it also lands in the journal when run from the systemd timer):

    python -m bot.report --days 1          # daily (default)
    python -m bot.report --days 7          # weekly
    python -m bot.report --days 7 --mfe    # + max favourable/adverse excursion
    python -m bot.report --days 7 --refusals  # + what the entry filters declined
    python -m bot.report --days 30 --timing   # + how much of the move was still on the table

The headline figures (trades / win rate / P&L) cover the last ``--days``; the
confidence-band breakdown is all-time, answering the question the whole confidence
model exists for — *do higher-confidence trades actually pay off?*

``--mfe`` (IMP-025) appends the excursion table from :mod:`bot.excursion`: how far
each closed trade ran in our favour versus what it kept. It costs one historical-bars
call per trade, so it is opt-in, and it prints to **stdout only** — the Telegram
digest stays the short headline it has always been. Since IMP-042 it also prints the
**R ladder**: the share of entries that ever printed +1R, the doctrine's WIN line and
therefore a hard ceiling on the true win rate whatever the exits do.

``--refusals`` (IMP-033) does the same for the other population: how far each
scored-but-refused candidate ran, grouped by the filter that refused it. Same opt-in,
same stdout-only rule.

``--timing`` (IMP-040) asks the prior question both of those assume away: how much
of the day's range existed at all, and how much of it was still unspent when we
committed. It separates "the tape was dead" from "the tape moved and we were late",
which have opposite fixes. Same opt-in, same stdout-only rule.

Read-only. If persistence is disabled or unreachable, it logs and exits non-zero
without touching the trading path.
"""

from __future__ import annotations

import logging
import sys

from bot.config import Config, ConfigError
from bot.doctrine import StopExitSummary, format_stop_exits
from bot.doctrine import summarize as summarize_stop_exits
from bot.doctrine import verdicts_for
from bot.excursion import (
    alpaca_bar_fetcher,
    ceiling_table,
    excursions_for,
    format_ceiling,
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
from bot.timing import alpaca_session_fetcher, format_timing, timings_for
from bot.timing import summarize as summarize_timing


log = logging.getLogger("ustradebot.report")


def _money(x: float) -> str:
    sign = "+" if x >= 0 else "−"
    return f"{sign}${abs(x):,.2f}"


def format_summary(
    s: PerformanceSummary, stop_exits: StopExitSummary | None = None
) -> str:
    span = "today" if s.days == 1 else f"last {s.days} days"
    lines = [
        f"📊 USTradeBot — {span}",
        f"closed trades: {s.trades}  ·  win rate: {s.win_rate * 100:.0f}%",
        f"P&L: {_money(s.total_pnl)}  ·  avg/trade: {_money(s.avg_pnl)}",
        f"open positions: {s.open_positions}",
    ]
    # The doctrine's figures ride the digest itself rather than a stdout-only study:
    # the true win rate is what governs the verdict, so it has to travel beside the
    # headline it corrects instead of sitting below the fold (IMP-039).
    if stop_exits is not None and stop_exits.trades:
        lines.append(format_stop_exits(stop_exits))
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
    """Build the MFE/MAE table + R ladder for the window. Never raises."""
    try:
        trades = store.closed_trades(days)
        if not trades:
            return "— MFE/MAE — no closed trades in this window."
        fetch = fetch_bars if fetch_bars is not None else alpaca_bar_fetcher(cfg)
        rows, skipped = excursions_for(trades, fetch, cfg.stop_loss)
        text = format_excursions(rows, summarize(rows), cfg.trail_percent, skipped)
        return f"{text}\n{format_ceiling(ceiling_table(rows), _true_win_rate(trades, rows, cfg))}"
    except Exception as e:  # a reporting extra must never break the report
        return f"— MFE/MAE — unavailable ({e.__class__.__name__}: {e})"


def _true_win_rate(trades, rows, cfg) -> float | None:
    """Realized true win rate over exactly the cohort the R ladder measured.

    Scored on the rows that produced bars, not on the whole window: a ceiling and a
    floor drawn from different populations are not comparable. Returns ``None`` rather
    than raising if the rows cannot be bucketed — the ladder is the deliverable here
    and it must still print without the overlay.
    """
    try:
        scored = {(e.symbol, e.entry_price) for e in rows}
        cohort = [t for t in trades if (t.symbol, t.entry_price) in scored]
        if not cohort:
            return None
        return summarize_stop_exits(verdicts_for(cohort, cfg.stop_loss)).true_win_rate
    except Exception:
        log.exception("could not score the true win rate for the R ladder")
        return None
    except Exception as e:  # a reporting extra must never break the report
        return f"— MFE/MAE — unavailable ({e.__class__.__name__}: {e})"


def stop_exit_summary(store, cfg, days: int) -> StopExitSummary | None:
    """Bucket the window's closed trades WIN/SCRATCH/FAIL (IMP-039). Never raises.

    Reads the same rows the excursion study uses, so it costs one query and no
    network — which is why, unlike ``--mfe``/``--refusals``, it is always on.
    """
    try:
        trades = store.closed_trades(days)
        if not trades:
            return None
        return summarize_stop_exits(verdicts_for(trades, cfg.stop_loss))
    except Exception:  # a reporting extra must never break the report
        log.exception("failed to build the stop-exit summary")
        return None


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


def timing_report(store, cfg, days: int, fetch_session=None) -> str:
    """Build the entry-timing ladder (IMP-040). Never raises."""
    try:
        trades = store.closed_trades(days)
        if not trades:
            return "— entry timing — no closed trades in this window."
        fetch = fetch_session if fetch_session is not None else alpaca_session_fetcher(cfg)
        rows, skipped = timings_for(trades, fetch)
        return format_timing(
            summarize_timing(rows, cfg.trail_percent), cfg.trail_percent, skipped
        )
    except Exception as e:  # a reporting extra must never break the report
        return f"— entry timing — unavailable ({e.__class__.__name__}: {e})"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    days = _parse_days(args)
    want_mfe = "--mfe" in args
    want_refusals = "--refusals" in args
    want_timing = "--timing" in args
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
    stop_exits = stop_exit_summary(store, cfg, days)
    mfe_text = excursion_report(store, cfg, days) if want_mfe else None
    refusal_text = refusal_report(store, cfg, days) if want_refusals else None
    timing_text = timing_report(store, cfg, days) if want_timing else None
    store.close()
    if summary is None:
        print("could not build the performance summary.")
        return 1
    text = format_summary(summary, stop_exits)
    print(text)
    if mfe_text:  # stdout/journal only — the Telegram digest stays short
        print(mfe_text)
    if refusal_text:  # same rule: study output never reaches Telegram
        print(refusal_text)
    if timing_text:  # same rule again (IMP-040)
        print(timing_text)
    notifier = open_notifier(cfg)
    if notifier is not None:
        notifier.send(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
