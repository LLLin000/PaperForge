# Changelog

All notable changes to PaperForge.

---

## [2.0.8] - 2026-11-27

### Onboarding, System Proxy & Host Lifecycle Hardening

- **System Proxy Inheritance & Cross-Language Parity**: Added Electron `session.resolveProxy()` + Windows Registry + macOS `scutil --proxy` detection (`system-proxy.ts`) inherited into managed runtime, daemon, and Python child environments with explicit override priority and Obsidian `requestUrl` adapter support; unified `NO_PROXY`, primary `DIRECT`, and `SOCKS4` semantics across TypeScript and Rust (`runtime_ops.rs`).
- **Zero-Network Daemon Startup & Bounded Fetches**: Restored the 12-hour SHA-256 checksum TTL fast path when Obsidian's `requestUrl` fetcher is enabled (`useRemoteTtl: true`) and bounded `createObsidianRequestFetcher` requests with 15s (10s `checksums.txt`) timeouts (`native-daemon.ts`).
- **Fresh Vault Manifest, Python Daemon Fallback & Companion Tab Reveal**: Stamped `.paperforge/vault-manifest.json` (`layout_version: 2`) on clean `.paperforge` setups without masking legacy vaults (`vault_engine.py`, `setup/plan.py`), surfaced setup manifest write warnings and a `vault.manifest_missing` probe diagnostic notice (`probes/library.py`), guarded Python stdio daemon engine-cache refreshes so unconfigured and veteran v1 vaults serve `probe`/`upgrade --plan` cleanly when the native Rust daemon is absent (`commands/daemon.py`), and preserved pending paper leaf resolution when revealing a hidden Companion tab (`dashboard.ts`).
- **Large-Library Sync Speedup & Timeout Hardening**: Switched bulk `build_index` journal metric enrichment to offline-first zero-HTTP resolution (`allow_network=False`), added mtime-cached local `zoterostyle.json` lookup, bundled CC0 OpenAlex seed hits during offline sync, and per-vault negative memoization (`journal_metrics.py`), pre-indexed workspace directories in O(1) to eliminate O(N²) directory globs (`asset_index.py`), removed discarded per-paper work in deprecated `run_selection_sync` (`worker/sync.py`), raised `client.sync()` RPC timeout to 300s (`paperforge-client.ts`), and clarified sync failure guidance in bilingual Settings UI (`i18n.ts`).
- **PDF Path Resolution & Viewer Fixes**: Preserved `att_key` on nested/backslash `storage:` paths and fell back to the first `.pdf` inside `storage/<KEY>` on filename mismatches (`zotero_sqlite.py`, `pdf_resolver.py`), added Zotero profile matching for `extensions.zotero.baseAttachmentPath` and `attachments:` handling across SQLite/BBT/resolver/PDF viewer (`bbt.py`, `zotero_paths.py`, `annotations_service.py`), honored v2 `vault_config.zotero_data_dir` and `.paperforge/Zotero` junctions in `resolve_source_pdf` and wikilink generation, and passed vault `zotero_dir` in `local_read._resolve_canonical_pdf`.
- **Real-Obsidian H2 Lifecycle Matrix & CI Speedup**: Added real-Obsidian Settings, Migration & Post-Install Operational Closed-Loop E2E coverage (`S1–S10` in `settings-lifecycle.e2e.ts`), isolated local `HOME`/`USERPROFILE` alongside `PAPERFORGE_HOME` (`wdio.conf.mts`), sharded `L1b` into 4 parallel workers, and added Rust Cargo caching.

---

## [2.0.7] - 2026-11-26

### Release Qualification & Hardening

