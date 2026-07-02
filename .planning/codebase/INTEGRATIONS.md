# External Integrations

**Analysis Date:** 2026-07-02

## APIs & External Services

**OCR:**
- PaddleOCR cloud API - submits PDFs, polls job state, downloads OCR JSONL results, and post-processes full text/images.
  - SDK/Client: direct HTTP through `requests` in `paperforge/worker/ocr.py`.
  - Auth: `PADDLEOCR_API_TOKEN` or `PADDLEOCR_API_TOKEN_USER`.
  - Endpoint: `PADDLEOCR_JOB_URL`, defaulting to `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` in `paperforge/worker/ocr.py`.
  - Model: `PADDLEOCR_MODEL`, defaulting to `PaddleOCR-VL-1.5` in `paperforge/worker/ocr.py`.

**Literature Source:**
- Zotero + Better BibTeX - Zotero owns the library and PDFs; Better BibTeX exports JSON files consumed by sync.
  - SDK/Client: local JSON parsing in `paperforge/adapters/bbt.py`; no Zotero web API client detected.
  - Auth: Not applicable for BBT JSON export.
  - Input location: `<system_dir>/PaperForge/exports/` from `paperforge/config.py`.

**Zotero Annotation Import:**
- Zotero local SQLite - reads annotation tables from `zotero.sqlite` via a temporary snapshot.
  - SDK/Client: Python `sqlite3` in `paperforge/annotation/zotero_probe.py`.
  - Auth: Local filesystem access to Zotero data directory; no network auth.
  - Safety pattern: copy database to a temp file, open URI with `mode=ro&immutable=1`, and never write to Zotero SQLite in `paperforge/annotation/zotero_probe.py`.

**Embeddings / Vector Search:**
- Local sentence-transformers - default embedding path for vector search.
  - SDK/Client: `sentence_transformers.SentenceTransformer`, lazy-imported in `paperforge/memory/vector_db.py`.
  - Auth: None for local cached/public models; optional `HF_TOKEN` when downloading through a mirror.
- Hugging Face compatible mirror - optional direct model file download.
  - SDK/Client: Python `urllib.request` in `paperforge/memory/vector_db.py`.
  - Auth: optional `HF_TOKEN`.
  - Endpoint: `HF_ENDPOINT` or plugin setting `vector_db_hf_endpoint`; default plugin setting is `https://hf-mirror.com` in `paperforge/plugin/main.js`.
- OpenAI-compatible embeddings API - optional vector DB API mode.
  - SDK/Client: `openai.OpenAI` in `paperforge/memory/vector_db.py`.
  - Auth: plugin setting `vector_db_api_key`, `.env` key `OPENAI_API_KEY`, or env override `VECTOR_DB_API_KEY`.
  - Endpoint: default OpenAI API or `VECTOR_DB_API_BASE` / plugin setting `vector_db_api_base`.
  - Model: `VECTOR_DB_API_MODEL` / plugin setting `vector_db_api_model`, defaulting to `text-embedding-3-small`.

**Updates and Releases:**
- GitHub repository API/content endpoints - checks remote package version and downloads zip updates.
  - SDK/Client: `urllib.request` and Git subprocesses in `paperforge/worker/update.py`.
  - Auth: None for runtime update checks; GitHub Actions uses `github.token` in `.github/workflows/publish.yml`.
  - Repository: `https://github.com/LLLin000/PaperForge` in `paperforge.json`.
- PyPI - package publish target and runtime update source.
  - SDK/Client: `pip` subprocess in `paperforge/worker/update.py`; publishing via `pypa/gh-action-pypi-publish@release/v1` in `.github/workflows/publish.yml`.
  - Auth: GitHub Actions secret `PYPI_TOKEN` in `.github/workflows/publish.yml`.

