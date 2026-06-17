# Annotation Phase 2 Research: Zotero Probe and Safe Import

## Research Summary

Annotation Phase 2 should build a narrow backend import layer:

1. Open a copied Zotero SQLite snapshot, never the live database for mutation.
2. Probe the Zotero annotation schema before reading rows.
3. Normalize Zotero annotation rows into PaperForge's source-agnostic annotation shape.
4. Reconcile imported rows into `annotations.db` only inside an explicit paper scope.

The existing repository already has the PaperForge-owned annotation schema from Annotation Phase 1:

- `paperforge/annotation/db.py`
- `paperforge/annotation/schema.py`
- `tests/unit/annotation/test_db.py`
- `tests/unit/annotation/test_schema.py`
- `tests/unit/annotation/test_rebuild_isolation.py`

The existing `tests/sandbox/TestZoteroData/zotero.sqlite` file is not a usable SQLite database. It is only 62 bytes and produces `sqlite3.DatabaseError: file is not a database`. Phase 2 must therefore create a minimal valid Zotero-style SQLite fixture rather than relying on that file.

## Existing PaperForge Annotation Schema

The `annotations` table already includes the fields Phase 2 needs:

- `paper_id`
- `source`
- `source_library_id`
- `source_annotation_key`
- `source_attachment_key`
- `source_parent_key`
- `source_version`
- `source_modified_at`
- `type`
- `page_index`
- `page_label`
- `selected_text`
- `comment`
- `color`
- `sort_index`
- `tags_json`
- `position_json`
- `selector_json`
- `sync_state`
- `is_readonly`
- `created_at`
- `updated_at`
- `deleted_at`

This means Phase 2 does not need a schema migration if import identity and payloads can fit these columns.

## Suggested Module Boundaries

- `paperforge/annotation/errors.py`
  - Structured domain exceptions for missing DB, unreadable DB, invalid schema, and invalid payload.

- `paperforge/annotation/zotero_probe.py`
  - Temp-copy snapshot helper.
  - Read-only SQLite opening.
  - Zotero table/column probe.
  - Raw Zotero annotation row fetch for a selected paper or attachment.

- `paperforge/annotation/zotero_normalize.py`
  - Dataclass or plain dict for normalized imported annotations.
  - Conversion from Zotero row shape to PaperForge row shape.
  - JSON normalization for tags, position, and selector fields.

- `paperforge/annotation/importer.py`
  - Upsert normalized rows into `annotations.db`.
  - Mark missing rows as stale/soft-deleted only within the requested paper scope.
  - Keep Zotero-sourced rows read-only.

## Minimal Zotero Fixture Shape

Use a test-created SQLite database rather than a committed binary fixture. The fixture should include enough Zotero-like tables/columns for the importer contract:

- `items(itemID, itemTypeID, libraryID, key, dateModified)`
- `itemAttachments(itemID, parentItemID, path, contentType)`
- `itemAnnotations(itemID, parentItemID, type, text, comment, color, pageLabel, sortIndex, position, dateModified)`
- `tags(tagID, name)`
- `itemTags(itemID, tagID)`

The implementation can support alternate column names through a probe mapping if needed, but the initial fixture should be explicit and small.

## Safety Notes

- Open the copied Zotero DB in SQLite URI read-only mode: `file:path?mode=ro`.
- Do not expose any function that writes to Zotero SQLite.
- Do not mutate Zotero paths in config.
- When importing one paper, select stale candidates by:
  - `paper_id`
  - `source = 'zotero'`
  - matching `source_library_id`
  - matching `source_parent_key` and/or `source_attachment_key`

## Planning Recommendation

Use four plans:

1. Zotero snapshot/probe/errors and valid fixture helpers.
2. Zotero annotation normalization.
3. Scoped import reconciliation into `annotations.db`.
4. Integration verification and roadmap/state cleanup.

This keeps each wave independently testable and avoids mixing schema probing, transformation, and database mutation in one large plan.

## Research Complete
