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
from bot.signals import ConfidenceBreakdown, EntryDecision, evaluate_entry
from bot.strategy import BotState, StrategyEngine, atr_pct_of, ribbon_spread_pct_of

# A Tuesday, 14:00 UTC == 10:00 EDT -> inside the regular session.
_OPEN_TS = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)
# A Saturday -> market closed.
_WEEKEND_TS = datetime(2026, 6, 6, 14, 0, tzinfo=UTC)
# A Tuesday, 19:56 UTC == 15:56 EDT -> inside the 5-min end-of-day flatten window.
_CLOSE_WINDOW_TS = datetime(2026, 6, 2, 19, 56, tzinfo=UTC)
# A Tuesday, 13:35 UTC == 09:35 EDT -> inside the IMP-017 opening-range blackout.
_BLACKOUT_TS = datetime(2026, 6, 2, 13, 35, tzinfo=UTC)

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
        atr=0.35,  # 0.35% of close — a live tape, full marks after IMP-036
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


def test_no_entry_during_the_opening_blackout(cfg):
    """IMP-017: a textbook trigger before 10:00 ET opens nothing. Over 219 live trades
    the pre-10:00 bucket lost $407 (41 trades, 36.6% win) and produced 48% of all
    stop-out damage from 19% of the trades — opening crosses are gap artifacts."""
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle(ts=_BLACKOUT_TS))
    sig = eng.on_short_candle(_candle(ts=_BLACKOUT_TS))
    assert sig is None
    assert eng.state("NFLX") is BotState.WAITING


def test_entry_allowed_from_the_cutoff_minute(cfg):
    """The same setup at 10:00 ET is tradeable — a blackout, not a filter that
    suppresses the signal for the rest of the session."""
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())  # _OPEN_TS == 10:00 EDT, the cutoff minute
    sig = eng.on_short_candle(_candle())
    assert sig is not None
    assert eng.state("NFLX") is BotState.EVALUATING


def test_blackout_disabled_by_setting_entry_start_to_the_open(monkeypatch):
    """Escape hatch: ENTRY_START=09:30 restores pre-IMP-017 behaviour."""
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ENTRY_START", "09:30")
    cfg = Config.load(dotenv=False)
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle(ts=_BLACKOUT_TS))
    assert eng.on_short_candle(_candle(ts=_BLACKOUT_TS)) is not None


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

    def reconcile_exit(self, symbol, *, after=None):
        return None  # close succeeds here, so reconcile is never consulted

    def entry_filled_at(self, order_id):
        return None  # no fill time scripted → IMP-027 recency guard stands down

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
    # 110 * (1 - 0.010) = 108.90 > 98 -> stop moves up, position stays open (no close)
    assert closer.moved == [("stop-1", 108.9)]
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


def test_open_positions_are_still_managed_during_the_blackout(cfg):
    """IMP-017 safety property: the blackout gates ENTRIES ONLY. A position carried
    into the opening range must keep trailing its stop — gating the MANAGING path
    would leave it unmanaged exactly when it is most likely to gap."""
    closer = _FakeCloser()
    eng = StrategyEngine(
        cfg,
        risk=RiskManager(cfg, executor=closer),
        trigger_engine=_FakeEngine([_rising_trigger(110.0)]),
    )
    eng._state["NFLX"] = BotState.MANAGING
    eng._positions["NFLX"] = _exec_result()  # entry 100, stop 98, leg "stop-1"
    eng.on_short_candle(_candle(ts=_BLACKOUT_TS))
    assert closer.moved == [("stop-1", 108.9)]  # trailed, blackout notwithstanding
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

    def reconcile_exit(self, symbol, *, after=None):
        self.reconciled.append(symbol)
        return self._fill

    def entry_filled_at(self, order_id):
        return None  # no fill time scripted → IMP-027 recency guard stands down

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
    assert closer.moved == [("stop-1", 108.9)]    # the ratchet was attempted, reported gone
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

    def reconcile_exit(self, symbol, *, after=None):
        return None  # genuine outage, not an already-flat position — escalation must fire

    def entry_filled_at(self, order_id):
        return None  # no fill time scripted → IMP-027 recency guard stands down

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


