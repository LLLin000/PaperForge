# Architecture

**Analysis Date:** 2026-05-16

## Architecture Pattern Overview

**Pattern:** Contract-Driven, Python-writes-JS-reads layered architecture with compound skill agent model.

**Key Characteristics:**
- **Python as data authority** — Python writes canonical JSON snapshots; JS reads them directly (no inference, no SQLite in JS)
- **PFResult contract** — All CLI commands return structured `{ok, command, version, data, error}` JSON via `paperforge/core/result.py`
- **Atoms -> Molecules -> Compound skill hierarchy** in agent layer
- **Three runtime state files** bridge Python backend to JS frontend
- **Obsidian plugin** is a thin UI layer that spawns Python subprocesses via `execFile()`/`spawn()`

## Layers

### Layer 1: CLI/Plugin Boundary (PFResult Contract)

**Shared Contract:**
- Python commands return `PFResult` dataclass: `{ok, command, version, data, error, warnings, next_actions}`
- JSON output via `--json` flag on all commands
- Plugin reads either PFResult JSON or falls back to snapshot files
- Defined in `paperforge/core/result.py` (69 lines)

**Error Codes:**
- Centralized enum in `paperforge/core/errors.py` (60 lines)
- 7 groups: Runtime, Config/Vault, BBT/Zotero, OCR, Sync, Schema, Generic
- `.missing_()` handler gracefully handles unknown codes from newer versions

### Layer 2: Python CLI Backend

**Entry Point:**
- `paperforge/cli.py` (572 lines) — argparse-based CLI with subcommands:
  - `sync`, `ocr`, `doctor`, `repair`, `status`, `embed`, `memory`, `deep-reading`, `runtime-health`, `dashboard`, `search`, `retrieve`, `paper-context`, `agent-context`, `paper-status`, `reading-log`, `project-log`, `context`

**CLI Dispatch (`paperforge/commands/`) — 17 command modules:**
| File | Lines | Purpose |
|------|-------|---------|
| `sync.py` | 62 | Sync CLI wrapper (delegates to SyncService) |
| `ocr.py` | 151 | OCR CLI wrapper |
| `status.py` | 33 | Status CLI wrapper |
| `embed.py` | 242 | Embed build/status/stop CLI |
| `memory.py` | 118 | Memory DB build/status CLI |
| `dashboard.py` | 191 | Dashboard JSON provider |
| `deep.py` | 60 | Deep-reading queue viewer |
| `repair.py` | 79 | Repair CLI wrapper |
| `runtime_health.py` | 38 | Health check wrapper + snapshot writer |
| `reading_log.py` | 470 | Reading log management |
| `project_log.py` | 154 | Project log management |
| `search.py` | 74 | FTS + vector search |
| `retrieve.py` | 66 | Vector retrieval |
| `paper_context.py` | 114 | Single-paper context builder |
| `agent_context.py` | 85 | Full agent context builder |
| `context.py` | 140 | Workspace context |
| `paper_status.py` | 63 | Paper status queries |

**Worker Layer (`paperforge/worker/`) — 16 modules:**
| File | Lines | Purpose |
|------|-------|---------|
| `ocr.py` | 1835 | PaddleOCR integration (largest module) |
| `sync.py` | 1126 | Selection sync + workspace migration |
| `status.py` | 1072 | Doctor + status run (health checks) |
| `asset_index.py` | 610 | Formal-library.json index builder |
| `base_views.py` | 475 | Obsidian Base view generation |
| `repair.py` | 389 | Three-way state divergence repair |
| `discussion.py` | 331 | Discussion JSON management |
| `paper_resolver.py` | 323 | Paper path resolution |
| `update.py` | 301 | Self-update mechanism |
| `deep_reading.py` | 121 | Deep reading queue |
| `_utils.py` | 232 | Shared utilities (JSON I/O, filename slug) |
| `asset_state.py` | 177 | Lifecycle/maturity/next-step computation |
| `_domain.py` | 78 | Domain config loading |
| `_progress.py` | 15 | CLI progress spinner |
| `_retry.py` | 69 | Tenacity-based retry helpers |
| `vector_db.py` | 70 | Preflight checks for vector DB |
| `paper_meta.py` | 70 | Per-paper metadata |

**Adapter Layer (`paperforge/adapters/`) — 4 modules:**
| File | Lines | Purpose |
|------|-------|---------|
| `bbt.py` | 210 | BBT JSON export parsing, attachment normalization, PDF identification |
| `obsidian_frontmatter.py` | 306 | Frontmatter reading/writing, candidate markdown generation |
| `zotero_paths.py` | 54 | Path normalization, wikilink generation |
| `collections.py` | 24 | Collection lookup building |

