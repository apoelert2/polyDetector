# 3. Java WebSocket hot path with in-process spike detection

Date: 2026-11-10 · Status: Accepted

## Context
The goal is to see a volume spike as early as possible. Latency comes, in order of size, from:
1. the network to Polymarket (tens of ms),
2. every hop before detection (broker, DB, batch intervals: milliseconds to seconds),
3. the language (microseconds per message).

The old design put detection *behind* storage, so (2) dominated.

## Decision
- The ws-subscriber (Java 25) receives the market channel, runs `SpikeDetector` **in the same
  process, on the receiving thread**, and only then hands the event to the DB writer.
- The DB writer queues in memory and writes in batches on its own thread. If the queue fills (DB down
  for a long time), events are dropped and counted. The hot path never blocks.
- The detector uses event time, not the wall clock, so stored events can be replayed through the same
  code for backtests.
- Detection rule (configurable): notional of the last 5 min ≥ 1000 USDC and ≥ 5× the expected notional
  per 5 min from the preceding hour. One alert per window per asset. A full hour of observation per asset
  before the first alert, so a restart does not flag every asset.
- Python stays where latency does not matter: Gamma markets every 60 s, Data API trades.
- Reconnects run through exactly one code path, and the client sends the text `PING` every 10 s
  that Polymarket expects.

## Consequences
- Two languages and toolchains. Java is used where it pays off: many concurrent streams, no GIL,
  stable latency.
- After a restart the detector is blind for one history window (60 min). Warming it up from the DB is
  possible later.
- The subscription follows the `markets` table (refresh every 60 s). A market entering the window is
  picked up within a minute.
