"""Tests for the performance report (Phase 10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import bot.report as report
from bot.persistence import PerfBand, PerformanceSummary
from bot.report import _parse_days, format_summary


def _summary(**kw):
    base = dict(
        days=1,
        trades=4,
        wins=3,
        win_rate=0.75,
        total_pnl=120.5,
        avg_pnl=30.125,
        open_positions=1,
        bands=[PerfBand("80-89", 2, 2, 1.0, 50.0, 100.0)],
    )
    base.update(kw)
    return PerformanceSummary(**base)


def test_format_summary_has_headline_and_bands():
    text = format_summary(_summary())
    assert "today" in text
    assert "win rate: 75%" in text
    assert "+$120.50" in text
    assert "open positions: 1" in text
    assert "80-89" in text


def test_format_summary_weekly_span_and_negative_pnl():
    text = format_summary(_summary(days=7, total_pnl=-40.0))
    assert "last 7 days" in text
    assert "−$40.00" in text  # explicit minus


def test_parse_days_default_and_explicit():
    assert _parse_days([]) == 1
    assert _parse_days(["--days", "7"]) == 7
    assert _parse_days(["--days", "garbage"]) == 1  # falls back
    assert _parse_days(["--days", "0"]) == 1  # clamped to >= 1


class _FakeStore:
    def __init__(self, summary, trades=()):
        self._summary = summary
        self._trades = list(trades)
        self.closed = False

    def performance_summary(self, days):
        return self._summary

    def closed_trades(self, days):
        return self._trades

    def close(self):
        self.closed = True


class _FakeNotifier:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return True


def test_main_sends_report(monkeypatch, capsys):
    store = _FakeStore(_summary())
    notifier = _FakeNotifier()
    monkeypatch.setattr(report, "Config", _FakeConfig)
    monkeypatch.setattr(report, "open_store", lambda cfg: store)
    monkeypatch.setattr(report, "open_notifier", lambda cfg: notifier)
    assert report.main([]) == 0
    assert store.closed  # connection released
    assert notifier.sent and "USTradeBot" in notifier.sent[0]
    assert "USTradeBot" in capsys.readouterr().out  # also printed for the journal


def test_main_returns_1_when_persistence_off(monkeypatch):
    monkeypatch.setattr(report, "Config", _FakeConfig)
    monkeypatch.setattr(report, "open_store", lambda cfg: None)
    assert report.main([]) == 1


# --- --mfe excursion table (IMP-025) --------------------------------------


@dataclass(frozen=True)
class _ClosedTrade:
    symbol: str
    entry_price: float
    exit_price: float
    pnl: float
    entry_time_utc: datetime
    exit_time_utc: datetime


def _closed(symbol="MU", entry=879.35, exit_=872.25, pnl=-14.20):
    return _ClosedTrade(
        symbol, entry, exit_, pnl,
        datetime(2026, 8, 10, 16, 17, tzinfo=UTC),
        datetime(2026, 8, 10, 19, 45, tzinfo=UTC),
    )


def test_excursion_report_renders_the_table():
    store = _FakeStore(_summary(), trades=[_closed()])
    text = report.excursion_report(
        store, _FakeConfig.load(), 1, fetch_bars=lambda s, a, b: [(884.65, 872.25)]
    )
    assert "MFE / MAE" in text
    assert "MU" in text
    assert "1/1 trades peaked below the 1.25% give-back" in text


def test_excursion_report_handles_an_empty_window():
    store = _FakeStore(_summary(), trades=[])
    text = report.excursion_report(store, _FakeConfig.load(), 1, fetch_bars=lambda *a: [])
    assert "no closed trades" in text


def test_excursion_report_never_raises():
    """A reporting extra must degrade, not break the report."""

    class _Boom:
        def closed_trades(self, days):
            raise RuntimeError("db gone")

    text = report.excursion_report(_Boom(), _FakeConfig.load(), 1, fetch_bars=lambda *a: [])
    assert "unavailable" in text and "db gone" in text


def test_mfe_flag_prints_to_stdout_but_not_to_telegram(monkeypatch, capsys):
    store = _FakeStore(_summary(), trades=[_closed()])
    notifier = _FakeNotifier()
    monkeypatch.setattr(report, "Config", _FakeConfig)
    monkeypatch.setattr(report, "open_store", lambda cfg: store)
    monkeypatch.setattr(report, "open_notifier", lambda cfg: notifier)
    monkeypatch.setattr(report, "alpaca_bar_fetcher", lambda cfg: (lambda s, a, b: [(884.65, 872.25)]))
    assert report.main(["--mfe"]) == 0
    out = capsys.readouterr().out
    assert "MFE / MAE" in out
    assert "MFE" not in notifier.sent[0]  # digest unchanged


def test_no_mfe_flag_skips_the_table(monkeypatch, capsys):
    store = _FakeStore(_summary(), trades=[_closed()])
    monkeypatch.setattr(report, "Config", _FakeConfig)
    monkeypatch.setattr(report, "open_store", lambda cfg: store)
    monkeypatch.setattr(report, "open_notifier", lambda cfg: None)
    assert report.main([]) == 0
    assert "MFE" not in capsys.readouterr().out


class _FakeConfig:
    trail_percent = 0.0125

    @staticmethod
    def load():
        return _FakeConfig()
