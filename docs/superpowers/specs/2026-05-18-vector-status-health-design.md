# Vector Status + Health + Auto-Embed — Design Spec

> **Status:** Draft | **Date:** 2026-05-18
> **Review:** Pending
> **Depends on:** memory-layer-simplify (embedding/ package already extracted)

## Goal

1. **Per-paper `vector_status` column** in `paperforge.db` for fast resume, accurate health check, and agent context
2. **`_check_vector()` strictness** — verify actual data, not just directory existence
3. **Resume logic fix** — use SQLite instead of ChromaDB for skip detection; handle corrupted index gracefully
4. **Auto-embed after OCR** — `embed_paper` + `vector_status` update runs when OCR completes

## Schema Change

### papers table — new column

```sql
ALTER TABLE papers ADD COLUMN vector_status TEXT NOT NULL DEFAULT '';
```

Values:
| Value      | Meaning                                   |
| ---------- | ----------------------------------------- |
| `''` (empty) | Not OCR-done, or not yet checked           |
| `pending`  | OCR done, queued for embedding             |
| `embedded` | Successfully embedded in ChromaDB          |
| `failed`   | Embedding errored (retry on next --resume) |

### Schema version: 2 → 3

```python
CURRENT_SCHEMA_VERSION = 3  # Bump from 2 for vector_status column
```

## Architecture

```
OCR completion
    ↓
  ocr.py → sync → _vec_auto_embed_if_new()
    ↓                                       ↓
  embed_paper()                          paperforge.db
    ↓ (ChromaDB)                          UPDATE vector_status='embedded'
  chunks stored                           (or 'failed' on error)

embed build --resume
    ↓
  SELECT zotero_key FROM papers
    WHERE ocr_status='done'
      AND (vector_status IS NULL OR vector_status != 'embedded')
    ↓
  chunk → embed → UPDATE vector_status='embedded'

embed build --force
    ↓
  DELETE vectors/ directory
  Mark all OCR-done papers as 'pending'
  For each: chunk → embed → UPDATE vector_status='embedded'

_check_vector()
    ↓
  SELECT COUNT(*) FROM papers
    WHERE ocr_status='done' AND vector_status='embedded'
  SELECT COUNT(*) FROM papers WHERE ocr_status='done'
    ↓
  coverage = embedded / total
  → degraded if < 1.0 or corrupted or disabled
```

## File Changes

### Part A: Schema + Builder

**Files:**
- Modify: `paperforge/memory/schema.py`
  - `CURRENT_SCHEMA_VERSION = 3`
  - Add `vector_status TEXT NOT NULL DEFAULT ''` to `CREATE_PAPERS`
- Modify: `paperforge/memory/_columns.py`
  - Add `"vector_status"` to `PAPER_COLUMNS` (so rebuild includes it)
- Modify: `paperforge/memory/builder.py`
  - Before DELETE: save old `{zotero_key: vector_status}` map
  - After INSERT: restore saved map for matching keys
  - Keeps auto-embedded status across memory rebuilds

### Part B: Embed Builder — Per-paper status tracking

**Files:**
- Modify: `paperforge/embedding/builder.py`
  - `embed_paper()`: accept optional `conn` parameter to update DB
  - Or: caller handles the DB write
- Modify: `paperforge/commands/embed.py`
  - Before build loop: `UPDATE papers SET vector_status='pending' WHERE ocr_status='done'`
  - After each paper success: `UPDATE papers SET vector_status='embedded' WHERE zotero_key=?`
  - On error: `UPDATE papers SET vector_status='failed' WHERE zotero_key=?`
  - Resume mode: `SELECT zotero_key FROM papers WHERE ocr_status='done' AND (vector_status IS NULL OR vector_status != 'embedded')`
  - Remove the ChromaDB `collection.get()` per-paper check

### Part C: Health — `_check_vector()` strict

