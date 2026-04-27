# Changelog

All notable changes to PaperForge Lite are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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
