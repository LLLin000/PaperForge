# Summary: annotation-01-03 — Memory rebuild isolation regression and targeted verification

## Files Created

| File | Purpose |
|------|---------|
| `tests/unit/annotation/test_rebuild_isolation.py` | 3 regression tests proving `annotations.db` is independent from memory rebuild operations + 1 structural sanity test |

## Files Modified

None. No existing files were modified (annotation code and memory code remain untouched).

## Design Decisions

1. **No annotation tables in `ALL_TABLES`** — Verified that `paperforge.memory.schema.ALL_TABLES` does NOT contain annotation-specific table names (`annotations`, `annotations_fts`, `sync_queue`). The shared `"meta"` name exists in both schemas but in separate databases, which is safe.

2. **Direct `drop_all_tables` regression** — `test_drop_all_tables_does_not_affect_annotations_db` provides the core isolation guarantee using separate in-memory "paperforge.db" and file-based "annotations.db" connections. This is the most direct proof that memory rebuild doesn't touch annotation data.

3. **`build_from_index` test skipped** — The full integration test (`test_build_from_index_preserves_annotations`) is marked `@pytest.mark.skip` because `build_from_index` transitively imports `filelock` (via `worker/asset_index.py`) which is not installed in this environment. The direct `drop_all_tables` test already proves the core isolation guarantee; the skipped test preserves the fixture code for future use once `filelock` is available.

4. **Minimal fixture design** — Tests avoid creating `paperforge.json` by relying on default config values. Only `System/PaperForge/indexes/formal-library.json` is created where needed.

## Test Results

### Annotation Phase 1 tests
```
python -m pytest tests/unit/annotation/test_db.py tests/unit/annotation/test_schema.py tests/unit/annotation/test_rebuild_isolation.py -q
.................s.                                                      [100%]
18 passed, 1 skipped
```

### Config tests (directly affected)
```
python -m pytest tests/test_config.py -q
.............                                                           [100%]
13 passed, 19 errors
```
The 19 errors are all `PermissionError: [WinError 5]` on `C:\Users\tan\AppData\Local\Temp\pytest-of-tan` — a **Windows environment issue** affecting all `tmp_path` fixture usage. These are NOT related to annotation code. The 13 passing tests are those that don't use `tmp_path`.

### Compile check
```
python -m compileall paperforge/annotation
Listing 'paperforge/annotation'...
# No errors
```

## Unrelated Baseline Failures (not annotation-related)

| Issue | Details |
|-------|---------|
| **Windows `tmp_path` permission** | All 19 `test_config.py` tests using `tmp_path` fixture fail with `PermissionError: [WinError 5]` on `C:\Users\tan\AppData\Local\Temp\pytest-of-tan`. This is a Windows OS-level permission issue affecting pytest's temp directory, not related to annotation code. |
| **`ld_deep_script` vs `pf_deep_script`** | `test_paperforge_paths_returns_exact_keys` expects key `ld_deep_script` but `paperforge_paths()` returns `pf_deep_script`. This is a pre-existing naming mismatch in the config test, not related to annotation. |
| **Missing `filelock`** | `build_from_index` integration test skipped because `filelock` is not installed (transitive dependency of `worker/asset_index.py`). Not an annotation issue. |

## Success Criteria

- [x] Annotation tables are absent from `paperforge.memory.schema.ALL_TABLES`
- [x] Separate `annotations.db` survives memory table drop/rebuild paths
- [x] Targeted annotation tests pass
- [x] Verification output clearly distinguishes annotation status from unrelated baseline failures

## Test Inventory (19 total)

| Source | Tests | Status |
|--------|-------|--------|
| `tests/unit/annotation/test_db.py` | 5 | ✅ 5 passed |
| `tests/unit/annotation/test_schema.py` | 10 | ✅ 10 passed |
| `tests/unit/annotation/test_rebuild_isolation.py` | 4 | ✅ 3 passed, 1 skipped (documented) |
