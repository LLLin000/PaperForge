# Phase ANN11 Validation Plan

**Phase:** ANN11 - Annotation Card View-Models and Layout
**Created:** 2026-07-05
**Status:** Ready for plan gate review
**Scope:** CANVAS-03, CANVAS-04, CARD-01, CARD-02, CARD-03, CARD-04

## Validation Strategy

ANN11 validates the card layer in two waves. Wave 1 proves pure card view-models and deterministic lane assignment without touching runtime DOM integration. Wave 2 proves DOM/CSS rendering only after the ANN10-02 Reading Canvas runtime gate passes.

The phase remains read-only and local to the existing Obsidian plugin stack. Validation uses focused Vitest/jsdom tests, `node --check`, and existing v0.2 annotation regression gates. No Python, new subprocess API, direct SQLite/Zotero access, new package install, persistent layout, source anchors, navigation, or connector geometry is part of this validation plan.

## Requirement Coverage Matrix

| Requirement | Validation Evidence | Plans | Gate |
|---|---|---|---|
| CANVAS-03 | DOM tests for central surface plus left/right card lanes rendered from ANN11-01 lane output | 02 | Card lanes appear only from loaded usable card states and preserve central surface/status area |
| CANVAS-04 | View-model and render tests for loaded, empty, missing paper, missing DB, missing source, command failure, refresh, and stale-result states | 01, 02 | Error/stale states remain distinct and never collapse into a false empty list |
| CARD-01 | Card view-model and DOM tests for selected text, comment, page, color/type, source, attachment/provenance, and read-only status | 01, 02 | Required fields are present in model and rendered card DOM |
| CARD-02 | Unit/DOM/CSS-hook tests for long, missing, and CJK-heavy selected text/comment values | 01, 02 | Long/CJK/missing content has bounded preview metadata, safe wrapping hooks, and no overlap-prone controls |
| CARD-03 | Pure layout tests for reading-order sorting and left/right alternation | 01 | Same input always yields the same sorted cards and lane assignment with no random or persisted layout state |
| CARD-04 | Model/DOM/runtime tests for source identity preservation and forbidden control absence | 01, 02 | Source/provenance identity remains available and no create/edit/delete/save/import/apply/write-back affordance appears |

## Wave Validation

### Wave 1: Card View-Models And Deterministic Layout

- Add `paperforge/plugin/src/canvas/view-model.js` and `layout.js`.
- Export ANN11 helpers through `paperforge/plugin/src/canvas/index.js`.
- Add `canvas-viewmodel.test.mjs` and `canvas-layout.test.mjs`.
- Gate: helpers consume existing normalized annotation state only, preserve source/provenance/read-only metadata, distinguish all required states, and assign lanes deterministically.

### Wave 2: Card Lane DOM, CSS, And Runtime Gate

- Before touching runtime integration, verify ANN10-02 Reading Canvas ItemView, command, paper-panel button, explicit `paperKey` path, runtime tests, and `src/canvas` delegation exist.
- If the gate fails, stop with `CHECKPOINT: ANN10-02 incomplete`.
- Add DOM rendering tests for card lanes, safe text insertion, placeholders, provenance/read-only badges, and forbidden controls.
- Add namespaced CSS tests/hooks for bounded card previews, stable lane/card geometry, and CJK-safe wrapping.
- Add scoped `zh`/`en` `i18n.js` keys for visible ANN11 labels/placeholders/status copy.
- Gate: runtime remains owned by ANN10-02; ANN11 only renders cards through the existing canvas delegation.

## Automated Commands

Run syntax checks after touching plugin JavaScript:

```powershell
Push-Location paperforge/plugin
node --check main.js
node --check src/canvas/view-model.js
node --check src/canvas/layout.js
node --check src/canvas/render.js
Pop-Location
```

Run focused ANN11 and regression tests:

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs
Pop-Location
```

Inspect Vitest output for `Startup Error`, `failed to load config`, and `FAIL`; do not rely on shell exit code alone if those strings appear.

## Nyquist Sampling

- Per task: run the smallest focused Vitest command that covers the touched helper, renderer, DOM test, CSS hook, or runtime gate.
- Per wave: run all ANN11 tests created so far plus the relevant ANN10/v0.2 regression tests named in the plan.
- Phase gate: run `node --check main.js`, syntax checks for touched `src/canvas/*` files, all ANN11 canvas tests, and existing v0.2 annotation list/runtime DOM tests.

## Blocking Criteria

- Do not proceed with ANN11-02 runtime work if ANN10-02 runtime wiring is absent.
- Do not render cards from raw loader results when ANN11-01 card view-model output is available.
- Do not collapse missing DB, command failure, refresh, or stale states into empty card lanes.
- Do not expose create, edit, delete, save, import, apply, write-back, evidence mutation, or concept-card controls.
- Do not add source anchors, bidirectional navigation, connector lines, draggable/freeform layout, persistent layout, new dependencies, direct SQLite/Zotero reads, or new Python subprocess APIs.
- Do not insert annotation selected text, comments, or provenance with `innerHTML`.
