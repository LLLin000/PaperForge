---
phase: ANN12
plan: "01"
subsystem: canvas
tags:
  - source-surface
  - anchor-resolver
  - commonjs
  - pure-functions
  - tdd

# Dependency graph
requires:
  - phase: ANN11-01
    provides: canvas card view-models with lane layout (buildCanvasCard, buildCanvasCardViewModel)
  - phase: ANN11-02
    provides: card lane DOM rendering, CSS resilience, runtime regression tests
provides:
  - Pure source surface model with fulltext → note → source-unavailable priority (surface.js)
  - Pure conservative anchor resolver with exact/page-level/unresolved statuses (anchors.js)
  - View-model integration: buildCanvasCard accepts optional sourceModel, buildCanvasCardViewModel accepts options.sourceModel
  - Normalized match finder with whitespace-collapse and raw-offset mapping
  - 251 passing tests across 4 test files
affects:
  - ANN12-02: DOM rendering of source content and anchor visual states
  - ANN13/ANN14: anchor identity/status/span/page/reason/provenance consumers

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure source surface selection: entry path → runtime inputs → source model"
    - "Conservative anchor resolution: exactly one normalized match = exact, else page-level or unresolved"
    - "Threat-aware identity checks: card paperKey vs sourceModel paperKey mismatch → page-level downgrade"

key-files:
  created:
    - paperforge/plugin/src/canvas/surface.js
    - paperforge/plugin/src/canvas/anchors.js
    - paperforge/plugin/tests/canvas-source-anchor.test.mjs
  modified:
    - paperforge/plugin/src/canvas/view-model.js
    - paperforge/plugin/src/canvas/index.js
    - paperforge/plugin/tests/canvas-viewmodel.test.mjs

key-decisions:
  - "Source priority: usable fulltext_path → usable note_path → source-unavailable with diagnostics"
  - "Anchor statuses: exact (1 normalized match), page-level (page metadata without unique text), unresolved (no source/page)"
  - "MIN_EXACT_TEXT_CHARS = 3; text below threshold always downgrades to page-level"
  - "Paper identity mismatch (card.paperKey ≠ sourceModel.paperKey) triggers page-level downgrade per T-ANN12-01-S"
  - "Normalization: whitespace collapse only — no case folding, no punctuation stripping, no stemming"
  - "sourceModel carries paperKey from entry for downstream identity checks"

patterns-established:
  - "sourceInputs carry already-read runtime data (path, text, exists, readable, error) — pure helpers never do I/O"
  - "Anchor diagnostics preserve full provenance: anchorId, cardId, sourceKind, reason, matchCount, pageIndex, sourceSpan"

requirements-completed:
  - ANCHOR-01
  - ANCHOR-02

# Metrics
duration: 12min
completed: 2026-07-06
---

# Phase ANN12 Plan 01: Pure Source Surface and Anchor Resolver Contracts

**Pure source surface model with fulltext→note→unavailable priority and conservative exact/page-level/unresolved anchor resolver, integrated into canvas card view-models**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-06T11:37:00Z
- **Completed:** 2026-07-06T11:49:00Z
- **Tasks:** 8 (TDD: RED → GREEN per task)
- **Files modified:** 6

## Accomplishments

- **surface.js**: Pure source selection with strict priority (fulltext → note → source-unavailable), page-block shaping from OCR markers (`<!-- page N -->`), whitespace-collapse normalization with raw-offset mapping, D-17 diagnostics distinguishing path-missing vs file-missing
- **anchors.js**: Conservative anchor resolver with three statuses (exact/page-level/unresolved), normalized match finder with whitespace collapse, paper-identity mismatch detection, empty/too-short/ambiguous/not-found downgrade with diagnostics
- **view-model.js integration**: `buildCanvasCard(row, sourceModel)` accepts optional source model; `buildCanvasCardViewModel(annotationState, { sourceModel })` passes source through for anchor computation — fully backward compatible
- **index.js exports**: All 11 new surface and anchor helpers exported alongside existing ANN10/ANN11 exports
- **Test coverage**: 251 tests across 4 files (51 surface+anchor, 89 view-model, 33 layout, 78 annotation-list-viewmodel) — all passing

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED: failing tests for surface/anchor contracts** — `b8a958d` (test)
2. **Task 1 GREEN: anchor resolver** — `77de24f` (feat)
3. **Task 1 GREEN: source surface model + view-model integration** — `4a6ced2` (feat)
4. **Task 2: anchor integration + sourceModel tests** — `ce74032` (test)

**Plan metadata:** pending final commit

## Files Created/Modified

- `paperforge/plugin/src/canvas/surface.js` (NEW) — Source surface selection, block shaping, text normalization
- `paperforge/plugin/src/canvas/anchors.js` (NEW) — Conservative anchor resolver
- `paperforge/plugin/src/canvas/view-model.js` (MOD) — Source model integration for anchor computation
- `paperforge/plugin/src/canvas/index.js` (MOD) — Surface + anchor exports
- `paperforge/plugin/tests/canvas-source-anchor.test.mjs` (NEW) — 51 tests for source/anchor contracts
- `paperforge/plugin/tests/canvas-viewmodel.test.mjs` (MOD) — 89 tests (+11 new anchor integration tests)

## Decisions Made

- **Source selection priority**: Usable fulltext from `entry.fulltext_path` first, then usable note from `entry.note_path`, then explicit source-unavailable model — strict order per D-01 through D-03
- **Anchor granularity**: Three distinct statuses — `exact` (one unique normalized match), `page-level` (page metadata without unique text), `unresolved` (no source/page) — per D-06 through D-10
- **Text normalization**: Whitespace-collapse only (no case folding, no punctuation stripping, no stemming) — conservative approach per D-12/D-13 to avoid false positives
- **MIN_EXACT_TEXT_CHARS = 3**: Selected text shorter than 3 characters always downgrades to page-level, preventing trivial "a" or "an" from producing misleading exact anchors
- **Paper identity tracking**: Source model carries `paperKey` from entry; identity mismatch between card and source model produces page-level anchor with clear reason (T-ANN12-01-S mitigation)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- **D-17 path/file distinction fix**: `_computeSourceUnavailableReason` initially only checked `entry.fulltext_path`/`entry.note_path`, but callers may provide path info via `sourceInputs` instead. Fixed to fall back to `input.path` when entry path is null.
- **Paper identity mismatch**: Initial anchor implementation didn't check paper identity because `buildCanvasSourceModel` didn't expose `paperKey`. Added `paperKey` field to the source model return object.

## Threat Surface Scan

No new threat flags — all new exports are pure data-model functions with no network, file I/O, DOM, or subprocess access. The `paperKey` field on source models enables downstream identity verification per T-ANN12-01-S.

## Next Phase Readiness

- ANN12-02 can consume source models and anchor results for DOM rendering of source content and anchor visual states
- Anchor diagnostics (anchorId, cardId, sourceKind, reason, matchCount, pageIndex, sourceSpan) ready for ANN13/ANN14 consumers
- Card visibility when source missing is tested and confirmed (D-15/D-18)

---
*Phase: ANN12-01*
*Completed: 2026-07-06*
