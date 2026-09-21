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
> **STATUS: ✅ DELIVERED — commit `da161c7`, pushed and deployed 2026-08-14 21:15:11 UTC**
> by the daily review of 2026-08-14, per the handoff at the foot of this entry.
> The next new change is **IMP-029**.

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

### ✅ Handoff executed — daily review of 2026-08-14

All six steps completed, in order, with the results the weekly asked for:

1. `chown ustradebot:ustradebot bot/persistence.py tests/test_persistence.py` — done (both were
   `root:root`; now `ustradebot:ustradebot`, mode 664 preserved).
2. **`pytest -q` → `363 passed, 1 warning`, exit 0** — exactly the 359 → 363 the weekly predicted.
   Non-vacuity re-checked by name: `pytest tests/test_persistence.py -k "retry or retries"` →
   **6 passed**, 26 deselected. **`bot.preflight` → RESULT: OK**, all three gates PASS (Alpaca
   ACTIVE equity 9,123.87 / SQL Server connected, schema ensured / Telegram delivered); the single
   WARN is the expected "session CLOSED now".
3. Committed **only** the two files — **`da161c7`**. `git status` before the commit showed
   `memory/daily-review.md` also dirty; it was left unstaged here and committed separately with the
   08-14 review, per the stage-only-what-you-touched rule.
4. Pushed `e004bec..da161c7 main -> main`, then `systemctl restart ustradebot.service` →
   **`active`**, clean startup: schema ensured, Alpaca ACTIVE, **no open positions**,
   **warmup primed 20/20 symbols**, IEX stream subscribed to all 20. **Zero warnings or errors.**
5. **Deployment verified against the mtime, as instructed:** `ActiveEnterTimestamp` is now
   **`Fri 2026-08-14 21:15:11 UTC`** vs `bot/persistence.py` mtime **`2026-08-13 21:43:07`** — the
   restart **postdates** the edit, so the running image contains the fix. New `MainPID=923901`
   (was 805070, which had been up since 08-13 11:37:48 with `NRestarts=0`). **The retry path is
   live in production for the first time.**
6. Status line at the head of this entry replaced with the commit hash. ✔

- **Observed effect (from 2026-08-14):** ⏳ **not yet measurable — deployed after the close, so it
  has not seen a live entry.** It cannot produce evidence until a session both trades *and* hits a
  stale socket, which is rare by construction. **Do not treat a quiet `dbo.trades` as validation;**
  the signal to look for is the log line `DB entry <SYM> recovered on retry (trade_id=…)`, or
  `DB entry <SYM> was already committed as trade_id=…` for the idempotent branch. Until one of
  those appears, this fix is unexercised, not proven.
- **Standing lesson, third occurrence of this class in this project.** The 08-13 run reported
  "363 tests passing" and pointed at an improvement-log entry that did not exist, while committing
  nothing and restarting nothing. Validation is not delivery. **A change is only real when
  `ActiveEnterTimestamp` postdates the file mtime** — the same check that caught the IMP-003
  deploy-gap on USTradeWisBot. Every routine that ships code must end with that comparison, and
  the number must appear in this log with a commit hash before the run reports success.

---

## IMP-029 — 2026-08-17 (daily) — record the pre-entry tape context on every entry

**Status: SHIPPED & LIVE. Instrumentation only — zero change to the trading path.**

> **Number note.** The 08-14 daily review pencilled IMP-029 as "make the trailing stop
> ATR-relative". That did **not** ship and the number has been reassigned. Two reasons, both
> disqualifying on their own: the 08-14 **weekly explicitly froze `TRAIL_PERCENT` and the two-stage
> trail**, and the candidate was self-gated on full-history `bot/replay.py` validation that has not
> been run. It is **renumbered to a future IMP, not cancelled** — and this change is precisely what
> unblocks it (see below).

- **Problem.** The 08-14 weekly named one task as the week's most important: *"is there any pre-entry
  discriminator for entries that never trade above their entry price?"* — the `<0.5%`-MFE cohort,
  which it called the sole remaining first-order leak. Tonight's study answered it (4-of-4 windows,
  see the 08-17 daily review) and the answer is **pre-entry volatility**. But the study had to be run
  from a **throwaway script that re-fetched 1-minute bars for 251 historical trades**, because the
  variables it tests are recorded **nowhere**. `dbo.trades` stores the five confidence sub-scores and
  nothing about the tape the entry was taken into.
  **The bot already computes the number and throws it away**: `RibbonSnapshot.atr` is populated on
  every trigger candle and feeds `conf_volatility`, then is discarded at the signal boundary.
  This is the IMP-025 argument, one step upstream — that entry made *excursion* measurable after it
  had been rebuilt by hand three reviews running; this makes the *entry conditions* measurable
  before the same thing happens to them.
- **Change (5 files, no behavioural surface):**
  - **`bot/strategy.py`** — two pure helpers, `atr_pct_of()` and `ribbon_spread_pct_of()`, and two
    new optional fields on `TradeSignal`. Both are **price-relative** (`atr / close * 100`), which is
    the point: today's INTC at $105 and MU at $1,034 have raw ATRs an order of magnitude apart but
    read **0.204%** and **0.158%** — on one scale, and comparable. Both return **`None`, never 0.0**,
    when the indicator has not seeded: "not measured" and "a flat tape" are different facts and the
    study that reads this column must not conflate them. The `ENTRY` log line now carries
    `tape(atr=… spread=…)` so the value is in journald even if the DB write fails.
  - **`bot/persistence.py`** — a frozen `TapeContext`, threaded through `TradeRecorder.on_signal`
    (which already caches the confidence breakdown per symbol for exactly this reason — the tape is
    known at signal time and is not recoverable from the `ExecutionResult`) into `record_entry` /
    `_insert_entry` as an optional third argument. **Both IMP-028 retry paths pass it**, so a row
    recovered on the retry is not recovered stripped of its tape.
  - **`sql/schema.sql`** — `atr_pct` and `ribbon_spread_pct` as `DECIMAL(9,5) NULL`, added to the
    `CREATE TABLE` for fresh installs *and* as two idempotent `IF COL_LENGTH(...) IS NULL ALTER TABLE`
    batches for this install, following the existing `dbo.orders.status` widening idiom.
  - **`tests/`** — +9 tests.
- **Why this and not the filter the study points at.** The evidence is directionally strong (4/4
  windows on dead-rate, at a fixed threshold with no per-window refitting) but **not yet decision-grade**:
  net P&L agrees in only **3 of 4** windows, the current-config window has **n=5** on the quiet side,
  and — decisively — **it would not have prevented either of today's losses**, whose pre-entry ATRs
  (0.204%, 0.158%) both sat on the *active* side of the threshold. Shipping an entry filter on that
  would be exactly the one-day overfit this routine exists to avoid, and it would breach the freeze.
  **The weekly's instruction was "build the evidence, do not ship the filter." This is the evidence,
  made permanent.** Friday inherits a live-recorded column instead of a script.
- **Validation.** **372 tests pass** (363 → 372, +9). Four in `test_strategy.py` cover the helpers
  against today's real INTC/MU prices and the unseeded case; five in `test_persistence.py` cover the
  signal→row hand-off, NULL-not-zero, the IMP-028 retry preserving the tape, and a **placeholder/column
  count assertion** so a future column can never silently shift the values into the wrong columns.
  **Two pre-existing tests were repaired, not just updated:** they asserted on `params[-5:]`, a tail
  slice that this change shifted — and which had been **failing open** on the all-`None` cases. They
  now slice from named offsets (`_CONF_SUBSCORES`, `_TAPE`).
  **Non-vacuity verified:** neutralising the change (unseeded ATR → 0.0, tape params → hardcoded
  `None`) fails **4** of the new tests; restored, all 372 pass. `bot.preflight` → **RESULT: OK**
  (Alpaca ACTIVE equity 9,089.21 / SQL Server connected, schema ensured **10 batches**, was 8 /
  Telegram delivered), single expected "session CLOSED" WARN. **Schema verified against the live DB
  after the ALTER: both columns present as `decimal(9,5) NULL`, all 268 existing rows preserved and
  NULL** (they are not zero-filled — any study must exclude pre-08-17 trades, not treat them as flat).
  `ruff` is not installed in the VPS venv (dev-only dependency), so lint was not run here.
- **Risk / no-go check.** No entry, exit or sizing *decision* is changed: the two fields are derived
  read-only from a snapshot the scorer had already consumed, and **nothing reads them back**. A test
  asserts the decision for a snapshot is exactly `evaluate_entry`'s own. Note honestly that ATR itself
  is *not* new to the decision — it has always fed `conf_volatility`; what is new is only the
  recording of it. Position size, loss limits, the stop, the trail, the market gate and the kill
  switch are all untouched. Worst case on a bug is two NULL columns.
- **Commit.** `8e00c6b` — pushed and deployed 2026-08-17 (restart verified below).
- **Observed effect:** ✅ **VALIDATED (weekly 08-21) — but via a route this entry did not anticipate.**
  The stated signal has **still not fired**: `dbo.trades.atr_pct` is non-NULL on **0 of 268 rows**,
  because there has been no entry since 08-17. What happened instead is that IMP-030 shipped the next
  night and carried the *same* tape context onto every **refused** candidate — so the fields are
  populated on **all 76 refusal rows** of 08-19/20/21. And they earned their place there:
  `ribbon_spread_pct` is the week's single best pre-entry lead for the `<0.5%`-MFE cohort (08-21: the
  two candidates with spread ≥0.11 ran **+2.62%** and **+2.05%** MFE; the other 21, all ≤0.029,
  averaged **+0.30%**). **Validated on the refusal side, still unvalidated on the trade side** — leave
  that half open until a live entry writes a row.

---

## IMP-030 — persist refused entry candidates to `dbo.entry_refusals` (2026-08-18)

- **Trigger.** 2026-08-18 made **33 scored entry decisions and wrote zero rows to SQL**: 18
  `crossover < 0.25`, 13 `confidence < 60`, and **2 fully-qualifying entries the IMP-022
  market gate turned away** (ABNB conf 79.8 at 14:25, NFLX conf 79.3 at 15:09). A flat session
  currently persists nothing at all, and flat sessions are no longer exceptional — **08-14 and
  08-18 both traded zero times**, and this morning's research forecast more of them.
- **The argument, which is not "more instrumentation for its own sake."** Refusals are the
  **counterfactual half of `dbo.trades`**. Every entry-threshold study this bot has ever run —
  `MIN_CROSSOVER` (refuted 08-13), the confidence bands, the `<0.5%`-MFE cohort (08-17) — was
  run on the **taken** population alone. *A threshold cannot be priced from the trades it
  admits; only from the candidates it rejects.* That population existed solely as journald
  INFO lines, which roll.
  **This bit tonight, concretely:** the one genuinely useful analysis this review produced —
  pricing the market gate — **could only reach n=15, spanning 08-07→08-18, because that is the
  entire journald retention window.** The answer it gave was worth having (the gate refuses a
  population that is 60% dead-on-arrival vs a 46.6% baseline, and averages −0.099% to the
  flatten — **the gate is a mild positive and the "it blocks the profitable 70-79 band" story
  is refuted**), and it is not decision-grade at n=15. Persisted, it is n≈100 by mid-September.
  This is the IMP-025 / IMP-029 argument applied to the one population still being discarded.
- **Change (4 files + tests, no behavioural surface):**
  - **`bot/strategy.py`** — a frozen `RefusedEntry` (symbol, candle_start, reason,
    `market_gate_open`, close_price, confidence + full `ConfidenceBreakdown`, and the IMP-029
    `atr_pct` / `ribbon_spread_pct`), an `OnRefusal` callback, and `_emit_refusal()` called
    from **exactly two points**: the scored-near-miss branch of `_log_skip`, and the IMP-022
    gate veto. It **mirrors the `on_signal` contract including swallowing callback failures** —
    an observational write must never kill a candle thread that is still managing positions.
  - **Volume guard, deliberate:** only candidates the scorer **actually scored** are recorded.
    The unscored "no fresh cross" rejections are **~10k a session** and carry no information;
    they stay DEBUG-only. Today's load would have been **33 rows**.
  - **`bot/persistence.py`** — `TradeStore.record_refusal()` and `TradeRecorder.on_refusal`.
    **No retry, unlike `record_entry` (IMP-028), and that asymmetry is the point:** a refusal
    is a datapoint, not a position — losing one to a stale socket costs a row in a study, not
    money, and the candle thread must not pay two round trips for it. Every failure is
    swallowed + `_reset()`.
    `RefusedEntry` lives in `strategy.py` (where it is produced) and is imported under
    `TYPE_CHECKING`, preserving the existing dependency direction — persistence already depends
    on strategy this way for `TradeSignal`, never the reverse.
  - **`bot/main.py`** — wired as `on_refusal=rec_refusal`. **SQL only, no Telegram/console
    fan-out:** ~30 a session is signal in a table and noise in a chat.
  - **`sql/schema.sql`** — `dbo.entry_refusals` (15 columns) + `IX_entry_refusals_candle` on
    `(candle_start_utc, symbol)`, both idempotent, following the existing `IF NOT EXISTS` idiom.
- **Why this and not the two filters today's refusals point at.** Today killed **all five**
  candidates that reached the profitable 70-79 band: three on the crossover floor (AAPL 70.6 /
  xo 0.14, ABNB 70.1 / 0.12, BABA 72.2 / 0.10) and two on the gate. That is a tempting-looking
  entry-filter change and it is refused on three independent grounds: **`MIN_CROSSOVER` was
  refuted unanimously across four windows on 08-13**; the **08-14 weekly's shipping freeze on
  trading logic runs one more week**; and **n=3 on a single zero-trade day** is the exact
  one-day overfit this routine exists to prevent. Meanwhile the gate half of that story was
  *tested tonight and refuted outright* — both of today's gate refusals would have lost
  (ABNB −0.41%, NFLX −1.47% to the flatten). Recording beats guessing.
- **Validation.** **388 tests pass** (372 → 388, **+16**). Seven in `test_strategy.py` cover
  both emit points against today's real refusal shapes (the near-miss fixture reproduces
  `crossover 0.18 < 0.25`, the same form as the live AAPL 0.21 and NFLX 0.24), the volume guard,
  the populations not overlapping (a taken signal records no refusal), tape-context parity with
  an entry, sink-failure containment, and the no-sink case. Eight in `test_persistence.py`
  cover the row, a **placeholder/column-count assertion** (so a future column cannot silently
  shift values), NULL-not-zero, reason truncation at the 160-char column width, failure
  swallowing + reset, the deliberate no-retry, and table isolation from `trades`/`orders`/
  `positions`. Plus **one end-to-end test driving a real `StrategyEngine` through a real
  `TradeRecorder` into the store** — IMP-028's delivery failure was a wiring gap, not a logic
  bug, so the seam is now pinned.
  **Non-vacuity verified:** neutralising the change (`_emit_refusal` early-return,
  `market_gate_open` hardcoded `None`, truncation removed) fails **6** tests; restored, all 388
  pass. `bot.preflight` → **RESULT: OK** (Alpaca ACTIVE, equity 9,089.13 / SQL Server connected,
  schema ensured **12 batches**, was 10 / Telegram delivered), single expected "session CLOSED"
  WARN. **Live schema verified after apply: `dbo.entry_refusals` present with all 15 columns at
  the intended types, `IX_entry_refusals_candle` present, and all 268 existing `dbo.trades`
  rows preserved.**
- **Risk / no-go check.** **No entry, exit or sizing decision changes.** Nothing reads this
  table back. Position size, loss limits, the stop, the trail, the market gate, the stand-down
  and the kill switch are all untouched; paper-only unchanged. The write sits behind an
  optional callback that defaults to `None`, so a bot with no database behaves exactly as
  before. Worst case on a bug is a missing row in a study. Freeze-compliant by the same
  standard IMP-027/028/029 were judged against.
- **Commit.** `dacd5d2` — pushed and deployed 2026-08-18 (restart verified: `is-active` active,
  `ActiveEnterTimestamp` 20:12:17 UTC > file mtimes, schema 12 batches, warmup primed **19/19**,
  IEX stream subscribed to all 19, `NRestarts=0`, zero errors).
- **Observed effect:** ✅ **VALIDATED (weekly 08-21) — the highest-leverage change of the week.**
  The stated signal fired on the **next** session: **26 rows** on 08-19, then 27 and 23, for **76 rows
  across three sessions**. It delivered exactly the stated payoff and more: the 08-21 weekly ran its
  crossover-floor, confidence-bar and gate studies **against rows**, not a rolling journald window
  (which only keeps ~11 days and was the binding limit on the 08-18 gate study, n=15). Structurally it
  raised the review's evidence sampling rate from **~1–2 trades/day to ~25 refusals/day (~15×)** — on a
  week when the bot took **2 trades**, this table was the only evidence there was.
- **Carry-forward:** **IMP-029 is still unvalidated** — `atr_pct IS NOT NULL` returns 0 rows,
  because there have been no entries since it shipped on 08-17. Both instrumentation IMPs now
  wait on the same thing: the next actual entry.
- **✅ OBSERVED EFFECT (updated 2026-08-19, one session later): VALIDATED.** The first live
  session after the deploy wrote **26 rows** to `dbo.entry_refusals` (17 crossover-floor, 5
  confidence, 4 market gate), every one carrying the full confidence breakdown and a non-NULL
  IMP-029 `atr_pct`. **The payoff arrived immediately and was larger than forecast:** the 08-19
  daily review priced all 26 refusals forward (MFE/MAE over 60 min + move to the flatten) as a
  SQL query plus one bar fetch, and the result **refuted the crossover-floor-is-too-tight story
  for a third independent time** — the floor's 17 refusals were 76% dead-on-arrival (vs a 46.6%
  baseline for taken trades) and averaged **−0.508%** to the flatten, the worst of the three
  cohorts. That study was not runnable at all before this change.

---

## IMP-031 — record the market-gate state on every scored refusal (2026-08-19)

**Status: SHIPPED & LIVE. Instrumentation only — zero change to the trading path.**

- **Trigger.** IMP-030's first live session (2026-08-19: 26 scored refusals, 0 entries) let the
  daily review run the study it was built for — and the study **hit a hole it could not close.**
  Of the 26 refusals, **17 died on the crossover floor**, and the natural next question is "what
  would loosening the floor have recovered?" **That question is unanswerable from the rows as
  they stand**, because the floor's refusals recorded `market_gate_open = NULL`. The IMP-022
  market gate was independently observed **shut at 14:13, 14:16, 15:47 and 16:15** (the four gate
  refusals), so an unknown share of those 17 sat inside gate-closed windows and **were never
  recoverable at any floor setting.**
- **The argument, stated precisely.** *Loosening an entry threshold does not admit a candidate —
  it advances that candidate to the gate.* The filters are sequential, so the counterfactual
  population for any threshold study is bounded by the gate, not by the threshold alone. A study
  that reads a near-miss row without the gate state **systematically overstates** what loosening
  would recover, and it overstates it by an amount that varies with the day's regime — which is
  exactly the kind of bias that produces a confident wrong answer rather than a noisy one.
  **Friday's weekly is due to run this study**, so the gap is worth closing tonight rather than
  after it has produced a number someone acts on.
- **Change (2 files + tests, no behavioural surface):**
  - **`bot/strategy.py`** — the scored-near-miss emit point passes
    `gate_open=self._market_gate_open()` instead of the hardcoded `None`. `_market_gate_open()`
    is a **pure read of a cached snapshot** (`self._gate_snap.get(sym)` → `snap.gate_open`), with
    no I/O and no mutation beyond a once-only warning latch, so the cost is a dict lookup on the
    **~26 scored candidates a session** — deliberately *not* on the ~10k unscored "no fresh
    cross" rejections, which never reach this branch.
  - **`RefusedEntry` docstring rewritten** for the new semantics, which are the substance of the
    change: `reason` says **which filter refused the candidate**; `market_gate_open` says
    **whether the gate would also have refused it**. The two are independent, and the study needs
    to read them separately. **`None` now means genuinely not measured** (the 26 pre-IMP-031 rows
    from 08-19), never "open" — the same NULL-not-zero discipline IMP-029 established.
  - **No schema change.** The column already exists from IMP-030; only what is written into it
    changes. Nothing to ALTER, nothing to migrate, and the 26 existing rows stay honestly NULL.
- **Why this and not the two changes today's data appears to invite.** Today killed all three
  candidates that reached the profitable 70-79 band on the crossover floor (AAPL 75.5 / xo 0.20,
  AMZN 74.6 / xo 0.15, BABA 71.7 / xo 0.10). **All three were priced forward and all three lost
  or went nowhere** (−0.45%, +0.20%, −0.85% to the flatten) — the floor was right, for the third
  independent time, and `MIN_CROSSOVER` remains frozen and thrice-refuted. Separately, today
  surfaced a genuinely strong structural finding — **`conf_rsi` is 1.0 on 252 of 268 trades and
  26 of 26 refusals**, so ~20 of the 100 confidence points are a constant (with `conf_volatility`
  near-constant for another 15) — which is the best explanation yet for six weeks of
  anti-predictive confidence. **The confidence weights are explicitly frozen by the 08-14
  weekly**, and a finding that good deserves replay validation across ≥3 windows, not a one-night
  edit. It is handed to Friday, recorded, not acted on.
- **Validation.** **391 tests pass** (388 → 391, **+3**). `test_near_miss_records_a_shut_gate`
  pins the discriminator (refused by the floor **and** the tape shut — the unrecoverable case)
  and asserts `reason` still attributes the refusal to the floor rather than the gate;
  `test_near_miss_records_an_open_gate` pins the recoverable case; and
  `test_gate_state_on_a_near_miss_changes_no_decision` runs the same near-miss under both tapes
  and asserts the **engine state, the refusal reason and the (empty) executor call list are
  identical** — only the recorded field differs. One pre-existing test
  (`test_scored_near_miss_is_persisted_with_its_breakdown`) was **updated, not deleted**: its
  `market_gate_open is None` assertion became `is True`, because with no QQQ ribbon fed the gate
  **fails open by design** and the row now honestly records that.
  **Non-vacuity verified:** reverting the one line to `gate_open=None` fails **3** tests;
  restored, all 391 pass. `bot.preflight` → **RESULT: OK** (Alpaca ACTIVE, equity 9,089.13 / SQL
  Server connected, schema ensured 12 batches / Telegram delivered), single expected "session
  CLOSED" WARN.
- **Risk / no-go check.** **No entry, exit or sizing decision changes** — pinned by a test, not
  merely asserted. Position size, loss limits, the stop, the trail, the market gate itself, the
  stand-down and the kill switch are untouched; paper-only unchanged. The one honest side effect
  is that `_market_gate_open()`'s **once-only** "market filter has no ready 5m ribbon" warning can
  now latch on a near-miss candle where it previously would not have — strictly more informative,
  latched so it cannot spam, and it reports a condition that was already true. Worst case on a
  bug is a wrong boolean in an observational column. Freeze-compliant by the same standard
  IMP-027/028/029/030 were judged against.
