# Deferred Items — Phase 48: Textual TUI Removal

## Pre-existing Test Failures (Unrelated to TUI changes)

Discovered during post-TUI-removal verification run on 2026-05-07.

### 1. TestOcrStateMachineLifecycle.test_retry_exhaustion_becomes_error
- **File:** tests/test_ocr_state_machine.py:805
- **Error:** Asserts `ocr_status == "error"` but got `"blocked"`
- **Root cause:** State machine behavior changed — retry exhaustion now produces `blocked` status instead of `error`. Pre-existing, not caused by TUI removal.

### 2. TestOcrEdgeCases.test_full_cycle_from_pending_to_done
- **File:** tests/test_ocr_state_machine.py:1190
- **Error:** Asserts `ocr_status == "done"` but got `"queued"`
- **Root cause:** State machine lifecycle changed — final state is now `queued` instead of `done`. Pre-existing, not caused by TUI removal.

**Resolution:** These failures were present before Phase 48 changes and are unrelated to Textual TUI removal. They should be addressed in a future phase focused on OCR state machine hardening (e.g., Phase 49 Module Hardening).
