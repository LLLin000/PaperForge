---
phase: annotation-02-zotero-probe-safe-import
plan: 02
type: execute
wave: 2
subsystem: annotation
tags:
  - normalization
  - zotero
  - tdd
  - dataclass
requires:
  - paperforge/annotation/errors.py — AnnotationImportError base type
  - paperforge/annotation/schema.py — annotations table column definitions
provides:
  - paperforge/annotation/zotero_normalize.py — NormalizedAnnotation + normalize_zotero_annotation
  - tests/unit/annotation/test_zotero_normalize.py — 21 normalization tests
affects:
  - Plan 03 — will consume normalize_zotero_annotation() for scoped import
tech-stack:
  added:
    - dataclasses.dataclass for NormalizedAnnotation model
    - json.dumps for compact JSON payload construction
  patterns:
    - NormalizedAnnotation dataclass maps directly to annotations table columns
    - normalize_zotero_annotation(dict, paper_id) -> NormalizedAnnotation
    - Pre-validated identity fields via _REQUIRED_IDENTITY_FIELDS frozenset
key-files:
  created:
    - paperforge/annotation/zotero_normalize.py
    - tests/unit/annotation/test_zotero_normalize.py
  modified:
    - (none)
key-decisions:
  - "Deterministic id format zotero:{library_id}:{attachment_key}:{annotation_key} encodes source + library scope + attachment + annotation"
  - "Required identity fields: library_id, annotation_key, attachment_key, type — validated early"
  - "Normalizer does NOT import from __init__.py — consistent with errors.py and zotero_probe.py pattern"
  - "Normalizer accepts enriched dict (caller resolves JOINs for identity fields) — separate of concerns"
patterns-established:
  - "NormalizedAnnotation dataclass with explicit field defaults matching schema defaults"
  - "Raw dict schema uses Zotero column names (text, pageLabel, sortIndex) — caller maps to schema names"
requirements-completed:
  - ZOT-01
  - ZOT-03
  - ZOT-05
metrics:
  duration_minutes: 4
  completed_date: "2026-06-18"
  tests_total: 21
  tests_passed: 21
  tests_failed: 0
  files_created: 2
  files_modified: 0
commits:
  - d45fca8: feat(annotation-02-02): implement Zotero annotation normalization
  - 902df17: test(annotation-02-02): add failing normalization tests
---

# Phase annotation-02 Zotero Probe & Safe Import Plan 2: Zotero Annotation Normalization

**NormalizedAnnotation dataclass and normalize_zotero_annotation() converter — maps enriched Zotero annotation rows to PaperForge source-agnostic records with deterministic identity, read-only marking, JSON payload construction, and field preservation that satisfies D-06/D-07/D-09**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-18T18:15:00Z
- **Completed:** 2026-06-18T18:19:00Z
- **Tasks:** 2 (1 TDD RED, 1 TDD GREEN)
- **Files created:** 2
- **Files modified:** 0

## Accomplishments

- **NormalizedAnnotation dataclass** — typed dataclass with all 24 fields matching the `annotations` table columns; Zotero-sourced defaults (is_readonly=1, sync_state="imported", source="zotero")
- **normalize_zotero_annotation() converter** — validates required identity fields, builds deterministic PaperForge id `zotero:{library_id}:{attachment_key}:{annotation_key}`, maps Zotero fields to schema columns, constructs compact JSON for tags/position/selector
- **21 TDD tests** — covering identity field preservation, deterministic id generation (same-library collision, cross-library uniqueness), content field passthrough, JSON payload validity, read-only marking, error handling for 4 missing-field scenarios, empty tags, type passthrough, timestamps, deleted_at default

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing normalization tests (TDD RED)** — `902df17` (test)
2. **Task 2: Implement normalized annotation model and converter (TDD GREEN)** — `d45fca8` (feat)

**Plan metadata:** Pending after SUMMARY.md commit.

## Files Created/Modified

- `paperforge/annotation/zotero_normalize.py` — NormalizedAnnotation dataclass (24 fields), normalize_zotero_annotation() function with identity validation, JSON construction, and field mapping logic
- `tests/unit/annotation/test_zotero_normalize.py` — 21 test cases covering all normalization contracts

## Decisions Made

1. **Normalizer accepts enriched dict, not bare sqlite3.Row** — The caller (Plan 03 importer) is responsible for resolving JOINs across Zotero tables to populate identity fields (`library_id`, `annotation_key`, `attachment_key`, `parent_key`). The normalizer validates and transforms; it doesn't do DB lookups. This keeps responsibilities separated and makes the normalizer trivially testable.

2. **Normalizer NOT exported from `__init__.py`** — Consistent with the existing pattern for `errors.py` and `zotero_probe.py`, the normalizer is imported directly from its module. No re-export through `paperforge.annotation.__init__`.

3. **Required identity fields validation** — `library_id`, `annotation_key`, `attachment_key`, and `type` are all validated as non-empty before any processing. Missing values raise `AnnotationImportError` with a clear message naming the missing field.

4. **Zotero type is passed through as-is** — The annotations schema uses a free-form TEXT type column, so Zotero's native types (highlight, note, underline, ink, etc.) are preserved unmodified.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

```
FOUND: paperforge/annotation/zotero_normalize.py
FOUND: tests/unit/annotation/test_zotero_normalize.py
FOUND: 902df17
FOUND: d45fca8
```

All created files exist on disk. Both commit hashes are present in git log.

## Threat Flags

None. The normalization module is a pure function with no network endpoints, auth paths, file access, or schema mutations.

## Next Phase Readiness

- `normalize_zotero_annotation()` is ready for Plan 03 (scoped import reconciliation) to consume.
- Plan 03 can import the normalizer and pass enriched Zotero rows from the probe layer.
- 31 annotation tests pass (21 normalization + 10 probe), providing a stable regression baseline for Plan 03.
