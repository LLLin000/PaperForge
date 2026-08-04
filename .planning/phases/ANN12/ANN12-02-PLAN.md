---
phase: ANN12
plan: "02"
type: execute
wave: 2
depends_on:
  - ANN12-01
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/src/canvas/render.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/i18n.js
  - paperforge/plugin/tests/canvas-render.test.mjs
  - paperforge/plugin/tests/canvas-card-dom.test.mjs
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
requirements:
  - ANCHOR-01
  - ANCHOR-02
requirements_addressed:
  - ANCHOR-01
  - ANCHOR-02
user_setup: []
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
must_haves:
  truths:
    - "D-01/D-02/D-03/D-17: Runtime source loading reads entry.fulltext_path first, falls back to entry.note_path, distinguishes missing path from missing/unreadable file where practical, and passes source-unavailable diagnostics to the canvas model."
    - "D-04/D-05/D-26: DOM rendering remains PaperForge-owned, uses safe text insertion for source/annotation/note text, and does not use native PDF selectors/classes or Obsidian PDF viewer internals."
    - "D-06/D-07/D-08/D-09/D-10: The central source surface visibly distinguishes exact, page-level, and unresolved anchors, with inline highlights only for exact anchors."
    - "D-11/D-12/D-13/D-14: Render/runtime tests prove unique-match exact anchors, ambiguous/short/missing/source-mismatch downgrades, and preserved diagnostics."
    - "D-15/D-16/D-18: Annotation cards remain visible when source content is missing, and source unavailable never masquerades as an empty annotation state."
    - "D-19/D-20/D-21/D-22: Exact anchors render restrained inline highlights, page-level anchors render page/block markers, unresolved anchors render explanation text only, and all ANN12 visual classes are namespaced without connector-line or geometry classes."
    - "D-23/D-24/D-25: Rendered anchors expose identity/status/source span/page block/reason/provenance while adding no card-source navigation, source-card focus, keyboard selection sync, SVG connectors, edit/import/apply/write-back, or mutation controls."
    - "Context decision coverage in this plan: D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-19 D-20 D-21 D-22 D-23 D-24 D-25 D-26."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Narrow runtime source read adapter for Reading Canvas source inputs"
    - path: "paperforge/plugin/src/canvas/render.js"
      provides: "Central source surface, exact highlights, page-level markers, and unresolved status DOM"
    - path: "paperforge/plugin/styles.css"
      provides: "Namespaced source surface and anchor status styling"
    - path: "paperforge/plugin/i18n.js"
      provides: "Scoped zh/en source and anchor status copy"
    - path: "paperforge/plugin/tests/canvas-render.test.mjs"
      provides: "DOM safety, exact/page/unresolved rendering, source unavailable, and forbidden selector/control coverage"
    - path: "paperforge/plugin/tests/canvas-card-dom.test.mjs"
      provides: "CSS hook and cards-remain-visible source-missing coverage"
    - path: "paperforge/plugin/tests/canvas-main-runtime.test.mjs"
      provides: "Runtime source loading, source priority, and no native PDF/connector/navigation regression tests"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/canvas/surface.js"
      via: "runtime sourceInputs passed into buildCanvasSourceModel or buildCanvasCardViewModel"
      pattern: "fulltext_path before note_path before source-unavailable"
    - from: "paperforge/plugin/src/canvas/render.js"
      to: "paperforge/plugin/src/canvas/anchors.js"
      via: "anchor.status and span/page diagnostics"
      pattern: "exact highlights only; page-level marker; unresolved explanation"
    - from: "paperforge/plugin/styles.css"
      to: "paperforge/plugin/src/canvas/render.js"
      via: "paperforge-canvas-source and paperforge-canvas-anchor namespaced classes"
      pattern: "no paperforge-canvas-connector; no svg connector path"
---

<objective>
Load source content at runtime and render the ANN12 central source surface with safe, visible source anchor statuses.

