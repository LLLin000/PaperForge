# Summary: annotation-01-01 — Annotation package and DB path/connection helpers

## Files Created

| File | Purpose |
|------|---------|
| `paperforge/annotation/__init__.py` | Package init with `__all__` exports |
| `paperforge/annotation/db.py` | `get_annotations_db_path()` and `get_annotations_connection()` |
| `tests/unit/annotation/__init__.py` | Test package init |
| `tests/unit/annotation/test_db.py` | 5 TDD tests for DB path/connection helpers |

## Files Modified

| File | Change |
|------|--------|
| `paperforge/config.py` | Added `"annotations_db": paperforge / "indexes" / "annotations.db"` to `paperforge_paths()` |
| `tests/test_config.py` | Added `"annotations_db"` and `"memory_db"` to required_keys in `test_paperforge_paths_returns_exact_keys` |

## Design Decisions

1. **Followed `memory/db.py` pattern exactly** — `get_annotations_db_path()` resolves through `paperforge_paths(vault)["annotations_db"]`, and `get_annotations_connection()` mirrors `get_connection()` from the memory module with WAL mode, foreign keys, `sqlite3.Row` row factory, and read-only URI `?mode=ro` support.

2. **`annotations_db` in paperforge_paths** — Added to `paperforge_paths()` return dict as `paperforge / "indexes" / "annotations.db"`, same parent directory as `memory_db` (`indexes/`), per plan requirements.

3. **No Zotero dependency** — The annotation package does not import or reference any Zotero code.

4. **No schema, CLI, or probe logic** — This plan delivers only the package scaffolding and DB path/connection helpers.

## Test Results

```
python -m pytest tests/unit/annotation/test_db.py -q
.....                                                                    [100%]
5 passed
```

```
python -m compileall paperforge/annotation
Listing 'paperforge/annotation'...
# No errors
```

## Success Criteria

- [x] `paperforge.annotation` package exists
- [x] `get_annotations_db_path(vault)` resolves to configured `PaperForge/indexes/annotations.db`
- [x] Write connections enable WAL and foreign keys
- [x] Read-only connections do not create a missing DB (raise `sqlite3.OperationalError`)
- [x] No import/probe/CLI/plugin overlay code is introduced
