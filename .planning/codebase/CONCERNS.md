# Codebase Concerns

**Analysis Date:** 2026-07-02

## Tech Debt

**Frozen worker modules still contain active business logic:**
- Issue: `paperforge/worker/sync.py` explicitly declares a freeze line at `paperforge/worker/sync.py:3` through `paperforge/worker/sync.py:8`, but the file still owns candidate adapters, workspace migration, path mutation, index refresh, and output generation. It remains one of the largest source files at 1126 lines.
- Files: `paperforge/worker/sync.py`, `paperforge/services/sync_service.py`, `paperforge/adapters/obsidian_frontmatter.py`, `paperforge/adapters/zotero_paths.py`
- Impact: New sync behavior can easily land in the frozen worker because callers and tests still exercise it directly. This increases regression risk for path handling, legacy migration, and generated note frontmatter.
- Fix approach: Move remaining non-wrapper functions from `paperforge/worker/sync.py` into `paperforge/services/sync_service.py` or adapter modules. Keep `paperforge/worker/sync.py` as CLI-compatible orchestration only, then tighten ruff ignores for this file in `pyproject.toml`.

**Large bundled plugin entrypoint blocks isolated maintenance:**
- Issue: `paperforge/plugin/main.js` is 6090 lines and mixes Obsidian lifecycle, dashboard rendering, annotation UI, runtime detection, memory rebuild, CLI spawning, auto-update, and settings validation in one file.
- Files: `paperforge/plugin/main.js`, `paperforge/plugin/src/testable.js`, `paperforge/plugin/tests/annotation-main-runtime.test.mjs`, `paperforge/plugin/tests/runtime.test.mjs`
- Impact: UI changes and runtime changes share the same file, making review hard and increasing the chance of accidental breakage in unrelated plugin surfaces. Tests rely on helper extraction in `paperforge/plugin/src/testable.js`, so behavior can drift between extracted helpers and `paperforge/plugin/main.js`.
- Fix approach: Split stable domains into modules under `paperforge/plugin/src/`: runtime resolution, annotation view/controller, memory panel, auto-update, and settings validation. Treat `paperforge/plugin/main.js` as generated/bundled output and document the build path.

**Generated or dependency artifacts are present in the working tree:**
- Issue: `paperforge/plugin/node_modules/` exists locally under the plugin directory, even though it is not tracked by `git ls-files`. Size scans accidentally include third-party code unless every command excludes it.
- Files: `paperforge/plugin/node_modules/`, `paperforge/plugin/package-lock.json`, `.gitignore`
- Impact: Mapper, audit, and ad hoc grep commands produce noisy results and can mask first-party issues. Local dependency contents may also affect scripts that recurse through `paperforge/plugin`.
- Fix approach: Keep `paperforge/plugin/node_modules/` ignored and excluded from all repo scanning scripts. Prefer `rg --glob '!paperforge/plugin/node_modules/**'` and add the same exclusion to maintenance scripts if they scan source trees.

**Ruff exceptions encode long-lived debt:**
- Issue: `pyproject.toml` has per-file ignores for undefined names, long lines, simplification rules, and bugbear rules across core worker files and all tests.
- Files: `pyproject.toml`, `paperforge/worker/update.py`, `paperforge/worker/sync.py`, `paperforge/worker/ocr.py`, `paperforge/worker/repair.py`, `paperforge/ocr_diagnostics.py`, `tests/**`
- Impact: Real defects can hide behind broad ignores, especially `F821` in `paperforge/worker/sync.py` and `paperforge/worker/update.py`.
- Fix approach: Retire ignores one file at a time when touching those modules. Start with `paperforge/worker/update.py` and `paperforge/worker/sync.py` because undefined-name ignores are highest risk.

## Known Bugs

**Auto-update path has unresolved imports in `paperforge/worker/update.py`:**
- Symptoms: `_remote_version()` and `update_via_zip()` call `urllib.request.Request` and `urllib.request.urlopen`, but the module imports `urllib.parse` only. These paths raise `AttributeError: module 'urllib' has no attribute 'request'` when executed.
- Files: `paperforge/worker/update.py`
- Trigger: Run the update flow that calls `_remote_version()` or `update_via_zip()`.
- Workaround: Use pip/git update commands outside this module, or add `import urllib.request` before using the update command.

