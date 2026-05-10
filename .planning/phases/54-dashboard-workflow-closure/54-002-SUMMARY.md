# Phase 54 Plan 002: Chaos Matrix + Chaos Tests — Summary

**Plan:** 54-002
**Phase:** 54-dashboard-workflow-closure
**Subsystem:** Testing — L6 Chaos/Destructive Tests
**Tags:** chaos-tests, chaos-matrix, corrupted-inputs, network-failures, filesystem-errors
**Date:** 2026-05-09

## Objective

Document all destructive/abnormal scenarios in CHAOS_MATRIX.md and implement Level 6 chaos tests — corrupted inputs, network failures, and filesystem errors — with strict isolation guards.

## Results

- **tests/chaos/scenarios/CHAOS_MATRIX.md**: 5437 chars, 15+ documented scenarios across 3 categories with IDs, triggers, expected behavior, and safety contracts.
- **tests/chaos/**: conftest + 3 test files — all passing.
- All tests marked `@pytest.mark.chaos`, excluded from default CI gate.
- All fixtures include isolation guard `assert any(x in str(vault).lower() for x in ("tmp", "temp"))`.

## Key Decisions

- Network failure tests use `PADDLEOCR_JOB_URL` env var manipulation instead of `responses` library, because `responses` mocks cannot cross the subprocess boundary.
- Network tests use a 25s short timeout with `TimeoutExpired` handling — OCR module has retry/backoff logic that can take minutes.
- Permission denied test (FE-05) skipped on Windows with `@pytest.mark.skipif`.
- Corrupted input tests accept current app behavior (some tracebacks on malformed JSON) as known deficiencies.

## Deviations from Plan

### Rule 2 — Missing Critical Functionality

1. **Cross-platform isolation guard**: Same fix as 54-001 — changed `"tmp" in str(vault)` to case-insensitive pattern.

### Known Deferred Issues

1. **Malformed JSON causes traceback**: When `exports/` contains truly malformed JSON (truncated), the sync command exits with a full Python traceback instead of a clean error message. The application logs `WARNING:Failed to parse export file` but then crashes with Traceback. This should be fixed upstream — the `load_export_rows` function in `worker/sync.py` should catch parse errors gracefully.

## Verification

```
python -m pytest tests/chaos/ -m chaos -v --tb=short --timeout=120
> 13 passed, 1 skipped
```

## Artifacts

| File | Status |
|------|--------|
| `tests/chaos/scenarios/CHAOS_MATRIX.md` | Created (15+ scenarios, 3 categories) |
| `tests/chaos/__init__.py` | Created |
| `tests/chaos/conftest.py` | Created (vault fixtures + helper functions + isolation guards) |
| `tests/chaos/test_corrupted_inputs.py` | Created (6 tests: malformed JSON, empty, missing key, corrupt PDF, broken meta, missing frontmatter) |
| `tests/chaos/test_network_failures.py` | Created (4 tests: 401, 500, timeout, DNS unreachable) |
| `tests/chaos/test_filesystem_errors.py` | Created (4 tests: deleted PDF dir, deleted OCR dir, deleted note, permission denied) |
