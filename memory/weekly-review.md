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

---

## Week ending 2026-08-07 — Grade: C

### Stats
- **13 closed trades, 10W / 3L → 76.9% win rate.** Net realized **+$125.89** (avg **+$9.68**/trade).
  **Profit factor 3.67** (gross +$173.11 / −$47.22). Avg win **+$17.31** vs avg loss **−$15.74** → payoff
  **1.10**. Best **AVGO +$55.35** (+2.24%, 08-04), worst **AMZN −$18.49** (−0.93%, 08-03).
- **Equity $8,950.04 → $9,075.74 = +$125.70 (+1.40%).** Reconciles to the DB net within $0.19. Book **flat**
  every single night, 0 open positions, nothing carried. **Best week by percentage since the book began.**
- **Daily curve:** 08-03 **−$1.29** (3 tr) · 08-04 **+$139.38** (7 tr, **7W/0L**) · 08-05 **−$12.20** (3 tr) ·
  08-06 **$0.00** (0 tr) · 08-07 **$0.00** (0 tr). Max intraweek drawdown **−0.01%**. No down day worse than
  −$12.20.
- **⚠️ Read the curve before believing the headline. The week IS one session.** Strip 08-04 and the other
  four sessions are **6 trades, −$13.49, 3W/3L**. 08-04 was the strongest trending tape in the 38-session
  sample (QQQ **+2.15%** open→close) and the long-only book went 7/7 on it. **+1.40% on the week is a beta
  print, not an alpha print**, and the 76.9% win rate / PF 3.67 are the statistics of a single lucky day, not
  of an edge. This is the same fact IMP-022 was built on, seen from the happy end of the distribution.
- **Two zero-trade sessions (08-06, 08-07)** — 40% of the week. Both were IMP-022 vetoes and both were
  correct (below). Friday's blank was **not** mostly the gate, though: 48 rejections broke down as
  **23 confidence-floor, 21 crossover-floor, 4 market-gate**. The signal engine was healthy and productive
  on both blank days (25 candidates scored 08-06, 48 rejection events 08-07) — these were not dead feeds.
- **Per symbol:** **INTC +$65.22 (3 tr, 3W)** — best name in the book and it carried the week; **AVGO
  +$55.35**, **NVDA +$16.72**, **AMD +$10.91**, **MSFT +$4.50**, **TSM +$4.04**. Losers: **MU −$12.36
  (4 tr, 2W)** — most-traded name and net negative; **AMZN −$18.49**.
- **Exit reasons:** 5 end-of-day flatten **+$104.68 (5W/0L)**; 8 broker-side stop/trail **+$21.21 (5W/3L)**.
  **83% of the week's P&L came from positions that simply survived to the close** — on 08-04. The trail
  produced $21 across 8 fills. Worth noting against IMP-021's thesis.
- **Confidence (this week):** 60-69 → 6 tr, +$8.52, 4W · 70-79 → 4 tr, **+$87.02, 4W** · 80-89 → 3 tr,
  +$30.35, 2W. **All-time (`vw_confidence_outcome`):** 70-79 **+$221.99** (82 tr, 53.7%) is still the only
  profitable band; 60-69 **−$87.27** (141 tr, 41.8%), 80-89 **−$13.10** (28 tr, 46.4%), 90-100 **−$144.42**
  (3 tr, 0%). The inversion above 80 narrowed slightly this week but the all-time shape is unchanged.
- **Service: `NRestarts=0`, `active`, zero crashes, zero naked carry, zero risk-limit breaches, books exact
  to the cent every trading day.** The 149 `TimeoutError` tracebacks in the 7-day journal all belong to
  pid 3809572 on **Aug 01** — last week's process, outside this window. This week's only errors were **three
  Alpaca-side failures on 08-05** (one `ECONNREFUSED`, two nginx `500`s reading a fill price for MU order
  `24fbc144`) — **broker outage, correctly swallowed, no trading impact**. Clean week operationally.
- **Market context (Perplexity `sonar-deep-research`, truncated mid-report — see note):** the week was
  "highly regime-dependent — Monday and Tuesday, with record-adjacent index levels, a strong risk-on bid and
  broad participation, were **unusually friendly to multi-timeframe trend-following**, while Wednesday
  through Friday" turned "increasingly choppy, catalyst-driven" with reversals, on rising long-end yields,
  volatile oil and a July jobs report that **surprised to the downside**. **The bot's P&L maps onto that
  description almost exactly** — it made all its money Tue, gave a little back Wed, and declined to trade
  Thu/Fri. The regime read and the equity curve agree, which is the single most reassuring thing in this
  review.

### Grade rationale
**A +1.40% week — the best on record — graded C, because the rubric's C is "profitable but rules broken,"
and the rule that was broken was the one this routine wrote down seven days ago in bold.**

