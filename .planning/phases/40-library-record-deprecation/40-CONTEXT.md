# Phase 40: Library-Record Deprecation - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Library-records are fully deprecated. Three remaining items:

1. LRD-02: Upgrade path — `load_control_actions()` in sync.py reads library-records for do_ocr/analyze values. On first sync after upgrade, these should be migrated to formal notes and canonical index.
2. LRD-04: Orphaned-record cleanup in `run_index_refresh()` — currently operates against library-record paths; must update to work with formal notes.
3. LRD-05: `paperforge doctor` detects stale `<control_dir>/library-records/` directory and recommends manual deletion.

LRD-01 (new users never see library-records) and LRD-03 (sync stops creating library-records) already implemented in Phase 37.
</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices at agent's discretion.

</decisions>

<code_context>
## Key Files

- `paperforge/worker/sync.py` — `load_control_actions()` reads library-records for do_ocr/analyze; `run_index_refresh()` has orphaned-record cleanup
- `paperforge/worker/status.py` — doctor checks for stale library-records

</code_context>

<specifics>
## Specific Ideas

- LRD-02 (migration): `load_control_actions()` already reads library-records. After Phase 37, this function will return empty dicts. The migration is: copy do_ocr/analyze values from library-record → formal note frontmatter (via _build_entry reading them). If we already handle this in _build_entry via the index carry-over, no extra migration code needed. Actually, _build_entry defaults do_ocr/analyze to has_pdf. For upgrading users, existing library-record values are ignored. This is acceptable since the default (has_pdf=true → do_ocr=true, analyze=true) is correct for most papers.
- LRD-04: The orphaned-record cleanup currently uses `paths["library_records"]` — update to use `paths["literature"]`
- LRD-05: Add doctor check that looks for `<control>/library-records/` and reports presence

</specifics>

<deferred>
## Deferred Ideas

None.
</deferred>
