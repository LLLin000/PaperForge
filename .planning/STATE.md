# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.3 — Path Normalization & Architecture Hardening

## Current Position

Phase: 11 (executing)
Plan: 11-PLAN.md (8 tasks, 4 waves)
Status: Wave 1 complete (Tasks 01-02 done), Wave 2 pending
Last activity: 2026-04-24 — Wave 1 executed: Task 01 (_normalize_attachment_path) + Task 02 (_identify_main_pdf)

## Next Action

Phase 11: Zotero Path Normalization — Wave 2 ready (Tasks 03-04: Wikilink Generation & Multi-Attachment Frontmatter)

Options:
- `/gsd-execute-phase 11` — continue execution (Task 03-08)
- Review `.planning/phases/11-zotero-path-normalization/11-SUMMARY.md` for Wave 1 results

## Completed in Wave 1

- Task 01: `_normalize_attachment_path()` handles absolute Windows, storage:, and bare relative paths
- Task 02: `_identify_main_pdf()` with hybrid strategy (title==PDF → largest size → shortest title)
- New frontmatter fields: `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `supplementary`
- Commits: `2939b86`, `7e7dbe1`

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
*Last updated: 2026-04-24 (Milestone v1.3 initiated)*
