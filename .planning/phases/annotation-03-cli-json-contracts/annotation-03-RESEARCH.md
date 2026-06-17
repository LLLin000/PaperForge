# Annotation Phase 3 Research: Annotation CLI JSON Contracts

## Research Summary

Annotation Phase 3 should add a stable CLI surface over the now-complete Phase 2 annotation backend.

Phase 2 has shipped these backend modules:

- `paperforge/annotation/errors.py`
- `paperforge/annotation/zotero_probe.py`
- `paperforge/annotation/zotero_normalize.py`
- `paperforge/annotation/importer.py`
- `paperforge/annotation/db.py`
- `paperforge/annotation/schema.py`

Phase 2 verification reports:

- 53 Phase 2-specific tests passing.
- 71 full annotation tests passing with 1 expected skip.
- No Zotero SQLite write-back path.
- `ImportResult` exists with stable count fields: `inserted`, `updated`, `unchanged`, `stale`, `skipped`, and `total`.

This means Phase 3 can focus on CLI contracts, not annotation import internals.

## Existing CLI Patterns

`paperforge/cli.py` owns:

- `build_parser()`
- top-level command registration
- dispatch in `main()`
- shared global flags such as `--vault`, `--verbose`, and `--no-progress`
- `args.vault_path`, `args.cfg`, and `args.paths` attachment before command dispatch

Existing command modules live under `paperforge/commands/` and usually expose:

```python
def run(args: argparse.Namespace) -> int:
    ...
```

Newer JSON commands use `paperforge.core.result.PFResult`:

- `ok`
- `command`
- `version`
- `data`
- `error`
- optional `warnings`
- optional `next_actions`

`PFError` uses `paperforge.core.errors.ErrorCode`, so Phase 3 may need either:

1. reuse existing generic error codes, or
2. extend `ErrorCode` with annotation-specific stable codes.

The discuss context requires stable `--json` error codes for annotation failures, so the planner should inspect `paperforge/core/errors.py` before implementation.

## Suggested Module Boundaries

- `paperforge/commands/annotation.py`
  - `run(args)` dispatches `annotation_subcommand`.
  - Converts annotation-domain exceptions into `PFResult` JSON or plain text.
  - Provides command-specific helpers for import/list/status/export.

- `paperforge/annotation/service.py` or command-local helpers
  - Optional if list/status/export logic grows beyond a few SQL queries.
  - Should query `annotations.db` only.
  - Should not import Obsidian plugin code.

- `tests/cli/test_annotation_json_contracts.py`
  - Success JSON for `annotation import/list/status/export --json`.

- `tests/cli/test_annotation_error_contracts.py`
  - Stable JSON failures for missing Zotero DB, invalid schema, invalid paper filter, missing config/DB, and unreadable DB.

## CLI Contract Recommendations

### Command Namespace

Use:

```powershell
paperforge annotation import --paper KEY --zotero-db PATH --json
paperforge annotation import --paper KEY --zotero-db PATH --apply --json
paperforge annotation list --paper KEY --json
paperforge annotation status --json
paperforge annotation export --paper KEY --json
```

Keep `annotation` as a single namespace. Do not place these under `sync`, `status`, or `memory`.

### Import Safety

`import` should default to preview mode. In preview mode:

- return `ok: true`
- return `data.dry_run: true`
- return projected counts when backend supports it
- do not mutate `annotations.db`

Real writes require `--apply`.

### Paper Selection

Use `--paper KEY` as the main user-facing selector. The first implementation can pass it through as `paper_id` if no richer resolver exists yet, but the plan should leave room to resolve Zotero key/title/alias through existing paper identity later.

Use optional `--attachment-key` for multi-PDF disambiguation.

### JSON Output

Use PFResult for every `--json` annotation command.

Recommended command values:

- `annotation.import`
- `annotation.list`
- `annotation.status`
- `annotation.export`

Recommended payloads:

- `import`: `dry_run`, `applied`, `paper`, `attachment_key`, `counts`, `source`
- `list`: `paper`, `annotations`, `count`
- `status`: `db_path`, `schema_version`, `total_annotations`, `source_counts`, `readonly_counts`, `deleted_count`, `health`
- `export`: `paper`, `annotations`, `count`, `format_version`

### Error Output

When `--json` is present, errors must be JSON on stdout, not traceback text.

Suggested stable error codes:

- `ANNOTATION_ZOTERO_DB_MISSING`
- `ANNOTATION_ZOTERO_DB_UNREADABLE`
- `ANNOTATION_ZOTERO_SCHEMA_UNKNOWN`
- `ANNOTATION_INVALID_PAPER_FILTER`
- `ANNOTATION_DB_MISSING`
- `ANNOTATION_DB_SCHEMA_MISMATCH`
- `ANNOTATION_PAYLOAD_INVALID`

If the existing `ErrorCode` enum cannot accept these without broad churn, use the closest existing enum values but keep annotation-specific `details.kind` or `details.annotation_error_code` stable.

## Planning Recommendation

Use four plans:

1. Parser namespace + command module scaffold + PFResult/error helpers.
2. `annotation import --json` preview/apply contract over Phase 2 backend.
3. `annotation list/status/export --json` read-only contracts over `annotations.db`.
4. CLI contract tests, snapshots, and roadmap/state updates.

This keeps command registration, write-capable import, read-only query commands, and contract verification separate.

## Research Complete
