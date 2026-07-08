# Memory Layer Simplification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract vector logic into a new `embedding/` package, delete local embedding model support (sentence-transformers), keep only API embedding, ensure zero breakage across all 11 Python consumers and 4 test files.

**Architecture:** New `paperforge/embedding/` package holds all API-only vector code. `memory/vector_db.py` and `worker/vector_db.py` become deprecated forwarding shims. Plugin snapshot files remain at their exact current paths. The `memory/state_snapshot.py` writer stays unchanged.

**Spec:** `docs/superpowers/specs/2026-05-18-memory-layer-simplify-design.md`

**Constraint — Plugin is immutable:** `plugin/main.js`, `plugin/styles.css`, `plugin/manifest.json` must not change. The plugin reads 4 JSON snapshot files from their current paths — these files must keep their exact schema.

---

## File Structure Map

```
Create (11 files):
  paperforge/embedding/
    __init__.py                           — package init, re-export all public APIs
    _config.py                            — _read_plugin_settings(), env var resolution
    _chroma.py                            — ChromaDB collection management (store only)
    providers/
      __init__.py                          — sub-package marker
      base.py                             — EmbeddingProvider ABC
      openai_compatible.py                — OpenAI-compatible API embedding client
    builder.py                            — embed_paper() API-only builder
    search.py                             — retrieve_chunks() API-only semantic search
    build_state.py                        — build state persistence (read/write/mark/get_path)
    status.py                             — get_embed_status()
    preflight.py                          — _preflight_check() (migrated from worker/)

Modify (11 files):
  paperforge/memory/vector_db.py           → deprecated forwarding shim
  paperforge/worker/vector_db.py           → deprecated forwarding shim
  paperforge/worker/asset_index.py:454     → update import paths
  paperforge/memory/runtime_health.py:121  → update import paths
  paperforge/commands/embed.py:11-19,21    → update import paths + simplify deps check
  paperforge/commands/retrieve.py:10,20    → update import paths
  tests/unit/memory/test_vector_db.py:3    → update import paths
  tests/unit/commands/test_embed.py:7      → update import paths
  tests/unit/commands/test_retrieve.py:14  → update patch target
  tests/unit/worker/test_vector_db.py:6    → update import paths
  pyproject.toml                           → remove sentence-transformers from [vector] extra

UNCHANGED (must verify they still work):
  paperforge/memory/state_snapshot.py       — writes memory-runtime-state.json, vector-runtime-state.json, runtime-health.json
  paperforge/commands/memory.py             — calls write_memory_runtime()
  paperforge/commands/runtime_health.py     — calls write_runtime_health()
  paperforge/worker/status.py               — calls write_memory_runtime()
  paperforge/memory/chunker.py              — chunk_fulltext stays here, consumers import directly
```

---

## Complete Dependency Map (must verify after each task)

```
memory/vector_db.py (deprecated shim)
  └─ embedding/__init__.py ──┬─ _config.py         (no deps)
                              ├─ _chroma.py          → chromadb (PyPI)
                              ├─ providers/ ─┬─ base.py (ABC, no deps)
                              │              └─ openai_compatible.py → openai (PyPI), _config.py
                              ├─ builder.py          → _chroma.py, providers/
                              ├─ search.py           → _chroma.py, providers/
                              ├─ build_state.py      → stdlib json
                              ├─ status.py           → _chroma.py, _config.py
                              └─ preflight.py        → openai, chromadb, worker._utils

worker/vector_db.py (deprecated shim)
  └─ embedding/{preflight.py, status.py}

consumer → old import → shim forwards → embedding/ package
   commands/embed.py ─────────────────→ embedding/{builder,_chroma,build_state,status,preflight}
   commands/retrieve.py ──────────────→ embedding/{search,status}
   worker/asset_index.py ─────────────→ embedding/{_config,builder,_chroma} + memory/chunker
   memory/runtime_health.py ─────────→ embedding/{_chroma,build_state}
   4 test files ──────────────────────→ embedding/{status,build_state}
   
Snapshot writers ── unchanged ──→ memory/state_snapshot.py (writes 3 legacy files)
```

---

### Task 1: Create `embedding/` directory and `__init__.py`

**Files:**
- Create: `paperforge/embedding/__init__.py`
- Create: `paperforge/embedding/providers/__init__.py`

- [ ] **Step 1: Create directories**

