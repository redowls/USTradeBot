# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Language: Python** (chosen in Phase 0). Stack: `alpaca-py`, `python-dotenv`, `pyodbc`;
`pytest` + `ruff` for dev. **Phases 0–7 are complete** (setup; Alpaca connection/market
data — verified live against the paper account; the indicator engine; the signal +
confidence scorer / state machine; position sizing + bracket-order execution; the risk
manager: early-exit on a 1-min bearish cross + feed-loss fail-safe; persistence: SQL
Server tables for orders/positions/confidence/P&L plus an outcome-vs-confidence view,
verified live against the `USBot` database; and Telegram alerts: a direct `POST` to
`sendMessage` on entry/exit/feed-loss, unit-tested with a fake poster and verified live
against the real Bot API). Phase 8 (run on paper & validate) is next. Build progresses
through the phases in [todo.md](todo.md) (Phase 0 → 10).

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
.venv\Scripts\python.exe -m bot.preflight             # Phase 8 connectivity check (run before a live session)
.venv\Scripts\python.exe -m pytest                    # run all tests
.venv\Scripts\python.exe -m pytest tests/test_config.py::test_loads_defaults  # single test
.venv\Scripts\python.exe -m ruff check .              # lint
.venv\Scripts\python.exe -m ruff format .             # format
```

Commit with the project author (it is not configured globally — set it per commit):

```powershell
git -c user.name=redowls -c user.email=lukitowisley@gmail.com commit -m "..."
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
  (gate). (Phase 5) a stream crash fires `on_feed_lost` and the first tick after reconnect
  fires `on_feed_restored` (latched, idempotent) — the risk manager's feed-loss fail-safe.
  Trading-client and stream factories are injectable so tests run without a network.
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
  `fast_rising`, `gate_open`, `fresh_cross` (a *fresh* bullish cross of fast over mid with the
  full stack above slow), and `bearish_cross` (Phase 5 early-exit: a fresh cross of fast *below*
  mid). **Incremental, not windowed:** EMAs/RSI/ATR are carried forward
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
- [bot/sizing.py](bot/sizing.py) — position sizing + bracket levels (Phase 4), all pure.
  `plan_model_a` (default, `SIZING_MODEL=A`): `alloc_fraction` scales `MIN_ALLOC`→`MAX_ALLOC`
  over the confidence range above the threshold → notional → **floored to whole shares** at
  the entry price. `plan_model_b` (`SIZING_MODEL=B`): risk-budget shares from the stop
  distance, capped by `MAX_ALLOC × buying_power`. Both return a `SizePlan` (qty + bracket
  stop/target via `bracket_prices`) or `None` if it rounds below 1 share. **Whole shares, not
  notional:** Alpaca rejects brackets on notional/fractional orders, so the bracket (required
  for Phase 5's broker-side stop/target) wins over sub-share precision.
- [bot/executor.py](bot/executor.py) — `OrderExecutor` (Phase 4). `execute(symbol, entry_price,
  confidence)` reads the live account (buying power / equity), sizes via `bot.sizing` (model
  per `cfg.sizing_model`), and submits a **market bracket** order (`OrderClass.BRACKET`,
  `TimeInForce.DAY`, `TakeProfitRequest` + `StopLossRequest`). Returns an `ExecutionResult` or
  `None` on a skip/reject/error (swallowed, never kills the strategy). `close_position(symbol)`
  (Phase 5) flattens a holding via Alpaca's `close_position` (which also cancels the live
  bracket) and returns the close order id (or `None` on error). Trading-client factory is
  injectable for tests. Handles the submit **ack + reject**; fill/partial-fill tracking needs
  the trade-updates stream and lands in Phase 6.
- [bot/risk.py](bot/risk.py) — `RiskManager` (Phase 5). Owns an open position. `check_exit`
  (pure) flags a **fresh bearish 1-min cross** (`RibbonSnapshot.bearish_cross` — fast crosses
  *below* mid; deliberately not requiring the full ribbon to invert, so the exit is *early*);
  `exit_position` then flattens via `executor.close_position` and reports an `ExitResult` to
  `on_exit`. The **feed-loss fail-safe** lives here too: `notify_feed_lost`/`notify_feed_restored`
  latch the `entries_allowed` flag and alert via `on_feed_alert` (Phase 7 wires Telegram). The
  bracket's stop/target are still the broker-side backstop — the risk manager only adds the
  discretionary early exit and the new-entry halt.
