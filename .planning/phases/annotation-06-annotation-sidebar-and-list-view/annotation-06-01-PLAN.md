---
phase: annotation-06-annotation-sidebar-and-list-view
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements:
  - LIST-01
  - LIST-02
  - LIST-03
  - LIST-04
  - LIST-05
hard_prerequisites:
  - annotation-05-01
  - annotation-05-02

must_haves:
  truths:
    - "Annotation Phase 5 is a hard prerequisite: `paperforge/plugin/src/testable.js` must expose annotation bridge helpers, `paperforge/plugin/main.js` must expose `getAnnotationState()` and `loadAnnotationsForCurrentPaper(reason)`, and the runtime test hook must make `PaperForgeStatusView` testable."
    - "If any Phase 5 bridge artifact is absent, execution stops before Phase 6 edits and reports that Annotation Phase 5 must be executed first."
    - "The recent reverted or revert-of-revert git history is not treated as proof of availability; the executor verifies the actual working tree at execution time."
    - "Plugin test dependencies come only from existing `paperforge/plugin/package.json`; no new npm package is added in Phase 6."
  artifacts:
    - path: "paperforge/plugin/src/testable.js"
      provides: "Existing Phase 5 annotation bridge helper exports consumed by later Phase 6 plans"
      contains: "loadAnnotationsForPaper"
    - path: "paperforge/plugin/main.js"
      provides: "Existing Phase 5 runtime annotation state and loader methods consumed by later Phase 6 plans"
      contains: "loadAnnotationsForCurrentPaper"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "Runtime test coverage or hook proving `PaperForgeStatusView` annotation bridge wiring"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/testable.js"
      via: "Phase 5 bridge contract mirrored into runtime"
      pattern: "loadAnnotationsForPaper|loadAnnotationsForCurrentPaper|getAnnotationState"
    - from: "paperforge/plugin/package.json"
      to: "Phase 6 verification"
      via: "existing Vitest/jsdom dev dependencies"
      pattern: "\"vitest\"|\"jsdom\""
---

<objective>
Gate Annotation Phase 6 on the completed Annotation Phase 5 plugin bridge.

Purpose: Prevent Phase 6 from smuggling CLI bridge work into the list UI phase and ensure later plans can consume the active-paper annotation state safely.
Output: A deterministic preflight result. If the bridge is missing, execution stops with a clear instruction to execute Annotation Phase 5 first.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-RESEARCH.md
@.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-CONTEXT.md
@.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-01-PLAN.md
@.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-02-PLAN.md
@paperforge/plugin/src/testable.js
@paperforge/plugin/main.js
@paperforge/plugin/tests/runtime.test.mjs
@paperforge/plugin/package.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify Phase 5 bridge artifacts before Phase 6 edits</name>
  <files>read-only: paperforge/plugin/src/testable.js, paperforge/plugin/main.js, paperforge/plugin/tests/annotation-main-runtime.test.mjs, paperforge/plugin/tests/runtime.test.mjs</files>
  <action>
    Run a preflight check before editing any Phase 6 file. Confirm that `paperforge/plugin/src/testable.js` exposes Phase 5 annotation bridge helpers such as `ANNOTATION_LOAD_STATES`, `normalizeAnnotationExportRow`, and `loadAnnotationsForPaper`. Confirm that `paperforge/plugin/main.js` exposes `getAnnotationState()` and `loadAnnotationsForCurrentPaper(reason)` on the real `PaperForgeStatusView` runtime path. Confirm that runtime tests can access or directly exercise `PaperForgeStatusView` through an existing test hook such as `module.exports.__test`.

    If any of these are absent, stop this plan and report: "Annotation Phase 5 bridge prerequisite is missing. Execute Annotation Phase 5 plans first, then rerun Annotation Phase 6." Do not implement CLI bridge helpers, active-paper annotation loading, or runtime bridge wiring inside Phase 6.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "$missing=@(); $testable=Get-Content -Raw 'paperforge/plugin/src/testable.js'; $main=Get-Content -Raw 'paperforge/plugin/main.js'; $runtime=''; if (Test-Path 'paperforge/plugin/tests/annotation-main-runtime.test.mjs') { $runtime=Get-Content -Raw 'paperforge/plugin/tests/annotation-main-runtime.test.mjs' }; if ($testable -notmatch 'ANNOTATION_LOAD_STATES' -or $testable -notmatch 'normalizeAnnotationExportRow' -or $testable -notmatch 'loadAnnotationsForPaper') { $missing += 'src/testable.js annotation bridge helpers' }; if ($main -notmatch 'getAnnotationState\s*\(') { $missing += 'main.js getAnnotationState()' }; if ($main -notmatch 'loadAnnotationsForCurrentPaper\s*\(') { $missing += 'main.js loadAnnotationsForCurrentPaper(reason)' }; if ($main -notmatch 'module\.exports\.__test' -and $runtime -notmatch 'PaperForgeStatusView') { $missing += 'runtime test hook for PaperForgeStatusView' }; if ($missing.Count -gt 0) { throw ('Annotation Phase 5 bridge prerequisite missing: ' + ($missing -join '; ') + '. Stop Phase 6 and execute Annotation Phase 5 first.') }; Write-Output 'Annotation Phase 5 bridge preflight passed.'"</automated>
  </verify>
  <done>Execution has proven that Phase 5 bridge helpers, runtime state methods, loader method, and runtime test access exist before any Phase 6 implementation begins.</done>
</task>

