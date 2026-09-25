"""Which confidence sub-score actually predicts anything (IMP-056).

The entry score is a weighted blend of five 0–1 sub-scores. Every entry decision this
bot has ever made turns on that blend, and until tonight **no instrument existed to ask
which of the five terms carries information.** Weights have been moved three times
(IMP-034 dropped ``volume`` to zero, IMP-036 reversed ``volatility``'s anchors, IMP-047
tried and rejected redistributing ``rsi``'s 20 points) and each time the question was
settled by replaying net P&L — which answers "did this config make money on that
window", not "is this term a ranking term at all".

Those are different questions, and the second one is cheaper, more stable, and logically
prior. A term that does not correlate with what the tape subsequently does cannot help
rank candidates at *any* weight, and no amount of replay tuning will make it.

**The measurement.** For every scored-but-refused candidate (``dbo.entry_refusals``,
which stores the full sub-score vector at decision time) pair the term's value with the
outcome :mod:`bot.refusals` already computes — MFE and the forward close to the session
flatten. Then report, per term:

* ``sd`` — the spread of the term across the population. **Read this first.** A term
  pinned near one value is a constant subsidy, not a ranking term, whatever its
  correlation says; a correlation computed on a degenerate column is noise amplified by
  a small denominator. ``DEGENERATE_SD`` marks the line.
* ``r_mfe`` / ``r_fwd`` — Pearson correlation against the two outcomes.
* the banded cohort table — because a term can be informative non-monotonically, which
  a single correlation hides.

**Why the refusal population and not closed trades.** It is 30–70x larger (430 rows with
a full vector versus 6 closed trades since the same date), it is unconfounded by sizing,
capital limits and exit geometry, and it is the population the entry filter is actually
choosing over. Its limitation is inherited from :mod:`bot.refusals` and is the same one
printed there: these candidates were *declined*, so this measures the term's power to
rank the tape, not a P&L an alternative config would have earned.

**What it found on first run (2026-09-25, n=430, scorer v3).** Stated here because it is
the reason the module exists and the tests pin it:

==============  =====  ========  ========  ==================================
term               sd     r_mfe     r_fwd  reading
==============  =====  ========  ========  ==================================
crossover       0.115    +0.330    +0.077  the only informative term
trend           0.154    ~0        ~0      weak
rsi (raw)        —       −0.025    −0.012  **noise, across its whole domain**
volatility      0.272    (see IMP-036)     informative, already acted on
==============  =====  ========  ========  ==================================

``conf_rsi`` is >= 0.95 on 97% of the population and every one of the 430 recorded
``rsi_raw`` values lands between 45 and 70 — inside or adjacent to the flat 45–65
plateau — so its three other branches have never fired. IMP-047 recorded ``rsi_raw``
specifically so a future run could "sweep the band edges on recorded history"; this is
that sweep, and the answer is that **there is no band edge to sweep to.** The outcome
surface is flat in RSI, so re-anchoring the plateau would replace a constant with noise.

This module only measures. It changes no weight, no threshold and no trading path — on
this bot a weight change is a config change, and the escalation rule in the stop-exit
doctrine forbids those while FAIL+SCRATCH sits at 100% of closed trades.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# Below this spread a 0–1 sub-score is a constant subsidy, not a ranking term.
# 0.10 is one tenth of the score's full range: a term that moves less than that across
# the whole population cannot reorder candidates by more than a tenth of its weight.
DEGENERATE_SD = 0.10

# The bands each term is bucketed into for the cohort table. ``rsi_raw`` is on its own
# 0–100 scale; the four sub-scores share the 0–1 one.
SUBSCORE_BANDS: tuple[tuple[float, float], ...] = (
    (0.00, 0.10), (0.10, 0.20), (0.20, 0.35), (0.35, 0.60), (0.60, 1.01),
)
RSI_BANDS: tuple[tuple[float, float], ...] = (
    (0.0, 45.0), (45.0, 55.0), (55.0, 60.0), (60.0, 65.0), (65.0, 70.0), (70.0, 101.0),
)


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson correlation, or ``None`` when it is undefined.

    Undefined means fewer than two pairs or a constant column — both of which happen
    routinely here (a fully saturated sub-score is exactly a constant column), and
    neither should be reported as a correlation of zero: "no variation to correlate"
    and "varies, predicts nothing" are different findings.
    """
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx <= 0.0 or sy <= 0.0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def stdev(xs: Sequence[float]) -> float:
    """Population standard deviation; 0.0 for fewer than two values."""
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / n)


@dataclass(frozen=True)
class Band:
    """One cohort of a term's range, paired with what the tape then did."""

    lo: float
    hi: float
    n: int
    avg_mfe: float
    avg_forward: float
    reached_1r: int


@dataclass(frozen=True)
class TermPower:
    """One sub-score's measured ability to rank candidates."""

    name: str
    n: int
    mean: float
    sd: float
    r_mfe: float | None
    r_forward: float | None
    bands: tuple[Band, ...]

    @property
    def degenerate(self) -> bool:
        """True when the term barely varies — read before any correlation."""
        return self.sd < DEGENERATE_SD


