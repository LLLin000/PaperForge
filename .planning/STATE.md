# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.3 — Path Normalization & Architecture Hardening

## Current Position

Phase: 11 (context gathered)
Plan: —
Status: Phase 11 discussion complete, ready for planning
Last activity: 2026-04-24 — Phase 11 context captured (6 gray areas, 8 decisions)

## Next Action

Phase 11: Zotero Path Normalization — Context gathered. Ready for planning.

Options:
- `/gsd-plan-phase 11` — create execution plan
- `/gsd-research-phase 11` — research implementation patterns first
- Review/edit `.planning/phases/11-zotero-path-normalization/11-CONTEXT.md`

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
