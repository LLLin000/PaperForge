# Memory Layer — Design Spec

> **Status:** Approved | **Date:** 2026-05-12
> **Review:** Passed (v2 — 5 BLOCKER, 3 MAJOR, 6 MINOR resolved)

## Goal

Add a SQLite-backed Memory Layer to PaperForge as a derived, rebuildable global index that serves
dashboard, resolver, agent-context, and search commands.

## Architecture

```
Zotero/BetterBibTeX → exports/*.json
    ↓
formal-library.json    (Canonical Index — source of truth, already exists)
    ↓
paperforge.db          (Memory Layer — derived, rebuildable SQLite index)
    ↓
paper-status / dashboard / agent-context / search / retrieve
```

**Core principle:** `paperforge.db` is a derived index, not the source of truth.
It can be safely deleted and rebuilt from `formal-library.json` at any time.

## Phase 1 Scope

**Tables:** `meta`, `papers`, `paper_assets`, `paper_aliases`

**Commands:**
- `paperforge memory build --json`
- `paperforge memory status --json`
- `paperforge paper-status <query> --json`

**NOT in Phase 1:** FTS5, chunk retrieval, embedding, `paperforge.db → Markdown` writes,
agent-context, dashboard integration.

## SQLite Location

```
<system_dir>/PaperForge/indexes/paperforge.db
```
(same directory as `formal-library.json`)

Register a new path key `"memory_db"` in `config.py:paperforge_paths()` pointing to
`paperforge / "indexes" / "paperforge.db"`. Do not reuse the existing `"index"` key.

## Schema

### Connection settings

- `PRAGMA journal_mode=WAL;` — allow concurrent reads during rebuild
- `PRAGMA foreign_keys=ON;`

### meta

