"""Persistence layer (Phase 6).

Logs the trade lifecycle to SQL Server so we can later ask the question the whole
confidence model exists to answer: *do higher-confidence trades actually perform
better?* (see the ``vw_confidence_outcome`` view in ``sql/schema.sql``).

Two pieces:

- :class:`TradeStore` — the data-access layer. Owns a DB-API 2.0 connection and
  writes through **parameterized** statements (pyodbc ``qmark`` ``?`` placeholders).
  Every write is wrapped so a database hiccup logs and resets the connection but
  **never** propagates into the trading path — persistence is a side-channel, not a
  dependency of placing orders. The connection factory is injectable, mirroring the
  rest of the bot, so tests run without a driver or a network.
- :class:`TradeRecorder` — the glue that subscribes to the existing strategy /
  executor / risk callbacks. It pairs the :class:`~bot.signals.ConfidenceBreakdown`
  from ``on_signal`` with the :class:`~bot.executor.ExecutionResult` from
  ``on_result`` (keyed by symbol — the state machine holds at most one position per
  symbol) so the full sub-score breakdown is stored alongside the entry, then closes
  the trade out on ``on_exit`` with realized P/L computed in SQL from the stored
  entry price.

Fill / partial-fill rows (``dbo.fills``) need the broker trade-updates stream and
are deferred; exits here price the round-trip off the reversal candle's close,
which is what the risk manager has at exit time.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bot.config import Config
    from bot.executor import ExecutionResult
    from bot.risk import ExitResult
    from bot.signals import ConfidenceBreakdown
    from bot.strategy import MarketGateSample, RefusedEntry, TradeSignal

log = logging.getLogger("ustradebot.persistence")

# A factory returning a fresh DB-API 2.0 connection (pyodbc in production, a fake
# in tests). Kept abstract so the store never imports the driver directly.
ConnectionFactory = Callable[[], Any]

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
_GO_SEPARATOR = re.compile(r"(?im)^[ \t]*GO[ \t]*$")

# Startup DB-init retry budget (IMP-019). A single transient login timeout at a cold
# start (SQL Server not yet accepting connections, a network blip) used to disable
# persistence *and* collapse the watchlist to the 3-symbol WATCHLIST env default for
# the whole session (observed 2026-07-28: HYT00 login timeout at 06:04 → bot ran all
# day on NFLX/BIRD/WPM, 2 of them parked, 0 trades recorded). Retrying the one-shot
# init a few times with a short backoff rides out a transient outage instead. The
# per-attempt connect still has its own 10s pyodbc timeout; this only governs how many
# attempts the startup bootstrap makes before falling back.
_SCHEMA_INIT_ATTEMPTS = 3
_SCHEMA_INIT_RETRY_DELAY_SEC = 5.0

# ``--days N`` means N *calendar* days ending today (UTC) — not a rolling N×24h
# window ending at the instant the query runs (IMP-035).
#
# Cutting at a bare ``DATEADD(day, -N, SYSUTCDATETIME())`` put the boundary at
# whatever hour the routine happened to fire, which made every "last N days"
# figure in the review history non-reproducible:
#   * at the 11:30 UTC pre-market slot, ``--days 1`` swept in the *previous*
#     session's afternoon — 68 refusals instead of the day's true 36 on
#     2026-08-25, and ``--days 5`` returned 118 against a true 91;
#   * at the 21:10 UTC post-close slot it happened to be correct, because the
#     cutoff landed after the prior session's 20:00 UTC close.
# Same code, same data, different answer by time of day. Anchoring on the DATE
# boundary makes the window depend only on N. ``-(? - 1)`` so that ``--days 1``
# is today, ``--days 2`` is today plus yesterday, and so on.
#
# One shared fragment rather than three copies: the three windowed readers below
# must agree, or a multi-window study silently compares different populations.
_WINDOW_START_SQL = "CAST(DATEADD(day, -(? - 1), SYSUTCDATETIME()) AS DATE)"


def _window_days(days: int) -> int:
    """Clamp a report window to at least 1 calendar day.

    ``_WINDOW_START_SQL`` offsets by ``-(N - 1)``, so N < 1 would push the cutoff
    into the *future* and silently return an empty window. The CLI already clamps,
    but the store is called directly from tests and the replay harness too.
    """
    return max(1, int(days))


def _sub(breakdown: ConfidenceBreakdown | None, field: str) -> float | None:
    """Pull one 0–1 sub-score off the breakdown, or ``None`` when we don't have it."""
    return getattr(breakdown, field) if breakdown is not None else None


