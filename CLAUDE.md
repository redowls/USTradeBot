# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Language: Python** (chosen in Phase 0). Stack: `alpaca-py`, `python-dotenv`; `pytest` +
`ruff` for dev. **Phases 0–3 are complete** (setup; Alpaca connection/market data —
verified live against the paper account; the indicator engine; and the signal +
confidence scorer / state machine). Phase 4 (position sizing + bracket-order execution)
is next. Build progresses through the phases in [todo.md](todo.md) (Phase 0 → 10).

**Strategy note:** the entry design is a **multi-timeframe triple-MA ribbon** — a
1-minute **8/10/20** EMA ribbon is the *trigger*, gated by a 5-minute **21/34/55** EMA
ribbon (see [summary.md](summary.md)). This is implemented as of Phase 3: `RibbonEngine`
runs two instances (1-min trigger, 5-min gate) off two `CandleAggregator`s on the same
trade stream. The earlier single-timeframe 9/21 + 50-MA config has been removed.

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
  the IEX trade WebSocket, feeds each tick into **two** `CandleAggregator`s (the trigger
  interval and the longer gate interval) and reconnects with backoff (`_BackoffStockDataStream`
  + a supervisor loop). Closed candles fan out to `on_candle` (trigger) and `on_long_candle`
  (gate). Trading-client and stream factories are injectable so tests run without a network.