```bash
New-Item -ItemType Directory -Path "paperforge\embedding\providers" -Force
```

- [ ] **Step 2: Write `paperforge/embedding/providers/__init__.py`**

Empty file (marks package).

- [ ] **Step 3: Write `paperforge/embedding/__init__.py`**

```python
from __future__ import annotations

from paperforge.embedding._chroma import (
    delete_paper_vectors,
    get_collection,
    get_vector_db_path,
)
from paperforge.embedding.build_state import (
    get_vector_build_state_path,
    mark_vector_build_state,
    read_vector_build_state,
    write_vector_build_state,
)
from paperforge.embedding.builder import embed_paper
from paperforge.embedding.preflight import _preflight_check
from paperforge.embedding.search import retrieve_chunks
from paperforge.embedding.status import get_embed_status

__all__ = [
    "delete_paper_vectors",
    "embed_paper",
    "get_collection",
    "get_embed_status",
    "get_vector_build_state_path",
    "get_vector_db_path",
    "mark_vector_build_state",
    "read_vector_build_state",
    "retrieve_chunks",
    "write_vector_build_state",
    "_preflight_check",
]
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/embedding/__init__.py paperforge/embedding/providers/__init__.py
git commit -m "feat(embedding): create embedding package skeleton"
```

---

### Task 2: Write `paperforge/embedding/_config.py`

**Files:**
- Create: `paperforge/embedding/_config.py`

- [ ] **Step 1: Write `_config.py`**

```python
from __future__ import annotations

import json
import os
from pathlib import Path


def _read_plugin_settings(vault: Path) -> dict:
    data_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if data_path.exists():
        return json.loads(data_path.read_text(encoding="utf-8"))
    return {}


def get_api_key(vault: Path) -> str:
    settings = _read_plugin_settings(vault)
    api_key = os.environ.get("VECTOR_DB_API_KEY", "")
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        api_key = settings.get("vector_db_api_key", "")
    if not api_key:
        env_file = vault / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("VECTOR_DB_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
                elif line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return api_key


def get_api_base_url(vault: Path) -> str:
    settings = _read_plugin_settings(vault)
    return os.environ.get("VECTOR_DB_API_BASE", "") or settings.get("vector_db_api_base", "") or ""


def get_api_model(vault: Path) -> str:
    settings = _read_plugin_settings(vault)
    return os.environ.get("VECTOR_DB_API_MODEL", "") or settings.get("vector_db_api_model", "text-embedding-3-small")
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/_config.py
git commit -m "feat(embedding): add config reader for API settings"
```

---

### Task 3: Write `paperforge/embedding/providers/base.py`

**Files:**
- Create: `paperforge/embedding/providers/base.py`

- [ ] **Step 1: Write base provider**

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def encode_single(self, text: str) -> list[float]:
        ...
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/providers/base.py
git commit -m "feat(embedding): add EmbeddingProvider ABC"
```

---

### Task 4: Write `paperforge/embedding/providers/openai_compatible.py`

**Files:**
- Create: `paperforge/embedding/providers/openai_compatible.py`

- [ ] **Step 1: Write OpenAI-compatible provider**

```python
from __future__ import annotations

import logging
from pathlib import Path

from openai import OpenAI