Last week's entry set an unambiguous focus: *"Protect the measurement — this is a 'let it run' week, not a
shipping week… Do **NOT** touch the exit structure, `TRAIL_PERCENT`, or `MIN_CROSSOVER`."* IMP-018 needed its
second clean week; IMP-020 needed its first full one. **On Monday — session one — IMP-021 changed
`TRAIL_PERCENT` into a two-stage trail.** That is precisely and specifically the forbidden change, and it
was made by a review that demonstrably *had read* the weekly (its own item 3 cites "the weekly review
explicitly deferred its verdict for a full week" as its reason for **not** touching the confidence bands).
So the constraint was understood, applied to entry filters, and overridden on the exit structure. Then
**IMP-022 shipped Wednesday** — a second, entry-side filter, landing while IMP-020 was still mid-window and
IMP-021 was two sessions old. **Three IMPs in four sessions during a declared measurement-protection week.**

The cost is not hypothetical, and it is the reason this is a C and not a B. **IMP-020 has now never received
a clean verdict and never will** — it was confounded first by IMP-021, then by IMP-022, then by two blank
days. **IMP-021's own window was destroyed by IMP-022** two sessions after it shipped: it has exactly **one**
qualifying trade of live evidence (INTC 08-05, +$5.25) and cannot be judged. Each change was individually
well-argued, evidence-backed and multi-window tested — and as a *set* they left the bot **less measurable
than it was on Monday**. That is the exact failure mode this routine exists to catch: improvements that
compound in code but cancel in knowledge.

It is emphatically **not a D or an F**: no risk-limit breach, no naked position, no crash, no sizing
violation, worst trade −$18.49 (−0.93%), books reconciled to the cent on all five days, `NRestarts=0`, and
the one real error burst was Alpaca's, absorbed cleanly. Nor was the week's work sloppy — the standard of
*analysis* was the highest yet recorded (the rejected flat-trail tightening, the MFE-capture table, the
gate ON/OFF counterfactual pricing, the ATR premise re-derivation). It is not a B because "flat-to-positive,
**minor** process slips" does not describe overriding an explicit, specific, one-week prohibition on day one
and then shipping twice more.

**Held at C rather than lower by the single best piece of evidence this bot has ever generated** — the
IMP-022 four-window A/B below. A week that both breaks the rules and produces the strategy's first
robustly-validated edge is genuinely a mixed week, and C is what mixed looks like.

**Process credits, recorded so the grade is not read as a verdict on the work's quality:** ① the 08-03
review **actively refuted** a seductive change (flat `TRAIL_PERCENT` → 0.6%, +$24.58 on 30 days) by testing
45 and 60-day windows where the ranking reverses, and wrote the methodology rule "**no replay-derived
parameter ships on a single window; require ≥3 windows agreeing in sign**" — then held IMP-021 to it. ② the
08-06 review caught that **the backtest harness disagreed with the live watchlist** and fixed it (IMP-023)
rather than trusting a convenient result. ③ the 08-05 review **downgraded its own long-standing backlog
item** (the "flat non-ATR stop") after re-deriving the premise and finding it much weaker than its
reputation, and separately established that **`STOP_LOSS` is structurally unreachable** behind the trail, so
tuning it is a no-op. Correcting the record against your own prior conclusions is the rarest good habit
here, and it happened three times in five days.

**Operational demerits outside the repo (not graded, but escalating):** the **08-03 pre-market died `rc=1`**,
the **08-04 post-close routine never ran**, and the **08-05 pre-market never ran** — three misses in three
sessions. Direct consequence: **AMD was parked 08-04 for earnings and stayed `enabled=0` for a full extra
session** because the run that was supposed to re-enable it did not happen, and there is **no research-log
entry for 08-03 or 08-05**. The scaffold lives in `/root/claude-routines`, outside this repo. The 08-06 and
08-07 runs executed normally and ABNB was correctly re-enabled Friday (watchlist now **20 enabled**,
QQQ among them) — but this needs an operator look, not another week of flagging.

### What worked / what didn't
- **Worked — IMP-022 is the real result of the week, and it is a big one.** Tested through the
  IMP-023-corrected harness across four windows, the market gate wins on **net, win rate, profit factor and
  average-per-trade simultaneously, in every window**: 60d **+$494.08 / 53.2% / PF 1.54** (109 tr) vs
  **+$252.33 / 46.0% / PF 1.15** (187 tr) with it off; 30d **+$241.91 / PF 1.64** vs **+$6.12 / PF 1.01**.
  Gate-ON win rate is **53.1 / 53.2 / 53.3%** across 5/30/60 days — a stability the entry signal has never
  shown. It cuts trade count 42–46% and it is the **only change in this bot's history to clear the
  ≥3-window robustness bar**. Live: it blocked 8 qualifying entries across 08-06/08-07 and the 08-06
  counterfactual priced the saving at ≈ **+$47**.
- **Worked — IMP-023 paid for itself in under 24 hours.** Every one of tonight's eight replay runs printed
  `symbols=20 (dbo.watchlist)`. Before the fix they would have used the three-name `NFLX,BIRD,WPM` stub,
  which **contains no QQQ**, so the gate would have failed open in *both* arms and returned identical ON/OFF
  results — and this review would have concluded "IMP-022 does nothing, revert it." **The week's
  highest-leverage change was not a strategy change; it was fixing the instrument.**
- **Worked — risk and reliability were flawless.** Flat every night, exact reconciliation daily, no crash,
  no 422s across ~25 stop replaces on 08-05, a genuine Alpaca outage absorbed without trading impact.
- **Didn't — the week's P&L is one session, and the review must not be seduced by it.** 08-04 = +$139.38 of
  a +$125.89 week. Six trades outside it, net −$13.49. **77% win / PF 3.67 are artifacts of n=13 with one
  outlier day** and should not be quoted as evidence of anything.
- **Didn't — the shipping cadence destroyed two measurement windows** (IMP-020's, IMP-021's) and produced
  the only genuinely unresolvable items on the board. See the grade rationale.
- **Didn't — two zero-trade days mean the week bought almost no information** about the questions that
  actually matter: signal quality, the confidence inversion, exit capture, sizing. A filter that never opens
  avoids losses but generates no knowledge, and 40% of the week was spent that way. This is IMP-022's real
  cost and it is now visible.
- **Didn't — MU was the most-traded name (4 tr) and lost money (−$12.36)**, including the week's
  highest-confidence entry (80.67 on 08-05, −$18.34). **Confidence remained inverted at the top for a third
  straight week.** Also unaddressed: whole-share quantisation put **qty=1 ($924)** on MU against $36k buying
  power, which flattens the confidence→size curve to nothing on $900+ names.

### Improvements shipped this week
- **IMP-022** (08-05, daily) — market-regime gate; no new long unless QQQ's 5m ribbon is bullish.
  **Observed: ✅ VALIDATED, four windows, strongest result in the bot's history. KEEP — DO NOT TOUCH.**
  Its own **>80%-block tripwire is formally hit** (8 of 8 qualifying entries blocked, 100%, over its two live
  sessions) and is being **deliberately not actioned**: both counterfactuals were negative, both blank days
  were correct, and two sessions is not the week the tripwire specifies. **Do not switch the proxy to SPY on
  this evidence.** Re-read the tripwire after a week containing at least one up-tape session.
- **IMP-021** (08-03, daily) — two-stage trail, tighten to 1.0% once +1.0% in profit.
  **Observed: ⏳ MECHANISM CONFIRMED (n=1), EFFECT UNMEASURED — verdict deferred, window destroyed.**
  Proven live exactly once (INTC 08-05: final stop 101.50 is consistent only with the 1.0% width, ≈ +$5.25,
  17 replaces, zero 422s). The week's win-rate rise is **not** attributable to it — 5 of 08-04's 7 winners
  exited on the flatten and never touched the trail. **Do not re-tune the trail.** Needs two clean weeks.
  *Also the change that violated last week's explicit prohibition — see grade rationale.*
- **IMP-023** (5cc500d, 08-06, daily) — replay resolves its universe from `dbo.watchlist`.
  **Observed: ✅ VALIDATED — prevented this review from reverting IMP-022.** No P&L by construction; the
  highest-value change of the week regardless.
- **Did they compound or cancel?** **IMP-022 and IMP-023 compounded** — the harness fix is what made the
  gate's validation possible, and together they are the first genuine step forward since IMP-018.
  **IMP-021 and IMP-022 cancelled in measurement terms**: the gate starved the trail change of the data it
  needed, two sessions after it shipped. Net for the week: **one strong validated change, one unmeasurable
  change, one excellent tool fix — and two dead observation windows.**

### Strategy verdict
**VIABLE, and upgraded: for the first time the bot has a filter with demonstrated, robust, out-of-window
edge. But the edge is in deciding WHEN NOT TO BE LONG — it is still not in the signal.**

Last week's verdict was "the edge is in the exit, not yet in the entry." That is now too generous to the
entry *signal* and not generous enough to the *system*. The IMP-022 A/B is unambiguous: removing longs taken
while QQQ's ribbon is not bullish takes 60 days from **+$252 / PF 1.15 / 46% win** to **+$494 / PF 1.54 /
53.2% win** on 42% fewer trades. That is a real, robust, four-window improvement, and it is the first thing
this bot has ever produced that survives its own methodology bar. Combined with IMP-018's trail, the system
now has two working parts: **it manages trades well, and it declines to trade in the wrong regime.**

**What it still does not have is signal alpha, and this week added nothing to that column.** The 60-69
confidence band remains the largest structural leak (**141 trades, 41.8%, −$87.27** all-time); confidence
is still inverted above 80 (**−$13.10** at 80-89, **−$144.42** at 90-100); the week's highest-confidence
entry was its second-worst trade. The honest summary: **the strategy is profitable because of two exposure-
management filters bolted onto an entry signal that has never demonstrated an edge.** That is a legitimate
and improving way to make money on paper — but every remaining unit of upside is in the signal, and the
signal has not been touched because it cannot be safely touched until the current changes are measured.
**Keep running, keep it on paper, and let it trade long enough to learn something.**

### Focus for next week
**SHIPPING FREEZE. This is the "let it run" week that last week asked for and did not get.** The bot has
**two live sessions of IMP-022, one qualifying trade of IMP-021, and no verdict at all on IMP-020**. It
traded on three of five days. There is not enough live data on the board to justify any behavioural change,
and a fourth change in six sessions would repeat exactly the mistake this entry grades down.
**Explicit instruction to the daily reviews 08-10 → 08-14: default to analysis-only. Ship code only if a
NEW failure appears — a crash, a naked position, a reconciliation break, a silent outage. Do NOT ship a
tuning change, and specifically do NOT touch `TRAIL_PERCENT` / the two-stage trail, `MIN_CROSSOVER`,
`MARKET_FILTER_SYMBOL`, `ENTRY_THRESHOLD`, or the confidence weights.** If a change looks compelling,
write it up with its evidence and hand it to next Friday.
- **The one measurement that matters next week:** does IMP-022 let the bot trade on an up-tape? Its tripwire
  reads >80% blocked *for a week*; it is at 100% over two sessions. **Count gate-open bar % and blocked-entry
  count every day.** If a genuinely bullish session still produces zero entries, the QQQ proxy *is* too
  strict and SPY becomes a live candidate — but that verdict belongs to next Friday, on a full week.
- **Permitted exception (the only one):** the **pure-observability** item both this and last week's entries
  have now ranked #1 — have `bot.report` emit gate-open %, blocked-entry count and their confidences
  automatically, instead of the weekly reconstructing them by hand from journald. Zero behavioural change,
  zero measurement disturbance, and it makes next Friday's IMP-022 verdict evidential rather than anecdotal.
  Ship it only if a session is otherwise quiet.
- **Escalate to the operator (outside this repo):** three routine misses in three sessions (08-03 `rc=1`,
  08-04 post-close absent, 08-05 pre-market absent) cost a research-log gap and left AMD parked an extra
  day. `/root/claude-routines` needs a look.
- **Standing, do not act yet:** the 60-69 confidence leak and the >80 inversion — **still the largest
  remaining structural loss and still the first candidate once IMP-022 has a full week.** Whole-share
  quantisation destroying the size curve on $900+ names (MU/AVGO/TSM/MSFT/NFLX) — needs its own study, and
  note it cannot be fixed by sizing alone (Alpaca brackets require whole shares). `STOP_LOSS` is a no-op to
  tune (structurally unreachable behind the trail) — do not spend a session on it. The "flat non-ATR stop"
  item stays **downgraded** (premise re-derived 08-05).
- **Ops gotcha, carried forward:** the service's log timestamps are **WIB (UTC+7)** since the 2026-08-02 TZ
  change, while `dbo.trades`, `systemctl` and these reviews are **UTC**. A review that reads journal
  timestamps as UTC will place trades outside market hours and misdiagnose.
- **Risk posture unchanged and non-negotiable:** position size, loss limits, kill switch and paper-only stay
  exactly as they are. Any move toward live trading requires explicit human approval — not this routine's
  call.
- **Next week's scheduled catalysts (08-10 → 08-14):** **July CPI on Wednesday is the dominant event**
  (consensus headline ~3.4% YoY, core ~2.5%), with **PPI Thursday** and **retail sales Friday**. Note the
  unusual asymmetry — with the July jobs report soft and the Fed's risk skewed toward *hikes* rather than
  cuts, a hot core print would raise September hike odds and produce exactly the gap-and-reverse tape that
  IMP-022 should veto. Earnings are in a **lull** (AMAT, CSCO, CRWV, SMCI, JD) — relevant because the book
  is semi-heavy. **Watch semiconductor volatility**: the SOX is +70% YTD but **−17% from its late-June high**
  and swinging hard daily, and INTC/MU/AVGO/NVDA/TSM/AMD are the core of this watchlist. Expect the gate to
  keep trade count low around Wednesday.

---

## Week ending 2026-08-14 — Grade: B

### Stats
- **DB (closed, Mon 08-10 → Fri 08-14):** **12 trades, 6W/6L → 50.0% win**, net **+$44.24**, **PF 1.54**,
  avg win **+$20.99** / avg loss **−$13.62** (payoff 1.54). Best **MU +$56.24** (08-13), worst
  **INTC −$23.19** (08-13).
- **⚠️ The DB is one trade short, and the correction is favourable.** The **08-12 MU winner (+$4.46)**
  never persisted — the entry INSERT hit a dead socket (see IMP-028 below), so the row does not exist.
  **True week: 13 trades, 7W/6L → 53.8% win, net +$48.70, PF 1.60.** Quote the corrected figures.
- **Equity is the arbiter and it agrees: $9,075.74 (Fri 08-07 close) → $9,123.87 = +$48.13 (+0.53%)**,
  within $0.57 of the corrected DB net (valuation rounding). All cash, **0 positions, 0 open orders**.
- **Zero losing days — the equity curve did not go down once all week:** 9,075.74 → 9,085.28 (08-10)
  → 9,085.28 (08-11) → 9,089.68 (08-12) → 9,123.87 (08-13) → flat (08-14). **Max drawdown ≈ $0.**
- **By day:** 08-10 **+$9.71** (4 tr) · 08-11 **$0** (0 tr) · 08-12 **+$4.46** (1 tr, unrecorded) ·
  08-13 **+$34.53** (8 tr) · 08-14 **$0** (0 tr).
- **By symbol:** TSLA +$29.16 (1) · ABNB +$26.21 (1) · MU +$24.04 (3, +$28.50 with the lost 08-12 row) ·
  BABA +$9.30 (1) · NVDA −$4.23 (1) · AMD −$10.49 (1) · AVGO −$11.60 (1) · **INTC −$18.15 (3)**.
- **Confidence vs outcome (all-time, `vw_confidence_outcome`) — still inverted at the top:**
  70-79 **+$250.84** (87 tr, 54.0%) · 60-69 **−$58.22** (146 tr, 41.8%) · 80-89 **−$26.75** (30 tr, 46.7%)
  · **90-100 −$144.42 (3 tr, 0% win)**. Third straight week the score fails to rank.
- **Third consecutive profitable week:** wk31 +$22.93 · wk32 +$125.89 · wk33 **+$48.70**.
  **All-time remains marginal: 266 trades, 45.9% win, net +$21.45, PF 1.009.**
- **Service: clean. `NRestarts=0`, zero crashes, zero 422s, one uptime spanning 08-13 11:37 → now.**
  The only ERROR records all week are the 08-12 persistence failure and the 08-13 stand-down notice.

### Grade rationale
**B — a quietly good trading week and the best *analytical* week this bot has ever had, held back from
A by a delivery failure that left the week's most important fix unshipped and the improvement log
carrying a false statement.**

**Results support a high grade but not on their own merits — the numbers are small.** +$48.70 on
+0.53% equity across 13 trades is real but thin, and n=13 across two effective trading days is not a
sample. What lifts the results half a grade is *shape*, not size: **no losing day, no drawdown, no
naked position, no crash, no risk breach, and a risk control that fired correctly and reset correctly**
(the 3-consecutive-loss stand-down tripped 08-13 19:25 and cleanly re-enabled for 08-14 — verified in
the journal, not assumed). A week that makes money without ever risking much of it is what this bot is
supposed to look like.

**Process is where this week genuinely excelled, and it deserves saying plainly.** Last week imposed a
shipping freeze on trading logic. **It was honored, and honored intelligently.** On 08-13 the daily
review had two live strategy candidates it had motive to ship — tighten the initial stop 2.0% → 1.25%,
and raise `MIN_CROSSOVER` 0.25 → 0.30 — both apparently supported by that session's own trade-by-trade
evidence and by damning live bucket statistics (the 0.25–0.30 crossover band is the biggest cohort and
the biggest loser, −$242.76 all-time). **Both were tested across four replay windows and both were
refuted, and neither shipped.** The stop candidate failed the ≥3-agreeing-windows rule (0/+/+/−); the
crossover floor was *unanimously negative* in all four windows. It further established *why* the stop
study was wrong — the trail ratchets on the first candle after entry, so the 2% initial stop is nearly
vestigial and the study priced a rule the live system never executes. **This is the discipline this bot
has historically lacked: it had the evidence, the authority and the temptation to tune, and it correctly
concluded the tuning was an artifact.** All four IMPs this week (025/026/027/028) were instrumentation
or data-integrity fixes with **zero behavioural change to entry, exit or sizing.** The freeze held.

**What costs the A is delivery, not judgement.** **IMP-028 — the fix for the defect that erased an entire
session from `dbo.trades` while the broker held a real filled position — was written, tested and then
never shipped.** It is uncommitted (since 08-13 21:43), **never deployed** (`ActiveEnterTimestamp`
08-13 11:37:48, MainPID 805070, `NRestarts=0` — the running process predates the edit by ten hours), and
was **never recorded** in `memory/improvement-log.md`, despite the 08-13 review stating *"Details in
`memory/improvement-log.md`."* That sentence was false, and it is the part that matters most: an
improvement log that records changes which are not running is worse than no log, because every
subsequent review reasons from it. The top-priority open defect is still live in production, and the
next routine to read the log for a free number would have reissued 028. I have written the entry, marked
it NOT DEPLOYED, reserved the number, and handed the deployment to tonight's daily review.
This is a **C-grade process failure sitting inside an A-grade process week**; the rest of the record —
exact broker reconciliation every session, non-vacuity checks on new tests, refusals documented so they
are not re-proposed — is why the week nets out at B rather than C.

**Not counted against the week:** the Perplexity `sonar-deep-research` call returned empty (1 byte) and
the fallback `sonar` was unreachable from this host; regime was sourced from IEX daily bars instead,
which the 08-10 review already established as the authoritative substitute after `sonar` returned a
prior session's record close as that day's tape. Zero-trade days on 08-11 and 08-14 were **correct
refusals, not outages** — 15 and 25 logged candidate rejections respectively, on a tape that fell both
days.

### What worked / what didn't
- **✅ Worked — the market gate (IMP-022), and this week finally answers last week's #1 question.**
  Last week asked: *does the gate let the bot trade on an up-tape, or is it a permanent off-switch?*
  **Answered decisively: it is not an off-switch.** Across the week the gate accounted for **7 of 141
  refusals (5.0%)** — the tripwire is >80% and it is nowhere near it, down from 100% over its first two
  sessions. On **08-13, the week's only genuinely bullish intraday session (QQQ +0.98% open→close), the
  gate blocked exactly ZERO candidates and the bot took 8 trades for its best day.** The proxy is not
  too strict. **Do not switch `MARKET_FILTER_SYMBOL` to SPY.** The tripwire is formally retired.
- **✅ Worked — and the gate is additive, re-validated in two fresh windows.** Replay (post-IMP-024,
  honest close-keyed semantics, 20 symbols from `dbo.watchlist`):

  | window | gate ON | gate OFF | gate edge |
  |---|---|---|---|
  | 5d (08-09→08-14) | 12 tr · **+$79.61** · 58.3% · PF 1.99 | 18 tr · +$58.61 · 50.0% · PF 1.45 | **+$21.00** |
  | 10d (08-04→08-14) | 14 tr · **+$37.68** · 50.0% · PF 1.31 | 29 tr · **−$53.84** · 41.4% · PF 0.80 | **+$91.52** |

  At 10 days the gate is **the difference between a profitable book and a losing one**, and it does it on
  half the trades. That is now **four independent windows agreeing in sign** (60d from 08-07, plus 5d
  and 10d here). IMP-022 is the most robust thing this bot owns.
- **✅ Worked — the exit structure, on the only day it was given something to work with.** 08-13's two
  real movers were both converted: **MU peaked +4.23% and banked +3.00% (71% capture)**; **TSLA peaked
  +2.45% and banked +1.75% (71% capture)**. Both were held through hours of noise and cut on the ratchet,
  not the clock. IMP-018 + IMP-021 doing exactly what they were specified to do.
- **✅ Worked — reconciliation caught what the DB hid.** On 08-12 the DB said "no trades"; the broker said
  one trade, and it won. Only the broker-vs-DB step in the daily routine found it. **The lesson from that
  session is the week's most durable: this bot's evidence base is not self-validating.**
- **❌ Didn't — the entry signal, for the fourth consecutive week, and it is now precisely localised.**
  On 08-13, **4 of 8 entries had MFE of +0.12 / +0.28 / +0.38 / +0.42%** — they never traded meaningfully
  above entry and were cut at −0.9% to −1.2%, **well inside the 2% stop**. No stop was hit, nothing
  gapped, nothing slipped, and the tape was *up*. That is not exit structure and not regime; it is entry
  selection. The same shape drove 08-10 (three of four trades peaked at ≈+0.6% against a 1.25% give-back).
- **❌ Didn't — confidence is still inverted at the top, and the sizing curve scales *with* it.** 08-13's
  two highest-confidence entries (83.4 MU, 81.2 INTC) returned **−$18.00** and +$4.34, while conf 66.4
  TSLA made +$29.16 and conf 77.9 MU made +$56.24. All-time the 90-100 band is **0 for 3, −$144.42**.
- **❌ Didn't — one expensive, instructive gate miss.** On **08-14 the gate blocked AMD twice, at conf
  76.5 and conf 91.2** (the highest-confidence candidate of the entire week), because QQQ's 5m ribbon was
  not bullish. **AMD closed +5.48% that day (487.67 → 514.39, 6.38% range) — the cleanest single-name
  intraday trend of the week.** This is the market-gate's structural cost made concrete: a market-wide
  filter vetoes idiosyncratic single-name strength. **It is a real cost and it is still worth paying** —
  the same gate is what produced the +$91.52 edge at 10 days, and the 90-100 confidence band it blocked
  is 0-for-3 lifetime. Logged as the standing argument *against* the gate so it is not re-discovered as
  if it were new; it does not currently outweigh four windows of evidence.
- **❌ Didn't — the week bought less information than its five sessions suggest.** Two blank days and a
  one-trade day mean **12 of 13 trades came from two sessions**, and 8 of those from one. Any statistic
  quoted from this week is really a statistic about 08-10 and 08-13.

### Improvements shipped this week
- **IMP-025** (82d1914, 08-10, daily) — `bot.report --mfe`, max favourable/adverse excursion.
  **Observed: ✅ VALIDATED.** Load-bearing within two sessions — 08-13's whole trade table is
  MFE/MAE-sourced from it, and it produced that session's cleanest finding: **all 4 winners had
  MAE ≤ 0.44%, all 4 losers MAE ≥ 0.90%**, a separator confidence itself failed to provide.
- **IMP-026** (49ecb07, 08-11, daily) — pin log timestamps to UTC (the 08-02 WIB regression).
  **Observed: ✅ VALIDATED.** Zero offset on every line since 08-11 21:23; this weekly rebuilt all five
  sessions' refusal tables straight from journald with no hand-shifting.
- **IMP-027** (b810188, 08-12, daily) — an exit may never be attributed to a sell that filled before its
  entry. **Observed: ✅ VALIDATED.** 08-13 was the strongest available test — 8 entries, 8 exits, several
  filling seconds apart — and every exit was attributed to its own sell, reconciled to the cent. Zero
  false refusals. The $108 mis-book has not recurred.
- **IMP-028** (08-13, daily) — `record_entry` retries once on a fresh connection.
  **Observed: ❌ NONE — WRITTEN BUT NEVER COMMITTED, NEVER DEPLOYED, NEVER LOGGED.** The code is sound
  (full suite re-run by this weekly: `pytest -q` exits 0) but the service has not restarted since
  08-13 11:37, ten hours before the files were touched. **The 08-12 data-loss defect is still live.**
  Number reserved and entry written by this weekly; deployment handed to tonight's daily review.
- **Did they compound or cancel? They compounded — this was a coherent set, not four unrelated tweaks.**
  All four attack the *same* target: **the trustworthiness of the evidence base**, after a fortnight in
  which two reviews were nearly misled by bad data. IMP-026 made the logs readable, IMP-025 made
  excursion measurable, IMP-027 stopped the DB recording the wrong exit, IMP-028 (had it shipped) stops
  it recording no trade at all. **Together with IMP-023/024 that is six consecutive changes hardening
  measurement rather than chasing P&L** — and the payoff is visible: 08-13's two refutations were only
  possible because the instruments were fixed first. **The one that cancelled is IMP-028 against
  itself**: written and unshipped is the same as not written, except that the log claimed otherwise.

### Strategy verdict
**VIABLE — unchanged in direction, strengthened in evidence. The edge is real, it is robust, and it is
still entirely in exposure management rather than in the signal.**

The gate's four-window agreement is the strongest result this bot has produced, and the 10-day
counterfactual (**+$37.68 with, −$53.84 without**) is the cleanest statement of where the money comes
from: **the bot makes money by declining to be long, and by managing the trades it does take. It does
not make money by picking them.** Nothing this week moved the signal column. The `<0.5%`-MFE cohort —
entries that never trade above their entry price — remains the dominant structural leak and produced
every loss on the bot's busiest day. Confidence remains inverted above 80 across three straight weeks.
**Lifetime the bot is +$21.45 on 266 trades at PF 1.009 — which is the honest headline: after everything,
it is a coin flip that has recently learned when not to flip.** Three consecutive profitable weeks under
the post-IMP-021 configuration is genuinely encouraging and is the first sustained stretch in its
history, but 08-03 → 08-14 is four effective trading sessions of data. **Keep running, keep it on paper,
keep the freeze on the signal until the sample justifies touching it.**

### Focus for next week
- **🔴 FIRST ACTION, TONIGHT, NOT NEXT WEEK — deploy IMP-028.** Handed to the 08-14 daily review with
  explicit steps in `memory/improvement-log.md`. It is a *delivery* task, not a new change, and it does
  not count against any freeze. **Verify deployment by comparing `systemctl show -p ActiveEnterTimestamp`
  against the file mtime** — this project's own memory records the identical failure on a sibling bot,
  where "restarted clean" was reported while the old process kept running.
- **🔧 Process fix, and it is the real lesson of the week: a change is not shipped until it is
  *running*.** Three of this bot's last four review cycles have produced a change that was written and
  logged before it was verified live. Standing rule from now on: **no IMP entry may be written in the
  past tense until `git log` shows the commit AND `ActiveEnterTimestamp` post-dates the file mtime.**
- **SHIPPING FREEZE ON TRADING LOGIC CONTINUES — one more week, and this time for a good reason rather
  than a precautionary one.** The freeze worked: it produced two rigorous refutations instead of two
  regrettable tunings. **Do NOT touch `MARKET_FILTER_SYMBOL` (the tripwire is retired — the gate is
  vindicated), `MIN_CROSSOVER` (refuted 08-13, unanimously, four windows), `STOP_LOSS` (refuted 08-13
  and structurally vestigial behind the trail — stop re-litigating it), `TRAIL_PERCENT`/the two-stage
  trail, `ENTRY_THRESHOLD`, or the confidence weights.** Permitted: correctness fixes, data-integrity
  fixes, instrumentation.
- **The one measurement that matters next week: the `<0.5%`-MFE cohort.** It is now the sole remaining
  first-order leak and the only place left with real upside. **Build the evidence, do not ship the
  filter.** The concrete question: *is there any pre-entry discriminator for entries that never trade
  above their entry price?* The 08-13 lead is **MAE-based, not confidence-based** — winners separated
  cleanly at MAE ≤ 0.44% vs losers ≥ 0.90%. That is an *outcome* variable, so it cannot be used directly;
  the task is to find the pre-entry proxy for it (ATR-relative entry placement, distance from the ribbon,
  entry-bar range). Requires the harness, ≥3 agreeing windows, and it is a **next-Friday decision**.
- **Standing, do not act yet:** confidence inverted above 80 (90-100 now 0-for-3, −$144.42) — thin at
  n=3, revisit when the top two bands reach n≈20 under post-08-03 config. Whole-share quantisation
  flattening the size curve on $900+ names (MU at qty=2 on $36k buying power) — needs its own study and
  cannot be fixed by sizing alone, since Alpaca brackets require whole shares.
- **⚠️ Carry forward — every live-history bucket study over 45+ days is contaminated by pre-IMP-021
  trades** (established 08-13). Judge changes on the post-08-03 window or on replay, never on the 45-day
  live tail. This invalidates the older "104 of 162 trades never reach +1% MFE" figure as a basis for action.
- **Ops:** the service ran **32 hours on one uptime** and did **not** restart for the 08-14 pre-market —
  so any watchlist edit made that morning was not loaded. Confirm the pre-market routine's restart step
  is actually firing. Also `chown ustradebot:ustradebot` on `bot/persistence.py` and
  `tests/test_persistence.py`, currently `root:root`.
- **Perplexity:** `sonar-deep-research` returned empty this run and `sonar` has now been thin, stale or
  unreachable **ten consecutive times**, once dangerously (08-10, a prior session's record close
  presented as that day's). **Standing rule reaffirmed: source regime from IEX daily bars first;
  `sonar` is lead-generation only and must never be written into a review unverified.**
- **Risk posture unchanged and non-negotiable:** position size, loss limits, the stand-down/kill switch
  and paper-only stay exactly as they are. The stand-down proved itself on 08-13 — it tripped after three
  consecutive losses and reset correctly for the next session. Any move toward live trading requires
  explicit human approval and is not this routine's call.
- **The tape, for context (IEX open→close, authoritative):** QQQ **−0.25 / −0.65 / −0.46 / +0.98 / −0.29%**
  and SPY **+0.03 / −0.52 / −0.28 / +0.40 / −0.28%** across 08-10→08-14. **Four of five sessions fell
  intraday**; the S&P still closed a third straight weekly gain and printed a record 7,800 on Thursday,
  a divergence that matters — **the index gains came from gaps and overnight drift, not from intraday
  trend, which is the one thing this bot cannot monetise (it never holds overnight).** July CPI and PPI
  came in soft, easing September hike fears; Friday's retail sales **−0.6%** (worst in over a year) and a
  weak UMich sentiment print sapped the afternoon. Broadcom **−5.5%** and AMAT **−5.2%** on Friday hit the
  semi-heavy end of this watchlist.
- **Next week's scheduled catalysts (08-17 → 08-21):** **retail earnings dominate — Walmart (WMT, Thu
  08-20 BMO, on the watchlist) and Target**, plus the tail of the semi complex. **NVDA reports 08-26**,
  i.e. *not* next week but close enough that positioning drift will start. No FOMC meeting; watch for
  Jackson Hole commentary and the FOMC minutes. Expect the gate to stay quiet on down-tape days and to
  open around any retail-driven risk-on session.


---

## Week ending 2026-08-21 — Grade: C+

### Stats
- **DB (closed, Mon 08-17 → Fri 08-21): 2 trades, 0W/2L → 0.0% win**, net **−$34.66**,
  **PF 0.00** (gross win $0.00, gross loss $34.66). Avg loss **−$17.33**. Best **MU −$12.33**,
  worst **INTC −$22.33**. **Both trades were Monday**; Tue/Wed/Thu/Fri were all zero-trade.
- **Equity $9,123.87 (Fri 08-14) → $9,089.13 = −$34.74 (−0.38%).** Broker reconciles: Alpaca
  `PA34DFFLTHRT` equity **$9,089.13**, all cash, **0 positions, 0 open orders**, `trading_blocked`
  false. **Max drawdown $34.74, entirely Monday**; the curve was a flat line 08-18 → 08-21
  (9,089.13 four sessions running, to the cent).
- **By symbol:** INTC −$22.33 (1) · MU −$12.33 (1). Both Model A, both exited on the broker-side
  trail ~2h after entry, neither approached the −2% hard stop.
- **Confidence vs outcome (all-time) — inverted at the top for a SEVENTH week:** 70-79 **+$250.84**
  (87 tr, 54.0%) · 60-69 −$92.88 (148 tr, 41.2%) · 80-89 −$26.75 (30 tr, 46.7%) ·
  **90-100 −$144.42 (3 tr, 0% win)**. Unchanged; still n=3 at the top.
- **All-time: 268 trades, 45.5% win, net −$13.22** (PF ≈ 1.0). **Post-08-03 config: 27 trades,
  59.3% win, +$135.47, PF 1.83** — this week added **2 trades and −$34.66** to that window.
- **Refusals (IMP-030/031/032): 76 rows** over the three instrumented sessions (26 / 27 / 23).
  **Gate duty cycle** (IMP-032 live + reconstruction): 08-18 **0.0%** · 08-19 **7.2%** ·
  08-20 **0.0%** · 08-21 **49.3%**; 24-session **31.6%**, and **bimodal** — 13 of 24 sessions
  ≤10% open, 7 ≥60%. The gate is close to a binary session switch, not a within-day trimmer.
- **Service: clean. `NRestarts=0` all week**, zero WARNING-or-above in any session's journal
  (8,638 lines Friday). The only journal "error" strings are two websocket keepalive reconnects
  (08-15 08:38, 08-20 06:55), both **outside market hours**, both auto-recovered. **No risk event,
  no naked position, no crash, no missed fill, no qty drift.** DB↔broker exact every session.

### Grade rationale
**C+ — a losing week by the rubric's letter (small loss, within risk limits = C), lifted by the
best measurement week this bot has ever had, and held down by one unresolved capital-risk gap.**

**Results are negative and the win rate is 0%, so this cannot be a B** — the rubric reserves B for
flat-to-positive. The magnitude is trivial (−0.38%, two trades, neither hitting a stop) and the four
flat sessions were **demonstrably** correct rather than assumed: the week's 76 declined candidates
averaged **−0.11% to the flatten** with **49 of 76 (64%) never trading +0.5% above entry**, against a
**46.6% baseline for trades the bot actually takes**. The bot did not miss a rally; it declined a tape
that had nothing in it. **It is emphatically not a D** — no meaningful loss, no repeated mistake, no
unvalidated change shipped, no risk breach, and every one of last week's focus items was honored.

**Process was A-grade and should be said plainly.** The 08-14 shipping freeze on trading logic held
for a second week and held *intelligently*: five IMPs shipped, **all five instrumentation, zero
behavioural change to entry, exit or sizing**. Along the way the daily reviews **refuted four separate
tempting changes on evidence** — `conf_volume` as a discriminator (it is *inverted*: vol=0.00 is the
best band at +$185.99, vol=1.00 the worst at −$377.93), loosening the market gate (08-18, n=15),
loosening the crossover floor (08-19 and again 08-21, now **five independent refutations** counting
the 08-13 four-window replay), and shipping a `ribbon_spread_pct` filter on n=2. Each had motive,
authority and a plausible story. None shipped. That is the discipline this bot historically lacked.

**What costs it the rest of a grade is one gap with real money attached.** The **08-19 pre-market
routine crashed (`claude exited rc=1`)**, so **WMT and BABA were NOT parked into their 08-20 earnings
prints** despite being scheduled for it. Nothing bad happened — the gate was 0.0% open on 08-20, so no
trade was structurally possible — but **that is luck, not control.** The bot has **no earnings guard of
its own**; its only protection is a routine that failed silently, and `run-routine.sh` discards stderr
so the cause is still unknown three days later. It lives in `/root/claude-routines`, outside this repo
and outside this routine's one-change scope, which is exactly why it keeps not getting fixed.

**Not counted against the week:** `sonar-deep-research` returned **empty (1 byte)** for the second
consecutive weekly, and `sonar` has now been thin, stale or **wrong** on 14 consecutive runs — on
08-21 it reported the S&P *"down 0.87%"* and Nasdaq *"down 1.00%, risk-off"* when IEX bars had SPY
**+0.40%** and QQQ **+0.35%**. It had the sign backwards. Regime was sourced from IEX daily bars, as
the standing rule requires. That rule has now earned its keep three times.

### The tape, and why it matters more than usual this week
IEX **open→close** — the only window this bot trades:

| | 08-17 | 08-18 | 08-19 | 08-20 | 08-21 |
|---|---|---|---|---|---|
| **QQQ o→c** | −0.41% | −0.35% | −0.61% | −0.16% | −0.26% |
| **SPY o→c** | −0.47% | −0.19% | −0.16% | −0.42% | −0.05% |
| **QQQ range** | 0.72% | 0.85% | 1.21% | 0.88% | 0.89% |

**QQQ fell intraday on all five sessions, and no session had a 1.25% range except one.** Friday is the
week in miniature: QQQ closed **+0.35% day-over-day** while falling **−0.26% open→close** — the entire
gain was an overnight gap. **A long-only intraday trend bot that flattens every close was structurally
excluded from the week's index gains, and structurally exposed to the only direction available to it.**
This is the same divergence the 08-14 weekly named, now in its second week and sharper. It is the
single most important market fact of the week and it is not a strategy defect — it is a mandate limit.

### 🔬 The week's decisive measurement — `bot.report --days 7 --refusals` (n=76)
IMP-033's own "what to check next" asked the weekly to run this. It did:

```
cohort        n   avgMFE   avgMAE   avgFwd  <0.5%MFE  hitTrail  stopped
crossover    38   +0.41%   -0.62%   -0.21%   26/38      2/38     2/38
confidence   23   +0.40%   -0.47%   -0.18%   16/23      2/23     0/23
gate         15   +1.08%   -0.94%   +0.28%    7/15      5/15     1/15
ALL          76   +0.54%   -0.64%   -0.11%   49/76      9/76     3/76
```

**Two filters are now settled, on live outcomes, over a full week:**
- **`MIN_CROSSOVER = 0.25` is validated.** 38 declined candidates, **−0.21% average forward return**,
  **68% dead on arrival**, only 2 of 38 could have reached the 1.25% trail. **Fifth independent
  refutation** of lowering it. It joins `STOP_LOSS` and `MARKET_FILTER_SYMBOL` on the
  do-not-relitigate list. **Stop proposing this.**
- **`ENTRY_THRESHOLD = 60` is validated at the bottom of the scale.** 23 declined, **−0.18% forward**,
  **70% dead**. Note the asymmetry, which is the honest version of the confidence story: **the score
  works below 60 and is inverted above 80.** It is not uniformly broken; it is broken at the top.

**And one filter looks different — this is the week's real finding, and the reason I am NOT acting on
it is the more important half.** The gate cohort beats the other two on *every* metric: **2.6× the
MFE**, the **only positive forward return (+0.28%)**, **47% dead vs 68/70%** — below even the 46.6%
baseline for admitted trades — and **5 of 15 reached the trail (33%) vs 5% and 9%**. Across three
sessions the gate declined the day's single best candidate three days running (MU conf 89.1 → +1.56%;
PLTR +2.62% and TSLA +2.05%; TSLA +2.93% is the week's best declined candidate outright). That is a
pattern across the week, not an anecdote, and it is exactly the bar Step 3 sets for a change.

**I am still not touching the gate, because the table cannot measure what it appears to measure.**
**A gate refusal is only recorded when a candidate already scored** — i.e. on the minutes when
something looked good. The sessions where the gate *saves* money are sessions where it holds the bot
out of a falling tape, and those contribute **few or no scored candidates and therefore almost nothing
to this table**. So the refusal counterfactual prices the gate's **misses** while being structurally
blind to its **saves**, and a positive forward return in the gate cohort is **exactly what a
profitable gate would also produce.** This is the same class of conditioning error IMP-031 exposed in
the 08-14 weekly's "gate = 5% of refusals" metric — a statistic whose ceiling is set by the filters
upstream of it. Against it stands the only measure that captures both sides: **four independent replay
windows on net P&L (5d, 10d, 60d + 08-13 live), including a 10-day counterfactual of +$37.68 with the
gate versus −$53.84 without.** Candidate quality and net P&L are different claims. **Both can be true:
the bot makes money by declining to be long, and it pays for that with a handful of missed runners.**
The report prints its own warning and it is correct: *upper bound — passing one filter only advances a
candidate to the next.*

### What worked / what didn't
- **✅ The measurement chain, and it compounded — this was one build, not five tweaks.** IMP-029
  captures the pre-entry tape state → **030** persists the declined population → **031** adds the gate
  condition to every row → **032** adds the gate *denominator* → **033** scores the outcomes. Together
  they raise the evidence sampling rate from **~1–2 trades/day to ~25 refusals/day (~15×)**, and turn
  the `<0.5%`-MFE question the 08-14 weekly called *"the one measurement that matters"* from a night's
  throwaway scripting into a single command. The freeze was waiting on sample size; **this week built
  the machine that supplies it.** Three of the five paid off within one session of shipping.
- **✅ Capital protection and ops.** −0.38% on a week where the bot's only tradeable direction fell
  five sessions out of five. `NRestarts=0`, zero warnings, exact broker reconciliation daily, warmup
  18/18, and the 08-14 weekly's flagged ops item — *is the pre-market restart actually firing?* —
  **confirmed fixed** (restarts at 11:39 on 08-20 and 11:38 on 08-21, watchlist edits loaded).
- **❌ Entry timing, unaddressed for a fifth week.** Monday's two losses were **both bought within
  0.6% of the session high** (INTC −0.53%, MU −0.19% from the high) after a run, on names that moved
  ~4% intraday and closed near their lows. MU finished **+1.28% from its open and the bot still lost.**
  The ribbon fires at the exhaustion point of the up-leg. That is the entire loss, and no IMP this
  week touched it.
- **❌ A design defect in the confidence score, found and correctly not acted on.** `conf_rsi == 1.0`
  on **252 of 268 trades (94%)** and on **26 of 26** refusals on 08-19; `conf_volatility == 1.0` on
  **65%**. With weights crossover 30 / trend 20 / **rsi 20** / volume 15 / **volatility 15**, roughly
  **35 of 100 points are a near-constant floor** — so the "60/100" bar is really **~25 of a variable
  65**. That is a strong mechanical explanation for seven weeks of anti-predictive confidence: a third
  of the score is a constant, which *compresses* the spread between good and bad candidates instead of
  widening it. **Best-evidenced open strategy question in the book.**
- **❌ The earnings gap (above).** WMT and BABA unparked into their prints. Still unowned.
- **❌ `sonar` wrong on direction (08-21) and `sonar-deep-research` empty for a second weekly.**

### Improvements shipped this week
All five are instrumentation — **zero behavioural change to entry, exit or sizing** — which is what
the 08-14 freeze permits.
- **IMP-029** (08-17, daily) — record pre-entry tape context (`atr_pct`, `ribbon_spread_pct`).
  **Observed: ✅ VALIDATED, but through a route it did not anticipate.** Still **0 of 268 `dbo.trades`
  rows** carry it (no entries since 08-17), yet it is populated on **all 76 refusal rows** via
  IMP-030 — and `ribbon_spread_pct` became the week's single best pre-entry lead (08-21: the two
  candidates with spread ≥0.11 ran +2.62%/+2.05%; the other 21, all ≤0.029, averaged +0.30% MFE).
  It validated on the refusal side, not the trade side.