<task type="auto">
  <name>Task 2: Verify Windows-safe plugin test prerequisites</name>
  <files>read-only: paperforge/plugin/package.json, paperforge/plugin/node_modules</files>
  <action>
    Confirm Node and `npm.cmd` are available, and confirm `paperforge/plugin/node_modules` exists before running Vitest plans. If `node_modules` is missing, stop and report that dependencies must be installed from the existing `paperforge/plugin/package.json` before execution continues. Do not install dependencies during planning and do not add new npm packages; `vitest` and `jsdom` are already declared.
  </action>
  <verify>
    <automated>node --version</automated>
    <automated>npm.cmd --version</automated>
    <automated>powershell -NoProfile -Command "if (!(Test-Path 'paperforge/plugin/node_modules')) { throw 'Missing paperforge/plugin/node_modules. Install existing plugin dependencies with npm.cmd install in paperforge/plugin before executing Phase 6 tests; do not add packages.' }; Write-Output 'Plugin dependencies present.'"</automated>
  </verify>
  <done>Execution environment can run plugin tests through `npm.cmd`, or it stops before implementation with an explicit dependency-install prerequisite.</done>
</task>

</tasks>

<source_audit>
SOURCE | ID | Feature/Requirement | Plan | Status | Notes
GOAL | phase-goal | Show paper-scoped annotations in the Obsidian PaperForge paper UI before overlay rendering is stable | 02-04 | COVERED | Plan 01 gates the Phase 5 bridge dependency; Plans 02-04 build view-model, runtime section, and bounded styling.
REQ | LIST-01 | User can view a paper-scoped annotation list in the PaperForge Obsidian UI | 03 | COVERED | Embedded in `PaperForgeStatusView` paper mode.
REQ | LIST-02 | User can scan annotations by page, color/type, selected text, and comment | 02,04 | COVERED | View-model exposes row data; CSS renders compact previews.
REQ | LIST-03 | User can filter or group annotations by at least page and type/color | 02,03 | COVERED | Pure helpers compute grouping/filter/search; runtime controls consume them.
REQ | LIST-04 | User can refresh the annotation list after import without restarting Obsidian | 03 | COVERED | Section refresh calls Phase 5 `loadAnnotationsForCurrentPaper('manual')`.
REQ | LIST-05 | List UI degrades gracefully for empty papers, missing PDFs, and unsupported fields | 02,03,04 | COVERED | Helpers and runtime render distinct states; styles preserve readable layout.
RESEARCH | preflight | Treat Phase 5 bridge absence as a hard blocker; do not reimplement CLI bridge in Phase 6 | 01 | COVERED | This preflight stops execution if bridge artifacts are missing.
RESEARCH | helper-layer | Put list behavior in `src/testable.js` pure helpers and tests | 02 | COVERED | Plan 02 owns pure view-model helpers.
RESEARCH | runtime-layer | Test real `PaperForgeStatusView` integration, not helper-only behavior | 03 | COVERED | Plan 03 owns `main.js` runtime tests.
RESEARCH | style-layer | Add compact, bounded list styles and regression checks | 04 | COVERED | Plan 04 owns CSS and DOM regression.
CONTEXT | D-01, D-02, D-03 | Embed in paper mode after overview, before Next Step, expanded by default | 03 | COVERED | Runtime insertion plan.
CONTEXT | D-04, D-05, D-06, D-07, D-08, D-09, D-10 | Bounded compact rows, previews, inline expansion, swatch/type, provenance in details | 04 | COVERED | Styling and row layout plan.
CONTEXT | D-11, D-12, D-13, D-14, D-15, D-16, D-17 | Reading order, grouping, filter/search, session-only UI state | 02 | COVERED | Pure helper plan.
CONTEXT | D-18, D-19, D-20, D-21, D-22, D-23 | Local refresh, stale banner, distinct states, section-local loading | 03 | COVERED | Runtime section plan.
CONTEXT | D-24, D-25 | No jump, overlay, edit, write-back, DB mutation, or evidence wiring | 03,04 | COVERED | Runtime and regression plans forbid and test against these controls.
</source_audit>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase 6 executor -> existing Phase 5 bridge | Later plans depend on code that may not exist in the current working tree. |
| Local environment -> plugin tests | Test execution depends on existing Node/npm dependencies. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-06-01 | Tampering | Phase boundary | mitigate | Preflight verifies Phase 5 bridge artifacts and stops if missing; Phase 6 does not reimplement CLI bridge code. |
| T-annotation-06-02 | Denial of Service | Vitest execution | mitigate | Check `node_modules` before running tests so execution fails early with a clear dependency prerequisite. |
| T-annotation-06-SC | Tampering | npm installs | mitigate | No package install task and no new package; if dependencies are missing, stop for existing `npm.cmd install` rather than modifying `package.json`. |
</threat_model>

<verification>
- `powershell -NoProfile -Command "...Phase 5 bridge preflight..."`
- `node --version`
- `npm.cmd --version`
- `powershell -NoProfile -Command "if (!(Test-Path 'paperforge/plugin/node_modules')) { throw ... }"`
</verification>

<success_criteria>
- [ ] Phase 5 bridge helper exports exist in `paperforge/plugin/src/testable.js`.
- [ ] Phase 5 runtime methods `getAnnotationState()` and `loadAnnotationsForCurrentPaper(reason)` exist in `paperforge/plugin/main.js`.
- [ ] Runtime tests can access or exercise `PaperForgeStatusView`.
- [ ] Missing bridge artifacts stop Phase 6 before any implementation edits.
- [ ] Plugin tests can be run through Windows-safe `npm.cmd` using existing dependencies only.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-01-SUMMARY.md`.
</output>
