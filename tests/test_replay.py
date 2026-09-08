"""Tests for the historical replay harness (bot.replay).

The harness is only useful if its simulated broker fills the way the real one does,
so these pin the fill semantics every backtest number rests on.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bot.candles import Candle
from bot.config import Config
from bot.executor import StopOrderGone
from bot.replay import LONG, SHORT, SimBroker, build_stream, resolve_symbols, summarize

_T0 = datetime(2026, 6, 2, 14, 0, tzinfo=UTC)
_T1 = datetime(2026, 6, 2, 14, 1, tzinfo=UTC)

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
def broker(cfg):
    """Frictionless broker — the fill-*mechanics* tests below assert exact prices.

    Pinning `slippage_bps=0` here keeps "which leg filled, at what trigger, under
    whose order id" separable from "what the fill cost" (IMP-044), and doubles as the
    standing guarantee that 0 bps reproduces every pre-IMP-044 number exactly. The
    default 10 bps path has its own fixture and tests further down.
    """
    b = SimBroker(cfg, equity=10_000.0, slippage_bps=0.0)
    b.now = _T0
    return b


@pytest.fixture
def friction_broker(cfg):
    """The shipped default: 10 bps per side, 0.20% per round trip."""
    b = SimBroker(cfg, equity=10_000.0)
    b.now = _T0
    return b


def _bar(close, *, high=None, low=None, ts=_T1, symbol="NFLX") -> Candle:
    return Candle(
        symbol=symbol,
        start=ts,
        open=close,
        high=high if high is not None else close,
        low=low if low is not None else close,
        close=close,
        volume=100.0,
        trades=1,
    )


def test_execute_sizes_through_the_real_sizing_model(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    assert r is not None
    assert r.qty >= 1
    # -2% stop / +4% target: the real bracket_prices helper on the config DEFAULTS
    # (dotenv=False, so the live .env's TAKE_PROFIT=0.10 is deliberately not read).
    assert r.stop_price == pytest.approx(98.0)
    assert r.take_profit_price == pytest.approx(104.0)
    assert broker.open_positions["NFLX"] is r


def test_execute_refuses_when_buying_power_is_exhausted(cfg):
    b = SimBroker(cfg, equity=100.0, margin_multiple=1.0)
    b.now = _T0
    assert b.execute(symbol="NFLX", entry_price=5_000.0, confidence=75.0) is None


def test_position_cannot_be_stopped_on_its_own_entry_bar(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(97.0, low=90.0, ts=_T0))  # same timestamp as the entry
    assert broker.reconcile_exit("NFLX") is None


def test_stop_fills_intrabar_from_the_bar_low(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(99.0, low=97.5))  # low pierces the 98.00 stop
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(98.0)


def test_target_fills_intrabar_from_the_bar_high(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(103.0, high=105.0))  # high clears the 104.00 target
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(104.0)


def test_bar_covering_both_legs_fills_the_stop_pessimistically(broker):
    """Intrabar sequence is unknowable from OHLC, so the harness must assume the
    worse leg — otherwise every wide bar is scored as a winner."""
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(102.0, high=105.0, low=97.0))  # spans stop AND target
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(98.0)  # the stop, not the target


def test_close_position_returns_none_once_a_leg_has_filled(broker):
    """Mirrors the live executor: a broker-side fill makes the close a no-op, which
    is what routes the exit through reconcile_exit and produces the
    'stop/target filled broker-side' reasons seen in the live book."""
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(99.0, low=97.5))
    assert broker.close_position("NFLX") is None


def test_close_position_fills_at_the_last_mark_when_no_leg_filled(broker):
    broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(103.0))
    oid = broker.close_position("NFLX")
    assert oid is not None
    assert broker.close_fill_price(oid) == pytest.approx(103.0)


def test_replace_stop_price_rotates_the_order_id(broker):
    """The live Alpaca stop leg gets a NEW id on every replace (the 2026-06-30 422
    bug); the sim must rotate too or the trailing ratchet is tested against a lie."""
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    new_id = broker.replace_stop_price(r.stop_order_id, 99.0)
    assert new_id is not None and new_id != r.stop_order_id
    assert broker.replace_stop_price(r.stop_order_id, 99.5) is None  # stale id


def test_replace_stop_price_raises_when_the_leg_already_filled(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.on_bar(_bar(99.0, low=97.5))
    with pytest.raises(StopOrderGone):
        broker.replace_stop_price(r.stop_order_id, 99.0)


def test_book_exit_settles_pnl_and_frees_capital(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    before = broker.buying_power
    broker.now = _T1
    broker.book_exit("NFLX", 105.0, "test exit")
    assert broker.equity == pytest.approx(10_000.0 + 5.0 * r.qty)
    assert "NFLX" not in broker.open_positions
    assert broker.buying_power > before  # capital released for later entries
    assert len(broker.trades) == 1
    assert broker.trades[0].pnl == pytest.approx(5.0 * r.qty)


def test_trailed_stop_fills_at_the_trailed_price_not_the_original(broker):
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.replace_stop_price(r.stop_order_id, 103.0)  # ratcheted up into profit
    broker.on_bar(_bar(104.0, low=102.5))  # pierces the TRAILED stop only
    filled = broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(103.0)


# --- replay universe resolution (IMP-023) ---------------------------------
#
# Regression cohort for the 2026-08-06 review: a bare `python -m bot.replay` silently
# backtested the WATCHLIST bootstrap stub (NFLX,BIRD,WPM) instead of the 19 enabled
# dbo.watchlist rows. Because QQQ — the IMP-022 market-filter symbol — was absent from
# the stub, the gate failed OPEN in both arms of that night's A/B and the filter looked
# like a no-op. These pin the precedence so the harness can never again disagree with
# the deployed watchlist without saying so.


class _FakeStore:
    def __init__(self, symbols):
        self._symbols = tuple(symbols)
        self.closed = False

    def load_watchlist(self):
        return self._symbols

    def close(self):
        self.closed = True


@pytest.fixture
def db_watchlist(monkeypatch):
    """Patch bot.persistence.open_store; returns a setter for the DB's reply."""
    holder = {}

    def _set(symbols):
        store = _FakeStore(symbols) if symbols is not None else None
        holder["store"] = store
        monkeypatch.setattr("bot.persistence.open_store", lambda cfg: store)
        return store

    return _set


