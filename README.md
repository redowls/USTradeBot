# USTradeBot

Rule-based US-equity trading bot running against the **Alpaca paper account**. See
[summary.md](summary.md) for the full design and [todo.md](todo.md) for the phased build
plan.

## Stack

Python 3.11+ · [alpaca-py](https://github.com/alpacahq/alpaca-py) · SQL Server (logging) ·
Telegram Bot API (alerts). Runs as a single long-lived process.

## Quick start (development)

```powershell
# 1. Create and activate a virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies (dev includes pytest + ruff)
pip install -r requirements-dev.txt

# 3. Configure
copy .env.example .env   # then fill in ALPACA_* and TELEGRAM_* (paper keys)

# 4. Run the tests and the bot
pytest
python -m bot.main
```

## Commands

| Task            | Command                              |
| --------------- | ------------------------------------ |
| Run the bot     | `python -m bot.main`                 |
| Run tests       | `pytest`                             |
| Single test     | `pytest tests/test_config.py::test_loads_defaults` |
| Lint            | `ruff check .`                       |
| Format          | `ruff format .`                      |

## Status

Phase 0 (setup) complete: project scaffold, env-var config layer, VS Code workspace.
Next: Phase 1 — Alpaca connection & market data.
