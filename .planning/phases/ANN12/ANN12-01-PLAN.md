---
phase: ANN12
plan: "01"
type: execute
wave: 1
depends_on:
  - ANN11-01
  - ANN11-02
files_modified:
  - paperforge/plugin/src/canvas/surface.js
  - paperforge/plugin/src/canvas/anchors.js
  - paperforge/plugin/src/canvas/view-model.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-source-anchor.test.mjs
  - paperforge/plugin/tests/canvas-viewmodel.test.mjs
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
  - D-23
  - D-24
  - D-25
  - D-26
must_haves:
  truths:
    - "D-01/D-02/D-03: Source selection prefers entry.fulltext_path content, falls back to entry.note_path content, then produces an explicit source-unavailable model with diagnostics."
    - "D-04/D-05/D-26: Source and anchor contracts are pure PaperForge-owned data contracts with no native PDF DOM selectors, no Obsidian PDF viewer dependency, and no unsafe source or annotation text insertion."
    - "D-06/D-07/D-08/D-09/D-10: Every annotation receives exactly one visible precision status: exact, page-level, or unresolved, with exact reserved for unique source-text grounding."
    - "D-11/D-12/D-13/D-14: Exact anchors are produced only when normalized selected text has exactly one owned-source match; missing, short, ambiguous, uncertain, or source-mismatched cases downgrade with reason, matchCount, sourceKind, pageIndex, and annotation identity diagnostics."
    - "D-15/D-16/D-17/D-18: Cards remain visible when source content is missing, source unavailable is distinct from no annotations, and missing path versus unreadable file reasons are represented where runtime data can provide them."
    - "D-23/D-24/D-25: Anchor identity/status/span/page/reason/provenance are exposed for ANN13/ANN14 consumers without adding navigation, selection sync, connector geometry, SVG paths, mutation controls, or write-back affordances."
    - "Context decision coverage in this plan: D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-23 D-24 D-25 D-26."
  artifacts:
    - path: "paperforge/plugin/src/canvas/surface.js"
      provides: "Pure source selection, source text normalization, page/block shaping, and source-unavailable diagnostics"
    - path: "paperforge/plugin/src/canvas/anchors.js"
      provides: "Conservative exact/page-level/unresolved source anchor resolver"
    - path: "paperforge/plugin/src/canvas/view-model.js"
      provides: "Card view-model integration with computed source anchor models"
    - path: "paperforge/plugin/src/canvas/index.js"
      provides: "Narrow CommonJS exports for ANN12 source and anchor helpers"
    - path: "paperforge/plugin/tests/canvas-source-anchor.test.mjs"
      provides: "Source priority, unavailable-source, exact/page-level/unresolved, downgrade, and diagnostics tests"
    - path: "paperforge/plugin/tests/canvas-viewmodel.test.mjs"
      provides: "Card visibility, anchor integration, source mismatch, and no-action-control regression tests"
  key_links:
    - from: "paperforge/plugin/src/canvas/surface.js"
      to: "paperforge/plugin/main.js"
      via: "runtime passes read file results into pure source model"
      pattern: "source helper accepts text/path/status inputs and performs no fs or Obsidian calls"
    - from: "paperforge/plugin/src/canvas/anchors.js"
      to: "paperforge/plugin/src/canvas/view-model.js"
      via: "buildCanvasCardViewModel attaches computed card.anchor"
      pattern: "exact|page-level|unresolved"
    - from: "paperforge/plugin/src/canvas/index.js"
      to: "paperforge/plugin/src/canvas/surface.js and anchors.js"
      via: "module.exports"
      pattern: "buildCanvasSourceModel|resolveCanvasAnchor"
---

<objective>
Create the pure source surface and anchor resolver contracts for ANN12.

Purpose: give the PaperForge Reading Canvas an honest source-grounding model before DOM/runtime work consumes it.
Output: `surface.js`, `anchors.js`, view-model integration, CommonJS exports, and focused Vitest coverage for source priority, exact/page-level/unresolved anchors, downgrade reasons, diagnostics, missing source behavior, and the read-only boundary.
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
@.planning/phases/ANN11/ANN11-01-SUMMARY.md
@.planning/phases/ANN11/ANN11-02-SUMMARY.md
@paperforge/plugin/package.json
@paperforge/plugin/src/canvas/context.js
@paperforge/plugin/src/canvas/view-model.js
@paperforge/plugin/src/canvas/layout.js
@paperforge/plugin/src/canvas/render.js
@paperforge/plugin/src/canvas/index.js
@paperforge/plugin/tests/canvas-viewmodel.test.mjs
</context>