def test_default_universe_comes_from_the_db_watchlist_not_the_env_stub(cfg, db_watchlist):
    live = ["AAPL", "AMD", "INTC", "MSFT", "MU", "QQQ"]
    store = db_watchlist(live)
    symbols, source = resolve_symbols(cfg)
    assert symbols == live
    assert source == "dbo.watchlist"
    assert cfg.watchlist == ("NFLX", "BIRD", "WPM")  # the stub it must NOT have used
    assert store.closed  # connection released, harness is a short-lived CLI


def test_default_universe_includes_the_market_filter_symbol(cfg, db_watchlist):
    """The 08-06 failure in one assertion: the gate needs QQQ's bars to evaluate."""
    db_watchlist(["AAPL", "AMD", "INTC", "MSFT", "MU", "QQQ"])
    symbols, _ = resolve_symbols(cfg)
    assert cfg.market_filter_symbol in symbols
    assert cfg.market_filter_symbol not in cfg.watchlist  # stub would have failed open


def test_explicit_symbols_win_over_the_db(cfg, db_watchlist):
    db_watchlist(["AAPL", "QQQ"])
    symbols, source = resolve_symbols(cfg, "mu, intc ")
    assert symbols == ["MU", "INTC"]  # upper-cased, trimmed, order preserved
    assert source == "--symbols"


def test_falls_back_to_env_when_the_db_is_unavailable(cfg, db_watchlist):
    db_watchlist(None)  # open_store returns None (SQLSERVER_CONN unset / init failed)
    symbols, source = resolve_symbols(cfg)
    assert symbols == ["NFLX", "BIRD", "WPM"]
    assert source == "WATCHLIST env"


