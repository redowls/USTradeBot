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

## 2026-07-30 — Pre-market Research

**Earnings rotation day: MSFT re-enabled (beat cleared), AAPL + AMZN parked (report AH today); plus the
queued SE liquidity park.** Book is CLEAN & FLAT (broker-confirmed **0 positions**, equity **$8,851.85**,
`last_equity` == `equity` → no overnight marks) → **nothing locked**. Acted on the 07-29 research flags
(re-enable MSFT / park AAPL+AMZN Thu) and the standing SE "on notice" flag. Four changes; **20 → 18 enabled**;
service restarted clean (warmup 18/18).

### Market context
- **Rebound after Wednesday's rout.** Futures higher into the open: **S&P +0.18%** (US500 ~7328), Nasdaq up,
  led by **MSFT +8% AH** on its Azure-driven Q4 beat. This follows a **brutal Wed 07-29 selloff** (Dow −2.19%
  / S&P −1.52% / Nasdaq −1.74%, now >10% off ATH) triggered by the **Fed holding rates + a bond-market revolt**
  (30-yr yield ~5.24%, highest since 2007). Overnight US strikes on Iranian targets add a geopolitical tail.
- **⚠️ Macro-heavy morning:** **June Core PCE (Fed's preferred gauge) + Q2 advance GDP + weekly jobless claims
  all 8:30am ET today.** Then **AAPL fiscal-Q3 + AMZN Q2 both report AFTER today's close** (AAPL Street ~$1.88
  EPS / ~$108.8B rev; AMZN ~$1.82 EPS / ~$196B rev, ±7.2% implied) — binary overnight events → parked.
- **MSFT Q4 FY26 verified (WebSearch, CNBC/Investing/24-7WallSt):** EPS **$4.74 vs $4.33** est, rev **$90.01B
  vs $87.6B** (+18% YoY), Azure strength, **+8% extended-hours** — binary resolved favorably → re-enable.
- Weak premarket names **META −8.5%, QCOM −4.8%** are **not enabled** (QCOM already parked) — no watchlist bleed.
- Perplexity sonar confirmed AAPL's after-close timing but was thin on the rest → WebSearch supplied MSFT's
  print/reaction, AMZN's confirmed after-close date, futures direction, and the PCE/GDP release schedule.

### Carried from daily review (07-28 EOD, latest written) + 07-29 research flags
- **Book CLEAN & FLAT into Thu 07-30** — confirmed live (ACTIVE, equity $8,851.85, 0 positions). Nothing locked.
- **"Thu 07-30 AM → PARK AAPL + AMZN (report AH) + Core PCE Thu"** and **"re-enable MSFT Thu once the print +
  reaction clear"** (07-29 entry) → both honored today.
- **SE "flag for a park decision if it keeps signalling and losing" (07-29)** → SE kept signalling (5 trades)
  and kept losing (worst 10d P&L, 1W/5 −$53.42) → parked today (see below).

### Watchlist review
- **10-day per-symbol P&L is broadly red** (net −$169 over 38 trades) — the **known bot-wide negative-edge
  issue** worked in daily-review/improvement, not a symbol-quality break. Winners this window: TSM +$34, AAPL
  +$32, BABA +$29, NFLX +$17 (4W/5). Losers concentrated in the semi/megacap cohort (NVDA −$52, GOOG −$50,
  INTC −$32, MU −$29) = regime, kept.
- **SE (parked)** — the exception: **worst 10d P&L (1W/5, −$53.42, 20% win)**, lowest-liquidity ADR of the
  set (thin IEX feed → recurrent 0.0 volume sub-scores), and on explicit notice two runs. This is a
  structural liquidity/quality park, not a churn-on-P&L park; re-consider only on a durable liquidity/trend
  improvement.
- **17 other enabled kept** — all liquid large-caps/ETFs, no fresh negative catalyst, fit the ribbon.
- **No adds** — a macro-heavy (PCE/GDP) morning after a −2% bond-driven selloff, with a fragile rebound, is
  the wrong session to chase momentum; no conviction new name. 18/30, room to spare.

### Changes applied to dbo.watchlist
- **RE-ENABLE MSFT** (`enabled=1`, note "Q4 FY26 beat 07-29 AH, Azure-driven +8% AH; earnings binary resolved").
- **PARK AAPL** (`enabled=0`, "fiscal Q3 earnings AH today (binary), re-enable next open once cleared").
- **PARK AMZN** (`enabled=0`, "Q2 earnings AH today (±7.2% implied, binary), re-enable next open once cleared").
- **PARK SE** (`enabled=0`, "lowest-liquidity ADR of set, worst 10d P&L 1W/5 −$53.42, on-notice 2 runs").
- Everything else unchanged. **Re-enable AAPL + AMZN Fri 07-31 pre-market** once their prints + reactions clear.

### Final watchlist
**18 enabled:** ABNB, AMD, AVGO, BABA, C, GOOG, INTC, JPM, MSFT, MU, NFLX, NVDA, QQQ, SPY, TSLA, TSM, UNH, WMT.
Parked (9): AAPL, AMZN, BIRD, COST, ENPH, QCOM, SE, WPM, XOM. **Service restarted 11:34 UTC — active, warmup
18/18, MSFT present / AAPL·AMZN·SE absent, account ACTIVE equity $8,851.85, 0 positions, clean 18-symbol IEX
subscription, no errors.** 🔒 Locked: none (0 open positions).

---

## 2026-07-29 — Pre-market Research

**Earnings-park day: MSFT out ahead of an AH print + FOMC double-catalyst.** Book is CLEAN & FLAT
(broker-confirmed **0 positions**, equity **$8,848.98**, `last_equity` == `equity` → no overnight marks,
matches 07-28 EOD) → **nothing locked**. Acted on the 07-28 daily-review flag: **PARK MSFT** (reports
AH today + Fed decision today). One change; **21 → 20 enabled**; service restarted clean (warmup 20/20).

### Market context
- **Risk-on bounce after the chip rout.** Futures higher into the open: **S&P +0.7%, Nasdaq-100 +1.1%**
  (Perplexity sonar) — a recovery from Tue's semi-led selloff. No single-name negative catalyst, halt,
  downgrade, or M&A on any enabled symbol overnight.
- **⚠️ Double-catalyst DURING/AFTER market hours today:** **FOMC rate decision 2:00pm ET + Powell/Warsh
  presser 2:30pm ET**, then **MSFT fiscal-Q4 FY26 earnings AH** (call 5:30pm ET). MSFT is trading near its
  **52-week low** ($380s vs 52wk low $349.20), 3rd down session, into AI-capex fear — binary event, no
  intraday longs into it. Confirmed by WebSearch (TipRanks/StockTitan/WallStreetHorizon) + Perplexity.
- **Tomorrow's parks pre-staged:** **AAPL + AMZN report Thu 07-30 AH** → park them at Thu pre-market per
  standing precedent (both confirmed AH Thu; AAPL Street ~$1.88 EPS / ~$108.8B rev, China-AI approval tailwind).

### Carried from daily review (07-28 EOD)
- **Book CLEAN & FLAT into Wed 07-29** — confirmed live (ACTIVE, equity $8,848.98, 0 positions). Nothing locked.
- **"Wed 07-29 AM → PARK MSFT (reports AH) + Fed decision"** → honored today.
- **IMP-019 verified working:** the post-close 07-28 21:17 UTC restart put the bot back on the full
  `dbo.watchlist` (journal *"Watchlist (dbo.watchlist)"*, warmup **21/21**) — NOT the 3-symbol `NFLX,BIRD,WPM`
  env stub that caused 07-28's zero-trade day (transient DB login timeout). No stub recurrence this run.

### Watchlist review
- **20 kept** (post-MSFT-park): AAPL, ABNB, AMD, AMZN, AVGO, BABA, C, GOOG, INTC, JPM, MU, NFLX, NVDA, QQQ,
  SE, SPY, TSLA, TSM, UNH, WMT — all liquid large-caps/ETFs, no fresh negative catalyst, fit the ribbon.
- **14-day per-symbol P&L is broadly red** (SE 0/4 −$78, INTC −$71, NVDA −$52 the worst) but this is the
  **known bot-wide negative-edge issue** being worked in daily-review/improvement, **not a symbol-quality
  break** — every name is a liquid, trending-capable large cap. Not churning on P&L alone. **SE on watch**
  (0/4, lowest-liquidity ADR of the set) — flag for a park decision if it keeps signalling and losing.
- **No adds** — futures-up bounce, but no conviction new name and no reason to churn a sound 20-name list.

### Changes applied to dbo.watchlist
- **PARK MSFT** (`enabled=0`, note "parked 2026-07-29: Q4 FY26 earnings AH today + FOMC decision (double
  binary); re-enable post-print"). **Re-enable Thu 07-30 pre-market** once the print + reaction clear.
- Everything else unchanged.

### Final watchlist
**20 enabled:** AAPL, ABNB, AMD, AMZN, AVGO, BABA, C, GOOG, INTC, JPM, MU, NFLX, NVDA, QQQ, SE, SPY, TSLA,
TSM, UNH, WMT. Parked (7): BIRD, COST, ENPH, MSFT, QCOM, WPM, XOM. **Service restarted 11:32 UTC — active,
warmup 20/20, MSFT dropped, clean startup (no errors).**

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

## 2026-07-31 — Pre-market Research

### Market context
Risk-on tape: S&P 500 futures ~+0.9%, Nasdaq 100 ~+1.3% pre-market, led by **AMZN**'s blowout
print. Perplexity `sonar` briefing ran (AAPL premarket direction came back **conflicting** — +4.3%
vs −7.4% — so both earnings reactions were re-verified via WebSearch before acting). Two mega-cap
prints from Thu 07-30 AH are the day's whole story; no watchlist symbol reports **during** today's
session.

### Carried from daily review (07-30 "Notes for pre-market research")
- Book **CLEAN & FLAT** into 07-31 — broker-confirmed **0 open positions**, equity **$8,889.20** all
  cash. Nothing locked; nothing to protect. ✔ verified via /v2/account + /v2/positions.
- Standing directive: **re-enable AAPL + AMZN today** once their Thu-AH prints + reactions clear
  (both were parked pre-market 07-30 for the binary). Acted on — see below.
- Semis cohort (INTC/MU/AVGO/TSM/NVDA/AMD) is producing best *and* worst — crossover-quality
  dispersion, not symbol quality; keep. MSFT lost small on a mediocre cross = regime, keep. No
  symbol flagged for a park on 07-30 evidence.

### Watchlist review
Account **ACTIVE**, equity **$8,889.20**, BP $35,556, **0 open positions = nothing locked.** 18
enabled reviewed; both re-enable candidates cleared their binary:
- **AMZN → RE-ENABLE.** Blowout Q2: net sales >$200B (first ever), **AWS reaccelerated to +37%**
  (5yr high, beat 31% est), stock **+8–10% AH**. Q3 revenue guide slightly soft but tape looked
  through it to AWS. Bullish gap, mega-liquid megacap, clean momentum — ideal ribbon fuel. Verified
  tradable=true/active on /v2/assets.
- **AAPL → RE-ENABLE, on notice.** Fiscal Q3 beat top+bottom (rev $109.4B, EPS $2.02, iPhone +22%)
  but **−6.6% AH to ~$311** on a Services miss ($30.7B vs $31.2B), soft "supply-constrained" guide,
  and China weakness ($18.8B). Binary is **resolved** (no more overnight surprise); the long-only 5m
  gate simply won't open longs if the gap-down downtrend persists — same self-protecting precedent as
  the NFLX/TSM post-earnings re-enables. Verified tradable=true/active.
- **All 18 enabled kept.** Every laggard in the 14d P&L (NVDA/GOOG/INTC/TSLA red) is regime/chop per
  the dailies, not a liquidity or signal-quality park. NFLX stays on notice (post-earnings downtrend,
  liquid, gate self-protects). No new park today.
- **Parked stay parked:** BIRD (micro-cap), COST (June-sales-miss downtrend 0/4), ENPH (10.9% ATR
  whipsaw), QCOM (−14% vs 20/50MA thin $vol), SE (lowest-liquidity ADR, worst 14d −$53.42 / 1W5),
  WPM (dead-vol downtrend), XOM (broken oil downtrend). No fresh bullish catalyst on any.

### Changes applied to dbo.watchlist
- **Re-enabled AAPL and AMZN** (`enabled 0→1`, dated notes set). Both were pre-existing parked rows
  (re-enabled, not re-inserted), both verified tradable & active on Alpaca first.
- No parks, no new inserts. No churn on the kept list.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SPY TSLA
TSM UNH WMT. Parked (7): BIRD COST ENPH QCOM SE WPM XOM. Service **RESTARTED** 11:34 UTC (watchlist
changed) — `active`, warmup primed **20/20** symbols, subscribed to all 20 on iex, no positions,
clean startup. 🔒 Locked: none (0 open positions).

---

## 2026-08-04 — Pre-market Research

**One change: AMD parked for tonight's after-close Q2 print.** Book is CLEAN & FLAT (broker-confirmed
**0 positions**, equity **$8,948.73**, `last_equity` == `equity` → nothing carried, nothing marked) →
**nothing locked**. This is the first run since **07-31** — the 08-03 routine died `rc=1` (model blip),
so there is no 08-03 research entry and Monday traded Friday's list unchanged. Started from the 07-31
entry + the 08-03 daily review, as that review instructed.

### Market context
Risk-on, tech-led, and **thin at the top**. Nasdaq-100 futures **+0.7%**, Dow futures **+201 (+0.5%)**,
S&P 500 futures **+0.2%** — a narrower, more selective bid than Monday's record Dow close. Drivers are
carry-over, not fresh: Trump halting further strikes on Iran took WTI down >5% Monday to $80.34 (crude
is +2% back this morning on supply worries), and the momentum unwind in chips/AI paused. **Semis are
bouncing** — MU **+4% pre**, MRVL +7% — after a brutal stretch (MU had its worst month in 11 years,
−8.2% vs its 20-day / −14.2% vs its 50-day even after yesterday's gain). Session movers are earnings
names outside our book: PLTR **+16%** on a blowout Q2, CAT +6%. Macro in-session: **June factory orders
+ international trade data**; 10y 4.69%, 2y 4.25%. **Perplexity `sonar` ran but came back near-empty**
(no futures data, "no catalyst found" for 19 of 20 names) — fell back to WebSearch for the whole
briefing, and every trade-critical claim below was verified there independently.

### Carried from daily review (08-03 "Notes for pre-market research")
- **Book CLEAN & FLAT into 08-04** — ✔ verified live: `/v2/account` ACTIVE, equity **$8,948.73** all
  cash, `/v2/positions` **0**, `/v2/orders?status=open` **0**. Nothing locked, nothing to protect.
- **⚠️ "If the 11:30 UTC run fails again that is a pattern"** — it did **not** fail: this run executed
  normally. Treating 08-03 as the one-off it was claimed to be; no escalation needed.
- **AMD flagged as the day's best trade and cleanest signal** (trend 0.96 / rsi 1.00 / vol 1.00) →
  ordinarily a clear keep. **Overridden today by an earnings binary** — see below.
- **AMZN on watch** (entered on crossover 0.2552, the closest any trade has come to IMP-020's floor, and
  was 08-03's only loser). Keep — one trade is not a park, and it is the strongest chart on the list.
- **MU won on a near-zero volume sub-score (0.07) = luck, not quality.** Keep, watch. Note MU is
  bouncing +4% pre today, so it will likely signal again.
- **C and SPY are burning gate cycles without producing a tradeable cross** — C rejected 4× on crossover
  (0.06–0.10), SPY 2× (0.03/0.01); last actual trade **C 07-10**, **SPY 06-26**. The review set the bar
  explicitly: *"if that persists another week."* Today is **one session** into that window → **no park
  today**, flag carried. Data supporting the mechanism, not the park: SPY's ATR is **1.17%** and QQQ's
  **2.15%**, the two lowest on the board — index ETFs structurally produce fewer sharp 1-min crosses.
  That is the diversifier trade-off, not a broken symbol.
- **TSM / GOOG / AVGO repeatedly rejected just under the 60 confidence floor** (57.6–59.3). Noted as a
  scoring question for the post-close routine — it is not a watchlist action and I did not treat it as one.

### Watchlist review
Account **ACTIVE**, equity **$8,948.73**, BP $35,794.92, **0 open positions = nothing locked.** Service
`active` since the 08-03 21:59 UTC IMP-021 restart, NRestarts=0. 20 enabled reviewed against overnight
news + 60-day daily bars (close vs 20/50-day MA, ATR%, 20-day avg $ volume):
- **⚠️ AMD → PARK (the one change).** AMD reports **fiscal Q2 2026 today, Tuesday 2026-08-04, AFTER the
  market close** (call 5:00 pm ET). This is the routine's standard binary-event park and it is
  **independently verified** — AMD's own 07-08 IR announcement (via StockTitan), the Seeking Alpha and
  Schwab week-ahead calendars, TIKR, and this morning's Benzinga pre-market piece all name the same date
  and time; Perplexity did **not** surface it, which is precisely why the fallback search matters. Street
  looks for ~$11.2–11.3B revenue (+46–47% y/y) and ~$1.61–1.67 EPS. Same precedent as GOOG+TSLA (07-22),
  MSFT (07-29), AAPL+AMZN (07-30): a long opened intraday would be held into an unhedgeable overnight
  gap — the EOD flatten is designed for it, but the trail-managed winner that runs into the close is
  exactly the trade that gets caught. **Not locked** (0 positions), so the park is safe. **Re-enable
  Wed 08-05** once the print and the reaction clear.
- **Core megacap engine kept:** MSFT (**+21.3% vs 20MA**, strongest trend on the board), AMZN (+15.5%,
  post-AWS-blowout leader), GOOG (+7.2%, +14.1% on the week), BABA (+10.8%, last week's best P&L +$52.10
  over 10 sessions), NVDA (+1.4%), JPM (+2.2% / +7.3% vs 50MA). All liquid, all trending, ideal ribbon fuel.
- **Post-earnings downtrends kept, on notice:** AAPL (−6.3% vs 20MA, −9.9% on the week after the Services
  miss, but **+$31.89 over 10 sessions** and $17.8B/day), NFLX (−4.5% vs 50MA), TSLA (**−10.3% vs 20MA,
  −17.2% vs 50MA**, 0/2 and −$32.42 over 10 sessions), TSM (−1.6%), UNH, WMT. Every one is mega-liquid and
  the long-only 5-min gate simply will not open longs while the trend is down — the same self-protecting
  logic that has justified holding these names since the NFLX/TSM re-enables. Downtrend alone is not a park.
- **Semis kept (regime, not symbol quality):** INTC (−18.9% vs 50MA, ATR 8.75%) and MU (−14.2% vs 50MA,
  **ATR 10.73%**) look ugly on the 50-day but were **last week's two best earners** (+$33.90 / +$40.29) and
  both are bouncing this morning. AVGO flat-ish (+1.7% vs 20MA). The dailies have been consistent that the
  semi cohort's dispersion is crossover quality, not liquidity or symbol quality.
- **Dead-signal watch (no action):** C (−0.2% vs 20MA, ATR 2.64%) and SPY (ATR **1.17%**) — see above,
  one session into the review's stated one-week window. ABNB has not traded since 07-15 either and is the
  thinnest name enabled ($499M/day, vs $1.4B for the next-thinnest BABA) — **and it reports Thu 08-06 after
  close**, so it is on the calendar for a park in Thursday's run regardless.
- **Parked stay parked:** BIRD (micro-cap), COST (June-sales-miss downtrend, 0/4), ENPH (10.9% ATR whipsaw),
  QCOM (thin $vol, lone chip laggard), SE (lowest-liquidity ADR, worst 10-day −$53.42 on 1W/5), WPM
  (dead-vol downtrend), XOM (oil gave back >5% Monday on the Iran de-escalation — the *opposite* of a
  bullish catalyst). No fresh reason to re-enable any.
- **Adds considered and declined.** PLTR (+16% on its Monday-AH blowout, $4.65B/day) is the obvious
  momentum candidate and its binary is resolved — but a **+16% gap day is the most fade-prone session a
  name has**, and this log's standing rule is not to chase a gap on the day it happens. MRVL (+7%, but
  −19.1% vs its 50MA) and CAT (+6% on an earnings gap, −9.7% vs 50MA) are both bounces inside downtrends.
  The stronger structural reason: the book is **capital-constrained** ($8.9k equity), so on a 3–8 trade
  day a 20th name mostly *displaces* a trade rather than adding one — IMP-017 made exactly this point.
  Nothing gets added to fill the slot AMD vacated.

### Changes applied to dbo.watchlist
- **AMD → `enabled = 0`** (row kept, note set: *"parked 2026-08-04: Q2 earnings AFTER CLOSE today (binary
  event); re-enable 08-05 once print clears"*). Parameterized UPDATE, 1 row affected, committed.
- **No adds, no re-enables, no deletes.** One change is the whole diff.

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SPY TSLA TSM UNH
WMT. Parked (8): AMD BIRD COST ENPH QCOM SE WPM XOM. Service **RESTARTED** 11:35:29 UTC (watchlist
changed) — `active`, NRestarts=0, warmup primed **19/19** symbols from history, subscribed to all 19 on
the iex feed, account ACTIVE $8,948.73, **no open positions**, and the startup banner confirms IMP-021 is
live (*"trailing stop 1.25% (active, IMP-018), tightening to 1.00% once +1.00% in profit (IMP-021)"*).
Clean startup, zero errors. 🔒 Locked: none (0 open positions).
**Wed 08-05 routine: RE-ENABLE AMD** after tonight's print. **Thu 08-06 routine: PARK ABNB** (Q2 after
Thursday's close). Carry the **C / SPY dead-signal** flag — the review's one-week window runs to ~08-10.

---

## 2026-08-06 — Pre-market Research

**Two changes, both queued by prior runs: AMD re-enabled (overdue by a session), ABNB parked for tonight's
print.** Book is CLEAN & FLAT (broker-confirmed **0 positions**, **0 open orders**, equity **$9,075.74**,
`last_equity` == `equity` → nothing carried, nothing marked) → **nothing locked**. Both changes were
explicitly ordered by the 08-05 daily review; neither is a discretionary call. **19 → 19 enabled** (one in,
one out); service restarted clean (warmup 19/19). **Today is IMP-022's first live session.**

### Market context
**Mixed and split by index — Dow/S&P bid, Nasdaq offered.** Pre-market: **SPY +0.18% ($771.20)** but
**QQQ −0.31% ($715.09)**; Wednesday closed mixed. The driver is macro, not single-name: an **Oman-brokered
Strait of Hormuz deal** is reportedly in its final stages (Reuters), taking **Brent to ~$79.91** and putting
a bid under cyclicals while tech lags. Rates **10y 4.62% / 2y 4.20%**, CME FedWatch **54.9%** for a September
Fed move. Monday's rally is the recent backdrop (Nasdaq +2.59%, Dow +907 to records, PLTR +29%).
- **⚠️ The semis backdrop is a bear market, not a dip.** The global AI-chip rout has taken ~**$1.3T** off the
  20 largest chip names since a recent Friday close (CNBC/FactSet), with **Micron, Samsung, SK Hynix all
  >20% off their June highs**; drivers are circular-financing fears (NVDA/OpenAI), CXMT's Shanghai debut
  pressuring memory pricing, and AI-capex ROI scepticism. **Our chip cohort is bouncing hard inside that
  downtrend** — 5-day: INTC **+23.4%**, MU **+20.9%**, NVDA **+15.4%**, AVGO **+13.0%**, AMD **+12.2%** —
  but MU is still −8.1% vs its 50MA and INTC −9.4%. Kept (regime, not symbol quality); IMP-022 is now the
  mechanism that decides whether to bet on that bounce, which is exactly what it was built for.
- **Earnings: ABNB is the only watchlist name reporting today** (after close). Verified against the full
  Thursday calendar — a heavy day (~577 reports) but no other enabled symbol is on it.
- **Perplexity `sonar` ran and was thin again** (returned "no catalyst surfaced" for 19 of 20 names and no
  futures tick) — but it **did independently flag ABNB's after-the-bell report**, which is the one
  trade-critical fact it needed to catch. WebSearch supplied the futures split, the Hormuz driver, the
  semis context and the AMD post-mortem; every claim acted on below was verified there.

### Carried from daily review (08-05 "Notes for pre-market research")
- **🚨 RE-ENABLE AMD** — parked 08-04 for its after-close print, and the 08-05 routine that was supposed to
  re-enable it **never ran**, so it sat out a full session for a binary that had already resolved. **Done
  today** (see below). ✔
- **🚨 PARK ABNB** — flagged on 08-04 and restated 08-05 as "still outstanding". **Done today.** ✔
- **⚠️ QQQ is now load-bearing infrastructure (IMP-022), not just a tradeable symbol.** Verified
  `enabled=1` before and after this run, and the check is asserted in the apply script. The gate **fails
  open** if QQQ is parked (bot trades as before, one WARNING) — safe but silently unfiltered. The standing
  C/SPY dead-signal review **must not park QQQ**; honored.
- **Book CLEAN & FLAT into 08-06** — ✔ verified live: `/v2/account` ACTIVE, equity **$9,075.74** all cash,
  `/v2/positions` **0**, `/v2/orders?status=open` **0**. (The review quoted $9,075.88; the $0.14 delta is a
  routine mark, not a position.) Nothing locked.
- **MU explicitly NOT a park candidate** despite being 08-05's whole loss (2 trades, −$28.73) — still the
  book's **2nd-best 60-day earner (+$177.84 / 21 tr)**. Honored, kept.
- **INTC best name in the book** (+$191.26 / 20 tr) and 08-05's only winner. Kept.
- **NVDA and AVGO flagged as the emerging dead-signal names** (NVDA rejected 3× on crossover 08-05, AVGO 4×)
  — carried as a watch item, **not acted on**: both are mega-liquid and repeatedly *reach* candidacy, which
  is a scoring question for the post-close routine, not a watchlist park.
- **C / SPY dead-signal window runs to ~08-10** — today is inside it, **no park**. Supporting data below.
- **🚨 Routine-failure escalation** (08-03 rc=1, 08-05 pre-market never ran, 08-04 post-close never ran) —
  **this run executed normally**, but the scaffold lives in `/root/claude-routines`, outside this repo, and
  the daily review is right that three misses in three sessions needs an operator look. Flagged, not fixable
  from here.

### Watchlist review
Account **ACTIVE**, equity **$9,075.74**, BP $36,302.96, **0 open positions = nothing locked.** Service was
`active` since the 08-05 21:29:35 UTC IMP-022 restart, NRestarts=0. 19 enabled + AMD reviewed against
overnight news and 60-day daily bars (close vs 20/50-day MA, ATR%, 20-day avg $ volume):
- **✅ AMD → RE-ENABLE (change 1).** Q2 reported **08-04 after close**: revenue **$11.54B** (+50% y/y) vs
  ~$11.28B est, adj EPS **$1.66** vs $1.62, Data Center **doubled to $6.7B**, and Q3 guided to **~$13B** vs
  ~$12.54B consensus — **a beat on revenue, EPS *and* guidance**. It sold off anyway, **−7% to −9%**, on
  flat 56% gross-margin guidance, FCF −39% sequentially, and a share price already +140% YTD. The binary is
  **fully resolved and fully traded**: a complete session (08-05) has printed on it, closing $482.05. That
  makes this a missed *recovery*, not a missed opportunity — and re-enabling a name into a post-earnings
  pullback is the same precedent as the AAPL, NFLX, TSM and GOOG re-enables: the long-only 5-min gate will
  not open a long while the trend is down, and IMP-022 now adds a second veto on top. Mega-liquid
  (**$15.1B/day**), verified `tradable=true` / `status=active`. **Kept on notice** — ATR **8.61%** is the
  third-highest on the board and it is −5.5% vs its 20MA / −6.3% vs 50MA.
- **⚠️ ABNB → PARK (change 2).** Reports **Q2 2026 today, 2026-08-06, after market close**, call 5:00pm ET.
  **Independently verified**: Airbnb's own IR release (announced 07-09), StockTitan, MarketBeat and the
  Yahoo/Kiplinger calendars all name the same date and time; Perplexity flagged it too. Street looks for
  **~$1.26 EPS / ~$3.58B revenue**. Standard binary-event park — same precedent as AMD (08-04), MSFT (07-29),
  AAPL+AMZN (07-30), GOOG+TSLA (07-22): a long opened intraday rides into an unhedgeable overnight gap, and
  the trail-managed winner that runs into the close is exactly the trade the EOD flatten cannot save.
  **Not locked** (0 positions), so the park is safe. Two independent reasons reinforce it: ABNB is the
  **thinnest name enabled** ($519M/day, vs $1.3B for the next-thinnest BABA) and has **not traded since
  07-15**. **Re-enable Fri 08-07** once the print and reaction clear.
- **Core megacap engine kept, and it is strong:** MSFT (**+18.2% vs 20MA, +20.8% vs 50MA, +24.8% on the
  week** — the best chart on the board), AMZN (+9.6% / +10.2%, +20.3% weekly), BABA (+9.5% / +12.9%),
  NVDA (+6.8% / +6.5%), AVGO (+7.4% / +5.9%), JPM (+3.4% / +8.6%, ATR 1.97%), GOOG (+3.5% / +1.2%, though
  **−4.1% yesterday**). All liquid, all trending — ideal ribbon fuel.
- **Post-earnings / downtrend names kept, on notice:** TSLA is the weakest chart enabled (**−8.6% vs 20MA,
  −16.5% vs 50MA**) and AAPL (−3.9% vs 20MA, −8.0% on the week) is still working off the Services miss;
  UNH (−2.3%), WMT (+0.2%), NFLX (+3.1% / −2.6%), TSM (+0.7% / −2.8%) are middling. Every one is mega-liquid
  and **downtrend alone is not a park** — the long-only gate self-protects. Unchanged position from prior runs.
- **Dead-signal watch, no action (window open to ~08-10):** **SPY has not traded since 2026-06-26 — 41 days**
  — and **C not since 07-10 (27 days)**. The mechanism is structural, not broken: SPY's daily ATR is
  **1.26%**, the lowest on the board, and QQQ's 2.18% is second-lowest — index ETFs simply produce fewer
  sharp 1-min crosses. That is the diversifier trade-off. **Deliberately not parked today**: the review set a
  one-week window that has not expired, and **QQQ is now excluded from that review entirely** because
  IMP-022 depends on it. SPY remains the only one of the two genuinely free to park on 08-10.
- **Parked stay parked:** BIRD (micro-cap), COST (June-sales-miss downtrend, 0/4), ENPH (10.9% ATR whipsaw),
  QCOM (thin $vol, lone chip laggard), SE (lowest-liquidity ADR, worst 10-day −$53.42 on 1W/5), WPM (dead-vol
  downtrend), XOM (**and the Hormuz deal takes Brent to ~$79.91 — crude easing is the opposite of a bullish
  catalyst**, so it stays parked for the same reason as 08-04). No fresh reason to re-enable any.
- **Adds considered and declined — deliberately, for a reason specific to today.** **IMP-022 shipped last
  night and today is its first live session.** Its whole purpose is a measurable ~40% cut in trade count at
  higher per-trade edge; adding a new symbol into the same session would confound that measurement from the
  first data point, and the weekly review's standing focus is explicitly *"protect the measurement."* The
  structural argument from 08-04 also still holds: the book is **capital-constrained** ($9.1k equity), so on
  a 3–8 trade day an extra name mostly *displaces* a trade rather than adding one (IMP-017). Nothing was
  added to fill the slot ABNB vacated — AMD's return already restores the count.

### Changes applied to dbo.watchlist
- **AMD → `enabled = 1`** (pre-existing parked row **re-enabled, not re-inserted**; note set: *"re-enabled
  2026-08-06: Q2 beat (08-04 AH), -8% reaction traded 08-05; binary resolved, $15B/d liquid; on notice"*).
- **ABNB → `enabled = 0`** (row **kept**, note set: *"parked 2026-08-06: Q2 earnings AFTER CLOSE today
  (binary); thinnest $519M/d; re-enable 08-07 once print clears"*).
- Both parameterized UPDATEs, 1 row affected each, committed. **No inserts, no deletes.** Post-apply
  assertions passed: **19 enabled ≤ 30** and **QQQ present**.
- *(Ops note for future runs: `dbo.watchlist.note` is **VARCHAR(128)** — the first attempt failed with a
  truncation error and the notes were shortened. Nothing was written on that attempt.)*

### Final watchlist
**19 enabled** (≤30 ✓): AAPL AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SPY TSLA TSM UNH WMT.
Parked (8): ABNB BIRD COST ENPH QCOM SE WPM XOM. Service **RESTARTED** 11:36:32 UTC (watchlist changed) —
`active`, NRestarts=0, warmup primed **19/19** symbols from history, subscribed to all 19 on the iex feed,
account ACTIVE $9,075.74, **no open positions**, zero errors. Startup banner confirms both live changes:
*"Market gate: QQQ 5m ribbon must be bullish to open a long (IMP-022)"* and *"trailing stop 1.25% (active,
IMP-018), tightening to 1.00% once +1.00% in profit (IMP-021)"*. 🔒 Locked: none (0 open positions).
**Fri 08-07 routine: RE-ENABLE ABNB** after tonight's print. Carry the **C / SPY dead-signal** flag to
**~08-10** (SPY 41 days without a trade, C 27 — **and QQQ is exempt, IMP-022 needs it**). **Today is
IMP-022's first live session** — the post-close review should count `market gate closed` skips and price
them; a low trade count today is the expected texture, not a malfunction.

---

## 2026-08-07 — Pre-market Research

**One change, and it is exactly the one the 08-06 review ordered: ABNB re-enabled after a beat-and-raise
print.** Book is CLEAN & FLAT (broker-confirmed **0 positions**, **0 open orders**, equity **$9,075.74**,
`last_equity` == `equity` → nothing carried, nothing marked) → **nothing locked**. **19 → 20 enabled**;
service restarted clean (warmup 20/20). **No adds, deliberately — day 2 of IMP-022's 5-session
observation window.**

### Market context
**Constructive and tech-led into the jobs print.** Pre-market futures **mixed-to-higher with Nasdaq
leading**: Nasdaq 100 **+0.5%**, S&P 500 **+0.2%**, Dow **+0.1%** (+41 pts). Thursday closed soft and
split (Dow **−0.85%**, S&P **−0.18%**, Nasdaq Composite **−0.06%**), but the week is shaping up as the
**second straight weekly gain**, with the Nasdaq on track for its **best week since May** on a
semiconductor bounce (iShares Semiconductor ETF **+5% on the week**). Rates **10y 4.67% / 2y 4.24%**;
crude lower again (**WTI $76.85 −0.6%, Brent $81.90 −0.7%**).
- **🚨 The July jobs report at 08:30 ET is the day's dominant event — but it lands PRE-OPEN, not during
  market hours.** Consensus is soft and dispersed: **83k** (CNBC), **80k** (Bloomberg survey), **97.5k**
  (FactSet), unemployment held at **4.2%**, against June's **57k**. CME FedWatch prices **54.7%** for a
  September Fed move. This matters to the bot only through the *shape* of the open, and the **10:00 ET
  opening-range blackout (IMP-017) already keeps it out of the first 30 minutes of the reaction** — which
  is precisely the structure IMP-017 was built for. No watchlist action warranted.
- **Earnings today are light and clean: no enabled watchlist symbol reports.** ~**74** reports scheduled
  (vs **323** on Thursday); the notable names are **Vistra, Take-Two, Under Armour, Wendy's, Oklo** —
  none of them ours. Verified against the Friday calendar, not assumed.
- **Pre-market movers:** **ABNB +7%** (see below), **NET +16%** (guidance), **DKNG −3%** (revenue miss).
- **⚠️ Perplexity `sonar` was thin for the third consecutive run AND actively misleading on one name.**
  It returned "no catalyst" for 19 of 20 tickers and gave **no futures tick at all**. It did correctly
  flag the **08:30 ET NFP/jobless-claims releases**. But both of its **AAPL** items — "$100B U.S.
  investment / semiconductor tariff relief" and "federal court decision risk on the Google default-search
  agreement" — are **stale 2025 stories recycled as overnight news**. Verified against WebSearch: Judge
  Mehta's remedy ruling was **September 2025**, final judgment **2025-12-05**, and the case is now on
  **appeal at the D.C. Circuit** with **no ruling due today**. **There is no AAPL binary today and AAPL
  was not parked.** Recording this explicitly: had the "court decision risk" line been trusted, a healthy
  mega-liquid name would have been parked on a year-old headline. **Treat sonar as a lead generator only;
  WebSearch carried this run entirely.**

### Carried from daily review (08-06 "Notes for pre-market research")
- **🚨 RE-ENABLE ABNB** — the review's one explicit order. **Done today** (see below). ✔
- **✅ AMD's re-enable already validated** — it produced a fully qualifying entry (conf **68.1**) on its
  first session back, plus 2 confidence and 1 crossover rejects. **Kept.** ✔
- **⚠️ QQQ is load-bearing twice over** (IMP-022 market gate — parking it makes the gate fail *open* and
  silently vanish — **and** IMP-023's replay universe). Verified `enabled=1` before and after, and the
  check is asserted in the apply script. ✔
- **"No park candidates from today — do not read the zero-trade day as dead names."** Honored: **zero
  parks this run.** ✔
- **"Expect more zero-trade days."** Noted — but today's setup is materially different from 08-06, when
  the QQQ gate was open for **0 of 85** 5-min bars. QQQ now sits **+2.0% vs its 20MA** (and flat vs the
  50MA) with Nasdaq futures **+0.5%**, so the gate has a realistic chance of opening. Not a prediction,
  just the distinction the post-close review will need.
- **Book CLEAN & FLAT into 08-07** — ✔ verified live: `/v2/account` ACTIVE, equity **$9,075.74** all cash,
  `/v2/positions` **0**, `/v2/orders?status=open` **0**. Nothing locked.
- **C / SPY dead-signal window runs to ~08-10** — today is inside it, **no park**. Supporting data below.

### Watchlist review
Account **ACTIVE**, equity **$9,075.74**, BP $36,302.96, **0 open positions = nothing locked.** Service was
`active` since 08-06 21:19:26 UTC, NRestarts=0. 19 enabled + ABNB reviewed against overnight news and 60-day
daily bars (close vs 20/50-day MA, 5-day change, ATR%, 20-day avg $ volume on the IEX tape):
- **✅ ABNB → RE-ENABLE (the one change).** Q2 reported **08-06 after close** and it is a **beat *and* a
  raise**: EPS **$1.37** vs $1.25 est, revenue **$3.61B** vs $3.58B est (**+17% y/y**), net income **$816M**
  (from $642M), FCF **+30% to $1.25B**, GBV **+16% to $27.2B**, 148M nights booked, $1.1B repurchased.
  Q3 revenue guided **$4.69–4.77B** vs $4.61B consensus and the FY adj-EBITDA margin outlook **raised to
  ≥35.5%** from 35%. Stock **+7% to +10% after hours (~$165)** on ~**1.7× average volume**; first-time
  booker growth **+11%**, the best in four years. **This is the cleanest re-enable of the whole earnings
  cycle** — every prior one (AMD, AAPL, NFLX, TSM, GOOG) was a re-enable into a post-print *sell-off*;
  this one resolves the binary *favourably* and into expanding volume. Verified on `/v2/assets`:
  **`tradable=true`, `status=active`**, NASDAQ. Row **re-enabled, not re-inserted**. **Kept on notice for
  exactly one reason:** it remains the **thinnest name on the board** (**$23M/day** of IEX-tape dollar
  volume vs **$46M** for the next-thinnest, BABA) and it has **not produced a trade since 07-15**
  (all-time **+$0.78 / 10 tr**). Today's post-earnings volume expansion is the best chance it will get to
  justify its slot.
- **The board is the healthiest it has looked in weeks.** Above the 20MA: **MSFT +19.6%** (and **+23.4%**
  vs 50MA — still the best chart enabled), AMZN **+8.9%**, AVGO **+7.7%**, BABA **+7.3%**, NVDA **+6.1%**,
  ABNB **+2.8%**, SPY **+2.6%**, INTC **+2.6%**, GOOG **+2.5%**, NFLX **+2.5%**, JPM **+2.3%**,
  QQQ **+2.0%**, TSM **+2.0%**, C **+0.3%**. Below: WMT −0.0%, MU −1.3%, AAPL −3.4%, AMD −3.5%,
  UNH −4.1%, **TSLA −8.0%** (−16.5% vs 50MA — still the weakest chart enabled). 5-day momentum confirms
  the semis bounce is broad: AMZN **+15.5%**, NVDA **+12.2%**, MSFT **+10.7%**, INTC **+9.6%**,
  BABA **+9.0%**, AVGO **+8.4%**. Ideal ribbon fuel; nothing here is a park candidate on trend.
- **⚠️ Volatility outliers, kept and noted:** **MU ATR 9.48%**, **AMD 8.25%**, **INTC 7.68%** — the three
  highest on the board and well above where a 1-min ribbon behaves best. All three are mega-liquid, and
  INTC/MU are the book's **two best all-time earners (+$191.26 and +$177.84)**. This is a *sizing* question
  for the post-close routine, **not** a watchlist park.
- **The two worst symbols in the book were reviewed for parking and deliberately KEPT.** **AMZN**
  (all-time **−$108.51 / 14 tr**, and **−$36.18 / 0W-2** over the last 14 days) and **AVGO** (all-time
  **−$109.77 / 13 tr**). Neither is parked, for a decisive reason: **the bulk of those losses predate
  IMP-018 (working trail), IMP-020 (crossover floor), IMP-021 and IMP-022.** Parking a name on a P&L
  record produced by an exit structure that has since been *replaced* is churn against stale evidence.
  Both are mega-liquid and both are trending hard right now, and **AVGO has in fact printed +$41.34
  (2W/3) over the last 14 days**. Revisit only if they keep losing *under the current rules*.
- **Last-14-day P&L is broadly GREEN — 40 closed trades, +$193.82.** Winners: **INTC +$99.12 (4W/4)**,
  AVGO +$41.34, **NFLX +$36.97 (3W/3)**, GOOG +$31.94, AAPL +$31.89, MU +$27.93, BABA +$18.74,
  NVDA +$16.72, WMT +$5.88, TSM +$3.28. Losers: AMZN −$36.18, SE −$26.80 (**already parked**),
  MSFT −$25.11 (1W/4), JPM −$23.25 (0/1), TSLA −$8.07, AMD −$0.58. **No enabled symbol has a park-worthy
  record under the current rules.**
- **MSFT explicitly NOT a park candidate** despite 1W/4 for −$25.11: it is simultaneously the **best chart
  on the board** and the **most productive signal generator** (08-06: 3 crossover rejects, 3 confidence
  rejects, and the day's single best signal at **conf 70.2**). Its problem is *conversion*, not candidacy —
  a scoring question for the post-close routine.
- **Dead-signal watch, no action (window open to ~08-10):** **SPY has not traded since 2026-06-26 — 42
  days** — and **C not since 07-10 — 28 days**. The mechanism is structural, not broken: SPY's daily ATR is
  **1.20%**, the lowest on the board, so an index ETF simply produces fewer sharp 1-min crosses. That is
  the diversifier trade-off. **QQQ (ATR 2.09%) is excluded from this review entirely** because IMP-022 and
  IMP-023 both depend on it. Of the two remaining, **C is now the stronger park candidate** — 28 days
  silent *and* all-time **−$39.84 on 1W/5** — whereas SPY is merely quiet (−$11.24 / 4 tr).
- **Parked stay parked:** BIRD (micro-cap), COST (June-sales-miss downtrend, 0/4), ENPH (10.9% ATR
  whipsaw), QCOM (thin $vol, lone chip laggard), SE (lowest-liquidity ADR, worst 10-day −$53.42), WPM
  (dead-vol downtrend), XOM (**crude fell again today — WTI $76.85 −0.6%, Brent $81.90 −0.7% — so the
  park holds for the third consecutive run**). No fresh reason to re-enable any. **Forward note: SE
  reports Q2 on Tue 08-11** — irrelevant while parked, but it must not be re-enabled on 08-10 or 08-11
  without accounting for that print.
- **Adds considered and DECLINED — same reason as 08-06, with one more session to run.** IMP-022 is on
  **day 2 of a 5-session observation window (to ~08-12)**, and the entire measurement is the trade-count
  and per-trade-edge delta it produces; adding a symbol changes the candidate pool *underneath* that
  measurement, and the weekly's standing focus is explicitly *"protect the measurement."* The structural
  argument also still holds: at **$9.1k equity** the book is capital-constrained, so on a 3–8 trade day an
  extra name mostly **displaces** a trade rather than adding one (IMP-017). ABNB's return already takes the
  board back to 20. **Earliest sensible add: after 08-12.**

### Changes applied to dbo.watchlist
- **ABNB → `enabled = 1`** (pre-existing parked row **re-enabled, not re-inserted**; note set: *"re-enabled
  2026-08-07: Q2 beat+raised FY guide (08-06 AH), +7% pre-mkt; binary resolved; thinnest $vol, on notice"*
  — 113 chars, checked against the **VARCHAR(128)** limit before the write).
- One parameterized UPDATE, **1 row affected**, committed. **No inserts, no deletes, no parks.** Post-apply
  assertions passed: **20 enabled ≤ 30** and **QQQ `enabled = 1`**.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA C GOOG INTC JPM MSFT MU NFLX NVDA QQQ SPY TSLA TSM
UNH WMT. Parked (7): BIRD COST ENPH QCOM SE WPM XOM. Service **RESTARTED** 11:35:31 UTC (watchlist
changed) — `active`, NRestarts=0, warmup primed **20/20** symbols from history, subscribed to all 20 on the
iex feed, account ACTIVE $9,075.74, **no open positions**, zero errors. Startup banner confirms the live
config: *"Market gate: QQQ 5m ribbon must be bullish to open a long (IMP-022)"*, *"Entry window: 10:00-16:00
ET (opening-range blackout on, IMP-017…)"* and *"trailing stop 1.25% (active, IMP-018), tightening to 1.00%
once +1.00% in profit (IMP-021)"*. 🔒 Locked: none (0 open positions).
**Mon 08-10 routine: the C / SPY dead-signal window expires** — **C is the stronger park candidate** (28
days silent, −$39.84 all-time) and **QQQ remains exempt and must stay enabled**. **No adds until IMP-022
clears ~08-12.** Post-close review should again count `market gate closed` skips and price them — today is
**session 2 of 5** for IMP-022, and unlike 08-06 the gate started the day with a plausible path to opening.

---

## 2026-08-10 — Pre-market Research

**One change, and it is the one both prior entries queued for today: C parked as the dead-signal window
expires.** Book is CLEAN & FLAT (broker-confirmed **0 positions**, **0 open orders**, equity **$9,075.74**,
`last_equity` == `equity` → nothing carried, nothing marked) → **nothing locked**. **20 → 19 enabled**;
service restarted clean (warmup 19/19). **No adds — IMP-022's observation window runs to ~08-12.**

### Market context
**Modestly higher and tech-led, into a CPI week.** Futures: **S&P 500 +0.13%**, **Nasdaq 100 +0.25%**,
Dow −0.02%, Russell 2000 −0.02%; **QQQ ~+0.42%** pre-market, with tech and energy bid and real estate /
consumer staples lagging. This follows **Friday's record close — S&P +0.6% to 7,758 (all-time high),
Nasdaq +1.3%, Dow +152** — driven by a *weak* labour print (**nonfarm payrolls unexpectedly FELL 23k**).
Rates have eased with it: **10y ~4.60%**, 1-yr inflation expectations **3.6%**. Crude roughly flat
(**WTI $78.08 −0.13%, Brent $83.64 +0.11%**) — still no case to un-park XOM.
- **No macro release during market hours today** (only a tentative Cleveland Fed inflation-expectations
  number). **July CPI on Wednesday is the week's dominant event**, PPI Thursday, retail sales Friday.
- **No enabled watchlist symbol reports this week.** Today: **FERG / MNDY / CAMT** pre-open and **SPG**
  after the close — none ours. The week's headliners are **CSCO** (Wed AH) and **AMAT** (Thu AH), plus
  CoreWeave, Cerebras and Lumentum. **WMT verified separately: it reports Thu 2026-08-20**, outside this
  week — checked because August is its reporting month and it sits enabled. **No earnings park today.**
- **Pre-market movers are all non-watchlist:** ZTS **−6.0%** (cut FY26 revenue and EPS guidance),
  RMD **−5.1%**, STX **−4.7%**. No bleed onto the board.
- **MU presents at the KeyBanc Capital Markets Technology Leadership Forum today, 8:00am MDT = 10:00 ET.**
  Verified against Micron's own IR release (announced 2026-07-15) and it is a **recurring annual
  appearance, not a guidance event** — it attended the same forum on 2025-08-11. It does land exactly on
  the IMP-017 entry-window open, in the **highest-ATR name on the board (9.54%)**. **NOT a park** — MU is
  the book's #1 all-time earner (**+$177.84**) and mega-liquid — but the headline risk is recorded.
- **AAPL trades ex-dividend today** ($0.27, pay 08-13): a mechanical **−0.09%** open adjustment on a $313
  stock, immaterial against a 1.25% trail. **No action.** (One aggregator dissents with 08-11; either
  date is noise at this magnitude.)
- **⚠️ Perplexity `sonar` was thin for the FOURTH consecutive run.** It returned "no catalyst confirmed"
  for **18 of 20** tickers, gave **no futures direction at all**, and quoted a stale **AAPL $311.45
  pre-market** against a verified 08-07 close of **$313.29**. To its credit it surfaced the two genuine
  items above (the MU forum and the AAPL ex-div) — both of which **WebSearch then confirmed** before they
  were written down. Its role is now demonstrably **lead-generation only**; WebSearch carried the run, as
  it did on 08-07.

### Carried from daily review (08-07 "Notes for pre-market research")
- **🚨 "Decide C at the 08-10 review"** — the review's one explicit order. **Done: C parked.** ✔
- **"Book CLEAN & FLAT into 08-10"** — ✔ verified live: `/v2/account` ACTIVE, equity **$9,075.74** all
  cash, `/v2/positions` **0**, `/v2/orders?status=open` **0**. Nothing locked.
- **"Do NOT park anything on the strength of two zero-trade days."** Honored — C was parked on **30 days
  without a trade plus its all-time record**, not on 08-06/08-07. **Nothing else parked.** ✔
- **"QQQ remains load-bearing twice over"** (IMP-022 gate + IMP-023 replay universe) — asserted
  `enabled = 1` *before* the commit and re-verified in the restart banner. ✔
- **"SPY / C dead-signal window closes ~08-10"** — **C parked, SPY kept**; the asymmetry is argued below.
- **"ABNB… Keep."** Kept, and its chart is now the strongest on the board. ✔

### Watchlist review
Account **ACTIVE**, equity **$9,075.74**, BP $36,302.96, **0 open positions = nothing locked.** Service had
been `active` since 08-07 21:26:44 UTC, NRestarts=0. All 20 enabled reviewed against overnight news and
60-day daily bars (close vs 20/50-day MA, 5-day change, ATR%, 20-day avg $ volume on the IEX tape):
- **➖ C → PARKED (the one change).** The dead-signal window the last two entries opened expires today, and
  C is the name that fails it: **30 days since its last trade (07-10)**, all-time **−$39.84 on 1W/5** — the
  **worst win rate on the board** — with **ATR 2.49%** and **$71.9M/day** of IEX-tape dollar volume, i.e.
  the low-volatility, thin end of the book, which is precisely the profile that yields few sharp 1-min
  crosses. **This is not a broken feed and the log proves it:** 466 one-minute candles on Friday alone and
  **3 scored candidates in 5 sessions** (two crossover near-misses at conf **67.3** and **61.1** on 08-04,
  last activity 08-05). **C evaluates; it just never converts, and it has not converted in six weeks.**
  JPM already covers financials. Row **parked (`enabled = 0`), not deleted** — re-enable if it starts
  converting.
- **✅ SPY → KEPT, deliberately, even though it is quieter still** (44 days, last trade 06-26). Three
  reasons, and they are why the two names split. ① Its **ATR is 1.18%, the lowest on the board** — the
  silence is *structural* for a broad index ETF and expected, not evidence of decay. ② It is **more active
  than the name being parked**: 5 scored candidates in the last 5 sessions vs C's 3. ③ The weekly review
  names **SPY as the live fallback candidate for `MARKET_FILTER_SYMBOL`** if IMP-022's tripwire ever fires
  — parking the one symbol the strategy may need to test would be self-defeating. **Next review point:
  end-August if still tradeless.**
- **The board is healthy and the trend is intact.** Above the 20MA: **ABNB +19.5%** (and **+17.7% on 5
  days** — the post-earnings move is still extending), **MSFT +17.9%** (+22.8% vs 50MA), AVGO **+9.1%**,
  AMZN **+9.1%**, NVDA **+8.3%**, BABA **+7.9%**, INTC **+4.8%**, QQQ **+3.2%**, SPY **+3.1%**,
  NFLX **+3.1%**, TSM **+2.6%**, JPM **+2.3%**, GOOG **+1.6%**. Below: WMT −0.1%, MU −1.1%, AAPL −3.1%,
  UNH −3.1%, AMD −4.0%, **TSLA −4.3%** (−13.6% vs 50MA, still the weakest chart enabled — but **+2.8%
  Friday and +5.6% on 5 days**, i.e. mending, not breaking). **Nothing here is a park candidate on trend.**
- **⚠️ Volatility outliers, kept and noted (unchanged from 08-07):** **MU 9.54%**, **AMD 8.27%**,
  **INTC 7.52%** — well above where a 1-min ribbon behaves best. All three are mega-liquid and INTC/MU are
  the book's **two best all-time earners (+$191.26 and +$177.84)**. A **sizing** question for the post-close
  routine, **not** a watchlist park.
- **Last-14-day P&L is GREEN — 35 closed trades, +$148.82.** Winners: **INTC +$99.12 (4W/4)**,
  AVGO +$41.34, GOOG +$31.94, MU +$27.93, BABA +$18.74, NVDA +$16.72, **NFLX +$14.89 (2W/2)**, TSM +$3.28.
  Losers: AMZN −$36.18 (0W/2), JPM −$23.25 (0/1), SE −$26.80→−$18.12 (**already parked**), MSFT −$11.73,
  TSLA −$8.07, AAPL −$7.21, AMD −$0.58. **No enabled symbol has a park-worthy record under the current
  rules.**
- **AMZN and AVGO reviewed for parking again and KEPT again**, same reasoning as 08-07: their all-time
  deficits (**−$108.51** and **−$109.78**) were overwhelmingly earned *before* IMP-018, IMP-020, IMP-021 and
  IMP-022, and **AVGO is +$41.34 over the last 14 days under the current rules**. Parking on an exit
  structure that has since been replaced is churn against stale evidence.
- **Parked stay parked:** BIRD, COST, ENPH, QCOM, SE, WPM, XOM — no fresh re-enable case, and crude is flat
  so XOM's park holds for a fourth run. **⚠️ SE reports Q2 tomorrow (Tue 08-11)** — it must not be
  re-enabled today or tomorrow without pricing that print.
- **Adds considered and DECLINED for the third consecutive run.** IMP-022 is at **session 3 of its
  5-session observation window (to ~08-12)** and the weekly's standing instruction is to **protect the
  measurement**; an add changes the candidate pool *underneath* the thing being measured. The capital
  argument also still holds — at **$9.1k equity** the book is capital-constrained, so an extra name mostly
  **displaces** a trade rather than adding one (IMP-017). **Earliest sensible add: after 08-12.**
  *Note the asymmetry that makes today's park compatible with the freeze:* C contributed **0 trades and
  ~0.6 candidates/session** to the pool, so removing it perturbs the measurement about as little as any
  edit could — whereas an add would inject a fresh, unmeasured candidate stream.

### Changes applied to dbo.watchlist
- **C → `enabled = 0`** (row **parked, not deleted**; note set: *"parked 2026-08-10: dead-signal window
  expired - 30d no trade (last 07-10), all-time -$39.84 on 1W/5, ATR 2.5% thin crosses"* — **122 chars**,
  checked against the **VARCHAR(128)** limit before the write).
- One parameterized UPDATE, **1 row affected**, committed only after the assertions passed. **No inserts,
  no deletes, no re-enables.** Post-apply assertions: **19 enabled ≤ 30 ✓** and **QQQ `enabled = 1` ✓**.

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA GOOG INTC JPM MSFT MU NFLX NVDA QQQ SPY TSLA TSM UNH
WMT. Parked (8): BIRD **C** COST ENPH QCOM SE WPM XOM. Service **RESTARTED** 11:36:31 UTC (watchlist
changed) — `active`, NRestarts=0, warmup primed **19/19** symbols from history, subscribed to all 19 on the
iex feed, account ACTIVE $9,075.74, **no open positions**, zero errors. Startup banner confirms the live
config is unchanged: *"Market gate: QQQ 5m ribbon must be bullish to open a long (IMP-022)"*, *"Entry
window: 10:00-16:00 ET (opening-range blackout on, IMP-017…)"*, *"trailing stop 1.25% (active, IMP-018),
tightening to 1.00% once +1.00% in profit (IMP-021)"*. 🔒 Locked: none (0 open positions).
**Tue 08-11 routine: SE reports Q2** — keep it parked, do **not** re-enable on the print. **Wed 08-12 is
July CPI *and* the end of IMP-022's observation window** — expect the gate to suppress trades around the
print and expect that to be **correct**; **earliest sensible add is after 08-12**. SPY's next review point
is **end-August** if it is still tradeless.

---

## 2026-08-11 — Pre-market Research

**NO CHANGES — and the biggest overnight event on the board is the reason it stays a no-change day, not a
reason to act.** Book is CLEAN & FLAT (broker-confirmed **0 positions**, **0 open orders**, equity
**$9,085.28** all cash, `last_equity` == `equity` → nothing carried, nothing marked) → **nothing locked**.
**19 enabled, unchanged**; **service NOT restarted** (nothing to reload). **INTC priced a $20B equity
offering overnight — verified resolved, therefore kept.** IMP-022's observation window closes tomorrow.

### Market context
**Flat tape into tomorrow's CPI, after a directionless Monday.** Monday 08-10 closed slightly red across the
board: **S&P 500 −0.06% to 7,753.11**, **Nasdaq Composite −0.32% to 26,605.36**, **Dow −0.11% to 53,975.98**
— i.e. Friday's record close (7,758) was not extended. Pre-market this morning is flat-to-marginally-lower:
**SPY −0.03%, QQQ −0.04%, DIA −0.14%, IWM −0.13%**. Confirmed against the IEX daily tape (authoritative, per
the 08-10 review's rule): **QQQ 720.80 (−0.29% d1)**, **SPY 773.02 (−0.02%)**.
- **Rates/Fed:** after the soft payrolls print (**−23k**), September *hike* odds have fallen to **~52%** from
  ~67% a week ago (CME FedWatch).
- **⚠️ Only one US release today and it is pre-open and low-impact: NFIB Small Business Optimism (July),
  6:00am ET. NOTHING lands during market hours.** **July CPI is tomorrow, Wed 08-12, 8:30am ET** (consensus
  ~+0.2% MoM core, headline ~2.9% YoY), **PPI Thursday**, **retail sales + UMich Friday**.
- **No enabled symbol reports today.** Today's calendar is **SE, ESLT, ONON, VG, CAH, AMTM, TME, ARMK** —
  **SE is ours and is already parked** (parked 07-30), exactly as the 08-10 review ordered. **It stays
  parked; it is not to be re-enabled on this print.** CSCO (Wed AH) and AMAT (Thu AH) are the week's
  headliners and neither is enabled. WMT's own report remains **Thu 08-20**, outside this week.

### 🚨 INTC — the overnight event, verified, and why it is a KEEP
- **Fact pattern (verified against Intel's own IR press release, CNBC and Investing.com — not taken from
  `sonar`, which missed it entirely):** Intel announced a **$15B** common-stock offering Monday morning;
  the stock closed **−4.06% at $97.52**. **Early this morning Intel upsized and PRICED the deal at $20B —
  210,526,315 shares at $95.00**, a **2.6% discount** to Monday's close, plus a 30-day greenshoe of
  31,578,947 shares. Reported demand **>$100B**. **The offering closes 2026-08-12.** Dilution ≈ **4%**.
- **Verdict: KEEP, and this is the same rule the log has applied all along — park PENDING binaries, keep
  RESOLVED ones.** As of this morning the deal is priced and sized; the uncertainty (does it happen, how
  big, at what price) is gone before the open. A >5x oversubscribed book is a demand signal, not a
  distress signal. INTC is the book's **#1 all-time earner (+$191.26 on 20 trades)** and went **4W/4 for
  +$99.12** in the last 14 days.
- **What is genuinely still live, and is recorded rather than acted on:** today is a supply/repricing
  session in a **7.56% ATR** name that will trade around a $95 print. The two structural defences are
  already in place and need no watchlist edit — the **IMP-017 10:00 ET entry blackout** keeps the bot out
  of the repricing open, and the **5-min gate + IMP-022 QQQ gate** will simply not open a long into a
  supply-driven downtape. **If INTC trades heavy and the bot still gets filled and stopped, that is the
  08-11 daily review's evidence to weigh, not a pre-market guess.**

### Carried from daily review (08-10 "Notes for pre-market research")
- **"Book CLEAN & FLAT into 08-11"** — ✔ verified live: `/v2/account` **ACTIVE**, equity **$9,085.28**, cash
  $9,085.28, BP $36,341.12, `/v2/positions` **0**, `/v2/orders?status=open` **0**. Nothing locked.
- **"🚨 SE reports Q2 tomorrow (Tue 08-11) — it is parked and must STAY parked."** — ✔ honored, and its
  report today is independently confirmed on the earnings calendar. **Untouched.**
- **"⚠️ Wed 08-12 is July CPI *and* the close of IMP-022's window."** — ✔ confirmed (CPI Wed 8:30am ET).
  No add today; see below.
- **"✅ ABNB… Keep, emphatically."** — ✔ kept. It is **still the strongest chart on the board** (+22.2% vs
  20MA, **+22.5% on 5 days**, +3.57% Monday) and delivered the 08-10 session's only excursion to clear the
  give-back.
- **"⚠️ AMZN is the name to watch… if it converts one of those near-misses and loses, park it."** — the
  condition was **not met**: AMZN took **no trade** on 08-10 (4 crossover rejects, 0 fills). **Per the
  review's own test, no park.** It stays on notice; it was the day's busiest generator (4 candidates).
- **"MSFT is the notable absence… flag it if it repeats."** — ✔ **it did not repeat as a concern**: MSFT is
  12 candidates over the last 6 sessions, third-most on the board. One quiet session, now closed out.
- **"QQQ remains load-bearing twice over — verify `enabled = 1`."** — ✔ asserted `enabled = 1` (it is), and
  since no write was issued there is no edit that could have disturbed it.
- **"Use `bot.report --mfe` instead of hand-deriving MFE."** — noted; it is a post-close instrument and the
  08-10 review's table is <24h old, so nothing was re-derived here.

### Watchlist review
Account **ACTIVE**, equity **$9,085.28**, **0 open positions = nothing locked.** Service `active` since
**08-10 21:27:44 UTC**, NRestarts=0. All 19 enabled reviewed against overnight news and 60-day daily bars
(close vs 20/50-day MA, 5-day change, ATR%, 20-day avg $ volume on the IEX tape):
- **Trend is broadly intact.** Above the 20MA: **ABNB +22.2%** (the clear leader), **MSFT +17.8%**,
  **BABA +10.3%**, **AMZN +9.8%**, **AVGO +7.3%**, NFLX +5.9%, NVDA +4.8%, QQQ +2.9%, SPY +2.9%, JPM +2.6%,
  TSM +2.3%, GOOG +2.2%, INTC +0.9%, WMT +0.7%. Below: MU −2.5%, UNH −2.5%, TSLA −2.7%, **AAPL −4.6%**,
  **AMD −6.1%**. Versus the 50MA the weak names are **TSLA −12.5%**, **INTC −11.4%**, **MU −11.1%**,
  **AMD −8.5%**. **Nothing here clears the park bar on trend** — and note the semis' 50MA deficits are the
  SOX drawdown the weekly already flagged, not name-specific decay.
- **⚠️ Volatility outliers, kept and noted (unchanged for a third run):** **MU 9.09%**, **AMD 8.06%**,
  **INTC 7.56%** ATR. Still a **sizing** question for the post-close routine, **not** a watchlist park.
- **AAPL — downgrade verified, and still not a park.** **Jefferies cut it hold → Underperform, PT
  $285.56 → $263.66** (~16% below spot), on supply-chain checks that Apple has **cancelled the all-glass
  iPhone** planned for Sept 2027 over yields; **DZ Bank cut to Hold**. This was the one genuine lead
  `sonar` produced and **WebSearch confirmed it independently** (AppleInsider / Yahoo / Fortune / Seeking
  Alpha). **It is a rating change, not a binary event, and Monday already traded it** (AAPL −1.63% to
  $308.17). AAPL is all-time **+$57.45 (7W/10)** and produced **10 candidates in 6 sessions**. **Keep — on
  notice**, which is what its row already says. Re-examine if it loses the 50MA (−0.5% away).
- **NVDA — noted, not actionable.** Reports of a **~$500B financing partnership** (Apollo, Blackstone,
  BlackRock/GIP, Brookfield, Goldman); closed **−2.88%** Monday with the chip complex. **Earnings confirmed
  for Wed 2026-08-26 AH — outside this week**, so no park is due. Keep.
- **Signal-liveness audit (new this run, 6 sessions 08-03 → 08-10, from the strategy journal): every one of
  the 19 enabled symbols scored at least 3 candidates. Nothing on this board is dead.** Most active:
  **BABA 19, SPY 17, NFLX 15, TSM 14, AVGO 13, QQQ 13, MSFT 12**. Quietest: **INTC 3, WMT 3, AMD 5, ABNB 6,
  UNH 6**. **This retires two open questions in the log's favour:** SPY's silence is *not* signal death
  (17 candidates, 2nd-most on the board — it is converting none, which is a different problem and its
  review point stays **end-August**), and INTC's low count is a *conversion-rate* artifact, not decay — its
  3 candidates produced 4 winning trades in the window.
- **14-day P&L is strongly GREEN: 31 closed trades, net +$236.73** (window 07-28 → 08-11; the 08-10 entry's
  +$148.82 used a window one day earlier — same trades, different edges). Winners: **INTC +$99.12 (4W/4)**,
  GOOG +$45.11, AVGO +$29.74, BABA +$29.25, **ABNB +$26.21**, NVDA +$16.72, MU +$13.73, NFLX +$11.27,
  TSM +$3.28. Losers: **AMZN −$18.49 (0W/1)**, TSLA −$8.07, MSFT −$5.76, SE −$4.80 (**already parked**),
  AMD −$0.58. **No enabled symbol has a park-worthy record under the current rules.**
- **Parked stay parked:** BIRD, C, COST, ENPH, QCOM, SE, WPM, XOM. **SE reports today and must not be
  re-enabled on the print** (its 07-30 park was for liquidity + record, and today's print resolves neither).
  No fresh re-enable case for any of the other seven; **C's park is one session old** and re-enabling it now
  would be pure churn.
- **📌 WMT is named here as the NEXT park candidate, for a decision after 08-12.** It is the weakest name on
  the combined dead-signal test: **tied-quietest at 3 candidates in 6 sessions**, **0 trades in 18 days**
  (last 07-24), all-time **−$47.51 on 6 trades**, ATR **2.29%**, **$115M/day** — the same low-volatility,
  low-conversion profile that got C parked. **It does not meet the C bar yet** (C was parked at **30** days
  tradeless, not 18). **Complication to handle deliberately, not by drift: WMT reports Thu 08-20**, so an
  earnings park is due 08-19 regardless. **Decide WMT on its own merits at the 08-13 run** — do not let the
  earnings park silently become the dead-signal park, because the two have different re-enable conditions.
- **Adds considered and DECLINED for the fourth consecutive run — the last time this reason will be
  available.** IMP-022 is at **session 4 of its 5-session window, which closes tomorrow (08-12)**, and the
  weekly's standing instruction is to protect the measurement; an add injects an unmeasured candidate
  stream underneath the thing being measured, on the eve of its verdict. The capital argument also holds at
  **$9.1k equity** (IMP-017: an extra name mostly *displaces* a trade rather than adding one). **From 08-13
  the freeze expires and the burden flips — the next run should arrive with a screened add candidate or an
  explicit reason it did not.**

### Changes applied to dbo.watchlist
**NONE. No UPDATE, no INSERT, no DELETE — the table was read, asserted, and left byte-for-byte alone.**
This is the intended outcome, not an omission: no enabled symbol carries a pending binary today (INTC's
resolved at pricing, AAPL's is a rating change already traded), no symbol meets the dead-signal park bar,
and the one measurement in flight closes tomorrow. Assertions re-run against the live table after the
review: **19 enabled ≤ 30 ✓**, **QQQ `enabled = 1` ✓**, 8 parked rows all still present (none deleted) ✓.

### Final watchlist
**19 enabled** (≤30 ✓), unchanged: AAPL ABNB AMD AMZN AVGO BABA GOOG INTC JPM MSFT MU NFLX NVDA QQQ SPY
TSLA TSM UNH WMT. Parked (8): BIRD C COST ENPH QCOM SE WPM XOM. **Service NOT restarted — correctly, because
nothing changed** (the watchlist is read only at startup, so a restart would have been a pointless
interruption). Health verified in place instead: `active`, **NRestarts=0**, up since **08-10 21:27:44 UTC**
(nightly restart), **warmup primed 19/19** from history, **subscribed to all 19** on the IEX feed, account
ACTIVE $9,085.45 at boot, **no open positions**, clean banner — entry window 10:00–16:00 ET (IMP-017), QQQ
market gate (IMP-022), trail 1.25% tightening to 1.00% (IMP-018/IMP-021). 🔒 Locked: none (0 positions).
**Wed 08-12: July CPI at 8:30am ET *and* IMP-022's verdict day *and* INTC's offering closes** — expect a low
trade count and expect that to be correct. **From Thu 08-13 the add-freeze expires** (bring a screened
candidate), **WMT gets its dead-signal decision**, and SPY's review point remains **end-August**.

### Perplexity `sonar` — run 6, thin again, and it missed the day's one real event
`sonar` returned **"no specific overnight/pre-market catalyst"** for **18 of 20** tickers, **no futures
direction at all** ("not provided in the search results"), and **no in-session calendar**. It produced one
genuine lead — the **AAPL Jefferies/DZ Bank downgrades**, which WebSearch then confirmed — and it also gave
**self-contradictory AAPL pre-market prints** (+0.3% in one feed, −1% in another) in the same answer.
**Most importantly it said nothing about INTC**, whose **$20B overnight pricing** was the single largest
event affecting an enabled symbol. **Sixth consecutive weak run; the 08-10 review's rule stands and is
extended: `sonar` is lead-generation only, never a market-regime source, and its silence on a ticker is
not evidence of no catalyst.** WebSearch + the IEX daily tape carried this run.

---

## 2026-08-12 — Pre-market Research

**NO CHANGES — CPI morning and the fifth and final session of IMP-022's measurement window, which is
exactly the day not to touch the board.** Book is CLEAN & FLAT (broker-confirmed **0 positions**,
**0 open orders**, equity **$9,085.28** all cash, `last_equity` == `equity`) → **nothing locked**.
**19 enabled, unchanged**; **service NOT restarted** (nothing to reload). Two on-notice triggers fired
and are recorded rather than acted on (**AAPL lost its 50MA; GOOG has gone quiet under an antitrust
slide**), and **the add candidate the 08-11 entry demanded is screened, verified and handed to tomorrow:
PLTR.**

### Market context
**Futures firm into the July CPI print, after a red Tuesday.** Pre-market: **S&P 500 futures +0.2%,
Nasdaq-100 +0.6%, Dow flat**; **SPY $772.33 (+0.23%), QQQ $722.62 (+0.58%)**. Tuesday 08-11 closed lower
across the board — **S&P 500 −0.32% to 7,728.20**, **Nasdaq Composite −0.60% to 26,445.45**, **Dow −0.34%
to 53,791.85** — i.e. the second consecutive down day and a further step off Friday's record. Confirmed
against the IEX daily tape (authoritative, per the 08-10 rule): **QQQ 718.30 (−0.35% d1)**, **SPY 770.52
(−0.32%)**.
- **⚠️ July CPI, 8:30am ET — and it lands PRE-OPEN, not in-session.** Consensus **headline +0.1% MoM /
  3.4% YoY** (from 3.5%), **core +0.2% MoM / 2.5% YoY**. **The risk skew is toward tightening, not
  easing:** multiple FOMC members have signalled a possible **September hike**, so a hot core print is the
  gap-and-reverse tape IMP-022 exists to veto. 10-year yield ~**4.7%**.
- **Nothing market-moving lands DURING market hours.** MBA mortgage applications (pre-open), the
  **10-year note auction 1:00pm ET** and the **Treasury monthly budget 2:00pm ET** are the only in-session
  items and neither moves single names.
- **No enabled symbol reports today.** Today's calendar is **CSCO (AMC), NBIS, CBRS, TRMB, GLBE, PAAS** —
  **none is enabled**. **AMAT is Thursday**, **WMT's own report remains Thu 08-20**, **NVDA Wed 08-26**.
  Both are outside this week; no earnings park is due today.
- **Pre-market movers are all outside the book** (WXM +175%, PLAG +105%, SCKT −38%, ONON −16.5% on its
  miss). **The one book-relevant line: INTC is the most active ticker pre-market at ≈$847M dollar volume**
  — its $20B offering **closes today**, exactly as the 08-11 entry recorded.

### Carried from daily review (08-11 "Notes for pre-market research")
- **"Book CLEAN & FLAT into 08-12"** — ✔ verified live: `/v2/account` **ACTIVE**, equity **$9,085.28**,
  cash $9,085.28, BP $36,341.12, `/v2/positions` **0**, `/v2/orders?status=open` **0**. Nothing locked.
- **"🚨 Wed 08-12 is a triple event: CPI, IMP-022's verdict day, INTC's offering closes."** — ✔ all three
  confirmed. **Expect a low trade count and expect that to be correct**; that expectation is why this is a
  no-change day and not a hedging day.
- **"✅ ABNB… Keep, emphatically."** — ✔ kept, and it is **still the strongest chart on the board**
  (**+20.9% vs 20MA, +27.1% vs 50MA, +23.3% on 5 days**), 11 candidates in the 7-day journal.
- **"⚠️ JPM produced 5 candidates, 4 died on the crossover floor — positive liveness, flag if near-misses
  accumulate without conversion."** — they **did** accumulate: JPM is **11 candidates in 5 sessions, third-
  most on the board, and still 0 trades since 07-27**. Recorded for the post-close routine, which owns
  `MIN_CROSSOVER` — **it is not a watchlist problem** and JPM is not a park candidate on a liveness high.
- **"MSFT is quiet two sessions running… re-check 08-12/08-13."** — ✔ **re-checked and the concern is
  retired**: MSFT is **10 candidates over the 5 journal sessions, 7th-most of 19**, and +15.7% vs 20MA /
  +23.0% vs 50MA. Two quiet sessions on a down tape, not decay.
- **"AMZN stays on notice; park only if it converts a near-miss and loses."** — condition **still not met**
  (7 candidates in the window, no new trade since 08-03). No park. Stays on notice.
- **"WMT's dead-signal decision is scheduled for the 08-13 run."** — ✔ **not advanced today, deliberately**;
  see below.
- **"QQQ remains load-bearing twice over — verify `enabled = 1`."** — ✔ asserted `enabled = 1`; no write was
  issued today, so nothing could have disturbed it.
- **"From 08-13 the add-freeze expires — arrive with a screened candidate."** — ✔ **done, one day early**:
  PLTR screened and verified below, ready for tomorrow.
- **"IMP-026: journald is UTC from tonight's restart."** — ✔ **acceptance test PASSES.** Startup lines read
  `2026-08-11 21:23:51,776 UTC INFO …` and the prefix matches `ActiveEnterTimestamp=21:23:50 UTC`. Today's
  post-close review can pair `no entry` lines to candles without shifting anything by hand — which matters,
  because **IMP-022's verdict is read off this instrument tonight**.

### Watchlist review
Account **ACTIVE**, equity **$9,085.28**, **0 open positions = nothing locked.** Service `active` since
**08-11 21:23:50 UTC**, **NRestarts=0**, warmup primed **19/19**, subscribed to all 19 on the IEX feed,
banner confirms the deployed process runs the QQQ market gate + the two-stage trail. All 19 enabled reviewed
against overnight news and 100-day daily bars (close vs 20/50-day MA, 5-day change, ATR%, 20-day avg $
volume on the IEX tape):
- **Trend has thinned but not broken.** Above the 20MA: **ABNB +20.9%** (the clear leader), **MSFT +15.7%**,
  **AMZN +7.0%**, **BABA +5.9%**, AVGO +5.3%, NVDA +4.6%, NFLX +3.7%, TSM +3.1%, JPM +3.0%, QQQ +2.5%,
  SPY +2.4%, INTC +1.6%, WMT +1.3%. Below: **MU −1.2%, TSLA −1.2%, GOOG −1.3%, UNH −3.7%, AMD −4.6%,
  AAPL −5.4%**. Versus the 50MA the weak names are **TSLA −11.5%, INTC −11.1%, MU −10.2%, AMD −7.5%** —
  the SOX drawdown the weekly flagged, not name-specific decay. **Nothing clears the park bar on trend.**
- **⚠️ Volatility outliers, kept and noted (fourth consecutive run):** **MU 8.91%**, **AMD 7.66%**,
  **INTC 7.39%** ATR. Still a **sizing** question for the post-close routine, **not** a watchlist park.
- **🔔 AAPL — the 08-11 trigger FIRED, and the answer is still keep-on-notice.** Yesterday's entry set the
  test "re-examine if it loses the 50MA (−0.5% away)". **It lost it: AAPL closed $304.88, −1.4% vs the 50MA
  and −5.4% vs the 20MA** (−1.07% Tuesday, −1.35% on 5 days), the follow-through from Monday's Jefferies
  cut to Underperform. **Re-examined, and it does not park:** it is the book's **third-best name all-time
  (+$57.45, 7W/10)**, **$638M/day** the second-most liquid single name on the board, ATR **3.10%** —
  textbook ribbon material — and **6 candidates in 5 sessions** says the signal is alive. A name trading
  under its MAs is precisely what the **5-min gate + IMP-022** decline to buy; the defence is structural and
  needs no watchlist edit. **New, tighter test recorded so this cannot drift: park AAPL if it is still below
  the 50MA on 08-19 AND has taken no trade by then** (last entry 07-27).
- **🔔 GOOG — new and the more serious of the two, formally ON NOTICE.** It is the **worst 5-day performer
  on the board (−8.61%)**, fell **−3.62% Tuesday**, and has now lost **both** MAs (−1.3% vs 20MA, −2.9% vs
  50MA) after being **+2.2% above the 20MA yesterday**. **Cause verified by WebSearch (gurufocus /
  tradingkey / SEC 8-K), not taken from `sonar`, which was silent on it:** federal enforcers' appellate
  filings seeking to overturn the search-remedy ruling (targeting the Apple/Mozilla default payments), a
  French publishers' complaint over AI Overviews, a **$25B senior-notes offering closed 08-10** on top of a
  $40B ATM programme against **~$205B 2026 capex**, and the departures of chief scientist Jeff Dean and
  DeepMind's Demis Hassabis. **This is a drift, not a binary — there is nothing scheduled today — so the
  park rule the log has always applied (park PENDING binaries, keep RESOLVED ones) does not fire.** But
  the second leg is what makes it notable: **GOOG is the ONLY enabled symbol with ZERO candidates in the
  5-session journal window**, and it has taken **no trade since 07-31**. **Test recorded: if GOOG is still
  below both MAs with 0 candidates at the 08-17 run, it parks** — it would then be 12 sessions silent with
  a broken chart, which is the C/WMT profile.
- **INTC — the offering closes today, and it stays a KEEP for the same reason it did yesterday.** The deal
  is priced and sized (**210,526,315 shares at $95.00**, ~4% dilution); today is settlement, not a new
  binary. It is the most-active ticker pre-market (~$847M), which is a liquidity fact, not a distress one.
  Book's **#1 all-time earner (+$191.26 on 20 trades)** and **4W/4 for +$99.12** in the 14-day window. The
  IMP-017 10:00 ET blackout keeps the bot out of the repricing open.
- **Signal-liveness audit, refreshed (5 sessions 08-05 → 08-11, from journald):** most active **NFLX 12,
  TSM 12, JPM 11, ABNB 11, BABA 11, AVGO 10, MSFT 10**; quietest **WMT 2, INTC 3, QQQ 3, TSLA 4, MU 4**;
  **GOOG 0**. Refusal split across the window: **65 confidence/other, 58 crossover floor, 12 market gate** —
  consistent with the 08-11 review's finding that **the crossover floor, not the market gate, is the largest
  unmeasured filter**. That is a post-close question and is flagged there, not here.
- **14-day P&L stays GREEN: 31 closed trades, 19W (61%), net +$236.73** (window unchanged from 08-11 — no
  trades on 08-11, so these are the same 31 trades, deliberately not re-derived). Winners **INTC +$99.12
  (4W/4)**, GOOG +$45.11, AVGO +$29.74, BABA +$29.25, ABNB +$26.21, NVDA +$16.72, MU +$13.73, NFLX +$11.27,
  TSM +$3.28. Losers AMD −$0.58, SE −$4.80 (**already parked**), MSFT −$5.76, TSLA −$8.07, AMZN −$18.49.
  **No enabled symbol has a park-worthy record under the current rules.**
- **📌 WMT — decision deliberately NOT taken today, and this is a choice not an oversight.** It is the
  quietest name on the board (**2 candidates in 5 sessions**), **0 trades in 19 days** (last 07-24),
  all-time **−$47.51 on 6 trades**, ATR **2.24%**, **$114M/day**. The 08-11 entry scheduled this for the
  **08-13 run** and there is no new information today that advances it — taking it a day early on a CPI
  morning would be churn dressed as decisiveness. **Its earnings park is separately due 08-19; the two have
  different re-enable conditions and must not be merged.**
- **Parked stay parked:** BIRD, C, COST, ENPH, QCOM, SE, WPM, XOM. Checked for re-enable cases and there is
  none: **SE** reported yesterday but its park was for liquidity + a 1W/5 −$53.42 record, neither of which a
  print resolves; **C** (parked 08-10) is +2.4% vs 20MA but two sessions into a 30-day-tradeless park and
  re-enabling it now would be pure churn; **QCOM −13.6% vs 50MA** and **COST flat at −0.0%/−0.5% with ATR
  1.90%** both still fail the trending-and-active test on their own numbers.

### Add candidate — screened, verified, and handed to the 08-13 run
**No add today.** The reason is specific and expires tonight: **today is session 5 of 5 of IMP-022's
measurement window**, the weekly's standing instruction is to protect that measurement, and injecting an
unmeasured candidate stream on the final session — of the best-validated change this bot has — to save one
day is a bad trade. **The 08-11 entry's burden ("arrive with a screened candidate or an explicit reason")
is met by screening it today so tomorrow can simply act:**
- **PLTR — the lead candidate. Verified on Alpaca: `tradable: true`, `status: active`, NASDAQ, us_equity.**
  **Strongest trend on any screened name: +25.5% vs 20MA, +30.9% vs 50MA, +7.58% on 5 days.** Liquidity
  **$204M/day on the IEX tape** — ahead of every current non-mega-cap on the board (BABA $44M, ABNB $33M)
  and comparable to AVGO $218M / NFLX $216M. **ATR 5.30%** — high, but below the three outliers already
  carried (MU 8.91 / AMD 7.66 / INTC 7.39), so it adds no new class of risk. **Earnings binary RESOLVED and
  far away: reported Q2 08-03 AMC (EPS $0.41 vs $0.34, rev $1.94B vs $1.81B, +93% YoY, FY guide raised to
  ~$8.15B, +11% AH); next report 2026-11-02** — a full quarter of clear runway, which no other candidate
  matches.
- **Alternates, all verified `tradable: true` / `status: active`:** **ANET** (+10.8%/+15.0%, +3.32% Tue,
  $80M/day, ATR 5.54%), **UBER** (+9.6%/+9.0%, **+9.10% on 5 days**, $87M/day, ATR 3.54%), **CRM**
  (+10.0%/+14.4%, $83M/day, ATR 4.42%), **LLY** ($136M/day but +3.1%/+4.4% only).
- **Rejected on their numbers:** META (−1.1% vs 20MA, no trend), ORCL (+10.8% vs 20MA but **−7.6% vs 50MA**,
  −3.69% Tue — conflicting timeframes), GS (−1.9%/−2.0%), COIN (−5.8%/−6.7%), MRVL (**−11.9% vs 50MA**),
  SMH/XLK/IWM (index overlap with QQQ/SPY, and **SMH would deepen an already semi-heavy book**).
- **Sizing caveat to carry into the add:** at **$9.1k equity** an extra name mostly *displaces* a trade
  rather than adding one (IMP-017), so **PLTR at $174.94 is a better fit than a $400+ name** — whole-share
  quantisation still flattens the confidence→size curve on expensive tickers (the weekly's open MU/AVGO
  item).

### Changes applied to dbo.watchlist
**NONE. No UPDATE, no INSERT, no DELETE — the table was read, asserted, and left byte-for-byte alone.**
This is the intended outcome: no enabled symbol carries a pending binary today (INTC's resolved at pricing,
AAPL's and GOOG's are drifts and ratings, not events), no symbol meets the dead-signal park bar, the two
scheduled decisions (WMT 08-13, GOOG 08-17) are not due, and the one measurement in flight closes tonight.
Assertions re-run against the live table after the review: **19 enabled ≤ 30 ✓**, **QQQ `enabled = 1` ✓**,
8 parked rows all still present (none deleted) ✓.

### Final watchlist
**19 enabled** (≤30 ✓), unchanged: AAPL ABNB AMD AMZN AVGO BABA GOOG INTC JPM MSFT MU NFLX NVDA QQQ SPY
TSLA TSM UNH WMT. Parked (8): BIRD C COST ENPH QCOM SE WPM XOM. **Service NOT restarted — correctly,
because nothing changed** (the watchlist is read only at startup, so a restart would have been a pointless
interruption). Health verified in place instead: `active`, **NRestarts=0**, up since **08-11 21:23:50 UTC**,
**warmup primed 19/19**, subscribed to all 19, account ACTIVE $9,085.28 at boot, no open positions, banner
clean — entry window 10:00–16:00 ET (IMP-017), QQQ market gate (IMP-022), trail 1.25% tightening to 1.00%
(IMP-018/IMP-021), **and log lines now stamped `UTC` (IMP-026 verified live)**. 🔒 Locked: none (0
positions). **Tonight the post-close routine owns IMP-022's 5-session verdict** — it is 3 for 3 on live
counterfactuals and the instrument it is read from is now correct. **Tomorrow 08-13: the add-freeze expires
(PLTR is screened and ready), WMT gets its dead-signal decision.** Then **WMT earnings park 08-19**,
**GOOG re-examination 08-17**, **AAPL re-examination 08-19**, and SPY's review point stays **end-August**.

### Perplexity `sonar` — run 7, thin again, and wrong on the one number it volunteered
`sonar` returned **"no specific overnight/pre-market catalyst"** for **17 of 19** tickers — including
**GOOG, whose −8.6% five-day antitrust-driven slide was the largest single-name development on the board**,
and **INTC on the day its $20B offering closes**. It called futures **"mixed"** with "no clear directional
move", which the tape contradicts (**ES +0.2%, NQ +0.6%, QQQ +0.58%**), and its only ticker-level lead was
the **stale** AAPL Jefferies downgrade already logged on 08-11. It also mislabelled the CPI release as
**"12:30 ET"** — that is 12:30 **UTC** / 8:30am ET, and a run that took it at face value would have booked
an in-session macro shock that does not exist. It did correctly identify CPI as the day's dominant catalyst,
which is the whole of its value today. **Seventh consecutive weak run. The standing rule holds and hardens:
`sonar` is lead-generation only, never a market-regime source, never a clock, and its silence on a ticker is
not evidence of no catalyst.** WebSearch + the IEX daily tape carried this run.

---

## 2026-08-13 — Pre-market Research

**The add-freeze expired and the one add it was held for is live: PLTR is in, 19 → 20 enabled. WMT's
dead-signal decision came due today and the answer is KEEP** — it fails the log's own 30-day bar by ten days
and its chart is the healthiest it has been all month. Book is CLEAN & FLAT (broker-confirmed **0 positions**,
**0 open orders**, equity **$9,089.68**, all cash, `last_equity` == `equity`) → **nothing locked**. One change;
service **restarted clean, warmup 20/20**.

### Market context
**Futures modestly higher into PPI, and yesterday's CPI removed the week's dominant risk.** Pre-market: **Dow
futures +102 (+0.2%), S&P 500 +0.2%, Nasdaq-100 +0.1%**, supported by retreating Treasury yields. **July CPI
landed exactly in line Wednesday — headline +0.1% MoM / 3.4% YoY, core +0.2% / 2.5%** — the benign resolution
of the gap-and-reverse tape the 08-12 entry was braced for. The S&P 500 is back **within striking distance of
a record** and the Nasdaq-100 hit a **one-month high**. Overnight, NQ contracts slipped slightly in Asia after
**CSCO's print disappointed** (**not enabled** — no book exposure).
- **⚠️ Everything that matters today lands PRE-OPEN, not in-session.** **July PPI + jobless claims share the
  8:30am ET tape** (PPI headline +0.2% MoM vs −0.3% prior, YoY easing to 4.9% from 5.5%, core +0.3% MoM /
  4.1% YoY; initial claims 202K vs 199K, continuing 1,800K vs 1,801K). **Fed's Barkin speaks 8:40am ET**,
  Hammack also on the docket — **both pre-open**. The bot's IMP-017 blackout means it takes no entry before
  **10:00 ET**, by which time all of it is priced.
- **The only in-session item is the 30-year auction at 1:00pm ET**, closing out the refunding. It does not
  move single names.
- **No enabled symbol reports today.** Today's calendar is **JD (BMO), BN, NTES, TPR, NU** and **AMAT (AMC)**
  — none enabled. **AMAT after the close is semi-adjacent** and can move MU/NVDA/AMD/INTC/TSM in tomorrow's
  pre-market, but not during today's session; the book is flat every night so there is no carry exposure to it.
  **WMT's own report is confirmed Thu 08-20 BMO** (Q2 FY27, cons. EPS $0.74 on ~$187B) — verified against
  Walmart IR, not taken from `sonar`. **NVDA remains 08-26.**
- Brent **−2% to $87.17**, WTI −2.2% to $81.41.

### Carried from daily review (08-12 "Notes for pre-market research")
- **"📌 The DB will tell you 08-12 was a blank day. It was not."** — ✔ **verified at the broker and the
  correction is applied throughout this entry.** `/v2/orders` shows **MU buy 2 @ 924.08 (14:08:01.58Z)** and
  **MU sell 2 @ 926.31 (18:25:38.99Z, stop)** = **+$4.46**. `dbo.trades` still has **no row for it**, so every
  DB-derived figure below understates MU by one winner. Recorded, not re-diagnosed — the entry-INSERT retry is
  the post-close routine's queued item, not a watchlist matter.
- **"Book CLEAN & FLAT into 08-13"** — ✔ live: **ACTIVE**, equity **$9,089.68**, cash $9,089.68, BP
  $36,358.72, **0 positions, 0 open orders**. (The 08-12 review recorded $9,089.74 at boot; the 6¢ delta is a
  settle-side adjustment, not a trade — `last_equity` == `equity` confirms nothing moved overnight.)
- **"✅ MU is the standout and should stay emphatically."** — ✔ kept, no question raised. It converted the
  only trade of the week, closed **+4.96% Wednesday**, and is **+3.7% vs its 20MA**. Its **8.61% ATR is again
  the highest on the board** and again a **sizing** question for the post-close routine, not a park question.
- **"⚠️ INTC: 6 candidates, 0 conversions… flag it again if it repeats."** — ✔ **it did not repeat as a
  concern**: INTC closed **+3.42% Wednesday**, is **+5.1% vs its 20MA**, and its offering overhang is settled.
  5 candidates on 08-12 with two near-misses at conf 73.5/62.4. Liveness is healthy; the blocker is the
  crossover floor, which is the post-close routine's file.
- **"ABNB going silent is a genuine break — the first thing to check tomorrow."** — ✔ **checked, and it is
  not a break.** Across the 5-session window ABNB ran **08-07:4, 08-11:5, and 0 on 08-06/08-10/08-12** — lumpy,
  not a four-session run into silence, and **it converted a winner on 08-10 (+$26.21)**. Its chart is still the
  strongest on the board (**+16.5% vs 20MA, +23.0% vs 50MA, +18.1% on 5 days**) after a −2.64% Wednesday
  give-back. **Keep, concern retired.**
- **"AMZN is now three sessions with no candidate at all."** — its park test ("converts a near-miss and loses")
  is **still not met**, and the silence claim is **softer than it looked**: AMZN has **7 candidates** in the
  window (08-06:2, 08-07:1, 08-10:4). Chart fine (+4.8%/+7.9%). **No park. Stays on notice.**
- **"WMT's dead-signal decision is due at the 08-13 run."** — ✔ **taken today. Decision: KEEP.** See below.
- **"PLTR was screened and handed over… the add decision is live tomorrow."** — ✔ **acted on: added.**
- **"QQQ remains load-bearing twice over — verify `enabled = 1` before and after any watchlist edit."** — ✔
  asserted **both before and after** today's INSERT; `enabled = 1` on both reads.

### Watchlist review
Account **ACTIVE**, equity **$9,089.68**, **0 open positions = nothing locked.** All 19 incumbents reviewed
against overnight news and 110-day daily bars off the IEX tape (close vs 20/50-day MA, 5-day and 1-day change,
ATR%, 20-day avg $ volume), plus a 5-session signal-liveness audit from journald.
- **Trend broadened this week — the thin-but-not-broken picture of 08-12 improved.** Above the 20MA:
  **ABNB +16.5%** (leader), **MSFT +11.8%**, **NVDA +7.5%**, AVGO +5.0%, INTC +5.1%, AMZN +4.8%, TSM +4.7%,
  MU +3.7%, JPM +3.6%, WMT +3.6%, BABA +3.4%, QQQ +3.2%, NFLX +2.9%, SPY +2.6%. Below: **TSLA −1.8%,
  GOOG −1.1%, AMD −2.3%, UNH −2.8%, AAPL −5.9%**. **Only five names are below their 20MA, versus six on
  08-12, and the index proxies both firmed** (QQQ +3.2% vs +2.5%, SPY +2.6% vs +2.4%). Versus the 50MA the
  laggards are **TSLA −12.5%, INTC −7.9%, AMD −5.6%, MU −5.6%** — still the SOX drawdown, still not
  name-specific decay. **Nothing clears the park bar on trend.**
- **⚠️ Volatility outliers, kept and noted (fifth consecutive run):** **MU 8.61%**, **AMD 7.32%**,
  **INTC 7.19%** ATR. Unchanged verdict: a **sizing** question for the post-close routine, **not** a park.
- **Signal-liveness audit, 5 sessions (08-06 → 08-12), 137 no-entry events:** most active **TSM 14, JPM 12,
  BABA 11, MSFT 10, NFLX 10, ABNB 9, NVDA 9, AVGO 8, SPY 8**; mid **AMZN 7, INTC 7, AMD 6, UNH 6, AAPL 5,
  QQQ 5**; quietest **TSLA 4, WMT 4, MU 2** (MU also **converted**, so its true liveness is 3). **GOOG is the
  only enabled symbol with ZERO candidates across all five sessions.** Refusal split: **crossover floor 63,
  confidence floor 61, market gate 13** — the crossover floor is again the largest filter, with **30 near-misses
  at conf ≥ 65**. Post-close's file, not this routine's.
- **⚙️ METHOD GOTCHA, recorded so the next run does not repeat it.** My first liveness pass returned **only
  08-12** and would have produced a false "the whole board went dead" reading. Cause: the regex required the
  ` UTC ` token in the message, and **IMP-026 only added that token on the 08-11 restart** — every pre-08-11
  line was silently dropped. **Fix: filter and date these audits off journald's own timestamp (`-o short-iso`),
  never off the message prefix**, which is UTC only after 08-11 and WIB before it. The unit's journal reaches
  back to **08-02**, so the history is there.
- **🔔 GOOG — deteriorating, and the dated test is held rather than pulled forward.** It is **0-for-5 sessions
  on candidates**, has taken **no trade since 07-31 (13 days)**, sits below both MAs (−1.1% / −3.0%) and is
  **−4.91% on 5 days**. The 08-12 entry set the test at the **08-17 run** and there is no *new* information
  today — the antitrust/capex drift is the same one already logged. **Pulling a dated test forward by two
  sessions because the number looks bad is exactly the churn this log exists to prevent.** Test stands: **if
  GOOG is still below both MAs with 0 candidates at the 08-17 run, it parks.**
- **🔔 UNH — new, and it gets the same treatment as GOOG rather than a snap park.** Last trade **07-17 (27
  days)**, below both MAs (−2.8% / −2.1%), ATR **2.53%**, **$102M/day** — the second-thinnest single name after
  WMT. But it is **all-time positive (+$19.38, 4W/7)** and **alive at the candidate level (6 in the window)**,
  so it fails the dead-signal profile on both the C precedent and liveness. **Its 30-day mark falls 08-16 →
  test recorded for the 08-17 run, same day as GOOG's: park UNH if it has taken no trade by then AND is still
  below both MAs.**
- **SPY — untouched, review point unchanged.** Longest tradeless streak on the board (**last trade 06-26, 48
  days**, 4 trades all-time, −$11.24) but **8 candidates in the window** and it is a deliberate diversifier.
  Its review point remains **end-August**; noted, not advanced.
- **14-day P&L (DB, therefore understating MU by the missing +$4.46): 27 closed trades, 17W (63%), net
  +$233.83.** Winners **INTC +$99.12 (4W/4)**, GOOG +$45.11, BABA +$32.82, AVGO +$29.74, ABNB +$26.21,
  NVDA +$16.72, MU +$13.73, TSM +$3.28. Losers AMD −$0.58, MSFT −$5.76, TSLA −$8.07, AMZN −$18.49. **No
  enabled symbol has a park-worthy record under the current rules.**
- **Parked stay parked:** BIRD, C, COST, ENPH, QCOM, SE, WPM, XOM. Re-enable cases checked, none qualifies —
  **C** is three sessions into a 30-day-tradeless park, **QCOM** and **WPM** remain broken downtrends, **SE**'s
  liquidity problem is structural and a print does not fix it, **COST** and **ENPH** still fail
  trending-and-active on their own numbers.

### 📌 WMT — the dead-signal decision, due today: **KEEP**
The 08-11 entry scheduled this for today and it is taken today rather than deferred again. **The answer is
keep, and the reasoning is the log's own precedent rather than a fresh judgement call:**
- **It fails the established bar by ten days.** The only dead-signal park this log has executed is **C (08-10)**,
  and its stated bar was **"30d no trade"**. WMT's last trade is **07-24 = 20 days**. Parking at 20 days would
  silently move a precedent that is three sessions old, and would make the C park retroactively arbitrary.
- **The chart argues the other way, and strongly.** WMT closed **+2.44% Wednesday**, is **above both MAs
  (+3.6% / +1.4%)** and **+3.25% on 5 days** — one of the better 5-day prints on the board. It is nothing like
  the broken-downtrend profile (WPM, QCOM, XOM) or the thin-chop profile that took C out.
- **It is not signal-dead; it is conversion-dead, and the blocker is a known unpriced filter.** WMT produced
  **3 candidates on 08-12** — its most active session of the window — at conf **66.0 and 71.1**, both refused
  on **crossover 0.04 < 0.25**. `MIN_CROSSOVER` is the single largest never-A/B'd filter in the system and is
  explicitly queued for the post-close routine. **Removing the name now would delete a data point from exactly
  the sample that decision needs.**
- **Honest counterweight, recorded not buried:** WMT is **all-time −$47.51 on 6 trades**, its ATR (**2.26%**)
  and $ volume (**$116M/day**) are the thinnest of any enabled single name, and 0.04 crossovers suggest its
  1-min ribbon may simply be too tightly wound for this strategy. **That is a real hypothesis and it now has a
  dated, unambiguous test instead of another deferral.**
- **Test recorded — WMT parks as dead-signal at the 08-24 run if it has taken no trade by then** (30 days from
  07-24, C precedent, first run after the 30-day mark on 08-23).
- **The earnings park is SEPARATE and is not merged, per the 08-12 instruction.** WMT reports **08-20 BMO**, so
  **park it at the 08-19 run** — deliberately the day *before*, not the morning of: this routine runs 11:30 UTC
  = **7:30am ET**, and the release lands **8:00am ET**, so an 08-20 decision would be taken blind to a print
  that is 30 minutes away. **Re-enable condition (earnings): the print and its reaction have cleared.
  Re-enable condition (dead-signal): does not exist — that park is terminal.** Two parks, two clocks.

### ➕ Add applied — PLTR
**Verified on Alpaca immediately before the INSERT: `tradable: true`, `status: active`, `class: us_equity`,
NASDAQ.** The 08-12 entry screened it and handed it here; today's re-screen on fresh bars **confirms the case
and it has not decayed:**
- **Strongest trend of any candidate screened: +21.1% vs 20MA, +27.9% vs 50MA, +7.96% on 5 days.**
- **Liquidity $209.9M/day** — in the same tier as AVGO ($217M), NFLX ($213M) and GOOG ($245M), and far ahead of
  the thinnest incumbents (ABNB $35M, BABA $41M). This is the liquidity the strategy needs.
- **ATR 5.46%** — high, but **below all three outliers already carried** (MU 8.61 / AMD 7.32 / INTC 7.19), so it
  **adds no new class of risk** to the book.
- **Earnings binary RESOLVED and a full quarter away:** Q2 reported **08-04** (revenue +93%, US commercial
  +150%, FY guide raised to $8.154B, +10% on the print); **next report 2026-11-02**. No other candidate offered
  that much clear runway.
- **Sizing fit:** at **$171.09** it quantises far better against $9.1k equity than a $400+ name — the
  whole-share problem the weekly flagged on MU/AVGO/TSM.
- **Two risks recorded up front, neither disqualifying.** ① It fell **−2.20% Wednesday** on profit-taking after
  a **+41.6% two-week run**, and **RSI ~73.6 is overbought** — but the scorer *penalises* RSI > 70, so the
  strategy dampens its own confidence here rather than chasing. ② It is a momentum name in a concentrated AI
  tape; the **5-min gate + IMP-022** are the structural defence and they need no watchlist edit.
- **Alternates verified `tradable: true` / `status: active` and passed over, held for the next add:** **ANET**
  (+16.6%/+21.7%, **+6.36% Wednesday**, $82M/day, ATR 5.46% — the closest runner-up, thinner only on volume),
  **UBER** (+5.0%/+4.6%, +10.60% on 5 days but **−4.06% Wednesday**, $89M/day), **CRM** (+6.9%/+12.1% but flat
  +0.24% on 5 days, $82M/day), **LLY** ($134M/day, trend too shallow at +3.4%/+4.7%).
- **Only ONE name added, deliberately.** At $9.1k equity an extra symbol mostly **displaces** a trade rather
  than adding one (IMP-017), so a second add would dilute the first rather than compound it.
- **⚠️ Note for the post-close routine (IMP-023 coupling):** `bot/replay.py` resolves its universe from
  `dbo.watchlist`, so **every replay from today forward runs 20 symbols, not 19**. Backtest results either side
  of 2026-08-13 are **not directly comparable** — hold the universe fixed when re-pricing `MIN_CROSSOVER`.

### Changes applied to dbo.watchlist
**ONE change, parameterized INSERT, `watchlist` table only:**
- **➕ PLTR — INSERT, `enabled = 1`**, note `added 2026-08-13: +21% vs 20MA/+28% vs 50MA, $210M/d, ATR 5.5%,
  earnings resolved 08-04 (next 11-02)`. Verified tradable+active on `/v2/assets/PLTR` before the write.
- **No parks, no re-enables, no DELETEs.** WMT keeps (above), GOOG/UNH tests are dated 08-17, AMZN's test is
  unmet, AAPL's is dated 08-19.
Post-write assertions re-run against the live table: **20 enabled ≤ 30 ✓**, **QQQ `enabled = 1` ✓** (checked
before *and* after), **8 parked rows all still present ✓**, PLTR row reads back exactly as written ✓.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA GOOG INTC JPM MSFT MU NFLX NVDA **PLTR** QQQ SPY TSLA TSM
UNH WMT. Parked (8): BIRD C COST ENPH QCOM SE WPM XOM. **Service restarted 2026-08-13 11:37:48 UTC and verified
healthy:** `active`, **NRestarts=0**, **warmup primed 20/20**, subscribed to all 20 on the IEX feed, account
ACTIVE $9,089.68 at boot, **no open positions**, banner confirms entry window 10:00–16:00 ET (IMP-017), QQQ
market gate (IMP-022), trail 1.25% → 1.00% (IMP-018/IMP-021), log lines stamped UTC (IMP-026). 🔒 Locked: none
(0 positions). **Upcoming: GOOG + UNH tests 08-17 · AAPL re-examination 08-19 · WMT earnings park 08-19 (reports
08-20 BMO) · WMT dead-signal test 08-24 · NVDA earnings 08-26 · SPY review end-August.**

### Perplexity `sonar` — run 8, thin again, and it mislabelled the clock for the second day running
`sonar` returned **"no specific overnight/pre-market catalyst"** for **17 of 19** tickers and **declined to give
a futures direction at all** ("not explicitly stated"), which is the one thing it was asked for that WebSearch
answered in a sentence (Dow +102, S&P +0.2%, NDX +0.1%). Its only ticker-level leads were the **stale** AAPL
Jefferies downgrade — already logged on **08-11**, now surfaced for the third consecutive run — and AAPL's
**$0.27 dividend payable today**, which is not an intraday catalyst. It then repeated **exactly yesterday's
error class**: it listed **Continuing Jobless Claims "at 8:30 AM ET"** under *market-hours* releases, when
8:30am ET is **pre-open**; a run that took it at face value would have booked an in-session macro event that
does not exist, two days running. It did correctly name PPI + claims as the day's macro axis and flagged
CSCO −5.62% pre-market. **Eighth consecutive weak run. Standing rule unchanged and now well-evidenced:
`sonar` is lead-generation only — never a market-regime source, never a clock, and its silence on a ticker is
not evidence of no catalyst.** WebSearch (futures, PPI/claims consensus, the earnings calendar, WMT's confirmed
08-20 BMO date, PLTR's post-earnings context) + the IEX daily tape carried this run.

---

## 2026-08-14 — Pre-market Research

**NO CHANGES — 20 enabled, unchanged, service NOT restarted.** No dated test comes due today, no enabled
symbol reports today, nothing on the board clears a park bar, and the one add-slot is deliberately left
closed while PLTR (one session old) is measured. Book is **CLEAN & FLAT** — broker-confirmed **0 positions,
0 open orders**, equity **$9,123.87**, all cash → **nothing locked**. The one genuinely new fact this run
produced is a **confirmed earnings date**: **BABA reports 08-20 BMO**, verified against Alibaba Group's own
07 Aug press release, so it joins WMT in a **park at the 08-19 run**.

### Market context
**Futures mixed-to-flat after a record close; the week's macro risk is spent, and today's only in-session
print lands exactly when the bot's entry window opens.** Thursday closed at a **record S&P 500 7,798.99
(+0.65%)**, **Nasdaq Composite 26,803.03 (+0.81%)**, **Dow 53,839.99 (+0.13%)** — the S&P and Nasdaq are on
track for a **third straight up week**, the S&P's first three-week streak since May. Pre-market reads
disagree at the margin (S&P futures ~flat to +0.2%, NDX futures −0.15% to +0.2%, **Dow futures −0.2%**);
call it **flat, not directional**.
- **⚠️ The macro clock matters more than the macro content today.** **8:30am ET: July retail sales
  (+0.2/+0.3% est), core retail sales, import prices — all PRE-OPEN.** **9:15am ET: industrial production —
  PRE-OPEN.** **10:00am ET: U. Michigan preliminary sentiment + June business inventories — these are the
  ONLY in-session releases, and 10:00 ET is the exact minute the IMP-017 blackout lifts.** Unlike the last
  two sessions, the bot's first eligible candle is not comfortably after the day's news; **the first
  entries of the day will be scored off candles printed into a live macro reaction.** Nothing to change in
  the watchlist for it — it is a note for the post-close read, not an edit.
- **No enabled symbol reports today.** Friday's calendar is small-cap and foreign issuers (Cellebrite,
  RLX, Transurban, Sigma Lithium et al.) — **no mega-cap US name on the docket.**
- **Semi read-through is POSITIVE, not a risk.** **AMAT** printed 08-13 AMC and guided FQ4 revenue to
  **$10.25B ±$0.5B vs $9.54B consensus** (low end ~$210M above the Street). The 08-13 entry flagged this as
  the one thing that could move MU/NVDA/AMD/INTC/TSM in this morning's tape; it resolved to the good side,
  and the book carried no overnight exposure to it either way.
- **Pre-market movers are all idiosyncratic and none are enabled:** RDDT **+12%** on **S&P 500 inclusion**
  (mechanical, not trend — screened and rejected below), CAPR +86% (Phase 3 data), IMXI +25% (WU deal
  cleared), INVA −45% (guidance suspended).
- **Backdrop:** Brent ~**$87** and firm — the Strait of Hormuz vessel attacks and an open-ended US naval
  blockade of Iran keep an energy tail-risk live; 10-year yield **~4.69%**, which keeps the tape in the
  negative-correlation regime the 08-12/08-13 entries described.

### Carried from daily review (08-13 "Notes for pre-market research")
- **"✅ MU is again the standout — keep emphatically."** — ✔ kept, no question raised. MU is **+7.5% vs
  20MA** and **+7.76% on 5 days** after a **+4.23%** Thursday. Its **8.16% ATR is again the highest on the
  board** — **seventh consecutive run** recording it as a **sizing** question for the post-close routine,
  **not** a park question.
- **"✅ INTC is the workhorse and the churn risk at once — do NOT read today's −$18 as decay."** — ✔ not
  read as decay and **not acted on**. INTC is **+$47.07 over 6 trades since 08-04**, the best symbol on the
  board, closed **+3.58%** Thursday and is **+8.5% vs its 20MA**. The late-session low-crossover re-entry
  weakness is real but its lever (`MIN_CROSSOVER`) was **tested and refuted last night** — leaving it alone
  is the instruction and it is followed.
- **"✅ TSLA converted beautifully at conf 66.4 while −1.8% below its 20MA — the trend screen is a watchlist
  filter, not a signal."** — ✔ **absorbed as a standing methodology note, and it changes today's reading of
  two names.** TSLA has since crossed **back above its 20MA (+2.7%)**. More importantly this is the reason
  **AMD (−2.1% vs 20MA) and UNH (−4.1%) are not parked on the trend line alone** today.
- **"✅ GOOG is no longer silent — 4 candidates, concern retired."** — ✔ confirmed against journald: **GOOG
  produced 4 no-entry events on 08-13** after five blank sessions. **Its 08-17 test is now half-dead by its
  own terms** (the test requires 0 candidates AND below both MAs); recorded, not rewritten — the test runs
  as written on 08-17.
- **"✅ PLTR produced 6 candidates on day one — liveness confirmed, keep."** — ✔ verified independently
  (6 events, second-most active name on the board). **This is the main reason no second name is added
  today** — see below.
- **"⚠️ Four enabled symbols produced zero candidates: AMZN, BABA, JPM, UNH."** — ✔ checked across the full
  5-session window rather than the single session, and **none is dead**: **BABA 11, JPM 12, UNH 6, AMZN 5**
  candidates in the window, and BABA + AMZN both converted inside the last two weeks (BABA **+$32.82**).
  A one-session blank is not a signal. **AMZN's park test ("converts a near-miss and loses") remains unmet
  for the fifth run — no park, stays on notice.**
- **"AMD entered at crossover 0.257, the lowest on the board, and lost −$10.49 — sizing question, not a
  park; single trade."** — ✔ agreed and not escalated. AMD is 14-day **−$11.07 on 3 trades**.
- **"Book is CLEAN & FLAT into 08-14."** — ✔ **live-verified**: ACTIVE, **0 positions, 0 open orders**,
  equity **$9,123.87**, cash $9,123.87, BP $36,495.48. (The 08-13 review closed at **$9,124.21**; the
  **−$0.34** delta is a settle-side adjustment, not a trade — `last_equity` == `equity` confirms nothing
  moved overnight.)

### Watchlist review
Account **ACTIVE**, **0 open positions = nothing locked.** All 20 incumbents reviewed against overnight news
and 110-day daily bars off the IEX tape (close vs 20/50-day MA, 5-day and 1-day change, ATR%, 20-day avg
$ volume), plus a 5-session signal-liveness audit from journald **dated off journald's own timestamps
(`-o short-iso`)**, per the method gotcha recorded on 08-13.
- **Trend broadened for a second straight session — the healthiest board reading of the month.** Above the
  20MA: **PLTR +24.8%** (leader on day two), **ABNB +18.4%**, **MSFT +11.6%**, INTC +8.5%, NFLX +8.2%,
  NVDA +7.7%, MU +7.5%, AVGO +4.9%, TSM +4.8%, QQQ +4.2%, AMZN +3.7%, WMT +3.3%, SPY +3.1%, TSLA +2.7%,
  JPM +2.7%, BABA +0.6%. Below: **GOOG −0.5%, AMD −2.1%, UNH −4.1%, AAPL −4.5%**. **Only FOUR names are
  below their 20MA (5 on 08-13, 6 on 08-12), and TSLA crossed back above.** Versus the 50MA the laggards
  are **TSLA −8.8%, AMD −5.5%, INTC −4.5%, UNH −3.7%, GOOG −2.4%** — the residual SOX drawdown plus two
  name-specific drifts, none new. **Nothing clears the park bar on trend.**
- **⚠️ Volatility outliers, kept and noted (sixth consecutive run):** **MU 8.16%**, **AMD 7.11%**,
  **INTC 6.74%** ATR, with **PLTR 5.45%** below all three as screened. Unchanged verdict: **sizing**, not
  park.
- **Liquidity floor holds.** Thinnest enabled names on 20-day IEX $ volume: **ABNB $37M**, **BABA $41M**,
  **JPM $77M**, **UNH $93M**, **WMT $114M**. Deepest: SPY $1,125M, MU $976M, NVDA $953M, AAPL $619M,
  MSFT $607M, AMZN $559M. No name has deteriorated into the sub-$35M band that took SE out.
- **Signal-liveness audit, 5 sessions (08-07 → 08-13), 164 no-entry events + 9 conversions:** most active
  **TSM 19, NFLX 18, ABNB 16, JPM 12, BABA 11, INTC 11, AVGO 9, NVDA 9, SPY 9**; mid **QQQ 7, UNH 6,
  PLTR 6, MSFT 5, AAPL 5, AMZN 5, WMT 5**; quietest **TSLA 4, GOOG 4, AMD 2, MU 1** — but **MU converted
  3 of its 4 opportunities and INTC 3 more**, so the two quiet tails are conversion, not silence.
  **Every one of the 20 enabled symbols produced at least one candidate in the window** — the first run
  this month with no zero-candidate name. Refusal split: **crossover floor 84, confidence floor 71, market
  gate 9**, with **51 near-misses at conf ≥ 65 blocked on crossover**. Post-close's file — and it was
  tested and refuted there last night; not re-raised here.
- **14-day P&L (DB; still understates MU by the missing 08-12 **+$4.46** row — IMP-028 fixes the mechanism
  going forward, it does not backfill): 29 closed trades, net +$230.99.** Winners **AVGO +$47.47 (3 tr)**,
  **INTC +$47.07 (6 tr, 5W)**, GOOG +$45.11, BABA +$32.82, TSLA +$29.16, ABNB +$26.21, NVDA +$12.49,
  MU +$11.68, MSFT +$4.50, TSM +$4.04. Losers **AMD −$11.07**, **AMZN −$18.49**. **No enabled symbol has a
  park-worthy record under the current rules.** (All-time, for context, still carries the pre-IMP-021 tail:
  AVGO −$121.38, AMZN −$108.51, AMD −$89.31 — the 08-13 review's standing correction applies, **judge on
  the post-08-03 window**, where AVGO and INTC are the two best names on the board.)
- **Dated tests — none due today, and none pulled forward.** GOOG + UNH **08-17**; AAPL **08-19**; WMT
  earnings park **08-19**; **BABA earnings park 08-19 (NEW, below)**; WMT dead-signal **08-24**; NVDA
  earnings **08-26**; SPY review **end-August**. UNH's clock ticked to **28 days without a trade** (last
  07-17) and AAPL is the weakest chart on the board (**−4.5% vs 20MA**) — **both are already scheduled and
  neither is advanced**, for the same reason the 08-13 entry gave: moving a dated test because the number
  looks bad two days early is exactly the churn this log exists to prevent.
- **Parked stay parked:** BIRD, C, COST, ENPH, QCOM, SE, WPM, XOM. Re-enable cases re-checked, **none
  qualifies** — C is four sessions into a 30-day-tradeless park, QCOM and WPM remain broken downtrends, SE's
  liquidity deficit is structural, COST and ENPH still fail trending-and-active on their own numbers.

### 🔔 NEW — BABA reports 08-20 BMO (confirmed at the source): park it at the 08-19 run
`sonar` said nothing about BABA. The routine's own earnings sweep caught it, and it was **verified against
Alibaba Group's investor-relations press release dated 07 Aug 2026**, not a data aggregator: **results for
the quarter ended 30 June 2026 will be released BEFORE the U.S. market opens on Thursday, 20 August 2026**,
with the call at **7:30am ET**. (Two aggregators disagreed — Wall Street Horizon said 08-20 "confirmed",
TipRanks estimated 08-28 — which is precisely why the company filing was the tiebreaker.)
- **Action is dated, not taken today.** The print is **four sessions out**. BABA is currently a healthy
  member of the board (11 candidates in the window, **+$32.82 over 2 winning trades in 14 days**), and
  removing a live symbol four days early costs trades for no risk reduction.
- **Park at the 08-19 run, deliberately the day BEFORE**, on the identical reasoning the 08-13 entry
  recorded for WMT: this routine runs **11:30 UTC = 7:30am ET**, and the release lands at/just before
  **8:00am ET**, so an 08-20 decision would be taken **blind to a print 30 minutes away**.
- **08-19 is now a two-name park run: WMT (reports 08-20 BMO) and BABA (reports 08-20 BMO).** That drops
  the board to **18 enabled** for 08-20 — worth knowing in advance, because it is also the day the AAPL
  re-examination falls due, and three edits in one run is the churn profile the weekly review penalises.
  **Re-enable condition for both: the print and its first-session reaction have cleared.**
- **BABA's ADR earnings gap risk is the specific hazard here** — the 5-min gate does not protect against an
  8:00am ET headline that re-prices the name before the 10:00 ET entry window even opens.

### ➕ Adds — none, and the slot is being held on purpose
Capacity is **20 of 30**, so this is a choice, not a constraint. Alternates were re-screened on fresh bars
so the next add decision starts from current numbers, and **RDDT was screened out on its own tape**:
- **CRM** — **+10.5% vs 20MA / +16.8% vs 50MA, +7.79% on 5 days, +4.15% Thursday**, $86M/day, ATR 4.29%.
  **It has improved materially since 08-13** (it was "flat +0.24% on 5 days" then) and is **now the leading
  alternate**, ahead of ANET.
- **ANET** — +11.8% / +17.4%, $82M/day, ATR 5.65%, but **−3.22% Thursday** after leading the prior day;
  still strong, momentum less clean than CRM's this week.
- **UBER** — +5.6% / +5.1%, $86M/day, ATR 3.47%; steady, shallower trend.
- **LLY** — +2.3% / +3.6%, $131M/day; **trend too shallow**, unchanged verdict.
- **RDDT — screened and REJECTED despite being today's headline mover.** It is **below both MAs (−4.7% /
  −9.6%)**, thinnest of the set at **$46M/day**, ATR **6.97%**, and this morning's **+12%** is **S&P 500
  index-inclusion mechanics** — a one-off flow event, not the sustained intraday trend the ribbon needs.
  Buying a name into an inclusion pop is the opposite of this strategy.
**Why nothing was added (three independent reasons, any one sufficient):** ① **PLTR is one session old** —
6 candidates, 0 conversions — and a second add would contaminate exactly the measurement that decides
whether the last add worked. ② **IMP-023 couples `bot/replay.py`'s universe to `dbo.watchlist`**, so a
second universe change in two days would leave **three consecutive non-comparable backtest baselines** for
the post-close routine. ③ At **$9.1k equity an extra symbol displaces a trade rather than adding one**
(IMP-017) — and the board just produced its first zero-silent-name session, i.e. it is **not short of
candidates**, it is short of conversions.

### Changes applied to dbo.watchlist
**NONE. No INSERT, no UPDATE, no DELETE — the `watchlist` table was read only.** No park qualified, no
dated test came due, no re-enable case cleared, and the add slot was held deliberately. Assertions re-run
against the live table after the review: **20 enabled ≤ 30 ✓**, **QQQ `enabled = 1` ✓** (load-bearing twice
over — diversifier *and* the IMP-022 market-regime proxy), **8 parked rows all still present ✓**,
**PLTR row intact and enabled ✓**.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA GOOG INTC JPM MSFT MU NFLX NVDA PLTR QQQ SPY TSLA TSM
UNH WMT. Parked (8): BIRD C COST ENPH QCOM SE WPM XOM. **Service NOT restarted — correctly, because nothing
changed.** It has been `active` since **2026-08-13 11:37:48 UTC** with **NRestarts=0**, **zero WARNING or
ERROR records** since, and its ribbons are **live-built through yesterday's full session** rather than
warmup-seeded — a better state than a fresh restart would leave it in. Verified normal: the journal is
silent from **08-13 20:59 UTC** to now, which matches the pre-restart overnight gap on 08-12→08-13 (IEX
prints no ticks on these names at 07:30 ET). 🔒 Locked: **none (0 positions)**. **Upcoming: GOOG + UNH
tests 08-17 · AAPL re-examination 08-19 · WMT earnings park 08-19 · BABA earnings park 08-19 (NEW) · WMT
dead-signal test 08-24 · NVDA earnings 08-26 · SPY review end-August.**

### Perplexity `sonar` — run 9, weakest yet, and it repeated the clock error for a THIRD consecutive day
`sonar` returned **"no overnight/pre-market catalyst found"** for **18 of 20** tickers, **declined to give a
futures direction at all** for the third run running ("not stated in the provided results"), and its only
two ticker-level offerings were both defective: the **AAPL Jefferies downgrade**, now surfaced for the
**fourth consecutive run** and first logged **08-11**, and an **AAPL FQ3 earnings/guidance item that is
weeks stale**. Its "biggest pre-market movers" were **NVDA +0.35%, AAPL −0.03%, MSFT −0.22%** — a screenshot
of a quote table, not movers, while the actual movers (RDDT +12%, CAPR +86%, INVA −45%) went unmentioned.
**Third consecutive clock error:** it filed **8:30am ET July retail sales** under *"releases DURING US
market hours"*. A run that trusted it would have booked a non-existent in-session event three days running —
**and would simultaneously have missed the one real in-session item, the 10:00am ET U. Michigan print that
lands on the entry-window open.** It also said nothing about **BABA's confirmed 08-20 earnings**, the single
most consequential fact found today. **Standing rule reaffirmed and now overwhelming: `sonar` is
lead-generation only — never a regime source, never a clock, and its silence on a ticker is not evidence of
no catalyst.** WebSearch (futures, the macro calendar with times, the earnings calendar, AMAT's guide,
pre-market movers, Alibaba's IR release) + the IEX daily tape + journald carried this run.

---

## 2026-08-17 — Pre-market Research

**The UNH dated test came due and it fired: 31 days without a trade AND below both MAs → PARKED. The GOOG
test came due the same day and did NOT fire — its 08-13 candidates killed the zero-candidate leg, so GOOG
keeps and gets a fresh 30-day clock.** Book is CLEAN & FLAT (broker-confirmed **0 positions, 0 open
orders**, equity **$9,123.87**, `last_equity == equity`) → **nothing locked**. **One change; 20 → 19
enabled**; service restarted clean (warmup 19/19).

### Market context
- **Quiet, mixed open into the biggest retail-earnings week of the quarter.** Benzinga's 10:02 UTC wrap:
  **Dow futures slip, S&P 500 futures rise, September Fed-hike odds down to ~30%.** No source gave a clean
  numeric futures print this morning; the honest read is **mixed-to-flat, no directional edge**, which is
  also what the IEX tape says — the last prints on SPY (776.03) and QQQ (731.01) are within **0.03%** of
  Friday's closes.
- **⚠️ The one in-session clock item: NAHB Housing Market Index at 10:00am ET — it lands exactly on the
  IMP-017 entry-window open.** Empire State Manufacturing is **8:30am ET, i.e. PRE-open** (sonar filed it
  as "during market hours" again — see below). The week's real macro is **Wednesday: FOMC minutes 2:00pm
  ET**, plus housing starts, jobless claims, Philly Fed and prelim August PMIs later in the week.
- **Earnings this week are retail and none of them are on the board until Thursday:** **HD Tue 08-18 BMO**,
  **TGT + LOW + TJX + ADI Wed 08-19**, **WMT Thu 08-20 BMO (enabled — park 08-19)**, **BABA Thu 08-20 BMO
  (enabled — park 08-19)**, ROST/DE Thu, BJ Fri. **Nothing on the watchlist reports today or tomorrow.**
  **WMT's 08-20 date is now independently confirmed** against the week-ahead calendars (CNBC/Kiplinger/
  Yahoo), not just carried forward from the 08-13 entry.
- **Oil is the live two-sided tail and it moved twice in 90 minutes this morning:** an **agreement to
  extend the US-Iran 60-day ceasefire** (Al Arabiya, 10:51 UTC) against a **circulating report that Trump
  said he will bomb** Iranian targets (11:20 UTC), on top of a WSJ piece that Iranian hardliners used the
  post-MoU window to plan expanding the war. Brent closed Thursday ~**$87**. This is headline whipsaw, not
  trend — and it is the reason the XOM re-enable case below is *held*, not taken.
- **Backdrop from Friday:** July **retail sales −0.6%**, the worst in over a year, plus a weak UMich print
  sapped the afternoon; the S&P still printed a record **7,798.99** close on Thursday. The divergence the
  weekly review flagged still holds — **index gains are coming from gaps and overnight drift, not from
  intraday trend**, which is the only thing this bot can monetise.

### Carried from daily review (08-14 "Notes for pre-market research")
- **"AMD is the standout and the lesson at once… keep it emphatically enabled."** — ✔ kept, no question
  raised. AMD closed **+6.50% Friday at the high**, is **+4.08% vs its 20MA** and back **above its 50MA
  (+0.78%)** for the first time in weeks, and produced **6 of Friday's 25 candidates**. Its **6.37% ATR** is
  logged for the seventh consecutive run as a **sizing/exit** question — and 08-14's review made that
  concrete (a flat 1.00% trail on a 6-7% ATR name is ~1/7th of a daily range). **IMP-029 is the post-close
  routine's file, not this one.** No action.
- **"Zero trades Friday was correct — do not respond by loosening the watchlist or adding names."** — ✔
  honored literally. **No add was made today**, and the one edit that *was* made is a park that was written
  and dated five sessions ago, not a reaction to Friday.
- **"Silent Friday (11): AMZN, ABNB, AVGO, GOOG, INTC, MU, NVDA, PLTR, QQQ, SPY, TSM — read as flat-tape
  artifact, not symbol death. In particular do not park MU or INTC."** — ✔ obeyed, and verified rather than
  assumed: across the **full 5-session window (08-10 → 08-14) every one of the 20 enabled symbols produced
  at least one candidate** (141 events). MU and INTC are the two best names on the board and were not
  considered for park. The standing 5-session rule was applied to every park question today.
- **"AMZN's park test remains unmet for a sixth run."** — ✔ still unmet, **seventh run**. AMZN needs to
  convert a near-miss and lose; it produced 4 candidates on 08-10 and none since, which advances the test
  in neither direction. **Stays on notice, no park.**
- **"BABA 08-20 BMO and WMT 08-20 BMO — both due to park at the 08-19 run. NVDA 08-26. Nothing reports
  Monday."** — ✔ all four re-verified this morning against the week-ahead calendars; **nothing reports
  today**, and both 08-19 parks stand.
- **"Book is CLEAN & FLAT into 08-17."** — ✔ **live-verified**: ACTIVE, **0 positions, 0 open orders**,
  equity **$9,123.87**, cash $9,123.87, BP $36,495.48, `last_equity == equity` to the cent. `dbo.trades`
  has **zero rows since 08-13**. Nothing locked, so no symbol was protected from review today.
- **Ops item from the weekly ("confirm the pre-market restart step is actually firing")** — ✔ **it fired
  today and is verified by timestamp**: `ActiveEnterTimestamp` **2026-08-17 11:36:32 UTC**, new
  MainPID 1071551, and the startup banner lists **19** symbols with UNH absent. The 08-14 non-restart was
  correct (nothing changed that morning), so there was no defect to fix — but the check is now done the way
  this project's memory demands, against the timestamp rather than against the log text.

### Watchlist review
Account **ACTIVE**, **0 open positions = nothing locked.** All 20 incumbents reviewed against overnight
news (Alpaca news tape since Friday 20:00 UTC + WebSearch) and **110 daily bars** off the Alpaca tape —
close vs 20/50-day MA, 1-day and 5-day change, ATR%, 20-day average $ volume — plus a 5-session
signal-liveness audit from journald dated off journald's own timestamps.
- **⚠️ Methodology note for whoever reads the $-volume numbers next: they are NOT comparable to previous
  entries in this log.** Earlier runs pulled bars with `feed=iex` and quoted the IEX subset (ABNB "$37M");
  this run pulled the **consolidated** tape (ABNB **$819M**). **The ordering is identical and that is what
  the liquidity floor is judged on** — but do not read a 20x jump as a liquidity improvement. Thinnest
  enabled names, consolidated: **ABNB $819M**, BABA $1,144M, JPM $2,338M, WMT $2,405M, NFLX $2,776M.
  Deepest: MU $37.0B, SPY $35.4B, QQQ $27.6B, NVDA $25.4B, MSFT $17.1B, AAPL $16.8B. **No name is anywhere
  near the band that took SE out.**
- **Trend held its breadth over the weekend.** Above the 20MA: **PLTR +19.6%**, **ABNB +16.3%**,
  **MSFT +10.0%**, MU +9.2%, NFLX +7.4%, NVDA +7.0%, INTC +5.9%, AMD +4.1%, TSLA +4.0%, QQQ +3.8%,
  TSM +3.5%, WMT +2.8%, SPY +2.7%, AMZN +2.4%, JPM +2.3%, BABA +1.6%. Below: **GOOG −0.55%, AVGO −1.63%,
  AAPL −3.93%** (and UNH −3.20%, parked below). **Three enabled names below their 20MA, down from four.**
  Versus the 50MA the laggards are **TSLA −7.8%, INTC −6.3%, GOOG −2.5%, AAPL −1.1%**. **Nothing new
  clears the park bar on trend.**
- **⚠️ Volatility outliers, kept and noted (seventh consecutive run):** **MU 7.72%**, **INTC 6.68%**,
  **AMD 6.37%**, **PLTR 5.52%**. Unchanged verdict: **sizing and exit, not park** — and 08-14's review
  turned that from an assertion into a measured number.
- **🔔 AVGO — the one name with a genuine live negative headline, and it is a KEEP on notice, not a park.**
  Friday's **−5.94%** (**−8.13% on 5 days**) was **not** an earnings event: it was **active in-the-wild
  exploitation of a critical VMware vCenter flaw (CVE-2026-59310, disclosed 07-29)**, with compromised
  systems traced to 361 IPs across 47 countries, layered on pre-earnings profit-taking. **Next print is
  09-02 AMC (confirmed) — outside every window this routine cares about.** It is still **+0.65% vs its
  50MA**, **$7.2B/day**, produced **8 candidates** in the window, and is **+$43.75 over 2 trades** in the
  14-day book. **The 5-min gate is the right instrument for a name whose chart just broke — it simply
  will not open a long until the 21/34/55 stack is rebuilt.** Park bar not met; **on notice, re-check 08-19.**
- **Signal-liveness audit, 5 sessions (08-10 → 08-14), 141 no-entry events + 12 conversions:** most active
  **JPM 16, TSM 15, NFLX 12, ABNB 12, INTC 9, WMT 8, AMD 8, AVGO 8**; mid **QQQ 6, SPY 6, NVDA 6, MSFT 6,
  PLTR 6**; quietest **TSLA 4, UNH 4, AMZN 4, GOOG 4, BABA 3, AAPL 3, MU 1**. **Zero symbols with zero
  candidates — the second consecutive window with no silent name.** Refusal split: **crossover floor 71,
  confidence floor 63, market gate 7 (5.0%)** — the gate is nowhere near the >80% tripwire the weekly
  formally retired. **MU converted 1-of-1 and INTC 3 more, so the quiet tails are conversion, not silence.**
- **14-day P&L (`dbo.trades`, closed since 08-03): 25 trades, net +$170.13.** Winners **INTC +$47.07 (6 tr,
  5W)**, **AVGO +$43.75**, TSLA +$29.16, ABNB +$26.21, NVDA +$12.49, MU +$11.68, BABA +$9.30, MSFT +$4.50,
  TSM +$4.04, AMD +$0.42. Only loser **AMZN −$18.49**. **No enabled symbol has a park-worthy record under
  the current rules.** (All-time still carries the pre-IMP-021 tail — AVGO −$121.38, AMZN −$108.51,
  AMD −$89.31 — and the standing correction applies: **judge on the post-08-03 window.**)
- **Parked stay parked (8 → 9).** BIRD, C, COST, ENPH, QCOM, SE, WPM, XOM re-checked on fresh bars.
  **SE is now the awkward one and it still does not qualify**: +9.3% vs 20MA / **+19.3% vs 50MA**, +7.5% on
  5 days — a genuinely good chart — but at **$567M/day it is the thinnest name in the entire screen**, and
  its park reason was *structural liquidity*, which a good fortnight does not repeal. C is nine sessions
  into a 30-day-tradeless park; QCOM is still **−9.8% vs its 50MA**; WPM ($225M) and ENPH ($181M) fail the
  liquidity floor outright; COST is +1.4%/+1.1% with a **1.90% ATR** — the definition of the flat,
  intertwined ribbon the strategy scores near zero.

### 🔴 Dated test #1 — UNH: BOTH legs met → PARKED (the one change today)
The 08-12 entry wrote the test in advance, deliberately, while UNH was still all-time positive: *"park UNH
if it has taken no trade by then AND is still below both MAs."* Both legs are met, unambiguously:
- **No trade since 2026-07-17 — 31 days.** `dbo.trades` confirms; nothing since.
- **Below both MAs: −3.20% vs the 20MA, −3.24% vs the 50MA.**
- Corroborating, though not part of the test: **$395–$415 range-bound all month** on outside coverage —
  consolidation after the 07-16 Q2 beat, not a broken chart. **A range that tight is precisely what a
  1-min EMA ribbon cannot monetise**, and it explains the 31-day silence better than the MA test does.
  4 candidates in the window, none converted.
- **It is also the exact C precedent applied consistently:** C was parked 08-10 at 31 days tradeless.
  UNH is 31 days tradeless. Applying the same rule to a name that happens to be **all-time positive
  (+$19.38, 4W/7)** is the point of writing the test down five days early — **it removes the discretion
  that would otherwise spare it.**
- **Not a judgement on UNH the company** (Q2 beat, raised FY guidance, consensus Buy). It is a judgement
  that a consolidating 2.62%-ATR insurer is not what a multi-timeframe momentum ribbon is for.
- **Re-enable condition, recorded now so it is not invented later:** UNH returns when it is **above its
  20MA** *and* has broken out of the $395–415 range. No calendar date — this one is condition-gated.

### ✅ Dated test #2 — GOOG: NOT met, keeps, and the clock is reset rather than quietly dropped
The test set on 08-12 was: *"if GOOG is still below both MAs with 0 candidates at the 08-17 run, it parks."*
- **Leg 1 met:** below both MAs (**−0.55% / −2.49%**).
- **Leg 2 NOT met:** GOOG produced **4 candidates on 08-13**, so the window is not zero. The 08-14 entry
  called this test "half-dead by its own terms" and chose to run it as written rather than rewrite it.
  **Run as written, it fails to fire. GOOG keeps.** This is the correct outcome even though the *concern*
  (no trade since 07-31, 17 days) is still live — a test that is met on one leg is not met.
- **What replaces it, so the concern does not evaporate:** GOOG gets the **same 30-day dead-signal clock
  that C and UNH got**. Last trade 07-31 → **30-day mark falls 08-31 (Monday, a trading day)**.
  **Test recorded: at the 08-31 run, park GOOG if it has still taken no trade AND is still below both MAs.**
- Overnight news is mildly *positive* and does not change the read: **Waymo cleared for robotaxi expansion
  across the Bay Area and LA**, and Stripe is reported near a $7B+ OpenRouter deal. The drift is capex and
  antitrust sentiment, already logged, not an event.

### ➕ Adds — none, and this time the reason is measurement, not caution
Capacity is **19 of 30**, so once again this is a choice. Alternates were re-screened on fresh bars and
**both leading candidates were verified tradable+active on `/v2/assets` this morning** so the 08-19 run can
act without re-doing the work:
- **CRM — still the leading alternate. `/v2/assets`: tradable ✓ active ✓ (NYSE).** +6.9% vs 20MA / **+13.7%
  vs 50MA**, $2.29B/day, ATR 4.31%; −2.56% Friday in the broad tech fade. **Next earnings ~early September
  — clear of this week.**
- **ANET — second. tradable ✓ active ✓.** +8.2% / +14.3%, $1.44B/day, ATR 5.76%, **+5.38% on 5 days**;
  momentum has caught back up with CRM's this week. Reported 08-05, so its binary is behind it.
- **NOW** (+9.3% / +15.2%, $2.78B/day) and **ORCL** (+11.4% vs 20MA but **−1.2% vs the 50MA** — a bounce
  inside a broken trend, rejected) screened for completeness. **UBER** +5.4%/+5.1% steady but shallow;
  **LLY** −0.2% vs 20MA, still too flat; **RDDT** has fixed itself since Friday (+12.6% Friday, now above
  both MAs) but that move is still **S&P-inclusion mechanics** — rejected again, for the same reason.
- **MRVL / LRCX** screen well on trend but sit **below their 50MAs** (−6.8%, −1.5%) with 7%+ ATRs; **AMAT
  is −3.3% / −9.3% after a −5.12% Friday** — the semi complex already has five representatives on this
  board and does not need a sixth from the weak end.
**Why nothing was added (the honest reason, not a boilerplate one):** today already spends this week's one
allowable universe change on the UNH park. **IMP-023 couples `bot/replay.py`'s universe to `dbo.watchlist`,
and the weekly review's single most important task this week is the `<0.5%`-MFE study, which needs ≥3
agreeing replay windows.** A park of a symbol that took **0 trades in 31 days and produced 4 of 141
candidates** is very close to a null edit for that study; **adding an active new name is not** — it would
inject fresh trades into the very windows the study has to compare. Secondary: **PLTR is still only two
sessions old with 6 candidates and 0 conversions**, and at **$9.1k equity an extra symbol displaces a trade
rather than adding one** (IMP-017). The board is not short of candidates — 141 in five sessions with no
silent name — it is short of *conversions*, which no add fixes.

### Changes applied to dbo.watchlist
- **➖ UNH — `UPDATE dbo.watchlist SET enabled = 0`**, note `parked 2026-08-17: dated test met - 31d no
  trade (last 07-17) AND below 20MA -3.2%/50MA -3.2%; 395-415 chop`. Parameterized UPDATE, **row kept, not
  deleted.**
- **No adds, no re-enables, no DELETEs. `watchlist` was the only table touched.**
Post-write assertions re-run against the live table: **19 enabled ≤ 30 ✓**, **QQQ `enabled = 1` ✓**
(load-bearing twice over — diversifier *and* the IMP-022 market-gate proxy), **28 rows still present, none
deleted ✓**, **9 parked rows ✓**, **UNH row intact with `enabled = 0` ✓**.

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA GOOG INTC JPM MSFT MU NFLX NVDA PLTR QQQ SPY TSLA TSM
WMT. Parked (9): BIRD C COST ENPH QCOM SE UNH WPM XOM. **Service RESTARTED and verified by timestamp, not
by log text:** `ActiveEnterTimestamp` **2026-08-17 11:36:32 UTC**, new **MainPID 1071551**, `is-active`
→ `active`, schema ensured, Alpaca ACTIVE $9,123.87, **no open positions**, **warmup primed 19/19**, IEX
stream subscribed to exactly the 19 — **UNH absent from the subscription list, which is the real proof the
edit loaded.** Zero warnings, zero errors. Banner confirms the live config: entry window 10:00–16:00 ET
(IMP-017), QQQ market gate (IMP-022), trail 1.25% → 1.00% (IMP-018/021), UTC timestamps (IMP-026).
🔒 Locked: **none (0 positions)**.
**Upcoming: WMT + BABA earnings parks 08-19 · AAPL re-examination 08-19 · AVGO on-notice re-check 08-19 ·
NVDA earnings 08-26 · GOOG dead-signal test 08-31 (NEW) · SPY review end-August · UNH re-enable is
condition-gated (above 20MA + out of the 395-415 range), not dated.**
**⚠️ Heads-up for 08-19: it is now a three-decision run (WMT park, BABA park, AAPL re-exam) that drops the
board to 17.** CRM and XOM are the two backfill candidates and both are pre-verified — **CRM on
`/v2/assets` this morning, XOM already holds a parked row** (+2.9% vs 20MA / **+8.5% vs 50MA**, $2.17B/day,
its 06-15 "broken downtrend, oil at a 3-month low" park reason now fully reversed). **XOM is held rather
than re-enabled today for one specific reason: this morning's ceasefire-extension headline and the
"will bomb" report moved oil in both directions inside 30 minutes.** A name being repriced by geopolitical
headlines produces gaps, not the sustained intraday trend the ribbon needs. **Re-enable XOM only if the
oil headline regime quiets down.**

### Perplexity `sonar` — run 10, and it made the identical clock error for a FOURTH consecutive day
`sonar` returned **"no specific overnight/pre-market catalyst was surfaced"** for **18 of 20** tickers,
**declined to give a futures direction for the fourth run running** ("not fully verifiable from the
available results"), and its only two ticker items were **quote-table rows presented as movers** (NVDA
+0.50%, GOOG +0.78%) — while the actual overnight tape carried the **Iran ceasefire extension**, the
**AVGO VMware exploitation story**, **Alibaba's $1.5B gaming divestiture**, and **Waymo's California
approval**, none of which it mentioned. **Fourth consecutive clock error:** it filed the **8:30am ET Empire
State** print under *"releases DURING US market hours"*. It did, to its credit, surface the **10:00am ET
NAHB** print, which is the one item that genuinely lands inside the session — **but a run that trusted it
wholesale would again have booked a non-existent in-session event.** **Standing rule reaffirmed for the
fourth week: `sonar` is lead-generation only — never a regime source, never a clock, and its silence on a
ticker is not evidence of no catalyst.** The Alpaca news tape (50 headlines since Friday's close), WebSearch
(week-ahead earnings calendar, AVGO's VMware CVE and 09-02 date, UNH's August range), the daily bars and
journald carried this run.

---

## 2026-08-18 — Pre-market Research

**No changes — 19 enabled. Today is the session *before* a three-decision run, on a tape that is the wrong
one to add momentum into.** Book is CLEAN & FLAT (broker-confirmed **0 positions**, 0 open orders, equity
**$9,089.13**, `last_equity` == `equity` → no overnight marks) → **nothing locked**. No enabled symbol
reports today, none carries a negative binary in the news tape, and every scheduled test on the calendar
falls on **08-19 or later**.

### Market context
**Risk-off into the open, led by exactly the part of this board that is heaviest.** S&P 500 futures
**−0.5%**, Nasdaq-100 futures **−1.2%** — verified on CNBC/Yahoo, *not* taken from `sonar`. The drag is
**memory/storage semis**: WDC **−6%**, SanDisk **−6%**, Marvell **−5%**, Seagate **−5%**. Dow futures are
*up* 7 points on **Home Depot's Q2 beat** (+1%) — a two-sided tape, not a broad rout.
- **Rates and oil are the driver.** 30-year Treasury **5.329%**, near a two-decade high; **Brent $90** after
  Trump **rejected extending the Iran ceasefire** ("doesn't see the war ending anytime soon"). Monday closed
  Dow −0.5%, S&P −0.5%, Nasdaq −0.3%. Asia was heavy: **Nikkei −2.54%**, Kospi −1.55%; Stoxx 600 −0.51%.
- **In-session events today: none for this board.** Today's reporters are **Home Depot (BMO), Keysight,
  Jack Henry** — none enabled here. Housing Starts / Building Permits / Import Prices all print **08:30 ET,
  before the open**. **FOMC minutes are Wednesday 14:00 ET** — the week's one genuine in-session event, and
  it lands tomorrow, not today.
- **Earnings dates confirmed for the scheduled parks: WMT Thu 08-20 BMO and BABA Thu 08-20 BMO** (Target,
  Lowe's, TJX, ADI Wednesday; Deere, Ross Thursday). **The 08-19 park date is correct and does not need
  pulling forward** — both names are two sessions clear of their print today.

### Carried from daily review (08-17)
- **INTC and MU kept, exactly as instructed.** The review's finding was that both losses were *mistimed
  entries into working names* (bought within 0.6% of the session high), not bad symbols. Today's bars agree:
  **INTC 6.31% ATR, +6.5% vs its 20MA, $11.5B/day; MU 7.09% ATR, +12.8% vs 20MA, $37.1B/day, +17.5% on 5
  days.** They are also the **top two earners all-time (MU +$189.55, INTC +$150.78)**. No action.
- **QQQ kept** — load-bearing twice over (diversifier *and* the IMP-022 market-gate proxy).
- **BABA's dead-signal drift noted, but no clock started** — it is being parked for earnings tomorrow, so a
  staleness clock this week would be measuring a symbol that will not be trading. Start it post-print.
- **`sonar`'s standing demotion re-applied** — see the closing section.

### Watchlist review (19 enabled, fresh IEX daily bars)
- **No park candidate exists on the data today.** The liquidity floor is comfortably held by every name —
  thinnest is **ABNB at $832M/day**, next **PLTR $7.07B** — nothing near the $181–225M level that parked
  ENPH/WPM. No sub-$5 names, no halts, and **33 Alpaca headlines since Monday's close contain zero
  company-specific shocks** for this board (all sector commentary, AI-bubble opinion pieces, and read-throughs).
- **Below both MAs, and both already carry pre-written dated tests: AAPL (−3.71% / −1.13%, 22 days
  tradeless) and GOOG (−1.01% / −2.93%, 18 days tradeless).** AAPL's re-examination is booked for **08-19**,
  GOOG's 30-day dead-signal test for **08-31**. **Neither is fired early.** The entire value of writing a
  test days in advance — the point the UNH park proved on 08-17 — is destroyed if the routine also parks on
  a hunch the day before the test falls due.
- **AVGO** (−1.94% vs 20MA / +0.64% vs 50MA, **−7.10% on 5 days**, $7.34B/day) is still the weakest chart on
  the board and its **on-notice re-check is 08-19**. It is also **+$43.75 over 2 trades** in the current-config
  window, and the 5-min gate refuses to open a long on a broken stack by construction. Held to its date.
- **🟠 SPY is the honest anomaly, and it is flagged rather than parked: 53 days without a trade (last
  06-26), a 1.02% ATR — the lowest on the board by a wide margin — and −$11.24 all-time on 4 trades.** That
  is **22 days past** the 30-day mark that parked C and UNH. **It does not park today because the standing
  rule has two legs and the second fails: SPY is +1.97% vs its 20MA and +3.13% vs its 50MA.** A rule that
  binds only when convenient is not a rule. Its review is already booked for **end-August**; if the silence
  persists it should be parked then on an explicit **volatility/dead-signal** test, not by quietly bending
  the MA leg to reach a predetermined answer.
- **⚠️ Semi concentration is today's real exposure, and it is a note rather than an action: 6 of 19 enabled
  names are semis** (AMD, AVGO, INTC, MU, NVDA, TSM) on the morning the semi complex leads the tape lower,
  with **MU the direct read-across** to the WDC/SanDisk/Seagate memory selloff. The correct response is *not*
  to pre-emptively park them — the 5-min 21/34/55 gate and the IMP-022 QQQ filter both refuse longs on a
  down tape without any help from the watchlist. It is to **expect a quiet session and judge the day on
  refusals, not on trade count.**
- **Recent P&L (`dbo.trades`, since 08-04 — the last 10 sessions): 24 trades, 14 wins (58%), net
  +$136.76.** Across the full post-08-03 current-config window (27 trades, **+$135.47**): leaders **AVGO
  +$43.75, TSLA +$29.16, ABNB +$26.21, INTC +$24.74**, NVDA +$12.49, BABA +$9.30; MU −$0.65 and the only
  material laggard **AMZN −$18.49 on a single trade**. **No enabled symbol has a park-worthy record under
  the current rules.** (All-time still carries the pre-IMP-021 tail — judge on the post-08-03 window.)
- **PLTR is 5 days old with 0 trades** — noted, not judged; it needs a fair window. It screens best on the
  entire board (+17.1% vs 20MA / **+27.2% vs 50MA**, 5.16% ATR, $7.07B/day).
- **Parked (9) re-checked on fresh bars, all stay parked. XOM is the live one, and today it fails its own
  re-enable condition explicitly.** Its chart has fully repaired (+3.3% vs 20MA / **+9.3% vs 50MA**,
  $2.19B/day, ATR 2.41%), but the 08-17 condition was *"re-enable XOM only if the oil headline regime quiets
  down"* — and overnight **Brent went to $90 on a presidential refusal to extend the ceasefire**, with Kpler
  reporting weakening Strait of Hormuz traffic. **That is a louder headline regime than yesterday's, not a
  quieter one. Condition not met; XOM stays parked** and stays a pre-verified backfill. C (39d tradeless),
  COST (41d), QCOM, SE, WPM, ENPH, BIRD and UNH are unchanged.

### ➕ Adds — none, deliberately
Capacity is **19 of 30**, so this is a choice. Three independent reasons point the same way:
1. **Timing.** Adding a momentum name on a **−1.2% Nasdaq-futures, semi-led** morning buys the top of the
   exact cohort being sold. Both pre-verified alternates screen well *because* they have already run —
   **CRM** (+3.6% / +10.7%, $2.31B/day, ATR 4.25%, but **−2.67% Monday**) and **ANET** (+8.9% / +15.6%,
   $1.45B/day, ATR 5.41%, **+5.37% on 5 days**). Neither improves by being bought into a risk-off open.
2. **The board shrinks on schedule tomorrow and the backfills are already chosen.** 08-19 removes WMT and
   BABA (earnings) and re-examines AAPL — a drop to **17, possibly 16**. **CRM and ANET stay verified and
   unused until then**; that is when a backfill is actually needed, and it is a better entry point.
3. **Universe stability for Friday's study.** IMP-023 couples `bot/replay.py`'s universe to `dbo.watchlist`,
   and the weekly's single named task is the `<0.5%`-MFE discriminator, which needs ≥3 agreeing windows.
   **A null edit keeps those windows comparable; injecting an active new symbol does not.**
Screened and rejected on fresh bars: **NOW** (−5.08% Monday, **−7.64% on 5 days** — a falling knife),
**ORCL** (+7.5% vs 20MA but **−2.6% vs the 50MA**, a bounce inside a broken trend — rejected a second time),
**BKNG** (−3.44% Monday), **UBER** (−3.90% on 5 days), **LLY** (−0.06% vs 20MA, still flat), **CAT**
(+2.93% Monday but **−3.26% vs its 50MA**), **GE** (+2.0% / +3.4% but only **2.45% ATR** on $1.23B/day —
too quiet to be worth a slot).

### Changes applied to dbo.watchlist
**NONE. No adds, no parks, no re-enables, no DELETEs — the table was read, never written.** Re-verified
against the live table after the review: **19 enabled ≤ 30 ✓**, **28 rows present ✓**, **9 parked ✓**,
**QQQ `enabled = 1` ✓**. `watchlist` was the only table touched, and only by `SELECT`.

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMZN AVGO BABA GOOG INTC JPM MSFT MU NFLX NVDA PLTR QQQ SPY TSLA TSM
WMT. Parked (9): BIRD C COST ENPH QCOM SE UNH WPM XOM.
**Service NOT restarted — correctly, and verified rather than assumed.** With no watchlist edit there is
nothing to reload, and the running process already carries this exact list: `is-active` → **active**,
**MainPID 1124645**, `ActiveEnterTimestamp` **2026-08-17 20:19:20 UTC** (the IMP-029 deploy restart),
journald confirms the banner **"Watchlist (dbo.watchlist): …"** with all 19, **warmup primed 19/19**, IEX
stream subscribed to exactly those 19, **NRestarts=0**, zero errors since.
🔒 Locked: **none (0 positions)**.
**Upcoming: WMT + BABA earnings parks 08-19 (both confirmed Thu 08-20 BMO) · AAPL re-examination 08-19 ·
AVGO on-notice re-check 08-19 · NVDA earnings 08-26 · GOOG dead-signal test 08-31 · SPY review end-August ·
UNH and XOM re-enables are condition-gated, not dated.**

### Perplexity `sonar` — run 11: its best directional call in weeks, and a FIFTH consecutive clock error
Credit where it is due: `sonar` called **"Nasdaq-100 futures −1.3%, S&P −0.6%"** and the verified figures
were **−1.2% / −0.5%** — the first time in eleven runs it produced a usable regime read, and it was
directionally right. **It still may not be trusted unverified**, for two reasons this run demonstrates:
(1) it filed **July Building Permits, Housing Starts and Import Prices** — all **08:30 ET, pre-open** —
under *"releases DURING US market hours"*, the **fifth consecutive run** with that exact error, and it
**missed the FOMC minutes entirely**, the week's one real in-session event; (2) its single ticker item was
an **AAPL Jefferies downgrade dated 08-10 — eight days stale** — presented as an overnight catalyst, while
it returned "no verified catalyst" for **17 of 19** tickers and missed the ceasefire rejection, Brent at
$90, and the memory-semi selloff outright. **Standing rule unchanged: lead-generation only, never a regime
source, never a clock.** WebSearch (futures, the 08-17→08-21 earnings calendar), the Alpaca news tape
(33 headlines), the IEX daily bars and journald carried this run.

---

## 2026-08-20 — Pre-market Research

**Three changes — the two decisions the crashed 08-19 run owed, plus its backfill, executed on today's data
rather than on yesterday's plan.** Book is CLEAN & FLAT (broker-confirmed **0 positions**, 0 open orders,
equity **$9,089.13**, `last_equity` == `equity`) → **nothing locked**. **WMT and AVGO parked, LLY added;
19 → 18 enabled**; service restarted clean (warmup 18/18). **No 08-19 research-log entry exists** — the
`ustradebot-premarket` routine crashed at 11:30 UTC (`claude exited rc=1`, 26s), which is why three dated
tests all fell due together this morning.

### Market context
**Mildly risk-off, geopolitics-led, and `sonar` had the sign wrong again.** Verified on Benzinga/CNBC:
**SPY −0.08% pre-market ($768.44), QQQ −0.05% ($715.71)** — Dow, S&P and Nasdaq-100 futures all lower after
Wednesday's higher close. `sonar` reported S&P futures **+12.5 points** and Nasdaq **+37** — the wrong
direction (see the closing section).
- **The driver is Iran, not earnings.** Trump launched **"Operation Economic Fury"**, described as an
  "economic D-Day" to isolate Iran, with threatened consequences for any country financing Tehran; Iran is
  reportedly weighing strikes on US targets in Europe. **Brent $92.09 (+0.5%), WTI $86.07.** Hormuz transits
  **73 in the week to 08-16, down from 91** (Lloyd's List). Qatar's foreign minister was on the tape at
  11:25Z on restoring Hormuz traffic.
- **Rates eased slightly:** 10-year **4.66%**, 2-year **4.17%** (the 30-year was near a two-decade high
  earlier this week). Gold −0.72% to ~$4,490.
- **In-session events today are minor but non-zero: July Leading Indicators at 10:00 ET.** Jobless claims
  and the August Philadelphia Fed survey are **08:30 ET, pre-open**. **Jackson Hole is NOT this week** —
  it falls ~08-24/26, with Powell's keynote the following Friday.
- **Today's reporters: WMT, BABA, DE, NTES, ROST.** Two are on this board and **both are BMO — already
  printed before this entry was written**, so neither is an in-session binary.

### Carried from daily review (08-19) — the three owed items
The 08-19 review flagged that the crashed pre-market run left three dated tests undone. All three are
resolved below **on today's bars, not on the reasoning that scheduled them.**
1. **WMT + BABA earnings parks (owed 08-19)** — the event rationale has **expired**, because both reported
   **before the open**. The rationale that scheduled a park (don't hold into a binary) no longer applies to
   a binary that resolved pre-session; this log's own precedent is to *re-enable* BMO reporters on print day
   (JPM 07-14, TSM 07-16). So both were re-judged **post-print, on the outcome** — and they split.
2. **AAPL re-examination (owed 08-19)** — resolved, and it passes. See below.
3. **AVGO on-notice re-check (owed 08-19)** — resolved, and it fails. See below.

The review's other instruction — **"do not churn the board after a flat session"** — is honoured: nothing
here is a P&L-driven edit. Every change is a scheduled test firing or a catalyst on the tape.

### Watchlist review (19 enabled, fresh daily bars through 08-19)

**➖ WMT — PARKED. The one item with real money attached, and the print settled it against the stock.**
Primary source is the Alpaca tape, 11:00–11:17Z: **Q2 adj EPS $0.81 beat $0.74 and sales $187.937B beat
$186.794B — but the guide is below consensus on every line.** Q3 adj EPS **$0.62–0.64 vs $0.68 est**, Q3
sales **$183.134–184.468B vs $188.339B est**, FY2027 adj EPS raised to **$2.80–2.87 but still under the
$2.90 est**, and **Q2 comparable sales missed**. That is a **guidance cut relative to consensus on a ~40x
forward multiple** — an explicit park trigger. `sonar` put it at **$108.17, −6.13%** pre-market; I could not
corroborate the exact percentage with a second source, so **the park does not rest on it** — it rests on the
guidance figures, which are primary-sourced. A move of that order takes WMT from 114.30 through **both** its
20MA (~112.7) and 50MA (~114.2). The record agrees independently: **27 days without a trade** (last 07-24)
and **all-time −$47.51 on 6 trades**, the second-worst on the board. Negative catalyst + broken chart + dead
signal + losing record — all four legs.

**✅ BABA — KEPT, deliberately, and this is the asymmetry worth defending.** BABA also printed BMO and also
fell: **Q1 adj EPADS $1.26 missed $1.85** (RMB 8.52 vs 10.72 consensus), **revenue $39.639B beat $38.630B**,
**AI Cloud & Compute RMB 48.4B with growth accelerating to +45% YoY**; shares **−4% pre-market**. It stays
enabled while WMT parks, and the differentiator is **not the size of the gap**:
- **Chart survives, WMT's does not.** BABA is **+4.66% vs its 20MA / +13.01% vs its 50MA**; a −4% gap leaves
  it ~$123.7, still above the 20MA (~123.2) and far above the 50MA (~114.1). WMT ends up below both.
- **Trailing miss vs forward impairment.** BABA missed on the quarter *behind* it while revenue and cloud
  accelerated; WMT cut the quarter *ahead*. Only one of those changes the forward path.
- **Record.** BABA is **+$52.80 all-time on 12 trades** and +$9.30 in the current window; WMT is −$47.51.
- Also noted: the last four quarters saw BABA **rise 4.7% on the prior print despite a large miss** — the
  pre-market move on this name has a poor record of holding.
**Per the 08-19 review's instruction, BABA's dead-signal clock starts today, post-print** (last trade 08-10,
10 days) — **30-day test due 2026-09-09.**

**✅ AAPL — KEPT; its owed re-examination passes on the data.** On 08-18 it was **−3.71% vs 20MA / −1.13% vs
50MA** and 22 days tradeless, which is why the test was written. Today it is **+0.25% vs 20MA / +2.39% vs
50MA**, **+2.19% yesterday, +4.82% on 5 days**, $16.8B/day, ATR 2.65%. **The chart repaired itself in the
two days the routine was down** — it now fails the trend leg of the two-leg park rule outright, and its
all-time P&L is **+$57.45 on 10 trades** (positive). It is **24 days tradeless**, so the dead-signal leg is
approaching but not met. **Kept; the 30-day dead-signal test is re-dated to 2026-08-27.**

**➖ AVGO — PARKED; its owed on-notice re-check fails on both legs.** On 08-18 it was −1.94% vs 20MA /
+0.64% vs 50MA and was held to its date rather than parked early. The date came due, and in two sessions the
chart deteriorated sharply: **−8.96% vs 20MA, −6.85% vs 50MA, −12.88% over 5 days, −4.61% yesterday.**
**Below both MAs — the same two-leg structural test that parked C and UNH.** It is also the **worst all-time
P&L on the entire board at −$121.38 over 14 trades**, and 10 days tradeless. **The honest counter-argument
is that AVGO is +$43.75 in the current-config window — the single best name in it.** That is **n=2 trades,
last one 08-10**, against a 14-trade structural record and a chart that is now the worst on the board by a
wide margin. Two trades do not overturn a rule that was written in advance and is falling due today; the
08-18 entry's own principle — *a rule that binds only when convenient is not a rule* — cuts this way.
**Parked. Re-enable is condition-gated on the chart repairing back above both MAs, not dated.**

**⚠️ INTC — KEPT, but it is today's genuine near-miss and it goes on notice with a date.** On 08-17 it was
**+6.5% vs its 20MA**; today it is **−3.55% vs 20MA and −14.73% vs 50MA**, **−8.07% on 5 days, −4.02%
yesterday**. That is below both MAs — the trend leg fires. **The rule does not, because it has two legs and
the second is nowhere close: INTC last traded 08-17, three days ago.** It is the **#2 all-time earner at
+$150.78 over 24 trades**, +$24.74 on 7 trades (5 wins) in the current window, $11.6B/day, ATR 6.75% — the
most productive symbol on the board, not a dead one. Parking the second-best earner for a two-day drawdown
would be the mirror image of the error I just refused to make on AVGO. **On notice; re-check 2026-08-27.**

**The rest of the semi complex is broken too, and none of it meets the rule.** AMD **−4.24% / −8.53%**
(7d tradeless, −$89.31 all-time) — Cathie Wood trimmed it a third straight day; MU **+4.73% / −2.62%**
(3d tradeless, **+$189.55, the top all-time earner**); TSM **−0.11% / −2.94%** (16d tradeless, +$20.47);
NVDA **+2.44% / +5.04%**, helped overnight by **China easing limits on H200 shipments**. All kept. **Parking
AVGO takes semi concentration from 6-of-19 to 4-of-18** — the exposure the 08-18 entry flagged, reduced as a
by-product of a rule firing rather than by a discretionary trim.

**🟠 SPY — kept, and the anomaly is now worse, not better.** **55 days without a trade** (last 06-26) and
**ATR down to 0.87%** — it has fallen through 1% since 08-18 and is by far the lowest on the board. But it
is **+1.22% vs 20MA / +2.48% vs 50MA**, so the two-leg rule's second leg fails, exactly as on 08-18.
**Not parked on a bent rule.** Its end-August review should test it on an explicit **volatility floor**
(a 0.87% ATR cannot produce a 1-min ribbon cross worth taking), which is the honest test for this name —
not the MA leg. Others below both MAs but with live signals: **GOOG −0.87% / −2.61%** (20d tradeless,
**dead-signal test 08-31** — untouched).

**Liquidity and safety floor: clean.** Thinnest enabled name is **ABNB at $882M/day**; no sub-$5 names, no
halts. **50 headlines since 08-19 18:00Z contain no company-specific shock** for the board beyond the two
earnings and the NVDA H200 easing — the rest is Iran, bond-market commentary and AI-bubble opinion.

### ➕ Add — LLY, and it is a substitution from the pre-committed plan
The board dropped to **17** after two parks, so a backfill was due and the 08-18 entry had pre-committed
**CRM and ANET**. Neither was added, for reasons found today:
- **CRM — rejected on a fact the pre-verification missed. Salesforce reports Q2 FY27 on Wednesday
  2026-08-26, after the close** (confirmed on Salesforce IR). It was pre-verified for *tradability*, never
  for its earnings date. Adding it today buys **four sessions** before it must be parked again — and on the
  same day as NVDA's 08-26 print, so the board would lose two names at once. Its chart is genuinely the
  strongest of the alternates (**+9.70% / +18.97%, $2.43B/day, ATR 3.98%, +5.07% yesterday**; Cantor
  reiterated Overweight, $250 PT, at 11:02Z today). **It stays a pre-verified backfill, correctly re-dated
  to after 2026-08-26 — post-print, which is how this log adds names.**
- **ANET — rejected; the reason it was chosen has evaporated.** On 08-18 it was +8.9% / +15.6% and **+5.37%
  on 5 days**. Today: **−0.24% vs 20MA, −3.48% yesterday, −11.43% over 5 days.** Momentum gone.
- **➕ LLY — ADDED. Verified on Alpaca `/v2/assets`: `tradable: true`, `status: active`, NYSE, us_equity.**
  **+7.39% vs 20MA, +8.95% vs 50MA, ATR 3.59%, $3.35B/day, +4.46% yesterday, +4.92% on 5 days.** Trending,
  liquid, and in the ATR band the ribbon works in. **Next earnings 2026-10-29 BMO — 70 days clear**, the
  cleanest event calendar of any candidate (Q2 already printed 08-05: revenue +48% YoY to $23.0B). Its
  08-19 move has **no single binary behind it** — an OmniAb ion-channel licensing deal (08-17), an Amplitude
  Therapeutics taRNA partnership (08-19), two CNBC *Final Trades* mentions and an IBD SwingTrader buy — i.e.
  momentum and flow, not a one-day event to mean-revert out of.
  **It also fixes a real structural gap: after UNH was parked 08-17 the board had zero healthcare**, and is
  otherwise 4 semis + 5 mega-cap tech + 2 ETFs + ABNB/BABA/JPM/NFLX/PLTR/TSLA.
  **Note the reversal and why it is not inconsistency:** the 08-18 entry rejected LLY as *"−0.06% vs 20MA,
  still flat."* That was true then. It has since moved +4.46% in a session and now screens. The rejection
  was a statement about price, and the price changed. **On notice as a new add; its live risk is GLP-1
  headline flow (Novo began testing lower-dose Wegovy pills, 08-19), not a scheduled binary.**
- **XOM — stays parked, and today it fails its own condition more clearly than ever.** Its chart is the best
  of the parked set (**+4.64% / +11.08%, $2.25B/day, ATR 2.30%**), but the 08-17 re-enable condition was
  *"only if the oil headline regime quiets down."* Today Trump launched an "economic D-Day" against Iran and
  **Brent is $92**. **Condition emphatically not met.** Pre-verified backfill, still waiting.
- Screened and rejected on fresh bars: **MRVL** (+15.07% / +1.19% but **+9.85% in one session** — a spike,
  and a fifth semi), **NOW** (+9.12% / +17.76% but a V-bounce off last week's −7.64%, and it was rejected
  08-18 as a falling knife), **UBER** (+7.31% / +7.57%, $1.54B/day — the runner-up), **COIN** (+9.55%
  yesterday, crypto-beta), **DELL** (−6.64% yesterday), **APP** (−14.46% / −28.59%), **CAT**, **GE**, **C**.

### Changes applied to dbo.watchlist
Three parameterized statements, `watchlist` the only table touched, **no DELETEs**:
1. `UPDATE ... SET enabled = 0, note = ?` — **WMT** (guide below consensus on Q3 EPS, Q3 sales and FY27;
   comps miss; gaps through both MAs; 27d tradeless; −$47.51).
2. `UPDATE ... SET enabled = 0, note = ?` — **AVGO** (on-notice re-check due: −8.96% vs 20MA / −6.85% vs
   50MA, −12.9% on 5 days; worst all-time P&L −$121.38).
3. `MERGE ... WHEN NOT MATCHED THEN INSERT` — **LLY** enabled 1 (new row; Alpaca-verified tradable/active).
Re-read after commit: **18 enabled ≤ 30 ✓**, **29 rows ✓**, **11 parked ✓**.

### Final watchlist
**18 enabled** (≤30 ✓): AAPL ABNB AMD AMZN BABA GOOG INTC JPM **LLY** MSFT MU NFLX NVDA PLTR QQQ SPY TSLA
TSM. Parked (11): **AVGO** BIRD C COST ENPH QCOM SE UNH **WMT** WPM XOM.
**Service restarted (required — the table changed) and verified, not assumed:** `is-active` → **active**,
**MainPID 1326480**, `ActiveEnterTimestamp` **2026-08-20 11:39:01 UTC**, **NRestarts=0**. Journald confirms
the banner *"Watchlist (dbo.watchlist): AAPL, ABNB, AMD, AMZN, BABA, GOOG, INTC, JPM, LLY, MSFT, MU, NFLX,
NVDA, PLTR, QQQ, SPY, TSLA, TSM"*, **warmup primed 18/18**, IEX stream subscribed to exactly those 18
(**LLY present in both**), account reconciled `PA34DFFLTHRT` equity 9089.13 / **no open positions**, and
**zero WARN or ERROR lines** since start.
🔒 Locked: **none (0 positions)**.
**Upcoming: NVDA earnings 08-26 · CRM add re-dated to after 08-26 (post-print) · AAPL 30-day dead-signal
test 08-27 · INTC on-notice re-check 08-27 · GOOG dead-signal test 08-31 · SPY volatility/dead-signal
review end-August · BABA dead-signal clock started today, due 09-09 · AVGO, UNH and XOM re-enables are
condition-gated, not dated.**

### Perplexity `sonar` — run 14: wrong sign on the index read, and the clock error finally stopped
`sonar` reported **"S&P 500 futures higher by about 12.5 points"** and **"Nasdaq futures higher by about 37
points."** The verified figures were **lower on all three indices** (SPY −0.08%, QQQ −0.05% pre-market).
**Wrong direction on the one thing a pre-market briefing exists to get right** — and the second consecutive
run where its index call had the opposite sign to reality (08-19's daily review recorded the same failure
against the open→close window). It returned **"no specific overnight catalyst"** for **18 of 19 tickers**,
including **BABA on the morning BABA reported earnings**, and it missed Operation Economic Fury, Brent at
$92 and the NVDA H200 easing entirely.
**Two things it did earn:** it was the **only** source that flagged **WMT reporting before the open with a
7:30 ET call**, and its **$108.17 / −6.13%** pre-market quote was the sole numeric on WMT's reaction.
Consistent with the standing rule, that lead was **used to go looking and never used as evidence** — the
WMT park is justified on the guidance lines off the Alpaca tape, which stand without it. Credit also where
due: after five consecutive runs misfiling pre-open releases as in-session, **it filed no clock error this
run** (it was cut off mid-sentence on the releases section instead). **Standing rule unchanged:
lead-generation only, never a regime source, never a clock.** WebSearch (futures, Iran, the earnings and
economic calendar, CRM's and LLY's earnings dates), the Alpaca news tape (50 headlines), the daily bars,
`/v2/assets` and journald carried this run.

### Harness note
The 08-19 `ustradebot-premarket` failure (`claude exited rc=1`, 26s, no stderr captured) cost this board a
day of drift and stacked three dated tests onto one morning. **It did not cost money** — the book was flat
and 08-19 traded zero times, so the un-parked WMT and BABA were never entered into their prints. That was
luck, not design. Fixing `run-routine.sh` to capture stderr remains a `/root/claude-routines` task, outside
this repo and outside this routine's remit, and it is still worth doing before the next earnings park lands
on a day the bot is actually holding something.

---

## 2026-08-21 — Pre-market Research

**One substitution, and it is the volatility-floor test this log owed on SPY — parked on it, UBER added in
its place. 18 → 18 enabled**, service restarted clean (warmup 18/18). Book is CLEAN & FLAT (broker-confirmed
**0 positions, 0 open orders**, equity **$9,089.13**, `last_equity` == `equity` — a fourth consecutive
session that did not move the book) → **nothing locked**. The 08-20 review's binding instruction — *no symbol
could have traded on a 0.0%-open gate, so silence carries zero information* — is honoured: **nothing here is
parked for being quiet**, and no dead-signal clock was started or advanced on 08-18/19/20 evidence.

### Market context
**A modest bounce off Thursday's rout, with the macro print landing 15 minutes before the bot may enter.**
- **Futures higher, and for once all three sources agree on the sign.** The Alpaca tape at 09:33Z carries
  *"Dow Jones, S&P 500 Futures Gain as Scott Bessent Touts 'Toughest Sanctions' for Iran"*; a second feed
  headlines *"Why Are Nasdaq, S&P 500 Futures Rising Premarket? NVDA, MU… In Focus"*; `sonar` gives **S&P
  +0.3%, Nasdaq +0.4–0.53%**. Three independent sources, same direction → taken as **up, modestly**.
  **No primary quote check was possible**: IEX had **zero pre-market prints** as of 11:35Z (every snapshot's
  `latestTrade` was still yesterday's after-hours), so this is the one figure today resting on secondary
  sources.
- **Thursday closed badly and that is the context for the bounce:** *"Dow Falls 700 Points, Nasdaq Drops 1%
  As Yields Rise Again"* (tape, 08-20 20:22Z). Daily bars: **QQQ −0.72%, SPY −0.84%** close-to-close.
- **In-session releases: S&P Global Flash Manufacturing + Services PMI at 09:45 ET** — independently
  confirmed on the release calendar for today (July composite was 53.6, an 8-month high) — and **BLS state
  employment at 10:00 ET**. The PMI lands **15 minutes before `ENTRY_START=10:00`**, so no entry can be taken
  into it; the bot sees only the reaction.
- **Iran is still the macro driver.** Bloomberg via the tape at 10:22Z: *Iranian oil supply to Chinese
  refiners squeezed by US blockade*; Bessent promising the toughest sanctions yet. This is directly
  load-bearing for XOM's re-enable condition (below).
- **No board name reports today.** NVDA is **08-26**. 45 headlines since 08-20 18:00Z contain **no halt, no
  guidance change and no in-session binary** for any enabled name.
- **Board headlines worth naming:** BMO initiated **NVDA** Outperform/$340 and **AMD** Outperform; **NVDA**
  reportedly in talks to buy Korean AI-chip startup Rebellions; **TSLA** recalling ~**1.96M** China-made
  Model 3/Y, discontinuing solar roof tiles, and carrying a JPM note doubting FSD; **BABA** says AI now
  drives >⅓ of cloud revenue; India ordered **GOOG** to shut hundreds of Firebase accounts.

### Carried from the 08-20 daily review
The review's finding — **the market gate was open 0.0% of 08-20's entry window and 7.2% on 08-19**, so no
long was structurally possible — constrains this run more than any single fact on the tape. Honoured in full:
- **No clock started or advanced on the shut-gate sessions.** BABA stays **paused** (due 09-09), AAPL
  **08-27**, INTC's on-notice re-check **08-27**, GOOG **08-31** — all untouched.
- **Nothing parked for being quiet.** The single park below is structural; its quietness is a *consequence*
  of the argument, not the argument, and the entry says so explicitly where it could be misread later.
- **"MU is the name to watch"** — kept, unchanged, and it is the strongest name on the board today
  (**+8.99% vs 20MA, +3.97% yesterday, $35.5B/day, ATR 6.03%**), plus a *"No AI Without Memory"* CEO piece
  on the tape. Nothing to do.
- **LLY, one session old with zero scored candidates** — no inference drawn, as instructed. Chart still
  screens (**+4.12% / +5.71%, ATR 3.70%, $3.40B/day**) despite −2.81% yesterday.

### Watchlist review (18 enabled, SIP daily bars through 08-20)

**➖ SPY — PARKED on an explicit volatility floor. This is the test the 08-20 entry said was owed on this
name, run on data instead of asserted.** Last 20 sessions, range = (H−L)/O:

| | ATR% | median range | ≥1.25% | ≥2% |
|---|---:|---:|---:|---:|
| **SPY** | **0.84** | **0.75%** | **25%** | **0%** |
| QQQ | 1.46 | 1.42% | 55% | 25% |
| JPM | 1.60 | 1.40% | 80% | 20% |
| NVDA / TSLA / MU | 2.90 / 3.19 / 6.03 | 2.73 / 3.48 / 5.92% | 100% | 65 / 95 / 100% |

**The trailing stop is 1.25%. On 15 of the last 20 sessions SPY's entire high-to-low range was smaller than
the give-back the exit structure requires** — a perfect entry at the low and exit at the high would not have
cleared the trail — and the bot enters mid-move on a 1-min cross, never at the low. **Zero of 20 sessions
ranged 2%.** That is a mismatch between the instrument and the exit config; it does not depend on regime, on
the gate, or on how quiet the last three sessions were, which is precisely why it survives the 08-20
instruction. Corroborating but **not load-bearing**: 56 days without a signal (last trade 06-26) and
**−$11.24 on 4 trades**.
**Note what this park deliberately does *not* use.** SPY's chart is fine (**+0.21% vs 20MA / +1.55% vs
50MA**), so the two-leg MA rule does not fire, and bending it to reach a park would be the exact error this
log refused on AVGO (08-18) and INTC (08-20). A different rule is stated instead, in advance and in the open.
**Re-enable is condition-gated, not dated: ATR back above ~1.5% with a median session range above the 1.25%
trail width.**

**🔒 QQQ — structurally locked, and this must be recorded because the trade record argues for parking it.**
QQQ last traded **07-14 — 38 days**, the second-longest silence on the board, and a future run reading only
`dbo.trades` would reach for it. **It must never be parked.** `bot/strategy.py:255-278` resolves
`MARKET_FILTER_SYMBOL` (default **QQQ**; unset in `.env`) against the same per-symbol gate snapshots the
*watchlist* populates, and **when the symbol is not on the watchlist the gate fails OPEN** — one WARNING line
and the bot's best-evidenced edge (four agreeing windows; **+$91.52 at 10 days**) silently switches off. On
its own merits it is also the best name here: **7 trades, 6 wins, +$80.15**. It is the gate, not a trade idea.

**✅ INTC — kept, on notice, unchanged.** **−3.84% vs 20MA / −15.10% vs 50MA, −11.89% on 5 days** — below
both, so the trend leg fires again. The second leg is nowhere near: it **last traded 08-17** and produced
**2 scored refusals on 08-20**, i.e. it is reaching the scorer. #2 all-time earner **+$150.78 / 24 trades**,
ATR 6.43%, $11.3B/day. **Re-check 08-27 as scheduled.**

**✅ AAPL — kept; the trend leg still fails.** It gave back yesterday's gain (**−1.75%**) and is **−1.34% vs
20MA but +0.47% vs 50MA**. Above one MA is not below both. All-time **+$57.45**. **Test stays 08-27.**

**⚠️ AMZN — kept, but it is today's nearest miss and it gets a date.** Sitting **exactly on its 20MA
(+0.02%)**, +4.33% vs 50MA, **−4.46% over 10 days**, last trade **08-03**, and the **worst all-time P&L on
the enabled board at −$108.51 over 14 trades**. Both legs are approaching and neither is met. **Dated
re-check 2026-09-02** (30 days from its last trade).

**⚠️ JPM — kept, and it is the name the new floor points at next.** **ATR 1.60%, median range 1.40%** — the
closest enabled single name to SPY's failure — but **80% of its sessions still clear the 1.25% trail** and
it is **above its 50MA (+2.47%)**, so neither the floor nor the two-leg rule fires. Record is poor
(**−$51.50 / 9 trades**) and it last traded **07-27**. **Dead-signal test dated 08-27**, the same day as
AAPL's, since they last traded the same day.

**✅ TSLA — kept, and the headline flow is logged rather than acted on.** A **~1.96M-vehicle China recall**,
the solar-roof discontinuation and a JPM FSD note is the worst news day of any enabled name. But it is
**not a scheduled binary and not a guidance change**, it is priced pre-open, and **the bot never holds
overnight**. Chart: **+5.98% vs 20MA / −5.76% vs 50MA**, ATR 3.19%, $11.5B/day; last trade 08-13 **+$29.16**.
The honest statement is that a recall of that size is a risk the ribbon cannot see coming — which is true of
every headline and is not a reason to trade a different book.

**✅ The rest, briefly.** **NVDA** +1.91% / +4.61%, two positive initiations, $25.0B/day — earnings **08-26**
is the next scheduled park. **TSM** +0.83% / −1.96%. **BABA** +5.28% / +14.23%, clock paused to 09-09.
**NFLX** **+7.13% / +7.47%**, ATR 2.85%, $2.56B/day — the chart has genuinely repaired even though its
all-time record is −$82.34. **PLTR** +12.65% / +26.12% and **ABNB** +11.00% / +21.36% are the two strongest
trends on the board. **MSFT** +2.81% / +15.07%. **AMD** −2.91% / −7.92% below both MAs but **last traded
08-13**, so the second leg fails — kept, **dated 2026-09-12**. **GOOG** −2.17% / −3.48%, test **08-31**,
untouched. **Liquidity floor clean:** thinnest enabled name is **ABNB at $0.91B/day**; no sub-$5 names, no
halts.

### ➕ Add — UBER, and it is a deliberate substitution rather than an unrelated backfill
**Verified on Alpaca `/v2/assets`: `tradable: true`, `status: active`, NYSE, us_equity.**
- **+7.30% vs 20MA, +8.03% vs 50MA, +3.52% on 5 days, +11.47% on 10 days, ATR 3.73%, $1.52B/day.**
- **Median intraday range 3.31%, with 100% of the last 20 sessions ≥1.25% and 75% ≥2%** — the exact inverse
  of the name it replaces. That symmetry is the point: the board loses the instrument that cannot pay for its
  own trailing stop and gains one that clears it every session.
- **Event calendar clear.** Q2 reported **2026-08-05 BMO**; the company has not announced Q3 and trackers put
  it **10-29 → 11-03** — **~70 days clear**, the same standard LLY was added on.
- **Its move is flow and product news, not one binary to mean-revert out of:** Baidu Apollo Go robotaxis to
  Dubai (08-20), Pony AI autonomous rides in Zagreb (08-19), a Zipline drone-delivery partnership plus a
  planned strategic investment (08-17), a CNBC *Final Trades* mention and a Cramer buy call. **Live risk is
  regulatory/labour headline flow** (California rideshare-union push, 08-18), not a scheduled event.
- **It also fixes a concentration the board has carried for weeks:** 5 semis + 5 mega-cap tech, and UBER is
  the first consumer-platform name since SE was parked on 07-30.

**Rejected on fresh evidence:**
- **➖ MRVL — rejected on a verified date, exactly as CRM was on 08-20.** It screened **best of every
  alternate** (**+20.52% vs 20MA, +12.98% on 5 days, ATR 6.91%, $4.98B/day**, and BMO initiated Outperform at
  09:48Z today), and it would have been the add on chart alone. **Marvell has announced Q2 FY2027 results for
  Thursday 2026-08-27, after the close** (company conference-call announcement, 08-03). Adding it today buys
  **four sessions** before a mandatory park — and it would be a fifth semi. **Re-screen after the print.**
- **CRM** — unchanged, still re-dated to after its **08-26** AMC print.
- **XOM — stays parked, condition still unmet.** Best chart of the parked set (**+5.21% / +11.75%,
  $2.24B/day, ATR 2.24%**) but the 08-17 condition was *"only if the oil headline regime quiets down,"* and
  today's tape has a US blockade squeezing Iranian oil and a Treasury Secretary promising the toughest
  sanctions yet. **Not quiet.**
- **AVGO — stays parked despite a genuinely good headline** (*Broadcom steps up NVIDIA challenge with a
  potential $100B AI financing deal*, 09:48Z). Its re-enable is **chart-gated**: **−8.24% vs 20MA / −6.32% vs
  50MA, −12.87% on 5 days**. A headline is not the condition; the condition is the chart.
- Screened and rejected on fresh bars: **NOW** (+9.53% / +19.62% but the same V-bounce shape rejected 08-18),
  **COIN** (+11.69% / +9.24% but crypto-beta), **ORCL** (−9.06% on 5 days), **META** (−5.69% / −8.02%),
  **PANW** (−11.76% on 5 days), **ANET** (momentum gone, −9.76% on 5 days), **GE** (−5.46% / −4.05%),
  **CAT** (−3.44% / −10.01%), **ISRG** (−5.84% yesterday), and **LIN** — which fails the same volatility
  floor SPY was just parked on (**ATR 1.71%**), applied consistently to a candidate on the day it was written.

### Changes applied to dbo.watchlist
Two parameterized statements, `watchlist` the only table touched, **no DELETEs**:
1. `UPDATE ... SET enabled = 0, note = ?` — **SPY** (volatility floor: ATR 0.84%, median range 0.75%, only
   25% of 20 sessions reach the 1.25% trail width; 56d no trade; −$11.24 on 4 trades).
2. `MERGE ... WHEN NOT MATCHED THEN INSERT` — **UBER** enabled 1 (new row; Alpaca-verified tradable/active).
**A first attempt failed and is recorded rather than hidden:** the SPY note was 141 characters and
`note` is `VARCHAR(128)`, so SQL Server raised *"String or binary data would be truncated."* **Nothing was
committed on that attempt** — both statements were then re-run and committed together. Re-read after commit:
**18 enabled ≤ 30 ✓**, **30 rows ✓**, **12 parked ✓**.

### Final watchlist
**18 enabled** (≤30 ✓): AAPL ABNB AMD AMZN BABA GOOG INTC JPM LLY MSFT MU NFLX NVDA PLTR QQQ TSLA TSM
**UBER**. Parked (12): AVGO BIRD C COST ENPH QCOM SE **SPY** UNH WMT WPM XOM.
**Service restarted (required — the table changed) and verified, not assumed:** `is-active` → **active**,
**MainPID 1405613**, `ActiveEnterTimestamp` **2026-08-21 11:38:43 UTC**, **NRestarts=0**. Journald confirms
the banner *"Watchlist (dbo.watchlist): AAPL, ABNB, AMD, AMZN, BABA, GOOG, INTC, JPM, LLY, MSFT, MU, NFLX,
NVDA, PLTR, QQQ, TSLA, TSM, UBER"* — **UBER present, SPY absent** — **warmup primed 18/18**, the IEX stream
subscribed to exactly those 18, account `PA34DFFLTHRT` reconciled at equity 9089.13 with **no open
positions**, and **0 WARNING/ERROR lines** in the 20 lines since start.
🔒 Locked: **none (0 positions, 0 open orders)**.
**Upcoming: NVDA earnings 08-26 · CRM add after 08-26 · AAPL and JPM dead-signal tests 08-27 · INTC
on-notice re-check 08-27 · MRVL re-screen after its 08-27 print · GOOG dead-signal test 08-31 · AMZN
re-check 09-02 · BABA 09-09 (paused for the shut-gate stretch) · AMD 09-12 · AVGO, UNH, XOM and now SPY
re-enables are condition-gated, not dated.**

### Perplexity `sonar` — run 15: right on the macro layer, useless on the ticker layer
**Credit where due, after two runs with the sign wrong: its index call was correct** (+0.3% S&P / +0.4–0.53%
Nasdaq), matching the tape's *"futures gain"* headline, and **it flagged the 09:45 ET flash PMI**, which
independent calendar confirmation verified. Per the standing rule it was still used only as a lead — the
futures direction is written here because **two other sources agreed**, not because `sonar` said it.
**The ticker layer failed again, and worse than the count suggests: "no specific overnight catalyst" for 17
of 18 names** — on a morning carrying a 1.96M-vehicle Tesla recall, two BMO initiations and an NVDA
acquisition report, all of which the Alpaca news tape had. **It also silently dropped PLTR from its output
entirely.** Fifteenth consecutive thin run. **Standing rule unchanged: lead-generation only, never a regime
source, never a clock, never a price.** WebSearch (futures, the PMI calendar, MRVL's and UBER's earnings
dates), the Alpaca news tape (45 headlines), SIP daily bars, `/v2/assets` and journald carried this run.

### Data-source note — worth two minutes to the next run
- **Daily bars must be pulled with `feed=sip`.** IEX daily volume is ~3% of the consolidated tape (AAPL:
  1.16M vs 41.1M shares on 08-20), which understates dollar volume by ~30× and would silently break the
  liquidity floor. `/v2/stocks/snapshots` returns **403 on `feed=sip`** but works on `feed=iex`.
- **`limit` alone returns `bars: null`** — an explicit `start` is required on the bars endpoint. Two runs
  have now rediscovered this.
- **IEX carries no pre-market prints**, so `latestTrade` before the open is yesterday's after-hours. A
  pre-market gap check cannot be sourced from this feed; it needs the news tape or WebSearch.

---

## 2026-08-24 — Pre-market Research

**The weekly review's one red-flag item is now closed: NVDA is PARKED ahead of Wednesday's print, three
sessions early and deliberately so.** DASH added in its place. **18 → 18 enabled**, service restarted clean
(warmup 18/18, banner shows DASH present / NVDA absent). Book is CLEAN & FLAT (broker-confirmed **0 positions,
0 open orders**, equity **$9,089.13**, `last_equity` == `equity` — a **fifth** consecutive session that did not
move the book) → **nothing locked**. The 08-21 daily review's instruction — *"the watchlist is not the problem,
the tape was… no watchlist change is indicated by today's session"* — is honoured: **neither change today is a
performance park.** One is event risk, one is an addition on its own merits.

### Market context
**A data-heavy, event-heavy week opening on a soft tape, with the board's largest scheduled risk on Wednesday.**
- **Futures slightly lower / mixed, and the sources genuinely disagree — recorded as such rather than smoothed.**
  The Alpaca tape at 09:30Z headlines *"S&P 500, Nasdaq 100 Futures Slip Ahead of Data-Heavy Week, Nvidia
  Earnings, and Jackson Hole"*; WebSearch returned one feed with **ES +0.4% / NQ +0.3%** and another with **Dow
  up, S&P and Nasdaq down**. **Taken as flat-to-slightly-lower, low conviction.** `sonar` gave **no futures
  direction at all**. Per the standing rule no primary quote check was possible — **IEX carries no pre-market
  prints**, so this figure rests on secondary sources and is flagged accordingly.
- **The rates backdrop is the driver, and it is the same one that broke last week.** US 10-year at **~4.74%, a
  20-month high**; the 30-year hit its **highest level since 2007**. S&P 500 sits **~2% below its record** after
  a **−1.4% week**; **the Philadelphia semiconductor index fell ~5% last week.** That last figure matters more
  than the index numbers — **five of the eighteen enabled names are semis.**
- **In-session releases today: none of consequence.** The Chicago Fed National Activity Index prints **08:30 ET,
  before the open**; 3- and 6-month bill auctions at 10:30 ET are not tradeable events. **`sonar` mislabelled the
  Chicago Fed print as a market-hours release — verified against the calendar and corrected here.**
- **This week's real calendar:** **NVDA Wed 08-26 AMC** · **July core PCE Wed 08:30 ET** · Q2 GDP revision +
  durable goods Wed · **Jackson Hole 08-27→29, Chair Warsh keynote Fri 10:00 ET**. Also reporting: PDD/XPeng
  today, INTU Tue, **CRWD + CRM + HPQ + OKTA Wed**, **MRVL + ULTA Thu**.
- **No enabled board name reports today, and none reports during market hours this week.** NVDA is the only
  board name with a print at all, and it is being parked for it below.

### Carried from the 08-21 daily + weekly reviews
- **🔴 "PARK NVDA BEFORE WED 08-26 — this is the one item with real money attached."** Done, today. See below
  for why it was not deferred to Tuesday.
- **"No watchlist change is indicated by today's session"** (daily) — honoured. **Nothing is parked for being
  quiet, and no dead-signal clock was started or advanced.** QQQ, TSM and UBER printed near-zero ribbon spread
  on 08-21 (0.00116 / 0.00186 / 0.00058) and the daily asked whether they are *"chronically inert or just quiet
  on a narrow tape."* **The answer is: quiet.** On a 0.89%-range QQQ session, ribbon spread is not a symbol
  property. All three clear the volatility floor on their own bars (**TSM ATR 3.26% / med range 2.43%**,
  **UBER 3.47% / 3.07%**); **QQQ is the market-filter symbol and is structurally unparkable regardless**
  (`bot/strategy.py:255-278` — the gate fails **OPEN** if `MARKET_FILTER_SYMBOL` leaves the watchlist).
- **"PLTR and TSLA are the two names worth keeping"** (daily) — kept, and both are vindicated on fresh bars:
  **PLTR +14.41% vs 20MA / +29.52% vs 50MA, ATR 4.28%, $6.18B/day**, the strongest chart on the board; **TSLA
  +10.58% / −0.82%, +5.14% on Friday alone, ATR 3.82%, $11.66B/day**.
- **"GOOG chopped hard — 5 refusals, the most of any symbol"** (daily) — **noted, not acted on.** Its
  dead-signal test is dated **08-31** and 7 refusals in 5 sessions means it is reaching the scorer, so the
  second leg fails anyway. Chart −1.46% / −2.40%. **Untouched.**
- **Frequency collapse is the project's binding constraint** (weekly: 45 → 2 trades/week over seven weeks).
  **This is the lens the DASH add is justified under** — it adds opportunity **without touching a single
  filter**, which is the only direction the weekly left open.

### Watchlist review (18 enabled, SIP daily bars through 08-21)

**➖ NVDA — PARKED on a verified scheduled binary. This is the weekly's red-flag item and the only change here
with capital at stake.**
- **Confirmed Wednesday 2026-08-26, after the close** (press release ~13:20 PT, call 14:00 PT). Consensus
  **~$91.85B revenue / $2.08 EPS** against company guidance of $91.0B ±2%. **Options are pricing a ~6% move**,
  with sell-side notes flagging downside toward **$190** on a miss — NVDA closed **$214.72**.
- **Why today and not Tuesday, which is the real decision.** The bot never holds overnight, so the mechanical
  risk is only the 08-26 session itself. **But the bot has no earnings guard of its own** — its sole protection
  is *this routine*, and **this routine crashed on 08-19 (`claude exited rc=1`) and left WMT and BABA unparked
  into their prints.** Nothing bad happened then because the gate was 0.0% open on 08-20 — **that was luck, not
  control**, and the weekly said so. Parking three sessions early costs two sessions of a **neutral** chart
  (**+0.72% vs 20MA / +3.44% vs 50MA, −4.64% on 5 days**) with a **negative all-time record (−$16.65 / 13
  trades)**; deferring costs a dependency on two more runs not crashing. **The insurance is cheaper than the
  risk it removes.**
- Headline flow is heavy but irrelevant to the decision: Cantor reiterated Overweight/$350, NVDA in talks to
  back Perplexity at **$30B+**, a **$6B** Poolside deal, and Bloomberg reporting AI-server price hikes >15%.
  **None of that is a reason to hold an enabled name into a 6% implied move.**
- **Re-enable 2026-08-27**, once the print clears — the same pattern AAPL, AMZN, MSFT and TSLA were all
  re-enabled on.

**⚠️ BABA — KEPT, and this is the closest call of the run, so the reasoning is written out rather than
asserted.** It is the board's worst two-day chart: **−8.57% on Friday** (a move **no prior entry captured**,
because it happened after the 08-21 pre-market run) and **another ~3.7% lower pre-market today**.
- **The cause is now known and it is dilution, not an earnings miss:** Alibaba **priced a HK$80B (~$10B) Hong
  Kong placement of 710M new shares at HK$112.70**, reported Sunday, to fund AI capex. HK-listed shares fell
  **~10%**. CEO Wu Yongming bought 350K shares; Michael Burry publicly rotated BABA → JD.
- **It does not meet any standing park rule.** Chart is **−4.02% vs 20MA but +4.36% vs 50MA** — above one MA, so
  the two-leg trend rule does not fire. ATR **3.80%**, median range **2.13%**, **95% of 20 sessions ≥1.25%** —
  it clears the volatility floor comfortably. Its dead-signal clock is **paused to 09-09**. All-time **+$52.80
  on 12 trades**, and **12 refusals in the last 5 sessions — the most of any symbol**, so it is very much alive
  to the scorer.
- **The governing precedent is three days old and points the same way:** TSLA's **1.96M-vehicle recall** was
  logged-not-acted-on on 08-21 because *"it is not a scheduled binary and not a guidance change, it is priced
  pre-open, and the bot never holds overnight."* **A priced placement is the same class of fact.** Bending a
  rule to reach a park is the exact error this log refused on AVGO (08-18) and INTC (08-20).
- **The clean resolution, stated in advance so it cannot be rationalised later: BABA's 50MA cushion is +4.36%
  and it is gapping ~3.7% lower today. If it closes below its 50MA, the two-leg rule fires on its own and it
  parks tomorrow — on the rule, not on the headline.** No new rule needed. **On notice.**

**⚠️ INTC — kept, on notice, and it is now the worst chart on the enabled board.** **−5.88% vs 20MA / −16.74%
vs 50MA, −12.13% over 5 days**, and the **worst recent P&L on the board: −$40.48 over 4 trades in 14 days.**
The trend leg fires emphatically. **The second leg still fails** — it last traded **08-17 (7 days)** and
produced 2 scored refusals on 08-20, so it is reaching the scorer. **Its re-check is dated 08-27 and I am
honouring the date**, exactly as the 08-20/08-21 entries did when the temptation ran the other way. It remains
the **#2 all-time earner (+$150.78 / 24 trades)**, ATR 7.22%, $10.05B/day. **Flagged as the most likely park of
the week.**

**⚠️ UBER — kept, one session old, and the risk its add note named has already landed.** The 08-21 entry said
*"live risk is regulatory/labour headline flow, not a scheduled event."* Today: **Dutch regulators reportedly
seeking nearly $1B in fines** over automated driver suspensions (08:48Z). **A reported fine is not a ruling and
not a scheduled binary**; the chart is unhurt (**+6.71% vs 20MA / +8.07% vs 50MA, ATR 3.47%, med range 3.07%,
100% of 20 sessions ≥1.25%**). **Kept. Recorded because a risk called in advance and then hit within one
session is worth scoring the call on, either way.**

**✅ MU — kept, and it is the board's liquidity anchor.** **+7.87% vs 20MA / +0.23% vs 50MA, ATR 6.90%, median
range 5.42%, $33.56B/day** — the most liquid name on the board by 35%. Down **~3.3% pre-market** with the semi
complex (`sonar` lead, consistent with SOX −5% last week), against a CEO piece: *"No End to AI Memory Supply
Crunch."* **#1 all-time earner (+$189.55 / 25 trades).** Nothing to do.

**🔒 QQQ — structurally locked, restated because the trade record keeps arguing for parking it.** Last traded
**07-14 — 41 days**, the longest silence on the enabled board, ATR **1.59%**, median range **1.30%**, and only
**50% of sessions clear the 1.25% trail**. **On the 08-21 volatility floor it would be a park candidate, and it
must still never be parked:** it is `MARKET_FILTER_SYMBOL`, and removing it from the watchlist makes the market
gate **fail OPEN** — one WARNING line and the bot's best-evidenced edge (four agreeing replay windows) silently
switches off. On its own merits it is also the best record on the board: **7 trades, 6 wins, +$80.15.**

**✅ The rest, briefly.** **ABNB** +10.84% / +21.94%, ATR 3.07% — strong, still the **thinnest enabled name at
$0.80B/day**, on notice for that alone. **TSLA** +10.58% / −0.82%, **+5.14% Friday**. **NFLX** +5.72% / +6.80%,
8 refusals in 5 sessions — genuinely active despite an all-time −$82.34. **LLY** +4.78% / +6.43%, ATR 3.34%,
$3.22B/day, 2 refusals — settling in. **MSFT** +2.15% / +15.10%. **TSM** +1.35% / −1.31%, 5 refusals.
**AMZN** −1.05% / +3.56%, above the 50MA so the trend leg fails, **re-check 09-02** unchanged. **JPM** −1.54% /
+2.22%, ATR 1.77% / median range 1.40% — **still the closest enabled name to SPY's volatility failure**, but
80% of sessions clear the trail and it is above its 50MA; **dead-signal test 08-27**. **AAPL** −1.59% / −0.28%,
**test 08-27**. **AMD** −1.63% / −7.25%, ATR 6.00%, below both MAs but last traded 08-13 — second leg fails,
**dated 09-12**. **GOOG** −1.46% / −2.40%, **test 08-31**. **Liquidity floor clean: no sub-$5 names, no halts,
thinnest enabled is ABNB at $0.80B/day.**

### ➕ Add — DASH, and it is justified on the weekly's own diagnosis rather than on the NVDA slot
**Verified on Alpaca `/v2/assets`: `tradable: true`, `status: active`, NASDAQ, us_equity.**
- **Trend, both legs: +7.20% vs 20MA, +16.68% vs 50MA**, +2.98% on 5 days, +3.34% on 10 days.
- **It clears the 08-21 volatility floor by the widest margin of any candidate screened: ATR 3.60%, median
  session range 3.64%, and 100% of the last 20 sessions ranged ≥1.25% *and* ≥2%.** The floor exists because
  SPY could not pay for its own 1.25% trailing stop; DASH's *median* session is nearly 3× that width.
- **Event calendar clear.** Q2 2026 reported **2026-08-05** (revenue $4.454B, +36% y/y; adj. EBITDA $914M, +40%;
  Q3 guidance **raised**). Q3 is due **late Oct → early Nov** — **~10 weeks clear**, the same standard LLY and
  UBER were added on.
- **Its move is operating momentum, not one binary to mean-revert out of.** Today's tape carries a DASH CFO
  piece on share gains as consumers cut back (10:21Z); the company also took FAA Part 135 certification for
  drone delivery and is scaling its "Dot" delivery robot.
- **Why it is the right add on a week like this one:** the board carries **5 semis** into a week where **SOX
  fell 5%** and the sector's bellwether reports Wednesday. DASH is a **consumer-platform** name, the second
  after UBER, and it is uncorrelated to both the NVDA print and the rates move driving the tape.
- **The honest debit, stated up front: $0.81B/day median dollar volume makes it the joint-thinnest name on the
  board with ABNB.** It clears the floor but sits at it. **On notice for liquidity from day one.**

**Rejected on fresh evidence:**
- **HOOD — rejected, and it is the day's instructive rejection.** It screens spectacularly (**+15.18% vs 20MA,
  ATR 5.66%, $1.60B/day**) — because it is **+13.70% pre-market on a Trump/Clarity Act crypto headline**. That
  is a **gap**, and this bot's entire lifetime loss is concentrated in buying moves that already happened
  (IMP-017). **A one-day news spike is the worst possible entry condition for a 1-min ribbon cross.**
- **MSTR (+20.98% / +19.51%) and COIN (+19.70% / +17.65%) — rejected on the 08-21 crypto-beta rule**, applied
  consistently rather than re-litigated because the numbers got prettier. Both are bitcoin proxies.
- **SNOW — rejected on a verified date, exactly as MRVL was on 08-21.** It screens well (**+5.49% / +19.43%,
  ATR 3.96%, $1.43B/day**) but **Snowflake reports this week**. Same reason MRVL (Thu 08-27), CRM and CRWD
  (both Wed 08-26) are all off the table.
- **NOW — rejected for a third time, and deliberately not overridden.** It is better than DASH on liquidity
  (**$2.29B/day**) and volatility (ATR 4.87%, median range 5.02%) and it was tempting to reverse. **But it was
  rejected on 08-18 and again on 08-21 for a V-bounce shape, and nothing in the fresh bars refutes that** — it
  is still **+7.12% vs 20MA against +17.96% vs 50MA**, the same stretched gap. **Overturning a twice-stated
  rejection with no new evidence is churn wearing a chart.** Re-screen when the 20/50 gap compresses.
- **SMCI** (+13.38% / +22.16% but **−6.53% on 5 days** — erratic, not trending), **ORCL** (+4.03% / **+0.72%**
  — the 50MA leg is effectively flat), **SHOP** (−3.29% on 5 days), **ANET** (−5.12% on 5 days), **META**
  (−4.61% / −7.27%), **GE** (−4.37% / −3.17%), **CAT** (−1.60% / −8.57%), **BA** (−5.25% / −3.46%), **ARM**
  (−6.69% / −19.53%), **APP** (−13.75% / −28.43%), **VST** (−6.08% / −11.18%), **RBLX** (−3.14% / −17.85%).
- **DIS and V — rejected on the volatility floor, applied to candidates on the same day it is applied to
  holdings.** DIS ATR **2.10%** / median range **1.82%** / only **40% of sessions ≥2%**; V ATR **1.87%** /
  median range **1.65%** / **35% ≥2%**. Both trend fine. **The floor is not a trend rule.**
- **Parked set — all four condition-gated re-enables re-checked, none met.** **XOM** is closest and genuinely
  improved (**+4.28% / +10.84%, ATR 2.22%, $2.23B/day**) but its 08-17 condition was *"only if the oil headline
  regime quiets down"* — with the Iran blockade still live it is **not quiet**; **unmet**. **AVGO −6.97% /
  −5.16%** (chart-gated, unmet). **UNH −3.91% / −5.72%** (unmet). **SPY ATR 0.91%, median range 0.69%, 25% of
  sessions ≥1.25%, 0% ≥2%** — the floor that parked it on Friday is **more** binding today, not less; **unmet**.

### Changes applied to dbo.watchlist
Two parameterized statements, `watchlist` the only table touched, **no DELETEs**. Note lengths were
**pre-checked against `VARCHAR(128)`** (105 and 109 chars) — the truncation failure the 08-21 run hit is now
a guard rather than a lesson:
1. `UPDATE ... SET enabled = 0, note = ?` — **NVDA** (Q2 FY27 earnings Wed 08-26 AMC, options imply ~6%;
   re-enable 08-27 once the print clears).
2. `MERGE ... WHEN NOT MATCHED THEN INSERT` — **DASH** enabled 1 (new row; Alpaca-verified tradable/active).
Both committed in one transaction. Re-read after commit: **18 enabled ≤ 30 ✓**, **31 rows ✓**, **13 parked ✓**.

### Final watchlist
**18 enabled** (≤30 ✓): AAPL ABNB AMD AMZN BABA **DASH** GOOG INTC JPM LLY MSFT MU NFLX PLTR QQQ TSLA TSM UBER.
Parked (13): AVGO BIRD C COST ENPH **NVDA** QCOM SE SPY UNH WMT WPM XOM.
**Service restarted (required — the table changed) and verified, not assumed:** `is-active` → **active**,
**MainPID 1622230**, `ActiveEnterTimestamp` **2026-08-24 11:37:11 UTC**, **NRestarts=0**. Journald confirms the
banner *"Watchlist (dbo.watchlist): AAPL, ABNB, AMD, AMZN, BABA, DASH, GOOG, INTC, JPM, LLY, MSFT, MU, NFLX,
PLTR, QQQ, TSLA, TSM, UBER"* — **DASH present, NVDA absent** — **warmup primed 18/18**, the IEX stream
subscribed to exactly those 18, account `PA34DFFLTHRT` reconciled at equity 9089.13 with **no open positions**,
and **0 WARNING-or-above lines** in the 20 lines since start.
🔒 Locked: **none (0 positions, 0 open orders)**.
**Ops note, benign but recorded:** the *pre-restart* process logged a `ValueError: connection limit exceeded` on
a websocket reconnect at **07:04:22 UTC** and **reconnected successfully one second later**, outside market
hours. Same class as the two keepalive reconnects the 08-21 weekly logged. **On the old PID, not the current
one; no action.**
**Upcoming: NVDA re-enable 08-27 (after the 08-26 AMC print) · core PCE + Q2 GDP Wed 08-26 · AAPL and JPM
dead-signal tests 08-27 · INTC on-notice re-check 08-27 · Jackson Hole 08-27→29 (Warsh Fri 10:00 ET) · MRVL
and SNOW re-screen after their prints · CRM add after 08-26 · GOOG dead-signal test 08-31 · AMZN re-check
09-02 · BABA 09-09 (and see the 50MA trigger above, which may fire first) · AMD 09-12 · AVGO, UNH, XOM and SPY
re-enables are condition-gated, not dated.**

### Perplexity `sonar` — run 16: thinnest ticker layer yet, and it missed the day's biggest board event
**16 of 18 names returned *"no specific overnight/pre-market catalyst surfaced"*** — on a morning when the
Alpaca news tape carried **Alibaba pricing a $10B share placement**, a **~$1B Dutch fine report against UBER**,
and a **Cantor reiteration on NVDA**. **It missed the BABA placement entirely**, which is the single most
consequential fact about the board today. It also **gave no futures direction at all** (*"not explicitly
reported"* for both indices) and **mislabelled the Chicago Fed National Activity Index as a market-hours
release** when it prints 08:30 ET, pre-open — an error that would have manufactured a fake in-session event
had it been taken at face value. **Sixteenth consecutive thin-or-wrong run.**
**Credit where it is due, and it is narrow but real:** its pre-market decliner list (**MU −3.3%, AMD −2.0%,
INTC −1.7%, NVDA −0.3/0.5%, TSLA −0.4%**) was directionally consistent with SOX −5% last week and with the
independently-confirmed HOOD +13.7% spike, and **that lead is what sent me to check HOOD and reject it.**
**Standing rule unchanged: lead-generation only, never a regime source, never a clock, never a price.**
WebSearch (futures, NVDA's and DASH's earnings dates, the week's calendar), the Alpaca news tape (50 headlines),
SIP daily bars, `/v2/assets` and journald carried this run.

### Note for the daily review
**Two decisions here are falsifiable tonight and should be scored, not assumed:**
1. **BABA was kept through a −8.57% Friday and a ~3.7% pre-market gap.** If it printed a scored candidate today
   and that candidate went badly, the TSLA-recall precedent deserves re-examination — *priced pre-open* may be
   doing less work for a **structural supply overhang** than it does for a one-off recall. **Check `--refusals`
   for BABA's forward outcomes specifically.**
2. **DASH is the first name added on the volatility floor as a positive screen** rather than the floor being
   used to park something. **Whether it scores at all on day one is the first datapoint on whether the floor
   selects for signal or only against dead names.**
Also: **NVDA is parked, so 08-26's session carries no board exposure to the print** — but the **semi cluster
(AMD, TSM, MU, INTC) will still trade the read-through**, and that is unhedged by design.

---

## 2026-08-25 — Pre-market Research

**One change: SPOT added (18 → 19 enabled). No parks, no re-enables — every dated item on the board falls on
08-27 and not one of them was pulled forward.** Book is CLEAN & FLAT (broker-confirmed **0 positions, 0 open
orders**, equity **$9,089.13**, `last_equity` == `equity` → no overnight marks) → **nothing locked**. BABA's
pre-registered 50MA trigger was checked and **did not fire**. Service restarted clean (warmup 19/19).

### Market context
- **Futures higher, reversing Monday's chip-led slide.** S&P 500 futures **+0.2% to +0.37%**, Nasdaq futures
  **+0.5% to +0.76%** (Perplexity + Benzinga tape, 09:38Z: *"Dow Jones, S&P 500 Futures Advance as Scott Bessent
  Expands Sanctions on Iran"*). Monday closed weak — *"Nasdaq Tumbles 200 Points as Chip Stocks Slide"*, Fear &
  Greed neutral — and QQQ printed a **0% gate duty cycle (0 of 95 candles)**, confirmed in `dbo.market_gate`.
- **⚠️ In-session data cluster at 10:00 ET, landing exactly when `ENTRY_START` lifts:** Conference Board
  **Consumer Confidence (Aug)**, **New Home Sales (Jul)** and the **Richmond Fed Manufacturing Index (Aug)** all
  print at 10:00 ET. Case-Shiller 09:00 ET is pre-open; a **2-year note auction** hits 13:00 ET. The bot's first
  eligible entry candle of the day is therefore a data candle — worth watching, not worth acting on in advance.
- **The week's pivot is still Wednesday: NVDA Q2 FY27 AMC + July core PCE 08:30 ET.** Jackson Hole runs
  **08-27→29**, Chair Warsh keynote **Fri 08-28 10:00 ET**. NVDA remains parked, so the board carries **no direct
  exposure to the print**; **AMD, TSM, MU and INTC trade the read-through unhedged, by design**.
- **No enabled name reports today.** The day's earnings event is **INTU (today AMC)** — which is not on the board
  and, as it turns out, was the screen's strongest-looking add candidate (see rejections).
- Headline flow, none of it decision-changing: a proposed **>$100k H-1B fee** (AMZN/GOOG/MSFT/META), a **TSLA
  Cybertruck price hike >7%**, **JPM** easing share-backed lending for AI wealth, **AAPL** readying a new Mac mini.
  Same class as the TSLA recall (08-21) and the UBER Dutch fine (08-24): **priced pre-open, not a scheduled
  binary, and the bot never holds overnight.** Logged, not acted on.

### Carried from daily review (08-24 EOD)
- **"No watchlist change is indicated by today's session, and the board is not the problem"** — honored. The
  liveness check below independently confirms it, and **no symbol was parked today**.
- **"BABA's 50MA trigger did not fire… check the close before acting either way"** → checked. BABA closed
  **118.47**, **+3.50% above its 50MA** (−4.85% vs 20MA). **The two-leg trend rule does not fire. Kept on the
  rule**, exactly as pre-registered on 08-24 so it could not be rationalised either way afterwards.
- **"DASH answered its day-one question emphatically"** (3 candidates, best mover on the board +3.87%) → kept,
  and it is the direct precedent for today's add.
- **Dated items due 08-27 — NVDA re-enable, AAPL and JPM dead-signal tests, INTC on-notice re-check — all left
  dated.** Two of them (INTC, JPM) were tempting today. Neither was pulled forward.

### Watchlist review
**Liveness check first, because it governs how much churn is warranted: all 18 enabled names produced scored
refusals in the last 5 sessions.** GOOG 11 · BABA 10 · NFLX 9 · DASH 8 · MSFT 6 · MU/PLTR/TSM/AMZN 5 · AMD/TSLA 3
· LLY/UBER/QQQ/AAPL/INTC 2 · JPM/ABNB 1. **Every name is reaching the scorer.** There is no dead weight to cut,
which is why today's work is one add and nothing else.

**⚠️ INTC — kept, date honoured, and it is again the worst chart on the board.** **−8.61% vs 20MA / −18.89% vs
50MA, −15.68% over 5 days** — deteriorated from 08-24's −5.88%/−16.74%/−12.13%. Worst 14-day P&L on the board
(**−$40.48 / 4 trades**). **The trend leg fires emphatically; the second leg still fails** — it last traded
**08-17 (8 days)**, well short of the ~30-day dead-signal bar, and it printed 2 refusals in 5 sessions. **Its
re-check is dated 08-27 and I am honouring it**, the same way 08-20, 08-21 and 08-24 did. Two independent reasons
not to pull it forward: it is the **#2 all-time earner (+$150.78 / 24 trades)** at $9.86B/day, and it carries a
**fresh positive catalyst this morning** — *"Intel Unveils Next-Gen AI Processors to Drive Enterprise and Data
Center Growth"* (10:54Z). **Parking a name on a chart rule that does not fire, on the morning it gets a product
catalyst, is the exact error this log refused on AVGO (08-18), INTC (08-20) and BABA (08-24). Still flagged as
the most likely park of the week.**

**⚠️ JPM — kept, date honoured, and it has quietly become the weakest name on the volatility floor.** **ATR
1.68%, median session range 1.41%, only 75% of 20 sessions ≥1.25% and 20% ≥2%** — the 1.25% trail is at the
*median* session, which is the shape that got SPY parked on 08-21 (ATR 0.91%, 25% ≥1.25%). It has **not traded in
29 days**, is **all-time −$51.50 on 9 trades**, and produced **1 refusal in 5 sessions — joint-fewest on the
board**. **But its trend leg fails** (−0.20% vs 20MA, **+3.36% vs 50MA** — above one MA) and its dead-signal test
is **dated 08-27**, when the clock reads 31 days. **Kept for two more sessions on the rule. It is now the second
candidate for the week's park, alongside INTC, and Thursday will settle both.**

**✅ AMD — kept, and the tape moved in its favour.** Below both MAs (**−4.69% / −10.37%, −9.73% on 5 days**) so
the trend leg fires, but it last traded **08-13 (12 days)** — second leg fails — and its re-check is **dated
09-12**. This morning **Raymond James upgraded it to Strong Buy, PT $641** (09:54Z). ATR 5.19%, $11.86B/day.

**✅ MU — the board's liquidity anchor, unchanged.** **$33.52B/day**, ATR 6.71%, median range 5.36%, +1.53% /
−5.45%. Mizuho **maintained Outperform, trimmed PT to $1,300** (11:23Z) — an analyst action, not a binary; Micron
does not report until late September. **#1 all-time earner (+$189.55 / 25 trades).**

**🔒 QQQ — structurally locked, restated because its own trade record keeps arguing for a park.** ATR **1.39%**,
median range **1.17%**, only **45% of sessions ≥1.25%**, and **42 days since its last trade** — on the 08-21
volatility floor it is a park candidate and **it must still never be parked**: it is `MARKET_FILTER_SYMBOL`, and
removing it makes the market gate **fail OPEN**, silently switching off the bot's best-evidenced edge (now eight
agreeing replay windows). On merit it is also the best record on the board: **7 trades, 6 wins, +$80.15**.

**✅ The rest, briefly.** **ABNB** +11.14% / +22.89%, ATR 3.09%, 100%/75% — strongest trend on the board, still
the **thinnest enabled name at $0.91B/day**, on notice for that alone. **PLTR** +10.28% / +25.79%, ATR 4.34%.
**DASH** +8.71% / +18.67%, ATR 3.55%, median range 3.63%, 8 refusals — settling in well. **UBER** +6.57% /
+8.45%. **NFLX** +5.60% / +7.40%, 9 refusals despite an all-time −$82.34 — genuinely active. **TSLA** +5.70% /
−4.36%, ATR 3.93%. **LLY** +3.86% / +5.56%, $3.28B/day. **MSFT** +1.95% / +15.54%. **AMZN** −0.32% / +4.77%,
above the 50MA so the trend leg fails, **re-check 09-02** unchanged. **GOOG** −0.90% / −1.52%, **11 refusals —
the most active name on the board for a third session**, **test 08-31**. **AAPL** −0.85% / −0.05%, sitting on
both MAs, 29 days quiet, **test 08-27**. **TSM** −0.91% / −3.34%, 5 refusals. **Liquidity floor clean: no sub-$5
names, no halts, thinnest enabled is ABNB at $0.91B/day.**

### ➕ Add — SPOT, chosen on gap *shape* rather than on trend magnitude
**Verified on Alpaca `/v2/assets`: `tradable: true`, `status: active`, NYSE, us_equity.**
- **Trend, both legs, and the most balanced structure of any candidate screened: +6.20% vs 20MA, +10.35% vs
  50MA** — a **4.15pp** gap between the legs, against DASH's 9.5pp at its add and NOW's 11.3pp (thrice-rejected).
  A tight 20/50 gap is what a *trending* name looks like; a wide one is a V-bounce.
- **Clears the 08-21 volatility floor with room: ATR 3.86%, median session range 3.86% — 3× the 1.25% trail —
  and 100% of the last 20 sessions ranged ≥1.25% *and* ≥2%.**
- **Liquidity $1.09B/day median — it does not become the new thinnest name**, sitting above both DASH ($0.89B)
  and ABNB ($0.91B). At MIN_ALLOC 0.05 × $36.4k buying power it sizes to **3 whole shares at $537.84**, clear of
  the sub-1-share skip.
- **Event calendar clear.** Q2 reported **2026-08-04** (EPS $2.61 vs $2.76 est, rev €4.78B, MAU 777M +12%,
  Premium 300M — shares fell ~5.9%); **next report 10-27**, ~9 weeks out. Same standard DASH, LLY and UBER were
  added on. **Verified by WebSearch, not assumed** — several trackers still stale-list 08-04 as "next".
- **The decisive test, and it is the one HOOD failed yesterday: is this a trend or a gap?** Nine sessions of
  daily bars, **largest single-day gap +1.6%**; the up-days are **+4.8% / +3.3% closes built intraday**, not
  overnight. **This is accumulation, not a headline spike** — the opposite of the condition that concentrated
  this bot's lifetime loss (IMP-017).
- **Why this name on this week:** the board carries **4 enabled semis into an NVDA print**. SPOT is a
  **consumer/media platform** — the third after UBER and DASH — uncorrelated to both the Wednesday print and the
  rates move driving the tape.

**Rejected on fresh evidence:**
- **INTU — rejected on a verified date, and it is the day's important rejection.** It screened as the strongest
  new name on the board (**+9.58% vs 20MA / +22.82% vs 50MA, ATR 3.62%, median range 3.69%, 100% ≥2%,
  $1.19B/day, +10.2% on 5 days**) — **because it reports fiscal Q4 TODAY after the close** (confirmed:
  Intuit press release, results 08-25 post-close, call 4:30pm ET; Street $3.59 EPS / $4.27B rev; the tape carried
  *"Intuit Could Swing By $8.94 Billion After Earnings"*). **A 20.8%-in-a-month chart into a same-day binary is
  the worst possible add.** Re-screen after the print.
- **MRK, NEM and FCX — rejected as gap-driven, on the HOOD/IMP-017 precedent.** All three screen beautifully and
  all three are one overnight print wearing a trend: **MRK +12.6% on a +8.7% gap (08-19)**, **NEM +7.8% on a
  +6.8% gap (08-19)**, **FCX +7.6% on a +4.5% gap (08-21)**. **A 1-min ribbon cross cannot capture a move that
  already happened overnight.** NEM ($0.82B) and FCX ($0.84B) would also both have become the thinnest name.
- **ADBE and BKNG — rejected on the NOW shape rule, applied to new names as well as to NOW itself.** ADBE
  **+5.29% vs 20MA against +18.12% vs 50MA (12.8pp — wider than the gap NOW was rejected on)**; BKNG 9.4pp with
  a **flat 10-day return (+0.23%)**. Both trend; neither trends *evenly*.
- **NOW — rejected a fourth time, and the stated re-screen condition moved the wrong way.** 08-24 said *"re-screen
  when the 20/50 gap compresses"*: it was 10.84pp, it is now **11.26pp** (+5.77% / +17.03%). **It widened.**
- **MSTR (+22.9% / +22.8%) and COIN (+14.8% / +13.0%) — rejected on the 08-21 crypto-beta rule**, applied again
  without re-litigation despite both screening near the top. **HOOD** — rejected yesterday on its +13.7% crypto
  headline spike; **nothing new refutes it**, and its 50MA leg has already decayed to +3.07%. **SMCI** — still
  erratic rather than trending (**−8.12% on 5 days** against +11.79% on 10).
- **CRM — still off the table until after its 08-26 print** (it screens well: +7.57% / +19.16%, $2.36B/day; the
  08-24 note *"CRM add after 08-26"* stands). **SNOW** and **MRVL** likewise report this week.
- **Parked set — all condition-gated re-enables re-checked, none met.** **XOM** is again the closest and its
  chart is now genuinely good (**+3.31% / +9.87%, ATR 2.15%, $2.25B/day**) — but its 08-17 condition is *"only if
  the oil headline regime quiets down"*, and **this morning's tape leads with Bessent expanding Iran sanctions**.
  **Explicitly unmet, for the second run in a row, on the stated condition rather than on the chart.**
  **AVGO** −9.14% / −7.53% · **UNH** −1.55% / −3.60% · **WMT** −4.87% / −6.02% · **QCOM** −0.94% / −10.76% ·
  **C** −2.07% / −3.82% — all chart-gated, all unmet. **COST** is above both MAs (+1.82% / +2.45%) but **fails
  the volatility floor** (ATR 2.01%, median range 1.74%, only 30% of sessions ≥2%) — the floor is not a trend
  rule, and it is applied to re-enables the same way it is applied to adds. **SPY** ATR **0.76%**, median range
  **0.62%**, **20% ≥1.25%, 0% ≥2%** — **worse than when it was parked**, not better. **SE** $0.47B/day, still
  half the liquidity of the thinnest enabled name. **NVDA** is dated 08-27 **and reports tomorrow AMC** — it
  stays parked.

### Changes applied to dbo.watchlist
**One parameterized statement**, `watchlist` the only table touched, **no DELETEs**. Note length **pre-checked
against `VARCHAR(128)`** (114 chars):
1. `MERGE ... WHEN NOT MATCHED THEN INSERT` — **SPOT** enabled 1 (new row; Alpaca-verified tradable/active).
Committed in one transaction. Re-read after commit: **19 enabled ≤ 30 ✓**, **32 rows ✓**, **13 parked ✓**.

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMZN BABA DASH GOOG INTC JPM LLY MSFT MU NFLX PLTR QQQ **SPOT** TSLA TSM
UBER. Parked (13): AVGO BIRD C COST ENPH NVDA QCOM SE SPY UNH WMT WPM XOM.
**Service restarted (required — the table changed) and verified, not assumed:** `is-active` → **active**,
**MainPID 1701050**, `ActiveEnterTimestamp` **2026-08-25 11:37:01 UTC**, **NRestarts=0**. Journald confirms the
banner *"Watchlist (dbo.watchlist): AAPL, ABNB, AMD, AMZN, BABA, DASH, GOOG, INTC, JPM, LLY, MSFT, MU, NFLX,
PLTR, QQQ, SPOT, TSLA, TSM, UBER"* — **SPOT present, NVDA absent** — **warmup primed 19/19**, the IEX stream
subscribed to exactly those 19, account `PA34DFFLTHRT` reconciled at equity 9089.13 with **no open positions**,
and **0 WARNING-or-above lines** since start. IMP-034's weights are live in this process (crossover 39 / trend 26
/ rsi 20 / volume 0 / volatility 15).
🔒 Locked: **none (0 positions, 0 open orders)**.
**Upcoming: NVDA re-enable 08-27 (after tomorrow's AMC print) · core PCE + Q2 GDP 2nd est. Wed 08-26 · AAPL and
JPM dead-signal tests 08-27 · INTC on-notice re-check 08-27 · Jackson Hole 08-27→29 (Warsh Fri 08-28 10:00 ET) ·
CRM add after 08-26 · INTU re-screen after tonight's print · MRVL and SNOW re-screen after theirs · GOOG
dead-signal test 08-31 · AMZN re-check 09-02 · BABA 09-09 · AMD 09-12 · AVGO, UNH, XOM, COST, SPY and SE
re-enables are condition-gated, not dated.**

### Perplexity `sonar` — run 17: best macro layer in weeks, and it still missed the one fact that changed a decision
**Credit, and it is more than usual:** it gave a **real futures direction for the first time in several runs**
(S&P +0.2–0.37%, Nasdaq +0.5–0.76%, both independently corroborated), and it **correctly identified the 10:00 ET
Consumer Confidence / New Home Sales / Richmond Fed cluster as market-hours releases** — the exact class of call
it got backwards on 08-24 when it mislabelled a pre-open print as in-session.
**The failure is the one that matters: 16 of 18 tickers came back "no specific overnight catalyst"**, and it
**never mentioned INTU reporting today** — the single fact that removed the day's best-screening add candidate.
It also missed the **AMD Strong Buy upgrade** and the **INTC AI-processor launch**, both on the Alpaca tape
before 11:00Z. **Seventeenth consecutive thin-or-wrong ticker layer. Standing rule unchanged: lead-generation
only, never a regime source, never a clock, never an earnings calendar.** WebSearch (INTU and SPOT earnings
dates, futures, today's economic calendar), the Alpaca news tape (50 headlines), SIP daily bars, `/v2/assets`,
`dbo.entry_refusals`, `dbo.market_gate` and journald carried this run.

### Note for the daily review
**Three things are falsifiable tonight and should be scored, not assumed:**
1. **SPOT is the second consecutive add on the volatility floor and the first selected primarily on *gap shape*
   (no daily gap >1.6% in nine sessions).** DASH scored 3 candidates on day one and was the day's best mover.
   **Does SPOT print a scored candidate on day one?** If the gap-shape screen is doing real work, it should
   behave like DASH rather than like a stretched name.
2. **The 10:00 ET data cluster lands exactly on `ENTRY_START`.** The bot's first eligible candle of the day is a
   data-reaction candle. **Check whether the 14:00–14:30 UTC refusals carry unusually wide `ribbon_spread_pct`**
   — if a macro print reliably widens ribbons at the exact moment entries unlock, that is a structural fact about
   this bot's day worth knowing, in either direction.
3. **INTC and JPM both come due 08-27 and both got worse today** — INTC on the chart (−18.89% vs 50MA, −15.68%
   on 5 days), JPM on the volatility floor (median range 1.41%, 20% of sessions ≥2%, 1 refusal in 5 sessions).
   **Two parks were deliberately not pulled forward. If either produced a bad scored candidate today, that is
   evidence the dated-test discipline is costing money and it should be written up, not smoothed over.**

---

## 2026-08-26 — Pre-market Research

**One change: AMGN added (19 → 20 enabled). No parks, no re-enables — INTC and JPM are dated 08-27 and were
honoured for a fourth consecutive run.** Book is CLEAN & FLAT (broker-confirmed **0 positions, 0 open orders**,
equity **$9,089.13**, `last_equity` == `equity` == `cash` → no overnight marks) → **nothing locked**. NVDA
reports **tonight AMC** and has been parked since 08-24, so the board carries **no direct exposure to the
print**. Service restarted clean (warmup 20/20).

### Market context
- **Futures flat-to-mixed ahead of the week's two events.** Dow futures higher, **S&P −0.07% to −0.13%**,
  **Nasdaq −0.18% to −0.29%**; ETF proxies **SPY −0.04% at $765.63, QQQ −0.13% at $709.83**. **NVDA +0.3%
  pre-market, MU −0.7%, SMH +0.22%** — the tape is in wait-and-see, not risk-off. Gold −0.95%, crude −1.17%.
- **⚠️ The macro is heavy but ALL of it is 08:30 ET — pre-open, not in-session:** July **durable goods**, the
  **Q2 GDP second estimate**, and **personal income/spending carrying the July PCE deflator** (core PCE
  consensus **3.3%, unchanged**). **There is no 10:00 ET cluster today** — that was yesterday's Consumer
  Confidence / New Home Sales / Richmond Fed. **The bot's first eligible candle at `ENTRY_START` is therefore
  a normal candle today, which makes this the clean control session for the 08-25 review's item 2.**
- **The pivot is tonight: NVDA Q2 FY27 after the close.** Options are priced for the quietest NVDA reaction in
  years. **NVDA is parked (dated re-enable 08-27); AMD, TSM, MU and INTC trade the read-through unhedged, by
  design** — and that read-through lands on **08-27's open**, not today's session, because the bot flattens
  every close. **Jackson Hole 08-27→29, Warsh keynote Fri 08-28 10:00 ET.**
- **No enabled name reports today.** Today's prints are **CRWD and CRM, both AMC**, neither on the board.
- **INTU −11.8% pre-market** — upbeat Q4, **FY27 guidance below estimates**. **ZM −5.2%** on soft Q3 guidance.
- Headline flow, none of it decision-changing: MSFT/HUMAIN AI collaboration, AAPL's new Mac mini + Mac Studio,
  a Reuters report on Moonshot revenue-sharing talks with AMZN/GOOG/MSFT, LLY real-world Zepbound retention
  data, a Bill Gates AI-jobs warning tagged PLTR. **Priced pre-open, no scheduled binary, no overnight hold.**

### Carried from daily review (08-25 EOD)
- **"No watchlist change is indicated, and the board is not the problem"** — the *park* side honoured in full:
  **no symbol was parked today**, and the liveness check below independently confirms it.
- **"Does SPOT print a scored candidate on day one?" — YES, and this is the finding that drove today's work.**
  SPOT produced **3 scored refusals on day one** (one gate veto at conf 70.9, two on confidence 59.6 / 56.3)
  and was **the session's best mover at +3.64%**. **The gap-shape screen is now 2 for 2** — DASH scored 3 on
  day one and was that day's best mover; SPOT did the same. That is why the same screen was run again today
  and why its output was acted on rather than merely logged.
- **"The 10:00 ET data cluster lands exactly on `ENTRY_START`"** → **the confound is absent today** (all
  releases 08:30 ET). Flagged forward as a controlled comparison rather than acted on.
- **"INTC and JPM both come due 08-27 and both got worse"** → **both left dated.** Neither pulled forward,
  for the fourth run in a row.

### Watchlist review
**Liveness check first: 144 scored refusals across 21 symbols over the last 5 instrumented sessions (08-19,
08-20, 08-21, 08-24, 08-25), and every one of the 19 previously-enabled names appears.** NFLX 16 · MSFT 14 ·
BABA 13 · DASH 13 · GOOG 13 · PLTR 10 · UBER 10 · AMD 9 · TSLA 8 · TSM 6 · MU 6 · AMZN 6 · LLY 3 · AAPL 3 ·
SPOT 3 · QQQ 2 · INTC 2 · JPM 1 · ABNB 1. **Everything is reaching the scorer; there is no dead weight to cut.**
Second consecutive session where the board is demonstrably not the constraint — hence one add and nothing else.

**⚠️ INTC — kept, date honoured, still the worst chart on the board.** **−8.43% vs 20MA / −18.12% vs 50MA,
−9.52% over 5 days**, ATR 5.91%. Worst 14-day P&L on the board (**−$40.48 / 4 trades**). **The trend leg fires;
the dead-signal leg still fails** — it last traded **08-17 (9 days)** against the ~30-day bar, and it printed 2
refusals in 5 sessions. **Its re-check is dated 08-27 and I am honouring it**, as 08-20, 08-21, 08-24 and 08-25
did. It remains the **#2 all-time earner (+$150.78 / 24 trades)** at $9.80B/day. **Still the most likely park of
the week — and note it sits squarely in tonight's NVDA blast radius, which is a reason to decide tomorrow with
the print in hand rather than today without it.**

**⚠️ JPM — kept, date honoured, and it is still the weakest name on the volatility floor.** **ATR 1.53%, median
session range 1.36%, only 70% of 20 sessions ≥1.25% and 20% ≥2%** — the 1.25% trail sits essentially at the
median session, the shape that got SPY parked on 08-21. **30 days since its last trade**, all-time **−$51.50 on
9 trades**, and **1 refusal in 5 sessions — fewest on the board**. **But its trend leg fails: −0.10% vs 20MA
against +3.23% vs 50MA** — still above one MA. Dead-signal test **dated 08-27**, when the clock reads 31 days.
**Kept one more session on the rule. INTC and JPM both settle tomorrow.**

**🔒 QQQ — structurally locked, restated because its own record keeps arguing for a park.** ATR **1.18%**,
median range **1.05%**, only **40% of sessions ≥1.25%**, and **43 days since its last trade** — on the 08-21
volatility floor it is a park candidate and **it must never be parked**: it is `MARKET_FILTER_SYMBOL`, and
removing it makes the market gate **fail OPEN**, silently disabling the bot's best-evidenced edge. On merit it
is also the best record on the board: **7 trades, 6 wins, +$80.15**. Gate duty cycle stays **bimodal** —
`dbo.market_gate`: 08-21 **42%**, 08-24 **0%**, 08-25 **42%**.

**✅ AMD — kept, and the upgrade worked.** **−0.26% vs 20MA / −5.85% vs 50MA**, recovered hard from 08-24's
−4.69% / −10.37% on Raymond James' Strong Buy (PT $641). ATR 4.31%, $10.84B/day, 9 refusals. Re-check **09-12**.

**✅ MU — the board's liquidity anchor, unchanged.** **$31.33B/day**, ATR 5.99%, median range 5.15%,
+3.39% / −3.01%. **#1 all-time earner (+$189.55 / 25 trades).** Reports late September, not this week.

**✅ The rest, briefly.** **ABNB** +10.11% / +22.16%, ATR 3.68% — strongest trend on the board and still the
**thinnest enabled name at $0.83B/day**, on notice for that alone. **DASH** +9.83% / +19.94%, 13 refusals —
fully settled in. **SPOT** +8.67% / +13.05%, day-one validated above. **NFLX** +7.83% / +10.33%, **16 refusals —
the most active name on the board**. **UBER** +7.30% / +9.56%, 10 refusals and yesterday's headline near-miss
(conf 68.8, xo 0.23). **PLTR** +6.65% / +22.74%, ATR 4.31%. **TSLA** +5.41% / −3.71%. **LLY** +2.70% / +4.25%,
$3.22B/day. **MSFT** +1.82% / +16.02%, 14 refusals but none close (all on confidence 50–55). **TSM** +0.54% /
−1.59%. **AAPL** −0.51% / −0.31%, sitting on both MAs, 30 days quiet, **test 08-27**. **AMZN** −1.27% / +4.18%,
above the 50MA so the trend leg fails, **re-check 09-02**. **GOOG** −1.41% / −1.80%, 13 refusals, **test 08-31**.
**BABA** −4.24% / +4.22% — below the 20MA but **above the 50MA, so the two-leg rule does not fire**, **09-09**
unchanged. **Liquidity floor clean: no sub-$5 names, no halts, thinnest enabled is ABNB at $0.83B/day.**

### ➕ Add — AMGN, chosen on a 24-session accumulation record rather than a 9-session one
**Verified on Alpaca `/v2/assets`: `tradable: true`, `status: active`, NASDAQ, us_equity.**
- **The decisive test, run over a longer window than any previous add: is this a trend or a gap?**
  **Across 24 sessions the largest single overnight gap is 2.04%**, and the move is carried by **intraday
  closes — o2c +3.20%, +3.68%, +2.82%, +2.57%, +2.43%**. SPOT cleared this on 9 sessions with a 1.6% max gap;
  AMGN clears it on **24 sessions**. **This is accumulation, not a headline spike** — the opposite of the
  condition that concentrated this bot's lifetime loss (IMP-017), and the opposite of MRK/NEM/FCX/HOOD.
- **Trend, both legs, with a tight gap between them: +6.82% vs 20MA, +15.62% vs 50MA** — an **8.80pp** spread,
  **tighter than DASH's 9.5pp at its add** and far tighter than NOW (11.3pp) or ADBE (12.8pp). The 10-day
  return is **+6.74%**, so it does not fail the way BKNG did (9.4pp on a flat +0.23%).
- **Clears the 08-21 volatility floor, but by the smallest margin of any add since the floor was set — and
  that is stated plainly rather than buried: ATR 2.31%, median session range 2.45% (≈2× the 1.25% trail),
  95% of the last 20 sessions ≥1.25%, 75% ≥2%.** That is the **NFLX (2.78% / 95% / 65%) and ABNB (2.92% / 95% /
  70%) band** — both enabled and both productive — and clearly above the **COST band (1.71% / 25% ≥2%)** that
  was rejected on this floor yesterday. It is **not** the SPOT/DASH band (3.9% / 3.4%). **This is a deliberate
  step down the volatility scale and it is the falsifiable part of today's decision.**
- **Liquidity $1.10B/day median — it does not become the new thinnest name**, sitting above ABNB ($0.83B),
  DASH ($0.90B) and SPOT ($1.00B). At MIN_ALLOC 0.05 × $36,356 buying power it sizes to **4 whole shares at
  $442.24**, clear of the sub-1-share skip across the whole confidence range.
- **Event calendar clear, verified rather than assumed.** Q2 reported late July / early August 2026; **the Q3
  report is expected early November** (Amgen's historical pattern, and no confirmed date is out) — ~10 weeks
  away. Same standard DASH, LLY, UBER and SPOT were added on. **Only one AMGN headline in five days**, and it
  was a retrospective puff piece.
- **Why this name on this day:** the board carries **4 enabled semis into tonight's NVDA print**. AMGN is
  **healthcare** — the first non-tech/non-consumer add in weeks and the second pharma after LLY — uncorrelated
  to both tonight's print and the rates move driving the tape.

**Rejected on fresh evidence:**
- **MELI — the day's important rejection, and it lost on sizing rather than on the chart.** It screened as the
  **best-shaped candidate of the entire run**: **+6.46% vs 20MA / +10.70% vs 50MA (4.24pp — tighter than
  SPOT's 4.15pp-class shape), ATR 3.95%, median range 2.95%, 100% ≥1.25%, 90% ≥2%, max gap 1.15%, $0.85B/day.**
  **It fails the sub-1-share test at $1,997/share:** MIN_ALLOC 0.05 × $36,356 = **$1,817.83 → qty 0**, so
  **every entry below roughly conf 64 is silently skipped**, and even at conf 100 it sizes to **1 share**.
  **Rejected on exactly the test SPOT was cleared on** — the rule cuts both ways or it is not a rule.
- **VRTX — rejected on two independent counts.** It screens beautifully (**+7.95% / +11.67%, 3.7pp, ATR
  3.02%**) but the move is carried by an **+8.75% overnight gap on 08-10** (HOOD/MRK/NEM precedent), and at
  **$0.57B/day it would become the new thinnest name** by a wide margin.
- **DIS — rejected on the volatility floor, applied consistently.** Its shape is genuinely good (**+7.41% /
  +10.93%, 3.5pp legs, max gap 0.67%, $0.88B/day**) but **ATR 2.02%, median range 1.76%, only 40% of sessions
  ≥2%** — that is the **COST band rejected on this same floor yesterday**. Closest thing to a second add today
  and refused on a stated rule.
- **SHOP — rejected on the BKNG shape.** **+7.41% / +19.95% = 12.5pp** with a **flat 10-day return (+0.83%)**.
  A wide 20/50 gap plus a flat recent tape is a V-bounce, not a trend, however clean the gaps look (1.25%).
- **NOW — rejected a fifth time, and its stated re-screen condition moved the wrong way again.** The 20/50 gap
  was 10.84pp (08-24), 11.26pp (08-25), and is now **11.34pp**. **It has widened on three consecutive runs.**
  **ADBE** 12.5pp and **BKNG** 9.2pp on a +0.43% 10-day return — both re-rejected on the same rule.
- **INTU — yesterday's rejection paid inside one session.** Refused on 08-25 for reporting into a same-day
  binary while screening as the strongest chart available; it is **−11.8% pre-market** on FY27 guidance below
  estimates. **Re-screen only once the post-print tape settles.**
- **CRM, CRWD, SNOW, MRVL — all off the table on earnings timing.** CRM and CRWD report **tonight AMC** (the
  standing "CRM add after 08-26" note now means *after tonight's print*); SNOW and MRVL report Thursday. MRVL
  also carries an **11.17% max gap**, so it would likely fail the gap-shape test regardless.
- **MSTR (+25.20% / +26.97%), COIN (+18.93% / +17.39%) and HOOD (+17.69% / +11.07%) — rejected on the 08-21
  crypto-beta rule**, re-applied without re-litigation despite screening at the very top; all three also carry
  **6–9% max overnight gaps**, so they fail the gap-shape test independently. **SMCI** max gap **10.73%**,
  still erratic rather than trending.
- **The wider screen produced nothing else.** 60 names screened across two batches. **META** is the most
  liquid unenabled mega-cap and **does not screen — it is below both MAs (−0.61% / −3.85%)**. ORCL (+1.12% /
  +0.66%, no trend), ANET (−3.49% on 10 days), GS/MS/SCHW (vol floor or flat), PANW, APP, DDOG, TTD, ZS,
  LULU, NKE, DAL, RCL, RBLX, CVNA and the power/industrial complex (GEV, VST, CEG, GE, ETN, URI, CAT) all fail
  on at least one of: **below a moving average, liquidity under the ABNB floor, or the volatility floor.**
- **Parked set — all condition-gated re-enables re-checked, none met.** **XOM** failed on *both* halves this
  time: its 08-17 condition is *"only if the oil headline regime quiets down"* and the tape still leads with
  Iran sanctions and Hormuz mine-clearing (crude −1.17%), **and its chart deteriorated** from +3.31% / +9.87%
  yesterday to **+0.92% / +7.39% with a −2.97% 5-day**. **WPM** screens spectacularly (**+23.15% / +35.44%**)
  and is refused on **the exact reason it was parked — $0.25B/day, the thinnest name in the whole 60-name
  screen.** A precious-metals momentum spike does not fix a liquidity park. **SE** +5.67% / +15.34%, chart now
  genuinely good, **$0.47B/day — still about half ABNB**. **COST** +0.66% / +1.30% fails the vol floor (ATR
  1.80%, 25% ≥2%). **SPY** ATR **0.63%**, **20% ≥1.25%, 0% ≥2%** — unmet and still deteriorating. **QCOM**
  +0.40% / −9.09% · **C** −0.96% / −2.61% · **UNH** −1.70% / −4.07% · **WMT** −5.54% / −6.75% · **AVGO**
  −9.37% / −7.93% · **ENPH** −4.71% / −11.92% · **BIRD** $2.37 (sub-$5) — all chart- or floor-gated, all unmet.
  **NVDA** −0.71% / +2.52% **reports tonight AMC** and is dated 08-27 — it stays parked.

### Changes applied to dbo.watchlist
**One parameterized statement**, `watchlist` the only table touched, **no DELETEs**. Note length **pre-checked
against `VARCHAR(128)`** (123 chars):
1. `MERGE ... WHEN NOT MATCHED THEN INSERT` — **AMGN** enabled 1 (new row; Alpaca-verified tradable/active).
Committed in one transaction. Re-read after commit: **20 enabled ≤ 30 ✓**, **33 rows ✓**, **13 parked ✓**.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD **AMGN** AMZN BABA DASH GOOG INTC JPM LLY MSFT MU NFLX PLTR QQQ SPOT
TSLA TSM UBER. Parked (13): AVGO BIRD C COST ENPH NVDA QCOM SE SPY UNH WMT WPM XOM.
**Service restarted (required — the table changed) and verified, not assumed:** `is-active` → **active**,
**MainPID 1781073**, `ActiveEnterTimestamp` **2026-08-26 11:38:24 UTC**, **NRestarts=0**. Journald confirms the
banner *"Watchlist (dbo.watchlist): AAPL, ABNB, AMD, AMGN, AMZN, BABA, DASH, GOOG, INTC, JPM, LLY, MSFT, MU,
NFLX, PLTR, QQQ, SPOT, TSLA, TSM, UBER"* — **AMGN present, NVDA absent** — **warmup primed 20/20**, the IEX
stream subscribed to exactly those 20, account `PA34DFFLTHRT` reconciled at equity 9089.13 with **no open
positions**, and **0 WARNING-or-above lines** since start.
🔒 Locked: **none (0 positions, 0 open orders)**.
**Upcoming: NVDA re-enable 08-27 (after tonight's AMC print) · AAPL and JPM dead-signal tests 08-27 · INTC
on-notice re-check 08-27 · Jackson Hole 08-27→29 (Warsh Fri 08-28 10:00 ET) · CRM and CRWD re-screen after
tonight's prints · MRVL and SNOW after Thursday's · INTU re-screen once the −11.8% settles · GOOG dead-signal
test 08-31 · AMZN re-check 09-02 · BABA 09-09 · AMD 09-12 · AVGO, UNH, XOM, COST, SPY, SE and WPM re-enables
are condition-gated, not dated.**

### Perplexity `sonar` — run 19: thinner than yesterday, and wrong on the week's single most important fact
**The failure is not thinness this time, it is a false statement about a scheduled binary.** It reported
**NVDA "is listed as reporting before the open"**. **NVDA reports AFTER today's close** — verified against the
Yahoo Finance and Benzinga pre-market tape. Acting on that claim would have inverted the entire risk picture
for the day. It also returned **"no specific catalyst identified" for 18 of 19 tickers**, and claimed **"no
U.S. economic releases during market hours were identified"** — accidentally correct today, but arrived at
with no evidence and while **never mentioning the 08:30 ET PCE / Q2 GDP / durable-goods slate at all**. It
missed **INTU −11.8%**, **ZM −5.2%** and **CRWD's after-close report**. **Credit where due: its futures
direction was right** (S&P −0.07/−0.13%, Nasdaq −0.18/−0.29%, corroborated). **Nineteenth consecutive
thin-or-wrong ticker layer, and the first to state a false earnings time for a name this board actively
manages. Standing rule reaffirmed and now load-bearing: lead-generation only, never a regime source, never a
clock, never an earnings calendar.** WebSearch (NVDA timing, AMGN earnings, today's economic calendar,
futures), the Alpaca news tape (36 headlines), SIP daily bars over 60 names, `/v2/assets`, `dbo.trades`,
`dbo.entry_refusals`, `dbo.market_gate` and journald carried this run.

### Note for the daily review
**Three things are falsifiable tonight and should be scored, not assumed:**
1. **AMGN is the lowest-volatility add since the 08-21 floor was set** (median session range **2.45%** against
   SPOT's 3.91% and DASH's 3.44%) and the **first selected on a 24-session accumulation record** rather than a
   9-session one. DASH and SPOT each printed **3 scored candidates on day one**. **Does AMGN?** If it prints
   zero while the rest of the board is active, the volatility floor is being stretched too far and today's add
   was a mistake — **say so rather than waiting for a 30-day dead-signal clock to say it.**
2. **Today is the clean control for the 08-25 `ENTRY_START` question.** Yesterday's 10:00 ET data cluster landed
   exactly on the first eligible candle; **today all macro was 08:30 ET and there was no in-session release.**
   Same board, same config. **Compare the 14:00–14:30 UTC refusals' `ribbon_spread_pct` against 08-25's** — if
   they are indistinguishable, the "macro print widens ribbons at unlock" hypothesis is dead and should be
   closed rather than carried.
3. **Tonight's NVDA print makes 08-27 a gap-reaction session for 4 of 20 enabled names.** AMD, TSM, MU and INTC
   are unhedged by design, and the bot's every-close flatten means **there is no overnight exposure — the risk
   is entirely in tomorrow's open, not tonight.** INTC is already the weakest chart on the board (−18.12% vs
   50MA) **and its on-notice re-check falls on exactly that session.** Note tonight whether the semis' behaviour
   argues for deciding INTC on 08-27 or deferring it one more day.
4. **INTC and JPM were again not pulled forward — fourth consecutive run honouring a date.** Both settle
   tomorrow. **If either produced a bad scored candidate today, that is evidence the dated-test discipline is
   costing money and it should be written up, not smoothed over.**

---

## 2026-08-27 — Pre-market Research

**All four dated items came due today and all four were settled with evidence, not deferred a fifth time:
NVDA re-enabled, JPM parked, AAPL and INTC kept on tests that were actually run and actually failed to fire.
Net 20 → 20 enabled.** Book is CLEAN & FLAT (broker-confirmed **0 positions, 0 open orders**, equity
**$9,094.34**, `last_equity == equity == cash` → no overnight marks) → **nothing locked**. **No adds: a
51-name screen produced zero passes**, and IMP-036's first live session is today — adding would confound it.
Service restarted clean (warmup 20/20).

### Market context
- **Risk-on and semi-led, on the back of the print this board has been positioned around for a week.**
  Dow futures **+0.25%**, S&P 500 **+0.35%**, Nasdaq 100 **+0.66%**, Russell 2000 −0.07%. ETF proxies
  **SPY +0.38% at $769.00, QQQ +1.00% at $718.50** — the index gain is concentrated in tech, and the Dow is
  the one that slips.
- **NVDA Q2 FY27 cleared, and cleared decisively: revenue $96.2B vs $92.2B consensus (+106% y/y), non-GAAP
  EPS $2.22 vs ~$2.06–2.09, data centre $89B vs $86.33B (92% of sales), gross margin 75%, and Q3 guidance
  $108B ±2% against ~$104.2B consensus.** CFO Kress put top-five hyperscaler capex at **$1.3T next year vs
  $800B in 2026**. **NVDA is +7.32% pre-market** and is dragging the complex with it — the Alpaca tape's
  own headline is *"Nvidia Stock Climbs Over 7% in Thursday Pre-Market: What's Lifting Micron, Intel and
  Other Chip Stocks"* (tagged AMD, AVGO, INTC, MU, NVDA, TSM). Separately NVDA agreed to acquire
  **Hugging Face for $12.9B**, and AWS committed to **2 million NVDA GPUs**.
- **⚠️ The one genuine two-sided risk today, and it is unscheduled: the Trump administration is weighing a
  new round of sweeping semiconductor tariffs**, reported as potentially hitting AI data-centre servers,
  laptops and consoles (tape tags AAPL, ASML, GOOG, INTC, META, MU; a second story tags AMZN, GOOG, MSFT).
  **This is headline risk, not a scheduled binary** — no halt, no earnings, nothing to park on — but it is
  the reason a semi-heavy board could reverse intraday, and the 5-min gate is the defence.
- **No enabled name reports today.** Today's calendar is **DG, DLTR, BBY, BURL, ULTA, RY, TD** pre-open and
  **MRVL, WDAY, ADSK, AFRM** AMC. **CRM +11.25%** and **CRWD +9.15%** on last night's prints — both off the
  board, both now re-screenable (see rejections).
- **Macro: yesterday's, not today's.** July core PCE landed in line at 0.2% m/m with headline 0.2% topping
  consensus; 10-year **4.66%**, 2-year **4.22%**, and CME FedWatch is pricing a **36.1% chance of a September
  Fed *hike***. **Jackson Hole opens today and runs to Saturday, but Warsh's keynote is FRIDAY 08-28** — so
  today carries **no in-session scheduled release**, same clean structure as yesterday.

### Carried from daily review (08-26 EOD)
- **"Dated items due 08-27: NVDA re-enable, AAPL and JPM dead-signal tests, INTC on-notice re-check"** —
  **all four executed below. None deferred.** This is the fifth consecutive run that a date was honoured and
  the first on which the dates actually came due.
- **"Does AMGN print a scored candidate on day one?" — NO. It printed ZERO, and per the 08-26 review's own
  instruction that is said plainly rather than buried.** See the AMGN section: the stated falsification
  triggered, at n=1, on a day it also had a real positive catalyst. Kept on a short dated test, not parked.
- **"IMP-036 will visibly cut the fill count — that is the change working, not a malfunction."** Noted and
  load-bearing for today's *no-add* decision: today is IMP-036's first live session (it went live on the
  **20:26 UTC** restart, *after* the 08-26 close, so yesterday's refusal population is un-contaminated).
- **"The board is still not the constraint; the tape is"** — independently re-confirmed below.

### Watchlist review
**Liveness check first: 138 scored refusals across 19 symbols over the last 7 days, and every enabled name
except AMGN appears.** MSFT 21 · DASH 14 · GOOG 11 · TSM 10 · UBER 10 · NFLX 9 · AMD 9 · QQQ 8 · PLTR 7 ·
MU 7 · AMZN 5 · BABA 5 · AAPL 5 · SPOT 4 · TSLA 3 · INTC 3 · JPM 3 · LLY 3 · ABNB 1. **Gate duty cycle
08-21 42% · 08-24 0% · 08-25 42% · 08-26 43%.** Third consecutive session confirming the board is not the
binding constraint — which is why today is three dated settlements and **no discretionary churn**.

**➕ NVDA — RE-ENABLED, condition met and verified rather than assumed.** Parked 08-24 solely for the print;
the note read *"re-enable 08-27 once print clears"*. **It cleared, and it beat on every line with guidance
above consensus** (figures above, cross-checked against the CNBC/Fortune coverage and the Alpaca news tape).
**Alpaca `/v2/assets/NVDA`: `tradable: true`, `status: active`, NASDAQ, us_equity, fractionable.** On merit
it is the second-most liquid name on the board at **$24.84B/day** (behind MU's $30.73B), **ATR 2.59%, median
session range 2.18%, 100% of the last 20 sessions ≥1.25% and 60% ≥2%** — comfortably clear of the 08-21
volatility floor. **Gap shape is the cleanest of any semi: max overnight gap 2.32% over 24 sessions.**
All-time **−$16.65 on 13 trades**, essentially flat, so no P&L case against it. At the 08-26 close it was
**−2.74% vs 20MA / +0.92% vs 50MA**; **the +7.3% pre-market puts it back above both.**
**⚠️ Stated honestly: re-enabling into a +7% gap is the exact shape IMP-017 identified as the source of this
bot's lifetime loss — buying a move that has already happened.** The mitigations are structural and were
not chosen for this trade: `ENTRY_START=10:00` blackouts the opening 30 minutes where gap reversals
concentrate, and the 5-min gate must be independently open. **The re-enable is the scheduled one, not a
momentum chase — it would have happened today regardless of the direction of the print.**

**➖ JPM — PARKED. The dated test came due at 31 days and it is the only name on the board that fails three
independent legs at once.** This is the exact SPY precedent from 08-21, leg for leg:
- **Dead-signal leg FIRES: 31 days since its last trade (2026-07-27)**, against the ~30-day bar. Only
  **3 refusals in 7 sessions** — tied for fewest on the board with INTC.
- **Volatility floor FAILS: ATR 1.44%, median session range 1.36%, only 65% of the last 20 sessions ≥1.25%
  and 15% ≥2%.** The **1.25% trail sits essentially on the median session**, so the trail can barely arm.
  For scale: SPY was parked at 0.84% / 0.75% / 25%; every other enabled name is ≥1.77% ATR, and JPM is now
  the lowest-volatility enabled name **other than QQQ, which is structurally locked**.
- **P&L leg FAILS: −$51.50 on 9 trades (3W)** — the second-worst all-time record on the enabled board.
- **Trend leg does NOT fire (−0.32% vs 20MA but +2.96% vs 50MA)** — recorded because it is the leg that kept
  JPM alive for four runs, and it is **not** what parked it today. The park rests on the other three.
- **IMP-036 makes this structural rather than marginal.** Since last night the volatility sub-score rewards
  *range availability* instead of quietness. JPM's tape sits in the dead band by construction, so it now
  forfeits ~15 of 100 points on essentially every candidate. **It was selected under a scoring function that
  no longer exists.** Re-enable is **condition-gated, not dated**: only if ATR returns above ~2% with ≥80%
  of sessions ≥1.25%.

**✅ AAPL — KEPT. The dead-signal test was run and it does NOT fire; this is a pass, not a deferral.**
The clock leg fires (**31 days**, last trade 2026-07-27) but the **trend leg fails outright: +1.03% vs 20MA
AND +0.72% vs 50MA — above both**, exactly the two-leg exemption BABA has been carried on. The rest argues
the same way: **all-time +$57.45 on 10 trades with 7 wins — the best win rate on the enabled board**;
**5 scored refusals in 7 sessions, most recently 08-26**, so it is reaching the scorer; **$13.35B/day**,
ATR 1.90%, median range 1.80%, 85% ≥1.25%. It is tagged in the semiconductor-tariff story but has no
scheduled event. **Clock re-set: next dead-signal test 09-10.**

**✅ INTC — KEPT, and the on-notice re-check was genuinely run rather than waved through.** The 08-26 entry
asked to decide this one "with the print in hand"; the print is in hand and the answer is **keep, on the
rule as this log has always applied it**:
- **Trend leg FIRES, and hard: −7.94% vs 20MA / −16.80% vs 50MA on a −12.59% 10-day return.** Deepest
  downtrend on the board. **This is not disputed and is why it stays on notice.**
- **But every park in this log required a second failing leg, and INTC's second leg does not fail.**
  AVGO parked on trend **+ worst all-time P&L (−$121.38)**; WMT on trend **+ an earnings guide cut + 27
  days**; UNH on trend **+ 31 days**; SPY on the vol floor **+ 56 days + negative P&L**. INTC is the **#2
  all-time earner (+$150.78 on 24 trades, 13W = 54%)**, it **traded 10 days ago (08-17)**, and it has the
  **best range availability on the entire board — ATR 5.45%, median range 4.51%, 100% of sessions ≥2%** at
  **$9.48B/day**. Applying the trend leg alone would be a new, harsher rule invented to fit one symbol.
- **The honest cost of keeping it is stated: −$40.48 over 4 trades in the last 10 days, the worst recent
  P&L on the board.** That is the falsifiable part.
- **IMP-036 cuts toward keeping, not parking.** Last night's change made range availability the scored
  quantity, and INTC has more of it than anything else here except MU. Parking the highest-ATR liquid name
  on the first session of a scoring change that rewards ATR would be premature. **Re-check dated 09-03**,
  and it parks then if the trend leg still fires and the recent P&L has not turned.

**⚠️ AMGN — KEPT on a short dated test, and yesterday's stated falsification is reported as triggered.**
The 08-26 entry set the test explicitly: *"DASH and SPOT each printed 3 scored candidates on day one. Does
AMGN? If it prints zero while the rest of the board is active, the volatility floor is being stretched too
far and today's add was a mistake — say so rather than waiting for a 30-day dead-signal clock to say it."*
**AMGN printed ZERO scored refusals on day one while 19 other names printed 138 over the window and the
gate ran 43% open. The condition triggered. Saying so.** Three things stop this from being a same-day park:
**(1)** n=1 session — DASH and SPOT were validated on n=1 in the *positive* direction, but a single absence
of a fresh ribbon cross is weaker evidence than a presence; **(2)** its chart is intact and improved —
**+5.69% vs 20MA / +14.59% vs 50MA, ATR 2.12%, median range 2.35%, 90% ≥1.25%, 70% ≥2%, $1.08B/day, max gap
2.04%**; **(3)** it has a **real positive catalyst on the tape this morning** — AMGN/AstraZeneca's
**TEZSPIRE met both co-primary and all key secondary endpoints in Phase 3** in eosinophilic esophagitis.
**Test hardened and dated: if AMGN has produced zero scored candidates by 09-02, it is parked and the
volatility floor is re-tightened — no 30-day clock, no further extension.**

**🔒 QQQ — structurally locked, restated.** ATR **1.12%**, median range **0.99%**, only **35% of sessions
≥1.25%**, **44 days since its last trade**. On the 08-21 volatility floor it is a park candidate and **it
must never be parked**: it is `MARKET_FILTER_SYMBOL`, and removing it makes the market gate **fail OPEN**,
silently disabling the bot's best-evidenced edge. On merit it is also the best record on the board:
**7 trades, 6 wins, +$80.15**, and it printed **8 refusals** this week.

**✅ The rest, briefly.** **DASH** +10.31% / +20.84%, ATR 3.43%, 14 refusals — strongest trend on the board
and fully settled in. **SPOT** +7.90% / +12.21%, ATR 3.75%, medRng 3.89%, 100% ≥2%. **PLTR** +7.79% /
+25.37% — yesterday's only fill (+$5.28) and 7 refusals. **NFLX** +6.28% / +9.30%, 9 refusals. **UBER**
+4.31% / +6.86% but **−3.76% o2c yesterday**, 10 refusals. **TSLA** +3.34% / −4.58%, ATR 3.52%. **MU**
+2.86% / −2.14%, **$30.73B/day — the liquidity anchor**, #1 all-time earner, reports late September.
**MSFT** +1.67% / +16.59%, **21 refusals — the most active name on the board**, though the 08-25 review
noted none of them are close. **TSM** +0.09% / −1.42%, 10 refusals. **ABNB** +7.61% / +19.84% and still the
**thinnest enabled name at $0.83B/day**, on notice for that alone — **1 refusal in 7 sessions**, the
quietest enabled name that is not AMGN. **AMZN** −2.19% / +3.75%, above the 50MA so the two-leg rule does
not fire, **re-check 09-02**. **GOOG** −2.68% / −2.85% — **below both MAs, but its dead-signal leg fails
badly (11 refusals, last 08-24)**, so it is a keep; **dead-signal test 08-31** as dated. **BABA** −4.11% /
+4.43%, above the 50MA, **09-09** unchanged. **LLY** −0.90% / +0.41% after **−3.61% yesterday**, ATR 3.40%,
$3.30B/day. **AMD** −0.43% / −5.26%, ATR 4.13%, 9 refusals, gets the NVDA read-through today, re-check
**09-12**. **Liquidity floor clean: no sub-$5 names, no halts, thinnest enabled is ABNB at $0.83B/day.**

### ➕ Adds — NONE, and the screen is reported rather than asserted
**51 candidates screened against the standing floors** (above BOTH MAs · ATR ≥2.3% · median range ≥2.0% ·
≥80% of 20 sessions ≥1.25% · ≥$0.83B/day, the ABNB floor · max 24-session gap ≤4% · 20/50 leg spread ≤9pp ·
positive 10-day return). **Zero passed.** Not one name cleared all eight. Two further reasons make *no add*
the right call today rather than merely the default: **IMP-036's first live session is today**, and the
08-26 review explicitly expects it to cut the fill count — adding a name now would confound the only clean
read of that; and **AMGN's day-one zero is unresolved**, so widening the board before the last add is
adjudicated would compound an error rather than diversify one.
- **CRM (+11.25%) and CRWD (+9.15%) — the standing "re-screen after their prints" note now comes due, and
  both are refused today.** CRM screens **+4.69% / +16.13% = 11.4pp leg spread** (the NOW/ADBE V-bounce
  shape, well outside the 9pp bar) and is **mid-gap this morning**; re-screen once the post-print tape
  settles, exactly as INTU was handled. **MRVL reports AMC tonight** and carries an **11.17% max gap** —
  refused on both counts, unchanged from 08-26.
- **MSTR (+19.84% / +23.53%), COIN (+14.72% / +13.84%) and HOOD (+12.85% / +7.33%) — top of the screen
  again, refused again on the 08-21 crypto-beta rule**, re-applied without re-litigation; all three also
  carry **6.3–8.6% max gaps** and fail the gap-shape test independently.
- **Gap-shape refusals: SHOP 21.65%, NET 11.80%, MRVL 11.17%, CVNA 11.11%, SMCI 10.73%, ANET 10.33%,
  VRTX 8.75%.** SHOP's is the largest in the whole screen.
- **Leg-spread refusals (V-bounce shape): ADBE 12.0pp, CRM 11.4pp, NOW 11.2pp, SHOP 12.3pp, U 23.6pp.**
  **NOW is now refused a sixth time and its stated re-screen condition moved the wrong way for a fourth
  consecutive run** (10.84 → 11.26 → 11.34 → 11.21pp band, still nowhere near 9).
- **Liquidity refusals under the $0.83B ABNB floor: ZS $0.39B, U $0.49B, VRTX $0.57B, PYPL $0.58B, DE
  $0.63B, SBUX $0.65B, CVNA $0.68B, CEG $0.68B, SCHW $0.73B.**
- **Volatility-floor refusals: DIS (ATR 1.99%, medRng 1.88%, 90% ≥1.25%) — closest miss of the run and
  refused on the same floor as 08-26 — plus SCHW (1.95% / 1.67%) and GS (2.17% / 2.20% but below its 50MA).**
- **Below a moving average: SNOW, ZS, NET, GS.** **ORCL** is above both but on a **−2.88% 10-day return**,
  and **BKNG** repeats its 9.5pp-on-flat shape (−1.59% over 10 days). **META** was not re-screened as a
  candidate — it was below both MAs on 08-26 and nothing in today's tape changes that.
- **MELI — re-checked and still refused on sizing, not on chart.** At **$1,950/share**, MIN_ALLOC 0.05 ×
  $36,377 buying power = **$1,818.86 → qty 0**; every entry below ~conf 64 is silently skipped. Same rule
  SPOT was *cleared* on.
- **Parked set — all condition-gated re-enables re-checked, none met.** **WPM** screens spectacularly
  (**+15.34% / +28.39%**) and is refused on **exactly what parked it — $0.27B/day, thinnest name in the
  whole screen**. **SE** +1.72% / +10.87% at **$0.47B/day**, still about half ABNB. **QCOM** +2.12% but
  **−6.70% vs 50MA**. **XOM** −0.66% / +5.51% — below its 20MA, and the oil-headline regime has not quieted
  (Qatar's PM travelling to Tehran). **UNH** −0.36% / −2.95% · **C** −0.96% / −2.27% · **COST** +0.34% /
  +0.94% (ATR 1.70%, 25% ≥2% — vol floor) · **WMT** −6.06% / −7.40% · **AVGO** −9.50% / −8.04% ·
  **ENPH** −2.41% / −8.81% · **SPY** ATR **0.62%, 15% ≥1.25%, 0% ≥2%** — deteriorating further ·
  **BIRD** sub-$5. **All unmet.**

### Changes applied to dbo.watchlist
**Two parameterized `UPDATE`s in one transaction**, `watchlist` the only table touched, **no DELETEs**, no
INSERTs. Note lengths pre-checked against `VARCHAR(128)` (**120** and **117** chars):
1. `UPDATE dbo.watchlist SET enabled = 1, note = ? WHERE symbol = ?` — **NVDA** re-enabled (existing row
   re-enabled, not re-inserted; Alpaca-verified tradable/active).
2. `UPDATE dbo.watchlist SET enabled = 0, note = ? WHERE symbol = ?` — **JPM** parked (row kept).
The `enabled ≤ 30` assertion was evaluated **before** the commit. Re-read after commit: **20 enabled ≤ 30 ✓**,
**33 rows ✓**, **13 parked ✓**.

### Final watchlist
**20 enabled** (≤30 ✓): AAPL ABNB AMD AMGN AMZN BABA DASH GOOG INTC LLY MSFT MU NFLX **NVDA** PLTR QQQ SPOT
TSLA TSM UBER. Parked (13): AVGO BIRD C COST ENPH **JPM** QCOM SE SPY UNH WMT WPM XOM.
**Service restarted (required — the table changed) and verified, not assumed:** `is-active` → **active**,
**MainPID 1856952**, `ActiveEnterTimestamp` **2026-08-27 11:37:46 UTC**, **NRestarts=0**. Journald confirms
the banner *"Watchlist (dbo.watchlist): AAPL, ABNB, AMD, AMGN, AMZN, BABA, DASH, GOOG, INTC, LLY, MSFT, MU,
NFLX, NVDA, PLTR, QQQ, SPOT, TSLA, TSM, UBER"* — **NVDA present, JPM absent** — **warmup primed 20/20**,
account `PA34DFFLTHRT` reconciled at equity **9094.34** with **no open positions**, the IEX stream started,
and **0 WARNING-or-above lines** since start.
🔒 Locked: **none (0 positions, 0 open orders)**.
**Upcoming: GOOG dead-signal test 08-31 · AMGN zero-candidate verdict 09-02 (park if still zero) · AMZN
re-check 09-02 · INTC on-notice re-check 09-03 · BABA 09-09 · AAPL dead-signal test 09-10 · AMD 09-12 ·
Warsh Jackson Hole keynote Fri 08-28 · CRM and CRWD re-screen once their post-print tape settles · MRVL,
WDAY, ADSK after tonight's prints · INTU re-screen still pending · AVGO, UNH, XOM, COST, SPY, SE, WPM and
now JPM re-enables are condition-gated, not dated.**

### Perplexity `sonar` — run 20: it missed the single biggest fact on the tape
**Asked the morning after NVDA's blowout quarter, with NVDA explicitly in the ticker list, it returned
*"NVDA — Most active premarket name by dollar volume… no specific catalyst identified."*** It said
**"no overnight/pre-market catalyst found"** for **18 of 21 tickers**, and for the calendar it returned
**"no verified list of today's in-session earnings or economic releases was available"** — accidentally
harmless (there are none) but arrived at with no evidence. It missed the semiconductor-tariff story
entirely. **Credit where due, and this is a genuine improvement on run 19: its futures call was directionally
right** (it said S&P ~+0.5% / Nasdaq ~+1.1% against a verified +0.35% / +0.66% — right sign, magnitude
overstated) and **it correctly flagged CRWD +9.15% as the biggest pre-market mover.** **Twentieth consecutive
thin-or-wrong ticker layer. Standing rule unchanged and again load-bearing: lead-generation only, never a
regime source, never a clock, never an earnings calendar.** WebSearch (NVDA print detail, today's calendar,
futures, Jackson Hole timing), the Alpaca news tape (40 headlines, which is what actually surfaced the
tariff story and the AMGN Phase 3 result), SIP daily bars over 83 names, `/v2/assets`, `dbo.trades`,
`dbo.entry_refusals` and `dbo.market_gate` carried this run.

### Note for the daily review
**Four things are falsifiable tonight and should be scored, not assumed:**
1. **Today is IMP-036's first live session, and it is running on a semi-led risk-on tape — close to a
   best case for a change that rewards range availability.** The 08-26 review predicted *fewer entries and
   more "confidence X < 60" refusals, concentrated on the low-ATR names*. **Check the refusal population's
   `conf_volatility` distribution against 08-26's**: if it is still pinned near 1.00, the new anchors are
   not biting and the change is cosmetic. If entries fall on the high-ATR names too (MU, INTC, AMD), that is
   over-correction, not the intended effect.
2. **NVDA re-entered on a +7.3% gap — the IMP-017 shape.** If it produces scored candidates today, record
   **what time they fire and where they sit in the day's range**. This is the cleanest available test of the
   08-26 item 3 finding ("the bot enters late in the move") because the move is unambiguously already made
   at the open. **Do not act on one session; do record it.**
3. **AMGN is now on a hard, dated test rather than a soft notice.** Day one was zero. **If today is also
   zero, that is two sessions and the 09-02 park should be brought forward** — the point of the test was to
   avoid a 30-day clock, so do not let it quietly become one.
4. **JPM was parked and INTC was not, on the same day, on deliberately different reasoning.** JPM failed
   three legs (dead clock, vol floor, P&L) with an intact trend; INTC fails only the trend leg with an
   intact clock, record and volatility. **If INTC produces a bad scored candidate today, or another losing
   fill, that is direct evidence the second-leg requirement is too permissive for a name this far below its
   50MA — write it up, do not smooth it over.** The ⚠️ semiconductor-tariff headline is the live wildcard
   for exactly that name.

---
## 2026-08-28 — Pre-market Research

**No changes — and the substantive work today was refusing to bring a park forward on evidence that
cannot support it.** Book is CLEAN & FLAT (broker-confirmed **0 positions, 0 open orders**, equity
**$9,145.53**, `last_equity == equity == cash` → no overnight marks) → **nothing locked**. **No dated item
came due today** (next is GOOG 08-31). **92 candidates screened, 2 passed (GILD, TMO) — both deferred, with
the reasons stated and a date attached.** Board unchanged at **20 enabled**; **service NOT restarted (the
table did not change)** — the running process already carries this exact list.

### Market context
- **Futures slip into the single largest scheduled event of the week, and it lands on the bot's first
  tradeable minute.** Dow futures advancing while **S&P 500 and Nasdaq 100 futures fall** — the Alpaca tape's
  own 08:48 UTC headline is *"Stock Market Today: S&P 500, Nasdaq 100 Futures Slip Ahead of Kevin Warsh's
  Jackson Hole Speech."* Mixed, with the weakness concentrated exactly where this board is concentrated.
- **⚠️ THE FACT OF THE DAY: Fed Chair Kevin Warsh's Jackson Hole keynote is at 10:00 a.m. ET — the exact
  minute `ENTRY_START=10:00` lifts the IMP-017 opening blackout.** Verified via WebSearch (CNBC, Yahoo
  Finance, NPR, CNN). This is his **first major speech as Chair**, he has **ended forward guidance** (removed
  forward-looking language from FOMC statements), and on the eve **two Fed officials said inflation is
  running too hot and policy is too accommodative**. Markets want a rate path and are not expected to get
  one. **Add two in-session releases either side of it: Chicago PMI 9:45 ET and UMich final 10:00 ET.**
  The bot's most productive slice — **14:00–14:15 UTC is 41% of post-IMP-021 entries and +$180 of the
  book's +$193** (08-27 review) — collides head-on with a two-sided macro shock today.
- **Semis softening pre-market, the opposite of yesterday's setup.** Perplexity's quoted pre-market screen:
  **NVDA −0.8% ($226.23), MU −2.1%, INTC −1.8%, TSLA +0.3%**. **MRVL −8% despite a double beat** (valuation)
  — refused on gap shape on 08-26 and 08-27, so **no watchlist bleed, and yesterday's refusal is vindicated**.
- **NVDA gives back the gap it was re-enabled into.** Two negative headlines overnight: WSJ — *"Nvidia
  Pauses Revenue-Sharing Deals With AI Cloud Companies"* amid antitrust concerns, and Michael Burry calling
  the **$105B OpenAI guarantee "circular financing."** Offsetting: Trump praising Huang/Micron, and **SK
  Hynix warning the memory shortage persists through 2030** (constructive for MU). **Headline risk, not a
  scheduled binary — nothing to park on.**
- **No enabled name reports earnings today.** Friday is a quiet calendar (WebSearch: no Friday earnings
  alongside the Chicago PMI); yesterday's AMC names — MRVL, WDAY, ADSK, AFRM — are all off the board.
- **✅ LLY has a genuine positive catalyst, resolved not pending:** **FDA approved Mounjaro to reduce the
  risk of major adverse cardiovascular events** (Alpaca tape 11:03 UTC today). Approval granted — the binary
  is settled favourably, so this is a reason to keep, not to park.
- **Liveness: 147 scored refusals across 20 symbols in 7 days. Gate duty cycle 08-21 42.3% · 08-24 0% ·
  08-25 42.0% · 08-26 43.3% · 08-27 70.8%** — yesterday was the most permissive session in the record.
  **The board is still not the binding constraint.**

### Carried from daily review (08-27 EOD)
- **"AMGN zero-candidate verdict 09-02 … recommend parking at the 09-02 check at the latest"** — **examined
  properly today and deliberately NOT brought forward. See below; this is the run's main decision.**
- **"NVDA traded beautifully and we captured 12% of it … the problem today was ours, not the symbol's"** —
  agreed, kept, and the pre-market fade is recorded rather than treated as a reversal of the re-enable.
- **"Expect the 08-27 4/4 to revert. Do not widen anything on the strength of today."** — **honoured. This
  is the direct argument against today's two screen passes**, and it is why they are dated rather than added.
- **"INTC produced no scored candidate today, so the 'second-leg requirement too permissive' test is still
  unresolved"** — carried forward to the 09-03 re-check, unchanged.

### Watchlist review
**⚠️ AMGN — KEPT. The pre-registered test was run against the board's base rate and it does not
discriminate. The 09-02 date stands, unextended; the criterion is sharpened.**
The 08-26 test read: *"If it prints zero while the rest of the board is active, … today's add was a
mistake."* AMGN has **0 scored candidates all-time** over its two live sessions. **But the premise is
false, and this is measurable rather than arguable:**
- **08-26: 11 of 20 enabled names produced a scored candidate — 10 printed ZERO** (ABNB, AMD, AMGN, AMZN,
  GOOG, LLY, NFLX, NVDA, TSLA, UBER).
- **08-27: only 7 of 20 produced one — 13 printed ZERO**, including DASH, MU, INTC, SPOT and BABA.
- **Eight names printed zero on BOTH sessions.** Zero-over-two-sessions describes **8 of 20 enabled
  symbols**, several with the strongest charts on the board. **At n=2 the test has no discriminating power:
  applied literally it would park DASH, MU and SPOT alongside AMGN.**
**So the honest reading is that the criterion was mis-specified, not that AMGN passed.** Saying that
plainly is the point — the 08-26 entry asked for a falsification to be reported, and what is being reported
is that the instrument cannot resolve it yet. **Nothing is weakened: the 09-02 date is unchanged and the
park still happens then.** The criterion becomes **relative instead of absolute** — *park AMGN on 09-02 if
it is still at zero while the median enabled name has printed ≥2 scored candidates over the same window.*
On merit today it is unchanged and healthy: **+4.72% vs 20MA / +13.77% vs 50MA, ATR 2.33%, medRng 2.35%,
90% ≥1.25%, 70% ≥2%, $1.03B/day, max gap 2.04%, +5.19% over 10 days.** Its ATR is the **second-lowest on
the board after the structurally-locked QQQ**, which remains the real open question about the add.

**✅ NFLX — KEPT, and newly dated. It crossed the ~30-day dead-signal bar today and nobody had it on a
clock.** Last trade **2026-07-29 = 30 days**. Applying the rule as this log actually applies it:
- **Dead-signal leg does NOT fire.** **9 scored refusals in 7 sessions** (most recent 08-25) — it is
  reaching the scorer regularly. This is the **GOOG precedent from 08-27**, where 11 refusals rebutted a
  28-day clock. Days-since-*fill* is not the same quantity as dead signal.
- **Trend leg does NOT fire: +3.71% vs 20MA and +7.09% vs 50MA — above both.**
- **Vol floor passes comfortably:** ATR 2.83%, medRng 2.37%, 95% ≥1.25%, 65% ≥2%, **$2.16B/day**, max gap
  2.92%.
- **P&L leg DOES fail: −$82.34 on 14 trades (6W = 43%)** — third-worst all-time on the enabled board.
**One failing leg → keep**, consistent with AAPL yesterday. **But a 30-day no-fill name carrying the
third-worst record should not drift, so: dead-signal re-check dated 09-08.**

**⚠️ AMD — KEPT to its existing 09-12 date, but it moved the wrong way and the condition is now explicit.**
On 08-27 it was −0.43% / −5.26%; today **−1.22% vs 20MA / −5.98% vs 50MA — it is now below BOTH MAs**, so
the trend leg fires for the first time. **The P&L leg was already failing: −$89.31 on 12 trades (4W = 33%),
the worst all-time record on the enabled board after AMZN.** That is two legs on paper — the AVGO shape.
**It is not parked today for one honest reason: the trend break is marginal (−1.2% below the 20MA is at the
average, not through it),** against AVGO's −8.96% / −6.85% and INTC's −7.94% / −16.80% when those were
judged. It is also **mega-liquid at $9.18B/day with ATR 5.45% and 100% of 20 sessions ≥2%** — the range
availability IMP-036 now scores — and **alive at the scorer with 9 refusals**. **Condition made falsifiable:
AMD parks at the 09-12 re-check if it is still below both MAs, and parks sooner if it closes >3% below its
20MA.** No new discretion required at that point.

**🔒 QQQ — structurally locked, restated once.** ATR **1.46%**, medRng **0.97%**, only **30% of 20 sessions
≥1.25%**, **45 days since its last fill**. On the 08-21 volatility floor it is a park candidate and **it
must never be parked**: it is `MARKET_FILTER_SYMBOL`, and removing it makes the market gate **fail OPEN**,
silently disabling the bot's best-evidenced edge. It printed **9 refusals** this week and is the best record
on the board (**7 trades, 6 wins, +$80.15**).

**✅ The rest, briefly — all above their floors, none with an event today.** **PLTR** +10.76% / +30.36%,
ATR 4.30%, medRng 4.14%, **+4.02% o2c yesterday** — strongest trend on the board and yesterday's best fill
(+$25.93). **DASH** +7.11% / +17.53%, ATR 3.44%, 100% ≥2%. **TSLA** +5.30% / −1.83%, ATR 3.67%, max gap
**1.79% — the cleanest gap shape on the board**. **NVDA** +4.96% / +9.52%, $24.84B/day, ATR 3.20% (fading
pre-market, see above). **ABNB** +4.55% / +16.86% but **$0.87B/day — still the thinnest enabled name** and
**1 refusal in 7 sessions**, the quietest name that is not AMGN; **r10 is now −0.39%** and its leg spread is
12.3pp (V-bounce shape). **On notice, unchanged — no second failing leg** (clock 18 days, P&L +$26.99).
**SPOT** +3.38% / +7.31%, ATR 3.97%, medRng 4.04%, 100% ≥2%. **NFLX** above. **MSFT** +3.02% / +18.21%,
$12.95B/day, **25 refusals — the most active name on the board**. **AAPL** +1.73% / +1.04%, 8 refusals,
best win rate on the board (7W/10, +$57.45); **dead-signal test 09-10** as dated. **MU** +2.19% / −2.28%,
**$28.90B/day — the liquidity anchor**, #1 all-time earner (+$189.55), ATR 6.65%. **TSM** +2.10% / +0.84%.
**UBER** +1.82% / +4.66%, ATR 3.46%. **LLY** −2.02% / −0.69% — below both MAs but **narrowly (leg spread
1.3pp) and with today's FDA approval on the tape**; ATR 3.40%, 100% ≥1.25%, 95% ≥2%, $3.26B/day; **not a
two-leg case (P&L flat, added 08-20, no clock)** — watch, do not act. **GOOG** −3.13% / −3.07%, below both,
**last refusal 08-24 (3 quiet sessions)** — **dead-signal test 08-31 as dated, and it is now the most
likely park on the board.** **AMZN** −4.07% / +2.06%, above the 50MA so the two-leg rule does not fire;
worst all-time (−$108.51, 2W/14) and a **12.53% max gap**; **re-check 09-02**. **BABA** −6.93% / +1.27%,
above the 50MA, **09-09** unchanged. **INTC** −3.98% / −12.76% on a −11.93% 10-day return — deepest
downtrend, kept yesterday on an intact clock/record/ATR, **on-notice re-check 09-03 unchanged**.
**Liquidity floor clean: no sub-$5 names, no halts, thinnest enabled is ABNB at $0.87B/day.**
**All 20 enabled symbols re-verified on Alpaca `/v2/assets` this morning: 20/20 `tradable: true`,
`status: active`.** No halts, no status changes.

### ➕ Adds — NONE, but two names PASSED and are dated rather than dismissed
**92 candidates screened against the eight standing floors** (above BOTH MAs · ATR ≥2.3% · medRng ≥2.0% ·
≥80% of 20 sessions ≥1.25% · ≥$0.83B/day · max 24-session gap ≤4% · 20/50 leg spread ≤9pp · positive 10-day
return). **Two passed — the first passes in three runs:**
- **GILD** — +6.88% / +11.35%, ATR 2.52%, medRng 2.38%, **100% ≥1.25%**, 70% ≥2%, max gap **2.04%**,
  +7.76% over 10 days, leg spread 4.47pp. **Alpaca-verified `tradable: true`, `status: active`, NASDAQ.**
  **The one blemish is liquidity: $0.84B/day would make it the thinnest name on the board**, displacing an
  ABNB that is already on notice for exactly that.
- **TMO** — +4.92% / +13.79%, ATR 2.57%, medRng 2.16%, 90% ≥1.25%, **$1.00B/day**, max gap 2.23%, +5.84%
  over 10 days. **Alpaca-verified `tradable: true`, `status: active`, NYSE.** **Leg spread 8.87pp — inside
  the 9pp bar by 0.13pp**, i.e. it passes on the tightest possible margin.
**Neither is added today, for three reasons that are about timing, not about the names:**
1. **IMP-036 is 4 fills into a pre-registered 15-fill revert test.** The 08-27 entry declined to add for
   this exact reason and the reason has not aged; we are one session further in, not past it.
2. **Warsh at 10:00 ET lands on the entry-window open.** A new symbol's first live session would be scored
   on a macro-shock tape — the worst possible day to start a name's record.
3. **AMGN's own add is still unadjudicated** (09-02). Widening the board before the last add is judged
   compounds an error rather than diversifying one — the 08-27 argument, still true.
**Both are dated to 09-02, the same day as the AMGN verdict, so the board's composition gets decided as one
coherent judgement rather than three drifting ones.**
- **Notable refusals.** **CRM** now screens +26.04% / +40.91% — a **14.9pp leg spread and an 11.9% max
  gap**, refused a second time and moving further away, not closer. **CRWD** +9.82% / +16.74% but a **10.1%
  max gap**. **MSTR (+31.1% / +37.4%), COIN (+19.4% / +19.1%) and HOOD (+12.8% / +8.3%)** top the screen
  again and are refused again on the **08-21 crypto-beta rule**, all three also failing gap shape (6.3–8.6%).
  **NOW is refused a seventh time** (12.8pp leg spread — the fourth consecutive run its stated re-screen
  condition moved the wrong way). **MRVL** refused on an 11.17% max gap — and it is **−8% pre-market today**,
  which is the refusal earning its keep in real time. **DIS** misses the vol floor again (ATR 2.22%,
  medRng 1.87%) — closest miss for a third run. Gap-shape refusals: **TTD 27.2%, LRCX 26.1%, SHOP 21.7%,
  RBLX 20.1%, WDC 17.4%, STX 15.0%, ARM 14.7%**. Liquidity refusals under the floor: **ZS $0.39B, CELH
  $0.30B, RIVN $0.29B, TTD $0.29B, WDAY $0.67B, VRTX $0.56B, PYPL $0.58B, DE $0.61B, SBUX $0.65B, CEG
  $0.65B**. Below a moving average: **META, AVGO, GS, ISRG, CAT, BA, GE, WMT, KLAC, AMAT, ASML, UNH, XOM,
  COST, SCHW, C, JPM**.
- **Parked set — all condition-gated re-enables re-checked, none met.** **WPM** screens spectacularly
  (+14.98% / +29.50%) and is refused on **exactly what parked it — $0.28B/day, thinnest in the screen**.
  **JPM**, parked yesterday, has **deteriorated further on the leg that parked it: ATR 1.67%, medRng 1.35%,
  only 70% of sessions ≥1.25%, 15% ≥2%** — the vol floor is further away, not closer, and it is now below
  its 20MA too. **SPY** ATR **0.81%, 15% ≥1.25%, 0% ≥2%** — deteriorating for a third run. **QCOM** +2.36%
  but −5.56% vs 50MA · **SE** $0.47B/day and an 11.4% max gap · **UNH** −1.52% / −4.34% · **C** −1.61% /
  −2.46% · **COST** ATR 1.95%, 20% ≥2% · **WMT** −7.07% / −8.42% · **AVGO** −5.24% / −3.89% on a −11.08%
  10-day return · **XOM** −1.40% vs 20MA · **ENPH**, **BIRD** unchanged. **All unmet.**

### Changes applied to dbo.watchlist
**NONE.** No `UPDATE`, no `INSERT`, no `DELETE` — **the table was read and not written this run.** No dated
item came due, no enabled symbol has an event today, no symbol met a park bar, and the two screen passes are
deliberately deferred to 09-02. **20 enabled ≤ 30 ✓, 33 rows ✓, 13 parked ✓** (re-read to confirm, unchanged
from yesterday's post-commit state).

### Final watchlist
**20 enabled** (≤30 ✓), unchanged: AAPL ABNB AMD AMGN AMZN BABA DASH GOOG INTC LLY MSFT MU NFLX NVDA PLTR
QQQ SPOT TSLA TSM UBER. Parked (13): AVGO BIRD C COST ENPH JPM QCOM SE SPY UNH WMT WPM XOM.
**Service NOT restarted — correctly, because the table did not change**, and the restart rule is
conditional on a change. **Verified rather than assumed that the running process already carries this list:**
`is-active` → **active**, **MainPID 1898233**, `ExecMainStartTimestamp` **2026-08-27 20:24:55 UTC** (the
IMP-037 deploy restart, which post-dates yesterday's watchlist commit), **NRestarts=0**, journald banner
*"Watchlist (dbo.watchlist): AAPL, ABNB, AMD, AMGN, AMZN, BABA, DASH, GOOG, INTC, LLY, MSFT, MU, NFLX, NVDA,
PLTR, QQQ, SPOT, TSLA, TSM, UBER"* — **an exact match to the 20 enabled rows** — **warmup primed 20/20**,
and **0 WARNING-or-above lines since start**. Leaving it up also preserves ~15h of continuously-carried EMA
state, which a restart would discard and re-seed from history.
🔒 Locked: **none (0 positions, 0 open orders)**.
**Upcoming: GOOG dead-signal test 08-31 (most likely next park) · AMGN relative-criterion verdict 09-02 ·
AMZN re-check 09-02 · GILD + TMO add decision 09-02 · INTC on-notice re-check 09-03 · NFLX dead-signal
re-check 09-08 (new) · BABA 09-09 · AAPL dead-signal test 09-10 · AMD 09-12 (parks if still below both MAs)
· CRM/CRWD/MRVL/WDAY/ADSK re-screen once their post-print tape settles · INTU re-screen still pending ·
AVGO, UNH, XOM, COST, SPY, SE, WPM, JPM re-enables are condition-gated, not dated.**

### Perplexity `sonar` — run 21: thin on catalysts, but it supplied the calendar that mattered
**16 of 20 tickers came back *"No specific overnight catalyst found"*, and it declined to give a direction
for either S&P 500 or Nasdaq futures** — the two things the prompt asks for most explicitly. It **missed the
LLY FDA approval, the NVDA revenue-sharing/antitrust story and the Burry note entirely.** **Credit where it
is due, and it is real this run: it returned the in-session calendar correctly — Chicago PMI, UMich 1-year
inflation expectations and the Warsh speech** — which is the first time in this log's record that sonar has
supplied a usable clock item, and it independently quoted a pre-market screen (NVDA −0.8%, MU −2.1%, INTC
−1.8%, TSLA +0.3%) that matched the tape's direction. **Twenty-first consecutive thin-or-wrong ticker layer;
standing rule unchanged and unchanged in force: lead-generation only, never a regime source, never an
earnings calendar** — today its calendar was *verified* against WebSearch before being used, and that is the
only reason it was allowed to be load-bearing. WebSearch (Warsh timing and stakes, Friday earnings/economic
calendar, futures direction), the **Alpaca news tape (28 headlines — the only source that surfaced the LLY
approval and the NVDA antitrust story)**, SIP daily bars over **112 names**, `/v2/assets` × 22,
`dbo.trades`, `dbo.entry_refusals` and `dbo.market_gate` carried this run.

### Note for the daily review
**Five things are falsifiable tonight and should be scored, not assumed:**
1. **IMP-037's first live rows land today — and the first thing to check is that they are not NULL.** All
   four of yesterday's trades carry `mfe_pct = NULL, mae_pct = NULL`, which is **correct** (it shipped at
   20:25 UTC, after the close), but it means **today is the only evidence that the column actually
   populates.** If today's fills are also NULL, IMP-037 is not working and the 08-27 entry's "first rows
   land tomorrow" was wrong.
2. **Warsh's keynote at 10:00 ET lands on the entry-window open, on the bot's single most productive
   15-minute slice** (14:00–14:15 UTC = 41% of entries, +$180 of +$193). **Record what the cluster does on
   a macro-shock open** — whether entries fire into the speech, and where they sit in the day's range.
   **This is one session: record it, do not re-tune the entry window on it.** If it is ugly, the question
   for a later run is whether a scheduled-event blackout is worth owning in-repo — the same shape as the
   earnings-guard gap the 08-21 weekly flagged and nobody owns.
3. **The AMGN test was re-specified today and the reasoning should be checked, not accepted.** The claim is
   that per-session zero is the *modal* outcome on this board (10 of 20 on 08-26, 13 of 20 on 08-27), so an
   absolute zero-candidate test cannot discriminate at n=2. **If that is wrong, the 09-02 park should
   happen anyway.** The re-specified criterion is relative: park if AMGN is at zero while the median
   enabled name has ≥2.
4. **DB P&L is gross of regulatory fees, and it is now measurable.** Yesterday: **DB +$51.39 vs broker
   +$51.19 — a $0.20 gap**, fully explained by CAT/TAF/REG fee rows. Per-trade it is ~$0.05, and the
   sampled fee history is only −$2.09, so this is **small and NOT an explanation for the lifetime −$13.22**
   — recording it so nobody later "discovers" it as a large hidden cost. Worth one line in the reconciliation.
5. **NVDA is fading the gap it was re-enabled into (−0.8% pre-market).** Yesterday it entered at 14:01 and
   captured 12% of a +2.62% move. **The IMP-017 question — does this bot buy moves that have already
   happened? — gets a second data point today, on a day the gap is going the other way.** Two sessions is
   still not a verdict.

---

## 2026-08-31 — Pre-market Research

**The one dated item that came due today was settled with evidence: GOOG PARKED on a three-leg failure.
No adds — a 100-name screen produced exactly one pass (TMO) and it was refused on the AMGN precedent
rather than taken. Net 20 → 19 enabled.** Book is CLEAN & FLAT (broker-confirmed **0 positions, 0 open
orders**, equity **$9,133.65**, `last_equity == equity == cash` → no overnight marks) → **nothing locked**.
Service restarted clean (warmup 19/19, zero WARNING-or-above lines).

### Market context
- **Mildly risk-off into the last session of August, on geopolitics rather than data.** ETF proxies
  **SPY −0.17%, QQQ −0.12%, DIA −0.16%**, with **IWM +0.02%** — small caps the only green, which is the
  shape of a market with no conviction rather than a directional one. Energy is bid on **renewed US–Iran
  tensions** (Alpaca tape headline 09:37 UTC: *"S&P 500, Dow Futures Fall as US-Iran Tensions Flare Up"*).
  Global bond yields still rising in the background.
- **⚠️ No in-session scheduled US release today — and that is the *only* clean day this week.** The
  calendar loads up immediately afterwards: **Tue 09-01 ISM Manufacturing + JOLTS at 10:00 ET**,
  **Wed 09-02 ADP + durable goods/factory orders**, **Thu 09-03 Challenger, claims, ISM Services**,
  **Fri 09-04 the August employment report**.
- **🔴 Correction to the 08-28 weekly, which flagged its own forward section as unverified:** the weekly
  put Friday's payrolls at **13:30 UTC "comfortably inside the entry window."** It is **08:30 ET = 12:30
  UTC in EDT — an hour *before* the 13:30 UTC open**, so payrolls is a **pre-open gap event**, not an
  in-session one, and the IMP-017 10:00 ET blackout already covers the reaction window. **The genuinely
  in-session hazard is Tuesday: ISM Manufacturing + JOLTS both land 10:00 ET = 14:00 UTC, the exact minute
  the entry blackout lifts.** That is the date to watch, not Friday.
- **No enabled name reports this week.** Tue AMC is DELL/PANW/MDB/CRDO/GTLB, Wed AMC is **AVGO** + SNOW.
  **AVGO is parked**, so there is nothing to park for the print — but AVGO Wednesday night is the AI-capex
  read-through into **MU, NVDA, AMD, INTC, TSM** on Thursday, five enabled names. Flagging, not acting.
- Perplexity `sonar` ran and returned **no catalyst for any of the 20 tickers** and no futures direction —
  its only usable output was the earnings calendar, which is reproduced above and was cross-checked against
  WebSearch and the Alpaca news tape. **Treated as thin, not as an all-clear**; the market context above is
  WebSearch + Alpaca news, not Perplexity.

### Carried from daily review (08-28 EOD)
- **"GOOG dead-signal test 08-31"** — **came due today, was actually run, and it FIRED. Parked below.**
  This is the sixth consecutive run on which a date was honoured on its stated date.
- **"AMGN zero-candidate verdict 09-02 … recommend parking at the 09-02 check at the latest"** — **held to
  its date, and the evidence against it is now 3/3.** See AMGN below. Not parked today: the test says
  *"by 09-02"*, 09-02 is Wednesday, and there is **zero risk cost** to letting it run its stated course
  (the failure mode under test is that it does nothing at all). Accelerating a dated test by two sessions
  buys no information; the log's discipline is to settle on the date, not before it.
- **"Do not widen anything on the strength of [08-27's 4/4]"** — honoured. One park, no adds.
- **"MSFT (8 refusals), GOOG (8) … live but not productive"** — this is the observation the GOOG park acts
  on, and the reason MSFT does **not** get parked with it (MSFT is above both MAs; GOOG is below both).

### Watchlist review
**Liveness first: 220 scored refusals across 20 symbols in the last 8 sessions; every enabled name appears
except AMGN.** MSFT 34 · DASH 21 · GOOG 19 · BABA 17 · UBER 16 · TSM 14 · NFLX 14 · MU 13 · AAPL 13 ·
AMD 9 · AMZN 9 · PLTR 9 · QQQ 9 · SPOT 6 · INTC 5 · LLY 3 · TSLA 3 · ABNB 2 · NVDA 1 · **AMGN 0**.
The board is still not the binding constraint — the score is.

**➖ GOOG — PARKED. The dated test came due and it is the first name since JPM to fail three independent
legs at once.**
- **Dead-signal leg FIRES: 31 days since its last trade (2026-07-31)** against the ~30-day bar — the same
  clock that parked UNH (31d) and JPM (31d).
- **Trend leg FIRES: −1.45% vs 20MA AND −1.47% vs 50MA — below both.** This is the leg AAPL was *exempted*
  on twice (it is +3.18% / +2.47% today and stays), so the rule is discriminating, not being stretched.
- **Volatility floor FAILS: ATR 1.80%, median session range 1.64%, only 30% of the last 20 sessions ≥2%.**
  GOOG is now the **lowest-volatility enabled name other than QQQ, which is structurally locked**. The
  1.25% trail needs **76% of a median session** just to arm — this is the SPOT arithmetic from 08-28
  (MFE < 1.25% ⇒ the trail can only book a loss), and GOOG's own refusal rows carry it: **1-min ATR
  0.047%–0.130%** across all 21 scored candidates.
- **P&L leg: −$25.89 on 14 trades (6W, 43%)** — negative, though mild; recorded as supporting, not load-bearing.
- **The honest counter-argument, stated because it is strong: GOOG is the #3 most-active name in the scorer
  (19 scored refusals over 3 sessions) and printed a 78.21 on 08-24.** Two things defuse it. **(1)** That
  78.21 was refused on **`market gate closed`**, i.e. it was never GOOG's to convert. **(2)** Filtering to
  candidates where **the gate was actually open**, GOOG's best score in 14 days is **51.96** — it has not
  produced a single qualifying signal with a green light all fortnight. On 08-28 its whole distribution
  collapsed to **42.0–52.0 across 8 candidates**. High activity that never clears the bar is not liveness,
  it is a name occupying a slot.
- **Re-enable is condition-gated, not dated: back above BOTH moving averages AND ATR ≥2.3% with ≥60% of
  sessions ≥2%.** No 30-day clock.

**⚠️ AMGN — KEPT to its 09-02 date, and the evidence against it is now 3/3 rather than 1/1.** The 08-27
test read: *"if AMGN has produced zero scored candidates by 09-02, it is parked … no further extension."*
**It has produced zero rows of ANY kind — not one scored candidate, not one gate refusal — on 08-26, 08-27
and 08-28**, while the rest of the board printed 220. It also had a **positive catalyst on the tape this
morning** (Repatha cut death risk 20% in high-risk heart patients) and one on 08-27 (TEZSPIRE Phase 3), and
still does not trade — which is itself the finding: **the story is fine, the tape is not.**
- **Ruled out a plumbing bug before crediting the zero, rather than assuming it.** journald shows **428
  AMGN lines on 08-28**, AMGN present in the live IEX subscription list, and 1-min *and* 5-min candles
  building normally. **The silence is real: the 1-min ribbon simply never produces a fresh cross clearing
  `MIN_CROSSOVER` 0.25.** Its chart still screens fine (**+2.60% / +11.48%, ATR 2.10%, medRng 2.35%,
  90% ≥1.25%, 70% ≥2%, $1.03B/day, max gap 2.04%**) — which is exactly why the daily-chart screen alone
  failed to predict this.
- **New measurement, offered as an observation and NOT as a new floor, because it has a counterexample.**
  Median **IEX** trades-per-RTH-minute over the last 5 sessions: **AMGN 6 (last on the board)**, ABNB 7,
  SPOT 7, DASH 9, BABA 12, LLY 12, QQQ 12 … INTC 50, NVDA 109. AMGN also has the **fewest RTH minutes with
  any IEX print at all (842 vs NVDA's 1440 — ~42% of minutes empty)**. The tempting conclusion is a
  tick-density floor. **It does not survive: SPOT and ABNB sit at the same 7/min and both produce
  candidates, and SPOT actually filled on 08-28.** So density is *suggestive and AMGN is the extreme*, but
  it is not sufficient on its own. **Worth carrying: the add-screen measures SIP dollar volume while the bot
  trades the IEX tape — those are not the same liquidity**, and nothing in the current screen sees the gap.

**✅ The rest — all kept, none marginal enough to act on.** **DASH** +8.33% / +19.13%, ATR 3.22%, 100%
≥2%, 21 refusals — strongest name on the board. **PLTR** +8.93% / +29.60%, ATR 3.69%. **SPOT** +6.86% /
+11.02%, ATR 3.81%, 100% ≥2% — kept despite being the 08-28 loss; that was trail arithmetic on a
0.128% 1-min ATR, not a bad symbol. **ABNB** +6.26% / +19.31%, ATR 2.79%, **$0.90B/day and now only the
2nd-thinnest** (SPOT is $0.88B); 2 refusals, still on notice for liquidity alone. **NFLX** +5.47% / +9.48%.
**MSFT** +4.09% / +19.24%, **34 refusals — the most active name on the board**, above both MAs, no park
case. **UBER** +3.71% / +6.97%. **AAPL** +3.18% / +2.47% — above both, dead-signal clock re-set to **09-10**.
**TSLA** +2.93% / −3.25%, ATR 3.56%. **AMGN** above. **MU** +1.30% / −2.32%, **$27.29B/day, the liquidity
anchor and #1 all-time earner (+$189.55)**; reports late September. **AMZN** −0.17% / +5.87% — above the
50MA so the two-leg rule does not fire, **re-check 09-02**. **NVDA** −0.23% / +4.38% after **−4.57%
yesterday** giving back part of the post-print gap. **TSM** −0.39% / −1.40%. **LLY** −2.32% / −1.03%.
**AMD** −3.41% / −8.00% on a **−9.5% 10-day** — trend leg fires but it traded 08-13 (18d), so the clock
does not; **re-check 09-12** unchanged. **BABA** −4.73% / +3.32%, above the 50MA, **09-09** unchanged.
**INTC** −6.67% / −14.73% on a **−12.7% 10-day** — deepest downtrend on the board, but it is the #2
all-time earner (+$150.78), traded 08-17 (14d), and has the **best range availability here (ATR 5.24%,
medRng 4.51%, 100% ≥2%)**; **re-check 09-03 stands, and AVGO's Wednesday print lands inside it.**
**🔒 QQQ — structurally locked, restated: it is `MARKET_FILTER_SYMBOL` and parking it makes the market gate
fail OPEN.** On merit it would fail the volatility floor outright (ATR 1.17%, medRng 0.97%, 30% ≥1.25%).
**Liquidity floor clean: no sub-$5 names, no halts, thinnest enabled is SPOT at $0.88B/day.**

### ➕ Adds — NONE, and the screen is reported rather than asserted
**~100 candidates screened against the eight standing floors** (above BOTH MAs · ATR ≥2.3% · medRng ≥2.0% ·
≥80% of 20 sessions ≥1.25% · ≥$0.85B/day · max 24-session gap ≤4% · 20/50 leg spread ≤9pp · positive 10-day
return). **Exactly one passed: TMO** (+3.09% / +11.60%, ATR 2.48%, medRng 2.10%, 90% ≥1.25%, $0.99B/day,
gap 2.23%, spread 8.5pp, +5.8% 10d, no earnings until late October).
- **TMO is refused anyway, and the reason is AMGN.** TMO is the **same profile as the add that is currently
  failing its own falsification test** — a ~$1B/day healthcare large cap with low-2s ATR — and it is
  **weaker than AMGN on the discriminating axis** (medRng 2.10% vs AMGN's 2.35%; IEX density 7/min vs
  AMGN's 6). Adding it today would be widening the board on a template with a live, unresolved counter-
  example, which is the exact error the 08-27 entry named. **TMO is re-screenable on 09-02 once AMGN is
  adjudicated** — and note that if AMGN parks, its own test re-tightens the volatility floor, which would
  refuse TMO on the spot. Either way 09-02 decides it, not today.
- **Single-leg near-misses, recorded so the screen is auditable:** gap-shape — **CRWD 10.08%, MSTR 8.61%,
  MRK 8.71%, COIN 7.83%, HOOD 6.31%, MELI 5.05%, ORCL 5.04%**; liquidity under the $0.85B floor —
  **GILD $0.81B, TGT $0.75B, SBUX $0.64B, DHR $0.61B, SLB $0.46B, HCA $0.45B, LYFT $0.18B**; below a
  moving average — **IBM** (−3.36% vs 50MA). **MSTR/COIN/HOOD are refused on the 08-21 crypto-beta rule as
  well, re-applied without re-litigation.** **MELI** clears liquidity for the first time at $0.85B but
  **still fails sizing independently**: at $1,966/share, MIN_ALLOC 0.05 × $36,534 buying power = **$1,826
  → qty 0**. **NOW** is refused a seventh time on leg spread.
- **Parked set — all condition-gated re-enables re-checked, none met.** **WPM** screens best of anything
  anywhere (**+9.74% / +25.00%, +14.2% 10d**) and is refused on **exactly what parked it — $0.31B/day**.
  **SE** +0.86% / +9.86% at **$0.48B/day** and an 11.39% max gap. **QCOM** +1.47% but **−5.37% vs 50MA**.
  **XOM** −1.62% vs 20MA. **JPM** vol floor unchanged (**ATR 1.46%, medRng 1.34%, 15% ≥2%**) — the park is
  holding up. **SPY** deteriorated further (**ATR 0.66%, medRng 0.56%, 10% ≥1.25%, 0% ≥2%**). **COST**
  (1.85% / 1.71%, 25% ≥2%) · **UNH** −1.78% / −4.82% · **C** −1.48% / −2.46% · **AVGO** −5.69% / −4.49%
  (**and reports Wed AMC — do not re-enable into that print**) · **WMT** −6.48% / −7.96% · **ENPH**
  −5.56% / −10.66% at $0.15B/day · **BIRD** sub-$5. **All unmet.**

### Changes applied to dbo.watchlist
**One parameterized `UPDATE`**, `watchlist` the only table touched, **no DELETEs**, no INSERTs. Open
positions re-fetched from the broker **immediately before** the write and asserted not to contain GOOG
(0 positions). Note length pre-checked against `VARCHAR(128)` (**116** chars; a first draft at 133 was
rejected by the assertion and shortened, not truncated).
1. `UPDATE dbo.watchlist SET enabled = 0, note = ? WHERE symbol = ?` — **GOOG** parked (row kept).
The `enabled ≤ 30` assertion was evaluated **before** the commit. Re-read after commit: **19 enabled ≤ 30 ✓**,
**33 rows ✓**, **14 parked ✓**.

### Final watchlist
**19 enabled** (≤30 ✓): AAPL ABNB AMD AMGN AMZN BABA DASH INTC LLY MSFT MU NFLX NVDA PLTR QQQ SPOT TSLA
TSM UBER. Parked (14): AVGO BIRD C COST ENPH **GOOG** JPM QCOM SE SPY UNH WMT WPM XOM.
**Service restarted (required — the table changed) and verified, not assumed:** `is-active` → **active**,
**MainPID 2220001**, `ActiveEnterTimestamp` **2026-08-31 11:39:00 UTC**, **NRestarts=0**. Journald confirms
schema ensured (16 batches), broker handshake `PA34DFFLTHRT` equity **$9,133.65** with **no open positions**,
**warmup primed 19/19**, IEX stream connected and subscribed to all 19 symbols, **GOOG absent from the
subscription list (0 occurrences post-restart)**, and **zero WARNING-or-above lines** since boot.

### Notes for tomorrow / open dates
- **Tue 09-01 is the first genuinely hazardous session of the week: ISM Manufacturing + JOLTS at 10:00 ET
  = 14:00 UTC, landing the same minute the IMP-017 entry blackout lifts.** Expect the 14:00–14:15 candle
  cluster to be macro-driven rather than trend-driven.
- **09-02 is a triple date: AMGN's zero-candidate verdict (currently 3/3 against — park unless it prints a
  scored candidate today or tomorrow), AMZN's re-check, and TMO's re-screen.** They interact: if AMGN
  parks, the volatility floor re-tightens and TMO is refused by that alone.
- **Wed 09-02 AMC: AVGO reports** (parked — nothing to do) but it sets the AI-capex tone for **MU, NVDA,
  AMD, INTC, TSM** into Thursday, and **INTC's own re-check is 09-03**, the morning after.
- **Fri 09-04 payrolls is 12:30 UTC — PRE-OPEN, not in-session.** Corrected from the 08-28 weekly. The gap
  risk is at the open and the blackout covers it; do not plan an in-session mitigation for it.
- Remaining dates unchanged: **INTC 09-03 · BABA 09-09 · AAPL 09-10 · AMD 09-12.**
- **Carry for the screen, not for today: SIP dollar volume ≠ IEX tradability.** AMGN passes every daily-bar
  floor and is dead on the tape the bot actually consumes. The measurement is in the AMGN section above,
  including the SPOT/ABNB counterexample that stops it from being a rule yet.

---

## 2026-09-01 — Pre-market Research

**The bot was DOWN when this run started — dead since 09:41 UTC on a `.env` permission fault — and
restoring it was the run's real work. Watchlist: NO CHANGES, 19 enabled, and that is the correct
outcome (not a single dated test comes due today).** Book is CLEAN & FLAT (broker-confirmed
**0 positions, 0 open orders**, equity **$9,133.65**, `cash == equity == last_equity` → no overnight
marks) → **nothing locked**. Service restarted clean at 11:36:34 UTC, warmup 19/19, ~1h55m of
downtime, **entirely pre-market — zero trading impact.**

### 🔴 Outage: `.env` went root-owned, the service crash-looped, and it would have missed the whole session
- **Symptom:** `ustradebot.service` was `failed`, not active. `PermissionError: [Errno 13] Permission
  denied: '/opt/ustradebot/.env'` in `Config.load()` → `load_dotenv()`. Five restarts in 5s, then
  systemd gave up (`start request repeated too quickly`) at **09:41:32 UTC**.
- **Cause:** `.env` was `root:root` mode 600 with mtime **09:40:37 UTC** — rewritten by root ~55s
  before the first crash. That timestamp matches **no scheduled routine** (premarket 11:30,
  daily-review 20:00, weekly 21:00 UTC), so it was a manual root edit. The service runs as
  `ustradebot`, which then could not read its own config.
- **Fix:** `chown ustradebot:ustradebot .env` + `chmod 600`. **Content untouched** — the file was never
  rewritten, per the standing rule. `systemctl reset-failed` was required first (systemd had latched
  the rate limit), then restart.
- **No config drift:** startup re-reports the expected tunables — entry ≥60%, 10:00–16:00 ET window
  with the IMP-017 blackout, stop −2.00%, target +10.00%, trail 1.25% tightening to 1.00% (IMP-018 /
  IMP-021), QQQ market gate on (IMP-022) — and the account reconciled to PA34DFFLTHRT $9,133.65.
- **This is the third form of the root-owns-files gotcha** (after repo files and `.git`). The earlier
  two produced git friction; this one **silently takes the bot off the tape**. Worth noting that the
  15-min health-check timer and `OnFailure` alert did fire — the alert path worked; the bot was simply
  down until a human-equivalent ran. **Whoever edits `.env` as root must chown it back, always.**

### Market context
- **Mildly risk-off into the first session of September.** S&P 500 futures **−0.19%**, Nasdaq 100
  futures **−0.57%** (Perplexity `sonar`). Pre-market: **MU −1.7% to −1.9%** and **NVDA −0.4% to −1.3%**
  (the two heaviest semis on the board), against **AAPL +0.80%**, **TSLA +0.64%**, MSFT +0.07%. The
  one large mover is GAP +18.95%, not an enabled name.
- **⚠️ The in-session hazard pre-registered on 08-31 is today and it is confirmed:** **ISM Manufacturing,
  JOLTS and Construction Spending all land 10:00 ET = 14:00 UTC — the exact minute the IMP-017 entry
  blackout lifts.** (S&P Global Manufacturing PMI at 08:45 ET is pre-open and harmless.) Verified against
  the NY Fed and Scotiabank September calendars, not taken from Perplexity. **Watch-and-record, as the
  daily review specified — no pre-emptive widening of the blackout on one session's anticipation.**
- **No enabled name reports today.** Light calendar (~11 reporters); tonight's AMC names are
  DELL/PANW/MDB/CRDO/GTLB, none enabled. **Wed AMC is AVGO (parked) + SNOW** — AVGO remains the
  AI-capex read-through into MU/NVDA/AMD/INTC/TSM on Thursday. Flagging, not acting.
- Perplexity returned **no catalyst for any of the 19 tickers** for the second run running — usable only
  for futures and pre-market prints. **Treated as thin, not as an all-clear**; the calendar above is
  WebSearch-verified.

### Carried from daily review (08-31 EOD)
- **"Do not add symbols to compensate for today's zero" — honoured. No adds.**
- **"AMGN dated test due 09-02"** — **held to its date, not accelerated.** Evidence is now stronger, not
  weaker: `dbo.entry_refusals` shows **zero AMGN rows of any kind in the last 11 days** while the other
  18 enabled names produced 196. It is the only enabled symbol absent from the table entirely. **09-02 is
  tomorrow; there is no risk cost to letting a "does nothing at all" failure mode run one more session,
  and the log's discipline is to settle on the date, not before it.**
- **"NFLX volatility-floor park candidate — flagging for accumulation, not recommending a park"** —
  **accumulated, and the case has now REVERSED. See below. This is today's one substantive finding.**
- **"Live results since 08-21 (6 trades, 5W/1L, +$44.85) should not be panicked away"** — honoured.
- **"Expect the first post-blackout candles to be noisy"** — the 14:00 UTC coincidence is confirmed above.

### Watchlist review
**Liveness: 196 scored refusals across 18 of 19 enabled names in the last 11 days.** MSFT 34 (best 71.0) ·
DASH 21 (73.5) · MU 16 (79.0) · UBER 16 (70.2) · **NFLX 13 (66.8)** · AAPL 12 (61.6) · PLTR 10 (76.0) ·
TSM 10 (64.3) · QQQ 9 (61.0) · AMD 9 (74.3) · AMZN 9 (83.2) · BABA 7 (68.6) · SPOT 6 (70.9) · TSLA 4 (77.3) ·
INTC 3 (60.8) · LLY 3 (69.0) · ABNB 2 (67.0) · NVDA 2 (52.7) · **AMGN 0**. The board is live; the score is
still the binding constraint, exactly as the daily review said.

**🟢 NFLX — the 08-31 park flag is WITHDRAWN, on evidence that contradicts it.** The flag rested on two
1-min rows with ATR 0.036–0.044% on a single risk-off session. Measured properly over 20 sessions on the
daily chart, NFLX fails **none** of the GOOG park legs:
- **Trend leg does NOT fire: +4.09% vs 20MA AND +8.47% vs 50MA — above both.** (GOOG was below both.)
- **Volatility floor PASSES comfortably: ATR 2.67%, medRng 2.60%, 55% of 20 sessions ≥2%, 95% ≥1.25%,
  $2.25B/day.** GOOG was parked at ATR 1.80% / medRng 1.64% / 30% ≥2%. NFLX is not in that cohort — it is
  a full point of ATR above it and **+6.6% over 10 days**.
- **It is live in the scorer: 13 refusals, best 66.8 — a score that cleared the 60 threshold**, i.e. NFLX
  has produced a genuinely qualifying signal this fortnight. AMGN's problem (zero rows) is not NFLX's.
- **Only the dead-signal clock is red (33d, last trade 07-29), and one leg has never been sufficient** —
  that is precisely the AAPL exemption, applied twice. **Dead-signal clock re-set to 09-15** on the
  above-both-MAs exemption. Its lifetime −$82.34 is noted and is *not* load-bearing on its own.
- **The lesson is the generalisable part: a 1-min ATR reading taken on one shut-gate session is not a
  volatility measurement.** The volatility floor is a 20-session daily-bar rule; it must be evaluated as
  one. Two refusal rows nearly parked a name that is above both MAs and printing 66s.

**✅ The rest — all kept, and no dated test comes due today.** **DASH** +5.29% / +15.94%, ATR 3.19%, 100%
≥2%, 21 refusals — still the strongest all-round name. **TSLA** +7.87% / +2.26%, ATR 3.67%, 95% ≥2%,
**+$45.76 over the last 20 days, the best recent earner**. **PLTR** +7.08% / +28.62%, ATR 3.64%, +$31.21.
**SPOT** +5.51% / +9.89%, ATR 3.77%, 100% ≥2% — thinnest enabled at **$0.98B/day**, still on notice for
liquidity alone. **UBER** −0.72% / +2.55%, ATR 3.59% — below the 20MA but above the 50MA, 16 refusals,
no leg fires. **NFLX** above. **MSFT** +2.62% / +17.10%, most active on the board. **AMGN** held to 09-02.
**ABNB** +1.84% / +14.81%, ATR 2.85%, $1.05B/day. **AAPL** +2.03% / +1.43% — above both, exempt, **09-10**.
**MU** +3.39% / +0.76%, **$27.26B/day**, ATR 5.31%, #1 all-time earner (+$189.55); down ~1.9% pre-market.
**NVDA** +0.93% / +5.83%. **TSM** −1.03% / −1.70% — below both but traded 08-27 (4d), clock nowhere near.
**AMZN** −2.22% / **+3.10% — still above the 50MA so the two-leg rule does not fire; re-check 09-02**
stands. **LLY** −3.95% / −2.63%, ATR 3.20%, $3.45B/day, added 08-20, no trade yet — too new to judge.
**BABA** −8.15% / −1.04% — **it fell through the 20MA hard on 08-31 (−8.6% over 10 days) and is now below
both**, but its dead-signal clock reads **21d**, so the second leg does not fire. **Re-check 09-09 stands
and BABA is now the most likely name to park on that date.** **AMD** −2.21% / −6.74%, **09-12**. **INTC**
−6.56% / −13.96% on a **−13.5% 10-day**, deepest downtrend and **−$40.48 over the last 20 days, the worst
recent P&L on the board** — but the #2 all-time earner (+$150.78) with the best range availability here
(ATR 5.23%, medRng 4.26%, 100% ≥2%); **re-check 09-03 stands, two sessions away.**
**🔒 QQQ — structurally locked, restated: it is `MARKET_FILTER_SYMBOL` and parking it makes the market
gate fail OPEN.** On merit it fails the volatility floor outright (ATR 1.14%, medRng 0.94%, 5% ≥2%).
**Liquidity floor clean: no sub-$5 names, no halts, thinnest enabled is SPOT at $0.98B/day.**

### ➕ Adds — NONE, and the refusal is the same one as 08-31, now with three names instead of one
**~140 liquid large caps screened against the eight standing floors** (above BOTH MAs · ATR ≥2.3% ·
medRng ≥2.0% · ≥80% of 20 sessions ≥1.25% · ≥$0.85B/day · max 24-session gap ≤4% · 20/50 leg spread ≤9pp ·
positive 10-day return). **Three passed: TMO** (+1.88% / +10.09%, ATR 2.50%, $1.00B/day), **MCK** (+1.41% /
+6.05%, ATR 2.49%, $0.88B/day), **GILD** (+3.92% / +8.76%, ATR 2.49%, $0.88B/day).
- **All three are refused, and they are refused for one reason: they are the AMGN profile.** Every one is
  a **healthcare large cap at ~$0.9–1.0B/day with a low-2s ATR** — the exact template of the add that is
  currently failing its own falsification test, **which resolves tomorrow.** Adding three more copies of
  a profile the day before its test settles would make the test unreadable and is the clearest possible
  version of the error the log exists to prevent. **If AMGN parks on 09-02, this screen needs the
  IEX-tradability leg the 08-31 entry flagged (SIP dollar volume ≠ the tape the bot consumes) before any
  of these three can be reconsidered.**
- **The high-momentum names all failed on gap or spread, not on trend, and those floors did their job:**
  CRM (+24.3% / +40.7%, spread 16.4pp, gap 11.9%), NOW (spread 14.4pp), TEAM (gap **31.7%**), CRWD (gap
  10.1%), COIN (gap 7.8%), HOOD (gap 6.3%). Each is a 2%-stop-through-the-gap risk, not an intraday trend.
- **PANW and SNOW were excluded on earnings** (tonight AMC and Wednesday AMC), not on the screen.
- **Board headroom is 19/30 and is deliberately unused.** The daily review's finding stands: the score is
  the binding constraint, not the number of symbols.

### Changes applied to dbo.watchlist
**NONE.** No adds, no parks, no re-enables. Not one dated test came due today, the two names carrying red
legs (BABA, INTC) each fail only one leg, and the one name flagged for a park by yesterday's review (NFLX)
was cleared by the measurement. **The `.env`/service fix was the day's only intervention.**

### Final watchlist
**19 enabled** (≤30 ✅): AAPL, ABNB, AMD, AMGN, AMZN, BABA, DASH, INTC, LLY, MSFT, MU, NFLX, NVDA, PLTR,
QQQ, SPOT, TSLA, TSM, UBER. **Service restarted: YES — required, it was down.** `is-active` active,
NRestarts=0, ActiveEnterTimestamp 11:36:34 UTC, warmup primed **19/19**, all 19 subscribed on the IEX
feed, account reconciled (0 positions), **zero WARNING-or-above lines** (the single `grep` hit is the
substring "cancelErrors" inside the INFO subscription line — a false positive, verified).

### Dates carried forward
- **AMGN 09-02 (tomorrow) — park on zero candidates; evidence is 5/5 against and 0 rows in 11 days.**
- **AMZN 09-02 · INTC 09-03 · BABA 09-09 (now the most likely to fire) · AAPL 09-10 · AMD 09-12 ·
  NFLX 09-15 (new).**
- **Ops item, not a watchlist item: `.env` must never be left root-owned.** Any root edit needs
  `chown ustradebot:ustradebot` after it, or the bot silently misses the session.

---

## 2026-09-02 — Pre-market Research

**Both dated tests due today resolved as KEEP, and neither was a close call in the direction that would
have parked. No adds. NO CHANGES — 19 enabled, unchanged, service NOT restarted.** Book is CLEAN & FLAT
(broker-confirmed **0 positions, 0 orders of any status**, equity **$9,133.65**, `cash == equity ==
last_equity`) → **nothing locked, nothing at risk from any decision below.** Service `active` since
2026-09-01 23:17:54 UTC, NRestarts=0, and **`.env` verified `ustradebot:ustradebot` mode 600** — the
09-01 crash-loop hazard checked and clear before the open, as that review demanded.

### Market context
- **Third consecutive risk-off session setting up, and this one has a named driver.** Futures lower:
  **S&P −0.18%** (7,628.75), **Nasdaq 100 −0.49%** (28,981.50), Dow −0.06%, Russell −0.18%, **VIX +2.81%
  to 16.80**. QQQ itself −0.59% pre-market — the market-filter symbol is opening into weakness.
- **The driver is rates + oil, not tech fundamentals.** The **US 10-year hit 4.814%, its highest since
  November 2023**; UK/German/French yields rose with it and JGB 10y sits near multi-decade highs. **Crude
  ~$90.05** after the US and Iran exchanged strikes. Macquarie's Wizman: "higher yields are proving to be
  the stock market's undoing" — multiple compression, which hits exactly the long-duration growth names
  this watchlist is concentrated in.
- **Calendar: JOLTS (7.3M expected vs 7.36M prior) and August ISM Manufacturing, both just after the open
  at 14:00 UTC.** This is the **second session running** that a macro print lands at the exact minute the
  IMP-017 opening blackout lifts. 09-01's instance passed without incident (first refusal 14:02, conf ~45).
  **Still not a reason to widen the blackout — logging the third data point, not acting on it.**
- **No enabled name reports today.** **AVGO reports tonight AMC** (consensus rev ~$29.44B, +84.5% y/y;
  EPS $2.55) — parked, so no direct exposure, but it is **the AI-capex read-through into MU/NVDA/AMD/
  INTC/TSM for Thursday**, and AVGO fell **12.6%** the day after its last print. Flagging for tomorrow's
  run, not acting today.
- **Perplexity returned no catalyst for any of the 19 tickers for the THIRD run running**, and this time
  also failed to return futures direction or a movers list, then padded the calendar with irrelevant
  Fed statistical series (SOFR averages, Chicago Fed NFCI, metro-area employment). **Treated as thin and
  partly noise, not as an all-clear** — every fact above is WebSearch-verified. **If run four is also
  empty, the briefing step is not earning its place in this routine and should be flagged to the operator.**

### Carried from daily review (09-01 EOD)
- **"AMGN's 09-02 park test is now MOOT — do not park on the 4-session evidence, it produced rows on day
  5." HONOURED. AMGN is kept.** See below — I did not substitute my own reasoning for the review's
  instruction, but I did re-arm the question on a properly falsifiable footing.
- **"Do not add symbols to compensate for two flat sessions." HONOURED. No adds** (and the tape gives an
  independent second reason — see the adds section).
- **"Do not lower `ENTRY_THRESHOLD`."** Not a watchlist lever and not touched; noted because the temptation
  after two zero days is real and 08-31 already settled it in all three windows tested.
- **"NFLX's volatility-floor observation does not accumulate — it remains a 2-row anecdote."** HONOURED;
  NFLX produced no rows 09-01, so nothing accrued. Its 09-15 clock stands.
- **"AAPL was the most active name (10 of 17 candidates, top score 53.71) — watch it."** Confirmed on the
  12-day view: **22 scored refusals, best 61.6, active as recently as 09-01.** Healthy, still short of the bar.
- **"If today is a third sub-15% gate day, record it as a regime observation."** Recorded below.
- **⚠️ "Verify `.env` ownership and `is-active` before the open."** Done, both clean, stated above.

### Watchlist review
**Liveness (12d, scored refusals): 194 rows across 19 of 19 enabled names — every name on the board
produced at least one.** MSFT 34 (best 71.0) · AAPL 22 (61.6) · DASH 21 (73.5) · MU 17 (79.0) · UBER 16
(70.2) · NFLX 13 (66.8) · PLTR 10 (76.0) · TSM 10 (64.3) · AMZN 9 (**83.2 — top score on the board**) ·
AMD 9 (74.3) · QQQ 9 (61.0) · BABA 7 (68.6) · SPOT 6 (70.9) · LLY 5 (69.0) · ABNB 4 (67.0) · TSLA 4 (77.3) ·
INTC 3 (60.8) · **AMGN 2 (45.8)** · NVDA 2 (52.7). **The AMGN-shaped hole in this table is closed** — its
zero is gone, which is precisely why its park test is moot.

**🟡 AMGN — dated test due today, resolved KEEP on the daily review's instruction, and re-armed on a
better test.** The park case was built on *zero rows in 11 days*; it produced **2 rows on 09-01 (best
45.84)**, so the stated falsification condition ("park on zero candidates") did not occur. Keeping it is
the disciplined outcome — **the log's rule is to settle on the date against the stated condition, not to
reach for a replacement condition when the stated one fails.** But recording the weakness honestly:
2 rows in 12 days against a board median of 9, a best score of **45.8 that is the lowest maximum on the
entire board** and 14 points short of the bar, **ATR now 2.02% — below the 2.3% floor it was admitted
under on 08-26 (2.31%)** — and medRng 2.26%, 60% ≥2%, $1.05B/day. It is above both MAs (+2.75% / +11.88%),
so the two-leg trend rule does not fire and no exemption is needed. **New dated test, stated so it cannot
be moved again: 09-16 — park unless AMGN has by then produced either a score ≥60 or ≥8 scored rows in the
prior 12 days.** That is a liveness-quality test, not a liveness-existence test, and two rows at 45 will
not satisfy it.

**🟡 AMZN — dated test due today, resolved KEEP, and it is the board's best scorer.** The two-leg park
rule needs **both** a ≥30d dead-signal clock **and** price below both MAs. Leg one **fires**: last entry
**2026-08-03, exactly 30d**. Leg two **does not**: **−3.64% vs 20MA but +0.99% vs 50MA — still above it.**
One leg has never been sufficient, and the countervailing evidence is strong: **9 scored rows with a best
of 83.2, the single highest confidence print on the whole board this fortnight**, most recently 08-28.
A name scoring 83 is not a dead signal. **But the 50MA cushion is thinning fast — +3.10% yesterday to
+0.99% today, and one more down session puts it below both.** Lifetime −$108.51 is the second-worst on the
board and is noted without being load-bearing on its own. **Re-check 09-04**, two sessions out, deliberately
short: if it loses the 50MA while the clock is already past 30d, both legs fire and it parks that day.

**✅ Everything else kept; no other dated test comes due.** **Below both MAs but clock nowhere near 30d:**
TSM (−1.31 / −1.76, traded **6d** ago) · INTC (−6.54 / −13.61 on a −7.98% 10-day, the deepest downtrend
here, **16d**, re-check **09-03 tomorrow** and AVGO's print tonight is direct read-through) · AMD (−3.93 /
−8.61, **20d**, **09-12**) · BABA (−8.50 / −2.19, −11.94% over 10 days, **23d** — **09-09 stands and BABA
remains the most likely name to park on its date**) · LLY (−3.86 / −2.45, added 08-20, **no trade yet at
13d — too new to judge**, ATR 3.17%, $3.37B/day, 5 rows best 69.0). **Above both MAs, trend leg cannot
fire:** AAPL (+4.44 / +3.90, exempt, **09-10**) · NFLX (+3.30 / +7.92, ATR 2.79%, **09-15**) · AMGN ·
DASH (+1.99 / +12.29, ATR 3.36%, 100% ≥2%, 21 rows — still the strongest all-round name) · PLTR (+2.86 /
+23.14, ATR 3.78%) · SPOT (+4.94 / +9.62, ATR 3.71%, 100% ≥2%, **thinnest enabled at $0.89B/day and now
below the $0.85B add-floor's margin — on notice for liquidity alone, unchanged**) · MSFT (+1.27 / +14.94,
most active on the board) · ABNB (+0.55 / +13.77) · TSLA (+3.95 / −0.77, 95% ≥2%, best recent earner).
**Mixed:** MU (+0.44 / −1.32, **$26.88B/day**, ATR 5.30%, #1 all-time earner +$189.55) · NVDA (−0.73 /
+4.14, $27.89B/day) · UBER (−1.47 / +1.89).
**Liquidity floor clean: no sub-$5 names, no halts, thinnest is SPOT at $0.89B/day.**

**🔒 QQQ — both park legs fire on merit, and it is structurally exempt. Re-verified in code this run
rather than taken on faith from the prior entry.** QQQ is 50d without a trade **and** below both MAs
(−1.44 / −0.47), and it fails the volatility floor outright (**ATR 1.19%, medRng 0.94%, 0% of 20 sessions
≥2%**). On merit it is the worst name on the board. **It must not be parked:** `bot/strategy.py:264-278`
(`_market_gate_open`) resolves `MARKET_FILTER_SYMBOL` (`bot/config.py:332`, default **QQQ**) out of
`self._gate_snap`, and when the symbol has no ribbon — which is exactly what happens when it leaves the
watchlist — it **returns `True` and only logs a warning**. Parking QQQ therefore does not tighten the bot;
it **silently disables the market filter entirely and fails the gate OPEN**, which is the opposite of the
intent and would be near-invisible in the logs. Restating with the file:line so no future run has to
re-derive it.

### 🌐 Regime observation — recorded explicitly, as 09-01's review asked
**The QQQ 5-min gate has printed 42.0% (08-25) · 43.3% (08-26) · 71.1% (08-27) · 28.1% (08-28) · 13.0%
(08-31) · 0.0% (09-01) — a monotonic collapse over four sessions, and today opens into rising yields,
$90 oil and QQQ −0.59% pre-market.** A third consecutive sub-15% session is the base case. **This is the
gate working, not failing.** A long-only intraday trend bot in a rates-driven risk-off drift *should*
print zeros; the gate is refusing to buy a tape that is not trending up. **The correct response is to let
it print zeros, and specifically NOT to (a) add symbols, (b) lower `ENTRY_THRESHOLD`, or (c) treat the
flat sessions as evidence the board is dead** — 194 scored rows across all 19 names says it plainly is not.
**The thing to watch is the opposite risk:** the 09-01 review's finding is that this bot has **no
demonstrated edge** (+0.008R/trade over 274 trades, 7% true win rate under the stop doctrine, only 7.3% of
trades ever reaching +1R). **A flat book is currently the best outcome available to it**, and churning the
watchlist to manufacture fills would convert a harmless zero into a live drawdown. That is the reasoning
behind today's no-change decision as much as any single symbol's numbers.

### ➕ Adds — NONE, for three independent reasons
**~140 liquid large caps screened against the eight standing floors** (above BOTH MAs · ATR ≥2.3% ·
medRng ≥2.0% · ≥80% of 20 sessions ≥1.25% · ≥$0.85B/day · max 24-session gap ≤4% · 20/50 leg spread ≤9pp ·
positive 10-day return). The same three healthcare names clear as on 08-31 — **TMO, MCK, GILD** — and all
three are refused again:
1. **They are the AMGN profile, and AMGN did not pass its test — it merely failed to trigger the specific
   condition written down for it.** Each is a healthcare large cap at ~$0.9–1.0B/day with a low-2s ATR.
   AMGN's live behaviour under that profile is 2 rows at best-45.8 in 12 days. **The 08-31 entry said these
   could be reconsidered only after AMGN's test settled; it settled as "alive but the weakest name on the
   board," which argues against copying the profile three more times, not for it.** The IEX-tradability
   leg that entry flagged (SIP dollar volume ≠ the tape the bot actually consumes) is **still not built**,
   and all three sit close enough to the $0.85B floor that it would plausibly decide them.
2. **The tape.** Adding momentum names on a day with the 10-year at a 3-year high, oil at $90 and the gate
   trending to zero would put new symbols on the board precisely when nothing can trade anyway — all
   selection risk, no upside.
3. **The standing instruction not to add after flat sessions**, which is the exact impulse this section
   exists to resist.
**The high-momentum cohort failed on gap/spread as before** (CRM spread 16.4pp / gap 11.9%, NOW 14.4pp,
TEAM gap 31.7%, CRWD 10.1%, COIN 7.8%, HOOD 6.3%) — each a 2%-stop-through-the-gap risk, not an intraday
trend. **AVGO and SNOW excluded on tonight's earnings.** **Board headroom is 19/30 and stays deliberately
unused: the binding constraint is the score and the gate, not the symbol count.**

### Changes applied to dbo.watchlist
**NONE.** No adds, no parks, no re-enables. Both dated tests due today (AMGN, AMZN) resolved KEEP against
their stated conditions; the only name whose park legs both fire is QQQ, which is structurally exempt;
no enabled name has an earnings print or a verified negative catalyst today.

### Final watchlist
**19 enabled** (≤30 ✅), unchanged: AAPL, ABNB, AMD, AMGN, AMZN, BABA, DASH, INTC, LLY, MSFT, MU, NFLX,
NVDA, PLTR, QQQ, SPOT, TSLA, TSM, UBER. **Service restarted: NO — not needed, nothing changed.** Left
`active`, NRestarts=0, up since 2026-09-01 23:17:54 UTC with the same 19 symbols already loaded. Deliberately
not restarted: a restart with an identical watchlist would discard a warm 19/19 ribbon set and re-warm it
for no benefit, ~3h before the open.

### Dates carried forward
- **AMZN 09-04 (new, shortened) — parks if it loses the 50MA; the 30d clock leg has already fired.**
- **INTC 09-03 (tomorrow) · BABA 09-09 (most likely to fire) · AAPL 09-10 · AMD 09-12 · NFLX 09-15 ·
  AMGN 09-16 (new, re-armed as a score-quality test: ≥60 print or ≥8 rows in 12d, else park).**
- **For tonight's daily review:** AVGO reports AMC — its guide is the AI-capex read-through into
  MU/NVDA/AMD/INTC/TSM for Thursday, and INTC's re-check falls the same day.
- **For the operator:** Perplexity has now returned nothing usable three runs running and today also
  returned junk calendar entries. Worth checking the sonar call is still fit for purpose.
- **Ops item, unchanged: `.env` must never be left root-owned** — any root edit needs
  `chown ustradebot:ustradebot` after it, or the bot silently misses the session.
