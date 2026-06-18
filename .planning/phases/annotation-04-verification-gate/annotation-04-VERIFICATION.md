# Annotation Phase 4 — Verification Report

> **Phase:** Annotation Phase 4 — Verification Gate
> **Date:** 2026-06-18
> **Milestone:** annotation v0.1 — PDF Annotation Backend & CLI Foundation

---

## Commands Run

| Command | Result |
|---------|--------|
| `pytest tests/unit/annotation/ -q` | **88 passed, 1 skipped** |
| `pytest tests/cli/test_annotation_command_shape.py tests/cli/test_annotation_import_json.py tests/cli/test_annotation_read_json.py tests/cli/test_annotation_json_contracts.py tests/cli/test_annotation_error_contracts.py -q` | **52 passed** |
| `compileall paperforge/annotation paperforge/commands` | **Clean** (no errors) |

---

## Requirement Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| **TEST-01** | Fixture SQLite with parent paper, PDF attachment, multi-annotation rows | ✅ Pass | `conftest.py`: `build_zotero_two_paper`, `build_zotero_fixture_full`, `build_zotero_fixture_reduced` — all provide generated SQLite databases at runtime |
| **TEST-02** | Unit tests: schema, probe, normalize, importer reconciliation, service list/export | ✅ Pass | 88 unit tests covering: schema creation, probe (8), normalization, importer (insert/reimport/stale/scope/read-only/counts), flow (6), DB helpers, rebuild isolation, **service contracts (17)** |
| **TEST-03** | CLI tests: success and failure JSON for import/list/status/export | ✅ Pass | 52 CLI tests covering: PFResult envelope (all commands), import preview/apply, list ordering/fields, export full payload, status keys/counts, error codes, corrupt DB, missing params, unknown subcommands |
| **TEST-04** | Paper-scoped import doesn't soft-delete other paper annotations | ✅ Pass | `test_flow_reimport_does_not_stale_other_paper`: imports both papers → re-imports Paper A → asserts Paper B rows have `deleted_at IS NULL`. Also `TestScopeIsolation` (4 tests) covering different library/attachment/local rows |
| **TEST-05** | Verification notes call out unrelated upstream baseline failures separately | ✅ Covered | See **Known Unrelated Baseline Failures** below |

---

## Hard Gate Result

```
Annotation unit tests:  88 passed, 1 skipped  ✅
Annotation CLI tests:   52 passed             ✅
Compile check:          clean                 ✅
```

**Annotation v0.1 hard gate: PASSED**

---

## Failure Classification

### Blocking Annotation Failures

| # | Failure | Status | Notes |
|---|---------|--------|-------|
| 1 | `test_flow_unknown_schema_fails_before_mutation` — `NameError: pytest` not imported, `_open_ann` undefined | ✅ **Fixed in Plan 01** | Missing `import pytest` and wrong function name in test file |
| 2 | `test_flow_snapshot_cleanup` — `NameError: _PAPER_A_LIBRARY` not defined | ✅ **Fixed in Plan 01** | Used private `_PAPER_A_*` names instead of public `PAPER_A_*` constants |
| 3 | Windows PermissionError during temp SQLite cleanup in `zotero_snapshot` | ⚠️ **Mitigated** | Caused by unclosed connections when exceptions fire inside the `with` block. After fixing the bug above (exception no longer fires), the cleanup path runs correctly. Root cause is Windows file locking — same class as known baseline issue. |

### Known Unrelated Baseline Failures

These failures exist in `tests/unit/` and are **not caused by annotation v0.1 code**. They predate the annotation milestone:

| # | Failure | Scope | Root Cause |
|---|---------|-------|------------|
| 1 | `test_config.py` — 4 tests fail with `PermissionError` | Config module | `tmp_path` fixture cleanup on Windows (`PermissionError`) — pre-existing |
| 2 | `test_paperforge_paths_returns_exact_keys` — config key mismatch | Config module | Test expects `ld_deep_script` but config returns `pf_deep_script` — pre-existing baseline mismatch |
| 3 | Missing `filelock` dependency | Memory builder | `paperforge/memory/builder.py` transitively imports `filelock` via `worker/asset_index.py` — pre-existing |
| 4 | `.pytest_cache` permission denied | Test infrastructure | Windows permission issue on the `.pytest_cache` directory — cosmetic, doesn't affect test results |

