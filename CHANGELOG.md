# Changelog

All notable changes to PaperForge.

---

## 1.5.8 (2026-05-19)

### Memory Layer (New)

- SQLite + FTS5 database (`paperforge.db`) for fast paper metadata lookup
- `paperforge memory build` / `memory status` / `search`
- `paperforge agent-context` — structured bootstrap for AI agents
- `paperforge dashboard` — backed by SQLite (with file scan fallback)
- Automatic rebuild after sync (fast-path when index hash unchanged)
- Runtime health computation with degraded-status reporting
- JS-native memory state reader (file-based, no Python exec polling)

### Vector Embedding (New)

- ChromaDB-backed vector storage for OCR fulltext
- `paperforge embed build` / `embed status` / `embed stop`
- `paperforge retrieve` — semantic search across OCR chunks
- API-only embedding (OpenAI-compatible), no local models
- Configurable API key/base/model via env, plugin settings, or `.env`
- `--resume` / `--force` build modes with persistent build state
- Auto-trigger after OCR via background subprocess

### Embedding Package Refactoring

- Extracted vector logic from `memory/vector_db.py` into dedicated `embedding/` package
- Old modules converted to deprecated forwarding shims
- Removed sentence-transformers dependency (API-only)
- Model change auto-detection: resume mode detects model switch and triggers full rebuild

### Orphan Paper Cleanup (New)

- `paperforge prune` — detect and delete orphan workspaces (dry-run by default)
- `sync --prune` / `sync --prune-force` — integrate into sync pipeline
- Automatic orphan detection after every sync with Obsidian modal popup
- Click-to-toggle selection with paper metadata (title, authors, year, PDF, collection)

### Sync Performance

- Export hash check skips rebuild when BBT files unchanged (~24s → 0.1s)
- `canonical_index_hash` in memory DB meta for fast rebuild skip
- Removed redundant `refresh_paper` calls from build loop

### Plugin UI

- Tabbed settings: Installation + Features
- Runtime Health panel with manual sync button
- Memory Layer and Vector Embedding state machine UI
- Discussion card renders from `discussion.md` with `MarkdownRenderer`
- i18n: full Chinese/English translation for Features tab + orphan modal
- Vector DB config labeled as Experimental

### Discussion System

- Changed from JSON to plain Markdown (`discussion.md`)
- Plugin renders last 3 Q&A pairs with collapsible long answers

### Bug Fixes

- `get_collection()` no longer silently deletes collection on error
- nopdf OCR status resets to `pending` when PDF re-appears
- Embed chunk_count now reports actual DB count, not incremental count
- Plugin: embed build survives settings tab close
- Plugin: fix runtime health sync path for first-launch migration

### Infrastructure

- `release.yml` / `publish.yml` — fixed tag pattern to match `[0-9]*` (no `v` prefix)
- Pre-commit JS syntax hook added

---

## 1.5.7 (2026-05-19)

> Recovery release after 1.5.6 PyPI name conflict. All features listed under 1.5.8.

- Model change auto-detection in embed resume mode
- Orphan modal i18n completed (Chinese/English)
- CHANGELOG.md added

---

## 1.5.9 (2026-06-17)

### OCR Tail Rendering Fixes

- `_reorder_tail_run`: Added `skip_section_grouping` parameter for tail pages
  with reference items but no explicit "References" heading. These pages now
  emit blocks in column-sorted order with refs grouped at end, preserving
  natural reading order.
- `_order_tail_blocks`: Per-page detection of ref heading presence to activate
  the new path.
- `_normalize_backmatter_roles_after_boundary`: Removed forced
  `body_paragraph → backmatter_body` conversion inside backmatter region
  (body paragraphs attach naturally via geometric ownership).
- Synthetic ref section (Phase 2.5): Creates synthetic `ref_section` when
  ref_items exist but no ref_heading, preventing ref scattering as orphans.

For upgrade: `pip install --upgrade paperforge`
