# Memory Layer UX Architecture Audit

> **Date:** 2026-05-15 | **Scope:** JS ↔ Python bridge + state management + UI rendering

## Issues Found

### #1 State reset on every Settings open (BLOCKER)
- `_vectorDepsOk`, `_memoryStatusText`, `_embedStatusText` all reset to null
- Cause: `PluginSettingTab` constructor recreates all fields on every open
- Fix: persist to `this.plugin.settings._stateCache`

### #2 display() called 3+ times per Settings open
- 1st: initial render, 2nd: deps callback, 3rd: embed status callback
- Fix: batch refreshes with token-based guard

### #3 resolvePythonExecutable() called 20+ times redundantly
- Same path resolved at every call site
- Fix: cache to `this._cachedPython`, resolve once in constructor

### #4 _execMemoryStatus and _execEmbedStatus are duplicate patterns
- Same exec → JSON.parse → format → callback structure
- Fix: extract `_execPaperforgeJSON(cmd, callback)`

### #5 Embed status queried twice with different formats
- `_execEmbedStatus`: formatted string for UI
- Rehydrate: raw JSON for build_state
- Fix: both read from unified `_runtimeState`

### #6 Rehydrate exec has no guard against repeat calls
- Every `_renderVectorReady()` call spawns a new exec
- Fix: add `_rehydrating` flag

### #7 Inconsistent --vault flag position
- `exec()` mode uses correct position; older `execFile` had wrong order
- Fix: centralised arg builder

### #8 Error handling: 6 different patterns
- Silent catch, callback, Notice, console.log, ignore, raw text
- Fix: unified `_handleCLIError(err, context)`

### #9 Missing Python extraArgs in exec() calls
- `exec()` mode doesn't include `extraArgs` from Python resolution
- Fix: centralised call wrapper always includes extraArgs

## Proposed Architecture

### Unified Python Bridge
```javascript
_callPaperforge(cmd, {stream: false}) → Promise<{ok, data, error}>
```
- Caches Python path
- Constructs correct args with --vault, --json, extraArgs
- Handles exec/spawn/execFileSync uniformly
- Reports errors consistently

### Unified Runtime State
```javascript
this._runtimeState = {
  deps: { installed: true/false },
  memory: { count: 150, freshness: 'fresh' },
  embed: { chunks: 747, model: '...', mode: 'api' },
  build: { status: 'idle', current: 0, total: 0 },
}
```

### Display Debouncing
- Token-based: each `display()` call gets a token
- Only the latest token wins
- Prevents 3+ full-page rerenders per Settings open
