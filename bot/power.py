"""Time-to-decision: can the live book ever settle this bot's expectancy? (IMP-054)

Ten weekly reviews have implied the same answer and none has stated it. The ask has
been on the board three consecutive weeks — *"at the current fill rate and true win
rate, how many weeks of live trading are needed to distinguish this strategy's
expectancy from zero at any reasonable confidence? I expect the answer to be years.
If it is, that single number should govern the retire-or-rebuild decision"* — and it
was dropped every time in favour of another instrument. This module is that
arithmetic, made repeatable so nobody has to trust a one-off script.

**Why it is the decision, not a diagnostic.** Every other explanation for a 5-7% true
win rate has been closed by measurement: the entry-filter stack (2026-09-16, all-off
loses $1,162 at PF 0.67), the market gate (2026-09-18, declines +1R candidates 16.3%
of the time against the taken book's own 23.3% ceiling), ``ENTRY_THRESHOLD`` (three
refutations in four days), trail arming and trail width (2026-09-11, pure relabelling
— WIN count moved by zero trades in all three windows), and a reachable ``TAKE_PROFIT``
(2026-09-21, expectancy/PF/payoff fall monotonically as the target tightens). What
remains is the entry signal itself, and the only court that can judge a replacement is
the live book — so the live book's resolving power **is** the constraint on every
remaining question.

**The trap this module is built to avoid.** The obvious calculation — take the observed
mean, take the observed SD, solve for the n that would make *that* mean significant —
is post-hoc power, and it is circular: it assumes the estimate whose reality is in
question. Run on this bot it also answers almost anything you like, because the cohorts
disagree by 18x:

    all-time (n=282, from 2026-06-09)      +$0.37/trade   ->  ~33,000 trades
    post-IMP-021 (n=38, current geometry)  +$6.72/trade   ->  ~85 trades

Both estimates have 95% intervals straddling zero, so the data cannot say which is the
truth, and the "answer" is whichever cohort you picked. :func:`required_trades` is
provided because the ask names it, but the honest instrument is the inverse and it is
free of the assumption:

    **minimum detectable expectancy** — given the trades a calendar horizon actually
    buys at the measured fill rate, what is the *smallest* per-trade edge the live book
    could confirm? Compare that floor with what the bot has produced.

That statement needs no assumption about the true mean, it degrades gracefully, and it
turns "is this bot unfalsifiable?" into a number the operator can act on: an edge below
the floor cannot be demonstrated within the horizon at any fill rate the bot achieves,
however real it is.

**Arithmetic, and its one approximation.** Sample size for a one-sample two-sided test
of ``mean == 0`` is the textbook normal form

    n = ((z_{1-alpha/2} + z_{power}) * sd / mean)^2

plus :data:`T_CORRECTION`, the standard +2 that accounts for using a t-test with an
estimated SD rather than a known one. Verified by simulation at the levels this bot
uses: at the computed n, achieved power is 0.802-0.806 against the 0.800 target
(0.795-0.796 without the correction). No scipy on the VPS, so the two quantiles needed
are tabulated in :data:`_Z` and an unsupported level raises rather than silently
approximating.

Confidence intervals here are normal-based, which makes them **narrower** than the
exact t interval at these sample sizes. That is deliberate and it only ever
strengthens the conclusion this module reaches: when a normal interval already
straddles zero, the wider t interval necessarily does too.

Read-only, pure arithmetic, no I/O outside ``__main__``. Nothing the service imports
imports this — it changes what we *know*, never what we *do*.
"""

from __future__ import annotations

import datetime as dt
import logging
import math
import statistics
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

log = logging.getLogger("ustradebot.power")

# Standard normal quantiles. scipy is not installed on the VPS and is not worth a new
# runtime dependency for two constants, so the supported levels are tabulated and
# anything else raises — a wrong quantile would be invisible in the output.
_Z: dict[float, float] = {
    0.80: 0.8416212336,  # z_0.80 — the power term for 80% power
    0.90: 1.2815515655,  # z_0.90 — 90% power, and z_{1-alpha/2} for alpha=0.20
    0.95: 1.6448536270,  # z_{1-alpha/2} for alpha=0.10 (two-sided)
    0.975: 1.9599639845,  # z_{1-alpha/2} for alpha=0.05 (two-sided)
    0.995: 2.5758293035,  # z_{1-alpha/2} for alpha=0.01 (two-sided)
}

# The Guenther/Snedecor adjustment: a one-sample t-test needs about two more
# observations than the normal formula says, because the SD is estimated. Simulation
# at this bot's levels puts achieved power at 0.802-0.806 with it and 0.795-0.796
# without, so it is applied rather than noted.
T_CORRECTION = 2

ALPHA_DEFAULT = 0.05
POWER_DEFAULT = 0.80

# Calendar horizons the operator actually chooses between, in weeks.
DEFAULT_HORIZONS: tuple[int, ...] = (13, 26, 52, 104, 260)