def test_falls_back_to_env_when_the_watchlist_table_is_empty(cfg, db_watchlist):
    store = db_watchlist([])
    symbols, source = resolve_symbols(cfg)
    assert symbols == ["NFLX", "BIRD", "WPM"]
    assert source == "WATCHLIST env"
    assert store.closed


# --- gate-bar sequencing (IMP-024) -----------------------------------------
#
# Regression cohort for the 2026-08-07 failure: replay entered ABNB 14:45 and MSFT
# 14:47 because the 5m gate bar starting 14:45 had already been folded into the
# ribbon. Live, that bar does not exist until 14:50, and live correctly refused
# both entries ("market gate closed"). The harness was reading the future.

_GATE_SECONDS = 300


def _stamped_bar(symbol: str, start: datetime) -> Candle:
    """A flat bar that exists only to carry a timestamp — these tests assert on
    sequencing, never on price."""
    return Candle(
        symbol=symbol, start=start, open=1.0, high=1.0, low=1.0, close=1.0,
        volume=1.0, trades=1,
    )


def _session(minutes: int, *, at: datetime, symbol: str = "ABNB"):
    """(short, long) bar maps for ``minutes`` of one session, 1m and 5m."""
    short = {
        symbol: [_stamped_bar(symbol, at + timedelta(minutes=i)) for i in range(minutes)]
    }
    long = {
        symbol: [
            _stamped_bar(symbol, at + timedelta(minutes=i)) for i in range(0, minutes, 5)
        ]
    }
    return short, long


def test_gate_bar_is_sequenced_at_its_close_not_its_start():
    """The 08-07 bug in one assertion: the 14:45 gate bar must land at 14:50."""
    at = datetime(2026, 8, 7, 14, 45, tzinfo=UTC)
    short, long = _session(10, at=at)
    stream = build_stream(["ABNB"], short, long, at, at + timedelta(hours=1), _GATE_SECONDS)

    gate_bars = [(ts, c.start) for ts, kind, c in stream if kind == LONG]
    assert gate_bars == [
        (at + timedelta(minutes=5), at),
        (at + timedelta(minutes=10), at + timedelta(minutes=5)),
    ]


def test_trigger_bars_never_see_a_gate_bar_that_has_not_closed():
    """The invariant itself, over a full session: no lookahead at any bar."""
    at = datetime(2026, 8, 7, 13, 30, tzinfo=UTC)
    short, long = _session(390, at=at)
    stream = build_stream(["ABNB"], short, long, at, at + timedelta(days=1), _GATE_SECONDS)

    folded: list[datetime] = []
    for ts, kind, candle in stream:
        if kind == LONG:
            folded.append(candle.start)
            continue
        # Every gate bar the ribbon has seen must already have closed by ``ts``.
        assert all(s + timedelta(seconds=_GATE_SECONDS) <= ts for s in folded), (
            f"trigger bar {ts:%H:%M} saw gate bar {folded[-1]:%H:%M} before its close"
        )
    assert folded, "sanity: the session must contain gate bars"


def test_gate_bar_folds_before_the_trigger_bar_of_the_same_minute():
    """Live's order at the boundary: 5m closing at 14:50 lands before 1m 14:50."""
    at = datetime(2026, 8, 7, 14, 45, tzinfo=UTC)
    short, long = _session(10, at=at)
    stream = build_stream(["ABNB"], short, long, at, at + timedelta(hours=1), _GATE_SECONDS)

    boundary = at + timedelta(minutes=5)
    kinds = [kind for ts, kind, _ in stream if ts == boundary]
    assert kinds == [LONG, SHORT]


def test_sequencing_does_not_change_which_bars_are_replayed():
    """Close-time keying moves order only — the window must select the same bars."""
    at = datetime(2026, 8, 7, 13, 30, tzinfo=UTC)
    end = at + timedelta(minutes=60)
    short, long = _session(390, at=at)
    stream = build_stream(["ABNB"], short, long, at, end, _GATE_SECONDS)

    replayed_long = {c.start for _, kind, c in stream if kind == LONG}
    replayed_short = {c.start for _, kind, c in stream if kind == SHORT}
    assert replayed_long == {c.start for c in long["ABNB"] if at <= c.start < end}
    assert replayed_short == {c.start for c in short["ABNB"] if at <= c.start < end}