# --- IMP-022: market-regime gate -------------------------------------------------
#
# The per-symbol 5-min gate only asks whether that one name is trending; it says
# nothing about the tape the name has to swim in. Bucketing the 38 live sessions
# 2026-06-08..08-05 by QQQ's intraday move: QQQ up >0.5% = 104 trades, 54.8% win,
# +$755.65; QQQ down = 118 trades, 33.1% win, -$728.75. These cover the veto that
# turns the adverse half away, and the fail-open behaviour that keeps a watchlist
# edit from silently halting the bot.


def _market_gate_engine(open_gate: bool) -> _FakeEngine:
    """Gate engine yielding the index snapshot first, then the traded symbol's."""
    index = _open_gate() if open_gate else _shut_gate()
    return _FakeEngine([index, _open_gate()])


def _shut_gate() -> RibbonSnapshot:
    """Ribbon ready but rolling over — stacked False, sloping_up False."""
    return _ribbon_snap((100.0, 101.0, 102.0), (100.5, 101.5, 102.5), interval_seconds=300)


def _feed_index_then_symbol(eng, *, index_symbol="QQQ"):
    eng.on_long_candle(_candle(symbol=index_symbol))  # index 5m ribbon
    eng.on_long_candle(_candle())  # traded symbol's own 5m gate


def test_market_gate_blocks_a_qualifying_entry_when_the_tape_is_not_bullish(cfg, caplog):
    ex = _FakeExecutor(_exec_result())
    eng = StrategyEngine(
        cfg,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_market_gate_engine(open_gate=False),
    )
    _feed_index_then_symbol(eng)
    with caplog.at_level(logging.INFO, logger="ustradebot.strategy"):
        sig = eng.on_short_candle(_candle())
    assert sig is None  # scored and qualified, then vetoed
    assert ex.calls == []  # nothing reached the broker
    assert eng.state("NFLX") is BotState.WAITING
    assert any("market gate closed (QQQ" in r.getMessage() for r in caplog.records)


def test_market_gate_allows_the_same_entry_when_the_tape_is_bullish(cfg):
    """The mirror of the veto: a gate, not a filter that suppresses entries outright."""
    ex = _FakeExecutor(_exec_result())
    eng = StrategyEngine(
        cfg,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_market_gate_engine(open_gate=True),
    )
    _feed_index_then_symbol(eng)
    sig = eng.on_short_candle(_candle())
    assert sig is not None
    assert len(ex.calls) == 1
    assert eng.state("NFLX") is BotState.MANAGING


def test_market_gate_fails_open_when_the_index_has_no_ribbon(cfg, caplog):
    """QQQ off the watchlist must not silently halt trading — trade on, but warn."""
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())  # only the traded symbol; no QQQ ribbon ever
    with caplog.at_level(logging.WARNING, logger="ustradebot.strategy"):
        sig = eng.on_short_candle(_candle())
    assert sig is not None  # fails OPEN
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warns) == 1 and "failing OPEN" in warns[0].getMessage()


def test_market_gate_missing_ribbon_warns_only_once(cfg, caplog):
    """Latched: a missing index ribbon must not spam a warning every candle."""
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger(), _fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    with caplog.at_level(logging.WARNING, logger="ustradebot.strategy"):
        eng.on_short_candle(_candle())
        eng.on_short_candle(_candle())
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_market_gate_disabled_by_empty_symbol(monkeypatch):
    """MARKET_FILTER_SYMBOL='' restores pre-IMP-022 behaviour exactly."""
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("MARKET_FILTER_SYMBOL", "")
    cfg_off = Config.load(dotenv=False)
    eng = StrategyEngine(
        cfg_off,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_market_gate_engine(open_gate=False),
    )
    _feed_index_then_symbol(eng)
    assert eng.on_short_candle(_candle()) is not None  # shut tape, entry still taken


