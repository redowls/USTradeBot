#!/usr/bin/env bash
# On-demand status snapshot (read-only). Unlike healthcheck.sh — which only speaks up
# on the Telegram channel when the unit has *failed* — this prints an at-a-glance
# "is everything OK?" report to stdout for a human doing a daily check. Touches nothing.
#
#   ./deploy/status.sh           # print snapshot
#   ./deploy/status.sh --telegram  # also push the snapshot to Telegram
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/.venv/bin/python"

state="$(systemctl is-active ustradebot.service 2>/dev/null || true)"
since="$(systemctl show ustradebot.service -p ActiveEnterTimestamp --value 2>/dev/null)"
nrestarts="$(systemctl show ustradebot.service -p NRestarts --value 2>/dev/null)"
et="$(TZ=America/New_York date +'%a %Y-%m-%d %H:%M %Z')"

# Market-open gate: Mon-Fri 09:30-16:00 ET (matches bot.signals.market_is_open; ignores holidays).
dow="$(TZ=America/New_York date +%u)"        # 1=Mon .. 7=Sun
hm="$(TZ=America/New_York date +%H%M)"
if [ "$dow" -le 5 ] && [ "$hm" -ge 0930 ] && [ "$hm" -lt 1600 ]; then
    mkt="OPEN"
else
    mkt="CLOSED"
fi

# Feed health: the websocket logs only on (re)connect, never per-tick, so "quiet" is
# normal. What matters is the last connect line and whether a feed-loss fired recently.
feed="$(journalctl -u ustradebot --since today --no-pager 2>/dev/null \
        | grep -iE 'connected to wss' | tail -1 | cut -c1-15)"
[ -z "$feed" ] && feed="(no connect line today)"
feedlost="$(journalctl -u ustradebot --since '-24h' --no-pager 2>/dev/null \
        | grep -iE 'feed.lost|feed lost|feed.down' | wc -l)"
[ "$feedlost" -gt 0 ] && feed="$feed  ⚠ $feedlost feed-loss event(s) in 24h"

# Errors in the last 24h — grep message text (app logs to journald at INFO priority,
# so -p warning is unreliable). Excludes our own kill-switch/down-alert wording.
errpat='ERROR|WARNING|Traceback|Exception|reject|refused'
errs="$(journalctl -u ustradebot --since '-24h' --no-pager 2>/dev/null | grep -cE "$errpat")"
last_err="$(journalctl -u ustradebot --since '-24h' --no-pager 2>/dev/null | grep -E "$errpat" | tail -3)"

report="$("$PY" -m bot.report --days 1 2>&1 | grep -vE '^(Telegram|usage)' )"

snap="$(cat <<EOF
USTradeBot status — $et
service:   $state   (since ${since:-?}, restarts: ${nrestarts:-?})
market:    $mkt (09:30-16:00 ET, Mon-Fri)
feed:      last websocket log @ $feed
warnings:  $errs in last 24h
--
$report
EOF
)"

echo "$snap"
if [ "$errs" -gt 0 ]; then
    echo "-- recent warnings/errors --"
    echo "$last_err"
fi

if [ "${1:-}" = "--telegram" ]; then
    "$PY" -m bot.notify "$snap"
fi
