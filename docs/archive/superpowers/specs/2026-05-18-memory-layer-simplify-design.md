# Memory Layer Simplification — Design Spec

> **Status:** Draft | **Date:** 2026-05-18
> **Review:** Pending

## Goal

Simplify the memory/embedding layer by: (1) extracting vector DB logic from `memory/vector_db.py` into a new `embedding/` package, (2) removing local ChromaDB + sentence-transformers embedding model support entirely, keeping only API-based embedding, (3) ensuring zero breakage across all consumers.

## Motivation

The current `memory/vector_db.py` (364 lines) mixes ChromaDB local mode, sentence-transformers model loading, OpenAI API embedding, build state management, and retrieval — all in one file. This creates unnecessary dependency surface (`chromadb`, `sentence_transformers`, `torch`, `transformers`) and architectural coupling.

PaperForge is a **literature workflow engine**, not a local vector database server. API embedding via OpenAI-compatible providers is sufficient for semantic search enhancement. Local mode adds ~2GB of dependencies and significant maintenance burden with no proportional benefit.

## Constraint: Plugin is Immutable

The Obsidian plugin (`plugin/main.js`) reads exactly these JSON snapshot files:
- `System/PaperForge/indexes/memory-runtime-state.json`
- `System/PaperForge/indexes/vector-runtime-state.json`
- `System/PaperForge/indexes/runtime-health.json`
- `System/PaperForge/indexes/vector-build-state.json`

These files **must continue to exist at their current paths with the same schema**. No plugin code changes are allowed. The refactoring is Python-only.

## Architecture

```
Before:
  memory/vector_db.py         (364 lines — ChromaDB + ST + OpenAI + build state + retrieve + status)
  worker/vector_db.py         (92 lines — preflight + embed status)
  worker/asset_index.py:442   (inline auto-embed during sync)

After:
  embedding/                  (NEW package — API-only embedding)
    __init__.py                — public exports for all consumers
    _config.py                 — settings reader (.env + plugin data.json)
    providers/
      __init__.py
      base.py                  — EmbeddingProvider ABC
      openai_compatible.py     — OpenAI-compatible API client
    builder.py                 — embed_paper() via API only
    search.py                  — retrieve_chunks() via API only
    build_state.py             — build state persistence (read/write/mark)
    status.py                  — get_embed_status()
    preflight.py               — _preflight_check()

  memory/vector_db.py          → deprecated shim (forwards to embedding/)
  worker/vector_db.py          → deprecated shim (forwards to embedding/)

  memory/state_snapshot.py     — UNCHANGED (still writes 3 legacy snapshot files)
  memory/                      — UNCHANGED: db.py, schema.py, builder.py, fts.py,
                                 query.py, context.py, chunker.py, permanent.py,
                                 events.py, refresh.py, runtime_health.py, _columns.py
```

## Key Decisions

### D1: Delete local embedding mode entirely

**Decision:** Remove ChromaDB for local embedding calculation (sentence-transformers, `BAAI/bge-small-en-v1.5` model, `_get_st()`, `get_embedding_model()`, `_download_model_via_mirror()`). Keep ChromaDB **only as a vector store** — embeddings are generated exclusively via API.

**Rationale:**
- ChromaDB as a vector store is fine (~30MB)
- sentence-transformers is the problem (~500MB + torch)
- Users who want local embedding can point to a local OpenAI-compatible endpoint (e.g., llamafile, Ollama, vLLM)
- `openai` + `chromadb` are the only remaining deps

### D2: ChromaDB stays as vector store

**Decision:** Retain ChromaDB `PersistentClient` + `get_collection()` for on-disk vector storage. Only the embedding *source* changes from local model to API.

**Impact:** `_get_chroma()` is kept (moved to `_chroma.py`). `_get_st()`, `get_embedding_model()`, `_download_model_via_mirror()` are deleted.

### D3: Snapshot files stay at their current schema

**Decision:** `write_memory_runtime()`, `write_vector_runtime()`, `write_runtime_health()` keep their exact signatures. `state_snapshot.py` is not modified. This guarantees zero plugin breakage.

**Impact:** The old plan's "unified runtime-state.json" is removed. The 3 legacy files continue to be written from exactly the same call sites.

### D4: Deprecated shims for backward compatibility

**Decision:** `memory/vector_db.py` and `worker/vector_db.py` become forwarding shims that emit `DeprecationWarning` and delegate to `embedding/`. This ensures:
- Existing test imports still work
- Third-party scripts still work
- Gradual migration path

**Impact:** 4 test files continue to work without import changes on the test side (shim handles it). However, to clean up tech debt, tests should be migrated directly to `embedding/`.

### D5: `chunker.py` stays in `memory/`, imported directly

**Decision:** `chunk_fulltext` remains in `memory/chunker.py`. Consumers that currently import it through `memory/vector_db.py` (like `worker/asset_index.py:456`) must switch to importing directly from `memory/chunker.py`.

