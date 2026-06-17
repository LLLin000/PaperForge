---
phase: annotation-02-zotero-probe-safe-import
plan: 04
type: execute
subsystem: annotation
tags:
  - zotero-probe
  - safe-import
  - e2e-tests
  - verification
dependency:
  requires:
    - annotation-02-03
  provides:
    - Flow regression tests for probe-normalize-import pipeline
    - Phase 2 verification documentation
  affects:
    - tests/unit/annotation/test_zotero_import_flow.py
tech-stack:
  added: []
  patterns:
    - Flow-level integration testing across module boundaries
    - Minimal Zotero SQLite fixtures for two-paper scope isolation
    - Schema-error-before-mutation safety pattern
key-files:
  created:
    - tests/unit/annotation/test_zotero_import_flow.py
    - .planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md
decisions:
  - Safety pattern: probe schema BEFORE calling importer (caller responsibility)
  - Unknown schema test validates no annotation data rows are inserted,
    even though ensure_schema() may create empty PaperForge tables
  - Flow tests use higher-level scenarios distinct from existing unit tests
metrics:
  duration: "~15min"
  completed_date: "2026-06-18"
  flow_tests: 6
  total_annotation_tests: 71
  annotation_tests_passed: 71
  annotation_tests_failed: 0
---

# Phase annotation-02-04: End-to-End Import Flow Verification

**End-to-end probe-normalize-import flow tests + Phase 2 verification documentation.**

This plan added 6 flow-level integration tests that exercise the full pipeline from Zotero SQLite snapshot through probe, normalisation, and paper-scoped import into `annotations.db`. These cover the critical safety and correctness invariants that individual unit tests do not: scope isolation across papers, schema-error-before-mutation ordering, and snapshot lifecycle.

A comprehensive `annotation-02-VERIFICATION.md` documents the Phase 2 verification results, confirming all 8 requirements satisfied and no Zotero write-back path exists.

## Tasks Executed

### Task 1: End-to-End Import Flow Tests (`type=tdd`)

**Created:** `tests/unit/annotation/test_zotero_import_flow.py`

Six test scenarios cover the full flow:

| # | Test | Covers | Result |
|---|------|--------|--------|
| 1 | `test_flow_probe_finds_schema_in_snapshot` | Snapshot → open → probe discovers all 5 required tables | PASS |
| 2 | `test_flow_full_import_creates_rows` | Full pipeline produces 2 rows for Paper A | PASS |
| 3 | `test_flow_content_fields_preserved` | Text, comment, color, page, tags, position JSON, modified time survive | PASS |
| 4 | `test_flow_reimport_does_not_stale_other_paper` | Re-importing Paper A does not stale-mark Paper B's rows | PASS |
| 5 | `test_flow_unknown_schema_fails_before_mutation` | `ZoteroSchemaError` raised before any annotation data rows inserted | PASS |
| 6 | `test_flow_snapshot_cleanup` | Temp snapshot deleted after context exit (success path) | PASS |

> **Deviation (Rule 1 — Bug fix):** Test 5 originally tried to call `import_zotero_annotations_for_paper` directly on an unknown schema, which hits `sqlite3.OperationalError` (not `ZoteroSchemaError`) because the importer delegates schema probing to the caller. Fixed by restructuring to follow the safe pattern: caller probes schema first, then imports only if probe succeeds. The `ZoteroSchemaError` is raised before the importer's `ensure_schema` call, guaranteeing no annotation data mutation. Windows `PermissionError` during snapshot cleanup was also fixed by closing the Zotero connection before the context manager exits.

**Commit:** `870366b`

### Task 2: Phase 2 Verification (`type=auto`)

**Created:** `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md`

Verification commands and results:

| Command | Result |
|---------|--------|
| `python -m pytest tests/unit/annotation/test_zotero_probe.py test_zotero_normalize.py test_importer.py test_zotero_import_flow.py -q` | **53 passed** |
| `python -m pytest tests/unit/annotation -q` | **71 passed, 1 skipped** |
| `python -m compileall paperforge/annotation` | **No errors** (7 modules) |

Verification confirms:
- **SAFE-04:** No Zotero write-back path — all `zotero_conn.execute()` calls are read-only SELECT queries; all INSERT/UPDATE/DELETE target PaperForge's own `annotations.db`
- **D-01:** Scope boundary respected — CLI, overlay, editor, evidence integration deferred
- All 8 Phase 2 requirements (ZOT-01 through ZOT-05, SAFE-01/02/04) satisfied
- Unrelated baseline failures documented separately

**Commit:** `4897609`

## Deviations from Plan

### Rule 1 — Bug fix: Unknown schema test restructured

- **Found during:** Task 1 RED phase
- **Issue:** Calling `import_zotero_annotations_for_paper` directly on a DB with unknown schema raised `sqlite3.OperationalError` (no such table), not `ZoteroSchemaError`. The importer's schema probe is a caller responsibility, not inline in the import function.
- **Fix:** Restructured test to use the correct safety pattern: probe schema first, then import only if probe succeeds. The `ZoteroSchemaError` is raised during the probe phase, and the importer is never called — guaranteeing no annotation data mutation in `annotations.db`.
- **Files modified:** `tests/unit/annotation/test_zotero_import_flow.py`
- **Commit:** `870366b`

### Rule 1 — Bug fix: Windows snapshot cleanup PermissionError

- **Found during:** Task 1 RED phase (when the OperationalError was raised, the Zotero connection wasn't closed before the snapshot context manager tried to unlink the temp file)
- **Issue:** On Windows, a SQLite connection holding a file handle prevents file deletion with `PermissionError`.
- **Fix:** Restructured the test to close the Zotero connection (`zconn.close()`) before the `zotero_snapshot` context manager exits, ensuring the temp file is not locked.
- **Files modified:** `tests/unit/annotation/test_zotero_import_flow.py`
- **Commit:** `870366b`

## Known Stubs

None. The flow tests exercise real SQLite databases and real module imports — no stubs or mocks.

## Threat Flags

No new threat surface. The flow tests exercise existing probe/normalize/importer code through the same temp-copy read-only paths. No new network endpoints, auth paths, or file access patterns introduced.

## Self-Check: PASSED

- File `tests/unit/annotation/test_zotero_import_flow.py` — **FOUND** (533 lines, 6 tests)
- File `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-VERIFICATION.md` — **FOUND** (126 lines)
- Commit `870366b` — **FOUND** `test(annotation-02-04): add end-to-end Zotero import flow tests`
- Commit `4897609` — **FOUND** `docs(annotation-02-04): add Phase 2 verification results`
