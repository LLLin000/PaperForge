# Changelog

All notable changes to PaperForge.

---

## Unreleased

### Added

- Support hidden `.paperforge/` engine layout (`resolve_paths`, fresh Setup default, and `pf_bootstrap.py`) so OCR intermediates, indexes, backups, and internal `fulltext.md` stay invisible to Obsidian's file indexer while materializing collision-free `<workspace>/assets/<KEY>_figure_*.jpg` and `<KEY>_table_*.jpg` assets natively rendered in formal notes, plus `paperforge migrate-storage [--dry-run] [--json]` to upgrade legacy `System/PaperForge` vaults in place.
- Add non-destructive Zotero-style Sidecar PDF Annotator (`PaperForgePdfView` via Obsidian's built-in `loadPdfJs()`, `<workspace>/annotations.jsonl`, SQLite `paper_annotations` table, and `paperforge annotations <pdf-info|list|add|update|delete|promote|fulltext-preview>`) supporting multi-color text highlights, rectangular region crops (`<KEY>_ann_*.jpg`), SHA-256 provenance binding, automatic V3 OCR section/figure resolution, cognitive intent tags (`evidence`/`question`/`method`/`quote`), and one-click promotion to verified `reading-log` entries without modifying source PDF bytes.
- Surface `user_annotations` (`total`, `questions`, `highlights`) directly in `paperforge paper-context`, wire user PDF questions into `/pf-deep` (`molecules/deep-analyze-paper.md`, plus mandatory `paperforge deep-finalize`), fix `extract-methodology-card.md` and `write-reading-log-jsonl.md` guidance, and add `molecules/synthesize-evidence-matrix.md` for multi-paper horizontal evidence synthesis.
- Add all missing Settings UI controls (`vector_db_provider_type`, `paddleocr_job_url`, `paddleocr_model`, full 15-platform skill deployment mapping) with explicit Save / Stage 3 flush controls, and add O(1) `.sync-fastpath.json` short-circuiting and capped OCR version snapshots (`<= 3` kept).

### Fixed

- Harden Windows & CN novice onboarding in Setup Wizard and Python runtime discovery (`%LOCALAPPDATA%\Programs\Python`, `py -3.x` filtering Store stubs, UTF-8 `@chcp 65001` `.cmd` installers, PyPI mirror fallback, install Cancel action, Zotero `CSL JSON` structure detection, inline offline SVG guide, external Zotero PDF resolution without required symlinks, and preventing unintended whole-library OCR runs when zero papers have `do_ocr: true`).
- Protect user-authored Obsidian data across sync/prune: write `reading-log --render` to `reading-log.index.md` instead of overwriting user narrative `reading-log.md`, preserve custom YAML frontmatter keys via line-anchored `split_frontmatter_block`, automatically migrate cross-domain workspaces during index builds and deduplicate keys, fix `paperforge prune` workspace resolution, and tighten orphan cleanup matching with `trash_remove`.
- Hide internal machine `fulltext.md` from normal plugin user surfaces (removing "打开全文" / "Fulltext Path" from Dashboard and routing PDF opens to `PaperForgePdfView`, while preserving read-only `OCR Workspace` diagnostics via `annotations fulltext-preview`).
- Fix hybrid retrieval (`paperforge/embedding/search.py` and `commands/retrieve.py`) to compute the full RRF union across BM25, `vec_body`, and `vec_objects` with batch metadata hydration instead of dropping semantic hits whenever BM25 matches, allow `retrieve --deep` to run via FTS5 BM25 before vectors are built, and fix `pf_deep.py` scaffold heading validation + `<KEY>_*.jpg` embed resolution and `_build_collection_tree` `/` sub-path splitting.
- Add strictly read-only `paperforge inspect <query> [--json]` per-paper 6-stage diagnostic command (`source`, `lineage`, `ocr`, `objects_and_render`, `memory`, `vectors`) using SQLite `?mode=ro` URI without creating lock or WAL files, plus `scripts/dev/ocr_rebuild_paper.py --dump-stages` / `--dump-stages-only` for offline OCR V3 stage transition inspection.
- Formalize pluggable OCR inbound schema protocol (`paperforge/providers/base.py`, `paperforge/providers/__init__.py`) and route PaddleOCR normalization and job submission through `resolve_ocr_provider`.
- Add `check_module_graph.py --check` (R1-R4) to the L0 `static` GitHub Actions job and fold standalone cross-OS `unit-tests` into `j-matrix` while tightening CI caching and PR concurrency cancellation.
- Fail the static CI job when the research evidence corpus (`docs/evidence/`) is tracked, and — for a pull request — when any of its commits added it. The gate walks commits rather than diffing endpoints, so an add-then-delete inside a branch still fails; `.gitignore` cannot stop `git add -f`.
- Save research records from the paper panel, search specific quotes/use text separately from paper metadata, and inspect stable record IDs and append-only correction history (#353).
- Search JSONL immediately without rebuilding Memory or using embeddings; source checks distinguish recorded, user-confirmed, exact-text matched, stale and unavailable positions.
- Recheck hash-bound, canonical in-vault PDF sources before opening a validated physical page. External paths and junctions resolving outside the vault are refused; printed-page labels are separate and do not establish verification.
- Restrict OCR Support Diagnostic and issue-draft egress to validated public fields: no probe text, setup detail/stage logs or raw paths; home paths collapse to a location label. Clipboard and issue modal accept sanitized payloads, and drafts include only known OCR reason codes, bounded paper counts and static labels.

### Fixed

- Route embedding preflight and runtime clients (`preflight.py`, `builder.py`, `dim_detect.py`, `search.py`) through `resolve_embedding_provider` and `check_embedding_provider_prereqs`, enabling `vector_db_provider_type=requests` without requiring the `openai` SDK.
- Eliminate the remaining `worker -> commands` layer violation (`worker/ocr_health.py:collect_ocr_health_summary`), expose public read-only APIs on `promote_r` and `render_audit`, and defer top-level `pymupdf` / `PIL` imports inside OCR worker modules (verified by `tests/test_import_weight.py`).
- Build memory retrieval units from the configured OCR directory rather than a hardcoded system directory (#356).
- Distinguish a published runtime or completed library setup from a subsequent path refresh failure (#356).
- Classify explicit OCR HTTP 401/403 refusals as blocked; keep ambiguous submissions without a confirmed job ID for reconciliation, with no automatic resubmission or record deletion. On a per-paper poll timeout, release that paper's local concurrency slot while retaining the remote job ID; report provider rate-limit rejection separately (#356).
- Check installation compatibility with the Python versioned probe even when an older runtime ignores the version in its aggregate response (#356).
- Classify Setup failures from the complete child result while keeping command paths and raw stderr out of the user-facing message and Support Diagnostic; report unresolved package-source artifacts neutrally rather than assuming a Python/platform mismatch (#356).
- Keep an explicit Setup reinstall request across a ready installation probe, so the action remains available until the user retries or the reinstall completes (#356).
- Show blocked and failed paper keys from the actual OCR action result data in workspace error notices (#356).
- Refresh the existing Python-authoritative vault paths after successful setup and library configuration, so the first-use export location and subsequent path changes do not require a plugin reload (#356).
- Reuse the resolved source PDF throughout initial OCR postprocessing, including page rendering, span backfill and object extraction; vault-relative and wikilink locators no longer replace the resolved file mid-pipeline. Missing table source geometry can still require separate repair (#356).

- Count overlapping exact-text occurrences when checking research-record PDF sources; repeated overlapping quotes remain ambiguous and cannot pass source navigation as a unique match, including previously saved records (#356).
- Preserve partial version-restore results at all UI consumers: inline provenance warnings survive preview/paper reselection, current-version markers follow the confirmed restored content, and absent legacy metadata flags remain unconfirmed rather than definite write failures. Only explicit provenance persistence failure adds a single safe substep diagnostic (#356).
- Invalidate view-owned search timers, replies and focused shortcuts when switching or refreshing dashboard content, including version mode; obsolete requests cannot update the next paper's results (#356).
- Keep Setup Stage2 startup rejections client-owned while retaining local settings-save diagnostics; expected missing-runtime states do not acquire a duplicate generic error (#356).
- Preserve valid negative render-authority reports while diagnosing process/JSON failures once. Failed transport cannot claim success from stdout even when its exit code is unknown (#356).

- Treat long-task error/cancelled terminals and `result.ok:false` as failures even at exit 0; retain startup error codes and reject pending event readers rather than silently ending them. Cancel during runtime resolution prevents spawning, and plugin unload reaps streamed as well as result-mode children (#356).
- Preserve structured sync, OCR-list and probe failures instead of reporting success or an empty library. OCR Workspace distinguishes loading, setup required, load failure and a genuine empty result, offers Retry, and drops late replies and removed paper selections (#356).
- Stop search debounce and ignore in-flight replies after the panel closes. Setup cancellation cannot start publication after an awaited settings save; navigation cannot disguise running setup as idle. Memory backup restore reports failure and successful retry (#356).
- Open the OCR Workspace fulltext preview in the active Obsidian leaf using the backend-provided vault-relative path; report missing and open failures without guessing a replacement file.
- Label the OCR support-report action as an issue report in English and Chinese; restore focus to the OCR detail heading when a status refresh replaces the action while its draft is open (#356).
- Keep setup stdin open so Stop can deliver the cooperative `PAPERFORGE_STOP` token before kill escalation.
- Use the same prerelease-aware version comparison for interactive updates as the action path, so newer RC releases are not mistaken for the installed version (#356).
- Convert unexpected sync service exceptions into structured `SYNC_FAILED` results so JSON clients do not receive empty stdout on phase-two failures.
- Return exit status 1 when `sync --json` emits `ok:false`, while preserving its structured error payload (#356).
- Parse Trash timestamp directories as UTC before age comparison, so `paperforge trash purge --older-than` applies its age gate instead of raising a naive/aware datetime `TypeError` (#356).

- Metadata search without a local Memory index now shows a dedicated missing-memory recovery card (deep-retrieve PATH_NOT_FOUND stays distinct); the card navigates to the actual Memory module detail through the Plugin-owned openModuleSettings seam without dispatching builds/embeddings (#356).
- Route the Memory missing-vector-dependencies action into the managed-runtime reinstall flow; keep the active environment immutable (#356).
- Console ownership sweep: the shared client owns typed PFResult, probe and stream failures; local bootstrap/handshake, probe-schema validation, discussion read, external-note refresh and clipboard failures retain one redacted op/stage/code/exit diagnostic via traceConsoleError. NO_PYTHON/cancelled/empty remain quiet (#356).
- Doctor reports the plugin execution interpreter from the published managed-runtime pointer only: missing/invalid/missing-file/stale pointers report setup/repair/update and skip target-environment probing; no python_path or ambient-Python fallback, no in-place or global pip advice (#356).
- Search mode labels follow the dispatched request: `@`/leading-`@`/Ctrl+Enter deep retrieves render deep loading/results, and the transient input mode no longer leaks into rendered state (#356).
- Legacy OCR run/redo/rebuild cancelled terminals carry the existing `action.cancelled` machine code via `cancelled_result`; envelope event and exit 130 unchanged (#356).
- `core/next_actions.py` is wire DTOs plus schema version only; the shadow registry/validators are removed and the single authority stays `actions.registry` (#356).
- Preserve exact OCR paper scope from CLI, dashboard paper/collection context and workspace confirmation through provider upload (#349). Reject empty or unknown explicit scopes without partial execution.
- Confine OCR cleanup and stale-job resets to the selected scope. Stop prevents new uploads, including transport retries; submitted provider jobs remain separately reported as running remotely.
- Label whole-library OCR impact and require user confirmation in the plugin. Offline synthetic regressions intercept the final multipart HTTP upload; no paid-provider acceptance is implied.
- Pin `pymupdf<2`: 2.0 imports and activates its layout model (onnxruntime) at import time, which stalled OCR runs and broke imports on Windows; page counts and text extraction remain on 1.28.x.
- Preserve uppercase alphabetic figure suffixes in caption identities, so same-page figures such as Figure 1A and Figure 1B retain separate captions and assets; parenthesized panel labels remain part of the base figure.
- Keep cross-page figure reservations non-deliverable until page-qualified assets and crop evidence resolve; split shared same-page groups only when caption-band ownership uniquely covers every asset.
- Extend matched figure crops to include owned inner-text blocks outside asset bounds without absorbing unowned nearby text.

- Discover freshly indexed papers in OCR Workspace before any OCR directory exists; retain historical OCR records and report PDF readiness without writing artifacts (#351). Switching back from an empty filter replaces the empty state with the matching rows.
- Read existing notes through the Obsidian adapter when its file cache is cold. Refresh externally written notes without deleting/recreating them.
- Compare the published runtime pointer through the release spelling so an RC4 pointer stays a stale actionable mismatch under an rc5 bundle; `probe all` and read-model refresh carry the plugin version, and Setup renders reinstall on stale/mismatch instead of dead-ending (#356).
- Classify terminal OCR batches by settlement truth: blocked credential/source rejections surface `OCR_UPLOAD_FAILED` with failed/blocked keys and no re-upload, failures surface `OCR_RESULT_INVALID`, and only genuinely pending work keeps the poll-timeout resume instruction (#356). The Workspace shows the backend machine message first with actionable blocked/failed guidance naming the bounded keys, and drops the mutation snapshot before readback so resume refresh cannot resurrect stale statuses.
- Keep table caption/text/notes visible when no crop geometry exists: table object markdown emits no dangling image reference for unmaterialized crops, preserves provider HTML/text content with an explicit inability marker, and audit stays strict (#356). The single HTML flattener keeps header (`th`) and data (`td`) cells with matching-tag pairs.
- Route missing managed-runtime executables to an actionable Setup Wizard reinstall state during individual and aggregate status refreshes, without spawning the missing interpreter or changing the published pointer (#356).
- Route the memory probe liveness check through the owning service API: the old `paperforge.commands.embed._pid_alive` target does not exist, so live builds were misclassified as interrupted; live activity now reports ready/running correctly with the DTO schema unchanged.

## 1.5.8 (2026-05-19)

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
