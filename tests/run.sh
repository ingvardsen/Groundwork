#!/usr/bin/env bash
set -uo pipefail
TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 -m pytest "$TESTS_DIR/layer1.py" "$TESTS_DIR/layer2.py" -v --tb=short --no-header
