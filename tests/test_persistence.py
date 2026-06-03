"""Tests for the persistence layer (Phase 6).

A fake DB-API connection captures executed SQL + params so we can assert the writes
without a driver or a network, mirroring the executor/market-data test style.
"""

from __future__ import annotations

import pytest

from bot.executor import ExecutionResult
from bot.persistence import TradeRecorder, TradeStore, open_store
from bot.risk import ExitResult
from bot.signals import ConfidenceBreakdown


class _FakeCursor:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn
        self._row: tuple | None = None

    def execute(self, sql, params=()):
        self._conn.calls.append((" ".join(sql.split()), tuple(params)))
        if self._conn.raise_on and self._conn.raise_on in sql:
            raise RuntimeError("db boom")
        if "OUTPUT INSERTED.id, INSERTED.qty" in sql:
            self._row = (self._conn.next_id, self._conn.open_qty)
        elif "OUTPUT INSERTED.id" in sql:
            self._row = (self._conn.next_id,)
        else:
            self._row = None
        return self

    def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(self, *, next_id=7, open_qty=25, raise_on=None) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self.commits = 0
        self.closed = False
        self.next_id = next_id
        self.open_qty = open_qty
        self.raise_on = raise_on

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def _store(conn):
    return TradeStore(lambda: conn)


def _exec_result(**kw):
    base = dict(
        symbol="NFLX",
        order_id="order-1",
        qty=25,
        notional=2500.0,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        confidence=80.0,
        status="accepted",
        model="A",
    )
    base.update(kw)
    return ExecutionResult(**base)


def _breakdown():
    return ConfidenceBreakdown(
        crossover=0.9, trend=0.8, rsi=1.0, volume=0.5, volatility=0.7, total=80.0
    )


def _sql(calls):
    return [c[0] for c in calls]


# --- record_entry ----------------------------------------------------------


def test_record_entry_writes_trade_order_and_position():
    conn = _FakeConn(next_id=7)
    trade_id = _store(conn).record_entry(_exec_result(), _breakdown())

    assert trade_id == 7
    assert conn.commits == 1
    sqls = _sql(conn.calls)
    assert any("INSERT INTO dbo.trades" in s for s in sqls)
    assert any("INSERT INTO dbo.orders" in s and "'ENTRY'" in s for s in sqls)
    assert any("DELETE FROM dbo.positions" in s for s in sqls)
    assert any("INSERT INTO dbo.positions" in s for s in sqls)


def test_record_entry_stores_confidence_breakdown():
    conn = _FakeConn()
    _store(conn).record_entry(_exec_result(), _breakdown())

    trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    # ...confidence, conf_crossover, conf_trend, conf_rsi, conf_volume, conf_volatility
    assert params[-5:] == (0.9, 0.8, 1.0, 0.5, 0.7)
    assert params[8] == 80.0  # total confidence


def test_record_entry_tolerates_missing_breakdown():
    conn = _FakeConn()
    _store(conn).record_entry(_exec_result(), None)
    _trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[-5:] == (None, None, None, None, None)


def test_record_entry_uses_parameters_not_interpolation():
    conn = _FakeConn()
    _store(conn).record_entry(_exec_result(symbol="WPM"), _breakdown())
    trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert "WPM" not in trade_sql  # value travels as a bound param, not inlined
    assert params[0] == "WPM"


# --- record_exit -----------------------------------------------------------


def test_record_exit_closes_trade_with_pnl_and_drops_position():
    conn = _FakeConn(next_id=7, open_qty=25)
    exit_res = ExitResult(
        symbol="NFLX",
        reason="bearish 1-min ribbon cross",
        exit_price=101.5,
        qty=25,
        order_id="close-1",
    )
    _store(conn).record_exit(exit_res)

    assert conn.commits == 1
    update_sql, params = next(c for c in conn.calls if "UPDATE dbo.trades" in c[0])
    assert "pnl = (? - entry_price) * qty" in update_sql
    assert "status = 'CLOSED'" in update_sql
    assert params == ("close-1", 101.5, "bearish 1-min ribbon cross", 101.5, 101.5, "NFLX")
    assert any("INSERT INTO dbo.orders" in s and "'EXIT'" in s for s in _sql(conn.calls))
    assert any("DELETE FROM dbo.positions" in s for s in _sql(conn.calls))


def test_record_exit_uses_open_trade_qty_for_audit_order():
    conn = _FakeConn(next_id=7, open_qty=25)
    exit_res = ExitResult(symbol="NFLX", reason="x", exit_price=101.5, qty=None, order_id="c")
    _store(conn).record_exit(exit_res)
    _order_sql, params = next(
        c for c in conn.calls if "INSERT INTO dbo.orders" in c[0] and "'EXIT'" in c[0]
    )
    assert params == (7, "c", "NFLX", 25)  # qty came from the OUTPUT'd open trade


# --- error handling --------------------------------------------------------


