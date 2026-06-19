---
phase: annotation-05-plugin-annotation-data-bridge
plan: 02
type: execute
wave: 2
depends_on:
  - annotation-05-01
files_modified:
  - paperforge/plugin/src/testable.js
  - paperforge/plugin/tests/annotation-lifecycle.test.mjs
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
  - paperforge/plugin/main.js
autonomous: true
requirements:
  - BRDG-01
  - BRDG-02
  - BRDG-03
  - BRDG-04

must_haves:
  truths:
    - "D-05: Main plugin integration reuses existing dashboard paper-resolution behavior instead of creating another identity path."
    - "D-06: Active paper detection continues to support markdown `zotero_key`, canonical-index PDF path matching, and workspace folder key detection through existing `_resolveModeForFile(file)` behavior."
    - "D-07: If no active paper can be resolved, plugin annotation state becomes `missing-paper` and does not call the CLI with an empty or guessed key."
    - "D-08: Main plugin stores a complete annotation load state, not just annotation rows."
    - "D-09: Runtime state supports `idle`, `loading`, `ready`, `empty`, `missing-paper`, `missing-db`, `cli-error`, and `invalid-json`."
    - "D-10: Runtime state carries `paperKey`, `annotations`, `message`, `errorCode`, and raw CLI/PFResult details where useful."
    - "D-11: Phase 6 UI can consume the stored bridge state directly without reparsing raw CLI output."
    - "D-12: Missing or unreadable `annotations.db` remains `missing-db`, not `empty`, in the integrated plugin lifecycle."
    - "D-13: `empty` remains reserved for an available annotation system with no rows for the current paper."
    - "D-14: Subprocess failure maps to `cli-error`; invalid stdout/malformed JSON maps to `invalid-json`."
    - "D-15: Any user-facing state messages remain friendly and avoid raw Python traceback or shell noise."
    - "D-16: Integrated rows preserve `display` fields for page, page label, type, color, selected text, and comment."
    - "D-17: Integrated rows preserve `provenance` fields for source, read-only state, source library, parent key, attachment key, annotation key, sync state, and timestamps."
    - "D-18: Integrated rows preserve `pdfLocation` fields for page index/label, source attachment identity, `position_json`, `selector_json`, and sort/index fields."
    - "D-19: Integrated rows retain the raw export row under `raw`."
    - "D-20: Annotation state updates when the active paper changes using existing `_currentPaperKey` and `_currentPaperEntry` dashboard state."
    - "D-21: Phase 5 does not add database polling or a full visible refresh workflow; Phase 6 owns visible list UI and refresh controls."
    - "D-22: The plugin exposes a reusable loader method that later UI code can call for explicit manual refresh."
  artifacts:
    - path: "paperforge/plugin/src/testable.js"
      provides: "Testable active-paper annotation lifecycle guard used by runtime integration"
    - path: "paperforge/plugin/tests/annotation-lifecycle.test.mjs"
      provides: "Executable coverage for active-paper annotation refresh lifecycle"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "Executable coverage that the real `PaperForgeStatusView` runtime methods are wired to the annotation bridge"
    - path: "paperforge/plugin/main.js"
      provides: "Obsidian runtime integration for active-paper annotation loader state"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/testable.js"
      via: "duplicated/inlined helper logic following existing plugin runtime pattern"
      pattern: "loadAnnotationsForPaper"
    - from: "PaperForgeStatusView._detectAndSwitch"
      to: "PaperForgeStatusView.loadAnnotationsForCurrentPaper"
      via: "active paper key transition"
      pattern: "_currentPaperKey"
---

<objective>
Integrate the annotation bridge into the existing Obsidian plugin active-paper lifecycle.

Purpose: Keep the plugin state ready for Phase 6 annotation list rendering while preserving the current thin-shell architecture and avoiding a visible UI surface in Phase 5.
Output: `PaperForgeStatusView` stores and refreshes annotation state for the active paper, with a reusable loader method for later UI refresh controls.
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
@.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-CONTEXT.md
@.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-01-SUMMARY.md
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/annotation-bridge.test.mjs
@paperforge/plugin/tests/annotation-lifecycle.test.mjs
@paperforge/plugin/tests/annotation-main-runtime.test.mjs
@paperforge/plugin/package.json

