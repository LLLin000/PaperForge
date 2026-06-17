---
gsd_state_version: 1.0
milestone: annotation v0.1
milestone_name: PDF Annotation Backend & CLI Foundation
status: Ready to execute
stopped_at: Annotation Phase 3 planned - 4 plans ready
last_updated: "2026-06-18T18:30:00.000+08:00"
last_activity: 2026-06-18 - Annotation Phase 3 planned: 4 waves for CLI namespace, import JSON, read-only JSON commands, and contract verification
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 15
  completed_plans: 7
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-17)

**Core value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.
**Current focus:** Annotation Phase 3 - Annotation CLI JSON Contracts

## Current Position

Phase: Annotation Phase 3 of 4 (Annotation CLI JSON Contracts) - planned, ready to execute
Plan: 0 of 4 complete
Last activity: 2026-06-18 - Annotation Phase 3 plans created

## Performance Metrics

**Velocity:**

- Total plans completed: 7
- Total plans planned: 15
- Average duration: ~5.5 min
- Total execution time: ~37 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Annotation Phase 1 | 3/3 | 100% | ~3.5 min |
| Annotation Phase 2 | 4/4 | 100% | ~5.5 min |
| Annotation Phase 3 | 0/4 | 0% | - |

**Recent Trend:**

- Annotation Phase 1: 3/3 plans completed, 18 tests + 1 skipped pass.
- Annotation Phase 2: 4/4 plans completed, 71 annotation tests pass (47 Phase 2-specific + 18 Phase 1 + 6 flow). Zotero probe, normalization, importer, and E2E verification all built.
- Annotation Phase 3: 4 plans created, ready for execute phase.

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.1]: Incremental extraction from sync.py - adapters first, then SyncService, keeping sync.py as thin shell. No full rewrite.
- [v2.1]: Dual JSON output during contract transition - old format + new PFResult side-by-side until 2 release cycles of stability.
- [v2.1]: Plugin keeps fallback to direct index reading during PFResult transition - removed after 2 stable release cycles.
- [annotation v0.1]: Build PDF annotation as a parallel feature line from current upstream/master, not from the stale old branch directly.
- [annotation v0.1]: Import only backend/CLI annotation capabilities first; defer Obsidian PDF overlay to a later annotation milestone.
- [annotation v0.1]: Zotero SQLite is read-only input; PaperForge writes annotation state only to its own `annotations.db`.
- [annotation v0.1]: Paper-scoped imports must not mark unrelated paper annotations as stale/deleted.
- [annotation v0.1]: `annotations.db` schema source fields use generic names (source, source_library_id, etc.) - not Zotero-specific names.
- [annotation v0.1]: Annotation schema tables are defined in `paperforge.annotation.schema.ANNOTATION_TABLES`, not in `paperforge.memory.schema.ALL_TABLES`.
- [v2.1]: Tests must not be modified to pass if code is broken - tests verify contracts, not implementation convenience.
- [annotation v0.1]: Annotation Phase 2 prioritizes paper-scoped Zotero import first; lower-level code may stay extensible for full-library import later.
- [annotation v0.1]: Zotero reads default to temp-copy mode and treat imported Zotero rows as read-only PaperForge source rows.
- [annotation v0.1]: Zotero annotation identity must include source, library scope, parent item, attachment, and annotation key.
- [annotation v0.1]: Annotation CLI commands use a dedicated `paperforge annotation ...` namespace.
- [annotation v0.1]: Annotation import defaults to preview mode; writes require explicit `--apply`.
- [annotation v0.1]: Annotation JSON commands use the existing PFResult-style envelope with stable error codes for `--json` failures.

### Pending Todos

None yet.

### Blockers/Concerns

- **`test_config.py` Windows tmp_path failures**: 4 config tests fail with `PermissionError` on Windows when using the `tmp_path` pytest fixture. These are pre-existing and unrelated to annotation code; they affect all tests that create vault subdirectories in temp dirs. Not a blocker for annotation work.
- **`test_paperforge_paths_returns_exact_keys` key mismatch**: Test expects `ld_deep_script` but config returns `pf_deep_script`. Pre-existing baseline mismatch unrelated to annotation.
- **Missing `filelock` dependency**: `paperforge/memory/builder.py` transitively imports `filelock` via `worker/asset_index.py`. The `build_from_index` integration test in plan 03 is skipped due to this missing package. Direct `drop_all_tables` regression provides equivalent coverage.

## Session Continuity

Last session: 2026-06-18
Stopped at: Annotation Phase 3 planned - ready for execute phase
Resume file: Next up: `gsd-execute-phase annotation phase 3`
