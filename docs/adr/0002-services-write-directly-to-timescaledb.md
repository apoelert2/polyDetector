# 2. Services write directly to TimescaleDB (no broker, no extractor)

Date: 2026-11-10 · Status: Accepted

## Context
The first design had five services and RabbitMQ: Poller → `markets.raw` → Extractor →
`markets.enriched` → Storage → TimescaleDB, plus a WebSocket subscriber → `ws_raw` → Storage.
The load is about 10 messages per second on one machine. The extractor only renamed fields, and every
queue boundary duplicated the message schema in Python and Java. Two schema bugs came exactly from
there: `condition_id` vs. the API's `conditionId`, and `tag_id` vs. `tag_ids`. The result: no real market
reached the end of the pipeline. Also, `markets.enriched` had no consumer and would have filled the
broker within days.

## Decision
Each ingester writes straight to TimescaleDB: the Python poller (markets, snapshots, trades) and the
Java ws-subscriber (raw events, spikes). RabbitMQ, the extractor and the storage service are removed.
The DB schema (`db/init/001_schema.sql`) is the single contract between services.

## Consequences
- Fewer moving parts to fail during a month of unattended data collection on a VPS.
- One schema, tested against real TimescaleDB in the Java integration tests.
- No fan-out to future consumers. If that becomes necessary (e.g. live paper-trading signals in a
  separate process), Postgres `LISTEN/NOTIFY` or a broker can be added for *that* path only.
- Schema changes after the first deploy need a manual migration (no migration tool yet).
