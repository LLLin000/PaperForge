# JS-First Memory State — Revised Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all Python subprocess calls for memory layer state reads with JS-native file reads. Python writes canonical runtime snapshot files; JS reads them. Python retained only for heavy operations.

**Architecture:** New `memory-state.js` module reads JSON snapshot files on disk. Python CLI writes those snapshots after every status check / build / rebuild. main.js consumes `memoryState` instead of spawning Python for status. Single `_callPython()` wrapper handles remaining heavy operations.

**Tech Stack:** Node.js `fs` (sync reads of JSON files), Obsidian Plugin API, Python CLI (unchanged).

**Spec:** `docs/superpowers/specs/2026-05-15-js-native-memory-state.md` (Revised v2)

**Audit:** `docs/superpowers/specs/2026-05-15-memory-layer-ux-audit.md`

**Key revision:** No `sql.js`. No JS-side SQLite reads. No JS-side dep inference. No duplicated health logic. Python IS the judgment layer; JS IS the display layer.

---

## File Structure Map

```text
Create:
  paperforge/plugin/src/memory-state.js          — file-based state reader

Modify:
  paperforge/plugin/main.js                      — remove exec() for state reads, use memory-state
  paperforge/worker/status.py                    — write memory-runtime-state.json
  paperforge/commands/embed.py                   — write vector-runtime-state.json
  paperforge/commands/runtime_health.py          — write runtime-health.json
```

---

### Task 1: Make Python write canonical runtime snapshots

**Files:**
- Modify: `paperforge/worker/status.py`
- Modify: `paperforge/commands/embed.py`
- Modify: `paperforge/commands/runtime_health.py`
- Create: `paperforge/memory/state_snapshot.py` (helper)

Write canonical JSON snapshot files so JS never needs to spawn Python for status reads.

- [ ] **Step 1: Create snapshot helper**

Create `paperforge/memory/state_snapshot.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from paperforge.config import paperforge_paths


def _snapshot_dir(vault: Path) -> Path:
    paths = paperforge_paths(vault)
    d = paths["paperforge"] / "indexes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_memory_runtime(vault: Path, *, paper_count_db: int,
                         paper_count_index: int, fresh: bool,
                         needs_rebuild: bool, last_full_build_at: str,
                         schema_version_db: int, fts_ready: bool,
                         issues: list[str] | None = None) -> None:
    snap = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count_db": paper_count_db,
        "paper_count_index": paper_count_index,
        "fresh": fresh,
        "needs_rebuild": needs_rebuild,
        "last_full_build_at": last_full_build_at,
        "schema_version_db": schema_version_db,
        "fts_ready": fts_ready,
        "issues": issues or [],
    }
    path = _snapshot_dir(vault) / "memory-runtime-state.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


def write_vector_runtime(vault: Path, *, enabled: bool, mode: str, model: str,
                         deps_installed: bool, deps_missing: list[str] | None,
                         py_version: str, db_exists: bool, chunk_count: int,
                         build_state: dict | None, issues: list[str] | None = None) -> None:
    snap = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "enabled": enabled,
        "mode": mode,
        "model": model,
        "deps_installed": deps_installed,
        "deps_missing": deps_missing or [],
        "py_version": py_version,
        "db_exists": db_exists,
        "chunk_count": chunk_count,
        "build_state": build_state or {},
        "issues": issues or [],
    }
    path = _snapshot_dir(vault) / "vector-runtime-state.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


def write_runtime_health(vault: Path, health_data: dict) -> None:
    path = _snapshot_dir(vault) / "runtime-health.json"
    path.write_text(json.dumps(health_data, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 2: Wire memory status to write snapshot**

In `paperforge/worker/status.py`, after computing memory status data, call:

```python
from paperforge.memory.state_snapshot import write_memory_runtime

