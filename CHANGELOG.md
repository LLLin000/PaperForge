# Changelog

All notable changes to PaperForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [1.4.17rc1] — 2026-05-07

### Added

- **Upgrade migration safeguards**: legacy flat notes migrated even without pre-existing canonical index; legacy `do_ocr`/`analyze` control flags preserved from `library-records` including explicit false values; already-migrated workspace notes reconciled on subsequent sync
- **Non-canonical filename migration**: legacy files named only by key (`LEG001.md`) correctly migrate via frontmatter title

### Changed

- **Index path integrity**: `fulltext_path` and `deep_reading_path` in canonical index only advertised when backing files actually exist — consumers (dashboard, context, lifecycle) no longer see false-ready assets
- **Python >= 3.10 now required** (was 3.8 in setup_wizard, 3.9 in plugin UI). All setup checks, plugin notices, and documentation aligned
- **TUI removed**: `paperforge setup` without `--headless` now prints redirect message; all Textual classes, imports, and the `textual` dependency purged from `pyproject.toml`
- **Library-records fully deprecated**: zero residual references in production code and 10 command file copies; `paperforge status` label now `formal_notes` not `library_records`
- **Config-resolved paths**: 5 workspace-path index fields and 11 downstream consumers use user's configured `literature_dir` instead of hardcoded `"Literature/"`; env var typo `PAPERFORGERATURE_DIR` fixed to `PAPERFORGE_LITERATURE_DIR`

### Fixed

- **OCR state machine tests**: ambient token isolation and write-through mocking restored for deterministic offline test runs (2 previously-failing tests now pass)
- **Repair blind spots**: condition 4 (`ocr_status: pending` vs `meta done/failed`) now detected; all 6 divergence types handled or explicitly warned; bare `except:pass` replaced with `logger.warning()`

### Security

- **Module hardening**: discussion.py — file locking (filelock), markdown character escaping, UTC timestamps; main.js — API key via environment variable not CLI args, `createEl()` instead of `innerHTML`; asset_state.py — workspace integrity checks before `/pf-deep` recommendation; status.py — empty dicts instead of null for JSON consumers

### Merged milestones

v1.6 (AI-ready literature asset foundation) through v1.11 (merge gate remediation) consolidated into a single merge to master.

## [1.4.13] — 2026-05-01

### Added

- **Four-state OCR display**: Pending (do_ocr:true, not started) / Processing (queued/running) / Done / Failed — with pulse animation on Processing count
- **do_ocr-aware status counting**: `paperforge status` now scans library records for `do_ocr:true` items and reports them even before any meta.json is written
- **PDF sanitize fallback**: when provider returns `resultUrl 404` (result object missing), sets `needs_sanitize` and retries with fitz-rewritten PDF
- **8 edge case stress tests**: empty queue, corrupt meta.json, max_items=1 throttling, upload timeout, unknown API state, full pending→done cycle, mixed-state queue, done_incomplete→pending + error reset

### Changed

- **OCR pipeline**: combined upload + poll into a single loop — uploads up to `max_items` concurrency, polls all queued, decrements active count on completion, continues until all done
- **Error handling**: `error` status resets to `pending` on a fresh `paperforge ocr` run (clears job_id, retry_count=0); `done_incomplete` → pending (retry_count=0)
- **API "failed" state** treated as transient — kept as `queued` for retry instead of terminal `error`
- **Status classification**: `queued`, `running`, `processing` all count as "Processing"; `pending` counts separately; no more misclassification as `failed`
- **Zombie cleanup**: stale `queued`/`running` jobs (>30 min) reset to `pending` at start of each run
- **Plugin sidebar caching**: `_cachedStats` stores last successful status; panel renders cached data immediately on reopen, refreshes in background — no more blank Loading
- **Metric cards cleared on each render**: fixed duplicate card bug on refresh

### Fixed

- `ensure_ocr_meta` handles corrupt `meta.json` gracefully (falls back to `{}` instead of crashing `run_ocr`)
- `queued`/`running` no longer counted as `failed` in status output
- Sidebar "Loading..." no longer persists after data loads

### Performance

- `status.py` startup optimized by scanning only `do_ocr:true` records instead of all meta.jsons

---

## [1.4.12] — 2026-04-30

### Added

- Real-time OCR progress in Dashboard via background refresh timer (4s polling during `_runAction`)

### Fixed

- Dashboard `exec` replaced with `spawn` for actions, enabling live progress output
- Loading flicker on sidebar reopen

