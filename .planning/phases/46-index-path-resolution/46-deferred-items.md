# Phase 46: Deferred Items

Items discovered during execution but outside the scope of Phase 46.

## Pre-existing Test Failures

### 1. OCR State Machine: test_retry_exhaustion_becomes_error
- **File:** `tests/test_ocr_state_machine.py:805`
- **Failure:** Assert `blocked == error` — OCR state machine returns `blocked` instead of `error` after retry exhaustion
- **Root cause:** Pre-existing — not related to Phase 46 changes
- **Should be handled by:** Phase 49 (Module Hardening) or dedicated OCR state machine fix

### 2. OCR State Machine: test_full_cycle_from_pending_to_done
- **File:** `tests/test_ocr_state_machine.py:1190`
- **Failure:** Assert `queued == done` — OCR state machine returns `queued` instead of `done` after full cycle
- **Root cause:** Pre-existing — not related to Phase 46 changes
- **Should be handled by:** Phase 49 (Module Hardening) or dedicated OCR state machine fix
