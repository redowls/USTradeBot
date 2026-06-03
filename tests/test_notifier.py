"""Tests for the Telegram alerts layer (Phase 7).

A fake poster captures the URL + payload so we can assert the messages without a
network, mirroring the persistence/executor test style.
"""

from __future__ import annotations

import pytest

from bot.executor import ExecutionResult
from bot.notifier import AlertReporter, TelegramNotifier, format_entry, format_exit, open_notifier
from bot.risk import ExitResult


class _FakePoster:
    def __init__(self, *, raise_on_call=False) -> None:
        self.calls: list[tuple[str, dict, float]] = []
        self._raise = raise_on_call

    def __call__(self, url, payload, timeout):
        self.calls.append((url, payload, timeout))
        if self._raise:
            raise RuntimeError("network boom")


def _notifier(poster):
    return TelegramNotifier("TOK", "CHAT", poster=poster)


def _exec_result(**kw):
    base = dict(
        symbol="NFLX",
        order_id="order-1",
        qty=25,
        notional=2500.0,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        confidence=82.0,
        status="accepted",
        model="A",
    )
    base.update(kw)
    return ExecutionResult(**base)


# --- transport -------------------------------------------------------------


def test_send_posts_chat_id_and_text_to_token_url():
    poster = _FakePoster()
    assert _notifier(poster).send("hello") is True
    (url, payload, _timeout) = poster.calls[0]
    assert url == "https://api.telegram.org/botTOK/sendMessage"
    assert payload == {"chat_id": "CHAT", "text": "hello"}


def test_send_swallows_transport_errors():
    poster = _FakePoster(raise_on_call=True)
    # Must not raise into the trading path; reports failure instead.
    assert _notifier(poster).send("hi") is False


def test_token_never_appears_in_payload():
    poster = _FakePoster()
    _notifier(poster).send("x")
    _url, payload, _timeout = poster.calls[0]
    assert "TOK" not in payload["text"]
    assert "TOK" not in str(payload.get("chat_id"))


# --- message formatting ----------------------------------------------------


def test_format_entry_includes_size_and_confidence():
    msg = format_entry(_exec_result(qty=25, entry_price=100.0, confidence=82.0))
    assert "ENTRY NFLX" in msg
    assert "25 sh @ $100.00" in msg
    assert "82.0%" in msg
    assert "stop $98.00 / target $104.00" in msg


def test_format_exit_reports_realized_pnl_from_entry():
    entry = _exec_result(qty=10, entry_price=100.0)
    exit_res = ExitResult(
        symbol="NFLX", reason="bearish 1-min ribbon cross", exit_price=105.0, qty=10, order_id="c"
    )
    msg = format_exit(exit_res, entry)
    assert "EXIT NFLX" in msg
    assert "bearish 1-min ribbon cross" in msg
    assert "+$50.00" in msg  # (105 - 100) * 10
    assert "+5.00%" in msg


def test_format_exit_marks_a_loss_with_minus():
    entry = _exec_result(qty=10, entry_price=100.0)
    exit_res = ExitResult(symbol="NFLX", reason="x", exit_price=97.5, qty=10, order_id="c")
    msg = format_exit(exit_res, entry)
    assert "−$25.00" in msg  # explicit minus
    assert "−2.50%" in msg


def test_format_exit_without_entry_omits_pnl():
    exit_res = ExitResult(symbol="NFLX", reason="x", exit_price=99.0, qty=None, order_id="c")
    msg = format_exit(exit_res, None)
    assert "EXIT NFLX" in msg
    assert "P/L" not in msg


# --- AlertReporter glue ----------------------------------------------------


def test_reporter_sends_entry_then_exit_with_pnl():
    poster = _FakePoster()
    reporter = AlertReporter(_notifier(poster))

    reporter.on_result(_exec_result(qty=10, entry_price=100.0))
    reporter.on_exit(ExitResult(symbol="NFLX", reason="r", exit_price=110.0, qty=10, order_id="c"))

    assert len(poster.calls) == 2
    assert "ENTRY NFLX" in poster.calls[0][1]["text"]
    exit_text = poster.calls[1][1]["text"]
    assert "EXIT NFLX" in exit_text
    assert "+$100.00" in exit_text  # entry cached from on_result, (110-100)*10


def test_reporter_exit_without_prior_entry_still_alerts():
    poster = _FakePoster()
    reporter = AlertReporter(_notifier(poster))
    reporter.on_exit(ExitResult(symbol="WPM", reason="r", exit_price=50.0, qty=5, order_id="c"))
    assert "EXIT WPM" in poster.calls[0][1]["text"]
    assert "P/L" not in poster.calls[0][1]["text"]  # no cached entry → no P/L line


def test_reporter_drops_cached_entry_after_exit():
    poster = _FakePoster()
    reporter = AlertReporter(_notifier(poster))
    reporter.on_result(_exec_result(symbol="NFLX", entry_price=100.0, qty=10))
    reporter.on_exit(ExitResult(symbol="NFLX", reason="r", exit_price=110.0, qty=10, order_id="c"))
    # A second exit with no fresh entry must not reuse the consumed entry's P/L.
    reporter.on_exit(ExitResult(symbol="NFLX", reason="r", exit_price=120.0, qty=10, order_id="c"))
    assert "P/L" not in poster.calls[2][1]["text"]


def test_reporter_forwards_feed_alert_verbatim():
    poster = _FakePoster()
    reporter = AlertReporter(_notifier(poster))
    reporter.on_feed_alert("⚠️ market-data feed lost")
    assert poster.calls[0][1]["text"] == "⚠️ market-data feed lost"


# --- open_notifier ---------------------------------------------------------


def _env(monkeypatch, **over):
    base = {
        "ALPACA_KEY_ID": "k",
        "ALPACA_SECRET": "s",
        "TELEGRAM_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "c",
    }
    base.update(over)
    for key, val in base.items():
        monkeypatch.setenv(key, val)


def test_open_notifier_builds_when_configured(monkeypatch):
    _env(monkeypatch)
    from bot.config import Config

    poster = _FakePoster()
    notifier = open_notifier(Config.load(dotenv=False), poster=poster)
    assert notifier is not None
    notifier.send("ping")
    assert poster.calls  # the injected poster is used


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
