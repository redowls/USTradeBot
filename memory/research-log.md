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

## 2026-07-28 — Pre-market Research

**No-change day into a global chip sell-off.** Book is CLEAN & FLAT (broker-confirmed **0 positions**,
equity **$8,848.98**, `last_equity` == `equity` → no overnight marks, matches 07-27 EOD $8,849.01) →
nothing locked. **No enabled watchlist name reports today** (per the 07-27 daily-review note); the week's
prints on our names are all after-close on their own mornings. **Decision: NO CHANGES, no restart.**

### Market context
- **Mixed, tech-weak tape on a deepening semiconductor sell-off.** Futures: **Dow +0.23% (+121pts)**,
  **S&P ~flat/just below the line**, **Nasdaq-100 −0.73%** (CNBC/Benzinga). Driver: a **global chip rout
  spreading from Asia** — **SK Hynix −14.65%, Samsung −13%** at the close → US premarket **MU −4.5%,
  AMD −3%, INTC −3%+, Marvell −3%, NVDA −1.2%**. Oil extends lower on Iran de-escalation (Trump "good
  talks" with Iran). Broader market steadier (Dow green on non-tech strength) — it's a semi-specific risk-off.
- **Nothing DURING market hours today on our list.** 176 companies report Tue but **no enabled watchlist
  name**. The week's prints: **MSFT Wed 07-29 AH**, **AAPL + AMZN Thu 07-30 AH**; **Fed decision Wed**,
  **June Core PCE Thu**. Earnings-park decisions belong to Wed/Thu pre-market per standing precedent.
- No single-name negative catalyst, halt, downgrade, or M&A on any enabled symbol overnight (Perplexity
  sonar + WebSearch): the chip weakness is a **broad regime move**, not a symbol-quality break.

### Carried from daily review (07-27 EOD)
- **Book CLEAN & FLAT into Tue 07-28** — confirmed live (ACTIVE, equity $8,848.98, 0 positions). Nothing locked.
- **"Tue 07-28: no watchlist name reports → no park needed"** → honored. Wed/Thu are the earnings-park days.
- **Gap-fade regime watch** (07-27: bot bought 6 longs into a gap-up that faded, 7/8 red). Today is the
  mirror image — a **gap-DOWN, semi-led risk-off** open. The long-only 5m gate self-protects (opens no
  longs into a downtrend); if the tape breaches −2% intraday it is a candidate for IMP-016's first
  stand-down trip. Not a watchlist action — the regime to watch, acted on by **NOT adding into weakness**.
- **No quality parks** (07-27: every red was the tape, not the name) → honored; keep the full list.

### Watchlist review
- **All 21 enabled kept.** No overnight negative catalyst on any (AAPL/ABNB/AMD/AMZN/AVGO/BABA/C/GOOG/INTC/
  JPM/MSFT/MU/NFLX/NVDA/QQQ/SE/SPY/TSLA/TSM/UNH/WMT). All mega-liquid, trend-eligible for the ribbon.
- **Chip cohort (MU/AMD/INTC/NVDA/AVGO/TSM) gapping down −1% to −4.5%** = the Asian semi rout, **regime not
  symbol quality**. Parking the most-liquid semis mid-selloff is exactly the poor timing the log has warned
  against for weeks; the long-only gate simply won't open longs while they trend down → **KEEP, on notice**.
- **No re-enables.** Parked names still fail criteria: BIRD (micro-cap), COST (July sales miss), ENPH
  (10.9% ATR chop), QCOM (semi laggard — and today's chip rout makes it worse), WPM (downtrend), XOM
  (oil falling on Iran de-escalation → still bearish). Keep parked.
- **No adds.** A semi-led risk-off gap-down open is the wrong session to chase momentum, and we're already
  heavily chip-exposed. 21/30, room to spare — quality over churn.

### Flags for later this week (NOT today's action)
- **Wed 07-29 AM:** park **MSFT** ahead of its after-close print (binary overnight earnings) — re-enable Thu.
- **Thu 07-30 AM:** park **AAPL + AMZN** ahead of their after-close prints — re-enable Fri once cleared.

### Changes applied to dbo.watchlist
- **NONE.** No adds, no parks, no re-enables. 21 enabled unchanged.

### Final watchlist
- **21 enabled** (unchanged): AAPL, ABNB, AMD, AMZN, AVGO, BABA, C, GOOG, INTC, JPM, MSFT, MU, NFLX, NVDA,
  QQQ, SE, SPY, TSLA, TSM, UNH, WMT. 6 parked (BIRD, COST, ENPH, QCOM, WPM, XOM). **Service NOT restarted**
  (no change). 🔒 Locked: none (0 open positions).

---

## 2026-07-27 — Pre-market Research

**No-change day into the Big-Tech earnings week.** Book is CLEAN & FLAT (broker-confirmed **0 positions**,
equity **$8,927.21** all cash, `last_equity` == `equity` → **no trades Fri 07-25**, last DB entry 07-24
19:06 UTC) → nothing locked. No enabled watchlist name reports **today**; the week's prints on our names are
all **after-close** and get parked on their own morning. **Decision: NO CHANGES, no restart.**

### Market context
- **Risk-on gap-up open.** Futures: **Dow/S&P +0.8%, Nasdaq-100 +1.6%** (Yahoo/Fortune); **SPY +0.94% (~$745.85),
  QQQ +1.57% (~$695)** pre-market. Driver: **US–Iran weekend de-escalation** (US paused its airstrike campaign,
  Tehran halted retaliatory strikes) → **oil −~7%, Brent <$86**. Reverses Thu's AI-capex risk-off; S&P closed Fri
  +0.1% (−0.6% wk), Nasdaq −0.6% Fri (−2.1% wk).
- **Busiest week of the quarter — but nothing DURING market hours today.** On our enabled list: **MSFT reports
  Wed 07-29 AH**, **AAPL + AMZN report Thu 07-30 AH**. Also **Fed decision Wed** (≈68% priced hold), **June Core
  PCE Thu**. None of these are today; earnings-park decisions belong to Wed/Thu pre-market per standing precedent
  (park = binary overnight earnings, re-enable once the print clears).
- **AMD** (enabled) **+3% pre-market** on last week's Analyst Day (Anthropic + OpenAI partnerships, new DC
  products, $1.4T AI-accelerator TAM by 2030) — clean momentum, ribbon-friendly; AMD itself reports early Aug
  (outside this week). No negative catalysts, halts, or downgrades on any enabled symbol overnight.

### Carried from daily review (07-24 EOD)
- **Book CLEAN & FLAT into Mon 07-27** — confirmed live (ACTIVE, equity $8,927.21, 0 positions). Nothing locked.
- **INTC** re-enable (07-24) clean — enabled & `active`, no trade on the soft tape, no issue → keep.
- **MSFT / SE keep** (07-24 notes: MSFT's loss was the tape not the symbol; SE late-entry churn is data-refuted
  as a park reason). Both kept.
- **Open-hour P&L sink** (13Z / 09:30–10:30 ET = −$407 all-time) → acted on today by **NOT adding hyper-volatile
  gap-up momentum names** into a risk-on open that would feed low-quality first-hour crosses.

### Watchlist review
- **All 21 enabled kept.** No overnight negative catalyst on any (AAPL/ABNB/AMD/AMZN/AVGO/BABA/C/GOOG/INTC/JPM/
  MSFT/MU/NFLX/NVDA/QQQ/SE/SPY/TSLA/TSM/UNH/WMT). Mega-liquid, trend-eligible for the ribbon; risk-on tape suits
  long-only 5m gate.
- **DB 14-day net −$379.68** noted but **not actionable** — equity is flat/up over the same window
  ($8,927), the documented DB-exit-price-vs-fill divergence overstates per-symbol losses. No symbol is a true
  capital loser; no park on DB P&L alone.
- **Parked names — no re-enable.** COST (07-10 sales miss), ENPH (choppy 10.9% ATR), QCOM (semi laggard + **reports
  Wed AH**), WPM (downtrend), XOM (**oil −7% today → even more bearish**, broken downtrend), BIRD (micro-cap) — all
  still fail criteria. Keep parked.
- **No adds.** Conservative hold; risk-on gap-up open is exactly when to avoid adding momentum gappers (open-hour
  sink). 21/30, room to spare — quality over churn.

### Flags for later this week (NOT today's action)
- **Wed 07-29 AM:** park **MSFT** ahead of its after-close print (binary overnight earnings) — re-enable Thu once cleared.
- **Thu 07-30 AM:** park **AAPL + AMZN** ahead of their after-close prints — re-enable Fri once cleared.

### Changes applied to dbo.watchlist
- **NONE.** No adds, no parks, no re-enables. 21 enabled unchanged.

### Final watchlist
- **21 enabled** (unchanged): AAPL, ABNB, AMD, AMZN, AVGO, BABA, C, GOOG, INTC, JPM, MSFT, MU, NFLX, NVDA, QQQ,
  SE, SPY, TSLA, TSM, UNH, WMT. 6 parked (BIRD, COST, ENPH, QCOM, WPM, XOM). **Service NOT restarted** (no change).

---

## 2026-07-24 — Pre-market Research

**INTC re-enable day.** Book is CLEAN & FLAT (0 positions, equity **$8,882.24** all cash) → nothing
locked, watchlist free. One decided action, pre-flagged by the 07-23 research entry + 07-23 daily review:
**RE-ENABLE INTC** — its Thu 07-23 after-close Q2 print has cleared, and it beat.

### Market context
- **Futures recovering after Thursday's capex-fear selloff.** As of pre-open: **S&P +0.2%, Nasdaq-100 +0.1%,
  Dow +0.5% (+268pts)** — stabilizing after Thu 07-23's rough tape (Dow −0.97% to 51,711, **S&P −1.21% to
  7,408**, **Nasdaq −2.15% to 25,138**) driven by **GOOG −7% + TSLA −14%** on their raised-AI-capex prints.
  Major averages still on track for a down week (Dow −0.8%, S&P −0.7%, Nasdaq −1.5%).
- **⚠️ INTC Q2 verified (Perplexity + WebSearch):** reported **after Wed→Thu 07-23 close** — **rev $16.1B
  (+25% YoY), non-GAAP EPS $0.42, Q3 guide $15.8–16.8B / EPS $0.38 (both above consensus)**, fastest rev
  growth since 2011 on AI/server demand. Stock **+3.4–3.6% after-hours/pre-market** (~$103.68 vs $100.10
  close). Binary event resolved **favorably** → re-enable. **Today's earnings on deck** (INTC already out,
  plus TMUS, LMT, others) — **none of the remaining names are on our watchlist**; no market-hours event risk.
- Backdrop: oil crossed **$100 (Brent)** Thu on Mideast/Red-Sea tanker attacks, pared to WTI ~$89 / Brent
  ~$97 Fri; **10-yr ~4.69%** (18-mo high Thu on inflation/hike-back bets); **jobless claims 187K — lowest
  since 1969** (strong labor). Non-watchlist: geopolitics + oil the swing factors.

### Carried from daily review (07-23 EOD)
- **Book CLEAN & FLAT into Fri 07-24** — 0 positions, equity $8,882.27 all cash; **confirmed live**
  (ACTIVE, equity **$8,882.24**, 0 positions). Nothing locked.
- **"INTC park was due to fire Thu 07-23 — verify it was parked; re-enable on the next clean open once the
  print clears"** → **ACTIONED**. INTC was correctly parked 07-23; its beat is now digested → re-enabled.
  Same precedent as GOOG/TSLA (07-23), TSM/UNH (07-16), NFLX (07-17): park = binary overnight earnings,
  re-enable once resolved regardless of direction. Re-verified `tradable=true, status=active` on `/v2/assets`.
- **⚠️ "MU is UN-TRADEABLE at 1× buying power" (07-23) — decide its fate.** **Checked BP first, as instructed:
  today BP is 4× ($35,528.96)**, so 0.10×BP = $3,553 ≫ one MU share (~$993) → **MU is sizable today; KEEP
  enabled.** The un-tradeable flag was explicitly *conditional on 1× BP* (07-23 had BP 1× → MU dropped all
  session). BP swings 1×–4× day-to-day; MU stays a "trades on high-BP days" name — no park on a 4× day.
- **Regime was genuinely risk-off, not a bot problem; no add warranted into a down tape** (07-23) → honored;
  a recovering-but-choppy, oil/geopolitics-charged, weekly-down tape is no place to chase momentum → no adds.

### Watchlist review
20 enabled reviewed; book flat → nothing locked. Core megacap/ETF engine (AAPL/AMZN/MSFT/QQQ/SPY/NVDA) +
chip cohort (AMD/AVGO/MU/TSM) + BABA/SE/ABNB/C/JPM/WMT/UNH/GOOG/TSLA/NFLX all liquid; long-only 5m gate
self-protects on the soft tape. **GOOG/TSLA** got hit Thu (−7% / −14% on capex) but are flat (not held),
binary already resolved 07-23, gate handles the direction → keep enabled. **NFLX** thin-participation watch
continues (no fresh issue) → keep. **MU** sizable at 4× BP → keep.
- **INTC (parked → re-enabled)** — Q2 beat digested, +3.6% pre-market, mega-liquid top historical earner.
- **Parked re-enable check:** BIRD (micro-cap), COST (sales-miss downtrend), ENPH (10.9% ATR whipsaw),
  QCOM (−14% vs MA, thin $vol), WPM (dead-vol downtrend), XOM (oil is a one-headline spike into $100 then
  faded, not a durable uptrend) → **all stay parked**, no fresh bullish trend catalyst.
