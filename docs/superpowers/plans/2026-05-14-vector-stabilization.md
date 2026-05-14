# Vector DB Flow Stabilization Plan

> **For agentic workers:** Use subagent-driven-development to implement.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the user flow "install → enable vector DB → embed build → retrieve" stable — no missing deps, no silent failures, no misleading UI.

**Architecture:** Plugin settings drive the feature toggle; CLI preflight checks all deps before build; retrieve refuses to query empty index.

**Tech Stack:** esbuild (plugin), chromadb, sentence-transformers, openai, Python CLI

---

## Task 1: Remove ghost Setting code from main.js

**Files:**
- Modify: `paperforge/plugin/main.js:200-215`

**Goal:** Delete the misplaced `new Setting(containerEl)` block that sits inside `runSubprocess`. All vector settings already exist correctly in `_renderFeaturesTab`.

- [ ] **Step 1: Delete lines 200-215**

Remove the extra `});` and the two `new Setting(containerEl).setName('API Model')` blocks that are at lines 200-215.

The code to remove:
```javascript
                });
            new Setting(containerEl)
                .setName('API Model')
                .setDesc('Which OpenAI-compatible embedding model to use.')
            new Setting(containerEl)
                .setName('API Model')
                .setDesc('Embedding model name (e.g., text-embedding-3-small, qwen-3-embedding)')
                .addText(text => {
                    text.setPlaceholder('text-embedding-3-small')
                        .setValue(this.plugin.settings.vector_db_api_model || 'text-embedding-3-small')
                        .onChange(value => {
                            this.plugin.settings.vector_db_api_model = value;
                            this.plugin.saveSettings();
                        });
                });
        }
```

- [ ] **Step 2: Verify syntax**

Run: `node --check paperforge/plugin/main.js`
Expected: PASS (exit code 0)

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/main.js
git commit -m "fix: remove ghost vector API Model setting from runSubprocess scope"
```

---

## Task 2: Add vector optional dependencies to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Goal:** Users can `pip install paperforge[vector]` to get chromadb + embeddings deps.

- [ ] **Step 1: Add vector extra**

In `pyproject.toml`, under `[project]` (or at end of file), add:

```toml
[project.optional-dependencies]
vector = [
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "openai>=1.0.0",
]
```

- [ ] **Step 2: Add install hint to plugin setup page**

In `main.js` `_renderSetupTab()`, after dependency check output, add a notice:

```javascript
// In the deps status display section, add:
const vectorHint = containerEl.createEl('p', {
    cls: 'paperforge-settings-desc',
    text: 'Vector Database requires additional dependencies. '
        + 'Run: pip install "paperforge[vector]"'
});
```

- [ ] **Step 3: Verify**

Run: `python -c "import chromadb; import sentence_transformers; import openai; print('vector deps OK')"` 
(Only needed if deps are already installed — otherwise verify pyproject.toml syntax)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml paperforge/plugin/main.js
git commit -m "feat: add vector optional deps and install hint in plugin UI"
```

---

## Task 3: Add preflight to embed build

**Files:**
- Modify: `paperforge/worker/vector_db.py` (add `_preflight_check()`)
- Modify: `paperforge/commands/embed.py` (call preflight before build)

**Goal:** Before building embeddings, check all prerequisites and give clear error messages.

- [ ] **Step 1: Add _preflight_check() to vector_db.py**