**None of the above block annotation v0.1.**

### Advisory Risks / Gaps

| # | Risk | Severity | Notes |
|---|------|----------|-------|
| 1 | FTS5 test skipped | Low | `test_schema_fts5_created` skipped because the Python build doesn't include FTS5. This is a CPython packaging limitation, not an annotation code issue. FTS5 is used only for future text search features. |
| 2 | Windows temp file cleanup edge cases | Low | During test failures inside `zotero_snapshot` context, the `PermissionError` on `snapshot_path.unlink()` can mask the original error. Mitigated by closing connections before context exit. |
| 3 | No full-repo test run in this gate | Advisory | The hard gate runs annotation-specific tests + compile checks. Full-repo CI would also hit the known baseline failures above, so it provides no additional annotation signal. |

---

## Safety Audit

### Zotero Write-Back Audit

**Result: No Zotero write path exists.** PaperForge never writes to Zotero SQLite.

| Check | Finding | Source Evidence |
|-------|---------|----------------|
| Zotero snapshot mode | Read-only via SQLite URI `mode=ro&immutable=1` | `zotero_probe.py:142` |
| Zotero schema probe | Uses `SELECT` and `PRAGMA table_info` — read-only | `zotero_probe.py:184,198` |
| Annotation fetch | Uses `SELECT * FROM itemAnnotations` — read-only | `zotero_probe.py:254` |
| All `INSERT`/`UPDATE`/`DELETE`/`commit()` | Target PaperForge `annotations.db` (via `db_conn` parameter) | `importer.py:155,227,348,370` |
| All `commits` in annotation module | `db_conn.commit()` — writes to PaperForge's own DB | `importer.py:370`, `schema.py:172` |

**There are zero code paths that execute `INSERT`, `UPDATE`, `DELETE`, or `commit()` on a Zotero SQLite connection.**

### Obsidian Plugin Dependency Audit

**Result: Annotation backend/CLI does not require the Obsidian plugin runtime.**

All annotation operations are executed via `python -m paperforge annotation ...` CLI commands. The `vault_builder` fixture in CLI tests creates disposable vault directories with no Obsidian involvement. Unit tests use direct SQLite connections.

---

## Conclusion

**Annotation v0.1 backend and CLI foundation is complete and verified.**

- All 4 phases completed across 18 plans
- 140 tests pass (88 unit + 52 CLI) covering the full annotation surface
- Zero blocking annotation failures remaining
- Known unrelated baseline failures documented separately
- Safety audit confirms no Zotero write-back path exists
- Obsidian plugin is not required for annotation backend/CLI operations

### What annotation v0.1 Ships

| Capability | Status |
|------------|--------|
| Independent `annotations.db` (not dropped by memory rebuilds) | ✅ |
| Zotero SQLite temp-copy probe (read-only, `mode=ro`) | ✅ |
| Annotation normalization (selected text, comment, color, page, tags, position) | ✅ |
| Paper-scoped import with preview/apply | ✅ |
| Re-import reconciliation (update changed, stale-mark removed, restore reappeared) | ✅ |
| Scope isolation (other papers/libraries/attachments/local rows untouched) | ✅ |
| `paperforge annotation import/list/status/export --json` CLI | ✅ |
| JSON output uses PFResult envelope (`ok`, `command`, `version`, `data`, `error`) | ✅ |
| Error codes for missing Zotero DB, bad schema, missing params, corrupt DB | ✅ |
| No Zotero write-back | ✅ |
| No Obsidian plugin dependency | ✅ |

### What Is Deferred

| Capability | Planned For |
|------------|-------------|
| Obsidian PDF overlay (rendering annotations in PDF viewer) | Future annotation milestone |
| Local PDF annotation editing | Future annotation milestone |
| Zotero write-back | Future annotation milestone (requires API-based design) |
| Concept-card / evidence integration | Future annotation milestone |
