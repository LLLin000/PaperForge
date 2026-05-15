# JS-First Memory State — Revised Design

> **Date:** 2026-05-15 | **Revision:** 2 — after architecture review
>
> **Key change from v1:** JS does NOT duplicate Python judgment logic.
> Python writes canonical runtime snapshots; JS reads snapshots + spawns only heavy ops.

## Goal

Replace Python subprocess calls for memory layer **state reads** with JavaScript-native file reads. Python retained for all **state judgment** (deps check, chunk count, health assessment) and **heavy operations** (embed build, OCR, sync, repair).

## Problem (unchanged)

31 scattered `exec/spawn/execFileSync` calls in main.js, every state read spawns a Python subprocess. This causes:
- State reset on every settings open (constructor → null → async re-check)
- 3+ full-page re-renders per settings open
- "Status unavailable" when Python path resolution fails
- "Dependencies not installed" on every settings open

## Architecture: Two-Tier Boundary with State File Contract

```
┌──────────────────────────────────────────────────────────────────┐
│                    Obsidian Plugin (JS)                          │
│                                                                   │
│  ┌─────────────────┐   ┌──────────────┐                          │
│  │  memory-state.js│   │   main.js     │                         │
│  │  (JS-native     │──▶│  reads state  │                         │
│  │   file reads)   │   │  renders UI   │                         │
│  │                 │   │               │                          │
│  │ readJSONFile()  │   │ no subprocess │                         │
│  │ readState()     │   │ for state     │                         │
│  └─────────────────┘   └──────┬────────┘                         │
│                                │                                  │
│               spawn only for heavy operations                    │
└────────────────────────────────┼──────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │   Runtime State Snapshots (JSON files)        │
         │   Written by Python. Read by JS.              │
         │                                               │
         │   memory-runtime-state.json                   │
         │   vector-runtime-state.json                   │
         │   runtime-health.json                         │
         │   vector-build-state.json  (already exists)   │
         └───────────────────────┬───────────────────────┘
                                 │
┌────────────────────────────────┼──────────────────────────────────┐
│                     Python CLI (owns judgment)                     │
│                                                                   │
│  paperforge runtime-health --json         ← writes health snapshot│
│  paperforge memory status --json          ← writes memory snapshot│
│  paperforge embed status --json           ← writes vector snapshot│
│  paperforge embed build --resume          ← writes build state    │
│  paperforge memory build                  ← rebuilds DB           │
│  paperforge sync / ocr / repair           ← heavy ops             │
│                                                                   │
│  All health/debug/count judgment lives here.                      │
│  JS never infers health from raw files.                           │
└──────────────────────────────────────────────────────────────────┘
```

## Contract: Runtime Snapshots

### `memory-runtime-state.json`
Written by: `paperforge memory status --json` (mode `write-snapshot` or always)
Location: `<system_dir>/PaperForge/indexes/memory-runtime-state.json`

```json
{
  "schema_version": 1,
  "updated_at": "2026-05-15T12:00:00Z",
  "paper_count_db": 150,
  "paper_count_index": 150,
  "fresh": true,
  "needs_rebuild": false,
  "last_full_build_at": "2026-05-15T11:30:00Z",
  "schema_version_db": 2,
  "fts_ready": true,
  "issues": []
}
```

### `vector-runtime-state.json`
Written by: `paperforge embed status --json` (mode `write-snapshot` or always)
Location: `<system_dir>/PaperForge/indexes/vector-runtime-state.json`

```json
{
  "schema_version": 1,
  "updated_at": "2026-05-15T12:00:00Z",
  "enabled": true,
  "mode": "api",
  "model": "text-embedding-3-small",
  "deps_installed": true,
  "deps_missing": [],
  "py_version": "3.12.3",
  "db_exists": true,
  "chunk_count": 747,
  "build_state": {
    "status": "idle",
    "current": 0,
    "total": 0,
    "paper_id": "",
    "started_at": "",
    "finished_at": "",
    "resume_supported": true,
    "pid": 0,
    "message": ""
  },
  "issues": []
}
```

### `runtime-health.json`
Written by: `paperforge runtime-health --json` (always writes snapshot alongside stdout)
Location: `<system_dir>/PaperForge/indexes/runtime-health.json`

```json
{
  "schema_version": 1,
  "updated_at": "2026-05-15T12:00:00Z",
  "summary": {
    "status": "ok",
    "reason": "All systems operational",
    "safe_read": true,
    "safe_write": true,
    "safe_build": true,
    "safe_vector": true
  },
  "layers": {
    "bootstrap": {"status": "ok", "evidence": [], "next_action": "", "repair_command": ""},
    "read":      {"status": "ok", "evidence": [], "next_action": "", "repair_command": ""},
    "write":     {"status": "ok", "evidence": [], "next_action": "", "repair_command": ""},
    "index":     {"status": "ok", "evidence": [], "next_action": "", "repair_command": ""},
    "vector":    {"status": "ok", "evidence": [], "next_action": "", "repair_command": ""}
  },
  "capabilities": {
    "paper_context": true,
    "reading_log_write": true,
    "project_log_write": true,
    "fts_search": true,
    "vector_retrieve": true
  }
}
```

