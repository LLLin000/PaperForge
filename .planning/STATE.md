# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.3 — Path Normalization & Architecture Hardening

## Current Position

Phase: 11 (executing)
Plan: 11-PLAN.md (8 tasks, 4 waves)
Status: Wave 3 complete (Tasks 01-06 done), Wave 4 pending
Last activity: 2026-04-24 — Wave 3 executed: Task 05 (doctor path resolution checks) + Task 06 (repair/status path_error integration)

## Next Action

Phase 11: Zotero Path Normalization — Wave 4 ready (Tasks 07-08: Tests, Docs & Verification)

Options:
- `/gsd-execute-phase 11` — continue execution (Tasks 07-08)
- Review `.planning/phases/11-zotero-path-normalization/11-SUMMARY.md` for Wave 3 results

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

## Phase 10 Decisions (Locked)

- Unified command modules in `paperforge/commands/`
- Aggressive migration: no aliases for old commands
- `paperforge sync` combines selection-sync + index-refresh
- `paperforge ocr` merges run + diagnose with `--diagnose` flag

## Open Questions

- [x] How to handle multiple attachments per Zotero item (main PDF vs supplementary) — **Resolved in Task 02**
- Whether to archive `pipeline/` or merge into `paperforge/`
- CI platform choice (GitHub Actions vs pre-commit hooks)

---
*Initialized: 2026-04-23*
*Last updated: 2026-04-24 (Wave 2 complete)*
