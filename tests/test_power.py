"""Tests for the time-to-decision arithmetic (IMP-054).

The fixtures are the two real cohorts that motivated the module, measured
2026-09-22 against ``dbo.trades``:

* **current trail geometry** — the 38 trades closed since IMP-021 (2026-08-04) set
  the trail's present shape: expectancy **+$6.7247/trade**, sd **$21.7427**. The most
  flattering cohort the book contains, and its 95% interval still straddles zero.
* **all-time** — all 282 closed trades since 2026-06-09: expectancy **+$0.3743/trade**,
  sd **$26.1642**. 18x smaller than the cohort above, and indistinguishable from it.

The measured fill rate on that date was **2.60 trades/week** (trailing five complete
ISO weeks: W34-W38 = 2, 6, 2, 1, 2). Those three numbers are the whole finding: the
same book supports "four months" and "281 years" depending only on which cohort you
believe, and one year of live trading cannot see an edge the size of the one the bot
has actually produced.

The sample-size formula was validated by simulation before it shipped — at the n it
returns, achieved power is 0.802-0.806 against the 0.800 target (0.795-0.796 without
:data:`~bot.power.T_CORRECTION`).
"""

from __future__ import annotations

import datetime as dt

import pytest

from bot.power import (
    T_CORRECTION,
    ExpectancySample,
    Horizon,
    fills_per_week,
    format_power,
    horizon_table,
    minimum_detectable_expectancy,
    required_trades,
    sample_expectancy,
    weeks_to_confirm,
)

# The two live cohorts, 2026-09-22.
GEOMETRY = ExpectancySample(n=38, mean=6.7247, sd=21.7427, unit="$")
ALL_TIME = ExpectancySample(n=282, mean=0.3743, sd=26.1642, unit="$")
GEOMETRY_R = ExpectancySample(n=38, mean=0.1301, sd=0.5373, unit="R")
RATE = 2.60  # trades/week, trailing five complete ISO weeks


# --- the arithmetic ---------------------------------------------------------


def test_required_trades_matches_the_textbook_formula():
    """n = ((1.9600 + 0.8416) * sd / mean)^2 + 2, hand-computed.

    mean 0.10, sd 1.0 -> (2.8015852 * 10)^2 = 784.89 -> ceil 785 -> +2 -> 787.
    """
    assert required_trades(0.10, 1.0) == 787


def test_required_trades_applies_the_t_correction():
    bare = round((2.8015852181 * 1.0 / 0.10) ** 2)
    assert required_trades(0.10, 1.0) - bare == T_CORRECTION


def test_required_trades_is_scale_free():
    """Only the ratio mean/sd matters, so dollars and cents agree."""
    assert required_trades(6.7247, 21.7427) == required_trades(672.47, 2174.27)


def test_required_trades_is_none_when_there_is_no_edge_to_find():
    assert required_trades(0.0, 21.74) is None
    assert required_trades(6.72, 0.0) is None


def test_tighter_alpha_and_higher_power_both_cost_trades():
    base = required_trades(0.10, 1.0)
    assert required_trades(0.10, 1.0, alpha=0.01) > base
    assert required_trades(0.10, 1.0, power=0.90) > base


def test_unsupported_confidence_level_raises_rather_than_approximating():
    with pytest.raises(ValueError):
        required_trades(0.10, 1.0, alpha=0.07)
    with pytest.raises(ValueError):
        required_trades(0.10, 1.0, power=0.75)
    with pytest.raises(ValueError):
        required_trades(0.10, 1.0, alpha=1.5)


def test_minimum_detectable_inverts_required_trades():
    """The honest instrument and the post-hoc one are the same arithmetic."""
    mde = minimum_detectable_expectancy(173, 21.7427)
    assert mde is not None
    # Feeding the floor back in asks for the sample we started from.
    assert required_trades(mde, 21.7427) == pytest.approx(173, abs=T_CORRECTION + 1)


def test_minimum_detectable_falls_as_the_sample_grows():
    sd = 21.7427
    floors = [minimum_detectable_expectancy(n, sd) for n in (71, 105, 173, 308, 714)]
    assert all(a > b for a, b in zip(floors, floors[1:]))


def test_minimum_detectable_needs_more_trades_than_the_correction():
    assert minimum_detectable_expectancy(T_CORRECTION, 21.74) is None
    assert minimum_detectable_expectancy(0, 21.74) is None


# --- the cohorts, and the finding ------------------------------------------


def test_sample_expectancy_needs_two_trades_for_an_sd():
    assert sample_expectancy([1.0], "$") is None
    assert sample_expectancy([], "$") is None
    s = sample_expectancy([1.0, 3.0], "$")
    assert s is not None and s.n == 2 and s.mean == pytest.approx(2.0)


def test_the_most_flattering_cohort_still_straddles_zero():
    """+$6.72/trade over 38 trades is not a demonstrated edge."""
    assert GEOMETRY.straddles_zero()
    lo, hi = GEOMETRY.interval()
    assert lo == pytest.approx(-0.19, abs=0.01)
    assert hi == pytest.approx(13.64, abs=0.01)
    assert GEOMETRY.t_stat == pytest.approx(1.91, abs=0.01)


def test_current_geometry_cohort_would_need_85_trades_if_it_were_real():
    assert required_trades(GEOMETRY.mean, GEOMETRY.sd) == 85
    weeks = weeks_to_confirm(GEOMETRY, RATE)
    assert weeks is not None
    assert weeks == pytest.approx((85 - 38) / RATE, abs=0.01)  # ~18 weeks
    assert 17 < weeks < 19


