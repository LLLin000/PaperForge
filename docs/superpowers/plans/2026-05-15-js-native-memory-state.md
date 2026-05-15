# JS-Native Memory State — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all Python subprocess calls for memory layer state reads with direct JS file/SQLite reads. Python retained only for heavy operations (embed build, OCR, sync, repair).

**Architecture:** New `memory-state.js` module provides all status/health/deps reads via JS-native file I/O + SQLite. main.js consumes this module instead of spawning Python for status checks. Single `_callPython()` wrapper handles remaining heavy operations.

**Tech Stack:** Node.js `fs`, `better-sqlite3` (or `sql.js` pure-JS fallback), Vitest, Obsidian Plugin API.

**Spec:** `docs/superpowers/specs/2026-05-15-js-native-memory-state.md`

**Audit:** `docs/superpowers/specs/2026-05-15-memory-layer-ux-audit.md`

---

## File Structure Map

```text
Create:
  paperforge/plugin/src/memory-state.js          — all JS-native state reads
  paperforge/plugin/tests/memory-state.test.mjs  — Vitest tests

Modify:
  paperforge/plugin/main.js                      — remove exec() calls, use memory-state
  paperforge/plugin/src/testable.js              — extract pure helpers for testing
  paperforge/plugin/package.json                 — add SQLite dependency
```

---

### Task 1: Add SQLite dependency + verify it works in Obsidian Electron

**Files:**
- Modify: `paperforge/plugin/package.json`

- [ ] **Step 1: Install dependency**

```bash
npm install --save sql.js
```

Choose `sql.js` (pure JS WASM) over `better-sqlite3` (needs native rebuild for Electron).
`sql.js` is fully portable, no platform-specific compilation needed.

- [ ] **Step 2: Verify import works in Node**

Create a quick test script:

```javascript
// quick-test.mjs
import initSqlJs from 'sql.js';
const SQL = await initSqlJs();
const db = new SQL.Database();
db.run("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)");
db.run("INSERT INTO test VALUES (1, 'hello')");
const result = db.exec("SELECT * FROM test");
console.log(result[0].values[0]); // [1, 'hello']
db.close();
```

Run:
```bash
node quick-test.mjs
```
Expected: `[1, 'hello']`

- [ ] **Step 3: Verify sql.js works in Obsidian plugin context**

Add to `main.js` onload a one-liner test: `require('sql.js')`. Then `node --check main.js`.

Add `sql.js` to `package.json` `"dependencies"` (NOT `devDependencies`):
```json
{
  "dependencies": {
    "sql.js": "^1.11.0"
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/plugin/package.json paperforge/plugin/package-lock.json
git commit -m "deps: add sql.js for JS-native SQLite reads"
```

---

### Task 2: Create `memory-state.js` — JS-native state reader module

**Files:**
- Create: `paperforge/plugin/src/memory-state.js`
- Test: `paperforge/plugin/tests/memory-state.test.mjs`

This module replaces ALL Python exec calls for state reads. No subprocess. Pure JS.

- [ ] **Step 1: Write the failing tests**

