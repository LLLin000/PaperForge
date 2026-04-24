# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.3 — Path Normalization & Architecture Hardening

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Milestone v1.3 initiated
Last activity: 2026-04-24 — Milestone v1.3 planning started

## Next Action

Milestone v1.3 planning in progress.

Options:
- `/gsd-discuss-phase 11` — start Phase 11 discussion
- `/gsd-plan-phase 11` — plan Phase 11 directly

## Phase 10 Decisions (Locked)

- Unified command modules in `paperforge/commands/`
- Aggressive migration: no aliases for old commands
- `paperforge sync` combines selection-sync + index-refresh
- `paperforge ocr` merges run + diagnose with `--diagnose` flag

## Open Questions

- How to handle multiple attachments per Zotero item (main PDF vs supplementary)
- Whether to archive `pipeline/` or merge into `paperforge/`
- CI platform choice (GitHub Actions vs pre-commit hooks)

---
*Initialized: 2026-04-23*
*Last updated: 2026-04-24 (Milestone v1.3 initiated)*