- **Native MCP & Agent Skill Hub (`paperforge-daemon`)**: Added native Rust MCP server (`--mcp`) with 7 tools, `agent-brief`, `agent-onboarding`, `mcp-config`, `mcp-install`, `mcp-check`, and `skill-sync-all`. Hardened MCP vault pinning, argument validation, `--` positional separators, `exclusive_barrier` serialization across `cli.run` and mutating MCP tools, binary path/SHA-256/anti-downgrade verification in `maybe_reexec_latest_binary`, Windows Job Object reaping for reexec/runtime subprocesses, skill containment checks, and corrupt DB / `tier0_truth_intact` / `base-snapshot` parity.
- **Runtime Installer & Supply-Chain Security**: Enforced authoritative GitHub Release `checksums.txt` SHA-256 + ZIP integrity validation for wheel downloads (`runtime_ops.rs` and `runtime_uv.py`), removed `--trusted-host` TLS bypasses, and added secret redaction in `installer.log`.
- **OCR, Retrieval, Memory & Annotations**: Added CJK LIKE fallback for FTS5 metadata/content search, loaded `sqlite-vec` during paper vector deletion (`delete_paper_vectors_in_conn`), purged deleted keys from `workspace_registry`/`ocr_catalog`/`lineage`/`paper_memory_history`, made `agent_apply_annotations` two-phase atomic on `replace_lens`, added `--domain` filtering to `retrieve` and `done_incomplete` to `search`, fixed `ocr rebuild` `PFError` lookup, fixed `ocr --json run` stdout purity, treated truncated NDJSON OCR results as retryable, aligned dashboard/maintenance statuses, allowed `x0=0`/`y0=0` object crop bboxes, and preserved resumable `.db.build` candidates in `probe_memory`.
- **Data Safety, Migration & Zotero Sync**: Hardened vault upgrade per-file verification, rollback, Zotero sync fingerprint/backup handling, and trash boundary checks.
- **Obsidian Plugin & UIKit**: Added UIKit foundation, Quick Switcher, Unified Command Palette, Citation Inserter, and UI Gallery; fixed `paperforge-build-embeddings` action/scope/confirmation contract, virtual scroll freeze, layout-change listener leaks, shift-select, deep-link handling, inline rollback, CSS scoping, and bilingual i18n parity.
- **CI, Packaging & Docs**: Hardened `.github/workflows/publish.yml` and CI workflows with `SOURCE_DATE_EPOCH` deterministic wheel/sdist builds, cleaned `pyproject.toml` wheel excludes/package-data, synchronized `ci-shards.json`, and reconciled 2.0.x documentation and technical reference.

---

## [2.0.6] - 2026-11-24

### Performance & Reliability

- Deferred startup `configList` and background probes out of `onload()` onto `onLayoutReady()` idle (`deferred.ts`), reducing Obsidian startup overhead to milliseconds and avoiding concurrent Python process bursts.
- Added async `stat()` fingerprint gating on `zotero.sqlite` / `-wal` prior to background auto-sync (`0%` idle CPU and zero Python spawns when Zotero has not changed).
- Switched native daemon SHA-256 integrity checks to async streaming with a 12-hour healthy local cache.
- Fixed Settings tab re-probing and DOM rebuilds while closed (now marks dirty and refreshes on open).
- Fixed Companion sidebar listener leaks by calling `offref()` properly on `active-leaf-change` and `vault.modify` during close.
- Disabled high-GPU Liquid Glass blur by default (zero-blur solid high-performance mode, toggleable in Appearance), and removed global `.modal:has(...)` selectors and redundant Base re-renders.

---

## [2.0.5] - 2026-11-24

### Changed

- Rebuilt Settings into 4 focused pages (`Overview`, `Modules`, `Appearance`, `Help`): Overview shows a single Decision-Tree Hero Card plus 5 compact status rows; Appearance holds theme/density/motion controls; storage maintenance/rollback moved under `Modules → Installation`.
- Optimized Base Literature Workbench (`PaperForgeBasesView`): O(1) path index, SVG icon template cache, 80-row chunked streaming render, local checkbox refresh without full table rebuilds, CSS `content-visibility` isolation, fixed `<colgroup>` proportions, and frameless semantic `<a>` title links.

---

## [2.0.4] - 2026-11-24

### Added