**Obsidian Desktop:**
- Obsidian plugin host - UI shell, command registration, vault file access, settings persistence, and PDF navigation.
  - SDK/Client: Obsidian plugin API through CommonJS module imports in `paperforge/plugin/main.js`.
  - Auth: Local app/plugin permissions; no remote auth.
  - Runtime bridge: plugin invokes the Python package with `child_process` helpers in `paperforge/plugin/main.js`.

## Data Storage

**Databases:**
- SQLite `paperforge.db`
  - Connection: `<system_dir>/PaperForge/indexes/paperforge.db`, resolved as `memory_db` in `paperforge/config.py`.
  - Client: Python `sqlite3` with WAL and foreign keys in `paperforge/memory/db.py`.
- SQLite `annotations.db`
  - Connection: `<system_dir>/PaperForge/indexes/annotations.db`, resolved as `annotations_db` in `paperforge/config.py`.
  - Client: Python `sqlite3` with WAL and foreign keys in `paperforge/annotation/db.py`.
- ChromaDB persistent vector store
  - Connection: `<system_dir>/PaperForge/indexes/vectors`, derived by `get_vector_db_path()` in `paperforge/memory/vector_db.py`.
  - Client: `chromadb.PersistentClient` in `paperforge/memory/vector_db.py`.
- Zotero SQLite snapshot
  - Connection: user-selected Zotero data directory containing `zotero.sqlite`; resolved through setup/config and probed by `paperforge/annotation/zotero_probe.py`.
  - Client: read-only `sqlite3` snapshot in `paperforge/annotation/zotero_probe.py`.

**File Storage:**
- Local filesystem only for vault artifacts.
- Better BibTeX JSON exports live under `<system_dir>/PaperForge/exports/` from `paperforge/config.py`.
- OCR output lives under `<system_dir>/PaperForge/ocr/<zotero_key>/` with `meta.json`, `fulltext.md`, JSON results, and image assets managed by `paperforge/worker/ocr.py`.
- Formal notes live under `<resources_dir>/<literature_dir>/`, resolved by `paperforge/config.py`.
- Obsidian plugin settings live at `.obsidian/plugins/paperforge/data.json`, read by `paperforge/memory/vector_db.py` and `paperforge/plugin/main.js`.

**Caching:**
- ChromaDB vector cache/persistence under `<system_dir>/PaperForge/indexes/vectors` in `paperforge/memory/vector_db.py`.
- Local embedding model mirror cache under `~/.cache/paperforge/models/` in `paperforge/memory/vector_db.py`.
- OCR page/image caches are written under each paper OCR directory by `paperforge/worker/ocr.py`.

## Authentication & Identity

**Auth Provider:**
- Custom/local configuration, no centralized user identity provider detected.
  - Implementation: `.env`, process environment variables, `paperforge.json`, and Obsidian plugin settings; precedence for core path config is implemented in `paperforge/config.py`.

**API Secrets:**
- PaddleOCR token from `PADDLEOCR_API_TOKEN` / `PADDLEOCR_API_TOKEN_USER` in `paperforge/worker/ocr.py`.
- OpenAI-compatible embedding key from plugin settings, `.env` `OPENAI_API_KEY`, or `VECTOR_DB_API_KEY` in `paperforge/memory/vector_db.py`.
- Hugging Face token from `HF_TOKEN` in `paperforge/memory/vector_db.py`.
- PyPI publish token from GitHub Actions secret `PYPI_TOKEN` in `.github/workflows/publish.yml`.

## Monitoring & Observability

**Error Tracking:**
- None detected. No Sentry, Rollbar, OpenTelemetry, or hosted error tracking integration found.

**Logs:**
- Python uses stdlib `logging`; logging setup is centralized in `paperforge/logging_config.py`.
- `PAPERFORGE_LOG_LEVEL` controls default log level per docs and migration notes in `docs/ARCHITECTURE.md` and `docs/MIGRATION-v1.4.md`.
- Worker commands also print concise CLI progress/status messages, especially OCR status in `paperforge/worker/ocr.py`.
- Plugin surfaces notices/status text inside Obsidian via `paperforge/plugin/main.js`.