# After building the status dict inside run_memory_status():
write_memory_runtime(
    vault,
    paper_count_db=s.get("paper_count_db", 0),
    paper_count_index=s.get("paper_count_index", 0),
    fresh=s.get("fresh", False),
    needs_rebuild=s.get("needs_rebuild", False),
    last_full_build_at=s.get("last_full_build_at", ""),
    schema_version_db=s.get("schema_version_db", 0),
    fts_ready=s.get("fts_ready", False),
)
```

- [ ] **Step 3: Wire embed status to write snapshot**

In `paperforge/commands/embed.py`, after the `case "status"` block or inside `_cmd_status()`, call:

```python
from paperforge.memory.state_snapshot import write_vector_runtime

# Inside embed status handler, after computing status:
write_vector_runtime(
    vault,
    enabled=...,
    mode=...,
    model=...,
    deps_installed=...,
    deps_missing=...,
    py_version=...,
    db_exists=...,
    chunk_count=...,
    build_state=...,
)
```

Also call after `embed build` completes (success or fail).

- [ ] **Step 4: Wire runtime-health to write snapshot**

In `paperforge/commands/runtime_health.py`, after building the health dict, call:

```python
from paperforge.memory.state_snapshot import write_runtime_health

write_runtime_health(vault, health_data)
```

- [ ] **Step 5: Verify snapshots are written**

Run in test1 vault:
```bash
python -m paperforge --vault "D:\L\Med\test1" memory status --json
```
Expected: `System/PaperForge/indexes/memory-runtime-state.json` created.

```bash
python -m paperforge --vault "D:\L\Med\test1" embed status --json
```
Expected: `System/PaperForge/indexes/vector-runtime-state.json` created.

```bash
python -m paperforge --vault "D:\L\Med\test1" runtime-health --json
```
Expected: `System/PaperForge/indexes/runtime-health.json` created.

- [ ] **Step 6: Commit**

```bash
git add paperforge/memory/state_snapshot.py paperforge/worker/status.py paperforge/commands/embed.py paperforge/commands/runtime_health.py
git commit -m "feat: Python writes canonical runtime snapshot files for JS reads"
```

---

### Task 2: Create `memory-state.js` — JS-native file-based state reader

**Files:**
- Create: `paperforge/plugin/src/memory-state.js`
- Test: `paperforge/plugin/tests/memory-state.test.mjs`

This module reads canonical snapshot files. NO SQL. NO subprocess. Pure JS file I/O.

- [ ] **Step 1: Write the failing tests**

```javascript
// paperforge/plugin/tests/memory-state.test.mjs
import { describe, expect, it, beforeEach } from 'vitest';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// We test pure functions that don't need Obsidian API
import {
  resolveVaultPaths,
  readJSONFile,
  getMemoryRuntime,
  getVectorRuntime,
  getRuntimeHealth,
  isMemoryReady,
  isVectorReady,
  isHealthOk,
  getMemoryStatusText,
  getVectorStatusText,
  buildSnapshot,
} from '../src/memory-state.js';

describe('resolveVaultPaths', () => {
  it('resolves paperforge directories from vault root', () => {
    const paths = resolveVaultPaths('/fake/vault');
    expect(paths.systemDir).toBe(path.join('/fake/vault', 'System', 'PaperForge'));
    expect(paths.indexesDir).toBe(path.join('/fake/vault', 'System', 'PaperForge', 'indexes'));
  });
});

describe('readJSONFile', () => {
  it('returns null for non-existent file', () => {
    expect(readJSONFile('/nonexistent/file.json')).toBeNull();
  });
});