---

## [1.4.11] — 2026-04-30

### Fixed

- Author field missing `header_title` key causing blank panel in some locale setups
- Language detection fallback, config summary i18n gaps
- Inline all i18n strings into `main.js` (removed `require/` dependency for side-by-side loading)
- Corrected `versions.json` minAppVersion for plugin compatibility

---

### Added

- Persistent OCR polling: `paperforge ocr` now waits for all submitted jobs to complete before returning
- `postprocess-pass2` validation command for /pf-deep: checks figure order, image bounds, empty blocks, missing sub-headings, duplicates, and extra figures
- Fixed sub-headings in figure/table callout blocks (skeleton generation): AI fills pre-defined structure instead of creating free-form content
- One-click install script (`scripts/install-paperforge.ps1`)
- `paperforge setup` CLI command for the setup wizard
- OpenCode command files packaged for pip installation

### Fixed

- `paperforge update` now correctly detects local version from pip metadata
- Missing `GITHUB_REPO` import in `update.py` (caused "无法获取远程版本")
- `paperforge.json` version synced to match release (was stuck at 1.2.0)
- `zotero_dir` added to `paperforge_paths()` for PDF resolution in OCR pipeline
- OCR diagnostic L2 probes use POST instead of GET (PaddleOCR rejects GET)
- L3 diagnostic skips schema validation when no file is uploaded
- L2 accepts HTTP 400 as reachable (PaddleOCR rejects bare POST without fileUrl)
- Skills prompt and chart-reading `.md` files now included in pip package
- `PaperForge.base` removed (duplicated Literature Hub)
- `setup_wizard.py` moved into the `paperforge` package for pip-installed access
- Test OCR preflight and state machine tests mock `requests.get` to prevent real network calls
- Persistent poll reduced to 20 cycles (configurable via `PAPERFORGE_POLL_MAX_CYCLES`)
- `VaultStep.__init__` missing `step_id` and `checker` in `super()` call
- BBT JSON field extraction for `first_author`, `journal`, `impact_factor`
- PDF storage subdirectory resolution for `storage:KEY/file.pdf` paths
- Base view columns (`first_author`, `journal`, `impact_factor`) added to all views

### Changed

- `/pf-deep` skill refactored: `ld_deep.py` skeleton now includes 6 fixed sub-headings per figure callout block
- `prompt_deep_subagent.md` rewritten from 297 to 103 lines (directive command style)
- OC `doctor` renamed to unified `ocr` command with auto-diagnose

## [1.4.0] — 2026-04-27

### Added

- Structured logging with `PAPERFORGE_LOG_LEVEL` environment variable support
- `paperforge/worker/_utils.py` leaf module consolidating `read_json`, `write_json`, and shared path utilities
- `paperforge/worker/_progress.py` and `paperforge/worker/_retry.py` utility modules
- `auto_analyze_after_ocr` config option in `paperforge.json` (opt-in, default `false`)
- Pre-commit hooks: Ruff lint + format, YAML/TOML validation, end-of-file fixer, trailing-whitespace fixer, consistency audit
- Consistency audit script (`scripts/consistency_audit.py`): detects duplicate utility functions across worker modules
- CHANGELOG.md and CONTRIBUTING.md at vault root
- OCR error context in library-record frontmatter

### Changed

- Logging: `print()` replaced with `logging.getLogger(__name__)` in all worker modules — user-facing CLI `print()` preserved
- Monolithic `literature_pipeline.py` (4041 lines) refactored into 7 focused modules under `paperforge/worker/`
- Deep-reading queue: unified `scan_library_records()` from `_utils.py` replaces disparate record iteration patterns
- Config access: all worker modules use `from paperforge.config import load_vault_config`, `paperforge_paths`
- Re-exports preserved with `# Re-exported from _utils.py` comments for backward compatibility
- `paperforge.json` version bumped to 1.4.0

### Fixed

- Dead delegation wrappers removed from `paperforge/worker/` modules
- Circular import risk between `sync.py` and `ocr.py` — `_utils.py` enforced as leaf module
- Redundant function definitions eliminated across worker modules

## [1.3.0] — 2026-04-24

### Added

