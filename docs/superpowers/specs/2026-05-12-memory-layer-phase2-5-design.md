# Memory Layer Phase 2-5 — Complete Spec

> **Date:** 2026-05-12 | **Depends on:** Phase 1 (metadata DB) + FTS5 search

## Overview

Four remaining features to complete the Memory Layer, in priority order:

| # | Feature | Purpose |
|---|---------|---------|
| 1 | **agent-context** | Agent 启动路由器：library 概览 + commands 清单 + collection 地图 + rules |
| 2 | **Dashboard SQLite** | 仪表盘从文件扫描切换到读 paperforge.db |
| 3 | **Incremental refresh** | sync/ocr/deep-finalize 后单篇刷新 memory，不重建全库 |
| 4 | **Chunk retrieve** | OCR 全文 + figure caption 片段检索，返回带引用的证据 paragraph |

---

## Feature 1: agent-context

### Design

纯只读路由命令。Agent 拿到后知道：库里有什么、能调用什么、从哪开始。

### Output structure

```json
{
  "ok": true,
  "command": "agent-context",
  "version": "1.6.0",
  "data": {
    "paperforge": {
      "version": "1.6.0",
      "vault": "/path/to/vault",
      "memory_db": "ready"
    },
    "library": {
      "paper_count": 283,
      "domain_counts": {"骨科": 120, "运动医学": 80, "其他": 83},
      "lifecycle_counts": {"indexed": 2, "pdf_ready": 260, "fulltext_ready": 18, "deep_read_done": 3},
      "ocr_counts": {"done": 21, "pending": 262},
      "deep_reading_counts": {"done": 3, "pending": 280}
    },
    "collections": [
      {"name": "骨科", "count": 120, "sub": ["骨折", "软骨", "韧带"]},
      {"name": "运动医学", "count": 80}
    ],
    "commands": {
      "paper-status": {
        "usage": "paperforge paper-status <zotero_key|citation_key|doi|title> --json",
        "purpose": "Look up one paper's full status and recommended next action"
      },
      "search": {
        "usage": "paperforge search <query> --json [--collection NAME] [--domain NAME] [--ocr done|pending] [--year-from N] [--year-to N] [--limit N]",
        "purpose": "Full-text search with optional collection/domain/lifecycle filters"
      },
      "retrieve": {
        "usage": "paperforge retrieve <query> --json [--limit N]",
        "purpose": "Search OCR fulltext chunks for evidence paragraphs (coming soon)"
      },
      "deep": {
        "usage": "/pf-deep <zotero_key>",
        "purpose": "Full three-pass deep reading with chart analysis"
      },
      "ocr": {
        "usage": "/pf-ocr",
        "purpose": "Run OCR on papers marked do_ocr:true"
      },
      "sync": {
        "usage": "/pf-sync",
        "purpose": "Sync Zotero and regenerate formal notes + index"
      }
    },
    "rules": [
      "Use paperforge.db via CLI commands before reading individual files.",
      "Do not infer paper state from stale frontmatter when memory status is fresh.",
      "Read source files only after resolving candidates via paper-status or search.",
      "To locate a paper: start with collection scope if known, then expand to full library search."
    ]
  }
}
```

### Implementation

**File:** `paperforge/memory/context.py`

```python
def get_agent_context(vault: Path) -> dict:
    """Build agent bootstrap context from paperforge.db."""
    conn = get_connection(get_memory_db_path(vault), read_only=True)
    try:
        # Library overview
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        domains = {r["domain"]: r["cnt"] for r in conn.execute(
            "SELECT domain, COUNT(*) as cnt FROM papers GROUP BY domain ORDER BY cnt DESC"
        ).fetchall()}
        lifecycles = ...  # same GROUP BY pattern
        ocr = ...
        deep = ...
        
        # Collection tree
        collections = _build_collection_tree(conn)
        
        return {...}  # full structure above
    finally:
        conn.close()

def _build_collection_tree(conn) -> list[dict]:
    """Build nested collection hierarchy from papers.collection_path."""
    rows = conn.execute(
        "SELECT collection_path, COUNT(*) as cnt FROM papers "
        "WHERE collection_path != '' GROUP BY collection_path ORDER BY cnt DESC"
    ).fetchall()
    # Parse pipe-separated paths into tree
    # "骨科 | 骨折" -> nested under 骨科
```

