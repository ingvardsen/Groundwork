# Tests

All tests run via pytest against the `bin/groundwork` CLI — the single source of truth. No bash patterns are duplicated between the tests and the skill markdown.

```bash
bash tests/run.sh
# or
python3 -m pytest tests/ -v
```

Requires Python 3 and pytest (`pip install pytest`). Full suite runs in ~3 seconds.

---

## Layer 1 — Supervisor lifecycle, kill, slot rule (`layer1.py`)

Drives `groundwork supervise`, `groundwork kill`, and `groundwork next-slot` via subprocess. Replaces the previous `layer1.sh` and its hardcoded supervisor copy.

**Scenarios:**

- `supervise` writes `DONE` when work exits 0; `FAILED: work script exited non-zero` on non-zero exit; `FAILED: wall-time budget exceeded` on timeout.
- `supervise` returns exit 2 when the work script doesn't exist.
- `kill` terminates a running supervised job and appends `KILLED by architect` to the log.
- `next-slot` returns `001` for empty/missing dirs, highest+1 otherwise; counts both brief and return files; ignores work scripts and synthesis files.

## Layer 2 — Schema validation (`layer2.py`)

Drives `groundwork validate` and `groundwork schema` via subprocess. Builds documents in `tmp_path` from a canonical field map, mutates them, and asserts on the CLI's exit code and diagnostics.

**Scenarios:**

- *Anchor:* schema parsed from `groundwork schema {brief,return}` matches an explicit expectation. Drift in `templates/{brief,return}.md` fails this test.
- *Round-trip:* a complete brief or return validates with exit 0.
- *Mutation:* parametrized over each required field — dropping it produces exit 1 with a `missing required fields` message naming the field.
- *Optional fields:* parametrized over each optional field — dropping it leaves exit 0.
- *Enum rejection:* invalid `mode` and `status` values (case mismatches, unknowns) produce exit 1.
- *Behaviour:* prefix collisions (`Mode` ≠ `Model`), inline `**bold**` ignored as field declarations, complete returns without mechanism rejected.
- *Boundaries:* missing files return exit 2; unknown filenames need `--kind`; whitespace tolerance; slash-bearing field names parse correctly.
