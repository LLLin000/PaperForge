---
phase: ANN11
plan: "01"
type: execute
wave: 1
depends_on:
  - ANN10-01
files_modified:
  - paperforge/plugin/src/canvas/view-model.js
  - paperforge/plugin/src/canvas/layout.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-viewmodel.test.mjs
  - paperforge/plugin/tests/canvas-layout.test.mjs
requirements:
  - CANVAS-04
  - CARD-01
  - CARD-02
  - CARD-03
  - CARD-04
requirements_addressed:
  - CANVAS-04
  - CARD-01
  - CARD-02
  - CARD-03
  - CARD-04
autonomous: true
decision_coverage:
  - D-01
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
  - D-18
  - D-19
  - D-20
  - D-21
  - D-22
must_haves:
  truths:
    - "CANVAS-04: Canvas card view-model states distinguish loaded, empty, missing paper, missing annotation database, missing source, command failure, refresh, and stale-result conditions."
    - "CARD-01: Each card model carries selected text, comment, page, color/type, source, attachment/provenance, and read-only status."
    - "CARD-02: Missing, long, and CJK-heavy selected text/comment values are represented with explicit preview metadata for bounded DOM rendering."
    - "CARD-03: Lane placement is deterministic by reading/source order and alternates left/right without random or persisted layout state."
    - "CARD-04: Card models preserve source identity for downstream evidence workflows without exposing create/edit/delete/save/import/apply/write-back affordances."
    - "Context decision coverage in this plan: D-01 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-18 D-19 D-20 D-21 D-22."
  artifacts:
    - path: "paperforge/plugin/src/canvas/view-model.js"
      provides: "Read-only annotation card and canvas state projection"
    - path: "paperforge/plugin/src/canvas/layout.js"
      provides: "Deterministic reading-order sort and left/right lane assignment"
    - path: "paperforge/plugin/src/canvas/index.js"
      provides: "Narrow CommonJS exports for ANN11 card helpers"
    - path: "paperforge/plugin/tests/canvas-viewmodel.test.mjs"
      provides: "Card field, state, missing/long/CJK, source identity, and safety tests"
    - path: "paperforge/plugin/tests/canvas-layout.test.mjs"
      provides: "Deterministic lane placement and no-persistence tests"
  key_links:
    - from: "paperforge/plugin/src/canvas/view-model.js"
      to: "paperforge/plugin/src/canvas/annotations.js"
      via: "v0.2-compatible annotation state shape"
      pattern: "consume state.annotations only; no new loader"
    - from: "paperforge/plugin/src/canvas/layout.js"
      to: "paperforge/plugin/src/testable.js"
      via: "test parity with sortAnnotationsForReadingOrder and getAnnotationIdentity"
      pattern: "same page/sort/identity precedence without importing testable into shipped canvas modules"
    - from: "paperforge/plugin/src/canvas/index.js"
      to: "paperforge/plugin/src/canvas/view-model.js"
      via: "module.exports"
      pattern: "buildCanvasCardViewModel"
---

<objective>
Create pure canvas card view-model and deterministic lane-layout contracts for ANN11.

Purpose: turn ANN10's paper-scoped annotation state into safe, read-only card data before runtime DOM rendering is extended.
Output: `view-model.js`, `layout.js`, export updates, and focused Vitest coverage for explicit states, required card fields, long/CJK/missing values, deterministic lanes, source identity, and the read-only boundary.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/ANN11/ANN11-CONTEXT.md
@.planning/phases/ANN11/ANN11-RESEARCH.md
@.planning/phases/ANN10/annotation-10-CONTEXT.md
@.planning/phases/ANN10/ANN10-01-PLAN.md
@paperforge/plugin/package.json
@paperforge/plugin/src/canvas/context.js
@paperforge/plugin/src/canvas/annotations.js
@paperforge/plugin/src/canvas/controller.js
@paperforge/plugin/src/canvas/render.js
@paperforge/plugin/src/canvas/index.js
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/annotation-list-viewmodel.test.mjs
@paperforge/plugin/tests/canvas-context.test.mjs
@paperforge/plugin/tests/canvas-controller.test.mjs
</context>

