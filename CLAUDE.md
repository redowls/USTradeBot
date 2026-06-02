# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Language: Python** (chosen in Phase 0). Stack: `alpaca-py`, `python-dotenv`; `pytest` +
`ruff` for dev. **Phases 0–1 are complete** (setup + Alpaca connection/market data, both
verified live against the paper account); Phase 2 (indicator engine) is next. Build
progresses through the phases in [todo.md](todo.md) (Phase 0 → 10).

Source-of-truth documents — read both before writing code:

- [summary.md](summary.md) — the full system design (architecture, buy logic, confidence
  scoring, position sizing, integrations, config parameters).
- [todo.md](todo.md) — the phased build checklist. Check off items as you complete them.

Per the user's workflow: commit per logical chunk, **push to GitHub at the end of each
phase** (remote: `github.com/redowls/USTradeBot`, branch `main`). Git author is
`redowls <lukitowisley@gmail.com>` (set via `-c` on commit; not configured globally).

## Commands

```powershell
.\.venv\Scripts\Activate.ps1                          # activate venv (Windows dev)
.venv\Scripts\python.exe -m bot.main                  # run the bot
.venv\Scripts\python.exe -m pytest                    # run all tests
.venv\Scripts\python.exe -m pytest tests/test_config.py::test_loads_defaults  # single test
.venv\Scripts\python.exe -m ruff check .              # lint
.venv\Scripts\python.exe -m ruff format .             # format
```

Run via the venv interpreter directly (`.venv\Scripts\python.exe`) — the global `python`
is 3.14 and not the project env. Tests stub the environment with `monkeypatch` and call
`Config.load(dotenv=False)`, so they never touch the real `.env`.

Tooling config lives in [pyproject.toml](pyproject.toml): target is **Python 3.11+**, ruff
`line-length = 100` with rules `E,F,I,B,UP`, and pytest runs against `tests/` with `-q`.

## Code layout

- [bot/config.py](bot/config.py) — env-var config layer. `Config.load()` reads, type-parses,
  validates, and freezes all tunables/secrets once at startup. **All config flows through
  here** — don't read `os.environ` elsewhere. Secrets use `field(repr=False)`.
- [bot/market_data.py](bot/market_data.py) — data ingestion (Phase 1).
  `MarketDataClient.check_account()` hits the paper REST endpoint; `.run_forever()` holds
  the IEX trade WebSocket, feeds ticks to the aggregator, and reconnects with backoff
  (`_BackoffStockDataStream` + a supervisor loop). Trading-client and stream factories are
  injectable so tests run without a network.
- [bot/candles.py](bot/candles.py) — `CandleAggregator`: rolls trade ticks into 1-minute
  OHLCV `Candle`s per symbol, keeps a bounded rolling window, and only ever emits **closed**
  candles (`flush(now)` closes a bar once its minute has fully elapsed). Pure / no I/O.
- [bot/main.py](bot/main.py) — entrypoint: loads config, sets up logging, checks the
  account, then runs the data stream. The `WAITING → EVALUATING → EXECUTING → MANAGING`
  state machine will live here.
- [tests/](tests/) — pytest suite.
- `.env` (gitignored, holds real paper keys) ← copy from [.env.example](.env.example).

## What this is

A single long-lived, rule-based US-equity trading bot. It holds a WebSocket to Alpaca's
market-data feed, aggregates ticks into 1-minute candles, computes indicators on each
**closed** candle, scores a potential entry as a 0–100% confidence value, sizes the
position by that confidence, and submits **bracket orders** to Alpaca's **paper** account.
It runs on an Ubuntu VPS, logs to SQL Server, and pushes alerts directly to the Telegram
Bot API (no n8n). It is deterministic — a state machine over `WAITING → EVALUATING →
EXECUTING → MANAGING`.

## Architecture (the pipeline)

```
Alpaca WebSocket → Data Ingestion → Candle Aggregator → Indicator Engine
                                                              → Signal + Confidence Score
                                                              → Order Executor (size by conf.)
                                                              → Risk Manager (stop/target)
                                                              → Alpaca REST (paper) + SQL Server
                                                              → Telegram Bot API
```

Discrete components to build (each is a `todo.md` phase):

1. **Data ingestion** — Alpaca paper REST + market-data WebSocket (free tier = IEX feed),
   auto-reconnect with backoff, reconcile positions against Alpaca on startup and after
   every reconnect.
2. **Candle aggregator** — roll ticks/quotes into 1-minute bars per symbol, keep a rolling
   window long enough for the indicators.
3. **Indicator engine** — 9/21 EMAs, 50-MA trend filter, RSI(14), rolling avg volume.
   Recompute **only on closed candles** (acting on the live candle causes repainting).
4. **Signal + confidence scorer** — see invariants below.
5. **Order executor** — confidence → size (Model A or B), submit as Alpaca bracket order.
6. **Risk manager** — broker-side stop/target via the bracket; early-exit on reversal
   (bearish 9/21 cross); fail-safe (stop opening positions + alert) on feed loss.
7. **Persistence** — SQL Server tables for orders, fills, positions, **confidence per
   trade**, and P/L; parameterized queries.
8. **Telegram alerts** — direct `POST` to `sendMessage` on entry/exit/error.

## Domain invariants (easy to get wrong — enforce these)

- **Crossover = the cross, not the state.** Enter only when `prev_fast ≤ prev_slow` AND
  `curr_fast > curr_slow`. Checking `fast > slow` alone re-fires every candle while above.
- **Closed candles only.** Never evaluate or trade off the still-forming current candle.
- **MA crossover is the trigger; RSI/trend/volume/volatility are confirmation**, folded
  into the confidence score — they are *not* independent entry triggers (the original
  `cross OR RSI<30` rule mixed trend-following and mean-reversion and is rejected).
- **Confidence = Σ(sub_score × weight)** over 5 components (crossover strength 30, trend 20,
  RSI 20, volume 15, volatility 15); enter only if `confidence ≥ ENTRY_THRESHOLD` (~60).
  This is a heuristic ranking, **not** a probability of profit.
- **Position sizing** — Model A (`notional = buying_power × alloc_fraction`, where
  `alloc_fraction` scales from `MIN_ALLOC` to `MAX_ALLOC` over the confidence range above
  the threshold) is the default; Model B (risk-budget / stop-distance) is optional and must
  cap both per-position notional and total open exposure.
- **Paper account only.** Always use `https://paper-api.alpaca.markets`. Never wire the live
  endpoint.
- **Timezone.** Run the server clock on UTC; convert to US Eastern for the 09:30–16:00
  market-hours gate. Handle EST/EDT daylight-saving shift in a timezone-aware way — never
  hardcode a single UTC offset.

## Configuration & secrets

All tunables are read from environment variables via [bot/config.py](bot/config.py)
(loaded from `.env` in dev through `python-dotenv`; set directly in the environment on the
VPS). Add a new tunable by extending the `Config` dataclass and its `load()`/`validate()` —
never scatter `os.environ` reads. Secrets (`ALPACA_KEY_ID`, `ALPACA_SECRET`,
`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`) stay in `.env`, which is gitignored. The watchlist is
a fixed list (`NFLX, BIRD, WPM`); a dynamic scanner is explicitly deferred. `validate()`
already enforces several domain invariants below (paper endpoint, MA ordering, alloc
bounds) — keep new invariants there too.

## Deployment

Ubuntu VPS, started on boot and auto-restarted on crash via `systemd`. The VPS must reach
Alpaca, Telegram, and SQL Server.