@dataclass(frozen=True)
class PerfBand:
    """One confidence-band row of ``dbo.vw_confidence_outcome`` (all-time)."""

    band: str
    trades: int
    wins: int
    win_rate: float
    avg_pnl: float
    total_pnl: float


@dataclass(frozen=True)
class TapeContext:
    """Pre-entry tape context recorded with an entry (IMP-029).

    Both fields are percentages of price and either may be ``None`` when the trigger
    ribbon had not seeded that indicator yet. Observational only — no trading code
    reads them back; they exist so the ``<0.5%``-MFE study can be run against
    ``dbo.trades`` rather than by re-fetching bars for every historical trade.
    """

    atr_pct: float | None = None
    ribbon_spread_pct: float | None = None


@dataclass(frozen=True)
class ClosedTrade:
    """One closed round trip, enough to rebuild its excursion (IMP-025).

    ``stop_price``/``target_price`` are the entry-time bracket legs (IMP-039): the
    stop is the 1R anchor the stop-exit doctrine measures ``profit_R`` against, and
    the target is what attributes an IMP-038 broker-side catch-all to the leg that
    actually filled. Both default to ``None`` — rows predating the columns must stay
    distinguishable from a genuine zero.
    """

    symbol: str
    entry_time_utc: Any  # naive UTC datetimes, as stored
    exit_time_utc: Any
    entry_price: float
    exit_price: float
    pnl: float
    exit_reason: str
    stop_price: float | None = None
    target_price: float | None = None


@dataclass(frozen=True)
class RefusedCandidate:
    """One row of ``dbo.entry_refusals``, read back for scoring (IMP-033).

    The read side of :class:`~bot.strategy.RefusedEntry`. Carries the pre-entry
    feature vector the refusal was judged on — confidence, the gate state, and the
    IMP-029 tape context — so a study can pair each *decision* with the outcome the
    tape went on to print. Everything except ``symbol``/``candle_start_utc`` may be
    ``None``: these rows span three schema generations and "not measured" must stay
    distinguishable from zero.
    """

    symbol: str
    candle_start_utc: Any  # naive UTC datetime, as stored
    reason: str
    close_price: float
    confidence: float | None = None
    market_gate_open: bool | None = None
    atr_pct: float | None = None
    ribbon_spread_pct: float | None = None


@dataclass(frozen=True)
class PerformanceSummary:
    """Aggregate trading performance for the Phase 10 daily/weekly report."""

    days: int  # window for the headline figures
    trades: int
    wins: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    open_positions: int
    bands: list[PerfBand]  # all-time, by confidence band