<source_audit>
SOURCE | ID | Feature/Requirement | Plan | Status | Notes
GOAL | ANN12 | PaperForge-owned central reading surface with measurable source grounding | ANN12-01 and ANN12-02 | COVERED | ANN12-01 defines source/anchor contracts; ANN12-02 renders and loads source content.
REQ | ANCHOR-01 | Source anchors render for supported PaperForge-owned position, text, or page data | ANN12-01 and ANN12-02 | COVERED | ANN12-01 resolves anchor models; ANN12-02 renders exact/page-level/unresolved DOM.
REQ | ANCHOR-02 | Page-level or unresolved fallback anchors render when exact anchoring is unavailable | ANN12-01 and ANN12-02 | COVERED | ANN12-01 downgrade rules; ANN12-02 visible fallback statuses.
RESEARCH | Pure source model and anchor resolver before DOM/runtime integration | ANN12-01 | COVERED | Implements recommended `surface.js` and `anchors.js` split with no new packages.
RESEARCH | No native PDF internals, no fuzzy guessing, safe text rendering | ANN12-01 and ANN12-02 | COVERED | Pure helpers avoid DOM; ANN12-02 adds static/DOM tests.
CONTEXT | D-01 through D-18, D-23 through D-26 | ANN12-01 | COVERED | Cited in truths and task actions.
CONTEXT | D-19 through D-22 | ANN12-02 | COVERED | Render/CSS decisions are implemented in the dependent plan.
</source_audit>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Define pure source surface priority and diagnostics</name>
  <files>paperforge/plugin/src/canvas/surface.js, paperforge/plugin/src/canvas/index.js, paperforge/plugin/tests/canvas-source-anchor.test.mjs</files>
  <behavior>
    - Test D-01: when `entry.fulltext_path` and readable fulltext content are present, the source model is `ready`, `sourceKind` is `fulltext`, and note content is ignored.
    - Test D-02: when fulltext is unavailable but `entry.note_path` has usable readable content, the source model is `ready`, `sourceKind` is `note`, and diagnostics record the fulltext miss.
    - Test D-03/D-16/D-18: when neither source is usable, the source model is `source-unavailable`, cards are not treated as absent, and the reason does not imply there are no annotations.
    - Test D-17: missing `fulltext_path`/`note_path` and unreadable file results are distinguishable when the caller supplies path/read status details.
    - Test D-04/D-05/D-26: source helpers are pure CommonJS data functions with no `fs`, no Obsidian imports, no native PDF selectors, no PDF canvas probing, and no `innerHTML`.
  </behavior>
  <action>Create `paperforge/plugin/src/canvas/surface.js` as a pure CommonJS module. Define source constants and helpers such as `SOURCE_KINDS`, `SOURCE_STATES`, `buildCanvasSourceModel(entry, sourceInputs, options)`, `buildSourceBlocks(sourceText, sourceKind)`, and `normalizeSourceTextForAnchors(value)`. The helper must accept already-read runtime data rather than reading files directly: for example fulltext and note inputs can carry `path`, `text`, `exists`, `readable`, and `error` fields. Per D-01 through D-03, select source content in strict priority order: usable fulltext from `entry.fulltext_path`, then usable note body from `entry.note_path`, then a source-unavailable model with a clear reason. Per D-17, preserve reason values that distinguish missing path from unreadable/missing file when the caller supplies that information, such as `fulltext-path-missing`, `fulltext-file-missing`, `note-path-missing`, and `note-file-missing`. Per D-04, D-05, and D-26, keep this module independent of native PDF DOM selectors/classes, Obsidian PDF viewer internals, browser DOM APIs, `fs`, database, subprocess, and `innerHTML`. Shape OCR `fulltext.md` page markers such as `<!-- page N -->` into source blocks with stable ids and page metadata, but treat page blocks as PaperForge-owned text/page data, not PDF canvas geometry. Export the new helpers from `index.js` without removing ANN10 or ANN11 exports.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check src/canvas/surface.js; npm.cmd test -- canvas-source-anchor.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Source modeling is pure, priority-ordered, diagnostic-rich, and distinguishes source-unavailable from empty annotations without using native PDF or unsafe DOM mechanisms.</acceptance_criteria>
  <done>`surface.js` exists, is exported, and focused source priority/unavailable diagnostics tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Resolve conservative anchors and attach them to card view-models</name>
  <files>paperforge/plugin/src/canvas/anchors.js, paperforge/plugin/src/canvas/view-model.js, paperforge/plugin/src/canvas/index.js, paperforge/plugin/tests/canvas-source-anchor.test.mjs, paperforge/plugin/tests/canvas-viewmodel.test.mjs</files>
  <behavior>
    - Test D-06 through D-10: every card anchor has status `exact`, `page-level`, or `unresolved`, and the model exposes enough label/status data for the UI to distinguish the statuses.
    - Test D-11/D-13: normalized selected text with exactly one owned-source match produces `exact` with a raw source span and `matchCount: 1`; repeated matches never produce exact.
    - Test D-12: empty selected text, selected text below the chosen conservative threshold, missing source text, ambiguous matches, source/paper identity mismatch, and normalization-uncertain cases downgrade to `page-level` or `unresolved`.
    - Test D-08/D-09/D-16: page metadata without a unique text span produces `page-level` when source blocks can represent the page, and missing source/page metadata produces `unresolved`.
    - Test D-14/D-23: every anchor preserves `anchorId`, `cardId`, `sourceKind`, `reason`, `matchCount`, `pageIndex`, annotation identity, and provenance diagnostics.
    - Test D-15/D-18/D-24/D-25: cards remain visible with unresolved anchors when source is missing, and no navigation, connector, SVG, mutation, import/apply, or write-back fields are introduced.
  </behavior>
  <action>Create `paperforge/plugin/src/canvas/anchors.js` with pure helpers such as `ANCHOR_STATUSES`, `MIN_EXACT_TEXT_CHARS`, `resolveCanvasAnchor(card, sourceModel, options)`, `resolveCanvasAnchors(cards, sourceModel, options)`, and `findNormalizedSourceMatches(sourceText, selectedText)`. Use a conservative normalization rule that collapses whitespace and preserves a raw-offset mapping; if normalization cannot map a selected string back to one raw source span with confidence, downgrade rather than guessing per D-12 and D-13. Choose and export a documented `MIN_EXACT_TEXT_CHARS` threshold, and test that text below it downgrades. Exact is allowed only for one normalized match in the PaperForge-owned source text per D-07 and D-11. If the selected text is absent, too short, repeated, missing from the source, tied to a different paper/source identity, or has uncertain punctuation/CJK/whitespace offset mapping, return `page-level` when usable page/source metadata exists and otherwise `unresolved`. Extend `buildCanvasCard()` or `buildCanvasCardViewModel()` in `view-model.js` so cards receive computed anchors from an optional `sourceModel` or `sourceInputs` option while keeping ANN11 card fields and lane behavior intact. Preserve card visibility when source is missing per D-15 and D-18. Do not add DOM rendering, scroll/focus navigation, source-to-card selection sync, connector classes, SVG geometry, create/edit/delete/save/import/apply/write-back/evidence mutation controls, new subprocesses, direct SQLite/Zotero reads, or native PDF DOM hooks. Export anchor helpers from `index.js`.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check src/canvas/anchors.js; node --check src/canvas/view-model.js; npm.cmd test -- canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs annotation-list-viewmodel.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Anchor resolution is deterministic and conservative; exact/page-level/unresolved states and downgrade diagnostics are test-covered; card lanes still render all valid annotation cards when source grounding is unavailable.</acceptance_criteria>
  <done>`anchors.js`, view-model integration, exports, and focused anchor/card tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Runtime source read result -> surface.js | Vault file text and path/read diagnostics enter pure source modeling. |
