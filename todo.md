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

- [x] Fast & slow EMAs (9 / 21). → `bot/indicators.py` `_Ema` (SMA-seeded, k=2/(n+1))
- [x] Trend MA (50) for the higher-timeframe filter. → `_Sma` (`trend_ma`)
- [x] RSI (14). → `_Rsi` (Wilder smoothing)
- [x] Rolling average volume. → `_TrailingMean` (`avg_volume`, trailing/self-exclusive)
- [x] Recompute on each **closed** candle only; unit-test the math.
      → `IndicatorEngine.update` wired to `MarketDataClient(on_candle=...)`;
      `tests/test_indicators.py` (16 tests, hand-checked math)

## Phase 3 — Buy logic + confidence score

- [x] Generalize the indicator engine to a 3-EMA *ribbon* (stacked/sloping helpers)
      and run two: a 1-min 8/10/20 (trigger) and a 5-min 21/34/55 (gate). Needs a
      second, 5-min candle stream alongside the 1-min one. → `Ribbon`/`RibbonEngine`
      in `bot/indicators.py`; dual aggregators in `MarketDataClient`.
- [x] Crossover trigger: fire only on a *fresh* bullish cross in the 1-min ribbon —
      `prev_ema8 ≤ prev_ema10` **and** `ema8 > ema10`, with the full stack
      `ema8 > ema10 > ema20` (detect the cross, not the state).
      → `RibbonSnapshot.fresh_cross`.
- [x] Trend gate: require the 5-min 21/34/55 ribbon stacked bullish (`21 > 34 > 55`,
      rising) before any long; ignore the trigger otherwise.
      → `RibbonSnapshot.gate_open`; enforced in `signals.evaluate_entry`.
- [x] Compute the 5 confidence sub-scores (crossover strength, trend, RSI,
      volume, volatility) and the weighted total (0–100%). → `bot/signals.py`
      (`score_*` + `confidence`/`ScoreWeights`). Volatility = ATR/price proxy
      (no quote feed for a real spread).
- [x] Enter only if `confidence ≥ ENTRY_THRESHOLD` (e.g. 60%). → `evaluate_entry`.
- [x] Market-hours gate: only 09:30–16:00 US Eastern (handle EST/EDT shift in a
      timezone-aware way, not a hardcoded offset). → `signals.market_is_open`
      (zoneinfo America/New_York, Mon–Fri; holidays deferred to Phase 8/10).
- [x] State machine: WAITING → EVALUATING → EXECUTING → MANAGING. → `bot/strategy.py`
      `StrategyEngine`. Phase 3 cycles WAITING↔EVALUATING and emits `TradeSignal`s;
      EXECUTING/MANAGING are reserved for the Phase 4 executor / Phase 5 risk manager.

## Phase 4 — Position sizing + execution

- [x] Implement **Model A** sizing: `alloc_fraction` from confidence →
      `notional = buying_power × alloc_fraction`. → `bot/sizing.py` `plan_model_a`
      (`SIZING_MODEL=A`, default); `alloc_fraction` scales MIN→MAX over the
      confidence range above the threshold.
- [x] (Optional) Implement **Model B**: confidence → fraction of `MAX_RISK_PER_TRADE`
      → shares from the stop distance; cap notional and total exposure. → `plan_model_b`
      (`SIZING_MODEL=B`); risk-budget shares capped by `MAX_ALLOC × buying_power`.
- [x] Submit the entry as an Alpaca **bracket order** (`order_class=bracket`) with
      the stop-loss and take-profit attached. → `bot/executor.py` `OrderExecutor.execute`
      (market entry + `TakeProfitRequest`/`StopLossRequest`, `TimeInForce.DAY`).
- [~] ~~Use **notional** orders for Model A (fractional shares).~~ **Changed:**
      Alpaca rejects brackets on notional/fractional orders, and the broker-side
      bracket (Phase 5) is non-negotiable — so Model A sizes to a dollar notional,
      then **floors to whole shares** at the entry price. Sub-share precision is the
      cost of keeping the bracket.
- [~] Handle order lifecycle: acks, fills, partial fills, rejects. → submit **ack**
      and **reject** handled (`execute` returns `None` + logs on raise/`rejected`);
      **fill / partial-fill** tracking needs the trade-updates stream and is wired
      with persistence in **Phase 6**.
- [~] Reconcile internal state vs Alpaca on startup and after reconnect. → startup
      done (`StrategyEngine.reconcile` marks held watchlist names `MANAGING` so we
      don't double-enter); **post-reconnect** re-reconcile deferred to Phase 5
      (fail-safe on feed loss) where the supervisor loop already lives.

## Phase 5 — Risk management

- [ ] Rely on the bracket's stop/target (they execute broker-side even if the bot
      is down).
- [ ] Add an early-exit on a reversal signal (bearish cross in the 1-min 8/10/20 ribbon).
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
