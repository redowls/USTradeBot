"""Telegram alerts (Phase 7).

Pushes a short message to a Telegram chat on each entry, exit, and feed/error
event — a **direct** ``POST`` to the Bot API's ``sendMessage`` (no n8n, no extra
SDK). Two pieces, mirroring the persistence layer (Phase 6):

- :class:`TelegramNotifier` — the transport. Owns the bot token + chat id and
  posts JSON to ``https://api.telegram.org/bot<TOKEN>/sendMessage``. The HTTP
  ``poster`` is injectable (default: a stdlib ``urllib`` implementation) so tests
  run without a network and we add no new runtime dependency. Every send is
  wrapped to log + swallow — **alerts are a side-channel, never the trading
  critical path** (just like the DB writes).
- :class:`AlertReporter` — the glue that subscribes to the existing executor /
  risk callbacks. ``on_result`` fires the entry alert (size + confidence),
  ``on_exit`` fires the exit alert (reason + realized P/L, computed from the
  cached entry), and ``on_feed_alert`` forwards the feed-loss/restore message.

The post is synchronous on the candle thread (like the SQL writes), so it uses a
short timeout; a hung Telegram endpoint can't stall the strategy for long.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bot.config import Config
    from bot.executor import ExecutionResult
    from bot.risk import ExitResult

log = logging.getLogger("ustradebot.notifier")

# A poster sends one message: (url, json_payload, timeout) -> None, raising on
# any failure. Kept abstract so the notifier never hard-depends on a HTTP client
# and tests can capture the calls.
Poster = Callable[[str, dict[str, Any], float], None]

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _urllib_post(url: str, payload: dict[str, Any], timeout: float) -> None:
    """Default transport: POST JSON via the standard library, raising on non-200."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https URL)
        status = getattr(resp, "status", None) or resp.getcode()
        if status != 200:
            raise RuntimeError(f"Telegram sendMessage returned HTTP {status}")


class TelegramNotifier:
    """Sends plain-text messages to one Telegram chat via the Bot API."""

    def __init__(
        self,
        token: str,
        chat_id: str,
        *,
        poster: Poster | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._chat_id = chat_id
        self._poster = poster or _urllib_post
        self._timeout = timeout
        # The token is a secret — it lives only in the URL, never in a log line.
        self._url = _API.format(token=token)

    def send(self, text: str) -> bool:
        """Post one message. Returns success; never raises into the caller."""
        payload = {"chat_id": self._chat_id, "text": text}
        try:
            self._poster(self._url, payload, self._timeout)
            return True
        except Exception:  # a flaky alert endpoint must not kill the trading path
            log.exception("Telegram sendMessage failed")
            return False


# --- message formatting (pure) ---------------------------------------------


def format_entry(result: ExecutionResult) -> str:
    """Entry alert: size + bracket levels + confidence."""
    return (
        f"\U0001f7e2 ENTRY {result.symbol}\n"
        f"{result.qty} sh @ ${result.entry_price:.2f}  (${result.notional:,.2f})\n"
        f"stop ${result.stop_price:.2f} / target ${result.take_profit_price:.2f}\n"
        f"confidence {result.confidence:.1f}%  ·  model {result.model}  ·  {result.status}"
    )


def format_exit(result: ExitResult, entry: ExecutionResult | None) -> str:
    """Exit alert: reason + realized P/L when the original entry is known."""
    lines = [
        f"\U0001f534 EXIT {result.symbol}",
        f"@ ${result.exit_price:.2f} — {result.reason}",
    ]
    if entry is not None and entry.entry_price > 0:
        pnl = (result.exit_price - entry.entry_price) * entry.qty
        pct = (result.exit_price / entry.entry_price - 1) * 100
        sign = "+" if pnl >= 0 else "−"  # explicit minus for readability
        mag = abs(pnl)
        lines.append(f"{entry.qty} sh · P/L {sign}${mag:,.2f} ({sign}{abs(pct):.2f}%)")
    return "\n".join(lines)


class AlertReporter:
    """Wires :class:`TelegramNotifier` onto the executor/risk callbacks.

    Pass its methods as (one of) the executor's ``on_result``, the risk manager's
    ``on_exit`` and ``on_feed_alert``. It caches the entry per symbol so the exit
    alert can report realized P/L (the round-trip price is only known here, off the
    reversal candle — the same basis persistence uses).
    """

    def __init__(self, notifier: TelegramNotifier) -> None:
        self._notifier = notifier
        self._entries: dict[str, ExecutionResult] = {}

    def on_result(self, result: ExecutionResult) -> None:
        self._entries[result.symbol] = result
        self._notifier.send(format_entry(result))

    def on_exit(self, result: ExitResult) -> None:
        entry = self._entries.pop(result.symbol, None)
        self._notifier.send(format_exit(result, entry))

    def on_feed_alert(self, message: str) -> None:
        # Feed alerts arrive already formatted (with their own emoji) from the risk
        # manager; forward verbatim.
        self._notifier.send(message)


def open_notifier(cfg: Config, *, poster: Poster | None = None) -> TelegramNotifier | None:
    """Build a notifier from config, or ``None`` when Telegram isn't configured.

    Returns ``None`` if the token or chat id is unset so the bot still trades with
    alerts disabled (a side-channel, like persistence). Config currently *requires*
    both, so this normally returns a live notifier.
    """
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        log.info("TELEGRAM_TOKEN/TELEGRAM_CHAT_ID not set — alerts disabled")
        return None
    return TelegramNotifier(cfg.telegram_token, cfg.telegram_chat_id, poster=poster)