**Service Layer (`paperforge/services/`) — 2 modules:**
| File | Lines | Purpose |
|------|-------|---------|
| `sync_service.py` | 264 | Full sync orchestration (load, select, index, clean) |
| `skill_deploy.py` | 73 | Agent skill deployment |

**Memory Layer (`paperforge/memory/`) — 14 modules:**
| File | Lines | Purpose |
|------|-------|---------|
| `vector_db.py` | 296 | ChromaDB management, embedding, retrieval |
| `builder.py` | 238 | SQLite rebuild from canonical index |
| `runtime_health.py` | 185 | Layer-by-layer health checks |
| `schema.py` | 198 | SQLite schema (DLL), FTS5 config |
| `permanent.py` | 164 | JSONL reading-log/project-log/correction-log imports |
| `query.py` | 160 | SQL query helpers |
| `state_snapshot.py` | 61 | Canonical snapshot writer (3 JSON files) |
| `chunker.py` | 73 | OCR fulltext chunking for embedding |
| `db.py` | 28 | SQLite connection management (WAL mode) |
| `_columns.py` | 38 | Paper table column definitions |
| `fts.py` | 84 | FTS5 search |
| `events.py` | 86 | Event logging |
| `context.py` | 80 | Context assembly |
| `refresh.py` | 111 | Refresh logic |

**Setup Layer (`paperforge/setup/`) — 6 modules:**
| File | Lines | Purpose |
|------|-------|---------|
| `vault.py` | 129 | Vault directory creation |
| `runtime.py` | 91 | Python runtime detection |
| `agent.py` | 72 | Agent skill file deployment |
| `plan.py` | 79 | Installation plan generation |
| `config_writer.py` | 68 | Configuration writing |
| `checker.py` | 53 | Pre-installation checks |

**Schema & Doctor:**
- `paperforge/schema/field_registry.yaml` — 44 field definitions
- `paperforge/schema/__init__.py` — 22 lines: load_field_registry()
- `paperforge/doctor/field_validator.py` — 148 lines: frontmatter validation against registry

**Other Python Modules:**
- `paperforge/config.py` (346 lines) — Vault config management, path resolution
- `paperforge/setup_wizard.py` (794 lines) — Interactive setup wizard (Obsidian-style)
- `paperforge/pdf_resolver.py` (91 lines) — Zotero PDF path resolver
- `paperforge/ocr_diagnostics.py` (250 lines) — OCR troubleshooting
- `paperforge/logging_config.py` (53 lines) — Logging setup

### Layer 3: Obsidian Plugin (JS Frontend)

**Single Monolithic File:** `paperforge/plugin/main.js` (4,914 lines)

**Key Components:**
1. **`memoryState` IIFE (lines 8-143)** — Inline module for reading snapshots, python detection, buildSnapshot()
2. **Inlined testable functions (lines 146-341)** — `resolvePythonExecutable()`, `checkRuntimeVersion()`, `classifyError()`, `buildRuntimeInstallCommand()`, `parseRuntimeStatus()`, `runSubprocess()`, `buildCommandArgs()`, ACTIONS array
3. **Cross-platform Python/BBT detection (lines 343-509)** — `paperforgeEnrichedEnv()`, `getPaperforgePythonCmd()`, `tryExecPythonVersion()`, Mac/Linux/Windows Python discovery, BetterBibTeX profile scanning
4. **i18n System (lines 524-817)** — `LANG` object with `en` and `zh` keys, `t()` translation function, `langFromApp()` auto-detection
5. **PaperForgeStatusView (lines 883-2515)** — Obsidian ItemView with 3 modes:
   - `global` mode — system homepage with library snapshot, system status grid, issues panel, contextual actions
   - `paper` mode — per-paper reading companion with workflow toggles, next-step card, discussion, technical details
   - `collection` mode — domain-level workflow overview with funnel, OCR pipeline, batch actions
6. **PaperForgeSettingTab (lines 2517-3903)** — Settings UI with two tabs:
   - `setup` tab — Python interpreter management, runtime health, install wizard, preparation guide
   - `features` tab — Skills management (system/user), Memory Layer, Vector DB config with full lifecycle
7. **Setup Wizard Modal** — 5-step interactive installation wizard
8. **PaperForgePlugin class (lines ~4470-4912)** — Plugin registration, commands, auto-update, file polling
9. **OCR Privacy Modal** (lines 3905-3939) — Once-per-session privacy warning

**Extracted Pure Functions:**
- `paperforge/plugin/src/testable.js` (224 lines) — 8 exported functions from main.js, no Obsidian dependency

### Layer 4: Agent Skill Layer

