# Phase 9 — VPS deployment (Ubuntu + systemd)

Deploys USTradeBot as a long-lived service that starts on boot and auto-restarts
on crash. Everything stays on the **Alpaca paper account**. Run these on the
Ubuntu VPS as a sudo-capable user.

The layout this guide (and `deploy/ustradebot.service`) assumes:

| Thing            | Path / value                  |
|------------------|-------------------------------|
| Repo             | `/opt/ustradebot`             |
| Virtualenv       | `/opt/ustradebot/.venv`       |
| Secrets/tunables | `/opt/ustradebot/.env` (0600) |
| Service account  | `ustradebot` (no login shell) |
| Server clock     | **UTC**                       |

---

## 1. Prerequisites (run once, as sudo)

**Python 3.11+** — the project targets 3.11 (`zoneinfo`, modern typing). Ubuntu
24.04 ships 3.12 (fine). On 22.04 (ships 3.10) add deadsnakes:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv
# then run setup.sh with: PYTHON=python3.11 bash deploy/setup.sh
```

**SQL Server ODBC driver** (only if you use persistence — `SQLSERVER_CONN`). The
bot needs `ODBC Driver 18 for SQL Server` + unixODBC, per `requirements.txt`:

```bash
curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
  | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc > /dev/null
curl -sSL https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list \
  | sudo tee /etc/apt/sources.list.d/mssql-release.list > /dev/null
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
```

> If you leave `SQLSERVER_CONN` empty, persistence is disabled and you can skip
> the ODBC driver — the bot still trades and alerts (it's a side-channel).

**Git + build basics:**

```bash
sudo apt-get install -y git
```

---

## 2. Service account + code

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin ustradebot
sudo mkdir -p /opt/ustradebot
sudo chown ustradebot:ustradebot /opt/ustradebot

# Clone as the service account
sudo -u ustradebot git clone https://github.com/redowls/USTradeBot.git /opt/ustradebot
```

## 3. Virtualenv + dependencies + .env

```bash
cd /opt/ustradebot
sudo -u ustradebot bash deploy/setup.sh      # or: PYTHON=python3.11 ...
sudo -u ustradebot nano .env                 # fill in the secrets, then save
sudo -u ustradebot chmod 600 .env
```

Fill `.env` from the prompts in [`.env.example`](../.env.example): Alpaca **paper**
keys, `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID`, and (optionally) `SQLSERVER_CONN`.
`ALPACA_BASE_URL` must stay the paper endpoint — the bot refuses to start otherwise.

## 4. Set the clock to UTC

The market-hours gate converts UTC → US Eastern itself (EST/EDT-aware), so the
**server must run on UTC**:

```bash
sudo timedatectl set-timezone UTC
timedatectl            # confirm "Time zone: UTC"
```

## 5. Preflight — confirm the VPS reaches everything

This is the Phase 9 "VPS reaches Alpaca, Telegram, and SQL Server" check. It also
sends a real Telegram test message and reports whether the session is open now:

```bash
cd /opt/ustradebot
sudo -u ustradebot ./.venv/bin/python -m bot.preflight
```

Expect Alpaca **PASS** (status/equity/buying power), and PASS/WARN for SQL Server
and Telegram. A FAIL on Alpaca means the VPS can't reach the broker — fix that
before starting the service (firewall / keys / clock).

## 6. Install + start the service

```bash
sudo cp /opt/ustradebot/deploy/ustradebot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ustradebot
systemctl status ustradebot          # should be "active (running)"
```

## 7. Watch it run

```bash
journalctl -u ustradebot -f          # live logs
journalctl -u ustradebot --since "1 hour ago"
```

You should see the startup banner (watchlist + strategy line), the account
snapshot, and "no open positions" / reconciled holdings. Entries/exits appear in
the log, in Telegram, and (if configured) in SQL Server — but only when a fresh
1-min bullish cross fires while the 5-min gate is open, which may be rare.

---

## Operations

| Task                | Command                                              |
|---------------------|------------------------------------------------------|
| Restart             | `sudo systemctl restart ustradebot`                  |
| Stop                | `sudo systemctl stop ustradebot`                     |
| Disable on boot     | `sudo systemctl disable ustradebot`                  |
| Update to latest    | see below                                            |
| Tail logs           | `journalctl -u ustradebot -f`                        |
| Re-run preflight    | `sudo -u ustradebot ./.venv/bin/python -m bot.preflight` |

**Update to the latest `main`:**

```bash
cd /opt/ustradebot
sudo -u ustradebot git pull
sudo -u ustradebot ./.venv/bin/python -m pip install -r requirements.txt
sudo systemctl restart ustradebot
```

**Crash-loop guard:** if the bot exits non-zero 5 times within 5 minutes (e.g. a
bad `.env` or unreachable account), systemd stops retrying and the unit goes
`failed`. Check why with `systemctl status ustradebot` / `journalctl -u ustradebot`,
fix, then `sudo systemctl reset-failed ustradebot && sudo systemctl start ustradebot`.

---

## 8. Monitoring & maintenance (Phase 10)

Install the monitoring units (alongside `ustradebot.service`), the journald cap,
and make the scripts executable:

```bash
cd /opt/ustradebot
sudo cp deploy/ustradebot-down.service \
        deploy/ustradebot-report.service deploy/ustradebot-report.timer \
        deploy/ustradebot-health.service deploy/ustradebot-health.timer \
        /etc/systemd/system/
sudo cp deploy/journald-ustradebot.conf /etc/systemd/journald.conf.d/ustradebot.conf
sudo chmod +x deploy/healthcheck.sh deploy/kill-switch.sh
sudo systemctl daemon-reload
sudo systemctl restart systemd-journald
sudo systemctl enable --now ustradebot-report.timer ustradebot-health.timer
systemctl list-timers 'ustradebot-*'        # confirm both are scheduled
```

What you get:

| Feature | How |
|---------|-----|
| **Bot-down alert** | `OnFailure=ustradebot-down.service` on the main unit → Telegram message when the bot enters `failed`. |
| **Periodic health check** | `ustradebot-health.timer` (every 15 min) runs `healthcheck.sh`; alerts if the unit is `failed` (backstop to OnFailure; no spam on a clean stop). |
| **Daily performance report** | `ustradebot-report.timer` (Mon–Fri 21:30 UTC, after the US close) runs `python -m bot.report` → trades / win rate / P&L + the confidence-band breakdown, to Telegram + journal. |
| **Log rotation** | journald capped at `SystemMaxUse=500M` / 1-month retention via the drop-in. |

Manual reports any time:

```bash
sudo -u ustradebot ./.venv/bin/python -m bot.report --days 1     # today
sudo -u ustradebot ./.venv/bin/python -m bot.report --days 7     # last week
```

**🛑 Kill switch (flatten everything):** stops the bot, then cancels all open
orders and closes all positions on the paper account (with a Telegram alert):

```bash
sudo /opt/ustradebot/deploy/kill-switch.sh
# re-arm when ready:
sudo systemctl start ustradebot
```
