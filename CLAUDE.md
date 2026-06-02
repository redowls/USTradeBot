# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository is in the **planning/spec stage** — there is no code yet. The two
source-of-truth documents are:

- [summary.md](summary.md) — the full system design (architecture, buy logic, confidence
  scoring, position sizing, integrations, config parameters).
- [todo.md](todo.md) — the phased build checklist (Phase 0 → 10).

Before writing code, read both. When you implement something, keep these docs in sync
and check off the relevant `todo.md` item.

**Undecided foundational choice:** the implementation language is either **C#/.NET** or
**Python** (`alpaca-py` vs `Alpaca.Markets`). This is not yet settled — confirm with the
user before scaffolding, since it determines the entire toolchain (build, lint, test,
process manager). Do not assume one.

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

All tunables live in a config layer (env vars or config file) — see the parameter table in
[summary.md](summary.md). Secrets (`ALPACA_KEY_ID`, `ALPACA_SECRET`, `TELEGRAM_TOKEN`,
`TELEGRAM_CHAT_ID`) go in environment variables. The watchlist is a fixed list (e.g.
`NFLX, BIRD, WPM`); a dynamic scanner is explicitly deferred.

## Deployment

Ubuntu VPS, started on boot and auto-restarted on crash via `systemd` (C#/.NET or Python)
or `PM2` (Node). The VPS must reach Alpaca, Telegram, and SQL Server.