```javascript
// paperforge/plugin/tests/memory-state.test.mjs
import { describe, expect, it, beforeAll } from 'vitest';
import fs from 'fs';
import path from 'path';

// We test pure functions that don't need Obsidian API
import {
  resolvePythonPath,
  resolveVaultPaths,
  readJSONFile,
  readJSONLLines,
  checkVectorDeps,
  formatMemoryStatus,
  deriveRuntimeHealth,
} from '../src/memory-state.js';

describe('resolvePythonPath', () => {
  it('detects .paperforge-test-venv when present', () => {
    // Use a temp dir with a mock venv
    // ...
  });

  it('falls back to system python when no venv found', () => {
    // ...
  });
});

describe('resolveVaultPaths', () => {
  it('resolves paperforge directories from vault root', () => {
    const paths = resolveVaultPaths('/fake/vault');
    expect(paths.systemDir).toBe(path.join('/fake/vault', 'System', 'PaperForge'));
    expect(paths.indexesDir).toBe(path.join('/fake/vault', 'System', 'PaperForge', 'indexes'));
  });
});

describe('readJSONFile', () => {
  it('returns parsed JSON for valid file', () => {
    // ...
  });

  it('returns null for non-existent file', () => {
    expect(readJSONFile('/nonexistent/file.json')).toBeNull();
  });
});

describe('checkVectorDeps', () => {
  it('reports installed when packages found in venv site-packages', () => {
    // Mock fs.existsSync
    // ...
  });
});

describe('formatMemoryStatus', () => {
  it('formats fresh status with paper count', () => {
    expect(formatMemoryStatus(150, true)).toBe('Papers: 150 | fresh');
  });

  it('formats stale status', () => {
    expect(formatMemoryStatus(50, false)).toBe('Papers: 50 | stale');
  });
});

describe('deriveRuntimeHealth', () => {
  it('returns ok when all layers healthy', () => {
    const health = deriveRuntimeHealth({
      memory: { paperCount: 150, freshness: 'fresh' },
      embed: { dbExists: true, chunkCount: 747 },
      vectorEnabled: true,
      depsInstalled: true,
      buildState: { status: 'idle' },
    });
    expect(health.summary.status).toBe('ok');
    expect(health.summary.safeRead).toBe(true);
  });

  it('returns degraded when memory DB missing', () => {
    const health = deriveRuntimeHealth({
      memory: { paperCount: 0, freshness: 'stale' },
      embed: { dbExists: false, chunkCount: 0 },
      vectorEnabled: true,
      depsInstalled: true,
      buildState: { status: 'idle' },
    });
    expect(health.summary.status).toBe('degraded');
    expect(health.summary.safeRead).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd paperforge/plugin && npm test -- tests/memory-state.test.mjs
```
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

Create `paperforge/plugin/src/memory-state.js` with these exports:

