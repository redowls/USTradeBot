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
- [x] **DONE — IMP-028, commit `da161c7`, deployed 2026-08-14 21:15 UTC — retry `record_entry` once
      after `_reset()`.** Shipped with an idempotency guard: the bracket is looked up by its unique
      Alpaca `entry_order_id` before re-inserting, so a failure raised *by* `commit()` (where the
      transaction may have landed anyway) cannot double-count the position. 363 tests pass.
      ⚠️ **The "apply the same to `record_exit`" half of this item is NOT done — carried below.**
- [ ] **🔴 NEXT UP — IMP-029: make the trailing stop ATR-relative instead of a flat percent.**
      The exit structure cannot hold a trend. 2026-08-14 evidence: AMD closed **+6.5% at the high**
      on a flat index; walked bar-by-bar against the live rules, an entry at ~$503 peaks at $511.29,
      IMP-021 tightens the trail to 1.00% → $506.18, and the very next 5m bar (low $504.60) takes it
      out for **+0.63%** of a **+2.4%** available move. **A 1.00% trail on a 7.32%-ATR name is ~1/7
      of a daily range — ordinary noise.** MU (8.16% ATR) is worse. Lifetime exit-reason data agrees:
      trades left alone to the close are **176 for +$1,125 (+0.38% avg)**, while every stop-based
      path loses (broker-side stop/target **46 for −$417.56**, trailing stop **2 for −$54.69**,
      −1.53% avg). ⚠️ Partly selection — do **not** read it as "remove the stops". **Gate: must be
      validated on `bot/replay.py` across ≥3 windows before shipping.** The −2% hard stop, position
      sizing and all risk limits stay untouched; this changes only how profit is trailed, so max
      loss per trade does not increase. This is the long-open "flat non-ATR stop" item.
- [ ] **🟠 IMP-030 candidate — confidence is anti-predictive above 80 and unprofitable below 70.**
      `vw_confidence_outcome` over 266 trades: **60-69: 146 tr, 41.8% win, −$58.22** · **70-79:
      87 tr, 54.0% win, +$250.84 (the only profitable band)** · **80-89: 30 tr, −$26.75** ·
      **90-100: 3 tr, 0% win, −$144.42 (−1.51% avg)**. The score is non-monotonic and its top end is
      actively harmful, which also means `MIN_CONFIDENCE=60` is buying trades from the worst cohort.
      Related: all 15 retained market-gate refusals since 08-03 sit at **conf ≥ 69.1** — the gate is
      preferentially vetoing the one band that makes money. **Do not stack this on IMP-029 in the
      same session**; land the exit work and measure it first.
- [ ] **🟡 The QQQ market gate (IMP-022) blocks idiosyncratic single-name trends.** 2026-08-14: AMD
      scored **76.5** and **91.2** (the day's two best signals) and was vetoed twice because QQQ's 5m
      ribbon was not bullish on a −0.15% index day. Real, but **quantified at ≈0.6% of missed P&L**,
      i.e. second-order next to the exit problem. Revisit only after IMP-029 and IMP-030.
- [ ] **🟠 Apply IMP-028's one-retry treatment to `record_exit`.** A dead socket on the exit write
      still loses the close of a trade the broker really flattened, leaving `dbo.trades` with a
      permanently OPEN row. Same shape, same fix, needs its own idempotency key (the exit order id).
      Original 2026-08-12 context: the MU entry INSERT hit
      a stale socket (`pyodbc.OperationalError 08S01 — TCP Provider 0x20`), `record_entry` logged,
      returned `None` and **did not retry**; the exit then had no `trade_id` (`DB exit MU
      trade_id=None`), so **both legs were lost and the whole winning trade is absent from
      `dbo.trades`** — `bot.report --days 1` reports a blank day that was not blank. IMP-019 added
      `_reset()`-on-error so the *next* write reconnects, but nothing re-drives the failed one, and
      the connection was healthy 12 s later (every later DB call that session succeeded). One retry
      after `_reset()` recovers this exact case. Apply the same to `record_exit`.
- [ ] **Post-close DB⇄broker reconciliation assert.** Both 08-12 defects (the above, and IMP-027's
      stale-fill attribution) were invisible to every automated surface and were caught only because
      the daily-review routine queried Alpaca by hand. Compare the day's broker fills against
      `dbo.trades` at the close and alert on any mismatch — count, qty, or fill price. Would have
      paged at 18:26 instead of being found at 21:15. **Good weekly-review candidate.**
- [ ] **Price the crossover floor (`MIN_CROSSOVER=0.25`) — now overdue.** The busiest filter in the
      book and the largest never-A/B'd one: 13 refusals on 08-12 (four at conf 69–74, INTC missing by
      **0.01**), 7 on 08-11. The IMP-022 entry freeze expired with the 08-12 session, so the analysis
      is unblocked: replay 0.20 / 0.25 / 0.30 across ≥3 windows and price the refusals directly.
