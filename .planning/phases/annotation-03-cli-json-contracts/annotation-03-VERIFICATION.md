# Phase 3 Verification: Annotation CLI JSON Contracts

**Date:** 2026-06-18
**Status:** ✓ Complete — all 4 plans executed

## Commands Run

| Command | Result |
|---------|--------|
| `python -m pytest tests/cli/test_annotation_command_shape.py -q` | 7 passed |
| `python -m pytest tests/cli/test_annotation_import_json.py -q` | 8 passed |
| `python -m pytest tests/cli/test_annotation_read_json.py -q` | 8 passed |
| `python -m pytest tests/cli/test_annotation_json_contracts.py -q` | 15 passed |
| `python -m pytest tests/cli/test_annotation_error_contracts.py -q` | 14 passed |
| **CLI sub-total** | **52 passed** |
| `python -m pytest tests/unit/annotation -q` | 71 passed, 1 skipped |
| `python -m compileall paperforge/commands paperforge/annotation` | clean |

## Phase Goal Verification

### PFResult Contract — All JSON commands use PFResult envelope
- `annotation import --json` ✓
- `annotation list --json` ✓
- `annotation status --json` ✓
- `annotation export --json` ✓
- Verified: `{ok, command, version, data, error}` shape, stable `command` values, stable English keys in `data`

### CLI-01: Annotation import --json reports dry-run / applied counts
- Preview mode returns `{dry_run: true, counts: {total: N}}` ✓
- Apply mode returns `{applied: true, counts: {inserted, updated, unchanged, stale, skipped, total}}` ✓
- Missing `--paper` / `--zotero-db` return actionable `VALIDATION_ERROR` ✓

### CLI-02: Annotation list --json returns ordered lightweight rows
- Ordered by `page_index, sort_index, id` ✓
- Lightweight scan fields: `id, type, page, selected_text, comment, color, source, is_readonly` ✓
- Heavy fields (`position_json`, `selector_json`, `tags_json`) excluded ✓

### CLI-03: Annotation status --json reports DB health
- `schema_version`, `db_path`, `db_available`, `total_annotations`, `source_counts`, `readonly_count`, `deleted_count`, `total_papers_with_annotations` ✓
- Absent DB → `db_available: false` with zero counts ✓

### CLI-04: Annotation export --json returns full payload
- All annotation columns included in export output ✓
- `format_version: "1.0"` present ✓
- Paper-scoped — includes annotations for specified paper only ✓

### CLI-05: CLI failure output is stable and actionable
- Missing `--paper` → `VALIDATION_ERROR` with suggestions ✓
- Missing Zotero DB → `ZOTERO_DATA_NOT_FOUND` ✓
- Corrupt/missing annotations.db → graceful empty state (no traceback) ✓
- Unknown annotation schema → graceful empty state (no traceback) ✓
- Unknown subcommand → argparse error (not Python traceback) ✓

### SAFE-03: No Zotero write-back path introduced
- All Zotero reads use `zotero_snapshot()` (temp copy) + `open_zotero_readonly()` ✓
- PaperForge writes only to its own `annotations.db` ✓
- Imported rows marked `is_readonly=1`, `source='zotero'` ✓

### No Obsidian Plugin Dependency
- All CLI commands work without Obsidian plugin runtime ✓
- Tests run against disposable vaults via `vault_builder` ✓

## Unrelated Baseline Failures

| Test | Issue | Status |
|------|-------|--------|
| `test_config.py` (4 tests) | `PermissionError` with `tmp_path` on Windows | Pre-existing, unrelated to annotation |
| `test_paperforge_paths_returns_exact_keys` | expects `ld_deep_script` but config has `pf_deep_script` | Pre-existing key mismatch |
| `filelock` missing | `worker/asset_index.py` imports `filelock` | Pre-existing, `build_from_index` integration test skipped |
| `.pytest_cache/` permission | Windows permission warning (non-blocking) | Cosmetic |

None of these are annotation-specific.

## Residual Risks

1. **Import preview without `--zotero-db` is untestable in unit tests** — preview requires a real Zotero SQLite snapshot. The validation layer (missing args) is tested; the probe + count path requires integration-level fixtures.
2. **Corrupt DB fallback is connection-probed** — `_open_annotations_db` probes `SELECT 1 FROM annotations LIMIT 1` after opening. This catches corrupt files and missing tables, but an annotations table with incompatible column types may pass the probe and fail on the first real query.
3. **No full-library import path** — only paper-scoped import is implemented. Full-library sync is deferred to a later milestone.

## Verification Conclusion

Phase 3 delivers all four CLI JSON contracts with stable PFResult output, read-only Zotero access, and no Obsidian plugin dependency. Annotation backend coverage: **52 CLI tests + 71 unit tests = 123 total tests passing**.