describe('buildSnapshot', () => {
  it('returns partial snapshot when files are missing', () => {
    // Use custom readFn that always returns null
    const readFn = () => null;
    const snap = buildSnapshot('/vault', readFn, (p) => {});
    expect(snap.memory).toBeNull();
    expect(snap.vector).toBeNull();
    expect(snap.health).toBeNull();
    expect(snap.summary.status).toBe('unknown');
  });

  it('returns ok when all files present and healthy', () => {
    const files = {
      'memory-runtime-state.json': { paper_count_db: 150, fresh: true, needs_rebuild: false },
      'vector-runtime-state.json': { enabled: true, deps_installed: true, db_exists: true, chunk_count: 747 },
      'runtime-health.json': { summary: { status: 'ok' } },
    };
    const readFn = (filePath) => {
      for (const [name, data] of Object.entries(files)) {
        if (filePath.endsWith(name)) return data;
      }
      return null;
    };
    const snap = buildSnapshot('/vault', readFn, (p) => {});
    expect(snap.memory).not.toBeNull();
    expect(snap.vector).not.toBeNull();
    expect(snap.health).not.toBeNull();
    expect(snap.summary.status).toBe('ready');
  });
});

describe('formatting helpers', () => {
  it('getMemoryStatusText formats fresh status', () => {
    expect(getMemoryStatusText(150, true)).toBe('Papers: 150 | fresh');
  });

  it('getMemoryStatusText returns prompt when no data', () => {
    expect(getMemoryStatusText(0, false)).toBe('DB not found. Run paperforge memory build.');
  });

  it('getVectorStatusText formats api mode', () => {
    expect(getVectorStatusText(747, 'text-embedding-3-small', 'api')).toBe('Chunks: 747 | text-embedding-3-small | api');
  });

  it('isVectorReady returns false when deps not installed', () => {
    const snap = { vector: { deps_installed: false } };
    expect(isVectorReady(snap)).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd paperforge/plugin && npm test -- tests/memory-state.test.mjs
```
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

Create `paperforge/plugin/src/memory-state.js`:

```javascript
const fs = require('fs');
const path = require('path');

// ═══════════════════════════════════════════════════════════════
// Path Resolution
// ═══════════════════════════════════════════════════════════════

function resolveVaultPaths(vaultPath) {
  const systemDir = path.join(vaultPath, 'System', 'PaperForge');
  return {
    vault: vaultPath,
    systemDir,
    indexesDir: path.join(systemDir, 'indexes'),
    logsDir: path.join(systemDir, 'logs'),
    dbPath: path.join(systemDir, 'indexes', 'paperforge.db'),
    memoryStatePath: path.join(systemDir, 'indexes', 'memory-runtime-state.json'),
    vectorStatePath: path.join(systemDir, 'indexes', 'vector-runtime-state.json'),
    healthStatePath: path.join(systemDir, 'indexes', 'runtime-health.json'),
    buildStatePath: path.join(systemDir, 'indexes', 'vector-build-state.json'),
    pluginDataPath: path.join(vaultPath, '.obsidian', 'plugins', 'paperforge', 'data.json'),
    pfJsonPath: path.join(vaultPath, 'paperforge.json'),
  };
}

// ═══════════════════════════════════════════════════════════════
// Pure File Readers
// ═══════════════════════════════════════════════════════════════

function readJSONFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch (_) { return null; }
}

// ═══════════════════════════════════════════════════════════════
// Snapshot Readers (read Python-written canonical state)
// ═══════════════════════════════════════════════════════════════

function getMemoryRuntime(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.memoryStatePath);
}

function getVectorRuntime(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.vectorStatePath);
}

function getRuntimeHealth(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.healthStatePath);
}

// ═══════════════════════════════════════════════════════════════
// Quick Checks (turn snapshot into bool)
// ═══════════════════════════════════════════════════════════════

function isMemoryReady(vaultPath) {
  const s = getMemoryRuntime(vaultPath);
  return !!(s && s.paper_count_db > 0 && !s.needs_rebuild);
}

function isVectorReady(vaultPath) {
  const s = getVectorRuntime(vaultPath);
  if (!s) return false;
  if (!s.enabled) return false;
  if (!s.deps_installed) return false;
  if (!s.db_exists) return false;
  if (s.chunk_count === 0) return false;
  return true;
}

