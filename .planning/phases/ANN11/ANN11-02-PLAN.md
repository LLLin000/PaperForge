---
phase: ANN11
plan: "02"
type: implementation
wave: 2
depends_on:
  - ANN10-02
  - ANN11-01
files_modified:
  - paperforge/plugin/src/canvas/render.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/i18n.js
  - paperforge/plugin/main.js
  - paperforge/plugin/tests/canvas-render.test.mjs
  - paperforge/plugin/tests/canvas-card-dom.test.mjs
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
requirements:
  - CANVAS-03
  - CANVAS-04
  - CARD-01
  - CARD-02
  - CARD-04
requirements_addressed:
  - CANVAS-03
  - CANVAS-04
  - CARD-01
  - CARD-02
  - CARD-04
autonomous: true
decision_coverage:
  - D-01
  - D-02
  - D-03
  - D-04
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
must_haves:
  truths:
    - "CANVAS-03: User sees the PaperForge Reading Canvas central surface with deterministic left and right annotation card lanes rendered from ANN11-01 view-model/layout outputs."
    - "CANVAS-04: Loaded, empty, missing paper, missing annotation database, missing source, command failure, refresh, and stale-result states remain explicit in DOM rendering and never collapse into a false empty card list."
    - "CARD-01: Each rendered card shows selected text preview, comment preview, page, color/type, source/provenance, and read-only status."
    - "CARD-02: Long, missing, and CJK-heavy selected text/comment values render through bounded, resilient DOM/CSS hooks without stretching lanes or overlapping metadata."
    - "CARD-04: Rendered cards preserve source identity/provenance for later evidence workflows and expose no create/edit/delete/save/import/apply/write-back controls."
    - "Runtime integration with paperforge/plugin/main.js is blocked until ANN10-02 Reading Canvas ItemView, command, and paper-panel button wiring are present; if absent, the executor stops with a checkpoint instead of inventing upstream runtime wiring in ANN11."
    - "Context decision coverage in this plan: D-01 D-02 D-03 D-04 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-19 D-20 D-21 D-22."
  artifacts:
    - path: "paperforge/plugin/src/canvas/render.js"
      provides: "Central surface plus left/right card lane DOM rendering from ANN11-01 card view-model output"
    - path: "paperforge/plugin/styles.css"
      provides: "Namespaced resilient Reading Canvas card/lane styles"
    - path: "paperforge/plugin/i18n.js"
      provides: "Scoped zh/en visible text keys for ANN11 card labels, placeholders, provenance, read-only badges, and state copy"
    - path: "paperforge/plugin/main.js"
      provides: "Narrow runtime delegation update only if ANN10-02 runtime wiring is already complete"
    - path: "paperforge/plugin/tests/canvas-render.test.mjs"
      provides: "Canvas render state, lane, card field, source/provenance, and forbidden-control coverage"
    - path: "paperforge/plugin/tests/canvas-card-dom.test.mjs"
      provides: "DOM/CSS-hook coverage for cards, long/missing/CJK text, placeholders, and read-only badges"
    - path: "paperforge/plugin/tests/canvas-main-runtime.test.mjs"
      provides: "Runtime regression coverage behind the ANN10-02 pre-flight gate"
  key_links:
    - from: "paperforge/plugin/src/canvas/render.js"
      to: "paperforge/plugin/src/canvas/view-model.js"
      via: "ANN11-01 buildCanvasCardViewModel output"
      pattern: "render uses card lanes/viewModel; no annotation loader"
    - from: "paperforge/plugin/src/canvas/render.js"
      to: "paperforge/plugin/src/canvas/layout.js"
      via: "ANN11-01 deterministic lane assignments"
      pattern: "render lanes from left/right card arrays; no drag or persistence"
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/canvas/index.js"
      via: "existing ANN10-02 Reading Canvas ItemView delegation"
      pattern: "only after pre-flight proves VIEW_TYPE_PAPERFORGE_READING_CANVAS and PaperForgeReadingCanvasView exist"
---

<objective>
Render ANN11 annotation cards into resilient left/right Reading Canvas lanes and add the guarded runtime integration/regression checks after ANN10-02.