```sql
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

Stores: `schema_version` (integer), `paperforge_version`, `created_at`, `last_full_build_at`,
`canonical_index_hash`, `canonical_index_generated_at`.

### Schema versioning strategy

On `paperforge memory build`, if the stored `schema_version` in `meta` does not match the
current version, DROP all tables and rebuild from scratch. `paperforge.db` is a derived index
— full rebuild is always safe. This mirrors `formal-library.json`'s schema-version-check
pattern in `asset_index.py:475-480`.

Initial schema version: `1`.

### papers

One row per paper. Columns directly map to `_build_entry()` entry dict fields.
`asset_state.py` pure functions (`compute_lifecycle`, `compute_health`, `compute_maturity`,
`compute_next_step`) are called at **build time** on each entry dict to populate derived columns.

```sql
CREATE TABLE IF NOT EXISTS papers (
    zotero_key           TEXT PRIMARY KEY,
    citation_key         TEXT NOT NULL DEFAULT '',
    title                TEXT NOT NULL,
    year                 TEXT,
    doi                  TEXT,
    pmid                 TEXT,
    journal              TEXT,
    first_author         TEXT,
    authors_json         TEXT,          -- json.dumps(entry["authors"], ensure_ascii=False)
    abstract             TEXT,
    domain               TEXT,
    collection_path      TEXT,
    collections_json     TEXT,          -- json.dumps(entry["collections"], ensure_ascii=False)
    has_pdf              INTEGER NOT NULL DEFAULT 0,
    do_ocr               INTEGER,
    analyze              INTEGER,
    ocr_status           TEXT,
    deep_reading_status  TEXT,
    ocr_job_id           TEXT,
    impact_factor        REAL,
    lifecycle            TEXT,          -- compute_lifecycle(entry) → "indexed"|"pdf_ready"|"fulltext_ready"|"deep_read_done"
    maturity_level       INTEGER,       -- compute_maturity(entry)["level"] → 1-4
    maturity_name        TEXT,          -- compute_maturity(entry)["level_name"]
    next_step            TEXT,          -- compute_next_step(entry) → "sync"|"ocr"|"/pf-deep"|"ready"
    pdf_path             TEXT,
    note_path            TEXT,
    main_note_path       TEXT,
    paper_root           TEXT,
    fulltext_path        TEXT,
    ocr_md_path          TEXT,
    ocr_json_path        TEXT,
    ai_path              TEXT,
    deep_reading_md_path TEXT,
    updated_at           TEXT           -- envelope["generated_at"] from formal-library.json
);
```

Indexes:
```sql
CREATE INDEX IF NOT EXISTS idx_papers_zotero_key  ON papers(zotero_key);
CREATE INDEX IF NOT EXISTS idx_papers_citation_key ON papers(citation_key);
CREATE INDEX IF NOT EXISTS idx_papers_doi         ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_domain      ON papers(domain);
CREATE INDEX IF NOT EXISTS idx_papers_year        ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_ocr_status  ON papers(ocr_status);
CREATE INDEX IF NOT EXISTS idx_papers_deep_status ON papers(deep_reading_status);
CREATE INDEX IF NOT EXISTS idx_papers_lifecycle   ON papers(lifecycle);
CREATE INDEX IF NOT EXISTS idx_papers_next_step   ON papers(next_step);
```

**Important notes about column→entry mapping:**

- `maturity_level` = `compute_maturity(entry)["level"]` (scalar 1-4, not the full dict)
- `updated_at` = the envelope's `generated_at` timestamp from `formal-library.json` (shared across all papers in a build)
- `lifecycle` values: `"indexed"`, `"pdf_ready"`, `"fulltext_ready"`, `"deep_read_done"` — these are NOT all members of the `Lifecycle` enum in `core/state.py` (which has `OCR_READY`, `ANALYZE_READY`, `ERROR_STATE` that are never produced). Use plain string comparison, not enum membership.
- `ai_context_ready` is a pre-seeded zero in `summarize_index()` (`asset_index.py:644`) but is never produced by `compute_lifecycle()`. Keep the zero bucket for Phase 3 compatibility but document it as reserved.

**Health dimensions** (`pdf_health`, `ocr_health`, `note_health`, `asset_health`) are NOT stored in the papers table. They are computed at query time via `asset_state.compute_health(entry_dict)`. The `paper-status` command reconstructs the entry dict from SQLite columns, then calls `compute_health()` in-process.

### paper_assets

```sql
CREATE TABLE IF NOT EXISTS paper_assets (
    paper_id       TEXT NOT NULL,
    asset_type     TEXT NOT NULL,
    path           TEXT NOT NULL,
    exists_on_disk INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (paper_id, asset_type),
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
```

Asset types and their source fields:

| asset_type     | source in entry dict       | notes                                                     |
| -------------- | -------------------------- | --------------------------------------------------------- |
| `pdf`            | `pdf_path`                   | wiki-link; check existence via filesystem                 |
| `formal_note`    | `note_path`                  | relative vault path                                       |
| `main_note`      | `main_note_path`             | workspace `{key}.md`                                        |
| `ocr_fulltext`   | `fulltext_path`              | copied from `ocr/{key}/fulltext.md`                         |
| `ocr_meta`       | derived from `ocr_json_path` | `ocr/{key}/meta.json`                                       |
| `deep_reading`   | `main_note_path`             | checks for `## 🔍 精读` section within main note (NOT a separate file; `deep_reading_path` is deprecated and always empty) |
| `ai_dir`         | `ai_path`                    | workspace `ai/` directory                                   |

### paper_aliases

```sql
CREATE TABLE IF NOT EXISTS paper_aliases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id   TEXT NOT NULL,
    alias      TEXT NOT NULL,
    alias_norm TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
```

Alias types (Phase 1):

| alias_type    | source            | normalized to lowercase     |
| ------------- | ----------------- | --------------------------- |
| `zotero_key`    | `entry["zotero_key"]` | as-is (uppercase)           |
| `citation_key`  | `entry["citation_key"]` | as-is (case-sensitive)      |
| `title`         | `entry["title"]`        | `.lower().strip()`            |
| `doi`           | `entry["doi"]`          | `.lower().strip()`            |

## Commands

### `paperforge memory build --json`

1. Resolve vault path
2. Read `formal-library.json` (canonical index envelope) via `read_index(vault)`
3. If index is `None` or missing → return `PFResult(ok=False, error=PFError(code=PATH_NOT_FOUND, message="Canonical index not found. Run paperforge sync --rebuild-index."))`
4. Extract `items` list and envelope metadata
5. Create/open `paperforge.db` (WAL mode)
6. If stored `schema_version` != current → DROP all tables
7. Create tables if not exist
8. Upsert `meta` rows: `schema_version`, `paperforge_version`, `created_at`, `last_full_build_at`, `canonical_index_generated_at`
9. Compute `canonical_index_hash` = SHA-256 of `json.dumps(sorted(items, key=lambda e: e["zotero_key"]), sort_keys=True, ensure_ascii=False)`; store in `meta`
10. For each entry in `items`:
    - Insert/upsert into `papers`
    - Insert/upsert into `paper_assets` (check `exists_on_disk` via `Path.exists()`)
    - Insert/upsert into `paper_aliases`
11. Return `PFResult(ok=True, data={...})` with `papers_indexed`, `assets_indexed`, `aliases_indexed` counts

**PFResult.next_actions format** (must match `core/result.py:26` — `list[dict]`):
```json
{
  "next_actions": [
    {"command": "paperforge paper-status <key> --json", "reason": "Look up a specific paper"}
  ]
}
```

### `paperforge memory status --json`

Check:
- `paperforge.db` exists → `db_exists: bool`
- `schema_version` matches current → `schema_ok: bool`
- `canonical_index_hash` matches computed hash of current `formal-library.json` → `fresh: bool`
- Paper count matches `envelope["paper_count"]` → `count_match: bool`
- Any check fails → `needs_rebuild: true`

Return `PFResult(ok=True, data={...})`.

### `paperforge paper-status <query> --json`

**Resolution is short-circuit:** stop at the first step that returns ≥1 result.

Resolution order:
1. Exact match on `zotero_key` (case-insensitive)
2. Exact match on `citation_key` (case-insensitive)
3. Exact match on `doi` (case-insensitive)
4. LIKE match on `title_norm` or normalized alias (`%<query_lower>%`)
5. Fallback: search `paper_aliases.alias_norm`

Behavior by result count:
- **0 results:** `PFResult(ok=False, error=NOT_FOUND, next_actions=[{"command": "paperforge search", ...}])`
- **1 result:** Full status with paper metadata, assets, lifecycle, next_step, recommended action
- **>1 results:** Candidate list only (no full status details)

Full status response includes:
- Paper metadata (title, year, authors, doi, journal, domain, abstract)
- Asset status (exists_on_disk for each asset type)
- Lifecycle state
- Health dimensions (computed at query time via `compute_health()`)
- Maturity level and name
- `next_step` with recommended action
- `recommended_action`: e.g., `"/pf-deep ABCDEFG"` or `"paperforge sync"` or `"paperforge ocr"`

## Integration Points

### With sync
After `paperforge sync` completes, optionally refresh memory for changed keys.
Not automatic in Phase 1.

### With dashboard
Dashboard should prefer `paperforge.db` for stats, fallback to file scanning.
This integration is deferred to Phase 2.

### With agent
Agent skill bootstrap runs `paperforge agent-context --compact --json` first.
This command is deferred to Phase 3.

## Constraints

1. `paperforge.db` is a derived index — deletable, rebuildable
2. No SQLite → Markdown writes in Phase 1
3. Reuse `asset_state.py` pure functions (compute_lifecycle, compute_health, compute_maturity, compute_next_step)
4. Health dimensions are computed at query time via `compute_health()`, not stored in SQLite
5. All `--json` output uses PFResult envelope (respecting `next_actions: list[dict]` contract)
6. SQLite connection uses WAL mode for concurrent reads
7. No external database services — only Python stdlib `sqlite3`
8. No PDF/image binary storage
9. No embedding or vector DB
10. Schema version mismatch → full drop-and-rebuild (derived index, always safe)