**Compound skill model:**
- `paperforge/skills/paperforge/SKILL.md` — Compound: bootstrap + agent-context + runtime-health -> route -> molecule
- `paperforge/skills/paperforge/workflows/` — 8 molecule workflow files: paper-search, deep-reading, paper-qa, reading-log, project-log, methodology, project-engineering
- `paperforge/skills/paperforge/references/` — Shared reference materials including 19 chart-reading guides
- `paperforge/skills/paperforge/scripts/` — Atomic scripts: `pf_bootstrap.py` (227 lines), `pf_deep.py` (1,569 lines)

**Supported Agent Platforms:**
- OpenCode (primary), Claude Code, Cursor, Windsurf, GitHub Copilot, Codex, Cline

## Data Flow

### Data Flow 1: Snapshot Bridge (Python -> JS)

```
Python writes (at end of every relevant CLI command):
  paperforge/commands/runtime_health.py -> write_runtime_health()
    -> System/PaperForge/indexes/runtime-health.json
  
  paperforge/worker/status.py (run_status) -> write_memory_runtime()
    -> System/PaperForge/indexes/memory-runtime-state.json
  
  paperforge/commands/embed.py (embed status) -> write_vector_runtime()
    -> System/PaperForge/indexes/vector-runtime-state.json

JS reads (via memoryState IIFE):
  main.js:30-35 -> readJSONFile() -> memoryState.getMemoryRuntime/VectorRuntime/RuntimeHealth()
  
Snapshot Contract (state_snapshot.py):
  memory-runtime-state.json: {schema_version, updated_at, source_command, paper_count_db, paper_count_index, fresh, needs_rebuild, last_full_build_at, schema_version_db, fts_ready}
  
  vector-runtime-state.json: {schema_version, updated_at, source_command, enabled, mode, model, deps_installed, deps_missing, py_version, db_exists, chunk_count, build_state}
  
  runtime-health.json: {summary: {status, reason, safe_read, safe_write, safe_build, safe_vector}, layers: {bootstrap, read, write, index, vector}, capabilities}
```

### Data Flow 2: Plugin Action Execution

```
User clicks button in Dashboard (e.g., "Sync Library")
  -> PaperForgeStatusView._runAction(action, button) [line 2274]
  -> guard checks: OCR privacy (DASH-03), disabled, double-click prevention
  -> resolvePythonExecutable(vaultPath, settings)
  -> spawn(pythonExe, [...extraArgs, '-m', 'paperforge', action.cmd, ...extraArgs])
  -> stdout event listener parses log lines, updates message area
  -> 4-second polling timer: _fetchStats(true)
  -> on close: check exit code, show success/failure, refresh stats
  -> triggers: _fetchStats() -> tries 'paperforge dashboard --json' first, falls back to formal-library.json, falls back to 'paperforge status --json'
```

### Data Flow 3: Memory Build

```
CLI: paperforge memory build
  -> paperforge/commands/memory.py -> build_from_index(vault)
  -> paperforge/worker/asset_index.py -> read_index(vault) # reads formal-library.json
  -> paperforge/memory/builder.py -> build_from_index(vault):
     1. Compute canonical hash from sorted index items
     2. Open SQLite connection to paperforge.db
     3. Schema version check: drop + recreate if mismatched
     4. DELETE all tables (foreign_keys OFF)
     5. Insert papers, assets, aliases rows
     6. FTS5 population: INSERT INTO paper_fts FROM papers
     7. Import JSONL logs: reading-log.jsonl -> reading_log table
     8. Import JSONL logs: project-log.jsonl -> project_log table
     9. Import corrections: correction-log.jsonl -> paper_events table
    10. Write meta table: schema_version, paperforge_version, created_at, last_full_build_at, canonical_index_hash
    11. COMMIT
```

### Data Flow 4: Embed Build

```
CLI: paperforge embed build
  -> paperforge/commands/embed.py run():
     1. Preflight check via _preflight_check() (deps installed, mode valid)
     2. Read canonical index from asset_index
     3. Filter items where ocr_status == "done"
     4. Mark build state as "running" in vector-build-state.json (pid, model, mode, total)
     5. For each paper:
        a. Read OCR fulltext from fulltext_path
        b. chunk_fulltext() -> split by page, group paragraphs, detect sections
        c. delete_paper_vectors(vault, key) -> remove old chunks from ChromaDB
        d. embed_paper() -> either local (sentence-transformers) or API (openai)
        e. Mark progress: EMBED_PROGRESS:current:total:key
     6. On completion: mark build state "completed", write vector-runtime-state.json
```

### Data Flow 5: Sync (Full Lifecycle)