Purpose: turn the pure card view-model and deterministic lane outputs from ANN11-01 into safe, read-only DOM/CSS while preserving ANN10's runtime ownership of the Reading Canvas view.
Output: card lane DOM rendering, namespaced resilient CSS, focused DOM/render tests, and runtime regression coverage that runs only after the ANN10-02 pre-flight gate passes.
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
@.planning/phases/ANN11/ANN11-01-PLAN.md
@.planning/phases/ANN10/ANN10-02-PLAN.md
@paperforge/plugin/package.json
@paperforge/plugin/main.js
@paperforge/plugin/styles.css
@paperforge/plugin/i18n.js
@paperforge/plugin/src/canvas/index.js
@paperforge/plugin/src/canvas/view-model.js
@paperforge/plugin/src/canvas/layout.js
@paperforge/plugin/src/canvas/render.js
@paperforge/plugin/tests/canvas-render.test.mjs
@paperforge/plugin/tests/canvas-main-runtime.test.mjs
@paperforge/plugin/tests/annotation-section-dom.test.mjs
@paperforge/plugin/tests/annotation-main-runtime.test.mjs
</context>

<source_audit>
GOAL: Covers the Phase ANN11 user-visible card lane step by rendering read-only annotation cards around the central Reading Canvas surface after pure card state/lane contracts exist.
REQ: CANVAS-03 is covered by central surface plus left/right lane DOM. CANVAS-04 is covered by explicit state rendering. CARD-01 and CARD-04 are covered by visible card fields, read-only/provenance metadata, and forbidden-control gates. CARD-02 is covered by bounded DOM/CSS hooks and long/missing/CJK tests.
RESEARCH: Implements the recommended Plan ANN11-02 split: `render.js`, `styles.css`, DOM tests, and runtime regression only after confirming ANN10-02 runtime view/command/button wiring. No new packages are installed.
CONTEXT: Implements D-01, D-02, D-03, D-04, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-19, D-20, D-21, and D-22. Consumes ANN11-01 outputs for D-05 through D-09 lane ordering without reimplementing layout persistence or draggable behavior.
</source_audit>

<runtime_gate>
`paperforge/plugin/main.js` integration is blocked until ANN10-02 Reading Canvas runtime wiring exists in the active worktree. The executor must run Task 1 before editing any file. If Task 1 cannot prove the ANN10-02 `ItemView`, command, paper-panel button, explicit `paperKey` path, and `src/canvas` delegation are present, stop the plan and report `CHECKPOINT: ANN10-02 incomplete`; do not create replacement view registration, button wiring, commands, loaders, or runtime identity resolution in ANN11.
</runtime_gate>

<tasks>

