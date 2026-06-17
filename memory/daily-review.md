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

## 2026-06-16 — Daily Review

### Stats
- **0 closed trades** (DB realized P&L **$0.00**). **4 entries** opened today — AAPL,
  ABNB, BABA, GOOG — **all still open at the broker** (none exited). Account **equity
  $9,384.92** (last_equity $9,384.87 — essentially **flat** on the day; net unrealized
  ≈ $0: AAPL −$4.47, ABNB −$3.00, BABA +$12.40, GOOG −$4.88). Cash $1,920.29.
- **🚨 Capital-protection event: the EOD flatten FAILED — 4 positions carried NAKED
  overnight.** Alpaca's paper API returned **persistent 504 Gateway Timeouts**
  (`{"code":50410000,"message":"request timed out"}`) on *both* `cancel_order` and
  `close_position` for GOOG/AAPL/BABA across ~20:02–20:58 UTC. All 12 close retries
  (IMP-001's widened budget) exhausted against the 504s; `close_position` returned
  `None` and the bot logged ERROR only — **no Telegram alert**. The DAY bracket legs
  expired at the 20:00 UTC close, so the 4 positions now sit unprotected overnight.
- **DB/report divergence:** `bot.report` shows "open positions: 11" but the broker holds
  **4** (`/v2/positions`). `dbo.positions` carries ~7 stale rows from prior sessions that
  the round-trip recorder never cleared — a reporting/persistence hygiene gap, not a
  broker discrepancy. Logged for follow-up; not today's fix.

### Trade-by-trade review
All four were fresh Model-A entries, mid-to-late session, that **never got an exit** (the
flatten couldn't close them). They were *not* stopped out and not signal failures — the
failure is in the exit/flatten infrastructure, not entry quality:
- **AAPL** 17:08 @ $299.43, conf 66.17 (**crossover only 0.058** — a weak cross), trend
  1.0/rsi 1.0/vol 1.0. Open, −$4.47 unrealized.
- **ABNB** 18:49 @ $141.21, conf 69.85 (crossover 0.125, trend 0.805). Open, −$3.00.
- **BABA** 18:59 @ $110.32, conf 66.05 (crossover 0.097, trend 0.674). Open, **+$12.40**
  (the lone winner-in-waiting).
- **GOOG** 19:14 @ $371.10, conf 64.97 (**crossover only 0.034**, trend 0.698). Open, −$4.88.
- Note: 3 of 4 fired on very weak crossover strength (xo < 0.13). One quiet day isn't
  enough to act on, but if low-xo entries keep underperforming a crossover-strength floor
  is the candidate (see below).

### What worked / what didn't
- **Worked:** entries themselves were benign — flat P&L, no stop-outs, no risk-limit
  trips, FOMC-eve tape was quiet as the pre-market read expected. Service stayed `active`
  the whole session; the websocket auto-reconnected cleanly through its drops.
- **Didn't — the headline:** the EOD flatten has **no escalation when it fails**. IMP-001
  fixed the *held_for_orders* async-cancel race, but today's failure mode was different —
  a **broker-side 504 outage** that no retry budget can beat. The bot exhausted retries and
  went silent, leaving naked overnight positions with the operator unaware. A failed
  flatten is exactly the "F-grade system failure" the weekly rubric calls out; it must be
  **loud**. → fixed this run (IMP-002): a one-time critical Telegram page per symbol when a
  close still fails inside the final ~2 min before the close (no retry runway left).
- The 504s also blocked each `close_position` for ~tens of seconds × 12 attempts, so one
  stuck name delayed flattening the others (GOOG's failure spanned 20:02→20:28). Secondary;
  not changed today (one change per run). Candidate: cap per-symbol close time / parallelize.

### Lessons & improvement candidates
1. **(SHIPPED — IMP-002)** Escalate a critical Telegram alert when the EOD flatten can't
   close a position with no retry runway left (naked-overnight risk). Highest impact:
   turns a silent capital-protection failure into an actionable operator page.
2. *(watch)* **Weak-crossover entries:** 3 of today's 4 entries had xo < 0.13 (AAPL 0.058,
   GOOG 0.034). None resolved today (flatten failed before any exit), so no P&L read yet.
   If low-xo entries keep churning, add a `MIN_CROSSOVER` floor or up-weight `score_crossover`
   in `ScoreWeights`. Needs more days — do NOT act on one inconclusive session.
3. *(carryover)* **`dbo.positions` stale rows** inflate `bot.report`'s open-position count.
   Have the round-trip exit recorder delete the position row on close. Reporting hygiene,
   low risk; queue behind capital-protection work.
4. *(carryover, watch)* 80-89 confidence band still negative all-time (−$51.38, 4 tr, 50%)
   vs 60-79 positive — sample still too small to touch `ScoreWeights`/threshold.

### Notes for pre-market research
- **⚠️ 4 positions are OPEN/NAKED into 2026-06-17:** AAPL (7 sh), ABNB (15), BABA (16),
  GOOG (4) — broker-confirmed, protective legs expired. Pre-market routine **must NOT park
  any of these** (hard rule: never park a name with an open position). At tomorrow's open
  the bot's startup reconcile will mark them MANAGING and the session will re-manage/flatten
  them; if you want them flat sooner, `python -m bot.flatten --yes` once the market opens.
- **FOMC decision today (Wed 06-17, 2pm ET)** — Warsh's first meeting, statement language is
  the binary wildcard. Late-day entries into the print are extra risky; the quiet tape held
  overnight but that can flip on the 2pm headline.
- **No entry-quality concerns** on the watchlist — AAPL/ABNB/BABA/GOOG all signaled and
  filled fine; today's problem was broker-side (Alpaca 504s) and exit infra, not symbols.
- BABA traded well (the only green open, +$12.4) — lower-liquidity but behaving; keep.

---

## 2026-06-17 — Daily Review

### Stats
- Closed trades (DB, after today's backfill): **8** — 1W / 7L → **12.5% win rate**. Net
  realized **−$181.06** (avg −$22.63). Account **equity $9,215.47** (cash, **0 positions at
  broker**), vs last_equity **$9,392.88** → mark-to-market day **≈ −$177.41**. The DB net and
  the equity delta agree to ~$4 — books are honest again after the backfill below.
- **Two cohorts, both losers.** (a) The **4 carried naked overnight from 06-16** (IMP-002's
  504 flatten failure *did* materialize) — AAPL/ABNB/BABA/GOOG — drifted down overnight and
  were flattened today 19:56 via market sell: AAPL **−$28.32**, ABNB **−$14.25**,
  BABA **−$43.60**, GOOG **−$39.68** (= −$125.85). (b) The **4 entered today** all **stopped
  out broker-side intraday** then sat phantom-open until reconciled: TSLA **−$20.80**,
  INTC **+$2.20**, TSM **−$21.00**, MU **−$15.61**.

### Trade-by-trade review (Model A throughout)
Carried-overnight cohort (entered 06-16, flattened 06-17 19:56):
- **BABA** (entry $110.32, conf 66.05) → $107.595 **−$43.60** worst. Overnight drift; the
  naked carry (no protective leg) is what made yesterday's small red a full-day loss.
- **GOOG** (entry $371.10, conf 64.97) → $361.18 **−$39.68**. Same — gap/drift down overnight.
- **AAPL** (entry $299.43, conf 66.17) → $295.385 **−$28.32**. Same.
- **ABNB** (entry $141.21, conf 69.85) → $140.26 **−$14.25**. Mildest of the four.
  → Root cause for all 4 = **the 06-16 naked-overnight hold**, not today's signal. They could
  not be stopped out overnight because IMP-002's 504 outage left them with no live legs.
- Today's entries (all opened 17:19–19:07, **stop filled broker-side**, NOT recorded until
  backfilled):
- **TSM** (entry $440.26, conf **72.83**) → stop $433.26 @19:38 **−$21.00**. Trend faded after
  entry; the 3×ATR stop did its job — clean broker exit.
- **TSLA** (entry $404.06, conf 61.34) → stop $397.13 @19:32 **−$20.80**. Low-conviction entry
  (conf just over the 60 gate); chopped straight to the stop.
- **MU** (entry $1086.11, conf **81.43** — highest of the day) → stop $1070.50 @19:38 **−$15.61**.
  High confidence didn't save it; entered 19:07 into a fading semis tape ~1h before close.
- **INTC** (entry $122.24, conf 66.66) → stop **$122.42** @19:20 **+$2.20** — the lone winner.
  Stop trailed *above* entry (IMP pre-existing trailing logic) and locked a small gain. Proof
  the trailing stop works — and proof of why recording its fills matters (it was logged as a
  phantom-open loss-less row until today's fix).

### What worked / what didn't
- **Worked:** the **trailing/bracket stops fired correctly broker-side** on all 4 fresh names
  (INTC even ratcheted to a win) — risk control is sound. EOD flatten of the 4 carried names
  succeeded via market sell. Test suite green.
- **Didn't:** (1) **The bot is blind to broker-side stop fills (today's headline bug).** The
  trailing stop lives broker-side; when it fills, the position is gone but the bot keeps the
  symbol MANAGING and only discovers it at EOD flatten, where `close_position` **404'd
  'position not found' and was retried 12× per name for ~6 min** (20:11–20:17), logged ERRORs,
  and **never recorded the exit** → 4 phantom-open rows, wrong win-rate (INTC's win invisible),
  near-miss false naked-overnight page. **Fixed today: IMP-003.** (2) **Regime:** a fading
  semis/megacap tape (post-FOMC digestion) + several **late, low-conviction entries** (TSLA at
  the 60 gate; MU 1h before close) — entering thin late tapes keeps producing scratch-to-stop
  trades. (3) The carried-overnight losses are 06-16's bill coming due.

### Backfill (book correction, broker-verified)
TSLA/INTC/TSM/MU were UPDATEd from OPEN→CLOSED at their **broker stop-fill prices** (from
`/v2/orders`), matched on exact entry_time so the older same-symbol phantoms were untouched.
This is what IMP-003 will now do automatically going forward.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-003]** Reconcile broker-side stop/target fills (record the real exit, drop
   the phantom). Highest impact — restores book integrity, win-rate accuracy, removes 404 spam
   and the false-page risk.
2. **Stale phantom cleanup (backlog):** **7 OPEN trade rows from 06-11/06-12** (ENPH, WPM, NFLX,
   TSLA, QCOM, INTC, AMD) remain in the DB though the broker holds **0** — same root cause,
   pre-IMP-003. One-off reconcile/cleanup needed; they pollute the "open positions" count (report
   still shows 9) but not closed-trade stats. Added to todo.md.
3. **Late-day / low-conviction entry quality:** consider a *time-of-day entry cutoff* (e.g. no
   new entries in the final ~60–90 min) and/or lifting the 60 gate — TSLA(61)/late-MU were the
   weak trades. Gather more days before changing the gate; flagged, not actioned.

### Notes for pre-market research
- **No naked positions into 06-18** — broker is **flat (0 positions)**, all of today's names
  exited cleanly broker-side. Nothing to protect from parking.
- **Semis/megacap tape faded post-FOMC** — MU/TSM/TSLA all stopped out; AMD/NVDA quiet. Don't
  assume the early-week semis tailwind persists; watch for a fresh 5m trend before leaning in.
- **Late-day entries keep failing** (TSLA 17:19→stop, MU 19:07→stop). Watchlist is fine; the
  issue is *when* we enter. Nothing to park for signal quality.
- **INTC behaved well** (trailed to a +$2.20 win) — keep; healthy stop behavior.
- BABA/GOOG/AAPL/ABNB losses were the **overnight carry**, not the names — all signal/fill fine.
