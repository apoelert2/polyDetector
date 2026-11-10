#!/usr/bin/env bash
set -euo pipefail

# Testcontainers talks to rootless podman through its socket (enable once: systemctl --user enable --now podman.socket).
export DOCKER_HOST="${DOCKER_HOST:-unix://${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
export TESTCONTAINERS_RYUK_DISABLED="${TESTCONTAINERS_RYUK_DISABLED:-true}"

echo "=== checkstyle ==="
mvn -B checkstyle:check
echo "=== spotbugs ==="
mvn -B compile spotbugs:check
echo "=== tests + jacoco ==="
mvn -B verify -Dcheckstyle.skip=true -Dspotbugs.skip=true
echo "=== ALL CHECKS PASSED ==="