- **Commit.** `5dc6c86` — pushed and deployed 2026-08-19 (restart verified below).
- **Observed effect:** ✅ **VALIDATED (weekly 08-21) — and it did more than it was built for.**
  The stated signal fired the next session: `market_gate_open` non-NULL on all 27 rows of 08-20 and
  all 23 of 08-21. It delivered the intended payoff (the floor's population can now be partitioned by
  tape state) but its **larger effect was on the review process itself**: it revealed
  `market_gate_open = FALSE` on **all 27** of 08-20's rows — not just the 8 labelled "gate closed" —
  which exposed the **08-14 weekly's "gate = 5% of refusals" restrictiveness metric as structurally
  biased.** That metric's ceiling is set by the filters upstream of it (a candidate failing crossover
  is attributed to crossover even though the gate would also have refused it), so on a day of
  *maximum* restrictiveness — 0.0% duty cycle — it still read only 30%. **A change that corrects a
  standing error in how the reviews reason is worth more than one that tunes a constant.**

---

## IMP-032 — persist the market gate's duty cycle to `dbo.market_gate` (2026-08-20, daily)

**Status: SHIPPED + DEPLOYED.** Commit `69a17cb`, service restarted and verified (see
Deployment below — this entry is written in the past tense only because both are confirmed, per
the 08-14 weekly's standing rule).

### The defect
Every study this bot has run on its market gate (IMP-022) has had a **numerator and no
denominator.** `dbo.entry_refusals` records the gate state (IMP-031) only at the ~30 moments a
session where a candidate happened to be *scored*. That measures the gate where candidates land;
it does not measure how often the gate is open.

The two diverge badly, and 2026-08-20 is the clean proof. The gate was open **0 of 69 bars** in
the entry window — a long was structurally impossible all day — yet only **8 of 27 refusals**
were labelled "market gate closed." The other 19 candidates failed the crossover floor or the
confidence bar *first* and were attributed there, even though the gate would have refused every
one of them (all 27 rows carry `market_gate_open = False`).

This has a concrete consequence: the **08-14 weekly retired the gate's tripwire** on the finding
that *"the gate accounted for 7 of 141 refusals (5.0%) — the tripwire is >80% and it is nowhere
near it."* That metric's ceiling is set by how many candidates survive the other two filters, so
it can never approach 80%. On the most restrictive day possible it reads 30%. It is not a
restrictiveness measure at all.

The duty cycle *is*, and reconstructing it from Alpaca's aggregated 5m bars — as tonight's review
had to — is not a substitute: the bot builds its own 5m candles from IEX **trade ticks** with
activity-driven closes (CLAUDE.md), which is a different series with different bar boundaries. The
gate the bot actually enforces was unobservable except at those ~30 moments.

### The change
One row per **closed gate candle** for `MARKET_FILTER_SYMBOL`, from the bot's own ribbon.

- `bot/strategy.py` — new frozen `MarketGateSample` (symbol, candle_start, `gate_open`,
  `stacked`, `fast_rising`, close, ema fast/mid/slow) and an `on_gate_sample` callback.
  `on_long_candle` emits it **after** storing the snapshot, via `_emit_gate_sample`, which
  swallows callback failures on the same rule as `_emit_refusal`.
  - **Filter symbol only.** All 18 watchlist names run a gate ribbon; sampling all of them would
    put 18 rows a bar into a table whose whole purpose is counting one series.
  - **Seeded ribbons only.** An unready ribbon fails the gate *open* (`_market_gate_open`), so
    recording it would write a permissive row for a state the bot could not evaluate — inflating
    the duty cycle exactly where it is least trustworthy.
  - `stacked` and `fast_rising` are the two conjuncts of `gate_open`, **stored apart**, so a 0%
    session is readable: a ribbon that lost its ordering and one merely rolling over are
    different tapes and only the second is near reopening.
- `bot/warmup.py` — **the trap this change had to avoid.** Warmup replayed history through
  `strategy.on_long_candle`, so a naive emit would backfill ~390 never-live rows at *every*
  restart — and the daily-review routine restarts the service every evening. Warmup now calls a
  new non-emitting `StrategyEngine.warmup_gate`, exactly mirroring the existing `warmup_trigger`,
  restoring the module's own stated invariant that warmup sinks "only fold candles into indicator
  state." Indicator effect is byte-identical.
- `bot/persistence.py` — `TradeStore.record_gate_sample` + `TradeRecorder.on_gate_sample`. Same
  contract as `record_refusal`: no retry, no reset on the happy path, errors logged and swallowed.
  The insert is guarded by `WHERE NOT EXISTS` on the unique key, so a re-emitted bar is a silent
  no-op — this table is *counted*, so a duplicate would bias the statistic, not merely repeat a row.
- `sql/schema.sql` — `dbo.market_gate` + **UNIQUE** index `UX_market_gate_candle
  (symbol, candle_start_utc)`. Unique rather than merely indexed, for the same reason.
- `bot/main.py` — wired `on_gate_sample=rec_gate`. SQL only; no console or Telegram fan-out.

### Why this and not the tempting alternative
Today's best refused candidate was **MU 14:20, confidence 89.1, crossover 0.777**, which ran
**+1.56% to the flatten** and was stopped by the gate alone. The tempting change is to loosen the
gate. It was **not** made, for three reasons: the gate has **four independent windows** of
profitability evidence behind it (5d/10d/60d replay + 08-13 live), the **90-100 confidence band
is 0-for-3 lifetime at −$144.42** so the bot's own record says its best-scored signals are its
worst, and n=1. It is also **frozen** — the 08-14 weekly's shipping freeze on trading logic
permits correctness, data-integrity and instrumentation only. This change is instrumentation, and
it is the thing that lets Friday's weekly rule on the gate with real data instead of a proxy.

### Non-vacuity
Verified twice, both restored to green afterwards:
- Neutralising the emit (early `return` in `_emit_gate_sample`) → **6 tests fail**.
- Letting warmup backfill (`warmup_gate` → `on_long_candle`) → the orchestrator test
  `test_warm_up_does_not_emit_gate_samples_through_the_orchestrator` **fails**.

### Validation
- **407 tests pass** (391 → 407, **+16**): 8 in `test_strategy.py`, 3 in `test_warmup.py`, 5 in
  `test_persistence.py`. Includes `test_gate_sampling_leaves_entry_behaviour_identical` — the
  same candles produce the same entry decision, same confidence total and same state with and
  without the sink — and `test_gate_sample_attributes_a_shut_gate_to_slope_not_ordering`, a
  regression built on today's real QQQ shape.
- `bot.preflight` **RESULT: OK** (1 expected WARN: session closed). Schema **12 → 14 batches**.
- Live DB verified: `dbo.market_gate` created with 11 columns, `UX_market_gate_candle` present
  and `is_unique = True`; **268 trades and 53 refusals preserved.**

### Live validation (same evening, not deferred)
Confirmed on the running service, not just in tests:
- Restart at **20:15:12 UTC** replayed ~390 historical QQQ gate bars through warmup →
  `dbo.market_gate` stayed at **0 rows**. The backfill guard holds in production.
- The first **live** closed gate candle wrote exactly one row at 20:20:31 UTC:
  `QQQ · 2026-08-20 20:15 · gate_open=False · stacked=False · fast_rising=False ·
  close 710.38 · EMAs 710.627 / 710.678 / 711.028`. The ribbon is inverted
  (fast < mid < slow), so `stacked=False` is correct and the gate was still shut —
  consistent with the whole session.
- `ActiveEnterTimestamp` **20:15:12** postdates the file mtimes (**20:12:04**), so the running
  process carries this code — the check the 08-14 weekly made standing after IMP-028.

### What to check tomorrow
`dbo.market_gate` should hold **~70–78 rows** for 08-21 covering the whole session, with **no
rows predating the restart** (the warmup-backfill guard) and **no duplicate
(symbol, candle_start_utc)** pairs. The duty-cycle query:

```sql
SELECT CAST(candle_start_utc AS DATE) d,
       SUM(CASE WHEN gate_open = 1 THEN 1 ELSE 0 END) AS open_bars,
       COUNT(*) AS bars,
       100.0 * SUM(CASE WHEN gate_open = 1 THEN 1 ELSE 0 END) / COUNT(*) AS duty_pct
FROM dbo.market_gate
WHERE CAST(candle_start_utc AS TIME) >= '14:00' AND CAST(candle_start_utc AS TIME) < '19:45'
GROUP BY CAST(candle_start_utc AS DATE) ORDER BY d;
```

Baseline to compare against, reconstructed from Alpaca bars over 24 sessions (08-20 review):
**31.6% overall**, bimodal — 13 of 24 sessions ≤10% open, 7 of 24 ≥60%. If the bot's own
tick-built number diverges materially from that proxy, the proxy is what was wrong, and every
prior gate study built on aggregated bars needs re-reading.

- **Observed effect:** ✅ **VALIDATED (weekly 08-21) on its first full session.** All four checks
  passed: **87 rows** on 08-21, **0 duplicate `(symbol, candle_start_utc)` pairs**, first row at
  **12:15 UTC against an 11:38 restart** — so the warmup backfill guard (the trap this change was
  built around) **held in production**. Duty cycle **34/69 entry-window bars = 49.3%**, which does
  **not** diverge materially from the 31.6% reconstructed proxy given the bimodal distribution, so
  no prior gate study needs re-reading. **Immediate payoff on the day it went live: it killed a lazy
  explanation.** Friday's zero-trade session had an obvious story — *"the gate was shut again"*, true
  on 08-18 and 08-20 — and the telemetry refuted it outright: the bot was permitted to be long for
  **half the session** and still found nothing worth buying. The binding constraint was signal
  strength on a 0.89%-range tape, not the gate. **The gate finally has a denominator.**

---

## IMP-033 — 2026-08-21 (daily) — make refused candidates measurable: `bot.report --refusals`

**Status: SHIPPED & LIVE. Instrumentation only — zero change to the trading path.**

### Problem
`dbo.entry_refusals` has recorded every scored-but-rejected candidate since **IMP-030**, with the
market-gate state since **IMP-031** and the pre-entry tape context since **IMP-029**. It records the
*decision* and the *features it was made on*. It has never recorded the **outcome**. So a refusal row
can prove that we did not trade; it cannot say whether the filter **saved money or cost it** — which
is the only question that matters about a filter.

The consequence is concrete and repeating: that number has now been **rebuilt by hand two reviews
running** — 08-20's *"MU 14:20, confidence 89.1, ran +1.56% to the flatten, stopped by the gate
alone"*, and tonight's session, which would have required the same manual reconstruction across 23
candidates. **This is exactly the failure mode IMP-025 was written to end for excursion**, and its
argument transfers verbatim: *an analysis that is redone by hand every night is one that will
eventually be skipped on the night it matters.*

It also unblocks the thing the **08-14 weekly named "the one measurement that matters"** — a pre-entry
discriminator for the `<0.5%`-MFE cohort. That study was starved of sample on 266 lifetime trades
(and, per the same weekly, *every live-history bucket study over 45+ days is contaminated by
pre-IMP-021 trades*). **Refusals accrue at ~25/day** — 26 / 27 / 23 on 08-19/20/21 — reaching n≈75 in
three sessions. This is the fastest available path to the sample size the shipping freeze is waiting on.

### Freeze compliance
The 08-14 weekly's freeze permits **correctness, data-integrity and instrumentation only**. This is
instrumentation: a read-only report path plus a read-only store method. It touches **no** entry, exit,
sizing or risk logic, and changes no configuration. `MARKET_FILTER_SYMBOL`, `MIN_CROSSOVER`,
`STOP_LOSS`, `TRAIL_PERCENT`, `ENTRY_THRESHOLD` and the confidence weights are untouched.

### Change (4 files, no behavioural surface)
- **`bot/refusals.py` (new)** — the study. `classify_reason` buckets the free-text reason to the filter
  that produced it (the string embeds its own numbers, so grouping needs the filter's identity);
  unrecognised reasons stay visible as `other` rather than folding into a neighbouring cohort.
  `session_flatten_utc` computes the horizon through **`America/New_York`**, not a fixed offset — a
  hardcoded `19:45Z` is right in August and **an hour wrong every winter session**. `outcomes_for`
  reuses **`bot.excursion.compute_excursion`** so the MFE/MAE arithmetic and the bucket edges are the
  same ones every prior study used. Bars come from `cfg.alpaca_data_feed` (IEX) for IMP-025's reason:
  scoring a declined candidate on a richer tape than the bot trades would overstate what was reachable.
- **`bot/persistence.py`** — `RefusedCandidate` + `TradeStore.refusals(days)`, read-only and wrapped
  **exactly** like `closed_trades` (DB error → log, reset, return `[]`). Every field except symbol and
  candle may be `None`: these rows span three schema generations and **"not measured" must stay
  distinguishable from zero**, the same rule IMP-029 set for the tape columns.
- **`bot/report.py`** — `--refusals` flag. Opt-in (one bars call per refusal) and **stdout only**, so
  the Telegram digest stays the short headline it has always been. `refusal_report()` catches
  everything: a reporting extra must degrade, never break the report.
- **`tests/test_refusals.py` (new)** + 3 tests in `tests/test_persistence.py`.

### The counterfactual, and its honesty guard
Enter at the refusal candle's close, hold to that session's flatten (the bot never holds overnight).
**This is an upper bound and the report says so in its own footer**, for three reasons: passing one
filter only advances a candidate **to the next one** (a loosened crossover floor does not buy the
trade, it sends it to the gate); the trail and stop would have exited many before the flatten; and
capital is finite. `reached_trail` and `stopped_out` are printed for exactly that reason — **a cohort
whose MFE never reaches the trail give-back could not have finished green however the filter was set.**
An over-claimed counterfactual is precisely how one talks oneself into loosening a working filter.

### First result (2026-08-21, n=23) — and it vindicates two frozen parameters
```
cohort        n   avgMFE   avgMAE   avgFwd  <0.5%MFE  hitTrail  stopped
crossover    12   +0.36%   -0.53%   -0.06%    8/12      0/12     0/12
confidence    8   +0.11%   -0.61%   -0.35%    8/8       0/8      0/8
gate          3   +1.67%   -0.70%   +0.75%    1/3       2/3      0/3
ALL          23   +0.45%   -0.58%   -0.05%   17/23      2/23     0/23
```
- **`ENTRY_THRESHOLD = 60`: 8 of 8 sub-60 candidates never traded 0.5% above entry, 0 of 8 reached the
  trail, cohort forward return −0.35%.** Perfectly discriminating today.
- **`MIN_CROSSOVER = 0.25`: 0 of 12 could have finished green on the trail; cohort forward −0.06%.**
  An independent, live, outcome-scored corroboration of the **08-13 four-window refutation** of
  lowering it. Two separate methods now agree — this parameter should stop being re-litigated.
- **The gate declined the only two runners** (PLTR +2.62%, TSLA +2.05% MFE). **Deliberately not acted
  on:** n=3 tonight plus n=1 on 08-20, against four independent windows of profitability evidence and
  a 10-day counterfactual of +$37.68 with vs −$53.84 without. Evidence to accumulate, not a change.

### Lead handed to the weekly (do NOT ship on it yet)
The refusal table sorts **almost monotonically by `ribbon_spread_pct`**. Spread ≥ 0.11 (n=2) → MFE
**+2.62% / +2.05%**; spread ≤ 0.029 (n=21) → mean MFE **+0.30%**. That is the shape of the pre-entry
proxy for the `<0.5%`-MFE cohort the weekly asked for, and unlike MAE it is **known before the entry**.
**Disqualifying caveats: spread and gate-state are confounded in this sample** (both wide-spread names
are the two the gate refused), and **n=2**. Requires ≥3 agreeing windows via the harness.

### Non-vacuity
Verified twice, both restored to green afterwards:
- Collapsing `classify_reason` to a single cohort → **3 tests fail**.
- Replacing the DST-correct horizon with a fixed `Etc/GMT+4` offset →
  `test_session_flatten_follows_dst_rather_than_a_fixed_offset` **fails**.

### Validation
- **431 tests pass** (407 → 431, **+24**): 21 in `test_refusals.py`, 3 in `test_persistence.py`. The
  fixtures are **today's real rows** (`entry_refusals` ids 55 / 62 / 75), so the session that motivated
  the tool regression-tests it. Covers: skip-don't-zero for a symbol the tape did not print, skip a
  refusal at/after its own flatten, one failing fetch loses one row not the table, MFE clamped at 0 for
  a candidate that never traded above entry, and `None` tape context surviving from pre-IMP-029 rows.
- `bot.preflight` **RESULT: OK** (1 expected WARN: session closed). Schema unchanged at 14 batches —
  this change reads, it does not migrate.
- Ran live against the real DB: 23 refusals scored, **0 skipped**.

### Live validation (same evening, not deferred)
Per the 08-14 weekly's standing rule — *no IMP entry may be written in the past tense until `git log`
shows the commit AND `ActiveEnterTimestamp` post-dates the file mtime.* Both confirmed:
- `git log` / `origin/main` → **733c110** (pushed).
- `ActiveEnterTimestamp` **20:11:58 UTC** post-dates every touched file's mtime
  (`persistence.py` 20:05:32, `report.py` 20:07:10, `refusals.py` 20:08:57). **The running process
  carries this code.**
- Clean startup: schema ensured (14 batches, unchanged), 18/18 symbols warmed from history, IEX stream
  subscribed, `NRestarts=0`, no WARNING-or-above. The restart is a no-op for behaviour — the service
  imports `persistence` but never `refusals`, which lives on the report path only — and was performed
  to prove the modified `persistence.py` still boots, not to activate anything.

### What to check next
Run `bot.report --days 7 --refusals` at the weekly. The three questions it can now answer that no
prior review could: (1) does the `crossover` cohort's forward return stay ≤ 0 across a full week, or
was today's wash a narrow-tape artefact; (2) does the `gate` cohort keep out-running the others — and
if it does over ≥3 windows, that is the first real case for revisiting the gate's shape; (3) does
`ribbon_spread_pct` separate the `<0.5%`-MFE cohort once gate-state is controlled for.

- **Observed effect:** ✅ **VALIDATED (weekly 08-21, ~1 hour after it shipped) — load-bearing
  immediately, forward effect still unmeasured.** The weekly ran the prescribed command and it
  answered two of its own three questions on the spot (n=76 over three sessions):

  ```
  cohort        n   avgMFE   avgMAE   avgFwd  <0.5%MFE  hitTrail  stopped
  crossover    38   +0.41%   -0.62%   -0.21%   26/38      2/38     2/38
  confidence   23   +0.40%   -0.47%   -0.18%   16/23      2/23     0/23
  gate         15   +1.08%   -0.94%   +0.28%    7/15      5/15     1/15
  ALL          76   +0.54%   -0.64%   -0.11%   49/76      9/76     3/76
  ```

  **(1) Answered — yes, the crossover cohort's forward return stays ≤ 0 across the full week**
  (−0.21%, 68% dead on arrival vs the 46.6% admitted-trade baseline, 2 of 38 reaching the trail).
  08-21's wash was not a narrow-tape artefact. This is the **fifth** independent refutation of
  lowering `MIN_CROSSOVER`. The confidence bar validated the same way (−0.18%, 70% dead).
  **(2) Answered directionally but NOT acted on — and the weekly recorded why, which matters more
  than the number.** The gate cohort does keep out-running the others on every metric. But the
  weekly ruled the table **cannot settle the gate question in either direction**, because a refusal
  is only logged when a candidate already scored: **the table prices the gate's misses and is
  structurally blind to its saves** (the sessions the gate protects produce few or no scored
  candidates and so contribute almost nothing to it). A positive forward return in the gate cohort
  is therefore what a *profitable* gate would also produce. Same conditioning error IMP-031 exposed
  in the 08-14 weekly's "5% of refusals" metric. **Net P&L in replay, gate ON vs OFF, remains the
  only measure that captures both sides — and it favours the gate 4 windows to 0.**
  **(3) Still open** — `ribbon_spread_pct` remains confounded with gate state at n=2. Needs ≥3
  windows with gate state controlled.
  **Caveat honoured:** the tool's own `UPPER BOUND` warning is doing real work — 9 of 76 would have
  hit the 1.25% trail before the flatten, so `avgFwd` overstates what any of these cohorts would
  actually have banked.

---

## Weekly review note — 2026-08-21 (weekly): NO CODE CHANGE SHIPPED

**The 08-21 weekly review shipped nothing, deliberately.** Recorded here so the numbering is
unambiguous and the next routine does not go looking for an IMP-034 that does not exist.

Three independent reasons, any one sufficient:
1. **The daily review already shipped tonight.** IMP-033 committed `733c110` at **20:11:52 UTC** and
   restarted the service at **20:11:58**. The weekly launched at **21:00 UTC**. Two strategy changes
   in one evening — the second untested against the first — is precisely the thrash the weekly
   routine exists to prevent. The handoff discipline runs both directions.
2. **Schedule slip.** The weekly is specified to run Fri 20:00 UTC with a hard no-new-code deadline
   at 20:35. It launched at **21:00**, already past that deadline before any evidence was gathered.
3. **Neither open candidate is ready.** Both the RSI-constant re-fit and the `ribbon_spread_pct`
   filter require ≥3 agreeing replay windows, which could not be run properly in the remaining time.
   Shipping either on this week's evidence alone would be exactly the overfit the freeze prevents.

**Analysis-only was the correct outcome, not a shortfall.** The week's substantive contributions were
(a) settling `MIN_CROSSOVER` and `ENTRY_THRESHOLD` on live outcomes at n=76, (b) refuting the
tempting gate change with a structural argument rather than a bigger sample, and (c) naming the
frequency collapse (45 → 2 trades/week over seven weeks) as the project's new binding constraint.
**Next number to use is IMP-034.** The weekly's recommendation for it is an **in-repo earnings
blackout** the bot owns itself — see `memory/weekly-review.md`, week ending 2026-08-21.

---

## IMP-034 — 2026-08-24 (daily) — stop paying for volume: `conf_volume` weight 15 → 0

### The problem
The confidence score is supposed to *rank* setups. Audited against 268 live trades, it
mostly does not — and one of its five components ranks them **backwards**.

**Dead weight.** Two of the five sub-scores are near-constant for any candidate that
reaches scoring:

| sub-score | ==1.00 | mean | effect |
|---|---|---|---|
| `conf_rsi` (20 pts) | 252/268 | 0.979 | ~19.6 pts handed to everyone |
| `conf_volatility` (15 pts) | 174/268 | 0.958 | ~14.4 pts handed to everyone |

So **~34 of 100 points are a constant subsidy**, and `ENTRY_THRESHOLD = 60` is in truth
asking for ~26 of the ~65 points that actually vary. The same pattern holds on the 108
refusals recorded since IMP-030 (`conf_rsi` 1.00 on 105, `conf_volatility` on 100).

**Inverted weight.** `conf_volume` is not inert — it varies widely (139 distinct values
over 268 trades) — and it is **anti-correlated with P&L**:

| `conf_volume` band | n | win % | total P&L |
|---|---|---|---|
| **1.00 (full marks)** | **79** | 44.3% | **−$377.93** |
| <1.00 | 23 | 56.5% | +$140.50 |
| <0.75 | 32 | 46.9% | +$60.48 |
| <0.50 | 43 | 53.5% | +$74.06 |
| <0.25 | 40 | 35.0% | −$96.31 |
| **0.00 (zero marks)** | **51** | 43.1% | **+$185.99** |

The band the scorer rewards most is the **worst band by a factor of two**, and the band
it punishes most is the best. It reproduces on the post-IMP-021 window (1.00 band the
only negative one). First observed 2026-08-17 and carried on the weekly's
do-not-relitigate list as *"`conf_volume` — inverted"*; **acting on it is the follow-through,
not a re-litigation.**

**Why it is inverted, mechanically:** heavy volume on a *1-minute ribbon cross* means the
move is already being chased. That is IMP-017's finding — this bot's entire lifetime loss
was concentrated in buying moves that had already happened — restated in a sub-score.

### The change
`bot/signals.py`, `ScoreWeights` defaults only. No entry/exit/sizing/risk path touched.

```
crossover  30.0 → 39.0
trend      20.0 → 26.0
rsi        20.0   (unchanged)
volume     15.0 → 0.0
volatility 15.0   (unchanged)
```

Three deliberate choices:
1. **The sub-score is still computed and still persisted** to `dbo.trades.conf_volume`
   and `dbo.entry_refusals.conf_volume`. Weight 0 stops it paying; it does not stop it
   being measured. The decision stays falsifiable — if the inversion reverses, we will
   see it.
2. **Proportional redistribution** across the two components that discriminate in the
   correct direction, preserving their 3:2 ratio (+9 / +6). This introduces **no new free
   parameter to fit**. The alternative tested (all 15 to crossover) was slightly worse.
3. **Renormalise to 100.** Leaving the weights summing to 85 would have silently turned
   `ENTRY_THRESHOLD = 60` into a 71%-of-maximum bar and cut trading hard — confounding a
   scoring change with a threshold change. Renormalising isolates *which* setups rank
   well and leaves the bar where it is.

### Validation
`bot.replay` over the current 18-name watchlist, gate ON, current config, 4 windows:

| window | baseline | IMP-034 | Δ net | PF |
|---|---|---|---|---|
| 10d | +$3.14 | −$1.78 | **−$4.92** | 1.14 → 0.93 |
| 20d | +$48.28 | **+$94.38** | +$46.10 | 1.30 → 1.57 |
| 30d | +$281.14 | **+$356.08** | +$74.94 | 2.25 → 2.43 |
| 45d | +$370.21 | **+$454.16** | +$83.95 | 2.14 → 2.30 |

**3 of 4 windows improve; the dissenting window holds n=3 trades** and turns on a single
outcome, so it carries no weight. Trade count over 45d goes **48 → 50** — this buys
better selection, not more activity. Win rate 64.6% → 64.0%: judged on payoff and PF, per
IMP-018's standing rule.

A rejected variant is recorded so it is not re-tried: **all 15 points to crossover**
(39/20/20/0/15 → 45/20/20/0/15) gave +$67.32 / +$332.71 / +$434.01 on 20/30/45d — better
than baseline, worse than proportional, and it required inventing a new ratio.

**Tests: 434 pass** (431 → 434, +3 in `tests/test_signals.py`):
- `test_weights_still_sum_to_100` — guards the renormalisation, so a future edit cannot
  silently move the effective threshold.
- `test_volume_subscore_is_reported_but_does_not_move_the_total` — a 2.0× and a 0.1×
  volume candidate, identical otherwise, must score 1.00 / 0.00 on the sub-score and
  **the same total**.
- `test_todays_refused_msft_no_longer_outranks_the_wider_cross` — built on today's real
  pair: MSFT 15:07 scored 71.01 on a narrow cross carried by volume 0.711, while GOOG
  15:09 scored 78.21 on a genuinely wide cross. Volume may no longer buy rank, and a
  wider cross must outrank a narrow-but-heavily-traded one.

`bot.preflight`: Alpaca PASS, SQL Server PASS, Telegram PASS, 1 expected market-closed
warning.

### What to check tomorrow
- **Does the trade population change shape?** Same-ish count, different names. The
  falsifier: if new entries cluster in the `conf_volume ≈ 1.00` band anyway (because
  crossover and volume are correlated on this watchlist), the change is cosmetic — check
  `conf_volume` on the next 10 fills.
- **The confidence bands should start to rank.** `dbo.vw_confidence_outcome` is currently
  non-monotonic and worst at the top (90-100: 3 trades, 0% win, −$144.42). If the score
  is now measuring something real, the top band should stop being the worst. Slow signal —
  needs weeks, not days.
- **Do NOT stack the `conf_rsi` / `conf_volatility` change on top of this yet.** The
  remaining 35 points of dead weight are the obvious next target and are filed in
  `todo.md`, but `conf_rsi` is doing veto work (it reaches 0.0 on overbought ≥70) that a
  naive weight removal would destroy. One scoring change at a time, with live evidence
  between them.

### Not changed, and why
The market gate. Four consecutive sessions of it declining the day's best candidate made
it the obvious target; the weekly's pre-registered ON/OFF test, run tonight on 4 fresh
windows, says **gate ON wins 4 of 4 on net P&L, PF, win rate and avg/trade** (see the
2026-08-24 daily review). Eight agreeing windows now. Untouched.

**Live validation (2026-08-24 20:21 UTC).** Verified, not assumed: `systemctl restart`
→ `is-active` **active**, **MainPID 1654015**, `ActiveEnterTimestamp` **20:21:19 UTC**
against a `bot/signals.py` mtime of **20:17:46 UTC** — the file predates the process, so
the running interpreter loaded the new weights (the deploy-gap check: a "restarted clean"
claim is worthless without it). `DEFAULT_WEIGHTS` in the live tree reads
**crossover=39.0 trend=26.0 rsi=20.0 volume=0.0 volatility=15.0, sum=100.0**. Startup
banner clean: watchlist 18/18, **warmup primed 18/18**, IEX stream subscribed to all 18,
account `PA34DFFLTHRT` reconciled at equity **9089.13** with no open positions,
**NRestarts=0**, **0 WARNING-or-above lines** since start. Files left
`ustradebot:ustradebot`; `.env` untouched.

- **Observed effect (weekly 08-28):** ⏳ **mechanism confirmed live, P&L not separable —
  and it never will be.** All **6** of the week's fills scored with `volume` unweighted
  (visible in the 08-26 PLTR entry: `volume 1.0000 (unweighted since IMP-034)`, and in
  08-28 SPOT's `vol=0.00` contributing nothing). The week returned **+$44.85 on 6 trades,
  83% win** — but **IMP-036 landed on the same score two days later**, so every fill from
  08-26 onward carries *both* changes. **There is no clean post-IMP-034 / pre-IMP-036
  cohort and there cannot be one** (08-24 and 08-25 took zero trades). The justification
  stands on the 08-17 inversion finding, not on this week's P&L; **do not cite the week's
  win rate as evidence for this change.** Lesson recorded: two edits to the same scoring
  function inside 48 hours cost the ability to attribute either.

---

## IMP-035 — 2026-08-25 (daily) — report windows are calendar days, not a rolling clock

### Problem
`TradeStore.performance_summary`, `.closed_trades` and `.refusals` each cut their window
at `DATEADD(day, -?, SYSUTCDATETIME())`. That is a rolling N×24h tail ending at **the
instant the query runs**, so the boundary moved with the hour the routine happened to
fire. Same code, same database, different answer by time of day.

Proven against tonight's real `dbo.entry_refusals`, re-anchoring the identical queries:

| `--days N` | anchored 11:30 UTC (pre-market slot) | anchored 20:00 UTC (post-close) | true calendar |
|---|---|---|---|
| 1 | **68** | 36 | **36** |
| 2 | 68 | 68 | 68 |
| 5 | **118** | 91 | **91** |
| 7 | 144 | 144 | 144 |

At the **11:30 UTC pre-market slot, `--days 1` reached back to 10:30 UTC *yesterday***
and swept the previous session's afternoon into "today" — 68 refusals against the day's
true 36. At the 21:10/20:00 UTC post-close slot the same code was correct **by luck**,
because the cutoff landed after the prior session's 20:00 UTC close. That is exactly why
this survived months of nightly use: the routine that reads these numbers most often sits
in the one slot where the bug is invisible, while the **pre-market routine reads a
silently doubled window every morning**.

First spotted 2026-08-24 (item 4: `--days 5` reported n=82 against a true 4-session
population of n=108) and filed to `todo.md` as the leading candidate for the next run.

### Change
- New module-level `_WINDOW_START_SQL = "CAST(DATEADD(day, -(? - 1), SYSUTCDATETIME()) AS DATE)"`
  in `bot/persistence.py`, interpolated into all three readers. **One shared fragment, not
  three copies** — if the three drift, a multi-window study silently compares different
  populations, which is the failure mode this fix exists to remove.
- `-(N - 1)` so `--days 1` = today, `--days 2` = today + yesterday. `--days N` now means
  N calendar days **ending today**, UTC.
- New `_window_days(days)` clamp (`max(1, int(days))`) applied at all three bindings.
  Without it, `days=0` yields `-(0-1) = +1` → a cutoff **one day in the future** → a
  silently empty window. `report._parse_days` already clamped, but the store is called
  directly from tests and the replay harness.
- **No trading logic touched.** Entry, exit, sizing, gate and risk paths are untouched;
  this is read-only reporting.

### Validation
- **442 tests pass** (434 → 442, +8).
- New coverage in `tests/test_persistence.py`:
  - `test_all_windowed_readers_cut_on_a_calendar_date` — parametrized over all three
    readers; asserts the calendar form is present **and** the old rolling form is absent,
    and that exactly one statement carries the window.
  - `test_days_one_means_today_regardless_of_the_hour_the_routine_fires` — the real
    2026-08-25 scenario as a regression: a 08-24 15:22 candle and the 08-25 14:04 UBER
    candle, asserting the old form includes yesterday at the 11:30 anchor and excludes it
    at 21:10, while the new form gives the same answer at both.
  - `test_days_n_spans_n_calendar_days_inclusive_of_today`, and a clamp test over
    `days ∈ {0, -1, -99}` that also asserts a valid window is **not** widened.
  - `_ClosedTradesConn` now records **every** statement (`performance_summary` issues
    three, so asserting on the last one alone would have missed the windowed query).
- **Non-vacuity verified**: reverting `_WINDOW_START_SQL` to the rolling form fails all
  three reader tests.
- `bot.preflight`: Alpaca PASS, SQL Server PASS, Telegram PASS, 1 expected market-closed
  warning.
- **Live DB after the fix**: `--days 1/2/5/7` → **36 / 68 / 91 / 144**, matching the
  calendar column above and now stable at any run hour.
- Deployed: committed `09b7acb`, pushed to `origin/main`, `systemctl restart` at
  20:10:45 UTC → **active**, warmup primed **19/19**, clean startup, no warnings.

### Why this, on a sixth consecutive zero-trade session
The two changes today's refusal data superficially argues for are both already refuted:
the market gate is closed by 8 agreeing windows (08-24) and the `MIN_CROSSOVER` floor by
7 confirmations (its 7-day cohort is n=67, avgFwd **−0.11%**, 3/67 reaching the trail).
Shipping either would be thrash. Meanwhile the **next** real strategy change — freeing
the 35 near-constant `conf_rsi`/`conf_volatility` points, which tonight's 36/36 readings
confirm for the third session — is a **multi-window replay study**, and its windows were
not reproducible until tonight. Fix the instrument, then run the experiment.

### Follow-ups
- Every "last N days" figure in the review history **written from a non-21:10 slot is
  suspect**, including the pre-market routine's daily reads. Do not retro-correct the
  archive; treat pre-08-25 windowed counts as approximate.
- Filed to `todo.md`: `MIN_CROSSOVER` and `ENTRY_THRESHOLD` may now be largely redundant
  (16 of 36 refusals tonight cleared confidence ≥ 60 and died on the crossover floor,
  which follows from IMP-034 raising crossover to 39 of the 65 live discriminating
  points). Measure **after** the rsi/volatility change, which moves those weights.

- **Observed effect (weekly 08-28):** ✅ **VALIDATED — cross-checked against an independent
  query tonight.** This weekly ran `bot.report --days 7` from the **21:00 UTC** slot (not
  the 21:10 one the old rolling window happened to suit) and got **6 trades / +$44.85**;
  an independent hand-written `WHERE exit_time_utc >= '2026-08-24'` query returned **the
  same 6 rows and the same +$44.85 to the cent.** Under the pre-IMP-035 rolling
  `DATEADD(day,-7,SYSUTCDATETIME())` the same call would have silently clipped the Monday
  boundary. **This is the first review whose headline stat needed no manual window
  correction** — the change paid off exactly where predicted, at a non-21:10 hour.

---

## IMP-036 — 2026-08-26 (daily) — the volatility sub-score was sign-inverted: score range availability, not quietness

### The problem
`score_volatility` was written as a **spread proxy**. Its own docstring said so: *"the
IEX trade feed gives us no bid/ask spread to measure directly"*, so it used ATR/close as
a stand-in and scored **tight = 1.0, spiky = 0.0** (`_ATR_GOOD = 0.20%`,
`_ATR_BAD = 1.00%`).

A cost control was thereby wired in as a **ranking** term. On a bot whose entire exit
structure is a **1.25% trail, a 2% stop and a 10% target**, it handed 15 of 100 points
to exactly the tape that cannot reach any of them.

It also never worked as the spread guard it was meant to be: on a **1-minute** candle,
ATR/close for these names runs 0.02%–0.15%, so the score sat pinned at **1.00 for
175 of 269 trades** and could only reach 0.0 at a 1-min ATR of 1% of price, which never
happens. It was simultaneously a dead constant for most candidates and an *inverted*
discriminator for the rest.

**Two independent populations agree on the direction and on the breakpoint.**

**(1) 269 closed trades — real P&L, real fills.** Split at the old saturation point:

| 1-min ATR/close | n | win % | net P&L | median % | trimmed |
|---|---|---|---|---|---|
| **≤ 0.20% ("full marks")** | **175** | 46% | **−$253.62** | **−0.069%** | −$270.45 |
| > 0.20% | 94 | 46% | **+$245.68** | −0.035% | +$200.72 |

Restricted to the live regime (entries ≥ 10:00 ET, post-IMP-017): dead **n=161,
−$328.91** against live **n=67, +$728.32**. The dead band is negative on the **median**
and **after trimming the extremes** in every era cut (all-time, ≥07-25, ≥08-05), so no
single blowup carries the sign. Its raw dollar loss *is* July-concentrated
(Jun −$0.97 / Jul −$258.03 / Aug +$5.38) — which is why the median and trimmed columns
are the ones this rests on, not the total.

**(2) 191 refused candidates over 8 sessions — never traded**, so no P&L, no sizing,
no capital confound. Scored against their own forward tape via `bot.refusals`:

| 1-min ATR/close | n | avg MFE | avg fwd | hit trail |
|---|---|---|---|---|
| ≤ 0.05% | 37 | +0.182% | −0.075% | 0/37 |
| 0.05 – 0.10% | 92 | +0.353% | −0.053% | 2/92 |
| 0.10 – 0.20% | 51 | +0.680% | −0.069% | 6/51 |
| 0.20 – 0.30% | 8 | +1.197% | **+0.738%** | 3/8 |
| > 0.30% | 3 | +1.695% | **+1.305%** | 3/3 |

**MFE rises monotonically across all five bands** and the trail-reach rate goes
**0% → 2% → 12% → 38% → 100%**. That is the mechanism stated directly: the 1-min ATR
predicts how far the tape will travel, and every exit this bot owns needs travel.

**Today's single trade is the archetype.** PLTR 18:34, entry ATR **0.090%** — deep dead
tape — scored 65.82 with volatility at full marks, then did what **77%** of that cohort
does (against 45% of the rest): drifted to the flatten for **+0.27%**, MFE +0.660%, the
1.25% trail never arming. PLTR itself ran **+4.10% on a 5.54% range** that day. The bot
took the flat part of the best mover on the board.

### The change
`bot/signals.py` only. Anchors **reversed, not re-fitted**:

```
_ATR_GOOD = 0.0020  ->  _ATR_DEAD = 0.0020   # <= this -> 0.0 (was 1.0)
_ATR_BAD  = 0.0100  ->  _ATR_LIVE = 0.0030   # >= this -> 1.0 (was 0.0)
```

Four deliberate choices:
1. **The dead anchor is the incumbent constant.** 0.20% is where the old score
   saturated *and* where the sign flips in both populations. It is not a fitted
   parameter — I reused the number already in the file.
2. **Kept as a ranking term at 15 points, not promoted to a veto.** A dead-tape
   candidate must now earn the full `ENTRY_THRESHOLD` from crossover + trend + rsi
   alone. On the live-regime population the soft form beat the hard veto on every
   window (**n=69 / 61% win / PF 3.18** vs **n=67 / 55% / PF 2.57**), because the 11
   dead-tape setups strong enough to clear the bar anyway made **+$28.77** while the
   150 it declined lost **−$357.68**.
3. **No weight change and no threshold change.** Exactly one thing moves. (This also
   sidesteps the trap that killed the naive version of the `conf_rsi` plan — see
   "What this refutes".)
4. **No taper above `_ATR_LIVE`.** The highest observed band (0.40–1.00%) was the best
   performer (n=10, 70% win, +$235.22), so there is no evidence for one, and the 2% stop
   already bounds a single over-lively name. Slippage control belongs to the watchlist
   liquidity floor, which is enforced and clean.

Sensitivity is a **plateau, not a knife-edge**. Upper anchor 0.25 / 0.30 / 0.35 / 0.40 /
0.50% → net +$830 / +$886 / +$802 / +$791 / +$731, win 58–61%, PF 2.79–3.18. Dead anchor
0.10 / 0.15 / **0.20** / 0.25% → +$681 / +$773 / **+$886** / +$662.

### Validation
- **444 tests pass** (441 → 444, +3), full suite, no regressions.
- New coverage in `tests/test_signals.py`:
  - `test_volatility_dead_tape_low_live_tape_high` — the reversed endpoints.
  - `test_volatility_is_monotone_non_decreasing_in_atr` — guards the **sign** across
    ten ratios rather than any single value, so a future "restore tight-is-good" edit
    cannot pass silently.
  - `test_pltr_2026_08_26_dead_tape_entry_no_longer_clears_the_bar` — **today's real
    trade as the motivating regression**: recorded sub-scores reproduce 65.82, and the
    same candle now scores 50.82 against a 60 bar.
- **Non-vacuity verified**: monkeypatching `score_volatility` back to the old ramp fails
  **all three** new tests (exit code 1, captured).
- **Fixture recalibration, disclosed:** 10 fixtures across `test_signals.py` and
  `test_strategy.py` used `atr=0.1`/`0.2` to mean *"a healthy candidate"*, which under
  the new semantics is a dead tape. They were moved to `atr=0.35` (a live tape) so each
  test still exercises the filter it was written for; `test_entry_candidate_below_
  threshold_does_not_enter` went the other way (1.5 → 0.1), since the weak-confirmation
  ATR is now the quiet one. **No assertion was weakened.**
- **`bot.replay`, current config, gate ON, six windows — baseline → IMP-036:**

| window | n | net | win % | PF | avg/trade |
|---|---|---|---|---|---|
| 10d | 7 → **2** | −35.23 → **−10.76** | 42.9 → **50.0** | 0.48 → **0.59** | −5.03 → −5.38 |
| 20d | 23 → **9** | +129.54 → **+81.39** | 60.9 → **77.8** | 1.89 → **2.82** | +5.63 → **+9.04** |
| 30d | 44 → **23** | +341.54 → **+302.61** | 61.4 → **65.2** | 2.22 → **3.10** | +7.76 → **+13.16** |
| 45d | 56 → **30** | +434.15 → **+367.51** | 62.5 → **66.7** | 2.12 → **2.97** | +7.75 → **+12.25** |
| 60d | 86 → **47** | +617.95 → **+512.31** | 55.8 → **57.4** | 1.96 → **2.52** | +7.19 → **+10.90** |
| 90d | 129 → **72** | +710.74 → **+633.78** | 56.6 → **59.7** | 1.69 → **2.09** | +5.51 → **+8.80** |

- `bot.preflight` not required (no connectivity/config surface touched); pure function.

### ⚠️ The honest cost, stated up front
**Replay net dollars FALL in 5 of 6 windows** (−4% to −12%; 90d +$710.74 → +$633.78) and
**trade count drops ~44%**. Win rate, profit factor and per-trade P&L rise in **every**
window, the last by roughly 60%.

I shipped it anyway, and the reason is a measurable reconciliation rather than a
preference. Over 90d the replay's removed cohort is worth **+$76.96 across 57 trades =
+$1.35/trade**. The *same cohort in the live record* is worth **−$2.04/trade** across 161
live-regime fills. That gap is execution: idealized fills flatter small moves on quiet
tape most, because there the entire "profit" is a few cents per share. A +$1.35/trade
simulated edge does not survive the sim-to-live gap; a PF of 1.69 → 2.09 does.

Second reason: the live book's all-time net is **−$7.93 over 269 trades**. A simulated
PF of 1.69 has produced **no live edge at all**. Raising per-trade edge ~60% is the thing
most likely to close that gap; adding trade count is not.

**This is falsifiable and I am pre-registering the test.** If over the next ~15 fills the
retained trades do not show both a better win rate and a better per-trade P&L than the
pre-IMP-036 book, **revert it**. `conf_volatility` remains computed and persisted to
`dbo.trades` and `dbo.entry_refusals` on every entry and refusal, so the measurement
needs no new instrumentation.

### What this refutes
- **The 08-25 "free the 35 near-constant points" plan, in its naive form.** Redistribute
  `conf_rsi` + `conf_volatility`'s 35 points proportionally to crossover/trend and hold
  `ENTRY_THRESHOLD` at 60, and today's PLTR entry scores **59.8 against a 60 bar** — the
  only trade of the day, killed for a reason unrelated to its merits. Removing a
  ~constant subsidy while holding the threshold silently moves the effective bar from
  ~38.5% to 60% of the discriminating range. IMP-034's renormalisation logic **does not
  transfer** to a term that sits at full marks. Any future version must be
  threshold-neutral (60 → ~38.5 on a 65-point scale). **Filed to `todo.md`.**
- **"`conf_volatility` is dead weight"** (08-24, 08-25, carried three sessions). Half
  right: it is a constant on the *refusal* population, but across 269 trades it takes
  **94 distinct values** and ranks them **backwards**. It was never inert — it was
  inverted, which is worse, and the near-constancy on refusals hid that.

### Follow-ups
- `conf_rsi` is now the **only** remaining dead-weight term (1.00 on 47/47 refusals
  today, 252/269 trades). Blocked on IMP-036 live fills; must be threshold-neutral.
- **Expect visibly fewer fills from 08-27.** Do not diagnose the lower count as a
  drought or a malfunction — it is this change working. The pre-market routine has been
  warned in today's "Notes for pre-market research".
- Deployed: committed, pushed to `origin/main`, `systemctl restart` — see below.

### Live validation (2026-08-26 20:26 UTC)
- `signals.py` mtime **20:21:13** precedes `ExecMainStartTimestamp` **20:26:27**, so the
  running process (**PID 1811318**) carries the new code — the deploy-gap check, not an
  assumption that "restarted" means "reloaded".
- Constants confirmed in the venv: `_ATR_DEAD=0.0020`, `_ATR_LIVE=0.0030`. The PLTR-like
  dead tape (atr 0.090%) now scores **0.00** where it scored 1.00; a live tape (0.350%)
  scores **1.00** where it scored 0.81.
- Clean boot: `is-active` **active**, schema ensured (14 batches), warmup primed
  **20/20**, broker handshake `PA34DFFLTHRT` equity **$9,094.41**, **no open positions**,
  IEX stream connected and subscribed to all 20 symbols. **Zero WARNING-or-above lines
  since the restart.**
- 444 tests green immediately before the commit. Commits `8f5b655` (IMP-036) and
  `2e6406d` (daily review), pushed to `origin/main`.

- **Observed effect (weekly 08-28):** ⏳ **mechanism operating as designed; P&L claim
  UNPROVEN and this week cannot prove it.** First live session **08-27: 4 fills, 4W,
  +$51.39** — the best session since 08-03. **I decline to credit IMP-036 for it.**
  08-27 was the week's one genuinely trending tape (S&P 500 info-tech **+3.4% on the day**,
  NVDA/CRM/CRWD leading per this week's deep-research recap); a long-only trend system
  taking four winners into that is the regime, not the rescored volatility term. **A change
  that predicts "trade more when range is available" cannot be validated on the one day
  range was abundant — that is the confound, not the confirmation.**
- **The genuinely informative datapoint is the loser, not the winners.** 08-28 SPOT scored
  `vlt=0.00` on `atr_pct` 0.128% — the reversed score **correctly marked the tape dead** —
  and the trade was taken anyway at confidence **63.94**, then lost −$11.82 to a 1.25%
  trail its ATR could never support. **So IMP-036 works and `ENTRY_THRESHOLD=60` overrode
  it.** The volatility term is now honest; the floor beneath it is what admitted the loss.
  Logged as the lead for the entry-floor study (see the 08-28 weekly).
- **Progress against its own gate:** todo.md's 15-fill mechanism test (does IMP-036's
  retained cohort show higher mean MFE?) stands at **6 of 15 fills**, and only **1** of
  those carries `mfe_pct` (IMP-037 shipped 08-27, after three of the four 08-27 entries).
  **Effective progress is 1/15, not 6/15.** Do not revert and do not claim victory before
  that test runs.

---

## IMP-037 — 2026-08-27 (daily) — persist in-trade excursion (MFE/MAE): make capture a column, not a re-derivation

**Status: SHIPPED & LIVE.**

### The problem — the bot cannot measure the metric it now turns on
Every exit decision this bot owns is a give-back decision: a 1.25% trail tightening to
1.0%, a 2% stop, a 10% ceiling, an EOD flatten. The metric that judges all of them is
**capture = realized / MFE**. It was recorded **nowhere**. `dbo.trades` stores where a
trade started and where it ended, and nothing about where it *went*.

The cost of that gap is documented in this very file. **IMP-021 pre-registered a capture
rerun as criterion (b) on 2026-08-03 and it went unmeasured for 24 days**, the 08-07
weekly recording only *"criterion (b) was not rerun"*. Tonight I finally ran it — and it
took a bar re-download over 29 trades and a purpose-built script, for a number the bot
had in memory at the moment of every exit and threw away.

It ran because today handed over the archetype. **NVDA** entered 224.5875, made a
**227.17 high-water close (+1.15%)**, tripped the +1% tighten so the stop moved to
**224.90**, and filled at **+0.14%**. NVDA then ran to **230.47 (+2.62%)**. In
`dbo.trades` that trade is `pnl_pct = +0.1403` — **a win**. Every aggregate the review
routine computes calls it a win. The −$31 of foregone move is invisible.

### The change
Three files, all additive, **no trading logic touched**.

- **`bot/risk.py`** — `RiskManager` carries `_excursion: dict[str, (hi, lo)]`, updated by
  `_track_excursion()` at the **top of `update_trailing_stop`, before its no-key early
  return**, so a position whose stop leg cannot be moved (a startup-reconciled holding) is
  still measured. `_excursion_pct()` pops the state at exit and converts to % of entry;
  `ExitResult` gains `mfe_pct` / `mae_pct`, and the `EXIT` log line now carries them.
- **`bot/persistence.py`** — `record_exit` writes both, guarded
  `mfe_pct = COALESCE(?, mfe_pct)` so a re-recorded exit that has no measurement can never
  blank one already stored. Read via `getattr`, the established optional-field pattern.
- **`sql/schema.sql`** — `mfe_pct` / `mae_pct` `DECIMAL(9,4) NULL`, idempotent
  `IF COL_LENGTH(...) IS NULL ALTER TABLE`, the IMP-029 template.

**Four deliberate choices:**
1. **Measured on CLOSES, not intrabar highs.** The ratchet sets the stop from `close`, so
   a close-based excursion is the move the exit structure could *actually* have banked. An
   intrabar high a close-driven trail can never reach would flatter every capture ratio.
   Stated in the schema comment so no future study silently assumes highs.
2. **Keyed by the position's symbol, not the candle's** — the exit-side pop is handed the
   strategy's symbol, so both sides agree by construction rather than by coincidence.
3. **Seeded at the entry price**, so a trade that only ever goes against us records
   `mfe_pct = 0` (it reached its entry, no more) rather than a misleading negative.
4. **`None`, never `0`, when never managed.** Absence of measurement is not a zero
   excursion. NULL for every trade closed before today; studies must exclude, not
   zero-fill — the same discipline IMP-029's columns carry.

### Validation
- **451 tests pass** (444 → 451, +7), full suite, no regressions.
- New coverage — `tests/test_risk.py` (6): running high/low water (not last close);
  entry-seeding so a pure loser reports mfe 0; `None` when never managed; **measured
  without a movable stop leg** (pins the before-the-early-return ordering); no leak across
  a re-entry of the same symbol; and
  **`test_nvda_2026_08_27_giveback_is_now_measurable`** — today's real fills, asserting
  `mfe_pct ≈ 1.15` and **capture < 15%**, so the failure that motivated this is now a
  regression test. `tests/test_persistence.py` (1): both columns reach the row and the
  COALESCE guard is present.
- **Non-vacuity verified**: neutering `_track_excursion` fails **5 of the 6** new risk
  tests (captured). The 6th is the `None`-when-never-managed case, which *should* still
  pass — it asserts absence.
- **Two legacy exact-tuple param pins updated, disclosed**: `test_record_exit_closes_
  trade_with_pnl_and_drops_position` and `test_record_exit_corrects_entry_price_from_
  delayed_fill` gain `None, None` before the symbol. **No assertion weakened** — they pin
  more of the statement than before.
- **Schema applied live and verified**, not assumed: `sys.dm_exec_describe_first_result_set`
  reports `mfe_pct decimal(9,4)`, `mae_pct decimal(9,4)` on `dbo.trades`.
- **`bot.preflight`: OK, 1 expected warning** — Alpaca ACTIVE (equity $9,145.73), SQL
  Server connected + schema ensured (16 batches), Telegram delivered.
- Replay not re-run for validation: this change is observational and cannot move a fill.

### Why this and not the trail retune
Tonight's sharper *trading* finding is that `TRAIL_TIGHTEN_AFTER` == `TRAIL_PERCENT_TIGHT`
== 1.0% makes the profit lock bank **exactly zero**. I built the experiment
(6 windows × 7 variants) rather than asserting it, and **did not ship the result**:
- Reverting IMP-021 to a flat 1.25% trail **loses in 5 of 6 windows**, refuting a live
  29-trade counterfactual that had favoured it by $48 — that gap was **two trades**. The
  ≥3-window rule earned its keep tonight.
- `TIGHTEN_AFTER 1.5% / TIGHT 1.0%` beats shipped in **6/6 windows on net**, but on a
  **worse PF** (90d 2.42 vs 2.44) and a **9pp worse win rate**, with a 90-day margin of
  **+0.5%** — inside noise.
- Decisive reason: **IMP-036 is 4 fills into a pre-registered 15-fill revert test.** A
  second exit-structure change now would confound it. Filed to `todo.md` as the leading
  candidate once that test completes.

Meanwhile the capture table says the exit structure is **no longer the binding
constraint** (45% / 65% capture in the winning buckets); **48% of trades with MFE < 1%
carry the entire −$122 loss**. That is an entry-selectivity problem — IMP-036's target.
Instrument first, then run the experiment (the IMP-035 precedent).

### Pre-registered use
From tomorrow, `dbo.trades` answers **without a bar download**: capture by exit reason;
whether IMP-036's retained trades have higher MFE than the pre-IMP-036 book (the direct
test of its stated mechanism — *"1-min ATR predicts how far the tape will travel"*, so far
supported only on refusals, never on fills); and the MFE<1% population that now holds all
the loss. **If, once ~15 post-IMP-037 trades exist, IMP-036's fills do not show higher
mean MFE than the pre-IMP-036 book, IMP-036's mechanism is not doing what it claims** —
and that is a revert argument independent of P&L.

### Known gap this does NOT fix (filed to `todo.md`)
`exit_reason` is unreliable for attribution. Today **PLTR's own EOD market close**
(submitted 19:45:27, filled 19:45:34.82) was checked **0.6 s early** at 19:45:34.25,
declared a failed close, and re-found by `reconcile_exit` — which tagged the bot's own
order `end-of-day flatten (stop/target filled broker-side)`. P&L is correct, the label is
not, and it means "trail hit" cannot be separated from "EOD flatten" in SQL. Tonight's
analysis used price arithmetic instead.

### Follow-ups
- `conf_rsi` remains the last dead-weight term (1.00 on 4/4 today, ~256/273 all-time).
  Still blocked on IMP-036 fills; still must be threshold-neutral.
- The 14:00–14:15 UTC entry cluster is **41% of entries and +$180 of +$193** — protect it;
  do not "spread out" entries without evidence.
- Deployed: committed, pushed to `origin/main`, `systemctl restart` — see below.

### Live validation (2026-08-27 20:25 UTC)
- **Deploy-gap check, not an assumption**: `bot/risk.py` mtime **20:20:43** precedes
  `ExecMainStartTimestamp` **20:24:55**, so the running process (**PID 1898233**) carries
  the new code. Confirmed in the venv: `ExitResult` fields are
  `[symbol, reason, exit_price, qty, order_id, entry_fill_price, mfe_pct, mae_pct]`.
- Clean boot: `is-active` **active**, **NRestarts=0**, schema ensured (**16 batches** — the
  two new `ALTER`s), warmup primed **20/20**, broker handshake `PA34DFFLTHRT` equity
  **$9,145.73** with **no open positions**, IEX stream subscribed to all 20 symbols.
  **Zero WARNING-or-above lines since the restart.**
- 451 tests green immediately before the commit; `bot.preflight` OK with the expected
  market-closed warning. Commit `60b62c3`, pushed to `origin/main`.
- **First rows land tomorrow (2026-08-28).** Every trade closed before today is NULL by
  design.

- **Observed effect (weekly 08-28):** ✅ **mechanism VALIDATED on n=1; sample is the
  limitation, not the code.** Exactly one row exists — **SPOT, MFE +0.54% / MAE −0.69%**
  against a realised **−0.72%** — and it is immediately load-bearing: it is the evidence
  that the 1.25% trail asked for **2.3× more favourable excursion than the trade ever
  produced**, which is the cleanest statement of that failure shape the project has. The
  other 5 fills this week closed before the column existed and are NULL by design.
  **Consequence to respect: the trail-retune and the IMP-036 mechanism test both need ~15
  excursion rows and currently have 1.** At this week's rate (6 fills/wk) that is ~2–3
  weeks away — which makes fill frequency, not instrumentation, the binding constraint on
  every queued exit question.

---

## IMP-038 — 2026-08-28 (daily) — name the leg that actually filled: split the broker-side exit catch-all

### The defect
Every exit that filled broker-side booked one string, **`stop/target filled broker-side`**,
which conflates four different outcomes: a **trail hit**, the original **−2% stop**, the
**take-profit**, and (via the close/fill race still open in `todo.md`) the bot's **own EOD
sell**. The cost is not cosmetic:

| exit_reason (lifetime, 274 trades) | n | net |
|---|---|---|
| `end-of-day flatten` | 178 | **+$1,146.92** |
| `stop/target filled broker-side` | 51 | −$455.18 |
| `end-of-day flatten (stop/target filled broker-side)` | 34 | −$550.21 |
| `trailing stop (stop/target filled broker-side)` | 2 | −$54.69 |

**87 of 274 exits (32%) sat in the ambiguous buckets and they carry −$1,060 — the entire
loss side of the book** — while the one bucket that names the trail read **n=2**.

### Today's proof that n=2 is an undercount
**2026-08-28 SPOT**, the day's only trade. The trail ratcheted **eight times** — 538.65 →
543.47 → 543.63 → 543.96 → 544.12 → 544.22 → 544.50 → **546.05** — Alpaca minting a fresh
order id at each replace. The broker record is unambiguous: order **`8d587433`** (the eighth
link) **filled @546.05**, i.e. **1.37% above the original stop**, while the take-profit leg
`de6910e0` was **cancelled unfilled**. This was the trailing stop and nothing else. The bot
booked it `stop/target filled broker-side`, and the trail took no credit for its own exit.

### Why this and not the trail retune
The sharper *trading* observation today is that a 1.25% trail cannot exit green on a **+0.54%
MFE** — it sits below entry by arithmetic. I did **not** ship that:
- It is **one trade**.
- The trail retune is explicitly **blocked until IMP-036's 15-fill test completes** (today
  was fill ~6). A second exit-structure change now would confound it.
