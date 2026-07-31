# Weekly Review

Friday recap for USTradeBot, written by the `ustradebot-weekly-review` routine
(Friday 22:15 UTC) after the daily review. Each entry grades the week with a
**letter grade (A–F)** for both results and process.

Grading guide:
- **A** — profitable week, rules followed, improvements validated, no system errors.
- **B** — flat-to-positive, minor process slips, clear lessons captured.
- **C** — small loss within risk limits OR profitable but rules broken.
- **D** — meaningful loss, repeated mistakes, or unvalidated changes shipped.
- **F** — large loss, risk-limit breach, or system failure (crash, naked positions).

Entry template:

## Week ending YYYY-MM-DD — Grade: X

### Stats
(trades, win rate, net P&L $, profit factor, equity start → end, best/worst trade)

### Grade rationale
(why this grade — results AND process)

### What worked / what didn't
### Improvements shipped this week
(from memory/improvement-log.md, with observed effect)

### Focus for next week

---

## Week ending 2026-06-19 — Grade: D

### Stats
- **DB (closed, Mon 06-15 → Fri 06-19):** 27 trades, 12W → **44.4% win**, net **+$97.26**,
  PF **1.42**, avg win **+$27.42** / avg loss **−$15.45**. Best **+$154.28** (INTC), worst
  **−$43.60** (BABA). By day: 06-15 **+$79.26** (10) · 06-17 **−$181.06** (8) · 06-18 **+$199.06** (9).
- **⚠️ The headline +$97.26 is FICTITIOUS — do not trust it.** 06-18's +$199.06 is fake: 7
  positions were recorded "end-of-day flatten" CLOSED but **never actually filled** (still open
  at the broker), plus a phantom **INTC +$154.28** row (a 06-12 stale row the flatten swept up;
  INTC was never held that week). Strip the fakes and the week is **negative**.
- **Equity is the truth: $9,384.89 (Mon 06-15 EOD) → $9,248.81 (now) = −$136.08 (−1.45%).**
  Plus **7 positions carrying NAKED into Monday 06-22** (GOOG/INTC/MU/QQQ/SE/TSLA/TSM, ≈ +$33
  unrealized, **no stops**, over the 3-day Juneteenth weekend).
- Confidence vs outcome (all-time): 70-79 best (+$184, 61%), 60-69 +$106 (55%), **80-89 still
  negative (−$70, 33%, 6 tr)** — unchanged signal; sample still too small to act.
- Service: **crash-loop 06-15 06:02 UTC** — 5 failed restarts on `PermissionError: .env`
  (file-ownership), recovered 06:04 (pre-market, no trading impact). Recurring Alpaca **504
  storms** + websocket drops near the close all week.

### Grade rationale
Results/reliability **alone read F** by the rubric: **naked positions TWICE** (4 names 06-16,
7 names 06-18 over a long weekend), a **service crash**, and **corrupted books** (the reported
+$97 P&L is not real). The bot repeatedly failed its #1 job — capital protection — and the same
naked-overnight failure **recurred** after a 06-15 fix. Held up from F to **D** by: (1) **no
large loss and no risk/sizing-limit breach** — real damage was a modest −1.45%, losses per trade
stayed contained; (2) **exemplary process** — every failure was root-caused *same day* and a
*validated* fix shipped (IMP-001→005, suite 186→**197** passing, one change per run), with honest
broker-verified book backfills (06-17) and no entry-quality recklessness; (3) by Friday the hole
is **closed in code** (IMP-004 detection + IMP-005 prevention). This is a "repeated failures,
well-remediated" week, not an uncontrolled blow-up — D, not F. It is emphatically **not** higher:
a week with live naked positions still riding into Monday cannot be a C. (First weekly entry —
no prior "Focus for next week" to grade against.)