```
CLI: paperforge sync
  -> paperforge/commands/sync.py -> SyncService.run():
     Phase 1: Selection
       -> load_exports() -> load BBT JSON files from System/PaperForge/exports/
       -> run_selection_sync() -> legacy worker sync
     Phase 2: Index
       -> resolve_paths() + load_domain_config()
       -> ensure_base_views() -> generate .base files
       -> migrate_to_workspace() -> flat notes -> workspace dirs
       -> asset_index.build_index() -> generate formal-library.json
       -> clean_orphaned_records() + clean_flat_notes()
     Phase 3: Return PFResult
       -> {... selection_result, index_result }
```

### Data Flow 6: Snapshot Refresh Polling

```
Plugin startup (_startFilePolling, line 4681):
  -> setInterval every 120 seconds:
     -> _checkExports(): monitor mtime of export JSON files, trigger auto-sync on change
     -> _checkOcr(): monitor mtime of meta.json files, trigger per-paper sync on change

First launch detection (line 4627):
  -> Check if memory-runtime-state.json exists
  -> If missing: fire-and-forget 'runtime-health --json' to generate snapshots

Formal-library.json change detection (line 2493):
  -> active-leaf-change event: 300ms debounce, detect mode (global/paper/collection)
  -> vault.modify event: if file is formal-library.json -> invalidate cache + refresh mode
```

## State Management

**Three-way state model** (managed by repair worker):
1. **Canonical index** (`formal-library.json`) — the "source of truth" for all paper metadata
2. **Formal notes** (frontmatter per .md file) — user-controlled workflow flags (do_ocr, analyze)
3. **SQLite DB** (`paperforge.db`) — denormalized, FTS-enabled query layer

**Divergence detection:**
- `paperforge/worker/repair.py` (389 lines) — three-way state divergence repair
- `paperforge/worker/asset_state.py` (177 lines) — lifecycle/maturity/next-step computation
- `paperforge/worker/asset_index.py` (610 lines) — canonical index builder

## Filesystem State Files

```
System/PaperForge/indexes/
  formal-library.json       — Canonical index (generated by sync)
  memory-runtime-state.json — Memory layer snapshot (generated by status, memory, embed)
  vector-runtime-state.json — Vector DB snapshot (generated by embed status/build)
  runtime-health.json       — Runtime health summary (generated by runtime-health)
  vector-build-state.json   — Embed build progress (streamed by embed build)
  paperforge.db             — SQLite memory layer database
  vectors/                  — ChromaDB persistence directory
```

## Cross-Platform Handling

- Python interpreter detection: Windows `Scripts/` vs POSIX `bin/` in venv detection
- Zotero data dir detection: APPDATA (Win) vs Application Support (macOS) vs .zotero (Linux)
- Junction vs symlink: Windows junctions handled via ctypes in `worker/status.py`
- Git detection: `cmd.exe /c where git` (Win) vs `which git` (POSIX)
- UTF-8 console: Win32 SetConsoleOutputCP(65001)
- Enriched PATH: homebrew (macOS), .local/bin (Linux), git dir appended

## Error Handling Strategy

**Python Side:**
- PFResult contract -> `data.error` field with ErrorCode
- Recovery hints: `data.next_actions: [dict]`, `error.suggestions: [str]`
- Per-module error classification via ErrorCode enum (7 groups)
- repair command handles three-way state divergence

**JS Side:**
- `classifyError()` (line 222) — maps error codes to {type, message, recoverable, action}
- `parseRuntimeStatus()` (line 248) — parses stderr/stdout for known error patterns
- 3-tier fallback for stats: `paperforge dashboard --json` -> formal-library.json -> `paperforge status --json`
- OCR privacy notice (once per session)
- Double-click guard on action buttons
- Disabled action resolution

## i18n System

**Location:** `paperforge/plugin/main.js`, lines 524-817

**Mechanism:**
- `LANG` object contains `en` and `zh` keys
- `Object.assign(LANG.en, ...)` extends both EN and ZH with shared fields
- `langFromApp(app)` checks Obsidian config -> localStorage -> defaults to 'en'
- `t(key)` function: returns `T[key]` || `LANG.en[key]` || key as fallback
- Translation granularity: per-UI-element level (~400 translated strings)
- Features tab has full bilingual support (field labels, descriptions, button text, wizard steps)

## Plugin Registration

**Location:** `paperforge/plugin/main.js`, lines ~4470-4912

- Plugin ID: `paperforge`
- Custom view: `VIEW_TYPE_PAPERFORGE = 'paperforge-status'`
- Custom icon: `PF_ICON_ID = 'paperforge'` with SVG path data
- 5 Obsidian commands registered:
  - `paperforge-open-view` — Open Dashboard
  - `paperforge-sync` — Sync Library
  - `paperforge-ocr` — Run OCR
  - `paperforge-doctor` — Run Doctor
  - `paperforge-repair` — Repair Issues
- Auto-update: checks plugin version vs installed package, tries PyPI then git

---

*Architecture analysis: 2026-05-16*
