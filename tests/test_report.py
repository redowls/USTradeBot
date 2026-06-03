"""Tests for the performance report (Phase 10)."""

from __future__ import annotations

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
    def __init__(self, summary):
        self._summary = summary
        self.closed = False

    def performance_summary(self, days):
        return self._summary

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


class _FakeConfig:
    @staticmethod
    def load():
        return object()