- Zotero path normalization: `_normalize_attachment_path()` handles all 3 BBT export formats (absolute Windows, `storage:` prefix, bare relative)
- Multi-attachment support: `_identify_main_pdf()` with hybrid strategy (title → size → shortest title)
- `obsidian_wikilink_for_pdf()` — generates standard `[[relative/path]]` wikilink from any BBT path format
- New library-record frontmatter fields: `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `supplementary` (wikilink array), `path_error`
- `paperforge doctor` enhanced: junction detection, path validation, mklink recommendation
- `paperforge repair --fix-paths` subcommand for automatic path error correction
- `paperforge status` shows `path_error` statistics
- 25 new test cases for path resolution

### Changed

- 4041-line `literature_pipeline.py` split into 7 focused modules under `paperforge/worker/`
- Module structure: `sync.py` (~1440 lines), `ocr.py` (~1377 lines), `repair.py`, `status.py`, `deep_reading.py`, `base_views.py`, `update.py`
- `pipeline/` and `skills/` directories removed after confirming zero import references
- Skills migrated to `paperforge/skills/literature-qa/`
- 40+ import paths updated across codebase and tests
- PDF path resolution now happens at `load_export_rows()` stage (not downstream)

### Fixed

- BBT bare path format (`KEY/KEY.pdf`) now resolved correctly against Zotero storage directory
- Junction/symlink resolution integrated into path absolutization
- Path error recovery via `repair --fix-paths`

## [1.2.0] — 2026-04-24

### Added

- Unified CLI: `paperforge sync` replaces `selection-sync` + `index-refresh`
- Unified Agent prefix: `/pf-deep`, `/pf-paper`, `/pf-ocr`, `/pf-sync`, `/pf-status` replace legacy `/LD-*` and `/lp-*` namespaces
- Shared command modules under `paperforge/commands/`
- `paperforge/__main__.py` entry point
- `python -m paperforge` fallback for CLI invocation
- Architecture documentation (`docs/ARCHITECTURE.md`)
- Migration guide (`docs/MIGRATION-v1.2.md`)
- `paperforge.json` configuration file with update channel, path configuration

### Changed

- Python package renamed from `paperforge-lite` to `paperforge`
- CLI entry point consolidated to single `paperforge` command
- All Agent commands migrated to `/pf-*` namespace (old names remain compatible)
- Path configuration moved from hardcoded constants to `paperforge.json`
- README, INSTALLATION.md, AGENTS.md updated for new command syntax

### Fixed

- CLI dispatch consistency — all subcommands now share argument parsing via `paperforge/config.py`
- Legacy command compatibility layer for smooth migration

## [1.1.0] — 2026-04-24

### Added

- Interactive setup wizard (`setup_wizard.py`) with step-by-step vault configuration
- `paperforge doctor` diagnostic command with per-domain JSON export validation
- `paperforge repair` command for three-way state divergence detection and fix
- `paperforge deep-reading` queue viewer with `--verbose` mode
- OCR state machine validation: `validate_ocr_meta()` ensures state consistency
- Deep reading prepare with rollback on failure
- Sandbox smoke test suite (14 tests covering setup → sync → OCR → deep-reading)
- Rollback pattern for `prepare_deep_reading` (tracks written files, restores on exception)
- PDF resolver with absolute, relative, and junction path support

### Changed

- Wizard UX: `--vault` prefill, no terminal stall, automatic `pip install -e .`
- `paperforge paths --json` emits correct paths matching command documentation
- Doctor validates importability, env var consistency (`PADDLEOCR_API_TOKEN`), and deployed worker paths
- OCR doctor distinguishes HTTP 405 from bad URL
- Frontmatter: `first_author` and `journal` populated from BBT export

### Fixed

- Setup stalls in interactive environments
- Contradictory diagnostics between doctor and pipeline
- Unresolved mock Zotero PDFs in sandbox
- `/LD-deep` prepare partial writes on failure (now rolls back)

## [1.0.0] — 2026-04-23

### Added

- Initial MVP release
- Zotero sync: `selection-sync` and `index-refresh` phases
- OCR pipeline via PaddleOCR-VL API with PDF upload, fulltext extraction, and chart/image segmentation
- Chart type intelligent recognition (20 chart types)
- Chart quality review guidelines (14 chart types with professional checklists)
- Deep reading via Keshav three-pass methodology (`/LD-deep` Agent command)
- Quick paper summary (`/pf-paper` Agent command)
- Obsidian Base view generation for literature queue management
- Better BibTeX JSON export integration
- Zotero storage path sharing via junction/symlink
- Auto-update system (`python literature_pipeline.py --vault . update`)
- Setup wizard with `.env` configuration for PaddleOCR API key
- AGENTS.md with command reference and architecture overview
- 30+ tests covering core functionality