def test_mu_2026_08_05_second_entry_is_vetoed_by_the_real_qqq_ribbon(cfg, caplog):
    """Regression from the live 2026-08-05 session.

    MU's second entry fired at 16:40 UTC (conf 62.11) and lost $10.39. QQQ's 5-min
    gate ribbon on that exact bar was (721.9659, 722.4467, 722.4473) over a prior
    (721.9934, 722.4925, 722.4754) -- not stacked, not rising, i.e. the tape was
    rolling over while the bot opened a long. Real values, pulled from the IEX 5m
    bar. This asserts the gate turns that entry away.
    """
    ts = datetime(2026, 8, 5, 16, 40, tzinfo=UTC)
    qqq = _ribbon_snap(
        (721.9659, 722.4467, 722.4473),
        (721.9934, 722.4925, 722.4754),
        ts=ts,
        close=721.69,
        interval_seconds=300,
    )
    assert not qqq.gate_open  # the tape really was shut on that bar

    ex = _FakeExecutor(_exec_result(symbol="MU"))
    eng = StrategyEngine(
        cfg,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([qqq, _open_gate()]),
    )
    eng.on_long_candle(_candle(ts=ts, symbol="QQQ"))
    eng.on_long_candle(_candle(ts=ts))
    with caplog.at_level(logging.INFO, logger="ustradebot.strategy"):
        sig = eng.on_short_candle(_candle(ts=ts))
    assert sig is None
    assert ex.calls == []
    assert any("market gate closed (QQQ" in r.getMessage() for r in caplog.records)


# --- IMP-029: pre-entry tape context on the signal --------------------------


def test_atr_pct_is_price_relative_so_symbols_are_comparable():
    """The 2026-08-17 pair: INTC at $105 and MU at $1,034 must be on one scale.

    Both entries died in the <0.5%-MFE cohort that day. Their raw ATRs differ by an
    order of magnitude purely because of share price; as a percentage they are 0.204%
    and 0.158% — close, and comparable, which is the whole point of recording it so.
    """
    intc = _ribbon_snap((1.0, 0.9, 0.8), (0.9, 0.9, 0.8), close=105.39, atr=0.215)
    mu = _ribbon_snap((1.0, 0.9, 0.8), (0.9, 0.9, 0.8), close=1034.13, atr=1.634)

    assert atr_pct_of(intc) == pytest.approx(0.204, abs=0.001)
    assert atr_pct_of(mu) == pytest.approx(0.158, abs=0.001)


def test_tape_context_is_none_when_the_indicator_has_not_seeded():
    """Unmeasured must not read back as 0.0 — a flat tape is a different fact."""
    unseeded = _ribbon_snap((None, None, None), (None, None, None), close=100.0, atr=None)
    assert atr_pct_of(unseeded) is None
    assert ribbon_spread_pct_of(unseeded) is None


def test_ribbon_spread_pct_measures_fast_to_slow_separation():
    snap = _ribbon_snap((101.0, 100.4, 100.0), (99.9, 100.4, 100.0), close=100.0, atr=0.5)
    assert ribbon_spread_pct_of(snap) == pytest.approx(1.0)  # (101 - 100) / 100 * 100


def test_entry_signal_carries_the_tape_context(cfg):
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle())

    assert sig is not None
    assert sig.atr_pct == pytest.approx(0.35)  # _fresh_strong_trigger: atr 0.35 @ close 100
    assert sig.ribbon_spread_pct == pytest.approx(1.0)


def test_recording_the_tape_does_not_change_the_entry_decision(cfg):
    """IMP-029 is observational — it records values the scorer already consumed.

    ATR is *not* new to the decision: it has always fed ``conf_volatility``. So the
    invariant is not "the decision is the same without ATR" (it isn't, and never was)
    but that the decision for a snapshot is exactly the scorer's own, unperturbed by
    the two derived fields now hanging off the signal.
    """
    trigger = _fresh_strong_trigger()
    expected = evaluate_entry(
        trigger, _open_gate(), threshold=cfg.entry_threshold, min_crossover=cfg.min_crossover
    )

    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([trigger]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle())

    assert sig.decision.enter == expected.enter
    assert sig.confidence.total == expected.confidence.total
    assert sig.confidence.volatility == expected.confidence.volatility
    # ...and the derived fields are pure functions of that same snapshot.
    assert sig.atr_pct == atr_pct_of(trigger)
    assert sig.ribbon_spread_pct == ribbon_spread_pct_of(trigger)


