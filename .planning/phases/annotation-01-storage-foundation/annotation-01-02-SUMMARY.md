# Summary: annotation-01-02 — Annotation schema lifecycle and schema tests

## Files Created

| File | Purpose |
|------|---------|
| `paperforge/annotation/schema.py` | Annotation schema lifecycle (`ensure_schema`, `get_schema_version`, `ANNOTATION_SCHEMA_VERSION`, `ANNOTATION_TABLES`) |
| `tests/unit/annotation/test_schema.py` | 10 TDD tests (RED → GREEN) for schema creation, versioning, idempotency, columns, and FTS triggers |

## Files Modified

None. This plan is self-contained and does not touch existing files.

## Design Decisions

1. **Independent schema version** — `ANNOTATION_SCHEMA_VERSION = 1` is completely separate from the memory layer's `CURRENT_SCHEMA_VERSION`. No cross-imports between the two schema modules.

2. **Source-agnostic column naming** — Columns like `source`, `source_library_id`, `source_annotation_key`, `source_attachment_key`, `source_parent_key`, and `source_version` use generic names that can represent Zotero, Zotero-style, or other annotation providers. No Zotero-specific names in the schema.

3. **Schema version stored in meta** — `ensure_schema` uses `INSERT OR IGNORE` to insert the schema version into the meta table only when absent, making it idempotent.

4. **FTS5 with content sync triggers** — The `annotations_fts` virtual table uses `content='annotations'` with `content_rowid='rowid'` for external content FTS5. Three triggers (`annotations_ai`, `annotations_ad`, `annotations_au`) keep the FTS index in sync on insert, delete, and update.

5. **`sync_queue` is a placeholder** — The table exists with minimal columns (`annotation_id`, `operation`, `payload_json`, `created_at`, `synced_at`) but no write-back logic is implemented. Future phases will add write-back behavior.

6. **No `drop_all_tables`** — Unlike the memory schema, the annotation schema does not provide a `drop_all_tables` function, as annotation data should not be dropped during normal operations.

7. **No changes to memory schema** — The annotation tables are NOT added to `paperforge.memory.schema.ALL_TABLES`. The two schemas remain fully independent.

## Test Results

```
python -m pytest tests/unit/annotation/test_schema.py tests/unit/annotation/test_db.py -q
...............                                                          [100%]
15 passed
```

```
python -m compileall paperforge/annotation
Listing 'paperforge/annotation'...
# No errors
```

## Success Criteria

- [x] `paperforge/annotation/schema.py` exposes `ANNOTATION_SCHEMA_VERSION`, `ensure_schema`, and `get_schema_version`
- [x] Required annotation columns exist (all 23 columns in the `annotations` table)
- [x] `meta.schema_version` records annotation schema version `1`
- [x] `ensure_schema` is idempotent and preserves existing rows
- [x] FTS table/triggers index annotation `selected_text` and `comment`
- [x] `sync_queue` exists as a placeholder (no write-back logic)
- [x] No annotation tables added to `paperforge.memory.schema.ALL_TABLES`
- [x] No Zotero code imported or referenced
