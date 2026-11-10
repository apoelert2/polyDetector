# 9. Order-book changes as typed rows

Date: 2026-11-10 · Status: Accepted

## Context
The first version stored every WebSocket event as raw JSON in `ws_events`. A two-hour local recording
(about 700 tokens, 24 h window) showed:

- 99.7 % of all events are `price_change` (order-book updates). Real trades (`last_trade_price`) are
  about 0.1 %, and trades with wallets come from the Data API anyway.
- One event is about 660 bytes of JSON. That is about 21 GB per day raw and, with compression
  (measured ratio 6.4 on a 30-minute sample), about 3.3 GB per day, or more than 100 GB per month.

## Decision
`price_change` events are split into one row per changed asset in `price_changes`, with typed columns
(`price`, `size`, `side`, `best_bid`, `best_ask`) instead of JSON. The split happens in the DB writer
thread, not on the WebSocket thread, so detection latency is unchanged. The table is compressed per
asset after one day (`segmentby asset_id`).

Everything else stays raw in `ws_events`: order-book snapshots (`book`), trades and tick size changes.
A `price_change` that cannot be split (missing field, number that does not parse) is stored raw in
`ws_events` instead of being dropped. The order hash is not kept.

The writer also treats constraint violations (SQL state class 23) like data errors: it drops that batch
and logs it, instead of retrying it forever and blocking the queue.

## Consequences
- Much smaller data, and queries like "best bid of an asset over time" need no JSON parsing.
- Full order-book depth over time can no longer be rebuilt from the changes alone. Each `book`
  snapshot still gives a starting point, and every change carries the resulting best bid and ask.
- Two tables to read for "everything that happened": `price_changes` and `ws_events`.
- The health checks look at `price_changes` (always flowing), not at `ws_events` (trades can be sparse
  at night).
