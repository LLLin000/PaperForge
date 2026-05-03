# Technology Stack

**Project:** PaperForge v1.6 literature asset foundation
**Researched:** 2026-05-03

## Recommended Stack

This milestone should stay **Python-first for business logic** and **CommonJS Obsidian-shell only for UI**. The plugin should render the canonical index and invoke CLI commands; it should not recompute lifecycle, health, maturity, or AI-context state on the JavaScript side.

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.10+ (existing) | Single owner of config, lifecycle, health, maturity, context-pack generation | Already owns workers/CLI and is the only place that can safely unify business rules without duplicating them in the plugin |
| Pydantic | 2.13.3 | Typed models for `paperforge.json`, canonical asset index, health records, maturity scoring payloads, AI context manifests | Best fit for strict runtime validation plus `model_json_schema()` generation from one source of truth; keeps Python authoritative and produces machine-readable contracts for the plugin/tests |
| Obsidian plugin (`main.js`, CommonJS) | existing thin shell | Dashboard/settings/commands only | Current plugin already shells out to `python -m paperforge status --json`; extend that pattern instead of adding a second domain layer |

### Database
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Filesystem JSON snapshot | UTF-8 JSON, schema-versioned | Canonical derived literature asset index | Local-first, Git/backup friendly, easy for Python to emit and plugin to read, no daemon/service required |
| Optional JSONL append log | UTF-8 JSON Lines | Append-only lifecycle/diagnostic history if needed later | Good long-lived audit primitive without committing to SQLite/event sourcing in v1.6 |

### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| filelock | 3.29.0 | Cross-process locking around index/context-pack writes | Verified cross-platform, and on Windows uses OS-level locking; prevents sync/OCR/plugin-triggered commands from corrupting shared JSON files |
| `tempfile` + `os.replace` | stdlib | Atomic file writes | Windows-safe write pattern for canonical JSON artifacts; avoids partial writes when commands are interrupted |
| `pathlib`, `hashlib`, `json` | stdlib | Path normalization, content fingerprints, serialization | Already aligned with current codebase and enough for local asset indexing |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsonschema | 4.26.0 | Validate emitted JSON artifacts against generated schemas in tests and `doctor`-style diagnostics | Use in Python tests/tooling, not as plugin runtime logic |

## File-Format Standards

### 1. `paperforge.json` stays the human-edited source of truth
- Keep it as the canonical config file.
- Add `schema_version`.
- Validate it in Python with a `PaperForgeConfig` Pydantic model.
- Keep secrets out of it; API keys remain in `.env` / environment.

Recommended structure for new v1.6 fields:

```json
{
  "schema_version": "1",
  "vault_config": { ...existing paths... },
  "index": {
    "output": "<system_dir>/PaperForge/indexes/library-assets.v1.json"
  },
  "health": {
    "enable_maturity_scoring": true
  },
  "context": {
    "output_dir": "<system_dir>/PaperForge/context",
    "default_max_chars": 24000
  }
}
```

### 2. Canonical asset index = one derived snapshot file
Recommended path:

`<system_dir>/PaperForge/indexes/library-assets.v1.json`

Recommended top-level shape:

```json
{
  "schema_version": "1",
  "generated_at": "2026-05-03T12:00:00Z",
  "paperforge_version": "1.6.x",
  "vault": { "...": "..." },
  "summary": { "...": "..." },
  "assets": [
    {
      "zotero_key": "ABCDEFG",
      "intent": { "analyze": true, "do_ocr": true },
      "artifacts": { "pdf": {...}, "ocr": {...}, "formal_note": {...}, "figures": {...} },
      "derived": {
        "lifecycle_state": "fulltext_ready",
        "health": { "library": "healthy", "pdf": "healthy", "ocr": "warning" },
        "maturity": { "level": 3, "score": 0.72, "next_steps": ["run_deep_reading"] },
        "ai_ready": true
      }
    }
  ]
}
```

Rules:
- `library-record` frontmatter remains **user intent**.
- `meta.json`, formal notes, OCR files, figure-map stay **machine artifacts**.
- `library-assets.v1.json` is **derived state only**.
- Plugin reads this file; it does not infer the state itself.

### 3. Generated schema file
Recommended path:

`<system_dir>/PaperForge/indexes/library-assets.schema.json`

Generate from Pydantic via `model_json_schema()`. This gives:
- a contract for future migrations,
- validation in tests/doctor,
- a stable interface for the plugin without duplicating Python rules.

### 4. AI context pack format
Use a folder, not a database blob:

`<system_dir>/PaperForge/context/<scope>/<id>/`

Contents:
- `manifest.json` — typed metadata, provenance, hashes, included files
- `context.md` — user/LLM-ready packaged text

