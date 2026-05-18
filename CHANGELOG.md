# Changelog

All notable changes to PaperForge since 1.5.5.

---

## 1.5.7 (2026-05-19)

> 1.5.6 was skipped due to a PyPI version name conflict.

### Memory Layer (New)

- SQLite + FTS5 database (`paperforge.db`) for fast paper metadata lookup
- `paperforge memory build` — build from canonical index
- `paperforge memory status` — freshness, schema version, coverage
- `paperforge search` — FTS5 full-text search across papers
- `paperforge agent-context` — structured bootstrap for AI agents
- `paperforge dashboard` — now backed by SQLite (with file scan fallback)
- `paperforge paper-status` / `paper-context` — per-paper status lookup
- Automatic rebuild after sync (fast-path when index hash unchanged)
- `reading_log`, `project_log`, `paper_events` tables with JSONL persistence
- `paperforge reading-log` — validate/import/lookup commands
- `paperforge project-log` — record and render engineering session notes
- Runtime health computation with degraded-status reporting
- JS-native memory state reader (file-based, no Python exec polling)

### Vector Embedding (New)

- ChromaDB-backed vector storage for OCR fulltext
- `paperforge embed build` / `embed status` / `embed stop`
- `paperforge retrieve` — semantic search across OCR chunks
- API-only embedding (OpenAI-compatible), no local models
- Configurable API key/base/model via env, plugin settings, or `.env`
- `--resume` flag for incremental build; `--force` for full rebuild
- Persistent build state (survives process restarts)
- Auto-trigger after OCR via background subprocess
- Preflight check for dependency readiness

### Embedding Package Refactoring

- Extracted all vector logic from `memory/vector_db.py` into dedicated `embedding/` package:
  - `_config.py`, `_chroma.py`, `build_state.py`, `builder.py`, `search.py`, `status.py`, `preflight.py`
  - `providers/base.py` (ABC), `providers/openai_compatible.py`
- Old `memory/vector_db.py` and `worker/vector_db.py` converted to deprecated forwarding shims
- Removed sentence-transformers dependency (API-only)

### Orphan Paper Cleanup (New)

- `paperforge prune` — detect and delete orphan workspaces (dry-run by default)
- `--force` for interactive selection or batch delete
- `sync --prune` / `sync --prune-force` — integrate into sync pipeline
- Automatic orphan detection after every sync
- Obsidian modal popup with paper metadata (title, authors, year, PDF status, collection)
- Click-to-toggle selection, batch delete from modal

### Sync Performance

- Index rebuild: export hash check skips rebuild when BBT files unchanged (~24s → 0.1s)
- `canonical_index_hash` stored in memory DB meta table for fast rebuild skip
- Removed redundant `refresh_paper` calls from build loop
- Phase timing logging in sync_service

### Plugin UI

- Tabbed settings: Installation + Features
- Runtime Health panel with sync timestamp + manual sync button
- Memory Layer status + rebuild button
- Vector Embedding: state machine UI with status/progress/stop
- Skills manager with collapsible groups (System/User)
- Agent platform selector with skill deployment
- Discussion card: renders from `discussion.md` with `MarkdownRenderer`
- i18n: full Chinese/English translation for Features tab
- Progressive disclosure: collapsible Advanced sections for Vector DB config
- Deduplicated Base views on every sync (fixed)

### Discussion System

- Changed from JSON to plain Markdown (`discussion.md`)
- Plugin renders last 3 Q&A pairs with markdown rendering (tables, code, callouts)
- Long answers collapsed with expand-on-click
- Removed JSON writing from `discussion.py`

### Workflows & Skills

- New: `reading-log` skill with strict template validation
- New: `project-log` skill for engineering session records
- New: `methodology-extraction` skill (pure prompt)
- Unification: 6 workflows under single `paperforge` compound skill
- `bootstrap` — memory_layer field, verified tuple return

### Bug Fixes

- `get_collection()` no longer silently deletes collection on error
- nopdf OCR status resets to `pending` when PDF re-appears
- `has_deep_reading_content` import fixed in `asset_index.py` and `deep_reading.py`
- Memory rebuild no longer affects sync result code (best-effort only)
- Vector resume launches as silent background process (DEVNULL)
- Plugin: async pip install with persistent notice + UTF-8 fix
- Plugin: remove dead cascading keys, fix toggle content sync
- Plugin: cache memory/vector status to avoid re-check on tab switch
- Plugin: embed build survives settings tab close
- Plugin: fix runtime health sync path for first-launch migration
- Plugin: fix `--vault` flag ordering before subcommand

### Infrastructure

- `release.yml` — fix tag pattern to match `[0-9]*` (no `v` prefix)
- `publish.yml` — same pattern fix + skip-existing handling
- Pre-commit JS syntax hook added
- `versions.json` updated for all releases

---

For upgrade: `pip install --upgrade paperforge`