<source_audit>
GOAL: Covered by projecting existing annotation state into deterministic read-only side-lane card data; DOM lane rendering is completed in ANN11-02.
REQ: CANVAS-04 is covered at the pure state/view-model layer. CARD-01, CARD-02, CARD-03, and CARD-04 are covered by card field, preview, lane, and source-identity contracts.
RESEARCH: Covers the recommended `src/canvas/view-model.js` and `src/canvas/layout.js` seams, uses no new dependencies, keeps annotation loading delegated to ANN10/v0.2 contracts, and avoids direct SQLite/Zotero/Python/API expansion.
CONTEXT: Implements D-01, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-18, D-19, D-20, D-21, and D-22. D-02, D-15, D-16, and D-17 are completed in ANN11-02 DOM/CSS work.
</source_audit>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Build read-only card and canvas state view-models</name>
  <files>paperforge/plugin/src/canvas/view-model.js, paperforge/plugin/src/canvas/index.js, paperforge/plugin/tests/canvas-viewmodel.test.mjs</files>
  <behavior>
    - Test D-01/CARD-01: a normalized annotation row becomes a card with selected text preview, comment preview, page label/index, type, color, source, sourceAttachmentKey, sourceAnnotationKey, row identity, sync/read-only metadata, and no action controls.
    - Test D-04/CARD-02: missing selected text and missing comment render as explicit quiet placeholders in the model, not absent fields or collapsed card data.
    - Test D-10 through D-14/CANVAS-04: loaded, empty, missing-paper, missing-db, cli-error, invalid-json, missing-source, unsupported, refreshing, and stale-result inputs produce distinct render states and never convert errors or stale data into empty annotations.
    - Test D-18/D-22: long selected text, long comments, CJK-heavy strings, HTML-like strings, and forbidden write verbs are handled as data with preview metadata and no rendered-control descriptors.
  </behavior>
  <action>Create `view-model.js` with pure CommonJS helpers such as `buildCanvasCard(row, options)`, `buildCanvasCardViewModel(annotationState, options)`, and `normalizeCanvasCardPreview(value, kind)`. Consume the existing normalized row shape from ANN10/v0.2 annotation state only; do not call `loadAnnotationsForPaper`, construct CLI args, import `fs`, import `child_process`, read SQLite/Zotero, or mutate row inputs. Per D-01, each card must carry selected text, comment, page, color/type, source/provenance, attachment identity, annotation identity, and read-only status. Per D-03 and D-21, expose no expandable details, drawers, popovers, editable forms, local mutation state, create/edit/delete/save/import/apply/write-back controls, evidence controls, or concept-card controls. Per D-10 through D-14, represent central surface status separately from side-lane card availability so missing source or unsupported anchoring can be visible while valid cards remain available. Per D-19 and D-20, include restrained `readOnlyLabel`/metadata and source identity fields needed by downstream phases. Export the new helpers from `index.js` without removing ANN10 exports.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; npm.cmd test -- canvas-viewmodel.test.mjs canvas-context.test.mjs canvas-controller.test.mjs annotation-list-viewmodel.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Card models are pure, deterministic, read-only, source-aware, and state-explicit; all D-01/D-03/D-04/D-10-D14/D-18-D22 tests pass without adding loaders, persistence, mutation controls, anchors, navigation, or connectors.</acceptance_criteria>
  <done>`view-model.js`, `canvas-viewmodel.test.mjs`, and `index.js` export updates exist and the focused tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build deterministic reading-order side-lane layout</name>
  <files>paperforge/plugin/src/canvas/layout.js, paperforge/plugin/src/canvas/view-model.js, paperforge/plugin/src/canvas/index.js, paperforge/plugin/tests/canvas-layout.test.mjs</files>
  <behavior>
    - Test D-05/CARD-03: rows are sorted by stable reading/source order before any lane assignment.
    - Test D-06: rows on the same page/source group preserve existing sort/order metadata when available and fall back to stable normalized identity when not.
    - Test D-07: sorted cards alternate left/right by sorted index and produce balanced lanes for odd and even counts.
    - Test D-08/D-09: results are deterministic for the same inputs and include no random, draggable, persisted, localStorage, settings, or Obsidian `.canvas` layout data.
  </behavior>
  <action>Create `layout.js` with helpers such as `compareCanvasCardsByReadingOrder(cardsOrRows)`, `sortCanvasCardsForReadingOrder(cardsOrRows)`, and `assignCanvasCardsToLanes(cards)`. Match the established precedence from `sortAnnotationsForReadingOrder()` in `paperforge/plugin/src/testable.js`: page index first, then sort index, then stable annotation identity; tests may import `sortAnnotationsForReadingOrder()` to prove parity, but shipped `layout.js` must not import `src/testable.js` because that module includes Node/runtime helper code unrelated to canvas rendering. Per D-05 through D-09, assign sorted cards to `{ left: [], right: [] }` by alternation, preserve `lane` and `laneIndex` on derived card copies, avoid mutating inputs, and avoid any persisted or random layout source. Wire `buildCanvasCardViewModel()` to use this lane helper for ready/refreshing/stale-safe card states.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; npm.cmd test -- canvas-layout.test.mjs canvas-viewmodel.test.mjs annotation-list-viewmodel.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Lane assignment is deterministic, alternates left/right after reading-order sorting, preserves source/order identity, and introduces no persistence or deferred card interactions.</acceptance_criteria>
  <done>`layout.js`, layout tests, view-model lane wiring, and export updates exist and pass focused tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| v0.2 annotation state -> card view-model | Imported annotation fields enter the canvas model layer and must be normalized safely. |
