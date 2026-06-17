---
gsd_state_version: 1.0
milestone: annotation v0.1
milestone_name: PDF Annotation Backend & CLI Foundation
status: Phase 1 complete
stopped_at: Annotation Phase 1 executed - 3/3 plans complete (18 tests + 1 skipped)
last_updated: "2026-06-17T12:45:00.000Z"
last_activity: 2026-06-17 - Annotation Phase 1 completed: annotation package, schema, rebuild isolation regression
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-17)

**Core value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.
**Current focus:** Annotation Phase 1 - Annotation Storage Foundation

## Current Position

Phase: Annotation Phase 1 of 4 (Annotation Storage Foundation) ✓ Complete
Plan: 3 of 3 complete
Last activity: 2026-06-17 - Annotation Phase 1 executed (3 waves, 3 plans)

## Performance Metrics

**Velocity:**

- Total plans completed: 3
- Average duration: ~3.5 min
- Total execution time: ~10.5 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Annotation Phase 1 | 3/3 | 100% | ~3.5 min |

**Recent Trend:**

- Annotation Phase 1: 3/3 plans completed, 18 tests + 1 skipped pass.

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.1]: Incremental extraction from sync.py — adapters first, then SyncService, keeping sync.py as thin shell. No full rewrite.
- [v2.1]: Dual JSON output during contract transition — old format + new PFResult side-by-side until 2 release cycles of stability.
- [v2.1]: Plugin keeps fallback to direct index reading during PFResult transition — removed after 2 stable release cycles.
- [annotation v0.1]: Build PDF annotation as a parallel feature line from current upstream/master, not from the stale old branch directly.
- [annotation v0.1]: Import only backend/CLI annotation capabilities first; defer Obsidian PDF overlay to a later annotation milestone.
- [annotation v0.1]: Zotero SQLite is read-only input; PaperForge writes annotation state only to its own `annotations.db`.
- [annotation v0.1]: Paper-scoped imports must not mark unrelated paper annotations as stale/deleted.
- [annotation v0.1]: `annotations.db` schema source fields use generic names (source, source_library_id, etc.) — not Zotero-specific names.
- [annotation v0.1]: Annotation schema tables are defined in `paperforge.annotation.schema.ANNOTATION_TABLES`, not in `paperforge.memory.schema.ALL_TABLES`.
- [v2.1]: Tests must not be modified to pass if code is broken — tests verify contracts, not implementation convenience.

### Pending Todos

None yet.

### Blockers/Concerns

- **`test_config.py` Windows tmp_path failures**: 4 config tests fail with `PermissionError` on Windows when using the `tmp_path` pytest fixture. These are pre-existing and unrelated to annotation code — affect all tests that create vault subdirectories in temp dirs. Not a blocker for annotation work.
- **`test_paperforge_paths_returns_exact_keys` key mismatch**: Test expects `ld_deep_script` but config returns `pf_deep_script`. Pre-existing baseline mismatch unrelated to annotation.
- **Missing `filelock` dependency**: `paperforge/memory/builder.py` transitively imports `filelock` via `worker/asset_index.py`. The `build_from_index` integration test in plan 03 is skipped due to this missing package. Direct `drop_all_tables` regression provides equivalent coverage.

## Session Continuity

Last session: 2026-06-17
Stopped at: Annotation Phase 1 complete - Annotation Storage Foundation (3/3 plans)
Resume file: Next up: Annotation Phase 2 (Zotero Probe and Safe Import)
