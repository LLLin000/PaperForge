# Technology Stack

**Analysis Date:** 2026-07-02

## Languages

**Primary:**
- Python >=3.10 - CLI engine, workers, setup wizard, data adapters, SQLite stores, OCR processing, memory/vector commands; declared in `pyproject.toml` and implemented under `paperforge/`.
- JavaScript CommonJS - Obsidian desktop plugin runtime in `paperforge/plugin/main.js`, with testable helper module `paperforge/plugin/src/testable.js`.

**Secondary:**
- TypeScript - Vitest config only in `paperforge/plugin/vitest.config.ts`.
- PowerShell - Windows installer helper in `scripts/install-paperforge.ps1`.
- Markdown/YAML/JSON - user-facing docs, command files, field registry, and runtime config in `README.en.md`, `paperforge/command_files/`, `paperforge/schema/field_registry.yaml`, `paperforge.json`, and `manifest.json`.

## Runtime

**Environment:**
- Python 3.10+ package runtime; CI validates with Python 3.11 in `.github/workflows/ci.yml`.
- Node.js 20 for plugin tests in `.github/workflows/ci.yml`.
- Obsidian desktop plugin runtime requires Obsidian `minAppVersion` 1.9.0 and `isDesktopOnly: true` in `manifest.json`.

**Package Manager:**
- Python: `pip`/setuptools; build backend is `setuptools.build_meta` in `pyproject.toml`.
- JavaScript: `npm`; lockfile present at `paperforge/plugin/package-lock.json`.
- Python lockfile: missing. Use version ranges from `pyproject.toml` or `requirements.txt`.

## Frameworks

**Core:**
- setuptools >=68.0 - Python package build backend in `pyproject.toml`.
- Obsidian plugin API - desktop UI, settings, commands, and vault access in `paperforge/plugin/main.js`; package metadata in `manifest.json` and `paperforge/plugin/manifest.json`.
- SQLite stdlib - durable local databases for memory and annotations in `paperforge/memory/db.py` and `paperforge/annotation/db.py`.
- ChromaDB >=0.5.0 - optional persistent vector index in `paperforge/memory/vector_db.py`.

**Testing:**
- pytest >=7.4.0 - Python unit/CLI/e2e/journey/chaos/audit/integration tests configured in `pyproject.toml`.
- pytest-snapshot, pytest-timeout, responses, pytest-mock, coverage - optional Python test dependencies in `pyproject.toml`.
- Vitest ^2.1.0 - Obsidian plugin tests configured by `paperforge/plugin/package.json` and `paperforge/plugin/vitest.config.ts`.
- jsdom ^25.0.0 and obsidian-test-mocks ^2.0.0 - DOM/Obsidian test harness for `paperforge/plugin/tests/`.

**Build/Dev:**
- Ruff >=0.4.0 - linting and formatting config in `pyproject.toml`; target `py310`, line length 120, double quotes.
- pre-commit - hook config in `.pre-commit-config.yaml`.
- GitHub Actions - CI, chaos CI, PyPI publish, and GitHub release workflows in `.github/workflows/`.

## Key Dependencies

**Critical:**
- `requests>=2.31.0` - HTTP client for PaddleOCR job submit/poll/result fetch in `paperforge/worker/ocr.py`.
- `pymupdf>=1.23.0` - imported as `fitz` for PDF rendering/sanitization in `paperforge/worker/ocr.py`.
- `pillow>=10.0.0` - image crop/cache handling for OCR figures in `paperforge/worker/ocr.py`.
- `pyyaml>=6.0` - YAML support for schema/config-style files declared in `pyproject.toml`.
- `filelock>=3.13.0` - cross-process filesystem locking declared in `pyproject.toml`.
- `tenacity>=8.2.0` - retry dependency declared in `pyproject.toml`; retry behavior is wrapped locally in `paperforge/worker/_retry.py`.
- `tqdm>=4.66.0` - progress display, surfaced through `paperforge/worker/_progress.py` and used by OCR worker code.

