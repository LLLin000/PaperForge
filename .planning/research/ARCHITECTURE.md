# Research: annotation v0.1 Architecture

**Date:** 2026-06-17
**Milestone:** annotation v0.1 - PDF Annotation Backend & CLI Foundation

## Proposed Module Layout

```text
paperforge/
  annotation/
    __init__.py
    db.py
    schema.py
    probe.py
    importer.py
    service.py
  commands/
    annotation.py
```

## Data Flow

```text
Zotero zotero.sqlite
  -> temp copied SQLite snapshot
  -> read-only probe
  -> normalized annotation rows
  -> safe scoped import
  -> PaperForge annotations.db
  -> CLI list/status/export JSON
```

## Database Boundary

`annotations.db` should be independent from `paperforge.db`.

Reason in plain language: `paperforge.db` is rebuildable machine memory; annotations are user evidence. Rebuilding machine memory must not wipe evidence.

## Identity Strategy

The old branch used a weak imported row identity:

```text
id = zotero annotation key
```

v0.1 should use a stronger external identity:

```text
source + library_id + annotation_key
```

Recommended persisted fields:

- `id`: PaperForge internal ID
- `source`: `zotero_db` or `paperforge`
- `source_library_id`
- `source_annotation_key`
- `source_attachment_key`
- `paper_id` / parent Zotero key
- `source_modified_at`
- `source_version`

## Import Scope

The importer must distinguish:

- full Zotero-library import
- paper-scoped import
- dry-run import

Stale deletion must only operate inside the current import scope. This directly fixes the old branch risk where importing one paper could mark annotations from other papers as deleted.

## CLI Boundary

The CLI owns user-facing commands. The annotation package owns business logic.

```text
paperforge.commands.annotation
  -> parses args, resolves paths, formats JSON

paperforge.annotation.*
  -> opens DB, probes Zotero, imports, lists, exports
```

## Future Hook Points

v0.1 should leave clean seams for:

- v0.2 Obsidian PDF read-only overlay
- v0.3 local create/edit/delete
- future evidence anchors into deep-reading/concept-card workflows

Those hooks should not force v0.1 to implement the frontend now.