- Deterministic 10-state Setup, Upgrade & Readiness Decision Tree (`setup-decision-tree.ts`), surfacing one clear primary card and next action across `engine_updating`, `engine_quarantined`, `checking`, `engine_version_mismatch`, `engine_not_installed`, `engine_probe_failed`, `legacy_vault_upgrade`, `zotero_not_configured`, `library_sync_error`, and `ready`.
- Collapsed release notes banner into a compact header pill next to the version badge.
- Zero-Python upgrade detection supporting custom `system_dir` paths in `paperforge.json`.

### Fixed

- Resolved race condition during cross-version Rust daemon hot-swap vs initial auto-sync / upgrade checks (startup waits for hot-swap and transport retries once transparently).
- Fixed installed legacy engines being misclassified as "Step 1 not installed" when a probe fails, and improved legacy API key migration error guidance.

---

## [2.0.3] - 2026-11-23

### Changed

- Unified 3-layer interaction feedback contract (`feedback.ts`): transient notices for quick confirmations, inline actionable cards for persistent issues (Windows Defender exclusion path copy, background sync retry, orphan cleanup, release notes), and plain-language translation of Python tracebacks, HTTP 401/429/404, Zotero locks, and timeouts.
- Achieved 100% EN/ZH bilingual dictionary coverage (`1386/1386` keys) across plugin UI and Rust daemon notifications.
- Eliminated duplicate failure/completion notices on streaming tasks, aligned `queued` task tracking, and unified `nopdf` handling across Dashboard and funnels.

---

## [2.0.2] - 2026-11-22

### Added

- True 1-click Express Onboarding (`_renderExpressSetup` + `domain-preview.ts`): automatically chains engine deployment, configuration, and initial Zotero sync in one action, with live A/B `domain_mode` folder preview.
- Multi-mirror resilience for university/hospital networks (10s connect timeout, GitHub mirror fallback, CN PyPI/Python mirrors, and inline 1-line proxy retry).
- Base Workbench missing-local-PDF diagnostic bar, free OCR/embedding API key links, and native Rust daemon SHA-256 self-healing + antivirus quarantine warning.

### Fixed

- Fixed valid empty SQLite `papers` tables (0 rows) mistakenly falling back to stale `formal-library.json`.
- Fixed macOS `kqueue` orphan reaper child exit status collection.
- Added `checksums.txt` asset verification gate to the release workflow.

---

## [2.0.1] - 2026-11-22

### Added

- Content-addressed versioned Rust daemon binary deployment (`.daemon-meta.json` + SHA-256) preventing Windows in-use binary replacement races.
- macOS kernel-level `kqueue` (`EVFILT_PROC` / `NOTE_EXIT`) zero-polling orphan reaper matching Windows Job Objects and Linux `PR_SET_PDEATHSIG`.
- Direct Zotero SQLite read-only Online Backup API snapshots (`zotero.sqlite` without tearing during Zotero writes).

### Fixed

- Consolidated `memory-card base-snapshot` onto SQLite SSOT (`has_pdf`, `do_ocr`, `analyze`, `collections_json`, no resurrection from stale JSON).
- Added SQLite single-key fallback in `engine.resolve_key` beyond the 2048-entry in-memory cache.
- Distinguished `completed` / `partial_success` / `failed` in directory migration and cleanup, and hid unwired bulk restore buttons in version history.

---

## [2.0.0] - 2026-11-18

### Breaking / Migration

- Consolidated Base workbench views into a single `"Literature Hub"` table (`paperforge-table` `BasesView`), removing preset multi-panel workflow splits (`控制面板` / `待 OCR` / `待深度阅读` / `Redo OCR`).
- Extended sidecar PDF annotation SQLite schema (`style_json`) to support freehand ink, geometric shapes, and page textboxes.
- Migrated default internal storage to hidden `.paperforge/` layout (`paperforge migrate-storage` & `paperforge upgrade --apply --fast-cutover` O(1) `<3s` cutover from `System/PaperForge/`), and moved vector search from ChromaDB to SQLite `sqlite-vec` (`vec0`).