from paperforge.embedding._config import get_api_base_url, get_api_key, get_api_model
from paperforge.embedding.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(EmbeddingProvider):
    def __init__(self, vault: Path):
        api_key = get_api_key(vault)
        if not api_key:
            raise ValueError(
                "No API key configured for embedding. "
                "Set VECTOR_DB_API_KEY or OPENAI_API_KEY in .env or plugin settings."
            )
        self._model = get_api_model(vault)
        base_url = get_api_base_url(vault)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        logger.info("Embedding provider: model=%s, base_url=%s", self._model, base_url or "(default OpenAI)")
        self._client = OpenAI(**kwargs)

    def encode(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [e.embedding for e in resp.data]

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/providers/openai_compatible.py
git commit -m "feat(embedding): add OpenAI-compatible embedding provider"
```

---

### Task 5: Write `paperforge/embedding/_chroma.py`

**Files:**
- Create: `paperforge/embedding/_chroma.py`

Extracts `get_vector_db_path()`, `get_collection()`, `delete_paper_vectors()` from `memory/vector_db.py`. **Removes** `_get_st()`, `get_embedding_model()`, `_download_model_via_mirror()` entirely.

```python
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_vector_db_path(vault: Path) -> Path:
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    return (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent / "vectors"


def _get_chroma():
    import chromadb
    return chromadb


def get_collection(vault: Path):
    chroma = _get_chroma()
    db_path = get_vector_db_path(vault)
    db_path.mkdir(parents=True, exist_ok=True)
    client = chroma.PersistentClient(path=str(db_path))
    try:
        return client.get_or_create_collection(
            name="paperforge_fulltext",
            metadata={"hnsw:space": "cosine"},
        )
    except Exception:
        client.delete_collection("paperforge_fulltext")
        return client.create_collection(
            name="paperforge_fulltext",
            metadata={"hnsw:space": "cosine"},
        )


def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
    collection = get_collection(vault)
    try:
        results = collection.get(where={"paper_id": zotero_key})
        ids = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/_chroma.py
git commit -m "feat(embedding): add ChromaDB collection manager (store only)"
```

---

### Task 6: Write `paperforge/embedding/build_state.py`

**Files:**
- Create: `paperforge/embedding/build_state.py`

- [ ] **Step 1: Write build state persistence**

```python
from __future__ import annotations

import json
from pathlib import Path


def get_vector_build_state_path(vault: Path) -> Path:
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    index_dir = (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent
    return index_dir / "vector-build-state.json"


def read_vector_build_state(vault: Path) -> dict:
    path = get_vector_build_state_path(vault)
    if not path.exists():
        return {
            "status": "idle",
            "current": 0,
            "total": 0,
            "paper_id": "",
            "last_update": "",
            "started_at": "",
            "finished_at": "",
            "resume_supported": True,
            "mode": "api",
            "model": "text-embedding-3-small",
            "message": "",
            "pid": 0,
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "idle", "current": 0, "total": 0, "paper_id": ""}


def write_vector_build_state(vault: Path, state: dict) -> None:
    path = get_vector_build_state_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def mark_vector_build_state(vault: Path, **fields) -> dict:
    state = read_vector_build_state(vault)
    state.update(fields)
    write_vector_build_state(vault, state)
    return state
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/build_state.py
git commit -m "feat(embedding): add build state persistence"
```

---

### Task 7: Write `paperforge/embedding/builder.py`

**Files:**
- Create: `paperforge/embedding/builder.py`

- [ ] **Step 1: Write embed_paper() — API only, no local branch**

```python
from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def embed_paper(vault: Path, zotero_key: str, chunks: list[dict]) -> int:
    """Embed chunks for one paper using API and insert into ChromaDB. Returns count."""
    collection = get_collection(vault)
    provider = OpenAICompatibleProvider(vault)

    texts = [c["text"] for c in chunks]
    ids = [f"{zotero_key}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section": c["section"],
            "page_number": c["page_number"],
            "chunk_index": c["chunk_index"],
            "token_estimate": c["token_estimate"],
        }
        for c in chunks
    ]

    embeddings = provider.encode(texts)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return len(chunks)
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/builder.py
git commit -m "feat(embedding): add API-only embed_paper() builder"
```

---

### Task 8: Write `paperforge/embedding/search.py`

**Files:**
- Create: `paperforge/embedding/search.py`

- [ ] **Step 1: Write retrieve_chunks() — API only**

```python
from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def retrieve_chunks(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Search chunks via API embedding. Returns list with metadata and similarity scores."""
    collection = get_collection(vault)
    provider = OpenAICompatibleProvider(vault)
    query_embedding = provider.encode_single(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit * 3 if expand else limit,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        chunks.append({
            "paper_id": meta["paper_id"],
            "section": meta.get("section", "Text"),
            "page_number": meta.get("page_number", 1),
            "chunk_index": meta.get("chunk_index", 0),
            "chunk_text": doc,
            "score": round(1.0 - dist, 4),
        })

    return chunks
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/search.py
git commit -m "feat(embedding): add API-only retrieve_chunks() semantic search"
```

---

### Task 9: Write `paperforge/embedding/status.py`

**Files:**
- Create: `paperforge/embedding/status.py`

- [ ] **Step 1: Write get_embed_status() — API mode always**

```python
from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection, get_vector_db_path
from paperforge.embedding._config import get_api_model

logger = logging.getLogger(__name__)


def get_embed_status(vault: Path) -> dict:
    """Get vector DB status. API-only mode.

    Returns dict with keys: db_exists, chunk_count, model, mode, healthy, error.
    """
    db_path = get_vector_db_path(vault)
    exists = db_path.exists()
    chunk_count = 0
    healthy = True
    error = ""
    if exists:
        try:
            collection = get_collection(vault)
            chunk_count = collection.count()
        except Exception as exc:
            healthy = False
            error = str(exc)

    model = get_api_model(vault)

    return {
        "db_exists": exists,
        "chunk_count": chunk_count,
        "model": model,
        "mode": "api",
        "healthy": healthy,
        "error": error,
    }
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/status.py
git commit -m "feat(embedding): add get_embed_status() for API-only mode"
```

---

### Task 10: Write `paperforge/embedding/preflight.py`

**Files:**
- Create: `paperforge/embedding/preflight.py`

- [ ] **Step 1: Write _preflight_check() — API mode only**

```python
from __future__ import annotations

import os
from pathlib import Path


def _preflight_check(vault: Path, settings: dict | None = None) -> dict:
    """Check prerequisites for embed build. Returns {ok: bool, error: str, fix: str}."""

    # 1. openai package
    try:
        import openai  # noqa: F401
    except ImportError:
        return {
            "ok": False,
            "error": "openai is not installed",
            "fix": 'Run: pip install "paperforge[vector]"',
        }

    # 2. chromadb package
    try:
        import chromadb  # noqa: F401
    except ImportError:
        return {
            "ok": False,
            "error": "chromadb is not installed",
            "fix": 'Run: pip install "paperforge[vector]"',
        }

    # 3. API key
    api_key = None
    if settings:
        api_key = settings.get("vector_db_api_key")
    if not api_key:
        api_key = os.environ.get("VECTOR_DB_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        env_path = vault / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("VECTOR_DB_API_KEY=") or line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        return {
            "ok": False,
            "error": "API key not configured",
            "fix": "Set VECTOR_DB_API_KEY or OPENAI_API_KEY in .env or plugin settings",
        }

    # 4. OCR done papers
    from paperforge.worker._utils import pipeline_paths
    paths = pipeline_paths(vault)
    idx_path = paths.get("indexes", Path("")) / "formal-library.json" if paths.get("indexes") else None
    if idx_path and idx_path.exists():
        import json
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        items = data.get("items", []) if isinstance(data, dict) else data
        done = sum(1 for i in (items or []) if i.get("ocr_status") == "done")
        if done == 0:
            return {
                "ok": False,
                "error": "No papers with OCR completed",
                "fix": "Run paperforge ocr first",
            }

    return {"ok": True}
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/embedding/preflight.py
git commit -m "feat(embedding): add API-only preflight check"
```

---

### Task 11: Convert `memory/vector_db.py` to deprecated shim

**Files:**
- Modify: `paperforge/memory/vector_db.py`

- [ ] **Step 1: Replace entire content with forwarding shim**

```python
"""Deprecated. Import from paperforge.embedding instead."""
from __future__ import annotations

import warnings

from paperforge.embedding import (
    delete_paper_vectors,        # noqa: F401
    embed_paper,                 # noqa: F401
    get_collection,              # noqa: F401
    get_embed_status,            # noqa: F401
    get_vector_build_state_path, # noqa: F401
    get_vector_db_path,          # noqa: F401
    mark_vector_build_state,     # noqa: F401
    read_vector_build_state,     # noqa: F401
    retrieve_chunks,             # noqa: F401
    write_vector_build_state,    # noqa: F401
)

warnings.warn(
    "paperforge.memory.vector_db is deprecated, use paperforge.embedding instead",
    DeprecationWarning,
    stacklevel=2,
)
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/memory/vector_db.py
git commit -m "refactor(memory): convert vector_db.py to deprecated forwarding shim"
```

---

### Task 12: Convert `worker/vector_db.py` to deprecated shim

**Files:**
- Modify: `paperforge/worker/vector_db.py`

- [ ] **Step 1: Replace entire content with forwarding shim**

```python
"""Deprecated. Import from paperforge.embedding instead."""
from __future__ import annotations

import warnings

from paperforge.embedding.preflight import _preflight_check  # noqa: F401
from paperforge.embedding.status import get_embed_status       # noqa: F401

warnings.warn(
    "paperforge.worker.vector_db is deprecated, use paperforge.embedding instead",
    DeprecationWarning,
    stacklevel=2,
)
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/worker/vector_db.py
git commit -m "refactor(worker): convert vector_db.py to deprecated forwarding shim"
```

---

### Task 13: Update `commands/embed.py` imports

**Constraint check:** This file also calls `write_vector_runtime()` from `state_snapshot.py` — that import stays unchanged.

**Files:**
- Modify: `paperforge/commands/embed.py:9-49`

- [ ] **Step 1: Replace import block (lines 9-21)**

Old:
```python
from paperforge.memory.vector_db import (
    delete_paper_vectors,
    embed_paper,
    get_collection,
    get_embed_status,
    get_vector_db_path,
    mark_vector_build_state,
    read_vector_build_state,
)
from paperforge.worker.vector_db import _preflight_check
```

New:
```python
from paperforge.embedding import (
    delete_paper_vectors,
    embed_paper,
    get_collection,
    get_embed_status,
    get_vector_db_path,
    mark_vector_build_state,
    read_vector_build_state,
)
from paperforge.embedding.preflight import _preflight_check
```

- [ ] **Step 2: Simplify dependency-check block (lines 33-49)**

Current code has a `mode` check that handles both "local" and "api" modes. Since only API mode exists now:

Replace:
```python
    _dep_missing = []
    _current_mode = status.get("mode", "local") or "local"
    if _current_mode == "api":
        try:
            import openai  # noqa: F401
        except ImportError:
            _dep_missing.append("openai")
    else:
        try:
            import chromadb  # noqa: F401
        except ImportError:
            _dep_missing.append("chromadb")
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            _dep_missing.append("sentence_transformers")
```

With:
```python
    _dep_missing = []
    try:
        import openai  # noqa: F401
    except ImportError:
        _dep_missing.append("openai")
    try:
        import chromadb  # noqa: F401
    except ImportError:
        _dep_missing.append("chromadb")
```

- [ ] **Step 3: Verify `write_vector_runtime` calls still work**

The `write_vector_runtime()` calls in `embed.py:50-63,193-206,218-231` use `status.get("mode", "")` for the `mode` field. Since `get_embed_status()` now always returns `"api"`, this will correctly pass `mode="api"` to the snapshot. No change needed.

- [ ] **Step 4: Commit**

```bash
git add paperforge/commands/embed.py
git commit -m "refactor(commands): update embed.py imports to embedding package"
```

---

### Task 14: Update `commands/retrieve.py` imports

**Files:**
- Modify: `paperforge/commands/retrieve.py:10,20`

- [ ] **Step 1: Replace import at line 10**

Old: `from paperforge.memory.vector_db import retrieve_chunks`
New: `from paperforge.embedding import retrieve_chunks`

- [ ] **Step 2: Replace import at line 20**

Old: `from paperforge.worker.vector_db import get_embed_status`
New: `from paperforge.embedding import get_embed_status`

- [ ] **Step 3: No key mismatch for retrieve.py**

Check confirmed: `retrieve.py` only uses `status.get("healthy", True)`, `status.get("chunk_count", 0)`, `status.get("error", "")` — all three keep the same key in the new `embedding.status.get_embed_status()`. The `"exists"` → `"db_exists"` rename only affects `tests/unit/worker/test_vector_db.py` (handled in Task 17 Step 4).

- [ ] **Step 4: Commit**

```bash
git add paperforge/commands/retrieve.py
git commit -m "refactor(commands): update retrieve.py imports to embedding package"
```

---

### Task 15: Update `worker/asset_index.py:454` imports

**Files:**
- Modify: `paperforge/worker/asset_index.py:454-459`

- [ ] **Step 1: Read the current import block**

```python
from paperforge.memory.vector_db import (
    _read_plugin_settings,
    chunk_fulltext,
    embed_paper,
    get_vector_db_path,
)
```

- [ ] **Step 2: Replace with direct imports**

```python
from paperforge.embedding._config import _read_plugin_settings
from paperforge.embedding import embed_paper, get_vector_db_path
from paperforge.memory.chunker import chunk_fulltext
```

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/asset_index.py
git commit -m "refactor(worker): update asset_index.py vector_db imports to embedding package"
```

---

### Task 16: Update `memory/runtime_health.py:121` import

**Files:**
- Modify: `paperforge/memory/runtime_health.py:121`

- [ ] **Step 1: Replace import**

Old: `from paperforge.memory.vector_db import get_vector_db_path, read_vector_build_state`
New: `from paperforge.embedding import get_vector_db_path, read_vector_build_state`

- [ ] **Step 2: Commit**

```bash
git add paperforge/memory/runtime_health.py
git commit -m "refactor(memory): update runtime_health.py imports to embedding package"
```

---

### Task 17: Update test imports

**Files:**
- Modify: `tests/unit/memory/test_vector_db.py:3`
- Modify: `tests/unit/commands/test_embed.py:7`
- Modify: `tests/unit/commands/test_retrieve.py:14`
- Modify: `tests/unit/worker/test_vector_db.py:6`

- [ ] **Step 1: Update `tests/unit/memory/test_vector_db.py:3`**

Old: `from paperforge.memory.vector_db import (`
New: `from paperforge.embedding.build_state import (`

This test uses: `get_vector_build_state_path, read_vector_build_state, write_vector_build_state, mark_vector_build_state` — all in `embedding.build_state`.

Also update default state check: at line 16, `state["mode"]` will now default to `"api"` instead of `"local"` in the new `read_vector_build_state()`:
```python
assert state["mode"] == "api"  # was "local"
```

Update `test_vector_build_state_defaults_when_missing`:
```python
def test_vector_build_state_defaults_when_missing(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    state = read_vector_build_state(vault)
    assert state["status"] == "idle"
    assert state["current"] == 0
    assert state["mode"] == "api"  # API-only mode now
```

- [ ] **Step 2: Update `tests/unit/commands/test_embed.py:7`**

Old: `from paperforge.memory.vector_db import write_vector_build_state, read_vector_build_state`
New: `from paperforge.embedding import write_vector_build_state, read_vector_build_state`

Also update the mock patch target at line 25:
Old: `with patch("paperforge.commands.embed.get_embed_status") as mock_status:`
New: stays the same (`get_embed_status` is imported in `embed.py` from `paperforge.embedding`; the mock patches the *local reference* in `embed` module, not the original source)

And update the mock return value at line 26:
Old: `mock_status.return_value = {"db_exists": True, "chunk_count": 0, "model": "test", "mode": "local"}`
New: `mock_status.return_value = {"db_exists": True, "chunk_count": 0, "model": "test", "mode": "api"}`

- [ ] **Step 3: Update `tests/unit/commands/test_retrieve.py:14`**

Old: `with patch("paperforge.worker.vector_db.get_embed_status") as mock_status:`
New: `with patch("paperforge.embedding.status.get_embed_status") as mock_status:`

- [ ] **Step 4: Update `tests/unit/worker/test_vector_db.py:6`**

Old: `from paperforge.worker.vector_db import get_embed_status`
New: `from paperforge.embedding.status import get_embed_status`

**Also fix assertions in this file:** the new `get_embed_status()` returns `"db_exists"` instead of old `"exists"`. Update:
- Line 23: `assert status["exists"] is True` → `assert status["db_exists"] is True`
- Line 48: `assert status["exists"] is True` → `assert status["db_exists"] is True`

- [ ] **Step 5: Commit**

```bash
git add tests/unit/memory/test_vector_db.py tests/unit/commands/test_embed.py tests/unit/commands/test_retrieve.py tests/unit/worker/test_vector_db.py
git commit -m "test: update vector_db test imports to embedding package"
```

---

### Task 18: Update `pyproject.toml` to remove sentence-transformers

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Read pyproject.toml to find the [vector] extra**

```bash
grep -n "sentence.transformers\|\[vector\]" pyproject.toml
```

Expected output shows the `[vector]` extra definition.

- [ ] **Step 2: Remove `sentence-transformers` from [vector] extra**

Old: `"vector": ["chromadb", "sentence-transformers", "openai"]`
New: `"vector": ["chromadb", "openai"]`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: remove sentence-transformers from [vector] extra"
```

---

### Task 19: Run full test suite

**Files:**
- Verify: `tests/unit/` (all existing tests)

- [ ] **Step 1: Run all unit tests**

```bash
python -m pytest tests/unit/ -q --tb=short
```

Expected: All tests pass. Any failures indicate import chain breakage.

- [ ] **Step 2: Fix any test failures**

Possible failure modes:
- `test_vector_build_state_defaults_when_missing` — `mode` field now defaults to `"api"`; test may assert `"local"`
- `test_vector_build_state_roundtrip` — test writes `"mode": "local"` which should still work (the field is user-provided)
- Mock patch targets in test_retrieve.py and test_embed.py may need updating if patches target the wrong path

- [ ] **Step 3: Verify import chain end-to-end**

```bash
python -c "
# Test new embedding package exports
from paperforge.embedding import (
    delete_paper_vectors, embed_paper, get_collection,
    get_embed_status, get_vector_db_path,
    mark_vector_build_state, read_vector_build_state,
    write_vector_build_state, retrieve_chunks,
)
print('embedding: all exports OK')

# Test deprecated shim still works
from paperforge.memory.vector_db import retrieve_chunks
print('memory/vector_db shim OK (with DeprecationWarning)')

# Test worker shim still works
from paperforge.worker.vector_db import _preflight_check, get_embed_status
print('worker/vector_db shim OK (with DeprecationWarning)')

# Verify no more 'import' of removed functions
import sys
for mod_name in list(sys.modules.keys()):
    if 'vector_db' in mod_name:
        print(f'  loaded: {mod_name}')

# Test state snapshot imports unchanged
from paperforge.memory.state_snapshot import write_memory_runtime, write_vector_runtime, write_runtime_health
print('state_snapshot: all snapshot writers OK')

# Test chunker is importable directly
from paperforge.memory.chunker import chunk_fulltext
print('memory.chunker: OK')

# Verify config reader works
from paperforge.embedding._config import _read_plugin_settings, get_api_key, get_api_base_url, get_api_model
print('embedding._config: all config readers OK')

print('IMPORT CHAIN: ALL OK')
"
```

Expected: All imports succeed (may show DeprecationWarning for shim paths).

---

### Task 20: Manual smoke tests

- [ ] **Step 1: Verify `embed status` works**

```bash
paperforge embed status --json
```

Expected: Returns JSON with `"mode": "api"` — should work even if no API key configured (status check doesn't call the API, just checks ChromaDB state).

- [ ] **Step 2: Verify `runtime-health` still produces correct snapshot**

```bash
paperforge runtime-health --json
```

Expected: Returns health data. The `vector` layer in `runtime_health.py` reads `get_vector_db_path` and `read_vector_build_state` from the new embedding package — should work identically.

- [ ] **Step 3: Verify `memory-runtime-state.json` still written**

```bash
paperforge memory status --json
Get-Content "System\PaperForge\indexes\memory-runtime-state.json"
```

Expected: memory-runtime-state.json has the same schema as before.

- [ ] **Step 4: Verify `vector-runtime-state.json` still written**

```bash
paperforge embed status --json
Get-Content "System\PaperForge\indexes\vector-runtime-state.json"
```

Expected: vector-runtime-state.json has the same schema as before, with `"mode": "api"`.

---

## Verification Checklist (post-implementation)

After all 20 tasks are done:

```
[ ] 11 new embedding/ files created
[ ] 2 deprecated shim files updated
[ ] 6 consumer file imports updated
[ ] 4 test file imports updated
[ ] pyproject.toml updated
[ ] 0 plugin files changed
[ ] 0 state_snapshot.py changes
[ ] python -m pytest tests/unit/ -q --tb=short  → all pass
[ ] paperforge embed status --json               → {"mode": "api", ...}
[ ] paperforge memory status --json               → normal output
[ ] paperforge runtime-health --json              → normal output
[ ] memory-runtime-state.json exists              → same schema
[ ] vector-runtime-state.json exists              → same schema
[ ] runtime-health.json exists                    → same schema
[ ] vector-build-state.json exists                → same schema
[ ] from paperforge.memory.vector_db import X     → DeprecationWarning
[ ] from paperforge.worker.vector_db import X     → DeprecationWarning
[ ] pip/pip-compile install → no sentence-transformers in deps
```

## Rollback Plan

1. Each task is independently revertible via `git revert <commit>`
2. The shim files (`memory/vector_db.py`, `worker/vector_db.py`) preserve backward compatibility — no consumer breaks as long as shim is correct
3. `state_snapshot.py` is untouched — snapshot files are guaranteed stable
4. If ChromaDB vector store corrupts, old `System/PaperForge/vectors/` directory can be deleted and rebuilt via `paperforge embed build --force`