**Files:**
- Modify: `paperforge/memory/runtime_health.py:120-153`
  - Disabled → `degraded` (was `ok`)
  - Query paperforge.db for coverage ratio
  - If coverage == 0 and no build → `degraded` "not built"
  - If 0 < coverage < 1 → `degraded` "partial coverage (N/M)"
  - If `get_embed_status().corrupted == True` → `degraded` with `repair_command: "paperforge embed build --force"`
  - Only return `ok` when: coverage == 1 AND ChromaDB healthy

### Part D: Auto-embed — Update status after OCR

**Files:**
- Modify: `paperforge/worker/asset_index.py:479-505`
  - After `embed_paper()` succeeds: open paperforge.db, `UPDATE papers SET vector_status='embedded'`
  - On exception: `UPDATE papers SET vector_status='failed'`
  - Import `get_connection`, `get_memory_db_path` for DB access

### Part E: Resume — SQLite query instead of ChromaDB check

**Files:**
- Modify: `paperforge/commands/embed.py:172-179`
  - Remove: `get_collection(vault).get(where={"paper_id": key})`
  - Replace with: the `SELECT` before the loop filters out already-embedded papers
  - No per-paper ChromaDB queries

### Part F: Agent Context — Coverage reporting

**Files:**
- Modify: `paperforge/memory/context.py`
  - Add vector coverage stats to `get_agent_context()` output
  - `"vector": { "enabled": bool, "embedded": N, "total_ocr_done": M, "coverage": float }`

### Part G: Error handling — Corrupted index fallback

**Files:**
- Modify: `paperforge/commands/embed.py`
  - In resume mode, if `get_embed_status().corrupted == True`: log warning, fall through to embed anyway (cannot skip, ChromaDB is broken)
  - The `--resume` loop doesn't try `collection.get()` anymore (Part E), so corruption doesn't block it
  - But `collection.add()` will still fail with compaction error → user sees clear message to use `--force`

## ChromaDB Corruption Recovery Flow

```
User runs embed build --resume
  → SQLite says 200 papers need embedding
  → First embed_paper() → collection.add() → compaction error
  → builder.py catches HNSW/compaction error
  → Raises RuntimeError with "Run 'paperforge embed build --force'"
  → Embed build exits with error message
  → _check_vector() shows degraded + repair_command
  → User runs embed build --force
  → Delete vectors/ directory
  → Fresh build succeeds
```

## Dataset Flows

### Normal flow: new paper added
```
  sync → formal-library.json updated
  → _vec_auto_embed_if_new() chunks + embeds + sets vector_status='embedded'
  → memory build (if user runs it) preserves vector_status
```

### Normal flow: embed build on all papers
```
  embed build --force
  → DELETE vectors/
  → SQL UPDATE vector_status='pending' WHERE ocr_status='done'
  → For each: embed + UPDATE vector_status='embedded'
  → _check_vector() sees 658/658 → ok
```

### Normal flow: incremental update
```
  embed build --resume
  → SQL SELECT WHERE ocr_status='done' AND vector_status!='embedded'
  → Only new or failed papers
  → Fast: no ChromaDB queries
```

### Degraded flow: partial build
```
  embed build interrupted after 300/658
  → _check_vector() sees 300/658 → degraded "partial (58%)"
  → Agent sees coverage < 1.0, falls back to FTS
  → Next embed build --resume picks up remaining 358
```

## Testing

### Unit tests
- `tests/unit/memory/test_schema.py`: schema v3 has vector_status column
- `tests/unit/commands/test_embed.py`: resume uses SQLite, not ChromaDB get
- `tests/unit/memory/test_health.py`: _check_vector returns degraded when coverage < 1

### Manual tests
- `paperforge embed build --resume` after partial build
- `paperforge embed build --force` 
- `paperforge runtime-health --json` shows correct vector coverage
- `paperforge agent-context --json` shows vector coverage

## Out of Scope

- Automatic embed build trigger on OCR completion (user still clicks Build or runs CLI)
- UI for per-paper vector status in plugin dashboard
- ChromaDB version pinning/downgrade (user manages chromadb version)
