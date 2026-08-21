"""Tests for the refused-candidate outcome study (IMP-033).

The scenarios are today's real rows from ``dbo.entry_refusals`` (2026-08-21, a
23-refusal / 0-trade session), so the day that motivated the tool is the day that
regression-tests it.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from bot.persistence import RefusedCandidate
from bot.refusals import (
    classify_reason,
    format_refusals,
    outcomes_for,
    session_flatten_utc,
    summarize_by_reason,
)

# 2026-08-21 refusal ids 62 / 75 / 55, verbatim.
PLTR = RefusedCandidate(
    symbol="PLTR", candle_start_utc=datetime(2026, 8, 21, 16, 21),
    reason="crossover 0.20 < 0.25", close_price=181.07, confidence=75.99,
    market_gate_open=True, atr_pct=0.19813, ribbon_spread_pct=0.00944,
)
QQQ = RefusedCandidate(
    symbol="QQQ", candle_start_utc=datetime(2026, 8, 21, 19, 21),
    reason="crossover 0.02 < 0.25", close_price=713.44, confidence=61.04,
    market_gate_open=True, atr_pct=0.01958, ribbon_spread_pct=0.00116,
)
TSLA = RefusedCandidate(
    symbol="TSLA", candle_start_utc=datetime(2026, 8, 21, 14, 26),
    reason="market gate closed (QQQ 5m ribbon not bullish)", close_price=359.14,
    confidence=77.34, market_gate_open=False, atr_pct=0.30944,
    ribbon_spread_pct=0.15835,
)


def _fetch(mapping):
    """Bar fetcher over a ``{symbol: [(high, low, close), ...]}`` map."""

    def _f(symbol, start, end):
        return list(mapping.get(symbol, []))

    return _f


# --- reason classification -------------------------------------------------


@pytest.mark.parametrize(
    "reason, expected",
    [
        ("crossover 0.20 < 0.25", "crossover"),
        ("confidence 54.6 < 60", "confidence"),
        ("market gate closed (QQQ 5m ribbon not bullish)", "gate"),
        ("Crossover 0.02 < 0.25", "crossover"),  # case-insensitive
        ("some future filter", "other"),
        ("", "other"),
    ],
)
def test_classify_reason_buckets_by_filter_not_by_string(reason, expected):
    assert classify_reason(reason) == expected


def test_unrecognised_reasons_stay_visible_rather_than_folding_into_a_cohort():
    """A new filter must not be silently counted as an existing one."""
    rows, _ = outcomes_for(
        [RefusedCandidate("X", datetime(2026, 8, 21, 15, 0), "brand new filter", 100.0)],
        _fetch({"X": [(101.0, 99.0, 100.5)]}),
        15,
    )
    assert rows[0].reason_class == "other"


# --- the horizon -----------------------------------------------------------


def test_session_flatten_is_1945z_during_edt():
    # 16:00 ET − 15 min = 15:45 ET = 19:45 UTC while EDT is in force.
    assert session_flatten_utc(datetime(2026, 8, 21, 16, 21), 15) == datetime(
        2026, 8, 21, 19, 45
    )


def test_session_flatten_follows_dst_rather_than_a_fixed_offset():
    """A hardcoded 19:45Z would be an hour wrong every winter session."""
    assert session_flatten_utc(datetime(2026, 12, 15, 16, 21), 15) == datetime(
        2026, 12, 15, 20, 45
    )


def test_refusal_after_its_own_flatten_is_skipped_not_scored_as_flat():
    late = RefusedCandidate("QQQ", datetime(2026, 8, 21, 19, 50), "confidence 52 < 60", 713.8)
    rows, skipped = outcomes_for([late], _fetch({"QQQ": [(714.0, 713.0, 713.5)]}), 15)
    assert rows == [] and skipped == 1


def test_symbol_the_tape_did_not_print_is_skipped_not_zeroed():
    rows, skipped = outcomes_for([PLTR], _fetch({}), 15)
    assert rows == [] and skipped == 1


def test_a_failing_fetch_loses_one_row_not_the_table():
    def _boom(symbol, start, end):
        if symbol == "PLTR":
            raise RuntimeError("IEX hiccup")
        return [(714.0, 712.0, 713.0)]

    rows, skipped = outcomes_for([PLTR, QQQ], _boom, 15)
    assert [r.symbol for r in rows] == ["QQQ"]
    assert skipped == 1


# --- the measurement -------------------------------------------------------


def test_scores_the_declined_candidate_against_its_own_forward_tape():
    """PLTR refused at 181.07; tape ran to 183.00 then closed 182.00."""
    rows, skipped = outcomes_for(
        [PLTR], _fetch({"PLTR": [(182.0, 180.0, 181.5), (183.0, 181.0, 182.0)]}), 15
    )
    assert skipped == 0
    (r,) = rows
    assert r.mfe_pct == pytest.approx((183.0 - 181.07) / 181.07 * 100, rel=1e-6)
    assert r.mae_pct == pytest.approx((180.0 - 181.07) / 181.07 * 100, rel=1e-6)
    assert r.forward_pct == pytest.approx((182.0 - 181.07) / 181.07 * 100, rel=1e-6)


def test_a_candidate_that_never_traded_above_entry_has_zero_mfe_not_negative():
    """The <0.5%-MFE cohort question needs MFE clamped at 0, as bot.excursion does."""
    rows, _ = outcomes_for(
        [QQQ], _fetch({"QQQ": [(713.0, 710.0, 711.0)]}), 15
    )
    (r,) = rows
    assert r.mfe_pct == 0.0
    assert r.mae_pct < 0
    assert r.bucket == "<0.5%"


def test_pre_entry_feature_vector_survives_onto_the_outcome():
    """The whole point: pair the decision's features with the tape's verdict."""
    rows, _ = outcomes_for([PLTR], _fetch({"PLTR": [(182.0, 181.0, 181.5)]}), 15)
    (r,) = rows
    assert r.confidence == 75.99
    assert r.market_gate_open is True
    assert r.atr_pct == 0.19813
    assert r.ribbon_spread_pct == 0.00944
    assert r.reason == "crossover 0.20 < 0.25"


def test_missing_tape_context_stays_none_and_does_not_crash_the_study():
    bare = RefusedCandidate("OLD", datetime(2026, 8, 21, 15, 0), "confidence 50 < 60", 10.0)
    rows, _ = outcomes_for([bare], _fetch({"OLD": [(10.1, 9.9, 10.05)]}), 15)
    (r,) = rows
    assert r.confidence is None and r.atr_pct is None and r.market_gate_open is None


# --- aggregation -----------------------------------------------------------


def test_summarize_splits_cohorts_and_appends_an_all_row():
    rows, _ = outcomes_for(
        [PLTR, QQQ, TSLA],
        _fetch({
            "PLTR": [(184.0, 181.0, 183.0)],   # MFE +1.62%, ran
            "QQQ": [(713.5, 712.0, 712.5)],    # MFE +0.01%, never green
            "TSLA": [(360.0, 351.0, 352.0)],   # MAE −2.27%, would have stopped out
        }),
        15,
    )
    stats = {s.label: s for s in summarize_by_reason(rows, 0.0125, 0.02)}
    assert set(stats) == {"crossover", "gate", "ALL"}
    assert stats["crossover"].n == 2
    assert stats["gate"].n == 1
    assert stats["ALL"].n == 3


def test_counts_the_three_verdicts_the_freeze_debate_turns_on():
    rows, _ = outcomes_for(
        [PLTR, QQQ, TSLA],
        _fetch({
            "PLTR": [(184.0, 181.0, 183.0)],
            "QQQ": [(713.5, 712.0, 712.5)],
            "TSLA": [(360.0, 351.0, 352.0)],
        }),
        15,
    )
    allrow = [s for s in summarize_by_reason(rows, 0.0125, 0.02) if s.label == "ALL"][0]
    assert allrow.never_green == 2       # QQQ and TSLA never ran +0.5%
    assert allrow.reached_trail == 1     # only PLTR cleared the 1.25% give-back
    assert allrow.stopped_out == 1       # TSLA's −2.27% MAE breaches the 2% stop


def test_empty_window_summarizes_to_nothing_rather_than_dividing_by_zero():
    assert summarize_by_reason([], 0.0125, 0.02) == []


# --- rendering -------------------------------------------------------------


def test_report_names_the_best_declined_candidate_and_flags_the_upper_bound():
    rows, _ = outcomes_for(
        [PLTR, QQQ],
        _fetch({"PLTR": [(184.0, 181.0, 183.0)], "QQQ": [(713.5, 712.0, 712.5)]}),
        15,
    )
    text = format_refusals(rows, summarize_by_reason(rows, 0.0125, 0.02), 0.0125, 0.02)
    assert "PLTR" in text
    assert "UPPER BOUND" in text
    assert "crossover" in text


def test_report_degrades_to_a_sentence_when_nothing_was_refused():
    assert "nothing scored" in format_refusals([], [], 0.0125, 0.02)
