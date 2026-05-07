# Phase 23: Canonical Asset Index & Safe Rebuilds - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade `formal-library.json` from a bare list of paper entries into a versioned, rebuildable, atomic-write canonical asset index. Support both full rebuilds and incremental refreshes after sync/OCR/deep-reading/repair. Extract index generation into its own module.

This phase covers the index file format, envelope, atomic writes, incremental refresh, and workspace path integration. It does NOT cover lifecycle/health/maturity derivation (Phase 24), surface convergence (Phase 25), or AI context packs (Phase 26).

</domain>

<decisions>
## Implementation Decisions

### Index envelope & format
- **D-01:** Index file stays at `indexes/formal-library.json` — same path, new format.
- **D-02:** Add versioned envelope wrapping the items list:
  ```json
  {
    "schema_version": "2",
    "generated_at": "2026-05-04T00:00:00",
    "paper_count": 42,
    "items": [...]
  }
  ```
- **D-03:** `formal-library.json` is the single canonical index. There is no second index file.
- **D-04:** Old bare-list format is auto-migrated to envelope format on first write (detect by no `schema_version` key at root).

### Atomic writes & file safety
- **D-05:** Use `tempfile.NamedTemporaryFile()` + `os.replace()` for atomic writes. Interrupted writes do not leave half-written files.
- **D-06:** Add `filelock` for cross-process locking during index writes (sync/ocr/repair may race).
- **D-07:** Lock timeout: 10 seconds, then fail with clear error.

### Incremental refresh
- **D-08:** Support both full rebuild and incremental refresh by key.
- **D-09:** Incremental refresh: read existing index, update only the entries whose keys changed, write back.
- **D-10:** Full rebuild: available via `paperforge sync --rebuild-index` explicit flag, also triggered automatically when `schema_version` mismatch is detected.
- **D-11:** After `sync`, `ocr`, `deep-reading`, `repair` — call incremental refresh for the affected key(s).

### Workspace paths in index entries
- **D-12:** Each index entry gains these path fields (matching Phase 22 workspace structure):
  - `paper_root`: `Literature/<domain>/<key> - <Short Title>/`
  - `main_note_path`: `<paper_root>/<key> - <Short Title>.md`
  - `fulltext_path`: `<paper_root>/fulltext.md`
  - `deep_reading_path`: `<paper_root>/deep-reading.md`
  - `ai_path`: `<paper_root>/ai/`
- **D-13:** Existing system paths are retained: `ocr_path`, `meta_path`, `note_path` (backward compat).
- **D-14:** Path fields are written to both the canonical index JSON AND mirrored in note frontmatter (so Base views can still read them).

### Module extraction
- **D-15:** Extract index generation logic from `sync.py` to a new module `paperforge/worker/asset_index.py`.
- **D-16:** `asset_index.py` exports: `build_index(vault)`, `refresh_index_entry(vault, key)`, `get_index_path(vault)`.
- **D-17:** `run_index_refresh()` in `sync.py` delegates to `asset_index.build_index()`.

### Schema migration
- **D-18:** Legacy `formal-library.json` (bare list, no schema_version) is detected at read time and upgraded transparently.
- **D-19:** Old format is backed up as `formal-library.json.bak` before migration.

### Dependencies added
- **D-20:** Add `filelock` to project dependencies (for cross-process index locking).

### the agent's Discretion
- Exact envelope field naming (`generated_at` vs `last_built` vs `built_at`)
- `filelock` timeout value (may adjust 5-15s based on testing)
- Whether `--rebuild-index` flag goes on `sync` or a separate `paperforge rebuild-index` command
- Exact incremental refresh granularity (single key vs batch)

</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements

- `.planning/ROADMAP.md` §Phase 23 — Goal: "rebuildable, atomic, per-paper asset index"
- `.planning/REQUIREMENTS.md` — ASSET-01..04, MIG-02
- `.planning/phases/22-configuration-truth-compatibility/22-CONTEXT.md` — D-01..D-05 paper workspace structure
- `.planning/research/SUMMARY.md` §Phase 2 — Canonical index architecture

### Source code

- `paperforge/worker/sync.py` lines 1669-1745 — Current `run_index_refresh()` where index is built **Primary file to refactor**
- `paperforge/worker/_utils.py` line 263 — `"index": root / "indexes" / "formal-library.json"` path definition
- `paperforge/worker/_utils.py` line 264 — `pipeline_paths()` path inventory
- `paperforge/config.py` — `schema_version` (imported from Phase 22)
- `paperforge/worker/ocr.py` — OCR meta reading, needed for index metadata population
- `paperforge/worker/deep_reading.py` — deep reading status derivation
- `paperforge/worker/base_views.py` — Base generation (consumes frontmatter-backed path fields)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `paperforge/worker/sync.py` `run_index_refresh()` lines 1686-1745 — Current index build loop. The field mapping (line 1711-1740) is the core data model to evolve.
- `paperforge/worker/_utils.py` `write_json()` line 69 — Current write pattern. Will be replaced by atomic writer in `asset_index.py`.
- `paperforge/worker/_utils.py` `read_json()` line 23 — Current read pattern. Will still be used for reading index.

### Established Patterns

- Index is currently a side effect of `run_index_refresh()` in sync.py
- Index is rebuilt from `exports/*.json` (BBT data) + `ocr/<key>/meta.json` + formal note content
- All per-paper metadata is currently gathered in one loop (lines 1686-1745)
- `paperforge.config` import pattern: all workers import from `paperforge.config`

### Integration Points

- `paperforge/worker/sync.py:1745` — `write_json(paths["index"], index_rows)` — current write point
- `paperforge/worker/sync.py:1711-1740` — Entry field construction — will be extended with workspace paths
- `paperforge/worker/ocr.py:1813` — Calls `run_index_refresh(vault)` after OCR — needs to switch to incremental refresh
- `paperforge/worker/repair.py` — May need index refresh after repair
- `paperforge/worker/deep_reading.py` — May need to trigger index refresh after status update
- `paperforge/worker/status.py` — Reads counts; could read from index envelope instead of scanning filesystem

</code_context>

<specifics>
## Specific Ideas

- "尝试把一些东西放进json，人不用看到的内容，然后只需要一个索引json就行" — The canonical index JSON becomes the single machine-readable asset inventory. Machine-only fields (paths, provenance, status) live here. Human-facing fields are also mirrored in note frontmatter for Base views.
- Index envelope should be versioned so future schema migrations are safe.
- Incremental refresh should be keyed by `zotero_key` — simple, unique, already exists.

</specifics>

<deferred>

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-canonical-asset-index-safe-rebuilds*
*Context gathered: 2026-05-04*