Do not read all of `paperforge/plugin/main.js`; it is large. Use `rg` and narrow reads around these known integration points only:
- `PaperForgeStatusView` constructor tracks `_currentMode`, `_currentPaperKey`, `_currentPaperEntry`, `_currentFilePath`, `_modeSubscribers`, `_leafChangeTimer`.
- `_resolveModeForFile(file)` resolves markdown frontmatter `zotero_key`, PDF path through canonical index `pdf_path`, and workspace folder key.
- `_detectAndSwitch()` sets `_currentPaperKey` and `_currentPaperEntry`.
- `_switchMode()` and `_refreshCurrentMode()` rerender current mode on active file changes.
- Existing testable helper logic lives in `paperforge/plugin/src/testable.js` and is duplicated/inlined into `main.js` for the Obsidian runtime.
- Existing subprocess helper is `runSubprocess(pythonExe, args, cwd, timeout, _spawn, env)`.
- Existing Python resolver is `resolvePythonExecutable(vaultPath, settings, ...)`.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Inline tested annotation bridge helpers into plugin runtime</name>
  <files>
    paperforge/plugin/main.js
  </files>
  <action>
    Copy the tested annotation bridge helper logic from `paperforge/plugin/src/testable.js` into `paperforge/plugin/main.js` following the existing runtime pattern for helpers that are testable in `src/testable.js` and duplicated in the bundled Obsidian plugin file.

    Include only the helper surface needed by runtime integration: state constants/factories, JSON/PFResult parsing, `buildAnnotationStatusArgs`, `buildAnnotationExportArgs`, row normalization, and `loadAnnotationsForPaper`. Reuse existing `runSubprocess`, `resolvePythonExecutable`, and environment enrichment patterns already present in `main.js`. Do not add imports that require Node-only test modules inside Obsidian runtime code. Do not add UI rendering, buttons, sidebar/list DOM, grouping, filtering, PDF jump, overlay, editing, Zotero write-back, or TypeScript/JavaScript database access.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>cd paperforge/plugin; npm test -- tests/annotation-bridge.test.mjs</automated>
  </verify>
  <done>`main.js` contains the same tested bridge behavior needed by the Obsidian runtime and remains syntactically valid.</done>
</task>

<task type="auto">
  <name>Task 2: Wire annotation loading to active-paper changes</name>
  <files>
    paperforge/plugin/src/testable.js
    paperforge/plugin/tests/annotation-lifecycle.test.mjs
    paperforge/plugin/tests/annotation-main-runtime.test.mjs
    paperforge/plugin/main.js
  </files>
  <action>
    First add a small testable lifecycle helper in `paperforge/plugin/src/testable.js` and cover it with `paperforge/plugin/tests/annotation-lifecycle.test.mjs`. The helper should model the active-paper refresh decisions without importing Obsidian APIs, so the tests can prove:
    - missing paper sets `missing-paper` and never calls the loader/subprocess path;
    - a paper-key transition starts a load for the new key;
    - stale async load results cannot overwrite a newer active paper state;
    - `getAnnotationState()`-style access returns the currently stored state;
    - repeated refreshes use `_currentPaperKey` as the only bridge paper identity.

    Then extend `PaperForgeStatusView` with annotation bridge state while preserving current dashboard behavior:
    - initialize an `_annotationState` field to `idle`;
    - initialize a monotonic `_annotationLoadSeq` or equivalent stale-result guard;
    - add `getAnnotationState()` for Phase 6 consumers;
    - add reusable async `loadAnnotationsForCurrentPaper(reason = "manual")` so Phase 6 can call it for explicit refresh per D-22;
    - use `_currentPaperKey` as the only paper identity input to the bridge;
    - when `_currentPaperKey` is missing, set `missing-paper` and skip subprocess calls per D-07;
    - when the active paper key changes in the existing `_detectAndSwitch()` / `_switchMode()` / `_refreshCurrentMode()` lifecycle, update annotation state by calling the reusable loader;
    - ensure stale async loads cannot overwrite the state for a newer active paper.

    Add an integration-style Vitest harness in `paperforge/plugin/tests/annotation-main-runtime.test.mjs` that exercises the real `PaperForgeStatusView` method path in `paperforge/plugin/main.js`, not only the helper model. If needed, expose a minimal CommonJS test hook such as `module.exports.__test = { PaperForgeStatusView }` from `main.js`. Keep that export non-rendering and side-effect free. The runtime test may instantiate with `Object.create(PaperForgeStatusView.prototype)` and inject only the fields/mocks needed for the annotation loader path, but it must fail if the real runtime methods are not wired.

    The runtime test must cover at least:
    - `loadAnnotationsForCurrentPaper()` reads `_currentPaperKey` and calls the bridge loader with that key;
    - missing `_currentPaperKey` sets `missing-paper` and does not call the bridge loader/subprocess path;
    - a stale async result from an older key cannot overwrite the state after `_currentPaperKey` changes;
    - `getAnnotationState()` returns the stored runtime `_annotationState`;
    - the active-paper transition hook used in `_detectAndSwitch()` / `_switchMode()` / `_refreshCurrentMode()` invokes the reusable loader, or delegates to a shared runtime method that the test calls directly and that those hooks call.

    Keep the integration invisible or minimal: do not create a rendered annotation list, sidebar UI, refresh button, filter, group control, PDF jump action, PDF overlay, or annotation editor. Preserve `_currentMode`, `_currentPaperKey`, `_currentPaperEntry`, mode subscribers, and dashboard rerender behavior.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>cd paperforge/plugin; npm test -- tests/annotation-bridge.test.mjs</automated>
    <automated>cd paperforge/plugin; npm test -- tests/annotation-lifecycle.test.mjs</automated>
    <automated>cd paperforge/plugin; npm test -- tests/annotation-main-runtime.test.mjs</automated>
    <automated>cd paperforge/plugin; npm test</automated>
  </verify>
  <done>Active-paper changes update stored annotation bridge state through the reusable loader, and targeted tests prove both helper behavior and the real `PaperForgeStatusView` runtime wiring for missing-paper skipping, paper-key transition loading, stale-result guarding, and state exposure without adding a visible Phase 6 UI or any database mutation path.</done>
