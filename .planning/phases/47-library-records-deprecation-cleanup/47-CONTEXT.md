# Phase 47: Library-Records Deprecation Cleanup - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Zero library-records references remain in production code (status.py, sync.py, ld_deep.py), documentation (5 command skill files), or user-facing labels. Dead code removed, stale scan paths corrected, post-install instructions updated to single-command workflow.

Requirements: LEGACY-01 through LEGACY-07.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — infrastructure/cleanup phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Known code context:
- `status.py:525-533` — stale-record detection scans `<control>/library-records/` explicitly
- `status.py:728` — output label uses `library_records` instead of `formal_notes`
- `sync.py:722-723` — dead `record_path` construction and `parse_existing_library_record()` call
- `sync.py:652-669` — function with no other callers
- `ld_deep.py:39` — unused `records` key in return dict
- `ld_deep.py:32` — stale docstring
- `repair.py:33` — docstring says "library-records"
- `setup_wizard.py:1306-1307` — post-install text describes two-phase flow
- 5 command skill files (`pf-sync.md`, `pf-ocr.md`, `pf-status.md`, `pf-paper.md`, `pf-deep.md`) — library-records references
- `sync.py:1557-1562,1759` — hardcoded `"Literature/"` in docstrings/print labels
- `discussion.py:94` — hardcoded `"Literature/"` in label

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/worker/status.py` — status reporting and doctor checks
- `paperforge/worker/sync.py` — sync orchestration
- `paperforge/worker/ld_deep.py` — deep reading path provider
- `paperforge/worker/repair.py` — divergence detection
- `paperforge/worker/setup_wizard.py` — setup and post-install text
- `paperforge/worker/discussion.py` — AI discussion recorder

### Established Patterns
- grep/rg for finding residual references, docstring-first cleanup pattern
- Commands stored in agent_skills/ or similar skill directory

</code_context>

<specifics>
No specific requirements — infrastructure phase.

</specifics>

<deferred>
None

</deferred>
