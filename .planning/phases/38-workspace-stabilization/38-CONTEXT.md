# Phase 38: Workspace Stabilization - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Workspace directories are created directly on first sync (no flat-first-then-migrate); fulltext content is bridged from OCR output to workspace fulltext.md; path construction unified across discussion.py and canonical index.

Key references:
- `_build_entry()` in asset_index.py — currently creates workspace only when workspace_dir.exists(); needs to create workspace for new papers too
- `migrate_to_workspace()` in sync.py — copies flat note to workspace; needs fulltext bridging
- `discussion.py` — builds ai/ path independently; should read from index entry
- `paperforge/worker/status.py` — doctor checks; needs WS-05 workspace integrity validation
</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices at agent's discretion — pure infrastructure phase.

### Key Constraints
- fulltext_path is declared in _build_entry() but never populated — MUST create bridge after OCR
- discussion.py path construction MUST be unified: read ai_path from canonical index entry
- Doctor check: workspace dir exists for indexed papers; fulltext.md exists when ocr_status=done
- Must NOT break existing migrated papers (idempotency)
</decisions>

<code_context>
## Key Files

- `paperforge/worker/asset_index.py` — `_build_entry()` lines ~317-332: workspace-or-flat branching logic
- `paperforge/worker/sync.py` — `migrate_to_workspace()` lines ~1677-1749: flat-to-workspace migration
- `paperforge/worker/discussion.py` — path construction for ai/ directory
- `paperforge/worker/paper_meta.py` — new Phase 37 module, can extend for workspace validation
- `paperforge/worker/status.py` — `run_status()` for doctor workspace checks

</code_context>

<specifics>
## Specific Ideas

- fulltext bridge: in OCR worker (ocr.py) or in run_index_refresh(), when ocr_status=done and workspace exists, copy `<system_dir>/PaperForge/ocr/{key}/fulltext.md` to `workspace_dir/fulltext.md`
- New paper workspace creation: in _build_entry(), create workspace_dir unconditionally for all papers (remove the `if workspace_dir.exists()` check, always mkdir)
- discussion.py refactor: compute ai_path from canonical index entry's ai_path field instead of rebuilding path from zotero_key + title
- migrate_to_workspace: after copying note, check if ocr meta exists and copy fulltext.md if available
</specifics>

<deferred>
## Deferred Ideas

None — all planned for this phase per ROADMAP.
</deferred>
