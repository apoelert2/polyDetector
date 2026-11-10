# 5. Watch only markets of chosen tags that close soon

Date: 2026-11-10 · Status: Accepted

## Context
Polymarket has thousands of open markets. Insider trading is most likely shortly before resolution:
a market that closes in three months is a weaker target than one closing tomorrow. Watching everything
costs bandwidth, storage and WebSocket subscriptions.

## Decision
Watch markets that (a) carry one of the tags in `tag_ids.json` and (b) close within
`CLOSING_WINDOW_HOURS` (default 24), or whose `endDate` passed less than `CLOSING_GRACE_HOURS`
(default 6) ago: trading often goes on until resolution, and the last minutes are the most interesting.
The poller filters through Gamma's `end_date_min/max`. The ws-subscriber and the trade polling read the
same set from the `markets` table.

## Consequences
- Roughly 350 markets / 700 tokens at the default settings (measured 2026-11-10).
- Markets with a long run-up are only observed in their last day. A wider window is one env variable.
- The tag list is data, not code: edit `tag_ids.json`, no rebuild needed.
