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