# --- IMP-030: refusals are persisted, not just logged -------------------------------
# Motivated by 2026-08-18, a session that made 33 scored entry decisions and wrote ZERO
# rows to SQL: 16 confidence near-misses, 15 crossover near-misses and 2 fully-qualifying
# entries the market gate turned away (ABNB conf 79.8, NFLX conf 79.3). That evidence
# lived only in journald, which had 11 days of retention. These tests pin the two emit
# points, the volume guard that keeps the ~10k unscored rejections out, and the rule that
# an observational write can never break the candle thread.


class _FakeRefusalSink:
    def __init__(self, boom: bool = False):
        self.calls = []
        self._boom = boom

    def __call__(self, refusal):
        self.calls.append(refusal)
        if self._boom:
            raise RuntimeError("recorder is down")


def _near_miss_trigger() -> RibbonSnapshot:
    """A fresh cross that scores 66.4 but is refused on the crossover floor.

    Reproduces today's second-most-common refusal shape verbatim: the engine returns
    ``crossover 0.18 < 0.25``, the same form as the live ``crossover 0.21 < 0.25``
    (AAPL 14:30) and ``crossover 0.24 < 0.25`` (NFLX 15:20) on 2026-08-18.
    """
    return _ribbon_snap(
        (100.02, 100.01, 100.0),
        (99.99, 100.01, 100.0),
        close=100.0,
        rsi=50.5,
        prev_rsi=50.0,
        volume=90.0,
        avg_volume=100.0,
        atr=0.35,  # live tape, so the refusal under test is the crossover floor
    )


