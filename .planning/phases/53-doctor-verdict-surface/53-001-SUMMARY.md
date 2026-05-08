---
phase: 53
plan: 001
type: summary
subsystem: plugin-tests
generated: 2026-05-09
metrics:
  duration: ~45min
  files_created: 8
  files_modified: 1
  test_count: 42
  test_files: 3
  test_framework: vitest v2.1.9
requirements: [PLUG-01, PLUG-02, PLUG-03, CI-04]
---

# Phase 53 Plan 001: Plugin Source Extraction & Vitest Tests

**One-liner:** Extracted testable src/ modules (runtime, errors, commands) from main.js, set up Vitest + jsdom infrastructure, and wrote 42 passing plugin-backend integration tests.

## Summary

Extracted three pure-function modules from the monolithic `main.js` into `paperforge/plugin/src/` for testability:

- **runtime.js** — `resolvePythonExecutable(vaultPath, settings)`, `getPluginVersion(app)`, `checkRuntimeVersion(pythonExe, pluginVer, cwd, timeout)`
- **errors.js** — `classifyError(errorCode)`, `buildRuntimeInstallCommand(pythonExe, version, extraArgs)`, `parseRuntimeStatus(err, stdout, stderr)`
- **commands.js** — `ACTIONS` array (6 entries), `buildCommandArgs(action, key, filter)`, `runSubprocess(pythonExe, args, cwd, timeout)`

Used dependency injection (optional last parameter) for `fs`, `child_process` modules to enable testing without `vi.mock()` CJS/ESM interop issues in vitest v2.1.x.

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `paperforge/plugin/src/runtime.js` | ~150 | Python resolution + version check |
| `paperforge/plugin/src/errors.js` | ~100 | Error classification + install command builder |
| `paperforge/plugin/src/commands.js` | ~130 | Action definitions + subprocess dispatch |
| `paperforge/plugin/package.json` | 16 | Vitest deps: vitest, obsidian-test-mocks, jsdom |
| `paperforge/plugin/vitest.config.ts` | 10 | jsdom env, globals, test include pattern |
| `paperforge/plugin/tests/runtime.test.mjs` | 110 | 12 tests (resolvePython 5, getPlugin 3, checkRuntime 4) |
| `paperforge/plugin/tests/errors.test.mjs` | 110 | 15 tests (classify 7, buildCommand 3, parseStatus 5) |
| `paperforge/plugin/tests/commands.test.mjs` | 130 | 15 tests (ACTIONS 6, buildArgs 4, subprocess 5) |

### Files Modified

| File | Change |
|------|--------|
| `paperforge/plugin/main.js` | Added require('./src/...') imports; removed inline ACTIONS + resolvePythonExecutable; refactored _fetchVersion and _syncRuntime |

### CI Workflow

Created `.github/workflows/ci.yml` with Node 20 `plugin-tests` job that runs `npx vitest run` in `paperforge/plugin/`.

## Deviations from Plan

### Rule 2 — Missing critical functionality

1. **Dependency injection for testability** — Added optional last-parameter DI pattern to `resolvePythonExecutable(_fs, _execFileSync)`, `checkRuntimeVersion(_execFile)`, `runSubprocess(_spawn)` to work around vitest v2.1.x CJS/ESM module mocking limitations.

2. **Added obsidian ^1.12 dev dep** — Required by obsidian-test-mocks for type resolution.

3. **Moved test files into paperforge/plugin/tests/** — Vitest v2.1.x cannot reliably resolve test files outside the project root (CJS/ESM boundary issue).

## Test Results

```
Test Files  3 passed (3)
     Tests  42 passed (42)
```