### What worked / what didn't
- **Worked:** process discipline — daily root-cause → validated fix → honest books; risk sizing
  held (worst single trade −$43.60); watchlist discipline (zero churn, the "never park a held
  name" hard rule honored every day); 06-15's real day was genuinely good (+$79, PF 3.4).
- **Didn't:** the EOD flatten — the bot's exit/flatten infrastructure failed in **three distinct
  modes** in one week (504 timeout → submit-ack-without-fill → candle-timing past the close),
  each one leaving positions naked. Detection/prevention shipped, but **none is yet proven on
  live data** (no clean session since IMP-003/004/005). The .env crash-loop is a deploy/ownership
  gap that should never have reached production.

### Improvements shipped this week
- **IMP-001** (b7f37f7) — poll held-qty release before the flatten close. **Observed: held all
  week**, the async-cancel race never recurred. ✅
- **IMP-002** (1b575a7) — critical Telegram page when a flatten can't close (naked risk).
  **Observed: still NOT proven to fire** — 06-18's carry bypassed it (faked success). Owes Monday.
- **IMP-003** (9ec528f) — reconcile broker-side stop/target fills + 06-17 backfill. **Observed:
  not yet validated by clean data; 5 stale 06-11/06-12 phantom rows still need a one-off purge.**
- **IMP-004** (5825b4b) — `close_position` confirms the position is actually flat before
  reporting success. **Observed: unvalidated** (shipped 06-18 EOD, holiday since). The week's
  most important fix — first test Monday 06-22.
- **IMP-005** (99ea33d) — widen `FLATTEN_BEFORE_CLOSE_MIN` 5→15 so the flatten fills in liquid
  RTH (+ late-entry cutoff). **Observed: unvalidated** (shipped on the holiday). First test Monday.

### Focus for next week
**Monday 06-22 is the verdict day** — flatten the 7 naked carried lots at the open, then prove
IMP-004 (no fake CLOSED rows) + IMP-005 (flatten fills before 16:00, broker flat) + IMP-002 (NAKED
page actually fires) on live data; purge the 5 stale phantom rows; fix the .env ownership so the
service can't crash-loop on deploy. No new strategy/entry changes until the exit infra is proven clean.

---

## Week ending 2026-06-26 — Grade: B

### Stats
- **Strategy trades (Tue 06-23 → Fri 06-26):** 25 — 10W → **40% win**, net **−$9.79**, PF **0.95**,
  avg win **+$19.41** / avg loss **−$10.20**. Best **+$74.72** (MSFT 06-26), worst **−$53.94** (AMD
  06-25). By day: 06-23 **−$9.13** (3, 0W) · 06-24 **−$10.14** (6, 3W) · 06-25 **−$52.59** (5, 2W) ·
  06-26 **+$62.07** (11, 5W). (`bot.report --days 7` reads 30 / 33% / −$9.79 — the extra 5 are the
  06-22 **IMP-006 phantom-sweep rows** booked at pnl=0, reconciliation bookkeeping, not strategy trades.)
- **Equity: $9,321.14 (Mon 06-22 review) → $9,308.57 (now) = −$12.57 (−0.13%) — essentially flat.**
  Measured from last Friday's close ($9,248.81) it's **+$59.76**, but that includes a **+$72.33
  favourable weekend gap** as the 7 naked-carried 06-18 lots auto-liquidated at Monday's open (luck,
  not design — the exposure was real and unprotected, the prior week's last bill coming due).
- **Books are exact to the cent** — every clean session DB realized P&L == equity mark-to-market
  (06-26 +$62.07 == +$62.07). The multi-week DB⇄broker desync that earned last week's D is closed.
- **Crossover was the week's cleanest signal:** xo < 0.20 → 12 tr, **−$129.79, 8% win (1/12)**; xo
  0.20–0.40 → 6 tr, +$2.38 (50%); **xo ≥ 0.40 → 12 tr, +$117.62 (50%)** — the monotonic relationship
  that justified IMP-011, confirmed in the week's own data.
- **Confidence vs outcome (all-time):** 70-79 best (+$170.31, 58%, 26 tr); 80-89 +$25.38 (50%, 8 tr);
  **90-100 −$53.94 (0/1 = AMD's open-spike top)** — a *new* emerging concern.
- **Service: healthy all week** — 0 real errors (the only journal "error" hits are the websocket
  `cancelErrors:` field name), 3 clean scheduled restarts, **no crashes, no naked carries, no NAKED
  pages**. A stark reversal of last week's .env crash-loop.

### Grade rationale
**The turnaround week.** Last week's D was for an exit/flatten infrastructure that failed in three
distinct modes and rode positions naked over a long weekend with corrupted books. This week every one
of those fixes was **proven clean on FOUR consecutive live sessions (06-23..26)**: the wall-clock
watchdog fires the flatten at 15:45 ET, all market sells fill in liquid RTH, **0 phantom rows, broker
flat every night, no naked carry, no silent fake-success**, and the books now tie to equity **to the
cent**. Last week's "Focus for next week" was **fully honored** — Monday 06-22 was the verdict day (the
7 carried lots cleared at the open, IMP-004/005/002 validated, the 5 stale phantoms purged via IMP-006,
the .env crash-loop did not recur), and the rule *"no new strategy/entry change until the exit infra is
proven clean"* was obeyed to the letter: IMP-008/009/010 were all pure data-integrity, and the **first
strategy change (IMP-011) was deliberately held back until four clean-book days made the data
trustworthy** — textbook discipline. Risk control held all week (worst trade −1.64%, no risk-limit
trips), watchlist churn minimal and justified (MU event-park + validated re-enable, nothing else).
It is **not an A** for two reasons: (1) **results were flat, not profitable** — strategy net −$9.79,
equity −0.13%; and (2) a **new concern surfaced** — the highest-confidence entry the bot has ever
recorded (AMD, conf 91.73) was the week's worst loser (open-spike top, −$53.94 → 90-100 band now 0/1),
and IMP-011, the first win-rate change, is **unproven live**. A flat-to-positive week with exemplary,
fully-validated process on a now-clean system is a solid **B**.

### What worked / what didn't
- **Worked:** the exit infrastructure — the entire multi-week saga is closed and proven (4 clean
  sessions); books exact to the cent; daily root-cause → validated fix discipline (228 tests, one
  change per run); strong-crossover entries carried the up days (MSFT +$74.72 alone > the whole week's
  net); trailing stops captured wins (SE +1.82%, MU +2.48%) and capped every loss (worst −2.03%); the
  MU event-park + re-enable was executed and validated cleanly.
- **Didn't:** the strategy made no money in a choppy, regime-driven tape (40% win, PF 0.95) —
  weak-crossover chop was the recurring drag (now filtered by IMP-011); and the high-confidence /
  open-spike loss (AMD) is a fresh pattern the crossover floor does **not** address.

### Improvements shipped this week
- **IMP-006** (2635739) — startup phantom-sweep. **Observed: ✅ validated** — book stayed broker-matched
  all week (0 OPEN rows every session), no phantom re-accumulation, no new `trade_id=None` orphans.
- **IMP-007** (e19c4c6) — wall-clock EOD-flatten watchdog + skip logging. **Observed: ✅ validated 4×** —
  flatten fired 15:45 ET on wall-clock every session, all sells filled before 16:00, even on the 06-26
  zero-intraday-exit slow-drift tape. The naked-overnight failure cannot recur on this path.
- **IMP-008** (f854f96) — record exits at the real broker fill. **Observed: ✅** — DB exit prices match
  `/v2/orders`; DB P&L ties to equity to the cent.
- **IMP-009** (0737122) — record entries at the real buy fill. **Observed: ⚠️ mostly worked but missed
  AMD's ~2-min delayed fill (06-25), the day's whole book error — completed by IMP-010.**
- **IMP-010** (9e590c6) — re-read the entry fill at exit time (robust to delayed fills). **Observed:
  ✅ held** — 06-26 DB net == equity to the cent; all entry/exit prices match broker fills.
- **IMP-011** (0002ed9) — `MIN_CROSSOVER` 0.20 entry floor (the week's first strategy change).
  **Observed: unproven** — live from the 06-26 restart; first live read is next week.

### Focus for next week
**Prove IMP-011 on live data** — confirm the weak-cross (xo<0.20) cohort is filtered (skip logs fire),
entry *count* doesn't collapse toward zero, and the surviving entries' win rate rises above the 40%
baseline; do NOT raise the 0.20 floor yet. Begin watching the **90-100 confidence / open-spike** pattern
(AMD) for a possible first-N-minutes entry guard — gather occurrences, don't act on one. Now that the
book is clean and exact, **grade the strategy on results** (PF, win rate) — the exit-infra saga is closed.

---

## Week ending 2026-07-03 — Grade: A−

### Stats
- **DB (closed, Mon 06-29 → Fri 07-03; 07-03 was the Independence-Day holiday, market closed):** **35 trades,
  20W → 57.1% win**, net **+$171.24**, PF **1.59**, avg win **+$23.07** / avg loss **−$19.35**. Best **+$95.62**
  (TSLA 06-29), worst **−$46.84** (MSFT 06-29). By day: 06-29 **+$89.72** (12, 58%) · 06-30 **+$61.79** (9, 78%) ·
  07-01 **+$9.52** (7, 43%) · 07-02 **+$10.21** (7, 43%) · 07-03 **holiday (0)**.
- **Equity: $9,308.54 (Mon 06-29 open/last_equity) → $9,479.66 (now) = +$171.12 (+1.84%).** The **best week of the
  record**, and the DB net **+$171.24 ties to equity to the cent** every trading day (5th–8th consecutive clean
  sessions; the ~$0.12 residual is a $0.03 holiday bookkeeping drift + rounding). No phantoms, no naked carry,
  broker flat every night — 0 open positions into the long weekend.
- **Per-symbol:** winners led by **TSLA +$107.04** (3 tr, 2W), **TSM +$59.59** (2/2), **INTC +$50.90** (2/2),
  **AAPL +$24.23** (3/3); drags **SE −$30.85** (thin-tape fades), **ABNB −$27.09**, **AMZN −$26.06**, **MSFT
  −$43.84** (the early-entry chop). Semis/megacap trend names carried the week.
- **Confidence vs outcome (all-time):** 70-79 best **+$257.74 (59%, 41 tr)**, 60-69 **+$129.29 (46%, 76 tr)**,
  80-89 **+$47.38 (56%, 9 tr)**, **90-100 still −$53.94 (0/1 = AMD 06-25)** — unchanged (no 90+ trade this week).
- **Service: healthy — 0 crashes, `NRestarts=0`, one clean deploy restart (06-30 21:27 UTC for IMP-012).** The
  only journal ERRORs all week were the **06-30 trailing-stop 422 traceback storm** (AMD stop 698c6cdf, ~4.5h of
  minutely tracebacks) — the exact latent bug IMP-012 fixed; 07-01/07-02 ran clean (0 tracebacks, 0 WARNINGs).

### Grade rationale
**The best week of the record, on a now-clean system — and last week's plan executed to the letter.** Results
were genuinely good: **+1.84% ($171.12), PF 1.59, 57% win**, books **exact to the cent every trading day**, no
naked carries, no NAKED pages, no risk-limit trips, worst trade a contained −1.77% (MSFT). Last week's "Focus for
next week" was **fully honored**: **IMP-011 was proven on live data over its full first week** — entry count held
every day (12/9/7/7, never collapsed), the floor was honored every session, the `crossover < 0.20` skip logs fired
daily on the chop cohort, and win rate rose to **57% vs the 40% baseline**; the 0.20 floor was **not** raised
(GOOG entered at exactly 0.20 on 06-30 and barely paid — correctly placed); and the 90-100/open-spike pattern was
**watched, not acted on** (now 3 occurrences: AMD 06-25, MSFT 06-29, AMD 06-30). Discipline was textbook: **zero
entry-logic changes were stacked on IMP-011 during its proving window** (three "reviewed, no change warranted" days
— 06-29/07-01/07-02 — plus the holiday), and the one shipped change (IMP-012) was pure exit-infra that cannot
confound the evaluation. It is **not a clean A** for two honest reasons: (1) a **real system error occurred live
this week** — the 06-30 422 traceback storm swamped the log for ~4.5h and left two symbols stuck MANAGING (the
rubric reserves A for "no system errors"); it was zero-capital-cost, books stayed exact, and it was root-caused and
fixed *same day* (IMP-012), but it did happen in production; and (2) IMP-012 then surfaced a **complementary
residual gap** that recurred **3× (TSLA 07-01, GOOG+SE 07-02)** — a filled stop with no subsequent trail-replace
leaves a symbol MANAGING until the EOD reconcile — still **open** (staged, not shipped). Both are zero-realized-cost
and correctly handled, so this is a strong, well-run, profitable week docked one notch from a perfect A → **A−**.

### What worked / what didn't
- **Worked:** IMP-011 delivered exactly as designed (weak-cross chop filtered, win rate 40%→57%, count healthy,
  floor honored) — the week's headline; the strong/mid-cross trend longs carried it (TSLA +$95.62 on 06-29 alone >
  three of the four days' net; TSM/INTC/NVDA/QQQ green); exit infra clean 4 straight sessions (wall-clock flatten,
  all fills real, broker-side stops reconciled at the true price, books exact to the cent, broker flat nightly);
  risk control held (worst −1.77%, no stop-outs beyond contained trail exits); watchlist discipline (MU re-enable
  kept paying +$14.37; only QCOM park-watch pending — minimal, justified churn).
- **Didn't:** the **06-30 trailing-stop 422 storm** (latent pre-IMP-012 bug, ~4.5h of tracebacks, zero capital
  cost) reached production before being fixed; **IMP-012's residual MANAGING-until-EOD gap** recurred 3× (still
  open); the two flat mid-week days (07-01/07-02, both 43% / +~$10) show the strategy has **no edge in a
  low-volatility consolidation tape** — it makes its money on trend-dispersion days (06-29/06-30) and merely
  treads water when the tape chops; and the **early-entry / strong-cross underperformance** pattern is now 3 data
  points (MSFT was this week's worst trade at −$46.84) but remains correctly unactioned.

### Improvements shipped this week
- **IMP-011** (0002ed9, shipped 06-26) — `MIN_CROSSOVER` 0.20 entry floor. **Observed: ✅ VALIDATED over its full
  first week** — entry count held (12/9/7/7), floor honored every session, weak-cross skip logs fired daily, win
  rate 40%→57%, no over-filtering (GOOG at exactly 0.20 barely paid). Keep at 0.20; do not raise.
- **IMP-012** (c9fbcdc, shipped 06-30) — detect a broker-side stop-leg fill in the trailing path (422 "order is
  not open" → `StopOrderGone`), reconcile + free the symbol instead of re-issuing the doomed move every candle.
  **Observed: ✅ validated** (07-01/07-02: 0 tracebacks, no 422 storm — the 06-30 log flood cannot recur), **but
  it surfaced a complementary residual gap** — a filled stop with no subsequent trail-replace still sits MANAGING
  until the EOD reconcile (3× this week, all zero-cost). Staged follow-up correctly held back.

### Focus for next week
**Decide the staged MANAGING-reconcile fix (IMP-012's residual gap).** Its explicit ship trigger — "after IMP-011's
first full week is graded (this weekly) OR the next occurrence that blocks a real re-entry" — is now met by this
grade, and it has 3 clean occurrences of evidence: **green-light it on a calm, non-event trading session** (piggyback
the IMP-007 wall-clock `tick()` with a bounded `get_open_position` reconcile of MANAGING names; it is exit-infra, won't
confound IMP-011). **Keep IMP-011 at 0.20** (proven; do not raise). Keep **watching the early-entry / strong-cross
underperformance** (now 3 obs — MSFT/AMD) for a possible first-N-minutes or RSI-extreme guard, but **do not act on 3
points**. Now that IMP-011 is validated and the book is exact, the strategy's real open question is its **flat-tape
edge** (07-01/07-02 near-zero days) — gather more consolidation-tape sessions before any entry-quality change. Confirm
the **Monday 07-06 pre-market Claude routine actually runs** (today's failed on an expired OAuth token — re-authed).

---

## Week ending 2026-07-10 — Grade: C

### Stats
- **DB (closed, Mon 07-06 → Fri 07-10):** **45 trades, 18W → 40% win**, net **−$172.40**, PF **0.62**, avg win
  **+$15.39** / avg loss **−$16.64**. Best **+$53.21** (SE 07-09), worst **−$55.80** (AVGO 07-06). By day:
  07-06 **−$52.33** (11, 6W) · **07-07 −$179.00 (11, 1W)** · 07-08 **+$54.69** (7, 5W) · 07-09 **+$22.58** (10, 4W)
  · 07-10 **−$18.34** (6, 2W).
- **Equity: $9,479.66 (Mon 07-06 pre-open) → $9,307.15 (now) = −$172.51 (−1.82%).** The **worst week of the
  record** — a near-exact mirror of last week's best (+1.84%). **Books exact to the cent every trading day (5/5):**
  DB net −$172.40 == equity move; 0 phantoms, 0 naked carry, broker flat every night.
- **The entire loss is ONE day.** 07-07 (a broad false-breakout whipsaw, 1W/10L, **−$179.00**) = **104% of the
  week's net**; the other **four days combined to +$6.60** — essentially flat. Strip 07-07 and the week is
  break-even.
- **Per-symbol drags:** AVGO **−$87.70** (4 tr, whipsawed both ways incl. a 07-09 same-day re-entry), INTC
  **−$58.68** (2/0, the conf-94 top-band fade), TSM **−$31.23** (3/0), C **−$27.09**, NFLX **−$26.90**. **Winners:**
  NVDA **+$55.84** (3, 2W), BABA **+$48.10** (3/3), SE **+$28.62** (5, 3W), ABNB **+$26.07** (3, 2W).
- **Confidence vs outcome (all-time):** **70-79 the peak +$232.93 (54%, 54 tr)**, 60-69 +$80.92 (46%, 101 tr),
  80-89 +$38.63 (50%, 14 tr), **90-100 0W / 3 tr / −$144.42** — deepened this week by AVGO (conf 96, −$55.80) and
  INTC (conf 94, −$34.68). The top-band inversion IMP-013 targets is **reconfirmed**.
- **Service: healthy — `NRestarts=0`, no crashes, no naked carry, no 422 storm.** Only **1 real ERROR all week**
  (07-06 Telegram `sendMessage` SSL handshake timeout — a side-channel exit alert, **zero trading impact**) + 2
  benign IMP-012 stop-reconcile WARNINGs (working as designed) + 1 websocket auto-reconnect. A clean-reliability week.

### Grade rationale
**The mirror of last week — record-worst results (−1.82%) on the same A-grade process that earned the record-best
week its A−.** Two honest anchors fix the grade. It **cannot be a B** (B = flat-to-positive; this is a real −1.82%
loss, the biggest weekly drawdown on record). And it is **not a D**, for three reasons: (1) **risk was fully
controlled** — worst trade −1.62% (AVGO −$55.80), no risk-limit trip, no naked overnight, no system failure, books
exact to the cent all five days; (2) **no repeated mistakes and no reckless/unvalidated changes** — the multi-week
exit-infra saga stayed rock-solid, and the only two ships were capital-protective / data-integrity (IMP-013's
sizing cap is entry-neutral and can only *shrink* a position; IMP-014 is the deliberately-staged fix, green-lit
exactly on the trigger last week's grade set); and (3) **the entire loss is one unforecastable regime day** —
07-07's broad false-breakout whipsaw (1W/10L, −$179) was 104% of the week's net, the other four days summing to
+$6.60. Last week's **"Focus for next week" was honored to the letter:** IMP-014 (the staged MANAGING-reconcile
fix) shipped on its trigger; IMP-011 kept at 0.20 (not raised); the break-even-stop candidate was finally
**measured against real IEX minute bars** (07-09 MFE run, 99 trades) and **correctly NOT shipped** (edge marginal
and whipsaw-fragile); and 07-07's disaster was diagnosed as regime and **not overfit** ("reviewed, no change
warranted" — the day's own data would have removed the only winner and spared the losers). The week's real open
weakness is genuine but **correctly unactioned**: the long-only ribbon has no edge in a false-breakout tape and no
daily-loss / mark-to-market stand-down, so it kept opening entries into 07-07's adverse regime — a legitimate
structural gap that needs live MTM tracking (a larger critical-path change) and must not be rushed off one day.
Exemplary, fully-validated process on a contained, single-regime-day loss = a solid **C**. It is emphatically not
higher (a real record-worst loss), and the discipline holds it well clear of D.

### What worked / what didn't
- **Worked:** process discipline was textbook — the 07-09 **MFE study on real minute bars** (not another deferral)
  that correctly killed the break-even-stop candidate; **zero overfitting** of the −$179 day; one-clean-variable-
  at-a-time (only capital-protective / data-integrity ships); books exact to the cent 5/5; **exit infra flawless**
  (wall-clock flatten every day, all fills real, broker flat nightly, IMP-012 reconciles clean, no 422 storm);
  risk control held (worst −1.62%, no breach); minimal watchlist churn (only QCOM parked 07-06); service
  `NRestarts=0`. **IMP-013 got its first live confirmation** (INTC de-sized 07-09). The three green/flat days
  (07-08/09/10) show the strategy still works when the tape trends or holds.
- **Didn't:** the strategy has **no edge in chop and no stand-down mechanism** — on 07-07 it took 11 entries into a
  persistent false-breakout tape and lost 10 (−$179 = the whole week's loss). The **90-100 confidence band deepened
  to 0W/3/−$144.42**; IMP-013 caps *size* but bound only **once** live and does **not prevent** those entries. Both
  fresh ships are early: IMP-013 largely unproven (1 binding), IMP-014 unproven (shipped today, after the close).

### Improvements shipped this week
- **IMP-013** (ac195d6, shipped 07-06) — `SIZE_CONFIDENCE_CAP=85` (cap the confidence→size ramp). **Observed:
  ⚠️ directionally validated, but only ONE live binding all week** — INTC 07-09 (conf 94 → de-sized off eff_conf 85,
  ~$347 less notional, ~$5 less loss). No other >85-conf entry occurred to test it (07-06 AVGO conf 96 predated the
  deploy; 07-07/08/10 all peaked <85). The 90-100 band deepened to 0W/3/−$144.42, reconfirming the inversion — but
  the cap is **capital-protective sizing, not an entry guard**, so it shrinks damage it can't prevent. Keep at 85;
  **still early** — needs more bindings to judge the 80-100 PF effect.
- **IMP-014** (c92fdfd, shipped 07-10) — wall-clock `tick()` sweeps `MANAGING` symbols for a **down-move**
  broker-side stop fill the trailing ratchet never catches (closes IMP-012's residual gap — **last week's staged #1
  focus**). **Observed: UNPROVEN — shipped today AFTER the close** (live on the 21:23 UTC restart, 240 tests).
  Today's SE (stop filled @14:33, undetected ~5h until the EOD flatten) is the **motivating regression case, not
  yet a validated catch**; first live test is next week.

### Focus for next week
**Prove the two fresh ships on live data.** (1) **IMP-014** — a down-move broker-side stop fill must now reconcile
**mid-session** (`reconciled broker-side exit … -> WAITING`, exit booked at the true fill time) with **zero** late
`end-of-day flatten (stop/target filled broker-side)` rows and no double-exit / double-Telegram. (2) **IMP-013** —
accumulate more **>85-conf bindings** and re-check the 80-100 PF; keep the cap at 85. Keep **IMP-011 at 0.20** and
the **break-even-stop candidate downgraded** (07-09 MFE = marginal/fragile). The one strategic question worth
**designing (not rushing):** a **mark-to-market daily-loss / consecutive-loss stand-down** for broad-adverse days
like 07-07 — gather 1–2 more whipsaw sessions and design it on live open-P&L before shipping (same discipline that
made IMP-011 wait 4 clean days). **No entry-logic changes while IMP-013/014 are still proving.**

---

## Week ending 2026-07-17 — Grade: D

### Stats
- **DB (closed, Mon 07-13 → Fri 07-17):** **21 trades, 3W → 14% win**, net **−$285.95**, PF **0.16**, avg win
  **+$18.02** / avg loss **−$18.89**. Best **+$30.87** (GOOG 07-15), worst **−$48.96** (NFLX 07-13). By day:
  07-13 **−$51.48** (2, 0W) · 07-14 **−$62.38** (6, 2W) · 07-15 **−$38.19** (7, 1W) · 07-16 **−$20.64** (1, 0W) ·
  07-17 **−$113.26** (5, 0W). **Every single day red — the first all-red week of the record.**
- **Equity: $9,307.12 (Mon 07-13 pre-open) → $9,021.08 (now) = −$286.04 (−3.07%).** The **worst week of the
  record** by a wide margin (prior worst was 07-10's −$172.40 / −1.82%). **Books exact to the cent every trading
  day (5/5):** each day's DB realized == equity mark-to-market; 0 phantoms, 0 naked carry, broker flat every night.
- **Not one bad day — a broad, persistent losing week.** Unlike 07-10 (where 4 of 5 days summed to +$6.60 and
  one whipsaw day was 104% of the loss), here **every day lost meaningfully**: strip the worst day (07-17 −$113)
  and the other four still combine to **−$172.69**. There is no "single unforecastable event" rescue this week.
- **Per-symbol:** only **two** green — **GOOG +$30.87** (the week's one clean full-confirm trend, 07-15) and
  **QQQ +$0.86**. Drags: **NFLX −$97.80** (3 tr, re-enabled/parked/re-enabled around its Thu print, faded or
  stopped every time), **INTC −$45.06** (3, 1W), **WMT −$32.69**, **TSM −$32.20**, **SE −$29.64**, **TSLA −$22.05**,
  **BABA −$20.64**. Chip/semis names carried the damage on a risk-off week.
- **Exit reasons:** 7 `stop/target filled broker-side` (**−$188.08**) + 14 `end-of-day flatten` (−$97.87). All 7
  broker-side stops were **down-move fills cleanly reconciled by IMP-014** (its full-validation week — see below).
- **Crossover cohorts (this week):** 0.20–0.40 → 14 tr, **−$115.36 (3W)**; **xo ≥ 0.40 → 7 tr, −$170.59 (0W)** —
  the *strong*-cross cohort lost hardest, reinforcing the 07-16 "very-strong crossover = late/reversal entry"
  watch-candidate. **No xo<0.20 all week** — IMP-011's 0.20 floor honored every session.
- **Confidence vs outcome (all-time):** **70-79 still the peak +$156.97 (51%, 61 tr)** [fell from +$220 as INTC 76
  + NFLX 73 both lost 07-17], 60-69 **−$56.70 (42%, 112 tr)**, **80-89 −$33.73 (41%, 17 tr)** [flipped negative
  from +$38.63 as NFLX 83.2 + TSLA 83.6 lost], **90-100 −$144.42 (0%, 3 tr, unchanged — no ≥85 entry all week).**
- **Service: healthy — `NRestarts=0`, no crashes, no naked carry, no 422 storm, EOD flatten fired clean every day.**
  Only benign noise: a self-healed **07-13 Telegram `sendMessage` ConnectionReset** (side-channel exit alert, zero
  trading impact) and two **pre-market websocket `connection limit exceeded` blips** (07-14 05:48–05:52, 07-15
  11:22 — old-PID/new-PID restart-handoff overlap, recovered in minutes, zero session impact). A clean-reliability week.

### Grade rationale
**A record-worst, all-five-days-red loss (−3.07%) that exemplary process holds to a *high* D — but cannot rescue
to a C.** Two honest anchors fix the grade. It **cannot be a C**: the C rubric is "a *small* loss within risk
limits," and −$285.95 / −3.07% is the **biggest weekly drawdown on record** — ~68% larger than last week's −1.82%
C, and unlike that week it is **not one bad day** (every one of the five sessions lost, 14% win, PF 0.16). A grade
that stayed C here would be insensitive to a near-doubling of the loss and to the loss becoming *persistent* rather
than a single event — that is a **meaningful loss**, the D threshold. And it is emphatically **not an F**: no large
single-trade loss (worst −1.99%, TSM's near-floor stop), **no risk-limit breach, no naked overnight, no crash, no
corrupted books** — real per-trade damage stayed tightly contained and the capital-protection machinery worked
perfectly. What holds it at the **top of D** rather than lower is genuinely strong process: **books exact to the
cent all 5 days**, broker flat every night, service `NRestarts=0`; **zero reckless/unvalidated changes** (five
straight "reviewed, no change warranted" days that correctly **refused to overfit** — the volume floor was
*refuted* with full-history data on 07-16, the ≥80 sizing-cap cut stayed correctly gated, the crossover-cap idea
held at n=8); and **IMP-014 was fully validated** (7 clean live catches across 3 sessions — last week's #1 focus
retired). Last week's "Focus for next week" was **honored to the letter**: IMP-014 proven live, IMP-013 kept at 85
(it simply had no >85 entry to bind on), break-even-stop stayed downgraded, and no entry-logic change was stacked
during the proving window. The single process demerit — and the reason this is a D and not a "process-perfect
losing week" — is that the **broad-adverse-day failure mode RECURRED** (07-07 −$179 → 07-17 −$113, together −$292 =
the bulk of the drawdown): the long-only 5m gate opens multiple longs on intraday bounces that all fade/stop, the
bot still has **no daily-loss / MTM stand-down**, and that fix's own evidence gate ("1–2 more broad-adverse
sessions") is **now met** — a known, now-twice-realized structural gap took real money a second time while the
remedy sat staged. Deferring it once was disciplined; it is now **overdue**. Meaningful record loss + clean risk
control + one overdue structural fix = a solid **D**.

### What worked / what didn't
- **Worked:** process discipline stayed textbook — five correct "no change" calls with **zero overfitting** of a
  brutal tape (the volume floor was actively *refuted*, not just deferred; the ≥80 cap and crossover cap stayed
  correctly gated on insufficient/confounded evidence); **exit infra flawless** (wall-clock flatten every day, all
  fills real, broker flat nightly, books exact to the cent 5/5); **IMP-014 fully proven** (7 down-move stops caught
  mid-session, 0 double-exit/double-Telegram, even enabled INTC's +$22.33 07-14 re-entry); risk control absolute
  (worst trade −1.99%, no breach, no naked); watchlist churn minimal and justified (only earnings parks/re-enables:
  JPM/C, NFLX, TSM/UNH around their prints); service `NRestarts=0`. GOOG's clean full-confirm trend (+$30.87) shows
  the model still works when a real trend appears.
- **Didn't:** the long-only ribbon has **no edge — and now takes real, repeated damage — on broad risk-off / fade
  tapes**, and there is still **no stand-down mechanism**. This regime ran the **entire week** (5 straight soft/
  regime-loss days, 07-17 the broad-selloff climax), and the exact 07-07 failure mode recurred on 07-17. The
  **≥80 confidence band deteriorated further** (80-89 flipped to −$33.73) but IMP-013 (cap 85) can't touch the
  80-85 zone and had **zero bindings** all week — its proving is now bottlenecked on market conditions. The
  **strong-crossover cohort (xo≥0.40) went 0/7, −$170.59** — the top-end crossover concern, still un-actioned.

### Improvements shipped this week
- **None shipped** (0 code changes — five deliberate "no change warranted" days). The week's job was to *prove* the
  two prior-week ships on live data:
- **IMP-014** (c92fdfd, shipped 07-10) — down-move broker-side stop sweep. **Observed: ✅ FULLY VALIDATED** — 7
  clean live catches over 3 sessions (INTC/WMT 07-14, SE/NFLX 07-15, MU/INTC/TSM 07-17), each reconciled mid-session
  at the true fill within a watchdog tick, 0 late-EOD mislabels, 0 double-exit. IMP-012's residual gap is closed and
  proven; last week's #1 focus is retired.
- **IMP-013** (ac195d6, shipped 07-06) — `SIZE_CONFIDENCE_CAP=85`. **Observed: ⚠️ still bound only ONCE ever** — no
  >85-conf entry occurred all week (peak 83.6), so it never engaged; the 90-100 band is unchanged (0W/3/−$144.42)
  while 80-89 deteriorated to −$33.73 (which the 85 cap doesn't reach). Its PF effect **still cannot be judged** —
  proving now bottlenecked on market conditions, not process. Keep at 85.

### Focus for next week
**Ship the broad-adverse-day / daily-loss stand-down — it is now the #1 priority and its evidence gate is MET**
(two qualifying broad-adverse sessions: 07-07 −$179 whipsaw + 07-17 −$113 risk-off selloff, together −$292). Build
it **deliberately** per the 07-17 design brief: track intraday **MTM (realized+unrealized) P&L vs session-open
equity**; when session drawdown breaches ~**−2% to −2.5% of open equity** OR **~3 consecutive full stop-outs**,
**halt NEW entries for the rest of the session** (keep managing/flattening; reset next open). It is a critical-path
change (new intraday equity-tracking state) and a *behavioral* entry change — ship it as the **single** change of
its run, with a fresh test suite, and do **not** rush it reactively. IMP-014 is done (no further action); **keep
IMP-013 at 85** (its proving waits on the market producing a >85 entry — do not lower the cap to force bindings).
Keep **IMP-011 at 0.20**. Continue **watching the strong-crossover (xo≥0.40 / ≥0.70) cohort** (0/7 this week) for a
possible top-end de-rate once n≥15–20 — do not act yet. If the risk-off regime persists, expect the 5m gate to keep
opening low-conviction longs that fade until the stand-down lands — that fix is the week's whole job.

---

---

## Week ending 2026-07-31 — Grade: B

### Stats
- **22 closed trades, 8W / 14L → 36.4% win rate.** Net realized **+$22.93** (avg **+$1.04**/trade).
  **Profit factor 1.16** (gross +$170.67 / −$147.74). Avg win **+$21.33** vs avg loss **−$10.55** →
  **payoff ratio 2.02**. Best **GOOG +$45.11** (07-31), worst **JPM −$23.25** (07-27).
- **Equity $8,927.21 → $8,950.06 (+$22.85, +0.26%).** Reconciles to the DB net within a cent. Book **flat**
  at the close, 0 open positions, nothing carried.
- **Daily curve:** 07-27 **−$78.20** (8 tr, 1W) · 07-28 **$0.00** (0 tr — outage, see below) · 07-29 **+$2.90**
  (4 tr, 2W) · 07-30 **+$37.37** (6 tr, 2W) · 07-31 **+$60.86** (4 tr, 3W). **Monday was the whole drawdown;
  the other four sessions were green.** Max intraweek drawdown −0.88% (07-27) — modest, and recovered.
- **First profitable week since 2026-07-03**, and it lands against a **risk-off, tech-led tape**: Nasdaq
  −2.9% to −4.2%, S&P 500 −1.5% to −1.9% on the week (Perplexity). A long-only trend bot printing +0.26%
  while its universe fell ~3% is genuine relative outperformance, not a rising-tide result.
- **Per symbol:** winners **MU +$40.29**, **INTC +$33.90**, **GOOG +$31.94** (2 tr), **BABA +$18.74** (3 tr),
  **NFLX +$14.89** (2 tr). Losers **JPM −$23.25**, **SE −$18.12** (3 tr, 1W), **AMZN −$17.69**,
  **MSFT −$16.23** (2 tr, 0W), **AVGO −$14.01**, **AMD −$11.49**, **TSLA −$8.07**, **AAPL −$7.21**.
  Semis split hard: MU/INTC carried the week, AVGO/AMD/TSM bled.
- **Exit reasons:** 15 broker-side stop/target **−$40.19**; 7 end-of-day flatten **+$63.12**. Note the sign
  flip vs prior weeks — **the flatten bucket is now the profitable one**, because the trail lets winners run
  into the close instead of stopping them out early.
- **Crossover bands:** **<0.25 → 7 tr, −$60.45, 1W** (the week's worst cohort, all pre-IMP-020) ·
  0.25–0.30 → 3 tr, **+$26.41** · 0.30–0.40 → 6 tr, +$2.29 · 0.40–0.55 → 3 tr, −$1.78 · **0.55+ → 3 tr,
  +$56.46, 2W**. Clean story this week: the bottom band lost, the top band won.
- **Confidence (this week):** 60-69 → 10 tr, **−$84.38, 1W** · 70-79 → 9 tr, **+$96.99, 6W** · 80-89 → 3 tr,
  +$10.32. **All-time:** 70-79 **+$134.97** (78 tr, 51%) remains the only profitable band; 60-69 −$95.78
  (135 tr, 41%), 80-89 −$43.45 (25 tr, 44%), 90-100 −$144.42 (3 tr, 0%).
- **Service: `NRestarts=0`, `active`, no crash, no naked carry, no risk-limit breach, books exact every
  trading day.** Only benign noise: two IEX websocket reconnects (07-29 11:53, 07-30 16:53), both self-healed
  with zero trade impact. **One real availability failure — 07-28, below.**

### Grade rationale
**A profitable week (+0.26%) against a −3% tape, with the bot's biggest structural fix validating hard — held
to a B, not an A, by a self-inflicted lost session and a mildly confounded change cadence.**

It is clearly **not a C**: the week was profitable *and* the rules were followed — no risk-limit breach, no
naked overnight, books exact to the cent every day, worst trade −$23.25, and the one lever the daily review
was tempted by (raising the entry threshold 60→65/70) was **replay-tested and correctly REJECTED** on 07-27
for failing the both-halves robustness bar. That is the discipline this routine exists to enforce, applied
without being asked.

It is **not an A** for two honest reasons. First, the rubric's A requires **"no system errors"** and there
was one: **07-28 lost an entire trading session** — a single un-retried SQL Server login timeout at the
06:04 cold start disabled persistence *and* collapsed the watchlist to the 3-name `NFLX, BIRD, WPM` env stub,
so the bot sat out a full day recording nothing. It degraded gracefully rather than crashing, and it was
root-caused and fixed the same evening (IMP-019) — but a lost session is a lost session, and the brittleness
was self-inflicted, not external. Second, **three code changes landed in eight days** (IMP-017/018 on 07-25,
IMP-019 on 07-28, IMP-020 on 07-30), and **IMP-020 shipped inside IMP-018's stated ≥2-week observation
window** — so the two most recent sessions confound the very measurement IMP-018 needs. Each change was
individually well-argued; as a *set* they were shipped slightly faster than they can be evaluated.

What earns the B rather than a lower grade is that the week's improvements **compounded instead of cancelling**.
IMP-018 (the trail) is doing real, measurable work — payoff ratio 1.01 → 2.53 across the pre/post cohorts,
average loss compressed −$22.44 → −$10.55, 277 ratchet events vs 2 trail exits in the previous 219 trades.
IMP-019 fired in anger on 07-31 (two retries, then success) and directly rescued what would have been a second
zero-trade day into the week's best session, +$60.86. IMP-016's stand-down had its first genuine trips. That
is a detect → fix → validate loop closing within one week, on live data, three separate times.

**Process demerit carried in from last week, recorded here because it is an audit-trail hole:** the 07-25 run
shipped **two** IMPs (IMP-017 *and* IMP-018) in a single run, against this routine's explicit one-change-per-run
rule, and **wrote no `weekly-review.md` entry at all** — it updated IMP-016's observed-effect line "(weekly
07-24)" and stopped. So this week began with **no recorded weekly focus to be held to**, and the most recent
standing focus was the 07-17 entry's. That focus — ship the daily-loss stand-down — *was* honored, by IMP-016
on 07-21. Grading against a missing document is not possible; the gap is noted so it is not repeated.

### What worked / what didn't
- **Worked:** **IMP-018 is the story of the week** — the exit structure finally functions; the bot now has a
  way to *keep* a winner (GOOG +$45.11, BABA +$23.52 both rode the trail into the close) and to cut a loser
  small (AAPL held to −0.31% where the flat stop gave ~−$47). **IMP-019 proved itself in 3 days** with a
  measurable save. **Evidence discipline was excellent**: the entry-threshold raise was actively refuted with
  the replay harness rather than shipped on a plausible-looking confidence table, and IMP-020 was backed by
  two independent methods agreeing (DB attribution −$165.93 vs replay +$168). **Risk control absolute** —
  no breach, no naked, worst trade −1.3%. **Watchlist churn minimal and justified** (earnings parks only:
  MSFT for 07-29, AAPL/AMZN for 07-30). Service `NRestarts=0`.
- **Didn't:** the **07-28 zero-trade session** — one transient DB connect took the whole day, and the
  degradation was *silent* (one journald ERROR no human sees). The Telegram-page-on-fallback backlog item is
  now clearly under-prioritised. The **stand-down's value is still unproven and one trip looks costly**:
  07-27 tripped after all 8 entries were already open (**saved $0**), 07-30 tripped 30 min after the entry
  cluster and then held the bot flat for ~5 hours of a **green** session. The **60-69 confidence band remains
  the core leak** (−$84.38 this week, 1W/10; −$95.78 all-time over 135 trades) and the obvious fix is
  replay-refuted — meaning the problem is real but the cheap remedy is wrong. **80-89 still inverted**
  all-time (−$43.45). And **MSFT went 0/2 for −$16.23** on the week.

### Improvements shipped this week
- **IMP-019** (951ea7f, 07-28, daily) — bounded retry on startup DB init. **Observed: ✅ VALIDATED LIVE** —
  fired 07-31 06:10 (attempts 1/3 and 2/3 failed, 3rd succeeded), bot came up on the full 18-symbol
  `dbo.watchlist` instead of the 3-name stub; turned a would-be second zero-trade day into **+$60.86**.
- **IMP-020** (08b9855, 07-30, daily) — `MIN_CROSSOVER` 0.20 → 0.25. **Observed: ⏳ PENDING (1 session).**
  Floor binds correctly (min crossover 07-31 = **0.2701**) and did **not** over-filter (4 entries, no
  zero-trade collapse). The band it removes lost **−$60.45 (1W/7)** this week right up until removal. But
  n=4 post-change — Friday is far more plausibly IMP-018 plus tape. **Needs ≥1 more week.**
- **IMP-018** (6a015a8, shipped 07-25, evaluated here) — trail 2% → 1.25%. **Observed: ✅ WEEK 1 OF 2,
  STRONGLY CONFIRMED** — payoff 1.01 → **2.53**, avg loss −$22.44 → **−$10.55**, PF 0.69 → 2.53 on the
  pre/post cohorts, 277 ratchet events. Caveat: n=14 post-change, and win rate *rose* to 50% rather than
  falling as predicted, so some of the gain is tape. **Second clean week required before calling it done.**
- **IMP-016** (af56b67, shipped 07-21, evaluated here) — broad-adverse stand-down. **Observed: ✅ mechanism
  proven (2 first genuine trips), ⚠️ value unproven** — ~$0 saved across both trips, with real
  opportunity cost on 07-30. See its log entry for the full accounting.

### Strategy verdict
**Viable and improving — upgraded from "structurally losing" to "marginally positive, cause identified" —
but the edge is in the EXIT, not yet in the ENTRY.** The honest read: IMP-018 fixed an arithmetic defect that
*guaranteed* a loss (a trailing stop set equal to the hard stop, so it never engaged and the payoff ratio sat
at 1.01 against a sub-50% win rate). Removing that defect is worth roughly the whole turnaround. The entry
signal itself still shows **no demonstrated edge**: 36.4% win rate this week, 60-69 confidence still bleeding
over 135 all-time trades, confidence still inverted above 80. The bot is now profitable *because it manages
trades well*, not because it picks them well. That is a legitimate way to make money and it is a real
improvement — but it must not be mistaken for signal alpha, and one green week on n=22 is not proof of
anything. Verdict: **keep running, keep it on paper, protect IMP-018's second observation week.**

### Focus for next week
**Protect the measurement — this is a "let it run" week, not a shipping week.** IMP-018 needs its **second
clean week** and IMP-020 needs its **first full week**; both are mid-window. Do **not** touch the exit
structure, `TRAIL_PERCENT`, or `MIN_CROSSOVER`, and do **not** raise `MIN_CROSSOVER` toward 0.30 (the
0.25–0.30 band printed **+$26.41** this week — the first live sign that the further raise, already rejected,
would have been actively wrong). Judge both on **payoff ratio and PF, never win rate**.
Ranked candidates for the one change, if any is warranted:
1. **Instrument the IMP-016 stand-down before retuning it** (highest value, zero risk). It has tripped twice
   for ~$0 saved and plausibly cost real upside on 07-30. Log every entry candidate **suppressed while
   latched** and its would-be outcome, so the next review can *price* the consecutive-losses arm instead of
   guessing. Pure observability — no behavioural change, safe to ship inside the observation window.
2. **Telegram page on watchlist-fallback / persistence-off** (backlog, now well-evidenced by 07-28). Makes a
   silent whole-session outage visible. Side-channel only.
3. **(analysis, do NOT ship)** The 60-69 confidence leak. It is the largest remaining structural loss
   (−$95.78 / 135 tr) and the naive threshold raise is **replay-refuted** — so the work is to find *what
   distinguishes* the winners inside that band (the volume sub-score gradient is the standing hypothesis),
   not to re-run a rejected experiment. Accumulate evidence; act only when a robust both-halves result exists.
4. **(watch, do not act)** 80-89 inversion; flat non-ATR stop; MSFT 0/2 this week.
**Risk posture unchanged and non-negotiable:** position size, loss limits, kill switch and the paper-only
setting stay exactly as they are. Any move toward live trading requires explicit human approval — not this
routine's call. **Next week's scheduled catalysts:** the **jobs report / NFP** is the dominant event, plus
Fed-speaker follow-through after the 07-29 FOMC and continued mega-cap earnings digestion — expect
gap-sensitive opens and headline-driven reversals, exactly the tape that produced 07-27's 1/8 session.

