---
phase: 23-canonical-asset-index-safe-rebuilds
plan: 02
subsystem: asset-index
tags: [legacy-migration, incremental-refresh, workspace-paths, cli-flag]

requires:
  - phase: 23-canonical-asset-index-safe-rebuilds
    plan: 01
    provides: asset_index.py with build_index, atomic_write_index, envelope format
provides:
  - Legacy bare-list detection, .bak backup, and auto-migration to envelope format
  - refresh_index_entry(vault, key) for single-entry incremental refresh
  - Shared _build_entry() helper used by both full rebuild and incremental refresh
  - Schema version mismatch auto-detection triggering full rebuild
  - Workspace path fields (paper_root, main_note_path, etc.) in each index entry
  - Path fields mirrored in formal note frontmatter for Base view compatibility
  - --rebuild-index CLI flag on paperforge sync command
affects:
  - sync.py (frontmatter_note updated, run_index_refresh accepts rebuild_index)
  - cli.py (new --rebuild-index flag)
  - commands/sync.py (threads rebuild_index to run_index_refresh)

tech-stack:
  added: []
  patterns:
    - _build_entry shared helper pattern (single source of truth for entry construction)
    - Lazy imports inside helper functions to avoid circular deps

key-files:
  created: []
  modified:
    - paperforge/worker/asset_index.py (read_index, is_legacy_format, migrate_legacy_index, _build_entry, refresh_index_entry, schema_version check, workspace path fields)
    - paperforge/worker/sync.py (frontmatter_note path fields, run_index_refresh rebuild_index param)
    - paperforge/cli.py (--rebuild-index option)
    - paperforge/commands/sync.py (rebuild_index threading)

key-decisions:
  - "Legacy bare-list formal-library.json is auto-detected on read, backed up as .bak, and transparently migrated to envelope format"
  - "refresh_index_entry falls back to full build_index() when index is missing or in legacy format"
  - "Entry construction logic is extracted to _build_entry() — shared by both full rebuild and incremental refresh, guaranteeing field consistency"
  - "Schema version mismatch triggers full rebuild rather than making incremental refresh on mismatched schema (safer)"
  - "Workspace path fields are forward-slash paths relative to vault root, matching existing note_path format"
  - "Path fields are mirrored in note frontmatter (paper_root, main_note_path, etc.) so Obsidian Base views can read them directly"
  - "Existing system paths (ocr_path, meta_path, note_path, deep_reading_md_path) retained for backward compatibility (D-13)"

requirements-completed:
  - ASSET-01
  - ASSET-02
  - ASSET-03
  - ASSET-04

duration: 5 min
completed: 2026-05-04
---

# Phase 23 Plan 02: Safe rebuilds, incremental refresh, workspace paths, CLI flag

**Legacy bare-list auto-migration, incremental refresh by Zotero key, workspace path fields in every index entry, and --rebuild-index CLI flag for the canonical asset index**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-04T00:41:16Z
- **Completed:** 2026-05-04T00:46:40Z
- **Tasks:** 3 (3 auto)
- **Files modified:** 4

## Accomplishments

- Added `read_index()`, `is_legacy_format()`, `migrate_legacy_index()` for transparent legacy bare-list detection, backup (.bak), and auto-migration in `build_index()`
- Extracted shared `_build_entry()` helper from `build_index()` loop — used by both full rebuild and incremental refresh
- Added `refresh_index_entry(vault, key)` for single-entry incremental update with atomic write-back
- Added schema version mismatch check in `build_index()` — auto-triggers full rebuild when `schema_version` differs
- Added workspace path fields (`paper_root`, `main_note_path`, `fulltext_path`, `deep_reading_path`, `ai_path`) to each index entry matching Phase 22 paper workspace layout
- Mirrored workspace path fields in formal note YAML frontmatter for Obsidian Base view consumption
- Added `--rebuild-index` CLI flag to `paperforge sync` command, threaded through to `run_index_refresh()`
- All 14 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Legacy format detection, backup, and auto-migration** - `6da4116` (feat)
2. **Task 2: Incremental refresh (refresh_index_entry) and schema_version check** - `2fd3726` (feat)
3. **Task 3: Workspace path fields, frontmatter mirroring, and --rebuild-index flag** - `2886afa` (feat)

**Plan metadata:** (pending final commit)

## Files Created/Modified

- `paperforge/worker/asset_index.py` — Added `read_index`, `is_legacy_format`, `migrate_legacy_index`, `_build_entry`, `refresh_index_entry`; modified `build_index` to call migration + schema check + use `_build_entry`
- `paperforge/worker/sync.py` — Added workspace path fields to `frontmatter_note()` frontmatter; added `rebuild_index` parameter to `run_index_refresh()`
- `paperforge/cli.py` — Added `--rebuild-index` flag to sync subparser
- `paperforge/commands/sync.py` — Thread `rebuild_index` argument from CLI to `run_index_refresh()`

## Decisions Made

- Legacy format detection is done at read time by checking if the root JSON value is a `list` (bare-list) or a `dict` with `schema_version` (envelope)
- Backup overwrites previous `.bak` (idempotent — last backup is most recent legacy state)
- Corrupt JSON is treated as missing (starts fresh with warning log)
- `_build_entry()` function lives in `asset_index.py` with lazy imports (same pattern as `build_index()`) to avoid circular deps with `sync.py`
- `refresh_index_entry` delegates to full `build_index()` when the index is missing, legacy format, or the key is not found — full rebuild is always a safe fallback
- Workspace paths use forward slashes (consistent with existing `note_path` format)
- `--rebuild-index` is on the `sync` command (not a separate command) per D-10 discretion

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Plan 02 complete. Ready for Plan 03 (likely lifecycle state derivation, maturity models, or health diagnostics).

---

*Phase: 23-canonical-asset-index-safe-rebuilds*
*Completed: 2026-05-04*