| Annotation card model -> anchors.js | Imported annotation selected text, page metadata, and provenance are used to compute grounding precision. |
| Source/anchor model -> ANN12-02 DOM rendering | Exact spans and downgrade reasons must not overstate evidence precision. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ANN12-01-S | Spoofing | Anchor source identity | mitigate | Compare card/source paper identity and provenance where available; source mismatch downgrades per D-12. |
| T-ANN12-01-T | Tampering | Anchor precision model | mitigate | Exact requires one normalized owned-source match; ambiguous and uncertain cases downgrade with diagnostics. |
| T-ANN12-01-R | Repudiation | Downgrade reasons | mitigate | Preserve reason, matchCount, sourceKind, pageIndex, cardId, and annotation identity on every anchor per D-14. |
| T-ANN12-01-I | Information Disclosure | Source text modeling | mitigate | Pure helpers do not log or expose raw runtime errors beyond concise diagnostic reason fields needed for UI/tests. |
| T-ANN12-01-D | Denial of Service | Large source text matching | mitigate | Source blocks are bounded by page markers and exact matching remains deterministic; tests include repeated text downgrade behavior. |
| T-ANN12-01-E | Elevation of Privilege | Anchor model actions | mitigate | Anchor/card models contain no functions, mutation controls, import/apply/write-back affordances, navigation handlers, or connector geometry. |
| T-ANN12-01-SC | Tampering | npm installs | accept | No package-manager install is planned; use the existing CommonJS/Vitest/jsdom stack only. |

</threat_model>

<verification>

Run from the repository root:

```powershell
Push-Location paperforge/plugin
node --check src/canvas/surface.js
node --check src/canvas/anchors.js
node --check src/canvas/view-model.js
npm.cmd test -- canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs annotation-list-viewmodel.test.mjs
Pop-Location
```

Inspect Vitest output for `Startup Error`, `failed to load config`, and `FAIL`; do not treat a shell exit code alone as sufficient if those strings appear.

</verification>

<success_criteria>

- Source modeling chooses `fulltext_path` content first, `note_path` content second, and explicit source-unavailable third.
- Missing path and missing/unreadable file causes are distinguishable when runtime inputs expose them.
- Anchor statuses are exactly `exact`, `page-level`, and `unresolved`.
- Exact anchors require exactly one normalized match in PaperForge-owned source text.
- Empty, too-short, missing-source, ambiguous, source-mismatched, or normalization-uncertain text downgrades without fuzzy guessing.
- Page-level and unresolved anchors preserve visible reasons and diagnostics for ANN12-02 rendering.
- Cards remain visible when source content is missing.
- The implementation introduces no native PDF selectors/classes, PDF canvas anchoring, Obsidian PDF viewer dependence, connector classes, SVG geometry, navigation, selection sync, editing/import/apply/write-back controls, or mutation affordances.

</success_criteria>