```python
def _preflight_check(vault: Path, settings: dict) -> dict:
    """Check all prerequisites for embed build.
    
    Returns {"ok": True} or {"ok": False, "error": "...", "fix": "..."}
    """
    # 1. Check vector_db feature toggle
    if not settings.get("features", {}).get("vector_db", False):
        return {
            "ok": False,
            "error": "Vector DB is not enabled",
            "fix": "Enable 'Vector Database' in PaperForge plugin settings (Features tab).",
        }
    
    # 2. Check chromadb import
    try:
        import chromadb
    except ImportError:
        return {
            "ok": False,
            "error": "chromadb is not installed",
            "fix": 'Run: pip install "paperforge[vector]"',
        }
    
    # 3. Check mode-specific deps
    mode = settings.get("vector_db_mode", "local")
    if mode == "local":
        try:
            import sentence_transformers
        except ImportError:
            return {
                "ok": False,
                "error": "sentence-transformers is not installed (required for local mode)",
                "fix": 'Run: pip install "paperforge[vector]" or switch to API mode in plugin settings.',
            }
    elif mode == "api":
        try:
            import openai
        except ImportError:
            return {
                "ok": False,
                "error": "openai is not installed (required for API mode)",
                "fix": 'Run: pip install "paperforge[vector]" or switch to local mode in plugin settings.',
            }
        api_key = (
            settings.get("vector_db_api_key")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("VECTOR_DB_API_KEY")
        )
        if not api_key:
            return {
                "ok": False,
                "error": "API key not configured for API mode",
                "fix": "Set API Key in PaperForge plugin settings (Features tab) or OPENAI_API_KEY in .env.",
            }
    
    # 4. Check OCR done papers
    from paperforge.worker._utils import pipeline_paths, read_json
    paths = pipeline_paths(vault)
    index_path = paths.get("indexes", Path()) / "formal-library.json"
    if not index_path.exists():
        return {
            "ok": False,
            "error": "Index not found",
            "fix": "Run paperforge memory build first.",
        }
    
    index_data = read_json(index_path)
    items = index_data.get("items", []) if isinstance(index_data, dict) else index_data
    papers_with_ocr = [item for item in (items or []) if item.get("ocr_status") == "done"]
    
    if not papers_with_ocr:
        return {
            "ok": False,
            "error": "No papers with OCR completed",
            "fix": "Run paperforge ocr first, or set do_ocr: true on papers with PDFs.",
        }
    
    # 5. Check fulltext files exist
    unreadable = 0
    for item in papers_with_ocr[:5]:  # sample check
        fulltext = item.get("fulltext_path", "")
        if fulltext and not Path(fulltext).exists():
            unreadable += 1
    
    return {
        "ok": True,
        "ocr_done_count": len(papers_with_ocr),
        "fulltext_unreachable_sample": unreadable,
    }
```

- [ ] **Step 2: Call preflight in embed build**

In `embed.py` (or wherever `embed_build` is called), before the main loop:

```python
settings = read_plugin_settings(vault)  # read from data.json
preflight = _preflight_check(vault, settings)
if not preflight["ok"]:
    return PFResult(
        ok=False,
        command="embed-build",
        version=PF_VERSION,
        error=PFError(code=ErrorCode.VALIDATION_ERROR, message=preflight["error"]),
        data={"fix": preflight.get("fix", "")},
    )
```

- [ ] **Step 3: Verify**

Test manually: `python -m paperforge embed build` without vector deps → should get clear error.

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/vector_db.py paperforge/commands/embed.py
git commit -m "feat: add preflight checks before embed build"
```

---

## Task 4: Gating — respect feature toggle in CLI

**Files:**
- Modify: `paperforge/worker/vector_db.py` (preflight already checks this)
- Modify: `paperforge/skills/paperforge/scripts/pf_bootstrap.py` (fix vector_search reading)

**Goal:** If user hasn't enabled vector_db in settings, CLI should refuse to build, and bootstrap should report accurately.

- [ ] **Step 1: Verify preflight checks vector_db toggle**

(Already done in Task 3 step 1 — the `_preflight_check` checks `features.vector_db`)

- [ ] **Step 2: Fix bootstrap vector_search field**

In `pf_bootstrap.py`, change the memory_layer check to:

```python
# Read plugin data.json for real settings
dc_json = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
vector_enabled = False
if dc_json.exists():
    try:
        with open(dc_json, encoding="utf-8") as f:
            plugin_data = json.load(f)
        vector_enabled = plugin_data.get("features", {}).get("vector_db", False)
    except:
        pass