- [bot/candles.py](bot/candles.py) — `CandleAggregator`: rolls **trade** ticks (we aggregate
  ourselves rather than subscribing to Alpaca's minute bars) into fixed-interval OHLCV
  `Candle`s per symbol (interval set per instance — 60s and 300s), keeps a bounded rolling
  window, and only ever emits **closed** candles. Pure / no I/O. **Close timing is
  activity-driven:** `flush(now)` uses the freshest incoming tick's timestamp as the clock, so
  a bar closes only when a later tick proves its interval elapsed — an idle market leaves the
  last bar open until the next tick. Don't assume a bar closes the instant its interval ends.
- [bot/indicators.py](bot/indicators.py) — ribbon indicator engine (Phase 2 → 3). `RibbonEngine`
  maintains one 3-EMA `Ribbon` per symbol over one timeframe; `update(candle)` returns a
  `RibbonSnapshot`. Build the two instances via `RibbonEngine.trigger(cfg)` (short ribbon +
  Wilder RSI(14) + trailing `avg_volume` + ATR(14)) and `RibbonEngine.gate(cfg)` (long ribbon
  only). The snapshot exposes the strategy helpers: `stacked`, `sloping_up`/`bullish`,
  `fast_rising`, `gate_open`, and `fresh_cross` (a *fresh* bullish cross of fast over mid with
  the full stack above slow). **Incremental, not windowed:** EMAs/RSI/ATR are carried forward
  from inception so they don't drift as bars age out of the aggregator window; each field is
  `None` until seeded (`ribbon_ready` once the ribbon and its `prev` are filled). `avg_volume`
  is the mean of the *preceding* bars (current bar excluded). Pure / no I/O, per-symbol state.
- [bot/signals.py](bot/signals.py) — signal + confidence scorer (Phase 3), all pure. Candidacy
  is the hard `gate_open AND fresh_cross` rule; `confidence()` blends five 0–1 sub-scores
  (`score_crossover` 30, `score_trend` 20, `score_rsi` 20, `score_volume` 15, `score_volatility`
  15 via `ScoreWeights`) into a 0–100 total. `evaluate_entry()` returns an `EntryDecision`
  (candidate? scored? enter?). `market_is_open()` converts UTC → US Eastern (zoneinfo, EST/EDT
  safe, Mon–Fri). Volatility is an **ATR/price proxy** — the IEX trade feed gives no bid/ask
  spread. Weights/thresholds are module constants, meant to be tuned on paper (Phase 8).
- [bot/strategy.py](bot/strategy.py) — `StrategyEngine`: the per-symbol `WAITING → EVALUATING
  → EXECUTING → MANAGING` state machine (`BotState`). `on_long_candle` refreshes the gate
  ribbon; `on_short_candle` updates the trigger ribbon, checks market hours, evaluates the
  entry, and emits a `TradeSignal` via `on_signal` when confidence clears the threshold.
  **Phase 3 stops at the signal** — there's no executor, so it cycles WAITING↔EVALUATING;
  `EXECUTING`/`MANAGING` are reserved for the Phase 4 executor / Phase 5 risk manager, and
  `on_signal` is where Phase 7 hooks Telegram.
- [bot/main.py](bot/main.py) — entrypoint: loads config, sets up logging, checks the account,
  builds the `StrategyEngine`, then wires `MarketDataClient(on_candle=…, on_long_candle=…)` to
  feed both timeframes through it.
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
3. **Indicator engine** — dual-timeframe EMA ribbons: a 1-min **8/10/20** trigger ribbon
   and a 5-min **21/34/55** gate ribbon, plus RSI(14) and rolling avg volume on the 1-min
   series. Recompute **only on closed candles** (acting on the live candle causes repainting).
4. **Signal + confidence scorer** — see invariants below.
5. **Order executor** — confidence → size (Model A or B), submit as Alpaca bracket order.
6. **Risk manager** — broker-side stop/target via the bracket; early-exit on reversal
   (bearish cross in the 1-min 8/10/20 ribbon); fail-safe (stop opening positions + alert)
   on feed loss.
7. **Persistence** — SQL Server tables for orders, fills, positions, **confidence per
   trade**, and P/L; parameterized queries.
8. **Telegram alerts** — direct `POST` to `sendMessage` on entry/exit/error.

## Domain invariants (easy to get wrong — enforce these)

- **Crossover = the cross, not the state.** The entry *trigger* is a fresh bullish cross in
  the **1-min 8/10/20** ribbon: `prev_ema8 ≤ prev_ema10` AND `ema8 > ema10`, with the full
  stack `ema8 > ema10 > ema20`. Checking the stacked state alone re-fires every candle while
  above.
- **Closed candles only.** Never evaluate or trade off the still-forming current candle.
- **Multi-timeframe gate + trigger.** A long is allowed only when the slower **5-min
  21/34/55** ribbon is `gate_open` (stacked `21 > 34 > 55` and rising) *and* the 1-min trigger
  fires. The gate is a standing filter, never an independent trigger; RSI/volume/volatility are
  confirmation folded into the score. This supersedes the original single-timeframe 9/21-cross
  + 50-MA filter; the old `cross OR RSI<30` rule (mixing trend-following and mean-reversion) is
  still rejected.
- **Ribbon = stacked AND sloping.** A ribbon counts as bullish only when ordered
  (`fast > mid > slow`) *and* sloping up (EMAs rising, gaps widening) — a flat, intertwined
  ribbon scores low even if the order is technically right.
- **Confidence = Σ(sub_score × weight)** over 5 components (crossover strength 30 = 1-min
  ribbon spread/slope; trend 20 = 5-min ribbon stacking/slope; RSI 20; volume 15;
  volatility 15); enter only if `confidence ≥ ENTRY_THRESHOLD` (~60). This is a heuristic
  ranking, **not** a probability of profit.
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
already enforces several domain invariants below (paper endpoint, ribbon period ordering
`fast<mid<slow`, gate interval longer than the trigger interval, alloc bounds) — keep new
invariants there too. The ribbons are configured as `SHORT_MA_PERIODS`/`LONG_MA_PERIODS`
(3 EMAs each) and `CANDLE_INTERVAL`/`LONG_CANDLE_INTERVAL` (parsed to seconds).

## Deployment

Ubuntu VPS, started on boot and auto-restarted on crash via `systemd`. The VPS must reach
Alpaca, Telegram, and SQL Server.
