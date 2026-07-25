# Improvement Log

Audit trail of every code/config change shipped by the `ustradebot-daily-review`
routine. One compact entry per improvement (≤15 lines), numbered IMP-001, IMP-002, …
The weekly review reads this to judge whether shipped changes actually helped, and
the pre-market routine reads it for strategy context.

Entry template:

## IMP-NNN — YYYY-MM-DD

- **Problem:** (what today's trades showed)
- **Root cause:**
- **Change:** (files modified, one-line description)
- **Validation:** (tests run, results)
- **Expected impact:**
- **Commit:** (hash)
- **Observed effect:** (filled in by a later review once data exists)

---

## IMP-001 — 2026-06-15

- **Problem:** The 06-15 EOD flatten's first pass cancelled each bracket's resting leg then
  immediately tried `close_position`, and **403'd `held_for_orders`** on 6 of the open names
  (GOOG/AVGO/TSM/AMZN/UNH/WMT). Only a *later* candle-driven pass (~7s on) actually closed
  them. Self-healed today, but on a thin close with no further candle before 16:00 the
  positions would sit **naked, protective legs already cancelled**.
- **Root cause:** `OrderExecutor.close_position` cancelled the legs then retried the close
  only 3× with 0.4s sleeps (~0.8s total). Alpaca's cancel settles **asynchronously** — the
  qty stays `held_for_orders` for several seconds after the cancel call returns — so the
  whole 0.8s budget elapsed before the qty freed, and the close depended on a future candle.
- **Change:** `bot/executor.py` — after cancelling the legs, `close_position` now polls the
  position's `qty_available` (new `_qty_released` helper) until the held qty releases, then
  liquidates, all within one call. Budget widened to 12 attempts × 0.5s (`_CLOSE_ATTEMPTS` /
  `_CLOSE_RETRY_DELAY`, ~6s). No risk widened, no safety disabled — strengthens the flatten.
- **Validation:** full suite **186 passed** (`pytest -q`). New regression
  `test_close_position_waits_for_held_qty_to_release` reproduces today's async-cancel race
  (qty held for 3 polls, then frees) and asserts the close completes in the same call;
  added a `time.sleep` no-op fixture so the wider retry loop doesn't slow the suite.
- **Expected impact:** EOD flatten (and any reversal exit) closes reliably on the first pass
  → eliminates the naked-overnight tail risk. Capital protection; no win-rate change expected.
- **Commit:** b7f37f7
- **Observed effect:** 2026-06-16 — **did NOT recur** (no `held_for_orders` 403s in the
  06-16 flatten). A *different* flatten failure hit instead: persistent Alpaca **504 Gateway
  Timeouts** beat all 12 retries (broker-side outage, not the async-cancel race IMP-001
  fixed). IMP-001 holds; IMP-002 addresses the new mode. **Weekly (06-19):** held all week —
  the `held_for_orders` async-cancel race never reappeared; every later flatten failure was a
  different mode (504 06-16, submit-ack 06-18, candle-timing 06-18). IMP-001 confirmed good.

---

## IMP-002 — 2026-06-16

- **Problem:** The 06-16 EOD flatten **failed on all 4 open names** (AAPL/ABNB/BABA/GOOG)
  — Alpaca's paper API returned persistent **504 Gateway Timeouts** on `cancel_order` and
  `close_position` (`code 50410000 "request timed out"`) across 20:02–20:58 UTC. All 12
  close retries (IMP-001's budget) exhausted; `close_position` returned `None` and the bot
  logged a journald ERROR **only — no Telegram alert**. The DAY bracket legs expired at the
  20:00 UTC close, so 4 positions carried **naked overnight** with the operator unaware.
- **Root cause:** the EOD flatten (`StrategyEngine._flatten_all_eod`) had **no escalation
  on failure** — a symbol whose close failed just stayed `MANAGING` for the next candle's
  retry. When the failure is a broker-side 504 outage (no retry beats it) and the session
  ends, the position is silently abandoned naked. IMP-001 fixed the *held_for_orders* race;
  it cannot help a 504 — the gap was the **silent** failure, not the retry budget.
- **Change:** `bot/strategy.py` — `_flatten_all_eod` now takes the candle time and calls a
  new `_escalate_failed_flatten`: when a close fails within `_FLATTEN_ESCALATE_MIN` (2.0)
  min of the close (no retry runway before the DAY legs expire), it fires a **one-time
  critical Telegram page per symbol per session** ("position will carry NAKED overnight…").
  Dedup via `self._flatten_escalated`; re-armed on a later successful close. New
  `signals.minutes_until_close` helper; new public `RiskManager.send_alert` routes the page
  through the existing Telegram feed-alert channel. **No risk widened, no safety disabled,
  no trading logic changed** — pure capital-protection escalation.
- **Validation:** full suite **189 passed** (`pytest -q`, was 186 + 3 new). New regression
  `test_failed_eod_flatten_escalates_once` reproduces today's 504 (a closer that returns
  `None` in the final minute) and asserts the position stays held + exactly one NAKED page +
  dedup on the next candle; `test_failed_eod_flatten_does_not_escalate_with_runway_left`
  guards against early-window false pages; `test_minutes_until_close_counts_down_and_goes_negative`.
- **Expected impact:** a failed EOD flatten is never silent again — the operator is paged to
  manually flatten (`bot.flatten`) before/at the next open. No win-rate change; closes the
  naked-overnight tail-risk hole that IMP-001 couldn't (broker-side outages).
- **Commit:** 1b575a7
- **Observed effect:** 2026-06-17 — the naked-overnight it warns about **did happen on 06-16**:
  AAPL/ABNB/BABA/GOOG carried overnight (504 flatten failure) and were flattened on 06-17 for
  −$125.85 combined. No journald NAKED page is visible for 06-16 in today's window, so confirm
  the page actually fired that night (or whether the 504s pre-empted it). IMP-002 logic holds;
  the *carry* is the realized cost of that outage. **Weekly (06-19):** still NOT proven to fire
  in production — 06-18's 7-name naked carry **bypassed the page entirely** (the close faked
  success via submit-ack, IMP-004's gap, so the flatten never "failed" from the bot's view).
  IMP-002's first real proof is owed Monday 06-22, now that IMP-004 forces a true-fail path.

---

## IMP-004 — 2026-06-18

- **Problem:** The EOD flatten "closed" **7 positions that were still OPEN at the broker**
  (GOOG/INTC/MU/QQQ/SE/TSLA/TSM) → they carried **NAKED into the Juneteenth long weekend**, and
  the DB recorded 7 fake CLOSED exits (a fictitious +$199.06 day vs ≈ +$47 real unrealized). The
  flatten fired ~16:00–16:05 ET — *after* the 16:00 close — on a laggy feed (websocket drops + an
  Alpaca 504 storm); the bracket DAY legs had expired and the flatten's **market DAY sells were
  `accepted` but never filled**. IMP-002's naked-overnight page **never fired**.
- **Root cause:** `OrderExecutor.close_position` returned the order id on the **submit ack** — it
  never confirmed the position actually went flat. A market DAY order placed after the close is
  accepted but unfilled, so the bot read "submitted" as "closed," recorded the exit, released the
  symbol, and bypassed IMP-002 (the close looked successful). IMP-001/002/003 fixed the close
  *mechanics* and broker-side-fill reconciliation; none verified the bot's **own** close filled.
- **Change:** `bot/executor.py` — new `_confirm_flat(symbol)` polls `get_open_position` (reusing
  the `_CLOSE_ATTEMPTS`/`_CLOSE_RETRY_DELAY` budget) until the broker 404s (`_is_position_gone`).
  `close_position` now submits **once**, then requires `_confirm_flat` before returning the order
  id; if the position is still open when the budget is spent it returns **`None`**. Downstream
  (`risk.exit_position`): `None` → `reconcile_exit` (returns `None` while the position is still
  open) → no exit recorded, symbol stays MANAGING, and `strategy._escalate_failed_flatten` fires
  the IMP-002 NAKED page. **No risk widened, no safety disabled, no entry logic touched** — closes
  the "submit-ack ≠ fill" gap. Fails closed (a transient read that never clears → report not-flat).
- **Validation:** full suite **196 passed** (`pytest -q`, was 194 + 2 new). New regressions:
  `test_close_position_unfilled_after_close_returns_none` (today's exact scenario: close submitted
  but position stays open → `None`, not a fake success) and
  `test_close_position_confirms_flat_before_reporting_success` (happy path still returns the id once
  the broker confirms flat). `bot.preflight` PASS (Alpaca ACTIVE, equity $9,253; 1 WARN = market
  closed). Service restarted clean.
- **Expected impact:** a flatten/exit that doesn't truly close is never again logged as a success —
  the operator is paged (IMP-002) and the books stay honest (no fictitious exits, no inflated win
  rate). Capital protection + data integrity. Does **not** by itself prevent a late flatten from
  carrying naked — that's candidate #2 (widen `FLATTEN_BEFORE_CLOSE_MIN` so the flatten runs in
  liquid RTH); IMP-004 is the reliable detection/escalation half.
- **Commit:** 5825b4b
- **Observed effect:** **Weekly (06-19): unvalidated** — shipped 06-18 EOD, no trading session
  since (06-19 Juneteenth). First test **Monday 06-22**: confirm an accepted-but-unfilled close
  writes NO CLOSED row + fires the IMP-002 NAKED page, and a normal RTH exit still records cleanly.
  Until proven, this remains the single most important fix of the week (it is what makes IMP-002 fire).

---

## IMP-008 — 2026-06-23

- **Problem:** First fully clean session in 12 days (3 trades GOOG/UNH/JPM, all EOD-flattened &
  filled before 16:00 — IMP-005/006/007 validated live). With the exit-infra finally trustworthy,
  the one remaining book inaccuracy stood out: the bot's **own** EOD/reversal market sells were
  recorded at the **candle-close estimate** the caller passed, not the real broker fill — GOOG
  recorded @ $346.72 but actually filled @ **$347.14** ($0.42/sh = $2.5 on one trade). DB day
  −$9.13 vs equity −$6.41; the residual is exactly this gap.