# Trailing complete ISO weeks used to measure the current fill rate. Five weeks is
# short enough to track a cadence that has fallen 45/week -> single digits since
# 2026-07, and long enough that one dead week does not halve the estimate.
FILL_RATE_WEEKS = 5


def _z(p: float) -> float:
    try:
        return _Z[p]
    except KeyError:  # pragma: no cover - guarded by validate-style callers
        raise ValueError(
            f"no tabulated normal quantile for {p}; supported: {sorted(_Z)}"
        ) from None


def _z_terms(alpha: float, power: float) -> float:
    """``z_{1-alpha/2} + z_{power}``, the numerator of every formula here."""
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    if not 0 < power < 1:
        raise ValueError(f"power must be in (0, 1), got {power}")
    return _z(round(1 - alpha / 2, 6)) + _z(power)


@dataclass(frozen=True)
class ExpectancySample:
    """What one cohort of closed trades says about per-trade expectancy.

    ``unit`` is carried so a caller cannot mix the dollar and R views: dollars are
    what the account feels, R is what the doctrine scores, and their required sample
    sizes differ (position size varies, so the two are not proportional).
    """

    n: int
    mean: float
    sd: float
    unit: str

    @property
    def stderr(self) -> float:
        return self.sd / math.sqrt(self.n) if self.n else float("nan")

    @property
    def t_stat(self) -> float:
        """Observed mean in standard errors. |t| >~ 2 is the significance line."""
        se = self.stderr
        return self.mean / se if se else float("nan")

    def interval(self, alpha: float = ALPHA_DEFAULT) -> tuple[float, float]:
        """Normal-based CI — narrower than the exact t interval, see module docs."""
        half = _z(round(1 - alpha / 2, 6)) * self.stderr
        return (self.mean - half, self.mean + half)

    def straddles_zero(self, alpha: float = ALPHA_DEFAULT) -> bool:
        """True when the cohort cannot tell this expectancy from zero.

        Conservative by construction: the normal interval is the narrow one, so a
        True here would also be True on the wider t interval.
        """
        lo, hi = self.interval(alpha)
        return lo <= 0.0 <= hi


def sample_expectancy(values: Sequence[float], unit: str) -> ExpectancySample | None:
    """Mean and SD of a per-trade series. ``None`` below two trades (no SD)."""
    if len(values) < 2:
        return None
    return ExpectancySample(
        n=len(values),
        mean=statistics.fmean(values),
        sd=statistics.stdev(values),
        unit=unit,
    )


def required_trades(
    mean: float,
    sd: float,
    *,
    alpha: float = ALPHA_DEFAULT,
    power: float = POWER_DEFAULT,
) -> int | None:
    """Trades needed to call an edge of size ``mean`` significant.

    **Post-hoc power — read the module docstring before quoting this.** It assumes the
    observed mean is the true one, which is the question, not the answer. Returns
    ``None`` for a zero mean, where no finite sample suffices.
    """
    if not mean or sd <= 0:
        return None
    return math.ceil((_z_terms(alpha, power) * sd / abs(mean)) ** 2) + T_CORRECTION


def minimum_detectable_expectancy(
    n: int,
    sd: float,
    *,
    alpha: float = ALPHA_DEFAULT,
    power: float = POWER_DEFAULT,
) -> float | None:
    """The smallest per-trade edge ``n`` trades could confirm — the honest inverse.

    Inverts :func:`required_trades` on the same arithmetic, so the two agree, and
    assumes nothing about the true mean. An edge below this floor is not detectable
    in ``n`` trades however real it is: that is the unfalsifiability, quantified.
    """
    usable = n - T_CORRECTION
    if usable <= 0 or sd <= 0:
        return None
    return _z_terms(alpha, power) * sd / math.sqrt(usable)


@dataclass(frozen=True)
class Horizon:
    """One row of the decision table: what a calendar budget buys."""

    weeks: int
    trades: int
    mde: float | None

    @property
    def months(self) -> float:
        return self.weeks * 12.0 / 52.0


def horizon_table(
    sd: float,
    fills_per_week: float,
    *,
    already: int = 0,
    weeks: Iterable[int] = DEFAULT_HORIZONS,
    alpha: float = ALPHA_DEFAULT,
    power: float = POWER_DEFAULT,
) -> list[Horizon]:
    """Minimum detectable expectancy at each calendar horizon.

    ``already`` credits the trades the cohort has banked, so the table answers "from
    here" rather than "from scratch" — the operator's actual question.
    """
    rows = []
    for w in weeks:
        n = already + int(fills_per_week * w)
        rows.append(Horizon(weeks=w, trades=n, mde=minimum_detectable_expectancy(
            n, sd, alpha=alpha, power=power)))
    return rows


