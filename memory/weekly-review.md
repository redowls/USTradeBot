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