class TradeStore:
    """Writes the trade lifecycle to SQL Server through parameterized statements."""

    def __init__(
        self,
        conn_factory: ConnectionFactory,
        *,
        schema_path: Path = _SCHEMA_PATH,
    ) -> None:
        self._conn_factory = conn_factory
        self._schema_path = schema_path
        self._conn: Any | None = None

    # --- connection management --------------------------------------------

    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _reset(self) -> None:
        """Drop the connection so the next write reconnects (called after an error)."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # already broken — nothing more we can do
                pass
        self._conn = None

    def close(self) -> None:
        self._reset()

    # --- schema ------------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create the tables/view if absent. Raises on failure (caller decides)."""
        sql_text = self._schema_path.read_text(encoding="utf-8")
        batches = [b.strip() for b in _GO_SEPARATOR.split(sql_text) if b.strip()]
        conn = self._connection()
        cur = conn.cursor()
        for batch in batches:
            cur.execute(batch)
        conn.commit()
        log.info("database schema ensured (%d batches)", len(batches))

    # --- writes ------------------------------------------------------------

    def record_entry(
        self,
        result: ExecutionResult,
        breakdown: ConfidenceBreakdown | None = None,
        tape: TapeContext | None = None,
    ) -> int | None:
        """Persist a submitted bracket entry; returns the new ``trades.id`` (or None).

        ``tape`` is the pre-entry tape context (IMP-029), stored alongside the confidence
        breakdown. Optional so a caller that has none still writes a valid row.

        Retries **once** on a fresh connection (IMP-028). The 2026-08-12 MU entry hit a
        socket that had gone stale between sessions (``08S01 TCP Provider``); the write
        was lost, the exit then had no ``trade_id`` to attach to, and the whole session
        vanished from ``dbo.trades`` while the broker held a real, filled position. The
        connection was healthy 12 seconds later — every later write that day succeeded —
        so the row was recoverable and simply never re-driven. :meth:`_reset` already
        makes the *next* write reconnect; this makes *this* write take that path.

        The retry is **idempotent**: a failure raised by ``commit()`` may have landed the
        transaction anyway, so before re-inserting we look the trade up by its Alpaca
        ``entry_order_id`` (unique per bracket) and return the existing id if the first
        attempt did commit. Retrying blind would double-count the position. Exactly one
        retry — a database that is still down after a reconnect is an outage, and the
        candle thread must not block on it.
        """
        try:
            return self._insert_entry(result, breakdown, tape)
        except Exception:
            log.exception(
                "failed to persist entry for %s — retrying once on a fresh connection",
                result.symbol,
            )
            self._reset()

        try:
            existing = self._trade_id_for_order(result.order_id)
            if existing is not None:
                # The first attempt's commit landed before the socket died.
                log.warning(
                    "DB entry %s was already committed as trade_id=%s — not re-inserting",
                    result.symbol,
                    existing,
                )
                return existing
            trade_id = self._insert_entry(result, breakdown, tape)
            log.info("DB entry %s recovered on retry (trade_id=%s)", result.symbol, trade_id)
            return trade_id
        except Exception:
            log.exception(
                "entry retry failed for %s — this trade will be MISSING from dbo.trades",
                result.symbol,
            )
            self._reset()
            return None

    def _trade_id_for_order(self, entry_order_id: str) -> int | None:
        """``trades.id`` for an Alpaca entry order, or ``None`` if it never committed."""
        cur = self._connection().cursor()
        cur.execute(
            "SELECT id FROM dbo.trades WHERE entry_order_id = ?", (entry_order_id,)
        )
        row = cur.fetchone()
        return int(row[0]) if row else None

    def _insert_entry(
        self,
        result: ExecutionResult,
        breakdown: ConfidenceBreakdown | None,
        tape: TapeContext | None = None,
    ) -> int | None:
        """The entry write itself, as one transaction. Raises — the caller decides."""
        conn = self._connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dbo.trades "
            "(symbol, model, status, entry_order_id, entry_price, qty, notional, "
            " stop_price, target_price, confidence, conf_crossover, conf_trend, "
            " conf_rsi, conf_volume, conf_volatility, atr_pct, ribbon_spread_pct) "
            "OUTPUT INSERTED.id "
            "VALUES (?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                result.symbol,
                result.model,
                result.order_id,
                result.entry_price,
                result.qty,
                result.notional,
                result.stop_price,
                result.take_profit_price,
                result.confidence,
                _sub(breakdown, "crossover"),
                _sub(breakdown, "trend"),
                _sub(breakdown, "rsi"),
                _sub(breakdown, "volume"),
                _sub(breakdown, "volatility"),
                tape.atr_pct if tape else None,
                tape.ribbon_spread_pct if tape else None,
            ),
        )
        row = cur.fetchone()
        trade_id = int(row[0]) if row else None
        cur.execute(
            "INSERT INTO dbo.orders "
            "(trade_id, alpaca_order_id, symbol, side, role, qty, order_type, "
            " limit_price, stop_price, status, confidence) "
            "VALUES (?, ?, ?, 'BUY', 'ENTRY', ?, 'BRACKET', ?, ?, ?, ?)",
            (
                trade_id,
                result.order_id,
                result.symbol,
                result.qty,
                result.take_profit_price,
                result.stop_price,
                result.status,
                result.confidence,
            ),
        )
        # One position per symbol: replace any stale row outright.
        cur.execute("DELETE FROM dbo.positions WHERE symbol = ?", (result.symbol,))
        cur.execute(
            "INSERT INTO dbo.positions "
            "(symbol, trade_id, qty, entry_price, stop_price, target_price) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                result.symbol,
                trade_id,
                result.qty,
                result.entry_price,
                result.stop_price,
                result.take_profit_price,
            ),
        )
        conn.commit()
        log.info(
            "DB entry %s trade_id=%s qty=%d conf=%.1f",
            result.symbol,
            trade_id,
            result.qty,
            result.confidence,
        )
        return trade_id

    def record_refusal(self, refusal: RefusedEntry) -> None:
        """Persist one refused entry candidate (IMP-030). Never raises.

        Unlike :meth:`record_entry` this does **not** retry. A refusal is a datapoint,
        not a position — losing one to a transient socket costs a row in a study, not
        money, and the candle thread must not pay two round trips for it. It also does
        not reset the connection on the happy path, so the ~30 writes a session ride the
        same socket the entry/exit writes use.
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dbo.entry_refusals "
                "(symbol, candle_start_utc, reason, market_gate_open, close_price, "
                " confidence, conf_crossover, conf_trend, conf_rsi, conf_volume, "
                " conf_volatility, atr_pct, ribbon_spread_pct) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    refusal.symbol,
                    refusal.candle_start,
                    refusal.reason[:160],  # column width; reasons are short but bounded
                    refusal.market_gate_open,
                    refusal.close_price,
                    refusal.confidence,
                    _sub(refusal.breakdown, "crossover"),
                    _sub(refusal.breakdown, "trend"),
                    _sub(refusal.breakdown, "rsi"),
                    _sub(refusal.breakdown, "volume"),
                    _sub(refusal.breakdown, "volatility"),
                    refusal.atr_pct,
                    refusal.ribbon_spread_pct,
                ),
            )
            conn.commit()
        except Exception:
            # Observational data must never take the strategy down with it.
            log.exception("failed to persist refusal for %s", refusal.symbol)
            self._reset()

    def record_gate_sample(self, sample: MarketGateSample) -> None:
        """Persist one market-gate observation (IMP-032). Never raises.

        Same contract as :meth:`record_refusal` — no retry, no reset on the happy
        path — for the same reason: it is a datapoint, not a position. ~78 writes a
        session.

        The insert is guarded by ``WHERE NOT EXISTS`` against the unique
        ``(symbol, candle_start_utc)`` key so a re-emitted bar is a silent no-op
        rather than a duplicate. This table is *counted* to produce a duty cycle, so
        a double-written bar would not merely repeat a row, it would bias the
        statistic the table exists to compute.
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dbo.market_gate "
                "(symbol, candle_start_utc, gate_open, stacked, fast_rising, "
                " close_price, ema_fast, ema_mid, ema_slow) "
                "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ? "
                "WHERE NOT EXISTS (SELECT 1 FROM dbo.market_gate "
                "                  WHERE symbol = ? AND candle_start_utc = ?)",
                (
                    sample.symbol,
                    sample.candle_start,
                    sample.gate_open,
                    sample.stacked,
                    sample.fast_rising,
                    sample.close_price,
                    sample.ema_fast,
                    sample.ema_mid,
                    sample.ema_slow,
                    sample.symbol,
                    sample.candle_start,
                ),
            )
            conn.commit()
        except Exception:
            # Observational data must never take the strategy down with it.
            log.exception("failed to persist gate sample for %s", sample.symbol)
            self._reset()

    def record_exit(self, result: ExitResult) -> None:
        """Close the symbol's open trade: set exit fields + realized P/L, drop position."""
        try:
            conn = self._connection()
            cur = conn.cursor()
            # P/L is computed in SQL from the stored entry_price/qty so we never have
            # to carry them back here. OUTPUT hands us the trade id + qty for the
            # audit-log order row below. When the risk manager recovered a corrected
            # entry fill (a buy whose fill landed after IMP-009's submit-time readback
            # budget, so the row holds the candle-close estimate — 2026-06-25 AMD), we
            # COALESCE it over the stored entry_price and recompute P/L off the truth;
            # ``None`` keeps the existing entry_price untouched (the common case).
            entry_fill = getattr(result, "entry_fill_price", None)
            cur.execute(
                "UPDATE dbo.trades SET "
                "status = 'CLOSED', exit_order_id = ?, exit_time_utc = SYSUTCDATETIME(), "
                "entry_price = COALESCE(?, entry_price), "
                "exit_price = ?, exit_reason = ?, "
                "pnl = (? - COALESCE(?, entry_price)) * qty, "
                "pnl_pct = (? / COALESCE(?, entry_price) - 1) * 100, "
                # In-trade excursion (IMP-037). COALESCE keeps any already-stored value
                # when the risk manager has none to offer, so a re-recorded exit can
                # never blank a measurement it simply didn't observe.
                "mfe_pct = COALESCE(?, mfe_pct), mae_pct = COALESCE(?, mae_pct), "
                "updated_at_utc = SYSUTCDATETIME() "
                "OUTPUT INSERTED.id, INSERTED.qty "
                "WHERE symbol = ? AND status = 'OPEN'",
                (
                    result.order_id,
                    entry_fill,
                    result.exit_price,
                    result.reason,
                    result.exit_price,
                    entry_fill,
                    result.exit_price,
                    entry_fill,
                    getattr(result, "mfe_pct", None),
                    getattr(result, "mae_pct", None),
                    result.symbol,
                ),
            )
            row = cur.fetchone()
            trade_id = int(row[0]) if row else None
            qty = int(row[1]) if row else result.qty
            cur.execute(
                "INSERT INTO dbo.orders "
                "(trade_id, alpaca_order_id, symbol, side, role, qty, order_type, status) "
                "VALUES (?, ?, ?, 'SELL', 'EXIT', ?, 'CLOSE', 'submitted')",
                (trade_id, result.order_id, result.symbol, qty),
            )
            cur.execute("DELETE FROM dbo.positions WHERE symbol = ?", (result.symbol,))
            conn.commit()
            log.info(
                "DB exit %s trade_id=%s @ %.4f (%s)",
                result.symbol,
                trade_id,
                result.exit_price,
                result.reason,
            )
        except Exception:
            log.exception("failed to persist exit for %s", result.symbol)
            self._reset()

    def reconcile_open_positions(self, broker_symbols: Iterable[str]) -> list[str]:
        """Close DB-``OPEN`` trade rows the broker no longer holds (phantom sweep).

        The strategy's ``reconcile`` handles the *other* direction (broker-held names
        the bot re-adopts as MANAGING). This handles the gap that has bitten us
        repeatedly: a row left ``OPEN`` in ``dbo.trades`` whose position the broker is
        not actually holding — e.g. a stop that filled broker-side and was recorded
        against an already-CLOSED twin (``trade_id=None`` exits), or pre-IMP-003 residue.
        Such rows never get closed by any normal path, so they accumulate as phantom
        "open positions" that misstate the book and can be swept into fictitious P/L.

        Each phantom is closed honestly: ``exit_price = entry_price`` so realized
        ``pnl`` is exactly **0** (we have no real fill for it and refuse to fabricate a
        gain), reason ``reconciled: not held at broker``. Bookkeeping only — places no
        orders, touches no risk limit. Wrapped like every other write: a DB error logs,
        resets the connection, and returns ``[]`` rather than reaching the trading path.

        Returns the list of swept symbols (empty when the book already matches).
        """
        held = {str(s).strip().upper() for s in broker_symbols if str(s).strip()}
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute("SELECT symbol FROM dbo.trades WHERE status = 'OPEN'")
            open_syms = [str(r[0]).strip() for r in (cur.fetchall() or []) if str(r[0]).strip()]
            phantom = [s for s in open_syms if s.upper() not in held]
            for symbol in phantom:
                cur.execute(
                    "UPDATE dbo.trades SET "
                    "status = 'CLOSED', exit_time_utc = SYSUTCDATETIME(), "
                    "exit_price = entry_price, exit_reason = ?, "
                    "pnl = 0, pnl_pct = 0, updated_at_utc = SYSUTCDATETIME() "
                    "WHERE symbol = ? AND status = 'OPEN'",
                    ("reconciled: not held at broker", symbol),
                )
                cur.execute("DELETE FROM dbo.positions WHERE symbol = ?", (symbol,))
            conn.commit()
            if phantom:
                log.warning(
                    "reconciled %d phantom OPEN row(s) the broker does not hold: %s",
                    len(phantom),
                    ", ".join(phantom),
                )
            return phantom
        except Exception:
            log.exception("failed to reconcile open positions against the broker")
            self._reset()
            return []

    # --- reads -------------------------------------------------------------

    def load_watchlist(self) -> tuple[str, ...]:
        """Return the enabled watchlist symbols (upper-cased), or ``()`` if none.

        Read-only and wrapped like the writes: a DB error logs, resets the
        connection, and returns ``()`` so the caller falls back to the env var.
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT symbol FROM dbo.watchlist WHERE enabled = 1 ORDER BY symbol"
            )
            symbols = tuple(
                str(r[0]).strip().upper() for r in (cur.fetchall() or []) if str(r[0]).strip()
            )
            return symbols
        except Exception:
            log.exception("failed to load watchlist from the database")
            self._reset()
            return ()

    # --- reads (Phase 10 reporting) ---------------------------------------

    def performance_summary(self, days: int = 1) -> PerformanceSummary | None:
        """Aggregate closed-trade stats over the last ``days`` + all-time by band.

        Read-only and wrapped like the writes: a DB error logs, resets the
        connection, and returns ``None`` (the report just won't send).
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*), SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), "
                "SUM(pnl), AVG(pnl) "
                "FROM dbo.trades "
                "WHERE status = 'CLOSED' AND pnl IS NOT NULL "
                f"AND exit_time_utc >= {_WINDOW_START_SQL}",
                (_window_days(days),),
            )
            row = cur.fetchone() or (0, 0, None, None)
            trades = int(row[0] or 0)
            wins = int(row[1] or 0)
            total_pnl = float(row[2] or 0.0)
            avg_pnl = float(row[3] or 0.0)

            cur.execute("SELECT COUNT(*) FROM dbo.positions")
            open_positions = int((cur.fetchone() or (0,))[0] or 0)

            cur.execute(
                "SELECT confidence_band, trades, wins, win_rate, avg_pnl, total_pnl "
                "FROM dbo.vw_confidence_outcome ORDER BY confidence_band DESC"
            )
            bands = [
                PerfBand(
                    band=str(b[0]),
                    trades=int(b[1] or 0),
                    wins=int(b[2] or 0),
                    win_rate=float(b[3] or 0.0),
                    avg_pnl=float(b[4] or 0.0),
                    total_pnl=float(b[5] or 0.0),
                )
                for b in (cur.fetchall() or [])
            ]
            return PerformanceSummary(
                days=days,
                trades=trades,
                wins=wins,
                win_rate=(wins / trades) if trades else 0.0,
                total_pnl=total_pnl,
                avg_pnl=avg_pnl,
                open_positions=open_positions,
                bands=bands,
            )
        except Exception:
            log.exception("failed to build performance summary")
            self._reset()
            return None

    def closed_trades(self, days: int = 1) -> list[ClosedTrade]:
        """Closed round trips over the last ``days``, oldest first (IMP-025).

        Feeds the excursion report. Read-only and wrapped like the rest: a DB error
        logs, resets the connection, and returns ``[]`` so the report degrades to
        its headline figures instead of failing.
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT symbol, entry_time_utc, exit_time_utc, entry_price, "
                "exit_price, pnl, exit_reason, stop_price, target_price "
                "FROM dbo.trades "
                "WHERE status = 'CLOSED' AND pnl IS NOT NULL "
                "AND exit_time_utc IS NOT NULL AND entry_time_utc IS NOT NULL "
                f"AND exit_time_utc >= {_WINDOW_START_SQL} "
                "ORDER BY entry_time_utc",
                (_window_days(days),),
            )
            return [
                ClosedTrade(
                    symbol=str(r[0]).strip().upper(),
                    entry_time_utc=r[1],
                    exit_time_utc=r[2],
                    entry_price=float(r[3]),
                    exit_price=float(r[4]),
                    pnl=float(r[5]),
                    exit_reason=str(r[6] or ""),
                    # NULL stays NULL: the doctrine falls back to the configured
                    # stop width only when there is no recorded anchor (IMP-039).
                    stop_price=None if r[7] is None else float(r[7]),
                    target_price=None if r[8] is None else float(r[8]),
                )
                for r in (cur.fetchall() or [])
            ]
        except Exception:
            log.exception("failed to load closed trades")
            self._reset()
            return []

    def refusals(self, days: int = 1) -> list[RefusedCandidate]:
        """Scored-but-refused candidates over the last ``days``, oldest first (IMP-033).

        Feeds the refusal-outcome study. Read-only and wrapped exactly like
        :meth:`closed_trades`: a DB error logs, resets the connection, and returns
        ``[]`` so the report degrades rather than fails.
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT symbol, candle_start_utc, reason, close_price, confidence, "
                "market_gate_open, atr_pct, ribbon_spread_pct "
                "FROM dbo.entry_refusals "
                "WHERE candle_start_utc IS NOT NULL AND close_price IS NOT NULL "
                f"AND candle_start_utc >= {_WINDOW_START_SQL} "
                "ORDER BY candle_start_utc",
                (_window_days(days),),
            )
            return [
                RefusedCandidate(
                    symbol=str(r[0]).strip().upper(),
                    candle_start_utc=r[1],
                    reason=str(r[2] or ""),
                    close_price=float(r[3]),
                    confidence=None if r[4] is None else float(r[4]),
                    market_gate_open=None if r[5] is None else bool(r[5]),
                    atr_pct=None if r[6] is None else float(r[6]),
                    ribbon_spread_pct=None if r[7] is None else float(r[7]),
                )
                for r in (cur.fetchall() or [])
            ]
        except Exception:
            log.exception("failed to load entry refusals")
            self._reset()
            return []


