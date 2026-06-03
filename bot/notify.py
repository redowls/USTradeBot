"""Send an ad-hoc Telegram message from the CLI (Phase 10).

A thin wrapper over :func:`bot.notifier.open_notifier` so the systemd
``OnFailure`` ("bot down") and health-check units — and you, by hand — can push a
message using the *same* token/chat id the bot itself uses (from config / .env):

    python -m bot.notify "your message here"

Exit codes: 0 sent, 1 not sent (config/transport), 2 usage.
"""

from __future__ import annotations

import sys

from bot.config import Config, ConfigError
from bot.notifier import open_notifier


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = " ".join(args).strip()
    if not text:
        print("usage: python -m bot.notify <message>")
        return 2
    try:
        cfg = Config.load()
    except ConfigError as e:
        print(f"config error: {e}")
        return 1
    notifier = open_notifier(cfg)
    if notifier is None:
        print("Telegram not configured (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID unset).")
        return 1
    return 0 if notifier.send(text) else 1


if __name__ == "__main__":
    raise SystemExit(main())
