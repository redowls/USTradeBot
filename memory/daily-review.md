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
