# Phase 59: State Machine & Field Registry - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Formalized state machine with explicit enums and allowed transitions, plus a field registry that `paperforge doctor` can validate against:

1. `paperforge/core/state.py` — PdfStatus, OcrStatus, and Lifecycle enums with explicit string values mapping to all existing state strings in the codebase
2. ALLOWED_TRANSITIONS table defining legal state migrations — workers validate before writing
3. `paperforge/schema/field_registry.yaml` — defines every field (frontmatter, index, meta.json) with metadata
4. Doctor field completeness checks — missing required fields detected, drift detected
</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Refer to ROADMAP phase goal, success criteria, and existing codebase conventions.

### Prior Decisions
- ErrorCode enum in paperforge/core/errors.py from Phase 57 (available for worker error classification)
- PFResult from Phase 57 for doctor --json output
</decisions>

<code_context>
## Existing State Patterns

### Lifecycle States (from asset_state.py, asset_index.py)
- `pdf_ready` — has PDF, OCR not done
- `ocr_ready` — OCR validated done
- `analyze_ready` — analysis pending (default successor to ocr_ready)
- `deep_read_done` — deep reading complete
- `error_state` — error condition
- `indexed` — indexed state

### OCR Status (from workers, frontmatter)
- `pending` — OCR not started
- `processing` — OCR in progress
- `done` — OCR completed
- `failed` — OCR failed

### PDF Status (from dashboard.py)
- `healthy` — PDF accessible
- `broken` — PDF missing/broken path
- `missing` — no PDF at all

### Deep Reading Status (from frontmatter, ld_deep.py)
- `pending` — not started
- `done` — completed

### Field-Carrying Structures
1. Formal note frontmatter (~16 fields): zotero_key, domain, title, year, doi, collection_path, has_pdf, pdf_path, supplementary, fulltext_md_path, recommend_analyze, analyze, do_ocr, ocr_status, deep_reading_status, path_error
2. Canonical index entries (formal-library.json): all frontmatter fields + derived lifecycle/health/maturity
3. OCR meta.json: ocr_status, error
4. paper-meta.json: OCR backend data, derived state details

### Existing Resources
- `paperforge/core/` already has `__init__.py`, `errors.py`, `result.py` from Phase 57
- `paperforge/worker/asset_state.py` — existing lifecycle computation logic (compute_lifecycle function)
- `paperforge/worker/asset_index.py:577-657` — summary/index logic with lifecycle counts
- `paperforge/worker/status.py:440-469` — existing doctor checks (package versions) — extend for field registry

</code_context>

<specifics>
## Specific Ideas

### State Values
- OcrStatus: PENDING, PROCESSING, DONE, FAILED
- PdfStatus: HEALTHY, BROKEN, MISSING
- Lifecycle: PDF_READY, OCR_READY, ANALYZE_READY, DEEP_READ_DONE, ERROR_STATE

### Allowed Transitions
- ocr_status: pending → processing → done/failed; done → pending (re-run)
- deep_reading_status: pending → done; done → pending (with --force)
- lifecycle: pdf_ready → ocr_ready → analyze_ready → deep_read_done; any → error_state

### Field Registry
- Must cover formal note frontmatter fields, canonical index fields, ocr meta.json fields
- Each field has: name, type, required, public, owner, description

</specifics>

<deferred>
## Deferred Ideas

- None — infrastructure phase.

</deferred>
