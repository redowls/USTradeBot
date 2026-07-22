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