- **IMP-030** (08-18, daily) — persist refused candidates to `dbo.entry_refusals`.
  **Observed: ✅ VALIDATED next session** (26 rows) and **load-bearing for this entire review**.
  The highest-leverage change of the week: it converted the bot's largest dataset into evidence.
- **IMP-031** (08-19, daily) — gate state on **every** scored refusal.
  **Observed: ✅ VALIDATED one session later, and it overturned a prior weekly's finding** — it
  revealed `market_gate_open = FALSE` on all 27 of 08-20's rows and proved the 08-14 weekly's
  "gate = 5% of refusals" restrictiveness metric is **structurally biased** (its ceiling is set by the
  filters upstream). A change that corrects the review process itself is worth more than one that
  tunes a constant.
- **IMP-032** (08-20, daily) — persist the gate's duty cycle to `dbo.market_gate`.
  **Observed: ✅ VALIDATED first session** — 87 rows, 0 duplicate `(symbol, candle_start_utc)` pairs,
  first row 12:15 vs the 11:38 restart (**no warmup backfill** — the trap it was built to avoid). It
  immediately **killed a lazy explanation**: Friday's drought was *not* the gate (49.3% duty cycle),
  it was signal strength. The gate finally has a denominator.
- **IMP-033** (08-21, daily, shipped 20:12 UTC tonight) — `bot.report --refusals`.
  **Observed: ⏳ too new to have a forward effect, but immediately load-bearing** — the n=76 table
  above is its first output and it produced the week's decisive finding within an hour of shipping.
  431 tests, live-verified (`ActiveEnterTimestamp` 20:11:58 post-dates every touched file).