- The retune is supposed to be **"judged on capture, not net dollars"** — and capture *by
  exit reason* was unreadable in SQL precisely because of this defect.

So: **fix the instrument, then run the experiment** — the IMP-035 / IMP-037 precedent.

### The change
`RiskManager._broker_fill_reason(entry, order_id, exit_price)` resolves the filled order
against bookkeeping the manager **already** maintains (`_live_stop_oid` / `_trail_stops`,
both keyed by the trade's original stop-leg id):
- id is anywhere in this trade's stop chain → **`trailing stop`** if the trail had ratcheted
  above the bracket stop, else **`stop loss`**;
- otherwise the fill cleared the take-profit → **`take profit`**;
- anything unplaceable (unknown id, or no entry — a startup-reconciled holding) **keeps the
  honest catch-all**. It never guesses.

Wired into both broker-side paths (`exit_position`'s reconcile fallback and
`reconcile_if_closed`), with de-duplication so the STOP_GONE caller cannot produce
`trailing stop (trailing stop)`. No broker reads, no new state, no behaviour change.

**Also fixed the same blindness in the measurement harness.** `bot/replay.py` was minting a
*synthetic* fill id for simulated stop fills, so the RiskManager could not recognise its own
stop and **every** replay exit would have collapsed into the catch-all — leaving the trail
study blind in the very tool it must run in. The simulator now returns the stop leg's **own**
id (the ratcheted one when the trail has moved), exactly as Alpaca does.

### Validation
- **459 tests pass** (was 451; +8). New coverage is built on the **real 08-28 SPOT trade** —
  the eight-replace ratchet, its `trail-8` fill @546.05, and a P/L assertion that reconciles
  to the broker's **−$11.82** — plus the stop-loss, take-profit, unattributable and
  no-entry branches, and a guard that price/qty/entry-fill are untouched.
- Three pre-existing tests had **incoherent fixtures** the classifier exposed: they narrated
  a "broker-side **stop** fill" while using a fill price **above** the take-profit (113.21 /
  397.13 against a 104.0 target). Corrected to match their own stories rather than
  weakened — they now assert the precise leg.
- **Behaviour-neutrality proven by A/B, not asserted.** Ran `bot.replay --days 90` on a
  `git worktree` at HEAD and on the working tree, **same 20-symbol universe, same window**:

  | | trades | net | win% | PF | avg |
  |---|---|---|---|---|---|
  | HEAD | 78 | +765.50 | 61.5 | 2.39 | +9.81 |
  | IMP-038 | 78 | +765.50 | 61.5 | 2.39 | +9.81 |

  Bucket-for-bucket identical (n=23 / 35 / 20 at −168.59 / +344.68 / +589.41). **Only the
  labels moved.**
- `bot.preflight`: **OK, 1 expected warning** — Alpaca ACTIVE (equity $9,133.71), SQL Server
  connected + schema ensured, Telegram delivered. New labels are strictly **shorter** than
  the ones they replace, so there is no column-truncation risk.

### What it already bought us (first cohorts ever readable)
From the 90-day validation run:
- **All 58 broker-side exits were the trail; ZERO were the −2% bracket stop.** This confirms
  `todo.md`'s "`STOP_LOSS` is a dead knob" with measurement instead of inference.
- **In-session trail exits (`trailing stop`) are n=23 for −$168.59**, while trail fills
  discovered at the close (`end-of-day flatten (trailing stop)`) are **+$344.68** and pure
  EOD flattens **+$589.41**. The trail firing *during* the session is the losing cohort —
  a direct, quantified lead for the retune once IMP-036 unblocks.

### Scheduling note (read this before next Friday)
The `ustradebot-daily-review.md` **"Friday stand-down" rule is stale.** Per the live crontab
and `/root/claude-routines/SCHEDULE.md`, the weekly recap moved to **Sat 04:00 WIB = Fri
21:00 UTC**, which is **one hour AFTER** this routine (Fri 20:00 UTC), not ~70 minutes
before. Checked before shipping: `git log --since="6 hours ago"` was **empty** and no
`(weekly)` entry exists today, so nothing had shipped and the stand-down did not apply.
**The ordering is now reversed, so the risk has flipped: the weekly runs after us and should
stand down when a daily IMP has already shipped that evening.** IMP-038 shipped at ~20:20
UTC tonight. Filed to `todo.md` for the operator.

### Deployed
Committed, pushed to `origin/main`, `systemctl restart` — live validation below.

### Live validation (2026-08-28 20:16:57 UTC)
- **Deploy-gap check, not an assumption**: `bot/risk.py` mtime **20:06:27** and
  `bot/replay.py` **20:09:42** both precede `ExecMainStartTimestamp` **20:16:57**, so the
  running process (**PID 2012055**) carries the new code. Confirmed in the venv:
  `RiskManager._broker_fill_reason` present, labels `trailing stop | stop loss | take profit`.
- Clean boot: `is-active` **active**, **NRestarts=0**, schema ensured (16 batches), warmup
  primed **20/20**, broker handshake `PA34DFFLTHRT` equity **$9,133.71** with **no open
  positions**, IEX stream subscribed to all 20 symbols. **Zero WARNING-or-above lines.**
- 459 tests green immediately before the commit; `bot.preflight` OK with the expected
  market-closed warning. Commit `152908f`, pushed to `origin/main`.
- **First live rows land Monday 2026-08-31.** Every exit recorded before tonight keeps its
  historical label — this is not backfilled, and the old strings stay valid for those rows.

- **Observed effect (weekly 08-28, written ~45 min after it shipped):** ⏳ **zero live rows
  — but it has already produced the most important finding of the week, in replay.** The
  90-day validation split that this change made possible shows **in-session `trailing stop`
  exits n=23 for −$168.59** against **trail fills discovered at the close +$344.68** and
  pure EOD flattens **+$589.41**. **The live week independently agrees in sign**: the 3
  trades that exited intraday netted **−$2.96**, the 3 carried to the bell netted
  **+$47.81**. Two datasets, different mechanisms, same direction. **That is now the
  best-evidenced open question in the project** and it is pre-registered as a falsifiable
  replay test in the 08-28 weekly. Live label validation still owes Monday 08-31.
- **Process note, in this entry's favour:** this change shipped at 20:16 UTC and the weekly
  ran at 21:00 UTC — the reversed ordering this entry itself flagged. **The weekly stood
  down and shipped no code**, so IMP-038 gets a clean, unconfounded first live session on
  Monday. The scheduling hazard was caught by the daily and honoured by the weekly.

---

## IMP-039 — 2026-09-01 (daily) — the bot's own reporting now obeys the stop-exit doctrine

### The problem
The stop-exit doctrine ("a stop is a failed trade whatever the sign of its P&L", standing
user directive 2026-09-01) existed only in the review prompts. Everything the **bot**
printed still scored a win as `pnl > 0`:

```
bot/persistence.py:  SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)   -> PerformanceSummary.wins
bot/report.py:       f"closed trades: {s.trades} · win rate: {s.win_rate * 100:.0f}%"
```

So the Telegram digest, the journal line, and every figure quoted from them into
`memory/` reported a win rate the doctrine says is meaningless. The gap is not academic —
it is the exact mechanism by which a strategy with no edge keeps looking respectable.

**Last three sessions that traded (2026-08-26..28), real `dbo.trades` rows:**

| sym | entry | stop | target | exit | profit_R | P&L | exit_reason |
|---|---|---|---|---|---|---|---|
| PLTR | 177.27 | 173.75 | 195.03 | 177.75 | +0.14R | +$5.28 | end-of-day flatten |
| NVDA | 224.59 | 220.25 | 247.23 | 224.90 | +0.07R | +$3.78 | stop/target filled broker-side |
| TSM | 423.98 | 415.44 | 466.31 | 425.25 | +0.15R | +$5.08 | stop/target filled broker-side |
| TSLA | 351.23 | 344.28 | 386.44 | 354.55 | +0.48R | +$16.60 | end-of-day flatten |
| PLTR | 184.24 | 180.37 | 202.46 | 186.24 | +0.52R | +$25.93 | EOD flatten (broker-side) |
| SPOT | 549.99 | 538.65 | 604.60 | 546.05 | −0.35R | −$11.82 | stop/target filled broker-side |

**5 green of 6 = 83% headline. Zero reached +1R. Doctrine verdict: 0 WIN / 3 SCRATCH /
3 FAIL, true win rate 0%, stop rate 4/6.** All-time the same gap runs 46% headline vs
**7% true** over 274 trades, on an expectancy of **+0.008R/trade**.

### The change
New pure module **`bot/doctrine.py`** (no I/O, mirroring `bot/excursion.py`):

- `risk_per_share()` — 1R from the ORIGINAL bracket stop (`dbo.trades.stop_price`, which
  the broker-side trail never rewrites), falling back to `cfg.stop_loss × entry` only when
  there is no recorded anchor.
- `resolve_reason()` — **attributes the IMP-038 `stop/target filled broker-side` catch-all
  by fill price** instead of dropping it: at/above `target × 0.995` it was the take-profit
  leg, anything short of it was the stop leg. That bucket is 51+34+2 rows carrying
  **−$1,060** all-time, so dropping it would have hidden most of the loss side.
- `classify()` / `summarize()` — WIN (take-profit fill, or `profit_R ≥ +1.0`) /
  SCRATCH (stop-driven `+0.25 < profit_R < +1.0`, or flatten between −0.25R and +1.0R) /
  FAIL (stop-driven `profit_R ≤ +0.25`, or anything below −0.25R), with FAIL split
  **full-stop** (`≤ −0.75R`) vs **BE-scratch**. Carries `pnl` only to expose the headline gap.
- `format_stop_exits()` — the two lines the doctrine requires.

Wiring:
- `ClosedTrade` gains `stop_price` / `target_price` (defaulting to `None`, so rows
  predating the columns stay distinguishable from a genuine zero); `closed_trades()`
  selects them.
- `bot/report.py` gains `stop_exit_summary()` and `format_summary(s, stop_exits)`.
  **Always on** — it reuses the query the excursion study already runs and needs no
  network, unlike opt-in `--mfe`/`--refusals`. It rides the **Telegram digest**, not
  stdout-only: the true win rate governs the verdict, so it must travel beside the
  headline it corrects.

### Why this, and not a strategy change
The doctrine's escalation clause fired today (FAIL+SCRATCH 100% over the last 3 trading
sessions, 92% over 10, 93% all-time) and it says: **stop shipping parameter tweaks.**
Independently, every strategy candidate in `todo.md` is explicitly **blocked** pending
IMP-036's 15-fill test, and only ~6 fills have occurred since 08-26. So:

