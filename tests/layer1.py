"""
Layer 1: supervisor lifecycle, kill sequence, slot rule — exercised through
the bin/groundwork CLI (the single source of truth). No bash duplication.

Run with: pytest tests/layer1.py -v
"""
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GROUNDWORK = ROOT / "bin" / "groundwork"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAST_POLL = "0.1"  # tighter than the 15s default so tests finish fast


def gw(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(GROUNDWORK), *args],
                          capture_output=True, text=True, **kwargs)


def last_line(path: Path) -> str:
    return path.read_text().splitlines()[-1] if path.exists() else ""


# ── Supervisor lifecycle ──────────────────────────────────────────────────────

def test_supervise_writes_done_on_success(tmp_path):
    log = tmp_path / "job.log"
    job_pid = tmp_path / "job.pid"
    r = gw("supervise", "--work", str(FIXTURES / "work_fast.sh"),
           "--log", str(log), "--max-secs", "10",
           "--poll-interval", FAST_POLL, "--job-pid-file", str(job_pid))
    assert r.returncode == 0, r.stderr
    assert last_line(log) == "DONE"
    assert job_pid.exists()
    assert job_pid.read_text().strip().isdigit()


def test_supervise_writes_failed_on_nonzero_exit(tmp_path):
    log = tmp_path / "job.log"
    r = gw("supervise", "--work", str(FIXTURES / "work_fail.sh"),
           "--log", str(log), "--max-secs", "10", "--poll-interval", FAST_POLL)
    assert r.returncode == 1
    assert last_line(log) == "FAILED: work script exited non-zero"


def test_supervise_writes_failed_on_timeout(tmp_path):
    log = tmp_path / "job.log"
    r = gw("supervise", "--work", str(FIXTURES / "work_slow.sh"),
           "--log", str(log), "--max-secs", "1", "--poll-interval", FAST_POLL)
    assert r.returncode == 1
    assert last_line(log).startswith("FAILED: wall-time budget exceeded")


def test_supervise_missing_work_script_returns_2(tmp_path):
    r = gw("supervise", "--work", str(tmp_path / "nope.sh"),
           "--log", str(tmp_path / "job.log"),
           "--max-secs", "1", "--poll-interval", FAST_POLL)
    assert r.returncode == 2
    assert "not found" in r.stderr


# ── Kill sequence ─────────────────────────────────────────────────────────────

def test_kill_terminates_running_job_and_appends_sentinel(tmp_path):
    iter_dir = tmp_path
    stem = iter_dir / "001_slow"
    log = iter_dir / "001_slow.log"
    job_pid_file = iter_dir / "001_slow_job.pid"
    sup_pid_file = iter_dir / "001_slow.pid"

    sup = subprocess.Popen(
        [str(GROUNDWORK), "supervise",
         "--work", str(FIXTURES / "work_slow.sh"),
         "--log", str(log), "--max-secs", "60",
         "--poll-interval", FAST_POLL,
         "--job-pid-file", str(job_pid_file)])
    sup_pid_file.write_text(str(sup.pid))

    # Wait up to 5s for the supervisor to write the job pid file.
    for _ in range(50):
        if job_pid_file.exists():
            break
        time.sleep(0.1)
    assert job_pid_file.exists(), "supervisor failed to write job.pid in time"
    job_pid = int(job_pid_file.read_text().strip())

    r = gw("kill", str(stem))
    assert r.returncode == 0

    sup.wait(timeout=5)

    # Job process should be gone.
    with pytest.raises(ProcessLookupError):
        os.kill(job_pid, 0)
    assert "KILLED by architect" in log.read_text()


# ── Slot rule ─────────────────────────────────────────────────────────────────

def test_next_slot_in_empty_dir_is_001(tmp_path):
    r = gw("next-slot", str(tmp_path))
    assert r.returncode == 0
    assert r.stdout.strip() == "001"


def test_next_slot_for_nonexistent_dir_is_001(tmp_path):
    r = gw("next-slot", str(tmp_path / "missing"))
    assert r.returncode == 0
    assert r.stdout.strip() == "001"


def test_next_slot_skips_to_highest_plus_one(tmp_path):
    (tmp_path / "brief_003_foo.md").touch()
    (tmp_path / "return_001_bar.md").touch()
    r = gw("next-slot", str(tmp_path))
    assert r.stdout.strip() == "004"


def test_next_slot_counts_return_files_too(tmp_path):
    (tmp_path / "return_007_baz.md").touch()
    r = gw("next-slot", str(tmp_path))
    assert r.stdout.strip() == "008"


def test_next_slot_ignores_unrelated_files(tmp_path):
    (tmp_path / "brief_002_foo.md").touch()
    (tmp_path / "synthesis.md").touch()
    (tmp_path / "002_foo_work.sh").touch()  # work script — not a slot owner
    r = gw("next-slot", str(tmp_path))
    assert r.stdout.strip() == "003"
