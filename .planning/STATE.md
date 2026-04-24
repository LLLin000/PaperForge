# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.3 — Path Normalization & Architecture Hardening (Phase 12 IN PROGRESS)

## Current Position

Phase: 12 (IN PROGRESS)
Plan: 12-PLAN.md (11 tasks, 5 waves)
Status: Planning complete, ready for execution
Last activity: 2026-04-24 — Phase 12 context, discussion, and plan committed (cfe0b6a)

## Next Action

Phase 12: Architecture Cleanup — Execute Wave 1 (package structure + sync/ocr migration)

Options:
- `/gsd-execute-phase 12` — begin Phase 12 execution
- Review `.planning/phases/12-architecture-cleanup/12-PLAN.md` for full plan

## Completed in Wave 1

- Task 01: `_normalize_attachment_path()` handles absolute Windows, storage:, and bare relative paths
- Task 02: `_identify_main_pdf()` with hybrid strategy (title==PDF -> largest size -> shortest title)
- New frontmatter fields: `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `supplementary`
- Commits: `2939b86`, `7e7dbe1`

## Completed in Wave 2

- Task 03: `obsidian_wikilink_for_pdf()` rewritten with `zotero_dir` parameter and junction resolution
- Task 04: `run_selection_sync()` updated to pass all new fields to `library_record_markdown()`
- `absolutize_vault_path()` gains `resolve_junction` parameter (D-05)
- `library_record_markdown()` emits `pdf_path`, `supplementary` as wikilink strings
- `path_error` only emitted when non-empty
- Commits: `adf349e`

## Completed in Wave 3

- Task 05: `paperforge doctor` enhanced with "Path Resolution" section
  - `check_zotero_location()`: detects Zotero inside/outside vault, recommends exact `mklink /J` command
  - `check_pdf_paths()`: samples 5 items, validates wikilinks resolve to files
  - `check_wikilink_format()`: verifies all `pdf_path` values use `[[...]]` format
- Task 06: `path_error` integrated with repair and status commands
  - `paperforge repair` detects `path_error` fields, reports summary counts by type
  - `--fix-paths` flag added to re-resolve failed paths
  - `paperforge status` shows path error count and suggests `repair --fix-paths`
  - `repair_pdf_paths()` function re-runs path normalization on items with errors
- Commits: `bdbaca4`, `434660c`

## Completed in Wave 4

- Task 07: `tests/test_path_normalization.py` with 25 test methods
  - TestBBTPathNormalization: 8 tests (absolute Windows, storage:, bare, Chinese, spaces, etc.)
  - TestMainPdfIdentification: 6 tests (title=PDF, largest, first, none, single, mixed)
  - TestWikilinkGeneration: 6 tests (basic, junction, slashes, Chinese, empty, nonexistent)
  - TestLoadExportRowsIntegration: 5 tests using fixture JSON files
  - Fixtures: `bbt_export_absolute.json`, `bbt_export_storage.json`, `bbt_export_mixed.json`
- Task 08: Documentation and verification
  - AGENTS.md: Added "Path Resolution" section with BBT format table, wikilink rules, junction setup, multi-attachment handling
  - AGENTS.md: Updated Library Record frontmatter with new fields (`pdf_path`, `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `supplementary`, `path_error`)
  - docs/ARCHITECTURE.md: Added ADR-011 documenting D-01 through D-08
  - Consistency audit: 4/4 passing
  - Created `11-VERIFICATION.md` with test results and sample library-record
- Commits: `72cbdc3`, `13e548d`

## Phase 10 Decisions (Locked)

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

---
*Initialized: 2026-04-23*
*Last updated: 2026-04-24 (Wave 4 complete, Phase 11 done)*