| Card model -> lane layout | Source/order metadata drives placement and must remain deterministic. |
| Source/provenance metadata -> downstream phases | Identity fields are preserved without creating unsupported source-anchor or connector claims. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ANN11-01-S | Spoofing | Card source identity | mitigate | Preserve `sourceAttachmentKey`, `sourceAnnotationKey`, page, row id, and source fields; never infer a different paper/source. |
| T-ANN11-01-T | Tampering | Layout state | mitigate | Pure lane assignment only; no random, drag state, settings writes, localStorage, or `.canvas` persistence per D-08. |
| T-ANN11-01-R | Repudiation | Refresh/stale state | mitigate | Distinct view-model states for refresh and stale results so failures are not presented as empty lists. |
| T-ANN11-01-I | Information Disclosure | Error/message fields | mitigate | Model stores concise state messages only; no raw CLI output or stack traces required for cards. |
| T-ANN11-01-D | Denial of Service | Long/CJK text | mitigate | Preview metadata and bounded text flags support DOM/CSS clamps in ANN11-02. |
| T-ANN11-01-E | Elevation of Privilege | Card actions | mitigate | Card model contains no mutation/action descriptors and tests assert forbidden verbs are absent. |
| T-ANN11-01-SC | Tampering | npm installs | accept | No package-manager install is planned; ANN11 uses existing CommonJS/Vitest/jsdom stack only. |

</threat_model>

<verification>

Run from the repository root:

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-context.test.mjs canvas-controller.test.mjs annotation-list-viewmodel.test.mjs
Pop-Location
```

Inspect Vitest output for `Startup Error`, `failed to load config`, and `FAIL`; do not treat a shell exit code alone as sufficient if those strings appear.

</verification>

<success_criteria>

- `paperforge/plugin/src/canvas/view-model.js` and `layout.js` exist and are exported from `index.js`.
- Card view-models display or preserve selected text, comment, page, color/type, source, attachment/provenance, read-only status, row identity, and sync/source metadata.
- Missing selected text/comment values have explicit placeholder model fields.
- Long and CJK-heavy values have preview metadata for bounded rendering and are tested.
- Loaded, empty, missing-paper, missing-db, missing-source, unsupported, cli-error, invalid-json, refresh, and stale-result states are distinct.
- Lane assignment is deterministic by reading/source order, alternates left/right, and uses no random or persisted layout state.
- No create, edit, delete, save, import, apply, write-back, anchor, navigation, connector, direct SQLite/Zotero, or new Python API work appears in this plan.

</success_criteria>
