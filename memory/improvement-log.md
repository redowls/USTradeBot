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
- **Observed effect (weekly 07-31) — ✅ FIRST GENUINE TRIPS OBSERVED, mechanism works; VALUE still unproven.**
  The predicted setup arrived and the latch fired **twice**, both on the consecutive-losses arm, never the
  −2.5% arm: **07-27 16:39 UTC** (gap-up-fade tape, day −$78.20) and **07-30 14:55 UTC** (day **+$37.37**).
  Mechanically flawless — it latched, halted only NEW entries, kept managing and flattening open positions,
  reset next open; no misfire, no interaction with the EOD flatten.
  **But the P&L case is NOT yet made, and one trip looks actively costly.** On **07-27** the trip came at
  16:39, *after* all 8 entries were already open (last entry 15:21) — it blocked nothing and saved **$0**. On
  **07-30** it tripped at 14:55, only ~30 min after the 6-trade entry cluster, then **halted new entries for
  the remaining ~5 hours of a session that closed GREEN (+$37.37)** — both big winners (MU +$40.29, INTC
  +$33.90) were already open, so the halt could only have removed upside, not downside. Net across the two
  trips: **~$0 saved, unquantified opportunity cost.** ⚠️ **Open concern:** the 3-consecutive-losses arm may
  be **too fast for this bot's entry shape** — entries arrive in one tight post-blackout cluster, so three
  stop-outs can resolve early on a day that later recovers, latching the bot flat through the recovery.
  Do **not** retune it yet (n=2 trips). **Instrument first:** log each entry candidate suppressed while
  latched plus its would-be outcome, so the next review can *price* the arm instead of guessing.

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
- **Commit:** 6a015a8
- **Observed effect:** ⏳ pending — first live session **Mon 2026-07-28**. Watch: (a) the `trailing stop`
  exit reason should appear **regularly** now (it was 2 of 219 all-time — if it is still ~0 after a week the
  ratchet is not firing and something else is wrong), (b) average loss should compress toward ~−$15,
  (c) win rate should **drop** into the low 40s — that is expected and not a regression. Judge on payoff
  ratio and PF, **not** on win rate. Needs ≥2 weeks to separate from noise.
- **Observed effect (weekly 07-31) — ✅ WEEK 1 OF 2: STRONGLY CONFIRMED, and it is the reason the week is green.**
  This is the single most important result of the week. (a) **The ratchet fires constantly** — 277 `trailing
  stop` log lines over the week (vs **2 trail exits in 219 trades all-time** pre-change), e.g. GOOG walked
  351.67 → 353.05 in eight steps on 07-31. The mechanism is unambiguously live. (b) **Average loss compressed
  past target: −$10.55 this week vs the −$22.44 pre-change baseline** (target was ~−$15) — better than the
  replay predicted. (c) Cohort comparison on live DB, entries **≥07-28 (post-change) vs 06-28…07-25 (pre)**:

  | | pre-IMP-018 (n=135) | post-IMP-018 (n=14) |
  |---|---|---|
  | net | −$459.04 | **+$101.13** |
  | profit factor | 0.69 | **2.53** |
  | avg win / avg loss | +$18.68 / −$18.58 | +$23.86 / **−$9.42** |
  | **payoff ratio** | **1.01** | **2.53** |

  The payoff ratio — the exact quantity IMP-018 targeted — went 1.01 → 2.53, and it is the *loss* side doing
  the work, precisely as designed. Concrete live catches: AAPL 07-27 held to **−0.31%** (−$7.21) where the flat
  2% stop would have given ~−$47; NFLX 07-27 **locked green at +$3.62** on a 1/8 day; on 07-31 the trail let
  GOOG (+$45.11) and BABA (+$23.52) run into the EOD flatten instead of stopping them out early.
  ⚠️ **Caveats, stated plainly:** n=14 post-change is **small**; win rate did *not* fall as predicted (it rose
  to 50%), which means part of the gain is favourable tape, not just the fix; and **IMP-020 landed 07-30 inside
  this observation window**, so the last two sessions are mildly confounded. **Keep TRAIL_PERCENT at 0.0125 and
  do not touch the exit structure next week** — this needs its second clean week to be called validated.
- **Still open (unchanged by this):** the 10% `TAKE_PROFIT` remains never-hit (0/219 live, 0/79 replay), but
  the replay shows it is **nearly irrelevant** once the trail works — TP 3% or 4% moves the result by ~$10,
  and TP+trail together add $0.12 over trail alone. Backlog #1 is therefore **downgraded**, not resolved.
  Also still open: flat non-ATR stop, and the inverted confidence→size ramp above conf 80.

---

## IMP-019 — 2026-07-28

- **Problem:** 0 trades all day. The 06:04:21 UTC cold restart hit a **transient** SQL Server login timeout
  (`pyodbc HYT00 Login timeout expired`) at the one-shot `open_store()` init. Because that single connect
  raised, `open_store()` returned `None` → **persistence disabled** AND (since `store is None`) `bot.main`
  never called `load_watchlist()`, so it **fell back to the `WATCHLIST` env default `NFLX, BIRD, WPM`** — a
  3-symbol stub, 2 of them parked — instead of the **21 enabled** `dbo.watchlist` names. The bot ran the whole
  session on that stub (journal: *"Watchlist (WATCHLIST env): NFLX, BIRD, WPM"*, *"warmup primed 3/3"*),
  recording nothing. The DB was fine by report time (same connect succeeds in 0.10s, 21 enabled rows).
