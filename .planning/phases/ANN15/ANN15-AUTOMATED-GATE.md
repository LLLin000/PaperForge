# ANN15 Automated Gate Evidence

**Phase:** ANN15 — Canvas Verification Gate and Live Harness Record
**Gate type:** Hard focused automated gate (D-01, D-03)
**Evidence date:** 2026-07-08
**Executor:** OpenCode agent (ANN15-01 plan)

---

## Hard Gate Commands (Minimum Locked Slice)

This is the canonical minimum focused command slice per D-05 through D-08. These commands constitute the ANN15 hard gate. Additional commands may be appended below this list but may not replace or omit it.

```powershell
Push-Location paperforge/plugin
# ── D-05: Syntax gate ──
node --check main.js
# ── D-06: Canvas module syntax gate ──
node --check src/canvas/context.js
node --check src/canvas/annotations.js
node --check src/canvas/controller.js
node --check src/canvas/view-model.js
node --check src/canvas/layout.js
node --check src/canvas/surface.js
node --check src/canvas/anchors.js
node --check src/canvas/navigation.js
node --check src/canvas/connectors.js
node --check src/canvas/render.js
node --check src/canvas/index.js
# ── D-07: v0.3 canvas Vitest slice ──
npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-source-anchor.test.mjs canvas-navigation.test.mjs canvas-connectors.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs
# ── D-08: v0.2 fallback preservation Vitest slice ──
npm.cmd test -- annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs annotation-overlay.test.mjs
Pop-Location
```

---

## Run Evidence

All commands executed from `paperforge/plugin` working directory.

### D-05: Syntax gate — `main.js`

| Field | Value |
|-------|-------|
| Command | `node --check main.js` |
| Result | **PASS** |
| Output | (no output — zero syntax errors) |
| Evidence | `node --check` exit code 0 |
| Timestamp | 2026-07-08 08:58 |

### D-06: Canvas module syntax gate (11 files)

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/context.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/annotations.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/controller.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/view-model.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/layout.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/surface.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/anchors.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/navigation.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/connectors.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/render.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

| Field | Value |
|-------|-------|
| Command | `node --check src/canvas/index.js` |
| Result | **PASS** |
| Output | (no output) |
| Timestamp | 2026-07-08 08:58 |

### D-07: v0.3 Canvas Vitest slice (10 test files, 571 tests)

| Field | Value |
|-------|-------|
| Command | `npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-source-anchor.test.mjs canvas-navigation.test.mjs canvas-connectors.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs` |
| Result | **PASS** |
| Test file summary | `canvas-navigation.test.mjs` — 28 tests ✓ |
| | `canvas-controller.test.mjs` — 20 tests ✓ |
| | `canvas-context.test.mjs` — 27 tests ✓ |
| | `canvas-connectors.test.mjs` — 51 tests ✓ |
| | `canvas-layout.test.mjs` — 33 tests ✓ |
| | `canvas-source-anchor.test.mjs` — 51 tests ✓ |
| | `canvas-viewmodel.test.mjs` — 93 tests ✓ |
| | `canvas-card-dom.test.mjs` — 57 tests ✓ |
| | `canvas-render.test.mjs` — 120 tests ✓ |
| | `canvas-main-runtime.test.mjs` — 91 tests ✓ |
| Aggregate | **10 files passed, 571 tests passed** |
| Duration | 23.10s |
| Timestamp | 2026-07-08 08:58:52 |

### D-08: v0.2 Annotation fallback Vitest slice (4 test files, 190 tests)

| Field | Value |
|-------|-------|
| Command | `npm.cmd test -- annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs annotation-overlay.test.mjs` |
| Result | **PASS** |
| Test file summary | `annotation-navigation.test.mjs` — 47 tests ✓ |
| | `annotation-overlay.test.mjs` — 76 tests ✓ |
| | `annotation-section-dom.test.mjs` — 20 tests ✓ |
| | `annotation-main-runtime.test.mjs` — 47 tests ✓ |
| Aggregate | **4 files passed, 190 tests passed** |
| Duration | 19.32s |
| Timestamp | 2026-07-08 08:58:52 |

### Non-blocking observation: Vitest results.json EBUSY

During concurrent execution of the two Vitest runs, a non-fatal `EBUSY` error was logged from `vitest/dist/chunks/resolveConfig.rBxzbVsl.js` when both instances attempted to write the results cache simultaneously. This is a known Vitest race condition (results.json is shared across the workspace cache):

| Field | Value |
|-------|-------|
| Error | `EBUSY: resource busy or locked, open '...node_modules/.vite/vitest/results.json'` |
| Classification | **Environment** — non-fatal, all 761 tests passed |
| Root cause | Vitest concurrent instance cache-write race |
| Blocker? | No — no test was affected, no assertion failed |

---

## Focused Failures

**None.** All 24 hard-gate commands (12 syntax checks, 10 canvas test files across 571 tests, 4 annotation test files across 190 tests) passed with zero failures or unexpected errors.

The EBUSY cache-race noted above is classified as an environment quirk, not a focused failure. Per D-04, no focused-slice failure exists to block ANN15.

---

## Baseline Bucket

**No optional broader checks were executed.** Only the minimum locked focused command slice from D-05 through D-08 was run. Per D-02, no baseline-bucket entries are needed.

If future planners choose to run broader plugin or full-repo informational suites, they should record non-ANN15 failures here with command, failure summary, and rationale for why each failure is unrelated to ANN15.

---

## Vocabulary

Per D-22/D-15: This gate uses `PASS`, `FAIL`, `PENDING`, `BASELINE`. All locked commands are `PASS`. No `FAIL`, `PENDING`, or `BASELINE` entries exist in the hard gate.

---

## Decision Trace

| Decision | Implementation |
|----------|---------------|
| D-01 | Hard gate is focused on v0.3 canvas + v0.2 fallback preservation; broader info checks are not part of this gate |
| D-02 | Baseline bucket defined; no entries needed (only minimum locked slice was run) |
| D-03 | Explicit minimum command list locked above; no substitutions or omissions |
| D-04 | No focused-slice failures exist; no blocker to move out of the hard gate |
| D-05 | `node --check main.js` executed **PASS** |
| D-06 | `node --check` for all 11 canvas modules executed — all **PASS** |
| D-07 | 10 v0.3 canvas Vitest files executed — all **PASS** (571/571) |
| D-08 | 4 v0.2 fallback Vitest files executed — all **PASS** (190/190) |
| D-22 | Status vocabulary: `PASS`/`FAIL`/`PENDING`/`BASELINE` — documented and applied |
| D-24 | jsdom passing does not prove live Obsidian behavior — caveat applies (see ANN15-LIVE-HARNESS.md) |
