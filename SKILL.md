---
name: delegated-iteration
description: Use when the user wants to run a series of iterative tasks (audits, comparisons, migrations, diagnostics, R&D experiments) where each unit is non-trivial and benefits from a written audit trail. Sets up an architect/engineer split with brief/return files as the filesystem contract — the architect (this session) authors briefs and synthesizes returns; an engineer subagent executes one iteration per turn. Triggers on signals like "run a sweep across X", "compare A vs B over the codebase", "iterate on Y with N variants", "audit Z and produce findings", or any multi-iteration task with ≥3 similar units of ≥5 minutes each.
---

# Delegated Iteration

Architect/engineer split with filesystem-as-contract. Use when iterative work has ≥3 similar units, each ≥5 min of agent time, and you want an audit trail.

## When to use vs skip

| Use | Skip |
|---|---|
| ≥3 similar units coming up | One-off task |
| Each unit ≥5 min | Each unit <2 min — overhead > benefit |
| Want an audit trail | Engineer needs frequent architect input mid-flight |
| Want parallel exploration | Units don't share a shape — no template benefit |
| Lead session's context window matters | Single contained task you can do inline |

## Architecture

- **Architect** (this session) — surveys work, authors briefs, gates on user approval, reads returns from disk, synthesizes. Does NOT execute iterations directly.
- **Engineer** (subagent) — reads one brief, executes one iteration, writes one return. Single-turn blocking. Verbal context does NOT cross the agent boundary.
- **Audit trail** = brief/return file pair on disk. Subagent's response message is decorative; architect reads the return file directly.

## Setup (first run)

1. Confirm with user:
   - Iterations directory (default: `iterations/`)
   - Iteration **category** (one of: audit-sweep · comparative-rnd · bulk-migration · diagnostic · long-compute)
   - Resource budget per iteration (wall-time cap, optional cost cap)
2. `mkdir -p <iterations-dir>` if it doesn't exist.

## Slot rule

- Briefs at `<iterations-dir>/brief_<NNN>_<slug>.md`; returns at `<iterations-dir>/return_<NNN>_<slug>.md`.
- Numbering monotonic: `001`, `002`, ...
- Check next free before writing:
  ```
  ls <iterations-dir>/ | grep -E "^(brief|return)_[0-9]+" | sort
  ```
- Next free = highest existing + 1. Never overwrite or fork.

## Brief authoring

Base: `templates/brief.md`. Tailor by category:

| Category | Brief additions |
|---|---|
| audit-sweep | `Classification taxonomy: [...]` |
| comparative-rnd | `Mechanism delta required: yes` · `Refutation outcomes: <conditions that falsify>` |
| bulk-migration | `Targets: [...]` (one brief per target, or batched) |
| diagnostic | `Question: <...>` · `Stop criterion: <...>` |

The brief is the engineer's complete contract. Self-sufficient — engineer reads only the brief + `/CLAUDE.md`.

## Engineer orchestration

| Pattern | When | Mechanism |
|---|---|---|
| A — direct | Single Bash call completes in <30s | Bash blocking, foreground spawn |
| B — supervised | Everything else | Script + supervisor, OS background, Monitor + ingest brief |

Decision is binary: "Can this be done in one Bash call under 30 seconds?" Yes → A. No → D.

**Pattern A spawn:**

```
Agent({
  subagent_type: "general-purpose",
  description: "Execute <NNN>_<slug>",
  prompt: <contents of templates/engineer_role.md>
          + "\n\nBrief: <iterations-dir>/brief_<NNN>_<slug>.md",
})
```

**Pattern B spawn:**

```
Agent({
  subagent_type: "general-purpose",
  description: "Execute <NNN>_<slug>",
  prompt: <contents of templates/engineer_role.md>
          + "\n\nBrief: <iterations-dir>/brief_<NNN>_<slug>.md",
})
```

Engineer writes and nohup-launches the scripts then ends its turn quickly. After the engineer returns, set up a Monitor:

```
Monitor("tail -f <iterations-dir>/NNN_slug.log")
```

Harness streams lines and fires a notification on `DONE` or `FAILED:` sentinel. Do NOT poll.

**On `DONE`:** draft an ingest brief (`Mode: ingest`), spawn ingest engineer (A or B).
**On `FAILED: <reason>`:** read the log tail, decide recovery or halt.

**Kill a running job:**
```
kill $(cat <iterations-dir>/NNN_slug_job.pid) 2>/dev/null
kill $(cat <iterations-dir>/NNN_slug.pid) 2>/dev/null
echo "KILLED by architect" >> <iterations-dir>/NNN_slug.log
```

**Interruption:** load `TaskStop` via ToolSearch to stop the engineer *subagent* only if it is still writing scripts. Once the engineer's turn has ended, the job runs as an OS process — use the kill commands above instead.

## File conventions (Pattern B)

```
<iterations-dir>/
  brief_NNN_slug.md
  return_NNN_slug.md        ← partial on supervised launch; substantive after ingest
  NNN_slug_work.sh
  NNN_slug_supervisor.sh
  NNN_slug.log              ← Monitor target; last line is DONE or FAILED: <reason>
  NNN_slug.pid              ← supervisor PID
  NNN_slug_job.pid          ← work script PID (written by supervisor)
```

## After return ingestion

1. Read the return file from disk; ignore the subagent's verbal response.
2. If verdict shifts program-level findings, patch a synthesis doc (`<iterations-dir>/synthesis.md` or wherever the user keeps it).
3. Draft the next brief if the outcome dictates one.
4. Summarise to user: verdict + proposed next move.
5. Wait for explicit user green light before invoking the next iteration.

## Memory discipline

- Don't save iteration state, results, mechanism findings, or role framings to auto-memory.
- Push lessons into artefacts (briefs, returns, synthesis docs).
- Auto-memory is reserved for cross-conversation collaboration preferences only.

## Files

- `templates/brief.md` — brief schema (architect fills in per iteration)
- `templates/return.md` — return schema (engineer fills in)
- `templates/engineer_role.md` — engineer prompt block (paste verbatim into engineer subagent's prompt)
- `templates/architect_role.md` — *only* used when the architect is itself a spawned subagent (campaign mode where the user supervises from outside). If you (the current session) are the architect, this file is `SKILL.md` itself; you don't need the wrapper.