- It touches **no trading logic** — IMP-036's test stays uncontaminated, no thrash.
- Every number it prints is **harsher** than the one beside it. It cannot be gaming the
  metric; it is the opposite of gaming it.
- It makes the blocked IMP-036 revert test — specified in terms of *"win rate"* —
  resolvable against the **true** rate instead of the misleading one.
- Read-only, zero risk to the trading path.

### Validation
- **483 tests pass** (was 459; +24: 20 in new `tests/test_doctrine.py`, 3 in
  `tests/test_report.py`, 1 in `tests/test_persistence.py`).
- The doctrine tests are built on the **six real rows above**, so the reporting failure
  that motivated this is now a regression test — `test_the_real_book_scores_zero_true_wins_against_an_83pc_headline`
  asserts 0 WIN / 3 SCRATCH / 3 FAIL, 0% true vs 83% headline, stop rate 67%.
- Also covered: catch-all attribution both ways, EOD-labelled catch-alls still counting as
  stop-driven, full-stop vs BE-scratch split, a take-profit below 1R still a WIN, a
  ≥1R trailing stop still a WIN (counted in the stop rate, not a failure), missing-anchor
  fallback, empty windows (no divide-by-zero), and graceful degradation on malformed rows.
- **Live cross-check against the real DB** (notifier bypassed, no spurious Telegram):
  reproduced an independent ad-hoc analysis exactly in all four windows —
  7d `4/6 (67%) · true 0% vs headline 83%`; 30d `23/33 (70%) · true 6% vs 64%`;
  90d `91/274 (33%) · true 7% vs 46%`.
