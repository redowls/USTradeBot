#!/usr/bin/env bash
# Periodic process-health probe (Phase 10), run by ustradebot-health.timer as the
# ustradebot service account. Alerts via Telegram only when the unit is in the
# "failed" state — a clean stop ("inactive") is treated as intentional, so this
# won't spam during maintenance. It's a backstop to ustradebot.service's OnFailure=
# alert (e.g. if Telegram was briefly unreachable when the unit first failed).
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
state="$(systemctl is-active ustradebot.service 2>/dev/null || true)"

if [ "$state" = "failed" ]; then
    "$DIR/.venv/bin/python" -m bot.notify \
        "🟠 USTradeBot health check: service is '$state' on $(hostname). It is NOT running."
fi
