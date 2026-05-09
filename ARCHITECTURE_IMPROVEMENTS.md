# Architecture Improvement Review & Plan
> Based on Gemini review of the RPA+AI self-healing architecture.
> 2026-05-08

## Priority Summary

| Priority | Item | Status |
|----------|------|--------|
| **P0** | Crash Snapshot Dump | Implemented |
| **P0** | pending_fix status (state machine) | Implemented |
| **P1** | File Lock (concurrency protection) | Implemented |
| **P1** | Pytest skeleton | Implemented |
| **P2** | CI/CD integration | Reserved (future) |
| -- | .env credential manager | Closed (existing solution adequate) |

## P0 Details

### Crash Snapshot (_dump_snapshot)
- File: `core/exceptions.py`
- When SystemException occurs, dump structured context to `crash_snapshots/crash_{run_id}.json`
- Contains: error_type, traceback, payload, action/expected/actual, git info
- Purpose: Claude Code can read this snapshot directly during AI self-healing

### pending_fix Status
- File: `core/entry.py`
- If SystemException + Linear issue created successfully -> status = `pending_fix`
- If SystemException + Linear issue failed (e.g., test env) -> status = `failed`
- Yingdao can use `pending_fix` to mark tasks as pending rather than failed

## P1 Details

### File Lock (_FileLock)
- File: `runner.py`
- Cross-process lock on `.runner.lock` file
- Same repo_path can only execute one instance at a time
- Returns `locked` status if another process holds the lock

### Pytest
- File: `pytest.ini`
- Configures test discovery in `tests/` directory

## Files Changed

| File | Change |
|------|--------|
| core/exceptions.py | Added _dump_snapshot(), fixed issue_url return |
| core/entry.py | Added pending_fix vs failed status logic |
| runner.py | Added _FileLock class + lock acquire/release in execute() |
| .gitignore | Added crash_snapshots/ and .runner.lock |
| pytest.ini | New file with pytest config |