**File:** `paperforge/commands/agent_context.py` — CLI wrapper with `--json` flag.

**CLI:** `paperforge agent-context --json`

### Constraints
- Pure read-only on paperforge.db
- If DB missing: return error with message "Run paperforge memory build"
- All SQL queries wrapped in try/except with graceful error handling
- Output wrapped in PFResult dataclass (matches all other CLI commands)

**Schema version:** `CURRENT_SCHEMA_VERSION` bumped to `2` when `paper_chunks` and `paper_chunk_fts` tables are added (Feature 4). On version mismatch, `memory build` performs full drop-and-rebuild as per existing strategy.

---

## Feature 2: Dashboard SQLite Integration

### Design

`dashboard.py` currently scans all `.md` files with regex frontmatter parsing. Replace with SQLite queries. Keep fallback to file scanning if DB is missing or stale.

### Change

**File:** `paperforge/commands/dashboard.py`

The `_gather_dashboard_data()` function currently at lines 54-163 will be refactored:

```python
def _gather_dashboard_data(vault: Path) -> dict:
    db_path = get_memory_db_path(vault)
    if db_path.exists():
        try:
            return _dashboard_from_db(vault, db_path)
        except Exception:
            pass  # fall through to file scanning
    return _dashboard_from_files(vault)  # existing logic, renamed
```

New function `_dashboard_from_db()`:
```python
def _dashboard_from_db(vault, db_path) -> dict:
    conn = get_connection(db_path, read_only=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        
        # PDF health
        pdf_rows = conn.execute(
            "SELECT lifecycle FROM papers"
        ).fetchall()
        pdf_healthy = sum(1 for r in pdf_rows if r["lifecycle"] != "indexed")
        pdf_missing = total - pdf_healthy
        
        # OCR health
        ocr_done = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE ocr_status='done'"
        ).fetchone()[0]
        ocr_pending = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE ocr_status NOT IN ('done','failed')"
        ).fetchone()[0]
        ocr_failed = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE ocr_status='failed'"
        ).fetchone()[0]
        
        # Domain counts
        domain_counts = {r["domain"]: r["cnt"] for r in conn.execute(
            "SELECT domain, COUNT(*) as cnt FROM papers GROUP BY domain"
        ).fetchall()}
        
        # Permissions (unchanged — still checks file existence)
        permissions = _check_permissions(vault)
        
        return {
            "stats": {
                "papers": total,
                "pdf_health": {"healthy": pdf_healthy, "missing": pdf_missing, "broken": 0},
                "ocr_health": {"pending": ocr_pending, "done": ocr_done, "failed": ocr_failed},
                "domain_counts": domain_counts,
                "_source": "paperforge.db"
            },
            "permissions": permissions
        }
    finally:
        conn.close()
```

### Constraints
- Keep existing `_dashboard_from_files()` as fallback, rename from current `_gather_dashboard_data()`
- Dashboard output format must NOT change (plugin depends on it)
- Add `_source` field so plugin can display data freshness
- If DB is stale (`memory status` shows needs_rebuild), fall back to file scanning

---

## Feature 3: Incremental Refresh

### Design

After `sync`, `ocr`, or `deep-finalize` modifies one paper, refresh only that paper's entries in SQLite instead of full `memory build`.

### Implementation

**File:** `paperforge/memory/refresh.py`

