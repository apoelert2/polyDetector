#!/usr/bin/env bash
# Daily DB dump (cron). Also the way to take the data home for analysis.
# Usage: scripts/backup.sh [target_dir]   (keeps the last BACKUP_KEEP dumps, default 1)
# Dumps live on the same disk as the DB: copy them off the server, then delete them (docs/deploy.md).
# Restore: see docs/deploy.md.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="${COMPOSE:-podman compose}"
DIR="${1:-backups}"
KEEP="${BACKUP_KEEP:-1}"
mkdir -p "$DIR"
file="$DIR/polydetector-$(date -u +%Y%m%dT%H%M%SZ).dump"

# A full disk stops the DB and with it the data collection: only dump if the DB size fits twice over.
db_bytes="$($COMPOSE exec -T timescaledb sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT pg_database_size(current_database())"' | tr -dc '0-9')"
free_bytes="$(df --output=avail -B1 "$DIR" | tail -1 | tr -dc '0-9')"
if ((free_bytes < 2 * db_bytes)); then
  echo "backup skipped: $((free_bytes >> 20)) MiB free, need $((2 * db_bytes >> 20)) MiB (2x DB size)" >&2
  exit 1
fi

# -Fc: compressed custom format for pg_restore. Written to .part first so a failed dump never looks complete.
trap 'rm -f "$file.part"' EXIT
$COMPOSE exec -T timescaledb sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$file.part"
mv "$file.part" "$file"
echo "backup: $file ($(du -h "$file" | cut -f1))"

ls -1t "$DIR"/polydetector-*.dump | tail -n +"$((KEEP + 1))" | xargs -r rm --