<task type="auto">
  <name>Task 1: Pre-flight ANN10-02 runtime gate before any main.js work</name>
  <files>paperforge/plugin/main.js, paperforge/plugin/tests/canvas-main-runtime.test.mjs, paperforge/plugin/tests/canvas-section-dom.test.mjs</files>
  <action>Before modifying any file, verify ANN10-02 is complete in the active worktree. Confirm `main.js` already contains a dedicated Reading Canvas view type such as `VIEW_TYPE_PAPERFORGE_READING_CANVAS`, `PaperForgeReadingCanvasView`, view registration in plugin load, a command for opening the Reading Canvas for the active paper, a paper-panel button that passes the current entry key, and CommonJS delegation to `./src/canvas`. Confirm runtime tests from ANN10-02 exist and cover view registration, explicit `paperKey`, missing-paper Notice behavior, no auto-switch on unrelated active paper changes, and the paper-panel button path. Run the focused ANN10 runtime gate below. If any check fails, stop with `CHECKPOINT: ANN10-02 incomplete`, leave `main.js` unchanged, do not proceed to runtime regression work, and do not invent ANN10 runtime wiring in this ANN11 plan.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- canvas-main-runtime.test.mjs canvas-section-dom.test.mjs canvas-render.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>The active worktree already has ANN10-02 Reading Canvas ItemView/command/button wiring and focused runtime tests; otherwise execution stops before any file edit.</acceptance_criteria>
  <done>Pre-flight passes and the executor may continue, or a checkpoint is reported with no ANN11 runtime invention.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Render read-only card lanes from ANN11-01 view-model output</name>
  <files>paperforge/plugin/src/canvas/render.js, paperforge/plugin/i18n.js, paperforge/plugin/tests/canvas-render.test.mjs, paperforge/plugin/tests/canvas-card-dom.test.mjs</files>
  <behavior>
    - Test D-01/D-02/CARD-01: rendered cards show selected text preview, comment preview, page, color/type, source/provenance, attachment/source identity where available, and a restrained read-only badge or chip.
    - Test D-03/D-21/D-22/CARD-04: card DOM contains no expandable details, drawers, popovers, editable forms, create/edit/delete/save/import/apply/write-back controls, evidence controls, concept-card controls, anchors, source navigation, connectors, or draggable handles.
    - Test D-04/D-18/CARD-02: missing selected text and missing comment values render explicit quiet placeholders, and long/CJK-heavy values are present as text with stable class hooks for bounded display.
    - Test D-10 through D-14/CANVAS-04: loaded, empty, missing-paper, missing-db, missing-source, unsupported, command failure, refresh, and stale-result states render distinct central/lane states; errors and stale states never masquerade as an empty card list.
  </behavior>
  <action>Extend `src/canvas/render.js` so the Reading Canvas renderer consumes the ANN11-01 card view-model/lane output, not raw annotation loader results. Keep the central PaperForge-owned status/surface area from ANN10 while adding left and right lane containers such as `.paperforge-canvas-lanes`, `.paperforge-canvas-lane-left`, and `.paperforge-canvas-lane-right` only when annotation card data is loaded and usable per D-10. Add scoped `zh`/`en` entries to `paperforge/plugin/i18n.js` for new visible ANN11 card labels, missing-text placeholders, read-only/provenance badges, and card/state copy; do not expand i18n cleanup to unrelated ANN10 shell text. Render each card with namespaced elements for selected text, comment, page, color/type, source/provenance, and read-only status per D-01, D-02, D-19, and D-20. Use safe text insertion (`textContent`, existing safe DOM helpers, or equivalent element creation); do not use `innerHTML` with annotation fields. Preserve Plan 01 lane order and `lane`/`laneIndex` outputs rather than sorting again in the DOM. For missing source or unsupported future anchoring, keep cards visible when metadata is otherwise valid and expose the limitation as provenance/status text per D-14. Do not add source anchors, card-to-source navigation, source-to-card navigation, connector lines, draggable/freeform layout, persistent layout state, edit/write controls, new dependencies, direct database/Zotero reads, or Python/API calls.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check src/canvas/render.js; npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs annotation-section-dom.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Canvas DOM renders central status/surface plus safe read-only left/right card lanes from Plan 01 output, visible ANN11 labels/placeholders use scoped bilingual i18n keys, and explicit non-ready states expose no forbidden controls or deferred interaction surfaces.</acceptance_criteria>
  <done>`render.js`, `i18n.js`, `canvas-render.test.mjs`, and `canvas-card-dom.test.mjs` prove card lane DOM, state rendering, safe text insertion, placeholders, and read-only/provenance fields.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add resilient card/lane CSS and guarded runtime regression</name>
  <files>paperforge/plugin/styles.css, paperforge/plugin/i18n.js, paperforge/plugin/main.js, paperforge/plugin/tests/canvas-card-dom.test.mjs, paperforge/plugin/tests/canvas-main-runtime.test.mjs</files>
  <behavior>
    - Test D-15/D-16/D-17/CARD-02: card lane CSS exposes stable dimensions, bounded previews, safe wrapping for long and CJK-heavy content, fixed badge/status geometry, and no viewport-scaled fonts, negative spacing tricks, or layout-shifting hover/focus states.
    - Test D-10/D-13/CANVAS-04: refresh/stale-safe classes are visible when existing cards remain during refresh; otherwise the renderer shows a clear refreshing state without stale cards.
    - Test runtime gate: after Task 1 passes, runtime tests confirm `main.js` continues to use ANN10-02's Reading Canvas ItemView/button and delegates rendering to `src/canvas` without adding a second loader or duplicate view wiring.
    - Test i18n: new ANN11 card labels/placeholders/read-only/provenance/status strings exist in both `zh` and `en` dictionaries and are used by render/runtime tests where visible.
    - Test D-21/D-22: the runtime Reading Canvas surface and card lane DOM contain no create/edit/delete/save/import/apply/write-back/evidence/concept-card controls or labels.
  </behavior>
  <action>Add namespaced CSS to `styles.css` for the Reading Canvas lane/card elements created in Task 2. Use stable lane/card sizing with responsive constraints, bounded preview blocks, maximum card height, overflow handling, CJK-safe wrapping, and restrained read-only/provenance badges per D-15 through D-17. Keep typography fixed or token-based; do not scale font size with viewport width and do not use negative letter spacing. Style hover/focus/read-only/status states so they do not resize lanes or cards. After Task 1 pre-flight passes, add only the narrowest `main.js` integration needed for ANN10-02's existing Reading Canvas view to receive/render the ANN11 card view-model path; if ANN10-02 already delegates generically to `src/canvas/render.js`, leave `main.js` unchanged and add regression coverage instead. Runtime tests must stay behind the pre-flight gate and must not create a new `ItemView`, command, paper-panel button, active-paper resolver, annotation loader, direct DB/Zotero/Python/API path, source anchor, navigation handler, connector renderer, draggable layout, persistence layer, or write controls.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- canvas-card-dom.test.mjs canvas-render.test.mjs canvas-main-runtime.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>CSS keeps card lanes stable for long/missing/CJK content, runtime regression proves ANN10-02 wiring remains the owner of view/button integration, and focused v0.2 annotation safety gates remain green.</acceptance_criteria>
  <done>`styles.css` and guarded runtime/DOM tests prove resilient card lane display, no forbidden controls, and no ANN11 runtime ownership creep.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ANN11-01 card view-model -> render.js | Render receives annotation-derived text/provenance and must insert it safely. |