- `python -m bot.preflight`: Alpaca PASS, SQL Server PASS, Telegram PASS, 1 expected
  market-closed WARN.
- Deployed: `systemctl restart`, service active, clean startup.

### What this does NOT do
It does not improve the edge, and it is not claimed to. Tonight's honest finding is
recorded in `memory/daily-review.md` 2026-09-01: **no demonstrated edge** —
+0.008R/trade over 274 trades, 7% true win rate, only 7.3% of trades ever reaching +1R,
and **0 of the last 18 FAILs being full stops** (every one a break-even or scratched
trail — profit capture, not stop geometry). Handed to the weekly review with the
recommendation to test an **entry-signal replacement** rather than another exit tweak.

---

## IMP-040 — 2026-09-02 (daily) — measure entry timing: how much of the move was still on the table

### The problem
Three consecutive flat sessions (08-31, 09-01, 09-02), and on the third the tape
cooperated: the QQQ gate was **open 37.1%** of the session (vs 13.0% and 0.0%), the
indexes closed **+0.5–0.6%**, and the bot still took nothing. Meanwhile the names it was
scoring *moved*: **NVDA traded a 4.34% range** (and was scored 53.69 and 51.66),
**INTC 3.35%**, **LLY 2.58%**.

That contradiction was **unmeasurable with the tooling the bot had.** `--mfe` (IMP-025)
answers "how far did the trade run once we were in?"; `--refusals` (IMP-033) answers "how
far did the ones we declined run?". Neither answers the prior question: **was there
anything to catch, and had we already missed it by the time we committed?**

This matters because "the tape was dead" and "the tape moved and we were late" produce
**identical MFE tables** and have **opposite fixes** — the first says change the universe,
the second says change the signal. The 09-01 review handed the weekly a structural verdict
("no demonstrated edge") without a way to choose between them, and the 08-31 review nearly
spent a session on watchlist liveness. Guessing here is how a review ships a watchlist edit
that was really an entry bug.

### The change
New `bot/timing.py` + a `--timing` flag on `bot.report`. It decomposes each closed trade's
opportunity into a four-rung ladder and reports where it collapses:

1. `session_range_pct` — the whole session's high/low range on that symbol (opportunity
   that existed at all).
2. `available_pct` — entry price to the session high **after** the entry bar (opportunity
   still unspent when we committed). The 1→2 gap is **entry timing**.
3. `mfe_pct` — best unrealised gain over the **holding** window. The 2→3 gap is
   **holding time**.
4. `realized_pct` — what we kept. The 3→4 gap is **profit capture**.

Each rung is also counted against `trail_percent`, since a trade must clear that width to
finish green on the ratchet at all (IMP-018). Plus `entry_percentile` (where in the day's
range the fill sat, 0 = bought the low) and `unspent_share` (rung 2 / rung 1).

The three gaps map one-to-one onto the stop-exit doctrine's three causes.

**Deliberately not a strategy change.** The escalation clause triggered on 09-01 is still
active (FAIL+SCRATCH 100% over the last 3 sessions with trades), which bars parameter
tweaks. This touches **no trading logic**: it is read-only, opt-in, stdout-only, cannot
reach the Telegram digest, and cannot contaminate the blocked IMP-036 / IMP-021 mechanism
tests. Same rationale as IMP-039 — under escalation, the highest-impact change available
is the instrument that makes the structural decision decidable.

Structure mirrors its siblings: arithmetic is **pure** and unit-tested, the only I/O is an
injected session-bar fetcher. Session bounds are derived through `bot.config.EASTERN`
(09:30–16:00 ET) rather than a hardcoded 13:30–20:00 UTC span, so the window does not shift
by an hour across the DST boundary — the IMP-026 lesson, applied up front.

### What it found (274 trades, the whole book)
| rung | median | ≥ 1.25% trail |
|---|---|---|
| 1 session range | **3.38%** | **268/274 (98%)** |
| 2 available at entry | **0.78%** | **90/274 (33%)** |
| 3 MFE while held | 0.70% | 78/274 (28%) |
| 4 realized | −0.04% | — |

Median unspent share **24%**; median entry percentile **71%** of the session range.

- **The universe is not the problem** — rung 1 clears on 98% of trades; these names move a
  median 3.38%, 2.7x the trail width.
- **The book collapses at 1→2 and nowhere else (268 → 90).** Two-thirds of trades are dead
  on arrival: less than the trail width remains when the bot commits.
- **The bot buys the top third of the day's range** (71st percentile). A 1-min fresh cross
  gated by a 5-min stacked ribbon is a *confirmation* signal — it cannot fire until the
  move is already visible on two timeframes.
- **Blackout-bias check:** re-measured rung 1 over only the tradable window (ENTRY_START
  10:00 ET → close) — median 2.80%, **256/274 (93%)** clear the trail, unspent share 31%,
  entry percentile 67%. **The finding survives; it is not an artefact of IMP-017.**

This **re-classifies the dominant failure cause from profit capture (09-01) to entry
quality.** The 18/18 break-even-scratched trails are real but downstream: a trade entered
with 0.78% of room against a 1.25% ratchet *must* end that way.

### Validation
- **500 tests pass** (483 → 500, +17), full suite, no regressions.
- New `tests/test_timing.py`:
  - Ladder arithmetic — `available` excludes range that happened *before* the entry bar;
    the entry bar is inclusive on both windows; MFE stops at the exit while `available`
    does not; favourable excursions clamp at zero; a missing session is dropped, not
    scored flat.
  - `test_session_bounds_follow_eastern_across_the_dst_boundary` — pins 13:30 UTC in EDT
    and 14:30 UTC in EST, so a future edit cannot reintroduce a fixed offset.
  - `test_summarize_uses_medians_not_means` — guards against one >2% runner dragging the
    typical-trade figure.
  - `test_nvda_2026_09_02_wide_range_but_the_signal_caught_the_flat_part` — **today's real
    session as the motivating regression**: the 4.34% range and the 14:55 cross, asserting
    rung 1 clears the trail while the entry sits at the 58th percentile.
  - `test_the_ladder_separates_a_dead_tape_from_a_late_entry` — two rows with **identical
    MFE** that the ladder splits, which is the module's entire reason to exist.
- Ran live against the book to produce the table above (`--days 90 --timing`).
- Service restarted and verified active with a clean startup (no trading-path change, but
  the deploy is verified rather than assumed — the IMP-003 lesson).

### What this hands the weekly (Fri 09-04)
The structural question, now sharply posed and **decidable**: not "which trail width", and
— settled here — not "which universe" either, but **can any entry rule on this watchlist
commit while more than the trail width of the day's move is still ahead of it?** Replay a
pullback/retest entry, or a hard "unspent range ≥ 2x trail" precondition, against the
ladder with every capital-protection rule fixed.

⚠️ Do **not** respond to this by relaxing IMP-036 or lowering `ENTRY_THRESHOLD`. Both
re-admit exactly the 0.78%-of-room cohort the ladder shows cannot pay. Counterfactual on
today's rows: 19 of 36 confidence-refusals would have cleared 60 under pre-IMP-036 scoring
and 6 had the gate open — but per the refusal study those 6 averaged ~nothing forward.

---

## IMP-041 — 2026-09-03 (daily) — measure excursion against the fill we actually got

### The problem
2026-09-03 TSLA was only the **second trade ever** to carry IMP-037's `mfe_pct` column, and
it exposed that the column is anchored to the wrong price.

The row records `entry_price = 374.765714` (the broker fill), `pnl = +$36.99` and
`pnl_pct = +1.41%` — all computed off that fill. But it also records `mfe_pct = 2.4853%`,
and 2.4853% is the high-water close (383.91) expressed against **374.60** — the *planned*
entry, not the fill. Against the fill the truth is **2.4400%**.

**Why the two diverge.** `executor.execute` polls `entry_fill_price` for a short budget and
falls back to `plan.entry_price` when the parent buy is still `pending_new` at the submit ack
— which it was here (`BRACKET TSLA ... entry=374.6000 ... (model A, pending_new)`). The
correction exists and works: at exit `risk._finish_exit` re-reads `entry_fill_price`, hands it
to `ExitResult.entry_fill_price`, and persistence COALESCEs it over the stored entry so
`entry_price`/`pnl`/`pnl_pct` all become exact. `_account_for_standdown` prefers it too
(`entry_ref = entry_fill if entry_fill is not None else ...`).

**`_excursion_pct` was the one consumer in that function that ignored it** — `entry_fill` was
computed five lines above the call and simply not passed. So `mfe_pct`/`mae_pct` were the only
pair of columns in the row measured against a different price than every sibling column.

**The bias has a direction, and it flatters us.** A market buy into a fresh bullish cross fills
at or above its plan, so the plan anchor is the *smaller* denominator **and** the larger
numerator: `mfe_pct` comes out **overstated** and `mae_pct` **understated**. Every capture
ratio (`realized / mfe`) built on the column is therefore optimistic. It is worst exactly where
it matters most — on **delayed fills**, which are the trades whose `ExecutionResult` stays
stale by construction: 2026-06-25 AMD planned 544.71 vs filled 547.873, **+0.58%**, about a
quarter of a typical 2% R.

The timing here is not incidental. Tomorrow's weekly (Fri 09-04) has been handed the
entry-vs-exit structural verdict and will lean on exactly these capture ratios. An instrument
with a known optimistic bias must not be the one that decides whether this strategy has an edge.

### The change
`bot/risk.py`, two edits, observational only:

1. **`_excursion_pct` takes `entry_fill` and prefers it**, mirroring `_account_for_standdown`'s
   existing `entry_ref` idiom; the call site passes the `entry_fill` it already had.
2. **`_track_excursion` stores observed closes only — the synthetic seed at the entry price is
   gone**, and the zero-clamp moved to `_excursion_pct`
   (`max(0.0, ...)` / `min(0.0, ...)`).

(2) is required by (1), not scope creep: the watermarks were *seeded* at the stale plan price,
so re-anchoring the denominator alone would have leaked the plan price back in as a phantom
drawdown (today: a fake `mae_pct = −0.0442%` on a trade that never traded below its fill).
Clamping at percentage time against the authoritative anchor preserves IMP-037's documented
invariant — "a trade that only ever goes against us reports `mfe_pct = 0`, it reached its entry
and no more" — while removing the only place the uncorrectable error could hide.

**Touches no trading logic.** Nothing in the bot reads `mfe_pct`/`mae_pct` to make a decision:
`persistence` writes them, `report` prints them, and `refusals` computes its own excursion from
bars via `bot.excursion`. Entries, sizing, stops, the trail and the gate are byte-identical.
It therefore **cannot confound tomorrow's weekly replay** — which, with the escalation clause
active for a fourth session, is the reason this and not a strategy change is tonight's work.

### Validation
- **503 tests pass** (`test_risk.py` 55 → 58), no regressions. `bot.preflight`: Alpaca PASS
  (equity 9170.64, 0 positions), SQL Server PASS, Telegram PASS, 1 expected market-closed WARN.
- Three new regression tests, the first built from today's real fills:
  - `test_excursion_is_measured_against_the_corrected_entry_fill` — plan 374.60, fill
    374.765714, peak close 383.91 → asserts **2.4400%, not 2.4853%**, and `mae_pct == 0.0`
    (the phantom-drawdown guard).
  - `test_excursion_falls_back_to_the_recorded_entry_when_no_fill_is_readable` — an unreadable
    fill leaves the planned anchor rather than voiding the measurement.
  - `test_excursion_never_reports_a_negative_mfe_when_the_fill_slipped_up` — the IMP-037
    invariant re-asserted at the corrected anchor.
- Deployed: `systemctl restart ustradebot.service`, confirmed `active`, clean startup.

### Scope and residue
- **Two historical rows predate this fix** (2026-08-28 SPOT, 2026-09-03 TSLA) and keep their
  plan-anchored values. **Deliberately not backfilled**: today's error is 0.045pp, SPOT's plan
  price is no longer recoverable from journald, and a half-backfilled column is worse than a
  uniformly-labelled pre-IMP-041 population of two. Every row from tomorrow is fill-anchored.
- Does **not** change the 275-trade ladder numbers the review quotes — `bot/timing.py`
  recomputes MFE from bars against the DB's (already corrected) `entry_price`, so the
  structural findings are unaffected. This fix aligns the *stored* column with that.

---

## IMP-042 — 2026-09-04 (daily) — express excursion in R: report the +1R ceiling

**Commit:** `ec9a711` · **Files:** `bot/excursion.py`, `bot/report.py`,
`tests/test_excursion.py` · **Tests:** 513 pass (10 new) · **Deployed:** service
restarted 20:15:40 UTC, clean boot, 19/19 warmup primed.

### Why
The escalation verdict turns on one number — **what share of entries ever print +1R** —
and the bot could not produce it. `--mfe` reports MFE in *percent bands*, but the
doctrine's WIN line is **+1R**, and R is per-trade (`entry − stop`, a median 2.01% of
price but ranging from under 1% to over 4%). A 1.5% excursion clears +1R on a
tight-stop trade and misses it on a wide-stop one, so **no fixed percent band separates
a winnable trade from an unwinnable one.**

The 2026-09-03 review needed that split and rebuilt it by hand over 275 rows — the same
by-hand rebuild `bot/excursion.py` was written to end, one level up. It also had to
approximate, applying a *single median R* to every trade. Measured properly, per trade,
against each row's own recorded stop, the ceiling is **18.8%, not the 16.0%** that
estimate produced.

Today's MU is the worked example that made it undeniable: **91% capture, +1.23% MFE —
and +0.60R.** The percent table calls that one of the best-handled trades in the book;
the R table shows it could not have been a WIN under any exit rule. Both readings are
arithmetically correct and they disagree about what the trade *was*. The doctrine's is
the one that governs.

### What changed
- `Excursion.risk_per_share` (optional) + `Excursion.mfe_r` — the conversion happens on
  the individual row, before anything is summed, because R cannot be applied in aggregate.
- `ceiling_table()` → rungs at **0.5R / 1.0R / 1.5R / 2.0R**; rows without a usable 1R are
  **dropped, never defaulted**, so the denominator is always the measured population.
- `format_ceiling()` — prints the ladder, names the WIN line, and splits the shortfall
  into *exit-recoverable* vs *entry signal* by drawing the realized true win rate beside
  the ceiling.
- `excursions_for(..., stop_loss)` takes 1R from `bot.doctrine.risk_per_share` — **the
  same denominator the WIN/SCRATCH/FAIL buckets use**, so the two studies cannot disagree
  about what one R is.
- `report.excursion_report` scores the true win rate over **exactly the cohort the ladder
  measured** (the rows that produced bars), not the whole window — a ceiling and a floor
  from different populations are not comparable. Degrades to the ladder alone if the rows
  cannot be bucketed; the ladder is the deliverable.

### Result (all-time, 276 trades)
| MFE ≥ | trades | share |
|---|---|---|
| 0.5R | 108/276 | 39.1% |
| **1.0R** | **52/276** | **18.8%** ← doctrine WIN line |
| 1.5R | 20/276 | 7.2% |
| 2.0R | 12/276 | 4.3% |

Realized true win rate **7.2%** → **11.6pp exit-recoverable, 81.2pp is the entry signal.**

### Why this and not a strategy change
Escalation is active for the **fifth** consecutive session (F+S 100% last-3, 94%
trailing-10, 93% all-time), and the doctrine forbids parameter tweaks under escalation.
The weekly review runs **45 minutes after this one** (cron is WIB: daily 20:00 UTC,
weekly 21:00 UTC — the weekly runs *after* the daily, not before it as the routine
prompt assumes) and 09-03 deliberately withheld a change so its entry replay would be
clean. A trading-path edit tonight would confound that replay. **IMP-042 is read-only
and touches no trading logic**, so the replay runs against unchanged strategy code.

### Rejected tonight, with evidence
- **Flatten later / hold into the close.** MU made its high *after* the flatten, which
  looked like a leak. Measured over every trade that reached the flatten (n=167,
  assumption-free, no trail modelling): **−0.007R/trade, t = −0.50, −$57.64**, up 47% of
  the time. ⛔ Refuted — do not re-propose.
- **A full trail simulator** to answer that question was built first and **discarded for
  failing validation**: it stopped out 59/179 trades that in reality reached the flatten,
  and its baseline was 2× off the actual. Shipping off an unvalidated simulator is how
  IMP-045 went wrong on the VWAP gate.
- **Loosening the gate** because it blocked the day's top score (INTC 82.9, which then
  finished +4.52%). Counterfactual: the blocked cohort had **avgMFE +0.76%, 0/2 reaching
  the 1.25% trail**. The gate cost nothing — INTC's move was the opening gap, already
  blocked by `ENTRY_START=10:00`. ⛔ Refuted.

### Validation
`.venv/bin/python -m pytest -q` → **513 passed**. Ladder run live against the book
(276 trades) and today (1 trade) — both render. Regression test pins MU 2026-09-04 at
91% capture / +0.59R so the percent-vs-R divergence stays covered.

---

## IMP-043 — 2026-09-07 (daily) — the backtest harness now obeys the stop-exit doctrine

**Status:** ✅ shipped & validated. `bot/replay.py`, `tests/test_replay.py`. 518 tests pass
(+5). **No service restart required or performed** — see "Deployment" below.

### The problem
`bot/replay.py:412` read:

```python
wins = [t for t in T if t.pnl > 0]
```

That is the precise test the stop-exit doctrine exists to abolish. IMP-039 (09-01) put the
doctrine into `bot/report.py` and **did not port it here**. The consequence is not
cosmetic and the 09-04 weekly named it the week's decisive finding:

> *"For the whole week the bot graded its live book honestly and its backtest dishonestly,
> and the dishonest one was steering the decisions."*

The harness is the **court of appeal**. Every REFUTED verdict of the last month —
`MIN_CROSSOVER` (six refutations), the `conf_crossover` anchors, the gate-width floor,
`MARKET_FILTER_SYMBOL` removal, lowering `ENTRY_THRESHOLD` — was decided on its output.
The 08-31 review wrote *"the strategy's current edge — PF ~2.4 in replay — is intact"* on
the strength of a **62.2% win rate that is 12% under the doctrine**. A backtest reporting
62% where live reports 7% does not look like a measurement discrepancy; it looks like
evidence the live book is being mismanaged, and it invites exactly the wrong fix (retune
the exits) for the actual problem (the entry never prints +1R).

### The change
Route the harness's own trade rows through the existing classifier and print the result
beside the headline, not instead of it.