Purpose: turn ANN12-01 source and anchor contracts into the user-visible PaperForge-owned reading surface while preserving the read-only and no-native-PDF boundaries.
Output: a narrow `main.js` source adapter, central source DOM rendering, namespaced CSS, scoped i18n copy, and focused DOM/runtime tests for exact/page-level/unresolved anchors, safe rendering, source unavailable, forbidden selectors/classes, and card visibility when source is missing.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/ANN12/ANN12-CONTEXT.md
@.planning/phases/ANN12/ANN12-RESEARCH.md
@.planning/phases/ANN12/ANN12-01-PLAN.md
@.planning/phases/ANN11/ANN11-01-SUMMARY.md
@.planning/phases/ANN11/ANN11-02-SUMMARY.md
@paperforge/plugin/package.json
@paperforge/plugin/main.js
@paperforge/plugin/src/canvas/surface.js
@paperforge/plugin/src/canvas/anchors.js
@paperforge/plugin/src/canvas/view-model.js
@paperforge/plugin/src/canvas/render.js
@paperforge/plugin/src/canvas/index.js
@paperforge/plugin/styles.css
@paperforge/plugin/i18n.js
@paperforge/plugin/tests/canvas-render.test.mjs
@paperforge/plugin/tests/canvas-card-dom.test.mjs
@paperforge/plugin/tests/canvas-main-runtime.test.mjs
</context>

