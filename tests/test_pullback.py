"""Tests for the pullback entry trigger (IMP-057).

Two layers:

* the pure state machine in ``bot.pullback`` — arm, advance, disarm, expire;
* its wiring into ``StrategyEngine``, where the safety-critical properties live:
  ``cross`` mode must be untouched, an arm must never outlive its session, and the
  market gate must be re-checked at the fill rather than only at the arm.

The gate-closes-while-armed case is the **2026-09-28 regression test**. On that session
the QQQ 5-min market gate was shut for all 79 five-minute bars of regular trading (a
risk-off tape: S&P −0.77%, Nasdaq −0.92%, VIX +8.5%, 10-yr above 5.2%), and the bot
correctly took nothing. A trigger that arms on one bar and fills on a later one opens a
brand-new way to enter a regime the gate has since closed, so that path is pinned here.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bot.candles import Candle
from bot.config import CROSS, PULLBACK, Config, ConfigError
from bot.indicators import RibbonSnapshot
from bot.pullback import DISARM, ENTER, WAIT, ArmedCross, advance, arm
from bot.signals import ConfidenceBreakdown
from bot.strategy import BotState, StrategyEngine

# A Tuesday, 14:00 UTC == 10:00 EDT -> inside the session, past the IMP-017 blackout.
_OPEN_TS = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)
# A Tuesday, 19:56 UTC == 15:56 EDT -> inside the end-of-day flatten window.
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


@pytest.fixture
def pullback_cfg(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ENTRY_MODE", "pullback")
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
        symbol=symbol, start=ts, open=close, high=close, low=close,
        close=close, volume=100.0, trades=1,
    )


def _ribbon_snap(ribbon, prev_ribbon, *, ts=_OPEN_TS, close=100.0, symbol="NFLX", **extra):
    fields = dict(
        rsi=None, prev_rsi=None, avg_volume=None, atr=None, volume=100.0, interval_seconds=60
    )
    fields.update(extra)
    return RibbonSnapshot(
        symbol=symbol, candle_start=ts, close=close,
        ribbon=ribbon, prev_ribbon=prev_ribbon, **fields,
    )


def _open_gate(symbol="NFLX") -> RibbonSnapshot:
    return _ribbon_snap(
        (102.0, 101.0, 100.0), (101.0, 100.5, 100.0),
        symbol=symbol, interval_seconds=300,
    )


def _shut_gate(symbol="QQQ") -> RibbonSnapshot:
    """Not stacked — ``gate_open`` is False, the IMP-022 market veto."""
    return _ribbon_snap(
        (100.0, 101.0, 102.0), (100.0, 101.0, 102.0),
        symbol=symbol, interval_seconds=300,
    )


def _fresh_strong_trigger(*, ts=_OPEN_TS, close=100.0) -> RibbonSnapshot:
    """A qualifying fresh bullish cross, confidence comfortably over the bar."""
    return _ribbon_snap(
        (101.0, 100.4, 100.0), (99.9, 100.4, 100.0),
        ts=ts, close=close, rsi=55.0, prev_rsi=50.0,
        volume=200.0, avg_volume=100.0, atr=0.35,
    )


def _stacked_above_mid(*, ts=_OPEN_TS, close=103.0) -> RibbonSnapshot:
    """Stack intact, price still above the mid EMA -> keep waiting."""
    return _ribbon_snap(
        (101.0, 100.4, 100.0), (100.8, 100.3, 99.9), ts=ts, close=close, atr=0.35
    )


def _stacked_at_mid(*, ts=_OPEN_TS, close=100.4) -> RibbonSnapshot:
    """Stack intact, price back down to the mid EMA -> the pullback fill."""
    return _ribbon_snap(
        (101.0, 100.4, 100.0), (100.8, 100.3, 99.9), ts=ts, close=close, atr=0.35
    )


def _broken_stack(*, ts=_OPEN_TS, close=99.0) -> RibbonSnapshot:
    """fast has fallen back below mid -> the setup is dead."""
    return _ribbon_snap(
        (100.0, 100.4, 100.0), (100.8, 100.3, 99.9), ts=ts, close=close, atr=0.35
    )


def _conf(total=72.0) -> ConfidenceBreakdown:
    return ConfidenceBreakdown(
        crossover=0.5, trend=1.0, rsi=1.0, volume=0.5, volatility=0.6, total=total
    )


def _armed(bars_waited=0) -> ArmedCross:
    return ArmedCross(
        symbol="NFLX", armed_at=_OPEN_TS, armed_close=100.0,
        confidence=_conf(), bars_waited=bars_waited,
    )


# --- the pure state machine ------------------------------------------------


def test_arm_records_the_cross_bar():
    a = arm("NFLX", _fresh_strong_trigger(), _conf(71.5))
    assert a.symbol == "NFLX"
    assert a.armed_at == _OPEN_TS
    assert a.armed_close == 100.0
    assert a.confidence.total == 71.5
    assert a.bars_waited == 0


def test_advance_waits_while_price_stays_above_the_mid():
    d = advance(_armed(), _stacked_above_mid(), max_bars=10)
    assert d.outcome == WAIT
    assert not d.enter
    assert d.armed is not None and d.armed.bars_waited == 1


def test_advance_enters_on_the_retracement_into_the_ribbon():
    d = advance(_armed(bars_waited=2), _stacked_at_mid(), max_bars=10)
    assert d.outcome == ENTER
    assert d.enter
    assert "pullback into ribbon" in d.reason


def test_advance_enters_when_price_closes_below_the_mid():
    d = advance(_armed(), _stacked_at_mid(close=100.1), max_bars=10)
    assert d.enter


def test_advance_disarms_when_the_stack_breaks():
    d = advance(_armed(), _broken_stack(), max_bars=10)
    assert d.outcome == DISARM
    assert d.disarmed
    assert d.armed is None
    assert "stack broke" in d.reason


def test_structure_is_checked_before_price():
    """A retracement into a *broken* ribbon is a breakdown, not an entry."""
    breaking_down = _ribbon_snap(
        (100.0, 100.4, 100.0), (100.8, 100.3, 99.9), close=99.0, atr=0.35
    )
    d = advance(_armed(), breaking_down, max_bars=10)
    assert d.disarmed and not d.enter


def test_advance_disarms_on_expiry():
    d = advance(_armed(bars_waited=9), _stacked_above_mid(), max_bars=10)
    assert d.outcome == DISARM
    assert "no pullback within 10 bars" in d.reason


def test_expiry_does_not_pre_empt_an_eligible_fill():
    """The last bar of the window can still fill — expiry is checked after price."""
    d = advance(_armed(bars_waited=9), _stacked_at_mid(), max_bars=10)
    assert d.enter


def test_advance_disarms_on_an_unready_ribbon():
    unready = _ribbon_snap((None, None, None), (None, None, None))
    assert advance(_armed(), unready, max_bars=10).disarmed


def test_bars_waited_accumulates_across_calls():
    a = _armed()
    for expected in (1, 2, 3):
        d = advance(a, _stacked_above_mid(), max_bars=10)
        assert d.armed is not None and d.armed.bars_waited == expected
        a = d.armed


# --- config ----------------------------------------------------------------


def test_entry_mode_defaults_to_cross(cfg):
    assert cfg.entry_mode == CROSS
    assert cfg.pullback_max_bars == 10


def test_entry_mode_pullback_loads(pullback_cfg):
    assert pullback_cfg.entry_mode == PULLBACK


def test_unknown_entry_mode_is_rejected(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ENTRY_MODE", "moonphase")
    with pytest.raises(ConfigError, match="ENTRY_MODE"):
        Config.load(dotenv=False)


def test_zero_pullback_max_bars_is_rejected(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("PULLBACK_MAX_BARS", "0")
    with pytest.raises(ConfigError, match="PULLBACK_MAX_BARS"):
        Config.load(dotenv=False)


# --- wiring into the strategy engine ---------------------------------------


def _engine(cfg, trigger_snaps, gate_snaps=None, **kw):
    return StrategyEngine(
        cfg,
        trigger_engine=_FakeEngine(trigger_snaps),
        gate_engine=_FakeEngine(gate_snaps if gate_snaps is not None else [_open_gate()]),
        **kw,
    )


def test_cross_mode_still_fills_on_the_cross_bar(cfg):
    """The control: default mode is unchanged by IMP-057."""
    seen = []
    eng = _engine(cfg, [_fresh_strong_trigger()], on_signal=seen.append)
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle())
    assert sig is not None
    assert len(seen) == 1
    assert eng._armed == {}  # cross mode never arms


def test_pullback_mode_arms_instead_of_filling(pullback_cfg):
    seen = []
    eng = _engine(pullback_cfg, [_fresh_strong_trigger()], on_signal=seen.append)
    eng.on_long_candle(_candle())
    sig = eng.on_short_candle(_candle())
    assert sig is None  # no fill on the cross bar
    assert seen == []
    assert "NFLX" in eng._armed
    assert eng._armed["NFLX"].armed_close == 100.0
    assert eng.state("NFLX") is BotState.WAITING


def test_pullback_mode_fills_on_the_retracement(pullback_cfg):
    seen = []
    eng = _engine(
        pullback_cfg,
        [_fresh_strong_trigger(), _stacked_at_mid(close=99.5)],
        on_signal=seen.append,
    )
    eng.on_long_candle(_candle())
    assert eng.on_short_candle(_candle()) is None  # arms
    sig = eng.on_short_candle(_candle(close=99.5))  # retraces -> fills
    assert sig is not None
    assert sig.close == 99.5  # filled at the *lower* retracement price
    assert len(seen) == 1
    assert eng._armed == {}


def test_pullback_fill_carries_the_cross_bar_confidence(pullback_cfg):
    """Sizing must see the score that qualified the setup, not a non-cross rescore."""
    eng = _engine(pullback_cfg, [_fresh_strong_trigger(), _stacked_at_mid(close=99.5)])
    eng.on_long_candle(_candle())
    eng.on_short_candle(_candle())
    armed_conf = eng._armed["NFLX"].confidence.total
    sig = eng.on_short_candle(_candle(close=99.5))
    assert sig is not None
    assert sig.confidence.total == armed_conf
    assert sig.decision.fresh_cross is False  # honest: the fill bar is not a cross


def test_pullback_arm_disarms_when_the_stack_breaks(pullback_cfg):
    eng = _engine(pullback_cfg, [_fresh_strong_trigger(), _broken_stack()])
    eng.on_long_candle(_candle())
    eng.on_short_candle(_candle())
    assert eng.on_short_candle(_candle(close=99.0)) is None
    assert eng._armed == {}


def test_gate_closing_while_armed_blocks_the_fill(pullback_cfg):
    """2026-09-28 regression: the QQQ gate was shut all session.

    An arm placed while the tape was acceptable must not fill once the market gate has
    closed — otherwise the pullback trigger becomes a back door into exactly the regime
    the gate exists to refuse.
    """
    eng = StrategyEngine(
        pullback_cfg,
        trigger_engine=_FakeEngine([_fresh_strong_trigger(), _stacked_at_mid(close=99.5)]),
        gate_engine=_FakeEngine([_open_gate("NFLX"), _shut_gate("QQQ")]),
    )
    eng.on_long_candle(_candle())  # NFLX's own gate ribbon: open
    eng.on_short_candle(_candle())  # arms (QQQ has no snapshot yet -> fails open)
    assert "NFLX" in eng._armed

    eng.on_long_candle(_candle(symbol="QQQ"))  # the market gate closes
    sig = eng.on_short_candle(_candle(close=99.5))  # retracement arrives anyway
    assert sig is None, "an armed cross must not fill into a closed market gate"
    assert eng._armed == {}


def test_eod_flatten_clears_pending_arms(pullback_cfg):
    eng = _engine(pullback_cfg, [_fresh_strong_trigger()])
    eng.on_long_candle(_candle())
    eng.on_short_candle(_candle())
    assert "NFLX" in eng._armed
    eng._flatten_all_eod(_CLOSE_WINDOW_TS)
    assert eng._armed == {}, "an arm must not outlive the session that created it"


def test_stale_arm_from_a_prior_session_is_disarmed(pullback_cfg):
    """If the flatten never ran (dead feed), the date guard still kills the arm."""
    next_day = datetime(2026, 6, 3, 14, 0, tzinfo=UTC)
    eng = _engine(
        pullback_cfg,
        [_fresh_strong_trigger(), _stacked_at_mid(ts=next_day, close=99.5)],
    )
    eng.on_long_candle(_candle())
    eng.on_short_candle(_candle())
    assert "NFLX" in eng._armed
    sig = eng.on_short_candle(_candle(ts=next_day, close=99.5))
    assert sig is None, "yesterday's cross must not justify today's fill"
    assert eng._armed == {}


def test_pullback_respects_the_expiry_window(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ENTRY_MODE", "pullback")
    monkeypatch.setenv("PULLBACK_MAX_BARS", "2")
    eng = _engine(
        Config.load(dotenv=False),
        [_fresh_strong_trigger(), _stacked_above_mid(), _stacked_above_mid()],
    )
    eng.on_long_candle(_candle())
    eng.on_short_candle(_candle())
    eng.on_short_candle(_candle(close=103.0))  # 1 bar waited
    assert "NFLX" in eng._armed
    eng.on_short_candle(_candle(close=103.0))  # 2 bars -> expires
    assert eng._armed == {}