def test_db_error_is_swallowed_and_connection_reset():
    conn = _FakeConn(raise_on="INSERT INTO dbo.trades")
    store = _store(conn)
    # Must not raise into the trading path; returns None and resets the connection.
    assert store.record_entry(_exec_result(), _breakdown()) is None
    assert conn.closed is True
    assert conn.commits == 0


# --- schema bootstrap ------------------------------------------------------


def test_ensure_schema_executes_batches_split_on_go():
    conn = _FakeConn()
    _store(conn).ensure_schema()  # runs against the real sql/schema.sql
    sqls = _sql(conn.calls)
    assert conn.commits == 1
    assert len(sqls) > 1  # multiple GO-separated batches
    assert any("CREATE TABLE dbo.trades" in s for s in sqls)
    assert any("CREATE OR ALTER VIEW dbo.vw_confidence_outcome" in s for s in sqls)
    assert not any(s.strip() == "GO" for s in sqls)  # separators stripped


# --- TradeRecorder glue ----------------------------------------------------


def test_recorder_pairs_signal_breakdown_with_entry():
    conn = _FakeConn()
    recorder = TradeRecorder(_store(conn))

    signal = _Signal("NFLX", _breakdown())
    recorder.on_signal(signal)
    recorder.on_result(_exec_result())

    _trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[-5:] == (0.9, 0.8, 1.0, 0.5, 0.7)  # breakdown flowed through


def test_recorder_without_signal_still_records_entry():
    conn = _FakeConn()
    recorder = TradeRecorder(_store(conn))
    recorder.on_result(_exec_result())  # no prior on_signal
    _trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[-5:] == (None, None, None, None, None)


def test_recorder_exit_records_exit():
    conn = _FakeConn()
    recorder = TradeRecorder(_store(conn))
    recorder.on_exit(ExitResult(symbol="NFLX", reason="x", exit_price=99.0, qty=10, order_id="c"))
    assert any("UPDATE dbo.trades" in s for s in _sql(conn.calls))


class _Signal:
    """Minimal stand-in for strategy.TradeSignal (only the fields the recorder reads)."""

    def __init__(self, symbol, confidence):
        self.symbol = symbol
        self.confidence = confidence


# --- open_store ------------------------------------------------------------


def test_open_store_returns_none_when_conn_unset(monkeypatch):
    monkeypatch.setenv("ALPACA_KEY_ID", "k")
    monkeypatch.setenv("ALPACA_SECRET", "s")
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.delenv("SQLSERVER_CONN", raising=False)
    from bot.config import Config

    assert open_store(Config.load(dotenv=False)) is None


# --- performance_summary (Phase 10 reads) ----------------------------------


class _ReadCursor:
    """Returns scripted rows keyed by a substring of the query."""

    def __init__(self, scalars, bands):
        self._scalars = scalars
        self._bands = bands
        self._mode = None

    def execute(self, sql, params=()):
        joined = " ".join(sql.split())
        if "vw_confidence_outcome" in joined:
            self._mode = "bands"
        elif "FROM dbo.positions" in joined:
            self._mode = "positions"
        else:
            self._mode = "headline"
        return self

    def fetchone(self):
        if self._mode == "headline":
            return self._scalars["headline"]
        if self._mode == "positions":
            return self._scalars["positions"]
        return None

    def fetchall(self):
        return self._bands if self._mode == "bands" else []


class _ReadConn:
    def __init__(self, scalars, bands):
        self._scalars = scalars
        self._bands = bands
        self.closed = False

    def cursor(self):
        return _ReadCursor(self._scalars, self._bands)

    def commit(self):
        pass

    def close(self):
        self.closed = True


def test_performance_summary_aggregates_window_and_bands():
    conn = _ReadConn(
        scalars={"headline": (4, 3, 120.5, 30.125), "positions": (2,)},
        bands=[("80-89", 2, 2, 1.0, 50.0, 100.0), ("60-69", 2, 1, 0.5, 10.25, 20.5)],
    )
    summary = TradeStore(lambda: conn).performance_summary(days=7)
    assert summary is not None
    assert summary.days == 7
    assert (summary.trades, summary.wins) == (4, 3)
    assert summary.win_rate == 0.75
    assert summary.total_pnl == 120.5
    assert summary.open_positions == 2
    assert [b.band for b in summary.bands] == ["80-89", "60-69"]
    assert summary.bands[0].total_pnl == 100.0


def test_performance_summary_handles_empty_window():
    conn = _ReadConn(scalars={"headline": (0, None, None, None), "positions": (0,)}, bands=[])
    summary = TradeStore(lambda: conn).performance_summary(days=1)
    assert summary is not None
    assert summary.trades == 0 and summary.win_rate == 0.0
    assert summary.total_pnl == 0.0 and summary.bands == []


def test_performance_summary_returns_none_on_error():
    class _BoomConn:
        def cursor(self):
            raise RuntimeError("db down")

        def close(self):
            pass

    assert TradeStore(lambda: _BoomConn()).performance_summary() is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