**Plugin documentation references a missing i18n file:**
- Symptoms: `AGENTS.md` says plugin i18n lives in `paperforge/plugin/i18n.js`, but `rg --files` shows no `paperforge/plugin/i18n.js`. Translation tables appear embedded in `paperforge/plugin/main.js`.
- Files: `AGENTS.md`, `paperforge/plugin/main.js`
- Trigger: Follow the agent guide and try to add strings to `paperforge/plugin/i18n.js`.
- Workaround: Update strings in the actual translation structure in `paperforge/plugin/main.js` until the i18n module is extracted.

**Encoding corruption appears in docs and user-facing strings:**
- Symptoms: Several files display mojibake such as `鈥?`, `鏇存柊`, and malformed Chinese strings in CLI/plugin messages.
- Files: `AGENTS.md`, `pyproject.toml`, `paperforge/plugin/main.js`, `paperforge/worker/update.py`, `paperforge/commands/annotation.py`
- Trigger: Open docs or run commands that emit affected messages, including annotation errors and update logs.
- Workaround: Prefer JSON output for machine consumers. For user-facing work, repair file encodings from original UTF-8 sources before editing nearby strings.

## Security Considerations

**Plugin auto-update installs Python packages from network sources:**
- Risk: The Obsidian plugin can spawn Python and run pip upgrade commands, falling back from PyPI to a GitHub URL. This executes downloaded package code in the user's Python environment.
- Files: `paperforge/plugin/main.js`, `paperforge/worker/update.py`, `scripts/install-paperforge.ps1`, `scripts/update-paperforge.ps1`
- Current mitigation: Commands use argument arrays (`spawn`/`execFile` or `subprocess.run` lists), which limits shell injection. `paperforge/worker/update.py` checks for dirty git state before `git pull`.
- Recommendations: Require explicit user confirmation before network install/update from `paperforge/plugin/main.js`, pin or verify package versions, show the exact source (`paperforge==version` or Git URL), and log update results without exposing tokens.

**HTML assignment is used for status rendering:**
- Risk: Several plugin settings/status branches assign `innerHTML` with interpolated message variables. Current values appear mostly constant, but this pattern is easy to reuse with user-provided paths or API messages.
- Files: `paperforge/plugin/main.js`
- Current mitigation: Annotation UI has tests and comments enforcing textContent for user-facing annotation text in `paperforge/plugin/tests/annotation-main-runtime.test.mjs`.
- Recommendations: Replace status `innerHTML` assignments with `createEl()`/`textContent` consistently. Keep `innerHTML` only for hard-coded SVG/icon markup and isolate those helpers.

**Secrets are read from plain files and plugin settings:**
- Risk: OCR and vector API keys are read from `.env` and Obsidian plugin settings. The vector API path falls back to `OPENAI_API_KEY` in `.env`.
- Files: `paperforge/worker/ocr.py`, `paperforge/ocr_diagnostics.py`, `paperforge/memory/vector_db.py`, `paperforge/setup_wizard.py`, `paperforge/config.py`
- Current mitigation: `.env` contents are not committed in this scan, and config comments state that secrets are not loaded by `paperforge/config.py`.
- Recommendations: Avoid logging full subprocess stdout/stderr around commands that may inherit secret-bearing environments. Keep `.env` parsing centralized and redact keys in diagnostic outputs.

**Zip update extraction lacks path traversal checks:**
- Risk: `zipfile.ZipFile.extractall()` extracts remote archive contents directly into a temp directory before scanning updateable paths.
- Files: `paperforge/worker/update.py`
- Current mitigation: Extraction target is a temporary directory and update application later filters `UPDATEABLE_PATHS`.
- Recommendations: Replace `extractall()` with safe member extraction that rejects absolute paths and `..` path segments. Keep the later `UPDATEABLE_PATHS` filter as a second guard.

## Performance Bottlenecks

**OCR worker performs broad filesystem scans and serial network polling:**
- Problem: `paperforge/worker/ocr.py` scans OCR metadata directories, loads all export rows, polls active jobs, downloads result payloads, postprocesses, and refreshes indexes in one long run.
- Files: `paperforge/worker/ocr.py`, `paperforge/worker/asset_index.py`, `paperforge/worker/sync.py`
- Cause: State discovery is filesystem-driven and network polling is handled serially in the main worker loop. On large vaults, every run can touch many metadata files and export JSON files.
- Improvement path: Maintain an explicit queue/index of active OCR keys, separate polling from submission, and refresh only changed index entries using `paperforge/worker/asset_index.py` where possible.