memory_layer["vector_search"] = vector_enabled
```

(Current code already does this — verify it reads from the right path.)

- [ ] **Step 3: Commit**

```bash
git add paperforge/skills/paperforge/scripts/pf_bootstrap.py
git commit -m "fix: ensure bootstrap reads vector_db toggle from plugin settings"
```

---

## Task 5: Retrieve guard — refuse empty index

**Files:**
- Modify: `paperforge/commands/retrieve.py`
- Modify: `paperforge/worker/vector_db.py` (add get_embed_status)

**Goal:** `paperforge retrieve` checks if index has chunks before loading models.

- [ ] **Step 1: Add get_embed_status() to vector_db.py**

```python
def get_embed_status(vault: Path) -> dict:
    """Check if vector index exists and has content."""
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    vectors_dir = paths.get("vectors", paths["paperforge"] / "vectors")
    
    status = {
        "exists": False,
        "chunk_count": 0,
        "collection_name": "",
        "embedding_model": "",
    }
    
    if not vectors_dir.exists():
        return status
    
    # Try to read Chroma collection metadata
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(vectors_dir))
        collections = client.list_collections()
        if collections:
            col = collections[0]
            status["exists"] = True
            status["collection_name"] = col.name
            status["chunk_count"] = col.count()
            status["embedding_model"] = col.metadata.get("embedding_model", "") if col.metadata else ""
    except Exception:
        pass
    
    return status
```

- [ ] **Step 2: Guard retrieve command**

In `retrieve.py`, before calling `retrieve_chunks()`:

```python
status = get_embed_status(vault)
if status["chunk_count"] == 0:
    result = PFResult(
        ok=False,
        command="retrieve",
        version=PF_VERSION,
        error=PFError(
            code=ErrorCode.PATH_NOT_FOUND,
            message="Vector index is empty. Run paperforge embed build first.",
        ),
        data={"next_action": "paperforge embed build"},
    )
    if args.json:
        print(result.to_json())
    else:
        print(f"Error: {result.error.message}", file=sys.stderr)
    return 1
```

- [ ] **Step 3: Commit**

```bash
git add paperforge/commands/retrieve.py paperforge/worker/vector_db.py
git commit -m "feat: guard retrieve against empty index, add embed status check"
```

---

## Task 6: Local mode HF download hint

**Files:**
- Modify: `paperforge/plugin/main.js` (_renderFeaturesTab)

**Goal:** Users on local mode know they need HF access and can set a mirror.

- [ ] **Step 1: Add HF download hint**

In `_renderFeaturesTab`, after the local model selector, add:

```javascript
new Setting(containerEl)
    .setName('HF Download Notice')
    .setDesc(
        'Local mode downloads models from Hugging Face on first use. '
        + 'If inaccessible, set HF Endpoint below (e.g. https://hf-mirror.com) '
        + 'or switch to API mode.'
    )
    .setDisabled(true);
```

(Use Obsidian Setting's `setDisabled` to make it a read-only notice, or just use an `info` div.)

- [ ] **Step 2: Commit**

```bash
git add paperforge/plugin/main.js
git commit -m "feat: add HF download notice for local mode in plugin settings"
```

---

## Summary

| Task | Priority | Files | Risk |
|------|----------|-------|------|
| 1 — Remove ghost code | P0 | main.js | None — deletes orphan code |
| 2 — Vector deps | P0 | pyproject.toml, main.js | Low — additive |
| 3 — Preflight | P0 | vector_db.py, embed.py | Low — additive guard |
| 4 — Feature gating | P1 | vector_db.py, pf_bootstrap.py | Low — already mostly done |
| 5 — Retrieve guard | P1 | retrieve.py, vector_db.py | Low — additive guard |
| 6 — HF hint | P2 | main.js | None — UI text only |