<source_audit>
SOURCE | ID | Feature/Requirement | Plan | Status | Notes
GOAL | ANN12 | PaperForge-owned central reading surface with measurable source grounding | ANN12-01 and ANN12-02 | COVERED | This plan renders the source surface and runtime loading path.
REQ | ANCHOR-01 | Source anchors render for supported PaperForge-owned position, text, or page data | ANN12-02 | COVERED | Exact and page-level DOM render from ANN12-01 anchor models.
REQ | ANCHOR-02 | Page-level or unresolved fallback anchors render when exact anchoring is unavailable | ANN12-02 | COVERED | Page markers and unresolved explanation copy are first-class DOM states.
RESEARCH | Runtime file reading stays narrow, helpers remain pure | ANN12-02 | COVERED | `main.js` adapts vault reads and delegates modeling/rendering to `src/canvas`.
RESEARCH | Safe DOM, no native PDF internals, no connectors/navigation | ANN12-02 | COVERED | DOM/runtime/static tests scan for unsafe insertion, forbidden selectors, connector classes, SVG paths, and deferred interactions.
CONTEXT | D-01 through D-26 | ANN12-02 | COVERED | All decisions cited in truths and task actions; ANN12-01 owns pure contracts and this plan owns runtime/DOM/CSS.
</source_audit>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add narrow runtime source loading for the Reading Canvas</name>
  <files>paperforge/plugin/main.js, paperforge/plugin/tests/canvas-main-runtime.test.mjs</files>
  <behavior>
    - Test D-01/D-02/D-03: `PaperForgeReadingCanvasView` attempts `entry.fulltext_path` first, then `entry.note_path`, then source-unavailable inputs when neither can be read.
    - Test D-17: runtime distinguishes missing path from missing file/unreadable content where the Obsidian vault APIs expose those outcomes.
    - Test D-15/D-16/D-18: missing source leaves annotation/card state available and does not render or model a false empty-annotations state.
    - Test D-04/D-24/D-25/D-26: runtime adds no native PDF DOM selectors, no PDF canvas probing, no card-source navigation, no source-card focus, no connector/SVG geometry, and no mutation/write controls.
  </behavior>
  <action>Extend `PaperForgeReadingCanvasView` in `paperforge/plugin/main.js` with a narrow async source-input adapter for the existing explicit paper entry. Keep `setPaperContext()` as the owner of explicit paper identity. Add helper methods with clear names such as `_loadCanvasSourceInputs(entry)` and `_readVaultText(path, sourceKind)` that use Obsidian vault APIs already present in this file: `app.vault.getAbstractFileByPath(path)` and `app.vault.read(file)` for files that exist, or `app.vault.adapter.read(path)` only if that is the existing path-correct pattern needed for raw adapter reads. The helper must return structured source inputs for ANN12-01 helpers, not parse anchors or render DOM in `main.js`. It must read `entry.fulltext_path` before `entry.note_path`, preserve missing-path and missing-file/read-error reasons where practical, and pass the resulting data into `buildCanvasSourceModel()` or `buildCanvasCardViewModel()` through `src/canvas` delegation. Guard stale async loads with the existing canvas context/session identity so source text from a previous paper cannot overwrite the current canvas. Do not add direct SQLite/Zotero/Python subprocess calls, new commands, new view registration, new paper-panel buttons, native PDF DOM selectors/classes, card/source navigation, selection sync, connector geometry, SVG paths, editing/import/apply/write-back controls, localStorage, settings writes, or persistent layout writes.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- canvas-main-runtime.test.mjs canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Runtime source loading is priority-ordered, identity-guarded, narrow, and delegates source/anchor modeling to ANN12-01 helpers without expanding plugin runtime ownership or deferred interactions.</acceptance_criteria>
  <done>`main.js` runtime source loading and focused runtime tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Render central source surface and anchor statuses safely</name>
  <files>paperforge/plugin/src/canvas/render.js, paperforge/plugin/i18n.js, paperforge/plugin/tests/canvas-render.test.mjs</files>
  <behavior>
    - Test D-06 through D-10/D-19/D-20/D-21: exact anchors render restrained inline highlights, page-level anchors render page/block markers, and unresolved anchors render explanation text only.
    - Test D-05: source text, note text, selected text, comments, and unresolved reasons are inserted only with `textContent`, text nodes, or equivalent safe APIs, never `innerHTML`.
    - Test D-10: exact, page-level, and unresolved statuses are visually and structurally distinguishable by namespaced classes and visible copy.
    - Test D-22/D-24: DOM contains no connector-line classes, no SVG connector paths, no card-source/source-card navigation hooks, and no selection-sync classes or handlers.
    - Test D-03/D-15/D-16/D-18: source unavailable renders an explicit central state while existing cards remain visible if annotations exist.
  </behavior>
  <action>Extend `paperforge/plugin/src/canvas/render.js` to render a central PaperForge-owned source surface from the ANN12-01 source and anchor view-model data. Add helpers such as `renderCanvasSourceSurface(contentEl, vm)`, `renderSourceBlock(block, anchors)`, `renderExactAnchorText(...)`, `renderPageLevelAnchorMarker(...)`, and `renderUnresolvedAnchorStatus(...)` if those names fit the existing style. Exact anchors may split a source text block into text nodes and a highlighted span only for the raw span provided by the anchor resolver. Page-level anchors must render block/page markers or a source strip marker and must not highlight a sentence or paragraph as exact. Unresolved anchors must render status/explanation text and no source marker. All new text must use safe insertion through `textContent`, text nodes, or `createEl(..., { text })`; do not use `innerHTML` for source, annotation, note, reason, or status content. Add scoped zh/en i18n keys in `paperforge/plugin/i18n.js` for source labels, source unavailable copy, exact/page-level/unresolved labels, downgrade reasons that are visible, and source-kind labels. Use namespaced classes under the existing Reading Canvas namespace, such as `paperforge-canvas-source-surface`, `paperforge-canvas-source-block`, `paperforge-canvas-anchor`, `paperforge-canvas-anchor--exact`, `paperforge-canvas-anchor--page-level`, and `paperforge-canvas-anchor--unresolved`. Do not add `paperforge-canvas-connector`, SVG paths, click/scroll/focus behavior, keyboard selection sync, fallback PDF navigation actions, draggable handles, edit/write controls, or native PDF DOM selectors/classes.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check src/canvas/render.js; npm.cmd test -- canvas-render.test.mjs canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>The DOM shows central source content, exact/page-level/unresolved anchors, explicit source unavailable state, safe text rendering, and no deferred navigation/connector/write surfaces.</acceptance_criteria>
  <done>`render.js`, `i18n.js`, and render tests prove central source and anchor status rendering.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add source/anchor CSS and final ANN12 safety gates</name>
  <files>paperforge/plugin/styles.css, paperforge/plugin/tests/canvas-card-dom.test.mjs, paperforge/plugin/tests/canvas-render.test.mjs, paperforge/plugin/tests/canvas-main-runtime.test.mjs</files>
  <behavior>
    - Test D-19/D-20/D-21/D-22: CSS classes distinguish exact highlight, page-level marker, and unresolved status without connector or geometry classes.
    - Test D-04/D-26: static/runtime scans fail if `.pdf-viewer`, `.pdf-embed`, `[data-page-number]`, PDF page canvas anchoring, or Obsidian native PDF viewer selector logic appears in ANN12 files.
    - Test D-24/D-25: runtime DOM contains no card-source navigation, source-card focus, selection sync, SVG connector paths, create/edit/delete/save/import/apply/write-back/evidence mutation controls, or concept-card mutation controls.
    - Test D-15/D-16/D-18: cards remain visible beside the central source-unavailable state when annotations exist but source cannot be grounded.
    - Test D-05: source and annotation HTML-like strings remain literal text in DOM and do not create script, image, onclick, or anchor elements.
  </behavior>
  <action>Add namespaced CSS to `paperforge/plugin/styles.css` for the central source surface and anchor statuses. Use stable dimensions and readable overflow behavior for the central source column so long fulltext and CJK-heavy text do not overlap the card lanes. Exact highlight styling must be restrained and may use annotation color when supplied, but it must preserve readability. Page-level markers must look like page/block status markers, not inline exact highlights. Unresolved styling must be explanatory/status-oriented and must not imply a source span. Add or extend DOM/runtime tests to verify the source surface and card lanes coexist, cards remain visible when source is unavailable, HTML-like source and annotation strings are safe text, forbidden native PDF selectors/classes are absent from the changed files, and connector/navigation/mutation surfaces remain absent. Keep CSS under the PaperForge Reading Canvas namespace. Do not introduce SVG geometry, connector classes, hover/selected line drawing, native PDF DOM anchoring, persistent layout, localStorage/settings writes, card-source/source-card navigation, selection sync, edit/import/apply/write-back controls, or new package dependencies.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; node --check src/canvas/render.js; npm.cmd test -- canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs canvas-layout.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>CSS and runtime gates prove the central source surface is readable, anchor precision is visually honest, safe rendering holds, forbidden selectors/classes are absent, and v0.2/ANN11 card surfaces remain unregressed.</acceptance_criteria>
  <done>`styles.css` and focused DOM/runtime gates pass for source surface rendering and ANN12 scope boundaries.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Obsidian vault file read -> main.js source adapter | User vault fulltext/note content crosses into runtime source inputs. |
