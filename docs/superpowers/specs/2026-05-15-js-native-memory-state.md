# JS-Native Memory State Design

> **Date:** 2026-05-15 | **Depends on:** Memory Layer UX Audit

## Goal

Replace Python subprocess calls for memory layer state reads with direct JavaScript file/SQLite reads. Python retained only for heavy operations (embed build, OCR, sync, repair).

## Problem

31 scattered `exec/spawn/execFileSync` calls in main.js, every state read (memory status, embed status, deps check, runtime health) spawns a Python subprocess. This causes:
- State reset on every settings open (constructor → null → async re-check)
- 3+ full-page re-renders per settings open
- "Status unavailable" when Python path resolution fails
- "Dependencies not installed" on every settings open

## Architecture: Two-Tier Boundary

```
┌─────────────────────────────────────────────────────────┐
│                     Obsidian Plugin (JS)                │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │ memory-state │   │   main.js     │   │  testable   │ │
│  │   (NEW)      │   │  (modified)   │   │  (extended) │ │
│  │              │   │               │   │             │ │
│  │ SQLite read  │──▶│ direct calls  │──▶│ pure helpers│ │
│  │ JSONL read   │   │ no subprocess │   │ for tests   │ │
│  │ JSON read    │   │               │   │             │ │
│  └──────────────┘   └──────┬────────┘   └─────────────┘ │
│                             │                            │
│                    spawn only for heavy ops               │
└─────────────────────────────┼────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────┐
│              Python CLI (unchanged)                       │
│                                                          │
│  paperforge memory build   ◀── rebuild (heavy)           │
│  paperforge embed build    ◀── vector build (heavy)      │
│  paperforge embed stop     ◀── stop (heavy)              │
│  paperforge sync           ◀── sync (heavy)              │
│  paperforge ocr            ◀── OCR (heavy)               │
│                                                          │
│  State written to disk:                                  │
│    paperforge.db                 ← SQLite (JS reads)     │
│    vector-build-state.json      ← JSON (JS reads)        │
│    formal-library.json          ← JSON (JS reads)        │
│    reading-log.jsonl            ← JSONL (JS reads)       │
│    data.json                    ← settings (JS reads)    │
└──────────────────────────────────────────────────────────┘
```

## New Module: `paperforge/plugin/src/memory-state.js`

Single entry point for all memory layer state reads. No subprocess. No async (except SQLite queries).

```javascript
const memoryState = {
  // ── Memory Database Status ──
  getMemoryStatus(vaultPath) → { paperCount, freshness, needsRebuild }

  // ── Embed/Vector Status ──
  getEmbedStatus(vaultPath) → { dbExists, chunkCount, model, mode, buildState }

  // ── Dependency Check ──
  checkVectorDeps() → { installed: bool, missing: string[] }

  // ── Runtime Health ──
  getRuntimeHealth(vaultPath) → { summary: {...}, layers: {...}, capabilities: {...} }

  // ── Dependency Check ──
  getPaperCount(vaultPath) → number

  // ── Python Version (cached) ──
  getPythonVersion(vaultPath, settings) → string | null
}
```

### Implementation Details

**1. `getMemoryStatus(vaultPath)`**
- Open `paperforge.db` via better-sqlite3 (read-only)
- Query: `SELECT COUNT(*) FROM papers` + `SELECT value FROM meta WHERE key='last_full_build_at'`
- Returns: `{ paperCount: 150, freshness: 'fresh'|'stale', lastBuild: '...' }`
- No Python call

**2. `getEmbedStatus(vaultPath)`**
- Read `vector-build-state.json` from `System/PaperForge/indexes/`
- Read `data.json` for model/mode settings
- Check ChromaDB: `System/PaperForge/indexes/vectors/chroma.sqlite3` exists → count tables
- Returns: `{ dbExists, chunkCount, model, mode, buildState }`
- No Python call

**3. `checkVectorDeps()`**
- `try { require('chromadb') } catch` → check if installable
- `try { require('sentence-transformers') } catch` → check if installable (this fails in Node, so check file existence in venv site-packages)
- Returns: `{ installed: bool, missing: ['chromadb', ...] }`
- No Python call

**4. `getRuntimeHealth(vaultPath)`**
- Composes results from getMemoryStatus + getEmbedStatus + bootstrap check
- Returns same shape as `paperforge runtime-health --json`
- No Python call for reading; heavy builds still use Python

**5. `resolvePythonPath(vaultPath, settings)`**
- Same logic as current `resolvePythonExecutable`
- Cached after first resolution
- Returns `{ path, source, extraArgs }`

## What Python Still Owns (spawn only)

| Command         | Reason                              |
| --------------- | ----------------------------------- |
| `memory build`    | Rebuilds SQLite from index (heavy)  |
| `embed build`     | Chunks + embeds + writes ChromaDB   |
| `embed stop`      | Signal management                   |
| `sync`            | Zotero import + note generation     |
| `ocr`             | PDF upload + API call               |
| `repair`          | Multi-step state reconciliation     |

## Plugin main.js Changes

**Removed:**
- `_execMemoryStatus()` (replaced by `memoryState.getMemoryStatus()`)
- `_execEmbedStatus()` (replaced by `memoryState.getEmbedStatus()`)
- Inline dep check `exec()` (replaced by `memoryState.checkVectorDeps()`)
- Rehydrate `exec()` (replaced by `memoryState.getEmbedStatus()`)
- Dashboard `execFileSync()` for runtime-health (replaced by `memoryState.getRuntimeHealth()`)

**Consolidated:**
- `_callPython(cmd, opts)` — single spawn wrapper for remaining heavy ops
- `_runtimeState` — unified cached state object (survives re-renders)

## Files

```
Create:
  paperforge/plugin/src/memory-state.js          — JS-native state reader
  paperforge/plugin/tests/memory-state.test.mjs  — Vitest tests

Modify:
  paperforge/plugin/main.js                      — replace exec calls
  paperforge/plugin/package.json                 — add better-sqlite3
  paperforge/plugin/src/testable.js              — add pure helpers
```

## Non-Goals
- No rewriting Python CLI
- No adding Node native module builds
- No touching OCR/sync/repair Python code
- No CDP/browser automation

## Success Criteria
1. Settings → Features opens without spawning Python for status checks
2. Memory status shows instantly (no "Checking...")
3. Vector deps check shows correct result on first open
4. Build button still works (spawn Python for build)
5. Dashboard System Status still works (JS-native runtime-health)
6. Zero Python subprocess for state reads in normal usage
