"""Tests for the persistence layer (Phase 6).

A fake DB-API connection captures executed SQL + params so we can assert the writes
without a driver or a network, mirroring the executor/market-data test style.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from bot.executor import ExecutionResult
from bot.persistence import TapeContext, TradeRecorder, TradeStore, open_store
from bot.risk import ExitResult
from bot.signals import ConfidenceBreakdown

# Column offsets into the dbo.trades INSERT param tuple. Named because the tuple grows:
# IMP-029 appended atr_pct + ribbon_spread_pct, which silently shifted every tail slice.
_CONF_SUBSCORES = slice(9, 14)  # conf_crossover..conf_volatility
_TAPE = slice(14, 16)  # atr_pct, ribbon_spread_pct


class _FakeCursor:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn
        self._row: tuple | None = None

    def execute(self, sql, params=()):
        self._conn.calls.append((" ".join(sql.split()), tuple(params)))
        if self._conn.raise_on and self._conn.raise_on in sql:
            raise RuntimeError("db boom")
        if "SELECT id FROM dbo.trades WHERE entry_order_id" in sql:
            # IMP-028's idempotency lookup: a row only exists if the first attempt committed.
            self._row = (
                (self._conn.existing_id,) if self._conn.existing_id is not None else None
            )
        elif "OUTPUT INSERTED.id, INSERTED.qty" in sql:
            self._row = (self._conn.next_id, self._conn.open_qty)
        elif "OUTPUT INSERTED.id" in sql:
            self._row = (self._conn.next_id,)
        else:
            self._row = None
        return self

    def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(
        self, *, next_id=7, open_qty=25, raise_on=None, raise_on_commit=False, existing_id=None
    ) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self.commits = 0
        self.closed = False
        self.next_id = next_id
        self.open_qty = open_qty
        self.raise_on = raise_on
        self.raise_on_commit = raise_on_commit
        self.existing_id = existing_id

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        if self.raise_on_commit:
            raise RuntimeError("08S01 TCP Provider: Error code 0x20 (32)")
        self.commits += 1

    def close(self):
        self.closed = True


def _store(conn):
    return TradeStore(lambda: conn)


class _SeqFactory:
    """Hands out connections in order, counting calls — a reconnect gets the next one."""

    def __init__(self, *conns) -> None:
        self.conns = list(conns)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        # Past the end, keep returning the last one (a store that reconnects too often
        # would otherwise IndexError and hide the real assertion).
        idx = min(self.calls - 1, len(self.conns) - 1)
        return self.conns[idx]


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
    # conf_crossover, conf_trend, conf_rsi, conf_volume, conf_volatility. Sliced from a
    # named offset rather than off the tail: the tail moved when IMP-029 appended the
    # tape columns, and a tail slice failed open on the all-None cases.
    assert params[_CONF_SUBSCORES] == (0.9, 0.8, 1.0, 0.5, 0.7)
    assert params[8] == 80.0  # total confidence


def test_record_entry_tolerates_missing_breakdown():
    conn = _FakeConn()
    _store(conn).record_entry(_exec_result(), None)
    _trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[_CONF_SUBSCORES] == (None, None, None, None, None)


def test_record_entry_uses_parameters_not_interpolation():
    conn = _FakeConn()
    _store(conn).record_entry(_exec_result(symbol="WPM"), _breakdown())
    trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert "WPM" not in trade_sql  # value travels as a bound param, not inlined
    assert params[0] == "WPM"


# --- record_entry retry (IMP-028) ------------------------------------------


def _mu_0812():
    """The 2026-08-12 MU entry whose INSERT hit a dead socket and was never re-driven."""
    return _exec_result(
        symbol="MU", order_id="0d1a2b3c-mu-0812", qty=2, notional=1848.16,
        entry_price=924.08, stop_price=905.60, take_profit_price=1016.49, confidence=80.5,
    )


def test_record_entry_retries_once_on_a_fresh_connection_after_a_dead_socket():
    # Regression, 2026-08-12: `pyodbc.OperationalError ('08S01', 'TCP Provider: Error code
    # 0x20 (32)')` on the trades INSERT. record_entry logged, reset and returned None, so the
    # exit had no trade_id and the whole session vanished from dbo.trades while the broker
    # held a real filled position. The socket was healthy seconds later — one retry saves it.
    dead = _FakeConn(raise_on="INSERT INTO dbo.trades")
    fresh = _FakeConn(next_id=285)
    factory = _SeqFactory(dead, fresh)

    trade_id = TradeStore(factory).record_entry(_mu_0812(), _breakdown())

    assert trade_id == 285, "the retry must recover the row the dead socket lost"
    assert factory.calls == 2, "the retry must run on a reconnected socket, not the dead one"
    assert dead.closed, "the dead connection must be dropped before retrying"
    assert fresh.commits == 1
    trade_sql, params = next(c for c in fresh.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[0] == "MU" and params[2] == "0d1a2b3c-mu-0812"
    # the full entry write is re-driven, not just the trades row
    assert any("INSERT INTO dbo.orders" in s for s in _sql(fresh.calls))
    assert any("INSERT INTO dbo.positions" in s for s in _sql(fresh.calls))


def test_record_entry_retry_does_not_duplicate_a_trade_that_already_committed():
    # A failure raised *by commit()* may still have landed the transaction. Re-inserting
    # blind would double-count the position, so the retry looks the bracket up by its
    # Alpaca entry_order_id first and adopts the existing row.
    committed = _FakeConn(raise_on_commit=True)
    fresh = _FakeConn(next_id=999, existing_id=285)
    factory = _SeqFactory(committed, fresh)

    trade_id = TradeStore(factory).record_entry(_mu_0812(), _breakdown())

    assert trade_id == 285, "must adopt the row the first attempt committed, not mint a new one"
    assert not any("INSERT INTO dbo.trades" in s for s in _sql(fresh.calls)), (
        "a second INSERT would duplicate the trade"
    )
    assert fresh.commits == 0


def test_record_entry_gives_up_after_exactly_one_retry():
    # A database still down after a reconnect is an outage; the candle thread must not
    # block on it. Behaviour then degrades to exactly what it was before IMP-028.
    dead = _FakeConn(raise_on="INSERT INTO dbo.trades")
    still_dead = _FakeConn(raise_on="INSERT INTO dbo.trades")
    factory = _SeqFactory(dead, still_dead)

    trade_id = TradeStore(factory).record_entry(_mu_0812(), _breakdown())

    assert trade_id is None
    assert factory.calls == 2, "exactly one retry — never a loop against a down database"
    assert still_dead.closed, "the connection is reset so the next write reconnects"


def test_record_entry_happy_path_does_not_reconnect_or_look_itself_up():
    # Non-regression: the successful path must be byte-identical to pre-IMP-028 — one
    # connection, one commit, and no idempotency SELECT on the hot path.
    conn = _FakeConn(next_id=7)
    factory = _SeqFactory(conn)

    assert TradeStore(factory).record_entry(_exec_result(), _breakdown()) == 7
    assert factory.calls == 1
    assert conn.commits == 1
    assert not conn.closed
    assert not any("SELECT id FROM dbo.trades" in s for s in _sql(conn.calls))


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
    assert "pnl = (? - COALESCE(?, entry_price)) * qty" in update_sql
    assert "status = 'CLOSED'" in update_sql
    # entry_fill_price defaults to None → COALESCE keeps the stored entry_price (common case).
    # Trailing None, None are the IMP-037 excursion columns, unmeasured on this exit.
    assert params == (
        "close-1", None, 101.5, "bearish 1-min ribbon cross", 101.5, None, 101.5, None,
        None, None, "NFLX",
    )
    assert any("INSERT INTO dbo.orders" in s and "'EXIT'" in s for s in _sql(conn.calls))
    assert any("DELETE FROM dbo.positions" in s for s in _sql(conn.calls))


def test_record_exit_corrects_entry_price_from_delayed_fill():
    # Regression (2026-06-25): AMD's buy filled after IMP-009's submit-time readback budget, so
    # the row held the candle-close estimate (544.71) not the real fill (547.873). The risk
    # manager recovers the true fill at exit; record_exit must COALESCE it over entry_price and
    # recompute P/L off the truth, so the understated loss is corrected in the books.
    conn = _FakeConn(next_id=7, open_qty=6)
    exit_res = ExitResult(
        symbol="AMD",
        reason="end-of-day flatten",
        exit_price=538.88,
        qty=6,
        order_id="close-1",
        entry_fill_price=547.873,
    )
    _store(conn).record_exit(exit_res)
    update_sql, params = next(c for c in conn.calls if "UPDATE dbo.trades" in c[0])
    assert "entry_price = COALESCE(?, entry_price)" in update_sql
    # the corrected fill (547.873) is threaded into entry_price + both P/L formulas
    assert params == (
        "close-1", 547.873, 538.88, "end-of-day flatten",
        538.88, 547.873, 538.88, 547.873, None, None, "AMD",
    )


def test_record_exit_persists_the_in_trade_excursion():
    """IMP-037: mfe/mae reach the row, and a COALESCE guard stops a later re-record
    (an exit re-run with no measurement) from blanking a value already stored."""
    conn = _FakeConn(next_id=7, open_qty=12)
    exit_res = ExitResult(
        symbol="NVDA",
        reason="stop/target filled broker-side",
        exit_price=224.9025,
        qty=12,
        order_id="close-1",
        mfe_pct=1.15,
        mae_pct=-0.32,
    )
    _store(conn).record_exit(exit_res)

    update_sql, params = next(c for c in conn.calls if "UPDATE dbo.trades" in c[0])
    assert "mfe_pct = COALESCE(?, mfe_pct), mae_pct = COALESCE(?, mae_pct)" in update_sql
    assert params[-3:] == (1.15, -0.32, "NVDA")


def test_record_exit_uses_open_trade_qty_for_audit_order():
    conn = _FakeConn(next_id=7, open_qty=25)
    exit_res = ExitResult(symbol="NFLX", reason="x", exit_price=101.5, qty=None, order_id="c")
    _store(conn).record_exit(exit_res)
    _order_sql, params = next(
        c for c in conn.calls if "INSERT INTO dbo.orders" in c[0] and "'EXIT'" in c[0]
    )
    assert params == (7, "c", "NFLX", 25)  # qty came from the OUTPUT'd open trade


# --- reconcile_open_positions (IMP-006 phantom sweep) ----------------------


class _ReconcileCursor:
    def __init__(self, conn: _ReconcileConn) -> None:
        self._conn = conn

    def execute(self, sql, params=()):
        joined = " ".join(sql.split())
        self._conn.calls.append((joined, tuple(params)))
        if self._conn.raise_on and self._conn.raise_on in joined:
            raise RuntimeError("db boom")
        self._is_select = joined.startswith("SELECT symbol FROM dbo.trades")
        return self

    def fetchall(self):
        return [(s,) for s in self._conn.open_syms] if self._is_select else []


class _ReconcileConn:
    def __init__(self, open_syms, raise_on=None) -> None:
        self.open_syms = open_syms
        self.calls: list[tuple[str, tuple]] = []
        self.commits = 0
        self.closed = False
        self.raise_on = raise_on

    def cursor(self):
        return _ReconcileCursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def test_reconcile_closes_phantom_rows_broker_does_not_hold():
    # The exact 2026-06-22 scenario: 5 rows stuck OPEN since 06-11/06-12, broker flat.
    conn = _ReconcileConn(open_syms=["ENPH", "WPM", "NFLX", "QCOM", "AMD"])
    swept = _store(conn).reconcile_open_positions(broker_symbols=set())

    assert sorted(swept) == ["AMD", "ENPH", "NFLX", "QCOM", "WPM"]
    assert conn.commits == 1
    closes = [c for c in conn.calls if "UPDATE dbo.trades" in c[0]]
    assert len(closes) == 5
    update_sql, params = closes[0]
    # Honest close: zero fabricated P/L, exit prices off the stored entry.
    assert "pnl = 0" in update_sql and "exit_price = entry_price" in update_sql
    assert params == ("reconciled: not held at broker", "ENPH")
    assert sum(1 for c in conn.calls if "DELETE FROM dbo.positions" in c[0]) == 5


def test_reconcile_keeps_rows_the_broker_still_holds():
    conn = _ReconcileConn(open_syms=["ENPH", "AMD"])
    # AMD is genuinely held at the broker → must NOT be swept; ENPH is phantom.
    swept = _store(conn).reconcile_open_positions(broker_symbols={"amd"})  # case-insensitive

    assert swept == ["ENPH"]
    assert all("AMD" not in p for _s, p in conn.calls if "UPDATE dbo.trades" in _s)


def test_reconcile_no_phantoms_is_a_noop_close():
    conn = _ReconcileConn(open_syms=["AMD"])
    assert _store(conn).reconcile_open_positions(broker_symbols={"AMD"}) == []
    assert not any("UPDATE dbo.trades" in c[0] for c in conn.calls)


def test_reconcile_swallows_db_error_and_resets():
    conn = _ReconcileConn(open_syms=["ENPH"], raise_on="UPDATE dbo.trades")
    assert _store(conn).reconcile_open_positions(broker_symbols=set()) == []
    assert conn.closed is True


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
    assert params[_CONF_SUBSCORES] == (0.9, 0.8, 1.0, 0.5, 0.7)  # breakdown flowed through


def test_recorder_without_signal_still_records_entry():
    conn = _FakeConn()
    recorder = TradeRecorder(_store(conn))
    recorder.on_result(_exec_result())  # no prior on_signal
    _trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[_CONF_SUBSCORES] == (None, None, None, None, None)
    assert params[_TAPE] == (None, None)  # no signal -> no tape, but still a valid row


def test_recorder_exit_records_exit():
    conn = _FakeConn()
    recorder = TradeRecorder(_store(conn))
    recorder.on_exit(ExitResult(symbol="NFLX", reason="x", exit_price=99.0, qty=10, order_id="c"))
    assert any("UPDATE dbo.trades" in s for s in _sql(conn.calls))


# --- IMP-029: pre-entry tape context ---------------------------------------


def test_recorder_carries_tape_context_from_signal_to_entry():
    """Today's real INTC entry (2026-08-17 15:20): the row must carry its tape."""
    conn = _FakeConn()
    recorder = TradeRecorder(_store(conn))

    recorder.on_signal(_Signal("NFLX", _breakdown(), atr_pct=0.204, ribbon_spread_pct=0.061))
    recorder.on_result(_exec_result())

    _trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[_TAPE] == (0.204, 0.061)


