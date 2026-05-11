# Architecture Improvement Review & Plan
> Based on Gemini review of the RPA+AI self-healing architecture.
> 2026-05-08 · Updated 2026-05-11

**人机协助流程**: 详见 [`HUMAN_MACHINE_COLLAB.md`](HUMAN_MACHINE_COLLAB.md) — 影刀/后端/AI 三层职责划分

## Priority Summary

| Priority | Item | Status |
|----------|------|--------|
| **P0** | Crash Snapshot Dump | Implemented |
| **P0** | AI Crash Analysis | Implemented |
| **P0** | pending_fix status (state machine) | Implemented |
| **P1** | File Lock (concurrency protection) | Implemented |
| **P1** | Pytest skeleton | Implemented |
| **P2** | CI/CD integration | Reserved (future) |
| -- | .env credential manager | Closed (existing solution adequate) |

## P0 Details

### Crash Snapshot (_dump_snapshot)
- File: 
- When SystemException occurs, dump structured context to 
- Contains: error_type, traceback, payload, action/expected/actual, git info
- Purpose: AI layer can read this snapshot during analysis

### AI Crash Analysis
- Module: core/ai_analyzer.py
- API: Volcengine Ark (chat/completions)
- Model: glm-4-7-251222 (configurable)
- When SystemException.notify() runs, after _dump_snapshot(), calls AI for root cause analysis
- AI result enriches Linear issue title + description + priority/severity/category
- Graceful fallback: no API key or timeout -> skip AI, keep existing behavior
- Config: project.json -> ai.enabled, ai.api_key, ai.model, ai.timeout

### pending_fix Status
- File: 
- If SystemException + Linear issue created successfully -> status = 
- If SystemException + Linear issue failed (e.g., test env) -> status = 
- Yingdao can use  to mark tasks as pending rather than failed

## P1 Details

### File Lock (_FileLock)
- File: 
- Cross-process lock on  file
- Same repo_path can only execute one instance at a time
- Returns  status if another process holds the lock

### Pytest
- File: 
- Configures test discovery in  directory

## Files Changed

| File | Change |
|------|--------|
| core/exceptions.py | Added _dump_snapshot(), fixed issue_url return, integrated AI analysis |
| core/entry.py | Added pending_fix vs failed status logic |
| runner.py | Added _FileLock class + lock acquire/release in execute() |
| .gitignore | Added crash_snapshots/ and .runner.lock |
| pytest.ini | New file with pytest config |
| core/ai_analyzer.py | NEW - AI crash analysis via Volcengine Ark API |
| core/config.py | Added AI_ENABLED, AI_API_KEY, AI_MODEL, AI_TIMEOUT |
| core/notifier.py | create_linear_issue() accepts ai_analysis param |
| project.json | Added ai section (api_key, enabled, model, timeout) |
| project.template.json | Added ai section + version field |
