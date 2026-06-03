"""Tests for the ad-hoc Telegram CLI (Phase 10)."""

from __future__ import annotations

import bot.notify as notify


class _FakeNotifier:
    def __init__(self, ok=True):
        self.sent = []
        self._ok = ok

    def send(self, text):
        self.sent.append(text)
        return self._ok


class _FakeConfig:
    @staticmethod
    def load():
        return object()


def test_usage_when_no_message(capsys):
    assert notify.main([]) == 2
    assert "usage" in capsys.readouterr().out


def test_sends_joined_message(monkeypatch):
    notifier = _FakeNotifier()
    monkeypatch.setattr(notify, "Config", _FakeConfig)
    monkeypatch.setattr(notify, "open_notifier", lambda cfg: notifier)
    assert notify.main(["bot", "is", "down"]) == 0
    assert notifier.sent == ["bot is down"]


def test_returns_1_when_telegram_unconfigured(monkeypatch):
    monkeypatch.setattr(notify, "Config", _FakeConfig)
    monkeypatch.setattr(notify, "open_notifier", lambda cfg: None)
    assert notify.main(["hi"]) == 1


def test_returns_1_when_send_fails(monkeypatch):
    monkeypatch.setattr(notify, "Config", _FakeConfig)
    monkeypatch.setattr(notify, "open_notifier", lambda cfg: _FakeNotifier(ok=False))
    assert notify.main(["hi"]) == 1
