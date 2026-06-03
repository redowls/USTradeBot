"""Tests for the kill switch (Phase 10) — fakes for the Alpaca client + notifier."""

from __future__ import annotations

from types import SimpleNamespace

from bot.flatten import FlattenResult, flatten_all, format_flatten, main


class _FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> bool:
        self.sent.append(text)
        return True


class _FakeClient:
    def __init__(self, *, positions=(), raise_positions=False, raise_close=False) -> None:
        self._positions = [SimpleNamespace(symbol=s) for s in positions]
        self._raise_positions = raise_positions
        self._raise_close = raise_close
        self.close_calls: list[dict] = []

    def get_all_positions(self):
        if self._raise_positions:
            raise RuntimeError("positions boom")
        return self._positions

    def close_all_positions(self, cancel_orders=False):
        self.close_calls.append({"cancel_orders": cancel_orders})
        if self._raise_close:
            raise RuntimeError("close boom")


def test_flatten_closes_positions_and_alerts():
    client = _FakeClient(positions=["NFLX", "WPM"])
    notifier = _FakeNotifier()
    result = flatten_all(client, notifier=notifier)
    assert result.ok and result.count == 2
    assert client.close_calls == [{"cancel_orders": True}]  # also cancels resting orders
    assert "NFLX" in notifier.sent[0] and "WPM" in notifier.sent[0]


def test_flatten_with_no_positions_still_cancels_and_alerts():
    client = _FakeClient(positions=[])
    notifier = _FakeNotifier()
    result = flatten_all(client, notifier=notifier)
    assert result.ok and result.count == 0
    assert client.close_calls == [{"cancel_orders": True}]
    assert "no open positions" in notifier.sent[0]


def test_flatten_reports_failure_when_close_raises():
    client = _FakeClient(positions=["NFLX"], raise_close=True)
    notifier = _FakeNotifier()
    result = flatten_all(client, notifier=notifier)
    assert result.ok is False
    assert "VERIFY MANUALLY" in notifier.sent[0]


def test_flatten_survives_position_read_error():
    client = _FakeClient(raise_positions=True)
    result = flatten_all(client)  # no notifier wired — must not raise
    assert result.count == 0 and result.ok is True
    assert client.close_calls == [{"cancel_orders": True}]


def test_format_flatten_variants():
    assert "closed 1" in format_flatten(FlattenResult(symbols=["NFLX"]))
    assert "no open positions" in format_flatten(FlattenResult(symbols=[]))
    assert "VERIFY" in format_flatten(FlattenResult(symbols=["NFLX"], ok=False))


def test_main_refuses_without_yes(capsys):
    assert main([]) == 2
    assert "Refusing" in capsys.readouterr().out
