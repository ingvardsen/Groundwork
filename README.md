# Groundwork

**A Claude Code skill for iterative agent campaigns.**
Sessions end; the audit trail doesn't.

---

## The problem

AI agent memory is the conversation. Restart, hit the context limit, or hand off to a different expert — the thread is gone. You rebuild from scratch.

Groundwork makes the **filesystem the single source of truth**. Every unit of work gets a brief before it runs and a return when it completes. The conversation becomes disposable. The files are not.

---

## How it works

Two roles, one filesystem contract:

- **Architect** (your session) — surveys work, authors briefs, gates on your approval, reads returns, synthesises findings. Does not execute work directly.
- **Engineer** (subagent) — reads one brief, executes one iteration, writes one return. Its verbal response is decorative; the architect reads the file.

```
iterations/
  brief_001_baseline.md       ← architect writes
  return_001_baseline.md      ← engineer writes
  synthesis.md                ← architect maintains across iterations
```

Nothing is ever overwritten. A new session reads the directory and picks up exactly where the last one left off.

---

## Use cases

### Audit sweep
Scan a codebase, dataset, or infrastructure for issues against a classification taxonomy. Each iteration audits one module or area and files findings in a structured return.

> *"Audit every API endpoint for auth vulnerabilities and classify by severity."*

### Comparative R&D
Test multiple approaches to the same problem. Each iteration runs one variant with a falsifiable hypothesis. The synthesis tracks which mechanisms actually moved the metric.

> *"Compare three prompt strategies for extraction accuracy — run each on the same 50 samples and report mechanism deltas."*

### Bulk migration
Apply the same transformation across many targets. Each iteration handles one target (a file, a service, a schema) with per-target acceptance criteria.

> *"Migrate all 12 database models from SQLAlchemy to Prisma, one model per iteration."*

### Diagnostic
Investigate a specific question through progressive narrowing. Each iteration sharpens the hypothesis until a stop criterion is met.

> *"The pipeline fails on Tuesdays. Narrow down whether it's a data issue, a cron race, or a resource limit."*

---

## Quick start

### 1. Invoke the skill

In a Claude Code session, type:

```
/groundwork-skill
```

Or just describe a multi-iteration task — Claude auto-loads the skill when it detects one.

### 2. Confirm setup

Claude asks three things before the first brief:

1. **Iterations directory** — where files live (default: `iterations/`)
2. **Category** — `audit-sweep` · `comparative-rnd` · `bulk-migration` · `diagnostic`
3. **Resource budget** — wall-time cap per iteration

### 3. Approve and iterate

The architect drafts a brief, you approve, an engineer executes, and the return lands on disk. Repeat until the campaign is done.

### Resuming

Start a new session, load the skill, point to the iterations directory. Claude reads the existing briefs and returns and continues from the last completed slot.

---

## Execution patterns

| Pattern | When | How |
|---------|------|-----|
| **A — Direct** | Single command, under 30 seconds | Engineer runs inline, writes return immediately |
| **B — Supervised** | Longer or unbounded work | Engineer writes a work script and launches `bin/groundwork supervise` detached, then ends turn. Architect monitors the log for a `DONE` / `FAILED` sentinel |

Kill a running supervised job at any time:

```bash
bin/groundwork kill iterations/NNN_slug
```

This terminates the work and supervisor processes and appends `KILLED by architect` to the log.

---

## Campaign mode

For fully autonomous runs, spawn an architect subagent with `templates/architect_role.md` as its role. The subagent runs the campaign loop and reports back for approval after each return.

---

## Testing

Two test layers ship with the skill covering infrastructure lifecycle and schema validation.

```bash
bash tests/run.sh
```

See [`tests/`](tests/) for details on individual layers and scenarios.

---

## Files

| Path | Purpose |
|------|---------|
| `SKILL.md` | Full skill specification (Claude reads this) |
| `bin/groundwork` | CLI: supervisor lifecycle, kill, slot rule, schema validation. `bin/groundwork --help` for the full surface. |
| `templates/brief.md` | Brief schema |
| `templates/return.md` | Return schema |
| `templates/engineer_role.md` | Engineer subagent prompt |
| `templates/architect_role.md` | Architect subagent prompt (campaign mode) |
| `tests/` | Infrastructure + schema tests (pytest) |