def test_the_all_time_cohort_needs_centuries():
    """The same book, read over 282 trades instead of 38: 281 years."""
    need = required_trades(ALL_TIME.mean, ALL_TIME.sd)
    assert need is not None and need > 38_000
    weeks = weeks_to_confirm(ALL_TIME, RATE)
    assert weeks is not None
    assert weeks / 52 > 250


def test_the_two_cohorts_disagree_by_an_order_of_magnitude_and_neither_excludes_zero():
    """Why the post-hoc answer must never be quoted alone."""
    assert GEOMETRY.mean / ALL_TIME.mean > 15
    assert GEOMETRY.straddles_zero() and ALL_TIME.straddles_zero()


def test_a_year_of_live_trading_cannot_see_the_edge_the_bot_has_produced():
    """**The finding.** The 2026-09-22 regression case for the whole module.

    At 2.60 fills/week a year buys 173 trades, whose smallest confirmable edge is
    ~$4.66/trade. The bot's realized all-time expectancy is $0.3743/trade — an order
    of magnitude below the floor. Even five years (714 trades) cannot reach it.
    """
    rows = horizon_table(GEOMETRY.sd, RATE, already=GEOMETRY.n)
    by_weeks = {r.weeks: r for r in rows}
    year = by_weeks[52]
    assert year.trades == 173
    assert year.mde == pytest.approx(4.66, abs=0.01)
    assert year.mde > ALL_TIME.mean * 10

    five = by_weeks[260]
    assert five.trades == 714
    assert five.mde == pytest.approx(2.28, abs=0.01)
    assert five.mde > ALL_TIME.mean * 5


def test_the_r_view_is_not_the_dollar_view():
    """Position size varies, so the two units need different samples (IMP-054)."""
    assert required_trades(GEOMETRY_R.mean, GEOMETRY_R.sd) == 136
    assert required_trades(GEOMETRY.mean, GEOMETRY.sd) == 85


def test_horizon_table_credits_trades_already_taken():
    fresh = horizon_table(21.74, RATE, already=0, weeks=(52,))[0]
    credited = horizon_table(21.74, RATE, already=38, weeks=(52,))[0]
    assert credited.trades - fresh.trades == 38
    assert credited.mde < fresh.mde


def test_horizon_months_are_reported_alongside_weeks():
    assert Horizon(weeks=26, trades=100, mde=1.0).months == pytest.approx(6.0)


def test_weeks_to_confirm_is_none_when_the_bot_is_not_trading():
    assert weeks_to_confirm(GEOMETRY, 0.0) is None
    assert weeks_to_confirm(ExpectancySample(38, 0.0, 21.74, "$"), RATE) is None


def test_weeks_to_confirm_is_zero_once_the_sample_is_already_large_enough():
    big = ExpectancySample(n=500, mean=6.7247, sd=21.7427, unit="$")
    assert weeks_to_confirm(big, RATE) == 0.0


# --- the fill rate ---------------------------------------------------------


def _d(iso_year: int, iso_week: int) -> dt.date:
    return dt.date.fromisocalendar(iso_year, iso_week, 3)  # a Wednesday


def test_fills_per_week_reproduces_the_measured_2026_09_22_rate():
    """W34-W38 held 2, 6, 2, 1, 2 exits -> 13/5 = 2.60 trades/week."""
    dates = []
    for week, count in ((34, 2), (35, 6), (36, 2), (37, 1), (38, 2)):
        dates += [_d(2026, week)] * count
    assert fills_per_week(dates, today=dt.date(2026, 9, 22)) == pytest.approx(2.60)


def test_fills_per_week_ignores_the_partial_current_week():
    """2026-09-22 is ISO W39; today's own fill must not inflate the rate."""
    dates = [_d(2026, 38)] * 2 + [dt.date(2026, 9, 22)] * 50
    assert fills_per_week(dates, today=dt.date(2026, 9, 22)) == pytest.approx(0.40)


def test_fills_per_week_counts_silent_weeks_as_zero():
    assert fills_per_week([], today=dt.date(2026, 9, 22)) == 0.0


def test_fills_per_week_window_is_configurable():
    dates = [_d(2026, 38)] * 5 + [_d(2026, 33)] * 100
    # W33 is six weeks back, outside the default five-week window.
    assert fills_per_week(dates, today=dt.date(2026, 9, 22)) == pytest.approx(1.0)
    assert fills_per_week(dates, weeks=6, today=dt.date(2026, 9, 22)) == pytest.approx(17.5)


# --- presentation ----------------------------------------------------------


def test_format_power_states_the_verdict_and_the_floor():
    text = format_power(GEOMETRY, RATE)
    assert "straddles zero: NOT distinguishable" in text
    assert "2.60 trades/week" in text
    assert "post-hoc" in text  # the caveat travels with the number
    assert "minimum detectable expectancy" in text
    assert "$4.66/trade" in text  # the 52-week floor


def test_format_power_renders_r_units_as_r():
    text = format_power(GEOMETRY_R, RATE)
    assert "R/trade" in text
    assert "$" not in text


def test_format_power_handles_a_zero_edge_without_dividing_by_it():
    text = format_power(ExpectancySample(38, 0.0, 21.74, "$"), RATE)
    assert "unconfirmable" in text
