#!/usr/bin/env bash
# Runs on the server. The CI deploy key may only run this script (forced command in authorized_keys),
# passing the commit to release. Usage: deploy.sh <40-char commit sha on main>
set -euo pipefail

main() {
  local sha="${SSH_ORIGINAL_COMMAND:-${1:-}}"
  if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
    echo "usage: deploy.sh <commit sha>" >&2
    exit 2
  fi
  cd "$(dirname "$0")/.."
  git fetch --quiet origin main
  if ! git merge-base --is-ancestor "$sha" origin/main; then
    echo "refusing: $sha is not on main" >&2
    exit 3
  fi
  git checkout --quiet --detach "$sha"
  # -f: ignore docker-compose.override.yaml, which builds from source (dev machines only).
  IMAGE_TAG="$sha" docker compose -f docker-compose.yaml pull --quiet
  IMAGE_TAG="$sha" docker compose -f docker-compose.yaml up -d --remove-orphans --wait --wait-timeout 180
  docker image prune -f >/dev/null
  echo "deployed $sha"
}

# Whole script is parsed before it runs: git checkout above may replace this file.
main "$@"
exit
