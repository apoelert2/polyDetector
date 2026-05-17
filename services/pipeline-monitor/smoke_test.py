#!/usr/bin/env python3
"""Runtime Smoke-Test for polyDetector pipeline.

Prerequisites:
- All containers are running (podman compose up -d)
- RabbitMQ Management API is accessible on port 15672

Usage:
    python services/pipeline-monitor/smoke_test.py

Exit codes:
    0 – All checks passed
    1 – One or more checks failed
"""

import base64
import json
import sys
import time
import urllib.error
import urllib.request

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 15672
RABBITMQ_USER = "guest"
RABBITMQ_PASS = "guest"
QUEUE_NAME = "markets.raw"
TIMEOUT_SECONDS = 120
POLL_INTERVAL = 10


def _rabbitmq_request(path: str) -> dict:
    """Make authenticated GET request to RabbitMQ Management API."""
    url = f"http://{RABBITMQ_HOST}:{RABBITMQ_PORT}/api/{path}"
    credentials = f"{RABBITMQ_USER}:{RABBITMQ_PASS}"
    b64_credentials = base64.b64encode(credentials.encode()).decode()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {b64_credentials}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}")
        sys.exit(1)


def check_rabbitmq_reachable() -> bool:
    """Check if RabbitMQ Management API is reachable."""
    try:
        overview = _rabbitmq_request("overview")
        version = overview.get("rabbitmq_version", "unknown")
        print(f"[OK] RabbitMQ reachable (version {version})")
        return True
    except Exception as e:
        print(f"[FAIL] RabbitMQ unreachable: {e}")
        return False


def check_queue_exists(queue: str) -> bool:
    """Check if the queue exists."""
    try:
        queues = _rabbitmq_request("queues")
        queue_names = [q["name"] for q in queues]
        if queue in queue_names:
            print(f"[OK] Queue '{queue}' exists")
            return True
        else:
            print(f"[FAIL] Queue '{queue}' not found. Available queues: {queue_names}")
            return False
    except Exception as e:
        print(f"[FAIL] Cannot list queues: {e}")
        return False


def check_queue_has_messages(queue: str) -> bool:
    """Poll queue until messages appear or timeout."""
    print(f"Waiting for messages in '{queue}' (timeout={TIMEOUT_SECONDS}s)...")
    start = time.time()
    while time.time() - start < TIMEOUT_SECONDS:
        try:
            info = _rabbitmq_request(f"queues/%2F/{queue}")
            ready = info.get("messages_ready", 0)
            total = info.get("messages", 0)
            if total > 0:
                print(f"[OK] Queue '{queue}' has {total} messages ({ready} ready)")
                return True
            else:
                print(f"  ... waiting (no messages yet, {int(time.time() - start)}s)")
        except Exception as e:
            print(f"  ... error querying queue: {e}")
        time.sleep(POLL_INTERVAL)
    print(f"[FAIL] Queue '{queue}' still empty after {TIMEOUT_SECONDS}s")
    return False


def main() -> int:
    print("=" * 50)
    print("polyDetector Runtime Smoke Test")
    print("=" * 50)

    checks = [
        ("RabbitMQ reachable", check_rabbitmq_reachable()),
        ("Queue 'markets.raw' exists", check_queue_exists(QUEUE_NAME)),
        ("Queue has messages", check_queue_has_messages(QUEUE_NAME)),
    ]

    print()
    all_ok = True
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("[RESULT] All smoke tests passed.")
        return 0
    else:
        print("[RESULT] Some smoke tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
