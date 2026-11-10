# Architecture Decision Records

Short records of decisions that shape this repo: what was decided, why, and what it costs.
Format: [Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
A decision is never edited after it is accepted; a new ADR supersedes it.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-services-write-directly-to-timescaledb.md) | Services write directly to TimescaleDB (no broker, no extractor) | Accepted |
| [0003](0003-java-hot-path-with-in-process-spike-detection.md) | Java WebSocket hot path with in-process spike detection | Accepted |
| [0004](0004-wallet-trades-from-data-api-v2.md) | Wallet-level trades from the Data API v2 | Accepted |
| [0005](0005-watch-only-markets-closing-soon.md) | Watch only markets of chosen tags that close soon | Accepted |
| [0006](0006-secrets-only-in-environment.md) | Secrets only in the environment, enforced by tests | Accepted |
| [0007](0007-paper-trading-only.md) | Paper trading only | Accepted |
