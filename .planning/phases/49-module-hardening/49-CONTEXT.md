# Phase 49: Module Hardening - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

New modules built during v1.6-v1.8 (discussion.py, asset_state.py, main.js) have production-grade safety guards: file locking prevents concurrent write corruption, markdown special characters are escaped, timestamps use UTC, API keys pass via environment not CLI args, DOM rendering avoids XSS vectors, and empty-state outputs are safe JSON.

Requirements: HARDEN-01 through HARDEN-07.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — infrastructure/hardening phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Known code context:
- `discussion.py:281-314` — file-level locking for JSON/MD read-modify-write
- `discussion.py:170-171` — Markdown special character escaping in QA fields
- `discussion.py:40` — hardcoded CST (UTC+8) → UTC
- `main.js:2116` — PaddleOCR API key passed via CLI arg → via env var
- `main.js:1815` — `innerHTML` → `createEl()` for directory tree rendering
- `asset_state.py:225-226` — workspace integrity checks before `/pf-deep`
- `status.py:687-690` — lifecycle_level_counts, health_aggregate, maturity_distribution → empty dicts not null

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `paperforge/worker/discussion.py` — AI discussion recorder
- `paperforge/plugin/main.js` — Obsidian plugin
- `paperforge/worker/asset_state.py` — next-step & maturity logic
- `paperforge/worker/status.py` — status reporting

### Established Patterns
- File locking: `fcntl` (Linux) / `msvcrt` (Windows) or `filelock` library
- API key handling: `.env` pattern via `os.environ`
- DOM manipulation: Obsidian's `createEl()` API

</code_context>

<specifics>
No specific requirements — infrastructure phase.

</specifics>

<deferred>
None

</deferred>