**Vector embedding loads large local models synchronously:**
- Problem: Local embedding mode loads `sentence-transformers` and the model `BAAI/bge-small-en-v1.5` in-process, then encodes chunks synchronously.
- Files: `paperforge/memory/vector_db.py`, `paperforge/commands/embed.py`
- Cause: Model caching is process-local globals (`_cached_model`, `_cached_model_name`), so each new CLI process pays import/model startup costs.
- Improvement path: Keep the current lazy import, but expose progress and cancellation for long builds, persist build state through `paperforge/memory/vector_db.py`, and prefer batch sizes that do not block plugin-triggered commands.

**Plugin command surface can block on long subprocesses:**
- Problem: Plugin functions trigger Python commands for memory rebuild, runtime sync, and auto-update from UI event handlers.
- Files: `paperforge/plugin/main.js`
- Cause: The UI layer owns subprocess orchestration and state rendering directly.
- Improvement path: Centralize subprocess execution with timeouts, cancellation, progress events, and user-visible failure states. Keep heavy tasks outside rendering methods.

## Fragile Areas

**OCR status state machine resets failures back to pending:**
- Files: `paperforge/worker/ocr.py`, `tests/test_ocr_state_machine.py`, `tests/chaos/test_network_failures.py`
- Why fragile: Network/API schema errors during polling and result postprocessing set `ocr_status` back to `pending` and increment retry counters. This preserves retry behavior but can hide permanent API/schema failures as ordinary pending work.
- Safe modification: Keep retry metadata (`last_error`, `retry_count`, `raw_response`) intact and add terminal failure thresholds before changing retry behavior.
- Test coverage: There is substantial state-machine and chaos coverage in `tests/test_ocr_state_machine.py` and `tests/chaos/test_network_failures.py`; add regression tests for any status transition changes.

**Workspace migration mutates user notes and copies OCR assets:**
- Files: `paperforge/worker/sync.py`, `tests/test_migration.py`, `tests/test_base_preservation.py`
- Why fragile: `migrate_to_workspace()` reads frontmatter, creates new workspace directories, renames old candidates, writes updated frontmatter, and copies `fulltext.md`. Multiple broad `except Exception: pass` blocks can silently skip partial migration work.
- Safe modification: Add dry-run reporting before new migration writes. Preserve old note content and frontmatter exactly unless a targeted field update is required.
- Test coverage: Migration tests exist in `tests/test_migration.py`; expand with partial-failure and rollback cases before changing this flow.

**Annotation import/export spans SQLite, Zotero schema, and plugin consumers:**
- Files: `paperforge/annotation/db.py`, `paperforge/annotation/schema.py`, `paperforge/annotation/importer.py`, `paperforge/commands/annotation.py`, `paperforge/plugin/tests/annotation-bridge.test.mjs`
- Why fragile: Annotation IDs encode Zotero library, attachment, parent, and annotation keys. CLI JSON contracts are consumed by the plugin tests.
- Safe modification: Change schema through explicit migrations in `paperforge/annotation/schema.py`, keep CLI JSON backwards-compatible, and run both Python annotation tests and plugin annotation tests.
- Test coverage: Good targeted coverage exists under `tests/unit/annotation/`, `tests/cli/test_annotation_*.py`, and `paperforge/plugin/tests/annotation-*.test.mjs`.

**Config hierarchy supports both nested and legacy keys:**
- Files: `paperforge/config.py`, `paperforge/setup_wizard.py`, `tests/test_config.py`, `fixtures/snapshots/paths_json/default_config.json`
- Why fragile: `paperforge/config.py` resolves paths from explicit overrides, environment variables, nested `vault_config`, legacy top-level keys, and defaults. Path behavior affects every worker and plugin subprocess.
- Safe modification: Add tests in `tests/test_config.py` for any new key or precedence rule. Do not mutate `os.environ` outside `load_simple_env()`.
- Test coverage: `tests/test_config.py` is broad; retain snapshot compatibility when updating defaults.

## Scaling Limits

**Vault filesystem is the primary state bus:**
- Current capacity: State is spread across Markdown frontmatter, `paperforge.json`, Better BibTeX exports, OCR metadata JSON, SQLite indexes, ChromaDB vectors, and Obsidian plugin settings.
- Limit: Large vaults increase scan cost and make partial failure recovery harder because the canonical state for one paper lives in several files.
- Scaling path: Treat `paperforge/indexes/paperforge.db` and annotation/vector indexes as query accelerators, and define one canonical state transition owner per domain: sync, OCR, annotation, memory.

