# 03-02-SUMMARY: CLI base-refresh + Tests

## What was built

Phase 3 Plan 02 adds the `paperforge base-refresh` CLI command and two test files covering 8-view generation and incremental merge behavior.

## Files modified

- `paperforge/cli.py` — added `base-refresh` subcommand

## Files created

- `tests/test_base_views.py` — 11 tests for `build_base_views()` and `substitute_config_placeholders()`
- `tests/test_base_preservation.py` — 10 tests for incremental merge and user-view preservation

## CLI changes

### `paperforge base-refresh`

```
usage: paperforge base-refresh [-h] [--force]

Refresh Obsidian Base view files

options:
  --force, -f  Force full regeneration (bypasses incremental merge,
               replaces all views including user views)
```

Calls `ensure_base_views(vault, paths, config, force=force)`.

## Test coverage

### `tests/test_base_views.py` (11 tests)
- `TestBuildBaseViews`: 7 tests — exactly 8 views, all names present, required keys, filter expressions
- `TestSubstituteConfigPlaceholders`: 4 tests — placeholder substitution, multiple placeholders, unknown unchanged, backslash conversion

### `tests/test_base_preservation.py` (10 tests)
- `TestIncrementalMerge`: 5 tests — user custom view preserved after refresh, standard views updated, force=True full regeneration, standard view filter overwrite on refresh, first-run creation
- `TestLiteratureHubBase`: 2 tests — Literature Hub.base created, PaperForge.base created
- `TestMergeBaseViews`: 3 tests — user view preservation, first-run fresh generation, unknown placeholder unchanged

## Verification

```
$ python -c "from paperforge.cli import build_parser; ..."
$ python -m pytest tests/test_base_views.py tests/test_base_preservation.py -v
tests/test_base_views.py: 11 passed
tests/test_base_preservation.py: 10 passed

$ python -m pytest tests/ -v --ignore=tests/test_integration.py
120 passed, 2 skipped
```
