# Phase 42: Core Pipeline Fix - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Infrastructure phase (discuss skipped)

<domain>
## Phase Boundary

OCR, status, and sync workers read workflow state (do_ocr, analyze, ocr_status) from formal note frontmatter — same logic as the existing `get_analyze_queue()` pattern. Core workflow unbroken for new papers created post-v1.9.

Requirements: WF-01, WF-02, WF-03, WF-04, SYN-01, SYN-02, SYN-03

Success criteria:
1. Running `paperforge ocr` finds and processes papers whose formal note frontmatter has `do_ocr: true` — no library-records reads
2. `auto_analyze_after_ocr` writes `analyze: true` into the formal note frontmatter
3. `paperforge status` reports counts from formal notes + canonical index
4. `paperforge status` doctor checks sample from formal notes
5. `paperforge sync` no longer creates empty library-records directories; `load_control_actions()` scans formal note frontmatter
6. Orphaned formal notes cleaned up from Literature/ directory during sync

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase.

Key constraints:
- **do_ocr read**: Must follow the same `get_analyze_queue()` pattern as analyze — direct formal note frontmatter scan, NOT canonical index (which lags behind user frontmatter edits).
- **load_control_actions()**: Rewrite to scan Literature/ for frontmatter patterns instead of library-records. This function is consumed by both OCR and repair workers.
- **auto_analyze_after_ocr**: Currently writes to library-record files — must write to formal note frontmatter instead.
- **orphan cleanup**: Currently targets library-records directory — must target Literature/ instead.
- **Status counts**: Currently count library-records for do_ocr/path stats — must read from formal notes + canonical index.
- **No new test files needed**: All changes are re-wiring existing logic to new data sources.

</decisions>

<code_context>
## Existing Code Insights

### Key Files to Modify

- `paperforge/worker/sync.py` — `load_control_actions()` (lines 672-684), `run_selection_sync()` (dir creation at 709-710), orphan cleanup (lines 1664-1708)
- `paperforge/worker/ocr.py` — `auto_analyze_after_ocr` (lines 1616-1627), OCR job loop (lines 1480-1481)
- `paperforge/worker/status.py` — `run_status()` (lines 600-667, 720), doctor checks (lines 125, 167)

### Existing Pattern to Follow
- `_utils.py` `get_analyze_queue()` — scans Literature/ frontmatter with regex for analyze/do_ocr/ocr_status
- `_read_frontmatter_bool()` in `asset_index.py` — reads boolean from .md frontmatter with tolerance for quotes/spacing
- `_build_entry()` in `asset_index.py` — workspace path construction

</code_context>

<specifics>
No specific requirements — infrastructure phase.

</specifics>

<deferred>
None.

</deferred>