def weeks_to_confirm(
    sample: ExpectancySample,
    fills_per_week: float,
    *,
    alpha: float = ALPHA_DEFAULT,
    power: float = POWER_DEFAULT,
) -> float | None:
    """Calendar weeks until ``sample``'s observed edge would be confirmable.

    Post-hoc, like :func:`required_trades`, and credited for trades already taken.
    ``None`` when the edge is zero or the bot is taking no trades.
    """
    need = required_trades(sample.mean, sample.sd, alpha=alpha, power=power)
    if need is None or fills_per_week <= 0:
        return None
    return max(0.0, (need - sample.n) / fills_per_week)


def fills_per_week(
    exit_dates: Iterable[dt.date],
    *,
    weeks: int = FILL_RATE_WEEKS,
    today: dt.date | None = None,
) -> float:
    """Measured fill rate over the trailing ``weeks`` **complete** ISO weeks.

    The current week is excluded because it is partial, and a cohort's own
    trades/span is *not* used: this bot's cadence has collapsed from 45 trades/week
    (2026-W28) to single digits, so a long-run average would credit the live book
    with resolving power it no longer has. Rate is per calendar week, which is what a
    calendar horizon spends.
    """
    today = today or dt.datetime.now(dt.UTC).date()
    current = today.isocalendar()[:2]
    counts = Counter(d.isocalendar()[:2] for d in exit_dates)
    wanted = []
    cursor = today - dt.timedelta(days=7)
    while len(wanted) < weeks:
        key = cursor.isocalendar()[:2]
        if key != current:
            wanted.append(key)
        cursor -= dt.timedelta(days=7)
    return sum(counts.get(k, 0) for k in wanted) / weeks


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}" if unit == "$" else f"{value:+.4f}R"


def format_power(
    sample: ExpectancySample,
    rate: float,
    *,
    alpha: float = ALPHA_DEFAULT,
    power: float = POWER_DEFAULT,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
) -> str:
    """The block that goes in front of the operator."""
    lo, hi = sample.interval(alpha)
    u = sample.unit
    conf = int(round((1 - alpha) * 100))
    lines = [
        f"— time-to-decision ({u}, n={sample.n}) —",
        f"  expectancy {_fmt(sample.mean, u)}/trade  sd {_fmt(sample.sd, u)}  "
        f"t={sample.t_stat:+.2f}",
        f"  {conf}% CI [{_fmt(lo, u)}, {_fmt(hi, u)}] — "
        + ("straddles zero: NOT distinguishable" if sample.straddles_zero(alpha)
           else "excludes zero"),
        f"  fill rate {rate:.2f} trades/week (trailing {FILL_RATE_WEEKS} complete ISO weeks)",
    ]
    need = required_trades(sample.mean, sample.sd, alpha=alpha, power=power)
    wks = weeks_to_confirm(sample, rate, alpha=alpha, power=power)
    if need is None or wks is None:
        lines.append("  if this estimate were the truth: unconfirmable (zero edge or zero fills)")
    else:
        lines.append(
            f"  if this estimate were the truth: {need} trades total "
            f"({max(0, need - sample.n)} more) = {wks:.0f} weeks = {wks / 52:.1f} years"
            "  [post-hoc, see docs]"
        )
    lines.append(f"  minimum detectable expectancy at {int(power * 100)}% power:")
    for row in horizon_table(sample.sd, rate, already=sample.n, weeks=horizons,
                             alpha=alpha, power=power):
        lines.append(
            f"    {row.weeks:>3} wk ({row.months:>4.1f} mo) -> {row.trades:>5} trades  "
            f"MDE {_fmt(row.mde, u)}/trade"
        )
    return "\n".join(lines)


def _parse_int(argv: list[str], flag: str, default: int) -> int:
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            try:
                return int(argv[i + 1])
            except ValueError:
                pass
    return default


def _parse_float(argv: list[str], flag: str) -> float | None:
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            try:
                return float(argv[i + 1])
            except ValueError:
                pass
    return None


def main(argv: list[str] | None = None) -> int:
    """``python -m bot.power [--days N] [--fills-per-week X]``. Read-only."""
    from bot.config import Config, ConfigError
    from bot.doctrine import verdicts_for
    from bot.persistence import open_store

    args = sys.argv[1:] if argv is None else argv
    days = _parse_int(args, "--days", 365)
    try:
        cfg = Config.load()
    except ConfigError as e:
        print(f"config error: {e}")
        return 1
    store = open_store(cfg)
    if store is None:
        print("persistence disabled or unreachable — no power report.")
        return 1
    trades = store.closed_trades(days)
    store.close()
    if len(trades) < 2:
        print(f"only {len(trades)} closed trades in {days}d — nothing to size.")
        return 1

    override = _parse_float(args, "--fills-per-week")
    rate = override if override is not None else fills_per_week(
        [t.exit_time_utc.date() for t in trades]
    )
    verdicts = verdicts_for(trades, cfg.stop_loss)
    print(f"📐 USTradeBot — time to decision (last {days}d, {len(trades)} closed trades)")
    for values, unit in (([t.pnl for t in trades], "$"),
                         ([v.profit_r for v in verdicts], "R")):
        sample = sample_expectancy(values, unit)
        if sample is not None:
            print(format_power(sample, rate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