function isHealthOk(vaultPath) {
  const s = getRuntimeHealth(vaultPath);
  return !!(s && s.summary && s.summary.status === 'ok');
}

// ═══════════════════════════════════════════════════════════════
// Formatting (turn snapshot into display string)
// ═══════════════════════════════════════════════════════════════

function getMemoryStatusText(vaultPath) {
  const s = getMemoryRuntime(vaultPath);
  if (!s || s.paper_count_db === 0) return 'DB not found. Run paperforge memory build.';
  return `Papers: ${s.paper_count_db} | ${s.fresh ? 'fresh' : 'stale'}`;
}

function getVectorStatusText(vaultPath) {
  const s = getVectorRuntime(vaultPath);
  if (!s) return 'Status unavailable';
  return `Chunks: ${s.chunk_count} | ${s.model} | ${s.mode}`;
}

// ═══════════════════════════════════════════════════════════════
// Python Path (for spawn only — NOT used for state reads)
// ═══════════════════════════════════════════════════════════════

const { execFileSync } = require('node:child_process');

function resolvePythonPath(vaultPath, settings) {
  if (settings && settings.python_path && settings.python_path.trim()) {
    const p = settings.python_path.trim();
    if (fs.existsSync(p)) return { path: p, source: 'manual', extraArgs: [] };
  }
  const venvCandidates = [
    path.join(vaultPath, '.paperforge-test-venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, '.venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, 'venv', 'Scripts', 'python.exe'),
  ];
  for (const c of venvCandidates) {
    if (fs.existsSync(c)) return { path: c, source: 'auto-detected', extraArgs: [] };
  }
  for (const c of [{path:'python',extraArgs:[]},{path:'python3',extraArgs:[]}]) {
    try {
      const out = execFileSync(c.path, [...c.extraArgs, '--version'], {encoding:'utf-8',timeout:5000,windowsHide:true});
      if (out && out.toLowerCase().includes('python')) return { path:c.path, source:'auto-detected', extraArgs:c.extraArgs };
    } catch {}
  }
  return { path: 'python', source: 'auto-detected', extraArgs: [] };
}

let _cachedPython = null;
function getCachedPython(vaultPath, settings) {
  if (!_cachedPython) _cachedPython = resolvePythonPath(vaultPath, settings);
  return _cachedPython;
}

// ═══════════════════════════════════════════════════════════════
// Build Snapshot (testable composition of all layers)
// ═══════════════════════════════════════════════════════════════

function buildSnapshot(vaultPath, _readFn, _resolvePaths) {
  const readFn = _readFn || readJSONFile;
  const resolvePaths = _resolvePaths || resolveVaultPaths;
  const paths = resolvePaths(vaultPath);

  const memory = readFn(paths.memoryStatePath);
  const vector = readFn(paths.vectorStatePath);
  const health = readFn(paths.healthStatePath);

  const memoryOk = !!(memory && memory.paper_count_db > 0 && !memory.needs_rebuild);
  const vectorOk = !!(vector && vector.enabled && vector.deps_installed && vector.db_exists && vector.chunk_count > 0);

  return {
    memory,
    vector,
    health,
    updatedAt: memory?.updated_at || vector?.updated_at || '',
    summary: {
      status: memoryOk && vectorOk ? 'ready' : 'degraded',
      memoryReady: memoryOk,
      vectorReady: vectorOk,
      healthOk: !!(health?.summary?.status === 'ok'),
    },
  };
}

// ═══════════════════════════════════════════════════════════════