def test_multiple_symbols_stay_in_true_chronological_order():
    """Capital contention is only real if symbols interleave by time, not by name."""
    at = datetime(2026, 8, 7, 14, 45, tzinfo=UTC)
    short_a, long_a = _session(10, at=at, symbol="ABNB")
    short_m, long_m = _session(10, at=at, symbol="MSFT")
    short = {**short_a, **short_m}
    long = {**long_a, **long_m}
    stream = build_stream(
        ["ABNB", "MSFT"], short, long, at, at + timedelta(hours=1), _GATE_SECONDS
    )

    stamps = [ts for ts, _, _ in stream]
    assert stamps == sorted(stamps)
    assert len(stream) == 2 * (10 + 2)  # both symbols, 10 trigger + 2 gate bars each


# --- doctrine scoring in the harness (IMP-043) ----------------------------
#
# Regression cohort for the 2026-09-04 weekly: `bot/replay.py` graded a win as
# `t.pnl > 0` while `bot.report` had obeyed the stop-exit doctrine since IMP-039.
# The harness was the court of appeal for every REFUTED verdict of the preceding
# month, so it was deciding strategy questions on the one test the doctrine exists
# to abolish — reporting a 62.3% win rate on the same 90d book the doctrine scores
# at 11.7%. These pin the two numbers to the same summary so they can never drift
# apart silently again.


def _closed(broker, symbol, entry, exit_px, reason, *, conf=75.0):
    """Open a trade through the real sizing model and close it at a chosen price."""
    broker.now = _T0
    broker.execute(symbol=symbol, entry_price=entry, confidence=conf)
    broker.now = _T1
    broker.book_exit(symbol, exit_px, reason)


def test_summary_reports_the_doctrine_beside_the_headline(broker):
    """A book of pure scratches: headline says 100% won, the doctrine says 0% did.

    This is the 2026-09-04 live week reproduced in the harness — TSLA +0.68R on the
    trail and MU +0.54R on the flatten, both green, neither paid for its risk.
    """
    _closed(broker, "NFLX", 100.0, 101.4, "trailing stop")          # +0.70R, green
    _closed(broker, "MSFT", 100.0, 101.1, "end-of-day flatten")     # +0.55R, green

    out = summarize(broker, 10_000.0, stop_loss=0.02)

    assert "win%=100.0" in out          # the headline is preserved, not replaced
    assert "true win rate: 0%" in out   # ...and corrected on the very next line
    assert "(headline 100%)" in out
    assert "SCRATCH 2" in out
    assert "WIN 0" in out
    assert "stop rate: 1/2 (50%)" in out  # only the trailing-stop exit is stop-driven
    assert "FAIL+SCRATCH: 2/2 (100%)" in out


def test_summary_counts_a_target_fill_as_a_real_win(broker):
    """The doctrine must still be able to say yes — otherwise it measures nothing."""
    _closed(broker, "NFLX", 100.0, 110.0, "take profit")  # +5R on a 2% stop

    out = summarize(broker, 10_000.0, stop_loss=0.02)

    assert "WIN 1" in out
    assert "true win rate: 100%" in out
    assert "FAIL+SCRATCH: 0/1 (0%)" in out


def test_summary_r_is_measured_from_the_original_stop_not_the_trailed_one(broker):
    """The ratchet moves the broker's order book; the trade row keeps the 1R anchor.

    If the trailed stop leaked into the denominator, a well-trailed scratch would
    divide by a tiny R and score as a WIN — flattery in exactly the direction the
    doctrine forbids. Pins the R denominator the live/replay comparison rests on.
    """
    broker.now = _T0
    r = broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    broker.replace_stop_price(r.stop_order_id, 99.9)  # ratcheted to a 0.1% width
    broker.now = _T1
    broker.book_exit("NFLX", 100.5, "trailing stop")

    assert broker.trades[0].stop_price == pytest.approx(98.0)  # untouched by the trail
    out = summarize(broker, 10_000.0, stop_loss=0.02)
    assert "WIN 0" in out          # +0.25R off the ORIGINAL stop, not +5R off the trail
    assert "SCRATCH 0" in out      # ...and a stop-driven exit at <= +0.25R is a FAIL
    assert "FAIL 1 (full 0 / BE-scratch 1)" in out


