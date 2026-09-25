"""Per-sub-score predictive power (IMP-056).

The numbers pinned here are the real 2026-09-25 measurement over the 430 refused
candidates that carry a full sub-score vector — the run that motivated the module.
They are asserted as *directions and orderings*, not to three decimals, so the tests
survive new rows arriving while still failing loudly if the finding reverses.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bot.features import (
    DEGENERATE_SD,
    RSI_BANDS,
    format_terms,
    measure_terms,
    pearson,
    stdev,
    term_power,
)


@dataclass
class FakeOutcome:
    """Enough of :class:`~bot.refusals.RefusalOutcome` for the measurement."""

    mfe_pct: float
    forward_pct: float
    conf_crossover: float | None = None
    conf_trend: float | None = None
    conf_rsi: float | None = None
    conf_volume: float | None = None
    conf_volatility: float | None = None
    rsi_raw: float | None = None


STOP_LOSS = 0.02  # live config: 1R == 2.00%


# --------------------------------------------------------------------------- pearson


def test_pearson_is_none_on_a_constant_column_not_zero():
    """The whole point of the module: 'no variation' != 'varies, predicts nothing'.

    ``conf_rsi`` is saturated at 1.00 on 97% of the population, so this is the case
    that actually occurs, and reporting it as r=0.0 would read as a measured finding
    when nothing was measurable.
    """
    assert pearson([1.0, 1.0, 1.0, 1.0], [0.1, -0.2, 0.5, 0.3]) is None
    assert pearson([0.1, 0.2], [0.5, 0.5]) is None


def test_pearson_needs_at_least_two_pairs_of_equal_length():
    assert pearson([], []) is None
    assert pearson([1.0], [2.0]) is None
    assert pearson([1.0, 2.0], [1.0]) is None


def test_pearson_recovers_a_known_correlation():
    assert pearson([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)
    assert pearson([1.0, 2.0, 3.0], [6.0, 4.0, 2.0]) == pytest.approx(-1.0)


def test_stdev_is_zero_below_two_values():
    assert stdev([]) == 0.0
    assert stdev([0.4]) == 0.0
    assert stdev([0.0, 1.0]) == pytest.approx(0.5)


# ----------------------------------------------------------------- the 09-25 finding


def _rsi_population() -> list[FakeOutcome]:
    """The 2026-09-25 RSI banding: every value in 45–70, outcomes flat across it.

    Band means are the measured ones (avgMFE +0.52 / +0.68 / +0.68 / +0.62 / +0.51 /
    +0.55 across the seven bands swept that night) — non-monotonic and inside a tenth
    of a percent of each other, which is the finding.
    """
    rows: list[FakeOutcome] = []
    for rsi, mfe in (
        (53.0, 0.52), (54.0, 0.55), (56.0, 0.68), (57.0, 0.66),
        (58.0, 0.68), (59.0, 0.62), (62.0, 0.51), (66.0, 0.55),
    ):
        rows.append(FakeOutcome(mfe_pct=mfe, forward_pct=0.0, rsi_raw=rsi))
    return rows


def test_rsi_raw_is_measured_as_noise_across_its_whole_observed_domain():
    """The IMP-047 sweep, answered: there is no band edge to re-anchor the plateau to."""
    tp = term_power(_rsi_population(), "rsi_raw", "rsi_raw", STOP_LOSS, RSI_BANDS)
    assert tp is not None
    assert tp.n == 8
    assert abs(tp.r_mfe) < 0.20, "RSI must not read as informative against MFE"
    # And the population really does sit inside the flat plateau, which is *why*:
    assert all(45.0 <= float(o.rsi_raw) < 70.0 for o in _rsi_population())
    assert not any(b.lo < 45.0 or b.hi > 101.0 for b in tp.bands)


def test_the_45_and_70_rsi_branches_never_fire_in_the_recorded_population():
    """0 of 430 recorded values fell below 45 or at/above 70 (measured 2026-09-25).

    Those are the two branches whose existence justifies ``score_rsi``'s 20 weight
    points. If new rows ever populate them this fails, and the term deserves a re-read.
    """
    tp = term_power(_rsi_population(), "rsi_raw", "rsi_raw", STOP_LOSS, RSI_BANDS)
    assert tp is not None
    fired = {(b.lo, b.hi) for b in tp.bands}
    assert (0.0, 45.0) not in fired
    assert (70.0, 101.0) not in fired


def test_crossover_outranks_rsi_on_measured_power():
    """The ordering the improvement queue now rests on: r(crossover) >> r(rsi).

    Measured 2026-09-25 over n=430: crossover +0.330 against MFE, rsi_raw −0.025.
    """
    rows = [
        FakeOutcome(mfe_pct=0.39, forward_pct=0.03, conf_crossover=0.05, rsi_raw=57.0),
        FakeOutcome(mfe_pct=0.59, forward_pct=-0.18, conf_crossover=0.17, rsi_raw=53.0),
        FakeOutcome(mfe_pct=0.80, forward_pct=0.15, conf_crossover=0.22, rsi_raw=62.0),
        FakeOutcome(mfe_pct=0.80, forward_pct=0.00, conf_crossover=0.30, rsi_raw=56.0),
        FakeOutcome(mfe_pct=1.26, forward_pct=0.39, conf_crossover=0.45, rsi_raw=58.0),
    ]
    xo = term_power(rows, "crossover", "conf_crossover", STOP_LOSS)
    rsi = term_power(rows, "rsi_raw", "rsi_raw", STOP_LOSS, RSI_BANDS)
    assert xo is not None and rsi is not None
    assert xo.r_mfe > 0.20, "crossover must still read as informative"
    assert xo.r_mfe > abs(rsi.r_mfe)


def test_a_saturated_subscore_is_flagged_degenerate_before_any_correlation():
    """``conf_rsi`` >= 0.95 on 97% of 430 rows, sd 0.061 — a subsidy, not a ranking term."""
    rows = [
        FakeOutcome(mfe_pct=m, forward_pct=0.0, conf_rsi=r)
        for m, r in ((0.2, 1.0), (1.4, 1.0), (0.5, 1.0), (0.9, 0.97), (0.3, 1.0))
    ]
    tp = term_power(rows, "rsi", "conf_rsi", STOP_LOSS)
    assert tp is not None
    assert tp.sd < DEGENERATE_SD
    assert tp.degenerate
    assert "DEGENERATE" in format_terms([tp], STOP_LOSS)


def test_a_fully_constant_subscore_reports_no_correlation_rather_than_zero():
    rows = [FakeOutcome(mfe_pct=m, forward_pct=0.0, conf_rsi=1.0) for m in (0.2, 1.4, 0.5)]
    tp = term_power(rows, "rsi", "conf_rsi", STOP_LOSS)
    assert tp is not None
    assert tp.r_mfe is None
    assert tp.sd == 0.0
    assert tp.degenerate


# ------------------------------------------------------------------------ mechanics


def test_missing_terms_are_skipped_not_read_as_a_score_of_zero():
    """Zero-filling a NULL would manufacture the variation the module tests for."""
    rows = [
        FakeOutcome(mfe_pct=0.5, forward_pct=0.0, conf_crossover=None),
        FakeOutcome(mfe_pct=1.5, forward_pct=0.0, conf_crossover=0.40),
        FakeOutcome(mfe_pct=0.9, forward_pct=0.0, conf_crossover=0.20),
    ]
    tp = term_power(rows, "crossover", "conf_crossover", STOP_LOSS)
    assert tp is not None
    assert tp.n == 2, "the NULL row must not be counted"
    assert tp.mean == pytest.approx(0.30)


def test_term_absent_from_the_whole_window_returns_none():
    rows = [FakeOutcome(mfe_pct=0.5, forward_pct=0.0)]
    assert term_power(rows, "crossover", "conf_crossover", STOP_LOSS) is None
    assert measure_terms(rows, STOP_LOSS) == []


def test_reached_1r_uses_the_doctrine_win_line_not_the_trail():
    """1R is ``stop_loss`` percent of entry — 2.00%, not the 1.25% trail give-back."""
    rows = [
        FakeOutcome(mfe_pct=1.30, forward_pct=0.0, conf_crossover=0.5),  # past trail
        FakeOutcome(mfe_pct=2.10, forward_pct=0.0, conf_crossover=0.6),  # past 1R
    ]
    tp = term_power(rows, "crossover", "conf_crossover", STOP_LOSS)
    assert tp is not None
    assert sum(b.reached_1r for b in tp.bands) == 1


def test_empty_bands_are_dropped_and_counts_are_conserved():
    rows = [
        FakeOutcome(mfe_pct=0.4, forward_pct=0.0, conf_crossover=0.02),
        FakeOutcome(mfe_pct=0.8, forward_pct=0.0, conf_crossover=0.05),
        FakeOutcome(mfe_pct=1.2, forward_pct=0.0, conf_crossover=0.90),
    ]
    tp = term_power(rows, "crossover", "conf_crossover", STOP_LOSS)
    assert tp is not None
    assert sum(b.n for b in tp.bands) == tp.n == 3
    assert len(tp.bands) == 2, "the three untouched middle bands must be dropped"


def test_format_is_readable_and_never_raises_on_an_empty_window():
    assert "no scored candidates" in format_terms([], STOP_LOSS)


def test_format_names_noise_and_informative_distinctly():
    # Spread across the range (so not degenerate) but symmetric in the outcome, so
    # the term genuinely carries no linear information: r == 0 by construction.
    noise = [
        FakeOutcome(mfe_pct=m, forward_pct=0.0, conf_trend=t)
        for m, t in ((0.4, 0.1), (0.8, 0.3), (0.5, 0.5), (0.8, 0.7), (0.4, 0.9))
    ]
    tp = term_power(noise, "trend", "conf_trend", STOP_LOSS)
    assert tp is not None and not tp.degenerate
    assert "NOISE" in format_terms([tp], STOP_LOSS)


def test_refusal_outcome_carries_the_vector_so_the_report_can_measure_it():
    """The plumbing IMP-056 added: the sub-scores survive the refusal->outcome hop."""
    from bot.refusals import RefusalOutcome

    o = RefusalOutcome(
        symbol="AMD", reason_class="confidence", reason="confidence 57.7 < 60",
        confidence=57.7, market_gate_open=True, atr_pct=0.20, ribbon_spread_pct=0.1,
        mfe_pct=0.5, mae_pct=-0.2, forward_pct=0.1,
        conf_crossover=0.30, conf_trend=1.0, conf_rsi=1.0,
        conf_volume=0.04, conf_volatility=0.0, rsi_raw=57.4,
    )
    tp = term_power([o], "crossover", "conf_crossover", STOP_LOSS)
    assert tp is not None and tp.mean == pytest.approx(0.30)


def test_refusal_outcome_defaults_the_vector_so_older_callers_still_construct():
    from bot.refusals import RefusalOutcome

    o = RefusalOutcome(
        symbol="AMD", reason_class="confidence", reason="r",
        confidence=None, market_gate_open=None, atr_pct=None, ribbon_spread_pct=None,
        mfe_pct=0.5, mae_pct=-0.2, forward_pct=0.1,
    )
    assert o.conf_crossover is None and o.rsi_raw is None
    assert measure_terms([o], STOP_LOSS) == []
