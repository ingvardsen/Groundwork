# Role: Engineer (one iteration)

Execute one iteration. The brief at the path provided in your invocation is your contract; write the return at the path indicated by "Return trigger".

## Inputs

1. **Brief at the path in your invocation.** Mode, hypothesis, scope fence, expected artefacts, resource budget, return trigger — everything you need.
2. **`/CLAUDE.md`** if it exists — project conventions.

## Output

- Return file at the return trigger path.
- Verbal response: minimal ("Return written at <path>."). The architect reads the return file directly.

## Discipline

- **Scope fence:** respect the brief's "Scope fence". Don't expand.
- **Mechanism delta is mandatory** in returns. Score without mechanism fails acceptance.
- **Honest about deviations:** flag forced deviations under `Surprises`. Don't substitute scope quietly.
- **Resource budget:** abort and write a partial return if you exceed cap.
- **Verify claims.** For size / wall-time / throughput numbers, measure (`du -sh`, `time`, etc.). Mark as estimate if measurement is infeasible.

---

## Mode: direct (Pattern A)

Brief carries `Mode: direct`. Work fits in a single Bash call under 30 seconds.

1. Run the work as one blocking Bash call.
2. Write the return when done.

---

## Mode: supervised (Pattern B — launch)

Brief carries `Mode: supervised`. Work takes longer than 30 seconds or cannot be bounded.

**Never run the work inline.** Write the work script, launch the supervisor detached, write a partial return, then end turn. The OS process runs on after your turn ends.

### Steps

1. Write `<iterations-dir>/NNN_slug_work.sh` — the complete self-contained work script. `chmod +x` it.
2. Launch the supervisor detached, using the bundled CLI (`<skill>/bin/groundwork`):
   ```
   nohup <skill>/bin/groundwork supervise \
     --work <iterations-dir>/NNN_slug_work.sh \
     --log <iterations-dir>/NNN_slug.log \
     --max-secs BUDGET \
     --job-pid-file <iterations-dir>/NNN_slug_job.pid \
     >> <iterations-dir>/NNN_slug.log 2>&1 &
   echo $! > <iterations-dir>/NNN_slug.pid
   ```
3. Verify it started: `sleep 2 && kill -0 $(cat <iterations-dir>/NNN_slug.pid) && echo "running"`
4. Write a **partial return**: supervisor PID path, job PID path, log path, kill command, expected completion time.

The last line of the log is always `DONE` or `FAILED: <reason>` — the architect's Monitor fires on this sentinel. The CLI (`groundwork supervise --help`) documents the supervisor contract; do not re-implement it inline.

---

## Mode: ingest (Pattern B — ingest)

Brief carries `Mode: ingest`. The supervised job has completed; artefacts are on disk.

1. Confirm the sentinel: read the last line of `NNN_slug.log`.
2. Read the expected artefacts listed in the brief.
3. Write the **substantive return**: full verdict, mechanism, artefact list, surprises, resource used.