def test_summary_stop_loss_defaults_to_the_brokers_config(broker):
    """Callers holding a Config need not thread it through; the broker has one."""
    _closed(broker, "NFLX", 100.0, 101.4, "trailing stop")

    assert summarize(broker, 10_000.0) == summarize(broker, 10_000.0, stop_loss=0.02)


def test_summary_money_figures_are_untouched_by_the_doctrine(broker):
    """IMP-043 changes what we count, never what we do — net/PF/avg must not move."""
    _closed(broker, "NFLX", 100.0, 104.0, "end-of-day flatten")
    _closed(broker, "MSFT", 100.0, 98.0, "trailing stop")

    net = sum(t.pnl for t in broker.trades)
    out = summarize(broker, 10_000.0, stop_loss=0.02)

    assert f"net={net:+.2f}" in out
    assert "trades=2" in out
    assert "exit reasons:" in out  # the per-reason table still follows the block


# --- friction: the harness pays a spread (IMP-044) -------------------------
#
# Pre-registered by the 2026-09-04 weekly as its #2, with a falsifiable prediction
# attached. The harness was frictionless while the live book was not, and the two
# disagreed about money by 1.8x on the only config-matched window (30d: live
# +$5.17/trade vs replay +$9.43/trade). That gap is ~$4 on ~$2,000 of notional —
# 0.2% per round trip, an ordinary market-order cost — and it was being counted as
# edge. These pin the correction: friction hits the *fill*, never the *trigger*,
# and `--slippage-bps 0` still reproduces every number computed before today.


def test_entry_fills_above_the_signal_close(friction_broker):
    """A market buy crosses the spread: the fill is worse than the price that fired it."""
    r = friction_broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)

    assert r.entry_price == pytest.approx(100.1)  # 10 bps = 0.10% up
    assert friction_broker.entry_fill_price(r.order_id) == pytest.approx(100.1)
    assert friction_broker.trades == []  # still open
    # The bracket legs stay anchored to the signal price, exactly as live: the bot
    # submits stop/target before the broker tells it where the entry actually filled.
    assert r.stop_price == pytest.approx(98.0)
    assert r.take_profit_price == pytest.approx(104.0)


def test_stop_triggers_at_the_stop_and_fills_below_it(friction_broker):
    """Friction must not move the trigger — only what the trigger costs."""
    friction_broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    friction_broker.now = _T1
    friction_broker.on_bar(_bar(99.0, low=98.0))  # touches 98.0 exactly

    filled = friction_broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(97.902)  # 98.0 - 10 bps, not 98.0


def test_a_bar_that_stops_just_short_still_does_not_fill(friction_broker):
    """The trigger is the stop price itself; slippage may not drag it into range."""
    friction_broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    friction_broker.now = _T1
    friction_broker.on_bar(_bar(99.0, low=98.01))  # one cent above the stop

    assert friction_broker.reconcile_exit("NFLX") is None


def test_target_fill_is_still_recognised_as_a_win_after_slippage(friction_broker):
    """A slipped target fill must not be misread as a stop by the doctrine classifier.

    `bot.doctrine` names the take-profit leg by price (within 0.5% of target). At
    10 bps the target fills 0.1% light, which must stay inside that tolerance —
    otherwise IMP-044 would silently convert every WIN in the harness into a FAIL.
    """
    friction_broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    friction_broker.now = _T1
    friction_broker.on_bar(_bar(104.5, high=105.0))
    filled = friction_broker.reconcile_exit("NFLX")
    assert filled is not None
    assert filled[1] == pytest.approx(103.896)  # 104.0 - 10 bps

    friction_broker.book_exit("NFLX", filled[1], "take profit")
    assert "WIN 1" in summarize(friction_broker, 10_000.0, stop_loss=0.02)


