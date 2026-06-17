# Annotation Phase 2 Verification: Zotero Probe and Safe Import

**Verification date:** 2026-06-18
**Scope:** Zotero SQLite probe (temp-copy, schema validation), annotation normalisation, paper-scoped import/reconciliation, end-to-end flow integration.

---

## Commands Run

### 1. Targeted Phase 2 test suite

```powershell
python -m pytest tests/unit/annotation/test_zotero_probe.py tests/unit/annotation/test_zotero_normalize.py tests/unit/annotation/test_importer.py tests/unit/annotation/test_zotero_import_flow.py -q
```

**Result:** 53 passed, 0 failed, 1 warning (pytest cache — unrelated)

### 2. Full annotation test directory

```powershell
python -m pytest tests/unit/annotation -q
```

**Result:** 71 passed, 1 skipped, 0 failed, 1 warning
- The 1 skip is `test_rebuild_isolation.py::test_memory_rebuild_does_not_drop_annotations_db` — skipped because memory rebuild fixtures are not available in this test context. This is expected and documented in Phase 1.

### 3. Compile check

```powershell
python -m compileall paperforge/annotation
```

**Result:** No errors. All 7 modules compile cleanly.

---

## Pass / Fail Summary

| Test file | Tests | Passed | Failed | Skipped |
|-----------|-------|--------|--------|---------|
| `test_zotero_probe.py` | 9 | 9 | 0 | 0 |
| `test_zotero_normalize.py` | 20 | 20 | 0 | 0 |
| `test_importer.py` | 17 | 17 | 0 | 0 |
| `test_zotero_import_flow.py` | 6 | 6 | 0 | 0 |
| `test_db.py` | 2 | 2 | 0 | 0 |
| `test_schema.py` | 12 | 12 | 0 | 0 |
| `test_rebuild_isolation.py` | 1 | 0 | 0 | 1 |
| `test_annotation_package.py` | 4 | 4 | 0 | 0 |

**All Phase 2-targeted tests pass with no failures.**

---

## Safety Confirmation: No Zotero Write-Back Path

Per requirement **SAFE-04**: a code-path audit confirms:

| Check | Result |
|-------|--------|
| `zotero_conn.execute()` calls in annotation package | All are **SELECT** queries (item key resolution, tag lookups) |
| `INSERT`/`UPDATE`/`DELETE` in `paperforge/annotation/*.py` | All target PaperForge's own `annotations.db` — never Zotero |
| `open_zotero_readonly()` mode | Uses SQLite URI `mode=ro&immutable=1` — engine-level write prevention |
| `zotero_snapshot()` safety | Copies to temp file; temp file deleted on context exit, even on error |
| No `zotero_conn.commit()` anywhere | Confirmed — no commit call on Zotero connections |
| No `sync_queue` write-back logic | `sync_queue` table exists but has **no write-back code** (placeholder only) |

**Verdict: SAFE-04 satisfied. No code path writes to Zotero SQLite.**

---

## Scope Boundary Confirmation

Per decision **D-01**, the following are intentionally **out of scope** for Phase 2:

- ❌ `paperforge annotation ...` CLI commands — deferred to Phase 3
- ❌ Obsidian plugin UI / Dashboard annotation views — deferred to future annotation milestone
- ❌ PDF overlay rendering (highlights on PDF pages) — deferred
- ❌ Editing annotations inside PaperForge — requires local annotation editor
- ❌ Writing annotation edits back to Zotero — requires sync_queue implementation
- ❌ Concept-card / deep-reading evidence integration — deferred

All Phase 2 code stays strictly within:
- Zotero SQLite snapshot/probe helpers (`zotero_probe.py`)
- Annotation normalization (`zotero_normalize.py`)
- PaperForge annotation storage (`schema.py`, `db.py`)
- Scoped import/reconciliation (`importer.py`)
- Structured domain errors (`errors.py`)

**Verdict: D-01 scope boundary respected.**

---

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **ZOT-01** — Read-only snapshot import | Verified | `zotero_snapshot()` copies DB to temp; `open_zotero_readonly()` opens `mode=ro`; all tests use snapshot path |
| **ZOT-02** — Paper-scoped reconciliation | Verified | `test_flow_reimport_does_not_stale_other_paper` proves scope isolation; `TestScopeIsolation` covers paper/library/attachment/local rows |
| **ZOT-03** — Identity includes source+library scope | Verified | IDs follow `zotero:{library_id}:{attachment_key}:{annotation_key}` format; `source_library_id`, `source_parent_key`, `source_attachment_key`, `source_annotation_key` all stored |
| **ZOT-04** — Actionable schema errors | Verified | `probe_zotero_annotation_schema()` raises `ZoteroSchemaError` with table/column name; `test_missing_table_raises_zotero_schema_error`, `test_missing_column_raises_zotero_schema_error` pass |
| **ZOT-05** — Read-only source row marking | Verified | `test_is_readonly_set` confirms `is_readonly=1`; `test_sync_state_imported` confirms `sync_state='imported'` |
| **SAFE-01** — Config-first Zotero path resolution | Verified | All functions accept explicit `Path` arguments; no hardcoded OS-specific paths in production code |
| **SAFE-02** — Temp-copy mode + cleanup | Verified | `test_snapshot_cleaned_up_after_context`, `test_flow_snapshot_cleanup` both pass |
| **SAFE-04** — No Zotero write-back | Verified | Code-path audit confirms zero write paths to Zotero |

---

## Known Unrelated Baseline Failures

The following failures exist in the upstream baseline and are **unrelated** to Phase 2 annotation code:

| Test | Issue | Status |
|------|-------|--------|
| `tests/test_config.py` (19 errors) | `PermissionError` on Windows when using `tmp_path` pytest fixture | Pre-existing, tracked in STATE.md |
| `test_paperforge_paths_returns_exact_keys` key mismatch | Test expects `ld_deep_script`, config returns `pf_deep_script` | Pre-existing naming mismatch |
| Missing `filelock` dependency | `paperforge/memory/builder.py` imports `filelock` via `worker/asset_index.py` | Pre-existing, causes skipped integration tests |

These failures existed before Phase 2 and are not caused by annotation module changes.

---

## Verification Summary

**Phase 2 status: PASS**

All 8 Phase 2 requirements are satisfied. All 71 annotation tests pass (1 expected skip). All 7 annotation modules compile cleanly. No Zotero write-back path exists. Scope boundary is respected.