## New Module: `paperforge/plugin/src/memory-state.js`

**Single responsibility:** read canonical state files on disk. No judgment. No inference. No SQL. No subprocess.

```javascript
const memoryState = {
  // ── Pure file readers ──
  readJSONFile(filePath) → object | null,
  resolveVaultPaths(vaultPath) → { all dir paths },

  // ── Memory Layer ──
  getMemoryRuntime(vaultPath) → object | null,    // reads memory-runtime-state.json
  isMemoryReady(vaultPath) → bool,                 // quick check: file exists + ok
  getMemoryStatusText(vaultPath) → string,         // "Papers: 150 | fresh"

  // ── Vector Layer ──
  getVectorRuntime(vaultPath) → object | null,     // reads vector-runtime-state.json
  isVectorReady(vaultPath) → bool,
  getVectorStatusText(vaultPath) → string,          // "Chunks: 747 | text-embedding-3-small | api"

  // ── Runtime Health ──
  getRuntimeHealth(vaultPath) → object | null,     // reads runtime-health.json
  isHealthOk(vaultPath) → bool,

  // ── Python Path (for spawn only) ──
  getCachedPython(vaultPath, settings) → {path, source, extraArgs},
};
```

### What memory-state.js NEVER does:
- Does NOT read SQLite directly (no `sql.js`, no `better-sqlite3`)
- Does NOT check Python deps by scanning site-packages
- Does NOT count chunks by file size
- Does NOT derive health from raw data
- Does NOT spawn subprocesses

### What memory-state.js DOES:
- Reads JSON files (sync, no async needed)
- Extracts and formats display strings from canonical state
- Caches Python executable path for spawn operations
- All functions are pure and independently testable

## Python Changes (minimal)

### `paperforge memory status --json`
- Unchanged contract
- Optionally writes `memory-runtime-state.json` snapshot after every call

### `paperforge embed status --json`
- Unchanged contract
- Optionally writes `vector-runtime-state.json` snapshot after every call

### `paperforge runtime-health --json`
- Unchanged contract
- Optionally writes `runtime-health.json` snapshot after every call

### `paperforge embed build --resume`
- Already writes `vector-build-state.json`
- Now also writes `vector-runtime-state.json` on completion

### `paperforge memory build`
- Already writes `indexes/`
- Now also writes `memory-runtime-state.json` on completion

## Plugin main.js Changes

### Removed:
- `_execMemoryStatus()` → replaced by `memoryState.getMemoryRuntime()`
- `_execEmbedStatus()` → replaced by `memoryState.getVectorRuntime()`
- Inline dep check `exec()` → replaced by `memoryState.getVectorRuntime().deps_installed`
- Rehydrate `exec()` → replaced by `memoryState.getVectorRuntime().build_state`
- Dashboard `execFileSync()` for runtime-health → replaced by `memoryState.getRuntimeHealth()`

### Added:
- `memory-state.js` import + usage
- `_callPython(cmd, { stream })` — single spawn wrapper for heavy ops
- `_runtimeState` — cached snapshot from last read (survives re-renders)

## Files

```
Create:
  paperforge/plugin/src/memory-state.js          — file-based state reader
  paperforge/plugin/tests/memory-state.test.mjs  — Vitest tests

Modify:
  paperforge/plugin/main.js                      — replace exec calls
  paperforge/plugin/src/testable.js              — add pure helpers for snapshots
  paperforge/worker/status.py                    — write memory-runtime-state.json
  paperforge/commands/embed.py                   — write vector-runtime-state.json
```

## What Python Still Owns (spawn only)

| Command         | Reason |
| --------------- | ------ |
| `memory build`  | Rebuilds SQLite from index (heavy) |
| `embed build`   | Chunks + embeds + writes ChromaDB |
| `embed stop`    | Signal management |
| `embed status --json` | Writes vector-runtime-state.json snapshot |
| `memory status --json` | Writes memory-runtime-state.json snapshot |
| `runtime-health --json` | Writes runtime-health.json snapshot |
| `sync`          | Zotero import + note generation |
| `ocr`           | PDF upload + API call |
| `repair`        | Multi-step state reconciliation |

## Non-Goals (unchanged)
- No rewriting Python CLI logic
- No adding Node native modules
- No touching OCR/sync/repair Python code
- No JS-side SQLite reads in this revision

## Success Criteria
1. Settings → Features opens without spawning Python for state checks
2. Memory status shows instantly (no "Checking...", no flash)
3. Vector deps check shows correct result on first open (from snapshot)
4. Build button still works (spawn Python for build)
5. Dashboard System Status reads from snapshot, not exec
6. Snapshots are refreshed after every build/rebuild/sync
7. Zero Python subprocess for state reads in normal usage