def test_market_close_fills_below_the_last_mark(friction_broker):
    """The EOD flatten is a market sell too — it pays the same spread."""
    friction_broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    friction_broker.now = _T1
    friction_broker.on_bar(_bar(103.0))  # no leg touched; sets the mark
    oid = friction_broker.close_position("NFLX")

    assert friction_broker.close_fill_price(oid) == pytest.approx(102.897)


def test_friction_is_the_exact_gap_between_gross_and_net(friction_broker):
    """The round trip on Friday's real MU fill: 2 sh @ ~997.57, $1,995 notional.

    The 09-04 weekly measured the live/replay gap at ~$4 per ~$2,000 round trip and
    pre-registered 10 bps/side as the explanation. This asserts the model actually
    charges that: ~$3.99 on the exact notional of the last trade the bot took.
    """
    friction_broker.execute(symbol="MU", entry_price=997.565, confidence=72.08)
    friction_broker.now = _T1
    friction_broker.book_exit("MU", friction_broker._sell_fill(1008.67), "end-of-day flatten")

    t = friction_broker.trades[0]
    assert t.friction == pytest.approx(t.gross_pnl - t.pnl)
    # The toll is 0.2% of the round trip, whatever the fixture happens to size.
    assert t.friction == pytest.approx(0.002 * t.qty * 997.565, rel=0.01)
    # Scaled to the 2 shares / $1,995.13 the bot actually held on 09-04: ~$4 —
    # the exact per-trade gap the weekly measured between live and replay.
    assert t.friction / t.qty * 2 == pytest.approx(4.0, abs=0.15)
    # ...on a trade whose frictionless P&L was the +$22.21 the live book recorded.
    assert t.gross_pnl / t.qty * 2 == pytest.approx(22.21, abs=0.01)
    assert t.pnl < t.gross_pnl


def test_summary_reports_friction_beside_the_money_line(friction_broker):
    friction_broker.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    friction_broker.now = _T1
    friction_broker.book_exit("NFLX", friction_broker._sell_fill(104.0), "end-of-day flatten")

    out = summarize(friction_broker, 10_000.0, stop_loss=0.02)
    t = friction_broker.trades[0]
    assert "10 bps/side" in out
    assert f"gross={t.gross_pnl:+.2f}" in out
    assert f"net={t.pnl:+.2f}" in out
    assert t.friction > 0


def test_zero_slippage_reproduces_the_frictionless_harness(cfg):
    """`--slippage-bps 0` must be bit-identical to every pre-IMP-044 replay run."""
    b = SimBroker(cfg, equity=10_000.0, slippage_bps=0.0)
    b.now = _T0
    r = b.execute(symbol="NFLX", entry_price=100.0, confidence=75.0)
    b.now = _T1
    b.on_bar(_bar(99.0, low=98.0))

    assert r.entry_price == pytest.approx(100.0)
    assert b.reconcile_exit("NFLX")[1] == pytest.approx(98.0)
    b.book_exit("NFLX", 98.0, "stop loss")
    t = b.trades[0]
    assert t.friction == pytest.approx(0.0)
    assert t.gross_pnl == pytest.approx(t.pnl)


def test_friction_scales_with_trade_count_not_with_edge(friction_broker):
    """Why a frictionless harness over-rewards churn — the mechanism, pinned.

    Two books with the same gross P&L but different trade counts must not net the
    same. This is the systematic bias the 09-04 weekly predicted: friction is a
    per-trade toll, so a scratch-heavy config pays it far more often than its edge
    can refund, and the old harness charged neither.
    """
    for i in range(4):
        sym = f"S{i}"
        friction_broker.now = _T0
        friction_broker.execute(symbol=sym, entry_price=100.0, confidence=75.0)
        friction_broker.now = _T1
        friction_broker.book_exit(sym, friction_broker._sell_fill(100.5), "trailing stop")

    many = sum(t.friction for t in friction_broker.trades)
    assert many == pytest.approx(4 * friction_broker.trades[0].friction)
    assert sum(t.gross_pnl for t in friction_broker.trades) > sum(
        t.pnl for t in friction_broker.trades
    )
