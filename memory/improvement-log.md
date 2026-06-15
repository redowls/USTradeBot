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
- **Observed effect:** (pending — confirm clean single-pass flatten at tomorrow's 06-16 close)

---
