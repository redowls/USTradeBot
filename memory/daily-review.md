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

---

## 2026-06-18 — Daily Review

### Stats
- DB **realized P&L +$199.06** across **9 "closed" rows (7W/2L, 78%)** — but the headline DB
  number is **fictitious** (see below). **Account equity ≈ $9,253–9,263** (last_equity
  $9,215.44) → real **mark-to-market day ≈ +$38–48**, all of it **unrealized** on positions
  that are **still open**. Cash −$1,426.57 (7 lots held).
- **🚨 Capital-protection event: the EOD flatten "closed" 7 positions that are STILL OPEN at
  the broker — 7 names carrying NAKED into the Juneteenth long weekend.** Broker `/v2/positions`
  holds **GOOG(5) INTC(16) MU(1) QQQ(1) SE(15) TSLA(4) TSM(4)** at *today's* entry prices; every
  one was recorded `end-of-day flatten` CLOSED in the DB. The flatten fired ~**16:00–16:05 ET
  (20:00–20:16 UTC), i.e. *after* the 16:00 close**, on a laggy/unstable feed (websocket errors
  19:49/19:54/19:59 + an Alpaca **504 storm** on stop-replaces and GOOG's close). The DAY bracket
  legs had already **expired** at 16:00 (cancels 422'd "order already in expired state"), and the
  flatten's **market DAY sells were `accepted` but never filled** (regular session shut). The bot
  read the submit-ack as success → recorded fake exits at candle-close prices → **IMP-002's NAKED
  page never fired** (the close "succeeded").
- **Books are corrupted for today.** The +$199.06 is dominated by a **fictitious INTC +$154.28**
  (a phantom row entered 06-12 @ $122.20 — one of the 7 stale phantoms flagged 06-17 — "closed"
  today @ $133.22; INTC was never actually held the whole week, broker was flat on 06-17). Strip
  the two 06-12 phantoms (INTC +$154.28, TSLA −$3.26) and the 7 unfilled fake exits, and the real
  day is the ≈ +$38–48 unrealized above. **Needs a Monday book correction** (backfill the 7 at
  their real Monday exit fills, like the 06-17 backfill).

### Trade-by-trade review (Model A throughout)
Two 06-12 **phantom rows** swept up by the flatten (NOT real round-trips):
- **INTC** (06-12 @ $122.20, conf 69.54) → "@ $133.22" **+$154.28** — fictitious; phantom-open row
  closed at today's mark. The +9% INTC rip (Intel–Apple chip news) is real *in the tape*, but the
  bot did **not** hold this lot from 06-12.
- **TSLA** (06-12 @ $402.79, conf 85.94) → "@ $402.33" **−$3.26** — same; phantom row.
Today's **7 real fresh entries** (all 17:28–19:35 UTC) — recorded CLOSED but **broker shows OPEN**:
- **TSLA** (17:56 @ $396.72, conf 71.53, xo 0.16) — open, +$13.56 unreal. "Exit" $402.33 (+$22.42 fake).
- **TSM** (18:01 @ $459.19, conf 73.62, xo 0.12) — open, +$14.77. Fake "+$17.10".
- **GOOG** (17:44 @ $366.26, conf 70.04, xo 0.11) — open, +$3.65. Fake "+$8.43".
- **MU** (17:51 @ $1136.35, conf 65.16, xo 0.22) — open, +$5.93. Fake "+$8.57".
- **INTC** (17:28 @ $133.98, conf 68.56, **xo 0.17**) — open, +$6.55. Fake "−$12.16".
- **QQQ** (19:35 @ $739.46, conf 64.14, **xo 0.04**) — open, +$1.39. Fake "+$1.43".
- **SE** (19:35 @ $91.18, conf 65.35, **xo 0.07**) — open, +$1.65. Fake "+$2.25".
- Root cause for ALL is the **exit/flatten infra**, not entry quality: the entries were green
  (net ≈ +$47 unrealized, the bullish chip-news tape the pre-market read called). The bot just
  never actually exited them, and lied that it did.

### What worked / what didn't
- **Worked:** entries tracked the morning thesis (semis/AI rebound on the Intel–Apple headline) —
  7 of 7 fresh lots are green unrealized. Service stayed `active` all session; websocket
  auto-reconnected through its drops. Trailing stops were being ratcheted (stop-replace logs).
- **Didn't — the headline:** **`close_position` reported success on a mere submit-ack.** A market
  DAY order placed after 16:00 is *accepted but never fills*, yet the bot recorded the exit and
  released the symbol. Net effect: corrupted books **and** a silent naked carry — IMP-002's whole
  escalation was bypassed because, from the bot's view, the close "worked." → **fixed this run
  (IMP-004).** Secondary contributors (not fixed today, one change per run): (a) the **flatten
  fires on candle-close timing**, which lags wall-clock when the feed quiets near 16:00, so the
  flatten executed *after* the close — widening `FLATTEN_BEFORE_CLOSE_MIN` (currently 5) so it
  runs earlier in liquid RTH is the top prevention candidate; (b) recurring **Alpaca 504 storms**
  near the close slow every call.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-004]** `close_position` now **confirms the position actually went flat**
   (`_confirm_flat` polls until the broker 404s) before reporting success; an accepted-but-unfilled
   close returns `None` → the symbol stays MANAGING and IMP-002's naked-overnight page fires, and
   no fake CLOSED row is written. Highest impact: restores book integrity + makes the existing
   safety page actually trigger. Capital protection + data integrity.
2. **(candidate — strong, multi-day)** Widen `FLATTEN_BEFORE_CLOSE_MIN` 5 → ~12–15 so the flatten
   *executes during liquid RTH* (market sells fill) instead of racing the 16:00 wire on a laggy
   feed. Doubles as the late-day-entry cutoff flagged 06-15/06-17 (late low-conviction entries keep
   churning). Prevention to pair with IMP-004's detection. Hold for next run (one change/run).
3. **(book correction — Monday)** Backfill the 7 fake-closed rows to their real Monday exit fills,
   and finally purge the 06-11/06-12 stale phantom rows (INTC/TSLA among them) that the flatten can
   still sweep into fictitious P&L (the INTC +$154.28 today). Pre-IMP-003 residue.
4. **(watch)** 80-89 confidence band still negative all-time (−$70.25, 6 tr, 33%) vs 70-79 (+$184,
   61%) / 60-69 (+$106, 55%). Sample growing but today's data is unreliable (fake exits) — don't
   touch `ScoreWeights`/threshold yet.

### Notes for pre-market research
- **🔒 7 positions are OPEN/NAKED into 2026-06-22** (Mon; **Fri 06-19 is Juneteenth, market closed**):
  **GOOG(5) INTC(16) MU(1) QQQ(1) SE(15) TSLA(4) TSM(4)** — broker-confirmed, protective legs
  expired. Pre-market routine **must NOT park any of these** (hard rule). They are green right now
  (≈ +$47 unrealized) but ride the weekend with **no stops**. Monday's startup reconcile will mark
  them MANAGING; if you want them flat at the open, `python -m bot.flatten --yes` once the market is
  open (NOT now — orders won't fill while it's closed).
- **DB is wrong for 06-18:** it shows these 7 (plus 2 06-12 phantoms) as CLOSED with a fake +$199.06.
  Real day ≈ +$47 unrealized. A **Monday book correction/backfill** is needed before trusting stats.
- **Entry quality was fine** — the Intel–Apple chip-news semis rebound played out; all 7 fresh lots
  green. No watchlist parks indicated. INTC/MU/TSM/TSLA/GOOG/QQQ/SE all signalled and filled cleanly.
- **Watch the late-session entries again:** QQQ (conf 64, xo 0.04) and SE (conf 65, xo 0.07) entered
  19:35 UTC on very weak crossover — same late-day/low-xo pattern flagged all week. Candidate #2
  (wider flatten window = late-entry cutoff) would have blocked both.

---

## 2026-06-19 — Daily Review

### Stats
- **No trades today — US market CLOSED (Juneteenth, Fri 06-19).** 0 entries, 0 exits, P&L
  **$0.00**. Service **active & healthy** all day (only benign IEX websocket keepalive
  reconnects in journald, no errors/restarts). Account **equity $9,248.81** (last_equity
  $9,248.81; cash **−$1,426.58** = margin from the held lots, BP $22,903).
- This is a correct no-trade day: `market_is_open` gated everything off; the bot idled,
  streaming ticks for warmup but opening nothing. Nothing to root-cause on the signal side.

### The real finding — 06-18 EOD flatten silently failed; 7 positions NAKED over the long weekend
The reviewable evidence today is **broker/DB desync from the 06-18 close**, surfaced by the
audit (report shows "open positions: 5" — itself wrong; see below):
- **Broker holds 7 positions right now:** GOOG(5 @366.26) INTC(16 @133.98) MU(1 @1136.38)
  QQQ(1 @739.49) SE(15 @91.19) TSLA(4 @396.56) TSM(4 @459.27) — ≈ **+$33 unrealized**, **no
  protective stops** (all bracket legs cancelled at the 06-18 close), riding the **3-day
  Juneteenth weekend** (reopens Mon 06-22 09:30 ET).
- **DB recorded all 7 as "end-of-day flatten" CLOSED at 06-18 20:05–20:16 UTC with P&L** —
  **fake exits.** The exact qtys/prices still sit open at the broker.
- **Root cause (definitive, from `/v2/orders`):** every 06-18 flatten market-sell was
  **submitted after the 16:00 ET close** (20:05–20:16 UTC) and is stuck **`accepted`,
  `filled 0`**. The flatten is driven by **activity-driven candle closes**, which lagged on a
  thin pre-close tape (GOOG candle events: 15:49, 15:54, then a 22-min gap to 16:16). With the
  flatten window only 5 min wide (opens 15:55 ET), no liquid-tape candle fell inside it to fire
  a *fill-able* flatten before the close. (06-18 ran on **pre-IMP-004** code — the flatten
  fired ~21:10 deploy *after* the 20:05 close — so it recorded the fake exits; IMP-004 now
  detects this but doesn't prevent the carry.)
- **Stale phantoms still present:** 5 OPEN DB rows from **06-11/06-12** (ENPH, WPM, NFLX, QCOM,
  AMD) the broker does **not** hold — pre-IMP-003 residue, still need a one-off cleanup (todo).

### What worked / what didn't
- **Worked:** holiday handling (clean no-trade idle); IMP-004's `_confirm_flat` is now live so the
  06-18 failure mode will be *detected & paged* (not silently faked) going forward; preflight green.
- **Didn't:** the 06-18 flatten's **timing** — gated on laggy candle closes, it fired past 16:00
  into a closed market. Detection (IMP-004) was the half shipped; **prevention** (fire earlier,
  while liquid) was the missing half. Shipped today as **IMP-005**.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-005]** Widen `FLATTEN_BEFORE_CLOSE_MIN` **5 → 15** so the EOD flatten runs in
   liquid RTH (opens 15:45 ET) and the close market orders fill before 16:00 — the prevention half
   IMP-004 deferred to, and a late-entry cutoff for the weak last-15-min entries. Highest impact;
   strictly reduces overnight/gap exposure.
2. **Monday 06-22 book correction (backlog):** after the open flattens the 7 carried lots, backfill
   their **real** exits (the 7 fake 06-18 CLOSED rows over-state P&L by ~+$199) and one-off cleanup
   the 5 stale 06-11/06-12 phantom OPEN rows. Until then, closed-trade stats for 06-18 are untrustworthy.
3. **Consider a wall-clock-driven flatten (backlog, NOT actioned):** the deepest fix for a truly
   illiquid tape (GOOG's 22-min candle gap) is a timer-driven flatten independent of ticks. Larger,
   critical-path change — gather another occurrence with IMP-005 in place before building it.

### Notes for pre-market research
- **🔒 7 positions OPEN/NAKED into Monday 06-22:** GOOG(5) INTC(16) MU(1) QQQ(1) SE(15) TSLA(4)
  TSM(4), no live stops. **The 7 stuck `accepted` 06-18 close orders are STILL LIVE** and will
  **auto-flatten these at Monday's open** (09:30 ET) as market orders — leave them; do **not** cancel
  them (cancelling strands the positions). If a clean book is wanted sooner, `python -m bot.flatten
  --yes` after the open. Startup reconcile marks all 7 MANAGING (no double-entry). **Hard rule honored:
  not parked, all remain enabled** — this is exit/flatten infra, not signal/symbol quality.
- **⚠️ MU reports earnings Wed 06-24** — MU is a held lot AND watchlist name; binary risk midweek (not
  Monday). Flag for Tue/Wed daily-review to manage/exit the MU lot before the print; can't park while held.
- **Entry/symbol quality is NOT the issue** — all 7 lots signalled and filled cleanly on the 06-18
  Intel–Apple semis-rebound tape. No watchlist parks indicated. Today's fix is code (flatten timing).
- **Monday 06-22 earnings** (AREC/EBF/FRVO/ICLR/POWW) — none on the watchlist → no Monday earnings risk.

---

## 2026-06-23 — Daily Review

### Stats
- **3 trades, 0W / 3L → 0% win rate.** Net DB realized **−$9.13** (avg −$3.04). Account
  **equity $9,314.71** (cash, **0 open positions** at broker — flat), vs last_equity
  **$9,321.12** → mark-to-market day **−$6.41**. **Books are HONEST** — DB −$9.13 vs equity
  −$6.41 agree to ~$3 (the residual is the candle-close-vs-fill exit pricing IMP-008 fixes
  this run). All losses tiny (−0.11% to −0.20%); no stop-outs, no risk-limit trips.
- **🎉 First fully clean session in 12 days.** 3 fresh Model-A entries, all flattened by the
  **wall-clock watchdog at 19:45:21–29 UTC (15:45 ET)**, all three market sells **FILLED**
  before 16:00 (GOOG 347.14, UNH 407.69, JPM 334.30), real exits recorded, **0 phantom rows,
  broker flat, no naked carry, no NAKED page** (closes all succeeded). The entire week's
  exit-infra saga (IMP-004/005/006/007) is **proven clean on live data** at last.
- Confidence vs outcome (all-time): 70-79 best (+$183.51, 52%), 60-69 +$96.61 (49%), 80-89
  still negative (−$70.25, 33%, 6 tr — unchanged, no 80+ trades today).

### Trade-by-trade review (Model A throughout; all exited "end-of-day flatten" 19:45 UTC)
- **GOOG** 17:11 @ $347.41, conf 69.16 (**xo 0.14**, trend 0.85, rsi 1.0, vol 0.86, vlt 1.0) →
  DB $346.72 / **real fill $347.14**, DB −$4.14 (real ≈ −$1.6). Held 2h34m. Entered despite the
  −2% pre DeepMind headline; gate trend was fine (0.85) but the name churned flat all afternoon —
  no follow-through. Regime (flat tape), not a bad signal.
- **UNH** 18:14 @ $408.56, conf 66.47 (**xo 0.14**, trend 0.66) → DB $407.775 / real fill $407.69,
  DB −$3.14. Held 1h31m. Mild drift; never threatened stop or target.
- **JPM** 18:58 @ $334.43, conf 63.81 (**xo 0.06** — barely crossed, trend 0.70) → DB $334.06 /
  real fill $334.30, DB −$1.85. Held 47m. Weakest crossover of the three, smallest loss — pure chop.
- **Root cause (all 3):** a **news-quiet, hawkish-Fed-overhang Tuesday** with low realized
  volatility — entries triggered on the gate+cross but the tape gave no momentum, so all three
  drifted slightly red and were flattened. **Market regime (no-trend chop), not signal failure**;
  losses were tightly contained. None was a stop-out.
- **Rejections logged (new IMP-007 observability):** QQQ conf 48.3 < 60, AAPL conf 56.8 < 60 —
  the gate correctly turned away sub-threshold candidates. A flat session is now diagnosable.

### What worked / what didn't
- **Worked — the headline:** the EOD flatten **fired on wall-clock time at 15:45 ET and FILLED
  all 3 sells in liquid RTH** (IMP-005 window + IMP-007 watchdog), recorded real exits (IMP-004
  confirm-flat), left **0 phantom rows** (IMP-006 sweep), broker flat at the close. After a week of
  504s / submit-ack fakes / candle-timing carries, the exit infrastructure did its #1 job cleanly.
  Risk sizing + bracket discipline held (worst trade −$4.14).
- **Didn't:** entries had **no edge in a flat tape** — 0/3, all weak-momentum (xo 0.06–0.14). One
  quiet day of tiny losses is not a strategy defect; do NOT overfit. The only *book* gap left is
  exit-price accuracy (DB recorded the candle-close estimate, not the real fill — GOOG off $0.42/sh)
  → **fixed this run (IMP-008)**.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-008]** Record EOD/reversal exits at the **actual broker market-sell fill price**
   (`close_fill_price` reads the filled order's `filled_avg_price`), not the candle-close estimate
   the caller passes. Highest-impact justified change today: the exit-infra is finally clean, so the
   *last* source of book inaccuracy is exit pricing — and it can flip a marginal win→loss in the
   win-rate metric this routine optimizes. Extends IMP-003's "record at the real fill" truth to the
   bot's own closes. No risk widened, no entry/strategy change.
2. *(watch — multi-day)* **Weak-crossover entries:** all 3 today had xo ≤ 0.14 (JPM 0.06) and all
   went nowhere — echoes the all-week low-xo pattern (06-16 3/4 xo<0.13, 06-18 QQQ 0.04 / SE 0.07).
   But the 60-69 band is net **+$96.61** all-time, today's losses were tiny, and this is the *first*
   clean-data day — **do NOT** add a `MIN_CROSSOVER` floor / up-weight `score_crossover` on one flat
   session. Accumulate several clean days now that the book is trustworthy, then revisit.
3. *(watch)* 80-89 band still negative all-time (−$70.25, 6 tr) — sample unchanged, don't touch weights.

### Notes for pre-market research
- **Book CLEAN & FLAT into 06-24** — 0 broker positions, 0 DB-open rows, equity $9,314.71 all cash.
  No carried lots, no naked exposure, no phantoms. Nothing locked; full watchlist free.
- **⚠️ MU earnings late Wed 06-24 (after close) — the Wed pre-market routine MUST PARK MU** before
  Wed's open so the bot cannot hold it into the print. Today (Tue) carried zero MU risk; tomorrow is
  the park day. (PCE Thu 06-25 also pending.)
- **Entry/symbol quality fine** — all 3 names (GOOG/UNH/JPM) signalled and filled cleanly; the 0/3 was
  a flat, news-quiet tape, not symbol failure. No parks indicated on quality grounds. GOOG traded
  despite its −2% DeepMind headline — behaved (small drift), no concern.
- **IMP-005/007 EOD flatten validated live** — fires 15:45 ET, fills before 16:00. The flatten-
  reliability risk that dogged the whole week is closed; carrying a binary-event name (MU) is still
  unwise, but the infra is now trustworthy.

---

## 2026-06-22 — Daily Review

### Stats
- **0 fresh entries, 0 DB-attributed exits today.** Closed-trade report = 0 trades / $0.00 (nothing the
  strategy opened intraday). Account **equity $9,321.14** (cash $9,321.14, **0 open positions** at the
  broker — flat). Equity rose from last_equity **$9,248.81 → +$72.33 today**, all of it the **7 carried
  06-18 lots being liquidated at the Monday open** (below) — *not* captured in `dbo.trades`.
- Real day P&L lives in **equity (+$72.33)**, not the DB: the Monday liquidation was recorded by
  `reconcile_exit` with **`trade_id=None`** (no OPEN row to attach to — those 7 were already fake-CLOSED
  06-18), so the trades table shows nothing for today. The 5-day report (78% / +$199) is still **inflated
  by the 06-18 fake exits** — directional only.

### Trade-by-trade review
No bot-initiated trades to root-cause. The reviewable events were **broker/DB reconciliation**, not signals:
- **7 carried lots (GOOG/INTC/MU/QQQ/SE/TSLA/TSM)** — held NAKED over the Juneteenth long weekend
  (06-18 close → 06-22) on pre-IMP-005 code. The stuck `accepted` 06-18 close orders **filled at the
  Monday open, 08:02:31 UTC** (MU 1190.60, TSLA 397.76, INTC 138.13, TSM 473.01, GOOG 355.15, SE 89.73,
  QQQ 742.25). The weekend gap resolved **favourably** (+$72 realized vs +$33 unreal Fri) — luck, not
  design; the exposure was real and unprotected. `reconcile_exit` caught the fills at 19:46 UTC but
  couldn't book them (`trade_id=None`).
- **5 phantom OPEN rows (ENPH/WPM/NFLX/QCOM/AMD, 06-11/06-12)** — broker never held them; pure DB
  residue. **Swept clean today by IMP-006** (closed at pnl=0, positions table emptied).

### What worked / what didn't
- **Worked:** the carried-lot risk *cleared itself* at the open and the broker is now flat & matched to a
  clean DB. The phantom desync that has dogged the book since 06-11 is **fixed at the root** (IMP-006) and
  verified live (journald `reconciled 5 phantom OPEN row(s)… AMD, ENPH, NFLX, QCOM, WPM`).
- **Didn't:** today's realized +$72 is **not attributed in `dbo.trades`** — `reconcile_exit` orphans a
  fill when the twin row is already CLOSED. The book is now *consistent* (0 open) but the carried-lot P&L
  (the 06-18 over-statement + the real Monday fills) is still unbooked — it skews closed-trade stats until
  corrected. Lower priority now the open-side is clean.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-006]** Startup phantom sweep — close DB-`OPEN` rows the broker doesn't hold. Done,
   verified live (5 swept), book now broker-matched (`OPEN trades=0, positions=0`).
2. **Backlog — book the carried-lot reality:** have `reconcile_exit` update the existing CLOSED row's exit
   to the real Monday fill (or insert a correcting row) instead of orphaning at `trade_id=None`; pair with
   a one-off backfill of the 06-18 fake-exit P&L (~+$199 over-stated). Care: don't double-count. Gather one
   more `trade_id=None` occurrence before building, now that opens are clean.
3. **[WATCH] IMP-005 still owes a clean live test** — 06-22 had no fresh entries to flatten. First real read
   is **06-23**: confirm the EOD flatten fires ~15:45–15:55 ET with all close orders FILLED before 16:00.
4. **[WATCH] 80-89 confidence band** still negative all-time (−$70.25, 6 tr, 33%) vs 70-79 (+$184) / 60-69
   (+$106). Don't touch `ScoreWeights`/threshold while closed-trade stats are still skewed by uncorrected
   06-18 rows.

### Notes for pre-market research
- **Book is CLEAN and FLAT for the first time in 11 days** — 0 broker positions, 0 DB-open rows, equity
  $9,321.14 all cash. No carried lots, no naked exposure, no phantoms. **Nothing locked** — the full
  watchlist is free to trade 06-23; no park/keep constraints inherited from open positions.
- **⚠️ MU earnings Wed 06-24** — MU is a watchlist name (no longer a held lot; the carried MU was
  liquidated today). Binary risk midweek: flag for the Tue 06-23 / Wed 06-24 routines to decide whether to
  park MU or accept the print. **PCE Fri 06-26** also still pending.
- **Entry/symbol quality unchanged** — no signals fired today (quiet post-holiday Monday tape, very thin
  candle volumes all session per journald). No watchlist parks indicated on quality grounds.
- **06-23 is the day to watch IMP-005 live** — if fresh entries are taken, confirm the EOD flatten fully
  fills before 16:00 ET and the book is flat at the close (the prevention that 06-22 couldn't exercise).

---

## 2026-06-24 — Daily Review

### Stats
- **6 trades, 3W / 3L → 50% win rate.** Net DB realized **−$10.14** (avg −$1.69). Avg win **+$15.81**,
  avg loss **−$19.19**, **profit factor 0.82**. Account **equity $9,299.14** (cash, **0 open positions**
  at broker — flat), vs last_equity **$9,314.69** → mark-to-market day **−$15.55**.
- **Book honest, residual ~$5.41.** DB −$10.14 vs equity −$15.55 differ by ~$5.41 — now that exits are
  exact (IMP-008 validated again below), the *last* source of divergence is the **entry price**, still
  recorded at the candle-close estimate not the broker buy fill → **fixed this run (IMP-009)**.
- **🎉 Second consecutive fully clean session.** All exits real (3 EOD-flatten market sells filled 19:45
  UTC / 15:45 ET via the IMP-007 wall-clock watchdog, 3 broker-side trailing-stop fills), **0 phantom
  rows, broker flat, no naked carry, no NAKED page.** MU correctly held NONE into its after-close print
  (parked pre-market). Exit infra is now proven clean on two straight days of live data.
- Confidence vs outcome (all-time): 70-79 best (+$196.40, 55%), 60-69 +$73.59 (48%), 80-89 still
  negative (−$70.25, 33%, 6 tr — unchanged, no 80+ trades today).

### Trade-by-trade review (Model A throughout)
- **ABNB** 14:11 @ $143.825, conf 71.76 (**xo 0.57** strong, trend 1.0, rsi 1.0, **vol 0.0**, vlt 0.98) →
  EOD flatten @ $144.63 **+$12.88** (+0.56%). Earliest entry (10:11 ET), strong fresh cross + maxed gate
  trend; held all day for a modest gain despite a thin-volume sub-score. Good signal.
- **SE** 14:45 @ $91.98, conf 66.84 (**xo 0.47**, trend 0.66) → broker-side trailing-stop fill @ $93.65
  19:20 **+$33.40** (+1.82%). **Best trade.** The trailing stop ratcheted *above* entry and locked a
  +1.82% gain — exactly the IMP trailing-stop design working as intended.
- **JPM** 19:10 @ $333.535, conf 61.94 (**xo 0.04** — barely crossed, trend 0.53) → EOD flatten @ $333.82
  **+$1.14** (+0.09%). Late (15:10 ET), weakest crossover of the day, near-scratch chop.
- **AMZN** 14:45 @ $238.82, conf 67.75 (**xo 0.31**, trend 1.0) → broker-side trailing-stop fill @ $237.395
  18:37 **−$11.40** (−0.60%). Mild fade; the trailing stop contained the loss to −0.6%.
- **SPY** 15:30 @ $739.63, conf 66.38 (**xo 0.13** weak, trend 0.62) → EOD flatten @ $731.52 **−$16.22**
  (−1.10%). Drifted down on the broad semi-led market weakness; weak crossover, no follow-through.
- **INTC** 16:18 @ $134.76, conf 68.61 (**xo 0.08** very weak, trend 0.82) → broker-side stop @ $132.265
  16:47 **−$29.94** (−1.85%). **Biggest loss.** Stopped out ~30 min after a weak-crossover entry; the stop
  did its job at −1.85% (no runaway).
- **Root cause:** a choppy **semi-rout-rebound tape** (Tue 06-23 Nasdaq −2.21%; 06-24 mixed). The two
  winners had **strong crossovers** (ABNB 0.57, SE 0.47); the three losers/scratch had **weak crossovers**
  (SPY 0.13, INTC 0.08, JPM 0.04). Trailing stops contained every loss (worst −1.85%) and captured SE's
  +1.82%. **Regime + weak-signal entries**, not a strategy or risk defect; no stop-outs were violent, no
  risk-limit trips, book honest & flat.

### What worked / what didn't
- **Worked:** the **trailing stops** — SE ratcheted to a +1.82% locked win, AMZN/INTC losses were capped
  at −0.6%/−1.85%. The **EOD flatten** fired on the wall-clock watchdog and filled cleanly (2nd clean day).
  **IMP-008 validated again** — every DB exit price matches the broker fill exactly (ABNB 144.63, SE 93.65,
  JPM 333.82, AMZN 237.395, INTC 132.265). MU park kept the bot out of a binary print.
- **Didn't:** (1) **Entry prices are still recorded at the candle-close estimate, not the buy fill** — INTC
  DB @134.76 vs broker @134.7817, SPY @739.63 vs @739.675, JPM @333.535 vs @333.57 — the ~$5.41 residual
  between DB P&L and equity. → **fixed this run (IMP-009)**. (2) **Weak-crossover entries underperformed
  again** (SPY/INTC/JPM all xo ≤ 0.13) — a strengthening multi-day pattern, but do NOT act yet (see below).

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-009]** Record entries at the **actual broker buy fill price** (`entry_fill_price` reads
   the bracket parent order's `filled_avg_price` after the submit ack), not the candle-close estimate the
   signal sized off. The entry-side mirror of IMP-008; closes the last DB↔equity divergence and makes the
   win-rate metric this routine optimizes exact. No risk widened, no entry/strategy logic changed.
2. *(watch — strengthening, do NOT act yet)* **Weak-crossover entries underperform.** Two straight clean
   days now show it: 06-23 all 3 xo ≤ 0.14 went nowhere; 06-24 the 3 low-xo names (xo ≤ 0.13) lost/scratched
   while the 2 high-xo (ABNB 0.57, SE 0.47) won big. Candidate: a `MIN_CROSSOVER` floor or up-weight
   `score_crossover`. But (a) only 2 clean days, (b) the 60-69 band is still net **+$73.59** all-time, and
   (c) **IMP-009 just made the data exact** — gather a few more clean days on now-accurate entry+exit prices,
   THEN revisit. Acting on 2 days risks overfitting (explicitly deferred 06-16/06-18/06-23).
3. *(watch)* 80-89 band still negative all-time (−$70.25, 6 tr) — sample unchanged, don't touch weights.
4. *(hygiene note)* **Git has two commits both labeled IMP-008** (warmup 27e4c03 + exit-fill f854f96); the
   warmup change never got an improvement-log entry. Documentation gap only — next number used here is IMP-009.

### Notes for pre-market research
- **Book CLEAN & FLAT into 06-25** — 0 broker positions, 0 DB-open rows, equity $9,299.14 all cash. No
  carried lots, no naked exposure, no phantoms. Nothing locked; watchlist free (MU currently parked).
- **⚠️ MU REPORTS EARNINGS AFTER TODAY'S CLOSE (06-24)** — MU was correctly **parked pre-market** so the
  bot held nothing into the print. The **06-25 pre-market routine should RE-ENABLE MU** once the after-hours
  move is digested (it's a top-2 earner; the park was event-driven, not a demotion). Check the post-print
  gap before re-enabling.
- **⚠️ May PCE Thursday 06-25** — the week's macro binary; late-day entries into it are extra risky.
- **Entry/symbol quality fine** — ABNB and SE traded beautifully (SE's trailing stop locked +1.82%). The 3
  weak-xo losers (SPY/INTC/JPM) reflect a choppy semi-rout-rebound tape, not symbol failure → no quality
  parks. The weak-crossover underperformance is a **code/scoring** question (daily-review candidate once the
  data is exact), NOT a watchlist change.

---

## 2026-06-25 — Daily Review

### Stats
- **5 trades, 2W / 3L → 40% win rate.** Net DB realized **−$52.59** (after the AMD book correction
  below; avg −$10.52). Avg win **+$25.10**, avg loss **−$34.26**, **profit factor 0.49**. Account
  **equity $9,246.52** (cash, **0 open positions** at broker — flat), vs last_equity **$9,299.11** →
  mark-to-market day **−$52.59**. **Books are now exact** — DB net −$52.59 == equity day −$52.59 to
  the cent (after correcting AMD; see below). No stop-outs were violent (worst −2.03%), no risk-limit trips.
- **🎯 Data-integrity finding — IMP-009 missed AMD's delayed fill.** AMD's market buy was **submitted
  13:33:34 but did not fill until 13:35:42 (~2 min later)** — well past IMP-009's 3 s submit-time
  readback budget — so the entry was recorded at the candle-close estimate **544.71** instead of the
  real broker fill **547.873**. That understated AMD's loss by **$18.98** (the **exact** DB↔equity gap:
  pre-correction DB −$33.61 vs equity −$52.59). → **fixed this run (IMP-010)** + one-off AMD row corrected.
- **🎉 Third consecutive clean exit-infra session.** All exits real (2 EOD-flatten market sells filled
  19:45 UTC / 15:45 ET via the IMP-007 wall-clock watchdog; 3 broker-side stop/trailing-stop fills), **0
  phantom rows, broker flat, no naked carry, no NAKED page.** The re-enabled MU traded beautifully.
- Confidence vs outcome (all-time, post-correction): 70-79 best (**+$154.69, 52%**), 60-69 **+$95.75
  (48%)**, **80-89 negative (−$49.34, 43%, 7 tr)**, **90-100 negative (−$53.94, 0%, 1 tr = AMD)**.

### Trade-by-trade review (Model A throughout)
- **AMD** 13:33 @ **$547.873** (real fill; pre-correction recorded @544.71), conf **91.73** (**xo 0.77**
  strong, trend 1.0, rsi 1.0, vol 1.0, vlt 0.90) → broker-side **stop @ $538.883** ~13:42 (9:42 ET)
  **−$53.94** (−1.64%). **Biggest loss.** The **highest-confidence entry the bot has ever recorded**,
  strong on every sub-score — yet it entered **~3 min after the open** into the **MU-blowout chip gap-up
  euphoria**, topped immediately, and stopped within ~9 min. Bought the open spike. Regime/timing, not a
  weak signal (its crossover was the *strongest* of the day).
- **C** 13:48 @ $145.48, conf 61.28 (**xo 0.39**, trend 0.67, **vol 0.08**) → EOD flatten @ $144.93
  **−$7.15** (−0.38%). Weakest confidence; near-scratch chop.
- **UNH** 13:56 @ $412.39, conf **81.67** (**xo 0.42**, trend 0.95) → EOD flatten @ $415.87 **+$20.90**
  (+0.84%). Strong cross, held all day for a modest gain — the lone 80+ winner.
- **JPM** 14:53 @ $342.66, conf 76.00 (**xo 0.20** weak, trend 1.0) → broker-side **stop @ $335.71**
  ~17:32 **−$41.70** (−2.03%). Weak-ish crossover; stopped out, the 3×ATR stop did its job at −2%.
- **MU** 15:22 @ $1182.54, conf 64.16 (**xo 0.42**, trend 1.0, **vol 0.16**) → broker-side **trailing-stop
  @ $1211.84** ~19:05 **+$29.30** (+2.48%). **Best trade.** The trailing stop ratcheted *above* entry and
  locked +2.48% on the re-enabled, post-earnings-blowout MU — the 06-25 pre-market re-enable paid off.
- **Root cause:** a **chip-led risk-on but choppy/fading tape** — MU's blowout gapped semis up at the open,
  then a hotter PCE-overhang capped the rally. The two winners ran via trailing-stop/hold (MU +2.48%, UNH
  +0.84%); the three losers were **AMD (open-euphoria top, stopped)**, JPM (weak xo, −2% stop), C (scratch).
  **Crossover strength did NOT predict outcome today** — AMD had the *strongest* xo (0.77) and lost the most;
  the discriminator was **time-of-entry / regime** (AMD bought the gap-up open spike). Trailing stops +
  brackets contained every loss (worst −2.03%); no risk-limit trips; book honest & flat.

### Book correction (broker-verified)
AMD's row UPDATEd entry_price 544.71 → **547.873333** (the real `/v2/orders` parent-buy `filled_avg_price`),
pnl recomputed −34.96 → **−53.94**, pnl_pct → −1.6409. This is exactly what IMP-010 now does automatically.
After the correction the day's DB net (−$52.59) ties to equity to the cent.

### What worked / what didn't
- **Worked:** the **trailing stops** (MU ratcheted to a +2.48% locked win; AMD/JPM losses capped at
  −1.64%/−2.03%). **MU re-enable validated** (+$29.30, best trade). The **EOD flatten** fired on the
  wall-clock watchdog and filled cleanly (3rd straight clean exit-infra day, 0 phantoms, broker flat).
- **Didn't:** (1) **IMP-009's entry-fill capture missed AMD's delayed (~2 min) fill** → a $18.98 book
  understatement, the exact DB↔equity gap. → **fixed this run (IMP-010)**. (2) **The highest-confidence
  entry of the bot's life (AMD 91.73) was the worst loser** — bought the gap-up open spike; the 90-100
  band is now 0/1 −$53.94 and 80-89 −$49.34 (3/7). High-confidence underperformance is strengthening, but
  UNH (81.67) *won* today, so it's mixed — keep watching, do NOT act on one day.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-010]** Re-read the entry parent-order fill at **exit time** (when the buy is definitively
   filled) and COALESCE it over the stored entry_price, recomputing P/L — robust to a fill delayed past
   IMP-009's short submit-time budget, with no candle-thread stall. Completes the IMP-003/008/009
   "record at the real fill" thread on the entry side. Plus the one-off AMD book correction above. No risk
   widened, no entry/strategy logic changed — pure data integrity (the win-rate metric this routine optimizes).
2. *(watch — strengthening)* **High-confidence / open-spike entries underperform.** AMD (conf 91.73, the
   highest ever) entered ~3 min after the open into a gap-up and topped; 80-89 (−$49.34, 7 tr) and 90-100
   (−$53.94, 1 tr) are both net negative all-time. Candidates if it persists: a **first-N-minutes / open-spike
   entry guard**, or revisiting `ScoreWeights` so a maxed-out gap-up score isn't over-trusted. But (a) one day,
   (b) UNH (81.67) won today, (c) data only just became exact again — gather more clean days, then revisit.
3. *(watch)* The multi-day **weak-crossover** thesis was **contradicted today** (strongest-xo AMD lost most) —
   the signal is time-of-entry/regime, not crossover strength alone. Do not act; let the now-exact data accumulate.

### Notes for pre-market research
- **Book CLEAN & FLAT into 06-26** — 0 broker positions, 0 DB-open rows, equity $9,246.52 all cash. No
  carried lots, no naked exposure, no phantoms. Nothing locked; full watchlist free.
- **MU re-enable validated** — MU traded beautifully (trailing stop locked **+2.48%** on the earnings-blowout
  tape); **keep enabled**, the event-driven park is fully unwound and paying.
- **AMD — open-spike risk on gap-up mornings.** The bot's highest-ever-confidence signal (91.73) bought the
  MU-euphoria gap-up open spike (~3 min after the bell) and stopped −1.64% within minutes. This is a
  **regime/timing** loss (open-spike top), **not a symbol-quality** issue → keep AMD, no park; just a heads-up
  that gap-up opens can spike-and-fade the most-confident long.
- **JPM** (weak xo 0.20, −2% stop) and **C** (xo 0.39, scratch) reflect a choppy tape, not symbol failure →
  no quality parks. All five names signalled and filled cleanly.
- **PCE (06-25, 8:30 ET) was today's macro binary** — note any follow-through into Friday 06-26; check 06-26
  pre-market for any watchlist-name earnings (none flagged as of tonight).

---

## 2026-06-26 — Daily Review

### Stats
- **11 trades, 5W / 6L → 45% win rate.** Net DB realized **+$62.07** (avg +$5.64). Avg win **+$19.30**,
  avg loss **−$5.74**, **profit factor ≈ 2.80**. Account **equity $9,308.57** (cash, **0 open positions**
  at broker — flat), vs pre-market $9,246.50 → mark-to-market day **+$62.07**. **Books exact** — DB net
  **+$62.07 == equity day +$62.07 to the cent** (IMP-009/010 validated a 4th straight session).
- **🎉 Fourth consecutive fully clean exit-infra session.** All 11 exited via the **wall-clock EOD flatten
  19:45–19:46 UTC (15:45 ET)** — every market sell FILLED in liquid RTH, 4 reconciled at the real
  broker-side fill (NFLX/TSLA/AMZN + others tagged "stop/target filled broker-side"), **0 phantom rows,
  broker flat, no naked carry, no NAKED page.** Notably **zero intraday stop/target/trailing exits fired**
  today — a slow-drift tape where nothing reached the ±2–3% bracket legs, so every name rode to the flatten.
- Confidence vs outcome (all-time): 70-79 best (**+$170.31, 58%, 26 tr**), 60-69 **+$67.47 (44%, 57 tr)**,
  80-89 **+$25.38 (50%, 8 tr)**, 90-100 **−$53.94 (0%, 1 tr = AMD)**.

### Trade-by-trade review (Model A throughout; all exited "end-of-day flatten" 19:45 UTC)
- **MSFT** 14:05 @ $363.295, conf **85.90** (**xo 0.58** strong, trend 1.0, rsi 1.0, vol 0.94, vlt 0.95) →
  $372.635 **+$74.72** (+2.57%). **Best trade by far.** Earliest + strongest setup; wide accelerating cross
  + maxed gate trend, rode a clean all-day uptrend. Textbook high-conviction strong-cross winner.
- **AAPL** 18:03 @ $279.74, conf 70.78 (**xo 0.24**, trend 0.68) → $281.59 **+$7.40** (+0.66%). Solid hold.
- **TSLA** 14:42 @ $377.984, conf 73.82 (**xo 0.28**, trend 0.77) → $379.556 **+$7.86** (+0.42%). Mild grind up.
- **UNH** 14:15 @ $423.67, conf 62.36 (**xo 0.25**, trend 1.0, **rsi 0.0**) → $425.723 **+$6.16** (+0.48%).
  The lone sub-67-conf winner; xo 0.25 (above the new floor).
- **NFLX** 14:06 @ $73.67, conf 73.31 (**xo 0.59** strong, **rsi 0.09**) → $73.682 **+$0.36** (+0.02%). Scratch-win.
- **NVDA** 17:28 @ $194.878, conf 60.03 (**xo 0.27**, vol 0.33) → $194.78 **−$0.49** (−0.05%). Scratch.
- **SPY** 16:51 @ $734.45, conf 63.69 (**xo 0.05** — weakest cross of the day) → $733.20 **−$1.25** (−0.17%). Chop.
- **QQQ** 16:51 @ $713.36, conf 64.37 (**xo 0.11**) → $711.37 **−$1.99** (−0.28%). Weak-cross drift.
- **COST** 14:54 @ $957.99, conf 61.59 (**xo 0.14**, vol 0.26) → $953.14 **−$4.85** (−0.51%). Weak-cross fade.
- **ABNB** 17:31 @ $147.24, conf 60.10 (**xo 0.17**, **rsi 0.0**) → $146.11 **−$6.78** (−0.77%). Weak-cross fade.
- **AMZN** 15:04 @ $231.12, conf 65.99 (**xo 0.12**, vol 0.68) → $227.942 **−$19.07** (−1.38%). **Biggest loss.**
  Weak, non-accelerating cross into a tech-down tape; drifted all afternoon, flattened deep red.
- **Root cause:** a **tech-led risk-off slow-drift day** (AI/memory-cost overhang, AAPL/MSFT hardware price
  hikes). The discriminator was **crossover strength, not regime alone**: the two **strong-cross** entries
  (MSFT 0.58, NFLX 0.59) won; the five **weak-cross** entries (xo < 0.20: COST 0.14, AMZN 0.12, SPY 0.05,
  QQQ 0.11, ABNB 0.17) **all lost** (0W/5L); the four mid-cross (xo 0.24–0.28: AAPL/TSLA/UNH/NVDA) went 3W/1L.
  No stop-outs (nothing hit the brackets), no risk-limit trips, book honest & flat.

### What worked / what didn't
- **Worked:** exit infra (4th clean day) — wall-clock flatten filled all 11 in liquid RTH, real fills
  reconciled, 0 phantoms, broker flat, books exact to the cent. The **strong-cross entries carried the day**
  (MSFT +$74.72 alone > the whole day's net). Losses were tightly contained (worst −1.38%, no stop-outs).
- **Didn't — the clean, now-actionable pattern:** **weak-crossover entries underperformed yet again, and on
  trustworthy data the signal is now unambiguous.** Today: xo < 0.20 went **0W/5L**. Across the four clean-book
  sessions (06-23..26): xo < 0.20 → **1 win of 12 (8%, avg −$10.82)**; xo 0.20–0.40 → 3/6 (50%, +$0.40);
  xo ≥ 0.40 → **6/7 (86%, +$16.80)** — a clean, monotonic relationship the muddy confidence bands don't show
  (clean-days 65-69 is *worse* than 60-64). The deferral conditions cited every prior run (clean exit-infra
  data + several clean days) are now met → **acted this run (IMP-011).**

### Lessons & improvement candidates (ranked)
1. **[SHIPPED IMP-011]** Add a **`MIN_CROSSOVER` entry floor (default 0.20)** in `evaluate_entry`, applied
   alongside `entry_threshold`: a scored candidate must clear **both** `confidence.total >= threshold` and
   `confidence.crossover >= 0.20`. Rejects the chop cohort that clears the total bar on trend/rsi/volume
   weight while riding a weak, non-accelerating cross (today's COST/AMZN/SPY/QQQ/ABNB, all losses). Justified
   by 4 clean sessions (xo<0.20 = 8% win, −$10.82 avg) + today (0/5). **Tightens entry selectivity only —
   never widens risk; the floor is a strict capital-protection filter.** No threshold/weights/sizing changed.
2. *(watch)* **High-confidence / open-spike** still on notice (AMD 91.73 −$53.94 on 06-25; 90-100 0/1). The
   crossover floor does NOT target it (AMD's xo was 0.77, strong) — that's a separate time-of-entry guard;
   gather more occurrences. UNH (81.67) won 06-25 and MSFT (85.9) won today, so the top band is mixed.
3. *(watch)* Set the MIN_CROSSOVER floor at 0.20, not higher: the 0.20–0.40 mid-cross band is ~coin-flip
   (50%) and produced 3 of today's winners (AAPL/TSLA/UNH) — cutting it would sacrifice real wins. Re-evaluate
   raising toward 0.30–0.40 only if the mid band keeps net-negative over more clean days.

### Notes for pre-market research
- **Book CLEAN & FLAT into the next session** — 0 broker positions, 0 DB-open rows, equity $9,308.57 all cash.
  No carried lots, no naked exposure, no phantoms. Nothing locked; full watchlist free.
- **Weak-cross chop names today** (xo < 0.20, all lost): **COST, AMZN, SPY, QQQ, ABNB** — these are NOT
  watchlist parks (they're liquid large-caps; the issue was *signal strength on the day*, now filtered in code
  by IMP-011). The strong-cross names **MSFT (+$74.72) and NFLX** traded beautifully → keep. No quality parks.
- **Tech-led risk-off tape** (AI/memory-cost overhang; AAPL/MSFT hardware price-hike headline) — non-binary,
  no watchlist-name earnings today. The long-only ribbon self-protected (no stop-outs); MSFT still found a
  clean trending long. No regime-driven park action.
- **Heads-up for next week:** IMP-011 is live from tonight's restart — expect **fewer entries** (the weak-cross
  cohort is now filtered). Watch that entry *count* doesn't collapse and that the surviving entries' win rate
  rises as the clean-day data predicts; the weekly review should grade IMP-011's first live sessions.

---

## 2026-06-29 — Daily Review

### Stats
- **12 trades, 7W / 5L → 58% win rate.** Net DB realized **+$89.72** (avg +$7.48). Avg win **+$31.92**,
  avg loss **−$26.74**, **profit factor 1.67**. Account **equity $9,398.26** (cash, **0 open positions**
  at broker — flat), vs last_equity **$9,308.54** → mark-to-market day **+$89.72**. **Books exact** — DB
  net **+$89.72 == equity day +$89.72 to the cent** (IMP-009/010 validated a **5th straight session**).
- **🎉 Fifth consecutive fully clean exit-infra session.** All 12 exited via the **wall-clock EOD flatten
  19:45–19:46 UTC (15:45 ET)** — every market sell FILLED in liquid RTH, 5 reconciled at the real
  broker-side fill (MSFT/AMZN/COST/NFLX/ABNB, tagged "stop/target filled broker-side"), **0 phantom rows,
  broker flat, no naked carry, no NAKED page, 0 journald errors, no restarts.**
- **✅ IMP-011 validated live on its first full trading day** — see below.
- Confidence vs outcome (all-time): 70-79 best (**+$206.03, 57%, 30 tr**), 60-69 **+$121.47 (46%, 65 tr)**,
  80-89 **+$25.38 (50%, 8 tr — no 80+ trade today)**, 90-100 **−$53.94 (0%, 1 tr = AMD, unchanged)**.

### Trade-by-trade review (Model A throughout; all exited "end-of-day flatten" 19:45–19:46 UTC)
Winners (7):
- **TSLA** 14:26 @ $393.14, conf 77.5 (**xo 0.53**, trend 1.0) → $412.26 **+$95.62** (+4.86%). **Best trade
  by far.** Strong fresh cross + maxed gate; rode a clean all-day uptrend. Textbook strong-cross winner.
- **TSM** 14:51 @ $439.79, conf 68.8 (**xo 0.47**, trend 1.0, **vol 0.0**) → $453.52 **+$41.19** (+3.12%).
  Chips traded *fine* intraday despite the −6% pre-market scare; clean trend hold.
- **GOOG** 14:08 @ $346.01, conf 68.5 (**xo 0.38**, trend 0.90) → $351.81 **+$29.00** (+1.68%). Solid grind up.
- **QQQ** 14:51 @ $713.70, conf 70.2 (**xo 0.30**, trend 0.56, vol 1.0) → $723.35 **+$19.30** (+1.35%). Index trend.
- **AMD** 16:35 @ $530.20, conf 68.4 (**xo 0.45**, vol 0.0) → $537.53 **+$14.67** (+1.38%). Mid-session entry,
  trended up — *not* a gap-up open-spike like 06-25's AMD; behaved.
- **MU** 18:03 @ $1118.89, conf 61.5 (**xo 0.24**, vol 0.0) → $1133.26 **+$14.37** (+1.28%). Re-enabled MU
  trended despite the −6% pre-market chip-rotation noise; the re-enable keeps paying.
- **INTC** 17:27 @ $129.78, conf 69.8 (**xo 0.35**) → $130.55 **+$9.27** (+0.60%). Modest hold.
Losers (5):
- **MSFT** 13:41 @ $379.10, conf 79.7 (**xo 0.66** — strongest cross of the day, trend 1.0) → $372.41
  **−$46.84** (−1.77%). **Biggest loss.** Earliest entry (9:41 ET) + strongest signal, yet drifted down all
  day to near its stop. Mirror of 06-25 AMD: a high-conf/strong-cross *early* entry was the worst trade.
- **NFLX** 14:26 @ $75.95, conf 71.2 (**xo 0.50**, rsi 1.0, **vol 0.11**) → $74.48 **−$32.36** (−1.94%).
  Strong cross but thin-volume; faded to the bracket. Strong-xo did not guarantee a winner today.
- **ABNB** 14:53 @ $149.93, conf 62.0 (**xo 0.23** — just above the floor, **vol 0.0**) → $146.94 **−$20.93**
  (−1.99%). Weakest surviving cross; near-stop fade.
- **COST** 14:12 @ $966.50, conf 63.6 (**xo 0.30**, vol 0.22) → $949.11 **−$17.39** (−1.80%). Drifted down.
- **AMZN** 14:44 @ $244.76, conf 66.8 (**xo 0.32**, vol 0.16) → $241.53 **−$16.18** (−1.32%). Mild fade.
- **Root cause:** a **bifurcated tape** (index futures up, chips down pre-market, per the morning read) that
  resolved as **trend dispersion** — names that trended ran (TSLA +4.86%, TSM +3.12%, GOOG/QQQ/MU/AMD/INTC
  green); names that didn't drifted to ~−1.3% to −2% near their stops (MSFT/NFLX/ABNB/COST/AMZN). **Regime /
  intraday follow-through, not signal failure or a risk defect** — no violent stop-outs, no risk-limit trips,
  losses tightly contained (worst −1.99%), book honest & flat. Crossover *strength* was **not** monotonic
  within the surviving population today (MSFT 0.66 was the worst loser) — but that is expected noise; IMP-011
  filters only the <0.20 dead zone, not within the kept population.

### IMP-011 (MIN_CROSSOVER 0.20) — first full live day, VALIDATED ✅
- **Filtering fired exactly as designed:** journald shows weak-cross candidates rejected all session —
  **C** (xo 0.06 / 0.08 / 0.12 / 0.07, ×4), **SPY** (0.04 / 0.03, ×2), **JPM** (0.08) — each logged
  `no entry … crossover X.XX < 0.20`. These are precisely the ~8%-win chop cohort the floor targets; ~7
  weak entries prevented.
- **Entry count held** (12 — did NOT collapse toward zero, the weekly review's first worry).
- **Win rate rose to 58%** vs the 40% four-clean-day baseline; **all 12 entries had xo ≥ 0.23** (floor
  honored — lowest survivors ABNB 0.23 / MU 0.24). PF 1.67, +$89.72.
- **Verdict:** IMP-011 is working as intended on day one. Per the weekly review's directive, **let it keep
  proving out over the full week — do NOT stack another entry-logic change on top that would confound it.**

### What worked / what didn't
- **Worked:** IMP-011 (weak-cross chop filtered, win rate up, count healthy); the trending strong/mid-cross
  longs carried the day (TSLA +$95.62 alone > the day's net); exit infra (5th clean day — wall-clock flatten,
  all fills real, 0 phantoms, broker flat, books exact to the cent); risk control (worst −1.99%, no stop-outs).
- **Didn't:** the day's biggest loser **MSFT** was a high-conf (79.7) / strongest-cross (0.66) **early**
  (9:41 ET) entry that topped and drifted — a *second soft occurrence* of the "strong signal, early entry,
  big loss" pattern (after 06-25 AMD). It is **not** an open-spike the way AMD was (~3 min vs MSFT's ~11 min),
  TSLA (also early-ish, 10:26 ET) won big, and it is only the 2nd data point → **watch, do NOT act.**

### Lessons & improvement candidates (ranked)
1. **No code change warranted today** (a respectable outcome). The system is profitable, books are exact,
   exit infra is clean for the 5th straight session, and **IMP-011 — live exactly one day — is doing precisely
   its job.** The explicit weekly-review directive is to *let IMP-011 prove out over its first full week*;
   shipping another entry-logic change now would confound its evaluation and risk overfitting to a single day.
2. *(watch — strengthening, do NOT act)* **High-conf / strong-cross *early* entries underperform.** AMD (conf
   91.73, xo 0.77, 06-25) and MSFT (conf 79.7, xo 0.66, today) were each the day's worst loser, both entered
   in the first ~10 min and topped. Candidate if it persists: a **first-N-minutes / open-spike entry guard**.
   But it's only 2 occurrences, TSLA/TSM trended fine from early entries today, and IMP-011 must be left to
   prove out first. Gather more occurrences; revisit no sooner than IMP-011's first week is graded.
3. *(watch)* **Do NOT raise the 0.20 floor.** Today's 0.20–0.40 mid band went **4W/3L net +$17.44** (GOOG/QQQ/
   MU winners at xo 0.24–0.38 would be cut by a higher floor); the weekly review explicitly says hold at 0.20.
4. *(watch)* 90-100 band still −$53.94 (0/1) and 80-89 +$25.38 (50%, 8 tr) — samples unchanged (no 80+ trade
   today); don't touch `ScoreWeights`/threshold.

### Notes for pre-market research
- **Book CLEAN & FLAT into 06-30** — 0 broker positions, 0 DB-open rows, equity $9,398.26 all cash. No carried
  lots, no naked exposure, no phantoms. Nothing locked; full watchlist free.
- **No watchlist-name earnings this week** (carried from 06-29 pre-market — next major tech reports late July).
  Zero binary event risk on the list near-term.
- **Chip-rotation pre-market scare was noise intraday** — despite MU/SNDK −6%+ pre-market, **MU (+1.28%), AMD
  (+1.38%), TSM (+3.12%)** all traded green via the long-only gate (it simply didn't fire longs until a real
  5m trend formed). **No semis park indicated** — the regime call holds; keep the semi roster.
- **C and SPY are persistent weak-cross chop names** (C rejected ×4, SPY ×2 today, all xo<0.20) — these are
  **NOT** watchlist parks (liquid large-caps; IMP-011 now filters their weak crosses in code). No quality park.
- **MSFT** was the biggest loser despite the strongest cross — a *code/timing* watch item (early high-conf
  entry), **not** a symbol-quality issue → keep MSFT (it was +$74.72 on 06-26). No watchlist action.

---

## 2026-06-30 — Daily Review

### Stats
- **9 trades, 7W / 2L → 78% win rate.** Net DB realized **+$61.79** (avg +$6.87). Avg win **+$18.08**,
  avg loss **−$32.39**, **profit factor 1.95**. Account **equity $9,460.02** (cash, **0 open positions** —
  flat), vs open/last_equity **$9,398.23** → mark-to-market day **+$61.79**. **Books exact** — DB net
  **+$61.79 == equity day +$61.79 to the cent** (IMP-009/010 validated a **6th straight session**).
- **All 9 exited via the wall-clock EOD flatten 19:45–19:46 UTC (15:45 ET)** — IMP-007 fired on time; the
  3 reconciled at the real broker-side fill (AMD/SE/TSM, tagged "stop/target filled broker-side"), the rest
  via the bot's own confirmed close. Broker flat, no naked carry, no NAKED page.
- **IMP-011 (MIN_CROSSOVER 0.20) day 2 of its full week — still validating.** 9 entries (count healthy), all
  xo ≥ 0.20 (GOOG entered exactly at the floor; AVGO 0.23 / TSM 0.22 just above) → no over-filtering, 78% win.
- Confidence vs outcome (all-time): 70-79 best (**+$264.05, 60%, 35 tr**), 60-69 **+$103.25 (47%, 68 tr)**,
  80-89 **+$47.38 (56%, 9 tr)**, 90-100 **−$53.94 (0%, 1 tr = AMD 06-25, unchanged)**.

### Trade-by-trade review (Model A throughout; all exited "end-of-day flatten" 19:45–19:46 UTC)
Winners (7):
- **INTC** 10:24 ET @ $137.43, conf 70.2 (xo 0.42) → $140.40 **+$41.63** (+2.16%). **Best trade.** Clean grind.
- **TSLA** 11:02 ET @ $415.80, conf 71.2 (xo 0.39) → $422.56 **+$27.05** (+1.63%). Strong all-day trend.
- **NVDA** 9:33 ET @ $197.46, conf 81.0 (xo 0.99, **rsi 0.35**) → $199.15 **+$22.00** (+0.86%). Early entry,
  sub-1.0 RSI, still won — RSI dip alone is not a loss predictor.
- **TSM** 12:26 ET @ $470.33, conf 76.7 (xo 0.22) → $476.46 **+$18.40** (+1.30%). Stop filled broker-side.
- **AVGO** 10:03 ET @ $376.80, conf 64.1 (xo 0.23) → $378.97 **+$10.85** (+0.58%). Marginal trend.
- **AAPL** 10:53 ET @ $286.60, conf 63.1 (xo 0.34, **rsi 0.15**) → $287.70 **+$5.51** (+0.38%). Churned ~flat.
- **GOOG** 11:56 ET @ $354.02, conf 73.6 (**xo 0.20 — exactly at the IMP-011 floor**) → $354.30 **+$1.13**
  (+0.08%). Essentially flat; the weakest surviving cross barely paid — validates keeping the floor at 0.20.
Losers (2):
- **SE** 9:35 ET @ $92.82, conf 65.0 (xo 0.59, rsi 1.0, **vol 0.05**) → $91.00 **−$34.58** (−1.96%). **Worst.**
  Decent cross but near-zero volume confirmation (thin tape); faded to its stop (filled broker-side).
- **AMD** 9:31 ET @ $559.91, conf 77.6 (**xo 1.00** strongest cross, **rsi 0.00** = overbought extreme, vol 1.0)
  → $552.36 **−$30.20** (−1.35%). First-minute entry on a maxed cross into an overbought RSI; topped and faded;
  stop filled broker-side ~15:07 UTC. Third occurrence of the "strong-cross / early entry → loss" pattern.
- **Root cause:** a low-volatility, megacap-led **drift-up** tape (Q2 close). Names that trended ran (INTC/TSLA
  +1.6–2.2%); the 2 losers faded to their broker-side stops mid-session. Both losers carried one near-zero leg
  (AMD rsi 0.00, SE vol 0.05) — **but that is NOT actionable**: across 06-23..30 a min sub-score < 0.10 went
  **7W/8L (47%)** vs ≥ 0.10 **17W/14L (55%)** — low legs are not a loss discriminator (a floor would cut winners
  ABNB +12.88, TSM +41.19, AMD +14.67, MU +14.37). **Regime / intraday follow-through, not a signal or risk defect.**

### 🔧 The day's real finding — the trailing-stop 422 loop (→ IMP-012)
- **AMD's and SE's broker-side stop legs filled mid-session** (AMD's stop order 698c6cdf "order is not open"
  from **15:07 UTC** onward; SE's 80faa3b7 likewise) — but the bot **never detected it**. The trailing-stop
  ratchet (`replace_stop_price`) kept trying to move those **already-filled** stop orders every candle,
  throwing a **full 422 traceback each time — 504 ERROR lines today** (AMD's "stop" climbing to 572 while it
  had actually exited at 552), and both symbols sat **MANAGING and un-re-enterable for ~4.5h** until the EOD
  flatten finally reconciled them. Books stayed correct (reconcile recorded the true broker fills), but the
  log was swamped and the state was wrong for hours. Fixed by **IMP-012** (below) — exit-infra, IMP-003's
  family; **not** an entry-logic change, so it does not confound IMP-011's evaluation.

### What worked / what didn't
- **Worked:** profitable clean day (78%, +$61.79, books exact 6th straight, broker flat); IMP-011 floor honored
  with no over-filtering (GOOG entered at exactly 0.20 and barely paid — the floor is correctly placed); IMP-007
  wall-clock flatten + IMP-003 reconcile kept the books honest despite the 422 storm; risk contained (worst −1.96%).
- **Didn't:** the trailing-stop 422 loop (504 tracebacks, two symbols stuck MANAGING ~4.5h) — diagnosed and fixed
  as IMP-012. AMD again a loser (−$30.20) on a first-minute strong-cross entry into overbought RSI.

### Lessons & improvement candidates (ranked)
1. **IMP-012 (shipped today):** detect the broker-side stop-leg fill in the trailing path (422 "order is not
   open" → `StopOrderGone`) and reconcile the exit + free the symbol immediately, instead of re-issuing the
   doomed move every candle. Capital/observability + state-correctness; reuses IMP-003's reconcile.
2. *(watch — now 3 occurrences, still do NOT act)* **strong-cross / early entry underperforms:** AMD (06-25,
   conf 91.7), MSFT (06-29, conf 79.7), AMD (06-30, conf 77.6, 9:31 ET, **rsi 0.00 overbought**). Today adds an
   RSI-overbought angle. Candidate: a first-N-minutes / open-spike or RSI-extreme entry guard — but TSLA/NVDA/INTC
   early entries won, and **IMP-011 must finish proving out before any entry-logic change.** Gather more.
3. *(disproven — do NOT build)* a "reject near-zero sub-score" entry filter: 7W/8L vs 17W/14L over 06-23..30.
4. *(watch)* **keep the 0.20 floor** — GOOG entered at exactly 0.20 and made +$0.08; the floor is well-placed,
   neither too high (would cut TSM/AVGO 0.22–0.23 winners) nor too low. Don't touch threshold/weights.

### Notes for pre-market research
- **Book CLEAN & FLAT into 07-01** — 0 broker positions, 0 DB-open rows, equity **$9,460.02** all cash. Nothing
  locked; full watchlist free.
- **AMD** lost again (−$30.20) on a **first-minute (9:31 ET) entry into an overbought RSI** — 2nd AMD loss in the
  recent set (also −$53.94 on 06-25, also early), though it won +$14.67 on 06-29 from a *mid-session* entry. Not a
  park (mega-liquid); flagged as a possible **open-spike / early-entry chopper** — a code/timing watch, not a quality issue.
- **SE** faded to its stop on **near-zero intraday volume** (vol sub-score 0.05) — a recurring thin-tape name; watch,
  but it won +$33.40 on 06-24, so no park.
- **No watchlist-name earnings this week** (next major tech reports late July) → zero binary risk near-term. **Q3
  begins 07-01**; Monday's quarter-end-rebalancing pop was a positioning distortion — don't read it as trend. The
  week's catalyst is **Thursday's June jobs report**; bond market half-day/closed around July 4.

---

## 2026-07-01 — Daily Review

### Stats
- **7 trades, 3W / 4L → 43% win rate.** Net DB realized **+$9.52** (avg +$1.36). Avg win **+$12.38**,
  avg loss **−$6.90**, **profit factor ≈ 1.35**. Account **equity $9,469.51** (cash, **0 open positions**
  at broker — flat), vs last_equity **$9,459.99** → mark-to-market day **+$9.52**. **Books exact** — DB
  net **+$9.52 == equity day +$9.52 to the cent** (IMP-009/010 validated a **7th straight session**).
- **🎉 Seventh consecutive fully clean exit-infra session.** 6 names exited via the **wall-clock EOD
  flatten 19:45 UTC (15:45 ET)** — every market sell FILLED in liquid RTH; **TSLA reconciled at its real
  broker-side stop fill @ $423.93** (order 360c6943, tagged "end-of-day flatten (stop/target filled
  broker-side)"). **0 phantom rows, broker flat, no naked carry, no NAKED page, 0 ERROR/traceback lines,
  0 WARNING lines, no restarts** (service up since the 06-30 21:27 UTC IMP-012 restart).
- Confidence vs outcome (all-time): 70-79 best (**+$255.00, 59%, 39 tr**), 60-69 **+$121.81 (46%, 71 tr)**,
  80-89 **+$47.38 (56%, 9 tr)**, 90-100 **−$53.94 (0%, 1 tr = AMD 06-25, unchanged — no 80+ trade today)**.

### Trade-by-trade review (Model A throughout; all exited "end-of-day flatten" 19:45 UTC)
Winners (3):
- **SE** 14:38 @ $101.66, conf 69.13 (**xo 0.4485** strong, trend 1.0, rsi 1.0, **vol 0.0508** near-zero,
  vlt 0.99) → $102.85 **+$24.99** (+1.17%). **Best trade.** Strong fresh cross carried a clean intraday
  trend despite a thin-volume sub-score — the recurring thin-tape name behaved (won +$33.40 on 06-24 too).
- **AAPL** 14:28 @ $292.98, conf 71.35 (**xo 0.2386**, trend 1.0, rsi 1.0, vol 0.61) → $294.24 **+$10.09**
  (+0.43%). Earliest entry (10:28 ET — *not* an open spike), maxed gate trend, held all day for a modest gain.
- **JPM** 14:58 @ $332.61, conf 70.72 (**xo 0.3936**, trend 0.81, rsi 0.90) → $333.02 **+$2.05** (+0.12%).
  Near-scratch chop; the trailing stop ratcheted but the name went nowhere.
Losers (4):
- **TSLA** 14:40 @ $427.84, conf 70.62 (**xo 0.2610**, trend 1.0, rsi 1.0) → broker-side **trailing-stop fill
  @ $423.93** **−$15.63** (−0.91%). **Worst (largest notional).** Entered after TSLA's +8.45% 06-29 rip /
  quarter-end pop; faded into the Q3-open consolidation, the trailing stop (ratcheted 418.74→423.94 by 15:28,
  still below entry) contained the loss to −0.91%. See the residual-gap finding below.
- **ABNB** 15:25 @ $148.23, conf 61.36 (**xo 0.3118**, trend 1.0, rsi 0.85, **vol 0.0**) → $147.46 **−$6.16**
  (−0.52%). Weakest confidence; drifted down on a zero-volume confirmation.
- **NFLX** 18:56 @ $74.312, conf 74.94 (**xo 0.2062** — weakest surviving cross, just above the 0.20 floor) →
  $74.09 **−$5.55** (−0.30%). Latest entry (14:56 ET); thin late-day cross, no follow-through.
- **AMZN** 15:10 @ $242.39, conf 63.97 (**xo 0.2600**, **vol 0.2051**) → $242.345 **−$0.27** (−0.02%). Scratch.
- **Root cause (all):** a **low-volatility Q3-open consolidation/digestion tape** after the record-quarter
  rally — names that trended a little ran (SE +1.17%, AAPL +0.43%); the rest drifted flat-to-slightly-red near
  their trailing stops. **Regime / intraday dispersion, not a signal or risk defect** — no violent stop-outs
  (worst −0.91%), no risk-limit trips, book honest & flat. Crossover strength was **NOT monotonic within the
  kept (≥0.20) population** (SE 0.45 won big, but JPM 0.39 barely won while TSLA 0.26 / ABNB 0.31 / NFLX 0.21
  lost) — expected noise; IMP-011 filters only the <0.20 dead zone, it does not rank within survivors.

### IMP-011 (MIN_CROSSOVER 0.20) — day 3 of its full week, still validating ✅
- **Filtering fired heavily and correctly:** journald shows weak-cross candidates rejected all session —
  **NFLX** (xo 0.08/0.11/0.13/0.16, ×4), **NVDA** (0.09/0.16/0.16), **MSFT** (0.07/0.17), **C** (0.15),
  **GOOG** (0.19), **UNH** (0.05/0.17) — each `no entry … crossover X.XX < 0.20`, plus many sub-60 confidence
  rejections. All **7 entries had xo ≥ 0.2062** (floor honored; NFLX's *surviving* 0.2062 lot barely cleared).
- **Entry count held** (7 — did not collapse). Win rate 43% on a flat consolidation tape; the two clean
  winners were the strongest-cross names (SE 0.45, JPM 0.39-ish/AAPL). **Do NOT stack another entry-logic
  change** — the weekly directive is to let IMP-011 finish proving out over its first full week (through 07-03).

### IMP-012 first live day — no regression, but a complementary residual gap surfaced (TSLA)
- IMP-012 (shipped 06-30, live from the 06-30 21:27 restart) got its first full trading day: **0 tracebacks,
  0 WARNING lines, no 422 "order is not open" storm** (the 06-30 failure mode did **not** recur). Its *exact*
  scenario (a trail *attempting* to move an already-filled stop) simply didn't arise today.
- **But TSLA exposed the complementary half.** TSLA's trailing stop ratcheted 418.74 → **423.94 by 15:28**,
  then the broker-side stop **filled** — yet **no `StopOrderGone`/reconcile fired mid-session**, so TSLA sat
  **MANAGING (un-re-enterable) for ~4.3h until the EOD reconcile** caught it at 19:45:12. Root: IMP-012 only
  detects the fill when the trail **next tries to replace** the stop; here the stop filled and **no later
  higher-high re-triggered a replace**, so the doomed-move path never ran and the symbol was never freed early.
- **Realized cost today ≈ zero:** books stayed correct (EOD reconciled the true fill), no naked risk, no log
  spam, and TSLA presented no fresh re-entry setup in the window (a same-day re-entry on a just-stopped name is
  arguably undesirable anyway — a mild implicit cooldown). One low-impact occurrence → **watch, do not ship**.

### What worked / what didn't
- **Worked:** profitable clean day (+$9.52, PF 1.35, books exact to the cent 7th straight); IMP-011 filtered
  the weak-cross chop cohort as designed (all entries xo ≥ 0.20) and the entry count held; exit infra clean
  (wall-clock flatten, TSLA's broker-side stop reconciled at the true fill, broker flat, 0 phantoms); risk
  contained (worst −0.91%, no stop-outs beyond the contained TSLA trail exit).
- **Didn't:** a flat consolidation tape gave the kept entries little momentum (4 of 7 drifted red/scratch).
  And IMP-012 left a **complementary detection gap** (a filled stop with no subsequent trail attempt keeps a
  symbol MANAGING until EOD) — surfaced once (TSLA), zero realized cost → logged as the top candidate.

### Lessons & improvement candidates (ranked)
1. **No code change warranted today** (a respectable outcome). The system is profitable, books are exact for
   the 7th straight session, exit infra is clean, **IMP-011 is mid-proving-window** (day 3 of its first full
   week — the weekly directive is to *not* stack another entry-logic change), and **IMP-012 is only 1 live day
   old** and owed more validation. Shipping into that on one low-impact occurrence would risk overfitting.
2. *(new candidate — top of queue, do NOT act yet)* **Free a MANAGING symbol when its broker-side stop fills
   even if the trail never re-fires.** Complements IMP-012: add a lightweight periodic broker reconcile of
   MANAGING positions (e.g. off the IMP-007 watchdog tick, or a manage-loop `get_open_position` check when the
   trail returns HELD) so a stopped-out name returns to WAITING promptly instead of sitting until EOD. It is
   exit-infra (IMP-003/012 family), would **not** confound IMP-011. But it is a critical-path change adding
   broker polling for **~zero realized benefit on one occurrence** — gather a 2nd occurrence (ideally one where
   the stuck-MANAGING actually blocks a real re-entry) before building, exactly as IMP-005/006 were staged.
3. *(watch — 3 occurrences, still do NOT act)* **strong-cross / early entry underperforms** (AMD 06-25 conf
   91.7; MSFT 06-29 conf 79.7; AMD 06-30 conf 77.6 rsi 0.00) — did **not** recur today (no first-N-minute
   entries; earliest was AAPL 10:28 ET, a winner). Gather more; revisit only after IMP-011's week is graded.
4. *(watch)* **Keep the 0.20 floor.** NFLX's surviving 0.2062 lot lost small and JPM (0.39) barely won —
   within-survivor xo is noisy, reinforcing that the floor is correctly placed (cut the <0.20 dead zone, don't
   rank above it). 90-100 still −$53.94 (0/1), 80-89 +$47.38 (56%) — samples unchanged; don't touch weights.

### Notes for pre-market research
- **Book CLEAN & FLAT into 07-02** — 0 broker positions, 0 DB-open rows, equity **$9,469.51** all cash. No
  carried lots, no naked exposure, no phantoms. Nothing locked; full watchlist free.
- **No watchlist-name earnings this week** (next major tech reports late July: META 07-29, AAPL 07-30) → zero
  binary risk near-term. The week's macro binary is **Thursday's June jobs report (NFP)**; note the bond-market
  half-day / July-4 holiday context. A low-volatility Q3-open consolidation tape today — no regime park signal.
- **TSLA** was the day's real loser (−$15.63, trailing-stop out) after unwinding its 06-29 rip / quarter-end
  pop — a **regime/timing** fade, **not** symbol quality (mega-liquid, no trend break) → **keep, no park**.
- **SE** won again on a thin tape (+1.17% despite vol sub-score 0.05) — the recurring thin-tape name is
  behaving (also +$33.40 06-24); **keep, watch the thin volume but no park**.
- **Entry/symbol quality fine** — all 7 names signalled and filled cleanly; the 4 small losses were flat-tape
  dispersion, not symbol failure → **no quality parks**. Weak-cross rejects (NFLX/NVDA/MSFT/GOOG/C/UNH xo<0.20)
  are code-filtered by IMP-011, **not** watchlist parks (all liquid large-caps).

---

## 2026-07-02 — Daily Review

### Stats
- **7 trades, 3W / 4L → 43% win rate.** Net DB realized **+$10.21** (avg +$1.46). Avg win **+$24.77**,
  avg loss **−$16.02**, **profit factor ≈ 1.16**. Account **equity $9,479.69** (cash, **0 open positions**
  at broker — flat), vs last_equity **$9,469.48** → mark-to-market day **+$10.21**. **Books exact** — DB
  net **+$10.21 == equity day +$10.21 to the cent** (IMP-009/010 validated an **8th straight session**).
- **🎉 Eighth consecutive fully clean exit-infra session.** 5 names exited via the **wall-clock EOD flatten
  19:45 UTC (15:45 ET)** — every market sell FILLED in liquid RTH; **GOOG and SE reconciled at their real
  broker-side stop fills** (@353.25 / @103.50, tagged "end-of-day flatten (stop/target filled broker-side)").
  **0 phantom rows, broker flat, no naked carry, no NAKED page, 0 ERROR/traceback lines, 0 WARNING lines,
  no restarts** (service up since the 06-30 21:27 UTC IMP-012 restart — so 07-01 and 07-02 both ran on IMP-012).
- **IMP-011 (MIN_CROSSOVER 0.20) — day 4 of its full week, still validating ✅.** Journald shows **7
  weak-cross candidates rejected** (`crossover X.XX < 0.20`); all **7 entries had xo ≥ 0.2083** (floor
  honored). Entry count held (7, did not collapse). See below.
- Confidence vs outcome (all-time): 70-79 best (**+$257.74, 59%, 41 tr**), 60-69 **+$129.30 (46%, 76 tr)**,
  80-89 **+$47.38 (56%, 9 tr)**, 90-100 **−$53.94 (0%, 1 tr = AMD 06-25, unchanged — no 80+ trade today)**.

### Trade-by-trade review (Model A throughout)
Winners (3):
- **NFLX** 14:05 @ $75.739, conf 67.54 (**xo 0.35** strongest cross, trend 1.0, rsi 1.0, **vol 0.19**, vlt 0.94)
  → EOD flatten @ $77.90 **+$62.67** (+2.85%). **Best trade by far** (> the whole day's net). Earliest entry
  (10:05 ET — *not* an open spike), strong fresh cross + maxed gate; rode a clean all-day uptrend. Textbook
  strong-cross winner and the day's carry.
- **AAPL** 14:52 @ $306.11, conf 61.31 (**xo 0.2105** — just above the floor, trend 1.0, **vol 0.0**) →
  EOD flatten @ $307.836 **+$8.63** (+0.56%). Maxed gate trend on a near-floor cross; held for a modest gain.
- **MSFT** 14:50 @ $390.20, conf 77.07 (**xo 0.34**, trend 0.85, vol 1.0, vlt 1.0) → EOD flatten @ $390.70
  **+$3.00** (+0.13%). 2nd-strongest cross + highest confidence, yet only scratched — within-survivor xo
  was **not** monotonic today (strongest NFLX won big, 2nd-strongest MSFT ~flat, at-floor AAPL won small).
Losers (4):
- **GOOG** 14:08 @ $359.84, conf 61.11 (**xo 0.28**, **trend 0.6838 — weakest gate of the day**, vol 0.29) →
  broker-side **stop @ $353.25** 15:42 **−$32.95** (−1.83%). **Worst.** The weakest 5m gate trend of the seven
  faded straight to its stop; the 3×ATR stop did its job. (Stuck MANAGING until EOD — see the residual finding.)
- **SE** 15:00 @ $105.135, conf 61.54 (**xo 0.2182** near-floor, trend 1.0, **vol 0.0** near-zero) → broker-side
  **stop @ $103.50** 16:24 **−$21.26** (−1.56%). Recurring thin-tape name — decent gate but zero volume
  confirmation; faded to its stop (also faded to stop on 06-30 vol 0.05, but won +$33.40 06-24 / +$24.99 07-01).
- **AMZN** 15:00 @ $245.233, conf 61.34 (**xo 0.2083** — the day's weakest surviving cross, exactly at the floor,
  vol 0.16) → EOD flatten @ $243.632 **−$9.61** (−0.65%). Near-floor cross, mild drift.
- **COST** 16:51 @ $948.88, conf 70.90 (**xo 0.22**, trend 1.0, vol 0.61) → EOD flatten @ $948.61 **−$0.27**
  (−0.03%). Latest entry (12:51 ET); scratch.
- **Root cause (all):** an **NFP-morning, holiday-shortened tape** (June jobs pulled a day early ahead of the
  07-03 Independence-Day close) following 07-01's sharp **SMH −5.4%** semi selloff. Only NFLX found a clean
  trend (+2.85%); the rest drifted flat-to-slightly-red near their stops. **Regime / intraday dispersion, not
  a signal or risk defect** — no violent stop-outs (worst −1.83%), no risk-limit trips, book exact & flat.
  Notably **4 of the 7 entries clustered right at the IMP-011 floor** (xo 0.208–0.224: GOOG/AAPL/AMZN/SE/COST)
  and went **1W/3L+1scratch** — the two clean winners were the two strongest crosses (NFLX 0.35, and MSFT 0.34
  scratched); consistent with the floor filtering the <0.20 dead zone but not ranking within survivors.

### 🔧 The day's real finding — IMP-012's complementary residual gap recurred 2× (GOOG, SE)
- **Both broker-side stops filled mid-session but the symbols weren't freed until the EOD reconcile:** GOOG's
  stop filled **15:42:02 @353.25** yet GOOG sat **MANAGING ~4h** until reconciled at 19:45; SE's stop filled
  **16:24:48 @103.50** yet SE sat **MANAGING ~3h21m** until 19:45. This is the **exact residual gap flagged on
  07-01 (TSLA)** — now **3 occurrences over 2 days.** Root: IMP-012 only detects a filled stop when the trail
  **next tries to replace** it (422 → `StopOrderGone`); when the stop fills and **no later higher-high
  re-triggers a replace**, the doomed-move path never runs, so the fill is caught only at the 19:45 EOD reconcile.
- **Realized cost again ≈ zero:** books stayed exact (EOD reconciled the true broker fills — the +$10.21 ties to
  equity to the cent), no naked risk, **no log spam** (0 tracebacks — IMP-012's 422-storm fix held), and **neither
  GOOG nor SE presented a fresh valid cross+gate re-entry** while stuck (GOOG kept drifting below entry; SE below
  its stop) — so **no real re-entry was blocked**. The stuck-MANAGING even acts as a mild implicit same-day
  cooldown on a just-stopped name (arguably desirable). See candidate #1.

### What worked / what didn't
- **Worked:** profitable clean day (+$10.21, PF 1.16, **books exact 8th straight**); IMP-011 filtered the
  weak-cross chop cohort as designed (7 rejects, all entries xo ≥ 0.208, count held); NFLX's strong-cross long
  carried the day; exit infra clean (wall-clock flatten, GOOG/SE broker-side stops reconciled at the true fill,
  broker flat, 0 phantoms, 0 tracebacks); risk contained (worst −1.83%, no risk-limit trips).
- **Didn't:** a flat/dispersed NFP-morning tape gave the kept entries little momentum (4 of 7 drifted red/scratch).
  And **IMP-012's complementary detection gap recurred twice** (GOOG/SE stopped mid-session, freed only at EOD) —
  now 3 occurrences, still zero realized cost → the top staged candidate (below), deliberately not shipped today.

### Lessons & improvement candidates (ranked)
1. **No code change warranted today** (a respectable, well-precedented outcome — cf. 06-29 & 07-01). The system
   is profitable, **books are exact for the 8th straight session**, exit infra is clean, and **IMP-011 is
   mid-proving-window** (day 4 of its first full week; the weekly directive is to *not* stack another change and
   let it finish proving out through the 07-03 weekly grade). The only anomaly — the MANAGING-until-EOD residual —
   has **zero realized cost** and did not block a re-entry.
2. *(top of queue — staged, NOT yet shipped; 3 occurrences now)* **Free a MANAGING symbol when its broker-side
   stop fills even if the trail never re-fires.** Complements IMP-012: add a lightweight periodic broker reconcile
   of MANAGING positions — cheapest clean seam is to piggyback the existing **IMP-007 wall-clock watchdog `tick()`**
   (already runs every 30s and already calls broker APIs at EOD) with a bounded `get_open_position` check for
   symbols currently in MANAGING, routing a detected fill through the proven `reconcile_exit` path. It is exit-infra
   (IMP-003/012 family) and would **NOT** confound IMP-011. **Why still not shipped:** it adds broker polling to a
   near-critical path for **~zero realized benefit** (3 occurrences, all zero-cost, none blocked a real re-entry),
   the streak is clean, and IMP-011's proving window runs through 07-03. **Ship trigger:** after IMP-011's first
   full week is graded (07-03 weekly), OR the next occurrence that demonstrably **blocks a real re-entry** — exactly
   how IMP-005/006 were staged. Do it on a calm, non-event session.
3. *(watch — 3 occurrences, still do NOT act)* **strong-cross / early entry underperforms** (AMD 06-25 conf 91.7;
   MSFT 06-29 conf 79.7; AMD 06-30 conf 77.6 rsi 0.00) — did **not** recur today (earliest entry NFLX 10:05 ET was
   the day's *best* trade). Gather more; revisit only after IMP-011's week is graded.
4. *(watch)* **Keep the 0.20 floor.** AMZN entered at exactly 0.2083 and lost small, AAPL at 0.2105 won small —
   within-survivor xo remains noisy (strongest NFLX won, 2nd-strongest MSFT scratched), reinforcing the floor is
   correctly placed (cut the <0.20 dead zone, don't rank above it). 90-100 still −$53.94 (0/1), 80-89 +$47.38
   (56%) — samples unchanged (no 80+ trade today); don't touch threshold/weights.

### Notes for pre-market research
- **Book CLEAN & FLAT into the next session (Mon 07-06; markets CLOSED Fri 07-03 for Independence Day)** — 0 broker
  positions, 0 DB-open rows, equity **$9,479.69** all cash. No carried lots, no naked exposure, no phantoms.
  Nothing locked; full watchlist free.
- **No watchlist-name earnings near-term** (next major tech: META 07-29, AAPL 07-30) → zero binary risk. The June
  jobs report is behind us; a long holiday weekend follows (Fri 07-03 closed). No regime park signal from a
  dispersed NFP-morning tape.
- **GOOG** was the day's worst (−$32.95, stopped) on the **weakest 5m gate trend of the group (0.68)** — a
  regime/timing fade (mega-liquid, no trend break), **not** symbol quality → keep, no park.
- **SE** faded to its stop again on **near-zero intraday volume** (vol sub-score 0.0) — the recurring thin-tape
  name; but it won +$33.40 (06-24) and +$24.99 (07-01), so **watch the thin volume, no park**.
- **QCOM park-watch carries** (flagged 07-02 pre-market: below both MAs, thinnest megacap-semi liquidity, no real
  trades) — action a park on a **calm, non-event session** if QCOM fails to reclaim its 20MA; today's NFP tape was
  the wrong day to judge it, and it didn't trade. Entry/symbol quality otherwise fine — all 7 names signalled and
  filled cleanly; weak-cross rejects (code-filtered by IMP-011) are **not** watchlist parks.

---

## 2026-07-03 — Daily Review

### Stats
- **No trades today — US market HOLIDAY (Independence Day observed).** July 4, 2026 is a **Saturday**, so the
  NYSE/NASDAQ holiday was observed **Friday 2026-07-03** → markets **closed all day**. Confirmed authoritatively
  via Alpaca: `/v2/clock` `is_open=false` (next_open **2026-07-06 09:30 ET**, Monday), and `/v2/calendar` for
  the week lists trading days **07-01, 07-02, 07-06, 07-07 — 07-03 absent.** This was fully anticipated in the
  07-02 entry's pre-market notes.
- **0 trades, 0 orders, 0 positions.** DB `dbo.trades` today = **0 rows**; Alpaca `/v2/orders?after=07-03` = **0**;
  `/v2/positions` = **0**. `bot.report --days 1`: 0 closed trades. **Book flat & exact** — nothing carried, no
  naked exposure, no phantoms.
- **Account equity $9,479.66** (all cash), essentially unchanged from 07-02's $9,479.69 (a $0.03 broker
  bookkeeping drift, no marks — flat holiday). Service **active, 0 restarts** since the 06-30 21:27 UTC IMP-012
  boot → 07-01/07-02/07-03 all ran on IMP-012 with no intervening restart.
- Confidence vs outcome (all-time, **unchanged** — no trade today): 70-79 best **+$257.74 (59%, 41 tr)**,
  60-69 **+$129.29 (46%, 76 tr)**, 80-89 **+$47.38 (56%, 9 tr)**, 90-100 **−$53.94 (0%, 1 tr)**.

### Trade-by-trade review
- **None — market closed.** Root-cause of the zero-trade day is **exogenous (exchange holiday), not the
  strategy, watchlist, gates, or any defect.** With the market shut there were **no trades on the tape all day**,
  hence no candles were aggregated and no entries evaluated (journald's last data line is **07-02 20:44 UTC**,
  after the 07-02 close; **zero log lines for 07-03**, exactly as expected for a dark session). The
  `market_is_open()` hours-gate and the empty feed both independently guarantee no entries on a closed day.

### What worked / what didn't
- **Worked:** the bot correctly did **nothing** on a holiday — no spurious entries, no errors, no restarts, book
  stayed flat & exact into a 3-day weekend. Process healthy (active since 06-30). DB↔broker↔report all agree at
  zero. IMP-012 exit-infra streak intact (no exits to test, but nothing broke).
- **Didn't:** N/A — no trading activity to critique. (Operational aside, **out of scope for this routine:** the
  *morning pre-market Claude routine* failed today with an expired OAuth token — moot, since the market was
  closed and no watchlist decision was needed; that is routine-infra, not USTradeBot code.)

### Lessons & improvement candidates (ranked)
1. **No code change warranted — zero-data holiday.** Making any change off a closed-market session with **no
   trades and no new evidence** would be a textbook random/overfit change and is explicitly forbidden. "Reviewed,
   no change warranted" is the correct outcome (cf. 06-29, 07-01, 07-02). The system is profitable, books are
   exact, exit infra is clean, and IMP-011's first-full-week proving window completes with **today's weekly
   grade** — the discipline is to add nothing here.
2. *(staged, unchanged — decision belongs to the weekly routine, NOT here)* **Free a MANAGING symbol when its
   broker-side stop fills even if the trail never re-fires** (piggyback the IMP-007 wall-clock `tick()` with a
   bounded `get_open_position` reconcile of MANAGING names; complements IMP-012). Still **3 zero-cost
   occurrences** (TSLA 07-01, GOOG+SE 07-02), none blocked a real re-entry. **Ship trigger** was "after IMP-011's
   first full week is graded (07-03 weekly) OR the next occurrence that demonstrably blocks a re-entry." Today's
   holiday produced **no new occurrence and no new evidence**, so it does not trip the trigger — the green-light
   call is for the **07-03 weekly-review routine** to make on a calm, non-event *trading* session, not for this
   dark-session daily review to force.
3. *(watch, unchanged)* strong-cross/early-entry underperformance (3 obs) and the 0.20 crossover floor — both
   need live trading days to accumulate evidence; nothing to add from a closed session.

### Notes for pre-market research
- **Next session = Monday 2026-07-06** (regular full day, 09:30–16:00 ET / 13:30–20:00 UTC). **07-03 was a
  full-day holiday close; 07-04 Sat, 07-05 Sun.** Book is **CLEAN & FLAT** into Monday — 0 broker positions, 0
  DB-open rows, equity **$9,479.66** all cash. Nothing locked; **full watchlist free.**
- **No watchlist-name earnings near-term** (next major tech: META 07-29, AAPL 07-30) → zero binary risk on the
  Monday reopen. Expect a **post-holiday-weekend gap/regime reset** — first candles Monday may be thin/gappy in
  the opening minutes; the warmup (IMP-008) rebuilds ribbons on boot so gates are ready at the open.
- **Carry-over watch items from 07-02 (unchanged by the holiday):** **SE** — recurring thin-tape name (faded to
  stop on near-zero volume 06-30 & 07-02, but won 06-24/07-01) → *watch volume, no park.* **QCOM** — park-watch
  (below both MAs, thinnest megacap-semi liquidity, no real trades) → action a park only on a **calm non-event
  trading session** if it fails to reclaim its 20MA. **GOOG** — 07-02's worst was a regime fade on the weakest 5m
  gate, not symbol quality → keep. No new park signals from a dark session.
- **Confirm the morning pre-market routine actually runs Monday** — today's routine failed on an expired Claude
  OAuth token (re-authed this session); verify the 07-06 11:30 UTC premarket job produces a fresh watchlist
  review rather than silently erroring.

---

## 2026-07-06 — Daily Review

### Stats
- Closed trades (DB): **11** — 6W / 5L → **55% win rate**. Net realized P&L **−$52.33** (avg −$4.76/trade).
  Avg win **+$8.56**, avg loss **−$20.74**, **profit factor ≈ 0.50** (losers ~2.4× the winners). Account
  **equity $9,427.33** (all cash, **0 open positions** — book flat).
- **Books exact to the cent.** DB net −$52.33 == equity move (premarket $9,479.66 → $9,427.33 = −$52.33).
  DB↔broker↔report all agree; every entry/exit matches the Alpaca fill (IMP-009/010 entry-fill + IMP-012
  broker-side-fill reconcile all holding; no phantoms, nothing carried).
- Confidence vs outcome (all-time, **updated by today's AVGO conf-96 loss**): **70-79 the peak** +$246.28
  (57%, 44 tr), 60-69 +$157.56 (48%, 81 tr), **80-89 mediocre +$34.02 (55%, 11 tr), 90-100 negative
  −$109.74 (0% win, 2 tr)**. The curve is **non-monotonic and inverts at the top** — the basis for IMP-013.

### Trade-by-trade review
All entries Model A; all 11 closed at/around the **19:45 UTC EOD flatten** — **4 had already hit their
broker-side (trailed) stops intraday** (annotated *"stop/target filled broker-side"*), the other 7 were
market-flattened at the close. **No target hit, no bearish-cross early exit fired all day.**
- **AVGO** (entry 13:36 @ 381.56, conf **96.28** [x1.0/t1.0/rsi1.0/v1.0/**vol0.75**], qty 9) → broker stop
  @375.36 at 14:56 → **−$55.80 (−1.62%)**. **Day's biggest loss = the day's highest confidence = the day's
  biggest size** (~37% BP via Model A). Entered 6 min after the open into the chip gap-up, faded. Root:
  **regime (opening-spike fade) + sizing (conf→size bet the most on the worst setup).**
- **INTC** (14:07 @ 126.20, conf **84.66** [x0.65/t1.0/rsi1.0/v1.0/**vol0.67**], qty 15) → stop @124.60 at
  15:12 → **−$24.00 (−1.27%)**. 2nd-highest conf, 2nd-biggest loss. Same open-drive semis fade; **lowest
  volatility sub-score of the book (0.67 = spikiest entry bar).**
- **MU** (14:34 @ 1011.04, conf 70.36, qty 1) → stop @997.57 at 15:08 → **−$13.47 (−1.33%)**. Semis fade.
- **AMD** (14:37 @ 568.05, conf 60.30 [x0.21 — just above the IMP-011 floor], qty 1) → stop @560.55 at
  15:17 → **−$7.50 (−1.32%)**. Marginal cross, semis fade.
- **TSM** (14:07 @ 456.57, conf 74.99, qty 3) → EOD flatten @455.59 → **−$2.94 (−0.21%)**. Small drift loss.
- **AAPL** (14:14 @ 309.85, conf 64.28, qty 4) → EOD @313.66 → **+$15.23 (+1.23%)**. Best trade; non-semi
  megacap that held the trend to the close.
- **SE** (15:47 @ 104.82, conf 66.33, qty 15) → EOD @105.57 → **+$11.25 (+0.72%)**. Trailing stop ratcheted
  (103.85→103.98) as it held; the thin-tape name *worked* today (as 06-24/07-01, not 06-30/07-02).
- **QQQ** (13:40 @ 721.17, conf 80.48, qty 3) → EOD @724.72 → **+$10.65 (+0.49%)**. Index, held.
- **BABA** (13:58 @ 97.31, conf 67.23, qty 17) → EOD @97.83 → **+$8.82 (+0.53%)**. Non-semi, held.
- **C** (13:58 @ 143.08, conf 79.39, qty 16) → EOD @143.39 → **+$4.96 (+0.22%)**. Financial, held small.
- **TSLA** (16:27 @ 417.27, conf 65.30, qty 3) → EOD @417.43 → **+$0.47 (+0.04%)**. Late entry, flat scratch.

### What worked / what didn't
- **Worked:** win *count* was fine (6/11); IMP-011 floor held (AMD x0.21 was the lowest survivor, all others
  ≥0.25); books exact; SE/BABA/C/AAPL/QQQ (non-semi/index) held their small trends to the close; trailing
  stop ratcheted correctly on SE/BABA. Service healthy, 0 restarts intraday, 0 naked overnight.
- **Didn't:** **P&L, not win rate, was the problem** — losers averaged −$20.74 vs wins +$8.56 (PF 0.50). Two
  structural threads: (1) **the confidence→size link is backwards** — the two highest-confidence trades
  (AVGO 96, INTC 85) were the two biggest losers, and Model A sized them largest, so the single biggest loss
  was the highest-conf/biggest-size trade; (2) **regime**: a post-holiday chip-led gap-up (research expected
  Nasdaq +1.1% / SMH +2.4%) that **faded** — the 4 semis/megacap-chip names entered in the first ~100 min all
  stopped out ~14:56–15:17, while the non-chip holds won. **Volatility sub-score cleanly split the book today**
  (all 6 winners vol=1.0; the 2 big losers had the lowest, 0.75/0.67 = spikiest bars) — a strong *single-day*
  signal, logged for accumulation, **not acted on** (one day = overfit risk; cf. IMP-011 needed 4 clean days).
- **Minor:** one Telegram send timed out (TSM exit alert, 19:45) — side-channel, swallowed, no trading impact.
- **IMP-012 residual gap recurred 4×** (AVGO/MU/INTC/AMD each sat MANAGING ~4h after the stop filled, caught
  only at the 19:45 EOD reconcile) — **zero realized cost, no re-entry demonstrably blocked** (the staged
  MANAGING-watchdog ship-trigger still not tripped; unchanged).

### Lessons & improvement candidates (ranked)
1. **[SHIPPED — IMP-013] Cap the confidence→size ramp (`SIZE_CONFIDENCE_CAP`, default 85).** Highest-impact,
   capital-protective, entry-neutral. Model A/B scaled size linearly to conf 100 assuming edge grows with
   confidence; the all-time 138-trade curve shows the opposite above the ~70s (70-79 peak; 80-89 mediocre;
   90-100 0% win / −$110), so the ramp bet the most capital on its worst cohort — today's AVGO (conf 96,
   ~37% BP) was the biggest loss. The cap sizes a >cap candidate as if it scored the cap: **only ever shrinks
   the top-band position, never enlarges one, never blocks an entry, never touches the stop/threshold.**
2. *(watch — accumulate, do NOT ship yet)* **Volatility-sub-score floor for entries.** Today it split the book
   perfectly (winners vol=1.0; big losers 0.67/0.75), consistent with an opening-spike-fade read, but it is a
   **single day** — needs ≥3–4 corroborating sessions before it earns a filter (the IMP-011 discipline). If it
   holds, a `MIN_VOLATILITY`-style floor is the natural next entry-quality change after IMP-011's crossover floor.
3. *(watch, unchanged)* **Opening-drive / time-of-day entry quality.** The 4 stop-outs all entered in the first
   ~100 min into a gap-up that faded; but 4 winners also entered early (QQQ 13:40, C/BABA 13:58) — not a clean
   time cutoff yet. Keep observing whether early *chip* entries specifically underperform on gap-up-fade days.
4. *(staged, unchanged — weekly-routine call)* **Free a MANAGING symbol when its broker stop fills even if the
   trail never re-fires** (piggyback IMP-007 wall-clock `tick()` with a bounded `get_open_position` reconcile).
   4 fresh zero-cost occurrences today; still no demonstrably-blocked re-entry → ship-trigger not tripped.

### Notes for pre-market research
- **Book CLEAN & FLAT into 07-07** — 0 broker positions, 0 DB-open rows, equity **$9,427.33** all cash.
  Nothing locked; full watchlist free.
- **Regime caution:** today was a **chip-led gap-up that FADED** — the semis/megacap-chip cohort (AVGO, INTC,
  MU, AMD, TSM) all gave back at the open and stopped out; the non-chip holds (AAPL, QQQ, C, BABA, SE) won.
  If 07-07 gaps up again on chips, **expect the same open-drive fade risk** — the ribbon fires freshest crosses
  right at the extended open. IMP-013 now trims size on the very-high-confidence (often most-extended) of these.
- **AVGO** — highest-conf loser two-in-a-row pattern; **INTC/MU/AMD** — semis that faded the open. Not park
  candidates (all intact/recovering trends per 07-06 premarket), but **flag the chip cohort as gap-up-fade-prone.**
- **SE worked today** (+$11.25 on adequate volume) — the thin-tape watch stays "watch volume, no park."
- **SPCX joins the Nasdaq-100 at today's (07-07) open** + Samsung prelim Q2 — still too new for the ribbon; note only.
- **No watchlist-name earnings this week** (next: META 07-29, AAPL 07-30) → zero binary risk.

---

## 2026-07-07 — Daily Review

### Stats
- Closed trades (DB): **11** — **1W / 10L → 9% win rate.** Net realized P&L **−$179.00**
  (avg **−$16.27**/trade). Avg win **+$2.88** (n=1, UNH), avg loss **−$18.19**, **profit factor
  ≈ 0.02** (the lone win was a +$2.88 scratch). Account **equity $9,248.30** (all cash, **0 open
  positions** — book flat). **Worst day since 06-17** (−$181).
- **Books exact to the cent.** DB net −$179.00 == equity move (premarket $9,427.30 → $9,248.30 =
  **−$179.00**). DB↔broker↔report all agree; every entry/exit matches the Alpaca fill (IMP-008/009/010
  price-truth + IMP-012 broker-side-fill reconcile all holding). **0 phantoms, nothing carried, no
  naked overnight, no NAKED page.** Exit infra clean again (wall-clock flatten fired 19:45 UTC, all
  sells filled in liquid RTH before 16:00 ET).
- **IMP-013 (SIZE_CONFIDENCE_CAP=85) did NOT bind today** — the day's highest confidence was NFLX
  79.51 (< 85), so no position was above the cap; today is not an IMP-013 test (await a >85 entry).
- Confidence vs outcome (all-time, dragged down by today's 60-79 losers): **70-79 +$189.62 (53%, 47 tr)**
  [was +$246], **60-69 +$35.23 (45%, 89 tr)** [was +$157], 80-89 +$34.02 (55%, 11 tr, unchanged),
  **90-100 −$109.74 (0%, 2 tr, unchanged)**.

### Trade-by-trade review (Model A throughout; entry times UTC)
Every entry cleared the gate (5m 21/34/55 stacked & rising) + a fresh 1m cross, then **faded** — a
broad, market-wide false-breakout tape. **All crosses were mid-band (xo 0.21–0.35); ZERO strong
crosses (≥0.40) were available all day** — the market was choppy, not trending, so no high-conviction
setup existed. 3 hit broker-side (trailed) stops, 8 rode to the EOD flatten.
- **C** 13:47 @ 144.01, conf 60.69 (xo 0.23, trend 0.94, **vol 0.0**) → broker stop @141.10 → **−$31.39
  (−1.98%)**. **Biggest loss**; stopped near the −2% floor. Financials faded with the tape.
- **NFLX** 14:38 @ 77.47, conf **79.51** (xo 0.32, all confirms 1.0) → broker stop @76.30 → **−$26.90
  (−1.51%)**. Highest-confidence trade of the day → 2nd-biggest loss; the tape reversed on the strongest-scored name.
- **WMT** 14:12 @ 113.24, conf 63.50 (xo 0.28) → EOD @111.66 → **−$22.13 (−1.40%)**. Drifted to near-stop, flattened.
- **SE** 18:06 @ 105.87, conf 73.05 (xo 0.31, vol 1.0) → EOD @104.19 → **−$21.84 (−1.59%)**. Latest entry (14:06 ET) still faded — not a purely opening-drive problem.
- **GOOG** 14:14 @ 369.73, conf 61.60 (xo 0.22) → EOD @362.99 → **−$20.22 (−1.82%)**.
- **AMZN** 13:47 @ 246.51, conf 61.01 (**xo 0.35 = strongest cross**, trend 0.67) → broker stop @241.54 → **−$18.48 (−1.07%)**. The day's strongest crossover was a stop-out.
- **MSFT** 13:51 @ 392.34, conf 62.95 (xo 0.24) → EOD @389.28 → **−$12.24 (−0.78%)**.
- **JPM** 13:43 @ 340.94, conf 65.52 (xo 0.35) → EOD @338.92 → **−$12.12 (−0.59%)**.
- **NVDA** 16:46 @ 197.37, conf 65.49 (xo 0.31) → EOD @195.93 → **−$8.64 (−0.73%)**. Late (12:46 ET) semis entry, faded.
- **ABNB** 14:33 @ 149.48, conf 72.42 (xo 0.27, all confirms 1.0) → EOD @148.76 → **−$7.92 (−0.48%)**.
- **UNH** 15:07 @ 426.04, conf 68.25 (**xo 0.21 = weakest cross**, vol 0.45) → EOD @427.00 → **+$2.88
  (+0.23%)**. **The ONLY winner — and it had the lowest crossover and a below-average volume sub-score.**
- **Root cause (all 11):** **market regime — a broad false-breakout / whipsaw day.** The 5m gate opened
  and the 1m cross fired on name after name, but there was no follow-through anywhere; the long-only
  ribbon has no edge when the whole tape reverses after every breakout. **Not signal-scorer failure, not
  infra, not stop placement** (losses contained, worst −1.98% at C's stop) — the strategy's known
  "no-edge-in-chop" weakness, on a severe day.

### What worked / what didn't
- **Worked:** exit infra flawless (wall-clock flatten 19:45, all fills real, broker flat, books exact to
  the cent, 0 phantoms, no naked carry); risk containment held (worst single trade −1.98%, no risk-limit
  event, no blowup); IMP-011 floor honored (weakest survivor UNH xo 0.21). Service healthy, 0 restarts,
  0 errors/504/422 all session.
- **Didn't:** the strategy took **11 losing/scratch entries into a persistently adverse tape** with no
  mechanism to stand down as the day went against it (see candidate #2). **No sub-score discriminated the
  outcome today** — the only winner (UNH) had the *lowest* crossover; the highest crosses (AMZN/JPM 0.35,
  NFLX 0.32) lost; and **volatility was ≈1.0 on 10 of 11 names yet 10 lost**, which directly **contradicts
  the 07-06 volatility-floor hypothesis** (07-06 the 2 big losers had the *low* vol sub-scores). One
  adverse regime day, cleanly attributable to the tape.

### Lessons & improvement candidates (ranked)
1. **NO CODE CHANGE WARRANTED — "reviewed, no change warranted" is the correct outcome.** Today is a
   single broad-regime false-breakout day; **today's own data contradicts every ready entry-quality
   candidate** — raising the `MIN_CROSSOVER` floor would have removed the day's only winner (UNH xo 0.21)
   and kept the losers (highest crosses lost); a `MIN_VOLATILITY` floor would have blocked ~0 losers (vol
   ≈1.0 on 10/11). Shipping any of these off today would be textbook overfitting to one noisy day, which
   the mandate forbids ("Never overfit to one day"). The weekly (07-03) said **keep IMP-011 at 0.20 — do
   not raise** — honored. Books are exact, exit infra clean, system profitable overall (best week 07-03
   +1.84%). **IMP-013 shipped 07-06 is still unobserved** (didn't bind today) — stacking a second change
   before evaluating it would muddy attribution. Add nothing.
2. *(NEW candidate — accumulate, do NOT ship on one day)* **Broad-adverse-day stand-down / daily-loss
   circuit breaker.** The bot has **no daily-drawdown or consecutive-loss entry halt** (only the feed-loss
   `entries_allowed` latch). Today it kept opening fresh entries (NVDA 16:46, SE 18:06) while the whole day
   went red. A halt on cumulative daily drawdown would be capital-protective and *general* (would also have
   helped 06-17). **Caveat that blocks shipping today:** most losses realized only at the 19:45 EOD flatten
   (positions rode open all day), so a *realized*-loss trigger would not have fired intraday — a correct
   version needs live **mark-to-market** equity/open-P&L tracking (a larger critical-path change). Design
   it on MTM drawdown, gather ≥1–2 more broad-adverse days as evidence, and ship deliberately — NOT rushed
   off one session (same discipline that made IMP-011 wait 4 clean days).
3. *(watch — 07-06's volatility candidate now NON-corroborated)* The `MIN_VOLATILITY` floor idea from
   07-06 (winners vol=1.0, big losers 0.67/0.75) **failed to replicate today** (all-high-vol book, all
   losing). Two contradictory sessions → the volatility sub-score is **not** a reliable outcome
   discriminator. Down-weight this candidate; needs a genuinely clean multi-day signal before it earns a filter.
4. *(staged, unchanged — weekly-routine call)* IMP-012 residual MANAGING-until-EOD gap recurred (NFLX/AMZN/C
   stops filled intraday, reconciled only at the 19:45 EOD sweep) — **zero realized cost, no re-entry
   demonstrably blocked**; ship-trigger still not tripped.

### Notes for pre-market research
- **Book CLEAN & FLAT into 07-08** — 0 broker positions, 0 DB-open rows, equity **$9,248.30** all cash.
  Nothing locked; full watchlist free.
- **Regime, NOT symbols:** all 11 names signalled and filled cleanly; the 1W/10L was a **broad
  false-breakout tape** where every breakout reversed — **no watchlist parks indicated on quality
  grounds.** C/NFLX/WMT/GOOG/SE were the biggest losers today purely because they faded with the market,
  not because they're broken; all are liquid, intact names. Do not park for a one-day regime loss.
- **Every entry was a mid-band cross (xo 0.21–0.35); zero strong crosses (≥0.40) fired all day** — the
  market simply wasn't trending. On a choppy tape the strategy makes many low-conviction entries with no
  edge; there is no watchlist fix for that (it's a regime, not a symbol, issue).
- **UNH** was the lone green (+$2.88) — behaved; keep. **SE** faded today (−$21.84) after working 07-06
  (+$11.25) — regime, not a fresh park signal; thin-tape watch continues ("watch volume, no park").
- **QCOM stays parked** (actioned 07-06 pre-market). **SPCX** (joined Nasdaq-100 07-07) still too new for
  the ribbon. No watchlist-name earnings this week (next: META 07-29, AAPL 07-30) → zero binary risk.

---

## 2026-07-08 — Daily Review

### Stats
- Closed trades (DB): **7** — 5W / 2L → **71% win rate**. Net realized P&L **+$54.69**
  (avg +$7.81/trade). Avg win **+$14.14**, avg loss **−$8.01**, **profit factor ≈ 4.4**.
  Account **equity $9,302.96** (= last_equity $9,248.27 + $54.69; all cash, **0 open positions**).
- **Books EXACT.** Equity delta (+$54.69) == DB net (+$54.69) to the cent; broker holds 0
  positions, 14 orders filled today (7 entries + 7 exits), 0 DB-open rows. Clean, reconciled
  session — the full recovery from yesterday's 07-07 whipsaw (1W/10L / −$179).
- Service `active` since the 06:29 UTC pre-market restart; no errors/504s/naked carries all day.

### Trade-by-trade review
**All 7 exited "end-of-day flatten" at ~19:45 UTC** — none hit stop, target, or a bearish-cross
early exit. Model A throughout. Trend sub-score ≥0.84 on every entry (the 5m gate held all day).
- **NVDA** (16:41 @199.52, conf 65.65, xo 0.28/tr 0.98/vol 0.18) → 204.49 **+$39.69 (+2.49%)** —
  **best.** Rode the afternoon semis bounce cleanly; the day's whole edge. Note: gain was realized
  only by *where it sat at the flatten* — no profit-lock mechanism captured it.
- **BABA** (14:18 @108.70, conf 79.80, **xo 0.65 strongest**/tr 1.0) → 109.24 **+$12.42 (+0.50%)** —
  strongest crossover of the day → clean orderly winner. Textbook entry.
- **AVGO** (14:34 @387.52, conf 62.36, xo 0.30/vol **0.00**) → 390.36 **+$11.36 (+0.73%)** — thin-vol
  entry that worked; chip cohort traded fine despite the memory/AI wobble.
- **SE** (19:06 @105.30, conf 61.11, **xo 0.20 weakest**/vol **0.00**) → 105.70 **+$4.80 (+0.38%)** —
  weakest cross + zero volume score, still green; late (24 min to flatten) but no give-back.
- **MU** (17:08 @945.30, conf 73.77, xo 0.39) → 947.73 **+$2.43 (+0.26%)** — marginal, near-scratch.
- **COST** (14:04 @957.68, conf 73.75, xo 0.37) → 954.13 **−$7.10 (−0.37%)** — drifted slightly red
  into the close; minor EOD give-back, not a stop-out, not signal failure.
- **TSM** (17:24 @438.69, conf 69.33, xo 0.21 weak/tr 0.84) → 435.72 **−$8.91 (−0.68%)** — **worst.**
  Faded after entry; weakest-but-one crossover, but SE (xo 0.20) won → crossover strength did **not**
  separate winners from losers today.

### What worked / what didn't
- **Worked:** the 5m gate held a real trend all session (trend ≥0.84 on all 7), so entries had
  follow-through and rode to the close instead of whipsawing out — the exact opposite of 07-07.
  Strong-cross BABA (0.65) and the NVDA semis bounce carried the day.
- **Didn't:** nothing broke. The two losers were sub-1% EOD drifts, not stop-outs. Neither
  crossover strength (SE 0.20 won, TSM 0.21 lost) nor volume score (AVGO/SE vol 0.00 both won)
  cleanly ranked outcomes today — consistent with a small (n=7), trend-carried sample.

### Lessons & improvement candidates
1. **[#1, structural — NEEDS INTRADAY-REPLAY VALIDATION, do NOT ship reactively] Break-even /
   trailing stop on the open position.** 20-day exit-bucket audit is the strongest signal in the
   data: `end-of-day flatten` (positions that rode to the close) = **62 tr / 60% win / +$497.40**,
   while `end-of-day flatten (stop/target filled broker-side)` = **27 tr / 19% win / −$512.59**
   (net 20d ≈ flat, −$15). **The entire drawdown is concentrated in broker-side STOP fills**
   (targets sit ~10% out and are never hit intraday). A break-even lock (move the bracket stop to
   entry after +X favorable) would convert some round-trip stop-outs into breakeven/small exits
   **without widening risk**. BUT it cannot be validated from the DB — exits price off the candle
   close, there is no fills/high-low stream, so there is **no max-favorable-excursion data** to
   confirm (a) how many of the 27 stop-outs first went favorable enough to trip a break-even, and
   (b) whether the +$497 EOD-winner bucket would be prematurely stopped on intraday dips (NVDA's
   +2.49% today likely dipped mid-session). **Next step:** a dedicated run that reconstructs MFE
   from Alpaca minute bars for the stop-out cohort, then sizes the break-even offset — then ship.
   Shipping it today would be a guess ("never make random changes").
2. IMP-013 (`SIZE_CONFIDENCE_CAP` 85, sizing, shipped 07-06) is **still unobserved** — only the
   07-07 whipsaw and today have run since. Discipline: one clean variable at a time; do not stack
   an exit change on top of an unproven sizing change and confound both.

### Decision — NO CODE CHANGE WARRANTED today
A clean, profitable, well-behaved 5W/2L day with **zero stop-outs** offers nothing that *today's*
data independently justifies changing (winners/losers don't separate on any recorded sub-score),
IMP-013 is still unproven, and the one genuinely high-impact candidate (break-even stop) cannot be
validated from available data and must not be shipped reactively. "Reviewed, no change warranted"
is the disciplined call. Candidate #1 is logged for a dedicated future run.

### Notes for pre-market research
- **Book CLEAN & FLAT into 07-09** — 0 broker positions, 0 DB-open rows, equity **$9,302.96** all
  cash. **Nothing locked**; full watchlist free.
- **07-08 fully recovered from the 07-07 whipsaw:** 5W/2L / **+$54.69**, all seven rode to EOD
  flatten on an orderly semis/megacap bounce. **NVDA best (+$39.69/+2.49%)**, BABA the clean
  strong-cross winner. **No stop-outs, no infra issues.**
- **No signal-quality parks.** Both small losers (COST −$7.10, TSM −$8.91) were sub-1% EOD
  give-backs, not symbol failures. TSM had a weak crossover (0.21) but SE won on an equally-weak
  one (0.20) → no park on quality grounds.
- **Chip cohort traded fine** (AVGO/NVDA/MU/TSM all signalled; 3 of 4 green) despite the ongoing
  memory/AI-valuation wobble — the long-only gate found clean longs. **No chip parks.**
- **SE** won again (+$4.80) on a thin tape (volume sub-score 0.00) → thin-tape watch stays
  **"watch volume, no park."**
- **QCOM/BIRD/ENPH/WPM/XOM stay parked** (XOM's oil pop is one Iran headline, not a trend). No
  watchlist-name earnings this week (next META 07-29, AAPL 07-30) → **zero binary risk**. SPCX
  still too new for the ribbon.

---