- **Root cause:** the startup DB init had **no retry** — a single cold-start/network blip disabled the whole
  DB side-channel *and* collapsed the critical-path watchlist for the entire session, with only one unseen
  journald ERROR as a trace. Graceful degradation worked (bot didn't crash, book stayed flat) but was far
  too brittle and too silent.
- **Change:** `bot/persistence.py::open_store` now **retries `ensure_schema()` with a bounded backoff**
  (`_SCHEMA_INIT_ATTEMPTS=3`, `_SCHEMA_INIT_RETRY_DELAY_SEC=5.0`) — it drops the failed connection and
  reconnects between tries, logs a WARNING per retry and (only) after exhausting all attempts logs the
  fall-back, then returns `None` exactly as before. Added `conn_factory`/`sleep` injection params for testing.
  **No trading logic, no sizing, no risk limit touched** — this only makes the existing side-channel survive a
  transient outage so the DB watchlist is used.
- **Validation:** full suite **281 passed** (was 278; +3 new). New regression tests anchored to today's
  scenario: `test_open_store_retries_transient_init_failure_then_succeeds` (fails 2×, succeeds on the 3rd →
  store live, backed off twice), `_returns_none_after_exhausting_retries` (bounded at 3 tries, still degrades),
  `_succeeds_first_try_without_retrying` (no backoff on the happy path). Preflight all-PASS (DB connects,
  schema ensured); post-restart journal verified on the live 21-symbol `dbo.watchlist`.
- **Expected impact:** a transient cold-start DB timeout no longer silently benches the bot on a 3-symbol
  parked stub for a session — it retries ~10s of extra runway and comes up on the full 21-name watchlist with
  persistence on. No effect on P&L mechanics; this is an availability/observability fix.
- **Commit:** _pending_
- **Observed effect:** ⏳ pending — watch the next few cold restarts: startup should log *"Watchlist
  (dbo.watchlist)"* + *"warmup primed 21/21"*; if a retry ever fires it logs *"database init attempt k/3
  failed — retrying in 5s"* then *"database initialized on attempt k/3"*. Backlog (NOT shipped): a Telegram
  page when the bot falls back to the env watchlist / persistence-off; and re-seed the `WATCHLIST` env default
  with core liquid names (2 of 3 current defaults are parked).
- **Observed effect (weekly 07-31) — ✅ VALIDATED LIVE, and it fired in anger within 3 days.** On the
  **07-31 06:10 UTC** cold restart the exact failure mode recurred and the retry **saved the session**:
  journald shows `database init attempt 1/3 failed — retrying in 5s`, then `attempt 2/3 failed — retrying in
  5s`, then success — after which the bot subscribed to the **full 18-symbol `dbo.watchlist`**, not the
  3-name `NFLX, BIRD, WPM` env stub. Under the old code that restart would have been a **second consecutive
  zero-trade session**; instead Friday traded 4 names for **+$60.86**, the week's best day. Direct, measurable
  save. Backlog items (Telegram page on env-watchlist fallback; re-seed the `WATCHLIST` default with liquid
  names) remain **open and are now better-evidenced** — the retry buys ~10s of runway, it does not cover a
  genuine multi-minute DB outage, and that degradation is still silent.

---

## IMP-020 — 2026-07-30

- **Problem:** Second **entry-quality** change (extends IMP-011's crossover floor). On a **green day**
  (6 trades, 2W/4L, **+$37.37**, broker-reconciled exact), the two winners were the day's two highest crossover
  sub-scores (MU 0.771 → +$40.29, INTC 1.00 → +$33.90) while **TSLA entered at crossover 0.206 — barely above
  the current 0.20 floor — and lost −$8.07.** That one trade is the tell for a large-sample leak: across **145
  post-IMP-011 trades (entry ≥ 2026-06-27, no pre-floor contamination)**, the **0.20–0.25 crossover band is the
  single worst cohort — 40 trades, −$165.93, avg −$4.15, 40% win**, sitting immediately above the floor.
  Everything below 0.30 is net-negative; 0.30–0.40 is the first band to turn positive (+$3.81).
- **Root cause:** IMP-011 set `MIN_CROSSOVER=0.20` on the first week's data (07-03 weekly said "keep at 0.20").
  With 3× more evidence the dead zone has proven to extend past 0.20 — a fresh cross with crossover 0.20–0.25 is
  still a narrow, non-accelerating trigger that clears the weighted total (60) on trend/rsi/volume weight and
  then chops out. The floor was set one notch too low.
- **Change:** `bot/config.py` — `min_crossover` default **0.20 → 0.25** (env `MIN_CROSSOVER` still overrides;
  `validate()` unchanged, still `[0,1]`). **Single-line tunable change.** No threshold, no weights, no sizing,
  no risk limit, no stop/target touched — a **stricter entry filter only** (fewer, higher-quality entries,
  never more exposure). Same proven family/mechanism as IMP-011; nothing new in the code path.
- **Validation:** full suite **283 passed** (was 281; +2 net new tests, 1 assertion re-anchored). TDD — new
  regressions in `tests/test_signals.py` built on **today's TSLA scenario**: `_midweak_xo_trigger` (a confident
  candidate whose crossover lands in 0.20–0.25, total ≥ 60), `test_midweak_crossover_lands_in_the_0_20_to_0_25_band`,
  and `test_imp020_floor_blocks_the_0_20_to_0_25_band_that_0_20_admitted` (the 0.20 floor ADMITS it — as it did
  TSLA today — while the new 0.25 floor turns it away with the crossover reason). `test_config.py::test_min_crossover_default_and_override`
  updated to assert the 0.25 default. Preflight not required (config value only, no connectivity/schema change).
- **Expected impact** (30-day 18-symbol replay, gate ON, vs the live 0.20 baseline):

  | | before (floor 0.20) | after (floor 0.25) |
  |---|---|---|
  | net | −$287.84 | **−$119.39** |
  | trades | 105 | 75 |
  | win % | 35.2 | 36.0 |
  | profit factor | 0.70 | **0.84** |
  | avg / trade | −$2.74 | **−$1.59** |

  Removing the ~30 worst-cross entries lifts net **+$168** and PF 0.70 → 0.84 with win% ~flat — the gain is
  cleaner *quality*, not a hit-rate story. Trade count stays healthy (75, no zero-trade risk). DB attribution
  (−$165.93 over the 0.20–0.25 band) and the independent engine replay (+$168) agree to within a few dollars.
- **Caveats (stated plainly):** ① the book is **still net-negative** after the fix (−$119 replay) — this
  removes the worst cohort, it does **not** manufacture edge; the strategy's lack of a strong edge is unchanged.
  ② Trade-removal/replay both slightly **overstate** the gain on a capital-constrained book (an entry skipped
  frees capital for the next, so the counterfactual isn't a clean subtraction — same caveat noted in IMP-017/018).
  ③ Crossover is **non-monotonic above the floor** (0.40–0.55 and 0.55–1.0 bands are also negative) — 0.25 cuts
  the clearly-worst *adjacent* band; it does not claim higher-is-better. A further raise to 0.30 was rejected: the
  0.25–0.30 band is near-scratch (−$37/20 tr, avg −$1.87) and removing it risks the over-filtering IMP-011's
  weekly explicitly warned about.
- **Commit:** _pending_
- **Observed effect:** ⏳ pending — first live session **Fri 2026-07-31**. Watch: (a) the `crossover X.XX < 0.25`
  skip logs should now fire on the 0.20–0.25 cohort that used to enter, (b) entry count should dip modestly
  (not collapse — if a session goes to zero trades on a normal tape, the floor is too high), (c) avg loss should
  compress further. Needs ≥1 week to separate from noise. **Still open (unchanged):** inverted confidence→outcome
  above ~80 (MSFT 81.95 lost again today — needs its own analysis, not folded here); flat non-ATR stop.
- **Observed effect (weekly 07-31) — ⏳ ONE live session only; floor is binding correctly, verdict PENDING.**
  Too early to judge, and I am explicitly declining to claim a win off one day. What the single session
  (07-31) shows: (a) **the floor binds and did not over-filter** — the minimum crossover of all 4 entries was
  **0.2701**, i.e. nothing in the old 0.20–0.25 dead band got through, and the day still produced a healthy
  4 entries (**no zero-trade collapse**, the stated failure mode); (b) the day was **3W/1L for +$60.86**, the
  week's best. (c) Week-level context that *supports* the thesis without proving it: the **<0.25 band was
  again the week's worst cohort — 7 trades, −$60.45, 1 win**, and every one of those was a **pre-IMP-020**
  entry (07-27/07-29). The band the change removes kept losing right up until it was removed.
  ⚠️ **Do not over-read this.** n=4 post-change; Friday's result is far more plausibly IMP-018's trail plus a
  constructive tape than a crossover-floor effect. **Needs ≥1 more full week.** Keep `MIN_CROSSOVER=0.25`;
  do **not** raise it toward 0.30 (the 0.25–0.30 band was **+$26.41 on 3 trades** this week — the first live
  hint that the rejected further-raise would have been actively wrong).

---

## REJECTED — 2026-07-31 (daily) — breakeven-gated trailing stop

**Status: built, A/B-tested, REFUTED, reverted. NOT SHIPPED. `IMP-021` remains unassigned.**
Recorded so no future run burns another evening re-deriving it.

- **Hypothesis (looked very strong):** `RiskManager.update_trailing_stop` seeds the ratchet from the
  bracket's *original* stop (`current = self._trail_stops.get(key, entry.stop_price)`) and then moves it to
  `close × (1 − trail_percent)` on the **first managed candle**. Because IMP-018 set trail 1.25% < stop 2%,
  that first move *always* tightens the stop, so **every position's stop silently goes from −2% to −1.25%
  the instant it opens, before the trade has earned anything.** IMP-018 shipped as "let winners run"; what it
  also did, unnoticed, was narrow the stop on every trade. Live evidence since IMP-018 fit perfectly:
  **11 of 11 losing broker-side exits landed inside −1.31%** (TSM −0.05%, BABA −0.18%, AAPL −0.31%,
  TSLA −0.53%, AMD −0.78% on 07-31, JPM −1.30%…), **none near the designed −2%**; exit buckets split
  **EOD flatten +$63.12 / 7 tr** vs **stop-leg −$40.19 / 15 tr**.
- **Change built:** `bot/config.py` — new `trail_locks_profit_only: bool` (env `TRAIL_LOCKS_PROFIT_ONLY`,
  default True); `bot/risk.py` — after the `new_stop <= current` check, `if cfg.trail_locks_profit_only and
  new_stop < entry.entry_price: return TrailResult.HELD`. I.e. the ratchet may only move the stop to a price
  **at or above the entry** — the trail locks breakeven-or-better and nothing else, and below that the
  *designed* `stop_loss` governs (which is what sizing already assumes). **Zero free parameters** — the gate
  is the entry price, not a fitted constant. Never widens a stop beyond the configured `stop_loss`.
- **A/B validation (30-day replay, 07-01→07-31, all 20 enabled symbols, identical seed/config otherwise):**

  | | gate OFF (live behavior) | gate ON (proposed) |
  |---|---|---|
  | trades | 84 | 84 |
  | net | **−$131.06** | −$264.58 |
  | win % | 36.9 | **48.8** |
  | profit factor | **0.84** | 0.74 |
  | avg / trade | **−$1.56** | −$3.15 |
  | stop-leg exits | 52 tr, −$499.66 | 27 tr, −$406.11 |
  | true EOD flattens | 32 tr, +$368.60 | 57 tr, +$141.54 |

- **Verdict: REFUTED, decisively — the proposal would have cost ~$134 over 30 days.** Reverted with
  `git checkout`; tree returned to HEAD, full suite **283 passed**, nothing deployed.
- **Why it failed — the durable lesson (this is the valuable part):** **this bot's losers do not recover.**
  Gating the trail lifts win rate **+11.9 points** (36.9 → 48.8) exactly as predicted — those cut-early
  trades really do end green — but the trades that *don't* recover then run the full 2% instead of 1.25%,
  and the extra loss on that tail outweighs everything the rescued winners bring back. Note the shape:
  gate ON converts 25 stop-leg exits into EOD flattens, yet the EOD bucket's total *falls* from +$368.60 to
  +$141.54 — the converted trades arrive at the close as losers.
- **Consequences for future work:**
  1. **Do not re-propose "let the trade breathe", breakeven gates, +0.5R/+1R trail activation, or any wider
     effective stop.** The direction is settled on 84 trades: for this strategy, **tighter is better**.
  2. IMP-018's tight trail is best understood **not as a trail but as a tight stop that happens to ratchet.**
     Its win is real but its stated mechanism ("winners run") is only half the story.
  3. The open todo item "flat non-ATR stop" should be re-framed: any future stop work goes **tighter or
     adaptive-tighter**, never wider. Low priority — IMP-018 already swept trail 0.9–2.0% (broad plateau).
  4. **Harness caveat:** `bot.replay`'s default `--symbols` resolved to only **3** symbols in a bare CLI
     process (config-watchlist fallback, not the DB's 20). **Always pass `--symbols` explicitly.** Also
     unexplained: IMP-018's 30-day replay scored **+$194** at trail 1.25%; the same window shifted +6 days
     with the current watchlist scores **−$131**. Verify harness stability before the next sizing/stop call.
- **Why no other change shipped tonight:** IMP-020 (07-30) has only **2 live sessions** and the weekly
  review explicitly deferred its verdict for a full week; the next-best candidate (a crossover *ceiling*
  for the inverted 80+ confidence band) is in the **same entry-filter family** and would confound that
  evaluation. Today was 3W/1L +$60.86 on a +2.8% Nasdaq — no failure demanding a fix. Shipping a second
  change tonight would be thrash, so the day's deliverable is the refutation above.

---

## IMP-021 — 2026-08-03 (daily) — two-stage trailing stop: tighten to 1.0% once +1.0% in profit

**Status: SHIPPED & LIVE.**

- **Problem (measured, not guessed):** the flat 1.25% trail is arithmetically incapable of keeping the
  winners this strategy actually produces. I pulled 1-min bars for all 25 trades since IMP-018 went live
  (07-25 → 08-03) and computed max-favourable-excursion capture:

  | MFE bucket | n | avg MFE | avg realized | capture | net |
  |---|---|---|---|---|---|
  | < 0.5% | 4 | 0.23% | −0.75% | — | −$50.71 |
  | 0.5–1.0% | 8 | 0.63% | −0.60% | −97% | −$77.01 |
  | **1.0–2.0%** | **9** | **1.42%** | **+0.28%** | **17%** | +$53.31 |
  | > 2.0% | 3 | 2.96% | +1.95% | 69% | +$119.30 |

  The modal winner peaks at 1.0–2.0%, so with a 1.25% give-back the *ceiling* on capture is
  (1.42−1.25)/1.42 = **12%**. Today AMD and MU each peaked **+1.69%** and banked **+0.45% / +0.38%**.
  Seven trades since IMP-018 ran ≥1.0% and exited under +0.5%. This is a spec error, not an execution bug.
- **Change:** `bot/config.py` — two new fields `trail_tighten_after` (env `TRAIL_TIGHTEN_AFTER`, default
  **0.010**) and `trail_percent_tight` (env `TRAIL_PERCENT_TIGHT`, default **0.010**); `bot/risk.py` —
  `update_trailing_stop` selects the width per candle: once `close >= entry_price * (1 + tighten_after)`
  the trade has proven itself and the ratchet uses the narrower width, otherwise it uses the unchanged
  1.25%. **Below the threshold behaviour is byte-identical to before** — the region the 07-31 A/B proved
  must not be loosened is untouched. The `new_stop <= current` ratchet guard is unchanged, so stops still
  never move down. `validate()` gained a hard invariant: **`TRAIL_PERCENT_TIGHT` must be <= `TRAIL_PERCENT`**
  — stage two may only ever tighten, so this can never become a stealth stop-widening. Shipped as config
  defaults (the IMP-020 pattern); `.env` untouched. `TRAIL_TIGHTEN_AFTER=0` restores the old flat trail.
- **A/B validation — replay, 20 enabled symbols, every window tested:**

  | window | flat 1.25% (live) | **two-stage (shipped)** |
  |---|---|---|
  | 15d | −$23.01 · PF 0.94 · 44.2% | **+$25.72 · PF 1.07 · 48.8%** |
  | 20d | −$92.61 · PF 0.81 · 39.6% | **−$40.76 · PF 0.91 · 43.4%** |
  | 30d | −$153.28 · PF 0.80 · 36.6% | **−$99.88 · PF 0.87 · 39.8%** |
  | 45d | +$82.29 · PF 1.07 · 41.9% | **+$129.57 · PF 1.12 · 45.6%** |
  | 60d | +$154.31 · PF 1.10 · 42.1% | **+$197.66 · PF 1.13 · 45.3%** |

  **Better in all five windows, on net AND profit factor AND win rate simultaneously** — this change does
  not trade hit-rate for payoff, which is unusual here and is the main reason I trust it.
- **Parameter choice is mid-plateau, not argmax.** On the 60-day window the threshold axis
  (0.008 / 0.010 / 0.012) and the width axis (0.009 / 0.010 / 0.011) *all* beat baseline (+$145 to +$198).
  The only failure mode is **over**-tightening: width 0.008 scores +$54.83 and 0.006 scores +$51.42, i.e.
  the cliff is on the tight side, so 0.010 is deliberately chosen away from that edge. 1.0% after +1.0% is
  also the interpretable point — at exactly +1.0% the new stop lands on breakeven, so the trade locks
  breakeven the moment it proves itself and then trails 1% behind the peak.
- **Tests:** 6 new (`tests/test_risk.py`: wide width below threshold, tightening above it, shipped-defaults
  pin, `TRAIL_TIGHTEN_AFTER=0` disable path, ratchet-never-lowers across the width switch, and an
  **AMD 2026-08-03 regression** built from the real trade — entry $482.498, peak $490.85 — asserting the
  stop rides at $485.94 rather than the $484.68 it actually exited at; `tests/test_config.py`: the
  may-only-tighten invariant, the accept case, and the fraction bound). Nine legacy trail assertions in
  `test_risk.py` / `test_strategy.py` were updated: they exercise the ratchet at +10%/+15% profit, which is
  past the new threshold, so their expected stop moves 108.62 → 108.90 (the properties they cover —
  ratcheting, never-lowering, Alpaca id rotation, `STOP_GONE` — are unchanged).
- **Validation:** full suite **292 passed**. `bot.preflight` **OK with 1 warning** (market closed) — Alpaca
  ACTIVE, SQL Server connected, Telegram delivered. Replay re-run with **no env overrides** reproduces the
  shipped numbers exactly (30d −$99.88, 45d +$129.57, 60d +$197.66).
- **Caveats (stated plainly):** ① The book is **still net-negative on the 30-day window** (−$99.88). This
  banks more of each winner; it does **not** manufacture edge, and the strategy's lack of a demonstrated
  edge is unchanged. ② Replay fills bracket legs at the exact stop price with **no slippage modelling**, so
  a tighter trail is flattered slightly — live give-back will be marginally worse than modelled. ③ The
  tighter width means **more order-replace churn** at the broker (already ~13 replaces per position today);
  watch for 422s, though the IMP-012 `STOP_GONE` path and the id-rotation fix both cover that ground.
- **Commit:** _see below_
- **Observed effect:** ⏳ pending — first live session **Tue 2026-08-04**. Watch: (a) `trailing stop`
  log lines should show the width narrowing once a position is +1% (stop ≈ close × 0.99 rather than
  × 0.9875); (b) the MFE-capture rerun should lift the 1.0–2.0% bucket well above 17%; (c) **win rate should
  RISE, not fall** — if it falls, the replay's no-slippage assumption is flattering the change and it should
  be reconsidered. Needs ≥1 week to separate from noise.
- **Observed effect (weekly 08-07) — ⏳ MECHANISM CONFIRMED, EFFECT STILL UNMEASURED. Verdict deferred: the
  observation window was destroyed, not completed.** Criterion (a) is met **exactly once**: INTC on 08-05
  settled its final stop at **101.50**, arithmetically consistent only with the narrow 1.0% width
  (101.50/0.99 = 102.53 peak, +1.83%, past the +1% trigger; the old flat 1.25% would have placed it at
  101.25) — worth **≈ +$0.25/share ≈ +$5.25** on that trade, with **17 stop replaces and zero 422s**, so the
  id-rotation fix holds under the extra churn this change causes. That is the entire body of direct
  evidence: **n=1 qualifying trade in five sessions.** Criterion (c) is superficially satisfied — the week
  ran **76.9% win** vs 36.4% the prior week — but it is **not attributable**: 7 of the week's 10 wins landed
  on **08-04 alone**, the strongest trending tape in the 38-session sample (QQQ **+2.15%** open→close), and
  **5 of those 7 exited on the EOD flatten, never touching the trail at all.** Criterion (b) was not rerun —
  with 13 closed trades and only 5 trail exits all week, the MFE-capture table cannot be refreshed with any
  power. **Root cause of the non-measurement is IMP-022**, shipped two sessions later: the market gate took
  trade count to **zero on 08-06 and 08-07**, so this change's window contains three trading days, not five.
  **Do not re-tune the trail.** Two consecutive weeks of live trading are required before IMP-021 can be
  judged; until then any further change to the exit structure is being made blind.

### Rejected the same evening — flat `TRAIL_PERCENT` tightening (recorded so it is not re-derived)
Tightening the single flat width looks excellent on 30 days — 0.6% scores **+$24.58 / PF 1.06** vs 1.25%'s
**−$153.28 / PF 0.80**, and the entire 0.2–0.7% region is positive with a broad plateau. **It reverses on
longer windows**: 45d 1.25% wins (+$82.29 vs +$49.95), 60d 1.25% wins decisively (**+$154.31 vs +$51.42**).
The apparent edge is a **30-day-window artifact**, and it retrospectively explains the harness instability
flagged on 07-31 (IMP-018's +$194 vs the same window's −$131 — same phenomenon, not a harness bug).
**Two corrections to the record:** (1) `config.py`'s claim that the trail curve is a "broad plateau
0.90–2.00%" does **not** hold on current data — it is a steep monotonic gradient over 30 days and the
opposite ranking over 60. (2) **Methodology rule going forward: no replay-derived parameter ships on a
single window. Require ≥3 windows agreeing in sign.** IMP-021 was held to that bar; this rejected variant
would have failed it.

---

## IMP-022 — 2026-08-05 (daily) — market-regime gate: no new long unless QQQ's 5m ribbon is bullish

**Status: SHIPPED & LIVE.**

- **Problem (measured, not guessed).** The bot has **no view on the market**. The 5-min
  21/34/55 gate asks only whether *the individual name* is trending; nothing in the system
  asks what the tape that name has to swim in is doing. Bucketing all **38 live sessions
  (2026-06-08 → 08-05, 254 closed trades)** by QQQ's intraday open→close move:

  | QQQ intraday | sessions | trades | win rate | net | per session |
  |---|---|---|---|---|---|
  | **up >0.5%** | 12 | 104 | **54.8%** | **+$755.65** | +$62.97 |
  | up 0–0.5% | 4 | 32 | 62.5% | −$49.70 | −$12.42 |
  | **down** | 22 | 118 | **33.1%** | **−$728.75** | −$33.12 |

  The book earns +$756 on up-tape and hands back −$729 on down-tape for a net of ≈ −$23.
  **That is long beta, not alpha** — and it is the honest answer to "why does this thing
  not compound": for 22 of 38 sessions it was structurally on the wrong side and had no
  mechanism to notice.
- **Change.** `bot/config.py` — one new field `market_filter_symbol`
  (env `MARKET_FILTER_SYMBOL`, default **`QQQ`**), normalised to upper-case and validated
  as a plain ticker (a typo like `QQQ,SPY` now fails at startup rather than failing open
  for a whole session); `""` disables and restores pre-IMP-022 behaviour exactly.
  `bot/strategy.py` — new `_market_gate_open()` plus a veto in `on_short_candle`.
  `bot/main.py` — the gate is reported on the startup banner (the IMP-021 precedent, so a
  post-close review can confirm from journald alone that the deployed process really runs it).
- **Three design choices worth defending:**
  1. **No new parameter to overfit.** The gate reuses the *existing* `gate_open` rule
     (21 > 34 > 55 stacked and rising) applied to the index's own 5-min ribbon. There is no
     threshold, lookback or width to tune — the change has **zero free parameters**, which
     is the main structural reason it is unlikely to be a fit.
  2. **Zero new data.** QQQ is already an enabled watchlist symbol, so its 5-min ribbon is
     already built every session. No new subscription, no new fetch, no new failure mode.
  3. **Veto placed *after* scoring, not before.** The decision is fully computed and the
     skip logged (`no entry SYM: market gate closed (QQQ 5m ribbon not bullish) (conf=…)`),
     so the journal records exactly which qualifying entries the filter turned away and
     tomorrow's review can price what it cost or saved. Cheaper to gate earlier; not worth
     losing the counterfactual.
- **Fails OPEN by design.** If the filter symbol has no ready ribbon — parked from
  `dbo.watchlist`, or still warming — the bot trades exactly as before and logs a single
  latched `WARNING`. A watchlist edit must never be able to *silently halt* trading. The
  cost of this choice is that the filter can disappear quietly; the warning plus the
  startup banner are the mitigations, and the daily review now carries a standing
  "QQQ must stay enabled" note.
- **A/B validation — replay, 19 enabled symbols, every window tested:**

  | window | OFF (live today) | **QQQ gate (shipped)** |
  |---|---|---|
  | 15d | n=43 · +$70.02 · PF 1.22 · 48.8% | **n=24 · +$163.24 · PF 2.20 · 58.3%** |
  | 20d | n=53 · +$53.77 · PF 1.12 · 49.1% | **n=31 · +$173.18 · PF 1.82 · 58.1%** |
  | 30d | n=82 · **−$28.03** · PF 0.96 · 41.5% | **n=45 · +$222.86 · PF 1.69 · 55.6%** |
  | 45d | n=127 · +$146.14 · PF 1.13 · 46.5% | **n=68 · +$318.29 · PF 1.61 · 55.9%** |
  | 60d | n=169 · +$240.97 · PF 1.17 · 46.7% | **n=100 · +$353.97 · PF 1.45 · 53.0%** |

  **Better in all five windows on net AND profit factor AND win rate simultaneously**, and
  it flips the stubborn 30-day window — negative through IMP-018 and IMP-021 alike — from
  −$28.03 to **+$222.86**. Trade count roughly halves (169 → 100 on 60d) while net *rises*,
  so per-trade edge more than doubles. Clears the IMP-021 methodology bar (≥3 windows
  agreeing in sign) with five for five.
- **Robustness — it is not a QQQ artifact.** Re-run with **SPY** as the filter: 30d
  +$139.42 (PF 1.38), 45d +$349.33 (PF 1.62), 60d +$329.54 (PF 1.44) — beats baseline on
  3 of 4 windows, failing only 15d (−$17.56). The *market-regime* effect survives changing
  the proxy; QQQ is simply the better proxy for what is structurally a **Nasdaq book**
  (AAPL AMZN AVGO GOOG INTC MSFT MU NVDA TSM QQQ). That is an economic reason for the
  choice, not a fitted one.
- **Tests:** 10 new. `tests/test_strategy.py` — veto blocks a qualifying entry (nothing
  reaches the broker, state returns to WAITING, skip logged); the mirror case admits the
  same entry when the tape is bullish; fails-open with no index ribbon; the warning is
  latched to once; `MARKET_FILTER_SYMBOL=""` disables; and a **2026-08-05 regression built
  from the real session** — MU's second entry (16:40 UTC, conf 62.11, −$10.39) asserted
  vetoed against QQQ's actual 5-min ribbon on that bar, `(721.9659, 722.4467, 722.4473)`
  over `(721.9934, 722.4925, 722.4754)`, pulled from the IEX 5m bar. `tests/test_config.py`
  — default is QQQ, whitespace/case normalisation, empty disables, non-ticker rejected.
- **Validation:** full suite **302 passed**. `bot.preflight` **OK with 1 warning** (market
  closed) — Alpaca ACTIVE (equity $9,075.88), SQL Server connected, Telegram delivered.
  (`ruff` is not installed in the VPS venv — lint not run; it is a dev-only dependency.)
- **Caveats, stated plainly:**
  ① **On today's own trades this change would have LOST money.** QQQ's gate was open at
  MU #1 (the −$18.34 loser, kept) and shut at both INTC (+$16.53 winner, blocked) and MU #2
  (−$10.39 loser, blocked): today would have been **−$18.34 instead of −$12.20, i.e. $6.14
  worse.** The case for this change is 254 trades over 5 windows and 2 proxies — **not
  today.** Recorded loudly so no future run mistakes one bad day for refutation.
  ② The gate was open only **11 of 79 QQQ 5-min bars (14%)** today. On tapes like this it
  will cut trade count hard; a run of near-flat sessions is the expected texture, not a
  malfunction.
  ③ It **does not manufacture edge** — it declines to bet when the tape is against the
  strategy's only direction. The book is still long-only with no short side, and the
  underlying signal's edge is unchanged.
  ④ Replay models no slippage on stop fills; today's MU #1 slipped **$0.51/share** through
  its stop, so live results will run modestly behind the modelled ones.
- **Commit:** _see below_
- **Observed effect:** ⏳ pending — first live session **Thu 2026-08-06**. Watch:
  (a) the banner line `Market gate: QQQ 5m ribbon must be bullish to open a long (IMP-022)`;
  (b) `no entry … market gate closed` lines — count them and price the blocked entries
  against what they would have done; (c) **trade count should fall ~40%** while net per
  trade rises; (d) if a week passes with the gate blocking >80% of entries, the proxy is
  too strict for this watchlist and SPY should be reconsidered. Needs ≥1 week.
- **Observed effect (weekly 08-07) — ✅ VALIDATED, AND IT IS THE STRONGEST RESULT THIS BOT HAS EVER
  PRODUCED. Keep. Do not touch.** Two live sessions (08-06, 08-07) plus a **four-window replay A/B**
  through the IMP-023-corrected harness (20 enabled symbols resolved from `dbo.watchlist`, gate toggled
  via `MARKET_FILTER_SYMBOL`):

  | window | gate ON | gate OFF | Δ net |
  |---|---|---|---|
  | 2d (08-05→08-07) | 2 tr, **−$41.60**, 0% win, PF 0.00 | 9 tr, −$83.85, 22.2%, PF 0.22 | **+$42.25** |
  | 5d (08-02→08-07) | 15 tr, **+$113.94**, 53.3%, PF **2.05** | 23 tr, +$50.55, 43.5%, PF 1.26 | **+$63.39** |
  | 30d (07-08→08-07) | 49 tr, **+$241.91**, 53.1%, PF **1.64** | 90 tr, +$6.12, 42.2%, PF 1.01 | **+$235.79** |
  | 60d (06-08→08-07) | 109 tr, **+$494.08**, 53.2%, PF **1.54** | 187 tr, +$252.33, 46.0%, PF 1.15 | **+$241.75** |

  **The gate wins in all four windows on every metric simultaneously** — net, win rate, profit factor and
  average per trade — while cutting trade count **42–46%** (criterion (c) predicted ~40%: met). Win rate
  with the gate ON is remarkably stable at **53.1 / 53.2 / 53.3%** across the 5, 30 and 60-day windows,
  against 42–46% with it off. This clears the ≥3-window robustness bar set on 08-03 with room to spare,
  and it is the *only* change in this bot's history to do so.
  **Live corroboration:** 08-06 blocked 4 qualifying entries and the ON/OFF replay of that session priced
  the saving at **≈ +$47**; 08-07 blocked 4 more (NFLX 66.5, ABNB 74.1, ABNB 71.9, MSFT 78.0) into a second
  choppy, rotation-driven tape. Both blank days were correct.
  **Criterion (d) — the >80% tripwire — is formally hit and is being deliberately NOT actioned.** The gate
  blocked **8 of 8** fully-qualified entries (100%) across its two live sessions. But (i) that is two
  sessions, not the week the tripwire specifies; (ii) both counterfactuals are *negative*, i.e. the veto was
  right both times; and (iii) the same two sessions sit inside the 2-day A/B window where gate-ON loses
  **half** as much as gate-OFF. A 100% block rate during a two-day tech selloff is the filter working, not
  the proxy being too strict. **Do not switch the proxy to SPY on this evidence.** Re-read the tripwire
  after a full week that contains at least one up-tape session.
  **Cost, stated honestly:** a filter this binding produces zero-trade days, and zero-trade days generate no
  information about the signal, the exits or the sizing. IMP-021's window was collateral damage. That is a
  real price and it is why nothing further ships until the book is trading again.

---

## IMP-023 — 2026-08-06 (daily) — replay resolves its universe from `dbo.watchlist`, like the live bot

- **Problem — the measuring instrument was miscalibrated, and it lied tonight.**
  `bot/main.py` sources the watchlist from **`dbo.watchlist`** (19 enabled symbols) and only
  falls back to the `WATCHLIST` env var when the DB is unavailable. `bot/replay.py` had **no
  such fallback chain**: with no `--symbols` it went straight to `cfg.watchlist`, i.e. the
  **`NFLX,BIRD,WPM` bootstrap stub** — a three-name list, **two of which (BIRD, WPM) have been
  parked for weeks**. Every bare `python -m bot.replay` since the harness was built (25fa3f6,
  07-25) has therefore backtested a universe **the bot has never traded**.
- **How it was caught — it produced a false negative on the change under observation.**
  Pricing IMP-022's first live session, `--days 1` with no `--symbols` returned
  `symbols=3 … trades=3 net=+2.38` for a day the live bot took **zero** trades, and — the
  damning part — **gate ON and gate OFF returned byte-identical output**. Cause: the market
  filter symbol **QQQ was not in the stub**, so `_market_gate_open()` found no ribbon and
  **failed open in both arms**. The naive reading is *"IMP-022 changes nothing, revert it."*
  Re-run with the real 19 symbols, the same session prints **0 trades vs −$47.11 (PF 0.25,
  20% win)** — the filter saved ≈$47. **The tool would have argued for reverting a change that
  worked.** That is the whole justification for spending tonight's one change here.
- **The change (`bot/replay.py`).** New `resolve_symbols(cfg, explicit) -> (symbols, source)`
  mirroring `bot.main`'s precedence exactly:
  1. explicit `--symbols` wins (source `--symbols`);
  2. else enabled `dbo.watchlist` via `open_store(cfg).load_watchlist()` (source `dbo.watchlist`);
  3. else `WATCHLIST` env, now with a **`log.warning` naming the symbols and stating plainly
     that this is NOT what the live bot trades** (source `WATCHLIST env`).
  The store is opened lazily inside the function (so the harness still runs on the env fallback
  where the ODBC driver is absent, exactly as persistence is optional live) and **closed in a
  `finally`** — this is a short-lived CLI, not a daemon. The resolved source is **printed in the
  header line** (`symbols=19 (dbo.watchlist)`) so no future run can be misled without ignoring
  it in writing.
- **Scope — deliberately zero trading-behaviour change, and that is the point.** `bot/replay.py`
  is **offline-only**: verified by grep that nothing under `bot/` imports it, so it is not on
  the live path and the running service is byte-for-byte unaffected in behaviour. Chosen
  *because* tonight sits on **day 1 of IMP-022's ≥1-week observation window**, where the
  standing weekly focus is *"protect the measurement"*: an entry-side change tonight (the
  tempting 60–69 confidence leak) would have made both changes unmeasurable. Fixing the
  instrument is the one improvement that is both justified by today's evidence and **incapable
  of confounding** the experiment it serves.
- **Tests: 5 new** in `tests/test_replay.py`, written as a regression cohort around tonight's
  actual failure — DB watchlist beats the env stub (and the store is closed); **the market
  filter symbol is present in the default universe but absent from the stub** (the 08-06 bug in
  one assertion); explicit `--symbols` wins and is upper-cased/trimmed with order preserved;
  fallback to env when `open_store` returns `None`; fallback to env when the table is empty.
- **Validation:** full suite **307 passed** (302 → 307), no regressions. `bot.preflight` **OK
  with 1 warning** (market closed) — Alpaca ACTIVE $9,075.74, SQL Server connected, Telegram
  delivered. End-to-end: a bare `--days 1` now reports `symbols=19 (dbo.watchlist)` and
  **`no trades`, reproducing the live session exactly**, where before the fix it reported a
  fictitious 3 trades / +$2.38.
- **Caveats, stated plainly:**
  ① **This earns $0 by itself.** It is a correctness fix to an analysis tool; it does not touch
  the strategy and will never show up in the equity curve. Its value is entirely in the wrong
  decisions it prevents — starting with the one it prevented tonight.
  ② **Every replay number recorded before tonight that did not pass `--symbols` explicitly is
  suspect** and should be re-derived before being cited. IMP-022's own A/B tables state 19
  symbols and so appear sound; older bare-invocation figures do not.
  ③ Replay now touches the DB on startup, so a DB outage changes its default universe (loudly —
  it warns). Acceptable: the same is true of the live bot, which is the point of the change.
- **Commit:** `5cc500d` (pushed to `origin/main`).
- **Observed effect:** ⏳ n/a by construction (no behavioural change). The check is that every
  future replay header names `dbo.watchlist` — if one ever prints `WATCHLIST env`, the DB is
  down and that run's numbers must be discarded.
- **Observed effect (weekly 08-07) — ✅ VALIDATED, and it paid for itself inside 24 hours.** All eight
  replay runs behind tonight's IMP-022 verdict printed `symbols=20 (dbo.watchlist)`. Without this fix every
  one of them would have silently used the three-name `NFLX,BIRD,WPM` stub, which **contains no QQQ** — so
  the market gate would have failed *open in both arms* and all four windows would have returned identical
  ON/OFF results. **The conclusion would have been "IMP-022 is a no-op, revert it," and this review would
  have deleted the single most valuable change the bot has.** The highest-leverage work this week was not a
  strategy change at all; it was fixing the instrument. Rule confirmed: **calibrate the measuring device
  before trusting anything it says.**

---

## IMP-024 — 2026-08-07 (daily) — the replay harness sequences gate bars at their CLOSE, not their start

- **Problem — every backtest this bot has ever run was reading the future.**
  `run_replay` built its event stream by keying **both** timeframes at `candle.start`:
  ```python
  stream += [(c.start, 1, c) for c in long_bars...]   # 5m gate bar
  stream += [(c.start, 2, c) for c in short_bars...]  # 1m trigger bar
  ```
  with long sorted ahead of short at equal stamps. So the 5m gate bar spanning **14:45–14:50**
  was folded into the gate ribbon at **14:45**, and every 1m trigger bar from 14:45 to 14:49 was
  then evaluated against **five minutes of price action that had not happened yet**. Live cannot
  do this: `bot/candles.py` closes a candle only when a trade lands in a *later* bucket
  (`bucket > builder.start` → `_close`), so `on_long_candle` first sees that bar at **14:50**.
  The harness had a **full gate interval of lookahead on every single trigger bar**, and it
  contaminated **both** the per-symbol 5m gate ribbon consumed by `evaluate_entry` *and* the
  IMP-022 market filter — i.e. the entire multi-timeframe premise of the strategy.
- **How it was caught — the harness contradicted the live bot on today's session.**
  Live took **0 trades** today and logged four `market gate closed` rejects. Replaying the same
  session reported **2 trades / −$41.60**: an ABNB entry at **14:45** (conf 71.6) and an MSFT entry
  at **14:47** (conf 77.8). Those are **exactly the two entries live refused** at 14:46 (ABNB,
  conf 71.9) and 14:48 (MSFT, conf 78.0). Reconstructing QQQ's gate both ways proved it directly:

  | decision minute | replay gate (start-keyed) | live gate (close-keyed) |
  |---|---|---|
  | 14:13, 14:14 | False | False |
  | **14:45, 14:46, 14:47, 14:48** | **True** | **False** |

  Across today's 390 session minutes the two gates **disagreed on 60 (15.4%)**. The close-keyed
  reconstruction reproduces live exactly: all four live blocks land inside reconstructed *closed*
  windows.
- **The change (`bot/replay.py`).** Sequencing extracted into a testable
  `build_stream(symbols, short_bars, long_bars, start, end, long_interval_seconds)` returning
  `(effective_time, kind, candle)`, with named `LONG`/`SHORT` kinds. Gate bars are now keyed at
  **`c.start + long_interval`**; trigger bars stay at `c.start`. `LONG` still sorts ahead of `SHORT`
  at equal stamps because that is *also* live's order — the 5m closing at 14:50 is folded before the
  1m bar starting 14:50 is evaluated at 14:51. The **window test stays on `candle.start` for both
  timeframes**, so the *set* of bars replayed is unchanged and only their order moves; the warmup
  partition (`c.start < start`) is untouched, so there is no double-fold and no gap at the seam.
- **Scope — offline only, zero live behaviour change.** `bot/replay.py` is not imported by anything
  under `bot/` on the live path (re-verified). The running service is unaffected. This is the same
  class of change as IMP-023 and was chosen for the same reason: **the instrument must be right
  before anything it says can be acted on**, and tonight it was demonstrably wrong.
- **What it costs — every pre-existing backtest number is overstated. Corrected 60-day table
  (2026-06-08 → 2026-08-07, 20 symbols from `dbo.watchlist`):**

  | | trades | net | win% | PF |
  |---|---|---|---|---|
  | gate ON — **before** (as cited by the 08-07 weekly) | 109 | **+$494.08** | 53.2 | 1.54 |
  | gate ON — **after (honest)** | **90** | **+$456.87** | **54.4** | **1.62** |
  | gate OFF — before | 187 | +$252.33 | 46.0 | 1.15 |
  | gate OFF — **after (honest)** | **168** | **+$224.38** | **45.8** | **1.15** |

  Net was inflated by **$37.21 (7.5%)** and **17% of all trades were lookahead artifacts**.
- **The verdict that matters: IMP-022 SURVIVES, and reads slightly better.** Under honest semantics
  the gate still turns **+$224.38 / PF 1.15 / 45.8% win** into **+$456.87 / PF 1.62 / 54.4% win** on
  46% fewer trades — a **+$232.49** edge (was +$241.75). The weekly's headline conclusion stands; it
  was simply measured with a ruler that was 7.5% long. Today's own session says the same thing more
  sharply: gate OFF would have taken **3 trades for −$27.96** on a day the S&P closed at an all-time
  high, so **the gate saved ≈$28** while the live bot risked nothing.
- **Tests: 5 new** in `tests/test_replay.py`, anchored on tonight's actual failure — the 14:45 gate
  bar must land at 14:50 (the bug in one assertion); the invariant over a full 390-minute session
  (no trigger bar may ever see an unclosed gate bar); LONG-before-SHORT at the boundary; the window
  selects the same bar *set* as before; and multi-symbol streams stay in true chronological order so
  capital contention is real. **Verified as genuine regression tests**: reintroducing `c.start`
  fails 2 of them, and they pass on the fix.
- **Validation:** full suite **312 passed** (307 → 312), no regressions. End-to-end, `--days 1` now
  reports **`no trades`, reproducing the live session exactly**, where before the fix it invented
  2 trades and −$41.60.
- **Caveats, stated plainly:**
  ① **This earns $0 by itself** — like IMP-023 it is a correctness fix to an analysis tool and will
  never appear in the equity curve. Its value is the wrong decisions it prevents.
  ② **Every replay figure recorded before tonight is optimistic** by roughly the margin above and
  should be re-derived before being cited — including IMP-017's and IMP-018's original A/B tables.
  ③ 1m trigger bars retain the *self-consistent* convention that a signal fills at its own bar's
  close, which matches live (live evaluates the 14:45 bar at 14:46 and buys at that close). Only the
  cross-timeframe seam was wrong.
- **Commit:** `8951734` (pushed to `origin/main`).
- **Observed effect:** ⏳ n/a by construction. The check is that a `--days N` replay of a session the
  live bot traded now matches the live trade list; any future divergence is a real bug, not noise.

---

## IMP-025 — 2026-08-10 (daily) — measure max favourable/adverse excursion: `bot.report --mfe`

**Status: SHIPPED & LIVE. Instrumentation only — zero change to the trading path.**

- **Problem (procedural, and it has already cost a shipped change its validation).** Every
  exit-structure decision this bot has made turns on one number — **how far a trade runs in our favour
  versus what the trail gives back** — and that number is recorded **nowhere**. `dbo.trades` stores
  entry, exit and P&L but no high-water mark; journald has the trail ladder only for trades that
  trailed, and only back to 07-29. So the MFE table has been rebuilt **by hand, from bars, three
  reviews running** (08-06, 08-07, 08-10). The concrete cost: **IMP-021's own validation criterion (b)**
  — *"the MFE-capture rerun should lift the 1.0-2.0% bucket well above 17%"* — was recorded by the
  08-07 weekly as **"not rerun"**, so a shipped change sat unvalidated for a week purely because
  measuring it was manual labour. An analysis that is redone by hand every night is one that will
  eventually be skipped on the night it matters.
- **Change (4 files, no behavioural surface):**
  - **`bot/excursion.py` (new)** — the arithmetic, **pure and fully unit-tested**: `compute_excursion`
    (MFE/MAE/realized/capture from a holding window's bar highs+lows), `bucket_of` (the *same* 0.5/1.0/2.0
    edges IMP-021 used, so new tables are directly comparable with that entry's), `summarize`,
    `format_excursions`. The only I/O is `alpaca_bar_fetcher`, injected as a callable so tests run
    network-free — same pattern as `bot/warmup.py`. Bars come from **`cfg.alpaca_data_feed` (IEX)**, the
    feed the bot actually trades on: measuring excursion on a richer feed would overstate what was reachable.
  - **`bot/persistence.py`** — `ClosedTrade` + `TradeStore.closed_trades(days)`, read-only and wrapped
    exactly like `performance_summary` (DB error → log, reset, return `[]`).
  - **`bot/report.py`** — `--mfe` flag. **Opt-in** (it costs one bars call per trade) and prints to
    **stdout only**, so the Telegram digest stays the short headline it has always been.
    `excursion_report()` catches everything: a reporting extra must degrade, never break the report.
- **Design calls worth recording.** ① MFE is **clamped at zero** — a trade that never traded above entry
  has *no* favourable excursion, not a negative one, and the bucket edges assume MFE ≥ 0. ② `capture` is
  `None` rather than a huge number when MFE ≈ 0 (no dividing by ~0). ③ A trade with **no bars** is
  **skipped and counted**, not scored as flat — a missing window is not a quiet one. ④ Bucket-level
  capture is avg-realized / avg-MFE, matching IMP-021's table rather than a weighted variant.
- **Validation.** Full suite **343 passed** (312 baseline + **31 new**: 24 in `tests/test_excursion.py`,
  5 in `tests/test_report.py`, 2 in `tests/test_persistence.py`). `bot.preflight` **OK with 1 warning**
  (market closed) — Alpaca ACTIVE, SQL Server connected, Telegram delivered.
  **The regression tests are built from today's real session** (AVGO/ABNB/MU/BABA, measured highs and
  lows), pinning the finding that motivated the module: three of four trades peaked below the give-back,
  and MU's capture is −134%.
  **End-to-end check against an independent hand computation:** run live on today's trades it reproduces
  the by-hand figures **exactly** (MFE 0.66 / 2.45 / 0.60 / 0.59; capture −102% / 59% / −134% / 79%).
- **First result — it paid for itself on the first run.** 30-day table, 86 closed trades:

  | MFE band | n | avg MFE | avg exit | capture | net |
  |---|---|---|---|---|---|
  | **<0.5%** | **28** | **+0.20%** | **−1.18%** | **−599%** | **−$605.91** |
  | 0.5–1.0% | 27 | +0.73% | −0.43% | −60% | −$214.03 |
  | 1.0–2.0% | 15 | +1.45% | +0.50% | 34% | +$155.61 |
  | >2.0% | 16 | +2.43% | +1.43% | 59% | +$443.18 |

  ① **59 of 86 trades (69%) peaked below the 1.25% give-back** — structurally unable to finish green on
  the trail regardless of how the ratchet is tuned. ② **IMP-021's criterion (b) is met**: 1.0–2.0%
  capture **17% → 34%**, 0.5–1.0% **−97% → −60%**. *Caveat: IMP-021's baseline was 25 trades over 10 days
  vs 86 over 30 here — overlapping, not identical samples, so this is strongly suggestive, not a clean
  A/B.* ③ **The `<0.5%` band is the book's dominant leak** and it is an **entry** failure, not an exit one:
  those trades never traded above their entry price, so no exit structure could have saved them.
- **Why this and not a strategy change tonight.** Today's evidence points squarely at the entry signal —
  and the entry side is frozen until **08-12** while IMP-022 completes its 5-session window (today was the
  *first traded session* in it), while the exit side is frozen by the 08-07 weekly's *"do not re-tune the
  trail."* Both freezes are correct on the merits. Shipping the measurement instead is the change that
  makes the 08-12 and Friday verdicts **evidential rather than anecdotal** — and note IMP-023/IMP-024 are
  the precedent: twice now a miscalibrated instrument nearly produced an inverted conclusion.
- **Caveats.** ① It costs one historical-bars call per closed trade, hence opt-in; a 30-day window is ~86
  calls and takes ~1 minute. ② Excursion is measured on **1-minute bar highs/lows**, so it is an upper
  bound on what a stop could actually have captured intra-bar. ③ It reads IEX; a trade whose tape was thin
  will under-report its true excursion — the same limitation the bot itself trades under, deliberately.
- **Commit:** `82d1914`
- **Observed effect:** ✅ **VALIDATED (weekly 08-14).** Adopted immediately and load-bearing within two
  sessions: the 08-13 daily review's entire trade table is MFE/MAE-sourced from `bot.report --mfe` rather
  than hand-derived, and it produced that session's central finding — **all 4 winners had MAE ≤ 0.44%,
  all 4 losers MAE ≥ 0.90%**, a clean separator that the confidence score itself failed to provide.
  (a) met — no review hand-built the table this week. (b) tracked: 4 of 08-13's 8 entries sat in the
  `<0.5%`-MFE cohort (MFE +0.12/+0.28/+0.38/+0.42%) and accounted for **every loss of the session**.
  (c) partially met — the capture read exists per-session but was never re-run as one post-08-12
  aggregate; carried forward. **Judgement: highest-leverage instrumentation the bot has; it paid for
  itself inside a week and it is what made 08-13's two refutations evidential rather than rhetorical.**

---

## IMP-026 — 2026-08-11 (daily) — pin log timestamps to UTC (the 2026-08-02 WIB regression)

**Status: SHIPPED & LIVE. Diagnostics only — the trading path is byte-identical.**

- **Problem (found while root-causing today's zero-trade session, not theorised).** Every timestamp this
  bot *reasons* about is UTC — candle starts, `entry_time_utc`/`exit_time_utc`, the market-hours gate,
  the IMP-017 blackout, the IMP-007 EOD-flatten watchdog. Until **2026-08-02** the VPS clock was UTC too,
  so `logging`'s default **local-time** `asctime` agreed with all of them *by coincidence*. On 08-02 the
  host moved to **Asia/Jakarta (UTC+7)** and the coincidence broke. Since that date every line in journald
  has disagreed with itself by seven hours:

  `2026-08-11 21:24:00,223 INFO ustradebot.data | candle TSLA [1m] 2026-08-11T14:23:00+00:00 …`

  Nine days of the evidence base the post-close review reads have been silently mislabelled. **The cost is
  concrete, not hypothetical:** today's review priced what the IMP-022 market gate turned away
  (**−$31.43**), and that number depends entirely on pairing each `no entry` line with the candle that
  produced it — which required shifting every line by hand. A reviewer taking the prefix at face value
  would have concluded the bot was signalling **ABNB at 23:35, seven hours after the close.**
- **Verified negative, and it is the important half of this entry: NO trading behaviour was affected.**
  Audited every clock read in `bot/` — `main.py:55` (watchdog) `datetime.now(UTC)`, `preflight.py:148`,
  `replay.py:489`, `warmup.py:68` all `datetime.now(UTC)`; the only `fromtimestamp` is
  `candles.py:109 fromtimestamp(aligned, tz=UTC)`, tz-aware and correct. **No `utcnow()`, no naive
  `now()`, no `date.today()` anywhere in the package.** So the market-hours gate, the opening-range
  blackout and the EOD flatten all ran on correct time through the migration. This was an **instrument**
  fault, never a **capital** fault. Recorded explicitly so no future run re-opens the question.
- **Change (4 files + 1 new, zero behavioural surface):**
  - **`bot/logsetup.py` (new)** — one `setup_logging(level)`. Pins `logging.Formatter.converter =
    time.gmtime` (class-level, so *any* formatter renders UTC) **and** sets it on our own formatter
    explicitly rather than relying on inheritance. Format gains an explicit `UTC` marker —
    `"%(asctime)s UTC %(levelname)-8s %(name)s | %(message)s"` — so the timebase is **stated in every
    line rather than inferred from the host**, which is the whole failure mode.
  - **`bot/main.py` / `bot/flatten.py` / `bot/preflight.py`** — three near-identical copies of the same
    local-time `basicConfig` (which is how this drifted in the first place) collapsed into one import.
    `bot.main.setup_logging` still resolves, so nothing that referenced it breaks.
- **Three design calls worth defending.**
  1. **Default `datefmt` deliberately kept.** Setting `datefmt` would have produced a tidier
     `%Y-%m-%dT%H:%M:%SZ` but silently **drops milliseconds** — and pairing a `no entry` line to its
     candle is done *on the millisecond* (both lines land in the same second). Losing ms would have
     broken the exact analysis that found this bug. The `UTC` marker after the ms field is slightly
     unusual placement; correctness of the data beat tidiness of the format.
  2. **`force=True`.** Plain `basicConfig` is a **no-op once the root logger has any handler**, so if any
     import configured logging first our UTC formatter would be silently discarded and local time would
     come straight back. This module exists precisely so the timebase can't depend on ambient conditions,
     so the call has to be authoritative. Caught by the tests, which failed until this was added.
  3. **Not fixed by pinning `TZ=UTC` in the systemd unit.** That would work today and break the next time
     someone runs the bot, the kill switch or preflight from a shell — and it would leave the format
     still *unlabelled*, so the same silent drift could recur. Fix it in the code, once, and say so in
     the line.
- **Tests: 9 new (`tests/test_logsetup.py`), all passing.** The headline one is the **2026-08-02
  regression itself, built from today's real session**: `monkeypatch.setenv("TZ", "Asia/Jakarta")` +
  `time.tzset()`, then format a record created at the real TSLA signal moment (epoch 1786458240.0 =
  `2026-08-11T14:24:00Z`, the "market gate closed, conf=64.8%" line) and assert the output contains
  **`14:24:00`** and **not `21:24:00`** — the exact string journald actually printed today. Verified it is
  a real regression test by rendering the same record through the *old* formatter under WIB and
  confirming it produces `21:24:00`. Plus: `UTC` marker present; **milliseconds preserved**
  (`14:24:00,223`); converter is `gmtime` globally; name/numeric/unknown level handling (unknown falls
  back to INFO — logging setup must never be why the bot fails to start); all three entrypoints resolve
  to one function; and a guard asserting **no module re-introduces the local-time format string**.
- **Validation:** full suite **352 passed** (343 baseline + 9 new), zero regressions.
  `bot.preflight` **OK with 1 warning** (market closed) — Alpaca ACTIVE equity $9,085.28, SQL Server
  connected + schema ensured, Telegram delivered — and its own output now renders with the `UTC` marker.
  (`ruff` is not installed in the VPS venv — dev-only dependency, lint not run, as on IMP-022.)
- **Caveats, stated plainly.** ① **This adds no edge and moves no P&L**, and it is not dressed up as
  though it does. It was chosen because both P&L surfaces are under active measurement freezes that
  expire within 72 hours (entry side 08-12 for IMP-022's window, exit side Friday for IMP-021), **both
  verdicts are read off journald**, and breaking either freeze on one session's data would be thrash.
  ② **Journald lines from 08-02 → 08-11 remain WIB** — this fixes forward, it cannot retro-label history.
  Anyone reading that range must subtract 7 hours; noted in today's daily review.
  ③ The `UTC` marker changes the log line shape, so any downstream log grep that anchors on the
  `levelname` column position would need adjusting — nothing in this repo does.
- **Commit:** `49ecb07`
- **Observed effect:** ✅ **VALIDATED (weekly 08-14).** (a) met — every journald line from 08-11 21:23:58
  onward carries the `UTC` marker and the prefix matches the payload (`2026-08-12 14:08:01,840 UTC ERROR`
  against a journald stamp of `Aug 12 14:08:01`, i.e. **zero offset**, where pre-fix lines showed the
  full 7 hours: `Aug 10 11:36:38 … 2026-08-10 18:36:38`). (b) met — this weekly reconstructed all five
  sessions' refusal tables straight from journald with **no hand-shifting**, which is precisely what the
  08-10 review had to do manually. (c) no residual offset found on any path. **Judgement: small change,
  disproportionate payoff — it removed a standing misdiagnosis risk that this repo's own memory flagged
  as having silently corrupted nine days of sibling-bot logs.**

---

## IMP-027 — 2026-08-12 (daily) — an exit may never be attributed to a sell that filled before its entry

**Trigger.** The 08-12 MU trade. The bot logged its exit as
`reconcile_exit MU: broker-side fill @ 872.25 (order 5434412a…)`. That order is the **2026-08-10** MU
stop leg — a different trade, two sessions old. The real exit (`c94f6f32`, stop 925.74) filled
**@926.31 at 18:25:38.99Z**; `reconcile_exit` ran at **18:25:40.07Z**, 1.09 s later.

**Root cause.** `reconcile_exit` confirmed the position was gone and then took *the newest filled sell
in the closed-order listing* on faith. Alpaca's closed-order listing is **eventually consistent**: a
fill from ~1 s ago need not be in it yet. Today it wasn't, so the scan fell straight through to the
previous trade's exit and returned a price from two sessions earlier. Confirming *"the position is
flat"* proves an exit happened; it does **not** prove the order you found is that exit. Verified after
the close by re-issuing the identical query — it now returns `c94f6f32` @926.31 first. The data was
always right; the read was 1 second early.

**Impact.** A **+$4.46 win recorded as a −$103.66 loss** — a $108 error, 1.2% of equity, wrong-signed,
on the only trade of the day. It would have landed in `dbo.trades`, the confidence-bucket table (80–89),
the MFE study and every downstream IMP judgement. (It did not, only because a *separate* defect — the
entry INSERT hitting a dead socket — meant there was no row to write the exit onto. Two bugs cancelling
is not a safety net.)

This is the **residual half of IMP-015**, which fixed the *entry-not-yet-filled* end of exactly this
failure (2026-07-20 NVDA: +$41 booked on a −$58 stop-out) and left the *exit-not-yet-listed* end open.
Third occurrence of the class (07-10 SE, 07-20 NVDA, 08-12 MU). IMP-015 answered it with a timing
guard; this answers it with an invariant, which is why it should be the last one.

**Change.** `bot/executor.py`, `bot/risk.py`:
- New `OrderExecutor.entry_filled_at(order_id)` — reads the entry buy's `filled_at` (single read, no
  poll; by exit time the entry is definitively filled, and the candle thread must not stall).
- `reconcile_exit(symbol, *, after=None)` skips any candidate whose `filled_at` is missing or precedes
  `after`. **An exit cannot fill before its own entry** — so a prior trade's sell is now structurally
  unmatchable, independent of listing lag, sort order or clock skew.
- `RiskManager._entry_filled_at()` supplies the anchor on **both** paths that reach reconcile
  (`exit_position`'s close-failed fallback and the poll-driven `reconcile_if_closed`).

**Degrades safely, deliberately.** No qualifying candidate → `None` → the caller leaves the symbol
`MANAGING` and retries next candle; today that retry reads 926.31 correctly at 18:26. A candidate with
an unreadable fill time is skipped while anchored — an unverifiable price is precisely what this must
never book. `after=None` (a startup-reconciled holding, whose entry the bot never saw) leaves behaviour
unchanged rather than blocking a legitimate exit.

**Validation.** **359 tests pass** (was 352; +7). Six new tests in `test_executor.py` are built from
today's real timestamps to the microsecond — the 08-10 stale sell @872.25 and today's @926.31 — plus two
in `test_risk.py` asserting *both* reconcile paths pass the anchor (an unanchored call is the bug).
**Non-vacuity checked:** with the guard neutralised, `test_reconcile_exit_rejects_sell_that_predates_
the_entry` fails; restored, it passes. Preflight OK (Alpaca ACTIVE, equity $9,089.74, SQL Server
connected, Telegram delivered). `bot/replay.py`'s simulated broker mirrors the new surface, so replay
stays signature-compatible with live.

**Risk / no-go check.** Read-only order-history logic. No position size, loss limit, kill switch or
risk check touched. No entry or exit *decision* changed — the trail, the stop, the gate and the signal
all behave identically. This changes only which order the bot is willing to call its exit, and it can
only ever refuse, never invent.

**Commit.** `b810188` — deployed and restarted 2026-08-12.

- **Observed effect:** ✅ **VALIDATED (weekly 08-14).** First full session under the guard was 08-13,
  which is the strongest possible test: **8 trades, 8 entries and 8 exits, every exit attributed to its
  own sell**, broker-reconciled to the cent (`last_equity` 9,089.68 → `equity` 9,124.21 = **+$34.53**,
  identical to `dbo.trades`). Three of those exits filled within seconds of each other (INTC 15:35:06,
  MU 15:34:33) — exactly the interleaved-fill shape that produced the 08-12 mis-book — and none was
  cross-attributed. Zero false refusals: no symbol was left stuck in `MANAGING` by the guard declining a
  legitimate candidate. **The 08-12 failure ($108 error in the wrong direction on the only trade of the
  day) has not recurred.** Judgement: correct fix, correctly scoped, and the third occurrence of this
  bug class is now closed at the invariant level rather than by another timing heuristic.

---

## IMP-028 — 2026-08-13 (daily) — `record_entry` retries once on a fresh connection

> **⚠️ ENTRY WRITTEN BY THE WEEKLY REVIEW OF 2026-08-14, NOT BY ITS AUTHOR.**
> **STATUS: WRITTEN — NOT COMMITTED, NOT DEPLOYED, NOT RUNNING.**
> This number is reserved here so the series cannot be reissued. The next new change is **IMP-029**.

- **What it is.** The fix for the 08-12 defect that erased an entire session from `dbo.trades`: a dead
  socket (`08S01 TCP Provider`) killed the MU entry INSERT, `record_entry` logged and returned `None`
  without retrying, the exit then had no `trade_id`, and **both legs were lost while the broker held a
  real filled position**. The change wraps the insert in `_insert_entry`, retries **exactly once** on a
  fresh connection after `_reset()`, and makes the retry **idempotent** by looking the bracket up by its
  unique Alpaca `entry_order_id` first — so a failure raised *by* `commit()` (where the transaction may
  have landed anyway) cannot double-count a position.
- **The design is sound and the code is written.** `bot/persistence.py` (+186/−68) and
  `tests/test_persistence.py` (+107). The 08-13 daily review reports **363 tests passing** (359 → 363)
  with non-vacuity verified, and this weekly independently re-ran the full suite on the working tree:
  **`pytest -q` exits 0, no failures.** The problem is not the change. The problem is that it was
  never delivered.
- **🔴 Three-way delivery failure, found by this weekly:**
  1. **Not committed.** Both files have sat as uncommitted working-tree modifications since
     **08-13 21:43 UTC** — through a full trading session and two days.
  2. **Not deployed.** `ustradebot.service` has `ActiveEnterTimestamp = 2026-08-13 11:37:48 UTC`,
     `NRestarts=0`, MainPID **805070** started `Thu Aug 13 11:37:48` — i.e. the process has been up
     continuously since **ten hours *before* the files were edited**, and was never restarted. The
     running bot executed all of 08-14 on the **old** `persistence.py`. **The 08-12 data-loss defect
     is still live in production.**
  3. **Not recorded.** The 08-13 daily review states *"Details in `memory/improvement-log.md`"* — there
     was no IMP-028 entry in this file until this weekly wrote one. The cross-reference was false, and
     any later routine reading this log for the next free number would have **reissued 028**.
  - Ancillary: both files are owned `root:root` rather than `ustradebot:ustradebot`, violating the
    standing ownership rule (mode 664 keeps them world-readable, so the service can still read them —
    no functional impact, but it is the same root-owns-repo-files gotcha this project has hit before).
- **Deliberately left untouched by this weekly.** The standing rule is that a review does not touch
  uncommitted modifications it did not make. The code is not mine to validate, commit or deploy on
  someone else's behalf, and the correct owner is the routine that wrote it.
- **➡️ HANDOFF — action for the daily review of 2026-08-14 (21:10 UTC).** This is your one job tonight
  and it is **not** a new change: (1) `chown ustradebot:ustradebot bot/persistence.py
  tests/test_persistence.py`; (2) re-run `pytest -q` (expect 363 pass) and `bot.preflight`; (3) commit
  **only** those two files as `IMP-028: record_entry retries once on a fresh connection` and push;
  (4) `systemctl restart ustradebot.service`, wait ~10s, confirm `is-active` and a clean startup with
  warmup primed; (5) **verify deployment the way this project's memory says to — compare
  `systemctl show -p ActiveEnterTimestamp` against the file mtime.** A restart that predates the edit
  means the fix is not running. (6) Replace this block's status line with the real commit hash.
- **Observed effect:** ❌ **NONE — the change has never executed.** It cannot be evaluated until it is
  deployed. Its motivating defect did not recur on 08-13 or 08-14, but that is luck and a healthy
  socket, not this fix working: the code that ran those sessions is the code that failed on 08-12.
