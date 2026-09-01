"""Tests for the stop-exit doctrine accounting (IMP-039).

The fixtures are the real ``dbo.trades`` rows from the last three sessions that
traded (2026-08-26..28) — the book that motivated the doctrine: 5 of 6 green, an 83%
headline win rate, and not one trade that reached +1R.
"""

from __future__ import annotations

from bot.doctrine import (
    BE_SCRATCH,
    FAIL,
    FULL_STOP,
    SCRATCH,
    WIN,
    classify,
    format_stop_exits,
    is_stop_driven,
    resolve_reason,
    risk_per_share,
    summarize,
    verdicts_for,
)

STOP_LOSS = 0.02  # cfg.stop_loss

# symbol, entry, stop, target, exit, reason, pnl
LIVE_ROWS = [
    ("PLTR", 177.27, 173.75, 195.03, 177.75, "end-of-day flatten", 5.28),
    ("NVDA", 224.59, 220.25, 247.23, 224.90, "stop/target filled broker-side", 3.78),
    ("TSM", 423.98, 415.44, 466.31, 425.25, "stop/target filled broker-side", 5.08),
    ("TSLA", 351.23, 344.28, 386.44, 354.55, "end-of-day flatten", 16.60),
    (
        "PLTR",
        184.24,
        180.37,
        202.46,
        186.24,
        "end-of-day flatten (stop/target filled broker-side)",
        25.93,
    ),
    ("SPOT", 549.99, 538.65, 604.60, 546.05, "stop/target filled broker-side", -11.82),
]


class _Row:
    """Duck-types :class:`~bot.persistence.ClosedTrade` for ``verdicts_for``."""

    def __init__(self, symbol, entry, stop, target, exit_price, reason, pnl):
        self.symbol = symbol
        self.entry_price = entry
        self.stop_price = stop
        self.target_price = target
        self.exit_price = exit_price
        self.exit_reason = reason
        self.pnl = pnl


def _classify(row):
    symbol, entry, stop, target, exit_price, reason, pnl = row
    return classify(
        symbol=symbol,
        entry_price=entry,
        exit_price=exit_price,
        stop_price=stop,
        target_price=target,
        exit_reason=reason,
        pnl=pnl,
        stop_loss=STOP_LOSS,
    )


# --- R and profit_R ------------------------------------------------------


def test_risk_per_share_uses_the_original_bracket_stop():
    assert risk_per_share(177.27, 173.75, STOP_LOSS) == 177.27 - 173.75


def test_risk_per_share_falls_back_when_the_anchor_is_missing_or_absurd():
    # Rows predating the column, and rows whose stop sits at/above entry.
    assert risk_per_share(100.0, None, STOP_LOSS) == 2.0
    assert risk_per_share(100.0, 0.0, STOP_LOSS) == 2.0
    assert risk_per_share(100.0, 105.0, STOP_LOSS) == 2.0


# --- attributing the IMP-038 catch-all -----------------------------------


def test_catchall_below_target_resolves_to_the_stop_leg():
    # NVDA exited 224.90 against a 247.23 target: that is not the take-profit leg.
    assert resolve_reason("stop/target filled broker-side", 224.90, 247.23) == (
        "trailing stop"
    )


def test_catchall_at_the_target_resolves_to_take_profit():
    assert "take profit" in resolve_reason("stop/target filled broker-side", 247.23, 247.23)


def test_catchall_inside_slippage_tolerance_still_reads_as_take_profit():
    assert "take profit" in resolve_reason("stop/target filled broker-side", 246.30, 247.23)


def test_catchall_with_no_recorded_target_resolves_to_the_stop_leg():
    assert resolve_reason("stop/target filled broker-side", 224.90, None) == "trailing stop"


def test_eod_labelled_catchall_keeps_its_flatten_prefix_but_counts_as_a_stop():
    resolved = resolve_reason(
        "end-of-day flatten (stop/target filled broker-side)", 186.24, 202.46
    )
    assert resolved == "end-of-day flatten (trailing stop)"
    assert is_stop_driven(resolved)


def test_reasons_that_name_their_leg_pass_through():
    assert resolve_reason("end-of-day flatten", 177.75, 195.03) == "end-of-day flatten"
    assert not is_stop_driven("end-of-day flatten")
    assert is_stop_driven("stop loss")
    assert not is_stop_driven("take profit")


# --- the doctrine's verdict on the real book -----------------------------


def test_break_even_stop_that_booked_real_dollars_is_a_FAIL():
    """NVDA booked +$3.78 on a stop leg at +0.07R. Green, and still a failure."""
    v = _classify(LIVE_ROWS[1])
    assert v.pnl > 0 and v.headline_win  # the old test would have called this a win
    assert v.bucket == FAIL
    assert v.fail_kind == BE_SCRATCH  # the stop had ratcheted; this was not a full stop
    assert v.stop_driven
    assert round(v.profit_r, 2) == 0.07


