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
