# Automated Trading Bot — System Summary (v2)

A continuously running, rule-based trading bot that pulls real-time US equity
data from **Alpaca**, evaluates technical signals, scores each potential entry
with a **confidence percentage**, sizes the position according to that
confidence, and submits orders through Alpaca's **paper** account. It runs
autonomously on an Ubuntu VPS, logs activity to SQL Server, and pushes trade
alerts **directly to Telegram** (no n8n).

The bot is deterministic: it reacts to live data against fixed rules, behaving as
a state machine that moves between *waiting → evaluating → executing → managing*.

---

## System Architecture

A single long-lived process holds a WebSocket connection to Alpaca's market-data
feed. Ticks are aggregated into candles on **two timeframes** — 1-minute (entry
timing) and 5-minute (trend context) — which feed an indicator engine that
maintains an EMA **ribbon** on each. The indicators feed a **signal + confidence
scorer**. If confidence clears the threshold, the order executor sizes and submits
the trade; once a position is open, the risk manager owns it until close. Events
are written to SQL Server and pushed straight to Telegram.

```
Alpaca WebSocket ──► Data Ingestion ──► Candle Aggregator ──► Indicator Engine
                                                                     │
                                                                     ▼
                                                       Signal + Confidence Score
                                                                     │
                                              ┌──────────────────────┤
                                              ▼                      ▼
                                        Order Executor         Risk Manager
                                        (size by conf.)        (stop / target)
                                              │                      │
                                              ▼                      ▼
                                      Alpaca REST (paper)      SQL Server (logs)
                                              │                      │
                                              └──────────┬───────────┘
                                                         ▼
                                              Telegram Bot API (direct)
```

---

## The Core Bot Loop

**1. Selection.** The bot subscribes only to a fixed watchlist (e.g. `NFLX`,
`BIRD`, `WPM`). A market scanner can be added later; a fixed list keeps early
behavior predictable.

**2. Evaluation.** Real-time data arrives over the Alpaca WebSocket and is
aggregated into 1-minute **and** 5-minute candles. On each **closed** candle the
indicator engine updates the relevant EMA ribbon (plus RSI and volume on the
1-minute series). The 5-minute **21/34/55** ribbon defines the trend *gate*; a
fresh bullish cross in the 1-minute **8/10/20** ribbon is the entry *trigger*.
When both align, the scorer produces a confidence score (below).

**3. Execution.** If confidence ≥ the entry threshold, the bot sizes the position
from the confidence score and submits the order to Alpaca — preferably as a
**bracket order** that attaches the stop-loss and take-profit at entry.

**4. Risk Management.** With a bracket order, the stop and target live broker-side
and execute even if the bot disconnects. The bot still monitors for a reversal
signal (a bearish cross in the 1-minute 8/10/20 ribbon) to exit early.

---

## Buy Logic — Review & Improvements

The original rule was: *enter if the 9-MA crosses the 21-MA **OR** RSI < 30.*
That works as a starting point but has weaknesses worth fixing:

1. **The OR mixes two opposite philosophies.** A 9/21 bullish crossover is
   *trend-following* (buy strength); RSI < 30 is *mean-reversion* (buy weakness).
   They often fire at opposite moments, so OR-ing them produces conflicting,
   noisy entries. Fix: make the MA crossover the **trigger** and use RSI, trend,
   and volume as **confirmation/scoring** rather than an independent trigger.
2. **Detect the *cross*, not the *state*.** Buy only when `prev_fast ≤ prev_slow`
   **and** `curr_fast > curr_slow`. Checking only `fast > slow` re-fires on every
   candle while it stays above.
3. **Act on closed candles only.** The current candle's values change until it
   closes; acting early causes repainting / phantom signals.
4. **Filter with a higher-timeframe trend.** Taking a cross *against* the larger
   trend gets chopped up. Gate entries on a slower **5-minute 21/34/55 EMA ribbon**
   that must be stacked bullishly (`21 > 34 > 55`, rising) before any long is allowed.
5. **Confirm with volume.** Crossovers on thin volume are unreliable; favor
   volume above its recent average.
6. **Don't buy a falling knife on RSI.** Instead of "RSI < 30," prefer "RSI
   *crossing back up* through 30" (oversold turning), or treat the 45–65 zone as
   healthy momentum. Penalize overbought (> 70).
7. **Use EMAs over SMAs on 1-minute data** to reduce lag/whipsaw (optional).

