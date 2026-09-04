"""Tests for the MFE/MAE excursion analysis (IMP-025).

The regression cases at the bottom are built from the **real 2026-08-10 session**,
the day that motivated this module: three of four trades peaked below the 1.25%
trail give-back and so were structurally unable to finish green on the trail.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from bot.excursion import (
    Excursion,
    bucket_of,
    ceiling_table,
    compute_excursion,
    excursions_for,
    format_ceiling,
    format_excursions,
    summarize,
)


@dataclass(frozen=True)
class _Trade:
    """Stand-in for persistence.ClosedTrade (duck-typed by excursions_for)."""

    symbol: str
    entry_price: float
    exit_price: float
    pnl: float
    entry_time_utc: datetime
    exit_time_utc: datetime


def _trade(symbol="AVGO", entry=100.0, exit_=101.0, pnl=1.0):
    return _Trade(
        symbol=symbol,
        entry_price=entry,
        exit_price=exit_,
        pnl=pnl,
        entry_time_utc=datetime(2026, 8, 10, 14, 0, tzinfo=UTC),
        exit_time_utc=datetime(2026, 8, 10, 15, 0, tzinfo=UTC),
    )


# --- bucketing ------------------------------------------------------------


@pytest.mark.parametrize(
    "mfe,label",
    [
        (0.0, "<0.5%"),
        (0.49, "<0.5%"),
        (0.5, "0.5-1.0%"),
        (0.99, "0.5-1.0%"),
        (1.0, "1.0-2.0%"),
        (1.99, "1.0-2.0%"),
        (2.0, ">2.0%"),
        (12.0, ">2.0%"),
    ],
)
def test_bucket_edges_are_upper_exclusive(mfe, label):
    assert bucket_of(mfe) == label


# --- compute_excursion ----------------------------------------------------


def test_computes_mfe_mae_and_realized():
    e = compute_excursion("X", 100.0, 101.0, 10.0, [(102.0, 99.0), (103.0, 98.0)])
    assert e is not None
    assert e.mfe_pct == pytest.approx(3.0)
    assert e.mae_pct == pytest.approx(-2.0)
    assert e.realized_pct == pytest.approx(1.0)
    assert e.capture == pytest.approx(100 / 3)
    assert e.bucket == ">2.0%"


def test_no_bars_returns_none_rather_than_a_zero_row():
    assert compute_excursion("X", 100.0, 101.0, 1.0, []) is None


def test_non_positive_entry_price_is_rejected():
    assert compute_excursion("X", 0.0, 1.0, 1.0, [(1.0, 1.0)]) is None


def test_mfe_and_mae_are_clamped_at_the_entry():
    """A trade that never traded above entry has zero MFE, not a negative one."""
    e = compute_excursion("X", 100.0, 98.0, -2.0, [(99.0, 97.0)])
    assert e is not None
    assert e.mfe_pct == 0.0
    assert e.mae_pct == pytest.approx(-3.0)
    assert e.capture is None  # nothing to capture — do not divide by ~0


def test_capture_is_negative_when_a_green_trade_is_closed_red():
    e = compute_excursion("X", 100.0, 99.0, -1.0, [(100.5, 98.9)])
    assert e is not None
    assert e.capture is not None and e.capture < 0


# --- summarize ------------------------------------------------------------


def _exc(symbol, mfe, realized, pnl):
    return Excursion(symbol, 100.0, 100.0 + realized, mfe, -0.5, realized, pnl)


def test_summarize_groups_and_averages_by_band():
    rows = [
        _exc("A", 0.60, -0.67, -11.60),
        _exc("B", 0.59, 0.47, 9.30),
        _exc("C", 2.45, 1.44, 26.21),
    ]
    buckets = {b.label: b for b in summarize(rows)}
    assert set(buckets) == {"0.5-1.0%", ">2.0%"}  # empty bands omitted
    band = buckets["0.5-1.0%"]
    assert band.trades == 2
    assert band.avg_mfe == pytest.approx(0.595)
    assert band.avg_realized == pytest.approx(-0.10)
    assert band.total_pnl == pytest.approx(-2.30)
    assert band.capture is not None and band.capture < 0


def test_summarize_orders_bands_low_to_high():
    rows = [_exc("A", 3.0, 1.0, 1.0), _exc("B", 0.1, 0.0, 0.0)]
    assert [b.label for b in summarize(rows)] == ["<0.5%", ">2.0%"]


def test_summarize_empty_is_empty():
    assert summarize([]) == []


# --- excursions_for -------------------------------------------------------


def test_excursions_for_maps_trades_and_counts_skips():
    bars = {"AAA": [(101.0, 99.0)], "BBB": []}
    rows, skipped = excursions_for(
        [_trade(symbol="AAA"), _trade(symbol="BBB")],
        lambda sym, start, end: bars[sym],
    )
    assert [r.symbol for r in rows] == ["AAA"]
    assert skipped == 1


def test_excursions_for_passes_the_holding_window_to_the_fetcher():
    seen = {}

    def fetch(sym, start, end):
        seen[sym] = (start, end)
        return [(101.0, 99.0)]

    t = _trade(symbol="ZZZ")
    excursions_for([t], fetch)
    assert seen["ZZZ"] == (t.entry_time_utc, t.exit_time_utc)


def test_a_failing_fetch_is_skipped_not_raised():
    def boom(sym, start, end):
        raise RuntimeError("IEX down")

    rows, skipped = excursions_for([_trade()], boom)
    assert rows == [] and skipped == 1


# --- formatting -----------------------------------------------------------


def test_format_reports_the_give_back_headline():
    rows = [_exc("A", 0.60, -0.67, -11.60), _exc("B", 2.45, 1.44, 26.21)]
    text = format_excursions(rows, summarize(rows), trail_percent=0.0125)
    assert "trail give-back 1.25%" in text
    assert "1/2 trades peaked below the 1.25% give-back" in text
    assert "A" in text and "B" in text


def test_format_notes_skipped_trades_and_handles_empty():
    rows = [_exc("A", 1.5, 0.2, 2.0)]
    assert "1 closed trade(s) skipped" in format_excursions(
        rows, summarize(rows), 0.0125, skipped=1
    )
    assert "no closed trades" in format_excursions([], [], 0.0125)


# --- regression: the real 2026-08-10 session ------------------------------
#
# Measured from IEX 1-minute bars over each trade's actual holding window. The
# point of the day: MFE 0.60 / 2.45 / 0.60 / 0.59 against a 1.25% give-back.

_SESSION_2026_08_10 = [
    # symbol, entry, exit, pnl, window high, window low
    ("AVGO", 429.83, 426.93, -11.60, 432.66, 426.73),
    ("ABNB", 181.479, 184.10, 26.21, 185.92, 180.37),
    ("MU", 879.35, 872.25, -14.20, 884.65, 872.25),
    ("BABA", 131.50, 132.12, 9.30, 132.28, 131.31),
]


def _session_rows():
    return [
        compute_excursion(sym, entry, exit_, pnl, [(high, low)])
        for sym, entry, exit_, pnl, high, low in _SESSION_2026_08_10
    ]


def test_2026_08_10_three_of_four_trades_peaked_below_the_give_back():
    rows = _session_rows()
    assert all(r is not None for r in rows)
    trail_pct = 1.25
    below = [r.symbol for r in rows if r.mfe_pct < trail_pct]
    assert below == ["AVGO", "MU", "BABA"]
    # ABNB is the only trade that could finish green on the trail, and did.
    abnb = next(r for r in rows if r.symbol == "ABNB")
    assert abnb.mfe_pct == pytest.approx(2.45, abs=0.01)
    assert abnb.realized_pct == pytest.approx(1.44, abs=0.01)


def test_2026_08_10_capture_is_negative_for_the_sub_give_back_band():
    """The 0.5-1.0% MFE band gave back more than it made — the day's whole story."""
    buckets = {b.label: b for b in summarize(_session_rows())}
    band = buckets["0.5-1.0%"]
    assert band.trades == 3
    assert band.avg_mfe == pytest.approx(0.62, abs=0.02)
    assert band.capture is not None and band.capture < 0
    assert band.total_pnl == pytest.approx(-16.50, abs=0.01)