- **Root cause:** `risk.exit_position` set `exit_price` from the candle-close value passed in on the
  happy close path; only the *broker-side-stop* reconcile branch (IMP-003) used the true fill. The
  bot's own close order's `filled_avg_price` (available once IMP-004's `_confirm_flat` confirms it
  filled) was never read back. So every EOD-flatten/reversal exit logged a slightly-off price → skews
  P&L and can flip a marginal win↔loss in the win-rate metric this routine optimizes.
- **Change:** `bot/executor.py` — new `close_fill_price(order_id)` reads the filled close order's
  `filled_avg_price` via `get_order_by_id` (None on empty id / unfilled / read error → safe fallback).
  `bot/risk.py` — `exit_position`, on a successful self-driven close, now records the **actual fill**
  (`close_fill_price`) instead of the passed-in estimate, falling back to the estimate when unreadable.
  Extends IMP-003's "record at the real fill" truth to the bot's own sells. **No risk widened, no
  safety disabled, no entry/strategy logic touched** — pure data integrity.
- **Validation:** full suite **213 passed** (`pytest -q`, was 207 + 6 new). New regressions:
  `test_close_fill_price_returns_actual_filled_avg` (GOOG 347.14 read back),
  `test_close_fill_price_none_when_unreadable` (empty id / unfilled → None),
  `test_exit_position_records_actual_close_fill` (today's exact GOOG scenario: passed 346.72, recorded
  347.14), `test_exit_position_falls_back_to_passed_price_when_fill_unreadable` (None → keeps estimate),
  plus `close_fill_price` added to the strategy/risk/executor fakes. Service restarted clean.
- **Expected impact:** EOD/reversal exits are booked at their true broker fill → P&L and win-rate are
  exact (no candle-close drift), closing the last desync between DB realized P&L and equity. Data
  integrity; the win-rate metric this routine optimizes is now precise. No win-rate behavior change.
- **Commit:** f854f96
- **Observed effect:** (await next review — confirm DB realized P&L ≈ equity mark-to-market to the
  cent on the next trading session, and that exit prices in `dbo.trades` match `/v2/orders` fills.)
  **Weekly (06-26): ✅ validated** — exit prices in `dbo.trades` match the broker fills, and DB realized
  P&L ties to equity to the cent on every clean session (06-26 DB +$62.07 == equity +$62.07). The
  candle-close-vs-fill exit drift is eliminated.

---

## IMP-009 — 2026-06-24

- **Problem:** Second straight fully clean session (6 trades, 3W/3L, all exits real — IMP-008
  validated again, every DB exit price matches the broker fill). With exits now exact, the only
  remaining DB↔equity divergence was the **entry** side: the bot recorded each trade's entry at the
  **candle-close estimate the signal sized off**, not the actual broker buy fill — INTC DB @134.76
  vs broker @134.7817, SPY @739.63 vs @739.675, JPM @333.535 vs @333.57. DB day −$10.14 vs equity
  −$15.55; the ~$5.41 residual is exactly this entry-price gap.
- **Root cause:** `OrderExecutor.execute` set `ExecutionResult.entry_price=plan.entry_price` (the
  estimate passed in for sizing). A market bracket buy is only `accepted`/`pending_new` at the submit
  ack, so its `filled_avg_price` is empty for a moment and was never read back — unlike the exit side,
  which IMP-008 already records at the real fill via `close_fill_price`. So every entry logged a
  slightly-off price → skews P&L and can flip a marginal win↔loss in the win-rate metric this routine
  optimizes (and which the deferred weak-crossover tuning will rest on).
- **Change:** `bot/executor.py` — new `entry_fill_price(order_id)` polls the bracket parent order's
  `filled_avg_price` via `get_order_by_id` (budget `_ENTRY_FILL_ATTEMPTS`=6 × `_ENTRY_FILL_DELAY`=0.5s,
  short so it never stalls the candle thread; `None` on empty id / unfilled-within-budget / read error).
  `execute` now records the **actual fill** as `entry_price`, falling back to the sizing estimate when
  unreadable. The bracket's broker-side stop/target stay at the submitted plan levels — only the
  *recorded* entry price is corrected. Entry-side mirror of IMP-008. **No risk widened, no safety
  disabled, no entry/strategy logic touched** — pure data integrity.
- **Validation:** full suite **220 passed** (`pytest -q`, was 216 + 4 new). New regressions:
  `test_execute_records_actual_entry_fill_price` (today's INTC scenario: sized 134.76, recorded
  134.7817), `test_execute_falls_back_to_estimate_when_entry_fill_unreadable` (None → keeps estimate,
  never a fabricated 0.0), `test_entry_fill_price_returns_actual_filled_avg`,
  `test_entry_fill_price_none_when_unreadable`; `entry_fill` added to the executor test fake.
- **Expected impact:** entries are booked at their true broker fill → P&L and win-rate are exact (DB
  realized P&L should now track equity mark-to-market to the cent), and the entry+exit data future
  strategy tuning (the weak-crossover candidate) will rest on is now accurate. No win-rate behavior change.
- **Commit:** 0737122
- **Observed effect:** (await next review — confirm DB realized P&L ≈ equity mark-to-market to the cent
  on the next session, and entry prices in `dbo.trades` match `/v2/orders` buy fills.)
  **Weekly (06-26): ⚠️ mostly worked, one gap (completed by IMP-010).** Entries matched the broker fill
  to the cent on 06-24 and 06-26, but on **06-25 it MISSED AMD's ~2-min-delayed fill** (submitted
  13:33:34, filled 13:35:42 — past IMP-009's ~3 s submit-time budget) → AMD booked at the estimate,
  the day's entire $18.98 book error. IMP-010 (re-read the fill at exit time) closed that gap; the
  combined IMP-009/010 thread is now solid (06-26 books exact to the cent).

---

## IMP-003 — 2026-06-17

- **Problem:** All 4 of today's fresh entries (TSLA/INTC/TSM/MU) **stopped out broker-side
  intraday** (19:20–19:38) yet showed **OPEN** in the DB. At the EOD flatten the bot's
  `close_position` **404'd `position not found`** and was retried **12× per name for ~6 min**
  (20:11–20:17, journald ERROR spam), the **exits were never recorded**, the win-rate was
  corrupted (INTC had trailed to a **+$2.20 win**, logged as a phantom loss-less row), and a
  false naked-overnight page was narrowly avoided. Same mechanism produced **7 stale phantom
  OPEN rows** from 06-11/06-12 (broker holds 0).
- **Root cause:** the trailing stop lives **broker-side** (`update_trailing_stop` replaces the
  bracket stop leg). When that leg **fills**, the position vanishes but the bot has **no
  detection** — the symbol stays `MANAGING` until the EOD flatten, where the close 404s. The
  404 was caught as a generic error and retried/abandoned (`close_position` → `None`), so
  `exit_position` returned `None` and the exit was never persisted (no trade-updates/fills
  stream wired). IMP-001/002 fixed the *close mechanics*; neither detects a broker-side fill.