| render.js -> browser DOM/CSS | Long, missing, CJK, and HTML-like fields cross into visible canvas lanes. |
| ANN10-02 runtime -> ANN11 render path | `main.js` may delegate into card rendering only after upstream ItemView/button wiring exists. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ANN11-02-S | Spoofing | Card provenance DOM | mitigate | Render source, attachment, page, and source annotation identity from ANN11-01 card model fields without inventing source anchors or navigation claims. |
| T-ANN11-02-T | Tampering | Runtime integration | mitigate | Pre-flight ANN10-02 before touching `main.js`; stop if view/button wiring is missing instead of reimplementing it. |
| T-ANN11-02-R | Repudiation | Refresh/stale rendering | mitigate | Distinct DOM states and tests for refresh/stale so stale data is visibly marked or hidden behind a clear refreshing state. |
| T-ANN11-02-I | Information Disclosure | Annotation text DOM | mitigate | Use safe text insertion for selected text, comment, and provenance; tests include HTML-like strings. |
| T-ANN11-02-D | Denial of Service | Long/CJK card content | mitigate | CSS clamps, max heights, overflow wrapping, and DOM tests for long and CJK-heavy values. |
| T-ANN11-02-E | Elevation of Privilege | Card/runtime controls | mitigate | No create/edit/delete/save/import/apply/write-back/evidence/concept controls; DOM and runtime tests assert forbidden verbs are absent. |
| T-ANN11-02-SC | Tampering | npm installs | accept | No new dependency or package-manager install is planned; use existing CommonJS/Vitest/jsdom stack. |

</threat_model>

<verification>

Run from the repository root after all tasks pass the pre-flight gate:

```powershell
Push-Location paperforge/plugin
node --check main.js
npm.cmd test -- canvas-card-dom.test.mjs canvas-render.test.mjs canvas-main-runtime.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs
Pop-Location
```

Inspect Vitest output for `Startup Error`, `failed to load config`, and `FAIL`; do not treat a shell exit code alone as sufficient if those strings appear.

</verification>

<success_criteria>

- Pre-flight proves ANN10-02 Reading Canvas ItemView, command, paper-panel button, explicit paper identity, and `src/canvas` runtime delegation exist before any `main.js` integration.
- If ANN10-02 runtime wiring is absent, execution stops with `CHECKPOINT: ANN10-02 incomplete` and does not invent runtime wiring in ANN11.
- The Reading Canvas renders a central PaperForge-owned surface plus left/right annotation card lanes from ANN11-01 view-model/layout outputs.
- Rendered cards show selected text, comment, page, color/type, source/provenance, attachment identity where available, and read-only status.
- Missing selected text/comment values render quiet explicit placeholders.
- Long and CJK-heavy selected text/comment values have bounded DOM/CSS hooks and stable lane/card geometry.
- Loaded, empty, missing-paper, missing-db, missing-source, unsupported, command failure, refresh, and stale-result states remain visibly distinct.
- Runtime/card DOM contains no source anchors, navigation, connectors, draggable layout, persistent layout, edit/write controls, new dependencies, direct DB/Zotero calls, or Python/API paths.
- `node --check main.js` and the focused Vitest gates pass after output inspection.

</success_criteria>
