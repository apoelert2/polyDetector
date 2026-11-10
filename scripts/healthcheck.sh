#!/usr/bin/env bash
# Dead man's switch, run by cron every 15 min. Reports to HEALTHCHECK_URL (e.g. healthchecks.io):
# success -> GET $HEALTHCHECK_URL, failure -> GET $HEALTHCHECK_URL/fail. If the server is down,
# the pings stop and the external service alerts. Without HEALTHCHECK_URL it only prints and exits.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="${COMPOSE:-podman compose}"
URL="${HEALTHCHECK_URL:-$(grep -E '^HEALTHCHECK_URL=' .env 2>/dev/null | cut -d= -f2- || true)}"

query() {
  $COMPOSE exec -T timescaledb sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$0"' "$1"
}

failures=()
check() {  # name, sql returning a count
  local n
  n="$(query "$2" 2>/dev/null || echo 0)"
  ((n > 0)) || failures+=("$1")
}
check "market snapshots (15 min)" "SELECT count(*) FROM market_snapshots WHERE time > now() - interval '15 minutes'"
check "websocket events (15 min)" "SELECT count(*) FROM ws_events WHERE received_at > now() - interval '15 minutes'"
# Trades can be quiet at night; one hour is a safer window.
check "trades (1 h)" "SELECT count(*) FROM trades WHERE time > now() - interval '1 hour'"

if ((${#failures[@]})); then
  msg="no new data: ${failures[*]}"
  echo "[FAIL] $msg"
  [[ -n "$URL" ]] && curl -fsS -m 10 --retry 3 --data-raw "$msg" "$URL/fail" >/dev/null
  exit 1
fi
echo "[OK] data is arriving"
[[ -n "$URL" ]] && curl -fsS -m 10 --retry 3 "$URL" >/dev/null
exit 0
