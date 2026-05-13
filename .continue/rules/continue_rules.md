# ~/.continue/rules/continue_rules.md

# polyDetector – Global Rules

## Vision
**polyDetector** soll eine vollständig eigenständige, containerisierte Datenpipeline werden, die auf beliebigen Hosting-Plattformen (Hetzner Cloud, AWS EC2, beliebige VPS) deployed werden kann.

**Leitprinzipien:**
- Jeder Microservice ist unabhängig containerisierbar und läuft in podman-compose sowie Kubernetes-fähig.
- Schrittweise Entwicklung: Starte mit einem Service, teste ihn isoliert, füge den nächsten hinzu. So werden Fehler früh erkannt und die Komplexität kontrolliert.
- Integrations-Tests nach jedem neuen Service oder Queue-Flow-Änderung.
- Die Pipeline muss nach `docker compose up -d` ohne manuelles Eingreifen laufen.
- Persistenz und Wiederanlauf: Alle Services verkraften Broker-/DB-Ausfälle und verbinden sich selbstständig neu.
- Dokumentiere das Projekt in der README.md im Projetkordner. Halte die Dokumentation stets aktuell, jedoch nur wenn ein Feature erfolgreich integriert wurde.

## Tech Stack & Language
- All infrastructure is defined in `docker-compose.yaml`.
- **Python 3**: Used for `poller`, `extractor`, `pipeline-monitor`. Use `asyncio` where beneficial, but simple synchronous scripts with `pika` are acceptable.
- **Java 17+**: Used for `ws-subscriber` and `storage`. Build with Gradle (preferred) or Maven, using shadow/fat JARs. Use `HikariCP` for JDBC connection pooling.
- **RabbitMQ**: Message broker, accessed via `pika` (Python) and `amqp-client` (Java).
- **TimescaleDB (PostgreSQL 16)**: Time-series storage, accessed via `psycopg2` (Python) and `JDBC` (Java). Always create hypertables after table creation.

## Code Conventions
- **Configuration by environment variables** with sensible defaults. Never hardcode hosts, ports, or credentials.
- Python: Use `python-dotenv` to load `.env`, but allow env vars to override. Logging with `logging` module, structured as JSON lines.
- Java: Use `SLF4J` + `Logback`, no `System.out.println`. Use `Properties` or environment for config.
- All services must have **health checks** or at least log startup and periodic heartbeats.
- **Error handling**: Transient errors (network, RabbitMQ reconnect) are retried with exponential backoff; fatal errors cause exit with non-zero code so Docker can restart.
- **Message format**: JSON. Fields must be snake_case. Use `_source` metadata field in all published messages.

## Project Structure
polyDetector/
├── docker-compose.yaml
├── .env.example
├── data/
│ └── tag_ids.json
├── services/
│ ├── poller/
│ │ └── main.py
│ ├── extractor/
│ │ └── main.py
│ ├── ws-subscriber/ # Java project
│ ├── storage/ # Java project
│ └── pipeline-monitor/
│ └── main.py
└── lib/ # Shared helpers if needed


## Testing
- Every service must have at least a basic integration test (can be a `docker-compose.test.yaml` with testcontainers or script).
- Mock external APIs (Polymarket Gamma) using `responses` or WireMock.
- RabbitMQ interactions are tested with a test queue on a local broker.

## Safety
- Never commit secrets. Use `.env` for local development, vault/references in CI.
- All SQL queries use parameterized statements (no string concatenation).

## Token Efficiency Rule
- Provide concise answers. Do NOT add explanations unless asked.
- Prefer code solutions over verbal descriptions.
- Always use the active programming language.
- Focus on solving the precise task.
- If three consecutive fix attempts fail, STOP. Propose: (a) revert, (b) what we know vs don't know, (c) a different approach.