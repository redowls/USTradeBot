#!/usr/bin/env bash
# USTradeBot VPS setup (Phase 9) — the repeatable, no-sudo part: create the venv,
# install pinned runtime deps, and scaffold .env. The OS-level prerequisites
# (Python 3.11+, unixODBC + msodbcsql18) are installed once by hand — see
# deploy/DEPLOY.md. Re-running this script is safe (idempotent).
#
# Usage (from the repo root, as the service account):
#   bash deploy/setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

PYTHON="${PYTHON:-python3}"
echo ">> Using $("$PYTHON" --version) at $(command -v "$PYTHON")"

# Require 3.11+ (the project targets py311; zoneinfo + modern typing are used).
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    sys.exit(f"Python 3.11+ required, found {sys.version.split()[0]}. See deploy/DEPLOY.md.")
PY

if [ ! -d .venv ]; then
    echo ">> Creating virtualenv at .venv"
    "$PYTHON" -m venv .venv
fi

echo ">> Installing pinned runtime dependencies"
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

if [ ! -f .env ]; then
    echo ">> Scaffolding .env from .env.example (FILL IN THE SECRETS, then chmod 600 .env)"
    cp .env.example .env
    chmod 600 .env
else
    echo ">> .env already present — leaving it untouched"
fi

echo
echo ">> Done. Next:"
echo "   1. Edit .env (Alpaca paper keys, Telegram token/chat id, SQLSERVER_CONN)."
echo "   2. Verify connectivity:  ./.venv/bin/python -m bot.preflight"
echo "   3. Install the systemd unit (see deploy/DEPLOY.md)."
