---
phase: annotation-05-plugin-annotation-data-bridge
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - paperforge/plugin/src/testable.js
  - paperforge/plugin/tests/annotation-bridge.test.mjs
autonomous: true
requirements:
  - BRDG-01
  - BRDG-02
  - BRDG-03
  - BRDG-04

must_haves:
  truths:
    - "D-01: The bridge uses `paperforge annotation export --paper KEY --json` as the primary annotation data source."
    - "D-02: The export payload is preferred over list output so attachment identity, provenance, `position_json`, and `selector_json` remain available."
    - "D-03: Normalization may add UI display fields but must retain the original export row."
    - "D-04: Phase 5 does not implement a dual-source list/export bridge unless export proves insufficient."
    - "D-08: Helpers return a complete annotation load state rather than a bare array."
    - "D-09: Helper states include `idle`, `loading`, `ready`, `empty`, `missing-paper`, `missing-db`, `cli-error`, and `invalid-json`."
    - "D-10: State objects carry `paperKey`, `annotations`, `message`, `errorCode`, and raw CLI/PFResult details where useful."
    - "D-11: Phase 6 can render list, empty, and error states without reparsing raw CLI output."
    - "D-12: Missing or unreadable `annotations.db` is classified as `missing-db`, not `empty`."
    - "D-13: `empty` means the annotation system is available and the active paper has no annotations."
    - "D-14: CLI process failures become `cli-error`; invalid stdout or malformed JSON becomes `invalid-json`."
    - "D-15: User-facing messages are friendly and do not expose raw Python tracebacks or shell noise."
    - "D-16: Normalized rows include `display` fields for page, page label, type, color, selected text, and comment."
    - "D-17: Normalized rows include `provenance` fields for source, read-only state, library, parent, attachment, annotation, sync state, and timestamps."
    - "D-18: Normalized rows include `pdfLocation` fields for page index/label, attachment identity, `position_json`, `selector_json`, and sort/index fields."
    - "D-19: Normalized rows keep the original export row under `raw`."
  artifacts:
    - path: "paperforge/plugin/src/testable.js"
      provides: "Node-testable annotation bridge helpers and load state machine"
    - path: "paperforge/plugin/tests/annotation-bridge.test.mjs"
      provides: "Representative PFResult fixtures and bridge failure-state coverage"
  key_links:
    - from: "paperforge/plugin/src/testable.js"
      to: "paperforge/commands/annotation.py"
      via: "CLI args for `annotation status --json` and `annotation export --paper KEY --json`"
      pattern: "annotation.*export"
    - from: "paperforge/plugin/tests/annotation-bridge.test.mjs"
      to: "paperforge/plugin/src/testable.js"
      via: "Vitest imports from the CommonJS testable helper module"
      pattern: "loadAnnotationsForPaper"
---

<objective>
Create the testable annotation data bridge contract for the Obsidian plugin.