The resulting entry is **multi-timeframe**: a slow ribbon gates the trend, a fast
ribbon times the cross, and RSI/volume/volatility confirm — all rolled into a
single confidence score. The concrete rules follow.

---

## Entry Logic — Multi-Timeframe Triple-MA Ribbon

Two EMA **ribbons** (three EMAs each) on two timeframes. A ribbon counts as
"bullish" only when it is both **stacked** (`fast > mid > slow`) and **sloping up**
(each EMA above its prior value, the gaps widening) — a stacked-but-flat tangle,
where the three EMAs are glued together, scores low.

**Gate — 5-minute 21 / 34 / 55 (a *state*, not a trigger).** Evaluated on the
latest closed 5-minute candle:

```
gate_open = ema21 > ema34 > ema55  AND  ema21 rising
```

If the gate is closed, no long is allowed and the 1-minute trigger is ignored. The
gate is a standing filter; it never fires an entry on its own.

**Trigger — 1-minute 8 / 10 / 20 (the *cross*).** Evaluated only when the gate is
open, comparing this closed 1-minute candle to the previous one:

```
fresh_cross = prev_ema8 ≤ prev_ema10          # was not yet bullish
          AND ema8 > ema10                     # now bullish
          AND ema8 > ema20 AND ema10 > ema20   # full stack above the slow anchor
```

The `prev ≤` term makes this fire **once** per cross, not every candle the ribbon
stays stacked. Requiring the **full stack** (above the 20) rejects shallow 8×10
crosses that haven't cleared the slow EMA — fewer, higher-quality entries on noisy
1-minute data.

**Entry.** `enter_candidate = gate_open AND fresh_cross`. Only candidates that pass
*both* are scored; the confidence threshold and position sizing then apply as below.

---

## Confidence Score (0–100%)

Each component returns a normalized 0–1 sub-score; the weighted sum is the
confidence. Weights are illustrative — tune them on paper.

| Component | Weight | 1.0 (high) → 0.0 (low) |
|---|---:|---|
| Crossover strength | 30 | Fresh 1-min 8/10/20 cross, ribbon wide & accelerating → tight/barely-crossed or none |
| Higher-TF trend | 20 | 5-min 21/34/55 stacked & expanding → flat or unstacked |
| RSI / momentum | 20 | Turning up from oversold, or in the 45–65 zone → overbought (>70) |
| Volume confirmation | 15 | ≥1.5× avg volume → well below average |
| Volatility / spread sanity | 15 | Tight spread, clean stop distance → spike / poor fill conditions |

`confidence = Σ (sub_score × weight)`  → enter only if `confidence ≥ ENTRY_THRESHOLD`
(e.g. 60%).

> Note: this "confidence %" is a heuristic blend of signals, **not** a true
> probability of profit. Treat it as a relative ranking of setups and validate it
> on the paper account before trusting it.

---

## Position Sizing by Confidence

