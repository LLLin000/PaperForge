---
phase: ANN10
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - paperforge/plugin/src/canvas/context.js
  - paperforge/plugin/src/canvas/annotations.js
  - paperforge/plugin/src/canvas/controller.js
  - paperforge/plugin/src/canvas/render.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-context.test.mjs
  - paperforge/plugin/tests/canvas-controller.test.mjs
  - paperforge/plugin/tests/canvas-render.test.mjs
requirements:
  - CANVAS-02
requirements_addressed:
  - CANVAS-02
autonomous: true
decision_coverage:
  - D-06
  - D-08
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
  - D-16
  - D-17
  - D-18
  - D-20
  - D-21
  - D-22
  - D-23
  - D-24
  - D-27
  - D-28
must_haves:
  truths:
    - "CANVAS-02: Canvas annotation loading reuses existing v0.2 annotation contracts and introduces no direct SQLite, Zotero, or new Python subprocess API."
    - "The canvas session owns an explicit paperKey and does not rely on live global _currentPaperKey drift after opening."
    - "Phase ANN10 shell modules do not implement annotation cards, source anchors, bidirectional navigation, connector lines, full visual polish, or native PDF overlay reliability."
    - "Context decision coverage for this plan is explicit: D-06 D-08 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-20 D-21 D-22 D-23 D-24 D-27 D-28."
  artifacts:
    - path: "paperforge/plugin/src/canvas/context.js"
      provides: "Explicit canvas context resolution"
    - path: "paperforge/plugin/src/canvas/annotations.js"
      provides: "Thin wrapper over v0.2 annotation loader/state contracts"
    - path: "paperforge/plugin/src/canvas/controller.js"
      provides: "Canvas session lifecycle, fixed paper identity, refresh, stale guard, teardown"
    - path: "paperforge/plugin/src/canvas/render.js"
      provides: "Phase ANN10 shell/loading/empty/error/unsupported DOM rendering"
    - path: "paperforge/plugin/src/canvas/index.js"
      provides: "Narrow CommonJS canvas module export surface"
  key_links:
    - from: "paperforge/plugin/src/canvas/annotations.js"
      to: "paperforge/plugin/src/testable.js"
      via: "loadAnnotationsForPaper, makeAnnotationState, ANNOTATION_LOAD_STATES"
      pattern: "thin wrapper; no new CLI contract"
    - from: "paperforge/plugin/src/canvas/controller.js"
      to: "paperforge/plugin/src/testable.js"
      via: "stale guard pattern"
      pattern: "createAnnotationLifecycleController and _annotationLoadSeq behavior"
---

<objective>
Create the pure canvas contract modules for Phase ANN10 and cover them with focused Vitest tests.

Purpose: establish the PaperForge Reading Canvas data/session/render foundation before touching Obsidian runtime wiring.
Output: `paperforge/plugin/src/canvas/*` CommonJS modules and helper tests proving explicit paper identity, v0.2 annotation contract reuse, stale-result handling, teardown, shell states, and read-only safety.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/ANN10/annotation-10-CONTEXT.md
@.planning/phases/ANN10/ANN10-RESEARCH.md
@.planning/research/SUMMARY.md
@.planning/research/ARCHITECTURE.md
@.planning/research/PITFALLS.md
@.planning/research/STACK.md
@paperforge/plugin/package.json
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/annotation-bridge.test.mjs
@paperforge/plugin/tests/annotation-main-runtime.test.mjs
</context>

<source_audit>
GOAL: Covers the Phase ANN10 data contract foundation: context, annotation wrapper, controller, render shell, and export seams.
REQ: CANVAS-02 is covered directly by reusing v0.2 annotation contracts and forbidding new DB/API/subprocess paths.
RESEARCH: Implements the recommended module seams under `paperforge/plugin/src/canvas/` and keeps `main.js` untouched until Plan 02.
CONTEXT: Implements D-06, D-08, D-11 through D-18, D-20 through D-24, D-27, and D-28. Entry points and runtime registration decisions D-01 through D-05, D-07, D-09, D-10, D-19, D-25, and D-26 are completed in Plan 02.
</source_audit>

<tasks>

