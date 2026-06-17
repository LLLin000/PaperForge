# Annotation Phase 1 Patterns

## Pattern 1: Database Path Helpers

Reference: `paperforge/memory/db.py`

Use:

```python
def get_annotations_db_path(vault: Path) -> Path:
    paths = paperforge_paths(vault)
    ...
```

Keep:

- Absolute `Path` return value.
- Parent directory creation only when opening write connections.
- Read-only connections opened with SQLite URI `mode=ro`.
- `sqlite3.Row` row factory.
- WAL and foreign key pragmas for write connections.

## Pattern 2: Schema Lifecycle

Reference: `paperforge/memory/schema.py`

Use:

- `CURRENT_ANNOTATION_SCHEMA_VERSION = 1`
- `CREATE_META`
- `ensure_schema(conn)`
- `get_schema_version(conn)`

Avoid:

- Adding annotation tables to `paperforge.memory.schema.ALL_TABLES`.
- Reusing `drop_all_tables` for annotation tables.

## Pattern 3: Tests

Reference:

- `tests/unit/memory/test_schema.py`
- `tests/test_config.py`

Use `tmp_path` or `tempfile.NamedTemporaryFile` for database tests.

Tests should assert:

- `annotations.db` resolves under configured `System/PaperForge/indexes`.
- write connection enables WAL.
- read-only connection works after DB exists.
- schema creates `meta`, `annotations`, `sync_queue`, and FTS table.
- schema version is recorded as `1`.
- `ensure_schema` is idempotent.
- memory rebuild does not remove or mutate `annotations.db`.

## Pattern 4: Baseline Failure Handling

Targeted verification should avoid claiming the whole repository is green, because current upstream baseline already has unrelated failures. Annotation Phase 1 plans should run the smallest relevant test set first.
