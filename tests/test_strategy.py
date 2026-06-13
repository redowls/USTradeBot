"""Tests for the strategy state machine (Phase 3).

The two ribbon engines are replaced with fakes that return scripted snapshots, so
these tests exercise the state transitions and entry wiring without driving real
indicator history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bot.candles import Candle
from bot.config import Config
from bot.executor import ExecutionResult
from bot.indicators import RibbonSnapshot
from bot.risk import RiskManager
from bot.strategy import BotState, StrategyEngine

# A Tuesday, 14:00 UTC == 10:00 EDT -> inside the regular session.
_OPEN_TS = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)
# A Saturday -> market closed.
_WEEKEND_TS = datetime(2026, 6, 6, 14, 0, tzinfo=UTC)
# A Tuesday, 19:56 UTC == 15:56 EDT -> inside the 5-min end-of-day flatten window.
_CLOSE_WINDOW_TS = datetime(2026, 6, 2, 19, 56, tzinfo=UTC)

_ENV = {
    "ALPACA_KEY_ID": "k",
    "ALPACA_SECRET": "s",
    "TELEGRAM_TOKEN": "t",
    "TELEGRAM_CHAT_ID": "c",
}


@pytest.fixture
def cfg(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    return Config.load(dotenv=False)


class _FakeEngine:
    """Returns queued snapshots in order; remembers the last as ``snapshot``."""

    def __init__(self, snaps):
        self._snaps = list(snaps)
        self.last = None

    def update(self, candle):
        self.last = self._snaps.pop(0)
        return self.last

    def snapshot(self, _symbol):
        return self.last


def _candle(ts=_OPEN_TS, *, close=100.0, symbol="NFLX") -> Candle:
    return Candle(
        symbol=symbol,
        start=ts,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=100.0,
        trades=1,
    )


def _ribbon_snap(ribbon, prev_ribbon, *, ts=_OPEN_TS, close=100.0, **extra) -> RibbonSnapshot:
    fields = dict(
        rsi=None, prev_rsi=None, avg_volume=None, atr=None, volume=100.0, interval_seconds=60
    )
    fields.update(extra)
    return RibbonSnapshot(
        symbol="NFLX",
        candle_start=ts,
        close=close,
        ribbon=ribbon,
        prev_ribbon=prev_ribbon,
        **fields,
    )


def _open_gate() -> RibbonSnapshot:
    return _ribbon_snap((102.0, 101.0, 100.0), (101.0, 100.5, 100.0), interval_seconds=300)


def _fresh_strong_trigger() -> RibbonSnapshot:
    return _ribbon_snap(
        (101.0, 100.4, 100.0),
        (99.9, 100.4, 100.0),
        close=100.0,
        rsi=55.0,
        prev_rsi=50.0,
        volume=200.0,
        avg_volume=100.0,
        atr=0.1,
    )


def _not_ready_trigger() -> RibbonSnapshot:
    return _ribbon_snap((None, None, None), (None, None, None))


def test_warming_up_stays_waiting(cfg):
    eng = StrategyEngine(cfg, trigger_engine=_FakeEngine([_not_ready_trigger()]))
    sig = eng.on_short_candle(_candle())
    assert sig is None
    assert eng.state("NFLX") is BotState.WAITING


def test_market_closed_stays_waiting(cfg):
    eng = StrategyEngine(cfg, trigger_engine=_FakeEngine([_fresh_strong_trigger()]))
    sig = eng.on_short_candle(_candle(ts=_WEEKEND_TS))
    assert sig is None
    assert eng.state("NFLX") is BotState.WAITING


def test_entry_emits_signal_when_gate_and_trigger_align(cfg):
    seen = []
    eng = StrategyEngine(
        cfg,
        on_signal=seen.append,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())  # refresh the gate first
    sig = eng.on_short_candle(_candle())
    assert sig is not None
    assert sig.symbol == "NFLX"
    assert sig.confidence.total >= cfg.entry_threshold
    assert seen == [sig]
    assert eng.state("NFLX") is BotState.EVALUATING


def test_no_signal_without_open_gate(cfg):
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([]),  # never updated -> no gate snapshot
    )
    sig = eng.on_short_candle(_candle())
    assert sig is None
    assert eng.state("NFLX") is BotState.EVALUATING  # evaluated, just no candidate


def test_executing_state_is_not_re_evaluated(cfg):
    eng = StrategyEngine(cfg, trigger_engine=_FakeEngine([_fresh_strong_trigger()]))
    eng._state["NFLX"] = BotState.EXECUTING  # Phase 4 would own this
    sig = eng.on_short_candle(_candle())
    assert sig is None
    assert eng.state("NFLX") is BotState.EXECUTING  # unchanged


class _FakeExecutor:
    """Records execute() calls; returns a scripted result (or None for a skip)."""

    def __init__(self, result):
        self._result = result
        self.calls = []

    def execute(self, *, symbol, entry_price, confidence):
        self.calls.append((symbol, entry_price, confidence))
        return self._result


def _exec_result(symbol="NFLX"):
    return ExecutionResult(
        symbol=symbol,
        order_id="o1",
        qty=10,
        notional=1000.0,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        confidence=75.0,
        status="accepted",
        model="A",
        stop_order_id="stop-1",
    )


def test_successful_execution_drives_managing(cfg):
    ex = _FakeExecutor(_exec_result())
    eng = StrategyEngine(
        cfg,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle())
    assert sig is not None
    assert len(ex.calls) == 1 and ex.calls[0][0] == "NFLX"
    assert eng.state("NFLX") is BotState.MANAGING


def test_failed_execution_falls_back_to_evaluating(cfg):
    ex = _FakeExecutor(None)  # skip/reject
    eng = StrategyEngine(
        cfg,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    eng.on_short_candle(_candle())
    assert len(ex.calls) == 1
    assert eng.state("NFLX") is BotState.EVALUATING


def test_reconcile_marks_held_symbols_managing(cfg):
    eng = StrategyEngine(cfg)
    held = SimpleNamespace(symbol="NFLX", qty="5")
    unknown = SimpleNamespace(symbol="ZZZZ", qty="1")  # not on the watchlist
    eng.reconcile([held, unknown])
    assert eng.state("NFLX") is BotState.MANAGING
    assert eng.state("ZZZZ") is BotState.WAITING  # ignored, off-watchlist


def test_managing_symbol_is_not_re_evaluated(cfg):
    ex = _FakeExecutor(_exec_result())
    eng = StrategyEngine(
        cfg,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
    )
    eng._state["NFLX"] = BotState.MANAGING  # already holding
    sig = eng.on_short_candle(_candle())
    assert sig is None
    assert ex.calls == []  # never tried to execute
    assert eng.state("NFLX") is BotState.MANAGING


class _FakeCloser:
    """A minimal executor exposing close_position + replace_stop_price for risk."""

    def __init__(self, order_id="close-1"):
        self._order_id = order_id
        self.closed = []
        self.moved = []

    def close_position(self, symbol):
        self.closed.append(symbol)
        return self._order_id

    def replace_stop_price(self, stop_order_id, new_stop_price):
        self.moved.append((stop_order_id, new_stop_price))
        return True


def _rising_trigger(close=110.0) -> RibbonSnapshot:
    # price well above entry -> the trailing stop should ratchet up
    return _ribbon_snap((close, close - 1.0, close - 2.0), (close - 1.0, close - 1.5, close - 2.0),
                        close=close)


def test_managing_trails_stop_up(cfg):
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([_rising_trigger(110.0)]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()  # entry 100, stop 98, leg "stop-1"
    sig = eng.on_short_candle(_candle())
    assert sig is None
    # 110 * (1 - 0.02) = 107.8 > 98 -> stop moves up, position stays open (no close)
    assert closer.moved == [("stop-1", 107.8)]
    assert closer.closed == []
    assert eng.state("NFLX") is BotState.MANAGING


def test_managing_does_not_lower_stop(cfg):
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([_rising_trigger(99.0)]),  # 99*0.98=97.02 < 98 stop
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.on_short_candle(_candle())
    assert closer.moved == []  # never ratchets the stop down
    assert eng.state("NFLX") is BotState.MANAGING


def test_eod_window_flattens_managing_position(cfg):
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([_rising_trigger()]),  # flatten regardless of signal
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    sig = eng.on_short_candle(_candle(ts=_CLOSE_WINDOW_TS))
    assert sig is None
    assert closer.closed == ["NFLX"]  # flattened despite no reversal
    assert eng.state("NFLX") is BotState.WAITING
    assert "NFLX" not in eng._positions


def test_eod_window_blocks_new_entry(cfg):
    ex = _FakeExecutor(_exec_result())
    eng = StrategyEngine(
        cfg,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle(ts=_CLOSE_WINDOW_TS))
    assert sig is None
    assert ex.calls == []  # a qualifying setup is ignored inside the close window
    assert eng.state("NFLX") is BotState.WAITING


def test_feed_loss_halts_new_entries(cfg):
    risk = RiskManager(cfg, executor=_FakeCloser())
    risk.notify_feed_lost()
    ex = _FakeExecutor(_exec_result())
    eng = StrategyEngine(
        cfg,
        executor=ex,
        risk=risk,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle())
    assert sig is None
    assert ex.calls == []  # never evaluated/executed while the feed is down
    assert eng.state("NFLX") is BotState.WAITING


def test_signal_callback_error_is_swallowed(cfg):
    def boom(_sig):
        raise RuntimeError("alert down")

    eng = StrategyEngine(
        cfg,
        on_signal=boom,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle())  # must not raise
    assert sig is not None