def test_2026_08_10_mu_gave_back_its_entire_excursion():
    """MU peaked +0.60% and exited on the trail at −0.81%: capture ≈ −134%."""
    mu = compute_excursion("MU", 879.35, 872.25, -14.20, [(884.65, 872.25)])
    assert mu is not None
    assert mu.mfe_pct == pytest.approx(0.60, abs=0.01)
    assert mu.realized_pct == pytest.approx(-0.81, abs=0.01)
    assert mu.capture == pytest.approx(-134, abs=2)


# --- the R ladder (IMP-042) -----------------------------------------------


def test_mfe_r_divides_the_excursion_by_the_trades_own_risk():
    """MFE in R is the move in price over 1R, not a rescaled percentage."""
    # entry 100, stop 98 -> 1R = 2.00. A 3% MFE is 3.00 of price = +1.5R.
    e = compute_excursion("X", 100.0, 101.0, 1.0, [(103.0, 99.0)], 2.0)
    assert e is not None
    assert e.mfe_pct == pytest.approx(3.0)
    assert e.mfe_r == pytest.approx(1.5)


def test_the_same_mfe_percent_lands_on_either_side_of_the_win_line():
    """Why a percent band cannot answer the doctrine's question.

    Identical +1.5% excursions, different stops: one is a WIN-line move, one is not.
    """
    tight = compute_excursion("T", 100.0, 100.0, 0.0, [(101.5, 100.0)], 1.0)
    wide = compute_excursion("W", 100.0, 100.0, 0.0, [(101.5, 100.0)], 3.0)
    assert tight is not None and wide is not None
    assert tight.mfe_pct == pytest.approx(wide.mfe_pct)
    assert tight.mfe_r == pytest.approx(1.5)
    assert wide.mfe_r == pytest.approx(0.5)
    rungs = {r.threshold_r: r for r in ceiling_table([tight, wide])}
    assert rungs[1.0].reached == 1 and rungs[1.0].total == 2


