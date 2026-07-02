# Coding Conventions

**Analysis Date:** 2026-07-02

## Naming Patterns

**Files:**
- Use lowercase snake_case for Python modules: `paperforge/core/result.py`, `paperforge/worker/_utils.py`, `paperforge/annotation/zotero_probe.py`.
- Use leading underscores for internal Python helper modules: `paperforge/worker/_retry.py`, `paperforge/worker/_progress.py`, `paperforge/worker/_domain.py`.
- Use `test_*.py` for Python tests and place tests under the matching layer directory: `tests/unit/core/test_result.py`, `tests/cli/test_json_contracts.py`, `tests/chaos/test_network_failures.py`.
- Use `.test.mjs` for plugin Vitest tests: `paperforge/plugin/tests/runtime.test.mjs`, `paperforge/plugin/tests/annotation-overlay.test.mjs`.
- Plugin testable CommonJS helpers live in `paperforge/plugin/src/testable.js`; generated/distribution plugin entrypoint lives in `paperforge/plugin/main.js`.

**Functions:**
- Use snake_case for Python functions and private helpers: `build_parser()` in `paperforge/cli.py`, `_find_repo_root()` in `paperforge/cli.py`, `_now_utc()` in `paperforge/annotation/importer.py`.
- Use `run_*` for command worker entry points and patchable CLI dispatch functions: `run_status`, `run_selection_sync`, `run_index_refresh`, `run_ocr` in `paperforge/cli.py`.
- Use `load_*`, `read_*`, `write_*`, `ensure_*`, and `resolve_*` prefixes for side-effect or resolver functions: `load_journal_db()` in `paperforge/worker/_utils.py`, `ensure_schema()` in `paperforge/annotation/schema.py`, `resolve_vault()` imported by `paperforge/cli.py`.
- Use camelCase for plugin JavaScript functions: `resolvePythonExecutable()`, `checkRuntimeVersion()`, `buildAnnotationExportArgs()`, `parseAnnotationPositionJson()` in `paperforge/plugin/src/testable.js`.

**Variables:**
- Use snake_case for Python locals, arguments, and fixture names: `annotations_db_path`, `attachment_item_key`, `ann_with_data`, `cli_invoker`.
- Use UPPER_SNAKE_CASE for Python constants: `PF_LITE_DIR`, `REPO_ROOT` in `paperforge/cli.py`, `_NOW`, `_ANNOTATION_COLS`, `_PLACEHOLDERS` in `tests/unit/annotation/test_service_contracts.py`.
- Use module globals sparingly for patchable dispatch seams or caches: `run_status = None` in `paperforge/cli.py`, `_JOURNAL_DB` in `paperforge/worker/_utils.py`.
- Use camelCase for plugin JavaScript locals and object fields exposed to UI view models: `paperKey`, `pythonExe`, `sourceAttachmentKey`, `pageIndex` in `paperforge/plugin/src/testable.js`.

**Types:**
- Use dataclasses for simple Python data contracts: `PFError` and `PFResult` in `paperforge/core/result.py`, `ImportResult` in `paperforge/annotation/importer.py`.
- Use `Enum` subclasses for stable symbolic contracts: `ErrorCode` in `paperforge/core/errors.py`.
- Use explicit return type annotations on Python production APIs and most tests: `def test_ok_is_true(self) -> None` in `tests/unit/core/test_result.py`, `def import_zotero_annotations_for_paper(...) -> ImportResult` in `paperforge/annotation/importer.py`.
- Use JSDoc object shapes for plugin testable helpers: `normalizeAnnotationExportRow()`, `makeAnnotationState()`, and `buildAnnotationOverlayMarks()` in `paperforge/plugin/src/testable.js`.

## Code Style

**Formatting:**
- Use Ruff format for Python, configured in `pyproject.toml`.
- Target Python 3.10 syntax and type hints: `target-version = "py310"` in `pyproject.toml`.
- Keep Python lines at or below 120 characters where practical: `line-length = 120` in `pyproject.toml`.
- Use double quotes for formatted Python output: `[tool.ruff.format] quote-style = "double"` in `pyproject.toml`.
- Preserve UTF-8 text handling for file IO and JSON: `ensure_ascii=False` in `paperforge/core/result.py`, `tests/conftest.py`, and `paperforge/worker/_utils.py`.

**Linting:**
- Use Ruff lint with rules `E`, `F`, `I`, `UP`, `B`, and `SIM` from `pyproject.toml`.
- Keep import sorting Ruff-compatible; `I` is selected in `pyproject.toml`.
- Do not apply strict test-file style cleanup opportunistically; `tests/**` has targeted per-file ignores in `pyproject.toml`.
- Pre-commit runs `ruff --fix` and `ruff-format` from `.pre-commit-config.yaml`.
- `paperforge/skills` is excluded from Ruff in `pyproject.toml`; avoid using it as a style reference for runtime code.

## Import Organization

**Order:**
1. Future annotations first when used: `from __future__ import annotations` appears in `paperforge/core/result.py`, `paperforge/cli.py`, and most tests.
2. Standard library imports next: `json`, `sqlite3`, `subprocess`, `Path`, `dataclass`.
3. Third-party imports next: `pytest`, `responses` in tests, external package imports in runtime modules.
4. Local `paperforge.*` imports last: `paperforge.core.errors`, `paperforge.annotation.schema`, `paperforge.config`.