</task>

</tasks>

<source_audit>
SOURCE | ID | Feature/Requirement | Plan | Status | Notes
GOAL | phase-goal | Plugin loads annotation data through v0.1 CLI contracts without reimplementing storage in JavaScript | 01-02 | COVERED | Plan 01 builds bridge helpers; Plan 02 wires runtime lifecycle.
REQ | BRDG-01 | Load annotation data for active paper in Obsidian plugin without manual shell commands | 02 | COVERED | Runtime loader triggers from active paper and is reusable for Phase 6 manual refresh.
REQ | BRDG-02 | Use v0.1 annotation CLI/contracts instead of TypeScript DB queries | 01-02 | COVERED | Plans use status/export CLI only and forbid JS DB access.
REQ | BRDG-03 | Missing DB, missing paper, empty list, and CLI failures produce clear states/messages | 01-02 | COVERED | Plan 01 tests states; Plan 02 preserves them in runtime lifecycle.
REQ | BRDG-04 | Preserve page, selected text, comment, color, type, read-only state, source, and attachment identity | 01-02 | COVERED | Normalized rows keep display/provenance/pdfLocation/raw.
CONTEXT | D-01 through D-04 | CLI entry point and export-vs-list source decision | 01 | COVERED | Export is the primary data source; list is not used in Phase 5.
CONTEXT | D-05 through D-07 | Active paper resolution and missing-paper behavior | 02 | COVERED | Existing `_currentPaperKey` is reused; missing key skips CLI.
CONTEXT | D-08 through D-15 | State machine and failure classification | 01-02 | COVERED | Helpers define and runtime stores the same state contract.
CONTEXT | D-16 through D-19 | Normalized row shape | 01-02 | COVERED | `display`, `provenance`, `pdfLocation`, and `raw` required in helpers and integration.
CONTEXT | D-20 through D-22 | Refresh lifecycle and reusable loader | 02 | COVERED | Active-paper changes load state; no polling/UI refresh workflow; reusable method exposed; lifecycle and main-runtime tests verify transition loading, missing-paper skipping, stale-result guarding, and state access in the actual `PaperForgeStatusView` path.
</source_audit>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Active Obsidian file -> plugin paper identity | Current file metadata is interpreted as a PaperForge paper key. |
| Plugin runtime -> PaperForge CLI | Runtime spawns local Python commands using resolved Python executable and vault path. |
| CLI stdout -> stored plugin state | Local subprocess output becomes future UI-renderable state. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-05-04 | Spoofing | active paper identity | mitigate | Reuse existing `_resolveModeForFile` and `_currentPaperKey`; do not guess paper keys or add a second resolver. |
| T-annotation-05-05 | Tampering | subprocess args | mitigate | Build fixed `paperforge annotation status/export --json` args and pass paper key as an arg element, not through shell concatenation. |
| T-annotation-05-06 | Denial of Service | async active-file changes | mitigate | Use a monotonic load sequence or equivalent guard so stale subprocess results cannot overwrite the current paper state. |
| T-annotation-05-07 | Information Disclosure | visible plugin UI | mitigate | Phase 5 stores state only; no visible annotation list or raw traceback rendering is added. |
| T-annotation-05-SC | Tampering | npm installs | accept | This plan adds no package-manager installs and uses existing project test tooling. |
</threat_model>

<verification>
- `node --check paperforge/plugin/main.js`
- `cd paperforge/plugin; npm test -- tests/annotation-bridge.test.mjs`
- `cd paperforge/plugin; npm test -- tests/annotation-lifecycle.test.mjs`
- `cd paperforge/plugin; npm test -- tests/annotation-main-runtime.test.mjs`
- `cd paperforge/plugin; npm test`
</verification>

<success_criteria>
- [ ] `PaperForgeStatusView` has stored annotation bridge state initialized to `idle`.
- [ ] Active-paper changes trigger annotation state refresh through existing `_currentPaperKey` without a second identity resolver.
- [ ] Missing active paper sets `missing-paper` and does not invoke the CLI.
- [ ] The plugin exposes a reusable loader method for Phase 6 manual refresh.
- [ ] Targeted lifecycle tests prove active-paper transition loading, missing-paper no-op behavior, stale-result protection, and stored state access.
- [ ] A runtime harness test fails if `PaperForgeStatusView` in `main.js` is missing the annotation loader wiring, stale guard, or `getAnnotationState()` exposure.
- [ ] Runtime integration preserves normalized `display`, `provenance`, `pdfLocation`, and `raw` rows from Plan 01.
- [ ] No annotation sidebar/list UI, grouping, filtering, PDF jump, PDF overlay, editing, Zotero write-back, concept-card evidence integration, TypeScript DB query, DB mutation, polling, or visible refresh workflow is added.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-02-SUMMARY.md`.
</output>