def test_scored_near_miss_is_persisted_with_its_breakdown(cfg):
    """Today's dominant refusal (confidence/crossover below the bar) becomes a row."""
    sink = _FakeRefusalSink()
    eng = StrategyEngine(
        cfg,
        on_refusal=sink,
        trigger_engine=_FakeEngine([_near_miss_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    assert eng.on_short_candle(_candle()) is None

    assert len(sink.calls) == 1
    r = sink.calls[0]
    assert r.symbol == "NFLX"
    assert r.candle_start == _OPEN_TS
    assert r.reason == "crossover 0.18 < 0.25"  # the live refusal shape, verbatim
    assert r.confidence is not None
    assert r.breakdown is not None  # the sub-scores travel with it, as for a taken entry
    # The whole point of the row: it cleared the confidence bar and was still refused,
    # so only the crossover floor can be priced against it.
    assert r.confidence >= cfg.entry_threshold
    assert r.breakdown.crossover < cfg.min_crossover
    assert r.close_price == 100.0
    # IMP-031 changed this field's meaning: it is now the gate state at this candle for
    # every scored candidate, not just for the ones the gate refused. No QQQ ribbon was
    # fed here, so the gate fails OPEN by design (a watchlist edit must never silently
    # halt trading) and the row honestly records True.
    assert r.market_gate_open is True
    assert "no fresh cross" not in r.reason


def test_market_gate_refusal_is_persisted_as_gate_closed(cfg):
    """The 2026-08-18 ABNB/NFLX case: fully qualified, vetoed by the index gate."""
    sink = _FakeRefusalSink()
    eng = StrategyEngine(
        cfg,
        on_refusal=sink,
        executor=_FakeExecutor(_exec_result()),
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_market_gate_engine(open_gate=False),
    )
    _feed_index_then_symbol(eng)
    assert eng.on_short_candle(_candle()) is None

    assert len(sink.calls) == 1
    r = sink.calls[0]
    assert r.market_gate_open is False  # the distinguishing fact for the gate study
    assert "market gate closed (QQQ" in r.reason
    # It qualified on its own merits — that is exactly what makes it worth recording.
    assert r.confidence >= cfg.entry_threshold
    assert r.breakdown is not None


# --- IMP-031: the gate state travels with EVERY scored refusal ----------------------
# Motivated by 2026-08-19: the crossover floor refused 17 candidates while the QQQ gate
# was independently observed shut at 14:13, 14:16, 15:47 and 16:15 — and the rows could
# not say which of the 17 fell inside those windows. Loosening a threshold does not admit
# a candidate, it only advances it to the gate, so pricing the floor without the gate
# state overstates what loosening it would recover.


def test_near_miss_records_a_shut_gate(cfg):
    """The discriminator: refused by the floor AND the tape was shut = unrecoverable."""
    sink = _FakeRefusalSink()
    eng = StrategyEngine(
        cfg,
        on_refusal=sink,
        trigger_engine=_FakeEngine([_near_miss_trigger()]),
        gate_engine=_market_gate_engine(open_gate=False),
    )
    _feed_index_then_symbol(eng)
    assert eng.on_short_candle(_candle()) is None

    r = sink.calls[0]
    assert r.market_gate_open is False
    # `reason` still attributes the refusal to the floor, not the gate — the two facts
    # are independent and the study needs to read them separately.
    assert r.reason == "crossover 0.18 < 0.25"
    assert "market gate" not in r.reason


def test_near_miss_records_an_open_gate(cfg):
    """The same candidate under a bullish tape: genuinely recoverable by the floor."""
    sink = _FakeRefusalSink()
    eng = StrategyEngine(
        cfg,
        on_refusal=sink,
        trigger_engine=_FakeEngine([_near_miss_trigger()]),
        gate_engine=_market_gate_engine(open_gate=True),
    )
    _feed_index_then_symbol(eng)
    assert eng.on_short_candle(_candle()) is None

    r = sink.calls[0]
    assert r.market_gate_open is True
    assert r.reason == "crossover 0.18 < 0.25"


def test_gate_state_on_a_near_miss_changes_no_decision(cfg):
    """Observational only: reading the gate for a near-miss must not alter behaviour.

    The near-miss is refused by the floor whether the tape is open or shut, reaches no
    broker either way, and lands in the same state. Only the recorded field differs.
    """
    outcomes = {}
    for open_gate in (True, False):
        sink = _FakeRefusalSink()
        ex = _FakeExecutor(_exec_result())
        eng = StrategyEngine(
            cfg,
            on_refusal=sink,
            executor=ex,
            trigger_engine=_FakeEngine([_near_miss_trigger()]),
            gate_engine=_market_gate_engine(open_gate=open_gate),
        )
        _feed_index_then_symbol(eng)
        sig = eng.on_short_candle(_candle())
        assert sig is None
        assert ex.calls == []  # nothing reached the broker on either tape
        outcomes[open_gate] = (eng.state("NFLX"), sink.calls[0].reason)

    assert outcomes[True] == outcomes[False]


def test_unscored_rejection_is_not_persisted(cfg):
    """Volume guard: ~10k 'no fresh cross' candles a session must not reach the table."""
    sink = _FakeRefusalSink()
    eng = StrategyEngine(cfg)
    decision = EntryDecision(
        symbol="NFLX",
        candle_start=_OPEN_TS,
        gate_open=False,
        fresh_cross=False,
        candidate=False,
        confidence=None,  # never scored
        enter=False,
        reason="gate closed",
    )
    eng._on_refusal = sink
    eng._log_skip("NFLX", decision)
    assert sink.calls == []


def test_a_taken_entry_records_no_refusal(cfg):
    """The populations must not overlap: a signal is not also a refusal."""
    sink = _FakeRefusalSink()
    eng = StrategyEngine(
        cfg,
        on_refusal=sink,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_market_gate_engine(open_gate=True),
    )
    _feed_index_then_symbol(eng)
    sig = eng.on_short_candle(_candle())
    assert sig is not None
    assert sink.calls == []


def test_refusal_carries_the_same_tape_context_as_an_entry(cfg):
    """IMP-029's tape fields on the refused side, so both populations are comparable."""
    sink = _FakeRefusalSink()
    trigger = _near_miss_trigger()
    eng = StrategyEngine(
        cfg,
        on_refusal=sink,
        trigger_engine=_FakeEngine([trigger]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    eng.on_short_candle(_candle())

    r = sink.calls[0]
    assert r.atr_pct == atr_pct_of(trigger)
    assert r.ribbon_spread_pct == ribbon_spread_pct_of(trigger)
    assert r.atr_pct is not None  # this trigger has seeded ATR, so it is a real value


def test_refusal_sink_failure_does_not_break_the_candle_thread(cfg, caplog):
    """An observational write is never allowed to kill a thread managing live positions."""
    sink = _FakeRefusalSink(boom=True)
    eng = StrategyEngine(
        cfg,
        on_refusal=sink,
        trigger_engine=_FakeEngine([_near_miss_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    with caplog.at_level(logging.ERROR, logger="ustradebot.strategy"):
        assert eng.on_short_candle(_candle()) is None  # swallowed, not raised
    assert any("on_refusal callback failed" in r.getMessage() for r in caplog.records)


def test_no_refusal_sink_is_harmless(cfg):
    """Persistence is optional everywhere else in this bot; refusals are no exception."""
    eng = StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine([_near_miss_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())
    assert eng.on_short_candle(_candle()) is None  # no sink wired -> no crash


# --- IMP-032: the market-gate duty-cycle sample -------------------------------------
# dbo.entry_refusals records the gate only where a candidate happened to be scored,
# which measures the gate where candidates land — not how often it is open. On
# 2026-08-20 the gate was shut for the entire entry window (0 of 69 bars) yet only
# 8 of 27 refusals were *labelled* a gate refusal; the other 19 died on the crossover
# floor or the confidence bar first. These tests pin the denominator that fixes that.


class _FakeGateSink:
    def __init__(self, boom: bool = False):
        self.calls = []
        self._boom = boom

    def __call__(self, sample):
        self.calls.append(sample)
        if self._boom:
            raise RuntimeError("recorder is down")


def _rolling_over_gate() -> RibbonSnapshot:
    """QQQ on 2026-08-20: still ordered 21>34>55, but the fast EMA has turned down.

    The case the two stored conjuncts exist to tell apart — ``gate_open`` is False
    because of *slope*, not because the ribbon lost its ordering.
    """
    return _ribbon_snap((102.0, 101.0, 100.0), (102.5, 100.5, 100.0), interval_seconds=300)


def test_gate_sample_recorded_for_the_filter_symbol(cfg):
    """One row per closed gate candle for MARKET_FILTER_SYMBOL, carrying the state."""
    sink = _FakeGateSink()
    eng = StrategyEngine(cfg, on_gate_sample=sink, gate_engine=_FakeEngine([_open_gate()]))

    eng.on_long_candle(_candle(symbol="QQQ", close=712.30))

    assert len(sink.calls) == 1
    s = sink.calls[0]
    assert s.symbol == "QQQ"
    assert s.candle_start == _OPEN_TS
    assert (s.gate_open, s.stacked, s.fast_rising) == (True, True, True)
    assert s.close_price == 712.30
    assert (s.ema_fast, s.ema_mid, s.ema_slow) == (102.0, 101.0, 100.0)


def test_gate_sample_attributes_a_shut_gate_to_slope_not_ordering(cfg):
    """Regression on 2026-08-20, when the gate was shut for all 69 entry-window bars.

    The duty-cycle table has to say *why* it was shut, or a 0% session is unreadable:
    a ribbon that lost its ordering and one that is merely rolling over are different
    tapes, and only the second is close to reopening.
    """
    sink = _FakeGateSink()
    eng = StrategyEngine(
        cfg, on_gate_sample=sink, gate_engine=_FakeEngine([_rolling_over_gate()])
    )

    eng.on_long_candle(_candle(symbol="QQQ"))

    s = sink.calls[0]
    assert s.gate_open is False
    assert s.stacked is True  # ordering intact...
    assert s.fast_rising is False  # ...the fast EMA turning down is what shut it


def test_gate_sample_only_for_the_filter_symbol(cfg):
    """A traded name's own 5m gate candle is not a market-gate observation.

    Every watchlist symbol runs the same gate ribbon; sampling all of them would put
    18 rows a bar in a table whose entire purpose is counting one series.
    """
    sink = _FakeGateSink()
    eng = StrategyEngine(
        cfg, on_gate_sample=sink, gate_engine=_FakeEngine([_open_gate(), _open_gate()])
    )

    eng.on_long_candle(_candle(symbol="NFLX"))
    assert sink.calls == []

    eng.on_long_candle(_candle(symbol="QQQ"))
    assert len(sink.calls) == 1


def test_gate_sample_skipped_while_the_ribbon_is_unseeded(cfg):
    """An unready ribbon fails the gate OPEN (_market_gate_open), so recording it
    would write a permissive row for a state the bot could not actually evaluate —
    inflating the duty cycle exactly where it is least trustworthy."""
    sink = _FakeGateSink()
    unseeded = _ribbon_snap((None, None, None), (None, None, None), interval_seconds=300)
    eng = StrategyEngine(cfg, on_gate_sample=sink, gate_engine=_FakeEngine([unseeded]))

    eng.on_long_candle(_candle(symbol="QQQ"))

    assert sink.calls == []


def test_gate_sampling_leaves_entry_behaviour_identical(cfg):
    """The change is observational: the same candles produce the same entry decision
    whether or not a sample sink is attached, and the sampled gate state agrees with
    the one the entry path read."""

    def run(sink):
        eng = StrategyEngine(
            cfg,
            on_gate_sample=sink,
            trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
            gate_engine=_market_gate_engine(open_gate=True),
        )
        _feed_index_then_symbol(eng)
        return eng, eng.on_short_candle(_candle())

    sink = _FakeGateSink()
    with_sink, sig_with = run(sink)
    without_sink, sig_without = run(None)

    assert (sig_with is None) == (sig_without is None) is False  # both entered
    assert sig_with.confidence.total == sig_without.confidence.total
    assert with_sink.state("NFLX") is without_sink.state("NFLX")
    assert sink.calls[0].gate_open is with_sink._market_gate_open()


def test_gate_sample_sink_failure_does_not_break_the_candle_thread(cfg, caplog):
    """An observational write is never allowed to kill a thread managing live positions."""
    sink = _FakeGateSink(boom=True)
    eng = StrategyEngine(cfg, on_gate_sample=sink, gate_engine=_FakeEngine([_open_gate()]))

    with caplog.at_level(logging.ERROR, logger="ustradebot.strategy"):
        eng.on_long_candle(_candle(symbol="QQQ"))  # swallowed, not raised

    assert any("on_gate_sample callback failed" in r.getMessage() for r in caplog.records)
    # ...and the gate snapshot is still stored, so entries are unaffected by the failure
    assert eng._market_gate_open() is True


def test_no_gate_sample_sink_is_harmless(cfg):
    """Persistence is optional everywhere else in this bot; gate samples are no exception."""
    eng = StrategyEngine(cfg, gate_engine=_FakeEngine([_open_gate()]))
    eng.on_long_candle(_candle(symbol="QQQ"))
    assert eng._market_gate_open() is True


def test_gate_sampling_disabled_when_the_market_filter_is_off(monkeypatch):
    """MARKET_FILTER_SYMBOL='' disables the gate entirely — there is nothing to sample."""
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("MARKET_FILTER_SYMBOL", "")
    cfg = Config.load(dotenv=False)
    sink = _FakeGateSink()
    eng = StrategyEngine(cfg, on_gate_sample=sink, gate_engine=_FakeEngine([_open_gate()]))

    eng.on_long_candle(_candle(symbol="QQQ"))

    assert sink.calls == []
