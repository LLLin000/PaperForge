# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-25)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.4 — Code Health & UX Hardening

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-25 — Milestone v1.4 started



- Unified command modules in `paperforge/commands/`
- Aggressive migration: no aliases for old commands
- `paperforge sync` combines selection-sync + index-refresh
- `paperforge ocr` merges run + diagnose with `--diagnose` flag

## Phase 11 Decisions (Locked)

- D-01 through D-08: Documented in ADR-011
- `storage:` prefix as unified internal representation for Zotero storage paths
- Hybrid main PDF selection (title -> size -> shortest title)
- Forward slashes exclusively in wikilinks (`Path.as_posix()`)
- `path_error` frontmatter field for explicit error tracking

## Open Questions

- [x] How to handle multiple attachments per Zotero item (main PDF vs supplementary) — **Resolved in Task 02**
- [x] Whether `storage:` prefix should include implicit `storage/` segment — **Deferred to Phase 12**
- CI platform choice (GitHub Actions vs pre-commit hooks)

## Phase 12 Decisions (Locked)

- Migrated 4041-line `literature_pipeline.py` into 7 focused modules under `paperforge/worker/`
- `paperforge/worker/sync.py` contains utilities + sync functions (selection-sync, index-refresh)
- `paperforge/worker/ocr.py` contains OCR queue and post-processing
- `paperforge/worker/repair.py`, `status.py`, `deep_reading.py`, `update.py`, `base_views.py` for respective domains
- `skills/literature-qa/` migrated to `paperforge/skills/literature-qa/`
- Function-level imports used to break circular dependencies between sync.py and ocr.py
- Module-reference imports (`_sync.run_selection_sync`) used in ocr.py to maintain test patch compatibility
- Old `pipeline/` and `skills/` directories removed after confirming zero import references

## Accumulated Context

### Phase 10 Decisions (Locked)
- Unified command modules in `paperforge/commands/`
- Aggressive migration: no aliases for old commands
- `paperforge sync` combines selection-sync + index-refresh
- `paperforge ocr` merges run + diagnose with `--diagnose` flag

### Phase 11 Decisions (Locked)
- D-01 through D-08: Documented in ADR-011
- `storage:` prefix as unified internal representation for Zotero storage paths
- Hybrid main PDF selection (title -> size -> shortest title)
- Forward slashes exclusively in wikilinks (`Path.as_posix()`)
- `path_error` frontmatter field for explicit error tracking

### Phase 12 Decisions (Locked)
- Migrated 4041-line `literature_pipeline.py` into 7 focused modules under `paperforge/worker/`
- Function-level imports used to break circular dependencies between sync.py and ocr.py
- Module-reference imports (`_sync.run_selection_sync`) used in ocr.py for test patch compatibility
- Old `pipeline/` and `skills/` directories removed after confirming zero import references

### Open Questions (carried forward)
- CI platform choice (GitHub Actions vs pre-commit hooks)
- Whether `storage:` prefix should include implicit `storage/` segment

---\n*Initialized: 2026-04-23*\n*Last updated: 2026-04-25 (Milestone v1.4 started)*