**Single-process CLI workers limit concurrency:**
- Current capacity: OCR polling/submission, sync, memory embedding, and update flows execute as CLI subprocesses.
- Limit: Long-running operations can overlap if triggered from plugin UI and terminal, causing stale status, file lock contention, or duplicate work.
- Scaling path: Use file locks consistently around write-heavy operations, especially OCR metadata, index refresh, vector build state, and annotation DB writes. `filelock` is available in dependencies but should be applied consistently.

## Dependencies at Risk

**Unpinned Python dependencies:**
- Risk: Runtime dependencies use lower bounds only (`requests>=2.31.0`, `pymupdf>=1.23.0`, `pillow>=10.0.0`, `chromadb>=0.5.0`, `sentence-transformers>=3.0.0`, `openai>=1.0.0`).
- Impact: Upstream breaking changes can alter OCR PDF rendering, vector storage, embeddings, or OpenAI API behavior without a lockfile.
- Migration plan: Add a tested constraints file for release builds while keeping broad ranges in `pyproject.toml` if library compatibility is desired.

**PaddleOCR API schema coupling:**
- Risk: OCR code expects response fields such as `data.jobId`, `data.state`, and `resultUrl.jsonUrl`.
- Impact: Provider response changes move papers back to pending and can stall OCR without a clear terminal state.
- Migration plan: Keep schema validation in `paperforge/ocr_diagnostics.py`, add fixture-driven tests under `fixtures/ocr/`, and version the provider adapter in `paperforge/worker/ocr.py`.

**Obsidian plugin runtime dependency drift:**
- Risk: Plugin tests use `vitest`, `jsdom`, `obsidian`, and `obsidian-test-mocks`, while production runs in Obsidian's Electron environment.
- Impact: DOM or API behavior can pass jsdom tests but fail in Obsidian.
- Migration plan: Keep pure helpers in `paperforge/plugin/src/testable.js`, but add manual/runtime checklist coverage for `paperforge/plugin/main.js` features that depend on Obsidian APIs.

## Missing Critical Features

**No obvious centralized operation lock for long-running workers:**
- Problem: OCR, sync, repair, vector build, and plugin-triggered update commands can all write under the same vault state tree.
- Blocks: Safe concurrent operation from Obsidian UI and terminal.
- Files: `paperforge/worker/ocr.py`, `paperforge/worker/sync.py`, `paperforge/worker/repair.py`, `paperforge/memory/vector_db.py`, `paperforge/plugin/main.js`

**No clear build contract for plugin source versus bundled entrypoint:**
- Problem: `paperforge/plugin/src/testable.js` contains testable helpers, but `paperforge/plugin/main.js` is the shipped entrypoint and appears manually maintained.
- Blocks: Safe modular plugin refactors and confidence that tests exercise shipped code.
- Files: `paperforge/plugin/main.js`, `paperforge/plugin/src/testable.js`, `paperforge/plugin/package.json`, `paperforge/plugin/vitest.config.ts`

## Test Coverage Gaps

**Update flows need direct regression coverage:**
- What's not tested: `_remote_version()`, `update_via_zip()`, safe zip extraction, pip fallback behavior, and plugin auto-update user consent.
- Files: `paperforge/worker/update.py`, `paperforge/plugin/main.js`, `scripts/update-paperforge.ps1`
- Risk: Update command failures are user-visible and can mutate installations.
- Priority: High

**Plugin settings/status HTML rendering needs XSS-oriented tests:**
- What's not tested: Settings validation branches around `desc.innerHTML` and status message rendering outside the annotation UI.
- Files: `paperforge/plugin/main.js`, `paperforge/plugin/tests/runtime.test.mjs`
- Risk: Future interpolated user-provided values could become unsafe HTML.
- Priority: Medium

**Concurrent write behavior lacks focused tests:**
- What's not tested: Two workers writing OCR metadata, vector build state, annotation DB, or index files at the same time.
- Files: `paperforge/worker/ocr.py`, `paperforge/memory/vector_db.py`, `paperforge/annotation/db.py`, `paperforge/worker/asset_index.py`
- Risk: Lost updates, corrupted JSON temp files, stale status, or duplicate queue work.
- Priority: Medium

**Encoding integrity is not guarded:**
- What's not tested: Chinese/English user-facing strings rendering correctly across docs, CLI output, plugin notices, and package metadata.
- Files: `AGENTS.md`, `pyproject.toml`, `paperforge/plugin/main.js`, `paperforge/commands/annotation.py`, `paperforge/worker/update.py`
- Risk: User-facing documentation and notices become unreadable after edits.
- Priority: Medium

---

*Concerns audit: 2026-07-02*
