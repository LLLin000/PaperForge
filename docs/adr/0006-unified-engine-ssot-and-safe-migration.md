# ADR-0006: Unified File & State Engine, SQLite Runtime SSOT, Identity-Anchored Workspaces, and Atom-Level Safe Migration

Status: accepted
Date: 2026-11-21
Related: [ADR-0002](0002-unified-artifact-materialization-state-contract.md), [ADR-018](../ARCHITECTURE.md#adr-018-unified-file--state-engine-sqlite-runtime-ssot-identity-anchored-workspaces--atom-level-safe-migration)

## Context

Forensic review of veteran multi-era vaults and the v2.0 migration/indexing codebase identified four systemic failure modes:

1. **Fragile monolithic & fragmented JSON state**: `formal-library.json` (~4+ MB at ~1k papers) suffers O(N) rewrite amplification on single-paper mutations, all-or-nothing JSON corruption blast radius, and frequent hash/version drift against `paperforge.db`. Around it, runtime state is fragmented across 20+ independent JSON/JSONL/TXT files (`ocr-queue.json`, `ocr_maintenance.json`, `vector-build-state.json`, `.sync-fastpath.json`, `sync-orphan-state.json`, `skill-deploy-state.json`, `annotation-cache.json`, etc.), forcing repeated full-vault `rglob("*.md")` scans and heavy disk I/O even when running via `paperforge daemon --stdio`.
2. **Brittle filename, positional, and string-reconstruction matching**: Key discovery and cleanup paths still parse `" - "` directory/file prefixes, require fixed `len(relative.parts) == 2` depth, reconstruct folder names from `slugify_filename(title)`, and execute wildcard `glob(f"{key} - *")` deletions.
3. **Coarse-grained migration & wasted OCR truth salvage**:
   - `materialization/ocr.py` treats missing/corrupt `canonical/blocks.raw.jsonl` as `ocr.run` (paid remote OCR) without checking whether `json/result.json` (Tier-0 paid OCR truth) is intact for zero-cost local `backfill_from_result`.
   - `migrate_vault_storage()` wraps the whole vault in one rollback boundary where 1 unreadable paper aborts 900+ valid papers, moves `System/Zotero` without verifying `zotero_data_dir`, and fails to persist `restorable_fulltexts` in `.migration-journal.json`.
4. **Unguarded deletions & un-converged defaults**: `sync_service.py` (`flat_note.unlink()`), `asset_index.py` (`stale_note.unlink()`), `ocr.py` (`shutil.rmtree(ocr_dir)`), and `skill_deploy.py` (`shutil.rmtree(backup_dir)`) bypass `trash_remove()`, while `config.py` still defaults `system_dir` to `"System"` instead of `".paperforge"`.

## Decision

### 1. Ownership-Split Single Source of Truth (SSOT)
- **Zotero**: Upstream bibliographic truth (read-only sync input).
- **Per-Paper Plaintext / Append-Only Sidecars** (Fault radius = 1 paper; Calibre-style disaster recovery base):
  - `<workspace>/<KEY>.md` (human notes + immutable `zotero_key` anchor)
  - `<workspace>/paper-meta.json` (immutable workspace identity & schema anchor; no cached external path strings)
  - `<workspace>/annotations.jsonl` & `<workspace>/ai/memory-card.json`
  - `.paperforge/logs/reading-log.jsonl` & `project-log.jsonl`
  - `.paperforge/ocr/<KEY>/json/result.json` (write-once OCR raw truth with `pdf_sha256` & `result_sha256`)
- **SQLite Engine (`paperforge.db`) as Single Runtime Authority**:
  - Consolidate canonical paper records, `workspace_registry` (`zotero_key -> current workspace/note paths`), task/OCR/embedding queues, OCR projection summaries, skill deploy state, and monotonic state sequence cursors inside `paperforge.db` under `WriterLock` + ACID transactions.
  - Retire `formal-library.json` as a runtime truth source (retain only as an optional one-way export snapshot if requested).
  - Support lossless full reconstruction (`db rebuild-from-truth`) by scanning Zotero exports + per-paper workspace sidecars + `.paperforge/ocr/<KEY>/`.

### 2. Identity-First Resolution
- Replace `" - "` filename splitting, `len(relative.parts)` depth checks, `slugify` path guessing, and `glob("{key} - *")` with SQLite `workspace_registry` lookups verified against `paper-meta.json` / Markdown YAML `zotero_key`.
- Eliminate hot-path `rglob("*.md")` loops in `dashboard`, `status`, `repair`, `ocr`, and `finalize` in favor of indexed DB queries + targeted dirty-set verification.

### 3. Atom-Level Safe Migration & Zero-Deletion Invariant
- **Capability/Shape Fingerprinting (`VaultUpgradeInspector`)**: Inspect disk reality orthogonally across Runtime, Plugin bundle purity, Secrets, Config, Storage layout, Workspaces, Index/DB/Vectors, Base views, and Skills—supporting arbitrary multi-era mixed states and classifying items into:
  - **(A) Deterministic Lossless Move/Upgrade**
  - **(B) Non-Auto-Migratable Reconfiguration** (split into low-impact vs experience-critical with guided remediation)
  - **(C) Human/Sync Tamper Detection & Integrity Repair**
- **Tiered OCR Truth Salvage**: Layer 0 (`json/result.json` / `raw/`) migrates atomically per paper; any derived-layer defect (`blocks.*`, `structure/`, `render/`, `assets/`) quarantines the defective derived file and schedules zero-cost local `backfill_from_result` rather than blocking migration or re-billing OCR APIs.
- **Per-Item Isolation**: Pre-flight immutable backups for small high-value files (`paperforge.json`, `data.json`, `Bases/*.base`, `paperforge.db`), followed by per-paper transactions so single-item failures report cleanly without aborting healthy papers.
- **No-Delete Guarantee**: Ban bare `unlink()` / `rmtree()` across sync, index, and migration paths; every displaced artifact routes through `quarantine_move()` into `.paperforge/trash/` or `.paperforge/backups/`. Permanent purge requires verified PaperForge ownership + explicit user confirmation.

### 4. Stateful Engine Daemon & Standard Convergence
- Converge fresh setups on `system_dir: ".paperforge"`, `skill_dir: ".agents/skills"`, and `.paperforge/vault-manifest.json` (`layout_version` + subsystem schemas).
- Evolve `paperforge daemon` from a stateless CLI argv wrapper into a warm engine host holding pooled read-only DB connections, cached config/probe projections invalidated by DB event sequence, and an idle background worker queue for incremental sync, local OCR derived backfill, and resumable embedding completion.

### 5. Ownership Provenance, Anti-False-Positive Gates, & Progressive Non-Blocking UX
- **Three-Tier Veteran Detection (Zero New-User False Positives)**: Never infer a legacy PaperForge vault from generic folders (`System/`, `Literature/`, `Bases/`) or generic citekey properties alone. Require Tier-1 strong PaperForge provenance (`paperforge.json` exclusive keys, `System/PaperForge` or `99_System/PaperForge`, `.paperforge/` engine subtrees, or historical plugin `data.json` markers); fall back to Rescue Mode only on Tier-2 composite signatures (`paper-meta.json` with `paperforge_version` + `ocr_status`, `# PAPERFORGE_VIEW:`, or 4-key frontmatter co-occurrence `zotero_key + ocr_status + deep_reading_status + do_ocr`).
- **Five-Bucket Full-Vault Census**: Classify every scanned object before mutation into `PF_MACHINE_PURE`, `PF_USER_ENRICHED`, `PF_CONFIRMED_RESIDUAL`, `USER_SOVEREIGN` (strictly hands-off), or `AMBIGUOUS_OR_CLONE` (freeze-in-place).
- **Clone & Lookalike Guards**:
  1. Legacy flat notes require 4 orthogonal checks (exact `<literature_dir>/<domain>/` depth, generator filename pattern, 4-key PaperForge signature, and zero unique user body text absent from the workspace `<KEY>.md`).
  2. Native Obsidian `.base` files (`type: table`) without `# PAPERFORGE_VIEW:` or `RETIRED_PF_VIEWS + zotero_key` filters are `USER_SOVEREIGN` and never touched.
  3. `System/` sibling folders (e.g., `System/Attachments/`) and unknown user `.md` files placed inside `System/PaperForge/` stay visible; symlinks / Windows Junctions are never traversed or moved across drives; cloud-sync conflict copies (`*conflict*`, `*(冲突副本)*`), locked `.db` handles, non-UTF8/broken YAML files, and backlink aliases (`aliases: [...]`) are explicitly guarded.
- **Progressive Two-Speed Migration (Anti-Perfectionism Escape Hatch)**:
  - **Fast Cutover (< 3s, 1-Click)**: Perform only O(1) structural cutover upfront (pre-flight config/base snapshot, atomic directory rename `System/PaperForge -> .paperforge`, config update, `vault-manifest.json`). Keep legacy readers tolerant (`Read-Both, Write-New`).
  - **Background / Just-in-Time (JIT) Healing**: Defer per-paper metadata cleanup, visual asset materialization, OCR derived backfills, and residual quarantine to non-blocking background batches (surfaced quietly on `.pf-global-activity-strip`) or JIT on paper open. Any unparsed/weird outlier paper is skipped in place (`Skip & Isolate`) rather than blocking the remaining 99% of the library.

## Consequences
- Eliminates multi-source hash drift between `formal-library.json`, `paperforge.db`, and `paper-meta.json`.
- Reduces single-paper state mutations from O(N) 4 MB+ JSON rewrites to O(1) SQLite transactions and removes repeated full-vault `rglob("*.md")` scans.
- Guarantees veteran vault upgrades never lose user notes, manual fulltext edits, or paid OCR raw results even on mid-flight errors, unforeseen legacy anomalies, or partial file corruption.
