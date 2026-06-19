# Research Log

Pre-market watchlist research journal for USTradeBot. **One dated entry per day**,
written by the `ustradebot-premarket` routine (11:30 UTC, Mon–Fri) after reviewing
news + technical charts for every watchlist symbol and applying changes to
`dbo.watchlist` in the USBot database.

Hard rules the routine must never break:
- NEVER park/remove a symbol that has an open position in the Alpaca account.
- Max **30 enabled** symbols.
- Every added symbol must be verified tradable & active on Alpaca (`/v2/assets/{SYM}`).
- Park with `enabled = 0` (keep the row) instead of DELETE.

Entry template:

## YYYY-MM-DD — Pre-market Research

### Market context
(futures, key news, earnings today, sector momentum)

### Carried from daily review
(watchlist observations from memory/daily-review.md acted on today)

### Watchlist review
(symbols reviewed: news + technical verdict; keep / park / add candidates)

### Changes applied to dbo.watchlist
(exact adds/parks/re-enables with one-line reasons; "no changes" is a valid outcome)

### Final watchlist
(N enabled symbols, listed; service restarted: yes/no)

---

## 2026-06-13 — Pre-market Research

First run of this routine. Note: today is Saturday; next session is **Monday 2026-06-15**
(this entry prepares Monday's open).

### Market context
- Volatile Iran-headline week: big drops Jun 9–10 on strike fears, +1.75–3% rally Jun 11
  on de-escalation hopes, mixed/choppy Friday Jun 12 (S&P flat, Dow +0.6%, Nasdaq −0.3%).
- SpaceX (SPCX) IPO debuted Fri +19% to $160.95 — largest IPO ever ($75B), now ~$2.1T cap.
  Watching as a future candidate once it has trading history; too new for the ribbon now.
- Week ahead: light earnings (ACN/KR Thu, KMX Wed — none on our list). Macro-heavy:
  industrial production Mon, **FOMC decision Wed Jun 17**, retail sales Wed,
  **market closed Fri Jun 19 (Juneteenth)**. Oil fell Friday on peace-deal prospect —
  energy momentum fading.

### Carried from daily review
None — memory/daily-review.md is template-only (routines went live today).

### Watchlist review
Account: ACTIVE, equity $9,416.79, **no open positions** (no locked symbols).
26 enabled symbols reviewed against 60-day Alpaca bars (trend vs 20/50MA, 15d ATR%,
20d avg dollar volume) + 14d closed-trade P&L from dbo.trades:
- Clean uptrends, liquid: AMD (+6/+32 vs 20/50MA), INTC (+10/+30), MU (+10/+45, best
  P&L +$83), C, JPM, UNH, TSM — core keeps.
- Broad market dip names (AAPL, AMZN, GOOG, MSFT, NVDA, QQQ, SPY, TSLA, etc.): below
  20MA from the Iran selloff but mega-liquid; kept — regime, not symbol, problem.
- **WPM**: lowest dollar volume on list (~$237M/day), −6%/−12% vs 20/50MA, zero
  signals in 14d → PARK.
- **ENPH**: 10.9% ATR (extreme whipsaw, −9% vs 20MA yet +22% vs 50MA), zero trades
  in 14d; unsuited to a ribbon-trend strategy → PARK.
- Watch (kept, on notice): NVDA 0/3 trades −$54 in 14d; AVGO −$74 (1/2) and −9% vs
  20MA with 6.5% ATR; SE third-lowest liquidity ($321M) in a downtrend.
- No watchlist name reports earnings next week; no binary events besides FOMC Wed.

### Changes applied to dbo.watchlist
- PARK WPM (enabled=0): downtrend, lowest $vol, no signals 14d.
- PARK ENPH (enabled=0): 10.9% ATR whipsaw, too choppy for ribbon, no trades.
- No adds — FOMC week, list already broad; no high-conviction candidate (SPCX too new).

### Final watchlist
24 enabled: AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA
QCOM QQQ SE SPY TSLA TSM UNH WMT XOM. Service restarted: yes — active, clean startup,
24-symbol subscribe confirmed in journal. (Side note for daily review: pre-restart log
shows a Jun 12 20:57 APIError "order is not open" during an exit — worth a look.)

---

## 2026-06-15 — Pre-market Research

### Market context
- **US–Iran ceasefire relief rally.** Deal announced late Sunday; Nasdaq-100 futures
  +1.9%, S&P +1.2%, Dow ~+1%. VIX ~16.8 (−14%). Risk-on: gold + Bitcoin up, dollar down.
- **Oil crashed** on the Strait of Hormuz reopening: WTI −5.5% to ~$80, Brent ~$83
  (3-month low). Energy is the day's laggard — direct negative for XOM.
- Week ahead unchanged: light earnings (none of ours; ACN/KR Thu), **FOMC Wed Jun 17**
  is the hawkish wildcard, **market closed Fri Jun 19 (Juneteenth)**. Short week.
- Risk-on tape favors semis/AI (most of our list) and travel/airlines on cheaper fuel.

### Carried from daily review
None — memory/daily-review.md is still template-only (no daily-review entries yet).

### Watchlist review
Account ACTIVE, equity $9,416.76, **0 open positions** (no locked symbols). 24 enabled
reviewed vs 60-day Alpaca bars (through Fri 06-12 close, pre-rally) + 14d closed-trade P&L:
- 14d P&L leaders: MU +$83, INTC +$62, QQQ +$50, JPM +$28, QCOM +$25 — core keeps.
- Clean uptrends, liquid: AMD (+6/+32 vs 20/50MA), INTC (+10/+30), MU (+10/+45), C
  (+8/+10), JPM, UNH, TSM, QQQ, SPY — keeps.
- **XOM**: oil −5% to a 3-mo low on the ceasefire; already −3.2%/−3.2% vs 20/50MA
  (sustained mild downtrend), energy momentum flagged "fading" on 06-13. Long-only ribbon
  bot gets no clean longs in a fresh oil-driven downtrend, and a knife-catch bounce is the
  bad-trade risk → **PARK**.
- **NVDA** (0/3, −$54 in 14d): poor record was the Iran-selloff regime; most liquid name
  ($1.1B IEX $vol) and today's risk-on semis rally directly favors it → KEEP (regime, not
  symbol). On notice.