- **Adds:** none. Recovering-but-down-week, oil/Mideast-driven tape; no conviction momentum candidate.

### Changes applied to dbo.watchlist
- **Re-enabled INTC** — `enabled=1`, note "re-enabled 2026-07-24: Q2 beat (07-23 AH), Q3 guide above cons,
  +3.6% pre-mkt; earnings event resolved, mega-liquid". Re-verified `tradable=true, status=active` on `/v2/assets`.
- **No adds, no parks, MU kept** (4× BP today makes it sizable). Perplexity sonar confirmed INTC's beat +
  reaction (thin on futures/movers) → WebSearch supplied futures direction, the Thu selloff recap, and INTC's
  +3.6% pre-market move.

### Final watchlist
**21 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SE SPY TSLA TSM
UNH WMT. Parked (6): BIRD COST ENPH QCOM WPM XOM. Service **RESTARTED** 11:36 UTC — verified `active`, warmup
primed **21/21** from history, account ACTIVE equity $8,882.24 / BP $35,528.96 (4×), 0 positions, clean
21-symbol IEX subscription (INTC present), no errors. 🔒 Locked: none (0 open positions). **Watch:** MU only
trades on high-BP days (dormant at 1× BP); NFLX thin participation; IMP-016 stand-down still awaits its first
genuine broad risk-off trip.

---

## 2026-07-23 — Pre-market Research

