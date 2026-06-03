#!/usr/bin/env bash
# Operator kill switch (Phase 10). Stops the bot so it can't re-enter, then cancels
# ALL open orders and closes ALL positions on the Alpaca paper account, with a
# Telegram alert. Run as root on the VPS:
#
#   sudo /opt/ustradebot/deploy/kill-switch.sh
#
# Re-arm afterwards with:  sudo systemctl start ustradebot
set -uo pipefail

echo ">> stopping ustradebot.service (so it can't open new positions)"
systemctl stop ustradebot.service || true

echo ">> flattening: cancel all orders + close all positions"
# Runs as the service account (it owns .env). cd so config finds /opt/ustradebot/.env.
sudo -u ustradebot bash -c 'cd /opt/ustradebot && ./.venv/bin/python -m bot.flatten --yes'

echo ">> done. The bot is stopped and flat. Re-arm with: sudo systemctl start ustradebot"