- [bot/strategy.py](bot/strategy.py) — `StrategyEngine`: the per-symbol `WAITING → EVALUATING
  → EXECUTING → MANAGING` state machine (`BotState`). `on_long_candle` refreshes the gate
  ribbon; `on_short_candle` updates the trigger ribbon, checks market hours, evaluates the
  entry, emits a `TradeSignal` via `on_signal`, then (Phase 4) calls the injected `executor`:
  a qualifying entry drives `EVALUATING → EXECUTING → MANAGING` on a filled bracket, falling
  back to `EVALUATING` on a skip/reject. (Phase 5) a `MANAGING` symbol is risk-managed via the
  injected `risk` manager — a bearish-cross exit flattens it and drops it back to `WAITING` —
  and while `risk.entries_allowed` is `False` (feed down) it opens nothing, staying `WAITING`.
  `reconcile(positions)` marks watchlist names already held at Alpaca as `MANAGING` on startup
  so the bot won't double-enter. An `EXECUTING` symbol is not touched. `on_signal` is where
  Phase 7 hooks Telegram.
- [bot/persistence.py](bot/persistence.py) — SQL Server persistence (Phase 6), all writes
  parameterized. `TradeStore` is the data-access layer: it owns a DB-API 2.0 connection (a
  **pyodbc** factory via `make_pyodbc_factory`, injectable so tests run driverless), runs
  `ensure_schema()` (executes [sql/schema.sql](sql/schema.sql), split on `GO`), and writes
  `record_entry`/`record_exit`. **Persistence is a side-channel, never the trading critical
  path:** every write is wrapped to log + reset the connection on error and swallow it.
  `TradeRecorder` is the glue onto the existing callbacks — it caches the `ConfidenceBreakdown`
  from `on_signal` and pairs it (keyed by symbol — one position per symbol) with the
  `ExecutionResult` from `on_result` so the full sub-score breakdown lands with the entry;
  `on_exit` closes the trade out, with realized P/L computed **in SQL** from the stored entry
  price (the exit prices off the reversal candle's close — no fills stream yet). `open_store(cfg)`
  returns `None` when `SQLSERVER_CONN` is unset or the DB is unreachable (the bot trades on).
- [sql/schema.sql](sql/schema.sql) — idempotent SQL Server DDL (Phase 6): `dbo.trades`
  (round-trip + confidence breakdown + realized P/L, the analytical core), `dbo.orders`
  (append-only submit log), `dbo.positions` (open holdings), `dbo.fills` (reserved for the
  trade-updates stream — created, not yet populated), and `dbo.vw_confidence_outcome` (buckets
  closed trades by confidence band → win rate / avg P/L; answers "do higher-confidence trades
  pay off?"). Single source of truth — the runtime bootstrap executes this same file.
- [bot/notifier.py](bot/notifier.py) — Telegram alerts (Phase 7). `TelegramNotifier.send`
  does a **direct** JSON `POST` to the Bot API's `sendMessage` (stdlib `urllib` — no new
  dependency; the bot token stays in the URL and is never logged); the HTTP `poster` is
  injectable so tests run network-free, and a failed send is logged + swallowed (**alerts
  are a side-channel, never the trading critical path** — same rule as persistence).
  `AlertReporter` is the glue onto the existing callbacks: `on_result` fires the entry alert
  (size + bracket levels + confidence%), `on_exit` fires the exit alert (reason + realized
  P/L — it caches the entry per symbol to compute it, off the same reversal-candle close
  persistence uses), and `on_feed_alert` forwards the risk manager's feed-loss/restore
  message verbatim. `format_entry`/`format_exit` are pure. `open_notifier(cfg)` returns
  `None` if the token/chat id are unset (the bot trades on); config currently *requires*
  both, so it normally returns a live notifier.
- [bot/preflight.py](bot/preflight.py) — Phase 8 preflight connectivity check
  (`python -m bot.preflight`). Runs four checks — Alpaca paper account (**critical**:
  reports status/equity/buying-power/open-positions), SQL Server persistence, Telegram
  alerts (sends a **real** test message), and whether the session is open now (EST/EDT
  aware) — and prints a PASS/WARN/FAIL summary. Exits non-zero only when a *critical*
  check fails; a WARN means a side-channel (DB/Telegram) is off but the trading path is
  ready. Each `check_*` helper takes its dependency directly so they unit-test with fakes;
  `run_preflight` builds them from config in production. Run it before any live session.
- [bot/main.py](bot/main.py) — entrypoint: loads config, sets up logging, checks + reconciles
  the account, opens the `TradeStore`/`TradeRecorder` (Phase 6) and the `TelegramNotifier`/
  `AlertReporter` (Phase 7), builds the `OrderExecutor`, `RiskManager`, and `StrategyEngine`
  — fanning each event to the log sink, the DB recorder, and the Telegram reporter via
  `_chain` — then wires `MarketDataClient(on_candle=…, on_long_candle=…, on_feed_lost=…,
  on_feed_restored=…)` to feed both timeframes and the feed-loss signals through them.
- [tests/](tests/) — pytest suite (one file per `bot/` module).
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
- **Brackets need whole shares.** Alpaca refuses `order_class=bracket` on notional/fractional
  orders. Since the broker-side bracket stop/target is required (Phase 5), sizing computes a
  dollar amount then **floors to an integer `qty`** at the entry price and submits a `qty`
  bracket — never a notional one. Sub-1-share plans are skipped, not rounded up.
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
