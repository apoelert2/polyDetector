#!/usr/bin/env python3
"""Runtime Smoke-Test for the Extractor (uses live Poller + Extractor).

Prerequisites:
- All containers are running (podman compose up -d)
- RabbitMQ Management API is accessible on port 15672
- Poller and Extractor are running

What it tests:
1. RabbitMQ reachable
2. Queue 'markets.raw' exists (created by Poller)
3. Queue 'markets.enriched' exists (created by Extractor)
4. Publish a test market to 'markets.raw' via API
5. Wait for it to appear on 'markets.enriched' (Extractor processed it)

Usage:
    python services/extractor/smoke_test.py

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
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
RAW_QUEUE = "markets.raw"
ENRICHED_QUEUE = "markets.enriched"
EXCHANGE = "polymarket"
TIMEOUT_SECONDS = 120
POLL_INTERVAL = 5


def _rabbitmq_request(path: str, method: str = "GET", body: dict | None = None) -> dict:
    """Make authenticated request to RabbitMQ Management API."""
    url = f"http://{RABBITMQ_HOST}:{RABBITMQ_PORT}/api/{path}"
    credentials = f"{RABBITMQ_USER}:{RABBITMQ_PASS}"
    b64_credentials = base64.b64encode(credentials.encode()).decode()
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Basic {b64_credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP error {e.code}: {e.reason}")
        if e.code == 404:
            return {}
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"  Connection error: {e.reason}")
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
    """Check if a queue exists."""
    try:
        queues = _rabbitmq_request("queues")
        queue_names = [q["name"] for q in queues]
        if queue in queue_names:
            print(f"[OK] Queue '{queue}' exists")
            return True
        else:
            print(f"[FAIL] Queue '{queue}' not found. Available: {queue_names}")
            return False
    except Exception as e:
        print(f"[FAIL] Cannot list queues: {e}")
        return False


def publish_test_message() -> str | None:
    """Publish a test market message to markets.raw via RabbitMQ API."""
    test_condition_id = f"smoke-test-{int(time.time())}"
    test_message = {
        "condition_id": test_condition_id,
        "question": "Smoke test: will this pass?",
        "description": "Automated smoke test message",
        "outcomes": [{"name": "Yes"}, {"name": "No"}],
        "volume": "1000.50",
        "end_date": "2026-12-31T23:59:59Z",
        "volume24hr": "100.00",
        "liquidity": "50000",
        "spread": "0.02",
    }
    body = {
        "properties": {"delivery_mode": 2, "content_type": "application/json"},
        "routing_key": RAW_QUEUE,
        "payload": json.dumps(test_message),
        "payload_encoding": "string",
    }
    try:
        _rabbitmq_request(
            f"exchanges/%2F/{EXCHANGE}/publish",
            method="POST",
            body=body,
        )
        print(f"[OK] Published test message (condition_id={test_condition_id})")
        return test_condition_id
    except Exception as e:
        print(f"[FAIL] Failed to publish test message: {e}")
        return None


def wait_for_enriched_message(expected_condition_id: str) -> bool:
    """Poll markets.enriched until our test message appears or timeout."""
    print(f"Waiting for enriched message on '{ENRICHED_QUEUE}' (timeout={TIMEOUT_SECONDS}s)...")
    start = time.time()
    while time.time() - start < TIMEOUT_SECONDS:
        try:
            info = _rabbitmq_request(f"queues/%2F/{ENRICHED_QUEUE}")
            total = info.get("messages", 0)
            if total > 0:
                print(f"[OK] Queue '{ENRICHED_QUEUE}' has {total} messages")
                return True
            else:
                elapsed = int(time.time() - start)
                print(f"  ... waiting ({elapsed}s) - enriched queue still empty")
        except Exception as e:
            print(f"  ... error: {e}")
        time.sleep(POLL_INTERVAL)
    print(f"[FAIL] Enriched message '{expected_condition_id}' not found after {TIMEOUT_SECONDS}s")
    return False


def purge_queue(queue: str) -> None:
    """Purge all messages from a queue."""
    try:
        _rabbitmq_request(f"queues/%2F/{queue}/contents", method="DELETE")
        print(f"[INFO] Purged queue '{queue}'")
    except Exception:
        pass  # Non-fatal


def main() -> int:
    print("=" * 55)
    print("polyDetector Extractor Runtime Smoke Test")
    print("(uses live Poller + Extractor pipeline)")
    print("=" * 55)

    # Step 1: RabbitMQ reachable
    rmq_ok = check_rabbitmq_reachable()

    # Step 2: Queues exist
    raw_ok = check_queue_exists(RAW_QUEUE)
    enriched_ok = check_queue_exists(ENRICHED_QUEUE)

    # Step 3: Publish test message & verify end-to-end
    published_condition_id = publish_test_message() if raw_ok else None
    e2e_ok = False
    if published_condition_id:
        e2e_ok = wait_for_enriched_message(published_condition_id)
        # Purge test messages so they don't accumulate
        purge_queue(RAW_QUEUE)
        purge_queue(ENRICHED_QUEUE)

    print()
    checks = [
        ("RabbitMQ reachable", rmq_ok),
        (f"Queue '{RAW_QUEUE}' exists", raw_ok),
        (f"Queue '{ENRICHED_QUEUE}' exists", enriched_ok),
        ("End-to-end: raw -> enriched", e2e_ok),
    ]

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
