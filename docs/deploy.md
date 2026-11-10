# Deploying to a VPS

How a merge to `main` reaches the server, and the one-time setup. Written for a Hetzner Cloud server
with Ubuntu 24.04, but any Linux VPS with Docker works.

```
merge to main ─→ GitHub Actions: checks ─→ images to ghcr.io ─→ ssh deploy@server <sha>
                                                                      │ forced command
                                                                      ▼
                                       scripts/deploy.sh: git checkout <sha>, compose pull + up --wait
```

The deploy key can only run `scripts/deploy.sh` with a commit that is on `main`
([ADR 8](adr/0008-pull-based-deploy-with-forced-command-key.md)).

## 1. Server

1. Create the server (2 GB+ RAM, 80 GB+ disk, see the sizing note below) with **your own SSH key**.
   Disable password login.
2. Cloud firewall: allow inbound **TCP 22 only**. The DB is bound to `127.0.0.1` anyway.
3. As root, install Docker from the [official guide](https://docs.docker.com/engine/install/ubuntu/), then:

```bash
apt install -y git unattended-upgrades
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
```

> Note: membership in the `docker` group is equivalent to root on that machine. The forced command
> in step 2 is what keeps the CI key from using it. If that is not enough, switch to rootless Docker.

4. As `deploy`:

```bash
git clone https://github.com/<owner>/polyDetector.git ~/polydetector
cd ~/polydetector
cp .env.example .env && chmod 600 .env   # set a NEW TIMESCALE_PASS (openssl rand -hex 24) and GHCR_OWNER
```

## 2. Deploy key (CI → server)

On your own machine, create a key that is used **only** by GitHub Actions:

```bash
ssh-keygen -t ed25519 -N "" -C "polydetector-ci" -f polydetector_ci
```

On the server, append the **public** key to `/home/deploy/.ssh/authorized_keys`, restricted to the deploy script:

```
command="/home/deploy/polydetector/scripts/deploy.sh",restrict ssh-ed25519 AAAA... polydetector-ci
```

## 3. GitHub settings

**Settings → Secrets and variables → Actions**

| Kind | Name | Value |
|------|------|-------|
| Secret | `DEPLOY_HOST` | server address |
| Secret | `DEPLOY_USER` | `deploy` |
| Secret | `DEPLOY_SSH_KEY` | content of the **private** key `polydetector_ci` |
| Secret | `DEPLOY_KNOWN_HOSTS` | output of `ssh-keyscan -t ed25519 <server address>`, compared with the fingerprint in the Hetzner console |
| Variable | `DEPLOY_ENABLED` | `true` (only once everything above is set) |

Then delete the private key file from your machine. It now lives only in GitHub.

**Packages:** after the first run on `main`, open both packages (`polydetector-poller`,
`polydetector-ws-subscriber`) under your GitHub profile → Packages → Package settings and set
visibility to **public**. Otherwise the server cannot pull them without a login.

**Protect main:** Settings → Rules → Rulesets → New branch ruleset → target `main`:
"Require a pull request before merging" and "Require status checks to pass" with
`secret-scan`, `poller` and `ws-subscriber`. Checks can only be selected after they ran once.

## 4. Backups and alarm (cron, as `deploy`)

```bash
crontab -e
```

```
COMPOSE="docker compose -f docker-compose.yaml"
*/15 * * * * cd ~/polydetector && scripts/healthcheck.sh >/dev/null 2>&1
30 3 * * *   cd ~/polydetector && scripts/backup.sh ~/backups >> ~/backup.log 2>&1
```

- **Alarm:** create a free check at [healthchecks.io](https://healthchecks.io) (period 15 min, grace
  15 min) and put its ping URL into `.env` as `HEALTHCHECK_URL`. It alerts by mail when data stops
  arriving *or* when the server is down, because the pings stop.
- **Backups** on the same server do not survive losing the server. Copy them off it: the Hetzner backup
  option (whole server), a storage bucket, or simply fetch them to your machine:
  `scp deploy@<server>:backups/*.dump .`
- `pg_dump` prints warnings about circular foreign keys in TimescaleDB's catalog. They are harmless.

### Restore a dump

```bash
# into a new database "restored" on a running stack
compose exec -T timescaledb sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE restored"'
compose exec -T timescaledb sh -c 'psql -U "$POSTGRES_USER" -d restored -c "CREATE EXTENSION timescaledb; SELECT timescaledb_pre_restore();"'
compose exec -T timescaledb sh -c 'pg_restore -U "$POSTGRES_USER" -d restored --no-owner' < polydetector-<date>.dump
compose exec -T timescaledb sh -c 'psql -U "$POSTGRES_USER" -d restored -c "SELECT timescaledb_post_restore();"'
```

## Sizing

Measured locally (2026-11-10, ~700 tokens, 24 h window): about 370 MB RAM for all services and
roughly 16 GB/day of raw WebSocket events before compression (compression after 1 day). Measure the
compressed size for a day before choosing the disk: `SELECT pg_size_pretty(hypertable_size('ws_events'));`