**Infrastructure:**
- `chromadb>=0.5.0` - optional vector persistence; lazy-imported by `paperforge/memory/vector_db.py`.
- `sentence-transformers>=3.0.0` - optional local embeddings; default model is `BAAI/bge-small-en-v1.5` in `paperforge/memory/vector_db.py`.
- `openai>=1.0.0` - optional API embedding mode in `paperforge/memory/vector_db.py`.
- `obsidian` npm package ^1.12.0 - plugin API types/runtime mocks for tests in `paperforge/plugin/package.json`.
- `jsdom` and `obsidian-test-mocks` - plugin test dependencies in `paperforge/plugin/package.json`.
- `textual>=0.47.0` appears in `requirements.txt` but is not listed in `pyproject.toml`; treat it as legacy/manual install residue unless implementation imports require it.

## Configuration

**Environment:**
- Use `paperforge/config.py` as the source of truth for vault/path configuration. Precedence is explicit overrides, `PAPERFORGE_*` env vars, nested `paperforge.json` `vault_config`, legacy top-level `paperforge.json` keys, then defaults.
- Vault discovery uses `PAPERFORGE_VAULT` or nearest parent containing `paperforge.json` in `paperforge/config.py`.
- Default vault directories are `System`, `Resources`, `Literature`, `LiteratureControl`, `Bases`, `.opencode/skills`, and `.opencode/command` in `paperforge/config.py`.
- OCR reads `PADDLEOCR_API_TOKEN`, optional `PADDLEOCR_API_TOKEN_USER`, `PADDLEOCR_JOB_URL`, `PADDLEOCR_MODEL`, `PADDLEOCR_MAX_ITEMS`, `PAPERFORGE_POLL_INTERVAL`, and `PAPERFORGE_POLL_MAX_CYCLES` in `paperforge/worker/ocr.py`.
- Vector API mode reads plugin settings from `.obsidian/plugins/paperforge/data.json`, `OPENAI_API_KEY` from `.env`, and env overrides `VECTOR_DB_API_KEY`, `VECTOR_DB_API_BASE`, and `VECTOR_DB_API_MODEL` in `paperforge/memory/vector_db.py`.
- Local vector model download can use `HF_ENDPOINT` and `HF_TOKEN` in `paperforge/memory/vector_db.py`.
- Do not read `.env` contents during mapping or docs generation; `.env` is a protected path in `paperforge.json`.

**Build:**
- Python package metadata and tool config: `pyproject.toml`.
- Runtime user config template/defaults: `paperforge.json`.
- Obsidian release manifest: `manifest.json`; packaged plugin manifest also lives at `paperforge/plugin/manifest.json`.
- Plugin npm metadata: `paperforge/plugin/package.json`.
- Plugin npm lockfile: `paperforge/plugin/package-lock.json`.
- CI: `.github/workflows/ci.yml`, `.github/workflows/ci-chaos.yml`.
- Publish/release: `.github/workflows/publish.yml`, `.github/workflows/release.yml`.

## Platform Requirements

**Development:**
- Python 3.10+ with editable install via `pip install -e ".[test]"` from `pyproject.toml`.
- Node.js 20 and `npm ci` under `paperforge/plugin/` for plugin tests.
- Obsidian desktop for manual plugin validation; plugin runtime calls Python through subprocess helpers in `paperforge/plugin/main.js`.
- Zotero Desktop plus Better BibTeX JSON export for realistic sync workflows; BBT parsing lives in `paperforge/adapters/bbt.py`.
- PaddleOCR API token for live OCR; tests simulate failures through env vars and mocks under `tests/chaos/`.

**Production:**
- Python package published to PyPI by `.github/workflows/publish.yml`.
- Obsidian plugin release assets are `paperforge/plugin/main.js`, `paperforge/plugin/styles.css`, `paperforge/plugin/manifest.json`, and `paperforge/plugin/versions.json` in `.github/workflows/publish.yml`.
- Runtime target is a local Obsidian vault with PaperForge directories under the configured vault root; persistent data lives under `<system_dir>/PaperForge/` as resolved by `paperforge/config.py`.

---

*Stack analysis: 2026-07-02*