Higher confidence → bigger slice of the wallet. Two models — start with **A**
(simpler, matches Alpaca's notional orders), graduate to **B** for tighter risk.

### Model A — % of buying power (recommended to start)

```
alloc_fraction = MIN_ALLOC + (MAX_ALLOC − MIN_ALLOC) × (confidence − THRESHOLD)/(100 − THRESHOLD)
notional       = buying_power × alloc_fraction
```

Submit as an Alpaca **notional** order (dollar amount, fractional shares allowed),
with a bracket stop-loss to cap the downside.

**Worked example.** Buying power $10,000, `MIN_ALLOC` 10%, `MAX_ALLOC` 40%,
threshold 60%. Confidence 80% → `0.10 + 0.30 × (20/40) = 0.25` → **$2,500**
notional. Confidence 60% → $1,000. Confidence 100% → $4,000.

### Model B — % of a fixed risk budget (tighter risk control)

```
multiplier     = 0.25 + 0.75 × (confidence − THRESHOLD)/(100 − THRESHOLD)   # 0.25 → 1.0
effective_risk = MAX_RISK_PER_TRADE × multiplier                            # e.g. 2% ceiling
shares         = (equity × effective_risk) / (entry_price − stop_price)
```

This ties size to the actual distance to your stop. **Caveat:** a very tight stop
can produce a large notional for a small dollar risk, so also cap notional
(e.g. no single position > 30–40% of buying power) and cap total open exposure.

---

## Alpaca Integration

- **Endpoints.** Paper trading: `https://paper-api.alpaca.markets`; live:
  `https://api.alpaca.markets`. You stay on the paper endpoint.
- **Auth.** API key id + secret, sent as `APCA-API-KEY-ID` and
  `APCA-API-SECRET-KEY` headers.
- **Market data.** WebSocket stream; the free tier uses the IEX feed (SIP is a
  paid upgrade). Aggregate into 1-minute bars yourself, or subscribe to bar data.
- **Orders.** `POST /v2/orders` supports market/limit, `qty` or `notional`, and
  `order_class=bracket` to attach take-profit and stop-loss in one call — ideal
  for the risk-management requirement.
- **Fractional / notional.** Many US equities support fractional and notional
  orders, which makes Model-A sizing clean.
- **SDKs.** `alpaca-py` (Python) or `Alpaca.Markets` (C#/.NET).

*(Alpaca's API has been stable, but confirm exact fields/limits in the current
docs at docs.alpaca.markets when you wire it up.)*

---

## Telegram Alerts (Direct)

No n8n. The bot calls the Telegram Bot API itself:

1. Create a bot with **@BotFather** → receive a **bot token**.
2. Get your **chat id** (message the bot, then read `getUpdates`, or use a helper).
3. On each event, `POST` to
   `https://api.telegram.org/bot<TOKEN>/sendMessage` with `chat_id` and `text`.

Send alerts for: entry (with confidence % and size), exit (with P/L), and errors.

---

## Persistence (SQL Server)

Log orders, fills, positions, the confidence score per trade, and outcomes to SQL
Server (already provisioned, managed via SSMS). This gives a queryable record for
reviewing whether higher-confidence trades actually perform better.

---

## Technology Stack

| Layer | Choice |
|---|---|
| Host | Ubuntu VPS |
| Language | C#/.NET *or* Python |
| Broker / data | **Alpaca** (paper account; IEX data feed) |
| Order routing | Alpaca REST — market/limit, **bracket**, notional |
| Process manager | `systemd` (.NET / Python) or `PM2` (Node) |
| Database | SQL Server (SSMS) |
| Alerts | **Telegram Bot API (direct)** |

---

## Configuration Parameters

| Parameter | Example | Notes |
|---|---|---|
| `WATCHLIST` | `NFLX, BIRD, WPM` | Symbols to subscribe to |
| `CANDLE_INTERVAL` | `1m` | Short-timeframe aggregation (trigger ribbon) |
| `LONG_CANDLE_INTERVAL` | `5m` | Higher-timeframe aggregation (gate ribbon) |
| `SHORT_MA_PERIODS` | `8,10,20` | 1-min trigger ribbon (fast/mid/slow EMA) |
| `LONG_MA_PERIODS` | `21,34,55` | 5-min gate ribbon (fast/mid/slow EMA) |
| `RSI_PERIOD` | `14` | RSI lookback (1-min) |
| `VOLUME_MA_PERIOD` | `20` | Rolling avg-volume lookback (1-min) |
| `ATR_PERIOD` | `14` | ATR lookback for the volatility sub-score (1-min) |
| `ENTRY_THRESHOLD` | `60` | Min confidence % to enter |
| `MIN_ALLOC` / `MAX_ALLOC` | `0.10` / `0.40` | Model-A wallet fraction range |
| `MAX_RISK_PER_TRADE` | `0.02` | Model-B risk ceiling |
| `STOP_LOSS` / `TAKE_PROFIT` | `2%` / `4%` | Bracket levels |
| `MARKET_OPEN` / `MARKET_CLOSE` | `09:30` / `16:00` US Eastern | Trading window |
| `ALPACA_KEY_ID` / `ALPACA_SECRET` | — | Put in env vars (simplest) |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | — | Put in env vars (simplest) |

---

## Operational Notes

- **You're on paper — that's the safety net.** No real money is at risk, so run it
  live on the paper account from the start and iterate.
- **Timezone.** Keep the server on UTC and convert to US Eastern for the
  market-hours check; Eastern shifts between EST/EDT for daylight saving, so don't
  hardcode a single offset.
- **Reconcile positions** against Alpaca on startup and after any reconnect.
- **Review the data.** Once trades accumulate, query SQL Server to see whether
  higher confidence scores actually correlate with better outcomes, then re-tune
  the weights and threshold.