class TradeRecorder:
    """Wires :class:`TradeStore` onto the strategy/executor/risk callbacks.

    Pass its methods as (one of) the ``on_signal`` / ``on_result`` / ``on_exit``
    callbacks. It caches the latest confidence breakdown per symbol from the signal
    so the entry write can store the full sub-score breakdown, not just the total,
    and alongside it the signal's pre-entry tape context (IMP-029) — both are known
    at signal time and neither is available from the :class:`ExecutionResult`.
    """

    def __init__(self, store: TradeStore) -> None:
        self._store = store
        self._pending: dict[str, tuple[ConfidenceBreakdown, TapeContext]] = {}

    def on_signal(self, signal: TradeSignal) -> None:
        self._pending[signal.symbol] = (
            signal.confidence,
            TapeContext(
                atr_pct=signal.atr_pct,
                ribbon_spread_pct=signal.ribbon_spread_pct,
            ),
        )

    def on_result(self, result: ExecutionResult) -> None:
        breakdown, tape = self._pending.pop(result.symbol, (None, TapeContext()))
        self._store.record_entry(result, breakdown, tape)

    def on_refusal(self, refusal: RefusedEntry) -> None:
        self._store.record_refusal(refusal)

    def on_gate_sample(self, sample: MarketGateSample) -> None:
        self._store.record_gate_sample(sample)

    def on_exit(self, result: ExitResult) -> None:
        self._store.record_exit(result)


