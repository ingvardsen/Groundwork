# Groundwork

**A Claude Code skill for iterative agent campaigns.**
Sessions end; the audit trail doesn't.

---

## Why

An agent's memory is the conversation. Restart, hit the context limit, hand off to a different expert — the thread is gone. You rebuild from scratch.

Groundwork makes the **filesystem the single source of truth**. Every unit of work gets a brief before it runs and a return when it completes. The conversation becomes disposable. The files are not.

---

## How it works

Two roles, one filesystem contract:

- **Architect** (your session) — surveys, authors briefs, reads returns, synthesises. Does not execute.
- **Engineer** (subagent) — reads one brief, executes one iteration, writes one return.

```
iterations/
  brief_001_baseline.md       ← architect writes, you approve
  return_001_baseline.md      ← engineer writes
  synthesis.md                ← architect maintains across iterations
```

Nothing is ever overwritten. A new session reads the directory and picks up where the last one left off.

---

## Quick start

1. In a Claude Code session, type `/groundwork-skill` — or just describe a multi-iteration task and Claude auto-loads when it detects one.
2. Confirm three things: iterations directory, category, per-iteration resource budget.
3. Architect drafts a brief → you approve → engineer executes → return lands on disk.
4. Repeat until done. To resume later, load the skill in a new session pointed at the same iterations directory.

---

## Use cases

**Audit sweep** — scan a codebase, dataset, or infrastructure against a classification taxonomy.
> *"Audit every API endpoint for auth vulnerabilities and classify by severity."*

**Comparative R&D** — test multiple approaches with falsifiable hypotheses; synthesis tracks which mechanisms actually moved the metric.
> *"Compare three prompt strategies for extraction accuracy on the same 50 samples — report mechanism deltas."*

**Bulk migration** — apply the same transformation across many targets with per-target acceptance criteria.
> *"Migrate all 12 database models from SQLAlchemy to Prisma, one model per iteration."*

**Diagnostic** — investigate a question through progressive narrowing until a stop criterion is met.
> *"The pipeline fails on Tuesdays. Narrow down whether it's a data issue, a cron race, or a resource limit."*

---

## Execution patterns

| Pattern | When | How |
|---------|------|-----|
| **A — Direct** | Single command, under 30s | Engineer runs inline, writes return immediately |
| **B — Supervised** | Longer or unbounded | Engineer launches `bin/groundwork supervise` detached and ends turn; architect monitors the log for `DONE` / `FAILED` |

The CLI handles all deterministic plumbing — supervisor lifecycle, kill, slot numbering, schema validation:

```bash
bin/groundwork --help
bin/groundwork next-slot iterations/
bin/groundwork validate iterations/brief_001_foo.md
bin/groundwork kill iterations/NNN_slug    # terminates work + supervisor, appends KILLED sentinel
```

---

## Campaign mode

For fully autonomous runs, spawn an architect subagent with `templates/architect_role.md`. It runs the campaign loop and reports back after each return.

---

## Testing

```bash
bash tests/run.sh   # 52 pytest tests against the CLI
```

Covers supervisor lifecycle, kill sequence, slot rule, and schema validation. See [`tests/`](tests/) for scenarios.

---

## Files

| Path | Purpose |
|------|---------|
| `SKILL.md` | Full skill specification (Claude reads this) |
| `bin/groundwork` | CLI — single source of truth for plumbing |
| `templates/` | Brief/return schemas + engineer/architect role prompts |
| `tests/` | Pytest suite |
