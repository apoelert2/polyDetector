# polyDetector

A containerized data pipeline for Polymarket prediction markets. Long-term goal: detect insider trading by correlating on-chain activity with market movements.

---

## Architecture

```
Poller ──→ Queue "markets.raw" ──→ Extractor ──→ Queue "markets.enriched" ──→ Storage ──→ TimescaleDB

WS-Subscriber ──→ Queue "ws_raw" ────────────────────────────────────────────────→ Storage ──→ TimescaleDB
```

Every service follows **Clean Architecture** (Entities → Use Cases → Adapters → Composition Root) and is independently containerizable.

### Services

| Service | Language | Task |
|---------|----------|------|
| **Poller** | Python 3.12 | Fetches Polymarket Gamma API, publishes raw data to `markets.raw` |
| **Extractor** | Python 3.12 | Consumes `markets.raw`, enriches with volume/liquidity/spread, publishes to `markets.enriched` |
| **WS-Subscriber** | Java 25+ | WebSocket client for real-time data |
| **Storage** | Java 25+ | Persists data to TimescaleDB |
| **Pipeline-Monitor** | Python 3.12 | Monitors health and throughput |

### Infrastructure

| Component | Version | Purpose |
|-----------|---------|---------|
| RabbitMQ | 3.13-management | Message broker |
| TimescaleDB | latest-pg16 | Time-series database |
| Podman | rootless | Container orchestration |

---

## Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd polyDetector

# 2. Create .env (optional)
cp .env.example .env

# 3. Start all services
podman compose up -d --build

# 4. Check logs
podman compose logs -f

# 5. Run smoke tests
python services/pipeline-monitor/smoke_test.py  # Poller pipeline
python services/extractor/smoke_test.py          # Extractor pipeline (raw → enriched)
```

### Individual Services

```bash
# Start only the poller
podman compose up -d --build poller

# Poller logs only
podman compose logs -f poller
```

---

## Development

### Prerequisites

- Podman (rootless)
- Python 3.12+
- Java 25+ (for WS-Subscriber and Storage)
- Gradle or Maven (for Java services)

### Linting & Tests

Every service has its own `lint.sh`:

```bash
bash services/poller/lint.sh
```

Includes: Ruff, MyPy, Bandit, Pytest (Python) / Checkstyle, SpotBugs, JaCoCo (Java).

### Project Structure

```
polyDetector/
├── docker-compose.yaml       # Service definitions
├── .env.example              # Environment variables (template)
├── pyproject.toml            # Python tool configuration
├── tag_ids.json              # Polymarket tag IDs
├── PLAN.md                   # Project plan & roadmap
├── README.md                 # This file
└── services/
    ├── poller/               # Phase 1
    ├── extractor/            # Phase 2
    ├── ws-subscriber/        # Phase 3
    ├── storage/              # Phase 4
    └── pipeline-monitor/     # Phase 5
```

---

## Project Plan

The full plan with phases, milestones, and architecture decisions is in **[PLAN.md](PLAN.md)**.

---

## License

See [LICENSE](LICENSE).
