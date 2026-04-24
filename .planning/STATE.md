# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.3 — Path Normalization & Architecture Hardening

## Current Position

Phase: 11 (executing)
Plan: 11-PLAN.md (8 tasks, 4 waves)
Status: Wave 2 complete (Tasks 01-04 done), Wave 3 pending
Last activity: 2026-04-24 — Wave 2 executed: Task 03 (obsidian_wikilink_for_pdf rewrite) + Task 04 (frontmatter field updates)

## Next Action

Phase 11: Zotero Path Normalization — Wave 3 ready (Tasks 05-06: Doctor Integration & Error Handling)

Options:
- `/gsd-execute-phase 11` — continue execution (Task 05-08)
- Review `.planning/phases/11-zotero-path-normalization/11-SUMMARY.md` for Wave 2 results

## Completed in Wave 1

- Task 01: `_normalize_attachment_path()` handles absolute Windows, storage:, and bare relative paths
- Task 02: `_identify_main_pdf()` with hybrid strategy (title==PDF → largest size → shortest title)
- New frontmatter fields: `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `supplementary`
- Commits: `2939b86`, `7e7dbe1`

## Completed in Wave 2

- Task 03: `obsidian_wikilink_for_pdf()` rewritten with `zotero_dir` parameter and junction resolution
- Task 04: `run_selection_sync()` updated to pass all new fields to `library_record_markdown()`
- `absolutize_vault_path()` gains `resolve_junction` parameter (D-05)
- `library_record_markdown()` emits `pdf_path`, `supplementary` as wikilink strings
- `path_error` only emitted when non-empty
- Commits: `adf349e`

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
