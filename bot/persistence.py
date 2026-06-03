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
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bot.config import Config
    from bot.executor import ExecutionResult
    from bot.risk import ExitResult
    from bot.signals import ConfidenceBreakdown
    from bot.strategy import TradeSignal

log = logging.getLogger("ustradebot.persistence")

# A factory returning a fresh DB-API 2.0 connection (pyodbc in production, a fake
# in tests). Kept abstract so the store never imports the driver directly.
ConnectionFactory = Callable[[], Any]

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
_GO_SEPARATOR = re.compile(r"(?im)^[ \t]*GO[ \t]*$")


def _sub(breakdown: ConfidenceBreakdown | None, field: str) -> float | None:
    """Pull one 0–1 sub-score off the breakdown, or ``None`` when we don't have it."""
    return getattr(breakdown, field) if breakdown is not None else None


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
        self, result: ExecutionResult, breakdown: ConfidenceBreakdown | None = None
    ) -> int | None:
        """Persist a submitted bracket entry; returns the new ``trades.id`` (or None)."""
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dbo.trades "
                "(symbol, model, status, entry_order_id, entry_price, qty, notional, "
                " stop_price, target_price, confidence, conf_crossover, conf_trend, "
                " conf_rsi, conf_volume, conf_volatility) "
                "OUTPUT INSERTED.id "
                "VALUES (?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
        except Exception:
            log.exception("failed to persist entry for %s", result.symbol)
            self._reset()
            return None

    def record_exit(self, result: ExitResult) -> None:
        """Close the symbol's open trade: set exit fields + realized P/L, drop position."""
        try:
            conn = self._connection()
            cur = conn.cursor()
            # P/L is computed in SQL from the stored entry_price/qty so we never have
            # to carry them back here. OUTPUT hands us the trade id + qty for the
            # audit-log order row below.
            cur.execute(
                "UPDATE dbo.trades SET "
                "status = 'CLOSED', exit_order_id = ?, exit_time_utc = SYSUTCDATETIME(), "
                "exit_price = ?, exit_reason = ?, "
                "pnl = (? - entry_price) * qty, "
                "pnl_pct = (? / entry_price - 1) * 100, "
                "updated_at_utc = SYSUTCDATETIME() "
                "OUTPUT INSERTED.id, INSERTED.qty "
                "WHERE symbol = ? AND status = 'OPEN'",
                (
                    result.order_id,
                    result.exit_price,
                    result.reason,
                    result.exit_price,
                    result.exit_price,
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


class TradeRecorder:
    """Wires :class:`TradeStore` onto the strategy/executor/risk callbacks.

    Pass its methods as (one of) the ``on_signal`` / ``on_result`` / ``on_exit``
    callbacks. It caches the latest confidence breakdown per symbol from the signal
    so the entry write can store the full sub-score breakdown, not just the total.
    """

    def __init__(self, store: TradeStore) -> None:
        self._store = store
        self._pending: dict[str, ConfidenceBreakdown] = {}

    def on_signal(self, signal: TradeSignal) -> None:
        self._pending[signal.symbol] = signal.confidence

    def on_result(self, result: ExecutionResult) -> None:
        breakdown = self._pending.pop(result.symbol, None)
        self._store.record_entry(result, breakdown)

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


def open_store(cfg: Config) -> TradeStore | None:
    """Build + initialize a store from config, or ``None`` if persistence is off.

    Returns ``None`` when ``SQLSERVER_CONN`` is unset, or when the schema bootstrap
    fails — in both cases the bot runs without persistence rather than refusing to
    trade (the DB is a side-channel, the broker bracket is the safety net).
    """
    if not cfg.sqlserver_conn:
        log.info("SQLSERVER_CONN not set — persistence disabled")
        return None
    store = TradeStore(make_pyodbc_factory(cfg.sqlserver_conn))
    try:
        store.ensure_schema()
    except Exception:
        log.exception("could not initialize the database — persistence disabled")
        store.close()
        return None
    return store
