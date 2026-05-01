"""
Layer 2: schema validation via the bin/groundwork CLI.

The CLI parses templates/{brief,return}.md at runtime; tests construct
documents in tmp_path and assert on the CLI's exit code and diagnostics.
Anchor tests pin the derived schema (parsed from `groundwork schema`) so a
template edit forces a corresponding test edit.

Run with: pytest tests/layer2.py -v
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GROUNDWORK = ROOT / "bin" / "groundwork"


def gw(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(GROUNDWORK), *args],
                          capture_output=True, text=True)


def parse_schema(kind: str) -> dict[str, set[str]]:
    r = gw("schema", kind)
    assert r.returncode == 0, r.stderr
    out: dict[str, set[str]] = {}
    section: str | None = None
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        if line in ("REQUIRED", "OPTIONAL", "MODES", "STATUSES"):
            section = line.lower()
            out[section] = set()
        elif section is not None:
            out[section].add(line)
    return out


BRIEF_SCHEMA = parse_schema("brief")
RETURN_SCHEMA = parse_schema("return")

# Canonical field order for round-trip construction. Pulled from the templates
# implicitly via BRIEF_SCHEMA["required"] | BRIEF_SCHEMA["optional"], but we
# need a deterministic order for assertions.
BRIEF_FIELD_ORDER = [
    ("Intention", "do thing"),
    ("Hypothesis / target", "thing happens"),
    ("Scope fence", "no expansion"),
    ("Expected artefacts", "out.txt"),
    ("Resource budget", "10s"),
    ("Return trigger", "scripts complete"),
    ("Mode", "direct"),
    ("Model", "sonnet"),
]
RETURN_FIELD_ORDER = [
    ("Status", "complete"),
    ("Verdict", "did the thing"),
    ("Mechanism / what changed", "wrote a file"),
    ("Artefacts", "out.txt"),
    ("Surprises", "none"),
    ("Resource used", "1s"),
    ("Suggested next", "n/a"),
]


def _build(header: str, ordered_fields: list[tuple[str, str]],
           overrides: dict[str, str], omit: set[str]) -> str:
    lines = [header, ""]
    for name, default in ordered_fields:
        canonical = name.lower()
        if canonical in omit:
            continue
        value = overrides.get(canonical, default)
        lines.append(f"**{name}:** {value}")
        lines.append("")
    return "\n".join(lines)


def make_brief(omit: set[str] | None = None, **overrides: str) -> str:
    return _build("# Brief 999: smoke", BRIEF_FIELD_ORDER,
                  {k.lower(): v for k, v in overrides.items()}, omit or set())


def make_return(omit: set[str] | None = None, **overrides: str) -> str:
    return _build("# Return 999: smoke", RETURN_FIELD_ORDER,
                  {k.lower(): v for k, v in overrides.items()}, omit or set())


def write_brief(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "brief_999_smoke.md"
    p.write_text(content)
    return p


def write_return(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "return_999_smoke.md"
    p.write_text(content)
    return p


# ── Anchor tests: drift between templates and validator's contract ────────────

def test_brief_required_fields_match_expectation():
    assert BRIEF_SCHEMA["required"] == {
        "intention", "hypothesis / target", "scope fence",
        "expected artefacts", "resource budget", "return trigger", "mode",
    }, "templates/brief.md required fields drifted"


def test_return_required_fields_match_expectation():
    assert RETURN_SCHEMA["required"] == {
        "status", "verdict", "mechanism / what changed",
        "artefacts", "surprises", "resource used",
    }, "templates/return.md required fields drifted"


def test_brief_optional_fields_match_expectation():
    assert BRIEF_SCHEMA["optional"] == {"model"}


def test_return_optional_fields_match_expectation():
    assert RETURN_SCHEMA["optional"] == {"suggested next"}


def test_valid_modes_match_template_enum():
    assert BRIEF_SCHEMA["modes"] == {"direct", "supervised", "ingest"}


def test_valid_statuses_match_template_enum():
    assert RETURN_SCHEMA["statuses"] == {"complete", "partial"}


# ── Round-trip: a complete document validates ────────────────────────────────

@pytest.mark.parametrize("mode", sorted(BRIEF_SCHEMA["modes"]))
def test_validate_accepts_complete_brief(tmp_path, mode):
    p = write_brief(tmp_path, make_brief(mode=mode))
    r = gw("validate", str(p))
    assert r.returncode == 0, f"stderr: {r.stderr}"
    assert "OK" in r.stdout


@pytest.mark.parametrize("status", sorted(RETURN_SCHEMA["statuses"]))
def test_validate_accepts_complete_return(tmp_path, status):
    p = write_return(tmp_path, make_return(status=status))
    r = gw("validate", str(p))
    assert r.returncode == 0, f"stderr: {r.stderr}"


# ── Mutation: dropping a required field is detected ──────────────────────────

@pytest.mark.parametrize("field", sorted(BRIEF_SCHEMA["required"]))
def test_validate_flags_missing_required_brief_field(tmp_path, field):
    p = write_brief(tmp_path, make_brief(omit={field}))
    r = gw("validate", str(p))
    assert r.returncode == 1
    assert "missing required fields" in r.stderr
    assert field in r.stderr


@pytest.mark.parametrize("field", sorted(RETURN_SCHEMA["required"]))
def test_validate_flags_missing_required_return_field(tmp_path, field):
    p = write_return(tmp_path, make_return(omit={field}))
    r = gw("validate", str(p))
    assert r.returncode == 1
    assert field in r.stderr


# ── Optional fields can be omitted ───────────────────────────────────────────

@pytest.mark.parametrize("field", sorted(BRIEF_SCHEMA["optional"]))
def test_validate_accepts_brief_without_optional_field(tmp_path, field):
    p = write_brief(tmp_path, make_brief(omit={field}))
    r = gw("validate", str(p))
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("field", sorted(RETURN_SCHEMA["optional"]))
def test_validate_accepts_return_without_optional_field(tmp_path, field):
    p = write_return(tmp_path, make_return(omit={field}))
    r = gw("validate", str(p))
    assert r.returncode == 0, r.stderr


# ── Enum validation ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_mode", ["background", "parallel", "DIRECT", "auto"])
def test_validate_rejects_invalid_mode(tmp_path, bad_mode):
    p = write_brief(tmp_path, make_brief(mode=bad_mode))
    r = gw("validate", str(p))
    assert r.returncode == 1
    assert "invalid mode" in r.stderr


@pytest.mark.parametrize("bad_status", ["pending", "running", "COMPLETE", "ok"])
def test_validate_rejects_invalid_status(tmp_path, bad_status):
    p = write_return(tmp_path, make_return(status=bad_status))
    r = gw("validate", str(p))
    assert r.returncode == 1
    assert "invalid status" in r.stderr


# ── Behaviour: prefix collisions, inline bold, mechanism rule ────────────────

def test_validate_does_not_alias_mode_to_model(tmp_path):
    """A brief with **Model:** but no **Mode:** must be flagged as missing Mode."""
    p = write_brief(tmp_path, make_brief(omit={"mode"}))
    r = gw("validate", str(p))
    assert r.returncode == 1
    assert "mode" in r.stderr
    # The **Model:** field is still present and should not be confused with Mode.
    assert "model" not in r.stderr.split("missing required fields:")[1]


def test_validate_ignores_inline_bold_as_field(tmp_path):
    """Inline **Mode:** mid-paragraph must not be parsed as a field declaration."""
    brief = make_brief(omit={"mode"})
    brief += "\nSome prose mentioning **Mode:** inline.\n"
    p = write_brief(tmp_path, brief)
    r = gw("validate", str(p))
    assert r.returncode == 1
    assert "mode" in r.stderr  # still missing because inline bold doesn't count


def test_validate_complete_return_without_mechanism_is_rejected(tmp_path):
    """templates/return.md: 'Score without mechanism is rejected.'"""
    p = write_return(tmp_path,
                     make_return(omit={"mechanism / what changed"}, status="complete"))
    r = gw("validate", str(p))
    assert r.returncode == 1
    assert "mechanism" in r.stderr


# ── Boundary cases ───────────────────────────────────────────────────────────

def test_validate_missing_file_returns_2(tmp_path):
    r = gw("validate", str(tmp_path / "nope.md"))
    assert r.returncode == 2
    assert "not found" in r.stderr


def test_validate_unknown_kind_requires_override(tmp_path):
    p = tmp_path / "synthesis.md"
    p.write_text("# Notes\n")
    r = gw("validate", str(p))
    assert r.returncode == 2
    assert "cannot infer kind" in r.stderr


def test_validate_kind_override_works(tmp_path):
    p = tmp_path / "synthesis.md"
    p.write_text(make_brief())
    r = gw("validate", str(p), "--kind", "brief")
    assert r.returncode == 0, r.stderr


def test_validate_handles_extra_whitespace_in_value(tmp_path):
    """Model output may use double spaces after the marker — must still parse."""
    brief = make_brief().replace("**Mode:** direct", "**Mode:**    direct")
    p = write_brief(tmp_path, brief)
    r = gw("validate", str(p))
    assert r.returncode == 0, r.stderr


def test_validate_handles_field_name_with_slash(tmp_path):
    """Hypothesis / target is a real template field — slash must not break parsing."""
    p = write_brief(tmp_path, make_brief())
    r = gw("validate", str(p))
    assert r.returncode == 0, r.stderr