This is Obsidian-compatible, inspectable, and easy to copy/share locally.

## Implementation Primitives

1. **Python domain models**
   - `PaperForgeConfig`
   - `AssetIndex`
   - `AssetRecord`
   - `AssetHealth`
   - `LifecycleState`
   - `MaturityReport`
   - `ContextPackManifest`

2. **One index builder module**
   - Example boundary: `paperforge/indexing/`
   - Reads library-records, OCR `meta.json`, formal notes, figure-map, exports
   - Produces the canonical index snapshot

3. **One health engine**
   - Example boundary: `paperforge/health/`
   - Pure functions: PDF health, OCR health, Base/template health, overall library health
   - Reused by `status`, `doctor`, plugin dashboard, context pack generation

4. **One context-pack generator**
   - Example boundary: `paperforge/context/`
   - Builds `ask-this-paper`, `ask-this-collection`, `copy-context-pack` payloads from canonical index + source artifacts

5. **One write discipline**
   - `FileLock(...).acquire()` around derived-artifact writes
   - write temp file
   - `os.replace()` into final path

6. **One plugin integration contract**
   - Plugin invokes CLI commands such as `paperforge index refresh`, `paperforge status --json`, `paperforge context pack ...`
   - Plugin reads `library-assets.v1.json`
   - Plugin never re-implements scoring/health/lifecycle logic

## What Should Stay in Stdlib / Current Stack

| Keep | Why |
|------|-----|
| `json` | Canonical index is not large enough to justify a binary or DB format yet |
| `pathlib` | Existing code is already path-centric and Windows-aware |
| `hashlib` | Enough for PDF/fulltext/context-pack fingerprints and stale-cache detection |
| Existing CLI/worker module pattern | Already proven in v1.2-v1.5 and matches the thin-shell plugin goal |
| Existing Obsidian CommonJS plugin style | No build-system migration needed for this milestone |

## What NOT to Add

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Index storage | JSON snapshot + optional JSONL history | SQLite | Adds migration/query complexity and hides state from the vault filesystem without solving a proven scale bottleneck |
| Config typing | Pydantic model on top of current loader | `pydantic-settings` | Helpful for env-heavy apps, but PaperForge's real source of truth is `paperforge.json`; adding another settings layer is unnecessary in v1.6 |
| Plugin validation | Python-generated schema + version check | AJV / Zod in plugin | Creates a second contract surface in JS and pushes business rules toward the plugin |
| File watching | Explicit refresh after worker commands | watchdog / daemon | Violates the local-simple architecture and is unnecessary for user-triggered workflows |
| Search/index engine | Current filesystem artifacts + canonical JSON | Elasticsearch / LanceDB / vector DB | Overkill for milestone scope; AI packaging needs traceable bundles first, not semantic infra |
| YAML parser | Current narrow frontmatter handling + Python indexer | PyYAML / round-trip YAML libs | Extra dependency and formatting churn risk; users do not need full YAML mutation for v1.6 |

## Installation

```bash
# Core additions
pip install "pydantic>=2.13,<3" "filelock>=3.29,<4"

# Dev / contract validation
pip install -D "jsonschema>=4.26,<5"
```

## Integration Notes for Existing Architecture

- Extend `paperforge.config` to return validated Pydantic-backed config objects, but keep current precedence semantics.
- Add a dedicated `index refresh` command that all relevant workers can call after successful mutations.
- Refactor `status --json` to consume the canonical index instead of recounting raw files independently.
- Have the plugin dashboard read index summary fields first, and shell out only for refresh/actions.
- Keep OCR/fulltext/figure outputs where they already live; the new index should reference them, not relocate them.

## Sources

- Pydantic docs via Context7 — typed models, validation, `model_dump()`, `model_json_schema()` — HIGH confidence — https://context7.com/pydantic/pydantic
- Pydantic PyPI JSON — current version `2.13.3` — HIGH confidence — https://pypi.org/pypi/pydantic/json
- filelock docs via Context7 — platform-aware locking, Windows OS-level locking — HIGH confidence — https://context7.com/tox-dev/filelock
- filelock PyPI JSON — current version `3.29.0` — HIGH confidence — https://pypi.org/pypi/filelock/json
- jsonschema docs via Context7 — Draft 2020-12 validator support — HIGH confidence — https://context7.com/python-jsonschema/jsonschema/v4.25.1
- jsonschema PyPI JSON — current version `4.26.0` — HIGH confidence — https://pypi.org/pypi/jsonschema/json
- Existing repo context: `pyproject.toml`, `paperforge/config.py`, `paperforge/worker/status.py`, `paperforge/plugin/main.js` — HIGH confidence
