# ANN12 Validation Strategy: Controlled Reading Surface and Source Anchors

**Phase:** ANN12  
**Requirements:** ANCHOR-01, ANCHOR-02  
**Nyquist validation:** enabled  
**Status:** Planned

## Validation Goal

ANN12 is valid only when the PaperForge Reading Canvas can load a PaperForge-owned source surface, attach honest anchor precision statuses to cards, and render those statuses safely without implying unsupported PDF, navigation, connector, or mutation behavior.

The validation strategy samples each critical behavior at two layers:

- Pure model layer: source selection, source blocks, exact/page-level/unresolved anchor resolution, downgrade diagnostics.
- DOM/runtime layer: vault source loading, central source rendering, safe text insertion, CSS/status classes, and forbidden-scope scans.

## Must Prove

| ID | Required truth | Covered by |
|----|----------------|------------|
| V-01 | Fulltext wins over note source when both are available. | `canvas-source-anchor.test.mjs`, `canvas-main-runtime.test.mjs` |
| V-02 | Note source is used only when fulltext path/content is unavailable. | `canvas-source-anchor.test.mjs`, `canvas-main-runtime.test.mjs` |
| V-03 | Missing source renders a source-unavailable state, not a blank or empty-annotations state. | `canvas-source-anchor.test.mjs`, `canvas-render.test.mjs`, `canvas-card-dom.test.mjs` |
| V-04 | Missing path and missing/unreadable file are distinguishable where runtime inputs expose that distinction. | `canvas-source-anchor.test.mjs`, `canvas-main-runtime.test.mjs` |
| V-05 | Exact anchors require exactly one normalized match in PaperForge-owned source text. | `canvas-source-anchor.test.mjs` |
| V-06 | Ambiguous, missing, too-short, source-mismatched, or normalization-uncertain selected text downgrades without fuzzy guessing. | `canvas-source-anchor.test.mjs`, `canvas-viewmodel.test.mjs` |
| V-07 | Page metadata without exact text grounding renders page-level, not inline highlight. | `canvas-source-anchor.test.mjs`, `canvas-render.test.mjs` |
| V-08 | Unresolved anchors render explanation/status only and no source marker. | `canvas-source-anchor.test.mjs`, `canvas-render.test.mjs` |
| V-09 | Cards remain visible when source is missing or ungroundable. | `canvas-viewmodel.test.mjs`, `canvas-card-dom.test.mjs` |
| V-10 | Source, note, selected text, comment, and reason strings render through safe text insertion only. | `canvas-render.test.mjs`, `canvas-card-dom.test.mjs` |
| V-11 | No native PDF DOM selectors/classes, PDF canvas anchoring, connector classes, SVG connector paths, navigation hooks, selection sync, or mutation controls are introduced. | `canvas-main-runtime.test.mjs`, static scan |

## Automated Gates

Run from the repository root after ANN12 implementation:

```powershell
Push-Location paperforge/plugin
node --check main.js
node --check src/canvas/surface.js
node --check src/canvas/anchors.js
node --check src/canvas/view-model.js
node --check src/canvas/render.js
npm.cmd test -- canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs canvas-layout.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs
Pop-Location
```

Inspect output for `Startup Error`, `failed to load config`, `FAIL`, and unhandled promise warnings.

Then run the static scope scan:

```powershell
Select-String -Path paperforge/plugin/main.js,paperforge/plugin/src/canvas/*.js,paperforge/plugin/styles.css -Pattern '\.pdf-viewer|\.pdf-embed|\[data-page-number\]|paperforge-canvas-connector|createElement\(''svg''|<svg|card-to-source|source-to-card|selection-sync|write-back|writeback|apply|import' -CaseSensitive
```

Any hit must be inspected against ANN12 scope:

- Native PDF selectors/classes fail.
- Connector classes or SVG connector paths fail.
- ANN12 card-source/source-card navigation or selection-sync hooks fail.
- Mutation controls or labels fail when they are in the Reading Canvas/source/anchor path.
- Existing non-ANN12 icon SVG usage may remain only if it is outside ANN12 source/anchor rendering.

## Test Fixture Matrix

| Fixture | Expected result |
|---------|-----------------|
| Entry has `fulltext_path` and fulltext text with one selected-text occurrence. | Source `fulltext`; anchor `exact`; inline highlight allowed. |
| Entry has `fulltext_path` and note text, but fulltext text is unreadable/missing. | Source `note` if note is usable; diagnostics preserve fulltext miss reason. |
| Entry lacks both usable fulltext and note content but has annotations. | Source unavailable; cards visible; anchors unresolved with source reason. |
| Selected text appears twice after normalization. | Not exact; page-level if page metadata usable, otherwise unresolved; `matchCount` is greater than 1. |
| Selected text is empty or below threshold. | Not exact; page-level or unresolved with reason. |
| Annotation page metadata exists but selected text cannot be uniquely matched. | Page-level marker, no inline highlight. |
| Annotation/source paper identity mismatches. | Downgrade; no exact anchor. |
| Source text contains HTML-like strings. | Literal text visible; no live `script`, `img`, `onclick`, or injected tags. |

## Residual Risk

ANN12 does not validate live Obsidian PDF overlay behavior, PDF DOM anchoring, navigation round-trips, or connector geometry. Those are outside this phase and remain covered by ANN13, ANN14, and ANN15 validation artifacts.
