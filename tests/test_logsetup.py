"""Tests for the UTC-pinned logging setup (IMP-026).

The regression these pin is real and dated: on 2026-08-02 the VPS moved from UTC to
Asia/Jakarta, and from that day the `asctime` prefix on every log line silently became
WIB while every timestamp *inside* the line stayed UTC. The 08-11 review had to shift
journald by seven hours by hand to root-cause a zero-trade session.
"""

from __future__ import annotations

import importlib
import logging
import time

import pytest

from bot import flatten, logsetup, main, preflight

# The real moment from the 2026-08-11 session that exposed this: the TSLA candle
# closing 14:23 UTC, whose "no entry ... market gate closed" line journald rendered as
# 21:24 WIB. Epoch seconds for 2026-08-11T14:24:00Z.
TSLA_SIGNAL_EPOCH = 1786458240.0  # == datetime(2026, 8, 11, 14, 24, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _restore_logging():
    """Leave global logging state exactly as found — this module mutates it."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    saved_converter = logging.Formatter.converter
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    logging.Formatter.converter = saved_converter


def _record(created: float) -> logging.LogRecord:
    rec = logging.LogRecord(
        name="ustradebot.strategy",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="no entry TSLA: market gate closed (QQQ 5m ribbon not bullish) (conf=64.8%%)",
        args=(),
        exc_info=None,
    )
    rec.created = created
    rec.msecs = (created - int(created)) * 1000
    return rec


def _formatter() -> logging.Formatter:
    logsetup.setup_logging()
    return logging.getLogger().handlers[0].formatter


def test_timestamps_render_in_utc_not_host_local(monkeypatch):
    """THE 2026-08-02 REGRESSION: WIB host, UTC output."""
    monkeypatch.setenv("TZ", "Asia/Jakarta")
    time.tzset()
    try:
        out = _formatter().format(_record(TSLA_SIGNAL_EPOCH))
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()
    assert "14:24:00" in out, out  # UTC — what the candle payload says
    assert "21:24:00" not in out, out  # WIB — what journald showed all of 08-11


def test_utc_marker_is_present_so_the_timebase_is_self_documenting():
    assert " UTC " in _formatter().format(_record(TSLA_SIGNAL_EPOCH))


def test_milliseconds_are_preserved():
    """Pairing a `no entry` line to the candle that produced it is done on the ms."""
    out = _formatter().format(_record(TSLA_SIGNAL_EPOCH + 0.223))
    assert "14:24:00,223" in out, out


def test_converter_is_gmtime_globally_not_just_on_our_handler():
    logsetup.setup_logging()
    assert logging.Formatter.converter is time.gmtime
    assert logging.Formatter("%(asctime)s").converter is time.gmtime


def test_level_accepts_a_name_like_config_log_level():
    logsetup.setup_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_unknown_level_falls_back_to_info_rather_than_raising():
    """Logging setup must never be the reason the bot fails to start."""
    logsetup.setup_logging("NOT_A_LEVEL")
    assert logging.getLogger().level == logging.INFO


def test_numeric_level_is_accepted():
    logsetup.setup_logging(logging.WARNING)
    assert logging.getLogger().level == logging.WARNING


def test_all_three_entrypoints_share_one_implementation():
    """The three copies that drifted into existence are now one."""
    assert main.setup_logging is logsetup.setup_logging
    assert flatten.setup_logging is logsetup.setup_logging
    assert preflight.setup_logging is logsetup.setup_logging


def test_no_module_configures_its_own_local_time_format():
    """Guards the actual failure mode: a stray basicConfig re-introducing local time."""
    for mod in (main, flatten, preflight, logsetup):
        src = importlib.import_module(mod.__name__).__file__
        with open(src) as fh:
            body = fh.read()
        assert "%(asctime)s %(levelname)" not in body, f"{mod.__name__} re-added a local-time format"
