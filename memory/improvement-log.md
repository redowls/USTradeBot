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
- **Commit:** f453a0a
- **Observed effect:** (pending — confirm the page fires if a flatten 504s again; otherwise
  confirm clean flatten at the 06-17 close)

---
