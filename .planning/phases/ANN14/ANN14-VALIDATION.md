# ANN14 Validation Matrix

**Phase:** ANN14 - Focused Connector Layer and Visual Polish  
**Generated:** 2026-07-06  
**Status:** Planned

## Validation Goal

ANN14 is valid when the Reading Canvas draws a quiet connector only for selected or hovered exact PaperForge-owned card/source pairs, hides every unsupported or unmeasurable connector state, recomputes or clears connector presentation on lifecycle changes, and preserves v0.2 annotation fallback paths without adding mutation, persistence, native PDF DOM coupling, or overstated evidence precision.

## Requirement Coverage

| Requirement | Planned Coverage | Verification |
| --- | --- | --- |
| CANVAS-05 | ANN14-04 preserves existing v0.2 annotation list, page jump, overlay, and explicit fallback paths when canvas connector geometry is unavailable. | `canvas-main-runtime.test.mjs`, `annotation-navigation.test.mjs`, `annotation-main-runtime.test.mjs`, `annotation-section-dom.test.mjs` |
| CONN-01 | ANN14-01 creates exact selected/hovered eligibility; ANN14-02 renders focused SVG; ANN14-03 wires runtime measurement. | `canvas-connectors.test.mjs`, `canvas-render.test.mjs`, `canvas-main-runtime.test.mjs` |
| CONN-02 | ANN14-01/02/03/04 hide page-only, unresolved, stale, source-unavailable, missing, zero-size, offscreen, clipped, and unsupported connectors. | `canvas-connectors.test.mjs`, `canvas-render.test.mjs`, `canvas-card-dom.test.mjs`, `canvas-main-runtime.test.mjs` |
| CONN-03 | ANN14-03 recomputes or clears connectors on selection, hover, scroll, resize, refresh, stale render, paper change, Escape, and teardown. | `canvas-main-runtime.test.mjs` |

## Decision Coverage

| Decision | Planned Verification |
| --- | --- |
| D-01 | Helper, render, and runtime tests prove only `exact` anchors produce visible connector state. |
| D-02 | Tests prove selected or hovered pairs can draw at most one connector; no always-on web is rendered. |
| D-03 | Page-level anchors keep ANN13 selection/group/status styling but produce no connector path. |
| D-04 | Runtime queries only PaperForge-owned `[data-card-id]` and `[data-anchor-id][data-anchor-status="exact"]` inside the Reading Canvas. |
| D-05 | Geometry helper and runtime tests use current DOMRect-like card, anchor, and canvas rectangles. |
| D-06 | Runtime tests cover recomputation after selection, hover, scroll, resize, refresh, paper change, and re-render. |
| D-07 | Missing, zero-size, stale, outside-canvas, clipped, and source-unavailable endpoint tests return hidden connector state. |
| D-08 | Forbidden scans and runtime tests prove no viewport-edge connector lines or offscreen direction hints. |
| D-09 | Refresh, stale render, paper change, Escape, and teardown tests clear connector layer contents. |
| D-10 | CSS tests prove connector stroke is thin, solid, and low-opacity. |
| D-11 | CSS tests prove selected connector is only slightly stronger than hovered connector. |
| D-12 | Forbidden scans prove no arrowheads, endpoint dots, animation, or annotation-color-following connector palettes. |
| D-13 | DOM/CSS tests prove connector classes and SVG are namespaced under `.paperforge-reading-canvas-view` and not emitted for page-level/unresolved states. |
| D-14 | Geometry and responsive CSS tests prove narrow, clipped, offscreen, and unreadable states hide connectors. |
| D-15 | Tests prove no cropped lines, fades, continuation hints, or directional edge badges. |
| D-16 | Runtime tests prove card/source selected/focus/fallback states remain visible when connector hides. |
| D-17 | Connector state is transient runtime presentation; tests and scans prove no settings, localStorage, vault note, database, or layout persistence. |
| D-18 | Forbidden scans prove no create, edit, delete, save, import, apply, write-back, evidence mutation, or concept-card mutation controls. |
| D-19 | Tests prove ANN12 anchor precision and ANN13 fallback/navigation semantics are consumed unchanged; connector hidden states never re-resolve anchors or auto-open PDF. |
| D-20 | Validation notes and scans keep ANN14 scoped to PaperForge Reading Canvas and avoid live native-PDF overlay reliability claims. |

