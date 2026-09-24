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


def test_losing_stop_below_entry_is_a_full_stop_not_a_BE_scratch():
    """SPOT −0.35R. The trail had lifted the stop off the 1R anchor, so the old R
    threshold filed it under BE-scratch — i.e. blamed profit capture. But it exited
    at 546.05 against a 549.99 entry: it never traded above entry, the ratchet never
    protected a cent, and the fault is the entry (IMP-055)."""
    v = _classify(LIVE_ROWS[5])
    assert v.bucket == FAIL
    assert v.profit_r < 0  # the fill is below entry
    assert v.fail_kind == FULL_STOP


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


# --- IMP-055: the FAIL split must name the cause, not the depth ----------


def _stop_fill(entry: float, exit_price: float):
    return classify(
        symbol="XYZ",
        entry_price=entry,
        exit_price=exit_price,
        stop_price=entry * (1 - STOP_LOSS),
        target_price=entry * 1.10,
        exit_reason="stop loss",
        pnl=(exit_price - entry) * 10,
        stop_loss=STOP_LOSS,
    )


def test_the_trail_floor_makes_the_old_R_threshold_unreachable():
    """The geometry behind the defect, pinned so a config change re-opens this.

    The ratchet sets the stop to ``price*(1-TRAIL_PERCENT)`` from the first candle
    and never lowers it, so the deepest a stop fill can reach is
    ``-TRAIL_PERCENT/STOP_LOSS`` R = −0.625R. The retired ``FULL_STOP_MAX_R`` of
    −0.75R sat *below* that floor, so no fill could ever be labelled a full stop.
    """
    trail_percent, stop_loss = 0.0125, 0.02  # the live .env pairing
    floor_r = -trail_percent / stop_loss
    assert floor_r == -0.625
    assert floor_r > -0.75  # the old threshold was below the reachable floor

    v = _stop_fill(100.0, 100.0 * (1 + floor_r * stop_loss))  # a fill AT the floor
    assert round(v.profit_r, 3) == -0.625
    assert v.bucket == FAIL
    assert v.fail_kind == FULL_STOP  # was BE_SCRATCH: −0.625 > −0.75


def test_a_stop_that_never_traded_above_entry_is_an_entry_failure():
    """Today's INTC peaked at +0.105R and never armed the ratchet. Under the old
    rule its −0.6R exit read 'BE-scratch' — profit capture — which is the wrong
    end of the strategy to attack."""
    for exit_price in (99.5, 98.8, 100.0):  # red, deep red, and flat on the nose
        v = _stop_fill(100.0, exit_price)
        assert v.bucket == FAIL
        assert v.fail_kind == FULL_STOP, exit_price


def test_a_stop_that_ratcheted_past_entry_is_still_a_capture_failure():
    """The label must keep working where it was always right: above entry the stop
    can only have got there by ratcheting, so the gain was real and unbanked."""
    v = _stop_fill(100.0, 100.15)  # +0.075R, inside FAIL_MAX_R
    assert v.bucket == FAIL
    assert v.fail_kind == BE_SCRATCH


def test_the_split_moves_no_bucket_and_no_headline_rate():
    """The IMP-055 constraint: this re-attributes FAILs, it does not re-count them.

    Everything the escalation rule and the Telegram digest key off must be invariant.
    """
    s = summarize(verdicts_for([_Row(*r) for r in LIVE_ROWS], STOP_LOSS))
    assert (s.trades, s.wins, s.scratches, s.fails) == (6, 0, 3, 3)
    assert (s.stops, s.headline_wins) == (4, 5)
    assert round(s.true_win_rate * 100) == 0
    assert round(s.headline_win_rate * 100) == 83
    assert round(s.stop_rate * 100) == 67
    assert round(s.fail_scratch_rate * 100) == 100
    # only the sub-split moved, and it still sums to the FAIL count
    assert s.full_stops + s.be_scratches == s.fails


def test_the_live_book_reattribution_measured_on_2026_09_24():
    """The finding, as a regression. Over the ten sessions with trades to 09-22 the
    old rule reported 9 BE-scratch / 0 full-stop — 'every failure is profit
    capture'. Seven of those nine never traded above entry.
    """
    # (entry, exit) of the nine FAILs in that window, from dbo.trades
    fails = [
        (100.0, 99.40), (100.0, 99.75), (100.0, 100.12), (100.0, 98.90),
        (100.0, 99.10), (100.0, 100.08), (100.0, 99.55), (100.0, 99.20),
        (100.0, 99.80),
    ]
    verdicts = [_stop_fill(e, x) for e, x in fails]
    assert all(v.bucket == FAIL for v in verdicts)
    s = summarize(verdicts)
    assert s.fails == 9
    assert s.full_stops == 7  # was 0
    assert s.be_scratches == 2  # was 9


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
    # IMP-055: split by where the fill landed, not by depth. NVDA (+0.07R) and TSM
    # (+0.15R) filled above entry — gains locked then handed back. SPOT filled below
    # entry and never locked anything.
    assert s.full_stops == 1
    assert s.be_scratches == 2
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
    assert "FAIL 3 (full 1 / BE-scratch 2)" in text  # IMP-055 re-attribution
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
