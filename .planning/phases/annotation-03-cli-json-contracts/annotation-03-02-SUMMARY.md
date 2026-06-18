# Plan 03-02 Summary: Annotation Import JSON Contract

**Date:** 2026-06-18
**Status:** ✓ Complete

## Objective

Implement `paperforge annotation import --json` with safe preview/apply behavior, wired to the Phase 2 Zotero probe and import backend.

## Deliverables

| Artifact | Status |
|----------|--------|
| `paperforge/commands/annotation.py` — Real `_cmd_import` with Zotero snapshot, schema probe, paper resolution, preview/apply | ✓ Done |
| `tests/cli/test_annotation_import_json.py` — 8 contract tests | ✓ Done (8 pass) |

## Test Results

```
tests/cli/test_annotation_import_json.py ......... [100%] 8 passed
tests/cli/test_annotation_command_shape.py ...... [100%] 7 passed
tests/unit/annotation .......................... [100%] 71 passed, 1 skipped
```

## Implementation Details

- **Preview mode** (default): Opens Zotero snapshot, probes schema, resolves paper key → attachment, counts raw annotations, returns `{dry_run: true, counts: {total: N}}` without writing.
- **Apply mode** (`--apply`): Full pipeline through `import_zotero_annotations_for_paper`, returns `{applied: true, counts: {inserted, updated, unchanged, stale, skipped, total}}`.
- **Paper resolution**: Looks up `--paper KEY` in Zotero `items` table, then finds attachment via `itemAttachments`. Supports `--attachment-key` for multi-PDF disambiguation.
- **Error codes used**: `VALIDATION_ERROR`, `ZOTERO_DATA_NOT_FOUND`, `CONFIG_NOT_FOUND`, `INTERNAL_ERROR` — all mapped through existing `ErrorCode` enum.

## Commit

`fc55ea0` — feat(annotation-03-02): wire annotation import preview/apply to Phase 2 backend
