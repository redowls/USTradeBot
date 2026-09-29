"""Tests for the historical excursion backfill (IMP-058).

The regression cases are built from the **real 2026-09-29 NBIS trade** — the day
that motivated this module. NBIS entered at 245.80 and exited at 242.38 on a trail
that had replaced the 2% bracket stop 58 seconds after entry; the live tracker
recorded ``mfe = +0.00%`` (it never printed a tick above entry) against
``mae = -1.29%``. A backfill that cannot reproduce those two numbers from bars is
not measuring the same thing as the live path, and the two must share a column.
"""

from __future__ import annotations

from datetime import UTC, datetime

from bot.backfill import (
    OpenWindow,
    _windows_from_rows,
    measure,
    select_bars,
    verify_report,
)

# --- the real 2026-09-29 NBIS trade -----------------------------------------

NBIS_ENTRY = datetime(2026, 9, 29, 14, 48, 3, tzinfo=UTC)
NBIS_EXIT = datetime(2026, 9, 29, 15, 6, 22, tzinfo=UTC)
NBIS = OpenWindow(
    trade_id=307,
    symbol="NBIS",
    entry_time=NBIS_ENTRY,
    exit_time=NBIS_EXIT,
    entry_price=245.80,
    exit_price=242.38,
    pnl=-34.20,
)


def _bar(minute: int, close: float) -> tuple[datetime, float]:
    return (datetime(2026, 9, 29, 14, minute, tzinfo=UTC), close)


class TestSelectBars:
    def test_includes_the_entry_minute_bar(self):
        """The entry-minute bar closes AFTER the fill, so it belongs in the window."""
        bars = [_bar(48, 245.0), _bar(49, 244.0)]
        assert select_bars(bars, NBIS) == [(245.0, 245.0), (244.0, 244.0)]

    def test_excludes_bars_before_entry(self):
        """A pre-entry high must not leak into the excursion — that is look-back bias."""
        bars = [_bar(47, 999.0), _bar(48, 245.0)]
        assert select_bars(bars, NBIS) == [(245.0, 245.0)]

    def test_includes_the_exit_minute_bar(self):
        """Live folds the candle whose close triggered the exit, so the window does too."""
        bars = [
            _bar(48, 245.0),
            (datetime(2026, 9, 29, 15, 6, tzinfo=UTC), 242.4),
            (datetime(2026, 9, 29, 15, 7, tzinfo=UTC), 999.0),
        ]
        selected = select_bars(bars, NBIS)
        assert (242.4, 242.4) in selected
        assert (999.0, 999.0) not in selected

    def test_measures_closes_not_intrabar_extremes(self):
        """Both legs of each pair are the close — the ratchet sets its stop from close."""
        bars = [_bar(48, 245.0)]
        assert select_bars(bars, NBIS) == [(245.0, 245.0)]


class TestMeasure:
    def test_reproduces_the_live_nbis_excursion(self):
        """The real trade: never above entry (MFE 0.00%), low-water close -1.29%."""
        low_close = 245.80 * (1 - 0.0129)
        bars = [_bar(48, 245.61), _bar(50, 244.2), _bar(58, low_close), _bar(59, 243.0)]
        measured, skipped = measure([NBIS], lambda *_: bars)
        assert skipped == []
        mfe, mae = measured[307]
        assert mfe == 0.0  # clamped: it reached its entry and no more
        assert round(mae, 2) == -1.29

    def test_a_window_with_no_bars_is_skipped_not_zeroed(self):
        """Scoring an unmeasurable window as 0% would manufacture a fake ceiling entry."""
        measured, skipped = measure([NBIS], lambda *_: [])
        assert measured == {}
        assert [w.trade_id for w in skipped] == [307]

    def test_bars_outside_the_window_do_not_count(self):
        measured, _ = measure([NBIS], lambda *_: [_bar(47, 900.0)])
        assert measured == {}

    def test_fetches_once_per_symbol_and_session(self):
        """Two trades in one symbol-day cost one call, not two."""
        second = OpenWindow(
            trade_id=308,
            symbol="NBIS",
            entry_time=datetime(2026, 9, 29, 15, 30, tzinfo=UTC),
            exit_time=datetime(2026, 9, 29, 15, 40, tzinfo=UTC),
            entry_price=240.0,
            exit_price=241.0,
            pnl=10.0,
        )
        calls: list[str] = []

        def _fetch(symbol, start, end):
            calls.append(symbol)
            return [_bar(48, 245.0), (datetime(2026, 9, 29, 15, 35, tzinfo=UTC), 242.0)]

        measure([NBIS, second], _fetch)
        assert len(calls) == 1

    def test_mfe_is_positive_when_price_runs_above_entry(self):
        bars = [_bar(48, 245.80 * 1.02), _bar(50, 245.0)]
        measured, _ = measure([NBIS], lambda *_: bars)
        mfe, mae = measured[307]
        assert round(mfe, 2) == 2.00
        assert mae <= 0.0


class TestWindowsFromRows:
    class _Row:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    def _row(self, **over):
        base = dict(
            id=307, symbol="NBIS", entry_time_utc=NBIS_ENTRY, exit_time_utc=NBIS_EXIT,
            entry_price=245.80, exit_price=242.38, pnl=-34.20, mfe_pct=None, mae_pct=None,
        )
        base.update(over)
        return self._Row(**base)

    def test_builds_a_window(self):
        assert _windows_from_rows([self._row()])[0].trade_id == 307

    def test_drops_rows_with_no_usable_anchor(self):
        assert _windows_from_rows([self._row(entry_price=0)]) == []
        assert _windows_from_rows([self._row(exit_time_utc=None)]) == []

    def test_drops_rows_whose_exit_precedes_entry(self):
        assert _windows_from_rows([self._row(exit_time_utc=NBIS_ENTRY.replace(hour=13))]) == []

    def test_naive_timestamps_are_read_as_utc(self):
        w = _windows_from_rows([self._row(entry_time_utc=NBIS_ENTRY.replace(tzinfo=None))])[0]
        assert w.entry_time.tzinfo is UTC

    def test_carries_the_live_measured_value_for_verification(self):
        w = _windows_from_rows([self._row(mfe_pct=0.0, mae_pct=-1.29)])[0]
        assert w.live_mfe == 0.0
        assert w.live_mae == -1.29


class TestVerifyReport:
    def test_reports_agreement_against_live_measured_rows(self):
        w = OpenWindow(**{**NBIS.__dict__, "live_mfe": 0.0, "live_mae": -1.29})
        out = verify_report([w], {307: (0.0, -1.27)})
        assert "n=1" in out
        assert "within 0.10pp: 1/1" in out

    def test_flags_a_reconstruction_that_disagrees(self):
        w = OpenWindow(**{**NBIS.__dict__, "live_mfe": 0.0, "live_mae": -1.29})
        out = verify_report([w], {307: (2.5, -1.27)})
        assert "within 0.10pp: 0/1" in out

    def test_handles_no_comparable_rows(self):
        assert "no comparable rows" in verify_report([NBIS], {})