- `summarize()` gains `stop_loss: float | None = None` (defaults to the simulated
  broker's own `Config`, so callers holding one need not thread it through) and appends
  `bot.doctrine.format_stop_exits(...)` plus one **F+S** line — the escalation metric,
  which the live report shows per-session but which here has the whole window as its
  population.
- `main()` passes `cfg.stop_loss` explicitly.
- The module docstring gains a **Scoring** paragraph stating what changed and why, next
  to the existing fidelity limits — anyone reading a replay number reads this first.
- **`win%`, `PF`, `net`, `avg`, `final equity` and the exit-reason table are untouched.**
  Money was never what `pnl > 0` got wrong; calling a scratch a win was.

**Why `SimTrade` needs no new plumbing, verified in the source:** `stop_price` and
`target_price` are written once in `SimBroker.execute()` from the sizing plan and never
mutated — the trailing ratchet rewrites `SimBroker._stop_price[new_id]`, the broker's own
order book, not the trade row. So `SimTrade.stop_price` is the **original 1R anchor**,
exactly like `dbo.trades.stop_price` live. That identity is what makes the live and replay
R denominators the same measurement rather than two similar-looking ones.

### Validation
**1 — it reproduces the weekly's independent hand re-scoring.** Friday's weekly re-scored
the harness output out-of-band through `bot.doctrine.classify`. Tonight the harness scores
itself, in-band:

| window | trades | net | PF | headline WR | **true WR** | stop rate | W/S/F | **F+S** |
|---|---|---|---|---|---|---|---|---|
| 90d | 77 | +$793.96 | 2.43 | 62.3% | **12%** | 75% | 9/29/39 | **88%** |
| 60d | 41 | +$472.18 | 2.87 | 65.9% | **10%** | 80% | 4/15/22 | **90%** |
| 30d | 18 | +$169.82 | 2.84 | 72.2% | **6%** | 83% | 1/7/10 | **94%** |

90d matches the weekly's `9/29/39, F+S 88.3%, true 11.7%` **exactly**; 30d matches
`1/7/10, 94.4%, 5.6%` **exactly**. 60d differs by one trade (41 vs 42) solely because the
window slid three calendar days over the long weekend. Two independent implementations
agreeing trade-for-trade is the strongest validation available on a day with no new data.

**2 — the money is provably unchanged.** A 90d run was captured *before* the edit; the
*after* run with the three new lines stripped **diffs byte-identical** to it. Same 77
trades, +$793.96, PF 2.43, avg +$10.31, same three exit-reason rows.

**3 — zero live risk.** `grep -rn 'bot\.replay' bot/` returns nothing outside
`bot/replay.py`. The harness is offline-only; the service does not import it.

**4 — 518 tests pass** (513 → 518). New coverage, written against tonight's real evidence:
- `test_summary_reports_the_doctrine_beside_the_headline` — **the pre-registered
  regression test.** A two-trade book of pure scratches reproducing the actual 2026-09-04
  live week (TSLA +0.68R trailing stop, MU +0.54R flatten): the summary must print
  `win%=100.0` **and** `true win rate: 0%` **and** `stop rate: 1/2 (50%)` **and**
  `FAIL+SCRATCH: 2/2 (100%)`. If the two rates ever silently converge again, this fails.
- `test_summary_r_is_measured_from_the_original_stop_not_the_trailed_one` — ratchet the
  stop to a 0.1% width, exit at +0.5%: must score **FAIL (BE-scratch)**, not WIN. Pins the
  denominator against the one bug that could make this instrument flatter the strategy.
- `test_summary_counts_a_target_fill_as_a_real_win` — the doctrine must still be able to
  say yes, or it measures nothing.
- `test_summary_stop_loss_defaults_to_the_brokers_config`, and
  `test_summary_money_figures_are_untouched_by_the_doctrine`.

Preflight: OK, 1 expected warning (market closed — Labor Day).

### Deployment
**Restarted, though this change cannot reach the service.** `bot/replay.py` is an offline
analysis tool that no service module imports, so the restart deploys nothing — it was done
anyway, on a closed market where it is free, to *prove the tree on disk boots*. That is a
real guarantee to hold going into Tuesday's open, and it is the control the 2026-06-23
DEPLOY-GAP incident exists to enforce (a fix recorded as "restarted clean" when the
process was in fact still running the old code; the rule since is to verify the running
PID against HEAD rather than assume).

Result: **clean boot at 20:11:26 UTC**, new PID 2854869 (was 2639553, 71h uptime),
`NRestarts=0`, `is-active` = **active**. Startup log green end to end — schema ensured
(16 batches), Alpaca `PA34DFFLTHRT` ACTIVE equity 9192.7, **no open positions**,
**warmup primed 19/19 symbols from history**, all 19 watchlist symbols subscribed on the
IEX feed, config echoed as expected (entry ≥60, 10:00–16:00 ET window, QQQ gate on, stop
−2.00%, trail 1.25%→1.00%). **Zero errors.** Files `chown ustradebot:ustradebot`
(including `.git` after the root-owned commit); **`.env` never touched**, still
`ustradebot:ustradebot` mode 600.

### Why this and not a strategy change
The escalation has been active for six consecutive sessions (F+S 100% over the last three
sessions with trades, 94% trailing 10, 93% all-time) and the doctrine forbids parameter
tweaks under it. **IMP-043 is not one** — it touches no entry, exit, sizing or risk path,
and its entire effect is to make every number the harness prints *harsher*. It also lands
on the one day of the year with zero live evidence, when any strategy edit would have been
fitted to Friday's single MU scratch.

### Expected effect
**Zero change to trading behaviour, by design.** What it changes is the quality of every
future decision: the weekly's pre-registered friction test (#2) can now be read on both
axes — money *and* trade quality — and every future "replay says this config is better"
claim carries a true win rate next to its PF. **It also removes the last standing
objection to the no-edge verdict**, which had rested entirely on a `pnl > 0` win rate.

### Follow-ups
1. **The weekly's #2 (friction in `SimBroker`) is now unblocked and is next.** Its
   baseline was re-verified tonight to the cent: **77 / +$793.96 / PF 2.43 / true WR 12% /
   F+S 88%** over the 19 enabled names.
2. **Pin that baseline with `--symbols`** so watchlist adds stop contaminating it — this
   is what currently blocks the META add (deferred twice; unconditional backstop 09-11).
3. The entry-signal study (#3) runs only after friction — measuring an entry change on a
   frictionless harness is how this blind spot happened in the first place.

---

- **Observed effect (weekly 09-11):** ✅ **VALIDATED — the week's most important fix.** The harness had scored `pnl > 0` while the live book scored by doctrine, so *the bot graded its backtest dishonestly and the dishonest one was the court of appeal for every REFUTED verdict of the last month.* It reproduces the 09-04 weekly's hand re-scoring **exactly** (90d 9/29/39, F+S 88%) — an independent implementation agreeing to the trade — and a before/after diff with the new lines stripped was **byte-identical**. F+S unmoved by design; it changed what we count, never what we do.

## IMP-044 — 2026-09-08 (daily) — the replay harness now pays a spread

### The problem
`bot/replay.py` was **frictionless**. Its own docstring said so — *"Fills are assumed at
the exact stop/target price with no slippage or gap-through modelling, and entries fill at
the signal candle's close"* — and that harness has been the court of appeal for every
REFUTED verdict of the last month: the IMP-022 gate A/B, the `conf_crossover`
recalibration, the trail retune, the VWAP gate.

The 09-04 weekly found live and replay agreeing about trade *quality* and disagreeing
badly about *money*. On the only config-matched window (30d) live booked **+$5.17/trade**
against replay's **+$9.43** — ≈$4 on ~$2,000 of notional, ≈0.2% per round trip, an
entirely ordinary market-order cost in liquid large-caps.

The bias is not merely "every net is inflated". Friction is charged **per trade** while
this strategy's edge is not, so a frictionless harness **systematically over-rewards
high-frequency, scratch-heavy configs**. With 88–94% of trades scratching near
break-even, friction is not a rounding error — it is the P&L. This is the same failure
shape found in CryptoAutoBot on 09-02: a ledger reporting gross as net.

### The change
Per-side spread/slippage on every simulated fill, **10 bps (0.10%) by default**, i.e.
0.20% per round trip.

- `SimBroker(..., slippage_bps=DEFAULT_SLIPPAGE_BPS)`; `--slippage-bps` on the CLI, echoed
  in the header line so a result is self-documenting.
- Buys fill **above** the price that fired them, sells **below** it — applied at the
  **fill**, never at the **trigger**. A stop still triggers when the bar trades through it
  and then fills worse, which is what a stop order does.
- Bracket legs and the sized quantity stay anchored to the signal-candle price, exactly as
  live: the bot submits stop/target before the broker tells it where the entry filled.
- Covers all four fill paths: entry, stop leg, target leg, market close (which is the EOD
  flatten, the reversal exit and the window-end settle — all route through
  `close_position`).
- `SimTrade` gains `slippage`, `gross_pnl` and `friction`. `gross_pnl` **inverts** the
  markup arithmetically rather than keeping a parallel ledger of pre-slippage prices that
  a mis-ordered exit path could desynchronise.
- `summarize()` prints `friction=… gross=… -> net=…  [% of gross]` under the money line,
  so an old frictionless figure stays directly comparable instead of silently
  incommensurable.
- **Not a config key.** Friction is a property of the *simulation*, not of the deployed
  strategy, so it must never reach `.env`. Nothing in the live trading path is touched —
  `bot/replay.py` is offline and not imported by the service.

### The result — a pre-registered prediction, scored, and FAILED
The weekly pre-registered: *"at 0.2%/round trip, replay 90d net falls from +$793.96 to
**under +$200**."*

| 90d, 19 symbols, identical config | 0 bps | **10 bps/side** |
|---|---|---|
| trades | 77 | 77 |
| **net** | **+$793.96** | **+$472.29** |
| PF | 2.43 | **1.68** |
| avg/trade | +$10.31 | **+$6.13** |
| headline win% | 62.3% | **53.2%** |
| true WR | 12% | **10%** |
| F+S | 88% | **90%** |
| friction | — | **$346.40 = $4.50/trade = 42% of gross** |

**❌ The prediction failed.** Net landed at **+$472.29**, more than double the predicted
ceiling. Three conclusions, recorded because the weekly bound itself to them in advance:

1. **The prediction contradicted its own input.** It estimated ~$4/round trip, then
   predicted a >$594 drag over 77 trades — which needs **$7.7/trade**. At its own $4 the
   arithmetic gives ~+$486; measured is **+$472.29 at $4.50/trade**. The *magnitude* was
   right, the *conclusion* drawn from it was not. **Check the implied per-trade cost
   before pre-registering a total.**
2. **"Replay proves an edge" survives, weakened.** +$472 / PF 1.68 over 90 days is still
   positive, so verdicts decided on PF do **not** all need re-opening — but PF fell 31%
   and every margin is thinner than the number that decided it.
3. **Friction explains 55% of the live-vs-replay gap, not all of it.** On 30d, replay
   avg/trade goes **+$9.43 → +$7.49** against live **+$5.17**: the $4.26 gap closes to
   **$2.32**. The residual is entry-at-signal-close optimism plus candle-boundary drift —
   now the open question, and a better-posed one than the weekly had.

### Validation
- **`--slippage-bps 0` reproduces the pre-IMP-044 90d run exactly** — 77 trades,
  +$793.96, PF 2.43, to the cent. Provably non-destructive.
- **527 tests pass** (10 new, was 517). `bot.preflight` OK with the expected
  market-closed warning.
- New tests pin: entry fills above the signal close; a stop triggers at the stop and fills
  below it; a bar stopping one cent short still does not fill (friction may not drag the
  trigger); a slipped target fill is still classified **WIN** by `bot.doctrine` (at 10 bps
  the fill is 0.1% light against a 0.5% tolerance — otherwise IMP-044 would have silently
  converted every harness WIN into a FAIL); the market close pays the same spread;
  friction equals `gross_pnl - pnl` exactly; friction scales with **trade count, not
  edge** (the over-rewarding-churn mechanism, pinned); and 0 bps is bit-identical to the
  old harness.
- The friction test is anchored to a **real recorded row** — Friday's MU fill, 2 sh @
  997.565, $1,995.13 notional — and asserts the toll on that notional is **≈$4.00**, the
  exact per-trade gap the weekly measured between live and replay.

### Why this and not a strategy change
The escalation is active for the **seventh** consecutive session (F+S 100% over the last
three sessions with trades, 94% trailing 10). Today produced **zero closed trades**, so
there was no trade-level evidence that could justify a strategy edit — any such edit would
have been fitted to Friday's single MU scratch. IMP-044 touches no entry, exit, sizing or
risk path, and it is the prerequisite the weekly explicitly attached to the entry study:
*"measuring an entry change on a frictionless, `pnl > 0`-scored harness is how this week's
blind spot happened."* With IMP-043 (doctrine) and IMP-044 (friction) both landed, the
harness is now honest on both axes.

**Also unblocked:** the META watchlist add. Its release condition was *"the first
pre-market run after IMP #1 and #2 are both recorded"* — both now are, ahead of the
unconditional 09-11 backstop.

### Follow-ups
- Model **entry-at-next-bar-open** and re-measure the residual $2.32/trade.
- Re-run the gate A/B **with friction** before Friday's weekly rules on gate hysteresis
  (see the 09-08 daily review): the old A/B compared 74 vs 156 trades, and friction is
  charged per trade, so the gate is likely *more* accretive than +$219, not less.

---

- **Observed effect (weekly 09-11):** ✅ **VALIDATED — and the pre-registered prediction FAILED, which is recorded rather than re-framed.** I predicted 90d net under +$200; it came in at **+$472.29** (from +$793.96; PF 2.43 → 1.68). The prediction was too pessimistic, the finding survived: **friction is $4.50/trade = 42% of gross profit**, and it is charged per trade while this strategy's edge is not — so the old harness **systematically over-rewarded scratch-heavy, high-frequency configs**. Replay F+S **88% → 90%**: the measured failure share got *worse* once the instrument got honest, which is the correct direction. **Every net/PF figure in this repo predating this IMP is gross and must be re-read or re-run.**

## IMP-046 — strip the lookahead out of the entry-timing diagnosis
**2026-09-09 (daily review).** `bot/timing.py`, `tests/test_timing.py`. Read-only
reporting fix — touches no entry, exit, sizing or risk path.

### The defect
`EntryTiming.entry_percentile` (IMP-040) is
`(entry − session_low) / (session_high − session_low)` over the **whole session**,
including every bar *after* the entry. A trade that runs after we buy lifts
`session_high` and pushes its own percentile down, so the statistic is largely a
monotone transform of the forward return rather than a property of the entry. Rung 2
(`available_pct`) reads that same future high, so the two are anti-correlated **by
construction**.

The module's own docstring asserted the causal reading — *"high values are the
signature of a late entry"* — and the `--timing` READ key asserted *"a big 1->2 drop =
late entry"*. **Six consecutive daily reviews reached a late-entry verdict from it and
none tested it.**

### The measurement (246 closed trades with session bars)
| metric | corr with `available_pct` | median |
|---|---|---|
| `entry_percentile` (whole session, lookahead) | **−0.664** | 71% |
| `causal_entry_percentile` (range known at the fill) | **+0.008** | **87%** |

Lookahead cohorts collapse monotonically (median realized +0.86% → −1.19%, ≥trail
34/43 → 0/27); causal cohorts are flat (median available 1.08 / 0.76 / 0.83 / 0.81%).
Cleanest row: **SE 2026-07-09**, +2.78% realized — lookahead scores the fill at the
**30th percentile** ("early entry"); it actually filled at **122%** of the range
printed so far, *above every price of the day*, a breakout buy.

### The change
- `EntryTiming` gains `high_at_entry` / `low_at_entry` — session extremes **as at the
  fill**. `<=` on the entry bar for the mirror image of the existing `>=` rule: we fill
  at that bar's close, so it is complete and known, and nothing later is.
- New `causal_entry_percentile` property. **Not clamped to [0,1]** — a fill above
  everything printed so far is a breakout and >1.0 is the only way to say so.
- `TimingSummary.median_causal_entry_percentile`; `--timing` prints it, relabels the old
  one **"whole session, LOOKAHEAD — descriptive only"**, drops the "1->2 drop = late
  entry" claim and warns explicitly instead.
- Module and property docstrings corrected where they asserted the refuted reading.
- Defaults to `0.0` so pre-IMP-046 rows degrade to `None`, never a divide-by-zero.

### Validation
- **534 tests pass** (7 new, was 527). Preflight OK (1 expected market-closed warning).
- Tests pin: the mechanism (identical entries, different post-entry highs → causal fixed
  at 1.0 while lookahead swings 1.0 → 0.2); **SE 07-09** (30.4% vs 122.5%); **today's
  META 15:17 @ 657.40**, where the two converge to 98%/99% *because* nothing ran — the
  artifact needs a forward move to open up, which is why a flat session can never reveal
  it; the `None` cases; and backward compatibility.

### What it does and does not settle
- ✅ **The late-entry charge has no support on the honest measure.** The median fill sits
  at the 87th percentile of the range so far — a crossover strategy buys strength by
  construction — and forward runway is flat across every cohort above the 25th.
- ✅ **Prevents an in-sample-brilliant, live-worthless entry filter** on this quantity.
- ❌ **Does not exonerate the entry signal.** Ceiling unchanged: **18.1%** of entries ever
  print +1R vs a **6.0%** realized true win rate → 12.0pp exit-recoverable, **81.9pp is
  the entry**. 171/249 trades never peaked past the 1.25% trail.
- Third lookahead/measurement-honesty defect found in a month (IMP-024 gate lookahead,
  IMP-044 frictionless harness, now this).

### Follow-ups
- Friday's gate-hysteresis A/B needs re-scoping: today had **zero** gate flips (0/88 bars
  open), so hysteresis would have changed nothing and on today's cohort would have cost
  money. Report **which sessions it changes**, with IMP-044 friction on.
- Re-derive, don't inherit, the ranked entry candidates built on the lookahead reading.
- Untested causal axes: ATR at signal time (today's refusals ran 0.06–0.24% ATR against a
  2.0% stop — +1R arithmetically unreachable) and the inverted 90–100 confidence band.

---

- **Observed effect (weekly 09-11):** ✅ **VALIDATED, observational.** Third lookahead found and removed in a month (after IMP-024 and IMP-045) — the class of bug is systemic to how these diagnostics are written, not three coincidences. F+S unmoved by design; no expectancy claim made or implied.

## IMP-047 — 2026-09-10 (daily) — stamp the scorer that wrote every row, and keep the raw RSI
**`bot/signals.py`, `bot/strategy.py`, `bot/persistence.py`, `sql/schema.sql`,
`tests/test_signals.py`, `tests/test_persistence.py`.** Observational only — touches no
entry, exit, sizing or risk path. **The weights were NOT changed** (see below).

### Why this, on a day with no trades
Zero trades (QQQ 5m gate open **0/89 candles**; risk-off tape), so the reviewable
question was the entry score itself. Working that question surfaced a real defect and
then ran straight into the reason it could not be answered from the database.

### The defect that was found, fixed, and then rejected
`conf_rsi == 1.00` on **259/276 closed trades (93.8%)** and **430/441 refusals (97.5%)** —
`score_rsi` returns a flat 1.0 for any RSI in 45–65 and a fresh bullish 1-min cross
almost always lands there. **20 of 100 confidence points are a constant subsidy**, and the
overbought branch that justifies them fired on **2 of 276 trades** (net +$8.90) and **0 of
441 refusals**.

The IMP-034 operation — redistribute the 20 points proportionally over the three
discriminating terms (39:26:15 → 48.75/32.50/18.75), renormalise to 100, leave
`ENTRY_THRESHOLD` at 60 — was implemented and A/B'd on the replay harness, friction on:

| window | baseline | reweighted | Δnet |
|---|---|---|---|
| 30d | n=16, +$124.15, PF 2.09, true 6% | n=10, +$137.87, PF 3.71, true 10% | **+$13.72** |
| 45d | n=31, +$305.99, PF 2.36, true 10% | n=23, +$274.19, PF 2.88, true 13% | **−$31.80** |
| 60d | n=38, +$363.92, PF 2.43, true 8% | n=24, +$279.29, PF 2.91, true 12% | **−$84.63** |

A variant redistributing over crossover+trend only (51.0/34.0, volatility left at 15) was
also run and is within $3 of the above in every window — the choice between them does not
matter, the cut does. **Rejected and reverted**: per-trade quality rises on every axis
(60d PF 2.43→2.91, true win 8%→12%, avg/trade +$9.58→+$11.64) but net dollars fall on two
of three windows on **37% fewer trades**. With `conf_rsi` pinned at 1.0 the operation is
**not a reweighting** — for 94% of candidates the ranking is byte-identical and only the
bar moves, **40/80 → 48/80** points of real signal. It is a threshold tightening wearing
a reweighting's clothes, and the doctrine's escalation clause (FAIL+SCRATCH 92.8%
all-time, 100% over the last 3 sessions with trades) forbids exactly that.

### The measurement defect this exposed — the real reason for the change
The DB counterfactual that motivated the reweighting looked decisive: all-time net
+$90.84 → +$442.64, the refused cohort **−$351.81 over n=95** with a **1.1%** true win
rate and 98.9% FAIL+SCRATCH, and trimming the best and worst row made it *worse*
(−$355.81), so not one outlier. **It was invalid.** `conf_volatility` **reversed its
meaning at IMP-036 (2026-08-26)**: the old ramp scored a *dead* tape 1.00, the current one
scores it 0.00. **268 of those 276 rows predate the flip**, so the cohort the study called
"weak signal" was largely an artifact of the old anchors — and because the proposed change
redistributes weight *into* volatility, the contamination pointed the same way as the
hypothesis. Only **8 of 276 closed trades (3%)** carry a usable `atr_pct`, so the honest
version of the test has n=8 and decides nothing. **Nothing in the schema said which scorer
wrote a row.** That is what this IMP fixes. (The uncontaminated slice — crossover+trend,
whose meanings never changed — does still separate: admits n=103 +$369.88 / +0.139R / true
12.6% vs refuses n=173 −$279.04 / −0.063R / true 4.0%. That is what justified taking the
question to the replay harness, which recomputes everything from bars and has no stale
sub-scores.)

Fourth measurement-honesty defect in a month: IMP-024 gate lookahead, IMP-044 frictionless
harness, IMP-046 timing lookahead, now scorer provenance.

### The change
- **`SCORER_VERSION = 3`** in `bot/signals.py`, with the generation table in a comment:
  v1 origin (volume weighted 15, volatility a *spread* proxy — tight tape scored 1.0),
  v2 2026-08-24 IMP-034 (volume 15 → 0), v3 2026-08-26 IMP-036 (volatility anchors
  reversed). Bump when a sub-score's scale, anchors or meaning change.
- **`rsi_raw`** — the raw RSI behind `conf_rsi`. The sub-score saturates across the whole
  45–65 plateau, so re-scaling the band edges cannot be back-tested from stored rows; the
  raw input was being computed and thrown away.
- Both carried on `TradeSignal` / `RefusedEntry` → `TapeContext` / `RefusedCandidate` and
  written to **`dbo.trades`** and **`dbo.entry_refusals`**, the refusal side included
  because that is where an entry threshold is actually priced.
- `sql/schema.sql`: idempotent `IF COL_LENGTH(...) IS NULL ALTER TABLE` pairs in the
  IMP-029 style, plus the columns inline in both `CREATE TABLE`s. Documented in the schema
  that NULL means **exclude the row**, not zero-fill — and that for `conf_volatility`
  specifically, NULL provenance means "possibly the opposite of what you think".
- `score_rsi`'s docstring now records the 93.8%/97.5% measurement and why deleting its
  weight was rejected, so the next attempt re-derives rather than rediscovers it.

### Validation
- **543 tests pass** (was 534; +9). Preflight **all-PASS** (1 expected market-closed warning);
  it ran the migration through the bot's own `ensure_schema` path — 20 batches, clean.
- Migration applied to the live `USBot` DB; all four columns confirmed present.
- Live `INSERT` probe against the real schema with today's QCOM vector round-tripped
  `(rsi_raw 55.0000, scorer_version 3)` and was **rolled back** — 0 rows left behind.
- A pre-existing test caught a genuine bug in my first version of the trades `INSERT`
  assertion (19 columns vs 18 placeholders — `status` travels as the literal `'OPEN'`).
  The placeholder-vs-column invariant is now asserted on the trades write too, not just
  on refusals, since that write has now grown twice.
- Tests pin: the v3 stamp and the weights it describes; the rsi plateau collapsing to a
  single stored value; the **arithmetic that made the rejected change a threshold move**
  (40/80 → 48/80); and **today's real QCOM 16:40 @ 59.26 vector**, which must stay refused.

### What it does and does not do
- ✅ Makes every future scored row self-describing, so a sub-score study can exclude rows
  written by a different scorer instead of silently averaging across a sign flip.
- ✅ Unblocks two specific pre-registered studies: re-scaling the `score_rsi` band edges,
  and the **ATR-scaled stop** (which needs per-trade signal-time ATR on every row).
- ❌ Changes nothing about what the bot trades. No expectancy claim is made for it.
- ❌ Does not backfill. The 268 pre-v3 rows stay NULL and must be **excluded**; there is no
  way to recover which scorer wrote them beyond the IMP dates, which is why the comment
  carries the date table.

### Follow-ups
- **ATR-scaled stop is the next structural candidate** and the escalation clause's answer:
  1R is currently **~24× the median 1-min ATR** (median 0.082% of price vs a 2.0% stop), so
  **0 of the last 32 trades touched a full stop** and +1R is near-unreachable — the stop
  defines an unreachable denominator rather than protecting capital. Needs its own sweep,
  every window, friction on. Risk-path change; sizing must be re-derived with it and that
  part needs human sign-off (noted in `todo.md`).
- Re-sweep the `score_rsi` 45–65 band edges once `rsi_raw` has a few weeks of rows.
- Do **not** re-run the entry-score counterfactual against `conf_volatility` on pre-v3
  rows. It will look compelling again and it will again be wrong.

---

- **Observed effect (weekly 09-11):** ✅ **VALIDATED, observational, correctly scoped.** Lets sub-score studies exclude rows written across a scorer sign-flip instead of silently averaging through one. The no-backfill decision is right: the 268 pre-v3 rows stay NULL and must be **excluded**, not zero-filled. F+S unmoved by design.

## IMP-048 — 2026-09-11 (daily) — record the trail's path, so "trail or stop?" is answerable in SQL
**`bot/risk.py`, `bot/persistence.py`, `sql/schema.sql`, `tests/test_risk.py`,
`tests/test_persistence.py`.** Observational only — touches no entry, exit, sizing or
risk decision. Nothing about what the bot trades changes.

### The change that was tested first, and rejected
Today's trade (INTC, −0.48R, FAIL) was ended **by the trail, not by the stop**: entry
103.3959, bracket stop 101.38 (−1.95%), and the ratchet moved the stop six times in 21
minutes — 101.38 → 102.10 **sixty seconds after entry** → … → 102.50 (−0.87%) — while MFE
was only **+0.39%**. MAE was −1.02%, so the original stop was never threatened.

The mechanism is structural, not a tuning accident: the ratchet is seeded from the
original stop, and IMP-018 *requires* `trail_percent < stop_loss`, so `close × (1 − 1.25%)`
clears that seed on the **first managed candle**. The stop is cut from −2.00% to −1.25%
before the trade has proven anything — **the risk budget the position was sized against is
silently reduced within a minute of entry**, and to −0.87% within five. A stop below entry
protects no profit; it only books a smaller loss sooner, which was never the documented
intent of the trail ("a winner now runs until it gives back trail_percent from its peak").

So I implemented the gate — suppress the ratchet until it would place the stop at or above
the **entry price** — and A/B'd it on the replay harness, friction on, three windows. It
introduces no tunable constant (the arming line is the trail's own geometry), never moves a
stop down, and leaves every ratchet at or above breakeven byte-identical.

| window | baseline | gated | Δnet | PF | stop rate | true win | FAIL+SCRATCH | WIN n |
|---|---|---|---|---|---|---|---|---|
| 30d (n=19) | +$151.77 | +$164.77 | **+$13.00** | 2.00 → 2.09 | 74% → 58% | 11% → 11% | 89% → 89% | 2 → 2 |
| 45d (n=37) | +$290.54 | +$276.49 | **−$14.05** | 1.95 → 1.73 | 81% → 68% | 11% → 11% | 89% → 89% | 4 → 4 |
| 60d (n=46) | +$331.51 | +$344.65 | **+$13.14** | 1.92 → 1.83 | 80% → 67% | 9% → 9% | 91% → 91% | 4 → 4 |

**Rejected and reverted.** Trade counts are identical in every window, so this is a clean
exit-only A/B — and it fails on its own terms: net signs disagree (IMP-021's ≥3-windows
rule), PF degrades in 2 of 3 including both longer windows, and the 13–16pp stop-rate drop
is the precise pattern the doctrine's anti-gaming rule says to reject ("cuts the stop rate
but flattens expectancy"). The drop is largely **relabelling**: full stops rise (1→3, 1→6,
1→6), BE-scratches fall (7→3, 19→10, 24→15), and **FAIL+SCRATCH is unchanged to the trade
in all three windows**.

**The negative result is the valuable part: the WIN count moved by zero trades in every
window.** Exit structure cannot manufacture a +1R trade. That eliminates *profit capture*
and *stop geometry* as the binding constraint with a trade-matched A/B and points at
**entry quality and the unreachable-1R denominator**.

### What shipped instead, and why it is the right thing to ship
Running that study exposed a measurement gap that made it needlessly hard: **`stop_price`
on the trade row is the ORIGINAL 1R anchor and never moves** — the ratchet replaces the
broker's order, not the row. So the database held **no record of where the stop actually
ended up**, and the question the whole analysis turned on — *did the trail end this trade,
or did the original stop?* — was unanswerable in SQL for every row ever written. I had to
reconstruct it by grepping journald, **which rotates**. Six weeks from now today's trade
would be unexplainable.

- **`trail_stop_final`** — the highest stop actually resting at the broker when the trade
  ended (the original when the ratchet never fired).
- **`trail_moves`** — how many replaces the broker accepted.
- Carried on `ExitResult`, read in `_record_exit` **before** the trail state is dropped
  (the same ordering constraint `_broker_fill_reason` already depends on), written to
  `dbo.trades` under `COALESCE` so a re-recorded exit can never blank a stored path.
- `sql/schema.sql`: idempotent `IF COL_LENGTH(...) IS NULL ALTER TABLE` pairs in the
  IMP-029/IMP-047 style, plus the columns inline in `CREATE TABLE`.
- **NULL semantics documented**: NULL = no measurement (pre-2026-09-11, or a
  startup-reconciled holding with no movable stop leg) and must be **excluded**, not
  zero-filled. That is deliberately distinct from `(trail_stop_final = stop_price,
  trail_moves = 0)`, which is the meaningful statement "the trail was armed and never fired".

With `entry_price`, `stop_price` and `exit_price` these give, in one query: trail-kill vs
stop-kill vs flatten; whether the final stop locked a **profit or a smaller loss**; and how
much of the sized 1R the trail consumed before the trade resolved. On today's INTC row that
reads: trail ended it **True**, locked a profit **False**, **55.6% of 1R consumed**.

**This is what unblocks the pre-registered ATR-stop decision** — that proposal cannot be
judged without knowing, across many trades, whether the stop that actually fired was the
sized one or a ratcheted one. Fifth measurement-honesty fix in a month: IMP-024 gate
lookahead, IMP-044 frictionless harness, IMP-046 timing lookahead, IMP-047 scorer
provenance, now trail provenance.

### Validation
- **550 tests pass** (was 543; +7). Preflight **all-PASS** with the expected
  market-closed warning; it ran the migration through the bot's own `ensure_schema`
  path — **22 batches** (was 20), clean.
- Migration applied to the live `USBot` DB; both columns confirmed present and nullable.
- Live `UPDATE` probe against the real schema on today's INTC row (id=301) round-tripped
  `(102.500000, 6)`, computed the three derived verdicts above, and was **rolled back** —
  re-read confirms `(None, None)`, 0 rows left behind.
- Three pre-existing tests asserted the exit UPDATE's params **positionally** and broke,
  correctly, on the two added binds. Fixed, and **added the placeholder-vs-assignment
  invariant to the UPDATE** — the INSERT already had one (IMP-047), the UPDATE did not,
  and it has now grown twice. Positional drift there would silently write each value into
  its neighbouring column with no other assertion catching it.
- Tests pin today's real INTC trade end-to-end: six ratchets → `trail_moves == 6`,
  `trail_stop_final ≈ 102.50`, and the two comparisons that carry the verdict
  (`> stop_price` = the trail ended it; `< entry_price` = it locked a loss). Plus the
  armed-never-fired `(stop_price, 0)` case, the None-without-a-stop-leg case, and
  non-leakage of the move count across a re-entry.

### What it does and does not do
- ✅ Makes the trail's effect on every future trade measurable in SQL instead of in journald.
- ✅ Unblocks the ATR-stop study, which needs exactly this attribution across many trades.
- ❌ Changes nothing about what the bot trades. No expectancy claim is made for it.
- ❌ Does not backfill. All 277 existing rows stay NULL and must be excluded; journald has
  already rotated past most of them.

### Follow-ups
- **🔴 The escalation clause has been active for three consecutive sessions with trades
  (FAIL+SCRATCH 100% over the last 3, 96.2% over the last 10, 92.8% all-time).** Today's
  A/B is the second consecutive run (after IMP-047) in which a well-motivated change was
  implemented, measured honestly, and **rejected because it moved labels rather than
  dollars**. That pattern is itself evidence: two independent attacks on the exit side
  have now failed to move the WIN count by one trade.
- **ATR-scaled stop is the remaining structural candidate and needs human sign-off**
  (risk path; sizing must be re-derived with it). Today: 1R = 2.00% against a **0.182%**
  ATR tape = 11×. In `todo.md`.
- Hand to the weekly review with the numbers attached, per the escalation clause.
- Do **not** re-test the trail-arming gate on a single window; it will look good on 30d
  and 60d and it is noise. If it is ever revisited, it needs ≥3 windows and a PF that does
  not degrade on the longest one.

- **Observed effect (weekly 09-11):** ✅ **VALIDATED — and the rejected experiment is worth more than the shipped code.** The trail-arming gate was implemented, A/B'd on three windows and **reverted**: net signs disagreed, PF degraded on both longer windows, and the 13–16pp stop-rate drop was pure relabelling with **F+S unchanged to the trade in all three windows** — a textbook anti-gaming rejection, correctly called. **The decisive number is that the WIN count moved by ZERO trades in every window.** Together with the 09-04 weekly's 18.8% +1R ceiling, this **closes the exit side as an explanation** for the 93pp shortfall and moves the whole burden to entry quality. What shipped instead removed a real blind spot (`stop_price` never moves, so "trail or stop?" lived only in rotating journald). F+S unmoved by design.
- ⚠️ **CORRECTION (weekly 09-18) — "closes the exit side as an explanation" was overstated and
  is hereby withdrawn as written.** It was an inference from a frozen WIN count, not a
  measurement. IMP-051 built the measurement: on 90d the ceiling is **23.3%** against a
  realized true WR of **13.3%**, so **6 of the 14 entries that reached +1R were given back —
  ~40% of the achievable WINs are lost after the trade is already right** (2 of 5 on 45d).
  **~10pp of exit-recoverable headroom exists.** What survives of the original claim, and it
  is still the larger half: **77% of entries never print +1R at all**, so the entry is the
  dominant cap and no exit change can touch that majority. What does *not* survive is the
  word "closes". The specific sub-claims remain correct — the trail-*arming* gate is
  relabelling (this IMP) and the trail *width* is relabelling (09-16, WIN frozen at 8 across
  four widths) — but a **reachable target** was never tested by either, and IMP-051 found
  **zero target fills in 60 trades** against a 10% `TAKE_PROFIT`. That is the untested gap the
  overstatement hid, and it is next week's #1.

---

## IMP-049 — 2026-09-14 (daily) — range availability becomes a hard entry precondition, not a 15-point suggestion
**`bot/config.py`, `bot/signals.py`, `bot/strategy.py`, `tests/test_signals.py`,
`tests/test_config.py`.** **Entry-path change** — the first strategy-logic change shipped
since the escalation clause went active. Tightens entry selectivity only; never widens
risk, touches no stop, sizing or exit path.

### The problem
Under the stop-exit doctrine a WIN requires **+1R**. `score_volatility` already measures
whether the tape can travel that far — IMP-036 re-anchored it so a dead tape (1-min ATR
≤ `_ATR_DEAD` = 0.20% of price) scores exactly **0.0**. But it is only a **weighted term
worth 15 of 100 points**, so a dead-tape setup is still admissible whenever crossover +
trend + rsi carry the total over 60.

That is not hypothetical. **The 09-11 INTC trade entered at confidence 60.1 with
`conf_volatility == 0.00`** on a 0.182% ATR tape, where +1R required an **11× ATR** move.
It peaked at +0.39%, never threatened its stop, and the trail ended it at **−0.48R, a
FAIL**. The 09-11 review called it *"arithmetically near-incapable of reaching +1R from
the moment it was placed."* A trade the book cannot win is not a low-quality trade — it is
an **unwinnable** one, and the scorer already knew it and was outvoted.

The architecture already had the right pattern for this: `min_crossover` (IMP-011) is a
hard sub-score floor applied in `evaluate_entry` independently of the weighted total.
IMP-049 applies the same pattern to the sub-score that answers "can this tape pay?".

### The change
`Config.min_volatility` (env `MIN_VOLATILITY`, **default 0.01**, 0.0 disables) — a
candidate must clear `confidence.volatility >= min_volatility` on top of
`entry_threshold` and `min_crossover`.

**No new fitted constant.** `score_volatility` returns exactly 0.0 at or below
`_ATR_DEAD`, a breakpoint IMP-036 calibrated independently. Any value in (0, 0.05]
rejects that cohort and nothing else; 0.01 is simply inside it. This is deliberate — the
alternative was fitting a fresh threshold to this book.

### Validation — replay, friction ON, four windows
| window | variant | n | net | PF | exp R | **WIN (+1R)** | stop% | F+S% |
|---|---|---|---|---|---|---|---|---|
| 30d | baseline | 15 | +$75.75 | 1.60 | +0.051 | 1 | 73% | 93% |
| 30d | **floor** | 10 | **+$133.00** | **2.93** | **+0.222** | **1** | 70% | 90% |
| 45d | baseline | 32 | +$204.08 | 1.80 | +0.107 | 3 | 78% | 91% |
| 45d | **floor** | 23 | **+$280.44** | **2.82** | **+0.224** | **3** | 78% | 87% |
| 60d | baseline | 43 | +$332.53 | 1.99 | +0.124 | 4 | 79% | 91% |
| 60d | **floor** | 32 | **+$442.09** | **3.15** | **+0.244** | **4** | 81% | 88% |
| 90d | baseline | 76 | +$330.14 | 1.46 | +0.083 | 8 | 76% | 89% |
| 90d | **floor** | 60 | **+$461.50** | **1.84** | **+0.157** | **8** | 80% | 87% |

1. **All four windows agree in sign** on net (+$57 / +$76 / +$110 / +$131), PF (+1.33 /
   +1.02 / +1.15 / +0.38) and expectancy (+0.171 / +0.117 / +0.119 / +0.074 R). The
   IMP-021 three-window rule is met with one to spare.
2. **The WIN count is identical in every single window** (1, 3, 4, 8 before and after).
   The floor removes 5 / 9 / 11 / 16 trades and **not one of them was a +1R winner.** It
   strictly subtracts unwinnable trades — which is the whole claim, tested directly.
3. **The stop rate is NOT what improved** — it is flat-to-*worse* (73→70, 78→78, 79→81,
   76→80). The doctrine's anti-gaming rule asks whether a change bought a nicer stop rate
   at the cost of expectancy; this one did the reverse, and that is the honest direction.
   Payoff is flat (2.49→2.21, 3.56→3.71, 3.40→3.41, 3.46→3.29).

**Anti-overfit check — floor sweep, 90d:** `0.0` → n=76 / +$330 / 8 WIN · **`0.01` →
n=60 / +$462 / 8 WIN** · `0.05` → n=59 / +$434 / 8 WIN · `0.20` → n=54 / +$265 / 6 WIN ·
`0.50` → n=42 / +$167 / 5 WIN · `0.99` → n=27 / +$190 / 3 WIN. **0.01 and 0.05 are the
same result** — confirming this is a genuine cohort edge at the `_ATR_DEAD` breakpoint,
not a knife-edge optimum — and pushing harder **destroys winners** (8→6→5→3), which is
the expected shape if the breakpoint is real.

**Live-book corroboration (the strongest evidence here).** The v3 scorer has written 8
closed trades since 2026-08-27; they are the only live rows whose `conf_volatility` is
comparable with today's. The floor blocks **exactly 2 of the 8**:

| symbol | date | conf | conf_vlt | profit_R | P&L | blocked? |
|---|---|---|---|---|---|---|
| NVDA | 08-27 | 82.4 | 1.00 | +0.07 | +$3.78 | no |
| TSM | 08-27 | 62.5 | 0.02 | +0.15 | +$5.08 | no |
| PLTR | 08-27 | 88.4 | 1.00 | +0.52 | +$25.93 | no |
| TSLA | 08-27 | 71.8 | 0.39 | +0.48 | +$16.60 | no |
| **SPOT** | **08-28** | **63.9** | **0.00** | **−0.35** | **−$11.82** | **BLOCKED** |
| TSLA | 09-03 | 78.7 | 1.00 | +0.68 | +$36.99 | no |
| MU | 09-04 | 72.1 | 1.00 | +0.54 | +$22.21 | no |
| **INTC** | **09-11** | **60.1** | **0.00** | **−0.48** | **−$16.52** | **BLOCKED** |

**Both blocked trades are FAILs, together −$28.34, and they are the two worst trades in
the window.** Every positive-R trade survives untouched. `TSM` at `conf_vlt = 0.02`
survives by 0.01 — the floor sits exactly where the dead-tape cohort ends.

### Honest limitations
- **It would have changed nothing today.** All 55 of today's dead-tape candidates were
  already refused on confidence. This is a fix for the *residual leak* — setups that clear
  60 despite a dead tape — not for today's zero-trade outcome.
- **It cuts trade frequency a further ~25%** (90d: 76→60) on a book whose frequency is
  already the standing concern. That is defensible only because the removed trades have
  negative expectancy and contain zero winners, and it is recorded here as a cost, not
  hidden. The frequency question itself is escalated separately — see `todo.md` and
  today's daily entry on the `ENTRY_THRESHOLD` renormalisation.
- n is small in absolute terms (10–60 trades/window). The four windows overlap heavily and
  are **not** independent samples.

### Tests
**558 pass (+8).** `test_dead_tape_clears_the_total_bar_without_the_floor` pins the
premise (the 09-11 INTC tape scores 85.0 total with `conf_volatility` 0.00 and enters
without the floor — the regression this exists to prevent);
`test_min_volatility_floor_blocks_dead_tape_entry` pins the fix on that same recorded
scenario; plus floor-disabled, live-tape-unaffected, reason-precedence, sub-threshold
reporting, and `test_min_volatility_floor_never_admits_a_trade_the_baseline_refused`,
which asserts across an ATR sweep that the floor can only ever **reject** — never admit a
trade the baseline refused.

### Deployment
`chown ustradebot:ustradebot` on all five files, `systemctl restart ustradebot.service`,
verified `active (running)` with a clean startup and warmup. Preflight all-PASS (the one
WARN is "market closed", expected post-close). `.env` untouched.

- **Observed effect (weekly 09-18):** ✅ **VALIDATED, and re-confirmed on a 6× longer window
  than it shipped on.** The 09-16 leave-one-out sweep ran `MIN_VOLATILITY 0` over **90 days,
  friction on, doctrine scoring**: floor off = **74 trades / +$331.25 / PF 1.47 / 8 WINs**
  against a control of **58 / +$461.87 / PF 1.87 / 8 WINs**. The floor therefore buys **+28%
  net and +0.40 PF for 16 fewer trades and ZERO forgone WINs** — it removes only trades that
  were never going to reach +1R, which is exactly the claim it shipped on. Replicated at 30d
  (control +$133.00/2.93 vs floor-off +$75.75/1.60). The 09-15 QCOM counterexample does not
  generalise.
- **F+S share: UNMOVED — 100% this week, as for the prior four.** Stated plainly rather than
  spun. IMP-049 is the week's only behaviour-changing IMP and it did **not** move the failure
  share, because it *removes* unwinnable trades rather than converting them into WINs. It
  raises expectancy per trade while shrinking an already-critical sample: a real but strictly
  defensive gain, and one that deepens the sample problem this review has flagged for three
  weeks. Both halves of that are true and neither cancels the other.

---

## IMP-050 — the entry-filter stack becomes sweepable in the replay harness
**Date:** 2026-09-15 · **Commit:** (see below) · **Files:** `bot/replay.py`, `tests/test_replay.py`

### Why
The 09-11 weekly (grade D) escalated an operator decision whose recommended first step is a
**leave-one-out sweep of the entry filter stack** — `ENTRY_START`, the QQQ market gate, the
60 confidence threshold, the 0.25 crossover floor — noting that "none has ever been evaluated
jointly". The 09-14 daily added `MIN_VOLATILITY` (IMP-049) to that list with an explicit
instruction: "Sweep them **jointly**, not one at a time."

**That sweep could not be run.** `bot/replay.py` exposed the whole *exit* side
(`--trail-percent`, `--take-profit`, `--stop-loss`, `--slippage-bps`) and `--entry-start`,
but nothing for the four filters that decide whether a trade exists at all. Studying them
meant editing `.env` on the live host and restarting the service — which is why, across
seven weeks of asking, no such sweep exists.

Today made the gap concrete. The QQQ 5-min gate was open on **0 of 84** sampled candles and
`market_gate_open` was `False` on all 16 scored refusals, so the obvious question — "what
would this session have done without the gate?" — was unanswerable with the tooling on hand.

### What changed
Four override flags on `bot.replay`, following the exact env-var pattern the exit-side
overrides already use, each disabling at its documented sentinel:

- `--entry-threshold` → `ENTRY_THRESHOLD`
- `--min-crossover` → `MIN_CROSSOVER` (0 lifts the IMP-011 floor)
- `--min-volatility` → `MIN_VOLATILITY` (0 lifts the IMP-049 range floor)
- `--market-filter-symbol` → `MARKET_FILTER_SYMBOL` (`""` disables the IMP-022 gate, which
  then fails open per `StrategyEngine._market_gate_open`)

Plus a second header line echoing the resolved entry stack, because a leave-one-out sweep is
a pile of runs differing only in those four values and an un-self-describing run is
unattributable once it scrolls.

### Risk
**None to live trading.** Replay-only CLI plumbing: no strategy, sizing, risk or exit logic
was touched, no default changed, and a bare run reproduces the shipped config exactly (pinned
by `test_omitting_the_entry_flags_leaves_the_shipped_defaults`). This is deliberately a
*capability*, not a parameter tweak — the stop-exit doctrine's escalation trigger is active
(FAIL+SCRATCH 96.2% over 10 sessions, 3/3 over the last 3), which forbids shipping parameter
tweaks and asks for structural work and evidence instead.

### Validation
- **561 tests pass** (+3), preflight all-PASS.
- A test-isolation defect was caught and fixed during validation: `main()` applies overrides
  with a bare `os.environ[key] = value`, which pytest's monkeypatch does not revert unless it
  already owns the key. The first draft left `MARKET_FILTER_SYMBOL=""` set for the rest of the
  session and broke 12 unrelated strategy/warmup tests. `_claim_entry_env()` now hands those
  keys to monkeypatch first. Worth remembering: **env-var overrides in `main()` leak across
  tests unless claimed.**
- **First real sweep, 30d, friction on, doctrine scoring on:**

  | arm | trades | net | PF | WIN | true win% |
  |---|---|---|---|---|---|
  | control (as shipped) | 10 | **+$133.00** | **2.93** | 1 | 10% |
  | `--market-filter-symbol ""` | **24** | +$112.56 | 1.41 | **3** | 12% |
  | `--min-volatility 0` | 15 | +$75.75 | 1.60 | 1 | 7% |

### What this says (handed to the weekly, not acted on)
- **IMP-049 stands.** Floor off is worse on every axis that matters (+$75.75/PF 1.60 vs
  +$133.00/PF 2.93). Yesterday's change was correct.
- **The market gate is the volume constraint, and removing it is a real trade-off, not a
  free win:** 2.4x the trades and 3x the WINs — the evidence-generation the weekly says the
  bot can no longer produce — but PF collapses 2.93 → 1.41 and net falls. True win rate is
  ~flat (10% → 12%), which is the honest read: **the gate is not what is stopping this
  strategy from having an edge. It is what is stopping it from having a sample.**
- Complementary live finding (see today's daily review): of 110 v3-era scored refusals since
  08-27, **64.5% were refused into a closed gate**, and lowering `ENTRY_THRESHOLD` from 60 to
  45 admits **zero** additional trades while the floors are on. **The escalated threshold
  renormalisation is close to a no-op; the gate is the first axis that matters.**

- **Observed effect (weekly 09-18):** ✅ **VALIDATED — and it is the most valuable IMP of the
  week, because the sweep it enabled REFUTED the hypothesis this review had been leading with
  for three consecutive weeks.** The 09-11 weekly's #1 ask was built on the premise that four
  independently-justified filters had "jointly removed 97% of the trading" and that the stack
  had drifted the bot somewhere worse. IMP-050 made that testable for the first time; the
  09-16 sweep (90d, friction on, doctrine scoring) answered it: **every filter that moves
  anything moves it in the right direction**, and **ALL FIVE OFF = 320 trades, −$1,162.07,
  PF 0.67, true WR 5%**, replicated at 45d (165 trades, −$656.63, PF 0.63). **The
  over-filtering hypothesis is dead, and it was my own.** Recording that here rather than in a
  footnote is the point of the exercise.
- **The load-bearing number is the one nobody asked for: the WIN column is frozen at
  8 / 9 / 12 / 8 / 8 / 8 across all six leave-one-out arms.** Nothing in the entry *filter*
  stack changes how many trades reach +1R — the filters only change how much is lost on the
  rest. That is what moved the burden onto the signal itself and set up IMP-051.
- **F+S share: unmoved by design** (replay-only CLI plumbing; a bare run reproduces the
  shipped config exactly, pinned by test). The `MARKET_FILTER_SYMBOL` and `ENTRY_THRESHOLD`
  releases from the do-not-relitigate list are now **spent**: both survived the test they were
  released for and return to the frozen list.

---

## IMP-051 — 2026-09-17 (daily) — the replay harness reports the +1R ceiling

**`bot/replay.py`, `tests/test_replay.py`.** **Measurement change only** — no trading-path
file touched, no config key added, no constant fitted. `bot/replay.py` is a CLI module that
nothing in the service imports (verified), so the running bot's behaviour is byte-identical
before and after.

### The problem
The doctrine's WIN line is **+1R**. A trade whose peak never prints +1R **cannot be scored
a WIN by any exit rule** — so the share of entries that reach it is a hard ceiling on the
true win rate, and the gap between that ceiling and the realized true win rate is the only
part an exit change could ever recover. `bot/excursion.py` has computed exactly that ladder
since IMP-042, but only for the **live book**, which currently supplies **six** rows with a
usable MFE. Six trades carry no distribution worth reading.

So every exit verdict this bot has reached was decided without it. The **09-16** filter-stack
sweep observed the WIN count frozen at **8** across six leave-one-out filter arms and four
trail widths, and concluded *"the exit structure is not what is capping this strategy"* and
*"the +1R rate is a property of the 3-EMA ribbon crossover itself."* Both were **inferences
from a frozen count, not measurements of the ceiling** — the sweep never asked how many
entries reached +1R and were then given back, because the harness could not answer.

Today's INTC is the live case that forced the issue: entry 108.80, stop 106.59, **peak
110.76 (+1.80%, 0.887R)**, trailed out at 109.654 for **+0.386R**. The doctrine scores it
**SCRATCH**, which reads like an exit that gave a winner back. It was not: the peak never
reached +1R, and **no trail width, arming rule or target could have made it a WIN.** Without
the ladder beside it, that trade is misdiagnosed as a profit-capture failure and would have
pointed the next change at the exits.

### The change
1. **`SimTrade` records its excursion.** New `mfe_price` / `mae_price`, folded by
   `observe(high, low)`; `excursion_bar` reduces the holding window to the one `(high, low)`
   pair `bot.excursion.compute_excursion` already takes. The arithmetic is **reused, not
   restated**, so the replay ladder and the live ladder cannot drift apart.
2. **`SimBroker.on_bar` folds every held bar** — from the bar after entry through the bar
   that fills a leg. **The entry bar is deliberately excluded**: the fill is that bar's
   close, so crediting its high counts travel we did not own. That is the IMP-046 lookahead,
   and the ceiling is precisely the number it would inflate. The live ladder fetches
   `[entry_time, exit_time]` and *includes* the entry bar, so **replay's ceiling is the
   conservative of the two** — noted so the two are never read as identical measurements.
3. **`summarize()` prints the ladder** directly under the F+S line, via the existing
   `ceiling_table` / `format_ceiling`. Trades with no observed bar (same-bar round trips)
   are **dropped and counted**, never scored as a 0R peak — a fabricated zero would drag
   the ceiling down with rows that were never measured.

### Validation — 566 tests pass (561 before; 5 added)
Five new tests in `tests/test_replay.py`: excursion folds every held bar; the entry bar is
excluded; an unobserved trade is dropped from the ladder rather than defaulted; a +1R print
is counted; and **`test_todays_intc_is_a_ceiling_failure_not_an_exit_failure`** — today's
real trade, seeded from the **signal** price 108.77 so the harness derives the live
bracket's 106.59 stop to the cent, asserting the doctrine says SCRATCH **and** the ladder
says `CEILING: 0.0%` on the same summary. The failure that motivated the change is now a
regression test.

### The finding — and a correction to the 09-16 verdict
Baseline, friction on, shipped config, **two windows**:

| window | trades | true WR | **ceiling (+1R reached)** | **exit-recoverable** | entry-limited |
|---|---|---|---|---|---|
| **90d** | 60 | 13.3% | **23.3% (14/60)** | **10.0pp** | 76.7% |
| **45d** | 24 | 12.5% | **20.8% (5/24)** | **8.3pp** | 79.2% |

1. **09-16 was right that the entry is the dominant cap** — **77–79% of entries never print
   +1R at all**, and nothing done to the exits touches them.
2. **🔴 09-16 overstated it.** *"The exit structure is not what is capping this strategy"*
   is **refuted as written**: **6 of the 14 entries that reached +1R on 90d were given
   back** (2 of 5 on 45d). **~40% of the achievable WINs are lost after the trade is
   already right.** Replicated on both windows.
3. **The instrument that would bank a +1R print does not exist here.** `TAKE_PROFIT` is
   **10%**, and the exit-reason table confirms **zero target fills in 60 trades**:
   `trailing stop` n=22 **−$99.52** (the only losing bucket), `end-of-day flatten
   (trailing stop)` n=26 +$169.58, `end-of-day flatten` n=12 +$393.11. The bot has a stop
   and a clock.

### What this does NOT license
- **No config shipped tonight.** The escalation clause (F+S 4/4 = 100% over the last three
  sessions with trades) forbids parameter tweaks, and a reachable target needs its own
  multi-window validation. **Handed to the weekly as a proposal with numbers attached.**
- **A target near +1R would be scored WIN by the doctrine's first clause**, so it would
  raise the WIN count **partly by relabelling**. It is not *pure* relabelling — the ladder
  proves the travel was real — but the honest test is **expectancy and payoff**, with the
  WIN count read beside the ceiling and never alone. Recorded here so the next run cannot
  mistake a relabel for an edge.
- **Still not a reason to widen the trail.** 09-16 measured that as relabelling (stop rate
  79%→75% bought with full stops 2→5, F+S unmoved). Unchanged.

### The rule this establishes
**Any future entry-trigger change is judged on whether it raises the ceiling, not on net.**
If an earlier or pullback-based trigger does not move the +1R share, it does not work,
whatever its P&L says on one window.

- **Observed effect (weekly 09-18):** ✅ **VALIDATED — and it corrected a verdict I had
  written into last week's review as settled.** The 09-11 weekly declared, off IMP-048, that
  *"the exit side is now closed as an explanation."* IMP-051 measured the thing that claim was
  inferred from and the claim is **wrong as written**: on 90d the ceiling is **23.3% (14/60)**
  against a realized true WR of **13.3%**, so **6 of the 14 entries that DID reach +1R were
  given back — ~40% of the achievable WINs are lost after the trade is already right**
  (2 of 5 on 45d; replicated). **10.0pp of exit-recoverable headroom exists and I had
  declared it closed.** The entry remains the dominant cap (**77% of entries never print +1R
  at all**) — 09-16 was right about the direction and overstated the magnitude.
- **It also pre-empted a live misdiagnosis on the day it shipped.** 09-17's INTC peaked at
  **0.887R** and trailed out at +0.386R; scored SCRATCH, it reads like an exit that gave a
  winner back. The ladder shows the peak never reached +1R, so **no trail width, arming rule
  or target could have made it a WIN.** Without the ceiling beside it that trade points the
  next change at the exits, which is where three of the last five IMPs already went.
- 🔴 **The finding with the most headroom attached: `TAKE_PROFIT` is 10% and there were ZERO
  target fills in 60 trades.** Exit reasons: `trailing stop` n=22 **−$99.52** (the only losing
  bucket), `end-of-day flatten (trailing stop)` n=26 +$169.58, `end-of-day flatten` n=12
  +$393.11. **The bot has a stop and a clock, and no instrument capable of banking a +1R
  print.** Handed to next week as the #1 candidate — see the weekly's Focus, including why it
  must be judged on expectancy and payoff rather than on the WIN count it would partly
  relabel.
- **F+S share: unmoved by design** (measurement-only; `bot/replay.py` is imported by nothing
  in the service).

---

## IMP-052 — 2026-09-18 (daily) — the refusal cohort is scored on the +1R WIN line

**`bot/refusals.py`, `tests/test_refusals.py`.** **Measurement change only.** No trading-path
file touched, no config key added, no constant fitted, no default changed. `bot.refusals` is
imported by **`bot/report.py` and the tests only** — verified at runtime that neither
`bot.main` nor `bot.strategy` loads it — so the running service's behaviour is byte-identical
before and after.

### The problem
The doctrine's WIN line is **+1R**. The refusal study (IMP-033) measures the population an
entry-filter change would admit, and reported it entirely in **percent**: `<0.5%MFE`,
`hitTrail` (MFE ≥ the 1.25% trail give-back), `stopped`. On a flat 2% stop, **`hitTrail` is
0.625R** — it counts candidates that could have banked *something*, never candidates that
would have been WINs, and nothing printed beside it said so.

That mattered tonight specifically. **This table is the evidence base for the one decision
still open on this bot** — whether to loosen the market gate — and the weekly review that
owns that decision runs **one hour after this routine**.

**2026-09-18 is the case that forced it.** Zero trades; the gate refused **5** candidates that
had already cleared `ENTRY_THRESHOLD`. The table read `hitTrail 3/5` for the gate cohort and
`9/31` overall, and named HOOD (15:13, conf 69.4) as the best declined at **MFE +1.88%**. That
reads like three trades the gate cost us. In R it is **0.94R**, and **0 of 31** refusals that
session reached +1R at all — so **no exit rule could have scored a single one a WIN.** The
filters cost **zero WINs**, and the report as written would have been quoted to argue the
opposite.

### The change
1. **`peak_r(mfe_pct, stop_loss)`** — one function, so the doctrine's line is derived in a
   single place. Exact arithmetic, not an approximation: the bracket stop is a flat fraction
   of entry, so 1R *is* `stop_loss` percent of it. Guards `stop_loss <= 0`.
   **Documented assumption:** if an ATR-scaled stop ever ships (open in `todo.md`), R stops
   being a constant fraction of price and this must take the per-candidate stop width — the
   refusal rows would then need to carry it. Every count below inherits that.
2. **`ReasonStats.reached_1r`** — MFE ≥ 1R per cohort, beside the existing columns rather than
   replacing them. The percent columns are still true and still useful; they were just never
   the WIN line.
3. **`format_refusals`** gains a `>=1R` column, renders **best declined in R** ("+1.88%
   (0.94R)"), prints a **`CEILING:`** line stating the share that reached +1R — and when that
   share is zero says so in words: *"the filters cost ZERO doctrine WINs. Loosening any of
   them buys sample, not edge."* A closing **`NOTE`** states that `hitTrail` is 0.62R and
   **below** the WIN line, so the old column can no longer be misread in isolation.

Deliberately **not** bundled: the refusal counterfactual includes the refusal candle's own bar
(the IMP-046 lookahead IMP-051 excluded for replay). I measured it on today's rows — the
session MFE fell well after the refusal bar in **every** case, `incl == excl` to the cent — so
it is immaterial here and fixing it tonight would be a second, unjustified change.

### Validation — 572 tests pass (566 before; 6 added), preflight all-PASS
`tests/test_refusals.py`: `peak_r` exactness (2.0%→1.0R, 1.88%→0.94R, 1.25%→0.625R) and its
zero-stop guard; `reached_1r` counts the WIN line not the trail (a candidate at exactly 1R
counts, one at 1.99% does not, both clear `hitTrail`); both `CEILING:` renderings; and
**`test_todays_hood_gate_refusal_hit_the_trail_and_still_missed_the_win_line`** — today's real
refusal (118.33 → 120.56 → 118.85) asserting `reached_trail == 1` **and** `reached_1r == 0` on
the same cohort. The misreading that motivated the change is now a regression test.

### The finding — two windows, and it does not all point one way
| window | cohort | n | hitTrail (0.625R) | **>= +1R** | max R |
|---|---|---|---|---|---|
| 10d | gate | 10 | 4/10 (40.0%) | **0/10 (0.0%)** | 0.94R |
| 10d | ALL | 269 | 35/269 (13.0%) | **4/269 (1.5%)** | 1.50R |
| **30d** | **gate** | 43 | 15/43 (34.9%) | **7/43 (16.3%)** | **2.32R** |
| 30d | confidence | 526 | 55/526 (10.5%) | **8/526 (1.5%)** | 1.50R |
| 30d | ALL | 645 | 77/645 (11.9%) | **16/645 (2.5%)** | 2.32R |

1. **The old proxy overstated the doctrine-recoverable population by ~5–8×.**
2. **The confidence floor is exonerated on both windows (1.5%).** Third independent
   refutation (09-15 live, 09-16 replay, tonight). **That question is closed.**
3. ⚠️ **The gate is the only cohort declining real +1R candidates (16.3% on 30d, >10× the
   confidence cohort) — but it is regime-unstable (0/10 on 10d), and 16.3% is BELOW the taken
   book's own 23.3% (90d) ceiling from IMP-051.** So opening the gate would add WIN-capable
   candidates *at a worse rate than the book already achieves* — a coherent mechanism for
   IMP-050's PF collapse (2.93 → 1.41). Under IMP-051's standing rule (an entry change is
   judged on whether it raises the ceiling), **opening the gate does not clear the bar.**

### Expected impact
No P&L effect by construction. It removes a **5–8× overstatement** from the one table the
open gate decision rests on, closes the `ENTRY_THRESHOLD` question with a third measurement,
and gives the weekly a ceiling-based answer on the gate one hour after this run.

### What this does NOT license
- **No config shipped.** Escalation is active (F+S 96% / 10 sessions, 100% / last 3) and
  forbids parameter tweaks. This is structural measurement, the same lane as IMP-050/051.
- **Not a reason to open the gate** — the measurement argues *against* it (point 3).
- **Not a reason to tighten the gate either.** 16.3% > 0 means the gate does decline some real
  +1R travel; it is not free. Tightening it further on this evidence would be overfitting to
  one quiet triple-witching session.

### Commit
- **Commit:** 9c937f8
- **Observed effect (weekly 09-18, written ~45 min after it shipped):** ✅ **VALIDATED on its
  own terms; too new for live evidence, and it does not need any.** It is a reporting change
  to a module the service does not import, and its claim is arithmetic: on a flat 2% stop
  `hitTrail` is **0.625R**, i.e. **below the WIN line**, so the column could never have
  counted WINs. **It landed one hour before the decision it existed to inform** — whether to
  open the market gate — and it changed that decision's evidence base by **5–8×**: recoverable
  population 13.0% → **1.5%** on 10d and 11.9% → **2.5%** on 30d.
- **The gate decision it enabled, resolved by this weekly: DO NOT OPEN THE GATE.** The gate is
  the only cohort that declines real +1R candidates (**16.3% on 30d**, >10× the confidence
  cohort's 1.5%) so it is genuinely not free — but 16.3% sits **below the taken book's own
  23.3% ceiling** (IMP-051). Opening it therefore buys sample at a **worse** +1R rate than
  what the bot already trades, which is a coherent mechanism for IMP-050's measured result
  (gate off → 2.4× trades, PF **2.93 → 1.41**). Per IMP-051's standing rule — entry changes
  are judged on whether they raise the ceiling — **it does not clear the bar.** The daily's
  recommendation is endorsed and **this operator item is now closed, not deferred.**
- **Also closed by it: lowering `ENTRY_THRESHOLD`.** Third independent refutation in four days
  (09-15 live: 60→45 admits 0 trades; 09-16 replay: 0 additional WINs; 09-18: the cohort
  reaches +1R **1.5%** of the time). Returns to the do-not-relitigate list permanently.
- **F+S share: unmoved by design.** Measurement-only, verified byte-identical service
  behaviour.

---

## IMP-053 — 2026-09-21 (daily) — the replay ceiling declares when a target has censored it

**`bot/replay.py`, `tests/test_replay.py`.** **Measurement change only.** No trading-path
file touched, no config key added, no constant fitted, no default changed. Re-verified at
runtime tonight that importing `bot.main`, `bot.strategy`, `bot.risk` and `bot.report`
does **not** load `bot.replay` — the running service's behaviour is byte-identical before
and after. The only non-test importer of `bot.replay` is its own `__main__`.

### The problem
The IMP-051 ceiling ladder measures how far an entry travelled, from the bars observed
**while the position was held**. A target ends the holding window. So under a reachable
target the ladder stops observing exactly where the target sits: **the exit truncates the
travel the ladder exists to measure**, and it truncates it at the level of the very
parameter under test.

This is circular in the worst possible place, because `format_ceiling` states its
conclusion in absolute terms — *"no exit change can lift the true win rate above that"* —
and IMP-051 established the standing rule that **entry changes are judged on whether they
raise the ceiling**. A censored ceiling silently corrupts the one number that governs the
only decision this bot has left.

**Tonight's sweep is the case, and the error is not small.** Same 30d window, same entry
stack, same cohort:

| run | ceiling (+1R) | the three furthest-travelling entries, in R |
|---|---|---|
| shipped 10% target | **23.1%** | 1.742R / 1.277R / 1.163R |
| 1R (2%) target | **0.0%** | 0.942R / 0.925R / 0.913R |

Every one censored to just under the WIN line **by its own take-profit fill**. Read
literally, the second run says the entry signal never travels and no exit can help — the
exact opposite of what those trades did on the tape. The corrupted run even printed
`realized true win rate 21.4% vs ceiling 0.0% -> -21.4pp is exit-recoverable`, a negative
recoverable share, which is arithmetically impossible and was the tell.

This is the same class of defect as IMP-052 (a proxy misread by 5–8×) and it would have
been read by the next agent to repeat tonight's sweep.

### The change
1. **`censoring_note(trades, stop_loss)`** — one pure function. Returns `""` when no
   target filled, so an untargeted run renders **exactly** as before. Otherwise it reports
   how many trades exited at a target and the **minimum** target R across them (the
   binding level), and states that rungs at or above it are a **lower bound on entry
   travel, not a measurement**, and that the ceiling is **not comparable** with a run whose
   target was never reached.
2. Target fills are identified through **`bot.doctrine.resolve_reason`** — the same
   resolution the doctrine block on the line above uses — so the two blocks cannot disagree
   about which leg filled.
3. The level is computed in **R of the filled entry**, which surfaced a second trap worth
   its own line: at the shipped 10 bps/side friction a **nominally-1R target sits at
   ~0.90R**, i.e. *below* the doctrine's WIN line, while the first clause ("a take profit
   fill") still scores it a WIN. A 1.0R target manufactures WINs that are realized
   SCRATCHes. The note prints that level, so it can no longer go unnoticed.

### Validation — 575 tests pass (572 before; 3 added), preflight all-PASS
`tests/test_replay.py`:
- `test_no_censoring_note_when_no_target_filled` — the silence guarantee for every
  existing run.
- **`test_todays_intc_under_a_1r_target_reads_as_a_zero_ceiling`** — today's real INTC
  trade (signal 121.31, bracket stop 118.88, ran to 124.68 = **1.27R** against the filled
  entry, trailed out at 123.48) re-run with a 1R target. The target fills at 123.74 on the
  way up, the 124.68 bar is **never observed**, and the ladder reports `CEILING: 0.0% of
  entries ever print +1R` for a trade that printed 1.27R — while the doctrine scores it
  `WIN 1` off a target that banked ~0.90R. Both halves of the trap, pinned on live data.
- `test_censoring_counts_only_the_legs_that_actually_filled_a_target` — today's AMD
  (trailed out at 607.75, never near its target) censors nothing; resolution is by price,
  not by config.

Verified live on a real `--days 30 --take-profit 0.02` run: the warning fires and names
the 0.90R level.

### Why this and not the target itself
Tonight's licensed change was the weekly's #1, a reachable `TAKE_PROFIT`. **I tested it and
it is refuted** — 3 windows × 4 target levels, friction on, doctrine scoring: true win rate
rises monotonically as the target tightens (90d: 12.9 → 42.4%) while **expectancy, PF and
payoff fall monotonically** (90d exp +8.06 → +5.48, PF 1.90 → 1.61, payoff 1.67 → 1.35).
The best variant (1.25R) is expectancy-neutral at best and **loses PF on all three
windows**. The weekly's own acceptance rule — *reject if expectancy or payoff falls* —
rejects it. Full table in tonight's `memory/daily-review.md`.

So the shipped change is the instrument that makes that refutation **safe to reproduce**.
Without it, the next agent runs the same sweep, reads `ceiling 0.0%`, and concludes the
entry signal collapsed under a target. The measurement lane is also the only lane the
escalation clause leaves open (F+S 95.7% / 10 sessions, 100% / last 3) — same lane as
IMP-050/051/052.

### Expected impact
No P&L effect by construction. It closes the weekly's #1 with a measurement instead of a
deferral, removes a defect that inverts the ceiling's meaning under exactly the experiment
the weekly ordered, and prices targets in R of the *filled* entry so friction can no longer
hide below the WIN line.

### What this does NOT license
- **No config shipped**, and none may be: escalation is active and forbids parameter
  tweaks. This is structural measurement.
- **Not a reason to ship any target**, at any level — the sweep argues against all of them.
- **Not a reason to touch the trail.** INTC gave back exactly the 1.00% tightened trail
  width tonight, which is the trail working as designed; width is on the frozen list and
  widening is forbidden by the doctrine irrespective of P&L.
- **Not an exoneration of the exits in general** — only of this instrument.

### Commit
- **Commit:** d504ae1
