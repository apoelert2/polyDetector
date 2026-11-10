#!/usr/bin/env bash
# End-to-end check against the running stack: real data must arrive in every table.
# Usage: podman compose up -d --build && scripts/smoke_test.sh [timeout_seconds]
# Credentials stay inside the DB container (psql uses its env); nothing secret is passed or printed.
set -euo pipefail

TIMEOUT="${1:-240}"
COMPOSE="${COMPOSE:-podman compose}"

query() {
  # Digits only: podman compose may prefix "\e[0m". Callers compare with 10# (no octal from a leading 0).
  $COMPOSE exec -T timescaledb sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$0"' "$1" | tr -dc '0-9'
}

check() {  # name, sql returning a count
  local deadline=$((SECONDS + TIMEOUT)) n
  while ((SECONDS < deadline)); do
    n="$(query "$2" 2>/dev/null || true)"
    if ((10#${n:-0} > 0)); then
      echo "[PASS] $1 ($n)"
      return 0
    fi
    sleep 10
  done
  echo "[FAIL] $1 (nothing after ${TIMEOUT}s)"
  return 1
}

status=0
check "markets closing in window, with token ids" \
  "SELECT count(*) FROM markets WHERE NOT closed AND end_date > now() AND cardinality(token_ids) > 0" || status=1
check "market snapshots with prices" \
  "SELECT count(*) FROM market_snapshots WHERE cardinality(outcome_prices) > 0" || status=1
check "trades with wallet" \
  "SELECT count(*) FROM trades WHERE proxy_wallet LIKE '0x%'" || status=1
check "websocket events" \
  "SELECT count(*) FROM ws_events WHERE received_at > now() - interval '10 minutes'" || status=1

for svc in poller ws-subscriber; do
  if $COMPOSE logs "$svc" 2>&1 | grep -qE "\[ERROR\]|\"level\":\"ERROR\"|Traceback"; then
    echo "[WARN] errors in $svc logs:"
    $COMPOSE logs --tail 20 "$svc" 2>&1 | grep -E "ERROR|Traceback" | tail -5
  fi
done

exit $status
