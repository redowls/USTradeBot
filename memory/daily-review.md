# Daily Review

Post-close trade review for USTradeBot. **One dated entry per trading day**, written
by the `ustradebot-daily-review` routine (21:10 UTC, Mon–Fri) after the US close.
Every trade taken today is reviewed: why it won or lost, and what concrete change
would improve the win rate. This file is the evidence base the improvement work and
the next morning's pre-market research build on.

Entry template:

## YYYY-MM-DD — Daily Review

### Stats
(trades, wins/losses, net P&L $, win rate, avg win vs avg loss, profit factor,
account equity; "no trades today" + why is a valid entry)

### Trade-by-trade review
(per trade: symbol, model, entry/exit time & price, confidence + sub-scores,
exit reason (stop/target/flatten), P&L, and the root cause — signal quality,
market regime, stop placement, slippage, exit logic)

### What worked / what didn't
(patterns across today's trades)

### Lessons & improvement candidates
(ranked by expected impact; feeds the improvement phase)

### Notes for pre-market research
(watchlist-level observations: symbols that chopped, gapped, or never signaled —
the pre-market routine reads this section the next morning)

---

## 2026-06-15 — Daily Review

### Stats
- Closed trades (DB): **10** — 4W / 6L → **40% win rate**. Net realized P&L **+$79.25**
  (avg +$7.93/trade). Avg win **+$28.10**, avg loss **−$5.53**, **profit factor ≈ 3.4**
  (winners dwarf the many small losers). Account **equity $9,384.89** (cash, 0 open
  positions at broker after the EOD flatten).
- **Caveat — DB P&L vs equity diverge.** Premarket equity was $9,416.76; the day closed
  $9,384.89 (**−$31.87** mark-to-market), yet DB realized P&L is **+$79.25**. Two reasons,
  both benign: (1) three trades were *carried* from prior sessions (see below) so their
  gains were already in yesterday's equity — realizing them today doesn't add to equity;
  (2) DB exits price off the reversal/trigger candle close, not the actual market-sell
  fill (known Phase 4/6 limitation — no trade-updates/fills stream yet). Equity is the
  capital truth; DB P&L is the per-trade attribution. Not today's fix, but worth tracking.

### Trade-by-trade review
All 10 exited **"end-of-day flatten"** at ~19:56 UTC (15:56 ET). Model A throughout.
- **MU** (carried, entry 06-12 15:35 @ $1000.27, conf 70.15) → exit $1077.80 **+$77.53**
  (+7.75%). Best trade. Rode a multi-day semis uptrend; pure regime tailwind (risk-on
  ceasefire rally favored semis, as premarket research predicted).
- **GOOG** (carried, entry 06-12 13:33 @ $361.70, conf 80.49) → $366.345 **+$27.87**
  (+1.28%). Solid trend hold.
- **AVGO** (06-15 17:23 @ $392.87, conf 63.29, weak trend 0.598) → $394.14 **+$5.08**. Marginal.
- **WMT** (06-15 19:31 @ $120.72, conf 65.55) → $120.88 **+$1.92**. Entered 25 min before
  the flatten — no room to work; churn.
- **GOOG** (06-15 17:13 @ $369.42, conf **63.50**, crossover only 0.052, vol 0.462) →
  $366.345 **−$15.38**. Worst. Low-conviction fresh entry into a name already long twice;
  chopped. Signal quality / over-trading one symbol.
- **AMZN** (06-15 17:37 @ $246.91, conf 69.44, trend 0.768) → $246.01 **−$7.20**. Mild
  fade; regime, small.
- **GOOG** (carried, entry 06-09 14:05 @ $367.885, conf 73.62) → $366.345 **−$6.16**.
  Stale multi-day hold that never reached target; flattened flat-ish.
- **UNH** −$1.64, **MU** (06-15 18:07, conf 79.07) −$1.60, **TSM** −$1.17 — all near-scratch
  late entries flattened within ~1h of entry. Time-of-day, not signal failure.

### What worked / what didn't
- **Worked:** the two carried winners (MU, GOOG-06-12) carried the day; semis regime call
  from premarket was correct. Losses were tightly contained (worst −$15) — no stop-outs,
  no risk-limit issues. Profit factor 3.4 is healthy.
- **Didn't:** (1) **The EOD flatten nearly failed — capital-protection bug.** journald shows
  the first flatten pass cancelled each bracket's resting leg then *immediately* tried to
  close and **403'd `held_for_orders`** on **6 of the open names** (GOOG/AVGO/TSM/AMZN/UNH/WMT)
  — the async cancel hadn't settled within the old 3-attempt / ~0.8s retry budget. Only a
  *second* flatten pass ~7s later (driven by another candle) actually closed them. It
  self-healed today (broker ended flat, 0 positions), but on a thin close where no further
  candle arrives before 16:00, those positions would sit **naked with their protective legs
  already cancelled**. → fixed this run (IMP-001). (2) **Carried multi-day holds:** three
  positions from 06-09/06-12 were only flattened today — EOD flatten evidently first ran
  this session, so prior sessions left positions open over the weekend. Now active; watch
  that it flattens cleanly tomorrow. (3) **Late, low-conviction entries** (WMT 19:31, the
  third GOOG @ conf 63.5) add churn with no room before the flatten.

### Lessons & improvement candidates
1. **(SHIPPED — IMP-001)** Make `close_position` poll `qty_available` until the cancelled
   bracket legs release the held qty, then liquidate within the same call (don't depend on a
   later candle). Highest impact: protects capital / prevents naked overnight positions.
2. *(candidate)* Consider a late-session entry cutoff (e.g. no new entries in the final
   ~20–30 min before the flatten window) — late entries today were pure churn. Needs more
   days of evidence before changing; not done today.
3. *(watch)* 80-89 confidence band still negative all-time (−$51, 4 trades) vs 60-79 positive
   — too small a sample to act; keep watching before touching `ScoreWeights`/threshold.

### Notes for pre-market research
- **XOM park (06-15) looks right** — energy stayed weak on the oil drop; no missed longs.
- **GOOG over-traded:** held two carried lots *and* opened a third fresh low-conviction
  (conf 63.5) lot today that lost −$15. Not a watchlist change, but the bot stacking a third
  entry on an already-held name is worth noting.
- **Semis regime call paid off** (MU +$77, carried): NVDA/AVGO/TSM kept correctly; risk-on
  tape favored them as predicted. AVGO traded fine (+$5) — the "on notice" name behaved.
- **Heads-up:** **FOMC decision Wed 06-17** (hawkish wildcard) and **market closed Fri 06-19
  (Juneteenth)** — short, event-heavy week. Late-day entries Tue/Wed are extra risky into FOMC.
- No symbol "never signaled" concern today; the list produced plenty of triggers.

---