- **Did they compound or cancel? They compounded, unambiguously** — a single coherent five-step
  build with a common target: **making the bot's own restraint measurable.** Counting IMP-025→028,
  that is **nine consecutive changes hardening measurement rather than chasing P&L.** The honest
  counter-charge is that this is the second week with no strategy change while the trade count fell
  to 2, and a freeze that keeps extending itself starts to look like an inability to decide. The
  defence is that the dailies did not merely measure — they **refuted four candidate changes on
  evidence**, and refutation is a decision. But this cannot continue indefinitely (see verdict).

### Strategy verdict
**VIABLE BUT UNPROVEN, AND NOW STRUCTURALLY STARVED — the binding risk has shifted from the signal to
the bot's inability to express it often enough to be judged.**

The edge that exists remains **entirely in exposure management, not in the signal** — unchanged from
last week and now better evidenced. The signal itself has never demonstrated edge: **268 lifetime
trades, −$13.22, PF ≈ 1.0.** A coin flip. The post-08-03 window (27 trades, +$135.47, PF 1.83) is the
best stretch in the bot's history and remains too small to lean on; this week contributed **2 trades
and a loss** to it.

**The new finding, and it is one a day-at-a-time view structurally cannot see: trade frequency has
collapsed ~95% in seven weeks.** Trades per week: **45 → 21 → 26 → 22 → 13 → 12 → 2.** Every filter
driving that is individually defensible and individually evidenced — the opening blackout (IMP-017,
validated on 219 trades), the crossover floor (five refutations of loosening it), the gate (four
replay windows). **Collectively they have produced a system that is flat ~96% of the time.** At two
trades a week the post-08-03 sample reaches n=100 somewhere in 2027. **A strategy that cannot be
tested cannot be improved**, and that — not any individual parameter — is now the binding constraint
on this project.

