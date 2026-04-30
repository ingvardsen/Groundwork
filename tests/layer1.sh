#!/usr/bin/env bash
# Layer 1: infrastructure tests — supervisor lifecycle and slot rule.
# No external dependencies. Runs in ~10s.
set -uo pipefail

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
FIXTURES="$TESTS_DIR/fixtures"
TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

PASS=0; FAIL=0

ok()   { echo "  ✓ $1"; PASS=$(( PASS + 1 )); }
fail() { echo "  ✗ $1"; FAIL=$(( FAIL + 1 )); }

assert_last_line() {
  local desc="$1" expected="$2" file="$3"
  local actual; actual=$(tail -1 "$file" 2>/dev/null || echo "")
  [[ "$actual" == *"$expected"* ]] && ok "$desc" || fail "$desc  →  got: '$actual'"
}

assert_file_exists() {
  local desc="$1" file="$2"
  [[ -f "$file" ]] && ok "$desc" || fail "$desc  →  missing: $file"
}

assert_process_dead() {
  local desc="$1" pid="$2"
  ! kill -0 "$pid" 2>/dev/null && ok "$desc" || fail "$desc  →  PID $pid still alive"
}

# Generates an instantiated supervisor script matching the engineer_role.md template.
# Poll interval is 0.5s instead of 15s so tests finish fast.
make_supervisor() {
  local work="$1" log="$2" job_pid="$3" max_secs="$4" out="$5"
  cat > "$out" <<SCRIPT
#!/usr/bin/env bash
bash '${work}' >> '${log}' 2>&1 &
JOB_PID=\$!
echo "\$JOB_PID" > '${job_pid}'
START=\$(date +%s)
while kill -0 "\$JOB_PID" 2>/dev/null; do
  sleep 0.5
  if (( \$(date +%s) - START > ${max_secs} )); then
    kill "\$JOB_PID" 2>/dev/null
    echo "FAILED: wall-time budget exceeded (${max_secs}s)" >> '${log}'
    exit 1
  fi
done
wait "\$JOB_PID"
(( \$? == 0 )) && echo "DONE" >> '${log}' || echo "FAILED: work script exited non-zero" >> '${log}'
SCRIPT
  chmod +x "$out"
}

# ── Supervisor lifecycle ───────────────────────────────────────────────────────

echo "Supervisor lifecycle"

# 1. Work exits 0 → DONE sentinel
T="$TMP/t_done"; mkdir "$T"
make_supervisor "$FIXTURES/work_fast.sh" "$T/job.log" "$T/job.pid" 10 "$T/supervisor.sh"
bash "$T/supervisor.sh" 2>/dev/null
assert_last_line "success → DONE" "DONE" "$T/job.log"
assert_file_exists "job.pid written" "$T/job.pid"

# 2. Work exits non-zero → FAILED: work script exited non-zero
T="$TMP/t_fail"; mkdir "$T"
make_supervisor "$FIXTURES/work_fail.sh" "$T/job.log" "$T/job.pid" 10 "$T/supervisor.sh"
bash "$T/supervisor.sh" 2>/dev/null || true
assert_last_line "non-zero exit → FAILED sentinel" "FAILED: work script exited non-zero" "$T/job.log"

# 3. Work exceeds budget → FAILED: wall-time budget exceeded
T="$TMP/t_timeout"; mkdir "$T"
make_supervisor "$FIXTURES/work_slow.sh" "$T/job.log" "$T/job.pid" 2 "$T/supervisor.sh"
bash "$T/supervisor.sh" 2>/dev/null || true
assert_last_line "timeout → FAILED sentinel" "FAILED: wall-time budget exceeded" "$T/job.log"

# 4. Kill via job.pid stops the work process
T="$TMP/t_kill"; mkdir "$T"
make_supervisor "$FIXTURES/work_slow.sh" "$T/job.log" "$T/job.pid" 60 "$T/supervisor.sh"
nohup bash "$T/supervisor.sh" >> "$T/sup.log" 2>&1 &
SUP_PID=$!
# Poll for job.pid (max 5s)
for _ in $(seq 1 10); do [[ -f "$T/job.pid" ]] && break; sleep 0.5; done
if [[ -f "$T/job.pid" ]]; then
  JOB_PID=$(cat "$T/job.pid")
  kill "$JOB_PID" 2>/dev/null || true
  kill "$SUP_PID" 2>/dev/null || true
  sleep 0.5
  assert_process_dead "kill via job.pid stops work process" "$JOB_PID"
else
  fail "job.pid not written within 5s"
  kill "$SUP_PID" 2>/dev/null || true
fi

# ── Slot rule ─────────────────────────────────────────────────────────────────

echo ""
echo "Slot rule"

next_slot() {
  local dir="$1"
  local last
  last=$(ls "$dir/" 2>/dev/null \
    | grep -oE "(brief|return)_[0-9]+" \
    | grep -oE "[0-9]+" \
    | sort -n | tail -1)
  printf "%03d" $(( 10#${last:-000} + 1 ))
}

# 5. Empty dir → 001
T="$TMP/s_empty"; mkdir "$T"
slot=$(next_slot "$T")
[[ "$slot" == "001" ]] && ok "empty dir → 001" || fail "empty dir → expected 001, got $slot"

# 6. Existing files → highest + 1
T="$TMP/s_existing"; mkdir "$T"
touch "$T/brief_003_foo.md" "$T/return_001_bar.md"
slot=$(next_slot "$T")
[[ "$slot" == "004" ]] && ok "existing 001,003 → 004" || fail "existing 001,003 → expected 004, got $slot"

# 7. Return files count toward slot numbering
T="$TMP/s_returns"; mkdir "$T"
touch "$T/return_007_baz.md"
slot=$(next_slot "$T")
[[ "$slot" == "008" ]] && ok "return_007 alone → 008" || fail "return_007 → expected 008, got $slot"

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "  Passed: $PASS  Failed: $FAIL"
(( FAIL == 0 ))
