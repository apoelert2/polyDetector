# polyDetector

A data pipeline that watches Polymarket prediction markets shortly before they close, to find
patterns that suggest insider trading: unusual volume spikes and the wallets behind them.

The first phase collects about a month of data on a VPS. That data is used to design and backtest
detection strategies, and later to test them live as signals only. No real money is traded
([ADR 7](docs/adr/0007-paper-trading-only.md)). Comparing other prediction markets (Kalshi first) is
planned.

## Architecture

```
            ┌──────────────── ws-subscriber (Java 25, one process) ────────────────┐
Polymarket ─┤ WebSocket client → SpikeDetector (in memory) → log + spikes table    │
 market WS  │          └──────→ batch writer (own thread, never blocks) ───────────┼──→ TimescaleDB
            └───────────────────────────────────────────────────────────────────────┘        ▲
Gamma API ───→ poller (Python 3.12, every 60 s): markets + price snapshots ──────────────────┤
Data API v2 ─→           …and trades with wallet + transaction hash ────────────────────────┘
```

- **Watch list:** markets with a tag from [`tag_ids.json`](tag_ids.json) that close within 24 h
  ([ADR 5](docs/adr/0005-watch-only-markets-closing-soon.md)).
- **Hot path:** spikes are detected in the WebSocket process before anything is stored
  ([ADR 3](docs/adr/0003-java-hot-path-with-in-process-spike-detection.md)).
- **Who traded:** wallet-level trades from the Data API, joinable to live events via `transaction_hash`
  ([ADR 4](docs/adr/0004-wallet-trades-from-data-api-v2.md)).
- **No broker:** services share one DB schema, [`db/init/001_schema.sql`](db/init/001_schema.sql)
  ([ADR 2](docs/adr/0002-services-write-directly-to-timescaledb.md)).

Each service follows Clean Architecture: entities → use cases with ports → adapters → composition root.

| Table | Written by | Content |
|-------|-----------|---------|
| `markets` | poller | current state per market, incl. token ids |
| `market_snapshots` | poller | prices, volume, liquidity per poll |
| `trades` | poller | trades with proxy wallet and tx hash |
| `ws_events` | ws-subscriber | every WebSocket event, raw JSON (compressed after 1 day) |
| `spikes` | ws-subscriber | detected volume spikes |

## Quick start

```bash
cp .env.example .env              # set TIMESCALE_PASS and GHCR_OWNER
podman compose up -d --build      # builds locally via docker-compose.override.yaml; docker compose works too
scripts/smoke_test.sh             # waits until real data is in every table
```

Settings (watch window, spike thresholds, …) are listed in [`.env.example`](.env.example).
The DB listens on `127.0.0.1:5432` only. On a server, use an SSH tunnel.

## Development

Requirements: Podman (rootless, `podman.socket` enabled for Testcontainers), Python 3.12+, Java 25, Maven.

```bash
bash services/poller/lint.sh          # ruff, mypy --strict, bandit, pytest
bash services/ws-subscriber/lint.sh   # checkstyle, spotbugs, tests incl. TimescaleDB integration, jacoco
python -m pytest                      # repo-wide secret scan (no passwords, keys, IPs in tracked files)
```

```
polyDetector/
├── db/init/              # DB schema, applied on first start
├── docs/adr/             # architecture decision records
├── scripts/smoke_test.sh # end-to-end check against the running stack
├── services/
│   ├── poller/           # Python: Gamma markets + Data API trades
│   └── ws-subscriber/    # Java: WebSocket, spike detection
├── tests/                # repo-wide checks
└── tag_ids.json          # tags to watch
```

## License

See [LICENSE](LICENSE).
