---
phase: 26-traceable-ai-context-packs
plan: 01
subsystem: worker
tags: [migration, workspace, flat-to-workspace, canonical-index, idempotent]

requires:
  - phase: 22-configuration-truth-compatibility
    provides: workspace path fields in canonical index (paper_root, main_note_path, etc.)
  - phase: 23-canonical-asset-index-safe-rebuilds
    provides: _build_entry(), build_index(), atomic writes, read_index()
provides:
  - "migrate_to_workspace() function — copies flat notes to workspace dirs on first sync"
  - "Workspace-aware _build_entry() — writes notes to workspace path when workspace dir exists"
  - "Flat path fallback — backward compat for unmigrated papers"
  - "Migration tests covering all D-11 through D-15 scenarios"
affects:
  - "26-02: AI context commands will read workspace-structured assets"
  - "26-03: Plugin context buttons will reference workspace paths"

tech-stack:
  added: []
  patterns:
    - "Workspace path computation matches entry's main_note_path formula"
    - "Flat path fallback preserves backward compatibility during transition"
    - "idempotent migration: workspace_dir.exists() check before every copy"

key-files:
  created:
    - tests/test_migration.py (9 tests for migration, _build_entry, and run_index_refresh)
  modified:
    - paperforge/worker/sync.py (migrate_to_workspace() + wired into run_index_refresh)
    - paperforge/worker/asset_index.py (_build_entry workspace-aware write logic)

key-decisions:
  - "Migration runs before build_index() in run_index_refresh() so _build_entry sees the workspace dir"
  - "When workspace dir exists, _build_entry writes to workspace path AND ensures ai/ dir exists"
  - "When workspace dir does NOT exist, _build_entry falls back to flat path (no auto-create of workspace)"
  - "New papers (first sync, no flat note) write to flat path; workspace creation deferred to migration pass"

patterns-established:
  - "Workspace directories are created by migrate_to_workspace(), not by _build_entry()"
  - "The flat-to-workspace transition is a one-time migration pass, not per-entry logic"
  - "Every workspace has ai/ subdir created during migration"

requirements-completed:
  - AIC-02
  - AIC-03
  - AIC-04

duration: 4 min
completed: 2026-05-04
---

# Phase 26 Plan 01: Flat-to-Workspace Note Migration Summary

**Flat literature notes copied into per-paper workspace directories with ## 🔍 精读 extraction and ai/ directory creation, wired into run_index_refresh() for first-sync migration, with workspace-aware _build_entry() writing and backward-compatible flat fallback**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-04T04:43:04Z
- **Completed:** 2026-05-04T04:46:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `migrate_to_workspace()` function in sync.py copies flat notes to workspace dirs, extracts deep-reading sections, and creates ai/ directories
- Migration wired into `run_index_refresh()` before `build_index()` — runs on every sync but skips already-migrated papers (idempotent per D-15)
- `_build_entry()` in asset_index.py updated to write notes to workspace path when workspace dir exists, with flat path fallback for backward compatibility
- 9 pytest tests covering migration, _build_entry workspace writing, idempotency, backward compatibility, and run_index_refresh integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Add migrate_to_workspace() and update _build_entry()** - `8e8677d` (feat)
2. **Task 2: Write migration tests** - `c753a96` (test)

**Plan metadata:** *(will be committed in final metadata commit)*

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `paperforge/worker/sync.py` | Modified | Added `migrate_to_workspace()` (~90 lines), wired into `run_index_refresh()` |
| `paperforge/worker/asset_index.py` | Modified | Updated `_build_entry()` note writing to support workspace paths + flat fallback |
| `tests/test_migration.py` | Created | 9 test cases covering all D-11 through D-15 scenarios |

## Decisions Made

- **Migration runs before build_index()**: This ensures `_build_entry()` sees the workspace dir and writes updates there, keeping existing deep-reading content in the workspace note.
- **Flat fallback is unconditional**: `_build_entry()` does NOT auto-create workspace dirs — it only reads/writes to workspace when the workspace dir already exists. This keeps the migration pass as the single source of truth for workspace creation.
- **Deep-reading preserved in both files**: The main workspace note is a full copy of the flat note (including `## 🔍 精读`), and the extracted deep-reading.md is a separate file. This provides redundancy — if deep-reading.md is lost, the content is still in the main note.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Flat-to-workspace migration is complete — workspace directories now point to real files
- Ready for Plan 26-02 (AI context commands) which reads workspace-structured assets
- Ready for Plan 26-03 (Plugin context buttons) referencing workspace paths
- Existing tests continue to pass (44 passed in asset index and asset state)
