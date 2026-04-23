---
phase: 05-workflow-hardening-and-optional-plugin-shell
plan: '01'
type: execute
subsystem: test-coverage-hardening
tags:
  - ocr
  - state-machine
  - base-views
  - command-docs
  - REL-01
  - REL-03
dependency_graph:
  requires: []
  provides:
    - tests/test_ocr_state_machine.py
  affects:
    - pipeline/worker/scripts/literature_pipeline.py
    - AGENTS.md
tech_stack:
  added:
    - unittest.mock (patches, MagicMock, side_effect factories)
  patterns:
    - HTTPError 401 -> classify_error -> 'blocked' state mapping
    - patch('pipeline.worker.scripts.literature_pipeline.requests.post') for API mocking
key_files:
  created:
    - tests/test_ocr_state_machine.py (474 lines, 8 tests)
  modified:
    - AGENTS.md (consistency verified, placeholder placeholders documented)
decisions:
  - Used HTTPError 401 side_effect to trigger 'blocked' state instead of env var manipulation (registry token always present in test environment)
  - Ensure_ocr_meta patched with side_effect factory to avoid dict mutation across loop iterations
key_links:
  - from: tests/test_ocr_state_machine.py
    to: pipeline/worker/scripts/literature_pipeline.py
    via: run_ocr state transitions
  - from: tests/test_base_views.py
    to: paperforge_lite/cli.py
    via: ensure_base_views rendering
  - from: AGENTS.md
    to: paperforge_lite/cli.py
    via: command reference consistency
---

# Phase 05 Plan 01: Test Coverage Hardening — Summary

## One-liner

OCR state machine tests with 8 passing cases, base view rendering tests verified (21 passing), and AGENTS.md command docs confirmed consistent with cli.py.

## What was done

### Task 1 — OCR State Machine Tests ✅

Created `tests/test_ocr_state_machine.py` (474 lines, 8 tests) covering:

| Test | What it verifies |
|------|-------------------|
| `test_pending_job_is_submitted_and_marked_queued` | Job transitions to `queued` when API returns jobId |
| `test_polling_done_transitions_to_done` | Poll with `state=done` + resultUrl moves job to `done` |
| `test_api_error_state_transitions_to_error` | Poll with `state=error` sets `ocr_status: error` |
| `test_missing_token_blocks_job` | HTTPError 401 → `classify_error` → `blocked` (no env manipulation needed) |
| `test_skips_done_and_blocked_from_existing_queue` | `sync_ocr_queue` skips done/blocked rows |
| `test_removes_blocked_dir_without_payload` | `cleanup_blocked_ocr_dirs` removes empty blocked dirs |
| `test_preserves_blocked_dir_with_payload` | Dirs with `fulltext.md` are preserved |
| `test_all_expected_states_covered` | All 7 states (pending/queued/running/done/error/blocked/nopdf) don't crash |

**Key technical finding:** Registry token is always present in test environment, so blocked state must be triggered via `HTTPError(401).response.status_code = 401` → `classify_error` → `'blocked'`.

### Task 2 — Base Rendering + Custom Path Tests ✅

`tests/test_base_views.py` (12 tests) and `tests/test_base_preservation.py` (9 tests) already covered custom path rendering via `substitute_config_placeholders` and force/non-force behavior. All 21 tests pass.

Existing coverage includes:
- Custom directory paths substituted via `${LIBRARY_RECORDS}`, `${LITERATURE}` placeholders
- `force=False` preserves user views, `force=True` does full regeneration
- Incremental merge preserves non-PaperForge views across refreshes

### Task 3 — Command Docs Consistency ✅

Cross-referenced AGENTS.md paperforge commands against `paperforge_lite/cli.py`:

**AGENTS.md commands verified in cli.py:**
- `paperforge selection-sync` ✅
- `paperforge index-refresh` ✅
- `paperforge ocr run` ✅ (aliased as default `paperforge ocr`)
- `paperforge deep-reading` ✅
- `paperforge deep-reading --verbose` ✅
- `paperforge status` ✅
- `paperforge doctor` ✅
- `paperforge base-refresh` ✅
- `paperforge base-refresh --force` ✅
- `paperforge ocr doctor` ✅
- `paperforge ocr doctor --live` ✅
- `paperforge paths` ✅
- `paperforge paths --json` ✅

**Consistency notes:**
- AGENTS.md uses `<system_dir>` and `<resources_dir>` placeholders in directory path diagrams (expected — these are user-configurable path names documented in installation context, not CLI commands)
- Legacy Python path examples in AGENTS.md (`python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py`) are documented as fallback, not current usage

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_missing_token_blocks_job` — 7 attempts to fix blocked state detection**
- **Issue:** Env var token is always read from registry in test environment, making `patch.dict(os.environ, {}, clear=True)` ineffective for simulating missing token.
- **Fix:** Used `HTTPError 401` with `response.status_code=401` as side_effect on mocked `requests.post`. This correctly triggers `classify_error` path which maps 401 → `'blocked'`.
- **Files modified:** `tests/test_ocr_state_machine.py`
- **Commit:** `935d948`

**2. [Rule 2 - Critical] `ensure_ocr_meta` dict mutation across loop iterations**
- **Issue:** Patching `ensure_ocr_meta` with `return_value={}` caused shared dict mutation as the same dict was reused across multiple items in the loop.
- **Fix:** Changed to `side_effect=make_meta` factory returning a fresh dict on each call.
- **Files modified:** `tests/test_ocr_state_machine.py`
- **Commit:** `935d948`

## Metrics

| Item | Value |
|------|-------|
| Duration | ~45 minutes |
| Tasks completed | 3/3 |
| Tests added | 8 (test_ocr_state_machine.py) |
| Tests verified | 21 base views + 8 OCR state = 29 passing |
| Commits | 1 (`935d948`) |

## Files created/modified

- `tests/test_ocr_state_machine.py` — 474 lines, 8 OCR state machine tests (created)
- `AGENTS.md` — command docs consistency verified (no changes needed)
- `tests/test_base_views.py` — 12 tests, verified passing (no changes needed)
- `tests/test_base_preservation.py` — 9 tests, verified passing (no changes needed)

## Self-Check

- [x] `tests/test_ocr_state_machine.py` exists and runs without errors
- [x] At least 4 test functions covering major state transitions
- [x] All mocks use unittest.mock — no real network calls
- [x] `pytest tests/ -k ocr_state` passes (8/8)
- [x] `pytest tests/ -k base` passes (21/21)
- [x] AGENTS.md commands match cli.py command surface
- [x] No broken command references in AGENTS.md