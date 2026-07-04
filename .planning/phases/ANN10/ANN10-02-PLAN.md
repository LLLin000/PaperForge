---
phase: ANN10
plan: "02"
type: execute
wave: 2
depends_on:
  - ANN10-01
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
  - paperforge/plugin/tests/canvas-section-dom.test.mjs
requirements:
  - CANVAS-01
  - CANVAS-02
requirements_addressed:
  - CANVAS-01
  - CANVAS-02
autonomous: true
decision_coverage:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-05
  - D-06
  - D-07
  - D-08
  - D-09
  - D-10
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
  - D-16
  - D-17
  - D-18
  - D-19
  - D-20
  - D-21
  - D-22
  - D-23
  - D-24
  - D-25
  - D-26
  - D-27
  - D-28
must_haves:
  truths:
    - "CANVAS-01: User can open a PaperForge Reading Canvas for an explicit active paper from the paper panel button and command palette command."
    - "CANVAS-02: Runtime canvas loading delegates to the Plan 01 v0.2 annotation contract wrapper and introduces no new DB/API/subprocess path."
    - "Paper panel opens use the current panel entry.key as authoritative identity; command palette opens use existing active-paper resolution and fail with Notice when unavailable."
    - "An already-open canvas does not auto-switch when active paper changes elsewhere."
    - "Context decision coverage for the phase set is explicit: D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-19 D-20 D-21 D-22 D-23 D-24 D-25 D-26 D-27 D-28."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Reading Canvas ItemView, view type registration, open command, paper panel button, runtime delegation to src/canvas"
    - path: "paperforge/plugin/styles.css"
      provides: "Minimal namespaced shell styling for Phase ANN10 canvas"
    - path: "paperforge/plugin/tests/canvas-main-runtime.test.mjs"
      provides: "View registration, command, explicit paperKey, and module delegation tests"
    - path: "paperforge/plugin/tests/canvas-section-dom.test.mjs"
      provides: "Paper panel button and read-only shell DOM tests"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/canvas/index.js"
      via: "CommonJS require"
      pattern: "runtime uses same helper modules tested in Plan 01"
    - from: "PaperForgeStatusView._renderPaperMode"
      to: "PaperForgeReadingCanvasView"
      via: "Open Reading Canvas button passes entry.key"
      pattern: "explicit paper identity"
---

<objective>
Wire the Phase ANN10 canvas contracts into the Obsidian plugin runtime and complete the focused verification gate.

Purpose: make the PaperForge Reading Canvas openable from the paper panel and command palette with explicit paper identity while preserving all v0.2 annotation fallback behavior.
Output: new Reading Canvas `ItemView`, view registration, open command, paper panel button, minimal shell styling, runtime/DOM tests, and focused regression gate.
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
@.planning/phases/ANN10/ANN10-01-PLAN.md
@paperforge/plugin/main.js
@paperforge/plugin/src/canvas/index.js
@paperforge/plugin/src/testable.js
@paperforge/plugin/styles.css
@paperforge/plugin/tests/annotation-bridge.test.mjs
@paperforge/plugin/tests/annotation-navigation.test.mjs
@paperforge/plugin/tests/annotation-overlay.test.mjs
@paperforge/plugin/tests/annotation-main-runtime.test.mjs
@paperforge/plugin/tests/annotation-section-dom.test.mjs
</context>

<source_audit>
GOAL: Covers the Phase ANN10 user-openable canvas foundation by registering a dedicated view and wiring explicit paper identity into runtime.
REQ: CANVAS-01 is covered by the paper panel button and command palette command; CANVAS-02 is covered by delegating runtime loading to Plan 01 v0.2 annotation wrapper.
RESEARCH: Implements runtime wiring recommendation with a second `ItemView`, CommonJS module delegation, and focused regression gates.
CONTEXT: Implements D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-19 D-20 D-25 D-26 D-27 and D-28 directly, and verifies D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-21 D-22 D-23 and D-24 remain honored by the Plan 01 modules.
</source_audit>

<tasks>