| ANN12-01 source/anchor model -> render.js | Anchor spans and downgrade reasons become visible DOM. |
| render.js/styles.css -> user Reading Canvas | Visual precision can mislead users if status distinctions are weak. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ANN12-02-S | Spoofing | Runtime source identity | mitigate | Use explicit canvas paper context and stale guards; source from a prior paper cannot overwrite the active paper. |
| T-ANN12-02-T | Tampering | DOM rendering | mitigate | Use textContent/text nodes for all source and annotation-derived content; no innerHTML for ANN12 content. |
| T-ANN12-02-R | Repudiation | Anchor downgrade UI | mitigate | Render reason/status text for page-level and unresolved anchors so downgraded evidence is auditable. |
| T-ANN12-02-I | Information Disclosure | Source read errors | mitigate | Visible copy uses concise source availability reasons, not stack traces or raw adapter errors. |
| T-ANN12-02-D | Denial of Service | Long source text DOM | mitigate | Bounded source block rendering and CSS overflow/wrapping keep the surface readable under large source content. |
| T-ANN12-02-E | Elevation of Privilege | Runtime controls | mitigate | Tests assert no edit/import/apply/write-back/evidence mutation controls and no deferred navigation/connector handlers. |
| T-ANN12-02-SC | Tampering | npm installs | accept | No package-manager install is planned; use existing CommonJS/Vitest/jsdom stack only. |

</threat_model>

<verification>

Run from the repository root:

```powershell
Push-Location paperforge/plugin
node --check main.js
node --check src/canvas/render.js
npm.cmd test -- canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs canvas-layout.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs
Pop-Location
```

After tests pass, run static source checks from the repository root:

```powershell
Select-String -Path paperforge/plugin/main.js,paperforge/plugin/src/canvas/*.js,paperforge/plugin/styles.css -Pattern '\.pdf-viewer|\.pdf-embed|\[data-page-number\]|paperforge-canvas-connector|<svg|createElement\(''svg''|innerHTML' -CaseSensitive
```

Any `innerHTML` hit must be inspected. Existing non-ANN12 SVG/icon uses may remain only when they are outside source, annotation, note, reason, and anchor rendering paths. Any native PDF selector, connector class, ANN12 SVG connector, or unsafe ANN12 content insertion hit fails the plan.

</verification>

<success_criteria>

- Runtime source loading prefers `entry.fulltext_path`, then `entry.note_path`, then explicit source-unavailable diagnostics.
- Missing path and missing/unreadable file cases remain distinguishable where Obsidian APIs expose that information.
- The central source surface renders PaperForge-owned source text/page blocks safely.
- Exact anchors render only restrained inline highlights from unique owned-source spans.
- Page-level anchors render block/page markers and never inline highlights.
- Unresolved anchors render explanation/status text only.
- Cards remain visible when source content is missing or ungroundable.
- All visual classes are namespaced under the PaperForge Reading Canvas namespace.
- No native PDF DOM selectors/classes, PDF canvas anchoring, Obsidian PDF viewer dependence, connector classes, SVG connector geometry, card-source/source-card navigation, selection sync, editing/import/apply/write-back controls, evidence mutation controls, or concept-card mutation controls are introduced.
- `node --check` and focused Vitest gates pass after output inspection.

</success_criteria>
