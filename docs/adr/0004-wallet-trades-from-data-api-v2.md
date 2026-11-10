# 4. Wallet-level trades from the Data API v2

Date: 2026-11-10 · Status: Accepted

## Context
Insider detection needs *who* bought *when*, *how much* and at *what price*. The WebSocket market
channel has no wallet addresses. Options:

| | Data API v2 (`/v2/trades`) | On-chain (Polygon `OrderFilled`) |
|---|---|---|
| Effort | HTTP polling | RPC/subgraph, ABI decoding, token→market mapping |
| Wallet | proxy wallet | maker and taker |
| Completeness | as published by Polymarket; may change (v1 was retired) | complete and tamper-proof |
| History | fine for ongoing collection | unlimited, also for backfills |

## Decision
Use the Data API v2 for the data-collection month. Poll trades for watched markets in batches of 20
condition ids (the API maximum), newest first, until the last seen trade per market. Store
`transaction_hash` with every trade.

## Consequences
- `transaction_hash` also appears in WebSocket `last_trade_price` events, so a live spike can be joined
  to the wallets behind it.
- Each trade can later be verified on-chain, and an on-chain ingester can be added without schema changes.
- Risk: the API changes again. Parsing is tested against saved real responses (`tests/fixtures`).
