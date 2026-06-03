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

- [x] Rely on the bracket's stop/target (they execute broker-side even if the bot
      is down). → unchanged from Phase 4: `OrderExecutor.execute` attaches the
      `TakeProfitRequest`/`StopLossRequest`; the risk manager only adds a
      discretionary early exit on top.
- [x] Add an early-exit on a reversal signal (bearish cross in the 1-min 8/10/20 ribbon).
      → `RibbonSnapshot.bearish_cross` (mirror of `fresh_cross`: fast crosses below
      mid) + `bot/risk.py` `RiskManager.check_exit`/`exit_position`, which flattens
      via `OrderExecutor.close_position` (cancels the live bracket). `StrategyEngine`
      checks it for `MANAGING` symbols and drops them back to `WAITING` on a close.
- [x] Fail safe on feed loss / errors: stop opening new positions and alert.
      → `MarketDataClient` fires `on_feed_lost` on a stream crash and `on_feed_restored`
      on the first tick after reconnect; `RiskManager.notify_feed_lost/restored` latch
      `entries_allowed`, and `StrategyEngine` refuses new entries (stays `WAITING`)
      while down. Alerts go through `on_feed_alert` (Phase 7 wires Telegram).
- [~] Post-reconnect re-reconcile (carried over from Phase 4): the `on_feed_restored`
      seam now exists, but re-reading positions from Alpaca on reconnect is still TODO
      (folds in with the trade-updates stream / persistence in Phase 6).

## Phase 6 — Persistence (SQL Server)

- [x] Tables for orders, fills, positions, **confidence score per trade**, and P/L.
      → `sql/schema.sql`: `dbo.trades` (round-trip + confidence breakdown + realized
      P/L), `dbo.orders` (append-only submit log), `dbo.positions` (open holdings),
      `dbo.fills` (reserved for the trade-updates stream). Idempotent DDL; created
      live on `USBot` (SQL Server 2022).
- [x] Data-access layer with parameterized queries. → `bot/persistence.py`
      `TradeStore` (pyodbc `?` placeholders; injectable connection factory; every
      write swallows + resets on error so the DB is never on the trading critical path).
- [x] Write every entry/exit and its confidence to the DB. → `TradeRecorder` rides the
      existing `on_signal`/`on_result`/`on_exit` callbacks (wired in `bot/main.py` via
      `_chain`); pairs the `ConfidenceBreakdown` from the signal with the entry, and
      computes realized P/L in SQL from the stored entry price on exit.
- [x] A query/view that compares outcome vs confidence band.
      → `dbo.vw_confidence_outcome` (buckets closed trades by confidence band →
      trades/wins/win_rate/avg_pnl/total_pnl). Verified live end-to-end.
- [~] Real fill / partial-fill rows (`dbo.fills`) still need the broker trade-updates
      stream — table created, population deferred (carried with Phase 4's fill-tracking
      TODO). Exits currently price the round-trip off the reversal candle close.

## Phase 7 — Telegram alerts (direct, no n8n)

- [x] Create the bot via **@BotFather**, get the token. → bot **USStockBot**
      (`@USStockWisBot`); token in `TELEGRAM_TOKEN` in `.env`.
- [x] Get your chat id (`getUpdates` after messaging the bot). → `7739672535`
      in `TELEGRAM_CHAT_ID`.
- [x] On entry/exit/error, `POST` to
      `https://api.telegram.org/bot<TOKEN>/sendMessage`. → `bot/notifier.py`
      `TelegramNotifier.send` (direct JSON POST via stdlib `urllib`, injectable
      `poster` for tests; the token stays in the URL, never logged). Errors are
      swallowed — alerts are a side-channel, never the trading path.
- [x] Include confidence %, size, and P/L in the messages. → `format_entry`
      (size + bracket levels + confidence%) / `format_exit` (reason + realized
      P/L from the cached entry). `AlertReporter` rides the executor's `on_result`,
      the risk manager's `on_exit` + `on_feed_alert` (wired in `bot/main.py` via
      `_chain`, alongside the log + DB sinks).
- [x] Test end to end → unit-tested with a fake poster (`tests/test_notifier.py`)
      **and** verified live against the real Bot API (plain + entry + exit messages
      delivered to chat `7739672535`).

## Phase 8 — Run on paper & validate

- [x] **Preflight connectivity check** — `python -m bot.preflight` verifies the three
      external systems in one command (Alpaca paper account = critical, SQL Server +
      Telegram = side-channels) and reports whether the session is open now. Run it
      before any live session. → `bot/preflight.py` (`tests/test_preflight.py`).
- [ ] Run the full system live against the Alpaca paper account. → **operator task**
      (long-running, market hours): `.venv\Scripts\python.exe -m bot.main`.
- [ ] Watch entries/exits arrive in Telegram and land in SQL Server. → **operator task**
      (observe over a live session; signals are infrequent).
- [~] Exercise edge cases: partial fills, rejects, disconnect + reconnect, restart
      mid-trade. → rejects (`test_executor`), disconnect+reconnect / feed-loss
      (`test_market_data`), and restart-mid-trade reconcile (`test_strategy::
      test_reconcile_marks_held_symbols_managing`) are covered by unit tests;
      **partial fills** need the broker trade-updates stream (deferred — see Phase 4/6),
      so there is no code path to exercise yet. Live re-exercise is an operator task.
- [x] Confirm market-hours gating behaves across an EST/EDT boundary. → unit-tested
      (`test_signals::test_market_hours_handle_est_edt_shift`, zoneinfo-based, not a
      hardcoded offset); live confirmation across a real Mar/Nov boundary is an
      operator follow-up.
- [ ] Review logged results and re-tune the confidence weights and threshold. → **operator
      task**: needs real trades in `dbo.trades` / `dbo.vw_confidence_outcome` to tune
      `ScoreWeights` + `ENTRY_THRESHOLD`.

## Phase 9 — VPS deployment

Deployment artifacts are in [`deploy/`](deploy/); the runbook is
[`deploy/DEPLOY.md`](deploy/DEPLOY.md). The on-VPS steps (clone, fill `.env`,
preflight, enable the unit) are **operator tasks** — they need the VPS + secrets.

- [x] Runtime pinned for deploy → `requirements.txt` (`~=` on the tested
      alpaca-py / python-dotenv / pyodbc versions); `deploy/setup.sh` builds the
      venv + installs them + scaffolds `.env` (no-sudo, idempotent).
- [ ] Provision/access the Ubuntu VPS and install the runtime. → **operator task**;
      commands in `deploy/DEPLOY.md` §1–§3 (Python 3.11+, optional msodbcsql18,
      service account, venv).
- [ ] Deploy the build; supply keys/token via env vars. → **operator task**;
      `git clone` + `.env` (0600). The systemd unit loads it via `EnvironmentFile`.
- [x] Configure the process manager (`systemd`) to start on boot + auto-restart on
      crash. → `deploy/ustradebot.service` (`Restart=on-failure`,
      `WantedBy=multi-user.target`, crash-loop cap via `StartLimitBurst`, basic
      hardening). Installing/enabling it is an operator task (§6).
- [ ] Confirm the VPS reaches Alpaca, Telegram, and SQL Server. → **operator task**:
      run `python -m bot.preflight` on the VPS (built in Phase 8); §5.
- [ ] Set the server clock to UTC and verify the market-hours logic. → **operator
      task**: `sudo timedatectl set-timezone UTC` (§4); the gate is EST/EDT-aware off
      UTC (already unit-tested in Phase 8).

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