**The queued INTC earnings park fires today; GOOG + TSLA re-enable.** Book is CLEAN & FLAT
(0 positions, equity **$8,882.27** all cash) → nothing locked, watchlist free. Two decided actions,
both pre-flagged by the 07-22 daily review: **PARK INTC** (reports Q2 after today's close, binary) and
**RE-ENABLE GOOG + TSLA** (their after-close prints from last night are now digested).

### Market context
- **Risk-OFF on AI-capex fears.** Futures lower (as of ~04:00 ET): **Nasdaq −0.7%**, S&P/Dow −0.5%,
  Russell −0.3%. **GOOG + TSLA both slump pre-market** after last night's Q2 prints — both **beat on
  revenue** but are punished on **elevated AI capex / margin** concerns (the AI-spending-vs-growth
  debate). Not chart-breaking collapses (GOOG ~−1-3%, TSLA soft/off-peak) — the binary *event* is
  resolved, only the reaction remains. Also today: **initial jobless claims**, Middle East tensions →
  oil bid.
- **⚠️ Earnings verified (WebSearch, multiple sources):** **INTC reports Q2 AFTER today's close**
  (Thu 07-23, 5pm ET; consensus ~$14.4B rev, options imply **~15% move** on a name +186% YTD) →
  textbook binary overnight event, **parked before the open** (book flat, not locked = safe). No other
  watchlist name reports today (AAPL Jul 30). GOOG/TSLA already reported (last night) → event risk gone.
- Non-watchlist: **ServiceNow (NOW)** popped on its print; **SPCX** in focus. Busy earnings day broadly.

### Carried from daily review (07-22 EOD)
- **Book CLEAN & FLAT into Thu 07-23** — daily review said equity $8,882.27 all cash; **confirmed live**
  (ACTIVE, equity **$8,882.27**, 0 positions, BP $8,882). Nothing locked.
- **"INTC's queued park fires Thu 07-23 — don't miss it"** → **ACTIONED** (the day's primary change).
  INTC signalled strongly on 07-22 (conf 75) but faded on regime; kept until its own earnings park, now due.
- **"Re-enable GOOG + TSLA on the next clean open after tonight's prints clear"** (07-22 research-log)
  → **ACTIONED**. Same precedent as TSM (07-16, re-enabled through ~4% gap-down) and NFLX (07-17, ~8%
  gap-down): the park criterion is *binary overnight earnings*, not direction — event resolved, the
  long-only 5m gate self-protects if they trend down intraday. Both re-verified `tradable/active` on Alpaca.
- **NFLX thin-participation watch** — 07-22 flagged its illiquid feed + 0-volume-subscore weak entries.
  Not a one-day park; kept on notice. Behaved-ish today (−0.14% daily). Keep, watch liquidity.
- **IMP-016 (broad-adverse-day stand-down) LIVE** — today's risk-off GOOG/TSLA-capex tape is a candidate
  for its **first real trip** if the selloff deepens (per weekly-review D focus + 07-22 note).

### Watchlist review
19 enabled reviewed against the risk-off tape. Book flat → nothing locked. Chip cohort
(INTC/MU/AVGO/NVDA/AMD) chopped on 07-22 = regime, not symbol quality — all signalled/stopped/flattened
correctly; keep. Core megacap/ETF engine (AAPL/AMZN/MSFT/QQQ/SPY/NVDA) + BABA/SE/ABNB/C/JPM/WMT/UNH/NFLX/TSM
all liquid, all regime-red where red; keep. Long-only gate self-protects on the risk-off tape.
- **INTC (enabled → parked)** — liquid, quality fine; **parked ONLY for tonight's binary Q2 print**
  (~15% implied), not for quality. Re-enable next clean open once cleared.
- **GOOG + TSLA (parked → re-enabled)** — Q2 prints digested; mega-liquid, trend intraday, binary risk gone.
- **Parked re-enable check:** BIRD (micro-cap), COST (sales-miss downtrend), ENPH (10.9% ATR whipsaw),
  QCOM (−14% vs MA, thin $vol), WPM (dead-vol downtrend), XOM (one-headline oil, no trend) → **all stay
  parked**, no fresh bullish catalyst.
- **Adds:** none. A risk-off, AI-capex-fear tape is the wrong session to chase momentum; no conviction
  candidate. 20 enabled is broad and healthy.

### Changes applied to dbo.watchlist
- **Parked INTC** — `enabled=0`, note "parked 2026-07-23: Q2 earnings AFTER today close (~15% implied),
  no binary overnight hold". Flat (not locked) = safe. The pre-flagged required action.
- **Re-enabled GOOG + TSLA** — `enabled=1`, notes "Q2 print cleared … event risk resolved, mega-liquid".
  Both re-verified `tradable=true, status=active` on `/v2/assets`.
- **No adds, no other parks.** Perplexity sonar briefing returned weak/"not verifiable" (thin retrieval)
  → fell back to WebSearch, which confirmed INTC's after-close timing and the GOOG/TSLA capex-driven slump.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG JPM MSFT MU NFLX NVDA QQQ SE SPY TSLA TSM UNH
WMT. Parked (7): BIRD COST ENPH INTC QCOM WPM XOM. Service **RESTARTED** 11:37 UTC — verified `active`,
warmup primed 20/20 from history, account ACTIVE equity $8,882.27, 0 positions, clean 20-symbol subscription
(GOOG/TSLA present, INTC absent; the connection-limit blips were the known old/new-PID restart handoff,
recovered by 11:37:30). 🔒 Locked: none (0 open positions). **Re-enable INTC on the next clean open after
tonight's print clears.** Watch NFLX participation + a possible first IMP-016 stand-down trip on the risk-off tape.

---

## 2026-07-22 — Pre-market Research

**The week's #1 queued binary parks fire today.** Book is CLEAN & FLAT (0 positions, equity
**$8,918.52** all cash) → nothing locked, watchlist free. Both the 07-20 daily review and the
07-21 research entry explicitly ordered: **the Wed 07-22 pre-market routine MUST PARK GOOG + TSLA**
(both report Q2 after today's close). Done this run. INTC's park is queued for **Thu 07-23** (not today).

### Market context
- **Risk-OFF into the first Magnificent-7 prints.** Futures lower: **Nasdaq-100 −1.26%**, S&P
  −0.33% — markets bracing for **GOOG + TSLA after today's close** (the first two Mag-7 to report,
  the AI-capex test). Tuesday 07-21 closed strong (S&P +0.89% to 7,509.20, semis rebound).
- **⚠️ Earnings verified (WebSearch):** **GOOG (Alphabet)** reports Q2 **after today's close**
  (Street EPS $2.88, rev ~$117B; +9% YTD). **TSLA (Tesla)** reports Q2 **after today's close**
  (Street EPS $0.52, rev ~$26B, record 480K deliveries; −15% YTD, options imply ~7.6% swing).
  Both are binary overnight events → **parked before the open** (book flat, neither locked = safe).
  No other watchlist name reports today (AAPL Jul 30). **INTC reports Thu 07-23 → Thu routine parks it.**
- Non-watchlist movers: **SMCI** surging pre (record backlog); **IBM** reports after close.
  Macro overhang: oil/inflation, Fed-hike odds up (~24% July, ~69% by Sept), fresh tariffs.

### Carried from daily review (07-21 EOD)
- **Book CLEAN & FLAT into Wed 07-22** — daily review said equity $8,918.55 all cash; **confirmed
  live** (ACTIVE, equity **$8,918.52**, 0 positions, BP $35,674). Nothing locked.
- **The Wed 07-22 GOOG+TSLA park was the daily review's explicit ⚠️ instruction** — executed.
- **Chip cohort chopped but is regime, not symbol quality** (TSM won +$34.14 on 07-21; INTC/MU
  whipsawed early then afternoon re-entries worked) → keep all enabled. **NFLX behaved** (+0.94%
  late winner), post-earnings watch relaxed → keep. **Resist chasing chip/momentum adds** into the
  megacap prints → honored (no adds).
- IMP-016 (broad-adverse-day stand-down) now LIVE — watch for its first trip if GOOG/TSLA disappoint tonight → Thu selloff.

### Watchlist review
21 enabled reviewed against the risk-off tape + 14d P&L. **14d net −$329** across 20 symbols, but
per the dailies this is the **semis/AI-capex regime week**, not symbol/liquidity quality — every
laggard signalled & stopped correctly. Winners BABA (+$52), ABNB (+$29), MSFT (+$14), NVDA (+$11).
- **GOOG (2 tr −$5.73) / TSLA (4 tr −$71.55)** — liquid mega-caps, red is regime; **parked ONLY for
  tonight's binary earnings**, not quality. Re-enable next open once the print clears.
- **Core megacap/ETF engine** (AAPL/AMZN/MSFT/QQQ/SPY/NVDA) + **chip cohort** (AVGO/AMD/INTC/MU/TSM)
  + **BABA/SE/ABNB/C/JPM/WMT/UNH/NFLX** — all liquid, all regime-red where red; keep. Long-only 5m
  gate self-protects on the risk-off tape.
- **Parked re-enable check:** BIRD (micro-cap), COST (sales-miss downtrend), ENPH (10.9% ATR whipsaw),
  QCOM (−14% vs MA, thin $vol), WPM (dead-vol downtrend), XOM (one-headline oil, no trend) → **all
  stay parked, no fresh bullish catalyst.**
- **Adds:** none. Risk-off tape into the pivotal Mag-7 prints is the wrong session to chase momentum;
  no conviction candidate. 19 enabled is broad and healthy.

### Changes applied to dbo.watchlist
- **Parked GOOG + TSLA** — `enabled=0`, note "parked 2026-07-22: Q2 earnings AFTER today close
  (binary), re-enable next open once cleared". Both flat (nothing locked) = safe.
- **No adds, no other parks, no re-enables.** Perplexity sonar briefing returned empty (no cited
  results) → fell back to WebSearch, which confirmed the GOOG/TSLA after-close timing.

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C INTC JPM MSFT MU NFLX NVDA QQQ SE SPY TSM UNH
WMT. Parked (8): BIRD COST ENPH GOOG QCOM TSLA WPM XOM. Service **RESTARTED** 11:35 UTC — verified
`active`, warmup primed, equity $8,918.52, 0 positions, clean 19-symbol subscription (GOOG/TSLA
absent). 🔒 Locked: none (0 open positions). **Thu 07-23 routine: PARK INTC** (reports Thu). **Re-enable
GOOG + TSLA on the next clean open after tonight's prints clear.**

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

## 2026-06-26 — Pre-market Research

### Market context
- **Risk-OFF, tech/semis selling off.** Futures lower on a **global tech sell-off** — investors worried
  about mounting **AI data-center / memory-infrastructure costs** and that AI valuations have run ahead of
  fundamentals. Asian tech sold off sharply overnight; Mag7 complex (MAGS ETF ~$60.95, −0.18% pre) under
  pressure again.
- **Thursday 06-25 close was mixed/lower** despite MU's blowout — S&P 500 and Nasdaq finished lower.
  **AAPL and MSFT fell** after both announced **price increases on consumer hardware** (rising memory
  costs) — a direct, but non-binary, headwind on those two names.
- **No watchlist-name earnings today.** MU already reported (Wed 06-24, after close); the week's macro
  binary (**May PCE**) printed **yesterday 06-25**. Today's follow-through is a **tech-led risk-off** drift,
  not an event day. NKE reports around now but is not on our list.
- 06-25's hotter-PCE/AI-cost overhang is now playing through as a tech fade. Energy still the laggard
  (oil soft) → XOM stays parked.

### Carried from daily review (06-25)
- **Book CLEAN & FLAT into 06-26** — 0 broker positions, 0 DB-open rows, equity **$9,246.50** all cash.
  **Nothing locked**; full watchlist free of carry/park constraints. Confirmed live this run.
- **MU re-enable validated** (trailing stop locked +2.48% on 06-25) → **KEEP MU**, event-park fully unwound.
- **AMD open-spike loss** (highest-ever conf 91.73 bought the MU-euphoria gap-up and stopped −1.64%) was a
  **regime/timing** loss, **not symbol quality** → KEEP AMD, no park. Today's tech-down tape is the mirror
  case: the long-only ribbon simply won't fire longs in a downtrend, so it self-protects on a sell-off day.
- **JPM (weak xo) / C (scratch)** were choppy-tape outcomes, not symbol failures → no quality parks.

### Watchlist review
- Account **ACTIVE**, equity **$9,246.50**, **0 open positions → nothing locked.** 23 enabled / 4 parked
  (BIRD, ENPH, WPM, XOM). 27 rows total, 23 ≤ 30 ✓.
- 14d closed-trade P&L: **Leaders** INTC **+$114.38** (4 tr, 2W), MU **+$98.19** (5/3), SE +$35.65 (2/2),
  UNH +$16.12, ABNB +$13.26, AVGO/QQQ/WMT small green. **Laggards** AMD −$53.94 (2/0, the 06-25 open-spike
  loss), BABA −$38.26, GOOG −$29.06, AAPL −$28.32, AMZN −$18.60, TSM −$13.95, SPY/JPM/NVDA mid-single-neg.
  Every laggard is **regime/timing or overnight-carry** per the dailies — all mega-liquid large-caps, none a
  signal-quality or liquidity park. The core semi/index roster (INTC, MU, the two best earners) is exactly
  the regime the list is built around.
- **AAPL / MSFT carry today's only name-specific headline** (hardware price hikes on memory costs) — a
  mild, non-binary negative, not an earnings/halt/binary event. The long-only gate won't chase them lower;
  no park warranted (one-day macro/tech-cost headline, not a broken-symbol thesis).
- **No adds.** Adding momentum/semi names into a **tech-led sell-off** would be chasing into weakness and
  pure concentration-stacking — the wrong tape. The daily review requested no adds; conservative = correct.

### Changes applied to dbo.watchlist
- **No changes.** Book is flat (nothing locked), zero watchlist-name earnings today, all 23 enabled names
  are liquid large-caps whose recent weakness is regime/timing (not quality), and a risk-off tech sell-off
  is the wrong day to add momentum. The long-only ribbon self-protects by not firing longs in downtrends.
  BIRD/ENPH/WPM/XOM stay parked (unchanged).

### Final watchlist
**23 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA
QCOM QQQ SE SPY TSLA TSM UNH WMT. Service **NOT restarted** (no watchlist change → the bot reads the list
only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-06-29 — Pre-market Research

**First session after a flat, profitable Friday.** Book CLEAN & FLAT (0 positions, equity all cash);
nothing locked → full watchlist free. IMP-011 (`MIN_CROSSOVER` 0.20 floor) is live from the 06-26
restart and gets its **first full live trading week** — the weekly review's focus is to prove it
(entry count holds, weak-cross cohort filtered, win rate rises). That is a results/ops grade, not a
watchlist action.

### Market context
- **Bifurcated tape: index futures up, chips down again.** S&P futures +~1.1%, Nasdaq-100 +~1.3%,
  Dow +0.6%, Russell −0.2% — but the **semiconductor rotation that ran all last week continues**:
  **MU −6%+** and SanDisk (SNDK) −6%+ pre-market on multi-billion notionals; AI valuation / memory-cost
  overhang persists and Apple's hardware price hikes are pressuring Asian tech (KOSPI hit trading curbs).
  Speculative money is rotating into micro-caps (ILLR +65%, IVF +48%, SHPH +41%) — outside our liquid
  large-cap universe, not add candidates.
- **Quiet earnings week.** No major tech reports until late July (AAPL 07-30, META 07-29). **No watchlist
  name reports this week** — NKE (athleisure, not ours) is the only notable. **Zero watchlist earnings
  risk.** Busy macro week ahead (data + Fed speakers) but no binary today.
- Energy still the laggard → **XOM stays parked**.

### Carried from daily review (06-26)
- **Book CLEAN & FLAT into today** — 0 broker positions, 0 DB-open rows, equity **$9,308.54** all cash
  (== last_equity; confirmed live this run). Nothing locked; full watchlist free.
- **No quality parks indicated.** The 06-26 weak-cross losers (COST/AMZN/SPY/QQQ/ABNB, all xo<0.20) are
  **NOT** watchlist parks — they're liquid large-caps and the issue was *signal strength on the day*, now
  filtered in code by **IMP-011**. Strong-cross **MSFT (+$74.72) / NFLX** traded beautifully → keep.
- **AMD open-spike** (06-25, conf 91.73 −$53.94) is a regime/timing loss, not symbol quality → keep AMD.
- **IMP-011 live** — expect fewer entries; watch count doesn't collapse + surviving win rate rises.

### Watchlist review
Account ACTIVE, equity **$9,308.54**, **0 open positions = nothing locked.** 23 enabled / 4 parked
(BIRD, ENPH, WPM, XOM); 23 ≤ 30 ✓. Reviewed vs 12d closed-trade P&L from dbo.trades:
- **Leaders:** INTC **+$114.38** (4 tr, 2W), MSFT **+$74.72** (1/1), SE +$35.65 (2/2), UNH +$23.92,
  MU +$22.26 (3/2) — the semi/index regime the list is built around; all keeps.
- **Laggards:** AMD −$53.94 (06-25 open-spike), BABA −$43.60 (overnight-carry), JPM −$42.41, GOOG −$35.40,
  AMZN −$30.47, AAPL −$20.91, SPY −$17.47. Per the daily reviews every one is **regime / timing /
  overnight-carry / weak-cross (now filtered by IMP-011) — not signal quality**; all mega-liquid large-caps,
  none a liquidity or quality park → KEEP, on notice.
- **AVGO, WMT** enabled but **no trades in 12d** — liquid large-caps the gate simply hasn't triggered;
  consistent with keeping inactive-but-liquid names (C/NFLX) prior runs → no park-for-inactivity.
- **MU −6% pre** is the **chip-rotation selloff, not an event** (MU already reported 06-24). The long-only
  5m gate won't fire longs in a downtrend (fewer entries, not bad ones) — MU is a top earner, self-protects
  → **KEEP** (regime, not symbol). ENPH/WPM `n=1` in the query are IMP-006 phantom-sweep rows (pnl=0), not
  real trades.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked, but the list is broad (23 ≤ 30) and semi/index-heavy; **zero watchlist
earnings risk this week**; every laggard is regime/timing/carry/weak-cross per the dailies, none a
signal-quality or liquidity park; and a **bifurcated chip-rotation/risk-off-in-semis tape** is the wrong
day to chase a momentum add (today's gainers are speculative micro-caps outside our universe). IMP-011's
first full live week is the time to *let it prove out*, not churn the list. BIRD/ENPH/WPM/XOM stay parked.

### Final watchlist
**23 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA
QCOM QQQ SE SPY TSLA TSM UNH WMT. Service **NOT restarted** (no watchlist change → the bot reads the list
only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-06-30 — Pre-market Research

**Quarter-end day** (final session of Q2). Book CLEAN & FLAT (0 positions, equity all cash); nothing
locked → full watchlist free. IMP-011 (`MIN_CROSSOVER` 0.20 floor) continues its first full live week —
the weekly review's directive is to *let it prove out without stacking another entry-logic change*; that
is a results/ops grade, not a watchlist action.

### Market context
- **Risk-on, megacap-tech rebound into quarter-end.** Mon 06-29 ripped: Dow **record close 52,182.74**
  (+0.59%), S&P **+1.18%** (7,440.43), Nasdaq Composite **+2.07%** (Nasdaq-100 +2.3%) on a Mag7 rebound
  after a soft prior week. **GOOG/Alphabet +4.96%** (first day as a Dow component, replacing Verizon),
  **TSLA +8.45%**, AMZN +3.18%, META +2.2%, NVDA +1.3%. This morning futures hold the gains (Dow +~0.1%,
  S&P modestly higher). Some of the late-June tech wobble is attributed to **quarter-end rebalancing** by
  pensions/SWFs — a positioning distortion, not a fundamental signal.
- **No watchlist name reports today** (or this week). Today's only notable earnings is **NKE after close**
  (not ours); nothing before the bell. **Zero watchlist earnings/binary risk.** Next major tech reports
  late July (META 07-29, AAPL 07-30).
- **Macro:** holiday-shortened week — the big catalyst is **Thursday's June jobs report**; today is light.
  Bond market closed Fri 07-03 (Independence Day). S&P closed Friday just below its 50-day MA (now ~7,363)
  for the first time since early April — a level to watch, but Monday's rally lifted back above.
- **Oil firmer** (Brent $73.15 +1.6%, WTI $70.75 +2.2%) as traders watch whether the Iran pause holds —
  a **one-headline geopolitical bid, not a durable energy uptrend** → **XOM stays parked** (same discipline
  as every prior run; no knife-catch long).

### Carried from daily review (06-29)
- **Book CLEAN & FLAT into 06-30** — 0 broker positions, 0 DB-open rows, equity **$9,398.23** all cash
  (== last_equity; confirmed live this run). Nothing locked; full watchlist free.
- **No watchlist-name earnings this week → zero binary event risk.** Confirmed via today's calendar.
- **Chip-rotation pre-market scares are noise intraday** — on 06-29 MU (+1.28%), AMD (+1.38%), TSM (+3.12%)
  all traded green via the long-only gate. **No semis park indicated** — the regime call holds, keep the
  semi roster.
- **C and SPY are persistent weak-cross chop names** (rejected ×4 / ×2 on 06-29, xo<0.20) — these are **NOT**
  watchlist parks (liquid large-caps; IMP-011 filters their weak crosses in code). No quality park.
- **MSFT** was 06-29's biggest loser despite the strongest cross (high-conf *early* entry) — a *code/timing*
  watch item (the emerging open-spike pattern), **not** a symbol-quality issue → **keep MSFT**.

### Watchlist review
Account ACTIVE, equity **$9,398.23**, BP $37,592.92, **0 open positions = nothing locked.** 23 enabled /
4 parked (BIRD, ENPH, WPM, XOM); 27 rows, 23 ≤ 30 ✓.
- The roster is megacap/semi/index-heavy — **exactly the cohort leading today's risk-on, quarter-end
  rebound** (GOOG/TSLA/AMZN/MSFT/NVDA/QQQ/SPY). No name carries a negative catalyst, earnings, or halt risk
  today; every laggard from the dailies is **regime / timing / overnight-carry / weak-cross (now filtered by
  IMP-011) — not signal quality**, and all are mega-liquid large-caps → KEEP, on notice.
- **AVGO, WMT** still no trades recently — liquid large-caps the gate simply hasn't triggered; consistent
  with keeping inactive-but-liquid names (C/NFLX) → no park-for-inactivity.
- **XOM (parked):** today's oil pop is a geopolitical headline bid, not a trend → stays parked.
- **SPCX** fast-tracked into the Nasdaq-100 (joins ~07-07) — noted as a future candidate once it has trading
  history; still too new for the ribbon. Today's speculative gainers were micro-caps outside our universe.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked, the list is broad (23 ≤ 30) and megacap/semi/index-heavy into a risk-on,
megacap-led tape; **zero watchlist earnings/binary risk today**; every laggard is regime/timing/carry/
weak-cross per the dailies, none a signal-quality or liquidity park. A **quarter-end-rebalancing-distorted
pop** is the wrong day to chase a momentum add, and IMP-011's first full live week should be left to prove
out, not churned. BIRD/ENPH/WPM/XOM stay parked (unchanged).

### Final watchlist
**23 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA
QCOM QQQ SE SPY TSLA TSM UNH WMT. Service **NOT restarted** (no watchlist change → the bot reads the list
only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-07-01 — Pre-market Research

**First session of Q3 / H2.** Book CLEAN & FLAT (0 positions, equity all cash); nothing locked → full
watchlist free. IMP-011 (`MIN_CROSSOVER` 0.20 floor) continues its first full live week — the weekly
directive is to *let it prove out without stacking another entry-logic change*; that is a results/ops
grade, not a watchlist action.

### Market context
- **Record-quarter hangover; consolidation open.** Q2 closed as the **strongest quarter since 2020** —
  S&P +~14%, **Nasdaq +~20%**, Dow +~12%. Tue 06-30 set a **Dow record close 52,319** (Nasdaq Comp
  +1.52%, S&P +0.79%) on a **chip-led rally**: **NVDA +2.6%, AMD +7.7%, INTC +6%, Marvell +7.3%,
  SanDisk +10.9%**. This morning (Wed) futures are **little changed / edging slightly lower** — a
  digestion session after the record quarter, not a reversal. The AI/semi regime our list is built
  around is firing on all cylinders.
- **Jobs-heavy week; today is a warm-up.** Catalysts today = **ADP June employment, ISM Manufacturing
  PMI, construction spending**, and Fed Chair Warsh at the ECB Sintra forum (watch for policy tone,
  non-binary). The week's binary is **Thursday's June nonfarm payrolls** (Fed-policy implications).
- **Zero watchlist earnings risk.** ~12 names report today (only GIS notable — **not ours**); **no
  watchlist name reports today or this week** (next major tech reports late July: META 07-29, AAPL 07-30).
- Energy still the laggard → **XOM stays parked**. SPCX joins the Nasdaq-100 before 07-07 open — noted
  future candidate, still too new for the ribbon.

### Carried from daily review (06-30)
- **Book CLEAN & FLAT into 07-01** — 0 broker positions, 0 DB-open rows, equity **$9,459.99** all cash
  (== last_equity; confirmed live this run). Nothing locked; full watchlist free.
- **No watchlist-name earnings this week → zero binary event risk near-term.** Confirmed via today's calendar.
- **AMD** flagged as a possible **open-spike / early-entry chopper** (2 first-minute losses in the recent
  set, but won +$14.67 from a mid-session entry 06-29). Explicitly a **code/timing watch, NOT a
  symbol-quality park** — and AMD **ripped +7.7% on 06-30**, the regime is clearly working the name → **KEEP**.
- **SE** a recurring thin-tape name (faded to stop on vol sub-score 0.05 on 06-30) but won +$33.40 on
  06-24 → **watch, no park**.
- **No parks indicated on quality grounds** — the day's fix (IMP-012, trailing-stop 422 loop) is exit-infra,
  not a symbol/signal matter.

### Watchlist review
Account ACTIVE, equity **$9,459.99**, BP $37,839.96, **0 open positions = nothing locked.** 23 enabled /
4 parked (BIRD, ENPH, WPM, XOM); 27 rows, 23 ≤ 30 ✓. Reviewed vs 14d closed-trade P&L from dbo.trades:
- **Leaders:** INTC **+$165.28** (6 tr, 4W), TSLA **+$128.90** (6 tr, 4W), TSM +$55.69 (3/4? 3W), MU
  +$36.63 (3W), MSFT +$27.88, UNH +$23.92, NVDA +$21.51, QQQ +$18.74, AVGO +$10.85 — the semi/index
  regime the list is built around, and precisely the cohort that led Tuesday's record close.
- **Laggards:** AMD −$69.47 (4 tr, 1W — the early-entry chop, but +7.7% on the tape 06-30), AMZN −$46.65,
  BABA −$43.60 (single overnight-carry loser), JPM −$42.41, NFLX −$32.00, ABNB −$29.08, COST −$22.24,
  SPY −$17.47, AAPL −$15.40, C −$7.15, GOOG −$5.26. Per the dailies every one is **regime / timing /
  overnight-carry / weak-cross (now filtered by IMP-011) — not signal quality**; all mega-liquid
  large-caps, none a liquidity or quality park → KEEP, on notice. (WPM/ENPH/QCOM `n=1 pnl=0` in the query
  are IMP-006 phantom-sweep rows, not real trades.)
- No name carries a negative catalyst, earnings, or halt risk today. XOM (parked): energy still the
  laggard → stays parked.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked; the list is broad (23 ≤ 30) and semi/index-heavy into a chip-led,
record-setting tape; **zero watchlist earnings/binary risk today or this week**; every laggard is
regime/timing/carry/weak-cross per the dailies, none a signal-quality or liquidity park. A slightly-lower
consolidation open after a record quarter — with Thursday's NFP the week's real binary — is the wrong
tape to chase a momentum add, and IMP-011's first full live week should be left to prove out, not churned.
BIRD/ENPH/WPM/XOM stay parked (unchanged).

### Final watchlist
**23 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA
QCOM QQQ SE SPY TSLA TSM UNH WMT. Service **NOT restarted** (no watchlist change → the bot reads the list
only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-07-02 — Pre-market Research

### Market context
- **June jobs report (NFP) drops TODAY at 8:30 ET** — pulled a day early because Fri **07-03 is the
  Independence Day market holiday** (07-04 falls on Saturday). Consensus **+115K**, unemployment **4.3%**;
  ADP already printed a soft +98K. This is the pivotal binary of a holiday-shortened week — a hot number
  feeds the now-hawkish Fed tilt (market pricing at least one **2026 hike** off 3.50–3.75%), yields ticking up.
- **Futures wavering slightly red** into the print (Dow −0.1%, S&P −0.08%, Nasdaq-100 −0.3%) after a weak
  07-01 (S&P −0.2%, Nasdaq −0.7%). **07-01 was a sharp semiconductor selloff** — SMH **−5.4%**, Micron and
  Sandisk each **−10%+** as traders pared chip positions.
- **Zero watchlist earnings risk** — no watchlist name reports today or this week (next major tech: META
  07-29, AAPL 07-30). No halts, downgrades, or symbol-specific binary events on our names.

### Carried from daily review (07-01)
- **Book CLEAN & FLAT into 07-02** — 0 broker positions, 0 DB-open rows, equity **$9,469.48** all cash
  (confirmed live this run). Nothing locked; full watchlist free.
- **No parks indicated on quality grounds** (07-01 review): TSLA's −$15.63 was a regime/timing fade of its
  06-29 rip (mega-liquid, no trend break) → keep; SE won again on a thin tape → keep; the small losers were
  flat-tape dispersion, not symbol failure; weak-cross rejects are code-filtered by **IMP-011** (mid-proving
  window through 07-03), **not** watchlist parks. Weekly directive: don't stack entry/watchlist churn onto
  IMP-011's first full live week.

### Watchlist review
Account ACTIVE, equity **$9,469.48**, BP $37,877.92, **0 open positions = nothing locked.** 23 enabled /
4 parked (BIRD, ENPH, WPM, XOM); 27 rows, 23 ≤ 30 ✓. Reviewed vs 14d closed-trade P&L + fresh 60-day
daily-bar trend (vs 20/50MA, ATR%, 20d $vol):
- **Leaders (14d):** INTC **+$163**, TSLA **+$134**, TSM +$77, MU +$52, GOOG +$34, MSFT +$28, SE +$26,
  UNH +$24, AAPL +$23, NVDA +$22, QQQ +$19, AVGO +$11 — the semi/index regime the list is built around.
  14d book: **67 trades, ~51% win, +$350 net.**
- **Semis after the 07-01 selloff:** MU −10.6% 1d but **still +22.7% vs 50MA** (only −1.5% vs 20MA), AMD
  −6.9% but **+18.7% vs 50MA / +4.4% vs 20MA**, INTC −9.0% but **+13.1% vs 50MA / +3.5% vs 20MA**, TSM
  −7.0% but **+6.2% vs 50MA**. Every top semi held its **uptrend above both MAs** — a one-day, sector-wide
  give-back of froth, mega-liquid ($61B/$17B/$16B/$6B daily). **Regime, not symbol → KEEP all.**
- **Laggards (14d):** AMD −$69, AMZN −$47, JPM −$40, NFLX −$38, COST −$22, ABNB −$21 — per the dailies all
  regime/timing/weak-cross (IMP-011-filtered), all mega-liquid large-caps in intact or recovering trends
  (AMD +18.7% vs 50MA; JPM +7.0%; AMZN/NFLX +1.4%/+3.9% today reclaiming). **None a quality park → KEEP.**
- **QCOM — park-WATCH (not acted today).** The lone semi outlier: **below both MAs (−13.1% vs 20MA, −9.8%
  vs 50MA)** while its peers hold uptrends, thinnest megacap-semi liquidity ($4.7B/day), ATR 7.6% chop, and
  **no real trades in 14d** (its `n=1 pnl=0` was an IMP-006 phantom-sweep row, not a trade — its long-only
  gate rarely opens). A genuine weak-trend candidate — but **today, on an NFP-morning binary layered over a
  violent semi dislocation, is the wrong tape to judge a chip name's trend.** Stage it (as IMP-005/006 were):
  action a park on a calm, non-event session if QCOM fails to reclaim its 20MA.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked; the list is broad (23 ≤ 30), semi/index-heavy, and profitable (+$350/14d);
zero watchlist earnings/binary risk today or this week; every top semi held its uptrend through the 07-01
selloff and every laggard is regime/timing/weak-cross, not a quality or liquidity failure. Parking a chip
name INTO an NFP-morning binary stacked on a one-day sector dislocation would be poorly-timed churn, and
IMP-011's first full live week should finish proving out un-perturbed. QCOM logged as a park-watch for a
calmer session. BIRD/ENPH/WPM/XOM stay parked (unchanged).

### Final watchlist
**23 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA
QCOM QQQ SE SPY TSLA TSM UNH WMT. Service **NOT restarted** (no watchlist change → the bot reads the list
only at startup). 🔒 Locked: none (0 open positions).

---

## 2026-07-06 — Pre-market Research

**First session back after the 07-03 Independence Day holiday** (07-03 full close, 07-04 Sat, 07-05 Sun).
Book CLEAN & FLAT into today (0 positions, equity all cash); nothing locked → full watchlist free. This is
the **calm, non-event trading session** the staged **QCOM park-watch** was waiting for — actioned today.

### Market context
- **Risk-on, chip-led reopen.** Post-holiday futures higher: S&P +0.4%, **Nasdaq-100 +1.1%**, Dow ~flat.
  **SMH +2.4%** pre-bell leads a tech/semis rebound (WDC +4%, Teradyne +4%, Marvell/Oracle +3%+); XLK +1.2%.
  Building on last week's record run (Dow ~+2%, within striking distance of 53,000; S&P +1.8%, Nasdaq +2.1%).
- **No binary today.** June jobs (07-03) already printed labor-market resilience without an inflation
  overshoot; no major economic release today. **No watchlist name reports today or this week** (next major
  tech: META 07-29, AAPL 07-30) → **zero watchlist earnings/binary risk.** Oil softer post-holiday → energy
  the laggard, **XOM stays parked.**
- **SPCX joins the Nasdaq-100 before tomorrow's (07-07) open** (+ Samsung prelim Q2 07-07) — noted future
  candidate, still too new for the ribbon.

### Carried from daily review (07-03, holiday)
- **Book CLEAN & FLAT into Monday** — 0 broker positions, 0 DB-open rows, equity **$9,479.66** all cash
  (confirmed live this run). Nothing locked; full watchlist free.
- **Zero binary risk on the reopen**; expect a thin/gappy opening print — IMP-008 warmup rebuilds ribbons
  on boot so gates are ready at the open.
- **QCOM park-watch** (staged since 07-02): "action a park only on a **calm non-event trading session** if
  it fails to reclaim its 20MA." → trigger conditions met today (see below) → **ACTIONED: PARK QCOM.**
- **SE** thin-tape watch (won 06-24/07-01, faded on near-zero vol 06-30/07-02) → *watch volume, no park.*
  **GOOG** 07-02 worst = regime fade on weakest 5m gate, not symbol quality → keep.

### Watchlist review
Account ACTIVE, equity **$9,479.66**, BP $37,918.64, **0 open positions = nothing locked.** 23 enabled /
4 parked (BIRD, ENPH, WPM, XOM); 27 rows, 23 ≤ 30 ✓. Reviewed vs 14d closed-trade P&L (65 tr, net **+$161**)
+ fresh 60-day daily bars (through 07-02 close: trend vs 20/50MA, ATR%, 20d $vol):
- **Leaders (14d):** TSLA **+$115** (4 tr, 3W), TSM +$60, MU +$44, AAPL +$32 (4/4), MSFT +$31, NFLX +$25,
  UNH +$24, NVDA +$22, INTC +$21, QQQ +$17 — the semi/index regime the list is built around, and precisely
  the cohort leading today's chip-led reopen.
- **Laggards (14d):** AMD −$69 (early-entry chop, but +12.6% vs 50MA, ripped intraday recently), AMZN −$57,
  JPM −$40, COST −$23, ABNB −$21, SPY −$17 — per the dailies all regime/timing/weak-cross (IMP-011-filtered),
  every one a mega-liquid large-cap in an intact/recovering trend (AMD/AMZN/AAPL back at/above 20MA) → KEEP.
- **Top semis all hold their uptrends into the rally:** AMD +0.3%/+12.6% vs 20/50MA, INTC −2.2%/+6.2%,
  TSM −0.7%/+3.6%, MU −6.5%/**+14.5%**, NVDA −4.4%/−7.3% (mild, most-liquid name $980M) → regime intact, keep.
- **QCOM — PARK (staged trigger met).** The lone semi laggard: **−14.3% vs 20MA, −13.0% vs 50MA and still
  falling** (last-5 closes 188.62→176.12, fresh relative lows — *failed to reclaim its 20MA*), thinnest
  liquidity on the semi cohort (~$136M/day), 8.6% ATR chop, and **no real trades in 14d** (its long-only 5m
  gate rarely opens). Today is the calm, non-event session the 07-02 park-watch specified. Even on a broad
  chip rally, QCOM's own trend is broken and produces no clean intraday longs → PARK (re-enable if it
  reclaims its 20MA on a durable basis; this is a trend/liquidity park, not a demotion of the name).
- **SE** (+14.5%/+16.0% vs MAs, strong uptrend, but lowest $vol ~$20M) → thin-tape watch, no park.

### Changes applied to dbo.watchlist
- **PARK QCOM** (enabled=0, note "parked 2026-07-06: -14% vs 20/50MA & falling, lone semi laggard, thin
  $vol 136M, no real trades 14d"). The one decided action — the staged park-watch, actioned on the calm
  session it was waiting for.
- **No adds.** The roster is already semi/index-heavy (leading today's tape); adding momentum/chip names into
  a chip-led melt-up would be concentration-chasing, and the dailies requested no adds. SPCX too new. XOM/WPM/
  ENPH/BIRD stay parked.

### Final watchlist
**22 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QQQ SE SPY TSLA
TSM UNH WMT. Parked: BIRD, ENPH, QCOM, WPM, XOM. Service **restarted 11:34 UTC** — `active`, clean startup,
account ACTIVE equity $9,479.66, 0 positions reconciled, 22-symbol subscribe confirmed in journal (no QCOM).
🔒 Locked: none (0 open positions).

---

## 2026-07-07 — Pre-market Research

**Book CLEAN & FLAT into today** (0 broker positions, equity all cash); nothing locked → full watchlist
free. No decided action was carried in — the 07-06 daily review flagged **no park candidates** (the chip
cohort was tagged "gap-up-fade-prone" but explicitly *not* park candidates). So this is a review-and-hold
run unless overnight news changes it.

### Market context
- **Chip-pressured, memory-led risk-off open** after Monday's records (07-06: S&P +0.72% to 7,537, Nasdaq
  +1.12%, **Dow record 53,055**). This morning **Samsung's prelim Q2 disappointed** (profit surged 19× but
  under-whelmed → Samsung **−8.8% in Seoul**) and **SK Hynix debuts a ~$28B US listing** — memory names
  **MU and SanDisk slid ~5% pre** (sources conflict; one shows MU +3%). **Nasdaq-100 futures −1%, S&P −0.2%**;
  Brent up. The "does the semi rotation that took a 3% bite last week continue?" question is live again.
- **No binary for our names today.** **No watchlist name reports earnings today or this week** (week's
  reports are Delta/PepsiCo + Fed minutes — none ours; next tech META 07-29, AAPL 07-30) → **zero watchlist
  earnings/binary risk.** Oil firmer but energy still not a durable uptrend → **XOM stays parked.**
- **SPCX officially joins the Nasdaq-100 at today's open** (15 trading days after its 06-12 IPO) — noted
  future candidate, **still too new for the ribbon.** Today's big movers (TeraWulf +16% on an Anthropic
  data-center deal, VERA +6% into a PDUFA) are outside our liquid large-cap universe — not add candidates.

### Carried from daily review (07-06)
- **Book CLEAN & FLAT into 07-07** — 0 positions, equity **$9,427.33** all cash (confirmed live: equity
  $9,427.33, 0 open positions). Nothing locked; full watchlist free.
- **Regime caution actioned as a lens, not a park:** the chip cohort (AVGO/INTC/MU/AMD/TSM) faded a chip
  gap-up on 07-06 and stopped out; non-chip holds (AAPL/QQQ/C/BABA/SE) won. Today's Samsung/SK-Hynix memory
  wobble is the **same regime risk** — the long-only 5m gate simply won't fire longs in a downtrend, so the
  bot self-protects; **IMP-013 (SIZE_CONFIDENCE_CAP 85, shipped 07-06) now trims size on the very-high-conf
  / most-extended of these.** These are **not** park candidates (trends intact/recovering) → KEEP.
- **SE worked 07-06** (+$11.25 on adequate volume) → thin-tape watch stays "watch volume, no park."
- **No watchlist parks indicated on quality grounds.**

### Watchlist review
Account ACTIVE, equity **$9,427.33**, BP $37,709.32, **0 open positions = nothing locked.** 22 enabled /
5 parked (BIRD, ENPH, QCOM, WPM, XOM); 27 rows, 22 ≤ 30 ✓. Reviewed vs 14d closed-trade P&L from dbo.trades:
- **Leaders (14d):** TSLA **+$115** (5 tr, 4W), TSM +$57, AAPL +$47 (5/5), MSFT +$31, MU +$30, QQQ +$28,
  NFLX +$25, UNH +$24, NVDA +$22, SE +$14 — the semi/index/megacap regime the list is built around.
- **Laggards (14d):** AMD −$77 (4 tr, 1W), AMZN −$57 (5/0), AVGO −$45, JPM −$40, COST −$23, ABNB −$21,
  SPY −$17. Per the dailies/weekly every one is **regime / opening-drive-fade / weak-cross (IMP-011-filtered)
  — not signal quality**; all mega-liquid large-caps in intact/recovering trends (AMD bounced +3% pre today
  eyeing $546 resistance; AMZN/AAPL back at/above 20MA). None a liquidity or quality park → KEEP, on notice.
- **Chip cohort into the Samsung/SK-Hynix memory wobble** (MU/AVGO/INTC/AMD/NVDA/TSM): a **regime** headwind,
  not a symbol break; the gate won't open longs into weakness (fewer entries, not bad ones). No park.
- **C/COST/WMT/GOOG** low or negative recent activity but liquid large-caps the gate simply hasn't triggered
  cleanly — consistent with prior "keep inactive-but-liquid" discipline → no park-for-inactivity.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked, but the list is broad (22 ≤ 30) and semi/index/megacap-heavy; **zero
watchlist earnings/binary risk today or this week**; every laggard is regime/timing/weak-cross per the
dailies + weekly, none a signal-quality or liquidity park; and a **memory-chip-led risk-off open is the
wrong tape to chase a momentum add** (today's gainers are speculative/small names outside our universe;
SPCX too new). QCOM/BIRD/ENPH/WPM/XOM stay parked. Discipline: let IMP-011/IMP-013 keep proving out — do
not churn the list.

### Final watchlist
**22 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QQQ
SE SPY TSLA TSM UNH WMT. Parked: BIRD, ENPH, QCOM, WPM, XOM. Service **NOT restarted** (no watchlist change
→ the bot reads the list only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open
positions).

---

## 2026-07-08 — Pre-market Research

**Book CLEAN & FLAT into today** (0 broker positions, equity $9,248.27 all cash); nothing locked → full
watchlist free. No decided action carried in — the 07-07 daily review flagged **no park candidates** (the
1W/10L was a broad-regime whipsaw, explicitly *not* symbol quality). Review-and-hold unless overnight news
changes it.

### Market context
- **Chip / AI-valuation wobble continues; oil spikes on Iran.** Tue 07-07 closed lower on another AI/semis
  rotation: Dow **−0.25%** to 52,925 (off its record), S&P **−0.45%** to 7,503.85, Nasdaq Comp **−1.16%** to
  25,818; **SMH −3%**, MU −4.7%, AVGO/AMD/KLA/MRVL lower (Samsung prelim wobble + SK Hynix ~$28B US listing).
  This morning futures are **mixed/flattish** — S&P futures firm, **Nasdaq-100 futures soft (~29,400, techs
  "strong sell")**; Asia fell on AI-valuation fears. The "does the chip rotation keep biting?" question is live.
- **Oil SPIKED ~+5%** (Brent >$76, WTI >$72) after the US moved to **revoke the license permitting Iranian
  oil sales** — energy is bid, but a **single geopolitical headline, not a durable uptrend** → **XOM stays
  parked** (a bid oil name still isn't a clean intraday ribbon long; same discipline as every prior run).
- **Zero watchlist earnings/binary risk today or this week.** The week's reports are Delta/PepsiCo + Fed
  minutes — none ours; next tech is **META 07-29, AAPL 07-30**. Today's idiosyncratic movers (IBM +3% on a
  BofA target, Dell +4% on a Trump plug, EOSE, Circle +6%, AMZN +0.8% on a $25B bond sale, MSFT −1% on 4,800
  job cuts/Xbox, Rivian −10% offering) are not clean ribbon adds. **SPCX** (joined NDX 07-07) still too new.

### Carried from daily review (07-07)
- **Book CLEAN & FLAT into 07-08** — 0 positions, equity **$9,248.27** all cash (confirmed live this run).
  Nothing locked; full watchlist free.
- **07-07 was 1W/10L / −$179 — worst day since 06-17 — but a broad FALSE-BREAKOUT / whipsaw regime day**, not
  symbol failure: every 5m-gated fresh 1m cross faded with no follow-through anywhere; **all crosses mid-band
  (xo 0.21–0.35), zero strong (≥0.40) crosses fired all day** (the tape wasn't trending). All 11 names
  signalled/filled cleanly; C/NFLX/WMT/GOOG/SE were the biggest losers purely from fading with the market →
  **no watchlist parks indicated on quality grounds.** Do not park for a one-day regime loss.
- **Daily-review verdict = "NO CODE CHANGE WARRANTED"** (today's own data contradicts every ready
  entry-quality candidate; MIN_CROSSOVER raise would have cut the lone winner UNH xo 0.21 and kept the losers;
  the 07-06 MIN_VOLATILITY hypothesis failed to replicate) — a code/daily-review matter, no watchlist implication.
- **SE** faded 07-07 (−$21.84) after working 07-06 (+$11.25) → thin-tape watch stays **"watch volume, no park."**

### Watchlist review
Account ACTIVE, equity **$9,248.27**, BP $36,993, **0 open positions = nothing locked.** 22 enabled / 5 parked
(BIRD, ENPH, QCOM, WPM, XOM); 27 rows, 22 ≤ 30 ✓. Reviewed vs 10d closed-trade P&L from dbo.trades (57 tr, net
**−$60**, dragged entirely by the 07-07 −$179 whipsaw — the week ending 07-03 was **+$171 / PF 1.59 / 57% win**):
- **Leaders (10d):** TSLA **+$108** (4/3), TSM +$57 (3/2), AAPL +$39 (4/4), QQQ +$30 (2/2), INTC +$27 (3/2),
  NVDA +$13 — the semi/index/megacap trend cohort the list is built around.
- **Laggards (10d):** MSFT −$56 (early-entry chop + a non-binary 4,800-job-cut headline), AVGO −$45 (07-06
  highest-conf chip fade, now IMP-013-capped), AMZN −$45 (0W/4, regime fades; +0.8% pre on a $25B bond sale,
  back ≥20MA), SE −$41 (thin-tape watch), ABNB −$35, C −$26 (07-07 tape fade), GOOG/AMD/WMT/COST all regime.
  Every one is a **mega-liquid large-cap whose red is the 07-07 broad whipsaw + chip rotation** per the
  dailies/weekly — none a signal-quality or liquidity park → **KEEP, on notice.**
- **Chip cohort** (MU/AVGO/INTC/AMD/NVDA/TSM) into the continuing memory/AI-valuation wobble: a **regime**
  headwind, not a symbol break; the long-only 5m gate won't open longs into weakness (fewer entries, not bad
  ones) → no park.
- **C/COST/WMT/GOOG** low/negative recent activity but liquid large-caps the gate simply hasn't triggered
  cleanly — consistent with prior "keep inactive-but-liquid" discipline → no park-for-inactivity.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked; the list is broad (22 ≤ 30) and megacap/semi-heavy; **zero watchlist
earnings/binary risk today or this week**; every laggard is regime/whipsaw/chip-rotation per the dailies + the
A− weekly, none a quality or liquidity park; and a **chip-pressured / AI-valuation-wobble tape with an oil
spike is the wrong day to chase a momentum add** (today's gainers — IBM/Dell/EOSE/Circle — are idiosyncratic,
not ribbon trends; SPCX too new). QCOM/BIRD/ENPH/WPM/XOM stay parked (XOM's oil pop is one headline, not a
trend). Discipline: **IMP-013 (shipped 07-06) is still unobserved** — do not stack changes or churn the list
before it proves out.

### Final watchlist
**22 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QQQ SE
SPY TSLA TSM UNH WMT. Parked: BIRD, ENPH, QCOM, WPM, XOM. Service **NOT restarted** (no watchlist change → the
bot reads the list only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-07-09 — Pre-market Research

**Book CLEAN & FLAT into today** (0 broker positions, equity $9,302.94 all cash); nothing locked → full
watchlist free. No decided action carried in — the 07-08 daily review (5W/2L / +$54.69, full recovery from
the 07-07 whipsaw) flagged **no park candidates** and **NO CODE CHANGE WARRANTED**. Review-and-hold unless
overnight news changes it.

### Market context
- **Mixed-to-firmer, semis-led rebound attempt.** Futures: S&P +0.2%, **Nasdaq-100 +0.55–0.6%**, Dow ~flat.
  Semis bifurcated on the wires (one feed: **SMH +1.8%, MU +3.4%, SanDisk +2.4%**; another: MU −3.4%) — the
  memory/AI-valuation rotation that's chopped the tape all week is still live, but the NDX bid leans risk-on.
  Follows a weak Wed 07-08 (Dow tumbled on renewed Iran tensions).
- **Renewed US–Iran tensions + oil risk premium.** US launched fresh strikes on Iran (attacks on Strait of
  Hormuz shipping); Trump said the ceasefire is "over," then softened ("called Iran to make a deal") → crude
  roughly flat but with a re-established geopolitical risk premium. A **headline-driven oil bid, not a durable
  energy uptrend** → **XOM stays parked** (same discipline as every prior run).
- **BABA +11% pre-market** (watchlist name) — a clear **positive** catalyst; reinforces keeping it, no action.
- **Zero watchlist earnings/binary risk.** Today's reports are **PepsiCo (PEP)** + June existing-home sales —
  neither ours; next tech is **META 07-29, AAPL 07-30**. Today's big movers (VTAK +42%, IOTR +35%, PENG +19%,
  CMMB −20%, FCEL −20%) are speculative small-caps **outside our liquid large-cap universe** → not add
  candidates. **SPCX** (joined NDX 07-07) still too new for the ribbon.

### Carried from daily review (07-08)
- **Book CLEAN & FLAT into 07-09** — 0 positions, equity **$9,302.94** all cash (confirmed live this run).
  Nothing locked; full watchlist free.
- **No signal-quality parks.** 07-08 was a clean 5W/2L recovery on an orderly semis/megacap bounce (NVDA best
  +$39.69/+2.49%, BABA the strong-cross winner); both small losers (COST −$7.10, TSM −$8.91) were sub-1% EOD
  give-backs, not symbol failures. **Chip cohort traded fine** (3 of 4 green) → no chip parks.
- **SE** won again 07-08 (+$4.80) on a thin tape → thin-tape watch stays **"watch volume, no park."**
- **QCOM/BIRD/ENPH/WPM/XOM stay parked.** IMP-013 (SIZE_CONFIDENCE_CAP 85, shipped 07-06) is **still
  unobserved** — do not stack changes or churn the list before it proves out.

### Watchlist review
Account ACTIVE, equity **$9,302.94**, BP $37,211.76, **0 open positions = nothing locked.** 22 enabled /
5 parked (BIRD, ENPH, QCOM, WPM, XOM); 27 rows, 22 ≤ 30 ✓. Reviewed vs 10d closed-trade P&L from dbo.trades:
- **Leaders (10d):** TSLA **+$107.51** (4 tr, 3W), NVDA +$53.05 (3/2), TSM +$47.74, AAPL +$39.46 (**4/4**),
  QQQ +$29.95 (2/2), INTC +$26.90, BABA +$21.24 (2/2, and +11% pre today) — the semi/index/megacap trend
  cohort the list is built around, and exactly the names leading today's rebound attempt.
- **Laggards (10d):** MSFT −$56.08 (early-entry chop + non-binary job-cut headline), AMZN −$44.54 (0W/4,
  regime fades, back ≥20MA), SE −$36.64 (thin-tape watch), ABNB −$35.01, AVGO −$33.59 (07-06 high-conf chip
  fade, now IMP-013-capped), C −$26.43, COST −$24.76, GOOG −$23.04, AMD −$23.03, WMT −$22.13. Per the dailies
  + the A− weekly every one is a **mega-liquid large-cap whose red is the 07-07 broad whipsaw / chip rotation /
  weak-cross (IMP-011-filtered)** — none a signal-quality or liquidity park → **KEEP, on notice.**
- **Chip cohort** (MU/AVGO/INTC/AMD/NVDA/TSM) into the continuing memory/AI-valuation wobble: a **regime**
  headwind, not a symbol break; the long-only 5m gate won't open longs into weakness (fewer entries, not bad
  ones), and 07-08 showed it still finds clean longs when a trend forms (NVDA +2.49%) → no park.
- **C/COST/WMT/GOOG** low/negative recent activity but liquid large-caps the gate simply hasn't triggered
  cleanly — consistent with prior "keep inactive-but-liquid" discipline → no park-for-inactivity.

### Changes applied to dbo.watchlist
**No changes.** Nothing locked; the list is broad (22 ≤ 30) and megacap/semi-heavy; **zero watchlist
earnings/binary risk today or this week**; every laggard is regime/whipsaw/chip-rotation per the dailies + the
A− weekly, none a quality or liquidity park; BABA (+11% pre) is a positive, not a risk; and a bifurcated-chip /
renewed-Iran-tension tape with an oil bid is the wrong day to chase a momentum add (today's gainers —
VTAK/IOTR/PENG — are speculative small-caps outside our universe; SPCX too new). QCOM/BIRD/ENPH/WPM/XOM stay
parked (XOM's oil bid is one Iran headline, not a trend). Discipline: **IMP-013 is still unobserved** — do not
churn the list before it proves out.

### Final watchlist
**22 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C COST GOOG INTC JPM MSFT MU NFLX NVDA QQQ SE
SPY TSLA TSM UNH WMT. Parked: BIRD, ENPH, QCOM, WPM, XOM. Service **NOT restarted** (no watchlist change → the
bot reads the list only at startup, so a restart would be pointless churn). 🔒 Locked: none (0 open positions).

---

## 2026-07-10 — Pre-market Research

### Market context
- **Quiet, slightly soft open.** S&P futures ~flat/+0.2%, Nasdaq-100 futures **−0.2/−0.4%**, Dow +0.25%,
  Russell ~flat. **VIX ~15.9** (calm). Driver is **sticky bond yields — US 10Y ~4.6%** keeping "one more Fed
  hike" chatter alive; gold −0.6%. Year's hot rally "losing steam" narrative but no shock.
- **No watchlist-name earnings today or this week** (next META 07-29, AAPL 07-30) → **zero binary event risk.**
- Movers: HPE +9.9%, Lumentum (LITE) +11% (post-report pops — speculative/mid-cap optical, outside our clean
  large-cap trend universe); **COST −4.2% pre** (see below). SpaceX joining the Nasdaq-100 (SPCX still too new
  for the ribbon); OPEC "$40 oil" survival story keeps energy soft → **XOM stays parked**.

### Carried from daily review (07-09)
- Book **CLEAN & FLAT** into today — 0 broker positions, 0 DB-open rows, equity **$9,325.49** all cash.
  **Nothing locked**; full watchlist free. Verified against `/v2/positions` (count 0).
- 07-09 was healthy (4W/6L, **+$22.58**, PF 1.23, positive expectancy; exit infra flawless, books exact).
- Acted on the notes: **INTC** kept (maxed-conf fade is a *sizing*, not a quality, issue — IMP-013 now
  de-sizes the top band; keep, size-aware). **AVGO** flagged for whipsaw (chopped both ways −$43 on 07-09) →
  kept but on **whipsaw watch**. **MU/TSLA** scratches = flat-tape, kept. Parked set unchanged.

### Watchlist review
22 enabled reviewed vs overnight news + 14d closed-trade P&L (`dbo.trades`):
- **Winners/keeps:** TSLA +$115.09 (4/6), NVDA +$52.56, BABA +$48.10 (3/3), AAPL +$46.86 (5/5), TSM +$28.36,
  QQQ/MSFT/SE/UNH/MU green — core trend/megacap engine intact. SE thin-tape watch stays "watch volume, no park"
  (won again 07-09, +2.78%).
- **COST → PARK.** The one clear negative catalyst: June sales report **disappointed** (comps +8.8% vs May's
  +12.5%, missed ~10.6% est), FCF "air pocket" from heavy CapEx, JPMorgan cut PT → stock **−4.47% (07-09) then
  −4.2% pre (07-10)**, an **~8% two-day gap-down** now below both 20MA (958) and 50MA (989; 07-08 close 953,
  now ~$910). Also the **worst recent P&L on the list — 0W/4, −$29.61 (14d)** and a diversifier (WMT still
  covers consumer staples). A long-only intraday-ribbon strategy should not chase a name in an accelerating,
  catalyst-driven downtrend. Parked.
- **AVGO / AMZN — kept despite red 14d** (AVGO −$76.85, AMZN −$50.47). Mega-liquid trend names; per 07-09
  review these are **regime give-backs, not symbol failures** (both signalled and traded fine on trend days).
  AVGO on explicit **whipsaw watch** — if it stops out early and re-signals same-day, treat with suspicion.
- **No adds.** Today's gainers (HPE/LITE) are single-session earnings pops, not clean established trends; a
  soft-Nasdaq, sticky-yield tape is the wrong day to chase momentum, and the list is already broad. SPCX too
  new. **IMP-013 still barely observed (1 live confirmation, 07-09) — do not churn the list before it proves.**
- **No re-enables.** QCOM/BIRD/ENPH/WPM/XOM all still lack a positive catalyst (XOM: oil still soft on the
  OPEC story). Stay parked.

### Changes applied to dbo.watchlist
- **PARK COST** (`enabled=0`): June-sales miss + JPM PT cut, ~8% 2-day gap-down below 20/50MA, worst 14d P&L
  (0W/4, −$29.61). No adds, no re-enables.

### Final watchlist
**21 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SE SPY TSLA TSM UNH
WMT. Parked: BIRD, COST, ENPH, QCOM, WPM, XOM. Service **restarted** — active, clean startup, warmup primed
21/21, 21-symbol iex subscribe confirmed in journal (COST absent, no errors). 🔒 Locked: none (0 open positions).

---

## 2026-07-13 — Pre-market Research

**Q2 earnings season starts this week and it hits the watchlist** — the 07-10 daily-review note
("no watchlist-name earnings next week → zero binary risk") is **superseded by fresh news**: JPM & C
report **Tue 07-14 pre-open**, TSM **Wed 07-15**, NFLX & UNH **Thu 07-16**. Book CLEAN & FLAT
(0 positions), nothing locked → full watchlist free.

### Market context
- **Futures LOWER, chip-led selloff.** S&P −0.3%, Nasdaq-100 **−0.9%**, Dow ~flat. A **memory/AI-chip
  reversal**: SK Hynix ADR **−8%** (after its +13% Fri Nasdaq debut) dragged the complex — **MU −5.2%**,
  SanDisk −6.3%, Seagate −4%, **AMD −2.6%**, INTC lower; Samsung −10.7% / SK Hynix Korea −15% overnight.
  Attributed to profit-taking + ADR-vs-Korea valuation uncertainty. Follows a green Fri (S&P +0.4%).
- **Renewed US–Iran strikes over the weekend** (Strait of Hormuz) — oil risk premium back, but a
  headline, not a durable energy uptrend → **XOM stays parked** (same discipline as every prior run).
- **Event-heavy week:** **Tue 07-14 June CPI 8:30 ET + Warsh's first congressional testimony** (macro
  binary; CME prices a possible Sept hike), Wed PPI, Thu Retail Sales. **Earnings on our list:** JPM/C
  (Tue pre-open), TSM (Wed), NFLX/UNH (Thu). Nothing reports **today**.

### Carried from daily review (07-10)
- **Book CLEAN & FLAT into Mon 07-13** — 0 broker positions, 0 DB-open rows, equity **$9,307.12** all
  cash (== last_equity; confirmed live via /v2/positions count 0). Nothing locked.
- **NVDA** the 07-10 star (+1.20%, high conf + strong volume) → keep; **SE** high-conf fade/stop on thin
  volume → "watch volume, no park"; **TSLA** popped-then-reversed → chop watch; **C/AMZN** low-conf chop,
  keep. **QCOM/BIRD/ENPH/WPM/XOM/COST stay parked.** IMP-013/014 still proving — no entry-logic churn.

### Watchlist review
Account ACTIVE, equity **$9,307.12**, BP $37,228, **0 open positions = nothing locked.** 21 enabled /
6 parked (BIRD, COST, ENPH, QCOM, WPM, XOM); 27 rows. Reviewed vs 14d closed-trade P&L from dbo.trades:
- **Leaders (14d):** TSLA **+$82.4** (6/3), NVDA **+$77.8** (4/3), BABA +$48.1 (3/3), AAPL +$39.5 (4/4),
  QQQ +$30 (2/2), TSM +$28.4 — the trend/megacap engine the list is built around; NVDA/TSLA/AAPL/BABA keep.
- **Laggards (14d):** AVGO −$76.9 (whipsaw watch), MSFT −$56.1 (early-entry chop), AMZN −$35.8 (0-heavy,
  regime fades), C −$27.1, GOOG −$23, AMD −$23, WMT −$22.1. All mega-liquid large-caps whose red is the
  07-07 whipsaw / chip rotation / weak-cross (IMP-011-filtered) per the dailies + C-grade weekly — none a
  signal-quality or liquidity park → KEEP, on notice. **Chip cohort** (MU/AMD/INTC/AVGO/TSM/NVDA) sells
  off pre-market on the SK Hynix reversal — a **regime** headwind; the long-only 5m gate won't open longs
  into weakness (self-protects) → no park.
- **Earnings risk THIS WEEK:** JPM & C report **Tue 07-14 pre-open** → **today (Mon) is the last session
  before their prints**; a Monday entry risks a naked-overnight carry into a binary bank-earnings event if
  the EOD flatten hiccups (the exact tail the MU-park discipline guards). Both are financials/diversifiers,
  not core trend names → **PARK both today**, re-enable after the prints. TSM (Wed)/UNH (Wed-park)/NFLX
  (Thu) are flagged for the Tue/Wed/Thu routines, not today's park.
- **Parked re-enable check:** COST (still downtrending, no catalyst), QCOM (chip laggard into a chip
  selloff), ENPH/WPM/BIRD, XOM (oil bid is one Iran headline, not a trend) → **all stay parked, no re-enable.**

### Changes applied to dbo.watchlist
- **PARK JPM** (enabled=0): reports earnings Tue 07-14 pre-open (Q2 bank kickoff); avoid naked-overnight
  carry into the print; re-enable after.
- **PARK C** (enabled=0): reports earnings Tue 07-14 pre-open (Q2 bank); avoid naked-overnight carry into
  the binary print; re-enable after.
- **No adds** — a chip-selloff, risk-off Monday into CPI/earnings week is the wrong tape to chase a
  momentum add (SK Hynix too new; today's weakness isn't a ribbon trend). **No re-enables.**

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA GOOG INTC MSFT MU NFLX NVDA QQQ SE SPY TSLA TSM UNH
WMT. Parked: BIRD, C, COST, ENPH, JPM, QCOM, WPM, XOM. Service **restarted** 11:35 UTC — active, clean
startup, warmup primed **19/19** from history, 19-symbol iex subscribe confirmed in journal (JPM/C absent,
no errors), account ACTIVE equity $9,307.12, 0 positions reconciled. 🔒 Locked: none (0 open positions).

---

## 2026-07-15 — Pre-market Research

**Earnings-timing correction day.** The 07-14 daily-review notes carried provisional print dates
("TSM Wed 07-15, UNH Wed 07-15, NFLX Thu 07-16") that fresh SEC/company-source verification this
morning **corrected**: **TSM and UNH both report Thu 07-16 pre-open** (not Wed), **NFLX reports Thu
07-16 after the close**. Applying the standing "never hold a name overnight into its binary print"
discipline (the MU/JPM/C park rule) with the *correct* dates flips two of the three actions — see below.

### Market context
- **Cautiously positive, tech-led.** Futures modestly higher pre-open (Dow +0.2%, S&P +0.18%,
  **Nasdaq-100 +0.46%**) after **Tuesday's softer-than-expected June CPI** cut Fed-hike odds to
  ~17% (CME FedWatch, from ~41%). **June PPI today** + **day 2 of Warsh's congressional testimony**
  are the macro wildcards; Warsh said one data point isn't victory on inflation → caps the relief.
- **Chips firm:** ASML +3.8% pre on raised 2026 guidance (AI-demand reassurance) lifting the semi
  complex — a tailwind for our AVGO/NVDA/AMD/INTC/MU cohort. PayPal +18.5% on a Stripe/Advent
  takeover bid (not ours). Banks kicked off Q2 strong Tuesday (JPM/C both cleared, re-enabled 07-14).
- **Q2 earnings — verified dates:** **JPM & C reported Tue 07-14 pre-open** (cleared → both enabled).
  **TSM Thu 07-16 pre-open**, **UNH Thu 07-16 pre-open (8am ET call)**, **NFLX Thu 07-16 after close**.
  **No watchlist name reports today (Wed 07-15).** Renewed Strait-of-Hormuz/Iran tension bids oil —
  a headline, not a trend → **XOM stays parked**.

### Carried from daily review (07-14)
- **Book CLEAN & FLAT into today** — broker-confirmed **0 positions**, equity **$9,193.22** all cash
  (== last_equity). **Nothing locked**; watchlist free.
- **Re-enable JPM & C** (prints cleared 07-14) → **already done 07-14** (both enabled, notes dated).
- **Earnings parks "per timing":** verified TSM & UNH are **Thu pre-open** ⇒ the session that would
  carry them naked overnight *into* the print is **today (Wed)** → **PARK both today** (consistent with
  the note's "park the session before its print"). NFLX is **Thu after-close** ⇒ Thursday, not Wednesday,
  is its last pre-print session, so **KEEP NFLX today** and park it in the **Thu 07-16** routine. This
  corrects the note's premise that "Wed is NFLX's last pre-print session" (it isn't — NFLX prints Thu PM).
- **TSLA/WMT/INTC** losers 07-14 were regime/CPI-tape stop-outs (INTC's same-day re-entry won +$22.33)
  → no quality parks. **QCOM/BIRD/ENPH/WPM/XOM/COST stay parked.**

### Watchlist review
Account ACTIVE, equity **$9,193.22**, BP $36,772, **0 open positions = nothing locked.** 21 enabled /
6 parked reviewed vs 12d closed-trade P&L from dbo.trades:
- **Leaders (12d):** NVDA **+$55.84** (3/2), BABA **+$48.10** (3/3), SE **+$28.62** (5/3), ABNB +$26.07
  (3/2), AAPL +$15.23, QQQ +$11.51 (2/2) — the trend/megacap engine; keep.
- **Laggards (12d):** AVGO −$87.70, NFLX −$75.86 (2/0 — the high-conf fades 07-13/prior), INTC −$64.14,
  WMT −$54.82, TSLA −$46.73, TSM −$31.23, C −$27.09. All mega-liquid large-caps whose red is the
  07-07 whipsaw / chip rotation / weak-mid-cross CPI chop per the dailies — **none a signal-quality or
  liquidity park** → KEEP, on notice. Chip cohort catches today's ASML/AI tailwind.
- **Earnings risk:** TSM & UNH print **Thu pre-open** → parked today (overnight-into-binary). NFLX prints
  **Thu after-close** → kept today, flagged for a **Thu park**. JPM/C prints cleared → stay enabled.
- **Parked re-enable check:** COST (still downtrend/June-sales miss), QCOM (chip laggard), ENPH/WPM/BIRD,
  XOM (oil is one Iran headline, not a trend) → **all stay parked, no re-enable.**

### Changes applied to dbo.watchlist
- **PARK TSM** (enabled=0, note dated): reports **Thu 07-16 pre-open**; avoid a naked-overnight carry
  into the binary print; re-enable after.
- **PARK UNH** (enabled=0, note dated): reports **Thu 07-16 pre-open (8am ET)**; same overnight-binary
  discipline; re-enable after.
- **No adds** — mid-earnings-season on a PPI + Warsh-testimony day is the wrong tape to chase a momentum
  add; the list is broad and already semi/megacap-heavy. **No re-enables.**

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SE SPY TSLA
WMT. Parked: BIRD, COST, ENPH, QCOM, TSM, UNH, WPM, XOM. Service **restarted** 11:34 UTC — active, clean
startup, warmup primed **19/19** from history, 19-symbol iex subscribe confirmed in journal (TSM/UNH
absent, no errors), account ACTIVE equity $9,193.22, 0 positions. 🔒 Locked: none (0 open positions).
**Thu 07-16 routine: PARK NFLX** (earnings after close) and keep TSM/UNH parked through their prints.

---

## 2026-07-16 — Pre-market Research

**Earnings-rotation day.** Two carried actions land today: **PARK NFLX** (reports after today's
close → today is its last pre-print session) and unwind the TSM/UNH earnings parks now that both
have reported **pre-open this morning** (same play as JPM/C re-enabled on their 07-14 print morning).

### Market context
- **Mixed tape, chips soft, Big-Tech-led.** Futures mixed pre-open (Dow +0.2%, **Nasdaq-100 −0.47%**,
  Russell −0.36%, VIX ~16). Soft **June CPI** (−0.4% m/m, 3.5% y/y; core 2.6%) eased hike fears, but
  **June PPI (annual 5.5%)** + Warsh caution capped the relief. Wed 07-15 closed higher on a clear
  **rotation OUT of chips INTO Big Tech**: AAPL +4% (ATH), AMZN/GOOG ~+3%, MSFT ~+3%, while **MU −8%,
  AMD/LRCX −3%**. This morning **semis sell off across Asia** (KOSPI −6%, Nikkei −3%) on AI-valuation
  skepticism → a **regime** headwind for our chip cohort (AVGO/NVDA/AMD/INTC/MU/TSM); the long-only 5m
  gate self-protects (won't open longs into weakness). Oil climbed on renewed Iran headlines → **XOM
  stays parked**.
- **Earnings — verified today:** **TSM reported pre-open** (record Q2: rev ~$40.2B +36% y/y, GM 67.7%,
  ADR EPS $4.31 +14% beat, raised FY26 to >40% growth) — **yet ADR gaps DOWN ~3–4%** to ~$402 (from
  $419.48) on priced-to-perfection + a raised $62B capex bill / falling FCF. **UNH reported pre-open**
  (adj EPS **$6.38** vs ~$4.85 est, big beat + **raised FY26 adj to $19.50–20.00**) — strongly positive.
  **NFLX reports AFTER today's close.** No other watchlist name reports today.

### Carried from daily review (07-15)
- **Book CLEAN & FLAT into today** — broker-confirmed **0 positions**, equity **$9,155.03 == last_equity**,
  all cash. **Nothing locked**; watchlist free (subject to the earnings actions).
- **PARK NFLX today** (after-close print) — **actioned** (the standing naked-into-binary discipline).
  NFLX was correctly kept 07-15 and stopped −1.97% (regime, not a quality park).
- **Keep TSM/UNH parked through their prints, re-enable after** — both prints are **out pre-open this
  morning** (before the 9:30 ET open), so their overnight-into-binary risk is resolved → **re-enable
  both today**, exactly as JPM/C were re-enabled on their 07-14 pre-open print morning. TSM's gap-down
  is a reaction, not a broken thesis; the gate won't chase it. UNH's beat is clean.
- **GOOG** (07-15 sole win, full-confirm-stack trend) → keep. **SE/NFLX** low-volume fades (regime, not
  quality). **QCOM/BIRD/ENPH/WPM/XOM/COST stay parked.** IMP-013/014 proving — no entry-logic churn.

### Watchlist review
Account **ACTIVE**, equity **$9,155.03**, BP $36,620, **0 open positions = nothing locked.** 19 enabled /
8 parked reviewed:
- **Core megacap/trend engine** (AAPL/AMZN/GOOG/MSFT/QQQ/SPY/TSLA/NVDA) — AAPL/AMZN/GOOG/MSFT are the
  *leaders* of today's rotation; keep. Chip cohort (AVGO/AMD/INTC/MU/TSM) faces an Asia-led semi selloff
  — a **regime** headwind, not a symbol/quality issue; the long-only gate self-protects → **keep, on notice.**
- **BABA/SE/ABNB/C/WMT** — mega/large-liquid; recent red is 07-07 whipsaw / weak-mid-cross chop per the
  dailies, none a liquidity or signal-quality park → keep.
- **Earnings actions:** NFLX (after-close) → **PARK**. TSM & UNH (pre-open prints cleared) → **RE-ENABLE**.
- **Parked re-enable check:** COST (still downtrend/June-sales miss), QCOM (chip laggard into a chip
  selloff), ENPH/WPM/BIRD, XOM (oil is one Iran headline, not a trend) → **all stay parked, no re-enable.**

### Changes applied to dbo.watchlist
- **PARK NFLX** (enabled=0): reports earnings **after today's close**; no naked-overnight into a binary
  print; re-enable after the print is digested.
- **RE-ENABLE TSM** (enabled=1): Q2 pre-open print cleared (record beat; gapped down ~4% on priced-to-
  perfection); binary event risk resolved — park was event-driven, not a demotion.
- **RE-ENABLE UNH** (enabled=1): Q2 pre-open print cleared (beat + raised FY guidance); event risk resolved.
- **No adds** — a chip-selloff, rotation, PPI/retail-sales day is the wrong tape to chase a momentum add;
  the list is broad and already megacap/semi-heavy.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NVDA QQQ SE SPY TSLA TSM UNH
WMT. Parked: BIRD, COST, ENPH, NFLX, QCOM, WPM, XOM. Service **restarted** 11:35 UTC — active, clean
startup, warmup primed **20/20** from history, 20-symbol iex subscribe confirmed in journal (NFLX absent,
TSM/UNH present, no errors), account ACTIVE equity $9,155.03, 0 positions reconciled. 🔒 Locked: none.
**Fri 07-17 routine: re-enable NFLX** once the after-close print is digested (check the post-print gap).

---

## 2026-07-17 — Pre-market Research

**NFLX re-enable day.** The 07-16 daily review scheduled one action for today: unwind the NFLX
event-park now that its after-close print is resolved. Book is CLEAN & FLAT (0 positions) →
NFLX is not locked and is free to re-enable.

### Market context
- **Broad risk-OFF, semis-led.** Futures lower into the open: Dow −0.6%, S&P −0.9%, **Nasdaq-100
  −1.9%** on **AI-spending jitters**. A fresh **semiconductor selloff**: SOXX −3.7%, **NVDA −3%,
  MU/INTC/ARM −4%, AMAT/LRCX −5%** — a direct **regime** headwind for our chip cohort
  (AVGO/AMD/INTC/MU/TSM/NVDA); the long-only 5m gate self-protects (won't open longs into
  weakness). Majors head for a losing week. Gold bid as a safe haven.
- **NFLX Q2 (after 07-16 close):** narrow EPS beat (~in-line rev) but **weak Q3 guidance**
  (rev growth ~11.7% vs ~$13B est) + decelerating growth + engagement worries → **stock −8–9%
  after hours to a fresh 52-week low** (−21% YTD). A **chart-breaking gap DOWN**, the mirror of
  MU's 06-25 blowout re-enable — but a gap-down does not disqualify a top-liquid mega-cap; the
  gate simply won't chase it lower.
- **Earnings today:** TRV, TFC, ISRG (−10% post-print), FITB — **none on our watchlist.** No
  watchlist name reports today. Oil firm on Iran headlines → **XOM stays parked**.

### Carried from daily review (07-16)
- **Book CLEAN & FLAT into today** — broker-confirmed **0 positions**, equity **$9,134.34 ==
  last_equity**, all cash. **Nothing locked.**
- **RE-ENABLE NFLX** (after-close print digested) → **actioned.** Gap is a hard down-move to a
  52-wk low, but the park was purely event-driven (naked-into-binary); the binary is resolved.
  NFLX is a liquid, intraday-trending mega-cap = strategy universe; the long-only gate
  self-protects while it sits in a post-earnings downtrend, exactly as it does on the chip
  cohort today. Parking a liquid name merely for gapping down would contradict keeping
  AMD/INTC/MU/NVDA enabled through the same risk-off tape. Re-enabled, on notice. Asset
  re-verified on Alpaca: `tradable=true, status=active`.
- **TSM & UNH** re-enabled 07-16 post-print, behaved as regime names → keep. **BABA** kept
  (fade-prone on notice). **Chip cohort** kept (regime headwind, no watchlist fix). **Fade-tape
  watch (now 5th soft session):** resist adding momentum names into rotation/risk-off chop.

### Watchlist review
Account **ACTIVE**, equity **$9,134.34**, BP $36,537, **0 open positions = nothing locked.**
20 enabled / 7 parked reviewed vs 14d closed-trade P&L from dbo.trades (61 tr, 21W, net
**−$345** — the 07-07 whipsaw + a 4-day fade stretch; regime, per the dailies):
- **14d greens:** NVDA +$55.84 (3, 2W), BABA +$27.46 (4, 3W), ABNB +$21.39, AAPL +$15.23,
  QQQ +$11.51 (2/2), GOOG +$10.65, UNH +$2.88 — the trend/megacap engine still pays on
  dispersion days. **Reds:** NFLX −$100.85 (0/3, pre-park regime), AVGO −$87.70, INTC −$64.14,
  WMT −$54.82, TSLA −$46.73, TSM −$31.23 — every one is **regime (07-07 whipsaw / semi
  rotation / fade tape), not signal or liquidity quality** per the daily reviews; all
  mega-liquid, none a park candidate.
- **Parked re-enable check:** COST (still downtrend / June-sales miss, 0/4), QCOM (−14% vs
  20/50MA, thin $vol, lone chip laggard into a chip selloff), ENPH/WPM/BIRD, XOM (oil is one
  Iran headline, not a trend) → **all stay parked, no re-enable.**

### Changes applied to dbo.watchlist
- **RE-ENABLE NFLX** (enabled=1, note "re-enabled 2026-07-17: earnings binary resolved (weak Q3
  guide, ~8% gap-down to 52wk low); gate self-protects, on notice"). The single decided action.
- **No adds** — a risk-off, AI-jitters, semi-selloff Friday (5th straight soft/fade session) is
  the wrong tape to chase a momentum add; the list is broad and already megacap/semi-heavy.
  BIRD/COST/ENPH/QCOM/WPM/XOM stay parked.

### Final watchlist
**21 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SE
SPY TSLA TSM UNH WMT. Parked (6): BIRD COST ENPH QCOM WPM XOM. Service **restarted** 11:35 UTC —
active, `NRestarts=0`, clean startup, warmup primed **21/21** from history, 21-symbol iex
subscribe confirmed in journal (NFLX present, no errors), account ACTIVE equity $9,134.34,
0 positions reconciled. 🔒 Locked: none (0 open positions).

---

## 2026-07-20 — Pre-market Research

**First session after the worst week on record** (wk-end 07-17 all-5-days-red, −$285.95 / −3.07%,
Grade D). Book is CLEAN & FLAT (0 positions, equity all cash) → nothing locked, full watchlist free.
The week's damage was regime (07-07 whipsaw + a semis-led risk-off fade), not symbol quality — the
weekly/daily reviews' one ranked fix is a strategy-level daily-drawdown circuit breaker (a
critical-path *code* candidate owned by the daily-review routine), **not a watchlist action.**

### Market context
- **Risk-ON open after a brutal chip week.** Futures higher: S&P +0.3%, **Nasdaq-100 +0.6%**, Dow
  +131 (+0.3%); QQQ +0.40% / SPY +0.22% pre. **Chipmakers rebounding** after last week's SMH −9%
  (3rd weekly drop in 4; Fri's leg was a Moonshot-AI model scare). Polymarket ~68% "up" open. Fed
  FedWatch prices ~88% hold at the July meeting.
- **Oil elevated** — Brent +2.3% to ~$90 on a 9th day of US–Iran strikes, but midmorning diplomacy
  hopes (Iran open to talks) capped it. A one-headline bid, not a durable energy uptrend → **XOM
  stays parked** (same discipline as prior runs).
- **⚠️ The AI-trade's pivotal earnings week.** **GOOG + TSLA (+ PM, IBM, TXN, T) report Wed 07-22
  after the close**; **INTC headlines Thu 07-23**; GM Tue 07-21 BMO. **No watchlist name reports
  today** (Mon: DPZ, AMC) **or Tue** → zero watchlist earnings risk today. Three $1T+ prints Wed
  make this a volatility-heavy week — the wrong tape to chase a momentum add into.

### Carried from daily review (07-17)
- **Book CLEAN & FLAT into Mon 07-20** — daily review said equity $9,021.08 all cash, nothing
  locked; **confirmed live this run** (ACTIVE, equity **$9,021.05**, 0 positions).
- **Chip cohort (INTC/TSM/MU/NVDA/AVGO/AMD)** took the day's real damage on the semis selloff
  (INTC −$39.60 + TSM −$32.20 = 63% of the loss) — all signalled and stopped **correctly**;
  **regime, NOT symbol/liquidity quality → keep all enabled.** "Resist adding chip/momentum into a
  risk-off tape" → honored (no adds).
- **NFLX** — first session back after the earnings re-enable, faded −1.11% into its post-print
  downtrend. Explicit guidance: **keep, on notice as fade-prone until it bases** (not a quality
  park; binary resolved, liquid mega-cap, long-only gate self-protects in a downtrend).
- **UNH / MU** faded/scratched on regime → keep. **"No parks indicated."** honored.

### Watchlist review
Account **ACTIVE**, equity **$9,021.05**, BP $36,084, **0 open positions = nothing locked.** 21
enabled / 6 parked reviewed vs 14d closed-trade P&L from dbo.trades (net negative — the all-red
week; regime per the dailies):
- **14d greens:** NVDA **+$55.84** (3, 2W), BABA +$27.46 (4, 3W), ABNB +$21.39 (4, 2W), AAPL
  +$15.23 (1/1), QQQ +$11.51 (2/2), GOOG +$10.65 — the trend/megacap engine still pays on
  dispersion days. **Reds:** NFLX **−$124.70** (0/4), INTC −$103.74 (1/5), AVGO −$87.70 (1/4),
  TSM −$63.43 (0/4), WMT −$54.82 (0/2), TSLA −$46.73 (1/4) — every one is **regime (07-07 whipsaw /
  semis-led all-red week), not signal or liquidity quality** per the daily reviews; all mega-liquid,
  none a park candidate.
- **NFLX** is the worst 14d symbol and sits in a fresh post-earnings downtrend at a 52-wk low, but
  the daily review is explicit: **keep, on notice** — parking a top-liquid mega-cap merely for
  gapping down would contradict keeping the chip cohort through the same risk-off tape, and the
  long-only 5m gate won't chase it lower. One more session of evidence before any park.
- **Parked re-enable check:** BIRD (micro-cap), COST (June-sales miss downtrend, 0/4), ENPH (10.9%
  ATR whipsaw), QCOM (−14% vs 20/50MA, thin $vol, lone chip laggard), WPM (dead-vol downtrend),
  XOM (oil is one Iran headline, not a trend) → **all stay parked, no fresh bullish catalyst.**

### Changes applied to dbo.watchlist
- **No changes.** Nothing locked, but the list is broad (21 ≤ 30) and already megacap/semi-heavy;
  **zero watchlist earnings risk today**; every laggard is regime per the dailies, none a
  signal-quality or liquidity park (NFLX kept on notice); and a chip *bounce* into the AI-trade's
  most pivotal earnings week (3× $1T+ prints Wed) is the wrong tape to chase a momentum add.
  BIRD/COST/ENPH/QCOM/WPM/XOM stay parked.
- **⚠️ Binary-event parks queued for later this week (NOT today):** **GOOG + TSLA report Wed 07-22
  after close → the Wed 07-22 pre-market routine MUST park both before Wed's open** (no overnight
  binary hold). **INTC reports Thu 07-23 → the Thu routine parks INTC.** Today carries none of these.

### Final watchlist
**21 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA
QQQ SE SPY TSLA TSM UNH WMT. Parked (6): BIRD COST ENPH QCOM WPM XOM. Service **NOT restarted** (no
watchlist change → the bot reads the list only at startup, so a restart would be pointless churn;
service already `active` since the Fri 07-17 11:35 UTC restart, NRestarts=0). 🔒 Locked: none (0 open positions).

---

## 2026-07-21 — Pre-market Research

**Second session of the AI-trade's pivotal earnings week.** Book is CLEAN & FLAT (0 positions,
equity all cash) → nothing locked, full watchlist free. Today carries **zero watchlist earnings
risk**; the week's binary parks are queued for **Wed 07-22 (GOOG + TSLA, after close)** and
**Thu 07-23 (INTC)** — none today. No watchlist action indicated this run.

### Market context
- **Risk-ON, chip-led rebound.** Futures higher: **Nasdaq-100 +1.3%**, S&P +0.5%, Dow +0.3%;
  QQQ +1.38% ($705.68) / SPY +0.56% ($746.28) pre. **Semis revive** — KOSPI +2% overnight on
  chip strength; Mon's after-hours already showed AVGO +2%, MU +1.9%, AMD +1.6%, INTC +2.1%.
  The 2-week semis/AI-capex risk-off regime that damaged our chip cohort is **easing this
  morning**, but it's a *bounce* into the pivotal AI-earnings week — the wrong tape to chase adds.
- **Monday 07-20 closed mostly lower** (S&P −0.2%, Dow −307, Nasdaq-100 ~flat) on renewed
  **US–Iran tensions** — oil swung sharply, Treasury yields rose (energy-driven inflation →
  rate-hike-later-this-year expectations). Oil elevated on the conflict, capped by diplomacy
  hopes: a one-headline bid, not a durable energy uptrend → **XOM stays parked**.
- **⚠️ Earnings — verified none of ours today.** Tue 07-21 reporters: **GM (BMO), Novartis, 3M
  (MMM), Halliburton** — **no watchlist name.** GOOG + TSLA report **Wed 07-22 after close**
  (→ Wed routine parks both); **INTC Thu 07-23** (→ Thu routine parks INTC). Season strong so
  far (88% of ~50 S&P reporters beat, FactSet).

### Carried from daily review (07-20)
- **Book CLEAN & FLAT into Tue 07-21** — daily review said equity $8,927.72 all cash, nothing
  locked; **confirmed live this run** (ACTIVE, equity **$8,927.72**, 0 positions, BP $35,710).
- **Semis/AI-capex regime persisted into a 2nd week** — NVDA/AMD/AVGO all stopped 07-20 (plus
  GOOG); all signalled and stopped **correctly = regime, not symbol/liquidity quality; keep all
  enabled.** "Resist adding chip/momentum into this tape" → honored (no adds, even on today's bounce).
- **NVDA phantom-exit was a bot bug (IMP-015 shipped), not a symbol problem** — its real trade
  was a normal regime stop-out → keep, no action.
- **BABA** the clean trend winner two setups running (+$33.36 on 07-20) → keep.
- **SE (xo 0.22 / vol 0.0) and AVGO (vol 0.0)** traded on zero relative volume — thin, fade-prone,
  but a **signal-scoring** matter (both liquid, both signalled), **not a watchlist park.** Honored.
- **QCOM / BIRD / ENPH / WPM / XOM / COST stay parked.** Honored.

### Watchlist review
Account **ACTIVE**, equity **$8,927.72**, BP $35,710, **0 open positions = nothing locked.** 21
enabled / 6 parked reviewed against the chip-bounce risk-on tape + the dailies' 14d P&L read:
- **Core megacap/trend engine** (AAPL/AMZN/GOOG/MSFT/QQQ/SPY/NVDA/TSLA) — the dispersion-day
  earners; GOOG +1.5% pre ahead of Wed's guidance. Keep. **Chip cohort** (AVGO/AMD/INTC/MU/TSM)
  bounces this morning; the long-only 5m gate only opens longs if a real trend forms → keep, on notice.
- **BABA/SE/ABNB/C/WMT/UNH** — mega/large-liquid; recent red is regime (semis rotation / 07-07
  whipsaw / fade tape) per the dailies, none a liquidity or signal-quality park → keep. NFLX kept
  **on notice** (fade-prone in its post-earnings downtrend, but liquid mega-cap, gate self-protects).
- **Parked re-enable check:** COST (June-sales-miss downtrend, 0/4), QCOM (−14% vs 20/50MA, thin
  $vol, lone chip laggard), ENPH (10.9% ATR whipsaw), WPM (dead-vol downtrend), BIRD (micro-cap),
  XOM (oil is one Iran headline, not a trend) → **all stay parked, no fresh bullish catalyst.**

### Changes applied to dbo.watchlist
- **No changes.** Nothing locked; the list is broad (21 ≤ 30) and already megacap/semi-heavy;
  **zero watchlist earnings risk today**; every laggard is regime per the dailies, none a
  signal-quality or liquidity park (NFLX kept on notice); and a chip *bounce* into the week's
  three $1T+ prints (GOOG/TSLA Wed, INTC Thu) is the wrong tape to chase a momentum add.
  BIRD/COST/ENPH/QCOM/WPM/XOM stay parked.
- **⚠️ Binary-event parks queued (NOT today):** **Wed 07-22 pre-market routine MUST park GOOG +
  TSLA** before Wed's open (both report after Wed's close). **Thu 07-23 routine parks INTC.**

### Final watchlist
**21 enabled** (≤30 ✓, unchanged): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA
QQQ SE SPY TSLA TSM UNH WMT. Parked (6): BIRD COST ENPH QCOM WPM XOM. Service **NOT restarted** (no
watchlist change → the bot reads the list only at startup, so a restart would be pointless churn;
service already `active` since the Fri 07-17 11:35 UTC restart). 🔒 Locked: none (0 open positions).
**Wed 07-22 routine: PARK GOOG + TSLA** (after-close prints). **Thu 07-23 routine: PARK INTC.**

---
