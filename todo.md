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

## Phase 9 — VPS deployment ✅ (deployed live)

Deployment artifacts are in [`deploy/`](deploy/); the runbook is
[`deploy/DEPLOY.md`](deploy/DEPLOY.md). **Deployed live to the Ubuntu 24.04 VPS**
(service account `ustradebot`, `/opt/ustradebot`), running as the `ustradebot`
systemd service.

- [x] Runtime pinned for deploy → `requirements.txt` (`~=` on the tested
      alpaca-py / python-dotenv / pyodbc versions); `deploy/setup.sh` builds the
      venv + installs them + scaffolds `.env` (no-sudo, idempotent).
- [x] Provision/access the Ubuntu VPS and install the runtime. → Ubuntu 24.04 +
      Python 3.12 + msodbcsql18 (already present); service account + venv created
      via `deploy/setup.sh`.
- [x] Deploy the build; supply keys/token via env vars. → `git clone` to
      `/opt/ustradebot`; `.env` (0600, owned by `ustradebot`) loaded by the unit via
      `EnvironmentFile`.
- [x] Configure the process manager (`systemd`) to start on boot + auto-restart on
      crash. → `deploy/ustradebot.service` installed + `enable --now`
      (`Restart=on-failure`, `WantedBy=multi-user.target`, crash-loop cap via
      `StartLimitBurst`, basic hardening). Verified `active (running)`, `enabled`.
- [x] Confirm the VPS reaches Alpaca, Telegram, and SQL Server. → `bot.preflight`
      on the VPS: Alpaca **PASS** (account ACTIVE), SQL Server **PASS** (local
      mssql-server on :1433, schema ensured), Telegram **PASS** (test message
      delivered).
- [x] Set the server clock to UTC and verify the market-hours logic. → VPS timezone
      set to UTC (`timedatectl`); the gate converts UTC→Eastern (EST/EDT-aware,
      unit-tested in Phase 8). Preflight confirmed the closed-session reading.

## Phase 10 — Monitoring & maintenance

CLIs in `bot/` (unit-tested), wired to systemd timers/handlers in [`deploy/`](deploy/);
install per [`deploy/DEPLOY.md`](deploy/DEPLOY.md) §8.

- [x] Log rotation and a periodic process-health check. → journald cap
      (`deploy/journald-ustradebot.conf`, `SystemMaxUse=500M`/1-month) for rotation;
      `ustradebot-health.timer` (every 15 min) runs `deploy/healthcheck.sh`, which
      alerts via Telegram only when the unit is `failed` (no maintenance spam).
- [x] A daily/weekly performance summary from SQL Server. → `bot/report.py`
      (`python -m bot.report --days N`): headline trades/win-rate/P&L over the window
      + all-time confidence-band breakdown (reads `dbo.vw_confidence_outcome` via
      `TradeStore.performance_summary`), pushed to Telegram + journal.
      `ustradebot-report.timer` fires it Mon–Fri 21:30 UTC (after the US close).
- [x] A "bot down" / repeated-restart alert. → `OnFailure=ustradebot-down.service`
      on the main unit sends a Telegram alert when the bot crash-loops to `failed`
      (`bot/notify.py` is the generic Telegram CLI it uses).
- [x] A manual kill switch / flatten-all-positions procedure. → `bot/flatten.py`
      (`python -m bot.flatten --yes`: cancel all orders + close all positions, always
      alerts) and the operator wrapper `deploy/kill-switch.sh` (stops the service first,
      then flattens).

---

### Backlog (post-deploy, from daily reviews)

- [ ] **Stale phantom-open cleanup (from 2026-06-17 / IMP-003).** 7 `dbo.trades` rows are
      `status='OPEN'` from 06-11/06-12 (ENPH, WPM, NFLX, TSLA, QCOM, INTC, AMD) but the broker
      holds **0** positions — they were stopped out broker-side before IMP-003 recorded such
      fills. One-off: for each, pull its actual exit fill from Alpaca `/v2/orders` history and
      UPDATE OPEN→CLOSED (match on entry_time). They inflate the report's "open positions"
      count but don't affect closed-trade stats. IMP-003 prevents new ones.