**Path Aliases:**
- Python uses package imports from the repo root, not aliases: `from paperforge.core.result import PFError, PFResult` in `tests/unit/core/test_result.py`.
- Tests add the repository root to `sys.path` in `tests/conftest.py`; use package imports after that instead of relative path hacks.
- Plugin code uses CommonJS `require()` in `paperforge/plugin/src/testable.js` and TypeScript-style config imports only in `paperforge/plugin/vitest.config.ts`.

## Error Handling

**Patterns:**
- Use `PFResult` / `PFError` envelopes for stable CLI JSON contracts. `PFResult.to_dict()` in `paperforge/core/result.py` emits `ok`, `command`, `version`, `data`, and `error` consistently.
- Use `ErrorCode` enum values for machine-readable errors. Add narrow codes to `paperforge/core/errors.py` rather than string literals scattered across commands.
- Keep unknown forward-compatible error codes graceful: `ErrorCode._missing_()` in `paperforge/core/errors.py` returns `ErrorCode.UNKNOWN`.
- Return structured result objects for batch workflows: `ImportResult` in `paperforge/annotation/importer.py` tracks `inserted`, `updated`, `unchanged`, `stale`, and `skipped`.
- Catch expected data/import failures at row granularity when partial success is valid: `import_zotero_annotations_for_paper()` catches `AnnotationImportError` and increments `skipped` in `paperforge/annotation/importer.py`.
- For plugin UI helpers, return stable `{ ok, ..., reason }` or state objects instead of throwing for user-facing invalid input: `extractVaultPdfPath()`, `resolveAnnotationPdfTarget()`, `parseAnnotationPositionJson()` in `paperforge/plugin/src/testable.js`.

## Logging

**Framework:** Python `logging`; plugin helpers mostly return error objects.

**Patterns:**
- Use module loggers in runtime modules: `logger = logging.getLogger(__name__)` in `paperforge/worker/_utils.py`.
- Configure CLI logging centrally through `configure_logging` imported in `paperforge/cli.py`.
- Log recoverable operational failures as warnings when returning a boolean status: `install_obsidian_plugin()` in `paperforge/worker/_utils.py`.
- Tests usually assert returned output and state rather than logging side effects: `tests/cli/test_json_contracts.py`, `tests/chaos/test_network_failures.py`.

## Comments

**When to Comment:**
- Use docstrings on public modules, public functions, fixtures, and test classes to describe contracts and safety boundaries: `paperforge/annotation/importer.py`, `tests/cli/conftest.py`, `tests/unit/core/test_result.py`.
- Use section comments to separate dense command, import, or test-contract blocks: `paperforge/cli.py`, `paperforge/annotation/importer.py`, `tests/unit/annotation/test_service_contracts.py`.
- Use inline comments for safety-relevant or compatibility decisions, such as test-patchable worker stubs in `paperforge/cli.py` and read-only Zotero import guarantees in `paperforge/annotation/importer.py`.

**JSDoc/TSDoc:**
- Plugin helper functions use JSDoc for parameters and return object shapes: `loadAnnotationsForPaper()`, `buildPaperPdfCandidates()`, `buildAnnotationPopoverViewModel()` in `paperforge/plugin/src/testable.js`.
- Keep plugin JSDoc focused on input/output contracts and UI state guarantees.

## Function Design

**Size:** Prefer small typed helpers around a larger orchestration function when the workflow is stateful.
- Example: `paperforge/annotation/importer.py` splits `_enrich_annotation()`, `_upsert_annotation()`, and `import_zotero_annotations_for_paper()`.
- Example: `paperforge/plugin/src/testable.js` isolates pure helpers such as `buildAnnotationStatusArgs()` and `normalizeAnnotationColor()` for Vitest coverage.

**Parameters:** Pass explicit dependencies when testability or safety matters.
- Annotation import receives both Zotero and PaperForge database handles/paths explicitly in `paperforge/annotation/importer.py`.
- Plugin subprocess and filesystem helpers accept injected `_fs`, `_execFileSync`, `_spawn`, or `runSubprocessFn` dependencies in `paperforge/plugin/src/testable.js`.
- CLI subprocess tests pass environment overrides through fixtures in `tests/cli/conftest.py`.

**Return Values:** Prefer explicit contracts over implicit side effects.
- Runtime commands should produce `PFResult`-compatible dictionaries/JSON where CLI output is consumed by the plugin: `paperforge/core/result.py`, `tests/cli/test_json_contracts.py`.
- Data import workflows should return count/result dataclasses: `ImportResult` in `paperforge/annotation/importer.py`.
- Plugin view-model helpers should return complete state objects with defaults filled in: `makeAnnotationState()` in `paperforge/plugin/src/testable.js`.

## Module Design

**Exports:** Use narrow modules grouped by subsystem.
- Core contracts live in `paperforge/core/result.py` and `paperforge/core/errors.py`.
- CLI parsing and dispatch live in `paperforge/cli.py`.
- Annotation DB/import/probe logic lives in `paperforge/annotation/`.
- Memory/vector logic lives in `paperforge/memory/`.
- Worker operations live in `paperforge/worker/`.
- Plugin pure/testable functions are exported via `module.exports` in `paperforge/plugin/src/testable.js`.

**Barrel Files:** Minimal package markers are used.
- `paperforge/__init__.py` exposes package identity/version.
- Subpackage `__init__.py` files such as `paperforge/annotation/__init__.py` and `tests/unit/__init__.py` are lightweight; import concrete modules directly when adding code.

---

*Convention analysis: 2026-07-02*