def _bands_for(
    pairs: Sequence[tuple[float, float, float, bool]],
    edges: Sequence[tuple[float, float]],
) -> tuple[Band, ...]:
    """Bucket ``(value, mfe, forward, hit_1r)`` rows into ``edges``; drop empty bands."""
    out: list[Band] = []
    for lo, hi in edges:
        g = [p for p in pairs if lo <= p[0] < hi]
        if not g:
            continue
        out.append(
            Band(
                lo=lo,
                hi=hi,
                n=len(g),
                avg_mfe=sum(p[1] for p in g) / len(g),
                avg_forward=sum(p[2] for p in g) / len(g),
                reached_1r=sum(1 for p in g if p[3]),
            )
        )
    return tuple(out)


def term_power(
    outcomes: Sequence,
    name: str,
    attr: str,
    stop_loss: float,
    edges: Sequence[tuple[float, float]] = SUBSCORE_BANDS,
) -> TermPower | None:
    """Measure one term over :class:`~bot.refusals.RefusalOutcome` rows.

    Rows whose term is ``None`` are skipped rather than zero-filled: these rows span
    several schema generations and "not recorded" must not be read as a sub-score of
    0.0, which would manufacture exactly the variation this module exists to test for.
    Returns ``None`` when nothing in the window carries the term.
    """
    one_r = stop_loss * 100.0
    pairs: list[tuple[float, float, float, bool]] = []
    for o in outcomes:
        v = getattr(o, attr, None)
        if v is None:
            continue
        mfe = float(o.mfe_pct)
        pairs.append((float(v), mfe, float(o.forward_pct), one_r > 0 and mfe >= one_r))
    if not pairs:
        return None
    vals = [p[0] for p in pairs]
    return TermPower(
        name=name,
        n=len(pairs),
        mean=sum(vals) / len(vals),
        sd=stdev(vals),
        r_mfe=pearson(vals, [p[1] for p in pairs]),
        r_forward=pearson(vals, [p[2] for p in pairs]),
        bands=_bands_for(pairs, edges),
    )


# The five terms, in the order the score blends them. ``volume`` carries zero weight
# since IMP-034 but is still measured — a term at weight 0 that turned out to be the
# informative one would be the most actionable finding this table could produce.
TERMS: tuple[tuple[str, str, bool], ...] = (
    ("crossover", "conf_crossover", False),
    ("trend", "conf_trend", False),
    ("rsi", "conf_rsi", False),
    ("volume", "conf_volume", False),
    ("volatility", "conf_volatility", False),
    ("rsi_raw", "rsi_raw", True),
)


def measure_terms(outcomes: Sequence, stop_loss: float) -> list[TermPower]:
    """Measure every term; skips those absent from the window."""
    out: list[TermPower] = []
    for name, attr, is_rsi_raw in TERMS:
        tp = term_power(
            outcomes, name, attr, stop_loss,
            RSI_BANDS if is_rsi_raw else SUBSCORE_BANDS,
        )
        if tp is not None:
            out.append(tp)
    return out


def _r(x: float | None) -> str:
    return "   n/a" if x is None else f"{x:+6.3f}"


def format_terms(powers: Sequence[TermPower], stop_loss: float) -> str:
    """Render the per-term table. Pure; the caller decides where it goes."""
    if not powers:
        return "— sub-score power — no scored candidates in this window."
    lines = [
        "— sub-score power: which entry term predicts the tape —",
        "  counterfactual: enter at the refusal candle's close, flatten with the session.",
        f"  {'term':11s} {'n':>5s} {'mean':>6s} {'sd':>6s} {'r(MFE)':>7s} {'r(fwd)':>7s}  reading",
    ]
    for p in powers:
        if p.degenerate:
            reading = f"DEGENERATE (sd < {DEGENERATE_SD:.2f}) — a constant, not a ranking term"
        elif p.r_mfe is None:
            reading = "no variation to correlate"
        elif abs(p.r_mfe) >= 0.20:
            reading = "informative"
        elif abs(p.r_mfe) >= 0.10:
            reading = "weak"
        else:
            reading = "NOISE — no measured power to rank candidates"
        lines.append(
            f"  {p.name:11s} {p.n:5d} {p.mean:6.3f} {p.sd:6.3f} "
            f"{_r(p.r_mfe)} {_r(p.r_forward)}  {reading}"
        )
    lines.append(f"  bands (avgMFE / avgFwd / >=1R of n), 1R = {stop_loss * 100:.2f}%:")
    for p in powers:
        cells = " ".join(
            f"[{b.lo:g}-{b.hi:g}) n={b.n} {b.avg_mfe:+.2f}%/{b.avg_forward:+.2f}%/{b.reached_1r}"
            for b in p.bands
        )
        lines.append(f"    {p.name:11s} {cells}")
    lines.append(
        "  NOTE — read 'sd' before any correlation: a term pinned near one value cannot "
        "rank candidates at any weight, and its r is computed on a near-constant column."
    )
    lines.append(
        "  NOTE — this ranks the tape, not P&L. A term with power here still has to earn "
        "its weight in replay; a term with none cannot earn it anywhere."
    )
    return "\n".join(lines)
