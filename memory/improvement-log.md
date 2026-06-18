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
  fixed). IMP-001 holds; IMP-002 addresses the new mode.

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
  the *carry* is the realized cost of that outage.

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
- **Commit:** (filled below)
- **Observed effect:** (pending — confirm Monday 06-22 that any unfilled close logs a failed-close
  ERROR + NAKED page and writes NO CLOSED row, and that a normal RTH exit still records cleanly.)

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
- **Observed effect:** (pending — confirm at the next session that an intraday stop-out is
  recorded as CLOSED in the DB at its broker fill, with no `could not close position` ERRORs.)

---