<task type="auto">
  <name>Task 1: Register the Reading Canvas ItemView and command</name>
  <files>paperforge/plugin/main.js, paperforge/plugin/tests/canvas-main-runtime.test.mjs</files>
  <action>Add `VIEW_TYPE_PAPERFORGE_READING_CANVAS = 'paperforge-reading-canvas'` or equivalent. Add `PaperForgeReadingCanvasView extends ItemView` that owns explicit canvas context state, accepts `{ paperKey, entry }`, delegates load/render behavior to `require('./src/canvas')`, and renders Phase ANN10 shell states only. Register the view in `PaperForgePlugin.onload()`. Add command `PaperForge: Open Reading Canvas for active paper` using existing active-paper resolution; if no paper can be resolved, show a concise Notice asking the user to open a recognized paper note or PDF first. The command must not create a global paper picker. Runtime tests must prove the view type constant, class export through `module.exports.__test`, command registration, missing-paper Notice path, explicit `paperKey` state, and no auto-switch on unrelated active paper changes.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- canvas-main-runtime.test.mjs canvas-context.test.mjs canvas-controller.test.mjs canvas-render.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Reading Canvas view and command are registered, use explicit paper identity, delegate to `src/canvas/*`, and do not add paper-picking or editing behavior.</acceptance_criteria>
  <done>New runtime tests prove view registration, command availability, explicit paperKey, missing-paper handling, and module delegation.</done>
</task>

<task type="auto">
  <name>Task 2: Add paper panel open button, minimal shell styles, and final gate</name>
  <files>paperforge/plugin/main.js, paperforge/plugin/styles.css, paperforge/plugin/tests/canvas-section-dom.test.mjs</files>
  <action>Add a paper panel button near the current paper header or annotation area labelled along the lines of `Open Reading Canvas`. The click handler must pass the current paper panel `entry.key`/entry directly to the Reading Canvas open helper and must not re-resolve identity from active file/title/path. Add minimal namespaced CSS such as `.paperforge-reading-canvas-*` for shell-only distinction; do not implement card lanes, anchors, connector SVG, pan/zoom, or full visual polish. Add DOM tests proving the button appears in paper mode, calls the open helper with `entry.key`, does not appear when no paper entry exists, and does not introduce edit/delete/save/import/apply/write-back controls. Run the full focused ANN10 gate including Plan 01 canvas tests and v0.2 annotation regression tests.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-render.test.mjs canvas-main-runtime.test.mjs canvas-section-dom.test.mjs annotation-bridge.test.mjs annotation-navigation.test.mjs annotation-overlay.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Paper panel button opens the canvas with exact `entry.key`, shell styling is namespaced and minimal, forbidden controls are absent, and existing v0.2 annotation list/jump/overlay tests still pass.</acceptance_criteria>
  <done>Paper panel entry, shell CSS, runtime/DOM tests, and focused v0.2 regression gate pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Paper panel -> Reading Canvas | Runtime transfers paper identity from one view into another. |
| Command palette -> active-paper resolver | Runtime resolves active paper opportunistically and must fail closed. |
| Canvas modules -> shipped main.js | `main.js` must use the same module logic covered by pure tests or document parity debt. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ANN10-02-S | Spoofing | Paper panel open button | mitigate | Pass exact `entry.key`; do not re-guess from active file/title/path. |
| T-ANN10-02-T | Tampering | Existing paper panel/list DOM | mitigate | Add a bounded button and namespaced canvas CSS; preserve existing annotation section tests. |
| T-ANN10-02-R | Repudiation | View opening behavior | accept | No audit log needed; tests document command/button behavior. |
| T-ANN10-02-I | Information Disclosure | Runtime errors | mitigate | Use concise Notice/state reasons; no raw stack traces, JSON, or shell output in UI. |
| T-ANN10-02-D | Denial of Service | View activation/reuse | mitigate | Reuse or activate leaf sensibly; avoid loops or auto-switch behavior on active paper changes. |
| T-ANN10-02-E | Elevation of Privilege | Write controls | mitigate | Runtime shell must expose no edit/delete/save/import/apply/write-back controls and no storage writes. |

</threat_model>

<verification>

Run from the repository root:

```powershell
Push-Location paperforge/plugin
node --check main.js
npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-render.test.mjs canvas-main-runtime.test.mjs canvas-section-dom.test.mjs annotation-bridge.test.mjs annotation-navigation.test.mjs annotation-overlay.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs
Pop-Location
```

</verification>

<success_criteria>

- Plugin registers a dedicated PaperForge Reading Canvas `ItemView`.
- User can open the canvas from the paper panel using the current entry key.
- User can open the canvas from the command palette when an active paper is resolvable.
- Missing active paper produces a concise Notice and no crash.
- Open canvas instances keep their explicit paperKey and do not auto-switch on active paper changes.
- Runtime delegates to `src/canvas/*` modules or records explicit temporary inlining debt with parity tests.
- v0.2 annotation bridge/navigation/overlay/runtime/DOM focused tests still pass.
- No Phase 11+ cards, anchors, connectors, persistent layouts, native PDF overlay claims, or write controls are introduced.

</success_criteria>
