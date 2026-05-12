# Phase 7 — Vector Retrieval

> **Date:** 2026-05-12 | **Depends on:** Memory Layer Phase 1-6

## Overview

Add semantic vector retrieval for OCR fulltext, built on ChromaDB with local embedding models.
Optional module, disabled by default. Activated by user via plugin settings toggle.

## Architecture

```
fulltext.md
    ↓ 剔除 ![[*]] 图片链接行
    ↓ 替换行内图片链接为 [Figure N]
    ↓ 按 <!-- page N --> 分页
    ↓ 每页按双换行分自然段
    ↓ 2-3 段一组 → 300-400 token/chunk, 1 段重叠
    ↓ section 检测 (规则匹配 IMRaD + Figure/Table)
    ↓ embed with bge-small-en-v1.5 (384d)
    ↓
ChromaDB @ indexes/vectors/
    ↓ paperforge retrieve "PEMF dose response" --json
    ↓ top-5 chunks + 前后各 1 chunk (补上下文)
    ↓
{ chunks: [{ paper_id, title, section, page, text, score }] }
```

## Dependencies

```
pip install chromadb sentence-transformers
```

Local model auto-downloads on first use (~130 MB for `bge-small-en-v1.5`).
API mode uses `openai` package (already in deps).

## Section Detection (Rule-based)

Scan each paragraph for known section keywords:

```
Case-insensitive match, must appear as standalone short line (< 80 chars):

Introduction | Methods | Materials | Results | Discussion
Conclusion | Abstract | Background | References | Supplementary
Figure \d+ | Fig\.? \d+ | Table \d+
```

Rules (priority order):
1. Exact keyword match → section = matched text
2. ALL CAPS short line → probable section title
3. Short line, no period, surrounded by blank lines → probable section title
4. Fallback: inherit from previous chunk in same page
5. Default: "Text" (unclassified)

## Local Model Options

| Model ID                   | Dim  | Size  | Chinese | Speed |
| -------------------------- | ---- | ----- | ------- | ----- |
| `BAAI/bge-small-en-v1.5`     | 384  | 130MB | [*]     | Fast  |
| `sentence-transformers/all-MiniLM-L6-v2` | 384  | 80MB  | —       | Fast  |
| `BAAI/bge-base-en-v1.5`     | 768  | 440MB | [*]     | Medium |
| `sentence-transformers/all-mpnet-base-v2` | 768  | 420MB | —       | Medium |

Model selection stored in `data.json` → `vector_db_model`.

## API Mode

```python
# When vector_db_mode == "api":
from openai import OpenAI
client = OpenAI(api_key=api_key)
embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)
```

API key from `data.json` → `vector_db_api_key` or fallback to `.env` `OPENAI_API_KEY`.
Max 8191 tokens per call — chunking ensures we stay under limit.

## ChromaDB Storage

```
<system_dir>/PaperForge/indexes/vectors/
    ├── chroma.sqlite3
    └── <uuid>/                      (Chroma internal)
```

Collection name: `paperforge_fulltext`.
Metadata stored per chunk: `paper_id, citation_key, title, year, section, page, chunk_index, token_estimate`.

## Commands

### `paperforge embed build [--force]`

1. Check `data.json` for `features.vector_db == true`
2. Read `formal-library.json` for all papers with `ocr_status == "done"`
3. For each paper: read `fulltext.md`, chunk, embed, insert into ChromaDB
4. If `--force`: delete existing collection, rebuild from scratch

Returns PFResult:
```json
{
  "ok": true,
  "data": {
    "papers_embedded": 21,
    "chunks_embedded": 420,
    "model": "BAAI/bge-small-en-v1.5",
    "mode": "local"
  }
}
```

### `paperforge retrieve <query> --json [--limit N] [--expand true]`

1. Embed query with same model
2. Query ChromaDB, get top-N chunks
3. If `--expand true` (default): fetch adjacent chunks (±1) for context
4. Join with papers table for metadata

Returns:
```json
{
  "ok": true,
  "data": {
    "query": "PEMF dose response chondrocyte",
    "chunks": [
      {
        "paper_id": "ABC123",
        "citation_key": "aaronStimulation2004",
        "title": "Stimulation of growth factor synthesis...",
        "year": 2004,
        "section": "Results",
        "page": 6,
        "chunk_text": "At 24h post-stimulation, chondrocyte proliferation increased...\n\n...",
        "adjacent_before": "... (previous chunk, if expanded)",
        "adjacent_after": "... (next chunk, if expanded)",
        "score": 0.92
      }
    ],
    "count": 5,
    "model": "BAAI/bge-small-en-v1.5"
  }
}
```

### `paperforge embed status --json`

Returns: db exists, collection exists, chunk count, model name, last build time.

## Integration with Memory Layer

### Memory build

`paperforge memory build` does NOT trigger embed build. Vector DB is separate, user-controlled.

### Incremental refresh

`refresh_paper()` extended:
```python
def refresh_paper(vault, zotero_key):
    # existing SQLite refresh...
    
    # If vector DB enabled:
    if vector_db_enabled(vault):
        # Delete old chunks for this paper
        collection.delete(where={"paper_id": zotero_key})
        # Re-embed this paper
        _embed_paper(vault, zotero_key)
```

Triggered after OCR completes (fulltext changes) or deep-finalize.

## Files

```
Create:
  paperforge/memory/vector_db.py     — ChromaDB init, embed, query, delete
  paperforge/memory/chunker.py       — fulltext → chunks (rule-based)
  paperforge/commands/embed.py       — CLI: embed build/status
  paperforge/commands/retrieve.py    — CLI: retrieve <query>

Modify:
  paperforge/memory/refresh.py       — add vector refresh hook
  paperforge/cli.py                  — register embed + retrieve
```

## Constraints

1. Optional — disabled until user enables in settings
2. Requires `pip install chromadb sentence-transformers` (user installs or plugin offers button)
3. Windows compatible (ChromaDB embedded mode works on Windows)
4. `paperforge.db` remains source of truth; ChromaDB is deletable and rebuildable
5. No GPU required; CPU embedding for 150 papers takes ~30 seconds
6. API mode: respects rate limits, batches chunks to minimize API calls