@pytest.mark.parametrize("risk", [None, 0.0, -1.0])
def test_rows_without_a_usable_risk_are_excluded_not_defaulted(risk):
    """A missing stop must shrink the denominator, never be guessed at."""
    e = compute_excursion("X", 100.0, 101.0, 1.0, [(103.0, 99.0)], risk)
    assert e is not None and e.mfe_r is None
    assert all(r.total == 0 for r in ceiling_table([e]))
    assert "unavailable" in format_ceiling(ceiling_table([e]))


def test_ceiling_table_rungs_are_inclusive_and_always_the_full_ladder():
    exact = compute_excursion("X", 100.0, 100.0, 0.0, [(102.0, 100.0)], 2.0)  # exactly +1R
    assert exact is not None and exact.mfe_r == pytest.approx(1.0)
    rungs = ceiling_table([exact])
    assert [r.threshold_r for r in rungs] == [0.5, 1.0, 1.5, 2.0]
    assert [r.reached for r in rungs] == [1, 1, 0, 0]


def test_format_ceiling_names_the_win_line_and_splits_the_gap():
    """The ceiling indicts the entry; the gap below it is what exits could recover."""
    rows = [
        compute_excursion("A", 100.0, 100.0, 0.0, [(103.0, 100.0)], 2.0),  # +1.5R
        compute_excursion("B", 100.0, 100.0, 0.0, [(100.5, 100.0)], 2.0),  # +0.25R
        compute_excursion("C", 100.0, 100.0, 0.0, [(100.5, 100.0)], 2.0),  # +0.25R
        compute_excursion("D", 100.0, 100.0, 0.0, [(100.5, 100.0)], 2.0),  # +0.25R
    ]
    text = format_ceiling(ceiling_table(rows), true_win_rate=0.0)
    assert "doctrine WIN line" in text
    assert "CEILING: 25.0% of entries ever print +1R" in text
    # nothing realized, so the whole 25pp is exit-recoverable and 75pp is the signal
    assert "25.0pp is exit-recoverable" in text
    assert "75.0pp is the entry signal" in text


def test_excursions_for_takes_1r_from_the_recorded_stop_not_the_config():
    """The ladder and the WIN/SCRATCH/FAIL buckets must share one definition of R."""

    @dataclass(frozen=True)
    class _Stopped(_Trade):
        stop_price: float = 0.0

    t = _Stopped(
        symbol="X", entry_price=100.0, exit_price=101.0, pnl=1.0,
        entry_time_utc=datetime(2026, 9, 4, 14, 0, tzinfo=UTC),
        exit_time_utc=datetime(2026, 9, 4, 15, 0, tzinfo=UTC),
        stop_price=99.0,  # 1R = 1.00, far tighter than the 2% config fallback
    )
    rows, _ = excursions_for([t], lambda *_: [(102.0, 99.5)], stop_loss=0.02)
    assert rows[0].risk_per_share == pytest.approx(1.0)
    assert rows[0].mfe_r == pytest.approx(2.0)  # would read +1.0R off the config stop


def test_excursions_for_without_stop_loss_leaves_the_percent_tables_alone():
    rows, _ = excursions_for([_trade()], lambda *_: [(102.0, 99.0)])
    assert rows[0].risk_per_share is None
    assert rows[0].mfe_pct == pytest.approx(2.0)


# --- regression: MU, the real 2026-09-04 trade ----------------------------
#
# The trade that motivated the ladder. Entry 997.565, original bracket stop 976.95
# (1R = 20.615), flattened at 1008.67 for +$22.21. The percent table calls it a
# "1.0-2.0%" trade with 91% capture and reads like a good day; in R it printed
# +1.23% = +0.60R against a WIN line of +1.0R, so it was never a win available to
# any exit rule. The two readings disagree, and the R one is the doctrine's.


def test_2026_09_04_mu_never_reached_the_win_line():
    mu = compute_excursion(
        "MU", 997.565, 1008.67, 22.21, [(1009.685, 992.84)], 997.565 - 976.95
    )
    assert mu is not None
    assert mu.mfe_pct == pytest.approx(1.21, abs=0.02)
    assert mu.capture == pytest.approx(91, abs=2)  # the flattering percent reading
    assert mu.mfe_r == pytest.approx(0.59, abs=0.02)  # the doctrine reading
    rungs = {r.threshold_r: r for r in ceiling_table([mu])}
    assert rungs[0.5].reached == 1
    assert rungs[1.0].reached == 0  # 91% capture of a move that was never a win