**The resolution is not to loosen filters.** Five independent studies say that destroys money, and
this week's n=76 says the declined population is worse than the admitted one on two of three cohorts.
The resolution is the one the dailies already found: **the refusal dataset is the sample.** 76 rows in
three sessions, ~500/month, ~25/day against ~1 trade/day. IMP-030→033 built exactly that instrument.
**Next week must spend it, not extend it.** If the next two weeks produce a sixth and seventh
consecutive instrumentation IMP with no strategy decision, that is the failure mode to grade harshly,
and this review is putting that on the record now so it can be graded against.

**Keep running. Keep it on paper. Keep the freeze on constants — but the freeze does not cover the
RSI-constant finding, which is a design defect rather than a tuning knob, and next week should settle
it.**

### Focus for next week
- **🔴 PARK NVDA BEFORE WED 08-26 — it reports that day and it is currently ENABLED** (confirmed in
  Friday's 18-symbol subscription). This is the one item with real money attached. **And note the
  standing hazard: the bot has no earnings guard of its own** — its only protection is the pre-market
  routine, which **crashed on 08-19 and left WMT and BABA unparked into their prints.** Two options,
  both worth raising: fix `run-routine.sh` to preserve stderr and alert on `rc≠1` (harness work,
  `/root/claude-routines`, outside this repo), **or** give the bot an in-repo earnings blackout it
  owns itself. **The second is a legitimate weekly-review change and is my recommended IMP-034** —
  it removes a capital risk that currently depends on an external routine not crashing.
- **🟠 Settle the RSI-constant defect — the best-evidenced open strategy question, and it is a design
  flaw, not a constant.** `conf_rsi` returns a flat 1.0 across the whole 45-65 RSI band, which is
  where a fresh bullish cross almost always sits: 94% of trades, 100% of 08-19's refusals. **~35 of
  100 confidence points are a near-constant floor.** The study: re-fit `score_rsi` to something with
  variance across that band (or drop the component and re-weight), then validate on **≥3 agreeing
  replay windows** *and* against the 76+ refusal rows, which now provide an independent out-of-sample
  check the harness never had. **This is the one place a change could plausibly fix the seven-week
  confidence inversion at its root rather than papering over it.**
- **🟠 The `ribbon_spread_pct` study — now a command, not a night's work.** Friday's lead is the right
  shape for a pre-entry proxy for the `<0.5%`-MFE cohort (available *before* entry, unlike MAE). **Two
  disqualifying caveats to clear first: it is confounded with gate state** (both wide-spread names
  were also the two the gate refused) **and n=2.** Run it across ≥3 windows with gate state
  controlled. **Do not ship a spread filter until both are cleared.**
- **⚖️ The market gate: accumulate, do NOT touch — and here is the falsifiable test that would change
  my mind.** The n=76 table makes a tempting case (gate cohort +0.28% fwd, 33% trail-hit rate, three
  straight days declining the day's best candidate). **It is not sufficient, because the refusal table
  prices the gate's misses and is blind to its saves** (a refusal is only logged when a candidate
  scored; the gate's good days produce no candidates at all). **The only measure that captures both is
  net P&L in replay, gate ON vs OFF, and that is what already favours the gate 4 windows to 0.**
  **The test:** re-run gate ON/OFF on the *current* config across ≥3 fresh windows. **If net P&L
  agrees in sign in ≤1 of 3 windows, the gate's shape becomes revisable** — and the first thing to try
  is then a *softer* gate (e.g. gate on QQQ slope only, or a confidence surcharge instead of a veto),
  not removal. Until that study runs, **the gate is untouchable.**
- **Do-not-relitigate list (now five entries):** `MIN_CROSSOVER` (five independent refutations —
  08-13 four-window replay, 08-18, 08-19, 08-20, 08-21 live n=38) · `STOP_LOSS` (refuted 08-13,
  structurally vestigial behind the trail) · `MARKET_FILTER_SYMBOL` (tripwire retired 08-14) ·
  `conf_volume` (**inverted** — vol=0.00 is the *best* band, refuted 08-17) · loosening
  `ENTRY_THRESHOLD` downward (validated 08-21, n=23, −0.18% fwd, 70% dead).
- **⚠️ Carry forward:** every live-history bucket study over 45+ days is contaminated by pre-IMP-021
  trades. Judge on the post-08-03 window or on replay. And **watch the sample-source shift** — the
  refusal table is a *different population* from the trade table (candidates that failed a filter),
  so it is an excellent instrument for filter questions and a **poor** one for exit questions.
- **Next week's tape (Aug 24-28) — event-heavy, and the watchlist is squarely in the blast radius:**
  **NVDA earnings Wed 08-26** (consensus ~$91bn revenue; the single largest scheduled risk on this
  board) · **July core PCE Wed 08-26 08:30 ET** (consensus 3.2% y/y vs 3.3%) · **Jackson Hole
  Aug 27-29, Chair Warsh keynote Friday** · plus CRM, CRWD, Synopsys, Marvell (Thu). Semis fell ~5%
  into the weekend (SMH) and momentum −4%, so **AMD/TSM/MU/INTC ribbons should widen** — which is
  good for signal strength after a week where the binding constraint was a flat tape
  (`ribbon_spread_pct` of 0.00058% on UBER, 0.00116% on QQQ). **Expect more entries without any code
  change if the range expands** — and expect the gate to open more than the 31.6% recent duty cycle.
  Judge next week on whether widened ribbons finally grow the live sample.
- **Risk posture unchanged and non-negotiable:** position size, loss limits, the stand-down/kill
  switch and paper-only stay exactly as they are. Nothing this week justified touching any of them,
  and the shorting idea in `todo.md` remains explicitly out of scope for an unattended routine.

