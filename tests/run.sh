#!/usr/bin/env bash
set -uo pipefail
TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "━━━ Layer 1: Infrastructure ━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$TESTS_DIR/layer1.sh"
L1=$?

echo ""
echo "━━━ Layer 2: Schema ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 -m pytest "$TESTS_DIR/layer2.py" -v --tb=short --no-header -q
L2=$?

echo ""
if (( L1 == 0 && L2 == 0 )); then
  echo "All tests passed."
else
  echo "Failures — L1=$L1  L2=$L2"
  exit 1
fi