module.exports = {
  resolveVaultPaths,
  readJSONFile,
  getMemoryRuntime,
  getVectorRuntime,
  getRuntimeHealth,
  isMemoryReady,
  isVectorReady,
  isHealthOk,
  getMemoryStatusText,
  getVectorStatusText,
  resolvePythonPath,
  getCachedPython,
  buildSnapshot,
};
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd paperforge/plugin && npm test -- tests/memory-state.test.mjs
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/memory-state.js paperforge/plugin/tests/memory-state.test.mjs
git commit -m "feat: add JS-native file-based memory state reader module"
```

---

### Task 3: Wire main.js to use memory-state snapshots

**Files:**
- Modify: `paperforge/plugin/main.js`

Replace 5 Python exec sites with snapshot reads. Keep spawn for heavy ops.

- [ ] **Step 1: Add import**

At top of main.js:
```javascript
const memoryState = require('./src/memory-state.js');
```

- [ ] **Step 2: Replace `_execMemoryStatus()` with `getMemoryStatusText()`**

In `_renderMemoryStatus`, replace async exec pattern:
```javascript
// BEFORE:
if (this._memoryStatusText !== null) { ... cached ... }
else { ... async exec + callback ... }

// AFTER:
const statusText = memoryState.getMemoryStatusText(vp);
this._renderMemoryStatusText(statusRow, statusText, this._lastSyncTime || '');
```

Memory status is now synchronous — no "Checking...", no callback.

- [ ] **Step 3: Replace dep check with `getVectorRuntime().deps_installed`**

In `_renderVectorSection`:
```javascript
// BEFORE:
if (this._vectorDepsOk === null) {
    exec(`"${py}" -c "import chromadb,sentence_transformers;..."`);
}

// AFTER:
const vr = memoryState.getVectorRuntime(vp);
this._vectorDepsOk = vr ? vr.deps_installed : null;
```

- [ ] **Step 4: Replace `_execEmbedStatus()` and rehydrate with `getVectorRuntime()`**

```javascript
// BEFORE:
this._execEmbedStatus(pyResult.path, vp, (text) => { ... });
// AND separate rehydrate exec

// AFTER:
const vr = memoryState.getVectorRuntime(vp);
this._embedStatusText = memoryState.getVectorStatusText(vp);
// buildState from vr.build_state
```

- [ ] **Step 5: Replace Dashboard runtime-health exec**

At line ~1493:
```javascript
// BEFORE:
const rh = execFileSync(pyExe, [...args, '...runtime-health --json']);

// AFTER:
const rh = memoryState.getRuntimeHealth(vp2);
memOk = memoryState.isHealthOk(vp2);
memDetail = rh?.summary?.reason || 'Unknown';
```

- [ ] **Step 6: Add `_callPython()` wrapper for remaining heavy ops**

```javascript
_callPython(command, { stream, env, onData, onClose }) {
    const py = memoryState.getCachedPython(
        this.app.vault.adapter.basePath,
        this.plugin.settings
    );
    const vp = this.app.vault.adapter.basePath;
    const args = [...py.extraArgs, '-m', 'paperforge', '--vault', vp, ...command];
    if (stream) {
        const { spawn } = require('node:child_process');
        const child = spawn(py.path, args, { cwd: vp, env, windowsHide: true });
        if (onData) child.stdout.on('data', onData);
        child.on('close', onClose);
        return child;
    }
    const { execFile } = require('node:child_process');
    execFile(py.path, args, { cwd: vp, timeout: 60000 },
        (err, stdout, stderr) => { onClose(err ? 1 : 0, stdout, stderr); });
    return null;
}
```

Replace all remaining `spawn()/execFile()` calls in build/sync/stop handlers with `this._callPython(...)`.

- [ ] **Step 7: Verify**

```bash
node --check paperforge/plugin/main.js
```
Expected: no errors

- [ ] **Step 8: Commit**

```bash
git add paperforge/plugin/main.js
git commit -m "refactor: replace Python exec with memory-state snapshot reads"
```

---

### Task 4: Add `_refreshSnapshots()` — refresh snapshots after heavy ops

**Files:**
- Modify: `paperforge/plugin/main.js`

After each heavy operation completes (build, rebuild, sync), call a snapshot refresher.

- [ ] **Step 1: Add snapshot refresh function**

```javascript
_refreshSnapshots(vp) {
    const py = memoryState.getCachedPython(vp, this.plugin.settings);
    const { execFileSync } = require('node:child_process');
    const args = [...py.extraArgs, '-m', 'paperforge', '--vault', vp, 'runtime-health', '--json'];
    try {
        execFileSync(py.path, args, { cwd: vp, timeout: 30000, windowsHide: true, encoding: 'utf-8' });
        // runtime-health already writes all three snapshots as side effect
    } catch { /* best effort */ }
    // Now re-read fresh snapshots
    this._memoryStatusText = memoryState.getMemoryStatusText(vp);
    this._embedStatusText = memoryState.getVectorStatusText(vp);
}
```

- [ ] **Step 2: Call after build complete**

In `this._embedProcess.on('close', ...)` handler, call `this._refreshSnapshots(vp)`.

- [ ] **Step 3: Call after memory rebuild**

In the rebuild button handler, call `this._refreshSnapshots(vp)` after `execFile` completes.

- [ ] **Step 4: Call after sync**

In the sync button handler, call `this._refreshSnapshots(vp)` after sync completes.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js
git commit -m "feat: refresh runtime snapshots after heavy operations complete"
```