- [ ] **Late-day / low-conviction entry quality (watch).** 2026-06-17: TSLA (conf 61, at the 60
      gate) and MU (entered 19:07, ~1h before close) both went straight to their stops. Consider
      a time-of-day entry cutoff and/or a higher entry gate — needs more days of data first.
- [ ] **Confidence is inverted above ~70 — the next entry-filter candidate.** All-time bands:
      90–100 = 3 tr / 0% win / −$144.42; 80–89 = 28 tr / 46% / −$13.10; **70–79 = 82 tr / 54% /
      +$221.99**; 60–69 = 141 tr / 42% / −$87.27. The 70–79 band is the *only* profitable one and
      60–69 is the biggest and negative. Deferred 2026-08-05 because IMP-022 is itself an entry
      filter and will cut trade count ~40% — stacking two would make both unmeasurable. **Revisit
      once IMP-022 has a full week (≥ 2026-08-12).**
- [~] ~~**Flat non-ATR stop.**~~ **Downgraded 2026-08-05 — the premise was wrong.** Carried since
      IMP-018 on the reasoning that a flat 1.25% trail is absurd across SPY (1.17% *daily* ATR) to
      MU (10.73%). But the trail is faced against the **1-minute** ATR, and `score_volatility`
      (ATR/price, `_ATR_GOOD` 0.20% → `_ATR_BAD` 1.00%) is *itself* an ATR filter that only admits
      names in a narrow 1-min-ATR band. Measured on 2026-08-05: MU 1-min ATR ≈ $2.07 (0.224% of
      price) and INTC ≈ $0.246 (0.244%) — the trail is **≈5.6× and ≈5.1× the 1-min ATR**
      respectively, i.e. already near-normalised. Re-derive the premise before spending a session.
- [~] ~~**Tune `STOP_LOSS` (2%).**~~ **Dead knob — do not spend a session on it.** Since IMP-018 the
      trail seeds at the bracket stop and ratchets whenever `close × (1 − TRAIL_PERCENT)` clears
      it, which happens as soon as price trades above ≈ **−0.76%** from entry. The trail is
      therefore always the binding constraint and the −2% stop effectively never fills (all 3
      exits on 2026-08-05 were trail fills). Not a defect — the trail is strictly tighter, so this
      is more protective, not less — but changing `STOP_LOSS` is a no-op.
- [ ] **Whole-share quantisation wrecks Model A sizing on high-priced names.** 2026-08-05: MU sized
      to **qty 1 = $924** against $36k buying power. On a $900+ stock the floor-to-integer step is
      ~10% of a typical position, so the confidence→size curve barely functions for MU / AVGO /
      TSM / MSFT / NFLX. Cannot be fixed in sizing alone — Alpaca refuses brackets on fractional
      orders — so any fix is structural. Needs its own study.
- [ ] **⚠️ OPERATOR: the pre-market / post-close routine scaffold is failing.** 08-03 pre-market
      died rc=1, the 08-04 post-close routine never ran, and the 08-05 pre-market never ran. Real
      consequence: **AMD was parked 08-04 for earnings and never re-enabled**, so the watchlist ran
      a session at 19 names instead of 20. The scaffold is `/root/claude-routines`, outside this
      repo. Three misses in three sessions is a pattern, not a model blip.
- [ ] **⚠️ RISK — needs human approval, do NOT self-authorise.** IMP-022 makes the bot decline to
      trade a falling tape, which is capital protection. The *symmetric* idea — taking the short
      side when the gate is inverted — would give the book a second direction and is the only
      obvious route out of "long beta". It is a materially different risk profile (shorting,
      borrow, unbounded loss) and is **explicitly out of scope for an unattended routine.**
      Proposing it here only.

---

### Suggested build order

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10`

Get Alpaca data flowing (1) and indicators correct (2) before the buy logic (3).
Keep it on the paper account throughout — iterate freely.