Purpose: Let plugin code load active-paper annotations through the verified v0.1 CLI JSON contracts without reimplementing annotation database queries in JavaScript.
Output: Testable helpers that build CLI args, parse PFResult JSON, classify bridge states, and normalize export rows into UI-ready annotation objects.
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
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/commands.test.mjs
@paperforge/plugin/tests/errors.test.mjs
@paperforge/plugin/tests/runtime.test.mjs
@paperforge/plugin/package.json
@paperforge/commands/annotation.py
@tests/cli/test_annotation_json_contracts.py
@tests/cli/test_annotation_read_json.py
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Define normalized annotation row and state contracts</name>
  <files>
    paperforge/plugin/src/testable.js
    paperforge/plugin/tests/annotation-bridge.test.mjs
  </files>
  <behavior>
    - Test 1: `normalizeAnnotationExportRow(row)` returns `{display, provenance, pdfLocation, raw}` and preserves the exact input row object under `raw`.
    - Test 2: `display` maps page index, page label, type, color, selected text, and comment from full export rows.
    - Test 3: `provenance` maps source, `is_readonly`, source library ID, parent key, attachment key, annotation key, sync state, created/updated/source timestamps, and deleted timestamp where present.
    - Test 4: `pdfLocation` maps page index/label, source attachment key, `position_json`, `selector_json`, `sort_index`, and row `id`.
    - Test 5: pure state helpers can produce `idle`, `loading`, `ready`, `empty`, `missing-paper`, `missing-db`, `cli-error`, and `invalid-json` with consistent `paperKey`, `annotations`, `message`, `errorCode`, and raw details fields.
  </behavior>
  <action>
    Add `paperforge/plugin/tests/annotation-bridge.test.mjs` using the same Vitest import style as the existing plugin tests. Start with representative `annotation.export` PFResult fixtures based on the Python CLI contract tests, including at least one highlight and one note row with provenance and PDF-location fields.

    Extend `paperforge/plugin/src/testable.js` with exported constants/helpers for annotation load states and row normalization. Keep helper names explicit and stable, for example `ANNOTATION_LOAD_STATES`, `normalizeAnnotationExportRow`, and small state factory helpers. Do not import Obsidian APIs. Do not query or mutate `annotations.db` from JavaScript.
  </action>
  <verify>
    <automated>cd paperforge/plugin; npm test -- tests/annotation-bridge.test.mjs</automated>
  </verify>
  <done>Representative export rows normalize into the required grouped shape and all required state names can be constructed in Node tests.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Implement CLI loader parsing and failure classification</name>
  <files>
    paperforge/plugin/src/testable.js
    paperforge/plugin/tests/annotation-bridge.test.mjs
  </files>
  <behavior>
    - Test 1: `buildAnnotationStatusArgs(extraArgs)` builds a Python module invocation for `paperforge annotation status --json`.
    - Test 2: `buildAnnotationExportArgs(paperKey, extraArgs)` builds a Python module invocation for `paperforge annotation export --paper KEY --json`.
    - Test 3: `loadAnnotationsForPaper` returns `missing-paper` and does not spawn a subprocess when `paperKey` is blank or null.
    - Test 4: `loadAnnotationsForPaper` returns `missing-db` when the status PFResult reports `data.db_available === false`, and does not reinterpret that as an empty paper.
    - Test 5: `loadAnnotationsForPaper` returns `empty` when status is available, export succeeds, and export total/annotations are empty.
    - Test 6: `loadAnnotationsForPaper` returns `ready` with normalized rows when status is available and export succeeds with annotations.
    - Test 7: a valid PFResult error or nonzero subprocess failure becomes `cli-error` with friendly `message` and `errorCode`.
    - Test 8: invalid stdout or malformed JSON from status/export becomes `invalid-json` and preserves raw stdout/stderr for debugging without exposing traceback text as the user message.
  </behavior>
  <action>
    Implement a reusable async loader in `paperforge/plugin/src/testable.js`, for example `loadAnnotationsForPaper({ paperKey, pythonExe, pythonExtraArgs, cwd, timeout, runSubprocessFn, env })`. It should first call `annotation status --json` to distinguish missing `annotations.db` from a real empty paper, then call `annotation export --paper KEY --json` as the primary data source when the DB is available.

    Reuse the existing `runSubprocess` injection pattern so tests can provide deterministic subprocess fixtures. Keep raw PFResult/subprocess details in a non-rendered debug field such as `raw` or `details`, while `message` remains concise and user-friendly. Do not add dependencies, do not call `annotation list`, and do not change Python annotation command behavior in this plan.
  </action>
  <verify>
    <automated>cd paperforge/plugin; npm test -- tests/annotation-bridge.test.mjs</automated>
    <automated>cd paperforge/plugin; npm test</automated>
  </verify>
  <done>The loader covers success, empty, missing paper, missing DB, CLI failure, and invalid JSON cases using PFResult/subprocess fixtures.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Obsidian plugin -> PaperForge CLI | Plugin passes active paper identity into a local subprocess. |
| PaperForge CLI stdout -> plugin state | Untrusted process output is parsed into UI-ready state. |
| Normalized rows -> future UI | Future UI renders text/comment fields that originate in imported annotations. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-05-01 | Tampering | `loadAnnotationsForPaper` stdout parsing | mitigate | Parse JSON with explicit failure handling; classify malformed output as `invalid-json`; never eval or execute stdout. |
| T-annotation-05-02 | Information Disclosure | state `message` fields | mitigate | Keep raw traceback/shell noise only in debug details; user-facing messages stay friendly per D-15 and SAFE-04. |
| T-annotation-05-03 | Tampering | JavaScript bridge data access | mitigate | Use CLI contracts only; do not query or mutate `annotations.db` in TypeScript/JavaScript per BRDG-02 and SAFE-03. |
| T-annotation-05-SC | Tampering | npm installs | accept | This plan adds no npm package installs and uses existing Vitest tooling. |
</threat_model>

<verification>
- `cd paperforge/plugin; npm test -- tests/annotation-bridge.test.mjs`
- `cd paperforge/plugin; npm test`
</verification>

<success_criteria>
- [ ] Plugin helpers build `annotation status --json` and `annotation export --paper KEY --json` subprocess args.
- [ ] Loader states include all eight required states and expose `paperKey`, `annotations`, `message`, `errorCode`, and raw debug details.
- [ ] Missing DB, missing paper, empty paper, CLI failure, and invalid JSON are distinguishable.
- [ ] Normalized rows include `display`, `provenance`, `pdfLocation`, and `raw`.
- [ ] No visible annotation sidebar/list UI, filtering, grouping, jump behavior, overlay rendering, editing, Zotero write-back, concept-card evidence integration, TypeScript DB query, or DB mutation is added.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-01-SUMMARY.md`.
</output>
