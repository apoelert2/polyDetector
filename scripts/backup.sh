#!/usr/bin/env bash
# Daily DB dump (cron). Also the way to take the data home for analysis.
# Usage: scripts/backup.sh [target_dir]   (keeps the last BACKUP_KEEP dumps, default 3)
# Restore: see docs/deploy.md.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="${COMPOSE:-podman compose}"
DIR="${1:-backups}"
KEEP="${BACKUP_KEEP:-3}"
mkdir -p "$DIR"
file="$DIR/polydetector-$(date -u +%Y%m%dT%H%M%SZ).dump"

# -Fc: compressed custom format for pg_restore. Written to .part first so a failed dump never looks complete.
$COMPOSE exec -T timescaledb sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$file.part"
mv "$file.part" "$file"
echo "backup: $file ($(du -h "$file" | cut -f1))"

ls -1t "$DIR"/polydetector-*.dump | tail -n +"$((KEEP + 1))" | xargs -r rm --
