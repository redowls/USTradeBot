# Automated Trading Bot — Build Checklist (v2)

Phased to-do for building in VS Code and deploying to the VPS. Everything runs on
the **Alpaca paper account** from the start — no security hardening phase, no
real-capital gate. SQL Server (SSMS) is assumed available.

---

## Phase 0 — Setup

- [x] Choose the language (C#/.NET or Python) and create the repo. → **Python**, pushed to github.com/redowls/USTradeBot
- [x] Set up the VS Code workspace (runtime, linter, debugger). → `.vscode/`, ruff, debugpy
- [x] Create a config layer (env vars or config file) for all tunables. → `bot/config.py`
- [x] Put `ALPACA_KEY_ID`, `ALPACA_SECRET`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
      in env vars (simplest place — you just need them somewhere). → `.env.example` (copy to `.env`)
- [x] Create an Alpaca account and grab the **paper** API keys. → keys in `.env`, verified live (account `PA34DFFLTHRT`)

## Phase 1 — Alpaca connection & market data

- [x] Hit the paper REST endpoint (`paper-api.alpaca.markets`) and confirm the
      account responds. → `MarketDataClient.check_account()` (live: status ACTIVE, equity $10k)
- [x] Open the market-data WebSocket (IEX feed) and subscribe to the watchlist.
      → `MarketDataClient.run_forever()` (live: connected + subscribed to NFLX/BIRD/WPM)
- [x] Auto-reconnect with backoff on dropped connections. → `_BackoffStockDataStream`
      (per-connect backoff) + supervisor restart loop in `run_forever`
- [x] Aggregate ticks/quotes into 1-minute candles per symbol (or subscribe to
      bar data), keeping a rolling window long enough for the indicators.
      → `bot/candles.py` `CandleAggregator` (rolling window, closed-candle only)

## Phase 2 — Indicator engine

- [ ] Fast & slow EMAs (9 / 21).
- [ ] Trend MA (50) for the higher-timeframe filter.
- [ ] RSI (14).
- [ ] Rolling average volume.
- [ ] Recompute on each **closed** candle only; unit-test the math.

## Phase 3 — Buy logic + confidence score

- [ ] Crossover trigger: fire only when `prev_fast ≤ prev_slow` **and**
      `curr_fast > curr_slow` (detect the cross, not the state).
- [ ] Trend filter: require price above the 50-MA.
- [ ] Compute the 5 confidence sub-scores (crossover strength, trend, RSI,
      volume, volatility) and the weighted total (0–100%).
- [ ] Enter only if `confidence ≥ ENTRY_THRESHOLD` (e.g. 60%).
- [ ] Market-hours gate: only 09:30–16:00 US Eastern (handle EST/EDT shift in a
      timezone-aware way, not a hardcoded offset).
- [ ] State machine: WAITING → EVALUATING → EXECUTING → MANAGING.

## Phase 4 — Position sizing + execution

- [ ] Implement **Model A** sizing: `alloc_fraction` from confidence →
      `notional = buying_power × alloc_fraction`.
- [ ] (Optional) Implement **Model B**: confidence → fraction of `MAX_RISK_PER_TRADE`
      → shares from the stop distance; cap notional and total exposure.
- [ ] Submit the entry as an Alpaca **bracket order** (`order_class=bracket`) with
      the stop-loss and take-profit attached.
- [ ] Use **notional** orders for Model A (fractional shares).
- [ ] Handle order lifecycle: acks, fills, partial fills, rejects.
- [ ] Reconcile internal state vs Alpaca on startup and after reconnect.

## Phase 5 — Risk management

- [ ] Rely on the bracket's stop/target (they execute broker-side even if the bot
      is down).
- [ ] Add an early-exit on a reversal signal (e.g. bearish 9/21 cross).
- [ ] Fail safe on feed loss / errors: stop opening new positions and alert.

## Phase 6 — Persistence (SQL Server)

- [ ] Tables for orders, fills, positions, **confidence score per trade**, and P/L.
- [ ] Data-access layer with parameterized queries.
- [ ] Write every entry/exit and its confidence to the DB.
- [ ] A query/view that compares outcome vs confidence band.

## Phase 7 — Telegram alerts (direct, no n8n)

- [ ] Create the bot via **@BotFather**, get the token.
- [ ] Get your chat id (`getUpdates` after messaging the bot).
- [ ] On entry/exit/error, `POST` to
      `https://api.telegram.org/bot<TOKEN>/sendMessage`.
- [ ] Include confidence %, size, and P/L in the messages; test end to end.

## Phase 8 — Run on paper & validate

- [ ] Run the full system live against the Alpaca paper account.
- [ ] Watch entries/exits arrive in Telegram and land in SQL Server.
- [ ] Exercise edge cases: partial fills, rejects, disconnect + reconnect, restart
      mid-trade.
- [ ] Confirm market-hours gating behaves across an EST/EDT boundary.
- [ ] Review logged results and re-tune the confidence weights and threshold.

## Phase 9 — VPS deployment

- [ ] Provision/access the Ubuntu VPS and install the runtime.
- [ ] Deploy the build; supply keys/token via env vars.
- [ ] Configure the process manager — `systemd` (.NET / Python) or `PM2` (Node) —
      to start on boot and auto-restart on crash.
- [ ] Confirm the VPS reaches Alpaca, Telegram, and SQL Server.
- [ ] Set the server clock to UTC and verify the market-hours logic.

## Phase 10 — Monitoring & maintenance

- [ ] Log rotation and a periodic process-health check.
- [ ] A daily/weekly performance summary from SQL Server.
- [ ] A "bot down" / repeated-restart alert.
- [ ] A manual kill switch / flatten-all-positions procedure.

---

### Suggested build order

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10`

Get Alpaca data flowing (1) and indicators correct (2) before the buy logic (3).
Keep it on the paper account throughout — iterate freely.
