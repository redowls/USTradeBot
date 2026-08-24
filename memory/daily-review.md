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

## 2026-07-09 — Daily Review

### Stats
- Closed trades (DB): **10** — 4W / 6L → **40% win rate**. Net realized P&L **+$22.58**
  (avg +$2.26/trade). Avg win **+$30.39**, avg loss **−$16.50**, **profit factor ≈ 1.23**
  (winners ~2× losers → positive expectancy despite the sub-50% hit rate). Account **equity
  $9,325.52** (all cash, 0 open positions at broker after the EOD flatten).
- **Books exact to the cent.** Pre-open equity $9,302.94 → close $9,325.52 = **+$22.58**
  mark-to-market == DB realized **+$22.58**. Broker flat (0 positions), 20 fills = 10 entries
  + 10 exits, all matching `dbo.trades`. The IMP-008/009/010 fill-truth thread holds; no
  DB⇄broker desync. Model A throughout.

### Trade-by-trade review
- **SE** (13:35, conf 62.47, xo 0.2953) $106.47 → **$109.43** EOD **+$53.21** (+2.78%). **Best.**
  Weak-ish cross but rode a clean all-session Sea Ltd uptrend to the flatten — regime tailwind,
  not signal strength.
- **BABA** (13:41, conf 77.20, **xo 0.5822**) $109.82 → $111.40 EOD **+$26.86** (+1.44%). Strong
  cross, clean trend hold. The day's best signal-quality winner.
- **ABNB** (14:23, conf 74.47) $144.92 → $146.81 EOD **+$28.35** (+1.30%). Solid trend hold.
- **AMZN** (17:27, conf 64.05, xo 0.2370) $243.58 → $245.77 EOD **+$13.14** (+0.90%). Low-conf,
  near the IMP-011 floor, still won — mid-band coin-flip landed heads.
- **TSLA** (17:37, conf 79.17, all subs ≈max) $405.02 → $404.95 EOD **−$0.28** (scratch). Round-
  tripped, no net move. Regime (flat tape), not a signal failure.
- **MU** (13:36, conf 84.63) $1014.30 → $1013.61 EOD **−$1.38** (scratch). Round-trip, no trend.
- **AVGO #2** (18:02, conf 68.21, **xo 0.2014** — right at the floor) $406.30 → $401.82 EOD
  **−$13.44** (−1.10%). **Same-day re-entry** after AVGO #1 stopped out at 16:55; faded again.
- **TSM** (15:07, conf 77.10) $443.23 → $438.39 EOD **−$19.38** (−1.09%). Faded post-entry, rode
  to flatten. Regime give-back.
- **AVGO #1** (13:38, conf 67.90, xo 0.3971) $402.64 → **$395.18 trailing stop @16:55** **−$29.82**
  (−1.85%). **Only intraday stop of the day.** Faded after entry; the broker-side trailing stop
  caught it (IMP-012 path clean — single WARNING, no traceback storm, reconciled at true fill).
- **INTC** (13:36, **conf 94.26**, xo 1.00, every sub-score maxed) $115.66 → $114.21 EOD
  **−$34.68** (−1.25%). **Worst.** The textbook **high-confidence-underperformance** case: a
  fully-maxed ribbon at entry marked a late/exhausted move that faded. The all-time
  `vw_confidence_outcome` **90-100 band is now 0 wins / 3 trades / −$144.42**. **IMP-013 already
  de-sized it** — conf capped at 85 for sizing → alloc 0.081 (qty 24) vs the linear ramp's ~0.093
  (qty ~27), ~$347 less notional at risk. Working as designed.