```javascript
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('node:child_process');

// ── Path Resolution ──

function resolveVaultPaths(vaultPath) {
  const systemDir = path.join(vaultPath, 'System', 'PaperForge');
  return {
    vault: vaultPath,
    systemDir,
    indexesDir: path.join(systemDir, 'indexes'),
    logsDir: path.join(systemDir, 'logs'),
    dbPath: path.join(systemDir, 'indexes', 'paperforge.db'),
    vectorStatePath: path.join(systemDir, 'indexes', 'vector-build-state.json'),
    formalLibraryPath: path.join(systemDir, 'indexes', 'formal-library.json'),
    pluginDataPath: path.join(vaultPath, '.obsidian', 'plugins', 'paperforge', 'data.json'),
    pfJsonPath: path.join(vaultPath, 'paperforge.json'),
  };
}

// ── File Readers ──

function readJSONFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch { return null; }
}

function readJSONLLines(filePath, maxLines = 0) {
  try {
    if (!fs.existsSync(filePath)) return [];
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').filter(l => l.trim());
    if (maxLines > 0) return lines.slice(-maxLines);
    return lines;
  } catch { return []; }
}

// ── Python Path Resolution ──

function resolvePythonPath(vaultPath, settings = {}) {
  if (settings.python_path && settings.python_path.trim()) {
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
  for (const c of [{ path: 'python', extraArgs: [] }, { path: 'python3', extraArgs: [] }]) {
    try {
      const out = execFileSync(c.path, [...c.extraArgs, '--version'], {
        encoding: 'utf-8', timeout: 5000, windowsHide: true,
      });
      if (out && out.toLowerCase().includes('python')) {
        return { path: c.path, source: 'auto-detected', extraArgs: c.extraArgs };
      }
    } catch {}
  }
  return { path: 'python', source: 'auto-detected', extraArgs: [] };
}

let _cachedPython = null;
function getCachedPython(vaultPath, settings) {
  if (!_cachedPython) {
    _cachedPython = resolvePythonPath(vaultPath, settings);
  }
  return _cachedPython;
}

// ── Memory Status (SQLite via sql.js) ──

let _SQL = null;
async function _getSQL() {
  if (!_SQL) {
    const initSqlJs = require('sql.js');
    _SQL = await initSqlJs();
  }
  return _SQL;
}

function _readSQLiteDB(dbPath) {
  try {
    if (!fs.existsSync(dbPath)) return null;
    const buffer = fs.readFileSync(dbPath);
    return new Uint8Array(buffer);
  } catch { return null; }
}

function getMemoryStatusSync(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  const dbBuffer = _readSQLiteDB(paths.dbPath);
  if (!dbBuffer) {
    return { paperCount: 0, freshness: 'unavailable', lastBuild: '', needsRebuild: true };
  }
  // For sync reads, use a simpler approach: read formal-library.json
  const formalLib = readJSONFile(paths.formalLibraryPath);
  if (formalLib) {
    const items = formalLib.items || formalLib;
    const count = Array.isArray(items) ? items.length : Object.keys(items).length;
    const generatedAt = formalLib.generated_at || '';
    return { paperCount: count, freshness: generatedAt ? 'fresh' : 'stale', lastBuild: generatedAt, needsRebuild: false };
  }
  return { paperCount: 0, freshness: 'unavailable', lastBuild: '', needsRebuild: true };
}

async function getMemoryStatus(vaultPath) {
  // Async version that reads SQLite for more detail
  const paths = resolveVaultPaths(vaultPath);
  const dbBuffer = _readSQLiteDB(paths.dbPath);
  if (!dbBuffer) {
    return getMemoryStatusSync(vaultPath);
  }
  try {
    const SQL = await _getSQL();
    const db = new SQL.Database(dbBuffer);
    const paperResult = db.exec("SELECT COUNT(*) as count FROM papers");
    const metaResult = db.exec("SELECT value FROM meta WHERE key='last_full_build_at'");
    const schemaResult = db.exec("SELECT value FROM meta WHERE key='schema_version'");
    db.close();
    const count = paperResult[0]?.values[0]?.[0] || 0;
    const lastBuild = metaResult[0]?.values[0]?.[0] || '';
    const schemaVer = schemaResult[0]?.values[0]?.[0] || '0';
    return {
      paperCount: count,
      freshness: lastBuild ? 'fresh' : 'stale',
      lastBuild,
      schemaVersion: parseInt(schemaVer, 10) || 0,
      needsRebuild: count === 0,
    };
  } catch {
    return getMemoryStatusSync(vaultPath);
  }
}

// ── Embed Status ──

function getEmbedStatus(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  const buildState = readJSONFile(paths.vectorStatePath) || {
    status: 'idle', current: 0, total: 0, paper_id: '',
    last_update: '', started_at: '', finished_at: '',
    resume_supported: true, mode: 'local', model: 'BAAI/bge-small-en-v1.5',
    message: '', pid: 0,
  };
  const pluginData = readJSONFile(paths.pluginDataPath) || {};
  const features = pluginData.features || {};
  const vectorEnabled = !!features.vector_db;
  if (!vectorEnabled) {
    return { dbExists: false, chunkCount: 0, model: 'BAAI/bge-small-en-v1.5', mode: 'local', buildState };
  }
  const mode = pluginData.vector_db_mode || 'local';
  const model = mode === 'api'
    ? (pluginData.vector_db_api_model || 'text-embedding-3-small')
    : (pluginData.vector_db_model || 'BAAI/bge-small-en-v1.5');
  const chromaDBPath = path.join(paths.indexesDir, 'vectors', 'chroma.sqlite3');
  const dbExists = fs.existsSync(chromaDBPath);
  let chunkCount = 0;
  if (dbExists) {
    try {
      const buffer = fs.readFileSync(chromaDBPath);
      const chromaBuffer = new Uint8Array(buffer);
      // sql.js can read ChromaDB's internal sqlite3
      // For now, approximate: check file size > 0
      chunkCount = chromaBuffer.length > 1024 ? 1 : 0;
    } catch { chunkCount = 0; }
  }
  return { dbExists, chunkCount, model, mode, buildState };
}

// ── Dependency Check ──

function _findSitePackages(pythonPath) {
  const dir = path.dirname(pythonPath);
  const candidates = [
    path.join(dir, 'Lib', 'site-packages'),
    path.join(dir, '..', 'Lib', 'site-packages'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

function checkVectorDeps(vaultPath, settings) {
  const py = getCachedPython(vaultPath, settings);
  const sp = _findSitePackages(py.path);
  const missing = [];
  if (sp) {
    if (!fs.existsSync(path.join(sp, 'chromadb'))) missing.push('chromadb');
    if (!fs.existsSync(path.join(sp, 'sentence_transformers'))) missing.push('sentence-transformers');
  } else {
    missing.push('chromadb', 'sentence-transformers');
  }
  return { installed: missing.length === 0, missing };
}

// ── Formatting ──

function formatMemoryStatus(paperCount, freshness) {
  if (paperCount === 0) return 'DB not found. Run paperforge memory build.';
  const freshLabel = freshness === 'fresh' ? 'fresh' : 'stale';
  return `Papers: ${paperCount} | ${freshLabel}`;
}

function formatEmbedStatus(chunkCount, model, mode) {
  return `Chunks: ${chunkCount} | ${model} | ${mode}`;
}

// ── Runtime Health ──

function deriveRuntimeHealth({ memory, embed, vectorEnabled, depsInstalled, buildState }) {
  const layers = {
    bootstrap: { status: 'ok', evidence: [], nextAction: '', repairCommand: '' },
    read: { status: 'ok', evidence: [], nextAction: '', repairCommand: '' },
    write: { status: 'ok', evidence: [], nextAction: '', repairCommand: '' },
    index: { status: 'ok', evidence: [], nextAction: '', repairCommand: '' },
    vector: { status: 'ok', evidence: [], nextAction: '', repairCommand: '' },
  };

  // Read layer
  if (memory.paperCount === 0) {
    layers.read = { status: 'blocked', evidence: ['No papers in memory DB'],
      nextAction: 'Run paperforge memory build', repairCommand: 'paperforge memory build' };
  }

  // Index layer
  if (memory.paperCount === 0 || memory.freshness === 'unavailable') {
    layers.index = { status: 'blocked', evidence: ['Memory DB unavailable'],
      nextAction: 'Run paperforge memory build', repairCommand: 'paperforge memory build' };
  }
  if (memory.freshness === 'stale') {
    layers.index = { status: 'degraded', evidence: ['Memory DB may be stale'],
      nextAction: 'Run paperforge memory build', repairCommand: 'paperforge memory build' };
  }

  // Vector layer
  if (vectorEnabled) {
    if (!depsInstalled) {
      layers.vector = { status: 'blocked', evidence: ['Vector deps not installed'],
        nextAction: 'Install: pip install paperforge[vector]', repairCommand: 'pip install paperforge[vector]' };
    } else if (!embed.dbExists) {
      layers.vector = { status: 'degraded', evidence: ['Vector DB not built'],
        nextAction: 'Run embed build', repairCommand: 'paperforge embed build --resume' };
    } else if (buildState.status === 'running') {
      layers.vector = { status: 'degraded', evidence: ['Vector build in progress'],
        nextAction: 'Wait for build', repairCommand: 'paperforge embed status --json' };
    } else if (buildState.status === 'failed') {
      layers.vector = { status: 'blocked', evidence: ['Last build failed'],
        nextAction: 'Rebuild vectors', repairCommand: 'paperforge embed build --resume' };
    }
  } else {
    layers.vector = { status: 'ok', evidence: ['Vector DB disabled by user'] };
  }

  // Summary
  const blocked = Object.values(layers).some(l => l.status === 'blocked');
  const degraded = Object.values(layers).some(l => l.status === 'degraded');
  const status = blocked ? 'blocked' : degraded ? 'degraded' : 'ok';

  return {
    summary: {
      status,
      reason: status === 'ok' ? 'All systems operational' : `${status} — some layers need attention`,
      safeRead: layers.read.status === 'ok',
      safeWrite: layers.write.status === 'ok',
      safeBuild: layers.index.status === 'ok',
      safeVector: layers.vector.status === 'ok',
    },
    layers,
    capabilities: {
      paperContext: layers.read.status === 'ok',
      readingLogWrite: layers.write.status === 'ok',
      projectLogWrite: layers.write.status === 'ok',
      ftsSearch: layers.read.status === 'ok',
      vectorRetrieve: layers.vector.status === 'ok',
    },
  };
}

module.exports = {
  resolveVaultPaths,
  readJSONFile,
  readJSONLLines,
  resolvePythonPath,
  getCachedPython,
  getMemoryStatus,
  getMemoryStatusSync,
  getEmbedStatus,
  checkVectorDeps,
  formatMemoryStatus,
  formatEmbedStatus,
  deriveRuntimeHealth,
};
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd paperforge/plugin && npm test -- tests/memory-state.test.mjs
```
Expected: PASS (at least pure-function tests pass)

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/memory-state.js paperforge/plugin/tests/memory-state.test.mjs
git commit -m "feat: add JS-native memory state reader module"
```

---

### Task 3: Wire main.js to use memory-state.js (remove Python exec calls)

**Files:**
- Modify: `paperforge/plugin/main.js`

Replace these methods and call sites:

- [ ] **Step 1: Replace `_execMemoryStatus()` with `getMemoryStatusSync()`**

In `_renderMemoryStatus` (line ~2958), replace:
```javascript
if (this._memoryStatusText !== null) {
    this._renderMemoryStatusText(statusRow, this._memoryStatusText, this._lastSyncTime);
} else if (pyResult.path) {
    this._renderMemoryStatusText(statusRow, 'Checking...', this._lastSyncTime);
    this._execMemoryStatus(pyResult.path, vp, (text) => {
        this._memoryStatusText = text;
        this._renderMemoryStatusText(statusRow, text, this._lastSyncTime);
    });
}
```

With:
```javascript
if (this._memoryStatusText !== null) {
    this._renderMemoryStatusText(statusRow, this._memoryStatusText, this._lastSyncTime);
} else {
    const mem = memoryState.getMemoryStatusSync(vp);
    this._memoryStatusText = memoryState.formatMemoryStatus(mem.paperCount, mem.freshness);
    this._lastSyncTime = mem.lastBuild || 'Never';
    this._renderMemoryStatusText(statusRow, this._memoryStatusText, this._lastSyncTime);
}
```

- [ ] **Step 2: Replace `_execEmbedStatus()` with `memoryState.getEmbedStatus()`**

In `_renderVectorReady`, replace the async status fetch with sync:

```javascript
const embedStatus = memoryState.getEmbedStatus(vp);
this._embedStatusText = memoryState.formatEmbedStatus(embedStatus.chunkCount, embedStatus.model, embedStatus.mode);
```

- [ ] **Step 3: Replace dep check exec with `memoryState.checkVectorDeps()`**

In `_renderVectorSection` line ~3061, replace:
```javascript
exec(`"${pyResult.path}" -c "import chromadb, sentence_transformers; print('ok')"`, ...)
```

With:
```javascript
const deps = memoryState.checkVectorDeps(vp, this.plugin.settings);
this._vectorDepsOk = deps.installed;
if (deps.installed) {
    // proceed to embed status
} else {
    this.display();
}
```

- [ ] **Step 4: Replace rehydrate exec with `memoryState.getEmbedStatus()`**

Remove the rehydrate `exec()` call block, read `buildState` from `memoryState.getEmbedStatus(vp).buildState` instead.

- [ ] **Step 5: Replace Dashboard runtime-health `execFileSync` with `memoryState.deriveRuntimeHealth()`**

At line ~1493, replace the `execFileSync` call with:
```javascript
const rh = memoryState.deriveRuntimeHealth({
    memory: memoryState.getMemoryStatusSync(vp2),
    embed: memoryState.getEmbedStatus(vp2),
    vectorEnabled: plugin?.settings?.features?.vector_db || false,
    depsInstalled: memoryState.checkVectorDeps(vp2, plugin?.settings).installed,
    buildState: memoryState.getEmbedStatus(vp2).buildState,
});
memOk = rh.summary.status === 'ok';
memDetail = rh.summary.reason;
```

- [ ] **Step 6: Keep `_callPython(cmd, opts)` for heavy operations**

Consolidate spawn/exec for build, stop, sync into a single wrapper:

```javascript
_callPython(command, { stream, env, onData, onClose }) {
    const py = memoryState.getCachedPython(
        this.app.vault.adapter.basePath,
        this.plugin.settings
    );
    const args = [...py.extraArgs, '-m', 'paperforge', '--vault', this.app.vault.adapter.basePath, ...command];
    if (stream) {
        const child = spawn(py.path, args, { cwd: this.app.vault.adapter.basePath, env, windowsHide: true });
        if (onData) child.stdout.on('data', onData);
        child.on('close', onClose);
        return child;
    }
    // async exec
    execFile(py.path, args, { cwd: this.app.vault.adapter.basePath, timeout: 30000 },
        (err, stdout, stderr) => {
            onClose(err ? 1 : 0, stdout, stderr);
        });
    return null;
}
```

- [ ] **Step 7: Verify**

Run:
```bash
node --check paperforge/plugin/main.js
```
Expected: no errors

- [ ] **Step 8: Commit**

```bash
git add paperforge/plugin/main.js
git commit -m "refactor: replace Python exec calls with JS-native memory-state reads"
```

---

### Task 4: Extract remaining pure helpers to testable.js

**Files:**
- Modify: `paperforge/plugin/src/testable.js`

- [ ] **Step 1: Add pure helper wrappers**

Add factory wrappers for testability:

```javascript
function createMemoryState(mockFS) {
    const fs = mockFS || require('fs');
    // Re-implement memory-state functions using the provided fs mock
    // This allows Vitest to test logic without real filesystem
}
```

- [ ] **Step 2: Add test for the factory**

```javascript
// tests/memory-state.test.mjs
describe('createMemoryState with mock FS', () => {
    it('returns degraded when formal-library.json missing', () => {
        const mockFS = {
            existsSync: (p) => false,
            readFileSync: (p) => { throw new Error('ENOENT'); },
        };
        const state = createMemoryState(mockFS);
        const rh = state.deriveRuntimeHealth(...);
        expect(rh.summary.status).toBe('degraded');
    });
});
```

- [ ] **Step 3: Run tests**

Run:
```bash
cd paperforge/plugin && npm test -- tests/memory-state.test.mjs
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add paperforge/plugin/src/testable.js paperforge/plugin/tests/memory-state.test.mjs
git commit -m "test: add memory-state factory for Vitest mocking"
```

---

### Task 5: End-to-end smoke test in test1 vault

**Files:**
- No production files

- [ ] **Step 1: Deploy latest plugin to test1**

```bash
cp paperforge/plugin/main.js "D:\L\Med\test1\.obsidian\plugins\paperforge\main.js"
cp paperforge/plugin/src/memory-state.js "D:\L\Med\test1\.obsidian\plugins\paperforge\src\memory-state.js"
```

- [ ] **Step 2: Verify Settings → Features opens without Python subprocess**

Open Obsidian DevTools (Ctrl+Shift+I), check Network/Console tabs.
No `exec` or `spawn` calls should appear for status checks.

- [ ] **Step 3: Verify Memory Layer shows status instantly**

Expected: "Papers: 150 | fresh" without "Checking..." flash.

- [ ] **Step 4: Verify Vector DB section shows correctly**

Expected: deps check passes, embed status shows chunk count, no "Dependencies not installed".

- [ ] **Step 5: Verify Build button still works**

Click Build → progress bar shows → completes with Notice.

- [ ] **Step 6: Verify Dashboard System Status**

Expected: Memory Layer row shows correct status.

- [ ] **Step 7: Commit any final fixes**

```bash
git add paperforge/plugin/main.js
git commit -m "fix: deploy JS-native state changes from smoke test"
```

---

## Summary

| Task | Files                         | Description                                          |
| ---- | ----------------------------- | ---------------------------------------------------- |
| 1    | `package.json`                  | Add sql.js dependency                                |
| 2    | `src/memory-state.js` (new)     | JS-native state reads for memory/embed/deps/health   |
| 3    | `main.js`                       | Replace all Python exec for state reads              |
| 4    | `src/testable.js`               | Extract pure helpers for mocking                     |
| 5    | test1 vault                   | End-to-end smoke test                                |

### Dependency order

Task 1 → Task 2 → Task 3 → Task 4 → Task 5

Tasks 1-2 can be done together. Task 3 is the main integration. Task 4-5 verify.
