"""Tests for the strategy state machine (Phase 3).

The two ribbon engines are replaced with fakes that return scripted snapshots, so
these tests exercise the state transitions and entry wiring without driving real
indicator history.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from bot.candles import Candle
from bot.config import EASTERN, Config
from bot.executor import ExecutionResult, StopOrderGone
from bot.indicators import RibbonSnapshot
from bot.risk import RiskManager
from bot.signals import ConfidenceBreakdown, EntryDecision
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

    def reconcile_exit(self, symbol):
        return None  # close succeeds here, so reconcile is never consulted

    def close_fill_price(self, order_id):
        return None  # no fill price scripted → exit keeps the candle-close estimate

    def entry_fill_price(self, order_id):
        return None  # no corrected entry fill scripted → exit keeps the stored entry price

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


class _StopGoneCloser:
    """Reproduces 2026-06-30: the stop leg filled broker-side, so replace_stop_price
    raises StopOrderGone and the position is already flat — close_position returns None
    (a 404) and reconcile_exit recovers the real broker-side fill."""

    def __init__(self, fill=("stop-1", 97.5)):
        self._fill = fill  # (order_id, broker-side fill price)
        self.moved = []
        self.closed = []
        self.reconciled = []

    def close_position(self, symbol):
        self.closed.append(symbol)
        return None  # already flat broker-side → exit_position falls to reconcile

    def reconcile_exit(self, symbol):
        self.reconciled.append(symbol)
        return self._fill

    def close_fill_price(self, order_id):
        return None

    def entry_fill_price(self, order_id):
        return 100.0  # entry buy did fill (position genuinely opened, then stopped out)

    def replace_stop_price(self, stop_order_id, new_stop_price):
        self.moved.append((stop_order_id, new_stop_price))
        raise StopOrderGone(stop_order_id)  # the leg already filled — can't be moved


def test_managing_reconciles_and_frees_when_stop_filled(cfg):
    # IMP-012 regression: 2026-06-30 AMD/SE stopped out broker-side intraday, so every
    # trailing move 422'd "order is not open" (~minutely, 504 tracebacks) and the symbols
    # sat MANAGING and un-re-enterable for ~4.5h until the EOD flatten. The manager must
    # detect the gone stop, reconcile the real exit ONCE, and release the symbol to WAITING.
    closer = _StopGoneCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([_rising_trigger(110.0)]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()  # entry 100, stop 98, leg "stop-1"
    sig = eng.on_short_candle(_candle())
    assert sig is None
    assert closer.moved == [("stop-1", 107.8)]    # the ratchet was attempted, reported gone
    assert closer.reconciled == ["NFLX"]          # exit reconciled from broker order history
    assert eng.state("NFLX") is BotState.WAITING   # freed, not stuck MANAGING
    assert "NFLX" not in eng._positions


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


class _FailingCloser:
    """An executor whose close_position always fails (reproduces 2026-06-16's
    persistent Alpaca 504 Gateway Timeouts on the EOD flatten)."""

    def __init__(self):
        self.attempts = []

    def close_position(self, symbol):
        self.attempts.append(symbol)
        return None  # 504 / timeout — close never submits

    def reconcile_exit(self, symbol):
        return None  # genuine outage, not an already-flat position — escalation must fire

    def replace_stop_price(self, stop_order_id, new_stop_price):
        return True


# A Tuesday, 19:59 UTC == 15:59 EDT -> 1 min to the 20:00 UTC close: inside the
# final escalation window (_FLATTEN_ESCALATE_MIN = 2.0), no retry runway left.
_FINAL_MINUTE_TS = datetime(2026, 6, 2, 19, 59, tzinfo=UTC)


def test_failed_eod_flatten_escalates_once(cfg):
    # IMP-002 regression: 2026-06-16 the EOD flatten 504'd through every retry on
    # 4 names and left them naked overnight with NO Telegram alert. The failed
    # flatten in the final minute must page the operator exactly once per symbol.
    alerts: list[str] = []
    closer = _FailingCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer, on_feed_alert=alerts.append),
        trigger_engine=_FakeEngine([_rising_trigger(), _rising_trigger()]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()

    eng.on_short_candle(_candle(ts=_FINAL_MINUTE_TS))
    assert closer.attempts == ["NFLX"]  # tried to close
    assert eng.state("NFLX") is BotState.MANAGING  # close failed -> stays held
    assert "NFLX" in eng._positions  # not dropped — position is still live
    assert len(alerts) == 1 and "NAKED" in alerts[0] and "NFLX" in alerts[0]

    # A second close-window candle must NOT re-page (dedup per symbol per session).
    eng.on_short_candle(_candle(ts=_FINAL_MINUTE_TS))
    assert len(alerts) == 1


def test_failed_eod_flatten_does_not_escalate_with_runway_left(cfg):
    # At 19:56 UTC (4 min to close) a failed close still has retry runway on later
    # candles, so it must NOT page yet — only the runway-exhausted case escalates.
    alerts: list[str] = []
    closer = _FailingCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer, on_feed_alert=alerts.append),
        trigger_engine=_FakeEngine([_rising_trigger()]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.on_short_candle(_candle(ts=_CLOSE_WINDOW_TS))  # 19:56 == 4 min out
    assert closer.attempts == ["NFLX"]  # still attempted the flatten
    assert alerts == []  # but no naked-overnight page yet


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


def test_standdown_blocks_new_entries(cfg):
    # IMP-016: once the broad-adverse-day stand-down has tripped, a qualifying candle must
    # NOT open a position — the same entry gate the feed-loss fail-safe uses. Align the
    # trip with the candle's session so the per-candle roll_session doesn't reset it.
    risk = RiskManager(cfg, executor=_FakeCloser())
    risk.roll_session(_OPEN_TS.astimezone(EASTERN).date())
    for _ in range(3):  # three consecutive losing exits (entry 100 → exit 98) trip it
        risk.exit_position("NFLX", 98.0, "stop", _exec_result())
    assert risk.entries_allowed is False
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
    assert ex.calls == []  # never evaluated/executed while stood down
    assert eng.state("NFLX") is BotState.WAITING


def test_new_session_candle_resets_standdown(cfg):
    # The strategy drives roll_session off the candle's Eastern date, so the next session's
    # first candle clears a PRIOR day's stand-down before the entry gate is checked.
    risk = RiskManager(cfg, executor=_FakeCloser())
    risk.roll_session(date(2026, 6, 1))  # a prior session, then tripped
    for _ in range(3):
        risk.exit_position("NFLX", 98.0, "stop", _exec_result())
    assert risk.entries_allowed is False
    ex = _FakeExecutor(_exec_result())
    eng = StrategyEngine(
        cfg,
        executor=ex,
        risk=risk,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())  # candle is 2026-06-02 → a new session
    sig = eng.on_short_candle(_candle())
    assert sig is not None  # the new-session roll re-enabled entries
    assert len(ex.calls) == 1
    assert eng.state("NFLX") is BotState.MANAGING


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


# A Tuesday, 20:02 UTC == 16:02 EDT -> 2 min past the 20:00 UTC close, inside the
# post-close grace sweep (_POSTCLOSE_GRACE_MIN = 3.0) the watchdog uses to catch a
# feed-dead carry.
_POST_CLOSE_TS = datetime(2026, 6, 2, 20, 2, tzinfo=UTC)


def test_tick_flattens_on_wall_clock_without_any_candle(cfg):
    # 2026-06-19 regression: the IEX feed went silent through the close window, so
    # the candle-driven flatten never ran and positions carried NAKED over the
    # weekend. The wall-clock watchdog must flatten with NO candle ever delivered.
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([]),  # no candle arrives -> snapshot stays None
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_CLOSE_WINDOW_TS)
    assert closer.closed == ["NFLX"]  # flattened on wall-clock, no candle needed
    assert eng.state("NFLX") is BotState.WAITING
    assert "NFLX" not in eng._positions


def test_tick_outside_close_window_is_noop(cfg):
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg, risk=RiskManager(cfg, executor=closer), trigger_engine=_FakeEngine([])
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_OPEN_TS)  # mid-session, well before the flatten window
    assert closer.closed == []  # the watchdog only flattens near the close
    assert eng.state("NFLX") is BotState.MANAGING


def test_tick_post_close_grace_escalates_feed_dead_carry(cfg):
    # The exact silent-carry gap: feed dead through the close AND the close itself
    # fails. The post-close grace sweep must still attempt the close and page
    # naked-overnight (vs. carrying with no alert as on 2026-06-19).
    alerts: list[str] = []
    closer = _FailingCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer, on_feed_alert=alerts.append),
        trigger_engine=_FakeEngine([]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_POST_CLOSE_TS)
    assert closer.attempts == ["NFLX"]  # attempted the close past the bell
    assert eng.state("NFLX") is BotState.MANAGING  # failed -> stays held
    assert len(alerts) == 1 and "NAKED" in alerts[0] and "NFLX" in alerts[0]


def test_tick_after_candle_flatten_is_idempotent(cfg):
    # Candle thread and watchdog thread both reach the flatten in the close window;
    # a successful candle-driven close must not be re-closed by the next tick.
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([_rising_trigger()]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.on_short_candle(_candle(ts=_CLOSE_WINDOW_TS))  # candle path closes it
    assert closer.closed == ["NFLX"]
    eng.tick(_CLOSE_WINDOW_TS)  # watchdog tick must be a no-op now
    assert closer.closed == ["NFLX"]  # still exactly one close
    assert eng.state("NFLX") is BotState.WAITING


def _confidence(total: float) -> ConfidenceBreakdown:
    return ConfidenceBreakdown(
        crossover=0.5, trend=0.5, rsi=0.5, volume=0.5, volatility=0.5, total=total
    )


def test_near_miss_skip_logs_at_info(cfg, caplog):
    # A scored candidate that fell short of the threshold logs at INFO with its
    # confidence, so "why no buy today" is answerable from the logs.
    eng = StrategyEngine(cfg)
    decision = EntryDecision(
        symbol="NFLX",
        candle_start=_OPEN_TS,
        gate_open=True,
        fresh_cross=True,
        candidate=True,
        confidence=_confidence(55.0),
        enter=False,
        reason="confidence 55.0 < 60",
    )
    with caplog.at_level(logging.INFO, logger="ustradebot.strategy"):
        eng._log_skip("NFLX", decision)
    hits = [r for r in caplog.records if "no entry NFLX" in r.message]
    assert len(hits) == 1
    assert hits[0].levelno == logging.INFO
    assert "55.0" in hits[0].message


def test_non_candidate_skip_logs_at_debug_not_info(cfg, caplog):
    # The common gate-closed rejection (no scored candidate) stays at DEBUG so a
    # ~10k-candle session doesn't flood INFO.
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([]),  # gate never opens -> not a candidate
    )
    with caplog.at_level(logging.DEBUG, logger="ustradebot.strategy"):
        eng.on_short_candle(_candle())
    skips = [r for r in caplog.records if "no entry NFLX" in r.message]
    assert len(skips) == 1
    assert skips[0].levelno == logging.DEBUG
    assert "gate closed" in skips[0].message


# --- wall-clock EOD-flatten watchdog (tick) --------------------------------
#
# 2026-06-19 regression: the IEX feed went silent through the close window (zero
# candles 15:44–16:02 ET), so the candle-driven flatten never ran and 5 names
# carried NAKED over the weekend with no Telegram page. The watchdog drives the
# flatten on wall-clock time, independent of candle delivery.

# A Tuesday, 20:02 UTC == 16:02 EDT -> 2 min PAST the 20:00 UTC close, inside the
# _POSTCLOSE_GRACE_MIN=3 grace sweep (and past the escalation runway).
_POST_CLOSE_TS = datetime(2026, 6, 2, 20, 2, tzinfo=UTC)


def test_tick_flattens_on_wall_clock_without_any_candle(cfg):
    # The core fix: a MANAGING position is flattened by the watchdog even though no
    # candle is ever delivered (the trigger engine has none queued).
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([]),  # no candle ever arrives
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_CLOSE_WINDOW_TS)  # 19:56 UTC, inside the close window
    assert closer.closed == ["NFLX"]
    assert eng.state("NFLX") is BotState.WAITING
    assert "NFLX" not in eng._positions


def test_tick_outside_close_window_is_noop(cfg):
    # Mid-session ticks must not touch open positions — the watchdog only flattens.
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg, risk=RiskManager(cfg, executor=closer), trigger_engine=_FakeEngine([])
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_OPEN_TS)  # 14:00 UTC, well before the close window
    assert closer.closed == []
    assert eng.state("NFLX") is BotState.MANAGING


def test_tick_post_close_grace_escalates_feed_dead_carry(cfg):
    # Feed dead through the close AND the close itself fails: the post-close grace
    # sweep must still attempt the close and page naked-overnight — exactly the gap
    # that carried silently on 2026-06-19.
    alerts: list[str] = []
    closer = _FailingCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer, on_feed_alert=alerts.append),
        trigger_engine=_FakeEngine([]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_POST_CLOSE_TS)  # 2 min after the close, inside the grace sweep
    assert closer.attempts == ["NFLX"]  # tried to close
    assert eng.state("NFLX") is BotState.MANAGING  # failed -> still held
    assert len(alerts) == 1 and "NAKED" in alerts[0] and "NFLX" in alerts[0]


def test_tick_after_candle_flatten_is_idempotent(cfg):
    # Candle path and watchdog both fire in the same window: the second must be a
    # no-op (the position is already WAITING), never a double-close.
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([_rising_trigger()]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.on_short_candle(_candle(ts=_CLOSE_WINDOW_TS))  # candle path closes it
    assert closer.closed == ["NFLX"]
    eng.tick(_CLOSE_WINDOW_TS)  # watchdog must not re-close
    assert closer.closed == ["NFLX"]
    assert eng.state("NFLX") is BotState.WAITING


# --- wall-clock MANAGING reconcile (IMP-014) -------------------------------
#
# 2026-07-10 regression: SE's broker-side stop filled @14:33 UTC on a DOWN move, so the
# trailing ratchet (which only replaces the stop on a higher high) never attempted a move
# and never surfaced the fill as StopOrderGone. SE sat MANAGING, un-re-enterable, until the
# 19:45 EOD flatten reconciled it — its exit mistimed ~5h and mislabelled "end-of-day
# flatten". The wall-clock watchdog must detect the gone position mid-session and release it.


def test_tick_reconciles_broker_side_stop_fill_outside_close_window(cfg):
    exits: list = []
    closer = _StopGoneCloser(fill=("stop-se", 113.21))  # broker-side stop fill in order history
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer, on_exit=exits.append),
        trigger_engine=_FakeEngine([]),  # no candle needed — the watchdog drives this
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_OPEN_TS)  # mid-session, well OUTSIDE the close window
    assert closer.closed == []  # read-only reconcile: never submitted a close
    assert closer.reconciled == ["NFLX"]  # detected the broker-side fill from order history
    assert len(exits) == 1
    assert exits[0].exit_price == 113.21  # recorded at the real broker fill
    assert "stop/target filled broker-side" in exits[0].reason
    assert eng.state("NFLX") is BotState.WAITING  # freed, not stuck MANAGING for hours
    assert "NFLX" not in eng._positions
    # A second tick is a no-op — the symbol is already released (not MANAGING).
    eng.tick(_OPEN_TS)
    assert closer.reconciled == ["NFLX"]
    assert len(exits) == 1


def test_tick_reconcile_leaves_open_position_managing(cfg):
    # A MANAGING position still held at the broker (reconcile_exit → None) must be left
    # untouched by the sweep: no exit recorded, no close submitted, still MANAGING.
    exits: list = []
    closer = _FakeCloser()  # reconcile_exit returns None → still open
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer, on_exit=exits.append),
        trigger_engine=_FakeEngine([]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()
    eng.tick(_OPEN_TS)
    assert closer.closed == []
    assert exits == []
    assert eng.state("NFLX") is BotState.MANAGING
    assert "NFLX" in eng._positions


# --- rejected-entry logging ------------------------------------------------


def _breakdown(total: float) -> ConfidenceBreakdown:
    return ConfidenceBreakdown(
        crossover=0.5, trend=0.5, rsi=0.5, volume=0.5, volatility=0.5, total=total
    )


def test_near_miss_entry_logs_at_info(cfg, caplog):
    # A scored candidate that fell short of the threshold logs at INFO with its
    # confidence, so a flat session is diagnosable from the logs.
    eng = StrategyEngine(cfg)
    decision = EntryDecision(
        symbol="NFLX",
        candle_start=_OPEN_TS,
        gate_open=True,
        fresh_cross=True,
        candidate=True,
        confidence=_breakdown(55.0),
        enter=False,
        reason="confidence 55.0 < 60",
    )
    with caplog.at_level(logging.INFO, logger="ustradebot.strategy"):
        eng._log_skip("NFLX", decision)
    rec = [r for r in caplog.records if "no entry NFLX" in r.message]
    assert len(rec) == 1
    assert rec[0].levelno == logging.INFO
    assert "55.0" in rec[0].message


def test_non_candidate_skip_logs_at_debug(cfg, caplog):
    # The common gate-closed / no-fresh-cross rejection logs at DEBUG to keep the
    # ~10k-candle session readable; nothing is emitted at INFO.
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([]),  # no gate snapshot -> candidate fails ("gate closed")
    )
    with caplog.at_level(logging.DEBUG, logger="ustradebot.strategy"):
        eng.on_short_candle(_candle())
    skip = [r for r in caplog.records if "no entry NFLX" in r.message]
    assert len(skip) == 1
    assert skip[0].levelno == logging.DEBUG
    assert not [r for r in skip if r.levelno >= logging.INFO]
