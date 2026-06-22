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
