# Deferred Items — Phase 47

Items discovered during execution that are out of scope and deferred to future phases.

---

## Pre-existing OCR Test Failures (2 tests)

**Found during:** Plan 47-001 / Plan 47-002 — test suite run after all changes
**Files:** `tests/test_ocr_state_machine.py`
**Root cause:** Unknown — these failures existed prior to Phase 47 changes
**Status:** Not caused by this phase; deferred to Phase 49 (Module Hardening) for triage

### Failures

1. **`TestOcrStateMachineLifecycle::test_retry_exhaustion_becomes_error`**
   - Expected: `"error"` — Actual: `"blocked"`
   - Location: `tests/test_ocr_state_machine.py:805`

2. **`TestOcrEdgeCases::test_full_cycle_from_pending_to_done`**
   - Expected: `"done"` — Actual: `"queued"`
   - Location: `tests/test_ocr_state_machine.py:1190`

---

*Logged: 2026-05-07*