- [ ] **⚠️ RISK — needs human approval, do NOT self-authorise.** IMP-022 makes the bot decline to
      trade a falling tape, which is capital protection. The *symmetric* idea — taking the short
      side when the gate is inverted — would give the book a second direction and is the only
      obvious route out of "long beta". It is a materially different risk profile (shorting,
      borrow, unbounded loss) and is **explicitly out of scope for an unattended routine.**
      Proposing it here only.
- [ ] **Free the remaining 35 points of dead weight in the confidence score (follow-on to
      IMP-034).** `conf_rsi` is 1.00 on **252/268** live trades (mean 0.979) and
      `conf_volatility` on **174/268** (mean 0.958), so ~34 of 100 points are a constant
      subsidy handed to every candidate and `ENTRY_THRESHOLD=60` is really asking for ~26 of
      ~65 varying points. **Do not simply zero them like IMP-034 did to volume:** `conf_rsi`
      reaches 0.0 on overbought (RSI ≥ 70), so it is doing **veto** work, not ranking work,
      and dropping its weight would delete that veto. The right experiment is to **re-express
      both as explicit boolean gates** (refuse if RSI ≥ 70; refuse if ATR/close ≥ `_ATR_BAD`)
      and hand their 35 points to crossover and trend — measured in replay across ≥3 windows,
      gate ON, against the IMP-034 baseline. **Blocked until IMP-034 has live evidence — one
      scoring change at a time.**
- [x] **DONE (IMP-035, 2026-08-25) — `--days N` is a rolling timestamp, not a calendar
      boundary.** All three readers now cut at
      `CAST(DATEADD(day, -(? - 1), SYSUTCDATETIME()) AS DATE)` behind one shared
      `_WINDOW_START_SQL`, plus a `_window_days` clamp for N < 1. Measured before shipping:
      at the 11:30 UTC pre-market slot `--days 1` returned **68** refusals against a true
      **36**, and `--days 5` returned **118** against **91**; at the post-close slot both
      forms agreed, which is why it hid for months. 442 tests. **Windows are reproducible
      from 2026-08-25 on; earlier windowed counts written from a non-21:10 slot are
      approximate and should not be retro-corrected.**

- [ ] **`MIN_CROSSOVER` and `ENTRY_THRESHOLD` may now be largely redundant — measure, do
      not loosen.** On 2026-08-25, **16 of 36 refusals cleared confidence ≥ 60 (60.6–70.2)
      and died on the 0.25 crossover floor**. That follows mechanically from IMP-034 raising
      `crossover` to 39 of the ~65 *live discriminating* points (`conf_rsi` and
      `conf_volatility` are near-constant, contributing a ~34.5-point floor to every
      candidate), so the floor may be double-counting the score's largest term. **This is a
      merge/simplify question, not a loosen question** — the pooled 7-day window says both
      currently decline the same garbage (crossover cohort n=67, avgFwd −0.11%, 3/67 reach
      the trail). **Sequence: measure only *after* the rsi/volatility change above, which
      moves the very weights the redundancy is computed from.**

- [ ] **`conf_rsi` is the last dead-weight term — and any fix MUST be threshold-neutral.**
      `conf_rsi` scored **1.00 on 47/47 refusals on 2026-08-26** (fourth consecutive
      session) and on **252 of 269 trades**, so its 20 points are a flat subsidy handed to
      every candidate that reaches scoring. It is a **de-facto veto wearing a ranking
      term's clothes** — it only leaves 1.00 above RSI 65 and only hits 0.0 at RSI ≥ 70.
      **IMP-036 refuted the naive fix by arithmetic:** redistribute the points
      proportionally to crossover/trend and hold `ENTRY_THRESHOLD` at 60, and
      2026-08-26's PLTR entry scores **59.8 against a 60 bar** — the only trade of that
      day, killed for a reason unrelated to its merits. Removing a ~constant subsidy while
      holding the threshold silently moves the effective bar from **~38.5% to 60%** of the
      discriminating range. **IMP-034's renormalise-to-100 logic does not transfer to a
      term that sits at full marks.** Any version must move `ENTRY_THRESHOLD` **60 → ~38.5**
      in the same change, or convert `conf_rsi` to an explicit RSI ≥ 70 veto and re-derive
      the bar. **Blocked until IMP-036 has live fills to judge it against.**

- [ ] **IMP-036 pre-registered revert test (owner: whoever reviews ~15 fills after
      2026-08-26).** IMP-036 reversed the volatility sub-score's sign; replay net dollars
      **fell 4–12% in 5 of 6 windows** while win rate, PF and per-trade P&L rose in all
      six. It was shipped on the argument that the removed cohort is **+$1.35/trade in
      simulation but −$2.04/trade in the live record**, the gap being execution. **If over
      the next ~15 fills the retained trades do not show BOTH a better win rate AND a
      better per-trade P&L than the pre-IMP-036 book, revert it.** No new instrumentation
      needed — `conf_volatility` is still computed and persisted on every entry and refusal.

---

### Suggested build order

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10`

Get Alpaca data flowing (1) and indicators correct (2) before the buy logic (3).
Keep it on the paper account throughout — iterate freely.