## CI/CD & Deployment

**Hosting:**
- Python package: PyPI via `.github/workflows/publish.yml`.
- Plugin assets: GitHub Releases via `.github/workflows/publish.yml`.
- Source/update channel: GitHub repository configured in `paperforge.json`.

**CI Pipeline:**
- GitHub Actions CI in `.github/workflows/ci.yml`.
- Python unit tests run on Ubuntu, Windows, and macOS with Python 3.11 in `.github/workflows/ci.yml`.
- Plugin tests run with Node 20, `npm ci`, and Vitest under `paperforge/plugin/` in `.github/workflows/ci.yml`.
- E2E and audit tests run on Ubuntu with Python 3.11 in `.github/workflows/ci.yml`.
- Additional chaos/release workflows exist in `.github/workflows/ci-chaos.yml` and `.github/workflows/release.yml`.

## Environment Configuration

**Required env vars:**
- `PADDLEOCR_API_TOKEN` - required for live OCR in `paperforge/worker/ocr.py`.
- `PAPERFORGE_VAULT` - optional but important for non-interactive CLI vault resolution in `paperforge/config.py`.

**Optional env vars:**
- `PADDLEOCR_API_TOKEN_USER`, `PADDLEOCR_JOB_URL`, `PADDLEOCR_MODEL`, `PADDLEOCR_MAX_ITEMS` - OCR auth/endpoint/model/concurrency in `paperforge/worker/ocr.py`.
- `PAPERFORGE_POLL_INTERVAL`, `PAPERFORGE_POLL_MAX_CYCLES` - OCR polling behavior in `paperforge/worker/ocr.py`.
- `PAPERFORGE_SYSTEM_DIR`, `PAPERFORGE_RESOURCES_DIR`, `PAPERFORGE_LITERATURE_DIR`, `PAPERFORGE_CONTROL_DIR`, `PAPERFORGE_BASE_DIR`, `PAPERFORGE_SKILL_DIR`, `PAPERFORGE_COMMAND_DIR` - path overrides in `paperforge/config.py`.
- `ZOTERO_DATA_DIR` - Zotero data directory override used when building paths in `paperforge/config.py`.
- `OPENAI_API_KEY`, `VECTOR_DB_API_KEY`, `VECTOR_DB_API_BASE`, `VECTOR_DB_API_MODEL` - API embedding mode in `paperforge/memory/vector_db.py`.
- `HF_ENDPOINT`, `HF_TOKEN` - local embedding model mirror download in `paperforge/memory/vector_db.py`.
- `PAPERFORGE_LOG_LEVEL` - logging level documented in `docs/ARCHITECTURE.md`.

**Secrets location:**
- Runtime secrets are expected in the vault `.env` or process environment; `.env` is listed as protected in `paperforge.json`.
- Obsidian plugin vector settings, including optional API settings, are read from `.obsidian/plugins/paperforge/data.json` by `paperforge/memory/vector_db.py`.
- CI publish secret is stored as GitHub Actions secret `PYPI_TOKEN` in `.github/workflows/publish.yml`.

## Webhooks & Callbacks

**Incoming:**
- None detected. The project is a local CLI/plugin system and does not expose HTTP server endpoints.

**Outgoing:**
- PaddleOCR job submit/poll/result fetch from `paperforge/worker/ocr.py`.
- Optional OpenAI-compatible embeddings requests from `paperforge/memory/vector_db.py`.
- Optional Hugging Face mirror file downloads from `paperforge/memory/vector_db.py`.
- GitHub version/update checks and zip downloads from `paperforge/worker/update.py`.
- PyPI/GitHub release publishing through GitHub Actions in `.github/workflows/publish.yml`.

---

*Integration audit: 2026-07-02*