- **AVGO** (−$74 worst P&L, −8.8% vs 20MA weakest trend, 6.7% ATR): on notice since 06-13,
  but parking a semi right as semis rip on a relief rally is poor timing → KEEP, on notice
  one more session.
- SE/ABNB/BABA lowest IEX liquidity but all traded fine recently; no churn.
- No watchlist name reports earnings today; only binary event this week is FOMC Wed.

### Changes applied to dbo.watchlist
- PARK XOM (enabled=0): oil −5% to 3-mo low (Iran ceasefire), broken downtrend, no longs.
- No adds — list already broad and semi/index-heavy into a risk-on tape; no high-conviction
  new name (one-day ceasefire pops in airlines/travel aren't durable trends). FOMC Wed.

### Final watchlist
23 enabled: AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QCOM
QQQ SE SPY TSLA TSM UNH WMT. Service restarted: yes — active, clean startup, 23-symbol
subscribe confirmed in journal, 0 positions reconciled.

---

## 2026-06-16 — Pre-market Research

### Market context
- **FOMC eve.** Two-day meeting starts today; decision + projections **tomorrow Wed 06-17
  2pm ET** — Kevin Warsh's first meeting as Fed Chair. CME FedWatch prices **no cuts in 2026**;
  rates expected held but the statement language ("extent and timing of additional adjustments")
  and Warsh's tone are the binary wildcard. Futures flat-to-slightly-lower (Dow ~flat) ahead of it.
- **Monday 06-15 was a powerful risk-on rally** on the US–Iran ceasefire / Strait of Hormuz
  reopening: Nasdaq **+3.07%**, S&P **+1.65%**, Dow +0.92%. Oil fell to ~$80 (mid-April low);
  energy stays the laggard → XOM correctly parked, no missed longs.
- **No watchlist name reports earnings today** (light week; ACN/KR Thu). **Market closed Fri
  06-19 (Juneteenth)** — short, event-heavy week. AMD announced a small AI-memory acquisition
  (MEXT) — benign for a mega-liquid name, no halt risk. SPCX +8.9% pre-market but still too new
  for the ribbon. Gold/silver firm, dollar soft.

### Carried from daily review
06-15 daily-review "Notes for pre-market research" acted on:
- **XOM park looks right** (energy stayed weak on the oil drop) → keep parked.
- **GOOG over-traded** (bot stacked a 3rd low-conviction lot, −$15) — flagged as a *code/sizing*
  note, "not a watchlist change" → no action here.
- **Semis regime call paid off** (MU +$77 carried; AVGO behaved at +$5) → keep NVDA/AVGO/TSM.
- No symbol "never signaled"; list produces plenty of triggers → no park-for-inactivity.

### Watchlist review
Account ACTIVE, equity $9,384.87, **0 open positions** (no locked symbols). 23 enabled reviewed
against 14d closed-trade P&L from dbo.trades + the 06-15 risk-on/regime read:
- **14d P&L leaders:** MU +$159 (4 tr, 3W), INTC +$62, QQQ +$50, JPM +$28, QCOM +$25, ABNB +$15
  — core keeps; semis/index momentum intact.
- **Laggards:** AVGO −$69 (3 tr, 2W — losses front-loaded in the Iran selloff regime),
  NVDA −$54 (0/3), TSLA −$37, TSM −$9. NVDA/AVGO held on the explicit "regime not symbol" call
  from 06-13/06-15 — the AI/semis regime is now *working* (MU +$77 carried, AVGO +$5 on 06-15);
  parking the two most liquid semis the day before FOMC, mid-regime, would be poor timing → KEEP,
  on notice. TSLA/TSM mega-liquid, single bad trades, no trend break → keep.
- Lower-liquidity names (SE, ABNB, BABA) all traded fine recently (ABNB +$15, BABA +$7.5) → keep.
- No earnings on any name today; only binary event is FOMC tomorrow.

### Changes applied to dbo.watchlist
**No changes.** The list is broad (23), semi/index-heavy into a regime that's confirmed working,
carries zero earnings risk today, and the eve of a binary FOMC is the wrong time to churn or to
chase a momentum add. XOM/WPM/ENPH/BIRD stay parked. No high-conviction new name (SPCX too new).

### Final watchlist
23 enabled (unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QCOM
QQQ SE SPY TSLA TSM UNH WMT. Service **not restarted** (no watchlist change — bot reads the list
only at startup, so a restart would be pointless churn).

---

## 2026-06-17 — Pre-market Research

### Market context
- **FOMC decision DAY.** Statement + SEP/dot-plot at **2pm ET**, Warsh's first press conference 2:30pm.
  Hold is near-certain (CME FedWatch ~97%, range 3.50–3.75%); the binary wildcard is the **dot plot**
  (May CPI ran hot at 4.2% y/y → the single 2026 cut likely removed; ~70% odds of ≥1 *hike* by year-end),
  whether the **easing bias** is dropped, and Warsh's debut tone (regarded as hawkish). A hawkish print
  is specifically negative for high-multiple semis/AI.
- **Tape going in is split:** Tue 06-16 the **Dow closed at a record (>52,000)** while tech/Nasdaq
  slumped — value/cyclical rotation, growth on the back foot ahead of the print. Oil extended lower to
  **<$80 (WTI ~$78.7, first sub-$80 since March)** on the US–Iran ceasefire framework → energy stays the
  laggard, **XOM correctly parked**. 2-yr yield ~4.06%.
- **No watchlist name reports earnings today** (light week; ACN/KR Thu). **Market closed Fri 06-19
  (Juneteenth)** — short, event-heavy week.

### Carried from daily review
06-16 daily-review "Notes for pre-market research" acted on:
- **🔒 4 positions carried NAKED overnight** (EOD flatten failed on persistent Alpaca 504s): AAPL (7),
  ABNB (15), BABA (16), GOOG (4) — **broker-confirmed still open this morning**. Hard rule honored:
  **NOT parked**, all remain enabled. The startup reconcile will mark them MANAGING; the session will
  re-manage/flatten them (or `python -m bot.flatten --yes` once open if sooner is wanted). IMP-002
  shipped a critical Telegram page for a future failed flatten.
- **No entry-quality concerns** raised — 06-16's failure was broker-side (504s) + exit infra, not symbols.
- **BABA** the lone green open (+$12.4 at the close) — lower-liquidity but behaving; keep.

### Watchlist review
Account ACTIVE, equity **$9,347.37** (last_equity $9,392.88; the dip is the naked-overnight marks —
AAPL −$4.75, ABNB −$8.55, BABA −$15.87, GOOG −$8.32 unrealized). **4 open positions = locked.**
23 enabled reviewed vs 14d closed-trade P&L from dbo.trades (45 trades, net **+$201**):
- **14d P&L leaders:** MU +$159 (4 tr, 3W), INTC +$62, QQQ +$50 (2/2), JPM +$28, QCOM +$25, ABNB +$15,
  UNH +$9 — core keeps; semis/index momentum intact and the AI/semis regime is confirmed working.
- **Laggards:** AVGO −$69 (3 tr, 2W — one front-loaded Iran-selloff loser), NVDA −$54 (0/3), TSLA −$37,
  TSM −$9, C −$5.6, AMD −$4.9. All held on the standing **"regime not symbol"** call — the regime that
  produced those losses (Iran selloff) has reversed and is now paying (MU is the top earner). Parking
  the two most-liquid semis (NVDA/AVGO) mid-working-regime, on a binary FOMC day, is poor timing → KEEP,
  on notice. TSLA/AMD/TSM/C mega-liquid, single bad trades, no trend break → keep.
- Lower-liquidity names (SE +$2.5, ABNB +$15, BABA +$7.5) all traded fine recently → keep.
- No earnings on any name today; only binary event is FOMC at 2pm ET.

### Changes applied to dbo.watchlist
**No changes.** 4 names are locked (open positions, can't be parked); the list is broad (23) and
semi/index-heavy into a regime that's confirmed working; zero earnings risk today; and the **FOMC
decision is exactly the binary event you don't churn or chase a momentum add into** (same discipline as
06-15/06-16). XOM/WPM/ENPH/BIRD stay parked. No high-conviction new name.

### Final watchlist
23 enabled (unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QCOM
QQQ SE SPY TSLA TSM UNH WMT. Service **not restarted** (no watchlist change → restart would be pointless
churn). 🔒 Locked: AAPL ABNB BABA GOOG (open positions).

---

## 2026-06-18 — Pre-market Research

### Market context
- **Post-FOMC rebound, semis leading.** Wed 06-17's hawkish surprise (dot plot median to 3.8%,
  ~half the committee pencils a 2026 *hike*, Warsh's price-stability emphasis) sold stocks off
  (S&P −1.21%, Nasdaq −1.34%, worst new-chair "Fed day" since 1994). This morning futures
  **rebound**: S&P +0.9%, Nasdaq-100 **+1.6%**, Dow +0.6%. 2-yr yield ~4.22% (jumped +16bp Wed).
- **Chips rip on an Intel–Apple headline.** Trump said INTC will partner with AAPL on US chip
  design → **INTC +9% pre**, MU **+4.7%**, NVDA +1.2%, **SOXX +3.9%**. Directly favors our
  semi/AI-heavy list and AAPL — clean trending longs for the long-only ribbon if it holds.
- **No watchlist name reports earnings today.** Today's earnings are **ACN, KR** (neither ours).
  **Market closed Fri 06-19 (Juneteenth)** — today is the last session of a short, event-heavy week.

### Carried from daily review
06-17 daily-review "Notes for pre-market research" acted on:
- **No naked positions into 06-18** — broker confirmed **flat (0 positions)** this morning
  (equity $9,215.44 = last_equity, all 06-17 names exited cleanly broker-side). Nothing locked.
- **"Semis/megacap tape faded post-FOMC; watch for a fresh 5m trend before leaning in"** — noted,
  but this morning's tape has *reversed* bullishly on the INTC–AAPL news; the gate ribbon will
  confirm a real trend before any entry, so no symbol action needed.
- **"Late-day entries keep failing… Watchlist is fine; the issue is *when* we enter. Nothing to
  park for signal quality."** — explicit: no watchlist parks indicated. INTC kept (behaved well,
  trailed to a +$2.20 win). BABA/GOOG/AAPL/ABNB losses were the overnight carry, not the names.

### Watchlist review
Account ACTIVE, equity **$9,215.44**, **0 open positions** (no locked symbols). 23 enabled
reviewed vs 12d closed-trade P&L from dbo.trades (net **+$19.95**):
- **Leaders:** MU +$144 (5 tr, 3W), INTC +$64 (3 tr, 2W), QQQ +$50 (2/2), JPM +$28, QCOM +$25,
  UNH +$9, SPY +$6 — core keeps; semis/index momentum intact and *re-igniting* on today's tape.
- **Laggards:** AVGO −$69, TSLA −$57, NVDA −$54 (0/3, still never won), BABA −$36, GOOG −$33,
  TSM −$30, AAPL −$21. Every one is explained by the daily reviews as **regime (Iran selloff /
  FOMC fade) or the 06-16 naked-overnight carry — not signal quality.** All are mega-liquid (NVDA
  the most liquid name on the list) and today's semis rebound directly favors the AI/semi cohort;
  parking them into a bullish chip reversal would be exactly the bad timing prior runs warned of
  → KEEP, on notice. Single-bad-trade megacaps (TSLA/TSM/AAPL/C/AMD) show no trend break → keep.
- Lower-liquidity names (SE +$2.5, ABNB +$0.4, BABA) traded fine recently → keep.
- No earnings on any watchlist name today; FOMC (the week's binary event) is resolved.

### Changes applied to dbo.watchlist
**No changes.** The list is broad (23), carries zero earnings risk today, the binary FOMC event is
behind us, and the morning tape favors our semi/index-heavy roster (INTC–AAPL chip news). Every
laggard's losses are regime/overnight-carry per the daily reviews, none is a signal-quality or
liquidity park candidate, and no name "never signals." No high-conviction non-semi add, and we're
already heavily exposed to the leading sector — no churn for activity. XOM/WPM/ENPH/BIRD stay parked.

### Final watchlist
23 enabled (unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QCOM
QQQ SE SPY TSLA TSM UNH WMT. Service **not restarted** (no watchlist change → bot reads the list
only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-06-19 — Pre-market Research

**Run on Juneteenth — US market CLOSED today (Fri 06-19). This entry prepares the next
session, Monday 2026-06-22.** No restart/flatten attempted (orders can't fill while closed).

### Market context
- **Short holiday-shortened week behind us; hawkish-Fed overhang into Monday.** Warsh's
  first FOMC (06-17) held 3.50–3.75% but the dot plot leaned to *hikes* (9 officials see
  potential 2026 hikes), triggering a 06-17 selloff; 06-18 rebounded (Nasdaq-100 +1.6%) on
  the INTC–AAPL chip-design headline (INTC +9%, MU +4.7%, SOXX +3.9%). Tape stabilizing on
  lower oil (WTI <$80) + yield stabilization; 2-yr ~4.22%.
- **Semis remain the market's support beam** — the AI/semi regime our list is built around is
  working. Energy still the laggard (XOM correctly parked).
- **Monday 06-22 earnings:** AREC, EBF, FRVO, ICLR, POWW — **none on our watchlist** → no
  Monday earnings risk. Macro week is light post-holiday; a key inflation reading lands midweek.
- **⚠️ MU reports earnings Wed 06-24** (the week's marquee chip catalyst). MU is an **open/locked
  position** and a watchlist name — binary event risk midweek, but **not Monday's session** and
  cannot be parked while held. Flag for Tue/Wed daily-review to manage the MU lot before the print.

### Carried from daily review
06-18 daily-review "Notes for pre-market research" acted on:
- **🔒 7 positions OPEN/NAKED into 2026-06-22** (protective legs expired over the long weekend):
  **GOOG(5) INTC(16) MU(1) QQQ(1) SE(15) TSLA(4) TSM(4)** — broker-confirmed open this morning,
  ≈ +$36 unrealized. Hard rule honored: **NOT parked**, all remain enabled. Monday's startup
  reconcile marks them MANAGING; flatten via `python -m bot.flatten --yes` once the market opens
  if a clean book is wanted sooner (NOT possible today — market closed).
- **"Entry quality was fine — no watchlist parks indicated."** All 7 fresh lots signalled and
  filled cleanly on the bullish chip-news tape; the 06-18 book is corrupted (fake exits, IMP-004
  shipped to fix) but that is exit/flatten infra, **not** symbol/signal quality → no park action.
- **Late-session weak-xo entries** (QQQ conf 64/xo 0.04, SE conf 65/xo 0.07 at 19:35 UTC) flagged
  again — a *code* fix (wider flatten window = late-entry cutoff, candidate for daily-review), **not
  a watchlist change**.

### Watchlist review
Account ACTIVE, equity **$9,248.81** (cash −$1,426.58 from the held lots, BP $22,903). **7 open
positions = locked.** 23 enabled reviewed vs 14d closed-trade P&L from dbo.trades (NB: 06-18 rows
are unreliable pending Monday's book correction, so P&L read is directional only):
- **Leaders:** INTC +$207 (5 tr, 3W), MU +$152 (6 tr, 4W), QQQ +$51 (3/3), JPM +$28, QCOM +$25 —
  core keeps; semi/index momentum intact and re-igniting on the INTC–AAPL tape.
- **Laggards:** AVGO −$69 (2/3), NVDA −$54 (0/3, still never won), TSLA −$38, BABA −$36, GOOG −$25,
  AAPL −$21. Every one is regime (Iran selloff / FOMC fade) or 06-16/06-18 overnight-carry per the
  daily reviews — **not signal quality.** All mega-liquid; parking the most-liquid semis into a
  working semi regime is the poor timing prior runs warned of → KEEP, on notice.
- Lower-liquidity names (SE, ABNB, BABA) traded fine recently → keep.
- No Monday earnings on any watchlist name; MU earnings Wed 06-24 is the only binary flag (locked).

### Changes applied to dbo.watchlist
**No changes.** 7 names are locked (open positions, can't be parked); the list is broad (23 ≤ 30),
semi/index-heavy into a confirmed-working regime, carries **zero Monday earnings risk**, and the
daily review explicitly indicates no signal-quality/liquidity parks. No high-conviction new name to
add (and we're already heavily exposed to the leading sector — no churn for activity). XOM/WPM/ENPH/
BIRD stay parked. MU earnings (Wed) is a midweek manage-the-lot task, not a today park.

### Final watchlist
23 enabled (unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QCOM
QQQ SE SPY TSLA TSM UNH WMT. Service **not restarted** (no watchlist change; market closed today
anyway). 🔒 Locked: GOOG INTC MU QQQ SE TSLA TSM (7 open positions).

---