def test_tape_context_is_written_as_its_own_columns():
    conn = _FakeConn()
    _store(conn).record_entry(_exec_result(), _breakdown(), TapeContext(0.158, 0.042))

    trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert "atr_pct" in trade_sql and "ribbon_spread_pct" in trade_sql
    # The INSERT must bind one placeholder per named column, or the values land in
    # the wrong columns — the failure mode a tail-slice assertion would not catch.
    columns = trade_sql.split("(", 1)[1].split(")", 1)[0].split(",")
    assert len(columns) == len(params) + 1  # status is a literal, not a placeholder
    assert params[_TAPE] == (0.158, 0.042)


def test_unseeded_tape_is_recorded_as_null_not_zero():
    """A flat tape and an unmeasured one are different facts; only NULL means unknown."""
    conn = _FakeConn()
    _store(conn).record_entry(_exec_result(), _breakdown(), TapeContext(None, None))

    _trade_sql, params = next(c for c in conn.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[_TAPE] == (None, None)


def test_tape_context_survives_the_imp028_retry():
    """The IMP-028 retry re-inserts — it must not drop the tape on the second attempt."""
    dead = _FakeConn(raise_on="INSERT INTO dbo.trades")
    fresh = _FakeConn(next_id=293)
    factory = _SeqFactory(dead, fresh)

    trade_id = TradeStore(factory).record_entry(
        _mu_0812(), _breakdown(), TapeContext(0.158, 0.042)
    )

    assert trade_id == 293
    _trade_sql, params = next(c for c in fresh.calls if "INSERT INTO dbo.trades" in c[0])
    assert params[_TAPE] == (0.158, 0.042), "the retry re-drove the row without its tape"


class _Signal:
    """Minimal stand-in for strategy.TradeSignal (only the fields the recorder reads)."""

    def __init__(self, symbol, confidence, atr_pct=None, ribbon_spread_pct=None):
        self.symbol = symbol
        self.confidence = confidence
        self.atr_pct = atr_pct
        self.ribbon_spread_pct = ribbon_spread_pct


# --- open_store ------------------------------------------------------------


def _cfg_with_conn(monkeypatch):
    monkeypatch.setenv("ALPACA_KEY_ID", "k")
    monkeypatch.setenv("ALPACA_SECRET", "s")
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setenv("SQLSERVER_CONN", "Driver=fake;Server=fake")
    from bot.config import Config

    return Config.load(dotenv=False)


def test_open_store_returns_none_when_conn_unset(monkeypatch):
    monkeypatch.setenv("ALPACA_KEY_ID", "k")
    monkeypatch.setenv("ALPACA_SECRET", "s")
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.delenv("SQLSERVER_CONN", raising=False)
    from bot.config import Config

    assert open_store(Config.load(dotenv=False)) is None


class _FlakyFactory:
    """A connection factory that raises for the first ``fail_times`` calls, then works.

    Mirrors a cold SQL Server that isn't accepting logins yet at startup (the pyodbc
    ``connect(timeout=10)`` raises ``HYT00 Login timeout expired``), then comes alive.
    """

    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("HYT00 Login timeout expired")
        return _FakeConn()


def test_open_store_retries_transient_init_failure_then_succeeds(monkeypatch):
    # Regression (2026-07-28): a single HYT00 login timeout at the 06:04 UTC cold start
    # disabled persistence AND collapsed the watchlist to the 3-symbol WATCHLIST env
    # default for the whole session (bot ran on NFLX/BIRD/WPM, 0 trades recorded).
    # IMP-019: the startup init now retries a transient failure instead of giving up.
    factory = _FlakyFactory(fail_times=2)  # fails twice, succeeds on the 3rd attempt
    sleeps: list[float] = []
    store = open_store(_cfg_with_conn(monkeypatch), conn_factory=factory, sleep=sleeps.append)

    assert store is not None  # rode out the transient outage — persistence stays ON
    assert factory.calls == 3
    assert sleeps == [5.0, 5.0]  # backed off between the two failed attempts


def test_open_store_returns_none_after_exhausting_retries(monkeypatch):
    # A genuinely-down DB still degrades gracefully (persistence off, env watchlist) —
    # the retry budget is bounded, it never blocks startup forever.
    factory = _FlakyFactory(fail_times=99)  # never recovers
    sleeps: list[float] = []
    store = open_store(_cfg_with_conn(monkeypatch), conn_factory=factory, sleep=sleeps.append)

    assert store is None
    assert factory.calls == 3  # exactly _SCHEMA_INIT_ATTEMPTS tries
    assert sleeps == [5.0, 5.0]  # slept only *between* attempts, not after the last


def test_open_store_succeeds_first_try_without_retrying(monkeypatch):
    factory = _FlakyFactory(fail_times=0)
    sleeps: list[float] = []
    store = open_store(_cfg_with_conn(monkeypatch), conn_factory=factory, sleep=sleeps.append)

    assert store is not None
    assert factory.calls == 1
    assert sleeps == []  # no backoff when the first attempt works


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


# --- closed_trades (IMP-025) ----------------------------------------------


class _ClosedTradesConn:
    def __init__(self, rows, raise_it=False):
        self._rows = rows
        self._raise = raise_it
        self.sql = None
        self.params = None
        # Every statement, in order. ``performance_summary`` issues three, so asserting
        # on ``sql`` alone would only ever see the last one (IMP-035).
        self.statements: list[tuple[str, tuple]] = []

    def cursor(self):
        return self

    def execute(self, sql, params=()):
        if self._raise:
            raise RuntimeError("db down")
        self.sql = " ".join(sql.split())
        self.params = tuple(params)
        self.statements.append((self.sql, self.params))
        return self

    def fetchone(self):
        return None  # aggregates fall back to their zero row

    def fetchall(self):
        return self._rows

    def close(self):
        pass


def test_closed_trades_maps_rows_and_windows_by_days():
    t0 = datetime(2026, 8, 10, 16, 17)
    t1 = datetime(2026, 8, 10, 19, 45)
    conn = _ClosedTradesConn(
        [(" mu ", t0, t1, 879.35, 872.25, -14.20, "trail", 861.76, 967.29)]
    )
    rows = TradeStore(lambda: conn).closed_trades(days=7)
    assert len(rows) == 1
    r = rows[0]
    assert r.symbol == "MU"  # trimmed + upper-cased
    assert (r.entry_price, r.exit_price, r.pnl) == (879.35, 872.25, -14.20)
    assert (r.entry_time_utc, r.exit_time_utc) == (t0, t1)
    # The doctrine's 1R anchor and take-profit leg travel with the row (IMP-039).
    assert (r.stop_price, r.target_price) == (861.76, 967.29)
    assert conn.params == (7,)
    assert "status = 'CLOSED'" in conn.sql
    assert "exit_time_utc IS NOT NULL" in conn.sql


def test_closed_trades_keeps_a_missing_bracket_leg_as_none():
    """Rows predating ``stop_price`` must stay distinguishable from a zero stop."""
    t0 = datetime(2026, 6, 10, 16, 17)
    t1 = datetime(2026, 6, 10, 19, 45)
    conn = _ClosedTradesConn([("MU", t0, t1, 879.35, 872.25, -14.20, "trail", None, None)])
    r = TradeStore(lambda: conn).closed_trades(days=7)[0]
    assert r.stop_price is None and r.target_price is None


def test_closed_trades_returns_empty_on_error():
    assert TradeStore(lambda: _ClosedTradesConn([], raise_it=True)).closed_trades() == []


# --- refusals (IMP-033) ----------------------------------------------------


def test_refusals_maps_rows_and_windows_by_days():
    # Real row: dbo.entry_refusals id 62, 2026-08-21.
    t0 = datetime(2026, 8, 21, 16, 21)
    conn = _ClosedTradesConn(
        [(" pltr ", t0, "crossover 0.20 < 0.25", 181.07, 75.99, True, 0.19813, 0.00944)]
    )
    rows = TradeStore(lambda: conn).refusals(days=7)
    assert len(rows) == 1
    r = rows[0]
    assert r.symbol == "PLTR"  # trimmed + upper-cased, as closed_trades does
    assert (r.candle_start_utc, r.close_price, r.confidence) == (t0, 181.07, 75.99)
    assert r.market_gate_open is True
    assert (r.atr_pct, r.ribbon_spread_pct) == (0.19813, 0.00944)
    assert conn.params == (7,)
    assert "dbo.entry_refusals" in conn.sql


def test_refusals_keeps_unmeasured_columns_none_across_schema_generations():
    """Pre-IMP-029/031 rows have NULL tape and gate — that is not 0.0 and not False."""
    conn = _ClosedTradesConn(
        [("GOOG", datetime(2026, 8, 18, 15, 0), "confidence 50 < 60", 339.4, None, None, None, None)]
    )
    r = TradeStore(lambda: conn).refusals()[0]
    assert r.confidence is None
    assert r.market_gate_open is None
    assert r.atr_pct is None and r.ribbon_spread_pct is None


def test_refusals_returns_empty_on_error():
    assert TradeStore(lambda: _ClosedTradesConn([], raise_it=True)).refusals() == []


# --- report windows are calendar days, not a rolling clock (IMP-035) -------


def _rolling_cutoff(anchor: datetime, days: int) -> datetime:
    """The OLD window: ``DATEADD(day, -N, SYSUTCDATETIME())`` — no DATE cast."""
    return anchor - timedelta(days=days)


def _calendar_cutoff(anchor: datetime, days: int) -> datetime:
    """The NEW window: ``CAST(DATEADD(day, -(N - 1), SYSUTCDATETIME()) AS DATE)``."""
    return datetime.combine((anchor - timedelta(days=days - 1)).date(), time.min)


@pytest.mark.parametrize(
    "reader, expected_table",
    [
        ("performance_summary", "dbo.trades"),
        ("closed_trades", "dbo.trades"),
        ("refusals", "dbo.entry_refusals"),
    ],
)
def test_all_windowed_readers_cut_on_a_calendar_date(reader, expected_table):
    """No reader may cut at the raw clock — that is what made windows run-time dependent."""
    conn = _ClosedTradesConn([])
    getattr(TradeStore(lambda: conn), reader)(days=3)

    windowed = [
        (sql, params)
        for sql, params in conn.statements
        if "SYSUTCDATETIME()" in sql
    ]
    assert len(windowed) == 1, "exactly one statement should carry the report window"
    sql, params = windowed[0]
    assert expected_table in sql
    assert "CAST(DATEADD(day, -(? - 1), SYSUTCDATETIME()) AS DATE)" in sql
    # The old rolling form must be gone, or the window silently follows the clock again.
    assert "DATEADD(day, -?, SYSUTCDATETIME())" not in sql
    assert params == (3,)


@pytest.mark.parametrize("days", [0, -1, -99])
def test_window_days_below_one_is_clamped_not_inverted(days):
    """``-(N - 1)`` with N < 1 would put the cutoff in the future and return nothing."""
    conn = _ClosedTradesConn([])
    TradeStore(lambda: conn).refusals(days=days)
    assert conn.params == (1,)
    # And the clamp must not quietly widen a valid window.
    conn = _ClosedTradesConn([])
    TradeStore(lambda: conn).refusals(days=7)
    assert conn.params == (7,)


def test_days_one_means_today_regardless_of_the_hour_the_routine_fires():
    """Regression: the real 2026-08-25 pre-market-slot drift.

    ``--days 1`` fired at the 11:30 UTC pre-market slot used to reach back to
    10:30 UTC *yesterday*, sweeping the previous session's afternoon into "today":
    68 refusals against the day's true 36. At the 21:10 UTC post-close slot the same
    code was correct, because the cutoff landed after the prior 20:00 UTC close.
    The calendar cutoff must return the same population at both hours.
    """
    yesterday_afternoon = datetime(2026, 8, 24, 15, 22)  # a real 08-24 refusal candle
    today_morning = datetime(2026, 8, 25, 14, 4)  # UBER 14:04, conf 68.8, gate open

    premarket = datetime(2026, 8, 25, 11, 30)
    postclose = datetime(2026, 8, 25, 21, 10)

    # OLD: the pre-market slot wrongly includes yesterday; the post-close slot does not.
    assert yesterday_afternoon >= _rolling_cutoff(premarket, 1)
    assert yesterday_afternoon < _rolling_cutoff(postclose, 1)

    # NEW: today only, and the answer no longer depends on when the routine ran.
    for anchor in (premarket, postclose):
        cutoff = _calendar_cutoff(anchor, 1)
        assert yesterday_afternoon < cutoff
        assert today_morning >= cutoff


def test_days_n_spans_n_calendar_days_inclusive_of_today():
    """``--days 2`` is today + yesterday — not a 48h tail off the current instant."""
    anchor = datetime(2026, 8, 25, 11, 30)
    assert _calendar_cutoff(anchor, 1) == datetime(2026, 8, 25, 0, 0)
    assert _calendar_cutoff(anchor, 2) == datetime(2026, 8, 24, 0, 0)
    assert _calendar_cutoff(anchor, 5) == datetime(2026, 8, 21, 0, 0)


# --- load_watchlist --------------------------------------------------------


class _WatchlistCursor:
    def __init__(self, rows, raise_it=False):
        self._rows = rows
        self._raise = raise_it

    def execute(self, sql, params=()):
        if self._raise:
            raise RuntimeError("db down")
        return self

    def fetchall(self):
        return self._rows


class _WatchlistConn:
    def __init__(self, rows, raise_it=False):
        self._rows = rows
        self._raise = raise_it
        self.closed = False

    def cursor(self):
        return _WatchlistCursor(self._rows, self._raise)

    def close(self):
        self.closed = True


def test_load_watchlist_returns_uppercased_symbols():
    conn = _WatchlistConn([("nflx",), (" wpm ",), ("BIRD",)])
    assert TradeStore(lambda: conn).load_watchlist() == ("NFLX", "WPM", "BIRD")


def test_load_watchlist_empty_table_returns_empty_tuple():
    assert TradeStore(lambda: _WatchlistConn([])).load_watchlist() == ()


def test_load_watchlist_returns_empty_on_error_and_resets():
    conn = _WatchlistConn([], raise_it=True)
    assert TradeStore(lambda: conn).load_watchlist() == ()
    assert conn.closed is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# --- IMP-030: the refusal write ----------------------------------------------------
# Column offsets into the dbo.entry_refusals INSERT param tuple, named for the same
# reason as _CONF_SUBSCORES above: this tuple will grow too.
_REF_SUBSCORES = slice(6, 11)  # conf_crossover..conf_volatility
_REF_TAPE = slice(11, 13)  # atr_pct, ribbon_spread_pct


def _refusal(**over):
    """Today's ABNB gate refusal (2026-08-18 14:25 UTC, conf 79.8) unless overridden."""
    from bot.strategy import RefusedEntry

    fields = dict(
        symbol="ABNB",
        candle_start=datetime(2026, 8, 18, 14, 25),
        reason="market gate closed (QQQ 5m ribbon not bullish)",
        market_gate_open=False,
        close_price=184.71,
        confidence=79.8,
        breakdown=ConfidenceBreakdown(
            crossover=0.9, trend=0.8, rsi=1.0, volume=0.5, volatility=0.7, total=79.8
        ),
        atr_pct=0.204,
        ribbon_spread_pct=0.061,
    )
    fields.update(over)
    return RefusedEntry(**fields)


def test_record_refusal_writes_the_full_row():
    conn = _FakeConn()
    _store(conn).record_refusal(_refusal())

    sql, params = conn.calls[0]
    assert "INSERT INTO dbo.entry_refusals" in sql
    assert params[0] == "ABNB"
    assert params[1] == datetime(2026, 8, 18, 14, 25)
    assert params[2] == "market gate closed (QQQ 5m ribbon not bullish)"
    assert params[3] is False  # market_gate_open — the gate study's key column
    assert params[4] == 184.71
    assert params[5] == 79.8
    assert params[_REF_SUBSCORES] == (0.9, 0.8, 1.0, 0.5, 0.7)
    assert params[_REF_TAPE] == (0.204, 0.061)
    assert conn.commits == 1


def test_record_refusal_placeholder_count_matches_the_columns():
    """A future column must not silently shift values into the wrong ones."""
    conn = _FakeConn()
    _store(conn).record_refusal(_refusal())
    sql, params = conn.calls[0]
    columns = sql.split("(", 1)[1].split(")", 1)[0].split(",")
    assert len(columns) == sql.count("?") == len(params)


def test_record_refusal_without_a_breakdown_writes_nulls_not_zeros():
    """'Not measured' and 'scored zero' are different facts, as for dbo.trades."""
    conn = _FakeConn()
    _store(conn).record_refusal(_refusal(breakdown=None, atr_pct=None, ribbon_spread_pct=None))
    _, params = conn.calls[0]
    assert params[_REF_SUBSCORES] == (None, None, None, None, None)
    assert params[_REF_TAPE] == (None, None)


def test_record_refusal_truncates_an_overlong_reason():
    """The column is VARCHAR(160); a long reason must not fail the whole write."""
    conn = _FakeConn()
    _store(conn).record_refusal(_refusal(reason="x" * 400))
    _, params = conn.calls[0]
    assert len(params[2]) == 160


def test_record_refusal_swallows_a_db_failure_and_resets():
    """Losing a datapoint costs a row in a study; raising here would cost positions."""
    conn = _FakeConn(raise_on="dbo.entry_refusals")
    store = _store(conn)
    store.record_refusal(_refusal())  # must not raise
    assert conn.commits == 0
    assert conn.closed  # connection dropped so the next write reconnects


def test_record_refusal_does_not_retry():
    """Unlike record_entry (IMP-028): a refusal is a datapoint, not a position."""
    conn = _FakeConn(raise_on="dbo.entry_refusals")
    _store(conn).record_refusal(_refusal())
    inserts = [c for c in conn.calls if "INSERT INTO dbo.entry_refusals" in c[0]]
    assert len(inserts) == 1


def test_recorder_on_refusal_reaches_the_store():
    conn = _FakeConn()
    TradeRecorder(_store(conn)).on_refusal(_refusal())
    assert any("INSERT INTO dbo.entry_refusals" in c[0] for c in conn.calls)


def test_refusals_do_not_touch_the_trades_table():
    """The two populations stay in separate tables; a refusal is not a trade."""
    conn = _FakeConn()
    _store(conn).record_refusal(_refusal())
    assert not any("dbo.trades" in c[0] for c in conn.calls)
    assert not any("dbo.positions" in c[0] for c in conn.calls)
    assert not any("dbo.orders" in c[0] for c in conn.calls)


def test_strategy_to_store_refusal_wiring_end_to_end(monkeypatch):
    """The seam between the two halves: a real engine + a real recorder write a row.

    Both halves are unit-tested above, but IMP-028's delivery failure was a wiring gap,
    not a logic bug. This drives an actual StrategyEngine refusal through TradeRecorder
    into the store so the seam cannot silently come apart.
    """
    from bot.config import Config
    from tests.test_strategy import (
        _FakeEngine,
        _candle,
        _near_miss_trigger,
        _open_gate,
    )

    for k, v in {
        "ALPACA_KEY_ID": "k",
        "ALPACA_SECRET": "s",
        "TELEGRAM_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "c",
    }.items():
        monkeypatch.setenv(k, v)
    cfg = Config.load(dotenv=False)

    conn = _FakeConn()
    recorder = TradeRecorder(_store(conn))

    from bot.strategy import StrategyEngine

    eng = StrategyEngine(
        cfg,
        on_refusal=recorder.on_refusal,
        trigger_engine=_FakeEngine([_near_miss_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    assert eng.on_short_candle(_candle()) is None

    inserts = [c for c in conn.calls if "INSERT INTO dbo.entry_refusals" in c[0]]
    assert len(inserts) == 1
    params = inserts[0][1]
    assert params[0] == "NFLX"
    assert params[2] == "crossover 0.18 < 0.25"
    assert conn.commits == 1


# --- IMP-032: the market-gate duty-cycle write ---------------------------------------


def _gate_sample(**over):
    """QQQ's 14:20 gate candle on 2026-08-20 — shut, on the day the gate never opened."""
    from bot.strategy import MarketGateSample

    fields = dict(
        symbol="QQQ",
        candle_start=datetime(2026, 8, 20, 14, 20),
        gate_open=False,
        stacked=True,
        fast_rising=False,
        close_price=712.30,
        ema_fast=713.41,
        ema_mid=713.02,
        ema_slow=712.55,
    )
    fields.update(over)
    return MarketGateSample(**fields)


def test_record_gate_sample_writes_the_full_row():
    conn = _FakeConn()
    _store(conn).record_gate_sample(_gate_sample())

    sql, params = conn.calls[0]
    assert "INSERT INTO dbo.market_gate" in sql
    assert params[0] == "QQQ"
    assert params[1] == datetime(2026, 8, 20, 14, 20)
    assert params[2] is False  # gate_open
    assert params[3] is True  # stacked — ordering intact
    assert params[4] is False  # fast_rising — the conjunct that shut it
    assert params[5] == 712.30
    assert params[6:9] == (713.41, 713.02, 712.55)
    assert conn.commits == 1


def test_record_gate_sample_is_guarded_against_duplicating_a_bar():
    """This table is COUNTED to produce a duty cycle, so a re-emitted bar must be a
    no-op, not a second row — a duplicate would bias the statistic, not just repeat it.
    """
    conn = _FakeConn()
    _store(conn).record_gate_sample(_gate_sample())

    sql, params = conn.calls[0]
    assert "WHERE NOT EXISTS" in sql
    # the guard is keyed on the unique (symbol, candle_start_utc) index
    assert params[-2:] == ("QQQ", datetime(2026, 8, 20, 14, 20))


def test_record_gate_sample_placeholder_count_matches_the_columns():
    """A future column must not silently shift values into the wrong ones."""
    conn = _FakeConn()
    _store(conn).record_gate_sample(_gate_sample())
    sql, params = conn.calls[0]
    columns = sql.split("(", 1)[1].split(")", 1)[0].split(",")
    assert len(columns) + 2 == sql.count("?") == len(params)  # +2 for the NOT EXISTS guard


def test_record_gate_sample_swallows_a_database_error():
    """Observational data must never take the strategy down with it."""
    conn = _FakeConn(raise_on="dbo.market_gate")
    _store(conn).record_gate_sample(_gate_sample())  # must not raise
    assert conn.commits == 0
    assert conn.closed  # connection dropped so the next write reconnects


def test_recorder_forwards_gate_samples_to_the_store():
    conn = _FakeConn()
    TradeRecorder(_store(conn)).on_gate_sample(_gate_sample())
    assert any("INSERT INTO dbo.market_gate" in c[0] for c in conn.calls)