<task type="auto">
  <name>Task 1: Add canvas context and annotation contract modules</name>
  <files>paperforge/plugin/src/canvas/context.js, paperforge/plugin/src/canvas/annotations.js, paperforge/plugin/src/canvas/index.js, paperforge/plugin/tests/canvas-context.test.mjs</files>
  <action>Create `context.js` with pure helpers such as `buildCanvasContextFromEntry(entry)` and `buildMissingCanvasContext(reason)` or equivalent names. The entry path must treat `entry.key` as authoritative and return explicit `{ ok, paperKey, entry, reason }` objects. Create `annotations.js` with a thin injected wrapper around existing v0.2 `loadAnnotationsForPaper()` and `makeAnnotationState()` contracts; the wrapper must accept a `paperKey`, injected loader/dependencies, and return existing annotation load states without constructing new CLI commands. Export both through `index.js`. Tests must cover valid entry, missing paper, invalid entry, missing key, friendly reasons, no mutation of entry input, and that annotation loading delegates to the injected v0.2 loader with the explicit paperKey.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; npm.cmd test -- canvas-context.test.mjs annotation-bridge.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Context resolution is explicit and fail-closed; annotation wrapper delegates to v0.2 contracts only; no direct DB, Zotero, or new subprocess API appears in `src/canvas/*`.</acceptance_criteria>
  <done>`context.js`, `annotations.js`, `index.js`, and canvas context tests exist and pass with the annotation bridge test.</done>
</task>

<task type="auto">
  <name>Task 2: Add canvas controller lifecycle and shell renderer</name>
  <files>paperforge/plugin/src/canvas/controller.js, paperforge/plugin/src/canvas/render.js, paperforge/plugin/src/canvas/index.js, paperforge/plugin/tests/canvas-controller.test.mjs, paperforge/plugin/tests/canvas-render.test.mjs</files>
  <action>Create `controller.js` with a canvas session controller that stores a fixed `paperKey`, coordinates initial load/refresh through the annotation wrapper, discards stale async results with a monotonic sequence, exposes teardown, and never reads live global `_currentPaperKey`. Create `render.js` with shell-only DOM helpers for Phase ANN10 states: shell, paper identity, loading, empty, missing-paper, missing-db, CLI-error/invalid-json, missing-source, unsupported, and stale state. Rendering must use `textContent`, `setText`, or safe Obsidian DOM helpers only. It must not render edit/delete/create/save/import/apply/write-back/database/evidence/concept-card controls. Update `index.js` exports. Tests must cover stale discard, refresh, teardown, fixed paperKey, shell states, safe text rendering, and forbidden-control absence.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; npm.cmd test -- canvas-controller.test.mjs canvas-render.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Controller owns paper identity and stale guard; renderer covers shell states only; no Phase 11+ card/anchor/connector work is introduced; read-only safety is tested.</acceptance_criteria>
  <done>`controller.js`, `render.js`, export updates, and focused tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Paper panel entry -> canvas context | Paper identity enters the canvas from existing plugin state and must be explicit. |
| v0.2 annotation loader -> canvas controller | Annotation state is an external contract to the canvas and must not be reimplemented. |
| Annotation text -> canvas DOM | User/imported text reaches DOM and must be inserted safely. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ANN10-01-S | Spoofing | Canvas paper identity | mitigate | Require explicit `paperKey`; missing/invalid entry returns fail-closed context with reason. |
| T-ANN10-01-T | Tampering | Annotation state | mitigate | Delegate to v0.2 loader/state contracts; do not mutate rows or construct new DB/API calls. |
| T-ANN10-01-R | Repudiation | Refresh/stale behavior | accept | No audit log required for read-only display; tests document lifecycle behavior. |
| T-ANN10-01-I | Information Disclosure | DOM rendering | mitigate | Use text-safe insertion and avoid raw JSON, raw stack traces, or shell output. |
| T-ANN10-01-D | Denial of Service | Async refresh | mitigate | Use stale guards and teardown to prevent obsolete renders. |
| T-ANN10-01-E | Elevation of Privilege | Annotation storage | mitigate | No edit/write/import/apply/write-back controls; no persistent writes. |

</threat_model>

<verification>

Run from the repository root:

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-render.test.mjs annotation-bridge.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs
Pop-Location
```

</verification>

<success_criteria>

- `paperforge/plugin/src/canvas/` exists with `context.js`, `annotations.js`, `controller.js`, `render.js`, and `index.js`.
- Context helpers return explicit fail-closed `{ ok, paperKey, entry, reason }`-style results.
- Annotation helpers wrap v0.2 annotation contracts and introduce no new database, Zotero, or subprocess contract.
- Controller tests prove fixed paper identity, stale discard, refresh, and teardown.
- Render tests prove shell states, safe text rendering, and absence of forbidden write controls.
- No cards, anchors, connectors, persistent layout, native PDF overlay claims, or editing flows are implemented.

</success_criteria>