### Added

- **AsterLab Visual System & Thin-Client UI**: warm neutral AsterLab palette (`pf-theme-asterlab`) and Obsidian theme bridge (`pf-theme-obsidian`), checkbox + `Shift` range selection in Base view with contextual bulk action bar, and removal of emoji clutter / redundant status pills.
- **Non-Destructive Sidecar PDF Annotator (`PaperForgePdfView`)**: built on Obsidian `loadPdfJs()`, `<workspace>/annotations.jsonl` + SQLite `paper_annotations`, Apple Preview dual-layer markup bar (highlights, underlines, strikethroughs, rectangular crop screenshots `<KEY>_ann_*.jpg`, ink, shapes, textboxes, sticky notes), Human vs Agent dual-layer filtering, 3-stage PDF grounding (`pdf_grounding.py`), `provenance_status` SHA-256 verification, and 1-click promotion to verified `reading-log` entries without modifying source PDF bytes.
- **Living Paper Memory Cards**: 5-facet evolving cognitive cards (`paper_memory_cards` + `paper_memory_history`, `<workspace>/ai/memory-card.json`, `paperforge memory-card <get|refine|history|clear>`) surfaced in Companion and `paper-context`.
- **Hybrid Retrieval & Diagnostics**: full RRF union across FTS5 BM25, `vec_body`, and `vec_objects` (`retrieve --deep` falls back cleanly to BM25 without vectors), strictly read-only `paperforge inspect <query> --json` (`?mode=ro` 6-stage pipeline diagnosis), pluggable OCR inbound provider protocol (`resolve_ocr_provider`), and `.state-seq.json` live Obsidian sync.
- **Security & Robustness**: OS Keyring secret authority (`paperforge auth`), Research Record exact-text source verification, sanitized OCR diagnostic issue drafts, and CI static/module-graph/architecture gates.

### Fixed

- Hardened Windows/CN onboarding, protected user-authored `reading-log.md` and custom YAML frontmatter, hid internal machine `fulltext.md` from normal user surfaces (available read-only via `annotations fulltext-preview`), pinned `pymupdf<2`, improved OCR V3 figure suffix/reservation/inner-text merge invariants, and resolved numerous streaming/transport/probe edge cases.

---

## [1.5.9] - 2026-06-17

### OCR Tail Rendering Fixes

- `_reorder_tail_run`: Added `skip_section_grouping` parameter for tail pages with reference items but no explicit "References" heading. These pages now emit blocks in column-sorted order with refs grouped at end, preserving natural reading order.
- `_order_tail_blocks`: Per-page detection of ref heading presence to activate the new path.
- `_normalize_backmatter_roles_after_boundary`: Removed forced `body_paragraph → backmatter_body` conversion inside backmatter region (body paragraphs attach naturally via geometric ownership).
- Synthetic ref section (Phase 2.5): Creates synthetic `ref_section` when ref_items exist but no ref_heading, preventing ref scattering as orphans.

---

## [1.5.8] - 2026-05-19

- SQLite + FTS5 database (`paperforge.db`) for fast paper metadata lookup
- `paperforge memory build` / `memory status` / `search`
- `paperforge agent-context` — structured bootstrap for AI agents
- `paperforge dashboard` — backed by SQLite (with file scan fallback)
- Automatic rebuild after sync (fast-path when index hash unchanged)
- Runtime health computation with degraded-status reporting
- JS-native memory state reader (file-based, no Python exec polling)

### Vector Embedding (New)

- Legacy ChromaDB-backed vector storage for OCR fulltext (replaced by `sqlite-vec` in 2.0)
- `paperforge embed build` / `embed status`
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

## [1.5.7] - 2026-05-19

> Recovery release after 1.5.6 PyPI name conflict. All features listed under 1.5.8.

- Model change auto-detection in embed resume mode
- Orphan modal i18n completed (Chinese/English)
- CHANGELOG.md added

For upgrade: `pip install --upgrade paperforge`
