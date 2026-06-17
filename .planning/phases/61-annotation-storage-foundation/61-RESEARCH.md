# Phase 61 Research: Annotation Storage Foundation

## Research Result

Use the old annotation branch as design reference, but implement against the current upstream/master code patterns.

## Relevant Current Code

- `paperforge/config.py`
  - `paperforge_paths(vault)` currently returns:
    - `index`: `<vault>/<system_dir>/PaperForge/indexes/formal-library.json`
    - `memory_db`: `<vault>/<system_dir>/PaperForge/indexes/paperforge.db`
  - Phase 61 should either add an `annotations_db` key or derive it from `memory_db`/`index` in `paperforge.annotation.db`.

- `paperforge/memory/db.py`
  - Use as direct pattern for DB path and SQLite connection helper.
  - Important behavior: create parent directories for write connections, `row_factory = sqlite3.Row`, `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`.

- `paperforge/memory/schema.py`
  - Use as pattern for schema version, `ensure_schema`, `get_schema_version`, and drop-table boundary.

- `paperforge/memory/builder.py`
  - This is the rebuild path that must not touch `annotations.db`.

## Old Branch Reference

Useful files from old `feat/pdf-annotation-layer`:

- `paperforge/annotation/db.py`
- `paperforge/annotation/schema.py`
- `tests/unit/annotation/test_schema.py`

Do not copy blindly. Improve the schema to match annotation v0.1 requirements:

- Include source library scope as first-class fields.
- Use names that make Phase 62 identity safe:
  - `source`
  - `source_library_id`
  - `source_annotation_key`
  - `source_attachment_key`
  - `source_parent_key`
- Keep Zotero-specific aliases only if they help readability; do not make bare Zotero key the only identity.

## Suggested Schema Fields

Main `annotations` table:

- `id TEXT PRIMARY KEY`
- `paper_id TEXT NOT NULL`
- `source TEXT NOT NULL DEFAULT 'paperforge'`
- `source_library_id TEXT DEFAULT ''`
- `source_annotation_key TEXT DEFAULT ''`
- `source_attachment_key TEXT DEFAULT ''`
- `source_parent_key TEXT DEFAULT ''`
- `source_version INTEGER`
- `source_modified_at TEXT DEFAULT ''`
- `type TEXT NOT NULL`
- `page_index INTEGER`
- `page_label TEXT DEFAULT ''`
- `selected_text TEXT DEFAULT ''`
- `comment TEXT DEFAULT ''`
- `color TEXT DEFAULT ''`
- `sort_index TEXT DEFAULT ''`
- `tags_json TEXT DEFAULT '[]'`
- `position_json TEXT DEFAULT '{}'`
- `selector_json TEXT DEFAULT '{}'`
- `sync_state TEXT NOT NULL DEFAULT 'local'`
- `is_readonly INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- `deleted_at TEXT`

Support tables:

- `meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)`
- `sync_queue(...)` reserved for future write-back
- optional FTS table `annotations_fts` for `selected_text/comment/tags_json`

## Planning Implication

Phase 61 should be three plans:

1. Add annotation package/path helper.
2. Add schema and schema tests.
3. Add rebuild isolation regression and update path inventory tests if `annotations_db` is added to `paperforge_paths`.
