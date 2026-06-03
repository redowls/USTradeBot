"""Manual kill switch — flatten everything (Phase 10).

The emergency "get me flat" procedure: cancel **all** open orders and liquidate
**all** open positions on the Alpaca paper account in one shot, then alert via
Telegram. Use it when the strategy is misbehaving or before maintenance.

    python -m bot.flatten --yes        # the --yes guard prevents an accidental run

This only touches the broker. To also stop the bot so it can't re-enter, run the
operator wrapper ``deploy/kill-switch.sh`` (it stops the systemd service first).

``flatten_all`` takes the trading client + notifier directly so it unit-tests with
fakes, mirroring the rest of the codebase. It is deliberately robust: a failure
reading positions or closing them is logged and still alerted — the whole point is
to fire under adverse conditions.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field

from alpaca.trading.client import TradingClient

from bot.config import Config, ConfigError
from bot.notifier import TelegramNotifier, open_notifier

log = logging.getLogger("ustradebot.flatten")


@dataclass(frozen=True)
class FlattenResult:
    symbols: list[str] = field(default_factory=list)  # positions seen before flattening
    ok: bool = True  # False if the close call raised

    @property
    def count(self) -> int:
        return len(self.symbols)


def format_flatten(result: FlattenResult) -> str:
    head = "🛑 KILL SWITCH — flatten-all"
    if not result.ok:
        return f"{head}\nclose_all_positions raised — VERIFY MANUALLY at Alpaca."
    if result.count == 0:
        return f"{head}\nno open positions; cancelled any open orders."
    names = ", ".join(result.symbols)
    return f"{head}\nclosed {result.count} position(s): {names}\n(open orders cancelled)"


def flatten_all(
    client: TradingClient, *, notifier: TelegramNotifier | None = None
) -> FlattenResult:
    """Cancel all open orders and close all positions. Always alerts; never raises."""
    try:
        symbols = [p.symbol for p in client.get_all_positions()]
    except Exception:
        log.exception("could not read positions before flattening")
        symbols = []
    ok = True
    try:
        # cancel_orders=True cancels resting brackets/orders and liquidates holdings.
        client.close_all_positions(cancel_orders=True)
    except Exception:
        log.exception("close_all_positions failed")
        ok = False
    result = FlattenResult(symbols=symbols, ok=ok)
    log.warning("FLATTEN: ok=%s positions=%s", ok, symbols)
    if notifier is not None:
        notifier.send(format_flatten(result))
    return result


def _build_client(cfg: Config) -> TradingClient:
    return TradingClient(
        cfg.alpaca_key_id, cfg.alpaca_secret, paper=True, url_override=cfg.alpaca_base_url
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--yes" not in args and "-y" not in args:
        print(
            "Refusing to run without --yes.\n"
            "This CANCELS ALL OPEN ORDERS and CLOSES ALL POSITIONS on the paper account.\n"
            "Re-run: python -m bot.flatten --yes"
        )
        return 2
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s | %(message)s"
    )
    try:
        cfg = Config.load()
    except ConfigError as e:
        print(f"config error: {e}")
        return 1
    result = flatten_all(_build_client(cfg), notifier=open_notifier(cfg))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
