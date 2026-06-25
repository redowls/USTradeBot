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

## 2026-06-22 — Pre-market Research

**Verdict day** (per weekly review): the 7 naked lots carried over the Juneteenth weekend
should auto-flatten at the open via the still-live `accepted` 06-18 close orders, and IMP-004/
005/002 get their first live test. That is an **exit-infra/ops** matter — no watchlist action.

### Market context
- **Risk-off open.** US futures point **lower** on **renewed US–Iran tensions** (Trump
  threatened fresh strikes; Tehran reportedly suspended talks) → **oil higher**. First session
  back after Juneteenth (Fri 06-19 closed).
- **Backdrop:** hawkish Fed (06-17: 12-0 hold 3.50–3.75%, dot plot — 9/18 see ≥1 hike in 2026)
  + **PCE inflation report Fri 06-26** is the week's macro binary. Last week Nasdaq +2.43% led
  by semis on the **INTC–Apple chip-design** headline (INTC +10.6%, MU +8.5%, NVDA +2.8% Thu).
- **Earnings this week:** CCL & FDX Tue, **MU Wed 06-24**, PAYX & TCOM Wed. **No watchlist name
  reports today.** Only MU (Wed) is on our list — and it's a **locked held lot**.

### Carried from daily review
06-19 daily-review "Notes for pre-market research" acted on:
- **🔒 7 positions OPEN/NAKED into today:** GOOG(5) INTC(16) MU(1) QQQ(1) SE(15) TSLA(4) TSM(4)
  — broker-confirmed open this morning (equity $9,354.97 vs last_equity $9,248.81, **+$106 as
  the carried lots marked up**; net unreal ≈ +$139: INTC +$64.5, TSM +$54.1, MU +$49.6 lead,
  GOOG −$27.6 the laggard). **Hard rule honored: NOT parked, all remain enabled.** The live
  06-18 `accepted` close orders should auto-flatten them at 09:30 ET — leave them, do NOT cancel.
- **"Entry/symbol quality is NOT the issue"** — all 7 signalled/filled cleanly; the open book is
  exit-infra residue, not signal quality → **no parks indicated.**
- **⚠️ MU earnings Wed 06-24** flagged: MU is a held lot + watchlist name; binary risk **midweek,
  not today**, and cannot be parked while held → carry the flag to Tue/Wed daily-review.

### Watchlist review
Account ACTIVE, equity **$9,354.97**, cash −$1,426.58 (margin from held lots), BP $23,217.51.
**7 open positions = locked.** 23 enabled reviewed vs 14d closed-trade P&L from dbo.trades (NB:
06-18 rows still over-state P&L pending the Monday book correction → directional read only):
- **Leaders:** INTC +$207 (5 tr, 3W), MU +$152 (6 tr, 4W), QQQ +$51 (3/3), JPM +$28, QCOM +$25 —
  core keeps; semi/index momentum is the regime our list is built around.
- **Laggards:** AVGO −$69 (2/3), NVDA −$54 (0/3, still never won), TSLA −$38, BABA −$36, GOOG −$25,
  AAPL −$21. All explained by the daily reviews as **regime (Iran selloff / FOMC fade) or
  overnight-carry**, not signal quality; all mega-liquid. Parking the most-liquid semis mid-regime
  on a risk-off day is the poor timing prior runs warned of → KEEP, on notice.
- Lower-liquidity names (SE, ABNB, BABA) traded fine recently → keep.
- **XOM (parked):** renewed Iran tensions bid oil up this morning, but that's a one-headline pop,
  not a durable energy uptrend — same discipline as before, **stays parked** (no knife-catch long).
- No earnings on any watchlist name today; only binary events are MU (Wed) + PCE (Fri).

