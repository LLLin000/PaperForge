---
phase: 49-module-hardening
plan: 001-003 (combined)
wave: 1
subsystem: worker, plugin
tags: hardening, security, safety
provides:
  - HARDEN-01: Cross-process file locking in discussion.py
  - HARDEN-02: Markdown escaping in QA text fields
  - HARDEN-03: UTC timestamps (not CST/UTC+8)
  - HARDEN-04: API key via environment variable (not CLI arg)
  - HARDEN-05: createEl() DOM API (no innerHTML XSS vector)
  - HARDEN-06: Workspace integrity checks before /pf-deep recommendation
  - HARDEN-07: Empty dicts {} instead of None for index aggregates
affects:
  - discussion.py: read-modify-write now locked, timestamps UTC, MD escaped
  - main.js: spawn uses env var, dir tree uses createEl()
  - asset_state.py: next_step ordering corrected
  - status.py: JSON output safe for dict consumers
tech-stack:
  added:
    - filelock library (existing dependency, now used by discussion.py)
  patterns:
    - filelock.FileLock for cross-process synchronization
    - datetime.now(timezone.utc) for canonical timestamps
    - PADDLEOCR_API_TOKEN env var for API key transport
    - createEl() obsidian DOM API for XSS-safe rendering
key-files:
  created: []
  modified:
    - paperforge/worker/discussion.py
    - paperforge/plugin/main.js
    - paperforge/worker/asset_state.py
    - paperforge/worker/status.py
    - tests/test_discussion.py
    - tests/test_asset_state.py
    - tests/test_status.py
decisions:
  - "filelock.FileLock used over fcntl/msvcrt for cross-platform portability (same pattern as asset_index.py)"
  - "CST constant name preserved but now assigned timezone.utc — minimal diff, no downstream impact"
  - "Both JSON and MD writes wrapped in single lock scope for read-modify-write consistency"
metrics:
  duration: 8 min
  completed_date: "2026-05-07"
---

# Phase 49 Module Hardening: Summary

**One-liner:** Production-grade safety guards across discussion.py (locking, escaping, UTC), main.js (env var API key, createEl() DOM), and asset_state/status (reordered checks, empty-safe dicts).

## Plans Executed

### Plan 49-001: discussion.py hardening (HARDEN-01, HARDEN-02, HARDEN-03)

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | UTC timestamps + Markdown escaping | `5a69874` | discussion.py, test_discussion.py |
| 2 | File locking | `5a69874` | discussion.py, test_discussion.py |

### Plan 49-002: main.js hardening (HARDEN-04, HARDEN-05)

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | API key via env var | `8b9b366` | main.js |
| 2 | createEl() not innerHTML | `8b9b366` | main.js |

### Plan 49-003: asset_state.py + status.py hardening (HARDEN-06, HARDEN-07)

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Workspace integrity check order | `4e816f9` | asset_state.py, test_asset_state.py |
| 2 | Empty dicts not null | `4e816f9` | status.py, test_status.py |

## Verification Results

```
test_discussion.py ........ 12/12 passed (5 new tests)
test_asset_state.py ....... 28/28 passed (2 new + 1 updated)
test_status.py ............ 6/6 passed (1 assertion updated)
Full suite ................ 485/489 passed, 2 skipped, 2 pre-existing failures
```

- **2 pre-existing failures** in `test_ocr_state_machine.py` (unrelated — test OCR state transitions, not modified by any plan)
- **0 regressions** from our changes
- **JS verification:** `--paddleocr-key` absent, `PADDLEOCR_API_TOKEN` present, `innerHTML` eliminated from dir tree, `createEl()` chain present

## Deviations from Plan

None — all three plans executed exactly as written.

## Verification Details

### HARDEN-01: File locking
- `import filelock` present in discussion.py ✅
- `filelock.FileLock` used with `.json.lock` suffix ✅
- Lock timeout = 10s ✅
- Both JSON and MD writes inside same lock scope ✅
- `test_file_lock_prevents_concurrent_write` passes ✅
- `test_lock_timeout_returns_error` passes ✅

### HARDEN-02: Markdown escaping
- `_escape_md()` helper escapes `*`, `#`, `[`, `]`, `_`, `` ` `` via regex ✅
- Applied to both question and answer in `_build_md_session()` ✅
- `test_markdown_escaping` passes ✅
- `test_markdown_escaping_cjk` passes ✅
- Idempotent (does not double-escape) via regex pattern ✅

### HARDEN-03: UTC timestamps
- `_CST = timezone.utc` (replaced `timedelta(hours=8)`) ✅
- `_now_iso()` docstring updated ✅
- `test_utc_timestamp` passes (ends with `+00:00`) ✅
- No `timedelta(hours=8)` remains in discussion.py ✅

### HARDEN-04: API key via env var
- CLI arg `--paddleocr-key` removed from setupArgs ✅
- `PADDLEOCR_API_TOKEN` present in spawn options ✅
- `env: { ...process.env, PADDLEOCR_API_TOKEN: ... }` pattern ✅
- API key not visible in process listing ✅

### HARDEN-05: createEl() DOM API
- `tree.innerHTML = ...` replaced with `tree.createEl()` chain ✅
- `textContent` used instead of innerHTML for user-supplied values ✅
- XSS vector from directory names eliminated ✅

### HARDEN-06: Workspace integrity before /pf-deep
- note_path check moved before /pf-deep check ✅
- workspace_paths check moved before /pf-deep check ✅
- Docstring updated to reflect new ordering ✅
- `test_missing_note_blocks_pf_deep` returns "sync" ✅
- `test_missing_workspace_path_blocks_pf_deep` returns "sync" ✅

### HARDEN-07: Empty dicts not null
- `lifecycle_level_counts = {}` (was `None`) ✅
- `health_aggregate = {}` (was `None`) ✅
- `maturity_distribution = {}` (was `None`) ✅
- Comment updated ✅
- `test_status_json_fallback_when_index_missing` asserts `== {}` ✅

## Known Stubs

None identified.

## Self-Check: PASSED

- [x] All modified files verified: discussion.py, main.js, asset_state.py, status.py, 3 test files
- [x] All 3 commits exist in git log
- [x] Tests pass for all modified modules
- [x] Full suite: no regressions (2 pre-existing failures unrelated)
- [x] JS verification clean

## Self-Check

- [x] All modified files verified: discussion.py, main.js, asset_state.py, status.py, 3 test files
- [x] All 3 commits exist in git log
- [x] Tests pass for all modified modules
- [x] Full suite: no regressions (2 pre-existing failures unrelated)
- [x] JS verification clean
