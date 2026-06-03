"""Preflight connectivity check (Phase 8).

A single command — ``python -m bot.preflight`` — that verifies the bot's three
external dependencies are live *before* committing to a long market-hours run:

1. **Alpaca paper account** — the trading critical path; a failure here is fatal.
2. **SQL Server persistence** — a side-channel; unreachable/disabled is a warning,
   the bot would still trade (see :mod:`bot.persistence`).
3. **Telegram alerts** — a side-channel; sends a real test message so you can
   confirm delivery in the chat. Unreachable/disabled is a warning.

It also reports whether the regular session is open *now* (US Eastern, EST/EDT
aware) so you know whether to expect live ticks.

Each check returns a :class:`CheckResult` with a PASS / WARN / FAIL status. The
process exits non-zero only when a *critical* check (config or Alpaca) fails — a
WARN means a side-channel is off but the bot can still trade. The individual
``check_*`` helpers take their dependency directly so they unit-test with fakes,
mirroring the rest of the codebase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from bot.config import EASTERN, Config, ConfigError
from bot.market_data import MarketDataClient
from bot.notifier import TelegramNotifier, open_notifier
from bot.persistence import TradeStore, open_store
from bot.signals import market_is_open

log = logging.getLogger("ustradebot.preflight")


class Status(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    detail: str
    critical: bool = False  # a failing critical check aborts the live run

    @property
    def ok(self) -> bool:
        return self.status is not Status.FAIL


def check_alpaca(data: MarketDataClient) -> CheckResult:
    """Hit the paper REST endpoint; PASS reports equity / buying power / positions."""
    try:
        account, positions = data.check_account()
    except Exception as e:  # noqa: BLE001 — surface any failure as a FAIL line
        return CheckResult(
            "Alpaca paper account",
            Status.FAIL,
            f"could not reach the account: {e}",
            critical=True,
        )
    status = getattr(account, "status", "?")
    equity = getattr(account, "equity", "?")
    bp = getattr(account, "buying_power", "?")
    detail = (
        f"status={status} equity={equity} buying_power={bp} "
        f"open_positions={len(positions)}"
    )
    # An account that isn't ACTIVE can still respond but won't trade — flag it.
    st = Status.PASS if str(status).upper().endswith("ACTIVE") else Status.WARN
    return CheckResult("Alpaca paper account", st, detail, critical=True)


def check_database(cfg: Config, store: TradeStore | None) -> CheckResult:
    """``store`` is the result of :func:`open_store` (None = off or unreachable)."""
    if store is not None:
        return CheckResult("SQL Server persistence", Status.PASS, "connected; schema ensured")
    if not cfg.sqlserver_conn:
        return CheckResult(
            "SQL Server persistence",
            Status.WARN,
            "disabled (SQLSERVER_CONN unset) — bot would trade without persistence",
        )
    return CheckResult(
        "SQL Server persistence",
        Status.WARN,
        "configured but unreachable (schema bootstrap failed) — bot would trade without it",
    )


def check_telegram(notifier: TelegramNotifier | None) -> CheckResult:
    """Send a real test message; PASS means the Bot API accepted it."""
    if notifier is None:
        return CheckResult(
            "Telegram alerts",
            Status.WARN,
            "disabled (TELEGRAM_TOKEN/CHAT_ID unset) — bot would trade without alerts",
        )
    delivered = notifier.send("✅ USTradeBot preflight — connectivity OK")
    if delivered:
        return CheckResult("Telegram alerts", Status.PASS, "test message delivered to the chat")
    return CheckResult(
        "Telegram alerts",
        Status.WARN,
        "sendMessage failed (see log) — bot would trade without alerts",
    )


def check_market_hours(cfg: Config, now_utc: datetime) -> CheckResult:
    """Report whether the regular session is open now (US Eastern, EST/EDT aware)."""
    is_open = market_is_open(now_utc, cfg.market_open, cfg.market_close)
    et = now_utc.astimezone(EASTERN)
    when = et.strftime("%Y-%m-%d %H:%M %Z")
    if is_open:
        return CheckResult("Market hours", Status.PASS, f"session OPEN now ({when})")
    return CheckResult(
        "Market hours",
        Status.WARN,
        f"session CLOSED now ({when}) — no live ticks until the next session",
    )


def run_preflight(
    cfg: Config,
    *,
    data: MarketDataClient | None = None,
    store: TradeStore | None = None,
    notifier: TelegramNotifier | None = None,
    now_utc: datetime | None = None,
) -> list[CheckResult]:
    """Run all checks and return their results.

    Dependencies are injectable for tests; when omitted they are built from
    ``cfg`` (the production path).
    """
    if data is None:
        data = MarketDataClient(cfg)
    if store is None:
        store = open_store(cfg)
    if notifier is None:
        notifier = open_notifier(cfg)
    if now_utc is None:
        now_utc = datetime.now(UTC)

    results = [
        check_alpaca(data),
        check_database(cfg, store),
        check_telegram(notifier),
        check_market_hours(cfg, now_utc),
    ]
    if store is not None:
        store.close()
    return results


def _format(results: list[CheckResult]) -> str:
    width = max(len(r.name) for r in results)
    lines = ["", "USTradeBot preflight check", "=" * 40]
    for r in results:
        lines.append(f"[{r.status.value:4}] {r.name.ljust(width)}  {r.detail}")
    failed = [r for r in results if r.status is Status.FAIL]
    warned = [r for r in results if r.status is Status.WARN]
    lines.append("=" * 40)
    if failed:
        lines.append(
            f"RESULT: FAIL — {len(failed)} critical check(s) failed; do not start the bot."
        )
    elif warned:
        lines.append(
            f"RESULT: OK with {len(warned)} warning(s) — side-channels off, trading path is ready."
        )
    else:
        lines.append("RESULT: OK — all systems go.")
    return "\n".join(lines)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s | %(message)s"
    )
    try:
        cfg = Config.load()
    except ConfigError as e:
        print(f"[FAIL] Configuration: {e}")
        return 1
    results = run_preflight(cfg)
    print(_format(results))
    # Exit non-zero only when a critical check failed — a WARN is acceptable.
    return 1 if any(r.status is Status.FAIL and r.critical for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