def test_stop_driven_exit_above_a_quarter_R_is_a_SCRATCH_not_a_win():
    """PLTR ran to +0.52R and the stop took it — capital preserved, thesis unpaid."""
    v = _classify(LIVE_ROWS[4])
    assert v.stop_driven
    assert v.bucket == SCRATCH
    assert v.fail_kind == ""


def test_flatten_near_entry_is_a_SCRATCH():
    v = _classify(LIVE_ROWS[0])
    assert not v.stop_driven
    assert v.bucket == SCRATCH


def test_losing_stop_inside_1R_is_a_BE_scratch_FAIL():
    """SPOT −0.35R: red, but the trail had already lifted the stop off the 1R anchor."""
    v = _classify(LIVE_ROWS[5])
    assert v.bucket == FAIL
    assert v.fail_kind == BE_SCRATCH


def test_full_stop_is_distinguished_from_a_break_even_stop():
    v = classify(
        symbol="XYZ",
        entry_price=100.0,
        exit_price=98.0,  # the original 1R stop, taken in full
        stop_price=98.0,
        target_price=110.0,
        exit_reason="stop loss",
        pnl=-40.0,
        stop_loss=STOP_LOSS,
    )
    assert v.bucket == FAIL
    assert v.fail_kind == FULL_STOP


def test_take_profit_is_a_WIN_even_below_1R():
    v = classify(
        symbol="XYZ",
        entry_price=100.0,
        exit_price=100.5,
        stop_price=98.0,
        target_price=100.5,
        exit_reason="take profit",
        pnl=10.0,
        stop_loss=STOP_LOSS,
    )
    assert v.bucket == WIN
    assert not v.stop_driven


def test_exit_at_or_above_1R_is_a_WIN_whatever_ended_it():
    """A trail that gives back little enough still banked the move — that is a win."""
    v = classify(
        symbol="XYZ",
        entry_price=100.0,
        exit_price=102.5,
        stop_price=98.0,
        target_price=110.0,
        exit_reason="trailing stop",
        pnl=50.0,
        stop_loss=STOP_LOSS,
    )
    assert v.bucket == WIN
    assert v.stop_driven  # counted in the stop rate, but not a failure


def test_flatten_that_gave_back_real_money_is_a_FAIL():
    v = classify(
        symbol="XYZ",
        entry_price=100.0,
        exit_price=99.0,  # −0.5R with no stop touched
        stop_price=98.0,
        target_price=110.0,
        exit_reason="end-of-day flatten",
        pnl=-20.0,
        stop_loss=STOP_LOSS,
    )
    assert v.bucket == FAIL
    assert not v.stop_driven


# --- the summary the review reports --------------------------------------


def test_the_real_book_scores_zero_true_wins_against_an_83pc_headline():
    """The regression that motivated IMP-039: 5 green trades, no wins."""
    s = summarize(verdicts_for([_Row(*r) for r in LIVE_ROWS], STOP_LOSS))
    assert s.trades == 6
    assert s.wins == 0
    assert s.scratches == 3
    assert s.fails == 3
    assert s.full_stops == 0  # every failure was a ratcheted stop, not a 1R stop
    assert s.be_scratches == 3
    assert s.stops == 4
    assert s.headline_wins == 5
    assert round(s.true_win_rate * 100) == 0
    assert round(s.headline_win_rate * 100) == 83
    assert round(s.stop_rate * 100) == 67
    # Escalation: FAIL+SCRATCH >= 60% over three trading sessions indicts the entry.
    assert s.fail_scratch_rate == 1.0


def test_summary_of_an_empty_window_is_all_zeroes_and_never_divides_by_zero():
    s = summarize([])
    assert s.trades == 0
    assert s.stop_rate == 0.0
    assert s.true_win_rate == 0.0
    assert s.headline_win_rate == 0.0
    assert s.fail_scratch_rate == 0.0
    assert "no closed trades" in format_stop_exits(s)


def test_format_reports_stop_rate_and_both_win_rates():
    text = format_stop_exits(summarize(verdicts_for([_Row(*r) for r in LIVE_ROWS], STOP_LOSS)))
    assert "stop rate: 4/6 (67%)" in text
    assert "FAIL 3 (full 0 / BE-scratch 3)" in text
    assert "SCRATCH 3" in text
    assert "WIN 0" in text
    assert "true win rate: 0%" in text
    assert "headline 83%" in text


def test_rows_without_a_recorded_stop_still_classify_via_the_fallback():
    """Older rows predate ``stop_price``; they must not crash or silently vanish."""
    v = classify(
        symbol="XYZ",
        entry_price=100.0,
        exit_price=100.1,
        stop_price=None,
        target_price=None,
        exit_reason="stop/target filled broker-side",
        pnl=2.0,
        stop_loss=STOP_LOSS,
    )
    assert v.stop_driven
    assert v.bucket == FAIL  # +0.05R on a stop — a break-even scratch