```python
def refresh_paper(vault: Path, zotero_key: str) -> bool:
    """Incrementally refresh one paper in paperforge.db from formal-library.json."""
    envelope = read_index(vault)
    if not envelope:
        return False
    items = envelope if isinstance(envelope, list) else envelope.get("items", [])
    
    # Find the matching entry
    entry = None
    for e in items:
        if e.get("zotero_key") == zotero_key:
            entry = e
            break
    if not entry:
        return False
    
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=False)
    try:
        # Upsert paper row (same logic as builder)
        _upsert_paper(conn, entry, envelope.get("generated_at", ""))
        # Replace assets for this key
        conn.execute("DELETE FROM paper_assets WHERE paper_id=?", (zotero_key,))
        _insert_assets(conn, entry, vault)
        # Replace aliases for this key
        conn.execute("DELETE FROM paper_aliases WHERE paper_id=?", (zotero_key,))
        _insert_aliases(conn, entry)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### Integration points

Trigger `refresh_paper(vault, key)` after:
- `paperforge sync` — for each updated paper
- `paperforge ocr` — after OCR completes for a paper
- `paperforge deep-finalize <key>` — after marking deep reading done
- `paperforge repair --fix` — after repairing state

### Constraints
- Reuse `_build_entry()` logic from builder.py (extract shared helpers)
- Only refresh if paperforge.db exists (no auto-build)
- If formal-library.json is stale (entry not found), skip silently
- Transactional: all-or-nothing per paper

---

## Feature 4: Chunk Retrieval

### Design

Split OCR fulltext into paragraph-level chunks, store in `paper_chunks` table, index with FTS5. Figure captions from `figure-map.json` included as a chunk source type.

### Schema

```sql
CREATE TABLE IF NOT EXISTS paper_chunks (
    chunk_id      TEXT PRIMARY KEY,
    paper_id      TEXT NOT NULL,
    source_type   TEXT NOT NULL,   -- 'ocr_fulltext' | 'figure_caption' | 'abstract' | 'formal_note'
    section_title TEXT,            -- e.g., "Methods", "Results", "Figure 3"
    page_number   INTEGER,
    chunk_index   INTEGER,
    chunk_text    TEXT NOT NULL,
    token_estimate INTEGER,
    content_hash  TEXT,
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);

CREATE VIRTUAL TABLE IF NOT EXISTS paper_chunk_fts USING fts5(
    chunk_id UNINDEXED,
    paper_id UNINDEXED,
    source_type,
    section_title,
    chunk_text,
    content='paper_chunks',
    content_rowid='rowid'
);
```

### Chunking strategy

- **OCR fulltext**: Split by `<!-- page N -->` markers, then by double-newline paragraphs within each page. Max 500 tokens per chunk.
- **Figure captions**: Read `figure-map.json` from `ocr/<key>/`, one chunk per figure entry.
- **Abstract**: One chunk per paper (source_type='abstract').
- **Formal note**: Optional — split `## 🔍 精读` sections into chunks.

### Command

```
paperforge retrieve <query> --json [--limit N] [--source ocr_fulltext|figure_caption|all]
```

Output:
```json
{
  "ok": true,
  "command": "retrieve",
  "data": {
    "query": "PEMF dose response chondrocyte",
    "chunks": [
      {
        "zotero_key": "ABC123",
        "title": "...",
        "source_type": "ocr_fulltext",
        "section_title": "Results",
        "page_number": 6,
        "chunk_text": "At 24h post-stimulation, chondrocyte proliferation increased...",
        "rank": -2.5
      }
    ]
  }
}
```

### Constraints
- Chunks populated during `memory build` (full) or `memory refresh --key X` (incremental)
- Only for papers with `ocr_status == "done"`
- Figure-map.json must exist for figure caption chunks
- Max 3 paragraphs per chunk; overlap = 0
- `paper_chunks` and `paper_chunk_fts` added to `ALL_TABLES` and `ensure_schema()`
- FTS content sync triggers added for `paper_chunks` ↔ `paper_chunk_fts`
- `CURRENT_SCHEMA_VERSION` bumped to `2`

---

## Implementation Order

1. **agent-context** — highest value for agent workflow
2. **Dashboard integration** — unify data sources
3. **Incremental refresh** — performance improvement
4. **Chunk retrieval** — most complex, depends on OCR pipeline

Each feature gets its own plan → execute cycle within this spec.
