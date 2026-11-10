#!/usr/bin/env bash
set -euo pipefail

echo "=== ruff check ==="
ruff check .
echo "=== ruff format ==="
ruff format --check .
echo "=== mypy ==="
mypy . --strict
echo "=== bandit ==="
bandit -r . -ll
echo "=== pytest ==="
python -m pytest -q
echo "=== ALL CHECKS PASSED ==="