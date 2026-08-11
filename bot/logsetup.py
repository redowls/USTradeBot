"""Logging setup (IMP-026) — one configuration, pinned to UTC.

Every timestamp this bot *reasons* about is UTC: candle starts, `entry_time_utc` /
`exit_time_utc` in `dbo.trades`, the market-hours gate, the EOD-flatten watchdog. Until
2026-08-02 the VPS clock was UTC as well, so `logging`'s default **local-time** `asctime`
agreed with all of them by coincidence. The host then moved to Asia/Jakarta (UTC+7) and
that coincidence broke — a single line now disagrees with itself seven hours apart::

    2026-08-11 21:24:00,223 INFO ustradebot.data | candle TSLA [1m] 2026-08-11T14:23:00+00:00

**No trading behaviour was affected** — every clock read in the trading path is
`datetime.now(UTC)`, so the market-hours gate, the opening-range blackout and the
EOD-flatten watchdog all kept working correctly through the migration. What broke is the
*evidence base*: journald is what the post-close review root-causes trades from, and a
reviewer who reads the prefix as UTC misplaces every event in the session by seven hours.

So: pin the converter to UTC and *label* it in the format, which makes the timebase
self-documenting and means it can never silently follow the host clock again. The default
`datefmt` is kept deliberately — it is the only one that carries milliseconds, and pairing
a `no entry` line with the candle that produced it is done on the millisecond.
"""

from __future__ import annotations

import logging
import time

#: Note the explicit `UTC` marker: the timebase is stated in every line rather than
#: inferred from the host, which is the failure this module exists to prevent.
LOG_FORMAT = "%(asctime)s UTC %(levelname)-8s %(name)s | %(message)s"


def setup_logging(level: str | int = logging.INFO) -> None:
    """Configure root logging at ``level``, with timestamps in **UTC**.

    ``level`` accepts a name (``"INFO"``, as `Config.log_level` supplies) or a numeric
    level; an unrecognised name falls back to ``INFO`` rather than raising — logging
    setup must never be the reason the bot fails to start.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Class-level, so *every* formatter renders UTC — including any created by a
    # library that configures its own handler.
    logging.Formatter.converter = time.gmtime

    formatter = logging.Formatter(LOG_FORMAT)
    formatter.converter = time.gmtime  # explicit, not merely inherited
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # `force=True` because plain `basicConfig` is a *no-op* once the root logger has any
    # handler — so if any import configured logging first, our UTC formatter would be
    # silently discarded and the local-time prefix would come straight back. The whole
    # point of this module is that the timebase cannot depend on ambient conditions, so
    # this call has to be authoritative rather than best-effort. Also makes it idempotent.
    logging.basicConfig(level=level, handlers=[handler], force=True)