## Source Audit

| Source Type | Item | Covered By |
| --- | --- | --- |
| GOAL | Add the visual relationship layer from the target UI without overstating evidence precision. | ANN14-01, ANN14-02, ANN14-03, ANN14-04 |
| REQ | CANVAS-05 | ANN14-04 |
| REQ | CONN-01 | ANN14-01, ANN14-02, ANN14-03 |
| REQ | CONN-02 | ANN14-01, ANN14-02, ANN14-03, ANN14-04 |
| REQ | CONN-03 | ANN14-01, ANN14-03, ANN14-04 |
| RESEARCH | Pure eligibility before DOM measurement. | ANN14-01 |
| RESEARCH | DOMRect measurement from PaperForge-owned card and exact anchor endpoints. | ANN14-01, ANN14-03 |
| RESEARCH | Namespaced SVG connector layer with restrained visual language. | ANN14-02 |
| RESEARCH | Runtime transient connector state, hover/selection updates, and lifecycle cleanup. | ANN14-03 |
| RESEARCH | Forbidden-scope tests must narrow existing connector/SVG bans without allowing leakage. | ANN14-02, ANN14-04 |
| CONTEXT | Locked decisions D-01 through D-20. | Covered across ANN14-01 through ANN14-04 decision_coverage and task actions |
| CONTEXT | Deferred page-level weak lines, offscreen hints, connector polish, live native-PDF harness, persistence, editing, write-back, AI cards. | Explicitly out of scope in all four plans |

## Focused Verification Commands

```powershell
Push-Location paperforge/plugin
node --check src/canvas/connectors.js
node --check src/canvas/render.js
node --check src/canvas/index.js
node --check main.js
npm.cmd test -- canvas-connectors.test.mjs canvas-navigation.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs
Pop-Location
```

## Forbidden-Scope Scan

Execution should include targeted scans proving ANN14 added only the focused connector layer and did not loosen read-only or native-PDF boundaries. These scans must be scoped to ANN14-owned connector files, connector CSS, and modified canvas tests, or be diff-based against ANN14 changes. They must not treat pre-existing v0.2 annotation list, PDF page jump, overlay, storage, or fallback code as ANN14 failures; those paths are explicitly preserved by CANVAS-05.

```powershell
Push-Location paperforge/plugin
rg -n "marker-end|arrowhead|endpoint-dot|connector-palette|connector-color|connector-animation|always-on connector|page-level connector|unresolved connector|offscreen hint|edge badge|contenteditable|create annotation|edit annotation|delete annotation|write-back|apply annotation" src/canvas/connectors.js src/canvas/render.js tests/canvas-connectors.test.mjs tests/canvas-render.test.mjs tests/canvas-card-dom.test.mjs tests/canvas-main-runtime.test.mjs styles.css
rg -n "pdf-viewer|pdf-embed|data-page-number|localStorage|annotations.db|saveData" src/canvas/connectors.js src/canvas/render.js tests/canvas-connectors.test.mjs tests/canvas-render.test.mjs tests/canvas-card-dom.test.mjs
Pop-Location
```

Expected result: no forbidden native PDF selector in ANN14 connector-owned modules, no new mutation/write-back/persistence control, no page-level/unresolved connector path, no always-on connector web, no arrowhead, no endpoint dot, no offscreen hint, and no heavy connector polish. Occurrences in test names or negative assertions are acceptable only when the assertion is proving absence. Known legacy occurrences in `main.js`, `src/testable.js`, annotation tests, or storage/fallback code are allowed only outside ANN14 connector code and should be protected by CANVAS-05 regression tests rather than removed.

## Success Criteria

1. Connector helper tests prove exact-only selected/hovered eligibility and hidden states for every unsupported condition.
2. Render tests prove the connector SVG layer is namespaced, empty by default, and draws at most one focused exact connector.
3. Runtime tests prove connector geometry updates or clears after selection, hover, scroll, resize, refresh, paper change, Escape, and teardown.
4. Responsive tests prove connectors hide conservatively while ANN13 selected/focus/fallback states remain visible.
5. CANVAS-05 regression tests prove v0.2 annotation list, PDF page jump, overlay, and explicit fallback paths remain available.
6. Forbidden-scope scans prove ANN14 does not add native PDF DOM anchoring, mutation controls, persistence, or deferred connector polish.