---

### Task 5: End-to-end smoke test in test1 vault

**Files:**
- No production files

- [ ] **Step 1: Deploy latest plugin + Python code**

```bash
cp paperforge/plugin/main.js "D:\L\Med\test1\.obsidian\plugins\paperforge\main.js"
cp paperforge/plugin/src/memory-state.js "D:\L\Med\test1\.obsidian\plugins\paperforge\src\memory-state.js"
pip install -e .
```

- [ ] **Step 2: Generate initial snapshots**

```bash
python -m paperforge --vault "D:\L\Med\test1" runtime-health --json
```
Expected: three snapshot files created in `System/PaperForge/indexes/`.

- [ ] **Step 3: Verify Settings → Features opens without Python subprocess**

Open Obsidian DevTools (Ctrl+Shift+I), check Console.
No `exec`, `spawn`, or `execFileSync` calls should appear for status checks.
Memory status should show instantly.
Vector deps check should show correct result.

- [ ] **Step 4: Verify Build button still works**

Click Build → progress bar shows → completes with Notice.
After completion, snapshots should be refreshed.

- [ ] **Step 5: Verify Dashboard System Status**

Dashboard should show correct memory layer status from snapshot.

- [ ] **Step 6: Verify refresh after operations**

Rebuild → snapshots update → status row reflects new state.
Sync → same.

- [ ] **Step 7: Commit any final fixes**

```bash
git add paperforge/plugin/main.js
git commit -m "fix: deploy JS-first state changes from smoke test"
```

---

## Summary

| Task | Files | Description |
| ---- | ----- | ----------- |
| 1 | `state_snapshot.py` (new), `status.py`, `embed.py`, `runtime_health.py` | Python writes canonical snapshot files |
| 2 | `src/memory-state.js` (new), `tests/memory-state.test.mjs` | JS reads snapshots only; no SQL, no inference |
| 3 | `main.js` | Replace exec calls with snapshot reads + `_callPython()` wrapper |
| 4 | `main.js` | Refresh snapshots after heavy ops complete |
| 5 | test1 vault | End-to-end smoke test |

### Dependency order

Task 1 → Task 2 → Task 3 → Task 4 → Task 5

### Key architectural guarantees

1. Python is the ONLY source of truth for all judgment (deps, health, counts)
2. JS does zero inference from raw files
3. No SQLite reads in JS (no dependency on native Node modules)
4. `buildSnapshot()` is injectable — tests can mock the file reader
5. `_callPython()` is the single spawn path — eliminates 20+ duplicate Python resolutions
