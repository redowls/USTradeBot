"""Tests for startup indicator warmup (bot/warmup.py + StrategyEngine.warmup_trigger).

The live bot builds its ribbons from the trade stream, so after every restart it
is blind until ~3.5h of candles accumulate (the 55-period 5m gate). Warmup pre-
seeds the ribbons from historical bars so the bot can trade from the open. The
critical invariant: warmup must NEVER place an order or emit a signal — it only
folds historical candles into the indicator state.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bot.candles import Candle
from bot.config import Config
from bot.indicators import RibbonSnapshot
from bot.strategy import BotState, StrategyEngine
from bot.warmup import warm_up

_ENV = {"ALPACA_KEY_ID": "k", "ALPACA_SECRET": "s", "TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}
_OPEN_TS = datetime(2026, 6, 22, 15, 0, tzinfo=UTC)  # a Monday inside RTH


@pytest.fixture
def cfg(monkeypatch):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    return Config.load(dotenv=False)


class _FakeEngine:
    def __init__(self, snaps):
        self._snaps = list(snaps)
        self.last = None

    def update(self, candle):
        self.last = self._snaps.pop(0)
        return self.last


class _FakeExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, *, symbol, entry_price, confidence):
        self.calls.append((symbol, entry_price, confidence))
        return None


def _candle(ts=_OPEN_TS, *, close=100.0, symbol="NFLX") -> Candle:
    return Candle(symbol=symbol, start=ts, open=close, high=close, low=close,
                  close=close, volume=100.0, trades=1)


def _ribbon_snap(ribbon, prev_ribbon, **extra) -> RibbonSnapshot:
    fields = dict(rsi=55.0, prev_rsi=50.0, avg_volume=100.0, atr=0.1, volume=200.0,
                  interval_seconds=60, symbol="NFLX", candle_start=_OPEN_TS, close=100.0)
    fields.update(extra)
    return RibbonSnapshot(ribbon=ribbon, prev_ribbon=prev_ribbon, **fields)


def _open_gate() -> RibbonSnapshot:
    return _ribbon_snap((102.0, 101.0, 100.0), (101.0, 100.5, 100.0), interval_seconds=300)


def _fresh_strong_trigger() -> RibbonSnapshot:
    return _ribbon_snap((101.0, 100.4, 100.0), (99.9, 100.4, 100.0))


def _rising_series(symbol, n, *, interval_s, t0=datetime(2026, 6, 22, 9, 0, tzinfo=UTC)):
    """A steadily-rising OHLCV series — enough bars warms a ribbon to ready+stacked."""
    return [
        Candle(symbol=symbol, start=t0 + timedelta(seconds=interval_s * i),
               open=100.0 + i, high=100.5 + i, low=99.5 + i, close=100.0 + i,
               volume=100.0, trades=5)
        for i in range(n)
    ]


def test_warmup_trigger_never_trades_even_when_aligned(cfg):
    """warmup_trigger folds a candle into the trigger ribbon but must not evaluate,
    execute, emit a signal, or advance state — even when gate+trigger would align."""
    ex = _FakeExecutor()
    signals = []
    eng = StrategyEngine(
        cfg,
        on_signal=signals.append,
        executor=ex,
        trigger_engine=_FakeEngine([_fresh_strong_trigger()]),
        gate_engine=_FakeEngine([_open_gate()]),
    )
    eng.on_long_candle(_candle())  # gate is open and ready

    result = eng.warmup_trigger(_candle())

    assert result is None
    assert ex.calls == []          # no order placed during warmup
    assert signals == []           # no signal emitted during warmup
    assert eng.state("NFLX") is BotState.WAITING  # state not advanced by warmup


def test_warm_up_primes_gate_ribbon_ready_without_trading(cfg):
    """The orchestrator feeds historical long+short bars per symbol via real engines,
    leaving the 5m gate ribbon ready (and bullishly stacked) and placing no orders."""
    ex = _FakeExecutor()
    eng = StrategyEngine(cfg, executor=ex)  # real RibbonEngines
    longs = _rising_series("NFLX", 60, interval_s=cfg.long_interval_seconds)   # > 56 → ready
    shorts = _rising_series("NFLX", 30, interval_s=cfg.interval_seconds)

    primed = warm_up(eng, ["NFLX"], fetch_short=lambda s: shorts, fetch_long=lambda s: longs)

    assert primed == 1
    assert ex.calls == []  # warmup never trades
    snap = eng._gate_snap["NFLX"]
    assert snap.ribbon_ready          # gate is warm enough to evaluate
    assert snap.gate_open             # rising series → bullishly stacked + fast rising


# --- IMP-032: warmup must not backfill the market-gate duty-cycle table --------------


def test_warmup_gate_emits_no_market_gate_sample(cfg):
    """warmup_gate folds history into the gate ribbon but must NOT emit a sample.

    Warmup replays ~5 days of history at every restart, and the daily-review routine
    restarts the service every evening. Emitting from that path would write hundreds
    of rows for bars that never happened live — into the one table whose rows are
    *counted* to produce the gate's duty cycle, biasing the statistic it exists for.
    """
    samples = []
    eng = StrategyEngine(cfg, on_gate_sample=samples.append)  # real RibbonEngines
    bars = _rising_series("QQQ", 60, interval_s=cfg.long_interval_seconds)

    for candle in bars:
        eng.warmup_gate(candle)

    assert samples == []
    assert eng._market_gate_open() is True  # ...but the ribbon is warmed and readable


def test_warm_up_does_not_emit_gate_samples_through_the_orchestrator(cfg):
    """The same invariant at the level warmup is actually called: warm_up() over the
    filter symbol primes the ribbon and writes nothing."""
    samples = []
    eng = StrategyEngine(cfg, on_gate_sample=samples.append, executor=_FakeExecutor())
    longs = _rising_series("QQQ", 60, interval_s=cfg.long_interval_seconds)
    shorts = _rising_series("QQQ", 30, interval_s=cfg.interval_seconds)

    primed = warm_up(eng, ["QQQ"], fetch_short=lambda _s: shorts, fetch_long=lambda _s: longs)

    assert primed == 1
    assert samples == []
    assert eng._market_gate_open() is True


def test_live_gate_candle_after_warmup_does_emit(cfg):
    """The counterpart: once warmup is done, the first *live* gate candle is sampled —
    so the exclusion is about provenance, not a silently disabled feature."""
    samples = []
    eng = StrategyEngine(cfg, on_gate_sample=samples.append)
    longs = _rising_series("QQQ", 60, interval_s=cfg.long_interval_seconds)
    for candle in longs:
        eng.warmup_gate(candle)
    assert samples == []

    live = _rising_series("QQQ", 61, interval_s=cfg.long_interval_seconds)[-1]
    eng.on_long_candle(live)

    assert len(samples) == 1
    assert samples[0].symbol == "QQQ"
    assert samples[0].gate_open is True
