# Phase 39: Base View Fix - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Update base_views.py to remove ghost fields (lifecycle/maturity_level/next_step), restore workflow flags (has_pdf/do_ocr/analyze/ocr_status), change folder filter from LiteratureControl/ to Literature/, and regenerate .base files on next sync.

Key decisions already made:
- Ghost fields (lifecycle/maturity_level/next_step) removed from Base properties — dashboard-owned
- Workflow flags restored: has_pdf, do_ocr, analyze, ocr_status — these are user-actionable
- Folder filter: Literature/<domain> not LiteratureControl/library-records/<domain>
- 8 workflow views keep master version's workflow filter logic (do_ocr=true, analyze=true, ocr_status=pending, etc.)
</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
Implementation details at agent's discretion. Reference vault (D:\L\Med\Research_LitControl_Sandbox) has the correct Base view template.

</decisions>

<code_context>
## Key Files

- `paperforge/worker/base_views.py` — `_generate_views()`, `_build_base_yaml()`, `PROPERTIES_YAML`
- `tests/test_base_views.py` — Base view generation tests
- `tests/test_base_preservation.py` — Base file preservation/update tests

</code_context>

<specifics>
## Specific Ideas

- Properties YAML: replace lifecycle/maturity_level/next_step with has_pdf/do_ocr/analyze/ocr_status
- Folder filter: change from `<control_dir>/<domain>` to `<literature_dir>/<domain>`
- Views: use workflow filter logic matching master version (not lifecycle-based)
- The current feature branch generated views with lifecycle-based filters — revert to workflow-gate approach

</specifics>

<deferred>
## Deferred Ideas

None — all Base view fixes in this phase.
</deferred>