def make_pyodbc_factory(conn_str: str) -> ConnectionFactory:
    """Build a connection factory that opens a pyodbc connection on demand.

    Imported lazily so the module (and the test suite) load without the driver.
    """

    def factory() -> Any:
        import pyodbc

        return pyodbc.connect(conn_str, timeout=10)

    return factory


def open_store(
    cfg: Config,
    *,
    conn_factory: ConnectionFactory | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> TradeStore | None:
    """Build + initialize a store from config, or ``None`` if persistence is off.

    Returns ``None`` when ``SQLSERVER_CONN`` is unset, or when the schema bootstrap
    fails after ``_SCHEMA_INIT_ATTEMPTS`` tries — in both cases the bot runs without
    persistence rather than refusing to trade (the DB is a side-channel, the broker
    bracket is the safety net).

    The schema init is **retried with a short backoff** (IMP-019) so a transient
    login timeout at a cold start doesn't disable persistence *and* collapse the
    watchlist to the env default for the entire session. ``conn_factory`` / ``sleep``
    are injectable for tests; production builds a real pyodbc factory and sleeps for
    real.
    """
    if not cfg.sqlserver_conn:
        log.info("SQLSERVER_CONN not set — persistence disabled")
        return None
    factory = conn_factory or make_pyodbc_factory(cfg.sqlserver_conn)
    store = TradeStore(factory)
    for attempt in range(1, _SCHEMA_INIT_ATTEMPTS + 1):
        try:
            store.ensure_schema()
            if attempt > 1:
                log.info(
                    "database initialized on attempt %d/%d", attempt, _SCHEMA_INIT_ATTEMPTS
                )
            return store
        except Exception:
            store.close()  # drop the failed connection so the next attempt reconnects
            if attempt < _SCHEMA_INIT_ATTEMPTS:
                log.warning(
                    "database init attempt %d/%d failed — retrying in %.0fs",
                    attempt,
                    _SCHEMA_INIT_ATTEMPTS,
                    _SCHEMA_INIT_RETRY_DELAY_SEC,
                )
                sleep(_SCHEMA_INIT_RETRY_DELAY_SEC)
            else:
                log.exception(
                    "could not initialize the database after %d attempts — persistence "
                    "disabled (watchlist falls back to the WATCHLIST env var)",
                    _SCHEMA_INIT_ATTEMPTS,
                )
    return None
