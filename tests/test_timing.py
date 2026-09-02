"""Tests for the entry-timing ladder (IMP-040).

The regression cases at the bottom are built from the **real 2026-09-02 session**,
the day that motivated this module: the bot scored 37 candidates and took none,
while NVDA traded a 4.34% range and INTC a 3.35% range. An MFE table cannot tell
that apart from a dead tape; this ladder can, and the tests pin the distinction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from bot.timing import (
    EntryTiming,
    compute_timing,
    format_timing,
    session_bounds_utc,
    summarize,
    timings_for,
)


@dataclass(frozen=True)
class _Trade:
    """Stand-in for persistence.ClosedTrade (duck-typed by timings_for)."""

    symbol: str
    entry_price: float
    exit_price: float
    entry_time_utc: datetime
    exit_time_utc: datetime


def _t(minute: int) -> datetime:
    return datetime(2026, 9, 2, 14, minute, tzinfo=UTC)


def _bars(*rows: tuple[int, float, float]) -> list[tuple[datetime, float, float]]:
    """``(minute, high, low)`` -> session bars keyed by bar start."""
    return [(_t(m), h, low) for m, h, low in rows]


# --- the ladder arithmetic -------------------------------------------------


def test_available_measures_only_the_run_after_the_entry_bar():
    # The session's high (110) happens BEFORE the entry; only 102 is reachable.
    bars = _bars((0, 110.0, 100.0), (1, 101.0, 100.0), (2, 102.0, 100.5))
    r = compute_timing("X", 100.0, 101.0, _t(1), _t(2), bars)
    assert r is not None
    assert r.session_high == 110.0
    assert r.session_low == 100.0
    assert r.session_range_pct == pytest.approx(10.0)
    # 2% still on the table, against a 10% session range.
    assert r.available_pct == pytest.approx(2.0)
    assert r.unspent_share == pytest.approx(0.2)


def test_entry_bar_is_inclusive_on_both_windows():
    # The entry bar's own high is reachable — the bar is still trading when the
    # signal fires on its close.
    bars = _bars((0, 100.0, 99.0), (1, 105.0, 100.0))
    r = compute_timing("X", 100.0, 100.0, _t(1), _t(1), bars)
    assert r is not None
    assert r.available_pct == pytest.approx(5.0)
    assert r.mfe_pct == pytest.approx(5.0)


def test_mfe_stops_at_the_exit_but_available_does_not():
    # Upside that arrived after we were already out counts as available, not MFE:
    # that gap is holding time, and the ladder has to keep the two separable.
    bars = _bars((0, 100.5, 100.0), (1, 101.0, 100.0), (2, 108.0, 101.0))
    r = compute_timing("X", 100.0, 101.0, _t(0), _t(1), bars)
    assert r is not None
    assert r.mfe_pct == pytest.approx(1.0)
    assert r.available_pct == pytest.approx(8.0)


def test_favourable_excursions_clamp_at_zero():
    # A name that never traded above entry offered no upside — which is a
    # different statement from a negative one, and would corrupt unspent_share.
    bars = _bars((0, 100.0, 95.0), (1, 99.0, 94.0))
    r = compute_timing("X", 100.0, 96.0, _t(0), _t(1), bars)
    assert r is not None
    assert r.available_pct == 0.0
    assert r.mfe_pct == 0.0
    assert r.realized_pct == pytest.approx(-4.0)


def test_entry_percentile_locates_the_fill_in_the_days_range():
    bars = _bars((0, 110.0, 100.0))
    early = compute_timing("X", 100.0, 100.0, _t(0), _t(0), bars)
    late = compute_timing("X", 110.0, 110.0, _t(0), _t(0), bars)
    mid = compute_timing("X", 105.0, 105.0, _t(0), _t(0), bars)
    assert early is not None and late is not None and mid is not None
    assert early.entry_percentile == pytest.approx(0.0)  # bought the low
    assert late.entry_percentile == pytest.approx(1.0)  # bought the high
    assert mid.entry_percentile == pytest.approx(0.5)


def test_zero_range_session_has_no_percentile_and_no_unspent_share():
    bars = _bars((0, 100.0, 100.0))
    r = compute_timing("X", 100.0, 100.0, _t(0), _t(0), bars)
    assert r is not None
    assert r.session_range_pct == 0.0
    assert r.entry_percentile is None
    assert r.unspent_share is None


def test_missing_session_is_dropped_not_scored_as_flat():
    assert compute_timing("X", 100.0, 100.0, _t(0), _t(1), []) is None
    assert compute_timing("X", 0.0, 100.0, _t(0), _t(1), _bars((0, 1.0, 1.0))) is None


# --- aggregation -----------------------------------------------------------


def _row(session_range=2.0, available=1.0, mfe=0.5, realized=0.1):
    """Build an EntryTiming with a chosen range by placing the entry at the low."""
    low = 100.0
    return EntryTiming(
        symbol="X",
        entry_price=low,
        session_high=low * (1.0 + session_range / 100.0),
        session_low=low,
        available_pct=available,
        mfe_pct=mfe,
        realized_pct=realized,
    )


def test_summarize_counts_each_rung_against_the_trail():
    trail = 0.0125  # 1.25%
    rows = [
        _row(session_range=4.0, available=3.0, mfe=2.0),  # clears every rung
        _row(session_range=4.0, available=3.0, mfe=0.4),  # loses it while held
        _row(session_range=4.0, available=0.5, mfe=0.4),  # late entry
        _row(session_range=0.6, available=0.5, mfe=0.4),  # dead tape
    ]
    s = summarize(rows, trail)
    assert s is not None
    assert s.trades == 4
    assert s.range_reaching_trail == 3  # only the dead-tape row fails rung 1
    assert s.available_reaching_trail == 2  # the late entry drops out at rung 2
    assert s.mfe_reaching_trail == 1  # only one survived to see it


def test_summarize_uses_medians_not_means():
    # One 20% runner must not drag the typical trade's figure up with it.
    rows = [_row(session_range=1.0, available=0.5, mfe=0.5) for _ in range(4)]
    rows.append(_row(session_range=20.0, available=20.0, mfe=20.0))
    s = summarize(rows, 0.0125)
    assert s is not None
    assert s.median_session_range == pytest.approx(1.0)
    assert s.median_mfe == pytest.approx(0.5)


def test_summarize_of_nothing_is_none():
    assert summarize([], 0.0125) is None


def test_timings_for_skips_a_symbol_whose_fetch_raises():
    def _boom(symbol, start, end):
        if symbol == "BAD":
            raise RuntimeError("no bars")
        return _bars((0, 101.0, 100.0))

    trades = [
        _Trade("BAD", 100.0, 100.0, _t(0), _t(1)),
        _Trade("OK", 100.0, 100.5, _t(0), _t(1)),
    ]
    rows, skipped = timings_for(trades, _boom)
    assert skipped == 1
    assert [r.symbol for r in rows] == ["OK"]


def test_format_timing_survives_an_empty_summary():
    assert "no closed trades" in format_timing(None, 0.0125)


# --- the session window ----------------------------------------------------


def test_session_bounds_follow_eastern_across_the_dst_boundary():
    # EDT (UTC-4): 09:30 ET == 13:30 UTC. EST (UTC-5): 09:30 ET == 14:30 UTC.
    # A hardcoded UTC span would silently measure the wrong session all winter.
    edt_open, edt_close = session_bounds_utc(datetime(2026, 9, 2, 15, 0))
    assert (edt_open.hour, edt_open.minute) == (13, 30)
    assert (edt_close.hour, edt_close.minute) == (20, 0)

    est_open, est_close = session_bounds_utc(datetime(2026, 12, 2, 16, 0))
    assert (est_open.hour, est_open.minute) == (14, 30)
    assert (est_close.hour, est_close.minute) == (21, 0)


def test_session_bounds_return_naive_utc_to_match_stored_timestamps():
    # Trade timestamps are stored naive-UTC; an aware value here would raise on
    # the first comparison against a bar.
    start, end = session_bounds_utc(datetime(2026, 9, 2, 15, 0))
    assert start.tzinfo is None and end.tzinfo is None
    assert start.date() == end.date() == datetime(2026, 9, 2).date()


# --- the 2026-09-02 regression --------------------------------------------


def test_nvda_2026_09_02_wide_range_but_the_signal_caught_the_flat_part():
    """The day's motivating case, from the real session bar and refusal row.

    NVDA traded 218.48-227.95 (a 4.34% range) and closed 224.41. The bot's cross
    fired at 14:55 and was scored 53.69 — refused — with a forward MFE of +1.80%.
    Had it entered, the ladder must show rung 1 clearing the 1.25% trail easily
    while the entry itself sat high in the day's range: the opportunity existed,
    the signal did not catch it. That is an *entry-timing* verdict, and an MFE
    table alone cannot distinguish it from a dead tape.
    """
    # Low first (the 218.48 print is pre-cross), then the cross bar and the peak.
    bars = _bars(
        (0, 219.50, 218.48),
        (55, 224.30, 223.80),  # the 14:55 cross bar
        (56, 227.95, 224.00),  # the session high, after the entry
    )
    r = compute_timing("NVDA", 224.00, 224.41, _t(55), _t(56), bars)
    assert r is not None
    assert r.session_range_pct == pytest.approx(4.335, abs=0.01)
    # The tape offered far more than the trail needs...
    assert r.session_range_pct > 1.25
    # ...but by the entry we were already 58% of the way up the day's range,
    # so only a fraction of that range was still unspent.
    assert r.entry_percentile is not None
    assert r.entry_percentile == pytest.approx(0.583, abs=0.01)
    assert r.unspent_share is not None
    assert r.unspent_share < 0.45


def test_the_ladder_separates_a_dead_tape_from_a_late_entry():
    """Both produce a small MFE; only the ladder says which, and they differ.

    This is the whole point of IMP-040 — on 2026-09-02 the ``--mfe`` and
    ``--refusals`` tables were identical in shape to a genuinely dead session,
    yet NVDA/INTC had moved 4.34%/3.35%. The fixes are opposite: change the
    universe, or change the signal.
    """
    dead = _row(session_range=0.40, available=0.30, mfe=0.30)
    late = _row(session_range=4.34, available=0.30, mfe=0.30)
    assert dead.mfe_pct == late.mfe_pct  # indistinguishable on MFE alone
    s = summarize([dead, late], 0.0125)
    assert s is not None
    # Rung 1 splits them: one name never offered the trail width, the other did.
    assert s.range_reaching_trail == 1
    assert s.available_reaching_trail == 0
    assert dead.unspent_share == pytest.approx(0.75)
    assert late.unspent_share is not None and late.unspent_share < 0.10


def test_format_timing_renders_the_ladder_and_the_reading_key():
    s = summarize([_row(session_range=4.0, available=3.0, mfe=2.0)], 0.0125)
    text = format_timing(s, 0.0125)
    assert "session range" in text
    assert "available at entry" in text
    assert "MFE while held" in text
    assert "wrong universe" in text  # the reading key travels with the table