### What worked / what didn't
- **Worked:** winners rode clean trends to the EOD flatten (SE/BABA/ABNB/AMZN); **avg win 2×
  avg loss → positive expectancy** even at 40% hit rate. **IMP-011** floor honored (lowest survivor
  AVGO#2 xo 0.2014). **IMP-013** actively trimmed the INTC top-band position (first live confirmation).
  Exit infra flawless: 1 clean trailing-stop reconcile, 9 clean EOD flattens, books exact.
- **Didn't:** the **top confidence band inverted again** — INTC (conf 94) the single biggest loser,
  reconfirming IMP-013's thesis. **AVGO churned both ways** (−$43.26 combined) including a same-day
  re-entry that lost a second time. Both round-trip scratches (MU/TSLA) were flat-tape regime, not
  signal failures.

### Lessons & improvement candidates
1. **Break-even stop lock — RESOLVED with data (the 07-08-requested MFE run), NOT shipped.**
   Reconstructed max-favorable-excursion from **real IEX minute bars for all 99 clean-book-era
   trades (06-23→07-09, 0 missing bar-sets)** and simulated moving the stop to entry after +T·R
   favorable. Result: the edge is **marginal and trigger-fragile** — only an aggressive **0.5R**
   trigger helps (**+$25.38 / 99 trades**; saved 5 stop-outs +$35.83, but **already forfeited 2
   winners −$10.45**); **0.75R → +$8.17; ≥1.0R → ≈ $0** (−$0.36 to $0.00). Benefit is ~$0.26/trade
   concentrated in **5 trades**, and the winner-forfeit (whipsaw) cost would grow on trending days
   absent from this calm sample. **Not enough to ship**, and stacking an exit change on the
   **still-unproven IMP-013** (only 3 sessions old) would confound its evaluation. Candidate
   **downgraded**, evidence archived (`/tmp/mfe_sim.py` logic) — revisit only if the stop-out
   drawdown re-concentrates.
2. **High-confidence inversion (INTC today, 90-100 band 0/3):** already addressed by **IMP-013**
   sizing cap; observing. Do NOT layer a second high-conf change on a 3-trade band (overfit).
3. **Same-day re-entry (AVGO):** the **only** same-day double-entry in 45 days — a one-off, not a
   pattern. A re-entry cooldown would overfit a single event. No change.

### Decision — NO CODE CHANGE WARRANTED today
A healthy, profitable, well-behaved day (positive expectancy, exit infra flawless, books exact).
The one genuinely high-impact backlog candidate (break-even stop) was finally **measured against
real minute bars** rather than deferred again — and the MFE evidence shows only a marginal,
fragile edge that doesn't justify shipping over the still-unproven IMP-013. IMP-013 got its first
live confirmation (INTC de-sized). "Reviewed, no change warranted" is the disciplined call.

### Notes for pre-market research
- **Book CLEAN & FLAT into 07-10** — 0 broker positions, 0 DB-open rows, equity **$9,325.52** all
  cash. **Nothing locked**; full watchlist free.
- **SE** was the day's star (+2.78%) on a weak-ish cross (0.30) — momentum name behaving well;
  thin-tape watch stays **"watch volume, no park."** **BABA/ABNB/AMZN** all traded clean longs.
- **INTC** — a **maxed-confidence entry (94.26) that faded to the day's worst loss** (−1.25%). It
  signalled fine (no quality park), but the top confidence band keeps disappointing; IMP-013 now
  size-limits it. Flag for size-awareness, not exclusion.
- **AVGO chopped both directions** (−$43.26 combined, incl. a same-day re-entry that lost again) —
  **watch for whipsaw**; if AVGO stops out early tomorrow, treat a same-day re-signal with suspicion.
- **MU / TSLA round-tripped to scratch** — flat-tape, no trend; not symbol failures, keep.
- **QCOM/BIRD/ENPH/WPM/XOM stay parked.** No watchlist-name earnings this week (next META 07-29,
  AAPL 07-30) → **zero binary risk**.

---

## 2026-07-10 — Daily Review

### Stats
- Closed trades (DB): **6** — 2W / 4L → **33% win rate**. Net realized P&L **−$18.34**
  (avg −$3.06/trade). Avg win **+$15.22**, avg loss **−$12.19**, **profit factor ≈ 0.62**
  (small day; the two losers TSLA/SE were 88% of the loss). Account **equity $9,307.15**
  (all cash, **0 open positions** at broker after the flatten).
- **Books exact to the cent.** Pre-open equity $9,325.49 → close $9,307.15 = **−$18.34**
  mark-to-market == DB realized **−$18.34**. Broker flat (0 positions), 88 orders today
  (6 entries + 6 exits + bracket legs/replaces), 0 DB-open rows. IMP-008/009/010 fill-truth
  thread holds. Model A throughout. Service `active` all session, no 504s, no naked carry.

### Trade-by-trade review
- **NVDA** (14:11 @207.136, conf **83.76**, xo 0.57 / tr 1.0 / rsi 1.0 / **vol 0.86** / vlt 0.92)
  → EOD @209.615 **+$24.79 (+1.20%)**. **Best.** High conviction **+ strong volume** rode a clean
  semis trend hold to the flatten — the day's whole edge. High-conf paying off here (contrast SE).
- **ABNB** (13:54 @148.17, conf 65.24, xo 0.38 / vol 0.00) → EOD @148.64 **+$5.64 (+0.32%)**. Modest
  winner, orderly hold; thin volume score again didn't stop a green outcome.
- **C** (14:02 @140.88, conf 60.19 low, xo 0.24 / vol 0.00) → EOD @140.82 **−$0.66** scratch. Low-conf
  flat-tape round-trip; regime, not a signal failure.
- **AMZN** (15:48 @246.35, conf 60.37 low, xo 0.23) → EOD @245.61 **−$4.44 (−0.30%)**. Low-conf, late
  entry, minor fade to the close. Churn.
- **SE** (14:02 @114.15, conf **83.00** high, **xo 0.95 strongest** / vol 0.09) → **broker-side stop
  filled @113.21 at 14:33:21 UTC** **−$18.80 (−0.82%)**, but **detected only at the 19:45 EOD flatten**
  (booked "end-of-day flatten (stop/target filled broker-side)"). High-conviction entry that faded
  **straight down** from entry → stopped out inside 30 min. The stop filled on a down move, so the
  trailing ratchet never surfaced it → **IMP-012 residual gap (see below)**.
- **TSLA** (13:48 @409.284, conf 69.08, xo 0.41 / vol 0.26) → **trailing stop @404.31 (16:20 UTC)**
  **−$24.87 (−1.22%)**. **Worst.** Popped after the open (stop trailed 400.94→404.31), then reversed
  and gave it all back through the trail. Caught **cleanly intraday** via the trailing path (single
  WARNING, no traceback) — the IMP-012 *rising*-case works. Regime give-back, not signal failure.

### What worked / what didn't
- **Worked:** NVDA (conf 83.76 **+ volume 0.86**) carried the day on a clean semis hold; exit infra
  flawless (TSLA's reversal caught intraday, 5 clean EOD flattens, books exact to the cent).
- **Didn't:** **high-conf split** — NVDA (83.76) won big yet SE (83.00) was a fast stop-out; the
  **80-89 band stays a coin flip** (now 14 tr / 50% / +$38.63 all-time). No trade cleared **85** today,
  so **IMP-013's sizing cap never engaged**. Low-conf entries (C 60.19, AMZN 60.37) added small churn
  (both red). And **SE's stop fill on a down move sat undetected ~5h** — the residual gap, now 4th time.

### Lessons & improvement candidates
1. **[SHIPPED — IMP-014]** Wall-clock `tick()` now sweeps `MANAGING` symbols for a broker-side
   stop/target fill the trailing ratchet never caught (fills on a **down move** raise no higher-high
   replace → no 422 → invisible until the EOD flatten). Read-only `reconcile_if_closed` (never submits a
   close) records the exit at the true intraday time/price and frees the symbol to `WAITING` within a
   tick. Closes IMP-012's residual gap; today's SE is the regression scenario. 240 tests, restart clean.
2. **Volume sub-score (watch, not actionable):** today the winner NVDA had **vol 0.86** and all four
   losers had low vol (SE 0.09 / TSLA 0.26 / AMZN 0.255 / C 0.00) — but **ABNB won on vol 0.00**, so it
   doesn't cleanly separate (consistent with 07-08: AVGO/SE vol 0.00 both won). No change; keep logging.
3. **High-conf 80-89 coin flip:** don't touch a 50/50 band; IMP-013 already size-caps ≥85 (untouched
   today). The break-even/MFE candidate stays **downgraded** (measured 07-09: marginal/fragile).

### Notes for pre-market research
- **Book CLEAN & FLAT into Mon 07-13** — 0 broker positions, 0 DB-open rows, equity **$9,307.15** all
  cash. **Nothing locked**; full watchlist free.
- **NVDA** was the day's star (+1.20%) on high conviction **and strong volume** — semis leadership
  intact; keep.
- **SE** — a **high-conf entry (83.00) that faded straight down** and stopped out early (−0.82%) on
  **thin volume (0.09)**; momentum cooled today. **Watch volume, no park.**
- **TSLA** popped then fully reversed → trailing-stopped for the day's worst (−1.22%). **Chop watch** —
  if it re-signals early Monday and reverses again, treat with suspicion.
- **C / AMZN** chopped small on low conviction (both ~scratch/minor red) — flat-tape regime, not symbol
  failures; keep.
- **QCOM/BIRD/ENPH/WPM/XOM stay parked.** No watchlist-name earnings next week (META 07-29, AAPL 07-30)
  → **zero binary risk**.

---

## 2026-07-13 — Daily Review

### Stats
- Closed trades (DB): **2** — 0W / 2L → **0% win rate**. Net realized P&L **−$51.48**
  (avg −$25.74/trade). Avg loss **−$25.74**; no wins → profit factor 0. Account **equity
  $9,255.64** (all cash, **0 open positions** at broker after the EOD flatten).
- **Books exact to the cent.** Pre-open equity $9,307.12 → close $9,255.64 = **−$51.48**
  mark-to-market == DB realized **−$51.48** (AMZN −$2.52 + NFLX −$48.96). Broker flat
  (0 positions confirmed via preflight), 0 DB-open rows. Model A throughout. Service `active`
  all session, no 504s, no naked carry.
- **Quiet, defensive session on a risk-off, chip-selloff CPI-eve tape** (as the 07-13 pre-market
  research predicted): only **2 entries** all day. Journald shows the long-only 5m gate did its
  job — a wall of rejections into the weak tape (UNH conf 59.8/54.9 <60, BABA 56.8 <60, WMT
  50.4/50.5/61.2, MSFT crossover 0.12/0.06/0.05 <0.20). The bot correctly refused to chase longs
  into weakness. Low activity here is the gate protecting capital, not a malfunction.

### Trade-by-trade review
- **AMZN** (13:58 @247.57, conf 68.34, xo 0.28 / tr 0.68 / rsi 1.0 / vol 0.78 / vlt 0.97) → EOD
  flatten @247.29 **−$2.52 (−0.11%)**. **Near-scratch.** Low-mid-conf entry that round-tripped on
  a flat/choppy tape; drifted a few cents red into the close. Regime churn, **not** a signal
  failure — no stop-out, no fade of consequence. (DB exit priced @247.29 off the candle vs the
  actual broker fill @247.33 — the known Phase 4/6 candle-vs-fill $0.04 estimation gap; benign.)
- **NFLX** (14:03 @75.32, conf **83.21** high, xo 0.46 / tr 1.00 / rsi 1.00 / **vol 1.00** / vlt
  0.96) → EOD flatten @73.96 **−$48.96 (−1.81%)**. **Worst — the day's entire loss.** A
  high-conviction, fully-stacked ribbon (trend/rsi/vol all maxed) that **faded straight down from
  entry**, rode toward its 73.81 stop, and was flattened at 73.96 (just $0.15 above the stop) at
  the close. It never triggered the broker-side stop (so IMP-014's sweep had nothing to catch) and
  never recovered → a clean, textbook instance of the **high-confidence-underperformance** pattern
  logged repeatedly (INTC 07-09, SE 07-10). NFLX was freshly re-enabled this morning and reports
  earnings **Thu 07-16** — today was a fresh momentum entry that immediately reversed. Root cause:
  **signal quality of a maxed ribbon marking a late/exhausted push**, not stop placement (a 2% stop
  is normal) and not exit logic (nothing to trail — it went straight against the entry).

### What worked / what didn't
- **Worked:** the defensive gate — 2 entries on a risk-off chip-selloff day, dozens of correct
  rejections; exit infra flawless (both flattened cleanly, books exact to the cent, broker flat,
  no 504s / no naked carry). IMP-014 live and quiet (no broker-side stop fill to catch today).
- **Didn't:** **the high band bit again.** NFLX (conf 83.21) — the single biggest loser — is the
  4th consecutive session where an ≥80-conf entry disappointed. Its −$48.96 **single-handedly
  flipped the all-time 80-89 band from +$38.63 (14 tr, per 07-10) to −$10.32 (15 tr / 47% win)**.
  AMZN (68.34) was harmless scratch churn. Neither loss was an infra or stop-placement failure.
- **Transient, self-healed:** one `notifier | Telegram sendMessage failed … ConnectionReset` at
  19:45:26 during the AMZN exit alert — the exception was caught, the bot continued and flattened
  NFLX normally; preflight at 21:12 confirms Telegram delivery is healthy. A one-off network blip,
  **not** a code fault — no action.

### Lessons & improvement candidates
1. **High-conf ≥80 underperformance — candidate: consider lowering IMP-013's `SIZE_CONFIDENCE_CAP`
   from 85 toward ~80.** The 70-79 band is the clear sweet spot (+$232.93 / 54 tr / 54% win) while
   the ≥80 bands are collectively **−$154.75** (80-89: −$10.32/15; 90-100: −$144.42/3). But **NOT
   TODAY, and not reactively:** (a) today's band flip is driven by **one trade** (NFLX) — before
   today the 80-89 band was *positive* (+$38.63); reacting now would **overfit to a single day**;
   (b) IMP-013 (cap=85, shipped 07-06) is **still unproven** — it has engaged only once (INTC 07-09)
   and NFLX at 83.21 is *below* its cap so it didn't even fire today — changing its parameter now
   would **confound its own evaluation**. Revisit only once IMP-013 has several more observations
   AND the 80-89 band has post-today data confirming NFLX wasn't an outlier. Logged, not shipped.
2. **Break-even/MFE stop** stays **downgraded** (measured 07-09 vs real minute bars: marginal/fragile;
   NFLX today faded straight down with no favorable excursion, so a break-even lock would not have
   helped it either — reinforces the downgrade).
3. **IMP-014** (broker-side stop sweep) remains **unexercised** — no down-move broker-side stop fill
   occurred today; keep observing for its first real live catch.

### Decision — NO CODE CHANGE WARRANTED today
A 2-trade day (one regime scratch + one known-pattern high-conf fade) is far too thin to justify a
strategy change, and the one tempting move — lowering the ≥80 sizing cap — would both **overfit to
the single NFLX trade that flipped the band** and **confound the still-unproven IMP-013**. The gate
behaved correctly and defensively on a risk-off tape; infra was flawless; books reconcile to the
cent. "Reviewed, no change warranted" is the disciplined call. Candidate #1 is logged for a future
run once IMP-013 has matured and the band has more data.

### Notes for pre-market research
- **Book CLEAN & FLAT into Tue 07-14** — 0 broker positions, 0 DB-open rows, equity **$9,255.64**
  all cash. **Nothing locked**; watchlist free. **JPM & C are still parked** (report Tue 07-14
  pre-open) — the pre-market routine should **re-enable them after their prints clear** per the
  07-13 park plan.
- **⚠️ Event-heavy Tuesday:** **June CPI 08:30 ET + Warsh congressional testimony** (macro binary),
  and **JPM/C Q2 earnings pre-open**. Expect another choppy/gappy tape; late-day entries into CPI
  aftermath carry extra reversal risk.
- **NFLX** — a **maxed-confidence entry (83.21) that faded straight down to the day's whole loss
  (−1.81%)** on its first session back on the list, with **earnings Thu 07-16** looming. It signalled
  fine (no quality park), but flag it: **NFLX is size-/earnings-sensitive** — Wed 07-15 is the last
  session before its Thu print (same naked-overnight-into-binary risk that parks JPM/C). Consider
  parking NFLX for Wed's routine.
- **AMZN** chopped to scratch on a flat tape — regime, not a symbol failure; keep.
- **TSM reports Wed 07-15, UNH Wed, NFLX Thu 07-16** — flag for the Tue/Wed routines (park the day
  before each print). **QCOM/BIRD/ENPH/WPM/XOM/COST stay parked** (chip selloff / no trend).
- Chip cohort stayed weak all day (SK Hynix reversal); the gate opened **zero** chip longs — the
  long-only 5m gate self-protected against the selloff exactly as intended.

---

## 2026-07-14 — Daily Review

### Stats
- Closed trades (DB): **6** — 2W / 4L → **33% win rate**. Net realized P&L **−$62.38**
  (avg −$10.40/trade). Avg win **+$11.60** (QQQ +$0.86, INTC#2 +$22.33), avg loss **−$21.39**,
  **profit factor ≈ 0.27**. Account **equity $9,193.24** (all cash, **0 open positions** at
  broker after the EOD flatten).
- **Books exact to the cent.** Pre-open equity $9,255.62 → close $9,193.24 = **−$62.38**
  mark-to-market == DB realized **−$62.38**. Broker flat (0 positions, preflight/`/v2/positions`
  confirmed), 12 fills = 6 entries + 6 exits, all matching `dbo.trades`. IMP-008/009/010 fill-truth
  thread holds; no phantoms, nothing carried, no naked overnight, no NAKED page. Model A throughout.
- **Event-heavy CPI-day tape** (June CPI 08:30 ET + Warsh congressional testimony, as the 07-13
  pre-market flagged): a risk-off/choppy session; every entry was a weak-to-mid crossover (xo
  0.216–0.30, except TSLA's strong 0.659) and most faded. Service `active` since the 07-13 11:34
  UTC boot (**NRestarts=0**, running on IMP-014), no 504s/422s/errors all session.
- Confidence vs outcome (all-time, **80-89 deepened again by today's TSLA loss**): **70-79 the
  peak +$222.56 (54%, 56 tr)**, 60-69 +$48.44 (45%, 105 tr), **80-89 −$32.38 (44%, 16 tr)** [was
  −$10.32/15 tr on 07-13], **90-100 −$144.42 (0%, 3 tr, unchanged — no 90+ today)**.

### Trade-by-trade review (Model A throughout; entry times UTC)
- **TSLA** 13:39 @399.18, conf **83.60** (**xo 0.659 strong**, tr 0.74, rsi 1.0, vol 1.0, vlt 0.93),
  qty 7 → EOD flatten @396.03 **−$22.05 (−0.79%)**. High-conf (80-89), strongest cross of the day,
  all confirms high — yet **faded to the flatten** (never threatened its 391.14 stop). The
  **high-confidence-underperformance** pattern again — the 5th consecutive session an ≥80 entry
  disappointed (INTC 07-09 c94, SE 07-10 c83, NFLX 07-13 c83, TSLA today c83.6).
- **QQQ** 13:46 @719.93, conf 67.77 (xo 0.230) qty 2 → EOD @720.36 **+$0.86 (+0.06%)**. Scratch.
- **INTC #1** 13:49 @107.42, conf **60.10** (just above the 60 gate; xo 0.300, **vol 0.07 thin**,
  vlt 0.67) qty 13 → **broker-side stop @105.28 filled 14:05:08** **−$27.79 (−1.99%)**. Low-conviction,
  thin-volume entry stopped near the −2% floor within 16 min on a down move. **Caught intraday by the
  IMP-014 path at 14:05:30** (~22s after the broker fill) → freed to WAITING → re-enterable (see INTC #2).
- **WMT** 14:07 @115.56, conf 72.11 (xo 0.236, all confirms 1.0) qty 16 → **broker-side stop @113.52
  filled 19:22:04** **−$32.69 (−1.77%)**. **Biggest loss.** Drifted straight down over the session; the
  stop filled on a **down move** (no higher-high replace, so the trailing ratchet never surfaced it) →
  the exact **IMP-014 regression scenario**. **Reconciled by the IMP-014 wall-clock sweep at 19:22:25
  (~21s after the fill)**, booked at the true intraday fill/time tagged `stop/target filled broker-side`,
  freed to WAITING — **NOT** a late `end-of-day flatten (...)` row. First real live catch (see below).
- **MU** 16:40 @985.10, conf 61.92 (xo 0.231, **vol 0.00**) qty 1 → EOD @982.06 **−$3.04 (−0.31%)**. Scratch.
- **INTC #2** 16:43 @106.86, conf 71.10 (xo 0.216 — weakest survivor, honors IMP-011 floor) qty 15 →
  EOD @108.35 **+$22.33 (+1.39%)**. **Best trade.** **Same-day re-entry** after INTC #1's 14:05 stop-out;
  the name recovered and rode to the flatten. Because IMP-014 freed INTC to WAITING promptly, the bot
  re-entered and captured the afternoon recovery — a concrete win from the prompt reconcile.
- **Root cause (day):** **event-day / regime**, not a fixable single defect. On a risk-off CPI tape the
  gate+cross fired on weak-mid crosses that mostly faded. The two biggest losers (WMT −$32.69, INTC #1
  −$27.79 = ~97% of gross loss) were **stop-outs on weak-to-mid-conf entries** (conf 72.1/60.1, xo
  0.236/0.30); the single high-conf loss (TSLA −$22.05) was **~offset by the INTC re-entry (+$22.33)**.
  Losses contained (worst −1.99% at INTC #1's stop), no risk-limit trip, no infra/stop-placement fault.

### What worked / what didn't
- **Worked — the headline: IMP-014's FIRST TWO LIVE VALIDATIONS.** Both down-move broker-side stop
  fills that the trailing ratchet cannot surface (INTC #1 @14:05, WMT @19:22) were detected within ~20s
  by the wall-clock `_reconcile_managing()` sweep, booked at their **true intraday fill price/time**
  (tagged `stop/target filled broker-side`, not a late EOD row), and the symbols freed to WAITING —
  **INTC then re-entered and won +$22.33.** This is exactly the catch the 07-10 weekly asked to prove
  (`reconciled broker-side exit for <SYM> -> WAITING`, no double-exit, no double-Telegram). Exit infra
  flawless again: wall-clock EOD flatten fired 19:45, all sells filled in liquid RTH, broker flat, books
  exact. IMP-011 floor honored (weakest survivor INTC #2 xo 0.216).
- **Didn't:** the strategy has **no edge on a choppy CPI-event tape** — 6 weak-mid-cross entries, 4
  faded (2 to stops). And the **≥80 band bit again** (TSLA c83.6 → 80-89 now −$32.38/16 tr), the 5th
  straight high-conf disappointment — but today it was offset by the INTC re-entry, so it was **not**
  the day's damage. **No recorded sub-score separated winners from losers today**: the strong-cross
  TSLA (0.659) lost while the weakest-cross INTC #2 (0.216) won; low-vol MU (0.00) scratched while
  high-vol WMT (1.0) took the biggest stop — reconfirming (as 07-07/07-10) that neither a crossover nor
  a volatility/volume floor cleanly ranks outcomes.

### Lessons & improvement candidates (ranked)
1. **High-conf ≥80 underperformance — candidate still: lower IMP-013's `SIZE_CONFIDENCE_CAP` 85 → ~80.**
   The ≥80 cohort is now **19 tr / −$176.80** all-time (80-89 −$32.38/16; 90-100 −$144.42/3) vs the clear
   70-79 peak (+$222.56/56). Today's TSLA (c83.6, loss) is the second post-NFLX 80-89 datapoint, so the
   07-13 gate condition *"80-89 confirms NFLX wasn't an outlier"* is now met. **But NOT shipped today**,
   for two firm reasons the mandate demands: (a) the 07-13 review's *other* gate — *"IMP-013 has several
   more observations"* — is **NOT met**: IMP-013 (cap 85) has bound **only once live** (INTC 07-09; today's
   TSLA 83.6 is below the cap), so it remains essentially unproven — lowering its parameter now would
   **confound its own evaluation** and stack a change on an unproven ship; and (b) **it would not have
   helped today** — the day's damage was low/mid-conf stop-outs (WMT/INTC #1), and TSLA's high-conf loss
   was offset by the INTC re-entry, so shipping it off today's book would target the wrong cohort. Revisit
   once IMP-013 has ≥2–3 more live bindings AND the 80-89 band keeps deteriorating on fresh data.
2. *(watch — accumulating)* **Broad-adverse-day / MTM daily-loss stand-down** (the 07-07 candidate). Today
   was −$62 on a CPI event day but **not** a whipsaw disaster (2 wins, moderate loss), so it does not add a
   qualifying occurrence. Still needs live mark-to-market open-P&L tracking (a larger critical-path change)
   and 1–2 more genuine broad-adverse sessions before deliberate design — do NOT rush off a single day.
3. *(watch, unchanged)* **Same-day re-entry** is now 2 occurrences (AVGO 07-09 lost, INTC 07-14 **won**) →
   1W/1L, no actionable pattern; a re-entry cooldown would have **blocked today's best trade**. No change.
4. *(watch, unchanged)* Volatility/volume sub-score floor — again **failed to separate** today (see above);
   stays down-weighted (07-07/07-10 contradicted it). Break-even/MFE stop stays **downgraded** (07-09 MFE:
   marginal/fragile; TSLA/WMT/INTC #1 faded from entry with little favorable excursion → a BE lock wouldn't help).

### Decision — NO CODE CHANGE WARRANTED today
A moderate −$62 loss on a CPI-event regime day, dominated by two weak-mid-conf **stop-outs** and partly
offset by a winning re-entry, offers nothing today's data independently justifies changing. The one
tempting lever (lower the ≥80 sizing cap) is **explicitly gated off** by the 07-13 review (IMP-013 still
unproven — bound once), **would not have helped today's damage**, and would confound the two still-maturing
recent ships (IMP-013 07-06, IMP-014 07-10 — validated only *today*). Shipping it would overfit one CPI day
and violate the one-clean-variable discipline the weekly reviews have repeatedly praised. **The disciplined
call is to add nothing and let IMP-013/IMP-014 accumulate observations.** Today's real result is *positive on
process*: IMP-014's first two live catches close out the 07-10 weekly's #1 focus. Candidate #1 logged, not shipped.

### Notes for pre-market research
- **Book CLEAN & FLAT into Wed 07-15** — 0 broker positions, 0 DB-open rows, equity **$9,193.24** all cash.
  **Nothing locked**; watchlist free (subject to the earnings parks below).
- **⚠️ Earnings parks (carried from 07-13, action for the Wed routine):** **TSM reports Wed 07-15** and
  **UNH Wed 07-15** — park each the session before its print per timing; **NFLX reports Thu 07-16** →
  **Wed 07-15 is NFLX's last pre-print session, so the Wed routine should PARK NFLX** (same naked-into-binary
  discipline). **JPM & C** reported **today (Tue 07-14) pre-open** (parked per the 07-13 plan) → **re-enable
  them now that their prints have cleared** if charts are intact.
- **TSLA** — a high-conf (83.60) **strong-cross** entry that still **faded** (−0.79%, rode to flatten); 5th
  straight ≥80 disappointment. It signalled fine (**no quality park**) — flag it as **size-/high-conf-sensitive**,
  not broken. **WMT & INTC** both stopped out on the risk-off CPI tape (regime, not symbol quality) — and INTC's
  same-day **re-entry won (+$22.33)**, proof the name wasn't broken; **keep both**.
- **Weak-mid-cross chop day:** only TSLA had a strong cross (0.659); the rest were 0.216–0.30. On a choppy
  CPI tape the strategy makes many low-conviction entries with no edge — a **regime** issue, no watchlist fix.
- **QCOM / BIRD / ENPH / WPM / XOM / COST stay parked.** Chip/semis were mixed on the CPI print.

---

## 2026-07-15 — Daily Review

### Stats
- Closed trades (DB): **7** — 1W / 6L → **14% win rate**. Net realized P&L **−$38.19**
  (avg −$5.46/trade). **Only winner GOOG +$30.87**; avg loss **−$11.51**, **profit factor ≈ 0.45**.
  Account **equity $9,155.03** (all cash, **0 open positions** at broker after the EOD flatten).
- **Books exact to the cent.** Pre-open equity $9,193.22 → close $9,155.03 = **−$38.19**
  mark-to-market == DB realized **−$38.19**. Broker **flat** (`/v2/positions` = []), **14 fills =
  7 entries + 7 exits**, every price matching `dbo.trades`. No phantoms, nothing carried, no naked
  overnight, no NAKED page. Model A throughout.
- **Service healthy:** `active` since the 11:34 UTC pre-market restart (**NRestarts=0**), running on
  IMP-014. The only journald ERROR (`connection limit exceeded`, 11:22 UTC) belongs to the **old PID
  1672358 during the pre-market restart handoff** — the two websocket subs briefly overlapped; the
  11:34 restart re-subscribed cleanly to 19 symbols. **Zero 504s/422s/errors during the trading
  session.**
- **Regime:** cautiously-positive-then-fading tape (softer June CPI Tue cut hike odds, but **June PPI +
  day-2 Warsh testimony** capped the relief, as the 07-15 pre-market flagged). Entries clustered
  **13:55–15:01 UTC** on weak-to-mid crossovers (xo 0.28–0.49); most drifted or faded.
- Confidence vs outcome (all-time, `vw_confidence_outcome`): **70-79 the peak +$220.43 (53%, 59 tr)**,
  60-69 +$13.75 (44%, 108 tr), **80-89 −$33.73 (41%, 17 tr)** [MSFT 80.31 added a −$1.36 scratch],
  **90-100 −$144.42 (0%, 3 tr, unchanged — no 90+ today)**.

### Trade-by-trade review (Model A throughout; entry times UTC)
- **GOOG** 14:30 @364.34, conf **78.47** (xo 0.282, **trend/rsi/vol/vlt all 1.0** — full confirm stack),
  qty 6 → EOD flatten @369.49 **+$30.87 (+1.41%)**. **Only winner / best trade.** Rode a clean intraday
  uptrend; trailing stop ratcheted up all session (357.17→364.61 in journal). The full-confirm megacap
  trend behaved exactly as the model wants.
- **SE** 14:23 @113.73, conf 71.31 (xo 0.428, **vol 0.232 thin**), qty 19 → **broker-side stop @112.17
  filled, reconciled 17:05:53** **−$29.64 (−1.37%)**. 2nd-biggest loss. Fell straight from entry (no
  higher-high ratchet) → the classic down-move stop. **Caught by the IMP-014 wall-clock sweep** (`reconcile_exit
  SE broker-side fill @112.17` → `reconciled broker-side exit for SE -> WAITING`), booked at the **true
  intraday fill price/time** tagged `stop/target filled broker-side`, not a late EOD row.
- **NFLX** 14:39 @74.79, conf 62.33 (xo 0.297, **vol 0.095 very thin**), qty 17 → **broker-side stop
  @73.32 filled, reconciled 19:18:25** **−$24.99 (−1.97%)**. **Biggest loss** (near the −2% floor). Kept
  today per pre-market plan (earnings **Thu 07-16 after close**, so Wed is not the pre-print carry
  session). Straight down-move stop → **again caught cleanly by IMP-014** (`reconciled broker-side exit for
  NFLX -> WAITING`), booked at fill.
- **AMZN** 14:30 @254.94, conf 69.74 (xo 0.491, **vol 0.00**), qty 7 → EOD @254.22 **−$5.02 (−0.28%)**. Scratch.
- **ABNB** 13:55 @148.71, conf 64.88 (xo 0.403, vol 0.083), qty 13 → EOD @148.35 **−$4.68 (−0.24%)**.
  Scratch. Trailing stop ratcheted up early (147.29→147.63) then drifted back to a flat flatten.
- **JPM** 15:01 @348.32, conf 79.93 (xo 0.331, all confirms 1.0), qty 4 → EOD @347.48 **−$3.37 (−0.24%)**.
  Scratch. First session back after its Tue print cleared (re-enabled 07-14) — behaved fine, just no trend.
- **MSFT** 14:31 @395.58, conf **80.31** (xo 0.344, all confirms 1.0), qty 5 → EOD @395.31 **−$1.36 (−0.07%)**.
  Near-flat scratch. The **only ≥80 entry today** — it did **not** "bite" (essentially breakeven).
- **Root cause (day):** **regime, not a fixable single defect.** The two full losses (SE −$29.64 + NFLX
  −$24.99 = **−$54.63 = 143% of the net loss**) were **broker-side stop-outs on straight-down moves**, both
  reconciled cleanly by IMP-014; the four scratches (−$14.43 combined) were flat EOD flattens; GOOG's clean
  trend (+$30.87) offset ~57% of the two stops. Losses contained (worst −1.97% at NFLX's near-floor stop),
  no risk-limit trip, no stop-placement or infra fault. Third consecutive **soft regime-loss** day (07-13
  −$51, 07-14 −$62, 07-15 −$38) — chop/fade tapes where the long-only crossover has no edge.

### What worked / what didn't
- **Worked — IMP-014's 3rd & 4th live validations.** Both down-move broker-side stop fills (SE @17:05,
  NFLX @19:18) were detected within a watchdog tick (~20s), booked at their **true intraday price/time**
  (`stop/target filled broker-side`, not late EOD rows), and the symbols freed to WAITING — exactly the
  behaviour the 07-10 weekly asked to prove, now demonstrated on 4 fills across 2 sessions (INTC+WMT 07-14,
  SE+NFLX today), **zero** double-exit / double-Telegram. GOOG showed the model's happy path (full confirm
  stack + clean trend → the day's only win). Exit infra flawless: wall-clock EOD flatten fired 19:45, all
  sells filled in liquid RTH, broker flat, books exact.
- **Didn't:** the strategy has **no edge on a fade tape** — 7 mid-conviction entries, 6 red (2 to stops, 4
  scratch). **Notable but NOT yet actionable:** today the **volume sub-score separated cleanly** — the two
  full losses (SE vol 0.232, NFLX vol 0.095) and both other losers were **low-volume** entries (ABNB 0.083,
  AMZN 0.00), while all three **vol=1.0** entries avoided a real loss (GOOG +$30.87 win; MSFT/JPM ~flat). But
  this **directly contradicts 07-14**, where high-vol WMT (1.0) took the biggest stop and low-vol MU (0.00)
  scratched — so volume remains an **inconsistent** separator across days (as 07-07/07-10/07-14 all found).
  One clean day is an artifact, not a signal → **watch, do not act.**

### Lessons & improvement candidates (ranked)
1. *(watch — accumulating, do NOT ship on one day)* **Volume sub-score as an entry filter.** Today the four
   losers were all low-volume (conf_volume ≤0.23) and the three vol=1.0 entries avoided a real loss — the
   cleanest volume/outcome split yet. **But** 07-14 was the exact inversion (high-vol WMT = biggest stop),
   and 07-07/07-10 also found volume doesn't rank outcomes. Shipping a volume floor now would **overfit to
   today and contradict a direct recent counterexample**. Track whether "low-vol entries fade" recurs on 2–3
   more independent sessions before designing a filter; log the per-trade volume/outcome each day.
2. **Lower IMP-013's `SIZE_CONFIDENCE_CAP` 85 → ~80 — still NOT justified.** The only ≥80 entry today (MSFT
   80.31) was a **−$1.36 scratch**, so the ≥80 band did **not** bite today (80-89 barely moved to −$33.73/17).
   No ≥85 binding again → IMP-013 remains bound **only once live** (INTC 07-09), still essentially unproven;
   the 07-13/07-14 gate ("IMP-013 has several more observations") is **still unmet**. Lowering it now would
   confound its own evaluation and target a cohort that didn't cause today's damage. Revisit once IMP-013 has
   ≥2–3 more live bindings AND the 80-89 band deteriorates on fresh data.
3. *(watch, unchanged)* **Broad-adverse-day MTM daily-loss stand-down** (07-07 candidate). Today −$38 is a
   modest soft-loss, not a whipsaw disaster (had a +$30.87 winner) → does **not** add a qualifying occurrence.
   Still needs live open-P&L tracking + 1–2 genuine broad-adverse sessions before deliberate design.
4. *(watch, unchanged)* Break-even/MFE stop stays **downgraded** — SE and NFLX both faded straight from entry
   with no favorable excursion, so a break-even lock would not have helped either loser today (reinforces it).

### Decision — NO CODE CHANGE WARRANTED today
A −$38 soft-loss on a fade/regime tape, whose damage was two **correctly-stopped** down-move exits (both
**cleanly reconciled by IMP-014** — its 3rd & 4th live catches) partly offset by GOOG's clean trend win, and
whose remainder was four near-flat scratches, offers nothing today's data independently justifies changing.
The single tempting lever — a **volume floor** — is the cleanest signal in *today's* book but is **directly
contradicted by 07-14** and would overfit one session; the other lever (lower the ≥80 cap) is **gated off**
(IMP-013 still bound once) and **wasn't today's problem** (MSFT ≥80 scratched to breakeven). Books reconcile
to the cent, infra was flawless, no positions carried. **"Reviewed, no change warranted" is the disciplined
call** — the real positive is process: IMP-014 has now cleanly caught 4 down-move stops across 2 sessions,
retiring the 07-10 weekly's #1 concern. Candidates #1 (volume) and #2 (≥80 cap) logged, not shipped.

### Notes for pre-market research
- **Book CLEAN & FLAT into Thu 07-16** — 0 broker positions, 0 DB-open rows, equity **$9,155.03** all cash.
  **Nothing locked**; watchlist free (subject to the earnings parks below).
- **⚠️ EARNINGS PARKS — action for the Thu 07-16 routine:** **TSM reports Thu 07-16 pre-open** and **UNH Thu
  07-16 pre-open (8am ET)** → **both already parked** for the overnight-into-print carry; **keep parked through
  their prints, re-enable after.** **NFLX reports Thu 07-16 AFTER the close** → **Thu 07-16 is NFLX's last
  pre-print session, so the Thu routine should PARK NFLX** (same naked-into-binary discipline). NFLX was
  correctly kept today and it stopped out −1.97% (regime, not a quality park).
- **GOOG** — the day's only win (+$30.87) rode a **full-confirm-stack** (trend/rsi/vol/vlt all 1.0) clean
  uptrend; the megacap trend engine is intact. **Keep.**
- **SE & NFLX** both stopped out on straight-down fades on **thin volume** (conf_volume 0.23 / 0.095) — flag
  as **low-volume-fade-prone on this regime**, but **not** signal-quality parks (they signalled fine); keep,
  on notice. **MSFT/JPM** re-enabled/megacap, chopped to scratch — regime, keep.
- **Fade-tape watch:** 3rd straight chop/fade session. Only full-confirm-stack trends (GOOG) paid; mid-conf
  weak-cross entries faded. If PPI/Warsh keep the tape rangebound, expect more low-conviction scratches — a
  **regime** issue, no watchlist fix.
- **QCOM / BIRD / ENPH / WPM / XOM / COST stay parked** (chip laggards / oil-headline / no trend).

---

## 2026-07-16 — Daily Review

### Stats
- Closed trades (DB): **1** — 0W / 1L → **0% win rate**. Net realized P&L **−$20.64** (−1.16%).
  Single trade **BABA**. Account **equity $9,134.36** (all cash, **0 open positions** at broker
  after the EOD flatten).
- **Books exact to the cent.** Pre-open equity $9,155.03 → close $9,134.36 = **−$20.67** mark-to-market
  ≈ DB realized **−$20.64** (sub-cent rounding). Broker **flat** (`/v2/positions` = []); today's
  6 Alpaca orders = **1 entry fill @119.136 + 1 EOD-flatten sell @117.76** + the bracket stop/limit legs
  (replaced by the trailing ratchet, then **canceled cleanly at flatten** — no naked legs), every fill
  matching `dbo.trades` (entry 119.136, exit 117.76). No phantoms, nothing carried, no naked overnight,
  no NAKED page. Model A.
- **Service healthy:** `active` since the 11:35 UTC pre-market restart (**NRestarts=0**), running on
  IMP-014. Warmup primed **20/20** from history, 20-symbol IEX subscribe confirmed (NFLX absent per the
  earnings park; TSM/UNH present). **Zero 504s / 422s / errors** all session.
- **Regime:** mixed/soft, chip-heavy headwind — **Asia semis sell-off** (KOSPI −6%, Nikkei −3%) + rotation
  OUT of chips INTO Big Tech, exactly as the 07-16 pre-market flagged. The long-only 5m gate **self-protected**:
  only **1 entry taken all day**, a wall of `crossover < 0.20` and `confidence < 60` rejections otherwise.
- Confidence vs outcome (all-time, `vw_confidence_outcome`): **70-79 the peak +$220.43 (53%, 59 tr)**,
  60-69 **−$6.90 (43%, 109 tr)** [BABA 61.4 added here], **80-89 −$33.73 (41%, 17 tr)**, **90-100 −$144.42
  (0%, 3 tr, unchanged — no 80+ entry today)**.

### Trade-by-trade review (Model A; entry times UTC)
- **BABA** 13:51 @119.136, conf **61.43** (xo 0.468, trend 0.659, rsi 1.00, **vol 0.000**, vlt 0.949),
  qty 15, stop 116.69 / target 130.98 → **EOD flatten @117.76** **−$20.64 (−1.16%)**. Only trade.
  **Root cause: market regime, not a fixable defect.** A mid-conviction (61.4, marginal 60-69 band)
  weak-cross entry that never trended: it drifted down from entry on a chip-soft tape, the trailing stop
  ratcheted from 116.69 but never re-triggered (exit 117.76 sat well above the original stop), so it simply
  **faded to the wall-clock EOD flatten** for a contained −1.16% loss. Never threatened the −2% floor;
  no stop-placement, slippage, or infra fault. Classic fade-tape scratch-to-small-loss.

### What worked / what didn't
- **Worked — gate discipline on a hostile tape.** With Asia semis −6% and a chip-rotation headwind, the
  long-only 5m gate correctly **refused to open longs into weakness** — only 1 entry all day, and the many
  rejections were the *right* ones (WMT conf 72.1 xo 0.08, MSFT conf 74.0 xo 0.13 → **IMP-011 crossover
  floor** filtered the weak-cross high-conf chop cohort as designed). Exit infra flawless: bracket legs
  canceled cleanly at the 19:45 flatten, sell filled in liquid RTH, broker flat, books exact to the cent.
- **Didn't:** the one entry the gate *did* allow (BABA, marginal 61.4 band) faded — the persistent
  **no-edge-on-a-fade-tape** pattern, now a **4th consecutive soft regime-loss day** (07-13 −$51, 07-14 −$62,
  07-15 −$38, 07-16 −$20.64; each successively *smaller* as trade count falls on the tightening tape).
- **Volume-floor candidate REFUTED again (do NOT ship).** Today's sole loser BABA had **vol sub-score 0.00** —
  the exact feature 07-15 tentatively flagged as a "low-vol-fades" signal. But the all-time segmentation is
  the **opposite**: **vol=0 is the BEST bucket (+$239.28, 30 tr, avg +$7.98)**, vol≥0.5 the **worst
  (−$180.98, 101 tr)**. A volume floor would have blocked today's trade for the wrong reason and is
  contradicted by the full history — the 07-15 "watch" candidate is now **actively refuted**, not just unproven.

### Lessons & improvement candidates (ranked)
1. *(NEW — watch, sample too small to act)* **Crossover sub-score ≥0.7 is a stark loser.** All-time
   segmentation of *taken* entries: xo 0.5–0.7 **+$275.97 (12W/22, 55%)** = the money band; **xo≥0.7 = 1W/8,
   −$221.61 (avg −$27.70)** — very-strong crossovers appear to be late/overextended or reversal entries. This
   is the top-end mirror of IMP-011's 0.20 floor and is **not yet addressed**. **But n=8 → shipping a MAX_CROSSOVER
   cap now would overfit** exactly as the routine warns. **Track:** log crossover-vs-outcome each day; revisit a
   soft high-crossover de-rate (or cap) once the ≥0.7 cohort reaches ~15–20 trades and holds negative.
2. *(refuted — DROP)* **Volume sub-score as an entry filter.** See above — history inverts the 07-15 intraday
   read (vol=0 is the best bucket, not the worst). **Do not build a volume floor.** Close the candidate.
3. **Lower IMP-013's `SIZE_CONFIDENCE_CAP` 85 → ~80 — still NOT justified & still gated.** No ≥80 entry at
   all today (peak 61.4) → IMP-013 remains bound **only once live** (INTC 07-09). The 07-13/07-14/07-15 gate
   ("needs ≥2–3 more live bindings AND 80-89 deterioration") is **still unmet**. Revisit later.
4. *(watch, unchanged)* **Broad-adverse-day MTM daily-loss stand-down.** Today −$20 is a *shrinking* soft-loss
   with 1 trade, not a whipsaw disaster → does **not** add a qualifying occurrence. Needs live open-P&L
   tracking + 1–2 genuine broad-adverse sessions before design.

### Decision — NO CODE CHANGE WARRANTED today
A **single** regime-driven −$20.64 loss — one marginal-band weak-cross entry that faded on a chip-soft/
rotation tape the morning research correctly predicted — is the **weakest possible basis** for a strategy
change, and the day's only novel signal (crossover ≥0.7 losing) rests on **8 trades** = textbook overfit
risk. The tempting lever (a volume floor) is now **actively refuted** by the full history. Both open changes
(**IMP-013** sizing cap, bound once; **IMP-014** down-move reconcile, 4 clean catches) remain **under
observation** — a third concurrent change would confound them. Books reconcile to the cent, infra was
flawless, gate discipline was exactly right (self-protected into a semis sell-off), nothing carried.
**"Reviewed, no change warranted" is the disciplined call.** Candidate #1 (crossover ≥0.7) logged to watch;
candidate #2 (volume floor) closed as refuted.

### Notes for pre-market research
- **Book CLEAN & FLAT into Fri 07-17** — 0 broker positions, 0 DB-open rows, equity **$9,134.36** all cash.
  **Nothing locked**; watchlist free (subject to the NFLX action below).
- **⚠️ EARNINGS ACTION for the Fri 07-17 routine: RE-ENABLE NFLX.** NFLX reported **after today's close
  (07-16)** and was correctly parked for it; the binary is now resolved → **re-enable Fri once the post-print
  gap is digested** (check direction/size before it can open a long). **TSM & UNH** were re-enabled today
  post-print and behaved as regime names (no entries) — **keep enabled.**
- **BABA** — today's only trade, a **mid-conviction weak-cross fade** (conf 61.4, xo 0.47, vol 0.00) to a
  −1.16% EOD flatten; not a signal-quality or liquidity park (it signalled fine, regime faded it) → **keep,
  on notice as fade-prone in this tape.**
- **Chip cohort (AVGO/AMD/INTC/MU/TSM/NVDA)** — the 5m gate **never opened a single long** into the Asia-led
  semis sell-off; the long-only self-protection worked exactly as intended → **keep, no watchlist fix** (regime
  headwind, not symbol quality). If Asian semis keep bleeding, expect continued chip-side flatness.
- **Fade-tape watch — 4th straight chop/fade session.** Trade count is *falling* (7→1) as the gate tightens on
  a rangebound/rotation tape; only full-confirm-stack megacap trends have paid recently. This is a **regime**
  issue with **no watchlist fix** — resist adding momentum names into rotation chop.
- **QCOM / BIRD / ENPH / WPM / XOM / COST stay parked** (chip laggards / oil-headline / no trend).

---

## 2026-07-17 — Daily Review

### Stats
- Closed trades (DB): **5** — 0W / 5L → **0% win rate**. Net realized P&L **−$113.26**
  (avg −$22.65/trade). No winners; avg loss −$22.65, **profit factor 0.00**. Account
  **equity $9,021.08** (all cash, **0 open positions** at broker after the EOD flatten).
- **Books exact to the cent.** Pre-open equity $9,134.34 → close **$9,021.08 = −$113.26**
  mark-to-market == DB realized **−$113.26**. Broker **flat** (`get_all_positions()` = []),
  cash == equity, nothing carried, no naked overnight, no NAKED page. Model A throughout.
- **Service healthy:** `active` since the 11:35 UTC pre-market restart (**NRestarts=0**),
  running IMP-011/013/014. Warmup primed **21/21**, 21-symbol IEX subscribe (NFLX present per
  the earnings re-enable). **Zero 504s / 422s / errors** all session; EOD flatten fired clean
  at 19:45 UTC.
- **This is the WORST of a now-FIVE-day soft/regime-loss streak** (07-13 −$51, 07-14 −$62,
  07-15 −$38, 07-16 −$20.64, **07-17 −$113.26**) — the shrinking trend BROKE today as a broad
  risk-off semis selloff re-widened the damage. Second-worst single day of the period after
  **07-07 −$179** (the originating broad-whipsaw session).
- Confidence vs outcome (all-time, `vw_confidence_outcome`): **70-79 the peak +$156.97 (51%,
  61 tr)** [INTC 76.24 + NFLX 73.71 both lost today → band fell from +$220 to +$157], **60-69
  −$56.70 (42%, 112 tr)** [UNH/MU/TSM added], **80-89 −$33.73 (41%, 17 tr)**, **90-100 −$144.42
  (0%, 3 tr, unchanged — no ≥80 entry today; peak conf was INTC 76.24)**.

### Trade-by-trade review (Model A; entry times UTC)
All five were **long entries into the premarket-flagged broad risk-off, semis-led selloff**
(Nasdaq-100 futures −1.9%, SOXX −3.7%, NVDA/MU/INTC −3–4% on AI-spending jitters). Three of the
five (MU/TSM/INTC) were the exact chip cohort the morning research called out.
- **INTC** 17:32 @97.66, conf **76.24** (xo 0.457, trend 1.0, rsi 1.0, vol 0.562, vlt 0.941),
  qty 22 → **broker-side stop @95.86** **−$39.60 (−1.84%)**. **Biggest loss.** Highest-conf
  entry of the day, into the −4% chip tape; fell straight from entry, no higher-high ratchet →
  classic down-move stop. **Caught cleanly intraday by IMP-014** (booked `stop/target filled
  broker-side` @18:15, not a late EOD row).
- **TSM** 17:17 @403.57, conf 63.36 (xo 0.208, trend 0.743, vol 0.484), qty 4 → **broker-side
  stop @395.52** **−$32.20 (−1.99%)**. **2nd-biggest**, near the −2% floor. Weak-cross entry on
  an intraday chip bounce that immediately resumed lower. **IMP-014 catch** @19:08.
- **NFLX** 18:43 @69.39, conf 73.71 (xo 0.292, vol 1.0, all confirms high), qty 31 → **EOD
  flatten @68.62** **−$23.85 (−1.11%)**. First session back after the earnings re-enable; opened
  a long into the post-print downtrend on an intraday bounce, faded to the flatten. Regime, not a
  quality issue (it signalled fine).
- **UNH** 16:06 @432.15, conf **60.14** (xo 0.291, trend 0.651, vol 0.225), qty 4 → **EOD
  flatten @428.04** **−$16.44 (−0.95%)**. Marginal-band earliest entry; drifted down all session,
  trailing stop never re-triggered, faded to the flatten.
- **MU** 16:30 @885.18, conf **60.04** (xo 0.224, trend 1.0, vol 0.00), qty 1 → **broker-side
  stop @884.01** **−$1.17 (−0.13%)**. Near-scratch; qty 1 (high price / small alloc) contained it.
  **IMP-014 catch** @17:57.
- **Root cause (all 5):** **market regime — a broad risk-off, semis-led selloff, exactly as the
  07-17 pre-market predicted.** The long-only 5m gate, which the morning research expected to
  "self-protect," instead opened 5 longs on intraday bounces that each resumed lower. The two
  full chip stops (INTC −39.60 + TSM −32.20 = **−$71.80 = 63% of the day's loss**) were correct
  down-move stops on the −4% semis tape; NFLX/UNH faded to flat-ish flattens; MU was a scratch.
  Losses contained (worst −1.99% at TSM's near-floor stop), no risk-limit trip, no stop-placement,
  slippage, or infra fault.

### What worked / what didn't
- **Worked — IMP-014's 5th/6th/7th live catches.** All three down-move broker-side stop fills
  (MU 17:57, INTC 18:15, TSM 19:08) were detected within a watchdog tick and booked at their
  **true intraday price/time** tagged `stop/target filled broker-side` — not late EOD rows — and
  the symbols freed to WAITING. Zero double-exit / double-Telegram. Exit infra flawless: wall-clock
  EOD flatten fired 19:45, NFLX/UNH sold in liquid RTH, broker flat, books exact to the cent.
- **Didn't:** the long-only crossover strategy has **no edge — and now takes real damage — on a
  broad risk-off down day.** The gate did NOT self-protect as the morning research hoped: 5 mid-band
  crossovers (xo 0.21–0.46) fired on intraday bounces and all faded. This is the SAME failure mode
  as **07-07** (−$179, 11 mid-band longs into a broad whipsaw, 1W/10L): *the 5m gate opens multiple
  longs on intraday bounces during a market-wide adverse tape, and they all fade/stop.* Two clean
  qualifying broad-adverse sessions are now on record (07-07 whipsaw, 07-17 risk-off selloff).

### Lessons & improvement candidates (ranked)
1. **⬆ ELEVATED — Broad-adverse-day stand-down / daily-loss circuit breaker.** First logged
   **07-07** (the −$179 whipsaw) with the explicit gate *"design it on MTM drawdown, gather ≥1–2
   more broad-adverse days as evidence, and ship deliberately — NOT rushed off one day."* **Today
   is that additional qualifying broad-adverse session** (07-17 −$113, 0W/5L, broad risk-off; same
   many-mid-band-longs-into-an-adverse-tape failure mode). The gate's evidence bar is now MET (2
   genuine sessions: 07-07 + 07-17, together **−$292 = the bulk of the recent drawdown**). The bot
   still has **no daily-drawdown or consecutive-loss entry halt** (only the feed-loss fail-safe).
   **Concrete design brief for the deliberate build:** track intraday **realized+unrealized (MTM)
   P&L vs the session-open equity**; when the session drawdown breaches a floor (candidate ≈ **−2%
   to −2.5% of open equity**, i.e. ~−$180 to −$225 at current equity — sized above a normal 3–4
   contained-stop day and below these two disaster days) OR **N consecutive full stop-outs** (≈3),
   **stop opening NEW entries for the rest of the session** (keep managing/flattening open ones;
   reset at the next session open). On today's timeline a realized −$90 / 3-consecutive-loss halt
   after INTC (18:15) would have **blocked NFLX (−$23.85)**; on 07-07 it would have blocked most of
   the 10 losers. **Why still NOT shipped tonight:** (a) the routine's own chosen design is
   **MTM-based**, which needs new intraday equity/open-P&L tracking state — a **critical-path
   change**, not a one-line tweak, and rushing it reactively post-loss is the exact overfit trap the
   dailies warn against; (b) it is a **behavioral entry change** that would **confound IMP-013**
   (sizing cap, still bound only once — needs several more >85 bindings) and muddy IMP-014's fresh
   proving; a third concurrent behavioral change violates the one-clean-variable discipline. → **Ship
   deliberately as the NEXT change, with the weekly review's blessing, once IMP-013 has more bindings
   or is graded.** This is now the **#1 design priority.**
2. *(watch, unchanged)* **Crossover ≥0.7 de-rate/cap** (07-16 candidate). N/A today — all five
   crosses were 0.21–0.46, none ≥0.7. Cohort still ~8 trades; keep accumulating before acting.
3. **Lower IMP-013's `SIZE_CONFIDENCE_CAP` 85 → ~80 — still NOT justified & still gated.** No ≥80
   entry today (peak INTC 76.24). IMP-013 remains bound **only once live** (INTC 07-09); the
   multi-review gate ("≥2–3 more live bindings AND 80-89 deterioration") is **still unmet**. Revisit later.
4. *(refuted — closed)* **Volume floor** — the two full losers today split on volume (INTC vol 0.562
   full-loss vs MU vol 0.00 scratch; TSM 0.484), reconfirming volume does NOT rank outcomes. Stays closed.
5. *(refuted — do NOT re-propose)* **Market-direction / skip-bearish regime gate** was analyzed and
   **refuted with data on 07-09**. Today's fix is a *drawdown* stand-down (candidate #1), NOT a
   market-direction filter — the two are distinct; do not conflate.

### Decision — NO CODE CHANGE WARRANTED today
A −$113 loss whose entire damage is a **broad risk-off, semis-led selloff the morning research
predicted to the sector** — five long entries on intraday chip/mega-cap bounces that each resumed
lower, two correct down-move stops (both **cleanly caught by IMP-014**, its 5th–7th live validations)
plus two fades and a scratch — is a **market-regime** outcome, not a fixable single defect that today
independently justifies changing. The one high-impact lever this day strengthens (the broad-adverse
stand-down) is now **evidence-qualified** (2nd genuine session) and **elevated to #1 design
priority**, but its routine-chosen **MTM design is a critical-path build** that must be shipped
**deliberately** — not rushed reactively post-loss, and not concurrently with **IMP-013** (bound once,
unproven) and **IMP-014** (still proving), which a third behavioral change would confound. Every other
lever is refuted (volume floor, market-direction gate), gated (≥80 cap — not today's problem, no ≥80
entry), or premature (crossover-cap, n≈8). Books reconcile to the cent, infra flawless, gate/exit
discipline correct, nothing carried. **"Reviewed, no change warranted" is the disciplined call** — with
the daily-loss stand-down now teed up as the next deliberate build. Candidate #1 elevated, nothing shipped.

### Notes for pre-market research
- **Book CLEAN & FLAT into Mon 07-20** — 0 broker positions, 0 DB-open rows, equity **$9,021.08**
  all cash. **Nothing locked**; watchlist free. (Next session is Monday 07-20; today was Friday.)
- **Chip cohort (INTC/TSM/MU/NVDA/AVGO/AMD)** took the day's real damage on the AI-spending-jitters
  semis selloff (SOXX −3.7%): **INTC −$39.60 and TSM −$32.20 were the two full stops** (63% of the
  loss). All signalled and stopped correctly — **regime, NOT symbol/liquidity quality; keep all
  enabled.** If AI-capex jitters persist into Monday, expect continued chip-side adverse pressure —
  resist adding chip/momentum names into a risk-off tape.
- **NFLX** — first session back after the earnings re-enable; opened a long into its post-print
  downtrend and faded −1.11% to the flatten. Not a quality park (binary resolved, signalled fine),
  but it is **in a fresh post-earnings downtrend** — **keep, on notice as fade-prone** until it bases.
- **UNH** faded to a −0.95% flatten (marginal 60.14 band); **MU** a −0.13% scratch — regime, keep both.
- **Regime, not watchlist:** 5th straight soft session, and today it turned into the worst on a
  broad risk-off day. No single symbol is broken; the issue is the strategy opening longs into a
  market-wide down tape — a **strategy/regime** matter (see the elevated stand-down candidate), **not
  a watchlist fix.** No parks indicated.
- **QCOM / BIRD / ENPH / WPM / XOM / COST stay parked** (chip laggards / oil-headline / no trend).

---

## 2026-07-20 — Daily Review

### Stats
- **Closed trades (DB, corrected): 7 — 2W / 5L → 29% win.** Net realized **−$93.33**
  (avg −$13.33/trade). Avg win **+$24.44**, avg loss **−$28.44**, **profit factor ≈ 0.34**.
  Best **+$33.36** (BABA), worst **−$58.46** (NVDA). Account **equity $8,927.72** (all cash,
  0 open positions), from $9,021.08 pre-open = **−$93.33** — books now tie to equity to the cent.
- **⚠️ The report's headline (+$6.28, 3W/4L, 43%) was FICTITIOUS.** A data-integrity bug booked
  **NVDA as a phantom +$41.15 win** when it was really a **−$58.46 stop-out** — a **$99.61** error
  that exactly equals the DB↔equity gap ($6.28 DB vs −$93.33 equity). The NVDA row was
  broker-verified-corrected this run (entry 206.45→**206.807**, exit 209.615→**202.31** @19:16:18,
  pnl +41.15→**−58.46**), restoring the book. **The real day is a −1.03% loss, not a small gain.**

### Trade-by-trade review (Model A throughout; times UTC)
- **NVDA** 13:33:06 @**206.807** (buy filled ~13:35:52, ~2.5 min late), conf **82.40**
  (xo 0.55 / trend 0.86 / rsi 1.0 / vol 1.0 / vlt 0.93) → broker-side stop **@202.31 @19:16:18**,
  **−$58.46 (−2.17%)**. Worst. A top-of-morning long into the semis weakness that stopped out.
  **The IMP-015 bug (below) originally recorded this as a +$41.15 win** — a ≥80-conf name that was
  actually the day's biggest loser, reinforcing the ≥80 underperformance pattern.
- **BABA** 13:51 @118.92, conf **81.72** (xo 0.66 / trend 1.0 / rsi 1.0 / vol 0.50 / vlt 0.96)
  → EOD flatten @120.51, **+$33.36 (+1.34%)**. Best. Clean trend, held all session. Regime winner.
- **GOOG** 14:16 @359.39, conf **72.38** (xo 0.49 / trend 1.0 / rsi 0.70 / vol 0.57 / vlt 1.0)
  → broker-side stop @352.07 @17:16, **−$36.60 (−2.04%)**. Full stop; faded straight off entry.
- **MSFT** 15:39 @397.97, conf **67.17** (**xo 0.23 weak** / trend 0.90 / rsi 1.0 / vol 0.49 / vlt 1.0)
  → EOD flatten @401.85, **+$15.52 (+0.97%)**. Weak cross but trend/rsi carried a small win.
- **AVGO** 15:43 @381.43, conf **62.54** (xo 0.25 / trend 1.0 / rsi 1.0 / **vol 0.0** / vlt 1.0)
  → EOD flatten @379.35, **−$6.25 (−0.55%)**. Near-scratch; thin-volume marginal setup.
- **AMD** 15:52 @514.44, conf **67.69** (xo 0.34 / trend 1.0 / rsi 1.0 / vol 0.17 / vlt 1.0)
  → broker-side stop @507.30 @19:14, **−$14.28 (−1.39%)**. Full stop on the chip weakness.
- **SE** 16:11 @108.00, conf **61.58** (**xo 0.22 just above the 0.20 floor** / trend 1.0 / rsi 1.0
  / **vol 0.0** / vlt 1.0) → broker-side stop @105.58 @19:45, **−$26.62 (−2.24%)**. Weakest setup,
  worst % loss — a near-floor crossover on zero relative volume that faded to its stop.

### What worked / what didn't
- **Worked:** BABA (clean trend, +$33.36) and MSFT (trend-carried, +$15.52) held green; the exit
  infra otherwise behaved (all real stops filled broker-side, EOD flatten clean, broker flat at close).
- **Didn't:** (1) **A data-integrity bug corrupted the book** — the IMP-014 wall-clock MANAGING sweep
  fired ~30s after the NVDA entry while its buy was **still unfilled** (delayed ~2.5 min); the broker
  404'd (no position yet), `reconcile_exit` mistook "not opened" for "already flat," and matched a
  **stale prior-session NVDA sell (@209.615)** as a phantom exit — booking a +$41 win, freeing NVDA to
  WAITING, and **desyncing bot state from the broker** (the real buy then filled and rode to a real stop
  the DB never saw). This is the day's #1 issue and the shipped fix. (2) **Continued semis/AI-capex
  regime damage** — NVDA/AMD/AVGO plus GOOG all faded/stopped (same risk-off tape as 07-17). (3) The
  **≥80-conf band underperformed again** (NVDA 82.40 the worst loser); correcting NVDA flips today's
  80-89 contribution from ~+$41 phantom to ~−$58 real, deepening the top-band inversion.

### Lessons & improvement candidates
1. **[SHIPPED — IMP-015] Phantom-exit-on-unfilled-entry.** `reconcile_if_closed` now confirms the
   **entry buy has actually filled** (`entry_fill_price` returns a price) before reconciling a
   broker-side exit; until then the position simply hasn't opened, so it stays MANAGING and re-checks
   next tick. This closes the exact NVDA book-corruption + state-desync path. Highest impact: it
   protects the win-rate/P&L/confidence data that ALL tuning (incl. the stand-down) depends on.
2. **[DEFERRED — the standing #1 strategic priority] Broad-adverse-day / daily-loss MTM stand-down.**
   Its evidence gate is met (07-07, 07-17), but **today it was correctly preempted**: a fresh
   book-corruption bug surfaced, and the routine's own discipline is *fix data integrity before shipping
   a strategy change* — you cannot ship (or later judge) a stand-down on top of a corrupted book. Ship
   it on the next clean-book session as its single change (session MTM vs open equity, halt new entries
   at ~−2%, reset next session). It **would have helped today** (−1.03% approaches the trigger).
3. **[watch] ≥80 confidence + weak-cross/zero-volume entries** keep underperforming (NVDA 82.40 loss;
   SE xo 0.22/vol 0, AVGO xo 0.25/vol 0). Gather more; IMP-013's cap (85) doesn't reach the 80-85 zone.

### Notes for pre-market research
- **Book CLEAN & FLAT into Tue 07-21** — 0 broker positions, 0 DB-open rows, equity **$8,927.72** all
  cash after the NVDA-row correction. Nothing locked; watchlist free.
- **Semis/AI-capex regime persists into a 2nd week** — NVDA/AMD/AVGO all stopped today (plus GOOG), the
  same risk-off tape that ran all of last week. All signalled and stopped **correctly = regime, not
  symbol/liquidity quality; keep enabled.** Resist adding chip/momentum names into this tape.
- **BABA** was the clean trend winner two setups in a row — behaving well; keep.
- **SE** (xo 0.22 / vol 0.0, −2.24%) and **AVGO** (vol 0.0) traded on **zero relative volume** — thin,
  fade-prone setups, but that's a signal-scoring matter, **not a watchlist park** (both liquid, both
  signalled). No parks indicated on quality grounds.
- **NVDA** — the phantom-exit was a *bot bug*, not a symbol problem; NVDA's real trade was a normal
  regime stop-out. Keep enabled, no action.
- QCOM / BIRD / ENPH / WPM / XOM / COST stay parked (unchanged).

---

## 2026-07-21 — Daily Review

### Stats
- **8 trades, 5W / 3L → 62% win.** Net DB realized **−$9.15** (avg −$1.14). Avg win **+$19.01**,
  avg loss **−$34.73**, **profit factor ≈ 0.91** — winners small, losers larger but each contained
  (worst −2.13%, a normal stop). Best **+$34.14** (TSM), worst **−$40.05** (MU). Account
  **equity $8,918.55** (all cash, **0 open positions**), from $8,927.70 pre-open = **−$9.15**.
- **Books exact to the cent.** DB realized −$9.15 == broker equity delta −$9.15 (last_equity
  $8,927.70 → $8,918.55); broker **flat** (0 positions), cash == equity. Nothing carried, no naked
  overnight, no phantom rows, no NAKED page. **First clean-book session since the IMP-015 fix — the
  precondition the reviews set for shipping the stand-down.** Model A throughout.
- **Service healthy:** `active` since the Fri 07-17 11:35 UTC restart (NRestarts=0) through today's
  post-close IMP-016 restart; zero 504s/422s/errors all session; EOD flatten clean at 19:45 UTC.
- **A benign, mildly-green tape** — snapped the recent soft streak (07-13..07-20 all red). Not a
  broad-adverse day; a choppy risk-on chip bounce (PPI cooler; semis revived, as the pre-market read
  and a Perplexity post-close check both flagged) where early longs whipsawed and afternoon ones worked.
- Confidence vs outcome (all-time, `vw_confidence_outcome`): **70-79 the peak +$74.03 (50%, 66 tr)**,
  **60-69 −$56.20 (42%, 117 tr)**, **80-89 −$53.77 (45%, 22 tr)**, **90-100 −$144.42 (0%, 3 tr,
  unchanged — no 90+ entry today)**. Notably the **≥80 band was net GREEN today** (TSM 88.44 +$34.14,
  MU 82.30 +$10.98, MU 81.21 −$40.05 → +$5.07), a break from the recent top-band inversion.

### Trade-by-trade review (Model A; entry times UTC)
- **TSM** 13:36 @418.50, conf **88.44** (xo 0.93 / t 1.0 / r 0.57 / **v 1.0** / vlt 0.93), q6 → **EOD
  flatten @424.19 +$34.14 (+1.36%)**. **Best.** Earliest entry (09:36 ET), strong fresh cross + maxed
  trend/volume; rode the chip rebound all day. Textbook good signal.
- **INTC** 13:51 @103.29, conf 76.89 (xo 0.87 / t 1.0 / r 1.0 / **v 0.10** / vlt 0.63), q22 →
  **broker-side stop @101.48 −$39.78 (−1.75%)**. Early-morning long stopped ~18 min in **before the
  rebound firmed**; caught cleanly intraday (IMP-014).
- **MU** 13:51 @939.92, conf 81.21 (xo 0.997 / t 1.0 / r 1.0 / **v 0.00** / vlt 0.75), q2 →
  **broker-side stop @919.89 −$40.05 (−2.13%)**. **Worst.** Same early whipsaw, near the −2% floor.
- **TSLA** 14:40 @382.71, conf 73.85 (xo 0.45 / t 1.0 / r 1.0 / v 0.36 / vlt 1.0), q5 → **EOD flatten
  @377.84 −$24.35 (−1.27%)**. Faded off entry, drifted to the flatten. Mild regime fade.
- **INTC** 15:06 @103.62, conf 67.33 (xo 0.32 / t 1.0 / r 1.0 / v 0.22 / vlt 0.97), q16 → **EOD flatten
  @105.63 +$32.13 (+1.94%)**. Winner — the **re-entry worked once the chip tape firmed** intraday.
- **NVDA** 15:22 @206.30, conf 71.43 (xo 0.23 / t 0.72 / r 1.0 / v 1.0 / vlt 1.0), q8 → **EOD flatten
  @206.92 +$4.96 (+0.30%)**. Small winner; weak cross, near-scratch.
- **MU** 15:36 @956.67, conf 82.30 (xo 0.42 / t 1.0 / r 1.0 / v 1.0 / vlt 0.97), q2 → **broker-side
  trailing-stop fill @962.16 19:28 +$10.98 (+0.57%)**. Winner — the trailing stop ratcheted **above
  entry** and locked the gain (IMP-013/trailing working as designed).
- **NFLX** 19:17 @67.87, conf 70.27 (xo 0.20 / t 0.71 / r 1.0 / v 1.0 / vlt 1.0), q20 → **EOD flatten
  @68.51 +$12.82 (+0.94%)**. Late winner; behaving well post-earnings.
- **Root cause (net):** a **choppy risk-on chip-bounce day**, not a strategy defect. The two morning
  losses (INTC/MU @13:51) were longs opened **before the rebound solidified** and stopped on the early
  whipsaw; TSLA faded. Every afternoon entry (INTC/NVDA/MU/NFLX) worked as the tape firmed. Losses
  contained (worst −2.13%, a clean stop), books exact, infra flawless, broker flat.

### What worked / what didn't
- **Worked:** exit infra flawless (2 broker-side stops caught intraday by IMP-014; MU's trailing stop
  locked a win above entry; EOD flatten filled clean in liquid RTH; broker flat, books to the cent).
  Afternoon re-entries as the chip tape firmed were the day's green (INTC/NVDA/MU/NFLX). ≥80 band green.
- **Didn't:** early-morning longs (INTC/MU @13:51) whipsawed before the risk-on bounce firmed — timing,
  not signal quality. Losers averaged larger than winners (−$34.7 vs +$19), but that's the normal
  contained-stop-vs-modest-winner shape, and today's tiny net −$9.15 is noise, not a fixable defect.
- **Volume note (still refuted):** the 3 losers again had weak volume sub-scores (INTC v0.10, MU v0.00,
  TSLA v0.36) vs winners mostly v1.0 — but the **all-time volume bands contradict** it (hi-vol ≥0.8 band
  is −$295 over 82 tr; lo-vol <0.3 is **+$110** over 77 tr). Volume does NOT rank outcome; stays **closed**.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED — IMP-016] Broad-adverse-day / daily-loss stand-down.** The weekly review's explicit **#1
   priority** ("evidence gate is MET": 07-07 −$179 + 07-17 −$113 = −$292) and the item deferred across
   07-07/07-17/07-20. IMP-015 (07-20) preempted it to fix a book bug with the instruction *"ship it on
   the next clean-book session as its single change"* — **today is that session** (clean book, benign day,
   one-change slot free). Shipped **deliberately on a calm day, not reactively**: `RiskManager` now halts
   NEW entries for the rest of a session once **3 consecutive losing exits** occur OR the session realized
   loss breaches **2.5% of open equity** (open positions still managed/flattened; resets at the next open).
   Would have blocked INTC+NFLX (−$63) on 07-17 and ~7 losers on 07-07; **does NOT trip on today** (the
   winner reset the streak at 2). 250 tests pass, preflight all-PASS. This was **the week's whole job.**
2. *(watch, unchanged)* **≥80-conf band** — net **green today** (+$5.07) but still −$53.77 all-time; no
   90+ entry. IMP-013's cap (85) still bound only once live. Keep watching; don't touch.
3. *(watch)* **Strong-crossover (xo≥0.40/≥0.70) cohort** — TSM (xo 0.93) won big today; small sample.
   Keep accumulating for a possible top-end de-rate at n≥15–20. Do NOT act.
4. *(refuted — closed)* **Volume floor** — reconfirmed refuted above (all-time bands invert today's read).

### Notes for pre-market research
- **Book CLEAN & FLAT into Wed 07-22** — 0 broker positions, 0 DB-open rows, equity **$8,918.55** all
  cash. Nothing locked; watchlist free.
- **⚠️ BINARY EARNINGS TOMORROW — the Wed 07-22 pre-market routine MUST PARK GOOG + TSLA** before Wed's
  open (both report **after Wed's close**). **Thu 07-23 routine PARKS INTC.** These are the week's queued
  binary parks — do not miss them.
- **Chip cohort bounced but chopped** — TSM traded beautifully (+$34.14, strong cross, held all day);
  INTC/MU **whipsawed in the first 20 min** (early longs stopped before the risk-on bounce firmed) then
  the afternoon re-entries worked. All signalled/stopped correctly = **regime timing, not symbol quality;
  keep all enabled.** Resist chasing chip/momentum adds into the pivotal AI-earnings prints (GOOG/TSLA Wed).
- **NFLX** behaved (+0.94% late winner) — the fade-prone post-earnings watch can be relaxed; keep enabled.
- **No parks indicated on quality grounds.** QCOM / BIRD / ENPH / WPM / XOM / COST stay parked (unchanged).
- **IMP-016 now LIVE** — if a genuine broad risk-off tape hits (e.g. a disappointing GOOG/TSLA print
  Wed night → Thu selloff), expect the stand-down to halt entries after 3 straight losses; that is by
  design. Watch Thu's review for its first live trip (or correct non-trip).

---

## 2026-07-22 — Daily Review

### Stats
- **6 trades, 3W / 3L → 50% win.** Net DB realized **−$36.25** (avg −$6.04). Avg win **+$6.83**,
  avg loss **−$18.91**, **profit factor ≈ 0.36** — the two real stop-outs (NFLX, INTC) are the entire
  loss; the other four round-tripped to a roughly-flat EOD flatten. Best **+$17.94** (AMD), worst
  **−$32.55** (NFLX). Account **equity $8,882.27**, all cash, **0 positions**.
- **Broker reconciles to the cent.** last_equity $8,918.52 → equity $8,882.27 = **−$36.25**, exactly the
  DB realized P&L; broker flat, no drift, no missed fill, nothing carried. Clean book (the IMP-015 family
  is holding — no phantom exits, DB↔equity tie intact).
- **IMP-016 (stand-down) did NOT trip today, correctly.** Two real stops (INTC 16:46, NFLX 18:08) then
  four EOD flattens; session loss −0.41% of equity (backstop is −2.5%) and no 3-in-a-row real-stop run
  before the flatten. A normal chop day is exactly what it should ignore — first *live* observation of
  IMP-016 = benign non-trip, as designed. Its real test still awaits a genuine broad risk-off tape.

### Trade-by-trade review
- **NFLX** (14:06 @70.25, qty 28, conf **65.36** — xo **0.37**, trend 1.0, rsi 1.0, **vol 0.0**, vlt 0.95)
  → stop @69.09 **−$32.55 (−1.65%)**. **Worst.** Lowest-conviction entry of the day (weakest crossover,
  zero volume confirmation) on a thin name into the GOOG/TSLA-earnings caution tape; went underwater from
  entry and rode the full initial stop. **Root cause: signal quality + regime** — a marginal cross with no
  participation into a risk-averse afternoon.
- **INTC** (14:20 @105.79, qty 20, conf **75.02** — xo 0.63, trend 0.71, rsi 1.0, vol 0.65, vlt 0.81)
  → stop @104.59 **−$23.97 (−1.13%)**. A **genuinely strong** signal (best sub-scores of the day) that
  still failed — INTC drifted down all session (own feed: ~$103 by 20:40, below the $104.59 stop).
  **Root cause: regime, not signal** — a good long into a name that faded; nothing wrong with the entry.
- **AMD** (14:13 @549.32, qty 3, conf **64.04** — xo **0.37**, trend 1.0, rsi 1.0, **vol 0.0**, vlt 0.86)
  → EOD flatten @555.30 **+$17.94 (+1.09%). Best.** Note: the **same weak profile as NFLX** (0.37 cross,
  0 volume) — one won, one lost. **A coin flip, not an edge** (n too small to act, but the pattern that
  the 0.37-crossover / 0-volume entries are indistinguishable ex-ante is worth watching).
- **MU** (15:01 @972.90, qty 1, conf 69.06) → EOD flatten @972.68 **−$0.22**. Scratch; never worked,
  never stopped. Regime chop.
- **NVDA** (15:31 @212.58, qty 7, conf 68.59) → EOD flatten @212.76 **+$1.25**. Scratch.
- **AVGO** (17:46 @398.16, qty 5, conf 77.42) → EOD flatten @398.42 **+$1.30**. Scratch; late entry
  (17:46) with little runway before the flatten.

### What worked / what didn't
- **Worked:** the trailing/flatten machinery behaved — the four survivors round-tripped to a clean EOD
  flatten with no naked-overnight risk (0 positions at broker). Reconciliation is spotless. The stand-down
  stayed dormant on a normal day (its intended behaviour).
- **Didn't:** two stop-outs (−$56.52 combined) were the whole day. NFLX was a weak, thin, low-conviction
  entry that shouldn't carry full size into an earnings-caution tape; INTC was a good signal killed by a
  down-drifting regime — not fixable at entry.

### Lessons & improvement candidates (ranked; NO code change shipped today — see below)
Today's −$36 is normal chop, IMP-016 shipped **yesterday** and this is its first (benign) observation, and
every tempting lever is either refuted or unvalidatable tonight. Shipping a second strategy change on top of
an unobserved one, on one chop day, with no way to validate its sign, would violate *protect-capital /
never-overfit / one-traceable-change*. **Reviewed → no change warranted.** Candidates, in priority order:

1. **THE STRUCTURAL LEAK — broker-side stop fills are the entire drawdown (highest impact, needs tooling).**
   Last-30-day exit-reason breakdown: **clean `end-of-day flatten` = +$603.79 (98 tr, 55% win)** — the
   strategy's edge is in *holding to EOD*. But **`stop/target filled broker-side` = −$422.79 (15 tr, 1 win,
   avg −$28.19)** + **`end-of-day flatten (…filled broker-side)` = −$561.94 (32 tr, 6 win)** + trailing
   −$54.69 → **stops bleed ≈ −$1,039** against +$604 of flattens. **Targets sit ~10% away and essentially
   never fill intraday.** The leak is entries that go straight down into the initial 2% stop; the trail
   can't help a position that never goes green.
2. **The reversal early-exit (`RiskManager.check_exit`, "bearish 1-min ribbon cross") is INERT — 0 exits
   ever.** It's implemented + marked done in todo.md (Phase 5) but **never invoked**: `strategy._manage`
   only calls `update_trailing_stop`, and the `_manage` docstring shows this was a *deliberate* choice
   ("returns to WAITING via the EOD flatten… not on a single 1-min pullback"). So it is not a simple wiring
   bug — naively wiring it would chop the profitable +$604 EOD-flatten holds on shallow pullbacks and could
   make things worse. **Leading candidate:** wire an **underwater-guarded** reversal exit (fire *only* when
   the position is below entry — cut the −$28 pure-stop losers earlier, never touch a green runner).
   **BLOCKER:** its net effect on the winners bucket (many flatten winners surely dip below entry before
   recovering) **cannot be validated with unit tests alone — USTradeBot has NO replay/backtest harness.**
3. **Build a minimal historical replay harness (infrastructure, top enabler).** Without it, exit/entry logic
   cannot be changed safely — the bot has bled −$435 over 30 days on stops with no way to validate a fix.
   This is the real gate on #1/#2. Too large + risky to rush post-close tonight; propose as a dedicated run.
4. **Confidence-threshold raise — REFUTED, do not do it.** Last-30-day bands: 60-69 −$175.53 (83 tr),
   **70-79 −$132.16 (50 tr, also negative)**, 80-89 +$16.48 (16 tr), 90-100 −$144.42 (3 tr, 0 win). The
   all-time "70-79 sweet spot" has **decayed** — raising `ENTRY_THRESHOLD` 60→70 would cut volume but the
   retained band also loses. No clean confidence edge to exploit this month.
5. *(watch, n=3)* 90-100 band is 0/3, −$144 — extreme outliers; `SIZE_CONFIDENCE_CAP` (85) already limits
   sizing there. Too small to act.

### Notes for pre-market research
- **NFLX is thin and low-conviction here.** Its feed today was very illiquid (1-min volumes in the teens/20s)
  and the bot's NFLX entry was its weakest signal (0.37 cross, 0 volume) and its worst loss (−$32.55). Not a
  park call on one day, but NFLX has now given a fade-then-loss profile twice — **watch liquidity/quality**;
  if it keeps producing 0-volume-subscore entries, consider parking on thin-participation grounds.
- **GOOG + TSLA report tonight (after 07-22 close).** Both were correctly parked this morning. **The GOOG/TSLA
  reaction sets Thu 07-23's regime** — a disappointment could be the first genuine broad risk-off tape and the
  **first real test of the IMP-016 stand-down**. **INTC's queued park fires Thu 07-23** (reports after Thu
  close) — don't miss it; today INTC signalled strongly but faded on regime, consistent with keeping it until
  its own earnings park.
- **Chip cohort (INTC/MU/AVGO/NVDA/AMD) chopped, didn't trend** — regime, not symbol quality; all
  signalled/stopped/flattened correctly. Keep enabled. No adds warranted into tonight's binary Mag-7 prints.
- **Late entries have no runway:** AVGO (17:46) and MU (15:01) entered with little time before the flatten and
  scratched — consistent with prior "late low-conviction entries churn" notes; not acted on (needs more data).

---

## 2026-07-23 — Daily Review

### Stats
- **NO TRADES.** 0 closed, 0 opened, 0 positions. Net realized **$0.00**. Account **equity $8,882.27**,
  all cash — **flat vs the 07-22 close** ($8,882.27), no drift.
- **Broker reconciles to the cent.** `alpaca-usbot` MCP: 0 orders today (`status=all`, after 00:00Z),
  0 positions, equity/cash/portfolio_value all **$8,882.27**. DB agrees (0 rows entered/exited today).
  Nothing carried, nothing missed. Clean book.
- **Not a strategy failure — a risk-off tape the long-only gate correctly sat out.** Perplexity close read:
  **SPX −1.2% (7,408), Nasdaq −2.2% (25,138), risk-off/rotation-out-of-growth, no clean trend**; semis
  pressured by the AI/mega-cap selloff, no MU/JPM/NFLX-specific catalyst. On a down, trendless tape the 5m
  long-gate opens few longs by design — that is the strategy protecting capital, not breaking.

### Trade-by-trade review (no trades → root-cause the zero)
Only **MU reached the entry gate** all session — **3 ENTRY signals, all dropped by the executor** as
`skip MU: position sizing (model A) yields < 1 share`:
- **14:06 MU @ 993.71, conf 79.9** (xo 0.70 trend 0.99 rsi 1.00 vol 0.66 vlt 0.61) — the day's *best*
  signal (70-79 sweet-spot band). Dropped, unsizable.
- **16:16 MU @ 992.87, conf 62.2** (xo 0.26 vol 0.00) — dropped, unsizable.
- **16:24 MU @ 993.39, conf 64.9** (xo 0.30 vol 0.10) — dropped, unsizable.
- Everything else that came close was correctly gated by confidence: JPM 53.8/46.8/48.5, NFLX 57.2 — all
  `< 60`, no entry. So the watchlist wasn't dead; the tape simply didn't produce qualifying longs except MU.

**Root cause of the drop (reproduced in-code):** Model A sizes `notional = buying_power × alloc_fraction`,
then floors to whole shares. Today's runtime config is **MIN_ALLOC 0.05 / MAX_ALLOC 0.10** and **buying
power came back at 1× ($8,882)** (`get_account_info`: `multiplier:"1"`, buying_power==cash==equity). So the
**max** per-trade notional is **0.10 × $8,882 = $888**, but **one MU share ≈ $993**. A single MU share is
**11.2% of equity — above the 10% MAX_ALLOC ceiling** — so the floor correctly yields 0 shares. Reproduced:
conf 79.9 → frac 0.0749 → target $665 → 0.67 sh; conf 62.2 → 0.47 sh; conf 64.9 → 0.50 sh. **The skip is
correct risk behavior, not a bug** — forcing 1 share would breach the max-alloc cap (forbidden: never widen
risk to chase a fill).

**Why MU filled on 07-21/07-22 but not today = buying power, not price.** MU has traded fine for weeks at
$885–$1,182 (07-22 filled qty 1 @ $972.90; 07-21 qty 2 @ $956.67/$939.92). The lever is **buying power**:
the 07-22 pre-market note recorded **BP $35,710 (≈4×)**, which makes 0.10×BP = $3,571 → MU affordable; today
BP is **1× ($8,882)**, so 0.10×BP = $888 < one share. Buying power swinging **4× → 1×** day-to-day (DTBP/RegT
vs cash) silently flips MU (and any >~$890 name) between sizable and unsizable. See candidate #2.

### What worked / what didn't
- **Worked:** capital protection. A risk-off day (Nasdaq −2.2%) produced **zero trades and zero loss** — the
  long-only 5m gate did its job; the confidence gate correctly rejected the marginal JPM/NFLX crosses; and
  the sizing floor refused an over-cap MU position. Broker/DB tie to the cent. IMP-016 stand-down had nothing
  to act on (0 exits).
- **Didn't:** the *one* qualifying signal of the day (79.9%-conf MU, a sweet-spot-band long) was
  un-actionable purely because MU's share price exceeds this account's per-trade notional cap at 1× buying
  power. On a thin-signal day that turned a potential trade into a blank session. It's not a loss, but it is
  wasted watchlist capacity — MU currently generates only un-fillable signals here.

### Lessons & improvement candidates (ranked; NO code change shipped today)
Zero trades, zero loss, capital protected exactly as designed on a risk-off tape. Every candidate either
belongs to pre-market (watchlist) or is a core-sizing change that must be validated deliberately on a calm
day with a backtest — not shipped reactively on a no-trade day. **Reviewed → no change warranted.**

1. **MU is un-sizable at 1× buying power → a watchlist/capital call, not a code change (highest impact,
   OWNED BY PRE-MARKET).** One MU share (~$993) > MAX_ALLOC×equity ($888), so MU can only produce dropped
   signals until either equity grows or buying power returns to ≥~2×. It ate the whole session today. **The
   fix is a watchlist decision (park MU, or accept it's dormant at this account size) — deferred to
   pre-market per the routine's ground rules.** See Notes below. NOT a sizing-code change: making MU fillable
   at 1× BP would require breaching the 10% cap.
2. **Model A sizes off `buying_power`, which swings 1×–4× → position risk isn't anchored to the account
   (real, but needs a backtest; DO NOT ship reactively).** "10% of buying power" was **40% of equity** on the
   4× day (07-22) and 10% today — the same config produces wildly different per-name risk. A capital-*safer*
   variant would anchor the notional base to **equity** (or `min(buying_power, k×equity)`) so a position is a
   stable fraction of the *account*; this only ever *reduces* size on high-BP days (never widens), and is
   inert today (BP==equity). But it changes **all-symbol** sizing off a hypothesis about a *different* day,
   not today's data — exactly the "don't overfit / don't touch sizing casually" line. **Log as a deliberate
   calm-day candidate that needs the replay harness (candidate #3 below) to validate its sign first.**
3. **Still-open enabler: the minimal historical replay/backtest harness** (carried from 07-22 #3). Gates any
   safe change to sizing-base (#2) or the underwater reversal-exit. Unchanged tonight.
4. **Stop-bucket structural leak / inert reversal-exit** (07-22 #1/#2) — unchanged; no new evidence today
   (no trades). Still blocked on the harness.

### Notes for pre-market research
- **⚠️ MU is currently UN-TRADEABLE at this account size + 1× buying power.** At ~$993/share, one MU share is
  11% of equity — above the 10% MAX_ALLOC cap — so **every MU signal is dropped `< 1 share`** (3 dropped
  today, incl. a 79.9%-conf sweet-spot long; the *only* symbol that qualified all day). MU fills only when
  buying power is ≥~2× (it was 4× / BP $35,710 on 07-22). **Decide MU's fate at the watchlist level:** either
  **park MU** (it's occupying a slot and generating only un-fillable signals at 1× BP), or knowingly keep it
  as a dormant "trades only on high-BP days" name. Flagging, not deciding — this is your call.
- **Check today's buying-power figure before curating.** Account came back **1× today (BP $8,882)** vs **4×
  on 07-22 (BP $35,710)**. This flips MU and any **>~$890 share-price name** (none other on the list are that
  expensive — AVGO ~$398, TSLA ~$327, AAPL ~$321, NVDA ~$208 are all fine) between sizable and unsizable. If
  BP is 1× tomorrow, MU stays dormant regardless of tape.
- **INTC park was due to fire Thu 07-23** (earnings after close). Verify it was parked this morning; if not,
  it should be parked before Thu's open — carry forward. (No INTC trade today to confirm state from the tape.)
- **Regime was genuinely risk-off (Nasdaq −2.2%), not a bot problem.** The long-only gate sat out correctly;
  JPM/NFLX marginal crosses were rightly rejected `< 60`. No watchlist add warranted into a down tape; the
  chip cohort remains regime-suppressed. Keep the list as-is unless the tape turns.

---

## 2026-07-24 — Daily Review

### Stats
- Closed trades (DB): **5** — 3W / 2L → **60% win rate**. Net realized P&L **+$45.00**
  (avg **+$9.00**/trade). Avg win **+$22.35** (AAPL +$39.10, NFLX +$22.08, WMT +$5.88), avg loss
  **−$11.03** (MSFT −$13.38, SE −$8.68), **profit factor ≈ 3.04**. Account **equity $8,927.24**
  (cash, 0 open positions at broker).
- **Books tie to the cent.** Broker equity $8,927.24 vs last_equity $8,882.24 = **+$45.00**, which
  matches DB net realized **+$45.00** exactly; 0 open positions (DB & broker both flat), 7 fills / 6
  canceled bracket legs reconciled, no drift, no naked overnight. Clean session.
- **Regime (Perplexity):** S&P & Nasdaq **closed lower — a soft / risk-off tape** (AI-capex overhang
  lingering from Thu), no stock-specific catalyst on any name we traded. **The bot netted green on a
  down tape — a genuine strategy result, not a regime gift.**

### Trade-by-trade review
All 5 exited **"end-of-day flatten"** at 19:45 UTC (15:45 ET). Model A throughout. **No target, stop, or
bearish-cross reversal fired all day — every position rode to the EOD flatten.**
- **AAPL** (13:31 @ $324.90, conf 62.15 — **xo 0.673**, tr 0.598, rsi 0.00, vol 1.00, vlt 1.00) → $332.72
  **+$39.10 (+2.41%)**. Best. Opening-hour entry that rode a clean intraday uptrend all session; the
  strong crossover (0.67) carried it despite the RSI subscore being zeroed (overbought filter). Trend win.
- **MSFT** (13:35 @ $385.49, conf **74.67** — highest today; xo 0.560, tr 0.781, rsi 1.00, vol 0.50, vlt 0.984)
  → $382.81 **−$13.38 (−0.69%)**. Worst. **The day's highest-confidence trade was the only real loser** — it
  drifted down all session, never reached its $377.61 stop, and **never tripped the 1-min bearish-cross early
  exit**, so it flattened red at EOD. Textbook confidence-inversion + inert-reversal-exit leak.
- **NFLX** (14:19 @ $69.27, conf 62.92 — xo 0.318, rsi 1.00, vol 0.498) → $70.19 **+$22.08 (+1.33%)**. Win.
  Low-crossover but rode a steady mid-session uptrend. Post-split price (~$69) sizes cleanly (24 sh).
- **WMT** (14:32 @ $109.01, conf 63.60 — xo **0.234** weak, tr 0.762, vol 0.424) → $109.43 **+$5.88 (+0.39%)**.
  Marginal win; weak crossover, small drift up.
- **SE** (**late** 19:06 @ $100.73, conf 61.94 — xo 0.310, rsi 0.680, vol 0.642) → $100.11 **−$8.68 (−0.62%)**.
  Loss. Entered 15:06 ET, held 39 min, flattened red — late low-conviction churn. (But see below: late entries
  are **not** systematically worse in the full record.)

### What worked / what didn't
- **Worked:** **+$45 green on a soft/risk-off tape** — the long-only 5m gate still found real intraday trends
  (AAPL/NFLX/WMT) when the index faded; PF 3.0; **books exact to the cent** (broker +$45.00 = DB +$45.00), flat
  overnight, service `active`, no risk-limit issues (worst trade −0.69%). AAPL's strong-crossover trend hold
  (+$39) carried the day.
- **Didn't:** (1) **Confidence inversion again** — highest-conf MSFT (74.67) was the only real loser; the top of
  the scale still isn't paying (all-time 90-100 = 0% win / −$144, 80-89 = 45% / −$54). (2) **Inert exit
  machinery** — all 5 rode to the EOD flatten; MSFT trended down all day without tripping the bearish-cross
  early-exit or its stop. This is the documented stop-bucket / underwater-reversal leak, **still blocked on a
  replay harness that does not yet exist** — not shippable blind. (3) SE late low-conviction churn (small).

### Lessons & improvement candidates
1. **(NEW — quantified, tracked, NOT acted) Entry-hour P&L bleed.** Full-history win/PnL by entry hour (UTC):
   **13Z (09:30–10:30 ET open) is the single biggest drain — −$407.34 over 41 trades, 36.6% win, −$9.94 avg**;
   17Z −$113, 19Z −$84 (58.8% win but oversized losers). This **REFUTES a late-entry cutoff** (the SE-loss
   hypothesis): late entries ≥18Z actually win **more** (48.8% vs 43.8% early), so the existing 15:45-ET flatten
   window is the right late guard and needs no tightening. The real candidate is an **opening-range guard**
   (delay/gate first-hour entries). **Not acted today:** today's two 13Z entries netted **+$25.72** (AAPL +$39 /
   MSFT −$13) — today's own tape doesn't justify it, blocking the open would forfeit winners like AAPL, and it's
   a behavioral entry change that deserves its own deliberate run + more confirmation. Building the case (like
   the crossover cohort) — revisit once several more sessions confirm the open-hour drain net of its winners.
2. **Confidence inversion persists** (MSFT 74.67 lost) — governed by standing weekly guidance: **hold IMP-013
   at 85**, and the strong-crossover de-rate is **"do not act yet, n<15–20."** Today's xo≥0.40 cohort (AAPL,
   MSFT) was net **+$25.72**, so no fresh support to act — keep watching, don't touch weights.
3. **Stop-bucket leak / inert reversal-exit** (carried 07-22/07-23) — unchanged; the MSFT ride-to-EOD is fresh
   evidence but the fix is still gated on the **nonexistent replay harness**. No blind exit-logic change.

**Decision: reviewed — NO CHANGE WARRANTED.** A green +$45 / 60%-win day on a soft tape gives no clean single
justified lever: the one loss pattern (SE late) is data-refuted, the strongest new signal (open-hour bleed)
isn't justified by today's own +$25.72 open result and needs its own deliberate run, and the standing weekly
holds (IMP-013 @ 85, IMP-011 @ 0.20, crossover "don't act yet") bind the confidence work. IMP-016 stand-down
still awaits its first genuine trip. Shipping anything today would overfit or contradict standing guidance.

### Notes for pre-market research
- **Book CLEAN & FLAT into Mon 07-27** — broker-confirmed **0 positions**, equity **$8,927.24** all cash.
  Nothing locked.
- **INTC re-enable (07-24) is clean** — INTC was enabled and `active` but produced **no signal / no trade**
  today (no trigger on the soft tape) — no issue, just no cross. Keep enabled.
- **MSFT** — highest-confidence entry of the day yet drifted down all session for the only real loss; that's the
  soft/risk-off tape, **not** a symbol problem. Mega-liquid, keep. No park.
- **SE** — late (15:06 ET) low-conviction entry lost small; liquidity fine, keep. Late entries are **not**
  systematically worse (data: ≥18Z wins 48.8% vs 43.8%), so no park-for-lateness.
- **Regime read:** index closed **lower / soft risk-off** (Perplexity) but the bot found tradable longs
  (AAPL/NFLX/WMT) — a choppy-soft, not a broad-collapse, tape. No watchlist add warranted; no name "never
  signaled" beyond the normal soft-tape quiet.
- **Watch (my finding this run):** the **open hour (13Z / 09:30–10:30 ET) is the historical P&L sink**
  (−$407 all-time). Not a watchlist action, but pre-market should avoid adding hyper-volatile open-gappers that
  feed low-quality first-hour crosses.

---

## 2026-07-27 — Daily Review

### Stats
- **8 trades, 1W / 7L → 12.5% win rate.** Net DB realized **−$78.20** (avg −$9.78). Only winner **NFLX
  +$3.62**; avg loss **−$11.69**, **profit factor 0.04**. Account **equity $8,849.01** (cash, **0 open
  positions** at broker — flat), vs last_equity **$8,927.21** → mark-to-market day **−$78.20**.
- **📖 Books EXACT.** Broker equity delta (−$78.20) matches DB realized net **to the cent**; broker holds
  **0 positions**, DB has 0 open rows. No phantom, no naked carry, no reconciliation gap. Clean & flat.
- **🎯 IMP-018's trailing stop had its first real multi-trade live session — and it works.** journald shows
  the trail **ratcheting continuously** all session (AAPL 329.27→335.11, NFLX 69.13→70.09, GOOG/AMZN/MSFT
  likewise) — a total behavioural change from the pre-IMP-018 world (2 trail exits in 219 all-time). It
  **locked NFLX +$3.62** (trailing-stop exit above entry) and **compressed AAPL to −0.31%** (−$7.21 vs the
  −2% stop's ~−$47). This is exactly the payoff-ratio fix IMP-018 promised, now visible live.
- Confidence vs outcome (all-time, robust n): **70-79 the only profitable band** (+$34.39, 71 tr, 49%);
  60-69 −$72.70 (130 tr, 42%), 80-89 −$67.09 (23 tr, 43%), 90-100 −$144.42 (3 tr, 0%). SE's conf-80.49
  loss today re-confirms the **inverted high-confidence** pattern.

### Trade-by-trade review (Model A throughout)
Risk-ON **gap-up open that faded** (Iran de-escalation → oil −7%, Nasdaq futures +1.6%). Six longs opened in
the first ~26 min after the 10:00 ET blackout lifted, into names that had already gapped — then drifted lower.
- **AAPL** 14:01 @ $336.17, conf 72.97 (xo 0.30, trend 0.95, **vol 0.68**) → broker-side stop @ $335.14
  **−$7.21** (−0.31%). Trail ratcheted 329.27→335.11; **loss contained to a third of a stop** — IMP-018 at work.
- **JPM** 14:04 @ $358.16, conf 65.96 (xo 0.22, **vol 0.29**) → stop @ $353.51 **−$23.25** (−1.30%). Biggest
  loss; faded straight down, trail never engaged above entry.
- **GOOG** 14:05 @ $328.26, conf 63.64 (**vol 0.077**) → stop @ $325.63 **−$13.17** (−0.80%), stopped 31 min in.
- **AMZN** 14:13 @ $234.87, conf 61.54 (**vol 0.33**) → stop @ $231.92 **−$17.69** (−1.26%).
- **MSFT** 14:14 @ $391.98, conf 65.36 (**vol 0.28**) → EOD flatten @ $389.99 **−$5.97** (−0.51%).
- **NFLX** 14:26 @ $70.55, conf 71.97 (**vol 0.87** — highest) → **trailing-stop lock @ $70.71 +$3.62**
  (+0.22%). The lone winner; strongest volume sub-score of the book.
- **SE** 15:14 @ $105.09, **conf 80.49 (highest of the day, xo 0.35, all sub-scores maxed)** → EOD flatten
  @ $104.35 **−$13.32** (−0.70%). Highest conviction, still red — inverted-confidence signature again.
- **BABA** 15:21 @ $114.64, conf 64.46 (**vol 0.0**) → EOD flatten @ $114.53 **−$1.21** (−0.10%). Near-scratch.
- **Root cause (all):** **market regime, not signal failure.** A gap-up-fade tape gave the long-only ribbon no
  follow-through; every entry triggered on a clean gate+cross but the tape reversed. Losses were **tightly
  contained** (worst −1.30%, well inside the −2% stop; no runaway, no naked). Note the volume-sub-score gradient:
  the winner + smallest loss had the two highest volume scores (0.87, 0.68); the biggest %-losers had the lowest
  (GOOG 0.077, MSFT 0.28, JPM 0.29) — a signal to *watch*, not yet act on.

### What worked / what didn't
- **Worked:** IMP-018 trailing stop **proven live** (ratcheting all session, NFLX locked, AAPL compressed);
  exit infra flawless (wall-clock EOD flatten 19:45 UTC filled all in RTH, books exact, broker flat, no naked
  carry, no NAKED page); risk control absolute (worst −1.30%, no breach). Service `active`, **NRestarts=0**.
- **Didn't:** the long-only ribbon has **no edge on a gap-up-fade tape** — 1/8. Same known structural condition
  (5m gate opens multiple longs on a move that fades). Today's −0.88% MTM bleed was **too shallow to trip the
  IMP-016 stand-down** (−2% floor) — correct-by-design, not a miss; this was a slow bleed, not a −2% crash.

### Lessons & improvement candidates — **NO CHANGE WARRANTED this run**
1. **Entry-threshold raise (60→65/70): TESTED and REJECTED.** The all-time confidence view (60-69 = 130-tr
   −$72.70 loser; 70-79 the only green band) *suggested* raising the floor, so I validated it on the replay
   harness (30d, 21 symbols) before touching anything. Result **fails the both-halves bar**: T=70 is **worse**
   than 60 in the full window (−$50.68 vs −$12.22); T=65 wins the combined window (+$19.93) but **only via
   symbol-set B (+$49); it LOSES set A (−$12.38 vs −$3.74)**. That is a sample noise-peak, not a robust plateau —
   shipping it would violate the same discipline that chose IMP-017's 10:00 and IMP-018's 1.25%. **Not shipped.**
2. **IMP-018 needs its observation window.** Today is its *first* real live session; the trail is firing and
   compressing losses as designed but PF/payoff need ≥2 weeks. Piling an exit change on top now would confound
   its evaluation. Hold.
3. **(watch, do not act)** Volume sub-score gradient (winner/small-loss high vol; big losers low vol) — one
   gap-up-fade day; the volume floor was *refuted* in the last weekly review. Accumulate more clean days.
4. **(watch)** Inverted high-confidence (SE conf 80.49 red; 80-100 net −$211/26 tr all-time) — the real
   structural leak, but the ≥80 cohort's proving is bottlenecked on market conditions (IMP-013 @ 85 barely
   binds); needs deliberate, multi-day work, not a reactive one-day change.
- **Verdict:** every lever is either replay-refuted (threshold), under active observation (IMP-018), refuted
  (volume floor), or evidence-gated (≥80 de-rate, crossover). A disciplined **"reviewed, no change"** day.

### Notes for pre-market research
- **Book CLEAN & FLAT into Tue 07-28** — 0 broker positions, equity **$8,849.01** all cash, nothing locked.
- **⚠️ EARNINGS PARKS THIS WEEK (unchanged from the 07-27 pre-market flags):** **Wed 07-29 AM → PARK MSFT**
  (reports AH); **Thu 07-30 AM → PARK AAPL + AMZN** (report AH). Also **Fed decision Wed 07-29**, **Core PCE
  Thu 07-30**. **Tue 07-28: no watchlist name reports** → no park needed tomorrow.
- **Gap-up-fade regime watch:** today the bot bought 6 longs right after the 10:00 blackout into a risk-on
  gap-up that then faded (7/8 red). If futures gap up again, expect the same low-quality first-hour crosses —
  not a watchlist action, but the regime to watch. No symbol "never signaled"; all 8 filled cleanly.
- **No quality parks.** Every red was the tape, not the name — JPM/GOOG/AMZN/MSFT/SE/BABA all mega-liquid and
  behaved; SE's highest-confidence loss is the inverted-confidence pattern (code-side watch), not a symbol issue.
- **NFLX behaved** — strongest volume sub-score, the only winner, trail locked it green. Keep.

---

## 2026-07-28 — Daily Review

### Stats
- **0 closed trades. Net P&L $0.00. Win rate n/a.** Account **equity $8,848.98** (broker source of truth,
  `last_equity` == `equity` → no overnight marks), **0 open positions**, all cash. Equity is **unchanged**
  from the pre-market read ($8,848.98) and essentially flat vs 07-27 EOD ($8,849.01).
- **Reconciliation clean:** DB (persistence was off all day — see root cause) recorded 0 trades; broker
  holds 0 positions; no phantom rows, no naked carry, no qty drift. Nothing to reconcile.

### Trade-by-trade review (no trades → root-cause the zero)
**The bot did not trade because it ran all day on the wrong 3-symbol watchlist, with persistence off.**
- **06:04:21 UTC — cold restart** (nightly/maintenance; `NRestarts=0` since, so no crash-loop). At startup
  `open_store()` opened the SQL Server connection and it **timed out**:
  `pyodbc.OperationalError HYT00 [ODBC Driver 18] Login timeout expired (SQLDriverConnect)`.
- Because that single init connect raised, `open_store()` returned **`None`** → **persistence disabled** AND,
  since `store is None`, `bot.main` never called `load_watchlist()` and **fell back to the `WATCHLIST` env
  default = `NFLX, BIRD, WPM`** (journal 06:04:43: *"Watchlist (WATCHLIST env): NFLX, BIRD, WPM"*; 06:04:44
  *"subscribing to NFLX, BIRD, WPM"*, *"warmup primed 3/3"*).
- So the bot spent the whole session subscribed to **3 symbols — 2 of which are PARKED** (BIRD micro-cap, WPM
  low-vol downtrend) — instead of the **21 enabled** watchlist names. NFLX chopped in a 15-cent band all
  afternoon (72.34–72.53); BIRD/WPM are illiquid. No fresh bullish 1m cross gated by a rising 5m ribbon ever
  fired on that stub → **0 signals, 0 entries** is *correct behaviour for the universe it was given* — but the
  universe was wrong.
- **The DB outage was transient:** by report/preflight time the same connection succeeds in **0.10s** and the
  live `dbo.watchlist` has **21 enabled** rows. A cold SQL Server / network blip at 06:04, nothing more.
- **P&L impact today: $0** (flat, semi-led risk-off tape — see below — would have produced few longs anyway).
  **Latent risk: high** — on an active day this same failure silently trades a 3-name stub and logs nothing.

### Market regime (context, not cause)
- **S&P +0.2% (7,428.78), Nasdaq −0.2% (24,876.91) — mixed/choppy, semi-led risk-off** (Perplexity sonar),
  exactly the gap-down chip rout the pre-market flagged (SK Hynix −14.6%/Samsung −13% → MU/AMD/NVDA/INTC soft).
  The long-only 5m gate self-protects on this tape, so even the full 21-symbol list would have traded lightly.
  This is **regime, not the cause of the zero** — the cause is the stub watchlist.

### What worked / what didn't
- **Worked:** the graceful-degradation design did what it was built to do — a DB outage did **not** crash the
  bot or block trading (it stayed up all day, `NRestarts=0`); the broker bracket safety net was never needed;
  book stayed flat and honest. Warmup, feed, and the EOD watchdog all ran clean.
- **Didn't:** the fallback is **too silent and too brittle**. (1) A *single* transient login timeout — with no
  retry — was enough to disable persistence and collapse the watchlist to a 3-name stub for the entire session.
  (2) There was **no alert**: nothing paged that the bot was running a 3-symbol env-default list instead of 21
  DB names. The only trace was one ERROR line in journald that no human sees post-close.

### Lessons & improvement candidates (ranked)
1. **[SHIPPED — IMP-019] Retry the startup DB init before giving up.** Root cause of today's zero. A transient
   cold-start login timeout must not disable persistence + collapse the watchlist for a whole session. Bounded
   retry with backoff (3 attempts, 5s apart) rides out the blip; still degrades gracefully if the DB is truly
   down. Safe: side-channel only, no trading-path/risk change.
2. **(Backlog) Alert on watchlist fallback / persistence-off.** Even with the retry, if the DB is genuinely
   down the bot silently trades the `NFLX, BIRD, WPM` env stub. A one-time Telegram page ("running WATCHLIST
   env default, N=3 — DB unreachable") would make the degradation visible. Deferred — one change per run.
3. **(Backlog / ops) The `WATCHLIST` env default is a poor safety net** — 2 of its 3 names are parked. Consider
   seeding it with the core liquid engine (e.g. SPY/QQQ/AAPL/MSFT/NVDA) so a fallback day still trades a sane
   universe. Config/ops change, not today.

### Notes for pre-market research
- **Book CLEAN & FLAT into Wed 07-29** — broker-confirmed **0 positions**, equity **$8,848.98** all cash,
  `last_equity` == `equity` (no marks). Nothing locked.
- **⚠️ EARNINGS PARKS (unchanged flags):** **Wed 07-29 AM → PARK MSFT** (reports AH) + **Fed decision Wed**;
  **Thu 07-30 AM → PARK AAPL + AMZN** (report AH) + **Core PCE Thu**.
- **IMP-019 shipped + service RESTARTED post-close today** — so the bot is now on the **live 21-symbol
  `dbo.watchlist`** again (verify at your run: journal should say *"Watchlist (dbo.watchlist)"* and warmup
  *"21/21"*, NOT the 3-symbol env stub). If you see the 3-symbol stub, the DB was unreachable at that restart —
  IMP-019 will have retried 3×; check journald for the retry warnings.
- **No trades today = infrastructure, not signals or symbols.** No watchlist action indicated by today's
  session — every enabled name was simply never subscribed. Keep the 21-name list; the semi cohort gapping
  down is regime, not symbol quality (pre-market call holds).

---

## 2026-07-30 — Daily Review

### Stats
- Closed trades (DB): **6** — 2W / 4L → **33% win rate**. Net realized P&L **+$37.37** (avg +$6.23/trade).
  Avg win **+$37.10**, avg loss **−$9.21**, **profit factor ≈ 4.03** (two strong semis winners dwarf four
  small chop losses). A **green day.** Account **equity $8,889.22** (all cash, **0 open positions** at the
  broker after all six exited broker-side).
- **Broker reconciliation: EXACT.** Alpaca equity **$8,889.22** vs `last_equity` **$8,851.85** = **+$37.37**,
  matching the DB net to the cent — because every exit was a real broker-side bracket fill (no reversal-candle
  estimation today), so DB P&L == capital truth. 0 positions, nothing carried overnight, no missed fill, no
  qty drift. Book clean & flat.
- Warmup primed 18/18 on the 11:34 UTC restart; ran on the live 18-symbol `dbo.watchlist` (IMP-019 held — no
  env-stub fallback). One benign IEX websocket reconnect at 16:53 UTC (post-flatten, no trades affected).

### Trade-by-trade review
All six entered in a tight **14:13–14:26 UTC (10:13–10:26 ET) cluster** — the first ~25 min after the IMP-017
10:00 ET opening-range blackout lifted — and all exited **broker-side** (stop/trail/target). Model A throughout.
- **MU** (14:14 @ $833.97, conf 71.75, **crossover 0.771**) → $854.11 **+$40.29 (+2.42%)**. Best trade. Wide,
  accelerating cross on the semis-momentum leg; rode it to the trail/target. Strong-cross → clean win.
- **INTC** (14:13 @ $91.68, conf 80.45, **crossover 1.00**) → $92.85 **+$33.90 (+1.28%)**. Second winner; the
  strongest cross of the day. Both winners are the day's two **highest crossover sub-scores** — the exact
  crossover-strength signal IMP-011's floor is built on.
- **AVGO** (14:17 @ $386.19, conf 74.58, crossover 0.569) → $382.64 **−$17.73 (−0.92%)**. Worst loser. Cross
  cleared the 0.20 floor comfortably but the rebound tape faded it back through the stop. Mid-band chop.
- **MSFT** (14:26 @ $449.48, conf **81.95**, crossover 0.471) → $446.06 **−$10.26 (−0.76%)**. High-conf
  (top band) yet lost — consistent with the standing "confidence inverted above ~80" finding; the strong
  trend/rsi/vol carried a mediocre cross over the line.
- **TSLA** (14:22 @ $306.72, conf 69.40, **crossover 0.206**) → $305.11 **−$8.07 (−0.53%)**. The one trade in
  the **0.20–0.25 crossover band** — barely above the current floor — and it lost. This is the IMP-020 cohort
  (see below).
- **TSM** (14:18 @ $401.49, conf 68.13, crossover 0.461) → $401.30 **−$0.76 (−0.05%)**. Near-scratch chop.
- **Safety worked:** after AVGO/TSM/TSLA exited losing in sequence, the **3-consecutive-loss stand-down tripped
  at 14:55 UTC** and correctly halted all NEW entries for the rest of the session (MSFT, already open, was
  still managed to its broker exit). No churn after the cluster; the guard behaved exactly as designed.

### What worked / what didn't
- **Worked:** (1) The two strong-cross semis entries (MU 0.771, INTC 1.00) made the day — crossover strength
  again separated winners from losers cleanly at the top. (2) Broker-side exits + reconciliation are exact;
  no naked carry. (3) The stand-down guard fired precisely and prevented a losing-cluster spiral. (4) Losses
  were tightly contained (worst −$17.73) — the 1.25% trail (IMP-018) is compressing the loss side as intended.
- **Didn't:** (1) The **entry cluster** — six entries fired in a 13-min burst the moment the blackout lifted;
  four were mediocre-cross setups into a **choppy Fed-hold-rebound tape** and chopped out. (2) **The 0.20–0.25
  crossover band admitted TSLA and it lost** — this is the day's cleanest, most actionable leak (see below).
  (3) The top confidence band (MSFT 81.95) lost again — the inverted-conf-above-80 issue is still open but has
  no clean single-change fix yet.

### Lessons & improvement candidates
1. **(SHIPPED — IMP-020)** Raise the `MIN_CROSSOVER` floor **0.20 → 0.25.** Post-IMP-011 attribution (145
   trades since 06-27) shows the **0.20–0.25 crossover band is the single worst cohort: 40 trades, −$165.93,
   avg −$4.15, 40% win** — sitting immediately above the current floor. Everything below 0.30 is net-negative;
   the 0.30–0.40 band is the first to turn positive. 30-day 18-symbol replay confirms: net **−$287.84 →
   −$119.39 (+$168)**, PF **0.70 → 0.84**, avg/trade **−$2.74 → −$1.59**, trades 105 → 75 (no collapse), win%
   ~flat. Today's TSLA (crossover 0.206, −$8.07) is the confirming same-day instance. Capital-protective,
   same proven family as IMP-011 — never widens risk, just removes the worst-quality entries.
2. *(watch, still open)* **Confidence inverted above ~80:** 80-89 band all-time −$43 (25 tr, 44%), 90-100
   0% win −$144 (3 tr); MSFT 81.95 lost again today. IMP-013 caps *sizing* at 85 but doesn't block entries.
   No clean single-change lever yet — needs its own dedicated analysis; do not fold into IMP-020.
3. *(watch)* **Opening-cluster bunching** — the first 25 min after the 10:00 blackout produced all 6 entries
   and 4 of them were chop. Consider whether a brief post-blackout throttle or a slightly later ENTRY_START
   helps, but that overlaps IMP-017's already-tuned window; needs more days before touching.

### Notes for pre-market research
- **Book CLEAN & FLAT into Fri 07-31** — broker-confirmed **0 positions**, equity **$8,889.22** all cash,
  `last_equity` marks reconciled. Nothing locked; nothing to protect on the watchlist.
- **AAPL + AMZN reported AH Thu 07-30** (parked pre-market today) — **re-enable decision for tomorrow** once
  their prints + reactions clear, per the standing earnings-rotation rule. MSFT (re-enabled today, conf 81.95)
  traded and lost small on a mediocre cross — regime, not a symbol problem; keep.
- **Semis led the winners again** (MU +$40, INTC +$34) on strong accelerating crosses — the semi cohort
  (INTC/MU/AVGO/TSM/NVDA/AMD) is producing the day's best *and* worst; that's crossover-quality dispersion,
  not symbol quality. Keep the cohort; IMP-020 will thin the weak-cross tail.
- **Choppy Fed-hold rebound tape** (Wed's −1.5% S&P rout → Thu bounce) — the four losers were mid-band crosses
  faded by the chop, not catalyst-driven breaks. No symbol flagged for a park on today's evidence.
- No symbol "never signaled" concern — the 18-name list produced 6 clean triggers in the first half hour.

---

## 2026-07-31 — Daily Review

### Stats
- Closed trades (DB): **4** — 3W / 1L → **75% win rate**. Net realized P&L **+$60.86** (avg +$15.21/trade).
  Avg win **+$24.12**, avg loss **−$11.49**, **profit factor ≈ 6.30**. Best day of the week and the second
  green day running. Account **equity $8,950.06** (all cash, **0 open positions**).
- **Broker reconciliation: EXACT.** Alpaca equity **$8,950.06** vs `last_equity` **$8,889.20** = **+$60.86**,
  matching the DB net to the cent. 0 positions at the broker, DB also flat — nothing carried overnight, no
  missed fill, no qty drift. Book clean.
- Service **active** all session. Two benign `database init attempt 1-2/3 failed — retrying` warnings at
  06:10 UTC on the nightly restart, recovered on attempt 3 — **IMP-019 working exactly as designed** (second
  confirmed live save). Watchlist loaded 20 symbols, no env-stub fallback. No errors during RTH.
- **Market context (Perplexity):** strong **risk-on trending rebound** — S&P **+1.7%**, Nasdaq **+2.8%**,
  tech leading a broad recovery off the midweek Fed-driven selloff. No single-name catalyst identified for
  BABA / AMD / GOOG / AVGO. **Today's result is substantially regime, not demonstrated edge** — a long-only
  momentum bot should win on a +2.8% Nasdaq day, and that is most of what happened.

### Trade-by-trade review
All four Model A, all entered after the 10:00 ET blackout (IMP-017), spread across the session rather than
in a burst (unlike 07-30's 13-min cluster). **Three of four exited on the EOD flatten; only the loser
exited broker-side.**
- **BABA** (14:12 @ $120.65, conf **79.44**, crossover 0.396) → $121.77 **+$23.52 (+0.93%)**, EOD flatten,
  held 333 min. Solid mid-band cross, rode the risk-on tape all day. Clean win.
- **GOOG** (15:51 @ $350.23, conf 71.95, crossover **0.2701**) → $357.75 **+$45.11 (+2.15%)**, EOD flatten,
  held 234 min. **Best trade of the day and of the week.** Note the crossover — 0.2701 is *just* above the
  new IMP-020 floor of 0.25. Under the old 0.20 floor this trade also enters, so IMP-020 neither created nor
  cost this winner; it is the *nearest miss* to the new floor and a caution against raising it further.
- **AVGO** (16:52 @ $388.26, conf 70.44, crossover 0.324) → $389.19 **+$3.72 (+0.24%)**, EOD flatten,
  held 173 min. Near-scratch win; entered late into a move that had mostly already run.
- **AMD** (15:06 @ $492.21, conf 61.63, crossover 0.289) → $488.38 **−$11.49 (−0.78%)**, exited broker-side
  after **16 minutes** — the day's only loss. **Root cause: exit logic, not signal or regime.** The stop sat
  2% away at $483.25; the trade exited at −0.78%, i.e. it was cut by the **1.25% trail (IMP-018) ratcheting
  down onto a position that had barely moved**, not by the designed stop. Weakest confidence and lowest
  volume sub-score (conf_volume **0.00**) of the four — a thin-participation cross into a strong tape.

### What worked / what didn't
- **Worked:** (1) The tape — a +2.8% Nasdaq is the regime this strategy is built for, and it delivered.
  (2) **Letting winners run to the EOD flatten produced the entire day's P&L** (+$72.35 across three names);
  GOOG's +2.15% over ~4h is exactly the payoff profile IMP-018 was trying to unlock. (3) IMP-020's floor
  bound correctly a second session — minimum crossover taken was 0.2701, nothing from the old 0.20–0.25
  dead band entered, and the day still produced 4 entries (**no over-filtering**). (4) IMP-019's DB retry.
- **Didn't:** (1) AMD was cut in 16 minutes by the trail before it had earned anything. (2) AVGO's entry at
  16:52 (12:52 ET) captured +0.24% — late entries into an already-extended move are near-scratch at best.
  (3) n=4. **Nothing about today validates the strategy** — three EOD-flatten winners on a broad rally day is
  the market paying, not the signal working.

### Lessons & improvement candidates
1. **[TESTED AND REFUTED TONIGHT — do not retry]** *"The trail pre-empts the designed stop."* The ratchet
   (`RiskManager.update_trailing_stop`) starts from the bracket's original stop and moves to
   `close × (1 − trail_percent)` on the **first managed candle**, so with trail 1.25% < stop 2% every
   position has its stop silently tightened from −2% to −1.25% the moment it opens, before earning a cent.
   The live evidence looked damning: since IMP-018, **11 of 11 losing broker-side exits landed inside
   −1.31%** (AAPL −0.31%, TSM −0.05%, BABA −0.18%, AMD −0.78% today…), **none near the designed −2%**, and
   the EOD-flatten bucket was **+$63.12 / 7 trades** vs the stop-leg bucket **−$40.19 / 15**. I implemented
   the principled fix (gate the ratchet on breakeven: the trail may only move the stop to a price ≥ entry,
   leaving the designed stop to govern below that — zero free parameters) and **A/B'd it on the 30-day
   20-symbol replay. It is WORSE:**

   | | trail from entry (live) | breakeven-gated |
   |---|---|---|
   | net | **−$131.06** | −$264.58 |
   | win % | 36.9 | **48.8** |
   | profit factor | **0.84** | 0.74 |
   | stop-leg exits | 52 tr, −$499.66 | 27 tr, −$406.11 |

   **The finding that matters: this bot's losers do not recover.** Win rate *rises* 12 points when you stop
   cutting them early (those trades do end green), but the ones that keep going down go a full 2% instead of
   1.25%, and that costs more than the rescued winners earn. The "wrong" mechanism is doing the right job —
   IMP-018's tight trail is functioning as a **tight stop**, and that is why it worked. Reverted, not shipped.
2. **Consequence for the open "flat non-ATR stop" item (todo.md):** re-frame it. The evidence now says the
   effective ~1.25% stop **beats** the designed 2%, so the next stop experiment is *tighter/adaptive*, never
   wider. IMP-018 already swept trail 0.9–2.0% and found a broad plateau, so this is not urgent.
3. **Replay-vs-live drift worth a look (not tonight):** IMP-018's 30-day replay at trail 1.25% scored
   **+$194**; the same command over 07-01→07-31 scores **−$131**. Different window (+6 days) and a changed
   watchlist (SE/QCOM/COST disabled since). Confirm the harness is stable before trusting it for the next
   sizing/stop decision. Also note `bot.replay`'s default `--symbols` resolved to only **3** symbols in a
   bare CLI process (config watchlist fallback, not the DB's 20) — **always pass `--symbols` explicitly**.
4. **Still open, unchanged:** confidence inverted above ~80 (all-time 80+ = 28 tr, **−$187.87**, 39% win, vs
   70-79 = 78 tr, **+$134.97**, 51% win). `SIZE_CONFIDENCE_CAP=85` (IMP-013) already trims size on the worst
   band; the residual is an *entry* question with no clean single-change fix yet. Sub-score forensics on the
   80+ cohort show it is distinguished by **high crossover (0.68 vs 0.40 for the 70-79 band)** — consistent
   with IMP-020's note that crossover is non-monotonic and the 0.40–1.0 bands are also negative. **A crossover
   *ceiling* is the leading candidate**, but must not ship until IMP-020's floor has its full week.

### Notes for pre-market research
- **GOOG — trade of the week (+2.15%, +$45.11).** Trended cleanly all session on the risk-on tape. Keep.
- **BABA** — second clean patient winner in a row (+0.93% today). Keep.
- **AMD** — entered on the day's weakest signal (conf 61.6, **conf_volume 0.00**) and was cut in 16 min.
  Not a park candidate on one trade, but watch whether AMD keeps triggering on thin participation.
- **AVGO** — two sessions running of late, near-scratch-or-losing entries (+0.24% today after −0.92% on
  07-30). Entries are arriving *after* the move. Watch; not yet a park.
- Watchlist is **20 enabled** (SE, QCOM, COST, XOM, ENPH, WPM, BIRD disabled). 4 triggers from 20 names on a
  strongly trending day is on the thin side — worth watching whether IMP-020's floor is costing entries on
  quiet tapes. **If a normal session goes to zero trades, that is the signal the floor is too high.**
- Regime note for Monday: today was a sharp risk-on rebound (Nasdaq +2.8%). Expect mean-reversion /
  consolidation risk into Monday; late-session entries (AVGO 12:52 ET) are the most exposed to that.

---

## 2026-08-03 — Daily Review

### Stats
- Closed trades (DB): **3** — 2W / 1L → **67% win rate**. Net realized P&L **−$1.29** (avg −$0.43/trade).
  Avg win **+$8.60**, avg loss **−$18.49**, **payoff 0.47**, **profit factor 0.93**. A scratch day: the
  headline win rate is good and the money is flat, because the one loser was worth both winners combined.
  Account **equity $8,948.75** (all cash, **0 open positions**).
- **Broker reconciliation: EXACT.** Alpaca equity **$8,948.75** vs `last_equity` **$8,950.04** = **−$1.29**,
  matching the DB net to the cent. 0 positions at the broker, DB flat too — nothing carried overnight, no
  missed fill, no qty drift. Book clean.
- Service **active** all session, **zero errors, zero warnings, no restarts** in journald. All three exits
  reconciled cleanly (`reconcile_exit` → `EXIT` → `DB exit` → `WAITING`) with no 422 loops.
- ⚠️ **The pre-market routine did NOT run today.** `ustradebot-premarket` died `rc=1` eight seconds after
  starting at 11:30 UTC; `uswisbot-premarket` died identically at 11:45. Both were on `claude-opus-5`;
  `cryptoauto-daily` (sonnet-4-6) ran fine at 17:00. **Environmental/model-availability blip, not bot code
  and not routine config.** Consequence: **no `research-log.md` entry for 08-03 and no watchlist review** —
  today traded Friday's 20-name list, which was still current, so no harm done. Flagged, not fixed here
  (the routine scaffold lives in `/root/claude-routines`, outside this repo).
- **Market context (Perplexity):** **choppy risk-on, not a trend day.** Nasdaq finished **+1.0%** but had
  been **down 117.85 points intraday**, and **6 of 11 S&P sectors closed lower** despite the index gain.
  Driver was US-Iran de-escalation (oil and yields lower), not a tech-specific catalyst. No single-name
  catalyst for AMZN/AMD/MU — all three moved with the mega-cap/AI tape. **An index that round-trips a
  118-point intraday hole and closes green with most sectors red is precisely the tape that pays a
  long-only momentum bot on entry and then takes it back — which is exactly what the tape did.**

### Trade-by-trade review
All three Model A, all entered after the 10:00 ET blackout (IMP-017), **all three exited broker-side on the
IMP-018 trailing stop** — none reached the EOD flatten, and none came close to the 2% designed stop or the
10% target. Strikingly, **all three exits landed inside an 18-minute window (14:18–14:36 ET)**: this was one
market-wide afternoon pullback taking out three trails at once, not three independent signal failures.
- **AMZN** (11:24 ET @ $285.30, conf **66.57**, crossover **0.2552**, conf_volume **0.2610**) → $282.66
  **−$18.49 (−0.93%)**, 174 min. **The day's only loss, and the day's weakest entry.** Crossover 0.2552 is
  the *nearest miss* to IMP-020's 0.25 floor — it cleared by 0.005 — and participation was thin
  (conf_volume 0.26). It never worked: **MFE only +0.38%** against **MAE −0.93%**, i.e. the trade was
  essentially never in profit. Root cause: **signal quality**, not exit logic. Worth noting the exit logic
  did its job — the trail cut it at −0.93% instead of letting the designed −2% stop take $37.
- **AMD** (12:31 ET @ $482.50, conf **77.96**, crossover 0.2934, all other sub-scores ~1.00) → $484.68
  **+$10.91 (+0.45%)**, 125 min. **Cleanest signal of the day** — trend 0.96, rsi 1.00, volume 1.00,
  volatility 1.00. Ran to a high of **$490.85 (+1.69%)** and handed back a full trail width to bank +0.45%.
  Root cause of the shortfall: **exit logic** — the signal was right and the trade was right.
- **MU** (12:46 ET @ $822.54, conf **63.97**, crossover 0.3104, conf_volume **0.0709**) → $825.685
  **+$6.29 (+0.38%)**, 102 min. Same shape as AMD: peaked **+1.69%**, banked +0.38%. Won *despite*
  near-zero volume participation (conf_volume 0.07), which is luck rather than signal — flag, don't credit.
- **Entries rejected** (the gates worked, and were the reason the day was quiet): C rejected **4×** on
  crossover (0.06/0.10/0.10/0.07), SPY 2× (0.03/0.01), NVDA (0.10), TSLA (0.16), TSM (0.07); plus
  confidence-floor rejections TSM 58.3/58.5, SPY 59.3, AVGO 59.3, GOOG 57.6. **3 entries from 20 names is
  thin but not the zero-trade collapse that would condemn IMP-020's floor.**

### What worked / what didn't
- **Worked:** (1) **Execution and reconciliation were flawless** — clean startup, no errors, three
  broker-side exits reconciled first time, broker matches DB to the cent. (2) **The trail protected the
  loser** — AMZN exited −0.93% where the designed stop would have cost −2% (≈ −$37 instead of −$18.49);
  this is the IMP-018 mechanism doing the job the 07-31 refutation proved it does. (3) **IMP-020's floor
  bound a third session** and rejected 9 sub-floor crosses; the one entry nearest the floor (AMZN 0.2552)
  was the day's only loser, which is weak but directionally supportive evidence.
- **Didn't:** (1) **The trail gave back 73% of both winners.** AMD and MU each peaked at **+1.69%** and
  banked **+0.45% / +0.38%**. (2) The day's best *signal* (AMD, sub-scores ~1.0) produced +$10.91 while the
  day's worst *signal* (AMZN, barely over the floor) lost $18.49 — **the payoff asymmetry, not the hit
  rate, is what kept the day flat.** (3) n=3; nothing here validates or condemns the strategy on its own.

### Lessons & improvement candidates
1. **[SHIPPED TONIGHT — IMP-021]** **The flat trail width is arithmetically incapable of keeping a winner
   this strategy actually produces.** I pulled 1-min bars for every trade since IMP-018 (n=25, 07-25→08-03)
   and measured max-favourable-excursion capture:

   | MFE bucket | n | avg MFE | avg realized | **capture** | net |
   |---|---|---|---|---|---|
   | < 0.5% | 4 | 0.23% | −0.75% | — | −$50.71 |
   | 0.5–1.0% | 8 | 0.63% | −0.60% | −97% | −$77.01 |
   | **1.0–2.0%** | **9** | **1.42%** | **+0.28%** | **17%** | +$53.31 |
   | > 2.0% | 3 | 2.96% | +1.95% | 69% | +$119.30 |

   With trail = 1.25% and the modal winner peaking at 1.0–2.0%, max achievable capture is
   (MFE − 1.25%)/MFE — for the 1.42% average that is **12%**. The bot is not mis-executing; **the width is
   mis-specified relative to the size of the move it catches.** Seven trades since IMP-018 ran ≥1.0% and
   exited under +0.5%. Fix shipped as a **two-stage trail** — see IMP-021 below.
2. **[TESTED AND REJECTED TONIGHT — do not retry]** *"Just tighten `TRAIL_PERCENT`."* The 30-day replay is
   seductive: trail 0.6% scores **+$24.58 / PF 1.06** against 1.25%'s **−$153.28 / PF 0.80**, and the whole
   0.2–0.7% region is positive. **It does not survive the window test.** At 45 days 1.25% wins (+$82.29 vs
   +$49.95) and at 60 days it wins decisively (**+$154.31 vs +$51.42**). The tight-trail advantage is
   **an artifact of the 30-day window**, and it also explains the harness instability flagged on 07-31
   (IMP-018's +$194 vs the same window's −$131). **Corrects the record: `config.py` claims trail is a
   "broad plateau 0.9–2.0%" — on current data it is not, it is a steep monotonic gradient on 30 days and
   the opposite ranking on 60. Treat any single-window replay number as noise; require ≥3 windows.**
3. **Still open, unchanged:** confidence inverted above ~80 (all-time 80–89 = 25 tr −$43.45 44% win;
   90–100 = 3 tr −$144.42 0% win, vs 70–79 = 79 tr **+$145.88** 52% win). Deliberately NOT touched tonight:
   it is an *entry-filter* change and IMP-020 (crossover floor, shipped 07-30) has only **3 live sessions**;
   the weekly review explicitly deferred its verdict for a full week, and a second entry filter would
   confound it. Earliest candidate for next week once IMP-020 has its verdict.
4. **`conf_volume` is not doing useful work.** Today: AMZN lost with 0.26, MU won with **0.07**, AMD won with
   1.00. Two of three trades had near-dead volume sub-scores and the outcomes split. Not actionable on n=3 —
   logged for the sub-score forensics that the 80+ confidence analysis will need anyway.

### Notes for pre-market research
- ⚠️ **No 08-03 research-log entry exists** — the pre-market routine failed (rc=1, model blip, both bots).
  Today ran on **Friday's 20-name list unchanged**, which was fine. **Tomorrow's run starts from the 07-31
  research entry**, not from a 08-03 one. If the 11:30 UTC run fails again, that is now a pattern worth
  escalating rather than a one-off.
- **Book CLEAN & FLAT into 08-04** — broker-confirmed **0 positions**, equity **$8,948.75** all cash.
  Nothing locked, nothing to protect.
- **AMZN — watch.** Entered on crossover **0.2552**, the closest any trade has come to IMP-020's 0.25 floor,
  with thin volume (0.26), and was the day's only loser (MFE +0.38% — it never worked). Second consecutive
  session where the weakest-cross entry was the loser. Not a park on one trade; a data point for the floor.
- **AMD — best trade of the day and the cleanest signal** (trend 0.96 / rsi 1.00 / volume 1.00 / vol 1.00).
  Keep. Note it also peaked +1.69% — IMP-021 is aimed squarely at this trade.
- **MU — won on a near-zero volume sub-score (0.07).** Treat as luck, not signal quality. Watch.
- **C — signalled 4 times and was rejected 4 times** on crossover (0.06–0.10), never trading. SPY likewise
  (0.03/0.01). These two are burning gate cycles without ever producing a tradeable cross; if that persists
  another week they are the first candidates for a park on *dead-signal* grounds rather than P&L grounds.
- **TSM / GOOG / AVGO repeatedly rejected on the confidence floor** (57.6–59.3, i.e. just under 60) —
  consistently near-miss, never entering. Worth a look at whether these names sit structurally just below
  the threshold.
- Regime note for Tuesday: today was **choppy risk-on that round-tripped a 118-point Nasdaq hole**. Six of
  eleven sectors closed red on a green index — breadth is weak. Expect more give-back tapes; IMP-021 should
  bank more of the intraday runs if this persists.

---

## 2026-08-04 — Daily Review (backfilled 2026-08-05)

**The 08-04 post-close routine did not run** — no entry was written that evening and no
IMP was shipped. Backfilled here from the DB, broker and journal so the record is
continuous and IMP-021's first live session is not lost. Kept short: it is reconstruction,
not same-evening analysis.

### Stats
- Closed trades: **7 — 7W / 0L, 100% win rate.** Net **+$139.38** (avg +$19.91/trade,
  avg +0.88%). The best session in the book's recorded history and the **first live
  session under IMP-021** (two-stage trail; service restarted 11:35:29 UTC by the
  pre-market routine, so the code was live from the open).
- Trades: AVGO +$55.35 (+2.24%), INTC +$24.62 (+0.93%), INTC +$24.07 (+1.15%),
  NVDA +$16.72 (+0.99%), MU +$10.08 (+1.14%), MSFT +$4.50 (+0.45%), TSM +$4.04 (+0.24%).
- **5 of 7 exited on the EOD flatten, 2 on the trail — and both trail exits were WINNERS**
  (+0.93%, +1.14%). Against the all-time trail-exit record of 26% win, two trail exits
  banking ~+1% each is the IMP-021 mechanism doing precisely what it was designed to do.
- Tape: QQQ **+2.15% open→close** — the strongest trend day in the 38-session sample.

### Root cause
Not a strategy insight so much as a regime one: on the best trending tape of the sample the
long-only book went 7/7. That is the same fact IMP-022 is built on tonight, seen from the
happy end of the distribution.

### Notes carried
- **AMD was parked for its 08-04 after-close print and was never re-enabled** — the 08-05
  pre-market routine did not run either. AMD is still `enabled=0`. See tonight's entry.

---

## 2026-08-05 — Daily Review

### Stats
- Closed trades: **3** — 1W / 2L → **33% win rate**. Net realized **−$12.20**
  (avg −$4.07/trade). Avg win **+$16.53**, avg loss **−$14.37**, **payoff 1.15**,
  **profit factor 0.58**. Account **equity $9,075.88** (all cash, **0 open positions**).
- **Broker reconciliation: EXACT.** Alpaca equity **$9,075.88** vs `last_equity`
  **$9,088.08** = **−$12.20**, matching the DB net to the cent. All 6 fills (3 entries,
  3 exits) match the DB on price and qty; 0 positions at the broker, DB flat. Nothing
  carried overnight, no missed fill, no qty drift. Book clean.
- Service **active** all session, **NRestarts=0**, running since the 08-04 11:35:29 UTC
  restart — so today traded under IMP-021, as intended, with no deploy gap.
- ⚠️ **Two routines did not run.** There is **no 08-04 daily review** (backfilled above)
  and **no 08-05 research-log entry** — the 08-05 pre-market routine never executed. This
  is the *second* failure in three sessions (08-03 died rc=1 too). The 08-04 entry called
  08-03 "the one-off it was claimed to be"; **that call is now wrong — this is a pattern
  and it should be escalated.** Concrete consequence: **AMD was parked on 08-04 for its
  after-close earnings and the 08-05 run was supposed to re-enable it. It did not. AMD is
  still `enabled=0` and has now missed a full session for a binary event that resolved
  yesterday.** The watchlist is 19 names, not the intended 20.
- ⚠️ **Alpaca API instability, ~17:55–17:57 UTC.** `entry_fill_price` for MU order
  `24fbc144` failed repeatedly — first `[Errno 111] Connection refused`, then two nginx
  `500`s. **Handled correctly**: the errors are logged and swallowed, the DB kept the
  submit-time price, and the position stayed managed and exited normally at 19:25. No
  trading impact; recorded because it is a broker-side outage, not a bot defect.

### Market context (Perplexity `sonar` + bar data)
- **S&P 500 closed 7,398.93 (+0.84%) and the Nasdaq Composite 26,247.08 (+1.71%), both
  record closes.** Perplexity found no single-name catalyst for MU or INTC.
- **This framing is misleading for an intraday bot and I nearly mis-read the day on it.**
  Those are *close-over-close* numbers and the gains were an overnight gap. **QQQ's
  intraday open→close was −1.27%** — the tape the bot actually traded opened at the highs
  and faded all day. Today was a **fade day, not a trend day.** Against the −$33.12
  average for down-tape sessions, **−$12.20 is a comfortably better-than-typical result
  for the regime**, not a disaster.
- AMD's Q2 print (after the 08-04 close) landed with upbeat guidance that **failed to
  impress**; the reaction was negative. The 08-04 park was the right call — and it makes
  AMD's failed re-enable a missed *recovery*, not a missed opportunity.

### Trade-by-trade review
All three Model A, all after the 10:00 ET blackout, **all three exited broker-side on the
IMP-021 trail** — none reached the EOD flatten, none came near the −2% stop or +10% target.
- **MU #1** (10:09 ET @ $918.31, qty 3, conf **80.67**, xo 0.834, trend 1.00, rsi 1.00,
  volume 0.369) → $912.197, **−$18.34 (−0.67%)**, 14 min. Stop ratcheted 899.85 → 906.06 →
  909.02 → 911.23 → **912.71**, filled at **912.1967** — i.e. **$0.51/share of slippage
  through the stop** (~$1.54 on the trade). Peak close ≈ $924.26 (**+0.65%**), so it never
  reached IMP-021's +1.0% trigger and rode the **wide** 1.25% width the whole way.
  **The day's biggest loser was also the day's highest-confidence signal** (80.67, the
  strongest crossover at 0.834). Root cause: **market regime** — MU could not hold a
  +0.65% pop while the tape faded; the signal itself was the cleanest of the three.
- **INTC** (11:54 ET @ $100.6829, qty 21, conf **66.83**, xo 0.596, volume 0.224) →
  $101.47, **+$16.53 (+0.78%)**, 84 min. **The one trade that proves IMP-021 fired live:**
  the final stop sat at **101.50**, which is self-consistent *only* with the narrow 1.0%
  width (101.50/0.99 = 102.53 peak, +1.83% — past the +1% trigger; the old 1.25% width
  would have placed it at 101.25). **IMP-021 added ≈ +$0.25/share ≈ +$5.25 on this trade
  versus the flat trail.** 17 stop replaces — high churn, exactly IMP-021's caveat ③, and
  **zero 422s**, so the id-rotation fix is holding.
- **MU #2** (12:40 ET @ $924.39, **qty 1**, conf **62.11**, xo 0.252, volume **0.000**) →
  $914.00, **−$10.39 (−1.12%)**, 165 min. Peak close ≈ $925.57 (**+0.13%**) — **it was
  never in profit.** Root cause: **signal quality + regime** — crossover 0.252 is a
  hair over IMP-020's 0.25 floor (the third session running where the weakest-cross entry
  of the day lost) and volume participation was **exactly zero**.
- **Rejections** (the gates worked): NVDA 3× on crossover (0.20 / 0.15 / 0.08), AVGO 4×
  (0.02 / 0.11 + confidence 52.0 / 50.6 / 57.9 / 61.6), INTC 59.8, TSM 49.5, AAPL 49.9.

### What worked / what didn't
- **Worked:** (1) **Execution and reconciliation flawless** — broker matches DB to the
  cent, three broker-side exits reconciled first time, zero 422s across ~25 stop replaces,
  and a real Alpaca outage absorbed without trading impact. (2) **IMP-021 is confirmed
  live and additive** on its one qualifying trade (+$5.25 on INTC). (3) Combined with
  08-04, **IMP-021's first two sessions are 10 trades, +$127.18, 8W/2L** — early, small-n,
  but the win rate has *risen* as the IMP-021 entry required it to.
- **Didn't:** (1) **Two of three entries were MU, and MU was the wrong horse** — it chopped
  914–926 all day while the tape faded. (2) **Confidence was inverted again**: the 80.67
  entry lost the most, the 66.83 entry was the only winner. (3) **qty=1 on MU #2** — a
  $924 position against $36k buying power. Whole-share flooring quantises a $900+ name so
  coarsely that the confidence→size mapping barely functions on it (logged below, not
  acted on).

### Lessons & improvement candidates
1. **[SHIPPED TONIGHT — IMP-022] The bot has no view on the tape, and the tape is nearly
   the whole P&L.** Bucketing all 38 live sessions (2026-06-08 → 08-05, 254 closed trades)
   by QQQ's intraday open→close move:

   | QQQ intraday | sessions | trades | win rate | net | per session |
   |---|---|---|---|---|---|
   | **up >0.5%** | 12 | 104 | **54.8%** | **+$755.65** | +$62.97 |
   | up 0–0.5% | 4 | 32 | 62.5% | −$49.70 | −$12.42 |
   | **down** | 22 | 118 | **33.1%** | **−$728.75** | −$33.12 |

   The book earns +$756 on up-tape and gives back −$729 on down-tape, netting ≈ −$23.
   **This is long beta, not alpha.** The 5-min gate asks only whether *the name* is
   trending; nothing in the system asks what the market is doing. Fixed by requiring the
   index proxy's own 5-min ribbon to be bullish before any long opens — see IMP-022.
2. **The "flat non-ATR stop" backlog item is much weaker than it looks — correcting the
   record.** It has been carried as an open defect since IMP-018 on the reasoning that a
   flat 1.25% trail is absurd across names ranging from SPY (1.17% daily ATR) to MU
   (10.73%). But the trail is compared against the *1-minute* ATR, and today's recorded
   `conf_volatility` inverts cleanly to it: **MU 1-min ATR ≈ $2.07 (0.224% of price),
   INTC ≈ $0.246 (0.244%)** — i.e. the trail width is **≈5.6× the 1-min ATR on MU and
   ≈5.1× on INTC**. It is already *near-normalised in ATR terms*, because
   `score_volatility` (ATR/price, `_ATR_GOOD` 0.20% → `_ATR_BAD` 1.00%) is itself an ATR
   filter that only admits names in a narrow 1-min-ATR band. **Daily ATR dispersion is not
   the dispersion this bot's stop actually faces.** Downgrade this item; do not spend a
   session on it before re-deriving the premise.
3. **A second dead mechanism: `STOP_LOSS` (2%) is unreachable and has been since IMP-018.**
   The trail seeds at the bracket stop and ratchets whenever `close × (1 − 0.0125)` clears
   it, which happens as soon as price trades above **−0.76%** from entry. In practice the
   trail is always the binding constraint and the −2% stop never fills. Today confirms it:
   all 3 exits were trail fills. **Tuning `STOP_LOSS` is therefore a no-op** — worth
   knowing before someone spends a day on it. (Not a defect: the trail is strictly tighter,
   so this is *more* protective, not less.)
4. **Confidence remains inverted, and today added to it** (80.67 lost $18.34; 66.83 was the
   only winner). All-time: 90–100 = 3 tr / 0% / −$144.42; 80–89 = 28 tr / 46% / −$13.10;
   **70–79 = 82 tr / 54% / +$221.99**; 60–69 = 141 tr / 42% / −$87.27. The 70–79 band is
   the only profitable one and the 60–69 band is the largest and negative. **Deliberately
   NOT touched tonight** — IMP-022 is itself an entry filter and will cut trade count by
   ~40%; stacking a second entry filter in the same evening would make both unmeasurable.
   This is the first candidate once IMP-022 has a week.
5. **Whole-share quantisation on high-priced names (new, logged not acted).** MU #2 sized
   to **qty 1 = $924** against $36k buying power. On a $900+ stock the floor-to-integer
   step is ~10% of a typical position, so Model A's confidence→size curve is effectively
   destroyed for MU/AVGO/TSM/MSFT/NFLX. Cannot be fixed by sizing alone (brackets require
   whole shares — a hard Alpaca constraint), so any fix is structural. Needs its own study.

### Notes for pre-market research
- 🚨 **RE-ENABLE AMD.** It was parked 08-04 for its after-close print, the 08-05 routine
  was supposed to re-enable it and **never ran**. The print is out (upbeat guidance, weak
  reaction) so the binary is resolved. The watchlist is currently **19 enabled, not 20**.
- 🚨 **Escalate the pre-market routine failures.** 08-03 died rc=1, 08-05 did not run at
  all, and the 08-04 post-close routine also did not run. **Three misses in three
  sessions is not a model blip** — the scaffold lives in `/root/claude-routines`, outside
  this repo, and needs an operator look.
- ⚠️ **NEW — `QQQ` is now load-bearing infrastructure, not just a tradeable symbol.**
  IMP-022 reads QQQ's 5-min ribbon as the market gate. **QQQ must stay `enabled=1` on
  `dbo.watchlist`.** If it is parked, the gate fails **open** (the bot trades exactly as
  it did before) and logs a `WARNING` — safe, but the filter is silently gone. The
  standing "C / SPY dead-signal park" review, whose window runs to ~08-10, **must not
  park QQQ**; SPY remains free to park.
- **Book CLEAN & FLAT into 08-06** — broker-confirmed 0 positions, equity **$9,075.88**
  all cash. Nothing locked.
- **MU — the day's whole loss, and a pattern worth watching.** Signalled twice, lost both
  (−$18.34, −$10.39), chopping 914–926 while the tape faded. But it is still the book's
  **second-best earner over 60 days (+$177.84 / 21 trades)** and was +$10.08 yesterday.
  **Not a park candidate** — it is a high-beta name having a bad day in a fading tape,
  which is exactly the cohort IMP-022 now filters. Watch whether the gate fixes it.
- **INTC — best name in the book** (+$191.26 / 20 trades over 60 days) and the only winner
  today. Keep.
- **NVDA and AVGO are the emerging dead-signal names, not C/SPY.** NVDA was rejected 3×
  today on crossover (0.20/0.15/0.08) and AVGO 4× — both repeatedly reach candidacy and
  never clear the floor. Worth watching alongside the existing C/SPY flag.
- **Note for the 08-06 pre-market: ABNB reports Thursday 08-06 after the close** — the
  08-04 entry flagged it for a park in Thursday's run. Still outstanding.
- Regime note: two consecutive sessions of violent regime alternation (QQQ **+2.15%** on
  08-04 → **−1.27%** on 08-05). Expect IMP-022 to cut trade count materially on days like
  today and to be roughly transparent on days like yesterday.

---

## 2026-08-06 — Daily Review

### Stats
- **Closed trades: 0.** Net P&L **$0.00**. Win rate n/a. Account **equity $9,075.74**,
  all cash, **0 open positions** — `equity == last_equity`, i.e. the account did not move
  a cent today.
- **Broker reconciliation: perfect and trivial.** Alpaca `GET /v2/orders?status=all&after=
  2026-08-06T00:00Z` → **[] (zero orders placed all day)**; `/v2/positions` → **[]**;
  `/v2/account` → ACTIVE, equity/cash **$9,075.74**, not blocked. DB `dbo.trades` → **0 rows**
  touching today. **Broker, DB and journal agree on nothing-happened** — no missed fill, no
  qty drift, no position the DB thinks is flat while the broker holds it.
- **Service healthy.** `active`, **NRestarts=0**, up since **11:36:32 UTC** (the pre-market
  routine's watchlist restart — expected, not a crash). Zero errors, zero exceptions, zero
  422s. Two benign `data websocket error … no close frame received` reconnects at 01:20 UTC,
  both self-healed inside 10s and hours before the open.
- **This was IMP-022's first live session, and it is the entire story of the day.**

### Trade-by-trade review
No trades to review, so the reviewable evidence is **what the bot decided not to do**.

**The market gate was open for 0 of 85 QQQ 5-min bars today — never, not once, all session.**
(Recomputed independently from IEX 5m bars through `RibbonEngine.gate`, not read off the log.)
QQQ's 21/34/55 ribbon was never stacked-and-rising, so every long was vetoed by construction.

**Four entries passed every other gate — scoring, crossover floor, 10:00 ET blackout — and
were turned away by IMP-022 alone.** These are the day's only real decisions:

| time (ET) | symbol | confidence | outcome |
|---|---|---|---|
| 10:17 | **MSFT** | **70.2** | vetoed — market gate closed |
| 10:34 | **TSM** | 63.6 | vetoed — market gate closed |
| 10:36 | **AVGO** | 60.8 | vetoed — market gate closed |
| 13:19 | **AMD** | 68.1 | vetoed — market gate closed |

Other rejections (the older gates, working normally): **10 on crossover** (MSFT×3, MU×2,
AMZN×2, AVGO, AMD, AAPL) and **11 on confidence** 49–59 (MSFT×3, TSM×2, AVGO×2, AMD×2, AAPL).
So the signal engine was **healthy and productive** — 25 candidates evaluated, 4 fully
qualified. Zero trades is **not** a dead watchlist or a stuck feed; it is one filter, firing.

**What those four would have done — priced, not guessed.** Replay over the same session with
the real engines, 19 enabled symbols, gate ON vs gate OFF:

| arm | trades | net | win% | PF |
|---|---|---|---|---|
| **gate ON (what shipped, what happened)** | **0** | **$0.00** | — | — |
| gate OFF (pre-IMP-022 behaviour) | 5 | **−$47.11** | 20.0% | 0.25 |

**IMP-022 saved ≈ $47 on its first live day** (−0.47% of equity), and the counterfactual book
was ugly in texture as well as sign: **4 of 5 exits were EOD flatten**, i.e. entries that
never went anywhere and bled into the close — the classic no-trend-tape signature.

**Market context corroborates the veto rather than contradicting it.** Perplexity `sonar`
post-close: **S&P 500 −0.17% to −0.2%** (≈7,723.55), **Nasdaq −0.8% to −0.83%** (≈26,363.44),
regime **risk-off / choppy**, Dow outperforming on **rotation out of mega-cap tech and AI**
on AI-spending and higher-yield concerns. No name-specific catalyst on MSFT / TSM / AVGO /
AMD / NVDA / INTC / MU — all four vetoed names were moving **as sector beta in a tech
selloff**, which is exactly the cohort IMP-022 was built to decline. **Root cause of the
zero-trade day: market regime, correctly identified and correctly acted on.**

### What worked / what didn't
- **Worked — IMP-022 did precisely what it was shipped to do, on day 1.** It vetoed 4 longs
  into a −0.8% Nasdaq and avoided ≈ −$47. Its own log entry flagged that on 08-05 it would
  have *lost* $6.14; the honest scoreboard after two sessions of evidence (one hypothetical,
  one live) is **−$6.14 then +$47.11**. Still n=1 live — this is a data point, not a verdict.
- **Worked — the "log the veto, then skip" design paid for itself immediately.** Because the
  decision is fully scored *before* the veto, tonight's review could name the four blocked
  entries, their confidences and their timestamps. Had the gate been applied earlier (cheaper),
  today would be an unanalysable blank. That design call is vindicated.
- **Worked — infrastructure.** Clean reconciliation, no errors, no 422s, watchlist restart
  landed cleanly with 19/19 symbols warmed.
- **Didn't — nothing traded, so there is zero new evidence on signal quality, exits, sizing
  or the confidence inversion.** Tonight buys no information about the open questions. That
  is the cost of a filter this strict, and it must be counted honestly: **a filter that never
  opens generates no edge, it only avoids losses.** Watch it.
- **Didn't — the 100% block rate is at the boundary of the tripwire I set myself.** IMP-022's
  caveat ② says if the gate blocks **>80% of entries for a week**, the QQQ proxy is too strict
  and SPY should be reconsidered. Today was **100%**. One risk-off day is exactly when 100% is
  *correct*, so this is **not** a trigger yet — but it is day 1 of 5, and I am on notice.

### Lessons & improvement candidates
1. **[SHIPPED TONIGHT — IMP-023] The backtest harness silently disagreed with the live
   watchlist, and it produced a false result in this very session.** `bot/main.py` sources the
   watchlist from `dbo.watchlist` (19 enabled). `bot/replay.py` fell back to the `WATCHLIST`
   env var — the **three-name bootstrap stub `NFLX,BIRD,WPM`, two of which are long since
   parked**. My first A/B tonight ran `--days 1` with no `--symbols` and reported
   `trades=3 net=+2.38` for a day the bot took **zero** trades, and gate-ON vs gate-OFF came
   back **byte-identical** — because QQQ was absent from the stub, so IMP-022 **failed open in
   both arms** and the filter looked like a no-op. Had I trusted that, tonight's conclusion
   would have been "IMP-022 does nothing, revert it" — the exact opposite of the truth. Fixed:
   replay now resolves its universe DB-first, exactly like the live service, and prints the
   source. **A backtest that quietly disagrees with the deployed watchlist is worse than no
   backtest, because it is trusted.** This is the instrument every remaining question on the
   backlog will be measured with, and it was miscalibrated.
2. **Do NOT ship an entry-side change until IMP-022 has its week.** Restating deliberately,
   because the standing #1 candidate (the **60–69 confidence leak**, 141 tr / 42% / −$87.27,
   and the inversion above 80) is entry-side and tempting. IMP-022 cut trade count from ~3/day
   to **0** today; stacking a second entry filter now would make **both** unmeasurable and is
   precisely the thrash the mandate forbids. The weekly's standing focus is *"protect the
   measurement."* **Earliest sensible date: after 5 live sessions (~2026-08-12).**
3. **The observation window needs trade-count texture, not just P&L.** Today's useful numbers
   (gate-open bar %, blocked-entry count and their confidences, the ON/OFF replay delta) were
   all produced by hand tonight. If IMP-022 survives its week, the next *non-behavioural*
   candidate is to have the daily report emit them automatically — cheap, zero risk, and it
   makes the weekly's verdict evidential instead of anecdotal. Ranked below #2 only because
   the window is 4 sessions from done.
4. **Ops gotcha, newly confirmed and worth recording: the bot's log timestamps are WIB
   (UTC+7), not UTC.** The VPS default TZ moved to Asia/Jakarta on 2026-08-02 and the service's
   log formatter follows system local time, while `dbo.trades`, `systemctl` and this review are
   all **UTC**. Tonight's veto lines read `21:17` / `00:19 (08-07)` and are really **14:17 UTC /
   17:19 UTC** = 10:17 / 13:19 ET. Cross-check: banner logged `18:36:34` vs
   `ActiveEnterTimestamp=11:36:32 UTC` — a clean +7h. **A future review that reads journal
   timestamps as UTC will place trades outside market hours and misdiagnose.** Not worth a code
   change (the service is correct; only the display TZ shifted), but it must be known.
5. **Still-open items, unchanged and deliberately untouched tonight** (no new evidence, since
   nothing traded): confidence inversion above 80; the 60–69 band leak; whole-share
   quantisation destroying the size curve on $900+ names (MU/AVGO/TSM/MSFT/NFLX); `STOP_LOSS`
   being structurally unreachable behind the trail (a no-op to tune — do not spend a day on it);
   and the downgraded "flat non-ATR stop" item (premise re-derived 08-05 and found much weaker
   than its reputation).

### Notes for pre-market research
- 🚨 **RE-ENABLE ABNB tomorrow (Fri 08-07).** It was parked today purely for tonight's
  after-close Q2 print, which has now happened. The binary is resolved — re-enable and let the
  long-only gate plus IMP-022 handle the reaction, same precedent as AMD/MSFT/AAPL/AMZN. The
  watchlist is currently **19 enabled**.
- ✅ **AMD's re-enable is already validated.** Re-enabled this morning after its 08-04 print, it
  produced a **fully qualifying entry (conf 68.1) on its very first session back**, plus 2
  confidence rejects and 1 crossover reject. The name is alive and generating signal — only the
  market gate stopped it. Keep.
- ⚠️ **QQQ is load-bearing twice over now — it must stay `enabled=1`.** It was already the
  IMP-022 market gate (parking it makes the gate fail **open** and silently vanish); as of
  IMP-023 it is **also** how the backtest harness gets a correct universe. The **C / SPY
  dead-signal review window still runs to ~08-10 and must not park QQQ.** SPY remains free.
- **Signal generation is healthy across the megacaps — today's blank is not a watchlist
  problem.** 25 candidates were scored: MSFT was the most active name by far (**3 crossover +
  3 confidence rejects + the day's best signal at conf 70.2**), then AVGO (3), AMD (3), TSM (2),
  MU (2), AMZN (2), AAPL (2). **No park candidates from today.** Do not read the zero-trade day
  as dead names.
- **Expect more zero-trade days and do not treat them as malfunctions.** IMP-022 blocks 100% of
  entries on a session like this one. A blank day with `market gate closed` lines in the journal
  is the filter working; a blank day *without* them would be a real problem worth escalating.
- **Book CLEAN & FLAT into 08-07** — broker-confirmed **0 positions**, equity **$9,075.74** all
  cash, zero orders outstanding. Nothing locked, nothing to reconcile.
- Regime: three sessions of violent alternation — QQQ **+2.15%** (08-04) → **−1.27%** (08-05) →
  **Nasdaq −0.8%** (08-06), on rotation out of mega-cap tech / AI-spending concerns. If that
  rotation persists, tomorrow is likely another low- or zero-trade day.

---

---

## 2026-08-07 — Daily Review

### Stats
- **No trades today.** Closed trades (DB): **0**. Orders at Alpaca: **0**. Open positions: **0**.
  Net realized P&L **$0.00**. Account **equity $9,075.74**, all cash (`last_equity == equity`,
  nothing carried, nothing marked). Second consecutive zero-trade session (08-06, 08-07).
- **Reconciliation: CLEAN.** `dbo.trades` has 0 rows for today; `/v2/orders?status=all&after=…`
  returns an empty list; `/v2/positions` is empty; equity is unchanged from the pre-market read.
  DB and broker agree exactly — no missed fill, no qty drift, no naked overnight position.
- **Service:** `active` all session, started 11:35:31 UTC, **NRestarts=0**, warmup primed **20/20**
  symbols, IEX stream subscribed to all 20. No errors, no reconnects, no exceptions in journald.
- Last live trade remains **08-05** (MU). The book has now been flat for three sessions.

### Trade-by-trade review
No trades to review. Root-causing the *absence* of trades instead, which is the reviewable
evidence tonight.

**The day's tape (Perplexity `sonar`, corroborated):** strongly **risk-on and trending** — S&P 500
**+0.6% to 7,757.64, a new all-time high**; Nasdaq Composite **+1.3% to 26,690.62**, outperforming
and led by tech and semiconductors. The July jobs report landed **pre-open at 08:30 ET** and was
taken well; futures were already firming into it. No company-specific catalyst on any of our names
— this was a broad, index-led melt-up on the chip complex. **This is the bullish-tape scenario the
weekly review explicitly asked to be tested against.**

**The signal funnel — 48 candidate signals, 0 entries:**

| stage | rejects | note |
|---|---|---|
| confidence < 60 | **23** | incl. near-misses 59.6 (AAPL), 59.5 (NFLX), 59.3 (ABNB), 58.8 (NFLX) |
| crossover < 0.25 | **21** | incl. near-misses 0.24 (AVGO), 0.24 (TSLA), 0.23 (NVDA), 0.22 (NVDA) |
| **market gate closed (IMP-022)** | **4** | NFLX 66.5, ABNB 74.1, ABNB 71.9, **MSFT 78.0** |

The gate is evaluated **after** full scoring (by design, so the journal prices what it turns away),
so those 4 were **fully qualifying entries** — and they were the four **highest-confidence** signals
of the entire session, including the day's best at conf 78.0.

**Gate-open timeline today** (reconstructed from QQQ 5m bars under live close-time semantics, and
validated: all four live blocks fall exactly inside reconstructed *closed* windows):
- full session 13:30–20:00 UTC: **gate open 52.6%** of minutes
- **entry window 14:00–19:45 UTC: gate open 46.4%** (160 of 345 minutes)
- blocks: `14:00-14:19 closed · 14:20-14:39 OPEN · 14:40-14:49 closed · 14:50-16:24 OPEN ·
  16:25-16:49 closed · 16:50-16:54 OPEN · 16:55-17:09 closed · 17:10-17:14 OPEN ·
  17:15-17:39 closed · 17:40-17:44 OPEN · 17:45-19:14 closed · 19:15-19:44 OPEN`

**The decisive finding: the gate was NOT the binding constraint today.** All 4 gate blocks landed in
the 14:13–14:48 closed window. For the **160 minutes the gate was open**, the entry signal produced
**zero qualifying candidates** — **21 of the 44 signal-threshold rejects fell inside open-gate
minutes** (23 fell in closed ones), every one of them failing on crossover or confidence, several by
a hair. The bot did not sit out because the regime filter forbade it; it sat out because **its own
entry signal never once qualified while the tape was green.**

**What the gate cost or saved (honest counterfactual, post-IMP-024 semantics):** replaying today with
the gate disabled takes **3 trades for −$27.96** (33% win, PF 0.23). With the gate on: **0 trades,
$0.00**. **The gate SAVED ≈$28 on a day the market closed at an all-time high.** The naive reading
of "bullish tape + zero trades ⇒ the QQQ proxy is too strict, switch to SPY" is **refuted by its own
counterfactual** — the entries it blocked were losers.

### What worked / what didn't
- **Worked — IMP-022 (market gate), again, and under the hardest test it has faced.** The weekly's
  tripwire was "if a genuinely bullish session still produces zero entries, the QQQ proxy *is* too
  strict." Today was that session, and the tripwire's premise does not survive contact with the data:
  the gate was **open 46.4% of the entry window** (not >80% blocked), and the trades it declined
  would have lost money. **Do not switch the filter symbol to SPY on the strength of a green index
  print.** The gate is behaving as designed on a choppy-underneath, index-led tape.
- **Worked — risk and plumbing.** Zero errors, zero restarts, clean 20/20 warmup, exact DB/broker
  reconciliation, no capital at risk. A flat day on a tape you have no edge in is a *correct* outcome,
  not a failure.
- **Didn't work — the entry signal, and this is now the whole story.** On the most favourable regime
  in weeks, with 160 minutes of open gate, the signal generated **not one** qualifying entry. 44 of
  48 rejects were the signal's own thresholds. The multi-timeframe ribbon is not finding the trend on
  a day the trend was the single most obvious feature of the market.
- **Didn't work — the measuring instrument, again (see IMP-024).** Tonight's first replay of today's
  session claimed **2 trades / −$41.60** for a day the live bot took **0**. That divergence was not
  noise: it was **lookahead bias**, and it has been silently inflating every backtest this harness has
  ever produced.

### Lessons & improvement candidates
1. **[SHIPPED — IMP-024] The replay harness was reading the future on every gate decision.**
   `run_replay` sequenced 5m gate bars at their **start**, so the bar spanning 14:45–14:50 was folded
   into the ribbon at 14:45 and every 1m trigger bar from 14:45–14:49 was judged against **five
   minutes of data that had not happened yet**. Live emits a candle only once a trade lands in a later
   bucket (`bot/candles.py`), i.e. at start+interval. Proven on today's session: replay's gate read
   `True` at 14:45–14:48 where live correctly read `False`, and replay's two "trades" (ABNB 14:45,
   MSFT 14:47) are **exactly the two entries live blocked** at 14:46/14:48. The two gates disagreed on
   **15.4% of today's session minutes**. This contaminated the per-symbol 5m gate as well as the
   IMP-022 market filter — i.e. the core of the multi-timeframe strategy. Fixed; details below.
2. **Ranked #1 for next week, unchanged and now urgent: the entry signal has no demonstrated edge.**
   Two filters (IMP-018 trail, IMP-022 regime gate) are carrying the entire system. Today removes the
   last comfortable explanation — this was not a bad tape, and the signal still produced nothing while
   the gate was open. The 60-69 confidence band (**141 tr, 41.8%, −$87.27**) and the inversion above 80
   (**−$13.10** at 80-89, **−$144.42** at 90-100) remain the largest structural leaks. **Hand to the
   weekly with a full week of IMP-022 data.**
3. **Near-miss clustering is worth a study, NOT a threshold tweak.** Four confidence rejects at
   58.8–59.6 and four crossover rejects at 0.22–0.24 sit just under their floors. The temptation is to
   loosen `ENTRY_THRESHOLD`/`MIN_CROSSOVER`; the weekly has explicitly forbidden exactly that, and it
   would be fitting a threshold to one day. The honest question is whether those near-misses would have
   *won* — answerable now that the harness is trustworthy, and only over a multi-week window.
4. **Every backtest figure recorded before tonight is overstated.** Re-derive before citing (see the
   IMP-024 entry for the corrected 60-day table).

### Notes for pre-market research
- **Book is CLEAN & FLAT into 08-10** — broker-confirmed 0 positions, 0 open orders, equity
  **$9,075.74** all cash, `last_equity == equity`. Nothing locked, nothing carried.
- **Do NOT park anything on the strength of two zero-trade days.** 08-06 and 08-07 both produced zero
  trades for *structural* reasons (regime gate + signal thresholds), not because names went dead. No
  park candidates from today.
- **Most productive signal generators today** (48 candidates in total, worth keeping healthy):
  **NFLX 9** and **BABA 9** — the two busiest names, though only NFLX produced a qualifying entry and
  all 9 of BABA's died on crossover/confidence; then **TSM 4**, **ABNB 4**, **UNH / SPY / NVDA /
  MSFT / AAPL 3 each** (MSFT's three include the day's best signal at conf 78.0), **INTC 2**, and
  **TSLA / QQQ / JPM / AVGO / AMZN 1 each**.
- **✅ ABNB's re-enable is already earning its slot.** On its **first session back** it produced
  **4 candidates including two fully-qualifying entries** (conf 74.1 and 71.9) — more than it managed
  in the three weeks before it was parked. The thin-liquidity concern stands, but the post-earnings
  volume expansion did exactly what the 08-07 research predicted. **Keep.**
- **Never signalled at all today (0 candidates): MU, AMD, GOOG, WMT, C.** **MU and AMD are the
  notable pair** — the two highest-ATR names on the board (9.48%, 8.25%) produced nothing on a
  chip-led rally day. Not a park signal yet; worth watching whether high ATR is actively *preventing*
  ribbon alignment rather than helping it.
- **SPY / C dead-signal window closes ~08-10.** SPY produced 3 candidates today (all confidence
  rejects, 50.4–54.8) so it is *evaluating*, just never qualifying — consistent with the structural
  low-ATR explanation, not a broken feed. **C produced nothing at all again.** Decide C at the 08-10
  review; note it has now gone 28+ days without a trade.
- **QQQ remains load-bearing twice over** (IMP-022 market gate + IMP-023 replay universe). Verify
  `enabled=1` before and after any watchlist edit — parking it makes the gate fail **open** and vanish
  silently.
- **Next week's catalysts:** **July CPI Wednesday** is the dominant event, PPI Thursday, retail sales
  Friday. Earnings are in a lull (AMAT, CSCO, SMCI, JD) — none of ours. Expect the gate to keep trade
  count low into Wednesday, and expect that to be **correct** behaviour.

---

## 2026-08-10 — Daily Review

### Stats
- **4 closed trades — 2W / 2L → 50% win rate. Net realized +$9.71** (avg +$2.43/trade).
  Avg win **+$17.76**, avg loss **−$12.90**, **profit factor 1.38**, payoff 1.38.
  Account **equity $9,085.45**, all cash, **0 open positions**.
- **Reconciliation: EXACT.** Broker `last_equity` $9,075.74 → `equity` $9,085.45 = **+$9.71**,
  matching DB realized P&L **to the cent**. Alpaca shows 4 bracket entries (all filled), 3 exits on
  the **stop leg**, 1 EOD market sell; `dbo.trades` has exactly those 4 rows; `/v2/positions` empty;
  no open orders. No missed fill, no qty drift, nothing carried overnight.
- **Service healthy.** `active`, **NRestarts=0**, up since 11:36:31 UTC (pre-market watchlist
  restart, expected), warmup primed **19/19**, subscribed 19/19 on IEX. **Zero errors, zero
  exceptions, zero 422s** across 9,593 journal lines — including ~67 trailing-stop order replaces.
- **First traded session in four** (last trade before today: MU on 08-05). 08-06 and 08-07 were blanks.

### Trade-by-trade review
All times UTC. **Note: journal app-timestamps are WIB (+7); journald prefixes are UTC** — the
figures below are UTC throughout.

**1. AVGO — LOSS −$11.60 (−0.67%).** Entry 14:02:04 @ $429.83, 4 sh ($1,719), conf **64.4**
(xo 0.29 / trend 0.84 / rsi 1.00 / vol 0.27 / vlt 0.99). Exit 14:54:50 @ $426.93 on the **trailing
stop leg**. **MFE +0.66%** (peak $432.66, 11 min in), MAE −0.81%, **capture −102%**.
*Root cause: excursion smaller than the give-back.* It ran +0.66%, the trail ratcheted 421.06 →
426.95 in six moves, then it round-tripped. With a 1.25% give-back, a peak of +0.66% **arithmetically
guarantees** a ≈−0.6% exit unless the peak is exceeded. Not stop placement, not slippage, not regime
timing — **the trade was never large enough to pay for its own exit.**

**2. ABNB — WIN +$26.21 (+1.44%), the day's best.** Entry 14:15:04 @ $181.479, 10 sh ($1,815),
conf **62.9** — the *lowest* of the four — (xo 0.26 / trend 1.00 / rsi 1.00 / **vol 0.00** / vlt 1.00).
Exit 19:16:28 @ $184.10 on the trailing stop leg after **5h01m**. **MFE +2.45%**, MAE −0.61%,
**capture 59%**. **The only trade all day whose excursion exceeded the give-back — and it out-earned
the other three combined.**
- **IMP-021 CONFIRMED LIVE, instance #2.** Final stop $184.09 against a window peak of $185.92:
  185.92 × 0.99 = **184.06 ✓**, whereas 185.92 × 0.9875 = **183.60 ✗**. The flat 1.25% width **cannot**
  produce a 184.09 stop from any close in the window, so the narrow 1.0% second stage demonstrably
  engaged. Worth ≈ **+$4.60** on this trade vs. the old flat trail (first instance: INTC 08-05, ≈+$5.25).

**3. MU — LOSS −$14.20 (−0.81%).** Entry 16:17:02 @ $879.35, 2 sh ($1,758), conf **73.4 — the day's
highest** (xo 0.31 / trend 0.70 / rsi 1.00 / vol 1.00 / vlt 1.00). Exit 19:45:00 @ $872.25 on the
**trailing stop leg** (stop 872.26). **MFE +0.60%** (peak $884.65, 53 min in), MAE −0.81% — it exited
**at its worst price of the entire hold**. **Capture −134%.**
- ⚠️ **Label correction for the exit-bucket accounting:** the DB reason reads *"end-of-day flatten
  (stop/target filled broker-side)"*, but the broker record is unambiguous — the stop leg was
  triggered at **19:45:00.20 and filled at 19:45:00.24**, and the EOD flatten only ran at 19:45:13,
  finding it already flat. **MU died on the trail, not on the clock**, 13 seconds apart. A future
  review bucketing this as an EOD flatten would draw the wrong conclusion.
- The pre-market note flagged MU's KeyBanc forum appearance at 10:00 ET; entry was 12:17 ET and the
  whole move was +0.6%. **No catalyst effect visible — this was ordinary chop.**

**4. BABA — WIN +$9.30 (+0.47%).** Entry 16:18:04 @ $131.50, 15 sh ($1,973), conf 70.6
(xo **0.25 — exactly the floor** / trend 1.00 / rsi 1.00 / vol 0.54 / vlt 1.00). Exit 19:45:21 @
$132.12 on the **EOD flatten**. **MFE +0.59%**, MAE −0.14%, capture 79%.
- **This trade won because the clock arrived before the trail did.** Its stop sat at $130.60
  (−0.68%) and was simply never reached. Structurally it is the *same trade* as AVGO and MU —
  +0.6% peak, sub-give-back excursion — and got the opposite sign purely from where the session
  ended. **Do not count it as evidence the entry works.** On a 2W/2L day, one of the two wins is timing luck.

### Market context (Perplexity was wrong — verify before citing)
- ⚠️ **Perplexity `sonar` returned FRIDAY's numbers for a question explicitly dated 2026-08-10**:
  "S&P 500 +0.62% at 7,757.64, a record close; Nasdaq +1.30% at 26,690.62; regime trending/risk-on."
  Those are the **08-07** prints, already recorded in that day's review. **Fifth consecutive thin or
  stale run.** It also found no catalyst on any of the four traded names.
- **Actual tape, from IEX daily bars (authoritative):** **QQQ −0.25% open→close** (722.58 → 720.80),
  **SPY +0.03%** (772.77 → 773.02). The session was **flat, directionless chop**, not a melt-up.
  That is *exactly* consistent with three of four trades peaking at ≈+0.6%. Had I taken Perplexity at
  face value I would have concluded the strategy failed in a strong trend, which is the opposite of the truth.

### Signal funnel — 23 scored candidates, 4 entries
| stage | rejects | detail |
|---|---|---|
| confidence < 60 | **11** | BABA 50.9, QQQ 51.1, UNH 54.9, TSLA 55.1, QQQ 55.8, BABA 57.0, AMZN 57.3, TSM 57.4, TSM 57.6, JPM 58.1, **NFLX 59.0** |
| crossover < 0.25 | **7** | WMT 0.07, JPM 0.08, AMZN 0.09, JPM 0.09, TSLA 0.11, AMZN 0.16, **AMZN 0.24 (conf 75.9)** |
| **market gate (IMP-022)** | **1** | TSM, conf 64.4, 15:04 |

**IMP-022 — session 3 of 5.** It blocked **one** entry today, vs 4 on 08-06 and 4 on 08-07; today's
block rate ≈20%, nowhere near the >80%-for-a-week tripwire. **Critically, this is the first session
inside its own window that the gate actually let through** — the filter is not a permanent off-switch.
Running scoreboard: 08-05 −$6.14 (hypothetical), 08-06 +$47.11, 08-07 +$27.96, 08-10 one block (TSM).
**Verdict still due Wed 08-12.**

### The 30-day excursion table (new tonight — IMP-025)
The table IMP-021 specified but could never refresh, now computed automatically over 86 closed trades:

| MFE band | n | avg MFE | avg exit | capture | net |
|---|---|---|---|---|---|
| **<0.5%** | **28** | **+0.20%** | **−1.18%** | **−599%** | **−$605.91** |
| 0.5–1.0% | 27 | +0.73% | −0.43% | −60% | −$214.03 |
| 1.0–2.0% | 15 | +1.45% | +0.50% | 34% | +$155.61 |
| >2.0% | 16 | +2.43% | +1.43% | 59% | +$443.18 |

- **59 of 86 trades (69%) peaked below the 1.25% give-back** — i.e. more than two thirds of this
  book's trades are structurally incapable of finishing green on the trail, whatever the ratchet does.
- **IMP-021's criterion (b) is now MET.** The 1.0–2.0% bucket's capture went **17% → 34%** (exactly the
  doubling IMP-021 predicted) and 0.5–1.0% went **−97% → −60%**. *Honest caveat:* IMP-021's baseline was
  25 trades over 10 days and this is 86 over 30, so the samples overlap but are not the same — this is
  **strongly suggestive, not a clean A/B.** It is nonetheless the first real evidence IMP-021 works.
- 🚨 **The `<0.5%` band is the book's dominant leak: 28 trades, −$605.91, avg MFE +0.20%.** These trades
  essentially **never traded above their entry price**. No exit structure can rescue them — this is a
  pure **entry-selection** failure and it is roughly 2.7× the size of the next-worst band. Removing that
  cohort turns the 30-day book from **−$221 to +$385**. *Caveat (IMP-017): trade-removal overstates entry
  filters on a capital-constrained book — the freed capital would have gone somewhere.*

### What worked / what didn't
- **Worked — exit plumbing, unambiguously.** Three broker-side stop fills all reconciled within
  **13–30 seconds**, DB exit prices match broker fills **to the cent** (incl. BABA at 132.12 where the
  candle close was 132.05), ~67 stop replaces with **zero 422s**. The IMP-012/id-rotation work holds.
- **Worked — IMP-021**, mechanism confirmed live a second time (ABNB, ≈+$4.60), and now corroborated
  in aggregate by the capture table above.
- **Worked — IMP-022 is not a permanent veto.** The worry after two blank sessions was that the gate had
  simply switched the bot off. It let a session through and blocked only its worst-timed candidate.
- **Didn't — the entry signal, again, and now quantified rather than asserted.** **All four entries had
  crossover sub-scores of 0.25–0.31 — every one within 0.06 of the 0.25 floor.** Three of four peaked at
  ≈+0.6% into a directionless tape. The signal is selecting marginal crosses.
- **Didn't — confidence remains inverted.** Today the two **70+** trades netted **−$4.90**; the two
  **sub-65** trades netted **+$14.61**. All-time: 70–79 **+$217.09**, but 60–69 **−$72.66** and 80+
  **−$157.52** on 31 trades. The score is not ranking trades, and sizing scales *with* it.

### Lessons & improvement candidates
1. **[SHIPPED TONIGHT — IMP-025] MFE was measured nowhere, so the one number that decides
   entry-vs-exit blame was hand-derived every time.** Three consecutive reviews rebuilt it by hand;
   IMP-021's own validation criterion (b) went **unmeasured for a week** for exactly this reason. It is
   now `python -m bot.report --days N --mfe`. Zero trading-path change.
2. **Ranked #1 and now precisely targeted: the `<0.5%`-MFE cohort.** Previous reviews said "the entry
   signal has no demonstrated edge"; tonight names the specific failure — **28 trades that never traded
   above entry, −$605.91.** The question for the post-08-12 work is concrete: *is there a pre-entry
   discriminator for that cohort?* Today's four entries all clustered at crossover 0.25–0.31, which is
   the obvious first place to look — but **note the trap**: today's *best* trade (ABNB) had xo 0.26 and
   the day's near-miss at xo 0.24 carried conf 75.9. A naive crossover-floor raise would have cut the
   winner. Needs the harness, ≥3 agreeing windows, and it is **entry-side, therefore frozen until 08-12**.
3. **Deliberately shipped NO behavioural change tonight, and this is a judgement, not an omission.**
   Both axes today's evidence points at are frozen by standing decisions I endorse on the merits:
   **(a) entry side** — IMP-022 is at session 3 of 5, and today is the *first traded session in its
   window*; stacking a second entry filter now destroys the only measurement in progress.
   **(b) exit side** — the weekly of 08-07 recorded *"do not re-tune the trail; two consecutive weeks of
   live trading are required before IMP-021 can be judged."* Tonight ADDS evidence for IMP-021 rather
   than replacing it. Shipping a trail change on a 4-trade day would be textbook thrash.
   The temptation was real: three trades died to the give-back and "just tighten the trail" is one
   config line. It is also **already refuted** — the 07-31 A/B showed a tighter flat width is a
   30-day-window artifact that reverses at 45d and 60d, and the breakeven-gate variant cost ~$134.
4. **Perplexity has now failed five consecutive runs and tonight it failed *dangerously*** — not thin
   but **confidently wrong**, returning a prior session's record close as today's. **Rule: never write a
   market-regime line from `sonar` without an independent price check.** The IEX daily bars are free,
   local, and authoritative; use them first and treat `sonar` as lead-generation only.
5. **Still open, untouched, no new evidence tonight:** whole-share quantisation flattening the size
   curve (today conf 62.9 got $1,815 while conf 73.4 got $1,758 — **inverted**); `STOP_LOSS` structurally
   unreachable behind the trail; the 60–69 band leak.

### Notes for pre-market research
- **Book is CLEAN & FLAT into 08-11** — broker-confirmed **0 positions, 0 open orders**, equity
  **$9,085.45** all cash. Nothing locked, nothing carried.
- **🚨 SE reports Q2 tomorrow (Tue 08-11) — it is parked and must STAY parked.** Do not re-enable on the print.
- **⚠️ Wed 08-12 is July CPI *and* the close of IMP-022's 5-session window.** Expect suppressed trade
  count around the print and expect that to be correct.
- **✅ ABNB is the strongest name on the board and today proves it in P&L, not just chart terms.** Its
  **+2.45% MFE was the only excursion all day to clear the give-back**, and it delivered +$26.21 — more
  than the other three trades combined. Third consecutive session generating quality signal since its
  re-enable. **Keep, emphatically.**
- **⚠️ AMZN is the name to watch, in a bad way: 4 crossover rejects today** (0.24, 0.16, 0.09, 0.09),
  including one at **conf 75.9 / xo 0.24** — a hair under the floor. AMZN is **0W/2 and −$36.18 over 14
  days** and carries the board's largest all-time deficit. The crossover floor is currently the only
  thing keeping it out of the book. **Not a park recommendation yet** — but if it converts one of those
  near-misses and loses, park it.
- **Never signalled at all today (0 candidates): AAPL, AMD, GOOG, INTC, MSFT, NVDA, SPY.** **MSFT is the
  notable absence** — it was the single most productive generator on both 08-06 (3 rejects + the day's
  best signal at conf 70.2) and 08-07 (conf 78.0), and produced **nothing** today. One quiet session is
  not a park signal; flag it if it repeats. **INTC also silent**, and it is the book's best all-time
  earner (+$191.26) — worth noting, not acting on.
- **SPY produced 0 candidates today** (it had 3 on 08-07). Its review point remains **end-August**;
  today does not change that, and it must stay enabled as the IMP-022 fallback symbol.
- **QQQ remains load-bearing twice over** (IMP-022 market gate + IMP-023 replay universe) — verify
  `enabled = 1` before and after any watchlist edit. Parking it makes the gate fail **open** and vanish silently.
- **No park candidates from today's trading.** All four traded names behaved normally; the losses were
  structural (excursion < give-back), not name-specific decay.
- **New tool for tomorrow's routines:** `python -m bot.report --days N --mfe` prints the excursion table.
  Use it instead of hand-deriving MFE — and prefer it over `sonar` for judging whether a day's losses
  were regime or signal.

---

## 2026-08-11 — Daily Review

### Stats
- **Closed trades: 0. Entries: 0. Net realized P&L $0.00.** Broker-confirmed flat: `/v2/positions`
  **0**, `/v2/orders` (status=all, after 08-11T00:00Z) **0**, equity **$9,085.28** with
  `last_equity` **$9,085.28** — i.e. the account did not move a cent today, which is the correct
  signature of a genuine no-trade day rather than a day whose P&L merely netted to zero.
- **Reconciliation: DB ⇄ broker agree perfectly.** `dbo.trades` has 0 rows dated today, `dbo.positions`
  is empty, and the broker holds nothing. No missed fill, no qty drift, nothing carried overnight.
- Service `active`, **NRestarts=0**, up since **08-10 21:27:44 UTC**. Zero errors, zero warnings, zero
  reconnects in the whole session — 9,303 journald lines, of which **15** are non-candle.
- Context: **14-day book 31 trades, 61% win, +$236.73.** A blank day did not disturb that.

### Trade-by-trade review
No trades to review, so the reviewable evidence is **the 15 candidates that were refused**, and which
filter refused each. Times below are **UTC** (journald rendered them in WIB all day — see IMP-026):

| # | UTC | symbol | conf | refused by |
|---|---|---|---|---|
| 1 | 14:24 | TSLA | 64.8 | **market gate (IMP-022)** |
| 2 | 14:26 | TSM | 69.1 | **market gate (IMP-022)** |
| 3 | 14:30 | SPY | 61.8 | crossover 0.04 < 0.25 |
| 4 | 15:01 | SPY | 51.1 | confidence < 60 |
| 5 | 15:24 | ABNB | 57.8 | confidence < 60 |
| 6 | 15:30 | ABNB | 53.7 | confidence < 60 |
| 7 | 15:34 | ABNB | 69.7 | crossover 0.10 < 0.25 |
| 8 | 16:06 | JPM | 55.6 | confidence < 60 |
| 9 | 16:35 | ABNB | 73.3 | **market gate (IMP-022)** |
| 10 | 17:57 | JPM | 67.1 | crossover 0.02 < 0.25 |
| 11 | 18:09 | JPM | 67.0 | crossover 0.03 < 0.25 |
| 12 | 18:11 | ABNB | 63.3 | crossover 0.2499 < 0.25 |
| 13 | 18:25 | JPM | 64.1 | crossover 0.09 < 0.25 |
| 14 | 19:04 | AMD | 53.3 | confidence < 60 |
| 15 | 19:13 | AMD | 68.5 | crossover 0.10 < 0.25 |

**Refusal split: crossover floor 7, confidence threshold 5, market gate 3.** Note the ordering in
`strategy.on_short_candle` — `evaluate_entry` runs first, so the market gate only ever sees
**fully-qualified** entries. The three it blocked were real trades the bot wanted to take.

**Counterfactual — what the market gate turned away (priced against real IEX 1-min bars, live sizing
Model A off BP $36,341, live exits: 2% stop, trail 1.25% → 1.0% after +1%, 10% TP, EOD flatten 19:45):**

| symbol | conf | qty | entry | exit | reason | MFE | MAE | P&L |
|---|---|---|---|---|---|---|---|---|
| TSLA | 64.8 | 6 | 335.310 | 331.158 | stop/trail | **+0.09%** | −1.34% | **−$24.91** |
| TSM | 69.1 | 5 | 423.640 | 420.815 | EOD flatten | **+0.30%** | −0.92% | **−$14.12** |
| ABNB | 73.3 | 13 | 185.845 | 186.430 | EOD flatten | **+0.69%** | −0.41% | **+$7.61** |
| | | | | | | | | **−$31.43** |

**The gate saved $31.43 today.** Independently, a full replay of the session with
`MARKET_FILTER_SYMBOL=` (gate off) takes 1 trade for **−$13.65**; gate on reproduces live **exactly
(no trades)**. Two methods, same sign.

### What worked / what didn't
- **The blank day was correct, and this is the strongest single-session evidence IMP-022 has produced.**
  QQQ ran **open 723.01 → close 718.49 = −0.63%**, SPY −0.51%: a *down* session. IMP-022's own 38-session
  bucketing puts down-tape at **33.1% win, −$33.12 per session**. The gate's measured saving today
  (**−$31.43** avoided) lands within a dollar and a half of that historical average. The filter did
  precisely the job it was specified to do, on precisely the tape it was specified for.
- **Perplexity `sonar` corroborates the regime and nothing else** — "choppy with a risk-off bias",
  Nasdaq −0.3%/−0.6%, weakness attributed to Intel and chipmakers on Strait-of-Hormuz doubt; **no
  ticker-specific catalyst** for TSLA, TSM, ABNB, JPM or AMD. Seventh consecutive thin run. Regime read
  only, as the standing rule says — the QQQ tape, not `sonar`, is what carried this conclusion.
- **All three blocked entries peaked under +0.7% MFE.** None of them reached the 1.25% give-back, so
  none could have finished green on the trail regardless of exit tuning. They sit squarely in IMP-025's
  dominant `<1.0%` leak band. Even the "winner" (ABNB +$7.61) was an EOD-flatten scrape, not a trade
  that worked.
- **The crossover floor did more blocking than the market gate (7 vs 3) and is invisible in the P&L.**
  Nobody has ever priced what `MIN_CROSSOVER=0.25` refuses. Four of its seven refusals today carried
  conf **64–70** — these are not obvious junk. One (ABNB, #12) missed by **0.0001**. This is now the
  largest unmeasured filter in the system.
- **JPM is newly loud: 5 candidates today, its most in the sample, and 4 died on the crossover floor**
  with conf 64–67. It has been a quiet name. Worth watching, not acting on.
- **What did not happen is as informative as what did:** no feed loss, no reconnect, no 422, no
  stop-replace churn, no DB error, no restart. Every failure mode the last ten IMPs hardened stayed shut.

### Lessons & improvement candidates
1. **(Shipped tonight — IMP-026) The post-close evidence base was reading seven hours wrong.** Since the
   2026-08-02 VPS move to Asia/Jakarta, journald's `asctime` prefix has been **WIB** while every
   timestamp *inside* the same line — candle starts, `entry_time_utc`, the market-hours gate — stayed
   **UTC**. Today that cost real work: pairing each `no entry` line to the candle that produced it (the
   whole basis of the −$31.43 counterfactual above) required shifting every line by hand, and a reviewer
   who took the prefix at face value would have concluded the bot was signalling at 23:35 — seven hours
   after the close. **Verified negative, and it matters: the trading path was never affected.** Every
   clock read in `bot/` is `datetime.now(UTC)`; the only naive-looking call, `candles.py:109`, is
   `fromtimestamp(aligned, tz=UTC)` and is correct. So the market-hours gate, the IMP-017 blackout and
   the IMP-007 EOD-flatten watchdog all ran on correct time throughout. **This was an instrument fault,
   not a capital fault** — but tomorrow night's IMP-022 verdict is read off this instrument.
2. **Price the crossover floor — this is the next real strategy question, and it is now the biggest one.**
   `MIN_CROSSOVER=0.25` is the single most active filter in the book and has never been A/B'd. The
   analysis is ready to run the moment the entry freeze lifts: replay across ≥3 windows at 0.20 / 0.25 /
   0.30, and price today's seven refusals directly. **Deliberately NOT shipped tonight** — see below.
3. **`<1.0%` MFE remains the structural leak** (IMP-025: 59 of 86 trades over 30 days peaked below the
   give-back). Today added three more examples and zero counterexamples. It is an *entry* problem.
4. Unchanged and still open from 08-10: the sizing ladder is inverted above conf ~80 (conf 62.9 drew a
   larger notional than conf 73.4); the 90–100 band is **0% win on 3 trades, −$144.42**; `STOP_LOSS` is
   structurally unreachable behind the trail.

### Why tonight's change is instrumentation and not strategy
Both P&L surfaces are under deliberate, well-reasoned freezes that I am not entitled to break on one
session's data:
- **Entry side is frozen until 08-12** — today was session 4 of IMP-022's 5-session window. Shipping an
  entry-side change tonight would contaminate the final session of the measurement, and IMP-022 is the
  best-validated change this bot has (4-window A/B, every metric, same sign).
- **Exit side is frozen by the 08-07 weekly's explicit "do not re-tune the trail"** — IMP-021 still has
  n=1 qualifying live trade and needs two clean weeks.
Both expire imminently (08-12 and Friday), and **both verdicts will be reached by reading journald.**
Fixing the timebase tonight is therefore not filler — it is the precondition for two verdicts due within
72 hours, and it is the same call IMP-023/IMP-024/IMP-025 made three times: when the trading surfaces are
frozen, fix the instrument. The improvement log already records that a miscalibrated instrument twice
nearly produced an inverted conclusion.
**Honest statement of what this does NOT do: it adds no edge and moves no P&L.** The bot's underlying
signal still has no demonstrated standalone edge — the gate is doing the work, by declining to bet.

### Notes for pre-market research
- **Book is CLEAN & FLAT into 08-12** — broker-confirmed **0 positions, 0 open orders**, equity
  **$9,085.28**, all cash, `last_equity` identical. Nothing locked, nothing carried.
- **🚨 Wed 08-12 is a triple event: July CPI (8:30am ET), IMP-022's verdict day (session 5 of 5), and
  INTC's $20B offering closes.** Expect a low trade count and expect that to be correct. Do not read a
  quiet CPI morning as signal death.
- **📌 Hand tomorrow's post-close routine this: IMP-022 is now 3 for 3 on live counterfactuals** —
  08-06 ≈ +$47 saved, 08-07 both blank days correct, **08-11 +$31.43 saved (priced above)**. The
  5-session verdict should be a formality unless 08-12 inverts it. Also re-run `--days 30 --mfe` after
  the close for the capture-based verdict (IMP-025 criterion (c)); **today added no trades, so the
  30-day excursion table is byte-identical to the one in the 08-10 entry — do not re-derive it.**
- **✅ ABNB is again the most productive generator on the board — 5 of today's 15 candidates**, including
  the day's highest-confidence signal (73.3) and the only blocked entry that would have made money.
  Fourth consecutive session of quality signal. **Keep, emphatically.**
- **⚠️ JPM produced 5 candidates today, its most ever, and 4 died on the crossover floor at conf 64–67.**
  It has historically been quiet. This is a *positive* liveness observation, not a park signal — flag it
  if the near-misses keep accumulating without conversion.
- **AMZN: zero candidates today**, after 4 crossover rejects on 08-10. The 08-10 entry's park test —
  "if it converts one of those near-misses and loses, park it" — is **still not met**. No park. It stays
  on notice.
- **Never signalled at all today (0 candidates): AAPL, AVGO, BABA, GOOG, INTC, MSFT, MU, NFLX, NVDA,
  QQQ, UNH, WMT.** That is 12 of 19 silent, which on a −0.63% QQQ tape with a bullish-only signal is
  **expected, not decay** — do not park anything on today's silence. **MSFT is now quiet two sessions
  running** (flagged 08-10 as "flag it if it repeats") — it has now repeated, so it is formally on
  notice, but a 12-name-silent tape is the wrong day to judge it. Re-check 08-12/08-13.
- **WMT: still 0 trades since 07-24 and still 0 candidates today.** Its dead-signal decision was
  scheduled for the **08-13 run**; today does not advance it either way. Remember its earnings park is
  due **08-19** and the two decisions have different re-enable conditions — do not let one become the other.
- **QQQ remains load-bearing twice over** (IMP-022 market gate + IMP-023 replay universe) — verify
  `enabled = 1` before and after any watchlist edit. Parking it makes the gate fail **open** and vanish
  silently. It is also the symbol whose ribbon produced today's entire (correct) stand-down.
- **From 08-13 the add-freeze expires** — arrive with a screened add candidate or an explicit reason not to.
- **Reading journald from tomorrow on: timestamps are UTC and carry an explicit `UTC` marker** (IMP-026).
  Lines written *before* tonight's restart are WIB (UTC+7) — subtract 7 hours when reading back over
  08-02 → 08-11.

---

## 2026-08-12 — Daily Review

### Stats
- **The DB says 0 trades. The DB is wrong.** The broker took **1 trade today: MU, and it WON.**
  Entry **924.08 × 2 sh** @ 14:08:01.58Z, exit **926.31 × 2** @ 18:25:38.99Z → **+$4.46 (+0.241%)**.
  Confirmed three ways: the filled orders, and equity **$9,085.28 → $9,089.74 = +$4.46 to the cent**
  (`last_equity` vs `equity`). Flat at the close: **0 positions, 0 open orders**, all cash.
- `dbo.trades` has **zero rows** dated today and `bot.report --days 1` reports "0 closed trades".
  **This is a reporting failure, not a quiet day** — see the two defects below.
- Trailing context (DB, therefore now understated by one winner): 14-day **27 trades, 63% win,
  +$233.83**; 30-day **84 trades, 43% win, −$169.67**.
- Service `active`, **NRestarts=0**, up since 08-11 21:23:50 UTC. 9,369 journald lines, **1 ERROR**.

### Trade-by-trade review

**MU — model A, conf 80.5 (xo 0.66 / trend 1.00 / rsi 1.00 / vol 0.67 / vlt 0.71) — +$4.46 WIN**

| | |
|---|---|
| entry | 14:08:01.58Z @ **924.08** (signal 924.36), qty 2, notional $1,848.72 |
| initial stop / target | 905.87 (−2.0%) / 1,016.80 (+10%) |
| MFE | **+1.26%** (high **935.73** @ 17:50) · MAE ≈ −1.0% (low 914.84 @ 14:20) |
| exit | 18:25:38.99Z @ **926.31** — trailing stop, filled 0.06% *above* its 925.74 trigger |
| vs. holding | MU closed **911.30**; the EOD flatten would have booked ≈ **−$10**. The trail saved ≈$14 |

**Root cause of the win: IMP-021's two-stage trail, doing exactly what it was specified to do.**
This is the first *clean, qualifying* live demonstration (n=2 overall). MU crossed +1.0% at 17:45
(933.32 threshold; hit 933.49 then 935.73), which armed the tightened 1.0% give-back; the trail then
ratcheted 905.87 → 925.74 across **18 stop replaces**, all successful, no 422s. Price rolled over from
935.73 and the tightened stop cut it at 926.31 — **above the entry**. Under the old single-stage 1.25%
trail the stop would have sat ≈924.03, i.e. **at the entry**, and this is a scratch instead of a win.
Under EOD-flatten-only it is a −$10 loser. Small win, but the exit structure earned every cent of it.

**Regime check.** Perplexity `sonar`: S&P 500 **−0.32% to 7,728.20**, Nasdaq **−0.60% to 26,445.45**,
"choppy-to-risk-off", rotation out of large-cap tech, **no ticker-specific catalyst for MU, NVDA, INTC,
TSM or AVGO**. So MU was not a news move — it was a genuine intraday trend leg into a fading tape, and
the bot exited into strength before the −1.6% afternoon slide. Taking one trade on this tape was right.
Eighth consecutive thin `sonar` run — regime read only, as standing rule.

**The 31 refusals.** Crossover floor **13**, confidence < 60 **17**, market gate **1** (INTC @ 16:38,
conf 66.8, QQQ 5m ribbon not bullish). Ratio consistent with 08-11. The crossover floor is again the
busiest filter and again unpriced — four refusals carried conf 69–74 (TSM 73.6, INTC 73.5, WMT 71.1,
NVDA 72.9) and INTC missed by **0.01** at 17:20.

### 🔴 Two defects, both found only because the broker was reconciled against the DB

**1. `reconcile_exit` booked a two-day-old fill as today's exit (fixed tonight — IMP-027).**
At 18:25:40.07Z the bot logged `reconcile_exit MU: broker-side fill @ 872.25 (order 5434412a…)`.
Order `5434412a` is the **2026-08-10** MU stop, filled @872.25 — a *different trade, two sessions old*.
Today's real exit (`c94f6f32` @ **926.31**) had filled **1.09 seconds earlier** and was not yet in the
broker's closed-order listing, which is eventually consistent. `reconcile_exit` took "the newest filled
sell" on faith, found nothing from today, and fell through to the previous trade's exit.
**Impact: a +$4.46 win would have been recorded as a −$103.66 loss — a $108 error, 1.2% of equity, on
the only trade of the day, in the wrong direction.** It also feeds the confidence table (the 80–89
bucket), the MFE study, and every IMP decision downstream. Verified by re-querying the same endpoint
after the close: it now returns `c94f6f32` @926.31 first — the data was right, the *read* was early.
This is the residual half of **IMP-015**, which guarded the *entry-not-yet-filled* end of the same
failure and left the *exit-not-yet-listed* end open. Third time this class has bitten (2026-07-20 NVDA,
2026-07-10 SE, today).

**2. The entry never persisted, so the trade is invisible to the DB (NOT fixed — one change per run).**
`14:08:01,840 ERROR ustradebot.persistence | failed to persist entry for MU` →
`pyodbc.OperationalError ('08S01', 'TCP Provider: Error code 0x20 (32)')`. The connection had gone
stale between sessions and the INSERT hit a dead socket. `record_entry` catches, logs, returns `None`
— and **does not retry**. The exit then had no `trade_id` to attach to (`DB exit MU trade_id=None`), so
*both* legs were lost. IMP-019 added `_reset()`-on-error, which makes the *next* write reconnect, but
nothing re-drives the failed one. A single retry after `_reset()` would have saved this row: the
connection was healthy 12 seconds later (every subsequent DB call today succeeded).
**Queued as tomorrow's top candidate — recorded in `todo.md`.**

### What worked / what didn't
- **Worked: the trade itself, and the exit structure specifically.** Entry on a real crossover
  (xo 0.66 — the strongest signal component in weeks), trend and RSI both maxed, and the exit converted
  a +1.26% excursion into a realised gain instead of the round-trip that IMP-025 says kills 59 of 86
  trades. **This is the first live trade where the trail beat both alternatives on the same tape.**
- **Worked: the market gate stayed quiet and correct.** One block on a −0.60% Nasdaq day. IMP-022's
  5-session window closes today with the gate never having produced a wrong-signed session.
- **Didn't work: the recording layer, twice over, in the same trade.** Two independent defects on one
  trade is not coincidence — it is that *every* write path today ran without a verification step. The
  bot's P&L truth has been the broker all along; the DB is a derived copy that nothing was checking.
  **Today's real lesson is that the evidence base this bot improves from is not self-validating.**
- **Uncomfortable but honest:** had I read only `bot.report --days 1` and the DB, I would have written
  "no trades today, blank session, no change warranted" — and been wrong about the day, the trade, and
  the health of the system. The broker reconciliation step in this routine is what caught it.

### Lessons & improvement candidates
1. **(Shipped tonight — IMP-027)** An exit may never be attributed to a sell that filled *before* its
   own entry. Hard invariant, not another timing heuristic — it kills the whole class regardless of
   listing lag, and it degrades safely (no candidate → `None` → symbol stays MANAGING → next candle
   retries, which today would have read 926.31 correctly at 18:26).
2. **Retry `record_entry` once after `_reset()`** — highest-impact remaining, and today it cost a
   whole trade. In `todo.md`.
3. **Add a post-close DB⇄broker reconciliation assert.** Both of today's defects were invisible to
   every automated surface and surfaced only because this routine queried Alpaca by hand. A check that
   compares the day's broker fills against `dbo.trades` and alerts on a mismatch would have paged at
   18:26 instead of being found at 21:15. Strong candidate for the weekly.
4. **Price the crossover floor.** Carried unchanged from 08-11 and now overdue: 13 refusals today, four
   at conf 69–74, one missing by 0.01. `MIN_CROSSOVER=0.25` is still the largest never-A/B'd filter in
   the system, and the IMP-022 entry freeze expires with today's session.
5. Unchanged and open: sizing ladder inverted above conf ~80; the 90–100 band is 0% win on 3 trades,
   −$144.42; `STOP_LOSS` structurally unreachable behind the trail.

### Notes for pre-market research
- **📌 Correct today's number when you read it: the DB will tell you 08-12 was a blank day. It was
  not — MU, +$4.46, and it is missing from `dbo.trades` because the entry INSERT hit a dead socket.**
  Equity **$9,089.74** is the truth. Do not diagnose "signal death" from the empty table.
- **Book is CLEAN & FLAT into 08-13** — broker-confirmed **0 positions, 0 open orders**, equity
  **$9,089.74**, all cash. Nothing locked, nothing carried.
- **✅ MU is the standout and should stay emphatically.** Only name to convert today, did it on the
  day's strongest crossover (0.66) with trend and RSI maxed, and it is the bot's best generator this
  week. Note it is also the **highest-ATR name on the board (8.91%)** — that is why it produced a
  +1.26% excursion on a −0.6% Nasdaq day. The volatility is the edge here, not a defect; keep the
  sizing question separate from the keep/park question.
- **⚠️ INTC: 6 candidates, 0 conversions — the most active refused name today**, including a
  **0.01 miss** on the crossover floor at 17:20 (conf 62.4) and the day's single market-gate block
  (16:38, conf 66.8). Its $20B offering closed today, so the overhang is now resolved. Positive
  liveness, not a park signal — but it is the name most sensitive to the `MIN_CROSSOVER` decision the
  post-close routine owns. Flag it again if it repeats without conversion.
- **NVDA 5 candidates / 0 conversions, TSM 3, JPM 4, WMT 3, SPY 3, AVGO 3, QQQ 2, UNH 2, AMZN 0.**
  **AMZN is now three sessions with no candidate at all** — its 08-10 park test ("converts a near-miss
  and loses") is still **not met**, so still no park, but the silence itself is now worth a look.
- **Never signalled today (0 candidates): AAPL, ABNB, BABA, GOOG, MSFT, NFLX, TSLA.** **ABNB going
  silent is a genuine break** — it was the most productive generator for four straight sessions and
  led yesterday's board with 5. One session, on a risk-off tape, after a +20.9%-vs-20MA run: do not
  act, but this is the first thing to check tomorrow.
- **WMT's dead-signal decision is due at the 08-13 run** (3 candidates today, still 0 trades since
  07-24). Its earnings park is a separate decision due **08-20** — do not merge them.
- **PLTR was screened and handed over by the 08-12 pre-market entry** and the add-freeze expired
  today — the add decision is live tomorrow.
- **QQQ remains load-bearing twice over** (IMP-022 gate + IMP-023 replay universe) — verify
  `enabled = 1` before and after any watchlist edit. Parking it makes the gate fail **open**, silently.

---

## 2026-08-13 — Daily Review

### Stats
- **8 closed trades — 4W / 4L, 50% win, net +$34.53.** Avg win **+$22.61** vs avg loss **−$13.98**
  (**payoff 1.62**), **profit factor 1.62** (gross +$90.44 / −$55.91). Equity **$9,089.68 → $9,124.21**
  (+0.38%). Flat at the close: **0 positions, 0 open orders**, all cash.
- **Broker reconciles to the cent.** All 8 entries and 8 exits match `dbo.trades` exactly — 6 exits
  filled broker-side on the ratcheted stop leg, 2 on the EOD flatten market sell. `last_equity`
  $9,089.68 → `equity` $9,124.21 = **+$34.53**, identical to the DB. No missed fill, no qty drift,
  no phantom row, nothing carried overnight.
- **The 08-12 entry-INSERT defect did NOT recur** — all 8 rows persisted (trade_id 283–290).
  **IMP-027 held**: every exit was attributed to its own sell, no stale-order mis-book.
- Service `active`, **started 11:37:48 UTC (pre-open), NRestarts=0**, 10,084 journald lines,
  **zero WARNING or ERROR records all day**. Cleanest session in weeks.
- 51 refusals: **crossover floor 31, confidence floor 20, market gate 0**. 24 of the crossover
  refusals carried conf ≥ 65.

### Trade-by-trade review
All model A, all entered after the 10:00 ET blackout (IMP-017 respected — earliest 10:05 ET).
MFE/MAE from `bot.report --mfe`.

| # | sym | entry (UTC) | conf (xo/trend/rsi/vol/vlt) | MFE | MAE | exit | P&L |
|---|-----|------|------|------|------|------|------|
| 1 | NVDA | 14:05 @226.19 | 64.8 (.40/.89/1.0/.00/1.0) | +0.12% | −1.09% | 19:45 EOD @225.72 | **−$4.23** |
| 2 | INTC | 14:12 @105.33 | 73.7 (.77/1.0/1.0/.00/.70) | +1.24% | −0.44% | 14:55 trail @105.36 | **+$0.70** |
| 3 | MU | 14:13 @938.29 | 77.9 (.62/.94/1.0/.48/.88) | +4.23% | −0.40% | 15:34 trail @966.41 | **+$56.24** |
| 4 | TSLA | 14:23 @333.46 | 66.4 (.38/1.0/1.0/.00/1.0) | +2.45% | −0.33% | 19:45 EOD @339.29 | **+$29.16** |
| 5 | AMD | 14:48 @495.80 | 64.0 (**.26**/1.0/1.0/.09/1.0) | +0.42% | −0.99% | 15:52 trail @490.56 | **−$10.49** |
| 6 | INTC | 15:07 @106.08 | 81.2 (.41/1.0/1.0/1.0/.93) | +1.39% | −0.00% | 15:35 trail @106.31 | **+$4.34** |
| 7 | MU | 17:01 @971.50 | 83.4 (.46/1.0/.98/1.0/1.0) | +0.38% | −0.90% | 18:54 trail @962.50 | **−$18.00** |
| 8 | INTC | 18:47 @105.71 | 78.0 (**.27**/.99/1.0/1.0/1.0) | +0.28% | −1.18% | 19:25 trail @104.49 | **−$23.19** |

**Regime (Perplexity `sonar`).** S&P 500 **+0.7% to 7,798.99 — a record close**; Nasdaq Composite
**+0.8% to 26,803.03**. Regime read: **trending / risk-on**, broad advance, not choppy. No
ticker-specific catalyst for NVDA/INTC/MU/TSLA/AMD — semis simply participated in the tech bid.
Ninth consecutive thin `sonar` run on single names; regime read only, as standing rule.

**Root causes.**
- **The two winners are the whole day and they are exit-structure wins.** MU #3 peaked +4.23% and
  banked **+3.00% (71% capture)**; TSLA peaked +2.45% and banked **+1.75% (71% capture)**. Both were
  held through hours of noise and cut on the ratchet, not the clock. This is IMP-018 + IMP-021 doing
  precisely what they were specified to do, on a trending tape.
- **The four losers are all the same trade: an entry that never worked.** MFE +0.12 / +0.42 / +0.38 /
  +0.28% — none ever showed meaningful profit; all four were cut by the trail at −0.9% to −1.2%, i.e.
  **well inside the 2% stop**. No stop was hit, nothing gapped, nothing slipped. Not a stop-placement
  failure, not a regime failure (the tape was up) — **entry quality**.
- **Today separates cleanly on MAE, not on confidence.** All 4 winners had MAE ≤ **0.44%**; all 4
  losers had MAE ≥ **0.90%**. Confidence did the opposite of its job: the two highest-confidence
  entries of the day (83.4 MU, 81.2 INTC) returned −$18.00 and +$4.34, while conf 66.4 TSLA made
  +$29.16 and conf 77.9 MU made +$56.24.
- **The crossover sub-score did line up today.** Winners averaged xo **0.545**, losers **0.348**; the
  two lowest crossovers on the board (AMD **0.257**, INTC **0.275**) were the two worst trades,
  −$33.68 between them. Suggestive — and tested below, where it did **not** survive.
- **NVDA was dead capital for 5h40m** (MFE +0.12%, trail frozen at 223.62 from 14:38 onward) and only
  left on the EOD flatten. Cheap in P&L (−$4.23), expensive in opportunity.

### What worked / what didn't
- **Worked:** the exit structure (71% capture on both real movers); the opening-range blackout; the
  bracket/trail replace loop (no 422s, every stop leg moved cleanly); persistence (8/8 rows);
  reconciliation (exact); the service (zero warnings).
- **Didn't:** entry selection. 4 of 8 entries had no favourable excursion worth the name. Confidence
  remains **inverted at the top** — the 90-100 band is now 3 trades / 0% win / −$144.42 all-time and
  80-89 is 30 trades / 47% / −$26.75, against 70-79 at 87 trades / 54% / **+$250.84**.

### Lessons & improvement candidates
**Two changes were specified, tested against multiple windows, and BOTH were refuted. Neither
shipped.** Recording them in full so they are not re-proposed.

1. **❌ REFUTED — tighten the initial stop (2.0% → 1.25%).** A path-aware study over 174 live trades
   / 45 days (walking real 1-min bars in order) said trades that go −1% against them *before* making
   +1% win only **7% of the time** (4 of 58) and cost **−$1,287**; the counterfactual scored
   **+$220**. It does not survive the bot's own replay: across 15/30/45/60d the deltas are
   **0 / +$2.94 / +$3.87 / −$21.08** — signs 0/+/+/−, failing IMP-021's standing "≥3 windows agreeing
   in sign" rule. 1.0% is worse in **all four** windows (−$49/−$44/−$57/−$110).
   **Why the study was wrong, and it is worth knowing:** the trail ratchets the stop to
   `close × (1 − 1.25%)` on the *first candle after entry*, so the 2% initial stop is only ever
   binding for a trade that drops >0.76% immediately and keeps falling — roughly 1–2 trades per 45
   days. The study priced a rule the live system does not execute. **The initial stop is already
   nearly vestigial; do not re-litigate it.**
2. **❌ REFUTED — raise the crossover floor (`MIN_CROSSOVER` 0.25 → 0.30+).** This was the standing
   "now overdue" todo and today's per-trade evidence supported it. Live buckets look damning: the
   **0.25–0.30 band is the largest cohort and the biggest loser** — all-time n=133, 42.9% win,
   **−$242.76**; last 45d n=70, 38.6% win, **−$197.44**. But replay is **unanimous against it in all
   four windows**: net falls 0.25→0.30→0.35→0.40 at 15d (+327/+254/+252/+274), 30d
   (+379/+309/+261/+266), 45d (+528/+380/+346/+320) and 60d (+741/+529/+513/+478). Profit factor and
   avg/trade *rise* (PF 2.17→2.54 at 45d) — the floor buys quality and sells more gross profit than
   it buys. Also: at −$2.82/trade over 70 trades the live band signal is **inside one standard
   error**. Not shipped.

3. **🔬 The instrument was itself validated tonight, and this retires a real doubt.** Replay and live
   diverge hugely over 45–60 days (replay **+$528/+5.3%** vs live **−$188** at 45d), which initially
   looked like a broken harness. It is not. Over the **config-stable window since IMP-021 shipped
   (08-03 → 08-13)** the two agree closely: **replay 23 trades / 65.2% win / +$279.31** vs **live 22
   trades / 63.6% win / +$171.42** (the residual gap is replay's $10k vs the account's $9.1k base and
   zero slippage). The long-window divergence is replay correctly showing the **counterfactual value
   of IMP-017/018/021 applied to sessions that ran without them** — i.e. evidence those changes
   worked, not evidence the harness is broken.
   **⚠️ Corollary that must propagate: every live-history bucket study over 45+ days is contaminated
   by pre-IMP-021 trades.** The "104 of 162 trades never reach +1% MFE and lose $1,301" figure, and
   the crossover bands above, are largely legacy artifacts. **Under the current configuration the
   bot's live record is +$171.42 over 4 sessions at 63.6% win.** Judge future changes on the
   post-08-03 window or on replay — not on the 45-day live tail.

4. **Still open, not tonight:** confidence is inverted above ~80 (90-100 band 0/3, −$144.42) — the
   strongest remaining entry-side lead, but n=3 in the top band is too thin to act on and
   `SIZE_CONFIDENCE_CAP` already blunts it. Revisit when the top two bands reach n≈20 under
   post-08-03 config.

### Improvement shipped
**IMP-028 — `record_entry` retries once on a fresh connection.** With both strategy candidates
refuted, the slot went to the standing 🔴 top item from 08-12: the dead-socket INSERT that erased an
entire session from `dbo.trades` while the broker held a real filled position. Idempotent (looks the
bracket up by `entry_order_id` before re-inserting, so a failure raised *by* `commit()` cannot
double-count), bounded at exactly one retry. **363 tests pass** (359 → 363), non-vacuity verified.
Details in `memory/improvement-log.md`.

### Notes for pre-market research
- **✅ MU is again the standout — +$56.24 on a +4.23% MFE, the best trade of the day**, and +$38.24
  net across its two trades. Sixth consecutive run flagging its **8.61% ATR as a sizing question, not
  a park question**. Keep emphatically.
- **✅ INTC is the workhorse and the churn risk at once: 3 trades, net −$18.15 today** (+0.70, +4.34,
  −23.19) — but **+$47.07 over 6 trades since 08-04, the best symbol on the board**. Do **not** read
  today's −$18 as decay. Note its 3rd entry of the day (18:47, xo 0.275) was the worst trade;
  late-session low-crossover INTC re-entries are the weak spot, but the crossover floor was tested
  tonight and refuted — leave it alone.
- **✅ TSLA converted beautifully** (+$29.16, 71% capture) despite entering at conf 66.4 and sitting
  **−1.8% below its 20MA** on this morning's screen. A reminder that the trend screen is a watchlist
  filter, not a signal — do not park names for being below the 20MA alone.
- **✅ GOOG is no longer silent.** The 08-13 pre-market entry flagged it as "the only enabled symbol
  with ZERO candidates across all five sessions" — **it produced 4 candidates today**. Concern
  retired; no park.
- **✅ PLTR, added this morning, produced 6 candidates on day one** — second-most active name on the
  board. Liveness confirmed immediately; no conversion yet, which is expected. Keep.
- **⚠️ Four enabled symbols produced zero candidates today: AMZN, BABA, JPM, UNH.** AMZN is now on
  its second stretch of silence and was already "on notice" — its park test (converts a near-miss and
  loses) is **still not met**, so no park, but this is the fourth run raising it. BABA converted a
  winner on 08-10; JPM and UNH are the quiet end of the board as usual.
- **AMD entered at crossover 0.257, the lowest on the board, and lost −$10.49** — its 7.32% ATR
  remains a sizing question. Not a park; single trade.
- **Book is CLEAN & FLAT into 08-14** — broker-confirmed 0 positions, 0 open orders, equity
  **$9,124.21**, all cash, nothing locked. **No enabled symbol reports tomorrow**; AMAT printed after
  today's close and can move MU/NVDA/AMD/INTC/TSM in the pre-market — the book carries no exposure to
  it. **WMT reports Thu 08-20 BMO; NVDA 08-26.**

---

## 2026-08-14 — Daily Review

### Stats
- **Closed trades: 0. Entries: 0. Net realized P&L $0.00.** Win rate n/a, profit factor n/a.
- **Equity $9,123.87**, all cash, **0 positions, 0 open orders** — broker-verified via the
  `alpaca-usbot` MCP (`GET /v2/orders?status=all&after=2026-08-14T00:00:00Z` returned **[]**,
  `/v2/positions` returned **[]**). `dbo.trades` returned **0 rows** for today.
  **`equity == last_equity == 9,123.87` — perfect DB↔broker reconciliation, zero drift.**
- The **−$0.34** vs the 08-13 review's $9,124.21 was already explained in this morning's research
  log as a settle-side adjustment; `last_equity == equity` today confirms nothing moved.
- Service **ACTIVE** all session, **zero warnings, zero errors**, ~9,600 candles ingested across
  1m/5m for all 20 symbols. The feed was healthy — **this was not a data outage.**

### Trade-by-trade review
No trades to review. Root-causing the flat session instead — the strategy reached a scoring
decision **25 times** and refused every one:

| Refusal | n | Range seen | Threshold |
|---|---|---|---|
| `confidence < 60` | **15** | 51.1 – 59.4 | 60 |
| `crossover < 0.25` | **8** | 0.02 – 0.18 (conf 61.4–74.3) | 0.25 |
| `market gate closed (QQQ 5m ribbon not bullish)` | **2** | conf **76.5**, **91.2** | — |

- **The 15 confidence refusals were correct and should not be loosened.** Every one landed in
  51–59, i.e. below the band that would have put them in the **60-69 bucket — the bucket that has
  lost money over 146 lifetime trades (41.8% win, −$58.22)**. Loosening the threshold to catch a
  59.4 buys trades from the bot's *worst* cohort. The near-misses are a temptation, not a signal.
- **The 8 crossover refusals were also correct.** `MIN_CROSSOVER` was explicitly **tested and
  refuted on 08-12**; the 08-13 review instructed leaving it alone. Instruction followed, no change.
- **The 2 market-gate refusals are the only genuine cost of the day — and it is smaller than it
  looks.** Both were **AMD**, at 14:21 (conf 76.5) and 14:24 (**conf 91.2 — the highest score the
  bot produced all day**), blocked because the QQQ 5m ribbon was not bullish. AMD then closed
  **+6.5% at the high of the day**. That looks like a catastrophic miss. **It was not.** The
  counterfactual, walked bar-by-bar against the bot's own live exit rules:

  - Entry ≈ **$503** (14:20–14:25 5m bar: o 501.01 / h 504.375 / c 503.25).
  - Peak **$511.29** on the 14:35 bar → clears +1.00% profit → **IMP-021 tightens the trail from
    1.25% to 1.00%** → trail sits at **$506.18**.
  - 14:40 bar low **506.385** — holds by twenty cents. **14:45 bar low 504.60 → trail breached.**
  - **Exit ≈ $506.18 = +0.63%.**
  - Held instead to the EOD flatten (19:45 UTC, bar close 509.51) it would have made **+1.29%**.
  - It would *not* have hit the −2% hard stop ($493.94); AMD's worst point was 496.54 (−1.3%).

  **So the gate cost ≈ +0.6%, not +6.5%.** And most of AMD's 6.5% was never available: it **gapped
  +1.0% at the open and was already +3.0% by 14:00 UTC** when the IMP-017 blackout lifts. The whole
  move the bot could legitimately have reached was **≈ +2.4%** (497.61 → 509.51), of which its own
  trailing stop would have surrendered three quarters.

### What worked / what didn't
- **Worked: the bot was right to stand aside.** The tape was not what this morning's research (or
  Perplexity) implied. **Perplexity reported Thursday's record close as today's** — I checked it
  against broker bars and it is stale; treat that read as unreliable for 08-14. The truth:
  **SPY 777.84 → 776.30 (−0.20%), QQQ 732.11 → 731.05 (−0.15%)**, SPY's entire day spanning
  **0.43%**. A flat, narrow-range, drifting-lower index is the single worst tape for a 1m EMA-ribbon
  trend system. **Zero trades on this day is the system working, not failing.** No change is
  warranted to fix "no trades".
- **Didn't work — and this is the day's real finding: the exit structure cannot hold a trend.**
  AMD was the one clean trend on the board and the bot's own exit logic would have captured
  **0.6 of 6.5 points of it**. That is not a gate problem, it is an exit problem. **A flat 1.00%
  trail on a name with a 7.32% ATR is ~1/7th of a daily range — ordinary noise takes it out.**
  MU (8.16% ATR) is worse. This is the **"flat non-ATR stop"** item that has been open for weeks.
- **Lifetime exit-reason evidence says the same thing, loudly** (266 closed trades, net **+$21.45**):

  | exit_reason | n | total P&L | avg % |
  |---|---|---|---|
  | end-of-day flatten (ran to the close) | **176** | **+$1,125.05** | **+0.38%** |
  | end-of-day flatten (stop/target filled broker-side) | 33 | −$576.14 | −0.95% |
  | stop/target filled broker-side | 46 | −$417.56 | −0.53% |
  | stop filled broker-side (recovered, IMP-003) | 4 | −$55.21 | −1.15% |
  | trailing stop | 2 | −$54.69 | −1.53% |

  **Every stop-based exit path loses money. The only profitable path is being left alone until the
  close.** ⚠️ This must NOT be read as "remove the stops" — it is partly selection (a trade that
  reaches the close without being stopped is by construction one that did not go against you).
  But the asymmetry is far too large to be selection alone, and it points hard at exits being
  cut too tight rather than entries being bad.
- **Verdict on the strategy, stated plainly:** **266 trades for +$21.45 is not an edge.** The
  entry side has been tuned repeatedly (IMP-017 blackout, crossover floor, confidence floor) and
  the curve has not moved. The evidence now says the binding constraint is on the **exit** side.
  Further entry-filter tuning is expected to be wasted effort.

### Lessons & improvement candidates
1. **🔴 IMP-029 (lead candidate) — make the trailing stop ATR-relative instead of a flat percent.**
   Direct evidence today (AMD: 1.00% trail on a 7.32% ATR name exits after 0.63% of a 2.4%
   available move) and lifetime evidence above. **Must be validated on `bot/replay.py` across the
   full history before shipping — not on one day.** The −2% hard stop, position sizing and all
   risk limits stay **untouched**; this changes only how profit is trailed, so max loss per trade
   does not increase.
2. **🟠 Confidence is anti-predictive above 80 and unprofitable below 70.** 60-69: 146 tr, −$58.22.
   **70-79: 87 tr, 54.0% win, +$250.84 — the only profitable band.** 80-89: 30 tr, −$26.75.
   90-100: **3 tr, 0% win, −$144.42 (avg −1.51%)**. The score is non-monotonic and the top of it is
   actively harmful. Note today's gate refusals were conf 76.5 and **91.2** — and all 15 retained
   gate refusals since 08-03 sit at **conf ≥ 69.1**, i.e. the gate is preferentially vetoing the
   one band that makes money. Candidate for IMP-030 after the exit work lands; **do not stack it
   on top of IMP-029 in the same session.**
3. **🟡 The QQQ market gate (IMP-022) blocks idiosyncratic single-name trends.** Real but
   **second-order** — quantified at ≈0.6% today. Revisit only after 1 and 2; on the evidence it
   would not have changed today's P&L materially.

### Notes for pre-market research
- **AMD is the standout and the lesson at once.** Closed **+6.5% at the high ($514.40)** on a flat
  index, produced the day's top two scores (76.5, **91.2**), and was blocked both times by the QQQ
  gate. **Keep it emphatically enabled.** Its 7.32% ATR is a *sizing and exit* question, not a park
  question — do not read the gate blocks as AMD weakness.
- **Zero trades today was correct — do not respond by loosening the watchlist or adding names.**
  The refusal profile was healthy (25 evaluations across 9 distinct symbols).
- **Symbols that produced candidates today (9):** AMD (5), JPM (4), MSFT (4), WMT (3), NFLX (3),
  AAPL, UNH, BABA, TSLA (1 each). **AMD and JPM are the liveliest names on the board.**
- **Silent today (11): AMZN, ABNB, AVGO, GOOG, INTC, MU, NVDA, PLTR, QQQ, SPY, TSM.** ⚠️ Read this
  as a **flat-tape artifact, not symbol death** — on a 0.43%-range SPY day almost nothing crosses.
  In particular **do not park MU or INTC on this session**; both are the board's best performers and
  a single narrow-range Friday is not evidence. Apply the standing 5-session rule before any park.
- **AMZN's park test remains unmet for a sixth run** (it needs to convert a near-miss and lose; it
  produced no candidates today, which does not advance the test either way).
- **BABA reports 08-20 BMO** (confirmed in this morning's log) and **WMT 08-20 BMO** — both due to
  park at the 08-19 run. **NVDA 08-26.** Nothing reports Monday.
- **Book is CLEAN & FLAT into 08-17** — broker-confirmed 0 positions, 0 open orders, equity
  **$9,123.87**, all cash, nothing locked. Service restarted 21:15 UTC on IMP-028, warmup primed
  20/20.

### Change shipped tonight
**IMP-028 — delivered, not authored, tonight.** The 08-14 weekly review found that the 08-13 daily
review had written and validated IMP-028 (`record_entry` retries once on a fresh connection, the fix
for the 08-12 defect that erased a whole session from `dbo.trades`) but **never committed, deployed
or logged it** — the files had sat as uncommitted `root`-owned working-tree modifications since
08-13 21:43 UTC, and `ustradebot.service` had `NRestarts=0` with `ActiveEnterTimestamp` of
**08-13 11:37:48 UTC**, ten hours *before* the edits. **The 08-12 data-loss defect was still live in
production through all of 08-13 and 08-14.** The weekly handed delivery to this run.

Done tonight: `chown ustradebot:ustradebot` on both files → **`pytest -q` 363 passed, exit 0**
(359 → 363; the 6 retry tests pass by name) → **`bot.preflight` all PASS** (1 expected
"market closed" warning) → committed **only** those two files as **`da161c7`** → pushed →
`systemctl restart` → **verified the way this project's memory requires: `ActiveEnterTimestamp`
2026-08-14 **21:15:11** UTC now *postdates* the file mtime of 08-13 21:43:07**, new MainPID 923901,
clean startup, warmup primed 20/20, no errors. **IMP-028 is now actually running.**

**No new change was authored tonight**, by design: shipping a strategy change in the same restart as
a fix that had never once executed would leave neither attributable. IMP-029 (ATR-relative trail) is
specified above with its replay-validation gate and is the next session's work.

⚠️ **Process note for whoever reads this next:** the standing rule is that a routine does not touch
uncommitted changes it did not make. That rule was **deliberately overridden here**, on the weekly's
explicit written handoff and after reading the full diff to confirm it contained IMP-028 and nothing
else. The justification is that this was **this routine's own orphaned output** and a **live
data-integrity defect**, not a human's work in progress. `memory/daily-review.md` also carried an
uncommitted 08-13 entry from the same failed run; it is committed tonight along with this entry.

---

## 2026-08-17 — Daily Review

### Stats
- **2 trades, 0W / 2L → 0% win rate.** Net realized **−$34.66** (avg −$17.33/trade), both losses
  within 0.02pp of each other (−1.177% and −1.192%). Profit factor **0** (no gross win).
- **Equity $9,089.21**, from $9,123.87 → **−$34.66 (−0.38%)**. **Broker reconciles to the cent:**
  Alpaca `last_equity` 9,123.87 → `equity` 9,089.21 is exactly the DB's realized P&L. **0 open
  positions**, 0 open orders, all cash. Both fills match `dbo.trades` to six decimals
  (INTC 104.149444, MU 1021.80); both bracket target legs OCO-cancelled correctly. **No qty drift,
  no missed fill, nothing carried overnight.** IMP-027/IMP-028's machinery behaved.
- Rolling 7 days: **10 trades, 40% win, −$0.13** — flat, not broken.

### Trade-by-trade review
Both Model A, both entered inside two minutes of each other, both exited on the **trailing stop
filled broker-side** ~2 hours later. Neither came close to the −2% hard stop.

- **INTC** — entry 15:20:03 @ **105.39** (qty 18, $1,896.84), conf **63.79**
  (xo 0.30 · trend 1.00 · rsi 1.00 · **vol 0.00** · vlt 0.99). Trail moved 103.27 → **104.15 at
  15:21**, i.e. *one minute after entry*, and then **never moved again for 2h01m** until it filled
  @ 104.1494. **−$22.33 (−1.18%)**.
- **MU** — entry 15:22:02 @ **1034.13** (qty 1), conf **65.53** (xo 0.35 · trend 1.00 · rsi 1.00 ·
  **vol 0.00** · vlt 1.00). Trail 1013.17 → 1021.37 (15:23) → **1021.87 (15:28)**, then flat for
  2h00m until it filled @ 1021.80. **−$12.33 (−1.19%)**.

**Root cause — entry timing, not exit logic, and the IEX daily bars make it unambiguous:**

| | open | high | **our entry** | close | entry vs high |
|---|---|---|---|---|---|
| INTC | 103.69 | **105.95** | **105.39** | 103.47 | **−0.53%** |
| MU | 999.38 | **1036.05** | **1034.13** | 1012.14 | **−0.19%** |

**Both names were bought within 0.6% of their session high, after a run (MU had already travelled
+3.5% off its open), and both closed near their lows.** INTC's day range was **3.94%** on a
**−0.21%** open→close and MU's **4.07%** on **+1.28%** — i.e. both stocks moved enormously and went
nowhere. The ribbon fired at the exhaustion point of the up-leg. That is the whole loss.

**The exit structure was the best-performing component today and should be credited, not blamed.**
Counterfactual against the 15:56 EOD flatten at the closing price: INTC would have been
**−$34.56** (vs −$22.33) and MU **−$21.99** (vs −$12.33) — **the trail saved ≈$21.89**, more than
it cost. MU is the sharp case: the stock finished the day **+1.28% from its open** and our trade
still lost, because we bought its high; the trail got us out at 1021.80 against a **1012.14** close.
- **Not stop placement:** the −2% hard stops (103.27 / 1013.17) were never approached.
- **Not slippage:** INTC filled 0.0006 through its 104.15 stop; MU 0.07 through 1021.87. Negligible.
- **Not sizing:** $1.9k and $1.0k notional on $9.1k equity, well within model A.
- **Not the DB or the broker:** perfect reconciliation, no data defect of any kind today.

**Market regime (IEX daily bars, authoritative — not `sonar`): a narrow, drifting-down tape.**
QQQ **−0.41% open→close on a 0.72% range**; SPY **−0.47% on 0.54%**. So the index trended *down*
intraday all session while individual names chopped 2–4%. The **QQQ market gate (IMP-022) correctly
refused MU twice** earlier (14:14 conf 69.4, 14:30 conf 69.0) and then **opened right at the
intraday top** — the gate is not broken, but a 5-min ribbon is a lagging regime read and on a
0.72%-range day it will confirm bullish near the high by construction. Worth watching, not acting on.

### What worked / what didn't
- ✅ **The trail.** Cut both losers ~40% smaller than an EOD flatten would have. IMP-018/021 continue
  to earn their place.
- ✅ **Risk plumbing.** Exact broker reconciliation, correct OCO cancels, flat into the close.
- ✅ **The refusal log.** 11 documented rejections (crossover < 0.25 on AMD/TSM/QQQ/AAPL/BABA,
  confidence < 60 on BABA ×3 / TSM, gate closed on MU ×2) — the journal is genuinely diagnosable now.
- ❌ **Entry timing.** Both entries bought a local top on a down-drifting index.
- ❌ **`conf_volume = 0.00` on both entries** — the crossover had no volume behind it. *Tempting and
  wrong, see below.*

### Lessons & improvement candidates

**1. `conf_volume` as a discriminator — TESTED TONIGHT AND REFUTED. Do not re-propose it.**
Both losses scored volume 0.00, which looked like an obvious culprit. Across all 268 closed trades
the opposite is true: **`vol = 0.00` is the *best* band (n=51, 43.1% win, +$185.99) and `vol = 1.00`
is the *worst* (n=79, 44.3% win, −$377.93)**; post-08-03 `vol = 0.00` is +$21.37 at 55.6% win.
Volume confirmation is *inverted*, exactly like the confidence total. Today's pairing was coincidence
in a sample of two — the precise overfit this review exists to prevent.

**2. 🔴 The `<0.5%`-MFE cohort is confirmed as the whole leak, and tonight it finally has a
pre-entry discriminator.** Both of today's trades peaked at **+0.09%** and **+0.10%** — dead on
arrival. Over 7 days the bands are stark: **`<0.5%` MFE = 6 trades, −$90.57**; `1.0–2.0%` = 2,
+$5.04; `>2.0%` = 2, **+$85.40**. The dead cohort *is* the loss.

Tonight I ran the study the 08-14 weekly named as its single most important task, on **251 of 268
lifetime trades**, measuring MFE over a **fixed 60-minute forward horizon** so the result is
independent of exit config (and therefore not contaminated by the pre-IMP-021 window):

- **Baseline: 46.6% of all entries never trade +0.5% above entry.** Dead cohort **−$809.05**,
  live cohort **+$935.01**. The bot's entire lifetime P&L is that difference.
- **The discriminator is pre-entry volatility.** Splitting at the median 1-min ATR (0.133% of price):
  quiet tape **57.1% dead / −$265.62**, active tape **36.0% dead / +$391.59**. The same variable in
  three guises — 30-min range width (Δ22.7pp), run-up before entry (Δ22.7pp, **−$760.64 vs +$886.60**,
  the largest P&L spread in the study) and headroom to the 30-min high (Δ21.1pp) — all point the
  same way: **a ribbon cross on a tape that is not moving does not follow through.**
- **Robustness: 4 of 4 independent windows agree** on dead-rate, at a *fixed* threshold with no
  per-window refitting (Jun 58.8/29.7 · Jul 1–20 50.0/48.8 · Jul 21–Aug 2 53.3/21.7 · Aug 3+
  100.0/36.4). That clears the weekly's ≥3-window bar **on direction**.
- **⚠️ Three honest caveats, and they are why nothing was shipped on this tonight.**
  (a) **Net P&L agrees in only 3 of 4 windows** — Jul 1–20 has the quiet side *less* bad
  (−$168.15 vs −$236.87). Dead-rate is robust; profitability is not yet.
  (b) The current-config window has **n=5 on the quiet side**. That is not a sample.
  (c) **Decisively: it would not have saved today.** INTC's pre-entry ATR was **0.204%** and MU's
  **0.158%** — *both above the threshold, both on the "active" side.* Today's losses were bought-the-high
  failures, which this variable does not capture at all.
- **`conf_crossover` also discriminates (Δ24.3pp, the single strongest)** — but `MIN_CROSSOVER` was
  refuted unanimously across four windows on 08-13 and is under freeze. Recorded, not acted on.
- **Entry hour looked strong (Δ21.0pp) but is partly an artifact** — a late entry's 60-minute forward
  window is truncated by the 20:00 UTC close, mechanically depressing its MFE. Restricting to entries
  with a full window the gap narrows on P&L (+$139.38 early vs +$71.06 late). Weak evidence; not actionable.

**3. 🟠 Confidence remains anti-predictive at the top** — 90-100 still **0-for-3, −$144.42**; 70-79
still the only profitable band (+$250.84). Unchanged for a fourth week, still n=3 at the top. Standing.

**4. The pencilled "IMP-029 = ATR-relative trail" from 08-14 did NOT ship tonight, deliberately.**
It is a *trail-structure* change, and the 08-14 weekly explicitly froze `TRAIL_PERCENT` and the
two-stage trail; it was also self-gated on full-history replay validation that has not been run. Its
number has been reassigned to what actually shipped (below). **The candidate is not dead — it is
unblocked**: it needs per-trade ATR to validate, which until tonight was recorded nowhere. Renumber
it to a future IMP and judge it on replay, not on a day.

### Change shipped tonight
**IMP-029 — record the pre-entry tape context (`atr_pct`, `ribbon_spread_pct`) on every entry.**
Instrumentation only, which is what the freeze permits. The bot already computed the 1-min ATR at
entry (it feeds `conf_volatility`) and then **discarded it**; the ribbon spread likewise. Both are
now written to two new nullable `dbo.trades` columns. This is the IMP-025 argument repeated for the
entry side: tonight's study had to re-fetch bars for 251 trades from a throwaway script, and an
analysis that expensive is one that gets skipped on the night it matters. From tomorrow the
`<0.5%`-MFE question is a SQL query, and both open candidates (the ATR entry filter and the
ATR-relative trail) can be validated forward instead of only backward.
**372 tests pass** (363 → 372, +9), non-vacuity verified (4 of the new tests fail when the change is
neutralised, all pass restored), `bot.preflight` **RESULT: OK**. Schema ALTER applied live and
verified: both columns present as `decimal(9,5) NULL`, **all 268 existing rows preserved** and NULL.
Details in `memory/improvement-log.md`.

### Notes for pre-market research
- **INTC and MU are NOT park candidates despite being today's only two losses.** Both moved 4% intraday
  — they are *working* names that the bot mistimed. INTC 3.94% range on −0.21% open→close; MU 4.07%
  on **+1.28%** (MU finished the day up and we still lost, having bought its high). Keep both enabled.
- **Watch the "bought within 0.6% of the session high" pattern** — it is today's real failure and it
  is a *timing* problem, not a symbol-selection one. No watchlist action follows from it.
- **The QQQ gate opened at the intraday top** on a 0.72%-range day, having correctly blocked MU twice
  earlier. Not a defect; a known lag property of a 5-min ribbon on a narrow tape. **Keep QQQ enabled**
  (load-bearing twice over — diversifier and the IMP-022 gate proxy).
- **Never signalled today, worth noting for the board:** AAPL, AMD, TSM, BABA and QQQ all produced
  refusals but no entries; BABA scored below 60 three separate times (48.8, 52.2, 57.9) and cleared
  the confidence bar only once, on a 0.01 crossover. **BABA is drifting toward dead-signal territory
  — start a clock on it** if the pattern repeats this week. Its earnings park is already booked 08-19.
- **Scheduled, unchanged:** WMT + BABA earnings parks and the AAPL re-examination on **08-19** (a
  three-decision run that drops the board to 17; CRM and XOM are the pre-verified backfills), AVGO
  on-notice re-check 08-19, NVDA earnings 08-26, GOOG dead-signal test 08-31.
- **`sonar` was thin for an 11th consecutive run** — "no specific catalyst" for 6 of 8 tickers and no
  regime call beyond "choppy". Its one useful line (range-bound) was confirmed independently by the
  IEX bars. Standing rule holds: lead-generation only, never a regime source.

---

## 2026-08-18 — Daily Review

### Stats
- **0 trades.** No entries, no exits, no open positions. Net P&L **$0.00**. Account
  **equity $9,089.13** (all cash; `last_equity` **$9,089.13** — the day did not move the
  book by a cent). **Broker reconciliation clean:** Alpaca `PA34DFFLTHRT` reports 0 orders
  since 00:00Z, 0 positions, `long_market_value` 0 — and `dbo.trades` has 0 rows for today.
  DB and broker agree exactly; no missed fill, no phantom carry, no qty drift.
- **Service healthy all session:** `active`, zero ERROR/exception/traceback lines in the
  whole day's journal, no restarts, candles flowing from 12:00 UTC through the 20:00 close.
- **The day still produced 33 decisions.** This was not a dead bot; it was a bot that
  looked 33 times and said no 33 times.

### Trade-by-trade review
No trades, so the reviewable evidence is the **refusal set** — root-caused below.

**All 33 scored refusals, by cause:**

| Cause | n | What it means |
|---|---|---|
| `crossover < 0.25` | **18** | Scored candidate, cross too weak (IMP-011 floor) |
| `confidence < 60` | **13** | Scored candidate, total below the entry bar |
| `market gate closed` | **2** | **Fully qualified**, vetoed by the QQQ 5m ribbon (IMP-022) |

**By symbol:** AAPL 7 · BABA 6 · NFLX 6 · ABNB 5 · AMZN 2 · GOOG 2 · MSFT 2 · WMT 2 · JPM 1.
**Ten of nineteen names produced no scored candidate at all:** AMD, AVGO, INTC, MU, NVDA,
PLTR, QQQ, SPY, TSLA, TSM — i.e. the entire semi complex plus both index proxies never even
reached the scorer.

**The regime explains it.** IEX open→close (authoritative): **QQQ −0.35%** on a 0.85% range,
**SPY −0.19%** on a 0.33% range. `sonar` independently had S&P **−0.52%** / Nasdaq **−0.32%**
close-to-close and called the tape *risk-off / choppy, not a clean trend day* — directionally
consistent with the bars. **This morning's research predicted exactly this** ("expect a quiet
session and judge the day on refusals, not on trade count") on a −1.2% Nasdaq-futures,
semi-led open. **The pre-market call was correct and the bot behaved as designed.** A
long-only ribbon bot on a down, rangebound tape *should* produce zero entries. Filing this
as strategy failure would be the error.

### 🔬 The one real study tonight: what does the IMP-022 market gate actually cost?
Today's two gate refusals were **ABNB conf 79.8** (14:25) and **NFLX conf 79.3** (15:09) —
both in the **70-79 band, the only profitable confidence band in the bot's history**
(+$250.84, 54% win, n=87). The tempting story writes itself: *the gate is strangling the one
cohort that pays.* The `strategy.py` comment at the veto explicitly invites this test, so I
ran it rather than believing it.

Method: every gate refusal recoverable from journald (**n=15, 08-07→08-18** — that is the
entire retention window), priced as a hypothetical entry at that minute's close, with MFE/MAE
over a **fixed 60-minute forward horizon** (exit-config independent, the 08-17 methodology)
and the move to the 19:45 UTC flatten.

**Result — the gate is helping, not hurting:**
- **60% of refused candidates were dead on arrival** (MFE < 0.5%) vs the **46.6% baseline for
  trades the bot actually takes**. The refused population is *worse* than the admitted one.
- Mean move to the EOD flatten: **−0.099%**, only **6 of 15 would have been winners (40%)**.
- Mean MFE +0.714%, mean MAE −0.458%; **0 of 15** would have hit the 2% stop inside 60 min.
- **Today's two specifically would both have LOST:** ABNB MFE 0.62% but **−0.41%** to the
  flatten; NFLX MFE 0.05% and **−1.47%** to the flatten. The gate saved money today.

**Verdict: the "gate blocks the profitable band" story is refuted.** Confidence does not
discriminate *within* the refused set either (the 91.2 AMD refusal would have won +1.04%;
today's 79.8/79.3 both lose) — which is the same anti-predictive confidence signal seen for a
fifth week, now visible on the rejected side too. **Do not re-propose loosening the market
gate.** Honest limits: **n=15 is not decision-grade**, it spans 11 days only because that is
all journald keeps, and the effect (−0.099%/trade avoided) is small — the gate is a mild
positive, not a large one.

### What worked / what didn't
**Worked**
- **Capital protection.** A −0.35% QQQ day with no trend cost this book **$0.00**. Not trading
  is a position, and today it was the right one.
- **The refusal ladder behaved sensibly.** Confidence near-misses clustered tightly just under
  the bar (59.9, 59.9, 58.9, 58.1, 57.5, 57.4, 56.7, 56.6, 56.4) rather than scattering — the
  scorer is discriminating, not thrashing.
- **The market gate earned its keep**, measurably, for the first time (above).
- **Pre-market research called the day correctly**, and told me in advance how to judge it.

**Didn't**
- **A full trading day generated zero persisted evidence.** 33 decisions, 0 rows in SQL. This
  is the day's actual defect and it is what I fixed (below).
- **IMP-029 remains unvalidated** — it records tape context on entry, and there have been no
  entries since it shipped 08-17. `atr_pct IS NOT NULL` still returns **0 rows**. Not a
  failure, just not yet observable. Carry forward.
- **`sonar` thin for a 12th consecutive run:** "no specific catalyst" for **12 of 12** tickers.
  Its index-level read was usable and verified against IEX; its ticker layer was worthless
  again. Standing rule unchanged: lead-generation only, never a regime source.

### Lessons & improvement candidates

**1. 🔴 A flat session must stop being an invisible session — SHIPPED TONIGHT as IMP-030.**
Flat sessions are no longer exceptional (08-14 zero, 08-18 zero, and more forecast), yet they
wrote nothing to the database. Worse, tonight's gate study — the single most useful piece of
analysis this review has produced in a week — **could only reach n=15 because journald rolls.**
Every entry-threshold study to date has been run on the *taken* population alone, and a
threshold cannot be priced from the trades it admits; only from the candidates it rejects.
Those candidates were being thrown away. Fixed: see below.

**2. 🟠 The crossover floor killed three 70+ confidence candidates today. RECORDED, NOT ACTED
ON.** AAPL 70.6 (xo 0.14), ABNB 70.1 (xo 0.12), BABA 72.2 (xo 0.10) all cleared the confidence
bar and died on `MIN_CROSSOVER = 0.25`. Combined with the two gate refusals, **all five of
today's candidates in the profitable 70-79 band were refused.** This looks actionable and is
not: `MIN_CROSSOVER` was **refuted unanimously across four windows on 08-13** and is under the
08-14 shipping freeze. n=3 on a single flat day is precisely the overfit this review exists to
prevent. From tomorrow IMP-030 makes this answerable properly — with outcomes attached.

**3. 🟠 Confidence still anti-predictive, now on the rejected side too.** 90-100 remains
**0-for-3, −$144.42**; 70-79 the only profitable band. The gate study adds a new datapoint:
within refused candidates, confidence also failed to rank outcomes. Fifth consecutive week.
Standing, still n=3 at the top, still do not act.

**4. The strategy's core premise is untested this week, not refuted.** All-time **268 trades,
−$13.22**; post-08-03 current config **27 trades, +$135.47**. Two of the last four sessions
traded zero times. The honest statement is that the bot **has not had enough recent entries to
either confirm or refute an edge** — which is itself the argument for IMP-030, since refusals
are the only growing evidence stream the bot currently has and it was discarding them.

### Change shipped tonight
**IMP-030 — persist refused entry candidates to `dbo.entry_refusals`.** Instrumentation only,
which is what the 08-14 shipping freeze on trading logic permits: nothing reads the table back
and no entry, exit or sizing decision changes. Scored candidates only (the ~10k unscored "no
fresh cross" rejections a session stay DEBUG-only), ~30 rows a session, carrying the same
confidence breakdown and IMP-029 tape context an entry records — plus `market_gate_open`, so
tonight's n=15 gate study becomes a SQL query that reaches n≈100 by mid-September instead of
being re-derived from a rolling log. **388 tests pass** (372 → 388, +16), including an
end-to-end test through the strategy→recorder seam; non-vacuity verified (neutralising the
change fails 6 tests). `bot.preflight` **RESULT: OK**, schema **10 → 12 batches**, table and
index verified live, **268 existing trades preserved**. Details in `memory/improvement-log.md`.

### Notes for pre-market research
- **Nothing about today justifies a watchlist edit.** Zero entries on a −0.35% QQQ day is the
  gate and the ribbon working, not symbols failing. Resist the urge to churn the board after
  a flat session.
- **Ten names never produced a scored candidate:** AMD, AVGO, INTC, MU, NVDA, PLTR, QQQ, SPY,
  TSLA, TSM. **This is regime, not deadness** — it is the semi complex on a semi-led selloff
  day, exactly the read-across this morning's research flagged (WDC/SanDisk/Seagate → MU).
  **Do not start dead-signal clocks on any of them from today's evidence.**
- **BABA: second consecutive day of refusals with no entry** (6 today — four on confidence
  56.4-59.9, two on crossover). Yesterday's note started a clock on it. **The clock is moot:
  BABA is scheduled to be parked tomorrow for earnings (confirmed Thu 08-20 BMO)** — park it
  as planned and re-judge it after earnings, not on this.
- **AAPL was today's most active refuser (7)** and never once cleared both bars; its scores
  ran 57.4-70.6 with crossovers 0.04-0.21. **AAPL's re-examination is already booked for
  08-19** — this is useful input to it, but note the same regime caveat.
- **PLTR is 6 days old with 0 trades and 0 scored candidates.** Still needs a fair window; do
  not judge it yet, but it is now worth watching whether it ever reaches the scorer.
- **Scheduled tomorrow (08-19), unchanged:** WMT + BABA earnings parks, AAPL re-examination,
  AVGO on-notice re-check — a three-to-four-decision run dropping the board to ~17. **CRM and
  ANET remain the pre-verified backfills.** Later: NVDA earnings 08-26, GOOG dead-signal test
  08-31, SPY review end-August.
- **New capability for tomorrow morning:** `dbo.entry_refusals` starts filling from the next
  session. From now on "which of my symbols are actually reaching the scorer, and how close do
  they get?" is a SQL query against real rows, not a journald grep with 11 days of memory.

---

## 2026-08-19 — Daily Review

### Stats
- **0 trades.** No entries, no exits, no open positions. Net P&L **$0.00**. Account **equity
  $9,089.13**, `last_equity` **$9,089.13** — a second consecutive session that did not move the
  book by a cent. **Broker reconciliation clean:** Alpaca `PA34DFFLTHRT` returns **0 orders**
  since 00:00Z, **0 positions**, `long_market_value` 0; `dbo.trades` has 0 rows and
  `dbo.positions` 0 rows for today. DB and broker agree exactly.
- **Service healthy all session:** `active`, `NRestarts=0`, **zero WARN or ERROR lines in the
  entire day's journal** (9,231 lines), no restarts. Running since the IMP-030 deploy
  (`ActiveEnterTimestamp` 2026-08-18 20:12:17 UTC), so today traded under HEAD.
- **IMP-030 is VALIDATED on its first live session: 26 rows in `dbo.entry_refusals`**, each
  carrying the full confidence breakdown and the IMP-029 tape context (`atr_pct` populated on
  all 26). This is the first day in the bot's history where a flat session produced persisted,
  queryable evidence. **IMP-029 remains unvalidated** on the entry side — `dbo.trades.atr_pct`
  is still 0 rows, because there have still been no entries.

### Trade-by-trade review
No trades, so the reviewable population is the **26 scored refusals** — and for the first time
they are rows, not a journald grep.

| Cause | n | Notes |
|---|---|---|
| `crossover < 0.25` | **17** | The dominant filter, as on 08-18 |
| `confidence < 60` | **5** | 49.8, 54.1, 55.0, 56.0, 56.9 |
| market gate closed | **4** | Fully qualified, vetoed by the QQQ 5m ribbon (IMP-022) |

**By symbol:** PLTR 5 · TSLA 5 · WMT 4 · NFLX 4 · BABA 2 · GOOG 2 · AAPL 1 · AMZN 1 · MSFT 1 ·
SPY 1. **Nine of nineteen enabled names never reached the scorer:** ABNB, AMD, AVGO, INTC, JPM,
MU, NVDA, QQQ, TSM.

**The regime explains the day, but not in the way `sonar` said.** IEX open→close, which is the
only window this bot trades: **QQQ −0.61% on a 1.21% range**, **SPY −0.16% on a 0.56% range**.
The tape **gapped up and faded all session**. `sonar` reported S&P **+0.39/+0.50%** and Nasdaq
**+0.28/+0.41%** and called it "choppy-to-risk-on" — those are **close-to-close** figures, and
close-to-close had the **opposite sign** to the session the bot actually trades. Recorded as a
concrete instance of why the standing rule exists.

### 🔬 The study: what did today's 26 refusals actually cost?
This is the analysis IMP-030 was built for, and it ran as a SQL query plus one bar fetch instead
of a throwaway script against a rolling log. Every refusal priced as a hypothetical entry at that
minute's close, MFE/MAE over a **fixed 60-minute forward horizon** (exit-config independent — the
08-17 methodology), plus the move to the 19:45 UTC flatten.

| Cohort | n | mean MFE | mean MAE | mean → flatten | dead (MFE<0.5%) | would-be winners |
|---|---|---|---|---|---|---|
| **crossover floor** | 17 | +0.284% | −0.441% | **−0.508%** | **13/17 (76%)** | 5/17 (29%) |
| confidence bar | 5 | +0.549% | −0.109% | −0.062% | 2/5 (40%) | 2/5 (40%) |
| market gate | 4 | +1.069% | −0.528% | +0.041% | 2/4 (50%) | 2/4 (50%) |
| **ALL** | **26** | **+0.456%** | **−0.390%** | **−0.338%** | **17/26 (65%)** | 9/26 (35%) |

**Refusing all 26 saved money. The single best filter today was the one this review keeps being
tempted to loosen.** The crossover floor refused the *worst* cohort of the three by every
measure: 76% dead on arrival against the **46.6% baseline for trades the bot actually takes**,
and −0.508% average to the flatten. This is now the **third independent refutation** of the
"the floor is strangling good candidates" story (unanimous across four replay windows on 08-13;
the gate half refuted 08-18; the floor itself refuted on live rows today).

**And it refutes it precisely where it looked most convincing.** The three highest-confidence
crossover refusals were **AAPL 75.5 (xo 0.20)**, **AMZN 74.6 (xo 0.15)** and **BABA 71.7
(xo 0.10)** — all in the 70-79 band, the only historically profitable one. They went **−0.45%,
+0.20%, −0.85%** to the flatten. **Confidence again failed to rank outcomes inside the refused
set** (best: TSLA 66.6 at +2.60%; worst: WMT 66.4 at −2.01% — same confidence, 4.6 points apart).
**Sixth consecutive week of anti-predictive confidence.**

**Honest limits:** n=26, one session, one regime (a fading tape, which flatters every long
filter). The gate cohort's +1.069% mean MFE is **one trade** — TSLA 14:16, +2.60%; drop it and
the other three average **−0.81%** to the flatten. Nothing here is decision-grade on its own.
The point is that it now *accumulates*: this is day 1 of a series that reaches n≈100 by
mid-September, instead of being re-derived from scratch every Friday.

### 🔎 Structural finding: two of the five confidence components are near-constants
Today's rows made this visible at a glance — `conf_rsi = 1.0000` on **26 of 26** refusals — and
the full history confirms it is not a one-day artifact:

- **`conf_rsi == 1.0` on 252 of 268 trades (94%)**, and on 26/26 refusals. `score_rsi` returns
  a flat **1.0 for the entire 45-65 RSI band**, which is where a fresh bullish EMA cross almost
  always sits. It is doing what it was written to do; the consequence is that it carries **no
  information at the moment it is consulted.**
- **`conf_volatility == 1.0` on 174 of 268 (65%)**, full observed range only **[0.574, 1.0]**.
- Weights are crossover 30 / trend 20 / **rsi 20** / volume 15 / **volatility 15**.

**So ~35 of the 100 confidence points are a near-constant floor, and the "60/100" entry bar is
really ~25 of a variable 65** — i.e. the discriminating signal is crossover + trend + volume,
with RSI contributing a flat +20 to essentially every candidate. This is a strong candidate
explanation for *why* confidence has been anti-predictive for six weeks: a third of the score is
a constant, which compresses the spread between good and bad candidates rather than widening it.
**NOT ACTED ON — the 08-14 weekly explicitly froze the confidence weights**, and this deserves
replay validation across windows, not a one-night edit. **Handed to Friday's weekly as the
single best-evidenced strategy question currently open.**

### ⚠️ Operational defect: the pre-market routine failed and the watchlist is stale
**`ustradebot-premarket` crashed at 11:30 UTC today — `claude exited rc=1` after 26 seconds**,
producing no research-log entry (the newest is still 08-18) and making **no watchlist changes**.
`uswisbot-premarket` failed identically at 11:45 (rc=1, 9s), so this is shared-harness, not
prompt-specific. It is **outside `/opt/ustradebot`** (`/root/claude-routines`) and therefore
outside tonight's one-change scope, but it has a direct capital consequence:

- **WMT and BABA were scheduled to be parked today for earnings (both confirmed Thu 08-20 BMO)
  and were NOT parked.** Both are still enabled, and both were live candidates today — **WMT
  produced 4 refusals and BABA 2**, one of them at confidence 71.7. Tomorrow the bot may trade
  both **into and out of an earnings print** with no earnings guard of its own.
- The AAPL re-examination and the AVGO on-notice re-check also did not happen.
- **`run-routine.sh` discards the failure reason** — the run log keeps only
  `ERROR: claude exited rc=1`, no stderr — so the root cause is not recoverable after the fact.
  That is the fix worth making, and it belongs to the routines harness.

**The bot's only earnings protection is a routine that failed silently.** Flagged loudly for
tomorrow morning and for Friday.

### What worked / what didn't
**Worked**
- **Capital protection, correctly, for a second day.** A −0.61% intraday QQQ cost this book
  $0.00, and tonight I can *prove* the 26 things it declined would have averaged −0.338%.
- **IMP-030 paid off one day after shipping** — the study above took a SQL query, not a script.
- **The crossover floor and the confidence bar both earned their keep**, measurably.
- Service ran a clean 9,231-line session with zero warnings.

**Didn't**
- **`sonar` thin for a 13th consecutive run** — "no specific catalyst" for **9 of 9** tickers,
  and its index read had the wrong sign for the open→close window. Lead-generation only.
- **The pre-market routine failed and nobody noticed until now** (above).
- **Still no entries, so IMP-029 stays unvalidated** for a third session.
- **Three of the last four sessions have traded zero times** (08-14, 08-18, 08-19). Two of them
  are now *demonstrably* correct restraint rather than assumed restraint — but the sample of
  live entries needed to judge the strategy's edge is not growing.

### Lessons & improvement candidates

**1. 🔴 The gate state must travel with every refusal, not just gate refusals — SHIPPED as
IMP-031.** Today's study has a hole I could not close: for the 17 crossover refusals I do not
know whether the tape was open. The gate was independently observed **shut at 14:13, 14:16,
15:47 and 16:15**, so some unknown share of those 17 were never recoverable at any floor
setting. **Loosening a threshold does not admit a candidate — it advances that candidate to the
gate.** Pricing the floor without the gate state systematically overstates what loosening it
would recover, and Friday's weekly is due to run exactly that study. Fixed tonight.

**2. 🟠 The RSI component is a constant (above).** Best-evidenced open strategy question; frozen
until Friday; needs replay across ≥3 windows, not a one-day edit.

**3. 🟠 The crossover floor is now refuted three independent ways. Stop proposing it.** Adding
this to the standing do-not-relitigate list alongside `STOP_LOSS` and `MARKET_FILTER_SYMBOL`.

**4. The strategy's edge remains untested, not refuted.** All-time **268 trades, −$13.22**;
post-08-03 current config **27 trades, +$135.47**. The honest statement is unchanged from
08-18 and now has a second flat session behind it: **there are not enough recent entries to
confirm or refute an edge.** What *has* improved is that the bot's restraint is now
evidence-backed rather than merely plausible.

### Change shipped tonight
**IMP-031 — record the market-gate state on every scored refusal, not only on gate refusals.**
Instrumentation only, which is what the 08-14 freeze permits. One line of behaviour
(`gate_open=None` → `gate_open=self._market_gate_open()`) plus the semantics documented on
`RefusedEntry`. `_market_gate_open()` is a pure cached-snapshot read, called on the ~26 scored
candidates a session rather than the ~10k unscored ones, and **no entry, exit or sizing decision
changes** — a test pins that a near-miss behaves identically on an open and a shut tape.
**391 tests pass** (388 → 391, +3), non-vacuity verified (neutralising the change fails 3 tests,
all pass restored), `bot.preflight` **RESULT: OK**. Details in `memory/improvement-log.md`.

### Notes for pre-market research
- **🔴 ACT FIRST: WMT and BABA are still enabled and both report earnings tomorrow (Thu 08-20
  BMO).** Today's pre-market routine crashed before it could park them. **Park both**, and treat
  this as the highest-priority item of the morning — it is the one item with real money attached.
- **Also missed by the crashed run and still owed:** the **AAPL re-examination** and the **AVGO
  on-notice re-check**, both scheduled for 08-19. **CRM and ANET remain the pre-verified
  backfills.** Board is still at 19 enabled / 28 rows; the drop to ~17 has not happened.
- **No watchlist edit is justified by today's *trading* evidence.** Zero entries on a −0.61%
  intraday QQQ is the gate and the floor working — and tonight's study shows the 26 declined
  candidates averaged −0.338%. **Do not churn the board after a flat session.**
- **NFLX is the interesting name and not for the obvious reason.** It closed **+2.58%
  open→close** ($78.21 → $80.23) — the day's best mover among names the bot looked at — yet all
  **four** NFLX candidates were scored at **$80.30-$80.67, every one of them at or above the
  day's close.** The entire move happened before the bot's 10:00 ET entry window opened. Not a
  defect (IMP-017's opening blackout was validated on 219 trades) and **not a reason to touch
  `ENTRY_START`** — but worth knowing that NFLX does its work early.
- **PLTR is now the most active name on the board** (5 candidates, top confidence 77.2, the
  highest of any refusal today) after 7 days with zero trades. It is reaching the scorer
  regularly and getting close. **Keep it; the fair-window question is answered — it is alive.**
- **The nine names that never reached the scorer** — ABNB, AMD, AVGO, INTC, JPM, MU, NVDA, QQQ,
  TSM — are again mostly the semi complex on a faded tape. **This is the second consecutive day
  for AMD/AVGO/INTC/MU/NVDA/TSM.** Not yet a dead-signal case, but if it is a third and fourth
  day on a *rising* tape, it becomes one. Note it; do not act yet.
- **Scheduled/outstanding:** NVDA earnings **08-26**, GOOG dead-signal test **08-31**, SPY review
  end-August. UNH and XOM re-enables stay condition-gated.
- **Harness note for whoever reads this:** if the pre-market run fails again, the log will still
  not say why. Fixing `run-routine.sh` to capture stderr is a `/root/claude-routines` task, not
  a bot task, and it is worth doing before the next earnings park is missed.

---

## 2026-08-20 — Daily Review

### Stats
- **0 trades.** No entries, no exits, no open positions. Net P&L **$0.00**. Account **equity
  $9,089.13**, `last_equity` **$9,089.13** — a **third consecutive session** that did not move
  the book by a cent. **Broker reconciliation exact:** Alpaca `PA34DFFLTHRT` returns **0 orders**
  since 00:00Z, **0 positions**, `long_market_value` 0; `dbo.trades` has 0 rows and
  `dbo.positions` 0 rows for today. DB and broker agree.
- **Service healthy all session:** `active`, `NRestarts=0`, **zero WARN or ERROR lines** in the
  day's 8,702-line journal. Restarted 11:39:01 UTC by the pre-market routine (watchlist changed:
  WMT + AVGO parked, LLY added), warmup primed **18/18**, so today traded under HEAD (IMP-031).
- **27 scored refusals persisted** to `dbo.entry_refusals` — second full session of the IMP-030
  evidence stream, now at **53 rows** across two days.
- **IMP-029 remains unvalidated** for a fourth session — `dbo.trades.atr_pct` is still 0 of 268
  rows, because there have still been no entries. Not a failure; not yet observable.

### Trade-by-trade review
No trades. The reviewable population is the **27 scored refusals**, and today they say something
none of the previous flat sessions could.

| Cause | n | Notes |
|---|---|---|
| market gate closed | **8** | Fully qualified on confidence *and* crossover; vetoed by the QQQ 5m ribbon |
| `crossover < 0.25` | **9** | |
| `confidence < 60` | **10** | 49.6 … 58.8 |

**By symbol:** BABA 10 · MU 5 · TSM 4 · NFLX 3 · PLTR 2 · INTC 2 · AAPL 1. **Eleven of eighteen
enabled names never reached the scorer:** ABNB, AMD, AMZN, GOOG, JPM, LLY, MSFT, NVDA, QQQ, SPY,
TSLA.

### 🔴 The finding: `market_gate_open` was FALSE on all 27 rows, and the gate was shut all day
IMP-031 shipped last night to put the gate state on *every* scored refusal, not just gate
refusals. One session later it has produced the most consequential measurement this review has
made in weeks — and it is not the one it was built to make.

**Every one of today's 27 refusals happened on a shut tape.** Not the 8 labelled "market gate
closed" — all 27. I then rebuilt QQQ's 5m gate ribbon through the bot's own `RibbonEngine.gate`
over 24 sessions of IEX bars, scored inside the 14:00–19:45 UTC entry window:

| | |
|---|---|
| **2026-08-20 (today)** | **0 of 69 bars open — 0.0%** |
| 08-19 | 5/69 — 7.2% |
| 08-18 | 0/69 — 0.0% |
| 24-session duty cycle | **509/1610 — 31.6%** |

**The three-session drought is explained, and it is not the entry filters.** It is the market
gate. On 08-18 and 08-20 a long was *structurally impossible* — there was no minute of the entry
window in which the bot was permitted to open one, regardless of what any symbol did.

**And the distribution is bimodal, not centred.** Of 24 sessions: **13 were ≤10% open** (near-
totally shut) and **7 were ≥60%** (near-totally open). The gate is close to a binary
session-level switch, not a filter that trims candidates within a day. That is a materially
different object from the one the improvement log has been reasoning about.

### 🔎 What this does to the 08-14 weekly's headline gate metric
The 08-14 weekly retired the gate's tripwire on the finding that **"the gate accounted for 7 of
141 refusals (5.0%) — the tripwire is >80% and it is nowhere near it."** Today shows that metric
**cannot measure what it was being asked to measure**, and the error is structural, not a bad
sample:

- Gate-labelled refusals only fire for candidates that already cleared confidence **and**
  crossover. A candidate that fails either one is attributed to *that* filter and never counted
  against the gate — even though the gate would have refused it too.
- Today the gate was open **0.0%** of the entry window, and the refusal-share metric reported
  **8/27 = 30%**. On a day of maximum possible restrictiveness the metric reads 30%, not 100%.
  Its ceiling is set by how many candidates survive the other two filters, so it can never
  approach the >80% tripwire it was being compared against.

**This does not overturn the gate's four-window profitability evidence** (5d, 10d, 60d replay
plus 08-13 live), which is measured on P&L and stands untouched. It overturns the claim that the
gate is *not very restrictive*. Those are different claims and the weekly conflated them. **The
gate is both highly restrictive (68% of the tape excluded) and, on the evidence to date,
profitable.** Both can be true — the bot makes money by declining to be long.

### 🔬 What did today's 27 refusals actually cost?
Each priced as a hypothetical entry at that minute's close; MFE/MAE over a fixed **60-minute**
forward horizon (exit-config independent, the 08-17 methodology), plus the move to the 19:45 UTC
flatten. Bars from the same IEX feed the bot trades.

| Cohort | n | mean MFE | mean MAE | mean → flatten | dead (MFE<0.5%) | flatten>0 |
|---|---|---|---|---|---|---|
| **market gate** | **8** | +0.476% | −0.619% | **+0.219%** | 6/8 (75%) | 4/8 |
| crossover floor | 9 | +0.269% | −0.434% | +0.136% | 8/9 (89%) | 5/9 |
| confidence bar | 10 | +0.489% | −0.362% | −0.113% | 6/10 (60%) | 4/10 |
| **ALL** | **27** | **+0.412%** | **−0.462%** | **+0.068%** | **20/27 (74%)** | 13/27 |

**Verdict: today's restraint was roughly free, not costly.** +0.068% mean to the flatten across
all 27, with **74% dead on arrival** (vs the 46.6% baseline for trades the bot actually takes).
The gate cohort is the *best* of the three at +0.219% — but 6 of its 8 never traded 0.5% above
entry, and against a 1.25% trailing stop a +0.476% mean MFE is not a population that converts.

**The one that stings, honestly stated:** **MU 14:20, confidence 89.1, crossover sub-score
0.777** — the single strongest candidate the scorer has produced in weeks — ran **+1.251% MFE
and +1.562% to the flatten**. It was refused by the gate alone. Two things stop that from being
an argument: it is **n=1**, and the **90-100 confidence band is 0-for-3 lifetime at −$144.42**,
so the bot's own record says its highest-confidence signals are its worst. Recorded, not acted on.

**Honest limits:** n=27, one session, one regime. A fading tape flatters every long filter, and
today's QQQ fell intraday. Nothing here is decision-grade alone — the point is that it now
*accumulates*.

### Market context — and `sonar` had the ticker layer wrong again
IEX open→close, the only window this bot trades: **QQQ −0.16% on a 0.88% range**, **SPY −0.42%
on a 0.79% range**. A shallow, choppy drift lower — not the "risk-off" `sonar` reported (it gave
S&P ≈−0.3%, Nasdaq ≈−0.7/−0.8%, close-to-close). Its per-ticker layer returned **"no specific
same-day catalyst" for 7 of 8 tickers** — a **14th consecutive thin run** — and the one call it
did make was **wrong**: it said **MU "fell with the broader semiconductor selloff."** The bot's
own tape has MU at **952.18 at 14:20 → 964.07 at 19:22, +1.25% intraday**, and MU produced the
day's single best refused candidate. **Standing rule reaffirmed: lead-generation only, never a
regime source, never a price.**

### What worked / what didn't
**Worked**
- **IMP-031 paid off one day after shipping**, and not in the way it was designed to. It was
  built to close a hole in the crossover study; what it actually revealed is that the gate is a
  near-binary session switch and that the weekly's headline gate metric is structurally biased.
- **Capital protection, for a third session.** A −0.16% QQQ cost this book $0.00, and I can
  *prove* the 27 declined candidates averaged +0.068% — i.e. nothing was left on the table.
- **The crossover floor again refused the worst cohort** (89% dead). Fourth independent
  refutation of the "the floor is strangling good candidates" story. Stop proposing it.
- Clean 8,702-line session, zero warnings, exact broker reconciliation, warmup 18/18.

**Didn't**
- **Three consecutive zero-trade sessions**, and the live-entry sample the strategy verdict needs
  is not growing. The bot has taken **0 entries since 08-17**.
- **IMP-029 unvalidated for a fourth session** — nothing to validate it on.
- **`sonar` wrong on MU's direction** (above).
- **The bot cannot currently answer "how often is my gate open?" from its own data.** Tonight's
  duty cycle came from a reconstruction against Alpaca's *aggregated* bars, which are a different
  series from the bot's tick-built candles (activity-driven closes — see CLAUDE.md). That gap is
  what I fixed.

### Lessons & improvement candidates

**1. 🔴 The gate's duty cycle must be measured from the bot's own ribbon — SHIPPED as IMP-032.**
Every gate study to date has had a numerator (refusals) and no denominator. Tonight's headline
number is a *proxy* built from Alpaca's 5m bars; the bot's own gate is only observable at the ~30
scored-candidate moments a session. Friday's weekly is due to rule on the gate and on the
confidence weights, and it should not have to rule on a reconstruction. Fixed: see below.

**2. 🟠 The 08-14 weekly's "gate = 5% of refusals" metric is structurally biased and should be
retired as a restrictiveness measure.** Not because it was computed wrongly, but because its
ceiling is set by the other two filters. **Duty cycle replaces it.** Handed to Friday's weekly —
this is now the second best-evidenced open question alongside the RSI-constant finding.

**3. 🟠 The RSI component is a near-constant (`conf_rsi == 1.0` on 94% of trades, 26/26 refusals
on 08-19).** Unchanged from last night, still frozen, still the best-evidenced *signal* question.
Today's rows agree: `conf_volatility == 1.0` on 21 of 27 refusals.

**4. The strategy's edge remains untested, not refuted — and the reason is now named.** All-time
**268 trades, −$13.22**; post-08-03 config **27 trades, +$135.47**. The sample is not growing
because **the gate has been shut 68% of the last month and ~100% of the last three sessions.**
That is the honest mechanism behind "not enough recent entries," and it is a fact about the gate,
not about the signal.

### Change shipped tonight
**IMP-032 — persist the market gate's state on every closed gate candle (`dbo.market_gate`).**
Instrumentation only, which is what the 08-14 freeze permits: no entry, exit or sizing decision
changes, and a test pins that the same candles produce an identical entry decision with and
without the sink. ~78 rows a session for `MARKET_FILTER_SYMBOL` only, carrying `gate_open` plus
its two conjuncts (`stacked`, `fast_rising`) so a shut gate can be attributed to ordering or to
slope. **The trap this had to avoid:** warmup replays ~5 days of history through the same
`on_long_candle` sink at every restart, which would have backfilled hundreds of never-live rows
into the one table whose rows are *counted* — so warmup now uses a non-emitting `warmup_gate`,
mirroring the existing `warmup_trigger`, and the write is guarded by a unique
`(symbol, candle_start_utc)` index. **407 tests pass** (391 → 407, +16); non-vacuity verified
twice (disabling the emit fails 6 tests, letting warmup backfill fails the orchestrator test).
`bot.preflight` **RESULT: OK**, schema **12 → 14 batches**, table + unique index verified live,
**268 trades and 53 refusals preserved**. Details in `memory/improvement-log.md`.

### Notes for pre-market research
- **🔴 Read this before judging any symbol on "it never signalled."** The market gate was open
  **0.0% of today's entry window** and 7.2% on 08-19. **No symbol could have traded today**, so
  today's silence carries **zero information about any individual name.** Do not start or advance
  a dead-signal clock on anything from today's evidence, and do not park a name for being quiet.
  This applies to all eleven names that never reached the scorer: ABNB, AMD, AMZN, GOOG, JPM,
  LLY, MSFT, NVDA, QQQ, SPY, TSLA.
- **BABA was the most active name on the board by a wide margin (10 of 27 refusals)** on its
  post-earnings day, scoring 56.6–81.9. Yesterday's decision to keep it while parking WMT looks
  right on today's tape: BABA ran **128.03 → 130.13 (+1.6%) intraday** and produced a fully
  qualified 81.9 candidate. **Its dead-signal clock (due 09-09) should be considered paused, not
  running, for 08-18/19/20** — three shut-gate sessions are not a fair window.
- **MU is the name to watch tomorrow.** It produced today's best candidate (**conf 89.1, xo
  0.777, +1.56% to the flatten**) and three of the eight gate-blocked ones, and ran +1.25%
  intraday on a day `sonar` claimed it fell. It is reaching the scorer with real conviction.
  **Keep it; nothing to change.**
- **LLY, added this morning, produced zero scored candidates** — expected on a shut-gate day and
  on its first session. **No inference available yet; give it a fair window.**
- **The semi complex reached the scorer today** (MU 5, TSM 4, INTC 2) after two days of silence,
  which further supports reading 08-18/08-19's quiet as regime rather than deadness — as that
  night's note argued.
- **Scheduled/outstanding, unchanged:** NVDA earnings **08-26** · CRM add re-dated to after
  **08-26** (post-print) · AAPL 30-day dead-signal test **08-27** · INTC on-notice re-check
  **08-27** · GOOG dead-signal test **08-31** · SPY volatility review end-August · BABA
  **09-09**. AVGO, UNH and XOM re-enables stay condition-gated.
- **New capability from tomorrow:** `dbo.market_gate` fills from the next session, so
  "was the tape even open for business today?" becomes a one-line SQL query instead of a
  reconstruction. Pair it with `dbo.entry_refusals` before drawing any conclusion about a
  symbol's silence.
- **Harness note, still owed and now three days old:** `run-routine.sh` discards stderr, so the
  08-19 pre-market crash remains unexplained. `/root/claude-routines` task, outside this repo.

---

## 2026-08-21 — Daily Review

### Stats
- **Closed trades: 0.** No entries, no exits, no open positions. Net realized P&L **$0.00**.
- **Account equity $9,089.13**, `last_equity` **$9,089.13** — an exactly flat day at the broker.
- **Broker reconciliation: clean.** Alpaca `PA34DFFLTHRT` reports **0 orders** submitted since
  2026-08-21T00:00Z and **0 open positions**; `dbo.trades` agrees on both. No missed fill, no qty
  drift, nothing carried overnight. DB and broker are in exact agreement, which on a zero-trade day
  is the whole check.
- **Service healthy.** `active`, **`NRestarts=0`**, up continuously since **11:38:43 UTC** (the
  pre-market restart — so the watchlist edit *did* load, the ops item the 08-14 weekly flagged).
  8,638 journal lines today and **zero WARNING-or-above entries**.
- **Scored candidates: 23**, all refused. Cohorts: **crossover 12 · confidence 8 · gate 3**.

### Why there were no trades — the tape first
**Verified from IEX daily bars, not from `sonar`** (see the Perplexity note below):

| | prev close | open | close | day-over-day | **open→close** | range |
|---|---|---|---|---|---|---|
| QQQ | 710.93 | 715.265 | 713.41 | **+0.35%** | **−0.26%** | 709.29–715.65 = **0.89%** |
| SPY | 762.62 | 765.99 | 765.64 | **+0.40%** | **−0.05%** | 764.185–767.84 = **0.48%** |

The market **gapped up overnight and then went nowhere for six and a half hours.** A 0.89% QQQ range
is a narrow tape. This is precisely the regime the 08-14 weekly named as the one this bot structurally
cannot monetise — *"the index gains came from gaps and overnight drift, not from intraday trend, which
is the one thing this bot cannot monetise (it never holds overnight)."* Today the index closed green
and the bot could not have participated, because all of the gain happened while it was flat by design.

**The gate was not the binding constraint.** IMP-032's telemetry, in its first full session, records
**34 of 69 entry-window bars open = 49.3% duty cycle** (47.1% across all 87 bars). The bot was
*permitted* to be long for half the session and still found nothing worth buying. That kills the
lazy explanation ("the gate was shut again") outright.

The binding constraint was **signal strength**, and it was absent because the ribbon never separated:
recorded `ribbon_spread_pct` was **0.00058% (UBER), 0.00116% (QQQ), 0.00186% (TSM), 0.00604% (GOOG)**.
Crossover strength is ribbon width × slope; on a 0.89%-range tape there is no width to have. Twelve
candidates died at **crossover 0.02–0.20 against the 0.25 floor**. That is not a broken filter, it is
a filter reading a flat tape correctly.

### Trade-by-trade review → refusal-by-refusal review
No trades, so the reviewable population is the 23 refusals. **Newly measurable tonight** (IMP-033):
each declined candidate scored against its own forward tape — enter at the refusal candle's close,
flatten with the session, IEX bars, `bot.report --refusals`.

```
cohort        n   avgMFE   avgMAE   avgFwd  <0.5%MFE  hitTrail  stopped
crossover    12   +0.36%   -0.53%   -0.06%    8/12      0/12     0/12
confidence    8   +0.11%   -0.61%   -0.35%    8/8       0/8      0/8
gate          3   +1.67%   -0.70%   +0.75%    1/3       2/3      0/3
ALL          23   +0.45%   -0.58%   -0.05%   17/23      2/23     0/23
```

Ranked, worst-to-best declined (conf · MFE · MAE · forward-to-flatten · ribbon spread):

| sym | cohort | conf | MFE | MAE | fwd | gate | spread |
|---|---|---|---|---|---|---|---|
| PLTR | gate | 69.9 | **+2.62%** | −0.23% | +1.08% | shut | **0.11215** |
| TSLA | gate | 77.3 | **+2.05%** | −1.07% | +1.65% | shut | **0.15835** |
| GOOG | crossover | 60.5 | +1.13% | −0.11% | +1.01% | shut | 0.00774 |
| AMD | crossover | 62.0 | +0.73% | −0.16% | +0.28% | open | 0.01354 |
| …14 more between +0.50% and +0.02% MFE… | | | | | | | |
| PLTR | crossover | 76.0 | +0.15% | **−1.48%** | −0.77% | open | 0.00944 |
| UBER | confidence | 54.6 | **+0.00%** | −1.28% | −0.82% | open | 0.00058 |
| LLY | confidence | 53.3 | **+0.00%** | −1.11% | −0.98% | open | 0.00807 |

**Verdicts, per filter:**
- **`ENTRY_THRESHOLD = 60` was perfectly discriminating today. 8 of 8 sub-60 candidates never traded
  0.5% above their entry; 0 of 8 reached the trail give-back; the cohort's average forward return was
  **−0.35%**.** Every one was dead money. Confidence in the 50–58 band is doing real work at the
  bottom of the scale — which is worth stating precisely because the same score is *inverted* above 80.
- **`MIN_CROSSOVER = 0.25` cost nothing. 0 of 12 declined candidates could have finished green on the
  1.25% trail**, and the cohort's average forward return was **−0.06%** — a wash. It saved PLTR
  (−1.48% MAE) and LLY (−0.96% MAE) and missed GOOG (+1.01%). **This is an independent, live,
  outcome-scored corroboration of the 08-13 four-window refutation of lowering the floor.** Two
  separate methods now agree. Stop re-litigating it.
- **The gate is the only filter that declined runners: avg MFE +1.67%, avg forward +0.75%, 2 of 3
  reached the trail.** PLTR (+2.62%) and TSLA (+2.05%) were the day's two best declined candidates and
  the gate alone stopped both.

### What worked / what didn't
- **Worked: the bot correctly refused to trade a 0.89%-range tape.** A zero-trade day here is the
  system functioning, not failing. 17 of 23 declined candidates never traded 0.5% above entry;
  **0 of 23 would have been stopped out**, but only **2 of 23** could have banked anything on the
  trail. On this tape, trading was a coin-flip with a spread cost attached, and the bot passed.
- **Worked: the ops fixes are holding.** `NRestarts=0`, no warnings, DB↔broker exact, and IMP-032's
  gate table validated exactly as its "what to check tomorrow" specified — **87 rows, 0 duplicate
  `(symbol, candle_start_utc)` pairs, first row 12:15 UTC vs the 11:38 restart** (no warmup backfill).
- **Didn't work — and this is the second consecutive day it hasn't: the gate declined the day's best
  candidate.** 08-20 was MU (conf 89.1, ran +1.56% to the flatten, gate alone). Today it was PLTR
  (+2.62%) *and* TSLA (+2.05%). **I am deliberately not acting on this, and the reason matters more
  than the observation:** n=3 today on top of n=1 yesterday, against a filter carrying **four
  independent windows** of profitability evidence (5d/10d/60d replay + 08-13 live) and a 10-day
  counterfactual of **+$37.68 with the gate vs −$53.84 without**. The weekly's verdict stands — *the
  bot makes money by declining to be long.* Two days of anecdote is exactly how you would destroy the
  one component with demonstrated edge. **Logged as evidence to accumulate, not as a change to make.**
- **Perplexity was materially WRONG today and the standing rule caught it — 11th consecutive bad
  return.** `sonar` reported *"S&P 500 closed 7,641.16, down 0.87%"* and *"Nasdaq down 1.00%, risk-off"*.
  IEX bars say SPY **+0.40%** and QQQ **+0.35%** day-over-day. **It got the direction backwards.** Had
  it been written into this review unverified, today would read as a risk-off rout that justified the
  flat session, when the truth is the opposite and far more damning: the market rose and the bot's
  design excluded it from the move. The 08-14 weekly's rule — *source regime from IEX daily bars first,
  `sonar` is lead-generation only* — earned its keep for the second time.

### Lessons & improvement candidates
1. **SHIPPED — IMP-033: make refused candidates measurable (`bot.report --refusals`).** Rationale in
   the improvement log. It is the third leg of the IMP-030 → IMP-031 → IMP-032 chain and it converts
   the largest untapped dataset this bot has into evidence.
2. **The pre-entry discriminator the 08-14 weekly asked for has a lead, and it is `ribbon_spread_pct`.**
   The refusal table sorts almost monotonically by it. The two candidates with spread **≥ 0.11**
   (PLTR 0.112, TSLA 0.158) ran **+2.62%** and **+2.05%**; the other 21, all with spread **≤ 0.029**,
   averaged **+0.30% MFE**. That is the shape of a real pre-entry proxy for the `<0.5%`-MFE cohort —
   *available before the entry*, unlike MAE. **Two caveats, both disqualifying on their own for now:**
   spread and gate-state are **confounded** today (both wide-spread names are also the two the gate
   refused), and **n=2**. Needs ≥3 agreeing windows via the harness. **Do not ship a spread filter on
   this.** But `--refusals` now makes the study a command instead of a night's work.
3. **Sample-size unlock.** Refusals accrue at **~25/day** (26 / 27 / 23 on 08-19/20/21) versus ~1–2
   trades/day. The `<0.5%`-MFE cohort question the weekly called *"the one measurement that matters"*
   was starved on 266 lifetime trades; on refusals it reaches n≈75 in three sessions and n≈500 in a
   month. **This is the fastest available path to the sample the freeze is waiting on.**
4. **Not a candidate: loosening anything.** Today's data argues the opposite in two of three cohorts.

### Notes for pre-market research
- **The watchlist is not the problem — the tape was.** 11 distinct symbols scored 23 candidates. Nothing
  was dead; everything was quiet. **No watchlist change is indicated by today's session.**
- **PLTR and TSLA are the two names worth keeping.** They carried by far the widest ribbon spreads
  (0.112 / 0.158) and the only two genuine intraday runs (+2.62%, +2.05% MFE). On a day when nothing
  else moved, these two did. **TSLA scored the day's highest confidence (77.3).**
- **GOOG chopped hard — 5 refusals, the most of any symbol** (three on crossover 0.04/0.11/0.15, two on
  confidence 50.1/57.9), and its one real move (+1.13% MFE) came on the *weakest* crossover of the five.
  Classic whipsaw signature: many near-misses, no clean signal.
- **QQQ, TSM and UBER printed near-zero ribbon spread** (0.00116 / 0.00186 / 0.00058) and MFE of
  +0.07% / 0.00% / 0.00%. **Genuinely inert today** — worth a look at whether they are chronically
  inert or just quiet on a narrow tape.
- **Regime expectation:** the gate ran a **49.3% duty cycle** — the tape was permissive, the signals
  were not. If tomorrow's range widens, expect entries without any code change. **NVDA reports 08-26**;
  positioning drift into it starts next week and should widen semi ribbons (AMD, TSM).
- **Do not re-run the "why no trades" reconstruction by hand.** `bot.report --days N --refusals` now
  answers it.

---

## 2026-08-24 — Daily Review

### Stats
- **Closed trades: 0.** Fifth consecutive session with no trade — the last fill was
  **2026-08-17** (MU, INTC, both stopped). Net P&L **$0.00**, win rate n/a.
- **Equity $9,089.13** (cash $9,089.13, `last_equity` identical, 0 open positions,
  0 orders submitted today). **DB ↔ broker reconcile exactly**: `dbo.trades` has 0 rows
  touching today, `/v2/positions` empty, `/v2/orders?status=all&after=today` empty.
  Account `PA34DFFLTHRT`. No drift, no missed fill, nothing carried overnight.
- **Service healthy.** `is-active` → active, started **11:37:11 UTC** by the pre-market
  routine (watchlist changed: NVDA parked, DASH added), **0 WARNING-or-above lines all
  session**, no restarts, no reconnects.
- **Scored refusals: 32** across 10 symbols — the reviewable population tonight.
- One ops nit, benign: the 20:00 UTC `bot.report` invocation hit a **transient Telegram /
  DB read timeout** and printed empty tables. Re-running immediately returned full
  results. Network flap, not a code fault — but see "Lessons" #4.

### Trade-by-trade review → refusal-by-refusal review
No trades, so the population is the 32 refusals, each scored against its own forward
tape (`bot.report --refusals`, IMP-033: enter at the refusal candle's close, flatten
with the session).

**Today's cohort — the filters cost nothing, and this is not a close call:**
```
cohort        n   avgMFE   avgMAE   avgFwd  <0.5%MFE  hitTrail  stopped
ALL          32   +0.30%   -0.49%   -0.14%   26/32      0/32     0/32
```
**Zero of 32 declined candidates could have banked anything on the 1.25% trail. Zero
would have been stopped. 26 of 32 never traded 0.5% above their entry.** Average forward
return −0.14%. On today's tape, taking any of these was paying spread for a coin flip.

Refusal reasons: **16 below `ENTRY_THRESHOLD`** (conf 50.0–59.7), **12 on the
`MIN_CROSSOVER` 0.25 floor** (conf_crossover 0.03–0.18), **4 vetoed by the market gate**.

**Why the gate refused everything: QQQ's 5m ribbon was never bullish, all session.**
IMP-032's telemetry is unambiguous — **86 gate candles, `gate_open` 0, `stacked` 0**,
`fast_rising` 33. A **0% duty cycle**, against 49.3% on 08-21. QQQ closed **−0.11%**
intraday on a **0.96% range**; SPY **−0.05%** on **0.41%**.

**But the individual names trended, and that is the tension of the day.** IEX 1-min bars,
13:30→20:00 UTC: **GOOG +1.31%** (2.49% range), **NFLX +1.05%**, **AMZN +0.97%**,
**MSFT +0.91%**, **DASH +3.87%** (4.26% range). The four candidates the gate alone
vetoed were **AMZN (conf 83.2), GOOG (78.2), DASH (71.6), MSFT (71.0)** — i.e. the gate
declined four of the day's genuine movers because the *index* was flat. **This is the
fourth consecutive session the gate has declined the day's best candidate** (08-20 MU,
08-21 PLTR/TSLA, 08-24 these four). I ran the pre-registered test rather than acting on
the pattern — see below.

### What worked / what didn't
- **Worked — the two signal filters read a dead tape correctly.** `ENTRY_THRESHOLD=60`
  and `MIN_CROSSOVER=0.25` between them declined 28 candidates, **none of which reached
  the trail**. That is the fifth and sixth independent confirmation. Do not loosen either.
- **Worked — ops.** Clean session, exact broker reconciliation, gate telemetry writing
  correctly on its second full day (86 rows, first at 12:10 UTC vs the 11:37 restart, so
  no warmup backfill contamination).
- **⚖️ RESOLVED — the market gate is vindicated, and the temptation is now closed.**
  The 08-21 weekly pre-registered the falsifiable test: *"re-run gate ON/OFF on the
  current config across ≥3 fresh windows. If net P&L agrees in sign in ≤1 of 3 windows,
  the gate's shape becomes revisable."* **Run tonight, 4 windows, current 18-name
  watchlist, gate OFF via `MARKET_FILTER_SYMBOL=""`:**

  | window | gate ON | gate OFF |
  |---|---|---|
  | 10d | **+$3.14** · PF 1.14 · 3 tr | −$10.24 · PF 0.93 · 20 tr |
  | 20d | **+$48.28** · PF 1.30 · 19 tr | −$47.79 · PF 0.89 · 54 tr |
  | 30d | **+$281.14** · PF 2.25 · 36 tr | +$243.87 · PF 1.38 · 89 tr |
  | 45d | **+$370.21** · PF 2.14 · 48 tr | +$188.54 · PF 1.19 · 125 tr |

  **The gate wins on net P&L, profit factor, win rate and avg/trade in 4 of 4 windows.**
  The revisability condition is not met — it is not 1 of 3, it is 0 of 4. That is now
  **eight agreeing windows**. Gate OFF takes **2.6× more trades** and converts a winner
  into a loser in both recent windows. **The gate is not revisable. Stop re-opening it.**
- **And this explains why the refusal table is a trap for this question.** The gate
  cohort now reads n=19 over 4 sessions, avgMFE **+0.93%**, avgFwd **+0.21%**, trail-hit
  **5/19** — the only cohort with a positive forward return (crossover −0.20%, confidence
  −0.16%). Read alone it argues loudly for softening the gate. **It is wrong**, exactly as
  the weekly warned: it prices the gate's misses per-candidate and is blind to the 3–5×
  volume of losing trades the gate prevents, and to capital being finite. **Two honest
  instruments, opposite answers; replay net P&L is the one that decides.** Recorded so
  no future run re-derives the seductive half.
- **Didn't work — Perplexity `sonar`, 17th consecutive thin-or-wrong run, and wrong in
  the direction that matters.** It reported *"tech weakness… Nasdaq down 0.38%… risk-off"*
  and returned *"no specific catalyst"* for **8 of 9** tickers. The bars say the index was
  **flat (QQQ −0.11%)** while **GOOG +1.31%, DASH +3.87%, NFLX +1.05%, AMZN +0.97%,
  MSFT +0.91%** all trended intraday. "Risk-off tech weakness" would have written tonight
  up as a regime the bot correctly sat out; the truth is narrower and more useful — a
  **flat index with trending constituents**, which is precisely the tape the gate is
  designed to sit out and precisely the tape where that hurts most. **Standing rule earned
  its keep a third time: regime comes from IEX bars, `sonar` is lead-generation only.**

### Lessons & improvement candidates
1. **SHIPPED — IMP-034: `conf_volume` is measured but no longer weighted (15 → 0,
   redistributed proportionally to crossover 30→39 and trend 20→26).** The audit that
   drove it: across 268 live trades the confidence blend is **mostly dead weight** —
   `conf_rsi` is 1.00 on **252/268** (avg 0.979) and `conf_volatility` on **174/268**
   (avg 0.958), so **~34 of 100 points are handed to every candidate regardless of
   setup**. Of the rest, `conf_volume` is not merely inert but **inverted**: the band it
   rewards most (1.00, n=79) returned **−$377.93**, the band it punishes most (0.00,
   n=51) returned **+$185.99** — confirmed on both all-time and post-IMP-021 windows.
   Heavy volume on a 1-min ribbon cross means the move is being *chased*, which is
   IMP-017's lifetime-loss finding restated. Replay, 4 windows, gate ON: **+$48→+$94
   (20d), +$281→+$356 (30d), +$370→+$454 (45d)**; the only dissent is the **10d window at
   n=3 trades**, which is noise. Trade count 48→50 over 45d, so this is **selection
   quality, not more trading**. Rationale in the improvement log.
2. **The remaining dead weight is the next question, and it is NOT a tweak to make
   blind.** `conf_rsi` (20 pts) and `conf_volatility` (15 pts) are near-constant *for
   candidates that reach scoring* — but `conf_rsi` does hit 0.0 (overbought ≥70), so it
   is functioning as a **de-facto veto** rather than a ranking term, and removing its
   weight would remove that veto. **The right experiment is to re-express both as explicit
   gates and free their 35 points for the discriminators** — measured across ≥3 windows,
   not assumed. Filed to `todo.md`. **Do not touch until IMP-034 has live evidence.**
3. **`ribbon_spread_pct` — the weekly's confound is cleared, the effect is real but too
   weak to ship.** n=108 over 4 sessions, gate state controlled: within the **gate-shut**
   population (n=74) the high-spread half is **62% dead / 7 trail-hits** vs the low half
   **70% dead / 2 trail-hits**; tertiles across all rows give avgMFE **+0.72% (high)** vs
   **+0.34% / +0.34%**. So it does separate — **but every bucket still has a negative or
   zero average forward return**, i.e. it separates *less dead* from *more dead*, not
   winners from losers. **And a spread floor is an additional filter on a bot that has not
   traded in five sessions — the wrong direction.** Keep accruing; do not ship.
4. **Not a candidate tonight, but logged: the `--days N` window is a rolling timestamp,
   not a calendar boundary.** All three windowed queries use
   `DATEADD(day, -?, SYSUTCDATETIME())`, so `--days 3` run on a Monday evening silently
   returns **only Monday** (Friday's session ended before the cutoff) — it cost me a real
   confusion tonight, `--days 5` reporting n=82 against a true 4-session population of
   n=108. It is harmless at the 21:10 UTC cron slot and wrong at any other hour, which
   makes every study window **clock-dependent and non-reproducible**. Filed to `todo.md`
   as the leading candidate for the next run.
5. **Not a candidate: loosening anything.** 0 of 32 declined candidates reached the trail.
   There is no case in today's data for a lower threshold, a lower crossover floor, or a
   softer gate — and the gate question is now closed by 8 windows.

### Notes for pre-market research
- **No watchlist change is indicated by today's session, and the board is not the
  problem.** 10 distinct symbols produced 32 scored candidates — the most active refusal
  day yet. Everything is reaching the scorer.
- **DASH answered its day-one question emphatically: it works.** Added this morning as
  the first name selected *on* the volatility floor, it scored **3 candidates** and was
  the **best-moving name on the board (+3.87%, 4.26% range)**. The floor selects for
  signal, not just against dead names. **Keep. The liquidity caveat ($0.81B/day) stands.**
- **GOOG was the day's most active name — 6 refusals** (three on crossover 0.03/0.09/0.12,
  three on confidence 56.2/57.7/58.4) — and it **ran +1.31%**. Second consecutive session
  as the top chopper. Its pattern is many near-misses around a real move: the crossovers
  fire late and thin. **Dead-signal test is dated 08-31; it is nowhere near dead.**
- **AMZN (5 refusals, +0.97%), MSFT (5, +0.91%), NFLX (5, +1.05%) all trended and all
  went untraded.** None of these is a watchlist problem — they were gated by the index.
- **BABA's 50MA trigger did not fire and it printed no candidate today.** The pre-market
  entry pre-registered *"if it closes below its 50MA, the two-leg rule fires on its own"* —
  check the close before acting either way. It produced **0 refusals**, its quietest
  session in a week.
- **Regime expectation:** the gate ran a **0% duty cycle** on a flat index with trending
  constituents. **This is the single tape shape where this bot's design costs it the
  most, and it is by choice** — the 4-window study above says paying that cost is still
  correct. If QQQ resumes trending, entries should appear with no code change, and they
  will now be scored on cross geometry rather than on volume (IMP-034).
- **Wednesday 08-26 is the week's pivot: NVDA AMC + July core PCE 08:30 ET.** NVDA is
  parked so the board carries no direct exposure to the print, but **AMD, TSM, MU and
  INTC will trade the read-through unhedged by design**. Jackson Hole runs 08-27→29.
- **Dated items due 08-27:** NVDA re-enable, AAPL and JPM dead-signal tests, INTC
  on-notice re-check.