### D6: Plugin files unchanged

**Decision:** Zero changes to `plugin/main.js`, `plugin/styles.css`, `plugin/manifest.json`.

## Complete Consumer Map

All 11 places that import from the files being deprecated:

### Importing FROM `memory/vector_db` (5 files):

| # | File | Line | Importing | Action |
|---|------|------|-----------|--------|
| 1 | `commands/embed.py` | 11-19 | `delete_paper_vectors, embed_paper, get_collection, get_embed_status, get_vector_db_path, mark_vector_build_state, read_vector_build_state` | Change to `embedding` |
| 2 | `commands/retrieve.py` | 10 | `retrieve_chunks` | Change to `embedding` |
| 3 | `worker/asset_index.py` | 454 | `_read_plugin_settings, chunk_fulltext, embed_paper, get_vector_db_path` | Change: `_read_plugin_settings` → `embedding._config`, `chunk_fulltext` → `memory.chunker` |
| 4 | `memory/runtime_health.py` | 121 | `get_vector_db_path, read_vector_build_state` | Change to `embedding` |
| 5 | `worker/vector_db.py` | 59 | `get_vector_db_path` | (shim → `embedding` via shim) |

### Importing FROM `worker/vector_db` (2 files):

| # | File | Line | Importing | Action |
|---|------|------|-----------|--------|
| 6 | `commands/embed.py` | 21 | `_preflight_check` | Change to `embedding.preflight` |
| 7 | `commands/retrieve.py` | 20 | `get_embed_status` | Change to `embedding` |

### Importing FROM `memory/state_snapshot` (4 files — UNCHANGED):

| # | File | Line | Importing | Action |
|---|------|------|-----------|--------|
| 8 | `commands/embed.py` | 10 | `write_vector_runtime` | UNCHANGED |
| 9 | `commands/memory.py` | 66 | `write_memory_runtime` | UNCHANGED |
| 10 | `commands/runtime_health.py` | 9 | `write_runtime_health` | UNCHANGED |
| 11 | `worker/status.py` | 26 | `write_memory_runtime` | UNCHANGED |

### Test files (4 files):

| # | File | Line | Importing | Action |
|---|------|------|-----------|--------|
| 12 | `tests/unit/memory/test_vector_db.py` | 3 | `memory.vector_db` | Change to `embedding` OR keep (shim works) |
| 13 | `tests/unit/commands/test_embed.py` | 7 | `memory.vector_db` | Change to `embedding` OR keep (shim works) |
| 14 | `tests/unit/commands/test_retrieve.py` | 14 | patches `worker.vector_db.get_embed_status` | Change patch target to `embedding.status` |
| 15 | `tests/unit/worker/test_vector_db.py` | 6 | `worker.vector_db` | Change to `embedding` OR keep (shim works) |

### Cross-reference: what `_vec_auto_embed_if_new` in asset_index.py needs

Current code:
```python
from paperforge.memory.vector_db import (
    _read_plugin_settings,
    chunk_fulltext,
    embed_paper,
    get_vector_db_path,
)
```

After refactoring:
```python
from paperforge.embedding._config import _read_plugin_settings
from paperforge.embedding import embed_paper, get_vector_db_path
from paperforge.memory.chunker import chunk_fulltext
```

## Dependency Changes

| Dependency | Before | After | Reason |
|---|---|---|---|
| `chromadb` | Required for local + API store | Required for API store only | Still needed as vector store |
| `sentence-transformers` | Required for local mode | **REMOVED** | Replaced by API |
| `openai` | Required for API mode | Required (only mode) | Sole embedding source |
| `torch` (transitive) | Required via ST | **REMOVED** | Freedom from PyTorch |
| `transformers` (transitive) | Required via ST | **REMOVED** | Freedom from HF ecosystem |

`pyproject.toml` extras:
- `[vector]` extra: remove `sentence-transformers`, keep `chromadb` + `openai`
- New package weight: `chromadb` (~30MB) + `openai` (~200KB) = ~30MB (was ~2GB)

## Snapshot Schema (unchanged)

### `memory-runtime-state.json`
```json
{"schema_version": 1, "paper_count_db": 650, "fresh": true, ...}
```
Still written by `state_snapshot.py:write_memory_runtime()`.

### `vector-runtime-state.json`
```json
{"schema_version": 1, "enabled": true, "mode": "api", "chunk_count": 1200, ...}
```
Still written by `state_snapshot.py:write_vector_runtime()`.

### `runtime-health.json`
```json
{"summary": {"status": "ok"}, "layers": {...}, "capabilities": {...}}
```
Still written by `state_snapshot.py:write_runtime_health()`.

## Out of Scope

- FastAPI / HTTP server
- Plugin source restructuring (main.js stays as-is)
- Unified runtime state
- Performance optimization of FTS