- **Change:** `bot/executor.py` — `_is_position_gone()` detects the already-flat 404; in
  `close_position` that case now returns immediately (no 12× retry); new `reconcile_exit()`
  confirms the broker holds **no** position (guards against transient errors abandoning a live
  position) then returns the most recent **filled sell** order's `(id, avg_fill_price)`.
  `bot/risk.py` — `exit_position()`, when the close didn't submit, calls `reconcile_exit` and
  records the exit at the **real broker fill price** (reason tagged "stop/target filled
  broker-side"); a genuine outage still reconciles to `None` → stays MANAGING + IMP-002 page.
  **No risk widened, no safety disabled.** Today's 4 phantom rows were also backfilled from
  broker-verified `/v2/orders` fills (book correction; IMP-003 automates this going forward).
- **Validation:** full suite **194 passed** (`pytest -q`, was 189 + 5 new). New regressions:
  `test_close_position_already_flat_returns_none_without_retry`,
  `test_reconcile_exit_returns_broker_side_fill`,
  `test_reconcile_exit_none_when_position_still_open` (safety guard),
  `test_reconcile_exit_none_when_no_filled_exit`,
  `test_exit_position_reconciles_broker_side_stop_fill` (exit recorded at the real fill, not the
  price passed in). `bot.preflight` PASS (broker flat, equity $9,215.47). Service restarted
  clean, 0 positions.
- **Expected impact:** broker-side stop/target fills are recorded at their true price → win-rate
  & P&L become trustworthy, no more phantom-open rows, no 404 retry-storm at EOD, no false
  naked-overnight pages. Capital protection + data integrity; the win-rate *metric* this routine
  optimizes is now correct (it was understating wins).
- **Commit:** 9ec528f
- **Observed effect:** **Weekly (06-19): not yet validated by clean data.** The only post-ship
  session (06-18) was corrupted by the *submit-ack* failure (IMP-004's domain), so no broker-side
  stop-fill was cleanly reconciled to test this path; and the **5 stale 06-11/06-12 phantom OPEN
  rows** (ENPH/WPM/NFLX/QCOM/AMD) remain in the DB (IMP-003 reconciles *going-forward* but doesn't
  purge pre-existing residue — still on the backlog). First real test Monday 06-22.

---

## IMP-005 — 2026-06-19

- **Problem:** No trades today (Juneteenth, market closed) — but the post-close audit found
  the **2026-06-18 EOD flatten failed to actually close 7 positions** (GOOG/INTC/MU/QQQ/SE/TSLA/
  TSM). The DB recorded all 7 as "end-of-day flatten" exits with P&L at 20:05–20:16 UTC, yet the
  broker **still holds all 7** (naked, stops cancelled) **over the Juneteenth long weekend**. The
  06-18 close-orders are stuck `accepted`/`filled 0` at the broker — submitted **after** the
  16:00 ET close, they never filled.
- **Root cause:** the EOD flatten triggers on `in_close_window(candle.start, …, FLATTEN_BEFORE_CLOSE_MIN)`
  and only **executes when a candle closes** — and candle closes are *activity-driven* (a bar closes
  only when a later tick proves its interval elapsed). On a thin pre-close tape the final candles
  closed **5–16 min past 16:00 ET** (GOOG's events: 15:49, 15:54, then a 22-min gap to 16:16), so the
  market-sell flattens landed in a **closed market** → `accepted`, never filled. With the window only
  5 min wide (opens 15:55 ET) too few *liquid-tape* candles fell inside it to fire a fill-able flatten.
  IMP-004 now **detects** this (no fake exit, pages) but does **not prevent** the naked carry — this is
  the prevention half it explicitly deferred to (improvement-log candidate #2).
- **Change:** `bot/config.py` — `FLATTEN_BEFORE_CLOSE_MIN` default **5 → 15**. The flatten /
  no-new-entries window now opens at **15:45 ET**, giving the flatten several attempts while the tape
  is still liquid enough to fill before 16:00 — and doubling as a **late-entry cutoff** that kills the
  repeatedly-flagged weak last-15-min entries (06-18 QQQ conf64/xo0.04, SE conf65/xo0.07). **No risk
  widened, no safety disabled** — strictly *reduces* exposure (flattens earlier, enters less late).
- **Validation:** full suite **197 passed** (`pytest -q`, was 194 + 3 new). New/updated regressions:
  `test_close_window_15min_catches_late_thin_tape_candle` (encodes GOOG's 15:49 ET candle — outside the
  old 5-min window, inside the new 15-min one) in `tests/test_signals.py`, and a
  `cfg.flatten_before_close_min == 15` default assertion in `tests/test_config.py`. `bot.preflight`
  PASS (equity $9,248.81; correctly reports the 7 still-open positions).
- **Expected impact:** the EOD flatten fires while RTH is still liquid → close market orders fill
  before 16:00 ET → no more `accepted`-but-unfilled flattens carrying naked overnight; fewer weak
  late-day entries. Capital protection (overnight gap risk) is the headline.
- **Commit:** 99ea33d
- **Observed effect:** **Weekly (06-19): unvalidated** — shipped 06-19 (market closed). First test
  **Monday 06-22**: confirm the EOD flatten fires by ~15:45–15:55 ET with all close market orders
  FILLED before 16:00, the broker flat at the close, and nothing carries into 06-23. This is the
  *prevention* half; IMP-004 is the *detection* half — both owe their first live read Monday.
- **Observed 06-22:** the 7 lots carried from 06-18 (pre-IMP-005 residue) auto-flattened at the
  Monday open (08:02:31 UTC, the stuck `accepted` orders filled); `reconcile_exit` picked the fills
  up at 19:46 UTC but logged `DB exit … trade_id=None` (no matching OPEN row — the 06-18 fake exits
  had already CLOSED them), so today's realized P&L is uncaptured. **IMP-005's own first clean live
  test is 06-23** (no fresh 06-22 entries to flatten). The `trade_id=None` orphaning motivated IMP-006.

---

## IMP-006 — 2026-06-22

- **Problem:** Report showed `open positions: 5` while the broker held **0** — 5 rows stuck
  `status='OPEN'` in `dbo.trades` since 06-11/06-12 (ENPH/WPM/NFLX/QCOM/AMD) the broker never held.
  Same day, `reconcile_exit` closed the 7 carried lots with `DB exit … trade_id=None` (no OPEN row to
  match — already fake-CLOSED 06-18). Both are the recurring **DB⇄broker desync** the weekly graded D.
- **Root cause:** `record_exit` only updates `WHERE symbol=? AND status='OPEN'`, and the strategy
  `reconcile` only handles the broker→DB direction (adopt held names as MANAGING). **Nothing closed a
  DB-`OPEN` row the broker was no longer holding**, so phantoms accumulated, misstated the book, and
  could be swept into fictitious P&L by the EOD flatten (cf. 06-15 INTC +$154.28).
- **Change:** `bot/persistence.py` — new `TradeStore.reconcile_open_positions(broker_symbols)`: closes
  every `OPEN` row whose symbol the broker isn't holding, honestly (`exit_price=entry_price` → `pnl=0`,
  reason `reconciled: not held at broker`) and drops its `dbo.positions` row; wired into `bot/main.py`
  startup right after `strategy.reconcile(positions)`. **Bookkeeping only — no orders, no risk change.**
- **Validation:** full suite **201 passed** (was 197 + 4 new persistence regressions encoding the exact
  06-22 scenario: 5 phantoms swept, broker-held retained, no-op, DB-error-swallow). `bot.preflight` PASS.
  **Live restart confirmed:** journald `reconciled 5 phantom OPEN row(s)… AMD, ENPH, NFLX, QCOM, WPM`;
  DB now `OPEN trades=0, positions=0`, matching the flat broker.
- **Expected impact:** the book stays truthful (report `open positions` == broker), phantoms self-heal
  every startup instead of accumulating, and the EOD flatten can no longer act on positions that aren't
  there. Restores trust in closed-trade stats; no effect on entry/exit signal logic.
- **Commit:** 2635739
- **Observed effect:** (await next review — book should stay broker-matched; watch for any new
  `trade_id=None` reconcile exits, which would mean the *deeper* fix — recording the real Monday fill
  P&L against the carried lots — is still owed.)
  **Weekly (06-26): ✅ validated** — the book stayed broker-matched every session 06-23..26 (0 OPEN
  DB rows, 0 broker positions at every close), no phantoms re-accumulated, and no new `trade_id=None`
  reconcile orphan appeared after the 06-22 carried-lot cleanup. The DB⇄broker desync is closed.

---

## IMP-007 — 2026-06-23

- **Problem:** User asked why 06-22 showed "no buys, only exits." Two findings: (1) zero buys was
  **correct** — feed healthy (10,658 candles, 0 errors) but no name cleared the entry bar all session;
  rejections are silent, so a correct flat day looked dead. (2) The "exits" were **stale lots**
  (GOOG/INTC/MU opened 06-18) that carried through the 06-18 & 06-19 nights **and the weekend**, only
  clearing 06-22 on broker-side bracket fills.
- **Root cause:** the EOD flatten is **driven by the candle stream** — `_flatten_all_eod` runs only when
  a 1-min candle closes inside `in_close_window`. On **06-19 the IEX feed was silent 15:44–16:02 ET**
  (zero candles) → the flatten never ran; 06-18's window was full of websocket drops + Alpaca 504s. The
  naked-overnight page (IMP-002) only fires on a *failed close attempt*, never on a flatten that **never
  ran**, so it carried **silently**. IMP-005 widened the window 5→15 min but left it candle-gated — the
  structural hole.
- **Change:** `bot/strategy.py` — new public `tick(now_utc)` runs the close-window flatten + escalation
  on **wall-clock time** (independent of candle delivery), plus a `_POSTCLOSE_GRACE_MIN`=3 sweep so a
  feed-dead carry still gets a final close attempt + NAKED page; `_flatten_all_eod` now guarded by a
  re-entrant lock (candle thread + watchdog thread). `bot/main.py` — a daemon **watchdog thread** calls
  `strategy.tick(now)` every 30s. Fix 2: the silent `if not decision.enter: return None` now logs the
  rejection (`_log_skip`) — near-miss (scored candidate < threshold) at INFO w/ confidence, gate-closed/
  no-cross at DEBUG — so a flat session is diagnosable. **No risk widened, no entry logic changed.**
- **Validation:** full suite **207 passed** (`pytest -q`, +6 new in `tests/test_strategy.py`): watchdog
  flattens with **zero candles**, mid-session tick is a no-op, post-close grace escalates a feed-dead
  failed close once, candle+watchdog idempotent (no double-close), near-miss→INFO, non-candidate→DEBUG.
  Live restart confirmed new code (ActiveEnterTimestamp 03:32 UTC > file mtime 01:09; PID 3276294),
  clean startup, no errors.
- **Expected impact:** the EOD flatten fires on real time even if the candle feed dies at the close →
  the silent naked-weekend carry (06-18/06-19) cannot recur; and "why no buy today" is answerable from
  the logs. Capital protection (the *prevention* half IMP-005 only partially delivered) + observability.
- **Commit:** e19c4c6
- **Observed effect:** (await next review — first live test is the 06-23 close: confirm a wall-clock
  `EOD flatten` fires and any unclosable position pages NAKED, even if no candle prints in the final
  minutes.)
  **Weekly (06-26): ✅ validated 4× (the saga-closing fix)** — the wall-clock watchdog fired the EOD
  flatten at ~15:45 ET on every session 06-23..26, all market sells filled in liquid RTH before 16:00,
  broker flat every night, **0 phantom rows, no naked carry, no NAKED page**, including the 06-26
  slow-drift tape where *zero* intraday stop/target/trailing exits fired (all 11 rode to the flatten).
  The naked-overnight failure that earned last week's D cannot recur on this path.

---

## IMP-010 — 2026-06-25

- **Problem:** Third clean exit-infra session (5 trades, 2W/3L), but DB day −$33.61 vs equity −$52.59
  diverged by **$18.98**. Root: **AMD's entry was recorded at the candle-close estimate (544.71), not
  the real broker fill (547.873)** — understating its loss. The other 4 entries matched the broker to
  the cent (IMP-009 working). So IMP-009 *mostly* works but **failed for one trade**, and the failure
  was the whole day's book error.
- **Root cause:** IMP-009's `entry_fill_price` polls the parent buy's `filled_avg_price` for only
  `_ENTRY_FILL_ATTEMPTS`(6) × `_ENTRY_FILL_DELAY`(0.5s) = **~3 s** (kept short so it never stalls the
  candle thread). **AMD's market buy filled ~2 min after submission** (submitted 13:33:34, filled
  13:35:42 — an early-session/gap-up open delay), far past that budget, so `entry_fill_price` returned
  `None` and `execute` fell back to the sizing estimate. Widening the budget can't fix this (a 2-min
  synchronous poll would freeze the candle thread). The fill *is* available later — just not at submit time.
- **Change:** `bot/risk.py` — `exit_position` now re-reads the entry parent order's fill via
  `executor.entry_fill_price(entry.order_id)` **at exit time** (when the buy is definitively filled, so a
  single read returns immediately — no candle-thread stall) and carries it on a new
  `ExitResult.entry_fill_price` field (`None` when there's no entry order id or the read fails).
  `bot/persistence.py` — `record_exit` COALESCEs that corrected fill over the stored `entry_price` and
  recomputes `pnl`/`pnl_pct` off it (`None` → keeps the existing entry price, the common case). Completes
  the IMP-003/008/009 "record at the real fill" thread on the entry side, robust to **any** fill delay.
  Also a one-off broker-verified correction of today's AMD row (544.71 → 547.873, pnl −34.96 → −53.94).
  **No risk widened, no safety disabled, no entry/strategy logic touched** — pure data integrity.
- **Validation:** full suite **223 passed** (`pytest -q`, was 220 + 3 new). New regressions:
  `test_exit_position_recovers_delayed_entry_fill` (today's exact AMD scenario: re-reads order "o1",
  carries 547.873), `test_exit_position_entry_fill_none_when_unreadable_or_no_entry` (no entry → no read,
  no fabricated price; None → stored price untouched), `test_record_exit_corrects_entry_price_from_delayed_fill`
  (corrected fill threaded into entry_price + both P/L formulas); updated
  `test_record_exit_closes_trade_with_pnl_and_drops_position` to the COALESCE SQL; added `entry_fill_price`
  to the risk + strategy executor fakes. Post-fix the day's DB net (−$52.59) ties to equity to the cent.
- **Expected impact:** entries are booked at their true broker fill even when the fill lands seconds-to-
  minutes after submission → P/L and win-rate are exact (DB realized ≈ equity to the cent), and the
  high-confidence-underperformance evidence the routine is accumulating rests on accurate prices. No
  win-rate behavior change.
- **Commit:** 9e590c6
- **Observed effect:** (await next review — confirm any delayed-fill entry now books at the broker price,
  and DB realized P&L continues to tie to equity to the cent.)
- **Observed 06-26:** ✅ held — 4th straight session DB net (+$62.07) ties to equity (+$62.07) **to the cent**;
  all entry/exit prices match broker fills (the entry-fill thread IMP-009/010 is solid). Data now trustworthy
  enough to ship the first *strategy* change (IMP-011) on top of it.

---

## IMP-011 — 2026-06-26

- **Problem:** First **strategy** (entry-quality) change after the exit-infra saga closed. On the **4th
  consecutive clean-book session** (11 trades, 5W/6L, +$62.07, books exact to the cent), the long-deferred
  **weak-crossover** pattern became unambiguous on trustworthy data. Today the five entries with crossover
  sub-score **< 0.20 all lost** (COST/AMZN/SPY/QQQ/ABNB, 0W/5L); the two **strong-cross** entries (MSFT 0.58,
  NFLX 0.59) won, MSFT +$74.72 carrying the whole day. Across the four clean sessions (06-23..26): **xo<0.20
  → 1 win of 12 (8%, avg −$10.82)**, xo 0.20–0.40 → 3/6 (50%, +$0.40), **xo≥0.40 → 6/7 (86%, +$16.80)** — a
  clean monotonic relationship the (non-monotonic) confidence bands don't provide.
- **Root cause:** `evaluate_entry` gated only on `confidence.total >= entry_threshold`. The total is a weighted
  blend (crossover 30 / trend 20 / rsi 20 / volume 15 / volatility 15), so a candidate riding a **weak,
  non-accelerating 1-min cross** can still clear 60 on trend/rsi/volume weight alone — exactly the chop cohort
  flagged-but-deferred every run since 06-16 (held back pending clean exit-infra data + several clean days,
  both now satisfied). Crossover strength is the single cleanest discriminator of outcome; nothing acted on it.
- **Change:** `bot/signals.py` — `evaluate_entry` gains a `min_crossover` floor (default 0.0 = old behavior);
  a candidate now enters only if `confidence.total >= threshold` **and** `confidence.crossover >= min_crossover`,
  with a distinct diagnosable reason (`"crossover X.XX < Y.YY"`) when it clears the total but fails the floor.
  `bot/config.py` — new `min_crossover` field, env `MIN_CROSSOVER`, **default 0.20** (the xo<0.20 dead zone),
  validated to [0,1]. `bot/strategy.py` — passes `min_crossover=cfg.min_crossover` into `evaluate_entry`.
  Floor set at 0.20 (not higher) so the ~coin-flip 0.20–0.40 mid band — which produced 3 of today's winners
  (AAPL/TSLA/UNH) — is kept. **No threshold/weights/sizing/risk changed — strictly a stricter entry filter
  (capital protection): fewer, higher-quality entries, never more exposure.**
- **Validation:** full suite **228 passed** (`pytest -q`, was 223 + 5 new). New regressions in
  `tests/test_signals.py`: `test_weak_crossover_clears_total_but_below_floor` (the fixture = today's QQQ/SPY/COST
  cohort: total ≥ 60 yet crossover < 0.20), `test_min_crossover_floor_blocks_weak_cross_chop_entry` (floor
  rejects it with the crossover reason), `test_min_crossover_floor_disabled_lets_weak_cross_enter` (0.0 =
  pre-IMP-011 behavior), `test_min_crossover_floor_allows_strong_cross_entry` (MSFT/NFLX-style xo≥0.40 still
  enters); `tests/test_config.py::test_min_crossover_default_and_override` (0.20 default, 0 disables, >1 raises).
  `bot.preflight` PASS (Alpaca ACTIVE, equity $9,308.57, 0 positions; 1 WARN = market closed).
- **Expected impact:** the weak-cross chop cohort (≈8% historical win rate) is filtered out → **higher win
  rate and fewer churn losses** with no added risk. Expect a modest drop in entry *count*; the surviving
  entries should win at a materially higher rate (clean-day data: 50%+ vs 8%). First win-rate change shipped
  by this routine; everything prior was capital-protection / data-integrity.
- **Commit:** 0002ed9
- **Observed effect:** (await next review — confirm entry count holds up [not zero-trade sessions], the
  `"crossover < 0.20"` skip logs appear for filtered candidates, and the realized win rate on entries that DO
  fire rises vs the 4-clean-day baseline. Watch for over-filtering on strong-trend days where width is naturally
  tight.)
  **Weekly (07-03): ✅ VALIDATED over its first full week** (the week's headline result). Across the 4 trading
  sessions 06-29..07-02: **entry count held every day** (12 / 9 / 7 / 7 — never collapsed toward zero, the
  weekly review's #1 worry); **every entry honored the floor** (xo ≥ 0.20 each session, lowest survivors ~0.206–0.24);
  the `crossover X.XX < 0.20` skip logs **fired daily** on the weak-cross chop cohort (C/SPY/JPM 06-29; NFLX/NVDA/
  MSFT/C/GOOG/UNH 07-01; 7 rejects 07-02); and **win rate rose to 57% (20/35), +$171.24, PF 1.59** vs the 40%
  four-clean-day baseline. No over-filtering — GOOG entered at *exactly* 0.20 on 06-30 and barely paid (+$0.08),
  confirming the floor is correctly placed. Within-survivor crossover stays noisy/non-monotonic (MSFT 0.66 was
  06-29's worst loser) — expected, since the floor cuts the dead zone but does not rank above it. **Keep at 0.20.**

---

## IMP-012 — 2026-06-30

- **Problem:** A clean, profitable day (9 trades, 7W/2L, +$61.79, books exact 6th straight) was swamped by
  **504 ERROR tracebacks**: AMD's and SE's **broker-side stop legs filled mid-session** (AMD's stop order
  698c6cdf returned 422 `code 42210000 "order is not open"` from **15:07 UTC** onward; SE's 80faa3b7 likewise),
  yet the bot **never detected the fill**. The trailing-stop ratchet kept trying to move those already-filled
  stop orders every candle for **~4.5h** (AMD's phantom "stop" climbing to 572 while it had actually exited at
  552), and both symbols sat **MANAGING and un-re-enterable** until the EOD flatten finally reconciled them.
- **Root cause:** `OrderExecutor.replace_stop_price` caught **every** exception into a single
  `log.exception(...)` + `return None`, so the caller (`RiskManager.update_trailing_stop`) treated a stop leg
  that had **filled** (position gone — code 42210000 "order is not open") identically to a transient move
  failure: keep the old stop and **retry next candle, forever**. IMP-003 detects an already-flat position at
  *close* time (404 "position not found"); nothing detected the broker-side fill at *trailing-update* time, so
  the symbol stayed MANAGING (no re-entry possible) and the log filled with tracebacks until the close.
- **Change:** `bot/executor.py` — new `_is_order_gone(exc)` (recognises 422 `42210000 "order is not open"`,
  distinct from `_is_position_gone`'s 404) and a new `StopOrderGone` exception; `replace_stop_price` now, on
  that specific error, logs a concise **WARNING** (not a traceback) and **raises `StopOrderGone`** instead of
  swallowing it as `None`. `bot/risk.py` — new `TrailResult` enum (`MOVED`/`HELD`/`STOP_GONE`);
  `update_trailing_stop` returns it and maps `StopOrderGone` → `STOP_GONE`. `bot/strategy.py` — `_manage` now,
  on `STOP_GONE`, **reconciles the real exit once** via the proven `exit_position`→`reconcile_exit` path
  (records the true broker-side fill) and **releases the symbol to WAITING** — the same transition the EOD
  flatten produces, just at the moment the stop actually fills. **No risk widened, no safety disabled, no entry
  logic changed** — exit-infra / observability / state-correctness (IMP-003's family); it does NOT confound
  IMP-011's first-week evaluation.
- **Validation:** full suite **231 passed** (`pytest -q`, was 228 + 3 new). New regressions:
  `tests/test_executor.py::test_replace_stop_price_raises_when_order_not_open` (today's AMD 422 → `StopOrderGone`,
  generic errors still → `None`), `tests/test_risk.py::test_trailing_stop_reports_stop_gone_when_leg_filled`
  (a filled leg surfaces as `TrailResult.STOP_GONE`; existing trailing tests updated to the enum),
  `tests/test_strategy.py::test_managing_reconciles_and_frees_when_stop_filled` (today's exact AMD/SE scenario:
  the trail finds the stop gone → exit reconciled from broker history → symbol freed to WAITING, not stuck
  MANAGING). `bot.preflight` PASS (Alpaca ACTIVE, equity $9,460.02, 0 positions; 1 WARN = market closed).
- **Expected impact:** a broker-side stop fill is detected the moment it happens → **no more minutely 422
  traceback storms** (504× today), the books are reconciled at the true fill *immediately* rather than only at
  the EOD flatten, and a stopped-out symbol returns to WAITING (re-enterable on a fresh valid cross, exactly as
  the EOD-flatten path already permits). Observability + state-correctness; no win-rate behaviour change.
- **Commit:** c9fbcdc
- **Observed effect:** (await next review — confirm an intraday broker-side stop fill now logs a single WARNING
  + a `trailing stop (stop/target filled broker-side)` exit at the real fill time, with **zero** "could not move
  stop order" tracebacks, and the symbol freed to WAITING rather than carried MANAGING to the close.)
  **Weekly (07-03): ✅ validated, with one complementary gap left open.** Shipped on the 06-30 21:27 UTC restart;
  07-01 and 07-02 both ran on it with **0 tracebacks, 0 WARNING lines, no 422 "order is not open" storm** — the
  minutely traceback loop that swamped the 06-30 log (AMD stop 698c6cdf, ~4.5h of ERRORs) **cannot recur** on this
  path. BUT IMP-012's *exact* scenario (a trail *attempting* to move an already-filled stop) never arose; instead a
  **complementary residual gap** surfaced **3× (TSLA 07-01, GOOG+SE 07-02)**: when a broker-side stop fills and **no
  later higher-high re-triggers a replace**, the doomed-move path never runs, so the fill is caught only at the 19:45
  EOD reconcile and the symbol sits MANAGING for hours. **Zero realized cost all 3×** — books stayed exact to the
  cent, no naked risk, and no fresh valid re-entry was blocked (arguably a mild same-day cooldown). The staged fix
  (piggyback the IMP-007 wall-clock `tick()` with a bounded MANAGING `get_open_position` reconcile) was correctly
  **held back** — ship trigger is this weekly grade OR the next occurrence that demonstrably blocks a real re-entry.

---

## IMP-013 — 2026-07-06

- **Problem:** First **sizing** change (all prior IMPs were exit-infra, warmup, entry-fill, or the IMP-011
  entry filter). On the post-holiday reopen (11 trades, 6W/5L, **−$52.33**, PF 0.50, books exact to the cent),
  the loss was an **expectancy/sizing** problem, not a win-rate one: avg loss **−$20.74** vs avg win **+$8.56**.
  The two **highest-confidence** trades were the two **biggest losers** — **AVGO** (conf **96.28**, sized ~37%
  of BP → qty 9 → **−$55.80**, the day's single biggest loss) and **INTC** (conf 84.66 → **−$24.00**) — i.e.
  Model A bet the **most** capital on the setups that lost the most. This is the long-accumulating
  high-confidence-underperformance pattern, now vividly confirmed: the all-time `vw_confidence_outcome` curve is
  **non-monotonic and inverts at the top** — **70-79 is the peak (+$246.28, 57%, 44 tr)**, 60-69 +$157.56 (48%,
  81 tr), **80-89 mediocre (+$34.02, 55%, 11 tr)**, **90-100 negative (−$109.74, 0% win, 2 tr)**.
- **Root cause:** `bot/sizing.py` `plan_model_a`/`plan_model_b` scale position size **linearly across confidence
  [threshold, 100]** (`alloc_fraction`: MIN_ALLOC at 60 → MAX_ALLOC at 100). That encodes an assumption —
  *realized edge grows monotonically with confidence up to 100* — which the 138-trade outcome curve **falsifies**:
  edge peaks in the 70s and does not improve (indeed inverts) above it. So the ramp systematically over-sizes the
  exact band that underperforms. Confidence is the strategy's *ranking* heuristic, not a probability of profit
  (CLAUDE.md) — sizing treated it as the latter above the sweet spot.
- **Change:** new tunable **`SIZE_CONFIDENCE_CAP` (env, default 85.0)** in `bot/config.py` — the confidence used
  **for sizing only** is capped at this value (`eff_conf = min(confidence, cap)`) in both `plan_model_a`
  (alloc fraction) and `plan_model_b` (risk multiplier); `bot/executor.py` threads `cfg.size_confidence_cap`
  into both `plan_*` calls. A candidate scoring above the cap is sized **as if it scored the cap** — so it only
  ever **shrinks** a top-band position (e.g. today's AVGO conf 96 would size as conf 85: ~0.29 of BP → qty 7,
  not 0.37 → qty 9). Default 85 sits **above the proven 70-79 peak with a buffer**, de-sizing only the
  mediocre-to-negative 86-100 region; validated to lie in **[ENTRY_THRESHOLD, 100]** (100 disables it,
  = pre-IMP-013 behavior; a cap below the threshold is rejected). **No entry blocked, no risk widened, no stop /
  threshold / weight / entry logic touched — strictly a capital-protection *reduction* on the top confidence band.**
  This is orthogonal to IMP-011 (which filters *entries*) and does not confound its evaluation.
- **Validation:** full suite **235 passed** (`pytest -q`, was 231 + 4 new). New regressions in
  `tests/test_sizing.py`: `test_model_a_size_confidence_cap_shrinks_top_band` (today's AVGO conf-96 scenario —
  uncapped 37 shares vs capped-at-85 28 shares, and a candidate exactly at the cap sizes identically),
  `test_model_a_size_confidence_cap_leaves_below_cap_and_default_unchanged` (conf 80 below the cap is untouched;
  default 100 == pre-IMP-013), `test_model_b_size_confidence_cap_limits_multiplier` (the risk multiplier honors
  the cap); `tests/test_config.py::test_size_confidence_cap_default_and_override` (85 default, 100 disables,
  <threshold and >100 both raise `ConfigError`). `bot.preflight` **PASS** (Alpaca ACTIVE, equity $9,427.33,
  0 positions; 1 WARN = market closed).
- **Expected impact:** on very-high-confidence entries (the historically worst-performing, currently
  largest-sized band) position size and therefore **per-trade loss** shrink → smaller drawdown on the exact
  cohort that loses, with **no change to win rate or entry count** (nothing is filtered — only the top-band size
  is trimmed). On a day like today AVGO's loss would have been ~−$43 rather than −$55.80 (~$13 less), improving
  the day's PF without removing a single trade. First capital-*sizing* change shipped by this routine.
- **Commit:** ac195d6 (deployed live on the 2026-07-06 21:26 UTC restart — warmup primed 22/22, clean startup)
- **Observed effect:** (await next review — confirm that any conf > 85 entry is sized as conf 85 [smaller qty
  than the linear ramp would give], that entry *count* is unchanged vs the linear-ramp baseline, and that the
  top-band per-trade loss shrinks; re-check the `vw_confidence_outcome` 80-100 bands over the coming weeks to see
  whether de-sizing the top improves overall PF. If a cleaner sizing-vs-confidence relationship emerges, revisit
  the cap value [85] — set it to 100 to fully revert.)
- **Observed 07-09: ✅ first live confirmation.** INTC entered at **conf 94.26** (all sub-scores maxed) and was
  the day's **single biggest loser (−$34.68, −1.25%)** — the exact top-band inversion IMP-013 targets. The cap
  applied correctly: sized off **eff_conf 85** → alloc_fraction 0.081 (qty **24**) vs the linear ramp's ~0.093
  (qty ~**27**) — ~3 fewer shares / ~$347 less notional at risk, trimming the loss by ~$5. The all-time
  `vw_confidence_outcome` **90-100 band is now 0W/3 tr/−$144.42**; 70-79 remains the peak (54 tr, 54%, +$232.93).
  Entry count unaffected (nothing filtered). Keep observing 80-100 PF over coming weeks before revisiting the cap.
- **Observed 07-10 (weekly review): ⚠️ directionally validated but only ONE live binding all week.** The cap
  engaged exactly once — **INTC 07-09** (conf 94.26 → de-sized off eff_conf 85, ~$347 less notional, ~$5 less
  loss). No other >85-conf entry occurred to test it: 07-06's AVGO conf 96 (−$55.80, the week's worst) predated
  the 21:26 UTC deploy; 07-07 peaked at NFLX 79.5; 07-08 at BABA 79.8; 07-10 at NVDA 83.76 / SE 83.00 (both <85).
  Meanwhile the **all-time 90-100 band deepened to 0W/3 tr/−$144.42** (AVGO 96 + INTC 94 both losers) — the
  inversion thesis is **reconfirmed**, but IMP-013 is **capital-protective sizing, not an entry guard**: it can
  only shrink the damage it does not prevent. Correct and low-risk, but **still early** — needs several more >85
  bindings before its PF effect on the 80-100 bands can be judged. Keep at 85.
- **Observed 07-17 (weekly review): ⚠️ STILL bound only ONCE ever — ZERO >85-conf entries all week (07-13..17).**
  Peak confidence all week was TSLA **83.60** (07-14), below the 85 cap, so IMP-013 **never engaged**; it remains
  bound a single time live (INTC 07-09). The all-time **90-100 band is unchanged at 0W/3 tr/−$144.42** (no new
  top-band trade). But the adjacent **80-89 band flipped negative and deepened** — from **+$38.63 (14 tr, 07-10)**
  to **−$33.73 (41% win, 17 tr)** — driven by NFLX 83.21 (−$48.96, 07-13) and TSLA 83.60 (−$22.05, 07-14), the
  8th+ instances of the ≥80-underperformance pattern. IMP-013 caps at 85 so it does **not** touch this 80-85 zone.
  **Multi-review gate to lower the cap toward ~80 ("≥2–3 more >85 bindings AND 80-89 deterioration") is now
  HALF met** — the 80-89 deterioration is confirmed on fresh data, but the ">85 bindings" half is stuck at 1
  because the market simply produced no ≥85 entries. **Keep at 85; still cannot judge its 80-100 PF effect.**
  The proving of IMP-013 is now bottlenecked on market conditions, not process — de-prioritize behind the
  broad-adverse-day stand-down (the week's #1 open design priority).

---

## IMP-014 — 2026-07-10

- **Problem:** SE's **broker-side stop filled @14:33:21 UTC @113.21** (a −0.82% loss, confirmed in
  `/v2/orders`), but the bot **did not detect it until the 19:45 EOD flatten** — SE sat `MANAGING`
  and un-re-enterable for **~5h**, and its exit was booked at **19:45** tagged `end-of-day flatten
  (stop/target filled broker-side)` rather than at the real ~14:33 intraday fill. This is the
  **4th occurrence** of IMP-012's flagged **residual gap** (after TSLA 07-01, GOOG+SE 07-02) and the
  first to produce a concretely **mistimed/mislabelled** row in `dbo.trades` — the very win-rate
  metric this routine optimizes. (Contrast today's TSLA, whose stop filled on a *rising* tape and was
  caught cleanly intraday at 16:20 via the trailing path.)
- **Root cause:** the broker-side stop fill is only surfaced as `StopOrderGone` when the trailing
  ratchet **attempts a replace**, and `update_trailing_stop` only replaces on a **higher high**. When
  the stop fills on a **down move** (SE fell straight from entry), no higher high ever occurs → no
  replace is attempted → the 422 is never raised → the fill is invisible to the state machine until
  the EOD flatten's `reconcile_exit` finally catches it. IMP-012 fixed the *rising* case; the *falling*
  case was explicitly deferred (staged fix: "piggyback the IMP-007 wall-clock `tick()` with a bounded
  MANAGING reconcile"). Today is the ship trigger — a recurring gap now corrupting the trade record.
- **Change:** `bot/risk.py` — extracted the exit-recording tail of `exit_position` into a shared
  `_record_exit(...)`; added **`reconcile_if_closed(symbol, entry)`**, a **read-only** poll that calls
  the existing `reconcile_exit` (returns `None` while the broker still holds the position, so it
  **never submits a close**) and, on a real fill, records the exit at the true broker price tagged
  `stop/target filled broker-side`. `bot/strategy.py` — `tick()` now, **outside** the close window and
  while the market is open, calls new `_reconcile_managing()`: it sweeps `MANAGING` symbols and releases
  any whose broker-side stop/target has filled, freeing them to `WAITING` within a watchdog tick (~30s)
  instead of hours later. The candle thread's `_manage` STOP_GONE release and the sweep are both guarded
  by `_flatten_lock` + a state recheck so the same fill is **never recorded twice**. **No risk widened,
  no safety disabled, no entry/sizing/threshold logic touched** — state-correctness + data-integrity
  (IMP-003/012 family). Does not confound IMP-013 (still under observation).
- **Validation:** full suite **240 passed** (`pytest -q`, was 235 + 5 new). New regressions:
  `tests/test_risk.py::test_reconcile_if_closed_records_broker_side_fill` (today's SE scenario: fill
  @113.21 recorded, tagged broker-side, **no close submitted**), `..._none_when_still_open` (open
  position untouched), `..._clears_trailing_state`; `tests/test_strategy.py::
  test_tick_reconciles_broker_side_stop_fill_outside_close_window` (mid-session tick detects the gone
  position, reconciles once, frees to WAITING; second tick is a no-op) and
  `test_tick_reconcile_leaves_open_position_managing` (a still-held position stays MANAGING). `bot.preflight`
  **PASS** (Alpaca ACTIVE, equity $9,307.15, 0 positions; 1 WARN = market closed).
- **Expected impact:** a broker-side stop/target that fills on a down move is detected within a tick →
  the exit is booked at its **true intraday time & price** (not the 19:45 EOD estimate), the reason is
  correctly `stop/target filled broker-side` (so the exit-bucket audit stays honest), and the symbol
  returns to `WAITING` promptly (re-enterable on a fresh valid cross). Data integrity + state-correctness;
  no win-rate behaviour change.
- **Commit:** c92fdfd (deployed live on the 2026-07-10 post-close restart)
- **Observed effect:** (await next review — confirm any intraday broker-side stop fill now logs
  `reconciled broker-side exit for <SYM> -> WAITING` mid-session and books the exit at the fill time,
  with **zero** `end-of-day flatten (stop/target filled broker-side)` rows for stops that filled hours
  before the close; and that no double-exit / double-Telegram occurs when the trailing path and the sweep
  race the same fill.)
- **Observed 07-10 (weekly review): UNPROVEN — shipped today AFTER the close.** Live on the **21:23 UTC**
  post-close restart (`NRestarts=0`, 240 tests). Today's **SE** (stop filled @14:33 UTC on a down move,
  undetected until the 19:45 EOD flatten) is the **motivating regression case, not yet a validated catch** —
  the fix went live only after that row was already booked. First real live test is next week; ship-trigger
  from last week's weekly (the 07-03 grade) was correctly met, and the change is pure data-integrity so it
  does not confound IMP-013's still-open evaluation.
- **Observed 07-17 (weekly review): ✅ FULLY VALIDATED — 7 clean live catches across 3 sessions.** Its first
  live proving week delivered exactly the behaviour the 07-10 weekly asked for. Every one of the week's **7
  `stop/target filled broker-side` exits** (−$188.08 total) was a **down-move broker-side stop fill the trailing
  ratchet can't surface**, and each was reconciled **mid-session within a watchdog tick (~20–30s)**, booked at
  its **true intraday fill price/time**, and the symbol freed to `WAITING`: **INTC #1 & WMT (07-14), SE & NFLX
  (07-15), MU/INTC/TSM (07-17)**. **Zero** late `end-of-day flatten (stop/target filled broker-side)` rows,
  **zero** double-exit / double-Telegram, books exact to the cent all 5 days. The prompt release even **produced
  a win**: INTC's 07-14 same-day re-entry (+$22.33) was only possible because IMP-014 freed it promptly after the
  14:05 stop. IMP-012's residual down-move gap is **closed and proven**; the 07-10 weekly's #1 focus is retired.
  No parameter to revisit — this is settled data-integrity infra.

---

## IMP-015 — 2026-07-20

- **Problem:** Today's report showed a benign **+$6.28 / 3W-4L**, but equity fell **−$93.33**
  ($9,021.08 → $8,927.72) — a **$99.61** DB↔equity gap. Root: **NVDA was booked as a phantom
  +$41.15 win when it was really a −$58.46 stop-out.** NVDA's bracket buy filled **~2.5 min late**
  (submitted 13:33, filled 13:35:52 @206.807 — the known delayed-fill pattern of IMP-010); the
  IMP-014 wall-clock MANAGING sweep fired ~30 s after entry, while the position had **not yet opened**.
  `get_open_position` 404'd (no position), `reconcile_exit` treated that as "already flat," and matched
  a **stale prior-session NVDA sell (@209.615)** as the exit → a fake win, NVDA freed to WAITING, and
  the bot **desynced from the broker** (the real buy then filled and rode to a real broker-side stop
  @202.31 @19:16 that the DB never recorded). Corrupts exactly the win-rate/P&L/confidence data this
  routine optimizes (NVDA conf 82.40 flipped an 80-89 loser into a phantom win).
- **Root cause:** `RiskManager.reconcile_if_closed` (the IMP-014 down-move sweep) concluded "closed"
  from a bare 404 **without ever confirming the entry was filled**. A 404 means EITHER opened-then-closed
  OR **never-opened-yet** (entry fill still pending); the two are indistinguishable from the position
  read alone, and `reconcile_exit` then matches the most-recent filled sell — which, for a never-opened
  position, is a **stale sell from a prior session**. IMP-014 assumed a MANAGING symbol was always an
  open position; a delayed entry fill breaks that assumption.
- **Change:** `bot/risk.py` — `reconcile_if_closed` now first calls `entry_fill_price(entry.order_id)`
  and **returns `None` (leaves the symbol MANAGING) until the entry buy has actually filled**; only then
  does it consult `reconcile_exit`. When there is no entry order id (a startup-reconciled holding, which
  was confirmed held at startup) the guard is skipped, preserving that path. **No risk widened, no safety
  disabled, no entry/exit logic changed** — pure state-correctness / data-integrity (IMP-003/012/014
  family). Also a one-off broker-verified correction of today's NVDA row (entry 206.45→206.807, exit
  209.615→202.31 @19:16:18, pnl +41.15→−58.46) so the book ties to equity to the cent (−$93.33).
- **Validation:** full suite **241 passed** (`pytest -q`, was 240 + 1 net new). New regression
  `tests/test_risk.py::test_reconcile_if_closed_skips_while_entry_unfilled` (today's exact NVDA scenario:
  entry unfilled → the sweep never consults order history, records no phantom exit, leaves it MANAGING);
  the three existing `reconcile_if_closed` tests updated to supply a filled entry (the new precondition),
  and `_StopGoneCloser.entry_fill_price` now returns a real fill (it models a genuinely-opened position).
- **Expected impact:** a MANAGING symbol whose entry buy hasn't filled yet is never mistaken for a closed
  position → no more phantom exits from stale prior-session sells, no DB↔broker desync, and the
  win-rate/P&L/confidence data stays trustworthy. Data integrity + state-correctness; no win-rate behavior
  change. **This preempted the daily-loss stand-down (the weekly's #1 strategic priority): you don't ship
  a strategy change on a corrupted book — ship the stand-down on the next clean-book session.**
- **Commit:** 844dfa9
- **Observed effect:** ✅ **VALIDATED (weekly 07-24).** Books tied to equity **to the cent every session
  since** — 07-21 (−$9.15), 07-22 (−$36.25), 07-23 (flat, 0 trades), 07-24 all reconciled exactly, **zero
  phantom-win rows, no DB↔broker state-desync recurrence.** No `reconcile_exit` fired on an unfilled entry in
  the week's logs; the delayed-fill / MANAGING-sweep interaction is closed and the confidence/P&L data this
  routine optimizes is trustworthy again. The precondition it set (a clean book) is what let IMP-016 ship.

---

## IMP-016 — 2026-07-21

- **Problem:** The long-only ribbon strategy has **no edge and takes real damage on a market-wide down
  day** — it keeps opening fresh longs on intraday bounces that each resume lower — and the bot has **no
  daily-loss / consecutive-loss entry halt** (only the feed-loss fail-safe). Two qualifying broad-adverse
  sessions on record: **07-07 −$179 (1W/10L whipsaw)** and **07-17 −$113 (0W/5L risk-off selloff)** —
  together −$292, the bulk of the recent drawdown. This was the **weekly review's explicit #1 priority**
  ("evidence gate is MET") and the deferred item across 07-07/07-17/07-20; IMP-015 (07-20) preempted it to
  fix a book-corruption bug with the instruction *"ship the stand-down on the next clean-book session."*
  **Today (07-21) is that clean-book session** — books tie to equity to the cent (DB −$9.15 == equity
  −$9.15, broker flat), a benign day (5W/3L) with the one-change slot free. Shipped **deliberately on a calm
  day, NOT reactively** to today's −$9.15 (today would not have tripped it — see below).
- **Root cause (of the drawdown pattern):** the 5m gate opens multiple mid-band longs on intraday bounces
  during a market-wide adverse tape; each fades/stops. Nothing halts the run — the bot keeps re-arming.
- **Change:** a **broad-adverse-day stand-down** (session circuit-breaker). `bot/risk.py` — `RiskManager`
  now tallies each closed trade's realized P/L and consecutive-loss streak at its single exit chokepoint
  (`_record_exit` → `_account_for_standdown`); when the session realized loss breaches
  `standdown_max_loss_pct` of the session-open equity **OR** `standdown_max_consecutive_losses` losing exits
  occur back-to-back, it **latches a stand-down** and `entries_allowed` goes False (halting NEW entries —
  open positions are still managed/flattened, mirroring the feed-loss halt). `roll_session(day)` resets the
  tally + clears the halt at each new session; the strategy drives it from the candle's Eastern date in
  `on_short_candle` before the entry gate. `bot/config.py` — 3 tunables: `STANDDOWN_ENABLED` (default True),
  `STANDDOWN_MAX_LOSS_PCT` (0.025), `STANDDOWN_MAX_CONSECUTIVE_LOSSES` (3). `bot/executor.py` — caches
  `last_equity` off the account read `execute()` already does (session-open baseline; no extra broker call).
  **No risk widened, no sizing change, no stop disabled — it can only *stop opening*.**
- **Validation:** full suite **250 passed** (was 241 + 9 net new). New tests replay the motivating scenarios:
  `test_standdown_trips_after_consecutive_losses` (07-17 pattern → halts after the 3rd consecutive loss,
  pages once), `_winner_resets_the_streak`, `_trips_on_session_loss_pct` (2.5% backstop), `_resets_at_next_
  session`, `_disabled_never_trips`, `_skips_exit_without_entry`, `_and_feed_halt_compose`, plus strategy-
  level `test_standdown_blocks_new_entries` / `test_new_session_candle_resets_standdown`. Preflight all-PASS
  (config loads with the 3 new tunables). On **07-17** the streak trigger trips after TSM (3rd loss),
  blocking INTC (−$39.60) + NFLX (−$23.85) ≈ **−$63 saved**; on **07-07** it blocks ~7 later losers. On
  **today (07-21)** it does **NOT** trip (exit-time order MU−/INTC−/MU+… — the winner resets the streak at 2,
  and realized never approached −2.5%) — confirming it is dormant on normal days.
- **Expected impact:** caps the tail loss on a broad-adverse regime day (the −$179 / −$113 disaster
  sessions) by halting new entries after 3 consecutive losses or a −2.5%-of-equity session drawdown, while
  leaving normal chop/mixed days (like today) untouched. First real test is the next genuine risk-off tape.
- **Commit:** af56b67
- **Observed effect:** ⏳ **PARTIALLY VALIDATED (weekly 07-24).** First live observation **07-22 = correct
  benign non-trip** (session loss −0.41% of equity vs the −2.5% backstop, and the winner reset the loss
  streak at 2 before any 3-in-a-row) — exactly the dormant-on-a-normal-day behavior intended, **no misfire.**
  **07-23** was a genuine risk-off tape (Nasdaq −2.2%) but produced **0 exits** (the long-only 5m gate sat it
  out entirely), so the stand-down had nothing to act on. **A genuine broad-adverse TRIP has NOT yet been
  observed** — the real test still awaits a risk-off run of ≥3 straight stops or a −2.5% session drawdown
  *while positions are open*. Shipped correctly as the single change on a clean-book calm day; keep watching
  (next week's FOMC + mega-cap earnings + month-end is a plausible first-trip setup).

---

## IMP-017 — 2026-07-25

- **Problem:** user-raised ("why does ustradebot always lose?"). A full-book audit of all **219 closed
  trades** in `USBot.dbo.trades` shows the bot is **net −$171.62, PF 0.92, 44.7% win, payoff 1.14** —
  effectively a **zero-edge coin flip**, up +$380 through 07-02 then −$552 since 07-06 (win rate collapsed
  50.4% → 37.0%). Segmenting by **entry hour (ET)** localizes the entire lifetime loss to the opening range:

  | entry window | n | net | win% | PF |
  |---|---|---|---|---|
  | **pre-10:00 ET** | **41** | **−$407.34** | **36.6%** | **0.45** |
  | 10:00+ ET | 178 | **+$235.73** | 46.6% | 1.17 |

  Those 41 trades are **19% of the book but 48% of all stop-out damage** (−$528 of −$1,095), averaging
  **−$35 per stop-out vs −$15** for the rest of the day. Median pre-10:00 trade **−$7.15** vs −$0.27 kept.
- **Root cause:** the 1-min trigger ribbon is fed the **opening auction gap and the first noise bars**, so
  the crossovers it fires on in the first 30 minutes are **gap artifacts, not trends** — they mean-revert
  into the stop. Concentrated in the high-beta gappers: AVGO −$195, INTC −$102, AMD −$84, MSFT −$72,
  TSLA −$50. Nothing in the code gated it: `MARKET_OPEN=09:30` and the bot armed entries from the bell.
- **Change:** an **opening-range blackout**. `bot/signals.py` — new `in_open_blackout(ts, open, close,
  entry_start)`, the mirror of `in_close_window` at the other end of the session. `bot/strategy.py` —
  checked in `on_short_candle` immediately after `market_is_open`, i.e. **after** the MANAGING branch has
  already returned, so it gates **NEW ENTRIES ONLY**: open positions keep trailing their stop and the EOD
  flatten is untouched. `bot/config.py` — `ENTRY_START` (default `10:00`), validated into
  `[MARKET_OPEN, MARKET_CLOSE)`; setting it equal to `MARKET_OPEN` disables the blackout. `bot/main.py` —
  startup banner now prints the live entry window so a review can confirm the gate from the log alone.
  **No risk widened, no sizing change, no stop moved — it can only *stop opening*.**
- **Why 10:00 and not the argmax:** a cutoff sweep over the full history is a **smooth single-peaked
  plateau**, not a spike — 09:45 +$292, 09:50 +$390, **09:55 +$435**, **10:00 +$407**, 10:15 +$425,
  10:30 +$332, decaying to +$198 by 11:00. 09:55 is the sample maximum; **10:00 was chosen deliberately**
  because it sits mid-plateau on a conventional session boundary rather than on the sample's noise peak.
- **Robustness (all four checks pass — this is not a fitted result):** ① helps in **both regimes** —
  June trend +$174.81 (+$380→+$555), July chop +$232.53 (−$552→−$320); ② **6 of 7 weeks improved**, 1
  neutral (no pre-10:00 trades), **0 worsened**; ③ **not outlier-driven** — excluding the 5 worst blocked
  trades the blocked bucket is still −$83, and the whole distribution is shifted (median −$7.15 vs −$0.27);
  ④ mechanism confirmed by the exit-reason mix (the blocked bucket is where the stop-outs concentrate).
- **Validation:** full suite **263 passed** (was 251, +12 new), TDD — tests written first and confirmed
  failing (`ImportError: cannot import name 'in_open_blackout'`) before the implementation. New tests:
  `test_open_blackout_blocks_the_first_thirty_minutes`, `_boundary_opens_exactly_at_the_cutoff`
  (09:59 blocked / 10:00 allowed), `_disabled_when_cutoff_equals_open`, `_false_outside_the_session`,
  `_handles_est_edt_shift` (EST/EDT wall-clock, not UTC offset); config parse/default/validation ×4; and
  strategy-level `test_no_entry_during_the_opening_blackout`, `_entry_allowed_from_the_cutoff_minute`,
  `_blackout_disabled_by_setting_entry_start_to_the_open`, plus the safety property
  **`test_open_positions_are_still_managed_during_the_blackout`** (a position carried into the opening
  range must keep trailing — gating the MANAGING path would leave it unmanaged exactly when it gaps).
- **Expected impact:** **−$171.62 → +$235.73** on the historical book; PF 0.92 → 1.17, avg trade −$0.78 →
  +$1.32, win 44.7% → 46.6%. **Caveat: this is a first-order replay** — it removes the gated trades but
  cannot model later entries that the freed capital might have allowed (concurrency ran median 6/day, max
  17, against `MAX_ALLOC=0.10` ≈ 10 slots; 8 of 31 days exceeded 8 concurrent). Since post-10:00 trades
  average +$1.32, the unmodeled effect more likely helps than hurts — but +$407 is an estimate, not a
  promise. **PF 1.17 is a thin edge, not a fixed bot:** July stays net negative even gated (−$320), and
  the structural problems remain untouched (see backlog).
- **Deploy:** service restarted and **deploy-gap verified** (`ActiveEnterTimestamp` 01:34:10 UTC > newest
  source mtime 01:33:43) — the running process logs `Entry window: 10:00-16:00 ET (opening-range blackout
  on, IMP-017, EOD flatten from 15 min before the close)`, warmup primed 21/21, equity $8,927.24, book flat.
- **Backlog surfaced by the same audit (NOT shipped — one change at a time):**
  1. **`TAKE_PROFIT=0.10` has never once been hit in 219 trades** (median winner +0.75%, so the target is
     13× the median winner — it is decorative). The 2% stop / 10% target is a 5R ask that squashes the
     realized distribution: **192 of 219 trades finish between −1R and +1R, avgR −0.006**.
  2. **The trailing stop is inert** — `TRAIL_PERCENT=0.02` equals `STOP_LOSS=0.02`, so it cannot lock any
     profit until price is up >2%; **only 2 of 219 trades ever exited via the trailing path** despite
     `strategy.py` describing it as the primary exit. **74% (161/219) exit on the EOD-flatten clock.**
  3. **Flat 2% stop, no ATR scaling** (measured 1.89–3.28%, median exactly 2.00%) — inside the noise on
     AVGO/NVDA/AMD, far outside it on WMT/COST/JPM.
  4. **Confidence is inverted at the top and sizing amplifies it**: conf 70–80 → +$0.55/trade, but 80–85 →
     −$5.24, and **90+ → 0% win, −$48.14/trade (n=3)**. IMP-013 caps the ramp at 85; the data argues the
     ramp should be flat or inverted above ~80. Small n — needs more observations before acting.
  5. **Hold-overnight was tested and REFUTED** (asked directly by the user): replaying every trade forward
     on daily bars, holding +1d = −$210, +2d = −$482, +3d = −$1,536 with the 2% stop live (and −$1,003 /
     −$1,790 / −$3,283 without it) — **every variant worse than same-day flatten**, win rate falling
     monotonically 41.6% → 20.3% as the hold lengthens. Cause: **10.7% of overnight holds gap straight
     through the 2% stop** (p05 −3.05%, worst −6.55%), so the stop cannot protect overnight. Winners do not
     keep running — at +1d **47 improved vs 48 gave back** (net −$370). And it merely levers the regime:
     June +$702 better, July **−$1,489 worse**. Structurally, a 1-min ribbon signal has a horizon of
     minutes and cannot underwrite multi-day risk. **Keep the EOD flatten.**
- **Commit:** 957a21e
- **Observed effect:** ⏳ pending — first live session **Mon 2026-07-28**. Watch: (a) zero entries stamped
  before 10:00 ET, (b) entry count/day drops ~19% (7.5 → ~6), (c) the stop-out bucket's average loss
  improves toward the −$15 rest-of-day figure. Do **not** judge on one session — the gate's edge is ~$1.3
  per trade and needs ≥2 weeks to separate from noise.
- **PARTIAL REVISION (2026-07-25, from the bot/replay.py backtest):** the "+$407" above is a **first-order
  overestimate**. A full-strategy replay that *does* model capital contention puts the gate at **+$142**
  over 30 days / 10 symbols. Mechanism: blocking ~25 opening entries reduced the book by only **9** trades —
  16 replacement trades opened later in the day on the freed capital, and they were mediocre too. The gate
  is confirmed and stays (win rate 39.8% → 46.8% in replay); it is simply worth about a third of the naive
  trade-removal estimate. Lesson: trade-removal counterfactuals overstate any entry filter on a
  capital-constrained book.

---

## IMP-018 — 2026-07-25

- **Problem:** IMP-017 stopped the opening-range bleed but the bot was **still net negative** (30-day replay,
  10 symbols: 79 trades, 37W/42L, **−$159.25**, PF 0.83). Root arithmetic: **avg win $21.17 vs avg loss
  $22.44 → payoff 0.94.** At a 46.8% win rate breakeven needs payoff **1.14**; at payoff 0.94 it needs a
  **51.5%** win rate. The bot was short on *both* sides simultaneously — it loses by arithmetic, not by bad
  luck.
- **Root cause — the trailing stop was INERT, so the bot had no exit strategy, only a stop and a clock.**
  The ratchet sets the stop to `price*(1−TRAIL_PERCENT)`, so it only clears breakeven once price has run a
  full trail-width above entry. `TRAIL_PERCENT=0.02` **equalled** `STOP_LOSS=0.02`, so a winner had to run
  >2% before the trail locked a single cent — but the median live winner was **+0.75%**. Consequences,
  measured: only **2 of 219** live trades (3 of 79 in replay) ever exited on the trailing path; **0 of 219**
  ever hit the 10% target; **161 of 219 (74%)** exited on the EOD-flatten clock with a median hold of 4.8h.
  The 2% stop was the only functioning exit, and it only ever fires against you — hence a hard floor at
  exactly −1R (0/79 worse than −1R) while only **8.9%** of trades ever reached +1R. Symmetric ±0.55R noise
  with negative drift. The replay exit table is the proof: **stop fired → 12% win, −$559; stop did not fire
  → 63% win, +$472.**
- **Change:** `TRAIL_PERCENT` 0.02 → **0.0125** (`.env` + the `bot/config.py` default, so a fresh deploy
  inherits the fix). Plus a **generalizable guard** so this class of bug cannot silently return:
  `Config.trail_is_inert` (True when `trail_percent >= stop_loss`) and a startup **WARNING** in `bot/main.py`
  spelling out that the trail can never lock profit in that configuration. The startup banner now also
  prints the live exit triple (`Exits: stop −2.00%, target +10.00%, trailing stop 1.25% (active, IMP-018)`)
  so a review can confirm the ratchet is armed from the log alone. **No entry logic touched, no sizing
  change, no risk widened** — this only makes an existing exit function.
- **Why 1.25% and not the argmax:** combined 30-day replay over **20 symbols** (two disjoint 10-symbol sets)
  is a broad plateau — 0.75% +$49, 0.90% +$158, 1.00% +$177, **1.10% +$220**, **1.25% +$194**, 1.50% +$61,
  1.75% −$11, 2.00% −$108. 1.10% is the argmax and 1.00% the set-A peak, but **1.25% is the only candidate
  that beats the old 2% in BOTH halves of the window** (1.00% loses H1: +$252 vs +$264). Chosen mid-plateau
  on the both-halves criterion rather than on the sample's noise peak — same discipline as IMP-017's 10:00.
- **Validation:** full suite **278 passed** (was 275; +3 new, 8 updated). TDD — the new config tests were
  written first and confirmed failing (`AttributeError: 'Config' object has no attribute 'trail_is_inert'`).
  New: `test_trail_default_is_tighter_than_the_stop`, `_is_inert_when_it_matches_the_stop`,
  `_is_inert_when_wider_than_the_stop`. The 8 updated tests in `test_risk.py`/`test_strategy.py` had the old
  default's arithmetic hard-coded (`110*(1−0.02)=107.8` → `110*(1−0.0125)=108.62`) — they were asserting the
  *value*, not the *behaviour*, so updating them is correct, not a weakening.
- **Expected impact** (30-day replay, 10 symbols, gate ON, vs the IMP-017 baseline):

  | | before (trail 2%) | after (trail 1.25%) |
  |---|---|---|
  | net | −$159.25 | **+$56.88** |
  | W / L | 37 / 42 (46.8%) | 33 / 49 (40.2%) |
  | profit factor | 0.831 | **1.077** |
  | **payoff ratio** | **0.94** | **1.60** |
  | avg win / avg loss | +$21.17 / −$22.44 | +$24.00 / **−$15.01** |
  | biggest loss | −$52.65 | −$35.10 |
  | max drawdown | $372.84 (4.03%) | **$195.22 (2.11%)** |

  Note the win rate **falls** to 40.2% and it is profitable anyway — that is the point. The fix is the
  payoff ratio, not the hit rate: average loss drops a third while average win rises. Combined 20-symbol
  net is **+$194**.
- **Caveats (stated plainly):** ① **absolute profitability is outlier-dependent** — the +$194 combined
  becomes −$41 excluding the 3 best trades. What survives every removal is the *relative* gain over the 2%
  trail (~+$300 under both ex-3-best and ex-5-best). So this is "materially better", not "reliably
  profitable". ② The replay fills stops **exactly at the stop price with no slippage or gap modelling**, so
  the real loss side is slightly worse than shown (live had trades beyond −2%; the sim has none). ③ Only
  10/19 symbols are net-positive even after the fix. **The strategy still has no strong edge — this fixes
  the arithmetic that guaranteed a loss, it does not manufacture alpha.**
- **Deploy:** restarted and **deploy-gap verified** (`ActiveEnterTimestamp` 04:40:12 UTC > newest source
  mtime 04:39:04) — the running process logs `trailing stop 1.25% (active, IMP-018)`, warmup primed 21/21,
  equity $8,927.24, book flat, zero errors.
- **Commit:** _(recorded in the follow-up commit)_
- **Observed effect:** ⏳ pending — first live session **Mon 2026-07-28**. Watch: (a) the `trailing stop`
  exit reason should appear **regularly** now (it was 2 of 219 all-time — if it is still ~0 after a week the
  ratchet is not firing and something else is wrong), (b) average loss should compress toward ~−$15,
  (c) win rate should **drop** into the low 40s — that is expected and not a regression. Judge on payoff
  ratio and PF, **not** on win rate. Needs ≥2 weeks to separate from noise.
- **Still open (unchanged by this):** the 10% `TAKE_PROFIT` remains never-hit (0/219 live, 0/79 replay), but
  the replay shows it is **nearly irrelevant** once the trail works — TP 3% or 4% moves the result by ~$10,
  and TP+trail together add $0.12 over trail alone. Backlog #1 is therefore **downgraded**, not resolved.
  Also still open: flat non-ATR stop, and the inverted confidence→size ramp above conf 80.

---