### Changes applied to dbo.watchlist
**No changes.** 7 names are locked (open positions, can't be parked); the list is broad (23 ≤ 30)
and semi/index-heavy into a confirmed-working regime; **zero earnings risk today**; and a risk-off
open on renewed Iran tensions is the wrong tape to chase a momentum add into (oil's pop is one
headline, not a trend → XOM stays parked). Daily reviews explicitly indicate no signal-quality/
liquidity parks. XOM/WPM/ENPH/BIRD stay parked. MU earnings (Wed) is a midweek manage-the-lot task.

### Final watchlist
23 enabled (unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QCOM
QQQ SE SPY TSLA TSM UNH WMT. Service **not restarted** (no watchlist change → bot reads the list
only at startup, so a restart would be pointless churn). 🔒 Locked: GOOG INTC MU QQQ SE TSLA TSM
(7 open positions).

---

## 2026-06-24 — Pre-market Research

**MU park day.** The carried 06-19/06-22/06-23 instruction was explicit: today's pre-market
routine **MUST park MU** before the open because MU reports earnings **after today's close**
(binary event). Book is clean & flat (0 positions), so MU is **not locked** → free to park.
This is the day's one decided action.

### Market context
- **Futures mixed after a Tuesday semi rout.** Tue 06-23 saw a tech/semiconductor-driven
  selloff (S&P **−1.44%**, Nasdaq **−2.21%**) — South Korea's chip-heavy KOSPI fell ~10%, a
  BofA rate-hike note and AI/semi-valuation fears hit the sector. This morning stabilizes:
  S&P futures +0.1%, **Nasdaq-100 +0.5%**, Dow −0.2%. Memory/chips bounce pre-market (MU
  +4.1% after −13% Tue, SanDisk +3%, **INTC +1%**, **QCOM +2.2%**, DRAM ETF +4%). KOSPI
  rebounded +3% overnight.
- **⚠️ MU reports earnings after today's close** (confirmed; consensus ~$20.2–20.8 EPS on
  ~$33.5–35.7B rev). Options price a **~14–17% post-print move** on a name up 244% YTD past a
  $1T cap — a textbook binary overnight event. Given the flatten-reliability history (now fixed
  but only one clean session), **carrying MU overnight into the print is unacceptable → PARK.**
- **Other earnings today:** PAYX, JEF, LEVI — **none on our watchlist**. Macro: May new-home
  sales, Fed stress-test results. Oil eased again (**WTI ~$72**) on US–Iran diplomacy → energy
  the laggard, **XOM stays parked**. May **PCE Thu 06-25** is the week's next macro binary.

### Carried from daily review
06-23 daily-review "Notes for pre-market research" acted on:
- **Book CLEAN & FLAT into 06-24** — broker-confirmed **0 positions**, equity $9,314.69 all
  cash, 0 DB-open rows. **Nothing locked**; MU is a watchlist name only (not a held lot) → the
  hard "never park a held name" rule does **not** apply, MU is parkable.
- **"The Wed pre-market routine MUST PARK MU before Wed's open so the bot cannot hold it into
  the after-close print"** — **ACTIONED today** (the sole change this run).
- **"Entry/symbol quality fine; no parks on quality grounds"** — honored; only MU parked, and
  for *event* risk, not signal quality. GOOG/UNH/JPM (06-23's flat 0/3) were a news-quiet tape.
- **IMP-005/007 EOD flatten validated live 06-23** — exit infra now trustworthy; no watchlist action.

### Watchlist review
Account ACTIVE, equity **$9,314.69** (=last_equity), all cash, **0 open positions = nothing
locked.** 23 enabled reviewed vs 14d closed-trade P&L from dbo.trades:
- **Leaders:** INTC +$206.5 (5 tr, 3W), MU +$152 (6 tr, 4W), QQQ +$51 (3/3), AMD +$39, JPM +$26,
  QCOM +$25 — the semi/index regime the list is built around; chips bounce pre-market today.
- **Laggards:** AVGO −$69 (2/3), NVDA −$54 (**0/3, still never won**), BABA −$36, GOOG −$29,
  AAPL −$21, TSM −$13. Per the daily reviews every one is **regime (Iran selloff / FOMC fade /
  overnight-carry), not signal quality**; all mega-liquid. The list is semi-heavy into a volatile
  semi tape, but the long-only 5m gate simply won't fire longs in a downtrend (fewer entries, not
  bad ones) — **no signal-quality park**, KEEP on notice. Parking the most-liquid semis as they
  bounce off a one-day rout is the poor timing prior runs warned of.
- Lower-liquidity names (SE +$2.25, ABNB +$0.38, BABA) traded fine recently → keep.
- **Only MU reports earnings today** of all watchlist names → the single event-risk park.

### Changes applied to dbo.watchlist
- **PARK MU** (enabled=0, note "earnings after close today (~17% implied move), no overnight
  binary hold"). MU is not held → parkable; this is the pre-flagged required action.
- **No other changes.** A volatile, semi-rout-rebound tape on a binary-event day is the wrong
  time to churn or chase a momentum add; every laggard is regime/carry per the dailies, none a
  liquidity/signal park. XOM/WPM/ENPH/BIRD stay parked. **Re-enable MU on the 06-25 routine**
  once the print is digested (it's a top-2 earner — park is event-driven, not a demotion).

### Final watchlist
**22 enabled** (MU parked): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT NFLX NVDA
QCOM QQQ SE SPY TSLA TSM UNH WMT. Service **restarted: yes** — active, clean startup 11:32 UTC,
warmup 22/22 from history, account ACTIVE equity $9,314.69, 0 positions reconciled, 22-symbol
subscribe confirmed in journal (no MU). 🔒 Locked: none (0 open positions).

---

## 2026-06-23 — Pre-market Research

**First clean-and-flat morning in 12 sessions** — broker holds 0 positions, equity all cash.
Nothing locked; full watchlist free to trade. IMP-007 (wall-clock EOD-flatten watchdog) gets
its first live test at *tonight's* close — an exit-infra/ops matter, not a watchlist action.

### Market context
- **Light, news-quiet Tuesday.** No major economic releases and **no watchlist name reports
  today.** FedEx (FDX) reports **late Tue** and Micron (**MU**) **late Wed 06-24** — both
  after-close, neither today. **May PCE Thu 06-25** is the week's macro binary.
- **Hawkish-Fed overhang persists.** After 06-17's hawkish hold, short-end yields kept climbing;
  CME FedWatch now prices **~70% odds of a rate *hike* by September**. Last week S&P **+0.93%**,
  Nasdaq **+2.4%**, led by chips on the INTC–Apple chip-design theme.
- **Chips firm again pre-market** (Nasdaq tailwind) — directly supports our semi/AI-heavy roster.
  Oil **<$77** (Iran–US peace-talk progress) → energy still the laggard, **XOM stays parked**.
  **GOOGL −2% pre** on a report a DeepMind scientist is leaving for Anthropic — a mild,
  non-binary talent-headline, not an earnings/halt event.

### Carried from daily review
06-22 daily-review "Notes for pre-market research" acted on:
- **Book CLEAN & FLAT** (0 broker positions, 0 DB-open rows, equity $9,321.12) — **nothing
  locked**, no carried lots, no phantoms. No park/keep constraints inherited.
- **⚠️ MU earnings late Wed 06-24** — MU is a watchlist name (no longer a held lot). Reports
  **after Wednesday's close**, so **today (Tue) carries zero MU earnings risk → KEEP MU today.**
  The **Wed 06-24 pre-market routine MUST park MU** before Wed's open so the bot can't be holding
  it into the after-close print (the recurring flatten-reliability risk makes carrying a
  binary-event name overnight unacceptable). Flagged, not actioned today.
- **"Entry/symbol quality unchanged; no parks indicated on quality grounds"** — honored.
- **06-23 is IMP-005/007's first live flatten test** — ops/daily-review matter, no watchlist action.

### Watchlist review
Account ACTIVE, equity **$9,321.12** (= last_equity), all cash, **0 open positions = nothing
locked.** 23 enabled reviewed vs 14d closed-trade P&L from dbo.trades:
- **Leaders:** INTC +$206.5 (5 tr, 3W), MU +$152 (6 tr, 4W), QQQ +$51 (3/3), JPM +$28, QCOM +$25,
  UNH +$9, SPY +$6 — core keeps; the semi/index regime the list is built around is working and
  chips are firm again pre-market.
- **Laggards:** AVGO −$69 (2/3 — winning recently), NVDA −$54 (**0/3, still never won**), TSLA −$38,
  BABA −$36, GOOG −$25, AAPL −$21. Per the daily reviews every one is **regime (Iran selloff /
  FOMC fade) or overnight-carry, not signal quality**; all mega-liquid. Parking the most-liquid
  semis (NVDA/AVGO) as chips rip is the poor timing prior runs warned of → **KEEP, on notice**.
  GOOG's −2% pre on the DeepMind headline is minor and the long-only gate simply won't trigger
  longs in a downtrend — no park.
- Lower-liquidity names (SE +$4.7, ABNB +$0.4, BABA) traded fine recently → keep.
- No earnings on any watchlist name today; MU (Wed) + PCE (Thu) are the only binary flags ahead.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked, but the list is broad (23 ≤ 30) and semi/index-heavy into a
confirmed-working, chip-led tape; **zero earnings risk today** (MU is Wed, after-close); every
laggard is regime/carry per the dailies, none a signal-quality or liquidity park; and a hawkish-Fed,
news-quiet day is the wrong tape to chase a momentum add. XOM/WPM/ENPH/BIRD stay parked (energy
still the laggard on <$77 oil). MU park is **tomorrow's** task, not today's.

### Final watchlist
23 enabled (unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QCOM
QQQ SE SPY TSLA TSM UNH WMT. Service **not restarted** (no watchlist change → bot reads the list
only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-06-25 — Pre-market Research

### Market context
- **Risk-on, chip-led.** Futures up on **Micron's blowout** Q3 print: S&P 500 +0.8%, Nasdaq 100 **+2.2%**,
  Dow +0.3%. MU revived the AI trade and is dragging the whole semi complex higher.
- **MU Q3 (after close 06-24):** rev **$41.46B** (+346% YoY) vs $35.84B est, adj EPS **$25.11** vs ~$20.2 est,
  gross margin **84.9%**, Q4 guide **~$50B** vs $43.58B est, plus 16 take-or-pay long-term contracts
  (~$100B floor, $22B deposits). Stock **+15% after-hours** (~$1,201 last vs $1,047.92 reg-session close;
  ~+17% in pre-market). QCOM **+11.7%** on its own raised FY29 non-handset guidance. Sympathy bids across
  WDC/Sandisk/Lam/KLA/AMAT — our AMD/NVDA/AVGO/TSM/INTC all carry the tailwind.
- **⚠️ May PCE at 8:30 ET (12:30 UTC)** — Fed's preferred gauge and the day's macro binary. Consensus
  hotter than April (headline +0.5% m/m / +4.1% y/y; **core +0.3% m/m / +3.4% y/y**). Fed turned hawkish
  last week → a hot print could cap the AI rally. Tug-of-war: AI optimism vs sticky inflation. **Late-day
  entries into the print are extra risky** (carried straight from the 06-24 daily review).
- 10y yield 4.412% (+1bp). Oil still soft (Hormuz tankers exiting on the ceasefire) — energy stays the
  laggard, XOM stays parked.

### Carried from daily review (06-24)
- **RE-ENABLE MU** once the after-hours move is digested, after checking the post-print gap → **done.**
  The gap is a clean **+15% UP** on a blowout beat (not a chart-breaking gap down), MU is a top-2 earner
  (+$152 / 14d), very liquid (~$1.1B daily $-vol), and trends intraday. The park was event-driven, not a
  demotion → re-enabled. Asset re-verified on Alpaca: `tradable=true, status=active`.
- Book was **clean & flat** into 06-25 (0 positions, 0 DB-open rows, equity all cash) — confirmed.
- Daily review: symbol quality is otherwise fine; the weak-crossover underperformance is a code/scoring
  question for the daily-review routine, **not a watchlist change**. No quality parks today.

### Watchlist review
- Account ACTIVE, equity **$9,299.11**, **0 open positions** → nothing locked.
- 22 enabled names reviewed against the chip-led risk-on tape + 14d trade P&L. Semis (AMD/NVDA/AVGO/TSM/
  INTC/QCOM) all ride the MU/QCOM rally — keep. INTC (+$176/14d) and MU (+$152) remain the two best earners;
  QQQ (+$51, 3/3) and the mega-caps fit the trending tape. ABNB/SE/TSLA/JPM/AMD net positive. C and NFLX
  never signaled in 14d but are liquid large-caps — leave enabled, not park candidates yet.
- **No adds.** The list already holds 6–7 semis; piling more single-catalyst chip names (WDC/LRCX/KLAC/AMAT)
  the morning of a possibly-hot PCE would be concentration-chasing, and the daily review requested no adds.
  Conservative = correct.

### Changes applied to dbo.watchlist
- **Re-enabled MU** (`enabled=1`, note "re-enabled 2026-06-25: blowout Q3 earnings digested (+15% AH),
  top-2 earner, liquid"). Only change.
- Still parked (unchanged): BIRD (micro-cap), ENPH (10.9% ATR whipsaw), WPM (downtrend/dead-vol), XOM
  (broken oil downtrend).

### Final watchlist
**23 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT **MU** NFLX NVDA QCOM QQQ
SE SPY TSLA TSM UNH WMT. Service **restarted** at 11:34 UTC — `active`, warmup primed **23/23** symbols,
subscribed to all 23 (MU present), account ACTIVE, 0 open positions. Clean startup. 🔒 Locked: none.

---
