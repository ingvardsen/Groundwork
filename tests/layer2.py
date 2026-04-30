"""
Layer 2: schema validation for brief and return files.
Tests the markdown field contract — not agent reasoning, just structure.

Run with: pytest tests/layer2.py -v
"""
import re
import textwrap
import pytest

# ── Field extraction ──────────────────────────────────────────────────────────

def fields(content: str) -> set[str]:
    """Return lowercased field names (colon stripped) from lines starting with **Field:**."""
    return {m.group(1).rstrip(":").lower()
            for m in re.finditer(r"^\*\*([^*]+)\*\*", content, re.MULTILINE)}

def field_value(content: str, name: str) -> str | None:
    """Return first word after a **Field:** line, or None if absent."""
    m = re.search(rf"^\*\*{re.escape(name)}[^*]*\*\*\s*(\S+)", content, re.IGNORECASE | re.MULTILINE)
    return m.group(1) if m else None

BRIEF_REQUIRED = {"intention", "hypothesis", "scope fence", "expected artefacts",
                  "resource budget", "return trigger", "mode"}
RETURN_REQUIRED = {"status", "verdict", "mechanism", "artefacts", "surprises", "resource used"}

VALID_MODES    = {"direct", "supervised", "ingest"}
VALID_STATUSES = {"complete", "partial"}

# ── Fixtures ──────────────────────────────────────────────────────────────────

BRIEF_DIRECT = textwrap.dedent("""\
    # Brief 001: echo-test

    **Intention:** Write "hello" to output.txt.

    **Hypothesis / target:** output.txt contains the string "hello"

    **Scope fence:** Do not touch any file outside the working directory.

    **Expected artefacts:** output.txt

    **Resource budget:** 10s

    **Return trigger:** Script completes and output.txt is written.

    **Mode:** direct
""")

BRIEF_SUPERVISED = textwrap.dedent("""\
    # Brief 002: sleep-test

    **Intention:** Verify the supervised launch pattern works end-to-end.

    **Hypothesis / target:** DONE sentinel appears in log within budget.

    **Scope fence:** No system-level changes. Working dir only.

    **Expected artefacts:** 002_sleep-test.log, 002_sleep-test.pid, 002_sleep-test_job.pid

    **Resource budget:** 30s

    **Return trigger:** Supervisor launched and PID files written.

    **Mode:** supervised
""")

BRIEF_INGEST = textwrap.dedent("""\
    # Brief 003: sleep-test-ingest

    **Intention:** Read completed job artefacts and write substantive return.

    **Hypothesis / target:** Log ends with DONE; result.txt contains expected output.

    **Scope fence:** Read artefacts only — no new process launches.

    **Expected artefacts:** return_002_sleep-test.md (substantive)

    **Resource budget:** 15s

    **Return trigger:** Return file written with full verdict and mechanism.

    **Mode:** ingest
""")

BRIEF_MISSING_FIELDS = textwrap.dedent("""\
    # Brief 004: broken

    **Intention:** Brief with most required fields absent.

    **Mode:** direct
""")

BRIEF_INVALID_MODE = textwrap.dedent("""\
    # Brief 005: bad-mode

    **Intention:** Brief carrying an unrecognised mode value.

    **Hypothesis / target:** N/A

    **Scope fence:** N/A

    **Expected artefacts:** N/A

    **Resource budget:** 10s

    **Return trigger:** Done.

    **Mode:** background
""")

RETURN_COMPLETE = textwrap.dedent("""\
    # Return 001: echo-test

    **Status:** complete

    **Verdict:** output.txt contains "hello" as expected.

    **Mechanism / what changed:** Bash `echo` wrote to file via stdout redirect.

    **Artefacts:** output.txt

    **Surprises:** None.

    **Resource used:** 1s
""")

RETURN_PARTIAL = textwrap.dedent("""\
    # Return 002: sleep-test

    **Status:** partial — job launched, awaiting completion

    **Verdict:** Supervisor PID 12345; log at iterations/002_sleep-test.log

    **Mechanism / what changed:** n/a — launch only

    **Artefacts:** 002_sleep-test_work.sh, 002_sleep-test_supervisor.sh, 002_sleep-test.log, 002_sleep-test.pid, 002_sleep-test_job.pid

    **Surprises:** None.

    **Resource used:** 3s (launch only)
""")

RETURN_MISSING_MECHANISM = textwrap.dedent("""\
    # Return 006: no-mechanism

    **Status:** complete

    **Verdict:** Something happened.

    **Artefacts:** output.txt

    **Surprises:** None.

    **Resource used:** 5s
""")

# ── Brief schema ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("content", [BRIEF_DIRECT, BRIEF_SUPERVISED, BRIEF_INGEST],
                         ids=["direct", "supervised", "ingest"])
def test_valid_brief_has_all_required_fields(content):
    present = fields(content)
    missing = [f for f in BRIEF_REQUIRED if not any(f in p for p in present)]
    assert not missing, f"Missing fields: {missing}"

@pytest.mark.parametrize("content,expected_mode", [
    (BRIEF_DIRECT,     "direct"),
    (BRIEF_SUPERVISED, "supervised"),
    (BRIEF_INGEST,     "ingest"),
])
def test_brief_mode_is_valid(content, expected_mode):
    mode = field_value(content, "Mode")
    assert mode in VALID_MODES
    assert mode == expected_mode

def test_brief_missing_fields_detected():
    present = fields(BRIEF_MISSING_FIELDS)
    missing = [f for f in BRIEF_REQUIRED if not any(f in p for p in present)]
    assert len(missing) >= 4, f"Expected several missing fields, only found: {missing}"

def test_brief_invalid_mode_detected():
    mode = field_value(BRIEF_INVALID_MODE, "Mode")
    assert mode not in VALID_MODES, f"Expected invalid mode, got: {mode}"

# ── Return schema ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("content", [RETURN_COMPLETE, RETURN_PARTIAL],
                         ids=["complete", "partial"])
def test_valid_return_has_all_required_fields(content):
    present = fields(content)
    missing = [f for f in RETURN_REQUIRED if not any(f in p for p in present)]
    assert not missing, f"Missing fields: {missing}"

@pytest.mark.parametrize("content,expected_status", [
    (RETURN_COMPLETE, "complete"),
    (RETURN_PARTIAL,  "partial"),
])
def test_return_status_is_valid(content, expected_status):
    status = field_value(content, "Status")
    assert status in VALID_STATUSES
    assert status == expected_status

def test_return_missing_mechanism_detected():
    present = fields(RETURN_MISSING_MECHANISM)
    has_mechanism = any("mechanism" in p for p in present)
    assert not has_mechanism, "Expected mechanism to be absent"

def test_complete_return_without_mechanism_is_invalid():
    """A complete return must have a mechanism — score without mechanism is rejected."""
    status = field_value(RETURN_MISSING_MECHANISM, "Status")
    present = fields(RETURN_MISSING_MECHANISM)
    has_mechanism = any("mechanism" in p for p in present)
    assert status == "complete" and not has_mechanism, \
        "Fixture should represent an invalid complete-without-mechanism return"
